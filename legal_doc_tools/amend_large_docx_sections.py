#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from model_applicable_service import is_placeholder_api_key, send_message_with_docs
try:
    from rag_service import get_relevant_context
    RAG_AVAILABLE = True
except Exception:
    get_relevant_context = None  # type: ignore[assignment]
    RAG_AVAILABLE = False

from legal_doc_tools.amend_docx import (
    _assert_original_footnotes_preserved_if_relevant,
    _replace_existing_footnote_text,
    _rewrite_body_paragraph_preserving_footnotes,
)
from legal_doc_tools.refine_docx_from_amended import (
    DESKTOP_ROOT,
    _build_footnote_search_text_map,
    _copy_source_to_temp_if_same_as_output,
    _footnote_reference_runs_with_positions,
    _iter_body_paragraphs,
    _load_docx_xml,
    _load_docx_xml_if_exists,
    _normalize_to_final_output_path,
    _normalize_body_footnote_reference_positions,
    _normalize_body_footnote_reference_styles_from_original,
    _normalize_body_italics,
    _normalize_case_italics_in_footnotes,
    _normalize_footnote_styles_from_original,
    _paragraph_text_all_runs,
    _require_desktop_root_output,
    _write_docx_with_replaced_parts,
    _assert_markup_detectable,
)
from legal_doc_tools.validate_delivery_gates import _oscola_issues
from legal_doc_tools.workflow import (
    DocxSnapshot,
    _build_structured_amend_prompt,
    _extract_json_object,
    _normalize_plan,
)


WORD_RE = re.compile(r"\b\w+\b", flags=re.UNICODE)
CHAPTER_HEADING_RE = re.compile(r"^Chapter\s+(\d+):\s+")
TOPIC_HEADING_RE = re.compile(r"^Topic\s+(\d+)\.\s+")
SECTION_HEADING_RE = re.compile(r"^(Abstract|Chapter\s+\d+:\s+.+|Topic\s+\d+\.\s+.+)$")


@dataclass(frozen=True)
class Section:
    name: str
    start_index: int
    end_index: int

    @property
    def display_range(self) -> str:
        return f"{self.start_index + 1}-{self.end_index + 1}"


def _word_count(texts: Sequence[str]) -> int:
    return len(WORD_RE.findall("\n".join(texts)))


def _normalize_heading(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().casefold()


def _load_api_key(provider: str, root: Path) -> str:
    env_map = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "xai": "XAI_API_KEY",
    }
    env_name = env_map.get(provider.strip().lower(), "GEMINI_API_KEY")
    direct = (os.environ.get(env_name) or "").strip()
    if direct and not is_placeholder_api_key(direct):
        return direct

    env_file = root / ".env.local"
    if env_file.exists():
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == env_name:
                candidate = value.strip().strip("'").strip('"')
                if candidate and not is_placeholder_api_key(candidate):
                    return candidate
    raise ValueError(
        f"Missing usable {env_name}. Set a real provider key in the environment or {env_file}. "
        "The DOCX pipeline is local, but provider-backed amendment generation still needs a configured backend model key."
    )


def _detect_sections(paragraph_texts: Sequence[str]) -> List[Section]:
    abstract_idx: Optional[int] = None
    toc_idx: Optional[int] = None
    bibliography_idx: Optional[int] = None
    chapter_starts: Dict[int, int] = {}
    topic_starts: Dict[int, int] = {}

    for idx, text in enumerate(paragraph_texts):
        stripped = (text or "").strip()
        normalized = _normalize_heading(stripped)
        if normalized == "abstract" and abstract_idx is None:
            abstract_idx = idx
        elif normalized in {"table of contents", "contents"} and toc_idx is None:
            toc_idx = idx
        elif normalized == "bibliography":
            bibliography_idx = idx

        match = CHAPTER_HEADING_RE.match(stripped)
        if match:
            chapter_starts[int(match.group(1))] = idx
        match = TOPIC_HEADING_RE.match(stripped)
        if match:
            # Contents pages often repeat the topic headings before the real body.
            # Keep the latest occurrence so section export targets the actual section text.
            topic_starts[int(match.group(1))] = idx

    section_prefix: Optional[str] = None
    section_starts: Dict[int, int] = {}
    if chapter_starts:
        section_prefix = "chapter"
        section_starts = chapter_starts
    elif topic_starts:
        section_prefix = "topic"
        section_starts = topic_starts
    else:
        raise ValueError("Could not locate chapter or topic headings in the DOCX body.")

    boundaries = sorted(section_starts.values())
    if bibliography_idx is not None:
        boundaries.append(bibliography_idx)

    sections: List[Section] = []
    if abstract_idx is not None:
        abstract_end = (toc_idx - 1) if toc_idx is not None and toc_idx > abstract_idx else (min(boundaries) - 1)
        if abstract_end >= abstract_idx:
            sections.append(Section(name="abstract", start_index=abstract_idx, end_index=abstract_end))

    section_items = sorted(section_starts.items())
    for pos, (section_no, start_idx) in enumerate(section_items):
        if pos + 1 < len(section_items):
            end_idx = section_items[pos + 1][1] - 1
        else:
            end_idx = (bibliography_idx - 1) if bibliography_idx is not None else len(paragraph_texts) - 1
        sections.append(
            Section(
                name=f"{section_prefix}_{section_no}",
                start_index=start_idx,
                end_index=end_idx,
            )
        )
    return sections


def _section_footnote_ids(paragraphs: Iterable) -> List[int]:
    ids: List[int] = []
    seen: set[int] = set()
    for paragraph in paragraphs:
        for _run, _pos, ref_id in _footnote_reference_runs_with_positions(paragraph):
            try:
                parsed = int(ref_id)
            except (TypeError, ValueError):
                continue
            if parsed in seen:
                continue
            seen.add(parsed)
            ids.append(parsed)
    return ids


def _frozen_paragraph_indexes(paragraph_texts: Sequence[str]) -> set[int]:
    frozen: set[int] = set()
    for idx, text in enumerate(paragraph_texts):
        stripped = (text or "").strip()
        normalized = _normalize_heading(stripped)
        if not stripped:
            frozen.add(idx)
            continue
        if normalized in {"abstract", "keywords:"}:
            frozen.add(idx)
            continue
        if stripped.lower().startswith("keywords:"):
            frozen.add(idx)
            continue
        if SECTION_HEADING_RE.match(stripped):
            frozen.add(idx)
    return frozen


def _allowed_word_drift(original_words: int, *, max_drift_pct: float, max_drift_words: int) -> int:
    pct_drift = int(round(original_words * (max_drift_pct / 100.0)))
    return max(max_drift_words, pct_drift)


def _section_request(section: Section, *, original_words: int, lower_bound: int, upper_bound: int) -> str:
    label = section.name.replace("_", " ")
    return (
        f"Amend this DOCX section ({label}) to a genuine 90+ standard. "
        f"Keep the paragraph count identical. The current section is about {original_words} words; "
        f"keep the amended section between {lower_bound} and {upper_bound} words. "
        "Keep the authorial voice and thesis. Make real analytical improvements, not cosmetic padding. "
        "Use indexed RAG material and verification where helpful, but never invent authorities. "
        "Do not change heading paragraphs, keyword lines, or blank paragraphs. "
        "Do not add or remove live footnote IDs. Preserve user italics and local DOCX styling unless a targeted OSCOLA correction is required."
    )


def _section_plan_path(plan_dir: Path, section_name: str) -> Path:
    return plan_dir / f"{section_name}.plan.json"


def _snapshot_for_section(
    *,
    source_path: Path,
    doc_root,
    footnotes_root,
    section: Section,
) -> tuple[list, list[str], DocxSnapshot, set[int], int, int]:
    current_paragraphs = _iter_body_paragraphs(doc_root)
    section_paragraphs = current_paragraphs[section.start_index : section.end_index + 1]
    section_texts = [_paragraph_text_all_runs(p) for p in section_paragraphs]
    footnote_ids = _section_footnote_ids(section_paragraphs)
    footnote_text_map = _build_footnote_search_text_map(footnotes_root) if footnotes_root is not None else {}
    selected_footnotes = {fid: footnote_text_map[fid] for fid in footnote_ids if fid in footnote_text_map}
    snapshot = DocxSnapshot(
        source_path=source_path,
        paragraph_texts=section_texts,
        footnotes=selected_footnotes,
    )
    frozen_indexes = _frozen_paragraph_indexes(section_texts)
    original_words = _word_count(section_texts)
    return section_paragraphs, section_texts, snapshot, frozen_indexes, original_words, len(selected_footnotes)


def _baseline_plan(snapshot: DocxSnapshot, *, summary: str) -> Dict[str, object]:
    return {
        "summary": summary,
        "paragraphs": [
            {"index": idx, "text": text}
            for idx, text in enumerate(snapshot.paragraph_texts)
        ],
        "footnotes": [
            {"id": fid, "text": text}
            for fid, text in sorted(snapshot.footnotes.items())
        ],
    }


def export_codex_section_plans(
    *,
    source_path: Path,
    export_dir: Path,
    max_drift_pct: float,
    max_drift_words: int,
    section_filter: Optional[set[str]],
    rag_chunks: int,
) -> Path:
    source_path = source_path.expanduser().resolve()
    export_dir = export_dir.expanduser().resolve()
    export_dir.mkdir(parents=True, exist_ok=True)

    doc_root = _load_docx_xml(source_path, "word/document.xml")
    footnotes_root = _load_docx_xml_if_exists(source_path, "word/footnotes.xml")
    paragraph_texts = [_paragraph_text_all_runs(p) for p in _iter_body_paragraphs(doc_root)]
    sections = _detect_sections(paragraph_texts)
    if section_filter:
        sections = [section for section in sections if section.name in section_filter]
        if not sections:
            raise ValueError(f"No sections matched filter: {sorted(section_filter)}")

    print(
        f"Exporting Codex plan files for sections: {', '.join(section.name for section in sections)}",
        flush=True,
    )

    for section in sections:
        _section_paragraphs, section_texts, snapshot, frozen_indexes, original_words, footnote_count = _snapshot_for_section(
            source_path=source_path,
            doc_root=doc_root,
            footnotes_root=footnotes_root,
            section=section,
        )
        allowed_drift = _allowed_word_drift(
            original_words,
            max_drift_pct=max_drift_pct,
            max_drift_words=max_drift_words,
        )
        lower_bound = max(0, original_words - allowed_drift)
        upper_bound = original_words + allowed_drift
        request = _section_request(
            section,
            original_words=original_words,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )
        rag_query = request + "\n\n" + "\n\n".join(
            text for text in section_texts if text.strip()
        )
        rag_context = ""
        if rag_chunks > 0 and RAG_AVAILABLE and get_relevant_context is not None:
            try:
                rag_context = get_relevant_context(
                    rag_query,
                    max_chunks=rag_chunks,
                    query_type="general",
                    max_chars=18000,
                )
            except Exception as exc:
                rag_context = f"[RAG ERROR] {type(exc).__name__}: {exc}"

        plan = _baseline_plan(snapshot, summary="Baseline export for Codex/local amendment planning.")
        plan["_meta"] = {
            "mode": "codex_direct_amend",
            "source_path": str(source_path),
            "section_name": section.name,
            "paragraph_range": [section.start_index, section.end_index],
            "original_word_count": original_words,
            "allowed_word_range": [lower_bound, upper_bound],
            "footnote_count": footnote_count,
            "frozen_paragraph_indexes": sorted(frozen_indexes),
            "user_request": request,
            "rag_chunks": rag_chunks,
            "rag_context": rag_context,
        }
        plan_path = _section_plan_path(export_dir, section.name)
        plan_path.write_text(
            json.dumps(plan, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(
            f"Exported {section.name}: words={original_words} footnotes={footnote_count} -> {plan_path}",
            flush=True,
        )
    return export_dir


def _load_plan_from_file(
    *,
    snapshot: DocxSnapshot,
    plan_path: Path,
) -> tuple[List[str], Dict[int, str], str]:
    raw = plan_path.read_text(encoding="utf-8")
    plan = _extract_json_object(raw)
    return _normalize_plan(snapshot, plan)


def _call_structured_amend(
    *,
    api_key: str,
    provider: str,
    model_name: Optional[str],
    snapshot: DocxSnapshot,
    user_request: str,
    project_id: str,
) -> tuple[List[str], Dict[int, str], str]:
    prompt = _build_structured_amend_prompt(user_request, snapshot)
    print(
        f"Calling model for {project_id}: paragraphs={len(snapshot.paragraph_texts)} footnotes={len(snapshot.footnotes)}",
        flush=True,
    )
    (response_text, _), _rag_context = send_message_with_docs(
        api_key,
        prompt,
        [],
        project_id,
        history=[],
        stream=False,
        provider=provider,
        model_name=model_name,
        enforce_long_response_split=False,
    )
    print(f"Model returned for {project_id}: response_chars={len(response_text or '')}", flush=True)
    plan = _extract_json_object(response_text)
    return _normalize_plan(snapshot, plan)


def _validate_docx(source_path: Path) -> list[str]:
    doc_root = _load_docx_xml(source_path, "word/document.xml")
    footnotes_root = _load_docx_xml_if_exists(source_path, "word/footnotes.xml")
    document_text = "\n".join(_paragraph_text_all_runs(p) for p in _iter_body_paragraphs(doc_root))
    footnotes_text = ""
    if footnotes_root is not None:
        footnotes_text = " ".join(_build_footnote_search_text_map(footnotes_root).values())
    return _oscola_issues(document_text, footnotes_text, footnotes_root, doc_root)


def amend_large_docx(
    *,
    api_key: Optional[str],
    source_path: Path,
    output_path: Path,
    provider: Optional[str],
    model_name: Optional[str],
    max_drift_pct: float,
    max_drift_words: int,
    section_filter: Optional[set[str]],
    plan_dir: Optional[Path] = None,
) -> Path:
    source_path = source_path.expanduser().resolve()
    requested_output = output_path.expanduser().resolve()
    output_path, normalized_output = _normalize_to_final_output_path(source_path, requested_output)
    if normalized_output:
        print(
            f"Requested output path normalized to protected Desktop final DOCX: {output_path}",
            flush=True,
        )
    _require_desktop_root_output(output_path)
    work_source, temp_source_dir = _copy_source_to_temp_if_same_as_output(source_path, output_path)

    try:
        doc_root = _load_docx_xml(work_source, "word/document.xml")
        doc_template = _load_docx_xml(work_source, "word/document.xml")
        footnotes_root = _load_docx_xml_if_exists(work_source, "word/footnotes.xml")
        footnotes_template = _load_docx_xml_if_exists(work_source, "word/footnotes.xml")
        body_paragraphs = _iter_body_paragraphs(doc_root)
        paragraph_texts = [_paragraph_text_all_runs(p) for p in body_paragraphs]
        sections = _detect_sections(paragraph_texts)
        if section_filter:
            sections = [section for section in sections if section.name in section_filter]
            if not sections:
                raise ValueError(f"No sections matched filter: {sorted(section_filter)}")

        print(
            f"Detected sections: {', '.join(f'{section.name}[{section.display_range}]' for section in sections)}",
            flush=True,
        )
        changed_paragraphs = 0
        changed_footnotes = 0
        corrected_footnote_ids: set[int] = set()

        for section in sections:
            section_paragraphs, section_texts, snapshot, frozen_indexes, original_words, _footnote_count = _snapshot_for_section(
                source_path=source_path,
                doc_root=doc_root,
                footnotes_root=footnotes_root,
                section=section,
            )
            allowed_drift = _allowed_word_drift(
                original_words,
                max_drift_pct=max_drift_pct,
                max_drift_words=max_drift_words,
            )
            lower_bound = max(0, original_words - allowed_drift)
            upper_bound = original_words + allowed_drift

            request = _section_request(
                section,
                original_words=original_words,
                lower_bound=lower_bound,
                upper_bound=upper_bound,
            )
            amended_paragraphs: List[str] = []
            amended_footnotes: Dict[int, str] = {}
            summary = ""

            if plan_dir is not None:
                plan_path = _section_plan_path(plan_dir, section.name)
                if not plan_path.exists():
                    raise FileNotFoundError(f"Missing plan file for {section.name}: {plan_path}")
                amended_paragraphs, amended_footnotes, summary = _load_plan_from_file(
                    snapshot=snapshot,
                    plan_path=plan_path,
                )
                for idx in frozen_indexes:
                    amended_paragraphs[idx] = section_texts[idx]
                amended_words = _word_count(amended_paragraphs)
                if not (lower_bound <= amended_words <= upper_bound):
                    raise ValueError(
                        f"Section {section.name} drifted too far from the original length: "
                        f"{original_words} -> {amended_words} words."
                    )
            else:
                if not api_key or not provider:
                    raise ValueError(
                        "Provider-backed generation requires api_key/provider, or supply --plan-dir for Codex/local plan application."
                    )
                for attempt in range(2):
                    attempt_request = request
                    if attempt == 1:
                        attempt_request += (
                            f" Second attempt: your first draft drifted too far from the original length. "
                            f"Stay within {lower_bound}-{upper_bound} words and do not add filler."
                        )

                    amended_paragraphs, amended_footnotes, summary = _call_structured_amend(
                        api_key=api_key,
                        provider=provider,
                        model_name=model_name,
                        snapshot=snapshot,
                        user_request=attempt_request,
                        project_id=f"codex::{source_path.stem}::{section.name}::attempt_{attempt + 1}",
                    )
                    for idx in frozen_indexes:
                        amended_paragraphs[idx] = section_texts[idx]

                    amended_words = _word_count(amended_paragraphs)
                    if lower_bound <= amended_words <= upper_bound:
                        break
                    if attempt == 1:
                        raise ValueError(
                            f"Section {section.name} drifted too far from the original length: "
                            f"{original_words} -> {amended_words} words."
                        )

            section_changed_paragraphs = 0
            for paragraph, new_text in zip(section_paragraphs, amended_paragraphs):
                if new_text != _paragraph_text_all_runs(paragraph):
                    if _rewrite_body_paragraph_preserving_footnotes(paragraph, new_text):
                        changed_paragraphs += 1
                        section_changed_paragraphs += 1

            section_changed_footnotes = 0
            if footnotes_root is not None:
                current_footnotes = _build_footnote_search_text_map(footnotes_root)
                for footnote_id, new_text in amended_footnotes.items():
                    if current_footnotes.get(footnote_id, "") != new_text:
                        if _replace_existing_footnote_text(
                            footnotes_root,
                            footnote_id=footnote_id,
                            new_text=new_text,
                        ):
                            corrected_footnote_ids.add(footnote_id)
                            changed_footnotes += 1
                            section_changed_footnotes += 1

            print(
                f"{section.name}: words {original_words}->{_word_count(amended_paragraphs)}, "
                f"paragraphs changed {section_changed_paragraphs}, footnotes changed {section_changed_footnotes}, "
                f"summary={summary}",
                flush=True,
            )

        if footnotes_root is not None:
            italicized_footnotes = _normalize_case_italics_in_footnotes(footnotes_root)
            if footnotes_template is not None and (changed_footnotes > 0 or italicized_footnotes > 0):
                _normalize_footnote_styles_from_original(footnotes_template, footnotes_root)

        _normalize_body_footnote_reference_styles_from_original(doc_template, doc_root)
        _normalize_body_footnote_reference_positions(doc_root, footnotes_root)
        _normalize_body_italics(doc_root, footnotes_root)

        _assert_original_footnotes_preserved_if_relevant(
            original_doc_root=doc_template,
            amended_doc_root=doc_root,
            original_footnotes_root=footnotes_template,
            amended_footnotes_root=footnotes_root,
            explicitly_corrected_ids=corrected_footnote_ids,
        )

        parts_to_write = {"word/document.xml": doc_root}
        if footnotes_root is not None:
            parts_to_write["word/footnotes.xml"] = footnotes_root
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_docx_with_replaced_parts(work_source, output_path, parts_to_write)
        _assert_markup_detectable(work_source, output_path, changed_paragraphs + changed_footnotes)

        oscola_issues = _validate_docx(output_path)
        if oscola_issues:
            joined = "; ".join(oscola_issues[:10])
            raise ValueError(f"Final OSCOLA validation failed: {joined}")
        if changed_paragraphs + changed_footnotes <= 0:
            raise ValueError("No detectable amendments were generated.")

        print(
            f"Completed: changed_paragraphs={changed_paragraphs} changed_footnotes={changed_footnotes} output={output_path}",
            flush=True,
        )
        return output_path
    finally:
        if temp_source_dir is not None:
            import shutil

            shutil.rmtree(temp_source_dir, ignore_errors=True)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Amend a large DOCX in section-sized batches.")
    parser.add_argument("source", type=Path, help="Path to the source DOCX")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Requested amended DOCX path. The tool always normalizes to a protected Desktop final path "
            "for the source (<stem>_amended_marked_final.docx, then _v2, _v3, etc. if needed). "
            "The original source DOCX is never overwritten."
        ),
    )
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--max-drift-pct", type=float, default=5.0)
    parser.add_argument("--max-drift-words", type=int, default=25)
    parser.add_argument(
        "--export-plan-dir",
        type=Path,
        default=None,
        help="Write Codex/local section plan JSON files and exit without provider generation.",
    )
    parser.add_argument(
        "--plan-dir",
        type=Path,
        default=None,
        help="Load edited section plan JSON files from this directory instead of calling a provider.",
    )
    parser.add_argument(
        "--rag-chunks",
        type=int,
        default=14,
        help="Chunk count for local RAG context when exporting Codex plan files.",
    )
    parser.add_argument(
        "--sections",
        default=None,
        help="Comma-separated section names to amend, e.g. abstract,chapter_1",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    source_path = args.source.expanduser().resolve()
    output_path = (
        args.output.expanduser().resolve()
        if args.output is not None
        else DESKTOP_ROOT / f"{source_path.stem}_amended_marked_final.docx"
    )
    section_filter = None
    if args.sections:
        section_filter = {
            item.strip()
            for item in args.sections.split(",")
            if item.strip()
        }
    if args.export_plan_dir is not None:
        export_codex_section_plans(
            source_path=source_path,
            export_dir=args.export_plan_dir,
            max_drift_pct=args.max_drift_pct,
            max_drift_words=args.max_drift_words,
            section_filter=section_filter,
            rag_chunks=args.rag_chunks,
        )
        return 0

    api_key = None
    if args.plan_dir is None:
        api_key = _load_api_key(args.provider, ROOT_DIR)
    amend_large_docx(
        api_key=api_key,
        source_path=source_path,
        output_path=output_path,
        provider=args.provider if args.plan_dir is None else None,
        model_name=args.model_name,
        max_drift_pct=args.max_drift_pct,
        max_drift_words=args.max_drift_words,
        section_filter=section_filter,
        plan_dir=args.plan_dir,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
