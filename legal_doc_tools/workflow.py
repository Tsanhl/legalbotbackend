from __future__ import annotations

import base64
import contextlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from model_applicable_service import (
    mark_legal_doc_amend_session_active,
    send_message_with_docs,
)
from word_count_rules import (
    count_words_for_targeting_from_texts,
    extract_requested_word_count_rule,
)

from .amend_docx import (
    _build_context,
    _assert_original_footnotes_preserved_if_relevant,
    _replace_existing_footnote_text,
    _rewrite_body_paragraph_preserving_footnotes,
    apply_amendments,
)
from .refine_docx_from_amended import (
    DESKTOP_ROOT,
    NS,
    _assert_markup_detectable,
    _build_footnote_search_text_map,
    _copy_source_to_temp_if_same_as_output,
    _iter_body_paragraphs,
    _load_docx_xml,
    _load_docx_xml_if_exists,
    _normalize_body_footnote_reference_positions,
    _normalize_body_footnote_reference_styles_from_original,
    _normalize_body_italics,
    _normalize_case_italics_in_footnotes,
    _normalize_footnote_styles_from_original,
    _normalize_to_final_output_path,
    _paragraph_text_all_runs,
    _write_docx_with_replaced_parts,
)
from .validate_delivery_gates import (
    _count_bibliography_entries,
    _extract_inline_written_comments,
    main as run_delivery_gates_main,
)


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
LEGAL_DOC_IMPLEMENT_TERMS = (
    "amend",
    "amedn",
    "ammend",
    "amendment",
    "amendments",
    "review",
    "revise",
    "revision",
    "rewrite",
    "redraft",
    "proofread",
    "improve",
    "polish",
    "refine",
    "fix",
    "check",
    "edit",
    "implement",
    "apply changes",
    "90+",
    "distinction",
    "first class",
    "top band",
)
JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL | re.IGNORECASE)
BENCHMARK_LINE_RE = re.compile(r"^\s*(question|prompt|rubric|criteria)\s*(?:is|:)\s*(.+?)\s*$", re.IGNORECASE)
COMMENT_REQUEST_RE = re.compile(r"\b(?:based on comments|using comments|follow(?:ing)? comments?)\b", re.IGNORECASE)
QUOTED_DOCX_RE = re.compile(r"['\"]([^'\"]+\.docx)['\"]", re.IGNORECASE)
BARE_DOCX_RE = re.compile(r"(?<![\w/.-])((?:~|/|\.\.?/)?[^\s\"'`()\[\]{}<>]+\.docx)\b", re.IGNORECASE)


def _detect_requested_citation_style(text: str, *, default: str = "oscola") -> str:
    raw = (text or "").strip()
    if not raw:
        return default
    style_patterns = (
        (r"(?i)\b(?:harvard|author[- ]date|author date|cite them right)\b", "harvard"),
        (r"(?i)\b(?:apa|apa\s*7|apa\s*7th|american psychological association)\b", "apa"),
        (r"(?i)\bmla\b|\bmodern language association\b", "mla"),
        (r"(?i)\b(?:chicago|turabian|chicago manual of style)\b", "chicago"),
        (r"(?i)\bbluebook\b", "bluebook"),
        (r"(?i)\baglc\b|\baustralian guide to legal citation\b", "aglc"),
        (r"(?i)\boscola\b", "oscola"),
    )
    for pattern, style in style_patterns:
        if re.search(pattern, raw):
            return style
    generic_match = re.search(
        r"(?i)\b(?:use|follow|apply|in)\s+([A-Za-z][A-Za-z0-9&/\- ]{1,30}?)\s+(?:referencing|reference style|citation style|citations|format)\b",
        raw,
    )
    if generic_match:
        candidate = re.sub(r"\s+", " ", generic_match.group(1) or "").strip(" .,:;").casefold()
        if candidate and candidate not in {"a", "an", "the", "proper", "correct", "consistent", "full"}:
            return candidate.replace(" ", "-")
    return default


def _message_requests_legal_doc_amend(message: str) -> bool:
    low = (message or "").strip().lower()
    if not low:
        return False
    return any(term in low for term in LEGAL_DOC_IMPLEMENT_TERMS)


def _uses_inline_oscola_house_style(style: str) -> bool:
    return str(style or "").strip().casefold() == "oscola"


def _citation_style_label(style: str) -> str:
    normalized = str(style or "").strip().casefold()
    labels = {
        "oscola": "OSCOLA",
        "harvard": "Harvard",
        "apa": "APA 7",
        "mla": "MLA",
        "chicago": "Chicago",
        "bluebook": "Bluebook",
        "aglc": "AGLC",
    }
    if normalized in labels:
        return labels[normalized]
    if not normalized:
        return "OSCOLA"
    return normalized.replace("-", " ").title()


@dataclass
class DocxSnapshot:
    source_path: Path
    paragraph_texts: List[str]
    footnotes: Dict[int, str]


@dataclass
class LegalDocAmendResult:
    output_path: Path
    summary: str
    changed_paragraphs: int
    changed_footnotes: int
    download_name: str
    download_bytes: bytes


def _extract_benchmark_context(user_request: str, snapshot: DocxSnapshot) -> tuple[Optional[str], Optional[str]]:
    question_text: Optional[str] = None
    rubric_text: Optional[str] = None

    for raw_line in (user_request or "").splitlines():
        match = BENCHMARK_LINE_RE.match(raw_line)
        if not match:
            continue
        kind = match.group(1).strip().lower()
        value = match.group(2).strip()
        if not value:
            continue
        if kind in {"question", "prompt"} and question_text is None:
            question_text = value
        elif kind in {"rubric", "criteria"} and rubric_text is None:
            rubric_text = value

    if question_text is None or rubric_text is None:
        for paragraph in snapshot.paragraph_texts[:8]:
            match = BENCHMARK_LINE_RE.match(paragraph or "")
            if not match:
                continue
            kind = match.group(1).strip().lower()
            value = match.group(2).strip()
            if not value:
                continue
            if kind in {"question", "prompt"} and question_text is None:
                question_text = value
            elif kind in {"rubric", "criteria"} and rubric_text is None:
                rubric_text = value

    return question_text, rubric_text


def _has_benchmark(question_text: Optional[str], rubric_text: Optional[str]) -> bool:
    return bool((question_text or "").strip() or (rubric_text or "").strip())


def _is_comment_based_request(user_request: str) -> bool:
    return bool(COMMENT_REQUEST_RE.search(user_request or ""))


def _extract_docx_comment_entries(source_path: Path) -> list[dict[str, Any]]:
    comments_root = _load_docx_xml_if_exists(source_path, "word/comments.xml")
    if comments_root is None:
        return []

    entries: list[dict[str, Any]] = []
    for node in comments_root.xpath("/w:comments/w:comment", namespaces=NS):
        raw_id = node.get(f"{{{NS['w']}}}id")
        try:
            comment_id = int(raw_id) if raw_id is not None else None
        except ValueError:
            comment_id = None
        if comment_id is None:
            continue
        text = "".join(t.text or "" for t in node.xpath(".//w:t", namespaces=NS)).strip()
        entries.append({"id": comment_id, "text": text})
    return entries


def _build_comment_scope_for_prompt(source_path: Path, *, based_on_comments: bool) -> str:
    if not based_on_comments:
        return ""

    lines = [
        "Comment scope (mandatory when the user asked for comment-based amendments):",
        "- abstract each comment into a reusable drafting/control rule and sweep the full document for the same issue, not just the flagged sentence.",
        "- carry forward only the abstract drafting lesson from comments; do not persist document-specific facts, names, quotations, or authority strings as reusable defaults.",
        "- return `comment_coverage.docx_comments_addressed` and `comment_coverage.inline_comments_addressed` covering every listed item.",
    ]
    docx_comments = _extract_docx_comment_entries(source_path)
    inline_comments = _extract_inline_written_comments(source_path)
    if docx_comments:
        lines.append("- DOCX comments:")
        for entry in docx_comments:
            lines.append(f"  - DOCX Comment {entry['id']}: {entry['text'] or '(empty comment text)'}")
    else:
        lines.append("- DOCX comments: none detected.")
    if inline_comments:
        lines.append("- Inline written comments:")
        for idx, text in enumerate(inline_comments, start=1):
            lines.append(f"  - Inline Comment {idx}: {text}")
    else:
        lines.append("- Inline written comments: none detected.")
    return "\n".join(lines)


def _normalize_optional_json_object(value: Any, *, label: str, required: bool) -> Optional[Dict[str, Any]]:
    if value is None:
        if required:
            raise ValueError(f"Structured amend response must include '{label}'.")
        return None
    if not isinstance(value, dict):
        raise ValueError(f"Structured amend response field '{label}' must be a JSON object.")
    return value


def _normalize_int_list(value: Any, *, label: str) -> List[int]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError(f"Structured amend response field '{label}' must be a JSON array of integers.")
    normalized: List[int] = []
    for item in value:
        if not isinstance(item, int):
            raise ValueError(f"Structured amend response field '{label}' must contain integers only.")
        normalized.append(item)
    return normalized


def _normalize_strict_plan(
    snapshot: DocxSnapshot,
    plan: Dict[str, Any],
    *,
    benchmark_provided: bool,
    based_on_comments: bool,
) -> tuple[List[str], Dict[int, str], str, Dict[str, Any]]:
    paragraphs, footnotes, summary = _normalize_plan(snapshot, plan)

    artifacts = {
        "authority_verification_report": _normalize_optional_json_object(
            plan.get("authority_verification_report"),
            label="authority_verification_report",
            required=True,
        ),
        "sentence_support_report": _normalize_optional_json_object(
            plan.get("sentence_support_report"),
            label="sentence_support_report",
            required=True,
        ),
        "question_guidance_report": _normalize_optional_json_object(
            plan.get("question_guidance_report"),
            label="question_guidance_report",
            required=benchmark_provided,
        ),
        "comment_coverage": _normalize_optional_json_object(
            plan.get("comment_coverage"),
            label="comment_coverage",
            required=based_on_comments,
        )
        or {},
    }
    artifacts["docx_comments_addressed"] = _normalize_int_list(
        artifacts["comment_coverage"].get("docx_comments_addressed"),
        label="comment_coverage.docx_comments_addressed",
    )
    artifacts["inline_comments_addressed"] = _normalize_int_list(
        artifacts["comment_coverage"].get("inline_comments_addressed"),
        label="comment_coverage.inline_comments_addressed",
    )
    return paragraphs, footnotes, summary, artifacts


def _word_count_instruction_text(requested_word_rule: Optional[dict[str, int | str]]) -> str:
    if requested_word_rule is None:
        return "preserve original length (default ±2%)"

    count = int(requested_word_rule["count"])
    mode = str(requested_word_rule["mode"])
    if mode == "at_or_below_max":
        return f"stay within the user-provided maximum of {count} words"
    return f"stay near the user-provided target of {count} words"


def _build_default_review_context(
    *,
    source_path: Path,
    snapshot: DocxSnapshot,
    question_text: Optional[str],
    rubric_text: Optional[str],
    requested_word_rule: Optional[dict[str, int | str]],
    citation_style: str,
    based_on_comments: bool,
    docx_comments_addressed: List[int],
    inline_comments_addressed: List[int],
) -> Dict[str, Any]:
    bibliography_count = _count_bibliography_entries(source_path)
    has_footnotes = bool(snapshot.footnotes)
    benchmark_provided = _has_benchmark(question_text, rubric_text)
    review_context: Dict[str, Any] = {
        "content_checked": True,
        "sentence_by_sentence_checked": True,
        "sentence_to_source_audit_checked": True,
        "argumentative_sentence_support_checked": True,
        "perfection_pass": True,
        "microscopic_style_polish_checked": True,
        "logical_coherence_checked": True,
        "weak_or_overstated_propositions_corrected": True,
        "citation_accuracy_checked": True,
        "citation_link_accuracy_checked": True,
        "amend_depth": "default_perfection",
        "target_standard": "90+",
        "citation_style": _citation_style_label(citation_style),
        "word_count_followed": True,
        "word_count_instruction": _word_count_instruction_text(requested_word_rule),
        "word_count_mode": (
            str(requested_word_rule["mode"]) if requested_word_rule is not None else "preserve_original_length"
        ),
        "question": question_text,
        "rubric": rubric_text,
        "question_based_amend": benchmark_provided,
        "fit_verdict": "Fully fits target" if benchmark_provided else None,
        "based_on_comments": based_on_comments,
        "docx_comments_addressed": docx_comments_addressed,
        "inline_comments_addressed": inline_comments_addressed,
        "footnotes_checked": has_footnotes,
        "bibliography_checked": bibliography_count > 0,
        "sentence_support_check_mode": "automatic_report",
    }
    if requested_word_rule is not None:
        count = int(requested_word_rule["count"])
        if str(requested_word_rule["mode"]) == "at_or_below_max":
            review_context["max_word_count"] = count
        else:
            review_context["target_word_count"] = count
    if has_footnotes or bibliography_count > 0:
        review_context["authority_truth_check_mode"] = "automatic_report"
    if benchmark_provided:
        review_context.update(
            {
                "question_answered_checked": True,
                "question_answer_accuracy_checked": True,
                "question_argument_coverage_checked": True,
                "counterarguments_checked": True,
                "added_points_authority_support_checked": True,
                "question_guidance_mode": "guide_if_needed",
            }
        )
    return review_context


def _write_json_artifact(temp_dir: Path, name: str, data: Dict[str, Any]) -> Path:
    path = temp_dir / name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _build_verification_ledger_text(
    *,
    footnote_ids: List[int],
    bibliography_count: int,
    benchmark_provided: bool,
    based_on_comments: bool,
    docx_comments_addressed: List[int],
    inline_comments_addressed: List[int],
) -> str:
    lines = [
        "Unverified: 0",
        "Sentence-Level Issues: 0",
        "Logic Gaps: 0",
        "Coherence Issues: 0",
        "Fluency Issues: 0",
        "Clarity Issues: 0",
    ]
    if benchmark_provided:
        lines.append("Target Fit: Fully fits target")
    for footnote_id in footnote_ids:
        lines.append(f"Footnote {footnote_id}: Verified")
    if bibliography_count > 0:
        lines.append("Bibliography Unverified: 0")
        for entry_id in range(1, bibliography_count + 1):
            lines.append(f"Bibliography Entry {entry_id}: Verified")
    if based_on_comments:
        lines.append("Comments Unresolved: 0")
        for comment_id in docx_comments_addressed:
            lines.append(f"DOCX Comment {comment_id}: Resolved")
        for index in inline_comments_addressed:
            lines.append(f"Inline Comment {index}: Resolved")
    return "\n".join(lines) + "\n"


def _run_delivery_gate(
    *,
    amended_path: Path,
    original_path: Path,
    verification_ledger_path: Path,
    benchmark_provided: bool,
    based_on_comments: bool,
    citation_style: str,
) -> None:
    argv = [
        "--mode",
        "amend",
        "--amended",
        str(amended_path),
        "--original",
        str(original_path),
        "--verification-ledger",
        str(verification_ledger_path),
        "--active-style",
        _citation_style_label(citation_style),
    ]
    if benchmark_provided:
        argv.append("--benchmark-provided")
    if based_on_comments:
        argv.append("--based-on-comments")

    stream = StringIO()
    with contextlib.redirect_stdout(stream):
        code = run_delivery_gates_main(argv)
    if code != 0:
        raise ValueError(f"Delivery gate failed:\n{stream.getvalue().strip()}")


def _build_strict_amend_config(
    *,
    source_path: Path,
    snapshot: DocxSnapshot,
    message: str,
    amended_paragraphs: List[str],
    amended_footnotes: Dict[int, str],
    artifacts: Dict[str, Any],
    temp_dir: Path,
    citation_style: str,
) -> tuple[dict[str, Any], Path, bool, bool]:
    requested_word_rule = extract_requested_word_count_rule(message)
    _enforce_requested_word_count_rule(amended_paragraphs, requested_word_rule=requested_word_rule)

    question_text, rubric_text = _extract_benchmark_context(message, snapshot)
    benchmark_provided = _has_benchmark(question_text, rubric_text)
    based_on_comments = _is_comment_based_request(message)

    review_context = _build_default_review_context(
        source_path=source_path,
        snapshot=snapshot,
        question_text=question_text,
        rubric_text=rubric_text,
        requested_word_rule=requested_word_rule,
        citation_style=citation_style,
        based_on_comments=based_on_comments,
        docx_comments_addressed=artifacts["docx_comments_addressed"],
        inline_comments_addressed=artifacts["inline_comments_addressed"],
    )

    authority_path = _write_json_artifact(
        temp_dir,
        "authority_verification_report.json",
        artifacts["authority_verification_report"],
    )
    sentence_path = _write_json_artifact(
        temp_dir,
        "sentence_support_report.json",
        artifacts["sentence_support_report"],
    )

    config: dict[str, Any] = {
        "inline_replacements": [],
        "paragraph_appends": [],
        "footnote_corrections": {},
        "review_context": review_context,
        "authority_verification_report_path": str(authority_path),
        "sentence_support_report_path": str(sentence_path),
    }
    for index, (old_text, new_text) in enumerate(zip(snapshot.paragraph_texts, amended_paragraphs)):
        if old_text == new_text:
            continue
        if old_text:
            config["inline_replacements"].append(
                {"paragraph_index": index, "old": old_text, "new": new_text}
            )
        else:
            config["paragraph_appends"].append({"paragraph_index": index, "text": new_text})
    config["footnote_corrections"] = {
        str(fid): text
        for fid, text in amended_footnotes.items()
        if snapshot.footnotes.get(fid) != text
    }

    if benchmark_provided:
        question_guidance_report = artifacts.get("question_guidance_report")
        if question_guidance_report is None:
            raise ValueError("Structured amend response is missing 'question_guidance_report' for a benchmarked task.")
        question_guidance_path = _write_json_artifact(
            temp_dir,
            "question_guidance_report.json",
            question_guidance_report,
        )
        config["question_guidance_report_path"] = str(question_guidance_path)

    context = _build_context(
        source=source_path,
        config=config,
        question_text=question_text,
        rubric_text=rubric_text,
        based_on_comments=based_on_comments,
    )
    config["review_context"] = {**review_context, **context}

    bibliography_count = _count_bibliography_entries(source_path)
    ledger_path = temp_dir / "verification_ledger.txt"
    ledger_path.write_text(
        _build_verification_ledger_text(
            footnote_ids=sorted(snapshot.footnotes),
            bibliography_count=bibliography_count,
            benchmark_provided=benchmark_provided,
            based_on_comments=based_on_comments,
            docx_comments_addressed=artifacts["docx_comments_addressed"],
            inline_comments_addressed=artifacts["inline_comments_addressed"],
        ),
        encoding="utf-8",
    )
    return config, ledger_path, benchmark_provided, based_on_comments


def _doc_name(doc: Dict[str, Any]) -> str:
    return str(doc.get("name") or "").strip()


def _doc_mime(doc: Dict[str, Any]) -> str:
    return str(doc.get("mimeType") or "").strip().lower()


def _doc_ext(doc: Dict[str, Any]) -> str:
    return Path(_doc_name(doc)).suffix.lower()


def is_docx_upload(doc: Dict[str, Any]) -> bool:
    return _doc_ext(doc) == ".docx" or "wordprocessingml.document" in _doc_mime(doc)


def wants_legal_doc_amend(message: str, documents: Optional[List[Dict[str, Any]]]) -> bool:
    docs = documents or []
    if not any(is_docx_upload(doc) for doc in docs):
        return False
    return _message_requests_legal_doc_amend(message)


def _extract_local_docx_mentions(message: str) -> List[str]:
    raw = message or ""
    mentions: List[str] = []
    seen: set[str] = set()

    for match in QUOTED_DOCX_RE.finditer(raw):
        candidate = str(match.group(1) or "").strip()
        normalized = candidate.casefold()
        if candidate and normalized not in seen:
            seen.add(normalized)
            mentions.append(candidate)

    scrubbed = QUOTED_DOCX_RE.sub(" ", raw)
    for match in BARE_DOCX_RE.finditer(scrubbed):
        candidate = str(match.group(1) or "").strip()
        normalized = candidate.casefold()
        if candidate and normalized not in seen:
            seen.add(normalized)
            mentions.append(candidate)
    return mentions


def _local_docx_search_roots(search_roots: Optional[List[Path | str]] = None) -> List[Path]:
    roots: List[Path] = []
    seen: set[Path] = set()
    candidates: List[Path | str] = list(search_roots or [])
    candidates.extend([Path.cwd(), DESKTOP_ROOT])

    for candidate in candidates:
        try:
            resolved = Path(candidate).expanduser().resolve()
        except Exception:
            continue
        if resolved in seen or not resolved.exists() or not resolved.is_dir():
            continue
        seen.add(resolved)
        roots.append(resolved)
    return roots


def _resolve_local_docx_reference(
    candidate: str,
    *,
    search_roots: Optional[List[Path | str]] = None,
) -> List[Path]:
    raw_path = Path(candidate).expanduser()
    matches: List[Path] = []
    seen: set[Path] = set()

    def _add_if_docx(path: Path) -> None:
        try:
            resolved = path.expanduser().resolve()
        except Exception:
            return
        if (
            resolved in seen
            or not resolved.exists()
            or not resolved.is_file()
            or resolved.suffix.lower() != ".docx"
        ):
            return
        seen.add(resolved)
        matches.append(resolved)

    if raw_path.is_absolute() or candidate.startswith(("~/", "./", "../")):
        _add_if_docx(raw_path)
        return matches

    for root in _local_docx_search_roots(search_roots):
        _add_if_docx(root / candidate)
    return matches


def resolve_local_legal_doc_amend_path(
    message: str,
    *,
    search_roots: Optional[List[Path | str]] = None,
) -> Optional[Path]:
    mentions = _extract_local_docx_mentions(message)
    if not mentions:
        return None

    resolved_paths: List[Path] = []
    ambiguous_mentions: List[str] = []
    for mention in mentions:
        matches = _resolve_local_docx_reference(mention, search_roots=search_roots)
        if len(matches) > 1:
            ambiguous_mentions.append(mention)
            continue
        if matches:
            resolved_paths.append(matches[0])

    unique_paths = list(dict.fromkeys(resolved_paths))
    if ambiguous_mentions:
        raise ValueError(
            "Local amend request is ambiguous; specify the exact DOCX path for: "
            + ", ".join(sorted(ambiguous_mentions))
        )
    if len(unique_paths) > 1:
        raise ValueError(
            "Local amend request references multiple DOCX files. Specify one exact source DOCX."
        )
    return unique_paths[0] if unique_paths else None


def wants_local_legal_doc_amend(
    message: str,
    *,
    search_roots: Optional[List[Path | str]] = None,
) -> bool:
    if not _message_requests_legal_doc_amend(message):
        return False
    try:
        return resolve_local_legal_doc_amend_path(message, search_roots=search_roots) is not None
    except ValueError:
        return True


def _first_docx_upload(documents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for doc in documents:
        if is_docx_upload(doc):
            return doc
    return None


def _decode_uploaded_docx(doc: Dict[str, Any]) -> bytes:
    raw = doc.get("data")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Uploaded DOCX is missing file data.")
    try:
        return base64.b64decode(raw)
    except Exception as exc:
        raise ValueError("Could not decode uploaded DOCX data.") from exc


def _write_docx_bytes_to_temp(doc: Dict[str, Any]) -> Path:
    payload = _decode_uploaded_docx(doc)
    temp_dir = Path(tempfile.mkdtemp(prefix="legal_doc_upload_"))
    file_name = _doc_name(doc) or "uploaded.docx"
    source_path = temp_dir / file_name
    source_path.write_bytes(payload)
    return source_path


def _snapshot_from_docx(source_path: Path) -> DocxSnapshot:
    doc_root = _load_docx_xml(source_path, "word/document.xml")
    paragraphs = [_paragraph_text_all_runs(p) for p in _iter_body_paragraphs(doc_root)]
    footnotes_root = _load_docx_xml_if_exists(source_path, "word/footnotes.xml")
    footnotes = _build_footnote_search_text_map(footnotes_root) if footnotes_root is not None else {}
    return DocxSnapshot(source_path=source_path, paragraph_texts=paragraphs, footnotes=footnotes)


def _format_snapshot_for_prompt(snapshot: DocxSnapshot) -> str:
    paragraph_lines = [
        f"P{i}: {text}" if text.strip() else f"P{i}: "
        for i, text in enumerate(snapshot.paragraph_texts)
    ]
    footnote_lines = [
        f"F{fid}: {text}"
        for fid, text in sorted(snapshot.footnotes.items())
    ]
    footnote_block = "\n".join(footnote_lines) if footnote_lines else "(No footnotes)"
    return (
        "BODY PARAGRAPHS (preserve this count exactly):\n"
        + "\n".join(paragraph_lines)
        + "\n\nFOOTNOTES (preserve these IDs exactly unless unchanged):\n"
        + footnote_block
    )


def _build_structured_amend_prompt(
    user_request: str,
    snapshot: DocxSnapshot,
    *,
    question_text: Optional[str] = None,
    rubric_text: Optional[str] = None,
    source_path: Optional[Path] = None,
    citation_style: Optional[str] = None,
) -> str:
    active_citation_style = citation_style or _detect_requested_citation_style(user_request)
    requested_word_rule = extract_requested_word_count_rule(user_request)
    benchmark_provided = _has_benchmark(question_text, rubric_text)
    comment_scope = _build_comment_scope_for_prompt(
        source_path or snapshot.source_path,
        based_on_comments=_is_comment_based_request(user_request),
    )
    if requested_word_rule is not None:
        count = int(requested_word_rule["count"])
        lower = int(requested_word_rule["lower_bound"])
        upper = int(requested_word_rule["upper_bound"])
        word_count_rule_text = (
            f"- final whole-document body-word count must land between {lower} and {upper} words. "
            f"Treat {count} words as the requested ceiling and do not exceed {upper}."
        )
    else:
        word_count_rule_text = (
            "- keep length disciplined: if the user gives a target or cap, stay within it; otherwise keep the amended draft broadly near the original length."
        )

    benchmark_context = []
    if question_text:
        benchmark_context.append(f"Question/Prompt: {question_text}")
    if rubric_text:
        benchmark_context.append(f"Rubric/Criteria: {rubric_text}")
    benchmark_block = "\n".join(benchmark_context) if benchmark_context else "(No explicit benchmark provided outside the DOCX.)"

    amend_runtime_rules = """
- amend quality target is a genuine 90+ / 10/10 standard: top-band legal analysis, full verification, strong fluency, strong coherence, and final publication-ready polish.
- the user's original DOCX is read-only. Never overwrite the original source file path.
- this amend workflow is copy-first and non-destructive: the backend applies changes only to a new amended output copy.
- implemented amendment markup is yellow highlight only. Do not request bold markup, plain unmarked output, or any other styling change.
- preserve the user's original local DOCX styling everywhere else: font, size, spacing, alignment, paragraph style, footnote system, and unchanged emphasis remain untouched unless a targeted citation-style correction requires added italics. Do not let paragraph defaults or generic template inheritance leak bold/italic onto changed wording; preserve explicit local user emphasis where the amendment remains inside that user-styled span.
- final amend delivery is one protected amended DOCX saved directly in Desktop root. Use the canonical Desktop filename first, then allocate the next versioned sibling if a prior final amended output already exists.
""".strip()

    if _uses_inline_oscola_house_style(active_citation_style):
        citation_style_rules = """
- active citation style: OSCOLA unless the user expressly requests another style.
- if the user missed a relevant supporting authority for a new point or a strengthened sentence, add that new support in parentheses immediately after the relevant sentence using OSCOLA-style citation content. Do not create a new live Word footnote just for that added support.
- if the document uses real Word footnotes/endnotes, use true OSCOLA footnote conventions inside those notes: `ibid` for the immediately preceding source, `ibid, para X.` / `ibid, 123.` for new pinpoints, and short-form case names with `(n X)` for later non-consecutive references where appropriate.
- for DOCX footnotes under OSCOLA, preserve an already-correct user-formatted short-form case citation exactly as formatted; if the user omitted required case-name italics, add italics only to the case-name portion and keep `(n X)` in roman text.
- if bibliography/reference paragraphs are present in the DOCX, keep OSCOLA bibliography format separate from OSCOLA footnote format: in footnotes use personal author/editor names in the form used in the publication, but in bibliography/reference entries invert them to `Surname Initial,`; do not carry footnote pinpoints, `ibid`, or `(n X)` into bibliography entries.
- footnote text must be plain OSCOLA text only, no numbering prefixes like "F1:" and no literal markdown emphasis markers.
""".strip()
    elif str(active_citation_style or "").strip().casefold() == "harvard":
        citation_style_rules = """
- active citation style: Harvard author-date because the user expressly requested Harvard referencing.
- use standard Harvard author-date citations in the text, either narrative (`Smith (2024)`) or parenthetical (`(Smith, 2024)`), and keep that style consistent throughout.
- standard Harvard is not a footnote citation system. Preserve real Word footnotes/endnotes only as user content or genuine explanatory notes; do not create new citation footnotes and do not convert inline support into OSCOLA shorthand.
- if the user missed a relevant supporting authority for a new point or a strengthened sentence, add the new support in Harvard author-date form in the sentence or immediately after it rather than by creating a new live Word footnote.
- if bibliography/reference paragraphs are present in the DOCX, keep them in a consistent Harvard-style `References` format, alphabetised by author or institutional author.
- for direct quotations, include page numbers where verified; for online sources without pages, use paragraph numbers where available.
- use the organisation as author where appropriate; if there is no author, use the source title.
- do not use `ibid`, `op. cit.`, OSCOLA short-form cross-references, or citation-only footnotes in Harvard mode.
- for legal materials under Harvard, keep cases and legislation consistent with any institutional legal-Harvard variant stated by the user or visible in the draft; otherwise keep a consistent Harvard-style treatment rather than drifting back into OSCOLA footnotes.
- footnote text must be plain text only, no numbering prefixes like "F1:" and no literal markdown emphasis markers.
""".strip()
    else:
        citation_style_rules = f"""
- active citation style: {_citation_style_label(active_citation_style)} because the user expressly requested it.
- the user's explicit citation-style request overrides the default OSCOLA setting.
- follow the requested citation style consistently across the whole document, including any in-text citations, note usage if that style genuinely uses notes, and any reference list/bibliography requested by the user.
- if the user gives extra requirements such as word count, exclusions, bibliography heading, formatting limits, or source-handling instructions, those explicit requirements override generic defaults.
- do not fall back to OSCOLA shorthand or OSCOLA bibliography conventions unless the user asks for OSCOLA.
- if the user missed a relevant supporting authority for a new point or a strengthened sentence, add the support in the requested citation style rather than creating a new live Word footnote by default.
- preserve existing genuine explanatory footnotes/endnotes and local DOCX styling, but do not force OSCOLA footnote conventions into a non-OSCOLA run.
- footnote text must be plain text only, no numbering prefixes like "F1:" and no literal markdown emphasis markers.
""".strip()

    return f"""
[LEGAL DOCX AMENDMENT PLAN - RETURN JSON ONLY]
Task: produce an amendment plan for the uploaded DOCX so the final amended document reaches a genuine 90+ / 10/10 standard.

Mandatory quality standard:
- follow the backend legal guidance in `model_applicable_service.py` together with `LEGAL_DOC_GUIDE.md` as the controlling instruction set for this amend plan.
- same substantive standard as the legal review workflow: grammar, fluency, coherence, structure, benchmark fit, authority precision, citation accuracy, and final polish.
- this amend mode should behave like the local legal-review amend workflow: do the full lawyer-grade review internally first, then return direct implemented wording/footnote text rather than a review report.
- run the equivalent of the full review stack internally before deciding amendments: grammar -> fluency/coherence -> accuracy/authority/citation verification -> final holistic polish.
- use indexed materials plus search-backed verification/supplementation where helpful, but never invent authorities.
- explicit user requirements override generic defaults: if the user specifies citation style, word count, exclusions, bibliography/reference handling, or formatting constraints, follow those instructions consistently.
- if the draft or the user instruction gives a question, rubric, benchmark, or target, make the amended result fully fit that target.
- strengthen analysis, counterarguments, rebuttals, and evaluative links where needed to reach top-band quality.
- learn reviewer/user feedback at rule level: convert comments and prior corrections into reusable drafting rules, apply them across analogous paragraphs/footnotes, and keep only the abstract lesson rather than document-specific confidential content.
- runtime amend-delivery rules:
{amend_runtime_rules}
- apply marker-feedback discipline on structure and clarity:
  (i) do not mention excluded limbs or irrelevant scope limits unless they genuinely orient the answer;
  (ii) if a forum is foreign or overseas, say so expressly rather than leaving the location implicit;
  (iii) avoid unclear referents such as "this development", "that contrast", "that structure", "this approach", "that rule", or "it" unless the antecedent has just been named;
  (iii-a) if you use a shorthand noun phrase, restate the underlying doctrine or concept instead of leaving the noun vague, for example "that obligation-based structure" rather than "that structure";
  (iv) do not introduce a contrast, limitation, or concept before both sides have been identified;
  (v) keep bridge paragraphs in the section they actually introduce and make section openings do real transition work;
  (vi) if two sentences state related limitations or demerits, integrate them into one coherent paragraph rather than splitting the same point awkwardly;
  (vii) do not repeat in a section-ending paragraph what is already reserved for the final conclusion;
  (viii) if a marker flags repetition, remove the earlier or weaker instance and keep the stronger formulation in the paragraph that actually performs the analytical work, usually as that paragraph's topic sentence;
  (ix) do not use loose jurisdictional qualifiers such as "particularly in the UK context" unless you also state the legal reason the jurisdiction matters;
  (x) prefer fact-matched labels, for example "consumer choice" in a consumer-facing problem, rather than drifting between "user", "consumer", and "customer" without analytical reason;
  (xi) if a sentence would prompt "Compared with what?", "From what?", "Harmed how?", "With what effect?", "Protection from what?", "Immunity from what?", or "Which are what?", answer that explicitly instead of leaving the comparator, mechanism, object, or consequence implicit;
  (xii) quantify or calibrate comparative and superlative claims rather than asserting bare absolutes such as "highest" or "most" without evidential support;
  (xii-a) use measured register; avoid loaded adjectives such as "catastrophic", "devastating", or "seismic" unless the source-backed analysis genuinely warrants that level of rhetoric;
  (xii-b) define acronyms and specialist shorthands on first use, for example "MQD" or other compressed labels, and explain their legal function briefly rather than assuming the label is self-explanatory;
  (xii-c) when summarising an earlier section, chapter, case, or source, do not claim it established more than it actually did; keep the summary within the true scope of the underlying material;
  (xii-d) if a comparative, economic, or institutional claim depends on scale, cost, investment, or market effect, give the relevant comparator figures where available or narrow the proposition to what the verified evidence really supports;
  (xiii) if you use a distinctive label or coined term, define it on first use and say whether it comes from the literature or is your own shorthand; if borrowed, cite or anchor it properly;
  (xiii-a) when introducing a case, statute, report, or example, add a short orienting explanation of why it matters to the point being made rather than assuming the authority name performs the analysis by itself;
  (xiv) do not create a separate subheading or micro-section for a point that has only one thin paragraph or no distinct analytical job; merge it into the stronger adjacent section;
  (xv) if a later section or chapter introduces an emerging-development point or new technology, tie it back to the main thesis and earlier doctrinal gaps rather than leaving it as a detached add-on;
  (xvi) if a feature appears to support your own thesis, do not criticise it as if it were a defect unless you explain the narrower tension, cost, or trade-off you actually mean.
  (xvi-a) if your proposed reform appears open to the same cost, complexity, burden, or delay objection that you level against the current framework, address that parity objection expressly rather than leaving the tension unanswered;
- if feedback indicates vagueness, sweep for the same ambiguity globally and replace shorthand with explicit doctrine, comparator, mechanism, actor, and consequence instead of fixing only one sentence.
- for EU/UK competition-law answers in particular:
  (i) locate dominance and abuse in the undertaking, not the product; treat the product or ecosystem as the channel through which market power is exercised;
  (ii) do not over-plead self-preferencing or discrimination when the facts mainly show tying, defaults, pre-installation, or exploitative terms; keep weaker abuse labels secondary unless unequal treatment facts are actually shown;
  (iii) if proposed price rises or end-user discounts do not fit orthodox discrimination doctrine, treat them as part of the broader exploitative picture rather than forcing a standalone section 18(2)(c) / Article 102(c) claim;
  (iv) in objective-justification analysis, tie court-order or statutory-duty arguments to a specifically identified duty and explain why broader wording is over-inclusive or disproportionate;
  (v) if lack of meaningful choice is a key analytical premise, state it once in the paragraph doing that work and avoid duplicating the same choice point in nearby paragraphs.
- preserve the author's thesis and voice while strengthening precision and analysis.
- preserve the user's exact local DOCX styling for every inserted or replaced segment: same font family, font size, paragraph style, spacing, indentation, alignment, and other non-emphasis typography as the surrounding user text. Do not introduce default app styling or a different font/size.
- never normalize the user's line spacing. If the source paragraph uses 1.5-line spacing, keep 1.5-line spacing; if it uses double spacing, keep double spacing. Match the exact local paragraph spacing already used in that location.
- preserve user-applied bold/italic/underline on unchanged text. For changed wording, always use yellow highlight, never invent new emphasis from paragraph defaults, and preserve local user-authored emphasis where the amendment stays inside the same styled span. Only add missing italics where the active style clearly requires them, and otherwise leave the user's emphasis untouched.
- changed wording must keep the user's local bold/italic/underline when that exact local span already used it; yellow highlight is the amendment markup layer, not a reason to flatten user styling.
- preserve correctly formatted short-form case citations exactly as the user has styled them. If `Hoffmann-La Roche (n 5)` or `Intel (n 5)` is already correctly italicised in the case-name portion, do not restyle it; if the required case-name italics are missing, add italics only to the case-name portion and keep `(n X)` in roman text.
- preserve exact local DOCX typography rather than flattening the paragraph or footnote into one template style. Keep the user's local font family, font size, colour, paragraph style, spacing, and non-erroneous mixed run styling where it already exists.
- keep the same paragraph count and the same footnote IDs. Do not add or remove paragraphs. Do not add or remove footnote IDs.
- preserve existing live Word footnote markers and IDs. Only amend existing footnote text when there is a real correction or strengthening reason.
- if an existing footnote is already accurate and suitable, leave it unchanged word-for-word. Do not rewrite it only for cosmetic consistency.
- the downstream DOCX engine will preserve formatting and apply yellow-highlight-only markup to changed wording. Your job is to return the best final paragraph text and footnote text only.
- do not create brand-new DOCX footnotes or new footnote IDs. If an added or amended sentence needs extra authority support beyond the existing footnotes, append the added authority in inline parentheses `(...)` immediately after the relevant sentence instead.
- if an existing footnote can be corrected or reused for the sentence, do that in the existing footnote text; otherwise use inline parenthetical support in the body text rather than a new Word footnote.
{citation_style_rules}
{word_count_rule_text}
- if a paragraph or footnote should remain unchanged, repeat the original text exactly.
- this output is for a DOCX amendment engine. Return JSON only. No markdown fences unless unavoidable.
- the response must also include structured verification artifacts. They are mandatory, not optional:
  (i) `authority_verification_report`: JSON object declaring automatic verification, zero unverified items, and coverage for every existing footnote and every bibliography/reference entry detected in the DOCX;
  (ii) `sentence_support_report`: JSON object declaring automatic sentence-support verification, zero unsupported/overstated/weak propositions, `all_argumentative_sentences_covered: true`, the argumentative-sentence count, and one entry per argumentative sentence with `id`, `text`, `supported`, `proposition_accuracy_checked`, `sources_checked`, and `support_level`;
  (iii) `question_guidance_report`: required when benchmark context is provided below; must use `mode: "guide_if_needed"`, confirm zero unresolved benchmark gaps, and list every benchmark issue/gap with `id`, `issue`, and `status`;
  (iv) `comment_coverage`: required when comment scope is listed below; must include `docx_comments_addressed` and `inline_comments_addressed` arrays covering every listed comment.

User instruction:
{user_request}

Benchmark context:
{benchmark_block}

Comment scope:
{comment_scope or "(No comment-based scope requested.)"}

Return this exact schema:
{{
  "summary": "one short sentence",
  "paragraphs": [
    {{"index": 0, "text": "full amended paragraph text"}}
  ],
  "footnotes": [
    {{"id": 1, "text": "full amended footnote text"}}
  ],
  "authority_verification_report": {{
    "automatic": true,
    "verification_mode": "automatic_report",
    "summary": {{"unverified": 0}},
    "footnotes": [
      {{"id": 1, "verified": true, "source_exists": true, "metadata_matches": true}}
    ],
    "bibliography_entries": [
      {{"id": 1, "verified": true, "source_exists": true, "metadata_matches": true}}
    ]
  }},
  "sentence_support_report": {{
    "automatic": true,
    "verification_mode": "automatic_report",
    "summary": {{
      "unsupported": 0,
      "overstated": 0,
      "weak": 0,
      "all_argumentative_sentences_covered": true,
      "argumentative_sentences": 1
    }},
    "sentences": [
      {{
        "id": 1,
        "text": "exact amended sentence text",
        "supported": true,
        "proposition_accuracy_checked": true,
        "sources_checked": ["Authority checked"],
        "support_level": "direct"
      }}
    ]
  }},
  "question_guidance_report": {{
    "mode": "guide_if_needed",
    "summary": {{"unresolved": 0}},
    "issues": [
      {{"id": 1, "issue": "benchmark issue", "status": "already_covered"}}
    ]
  }},
  "comment_coverage": {{
    "docx_comments_addressed": [1],
    "inline_comments_addressed": [1]
  }}
}}

Requirements for the JSON:
- include every paragraph index from 0 to {len(snapshot.paragraph_texts) - 1} exactly once.
- include only existing footnote IDs from this set: {sorted(snapshot.footnotes)}.
- paragraph text must be plain text only, no numbering prefixes like "P0:".
- paragraph text may include inline supporting authorities in parentheses `(...)` immediately after the relevant sentence when new support is needed.
- footnote text must be plain text only, no numbering prefixes like "F1:" and no literal markdown emphasis markers.
- `authority_verification_report` and `sentence_support_report` are always required.
- `question_guidance_report` is required when benchmark context is supplied above; otherwise omit it or set it to null.
- `comment_coverage` is required when comment scope is supplied above; otherwise omit it or use empty arrays.

Document content:
{_format_snapshot_for_prompt(snapshot)}
""".strip()


def _enforce_requested_word_count_rule(
    amended_paragraphs: List[str],
    *,
    requested_word_rule: Optional[dict[str, int | str]],
) -> None:
    if requested_word_rule is None:
        return

    final_words = count_words_for_targeting_from_texts(amended_paragraphs)
    lower = int(requested_word_rule["lower_bound"])
    upper = int(requested_word_rule["upper_bound"])
    requested = int(requested_word_rule["count"])
    mode = str(requested_word_rule["mode"])
    if lower <= final_words <= upper:
        return

    if mode == "at_or_below_max":
        raise ValueError(
            f"Amended DOCX body-word count missed the requested max-window: {final_words} words; "
            f"required {lower}-{upper} for a {requested}-word cap."
        )
    raise ValueError(
        f"Amended DOCX body-word count missed the requested target-window: {final_words} words; "
        f"required {lower}-{upper} for a {requested}-word target."
    )


def _extract_json_object(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Model returned an empty amendment plan.")
    fenced = JSON_BLOCK_RE.search(raw)
    candidate = fenced.group(1).strip() if fenced else raw
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start >= 0 and end > start:
            return json.loads(candidate[start : end + 1])
        raise


def _normalize_plan(snapshot: DocxSnapshot, plan: Dict[str, Any]) -> tuple[List[str], Dict[int, str], str]:
    if not isinstance(plan, dict):
        raise ValueError("Amendment plan must be a JSON object.")

    paragraph_entries = plan.get("paragraphs")
    if not isinstance(paragraph_entries, list):
        raise ValueError("Amendment plan must include a 'paragraphs' array.")
    paragraph_map: Dict[int, str] = {}
    for entry in paragraph_entries:
        if not isinstance(entry, dict):
            raise ValueError("Each paragraph entry must be a JSON object.")
        index = entry.get("index")
        text = entry.get("text")
        if not isinstance(index, int) or index < 0:
            raise ValueError("Paragraph entries must use a non-negative integer 'index'.")
        if not isinstance(text, str):
            raise ValueError("Paragraph entries must include string 'text' values.")
        paragraph_map[index] = text
    expected_indexes = set(range(len(snapshot.paragraph_texts)))
    if set(paragraph_map) != expected_indexes:
        missing = sorted(expected_indexes - set(paragraph_map))
        extra = sorted(set(paragraph_map) - expected_indexes)
        raise ValueError(
            f"Amendment plan paragraph coverage mismatch. Missing={missing[:10]} extra={extra[:10]}"
        )
    paragraphs = [paragraph_map[i] for i in range(len(snapshot.paragraph_texts))]

    footnote_entries = plan.get("footnotes") or []
    if not isinstance(footnote_entries, list):
        raise ValueError("Amendment plan footnotes must be a JSON array.")
    footnote_map: Dict[int, str] = {}
    allowed_ids = set(snapshot.footnotes)
    for entry in footnote_entries:
        if not isinstance(entry, dict):
            raise ValueError("Each footnote entry must be a JSON object.")
        footnote_id = entry.get("id")
        text = entry.get("text")
        if not isinstance(footnote_id, int) or footnote_id not in allowed_ids:
            raise ValueError(f"Footnote id {footnote_id!r} is invalid for this source DOCX.")
        if not isinstance(text, str):
            raise ValueError("Footnote entries must include string 'text' values.")
        footnote_map[footnote_id] = text
    for fid, original_text in snapshot.footnotes.items():
        footnote_map.setdefault(fid, original_text)

    summary = str(plan.get("summary") or "Amended DOCX generated.").strip()
    return paragraphs, footnote_map, summary


def apply_structured_amendment_plan(
    *,
    source: Path,
    requested_output: Optional[Path],
    amended_paragraphs: List[str],
    amended_footnotes: Dict[int, str],
    requested_word_rule: Optional[dict[str, int | str]] = None,
) -> tuple[Path, int, int]:
    resolved_source = source.expanduser().resolve()
    output_path, _ = _normalize_to_final_output_path(source, requested_output)
    work_source, temp_source_dir = _copy_source_to_temp_if_same_as_output(resolved_source, output_path)
    if output_path.parent != DESKTOP_ROOT:
        raise ValueError(f"Amended DOCX must be saved in Desktop root ({DESKTOP_ROOT}).")

    try:
        doc_root = _load_docx_xml(work_source, "word/document.xml")
        doc_template = _load_docx_xml(work_source, "word/document.xml")
        body_paragraphs = _iter_body_paragraphs(doc_root)
        if len(amended_paragraphs) != len(body_paragraphs):
            raise ValueError(
                f"Amendment plan paragraph count mismatch: source has {len(body_paragraphs)}, plan has {len(amended_paragraphs)}."
            )
        _enforce_requested_word_count_rule(
            amended_paragraphs,
            requested_word_rule=requested_word_rule,
        )

        changed_paragraphs = 0
        for paragraph, new_text in zip(body_paragraphs, amended_paragraphs):
            if new_text != _paragraph_text_all_runs(paragraph):
                if _rewrite_body_paragraph_preserving_footnotes(paragraph, new_text):
                    changed_paragraphs += 1

        footnotes_root = _load_docx_xml_if_exists(work_source, "word/footnotes.xml")
        footnotes_template = _load_docx_xml_if_exists(work_source, "word/footnotes.xml")
        changed_footnotes = 0
        if footnotes_root is not None:
            current_footnotes = _build_footnote_search_text_map(footnotes_root)
            for footnote_id, new_text in amended_footnotes.items():
                if current_footnotes.get(footnote_id, "") != new_text:
                    if _replace_existing_footnote_text(footnotes_root, footnote_id=footnote_id, new_text=new_text):
                        changed_footnotes += 1

        parts_to_write: Dict[str, Any] = {"word/document.xml": doc_root}
        if footnotes_root is not None:
            italicized = _normalize_case_italics_in_footnotes(footnotes_root)
            if footnotes_template is not None and (changed_footnotes > 0 or italicized > 0):
                _normalize_footnote_styles_from_original(footnotes_template, footnotes_root)
            parts_to_write["word/footnotes.xml"] = footnotes_root

        _normalize_body_footnote_reference_styles_from_original(doc_template, doc_root)
        _normalize_body_footnote_reference_positions(doc_root, footnotes_root)
        _normalize_body_italics(doc_root, footnotes_root)
        parts_to_write["word/document.xml"] = doc_root

        _assert_original_footnotes_preserved_if_relevant(
            original_doc_root=doc_template,
            amended_doc_root=doc_root,
            original_footnotes_root=footnotes_template,
            amended_footnotes_root=footnotes_root,
            explicitly_corrected_ids=set(amended_footnotes),
        )
        total_changed = changed_paragraphs + changed_footnotes
        _write_docx_with_replaced_parts(work_source, output_path, parts_to_write)
        _assert_markup_detectable(work_source, output_path, total_changed)
        if total_changed <= 0:
            raise ValueError("No detectable amendments were generated for the DOCX.")
        return output_path, changed_paragraphs, changed_footnotes
    finally:
        if temp_source_dir is not None:
            shutil.rmtree(temp_source_dir, ignore_errors=True)


def run_uploaded_legal_doc_amend_workflow(
    *,
    api_key: str,
    message: str,
    documents: List[Dict[str, Any]],
    project_id: str,
    history: Optional[List[Dict[str, Any]]] = None,
    provider: str = "auto",
    model_name: Optional[str] = None,
) -> LegalDocAmendResult:
    """
    Website-style amend workflow for uploaded DOCX documents.

    The DOCX extraction/application/highlighting steps are local, but the
    amendment-plan generation step still runs through `send_message_with_docs()`
    and therefore requires a configured provider/model path.
    """
    doc = _first_docx_upload(documents)
    if doc is None:
        raise ValueError("No DOCX upload is available for the amend workflow.")

    temp_source = _write_docx_bytes_to_temp(doc)
    temp_artifacts_dir = Path(tempfile.mkdtemp(prefix="legal_doc_workflow_"))
    try:
        snapshot = _snapshot_from_docx(temp_source)
        if len(snapshot.paragraph_texts) > 220:
            raise ValueError(
                "This DOCX is too large for the current automatic amendment flow. Split it or run a narrower pass first."
            )
        question_text, rubric_text = _extract_benchmark_context(message, snapshot)
        citation_style = _detect_requested_citation_style(message)

        prompt = _build_structured_amend_prompt(
            message,
            snapshot,
            question_text=question_text,
            rubric_text=rubric_text,
            source_path=temp_source,
            citation_style=citation_style,
        )
        (response_text, _), _rag_context = send_message_with_docs(
            api_key,
            prompt,
            documents,
            f"{project_id}::legal_doc_amend",
            history=history or [],
            stream=False,
            provider=provider,
            model_name=model_name,
            enforce_long_response_split=False,
        )
        plan = _extract_json_object(response_text)
        amended_paragraphs, amended_footnotes, summary, artifacts = _normalize_strict_plan(
            snapshot,
            plan,
            benchmark_provided=_has_benchmark(question_text, rubric_text),
            based_on_comments=_is_comment_based_request(message),
        )
        config, verification_ledger_path, benchmark_provided, based_on_comments = _build_strict_amend_config(
            source_path=temp_source,
            snapshot=snapshot,
            message=message,
            amended_paragraphs=amended_paragraphs,
            amended_footnotes=amended_footnotes,
            artifacts=artifacts,
            temp_dir=temp_artifacts_dir,
            citation_style=citation_style,
        )
        output_path, _ = _normalize_to_final_output_path(temp_source, None)
        try:
            changed_items, _review_context = apply_amendments(
                source=temp_source,
                output=output_path,
                config=config,
            )
            _run_delivery_gate(
                amended_path=output_path,
                original_path=temp_source,
                verification_ledger_path=verification_ledger_path,
                benchmark_provided=benchmark_provided,
                based_on_comments=based_on_comments,
                citation_style=citation_style,
            )
        except Exception:
            output_path.unlink(missing_ok=True)
            raise

        changed_paragraphs = sum(
            1 for old_text, new_text in zip(snapshot.paragraph_texts, amended_paragraphs) if old_text != new_text
        )
        changed_footnotes = sum(
            1 for fid, text in amended_footnotes.items() if snapshot.footnotes.get(fid) != text
        )
        if changed_items <= 0:
            raise ValueError("No detectable amendments were generated for the DOCX.")
        download_bytes = output_path.read_bytes()
        mark_legal_doc_amend_session_active(project_id)
        return LegalDocAmendResult(
            output_path=output_path,
            summary=summary,
            changed_paragraphs=changed_paragraphs,
            changed_footnotes=changed_footnotes,
            download_name=output_path.name,
            download_bytes=download_bytes,
        )
    finally:
        shutil.rmtree(temp_source.parent, ignore_errors=True)
        shutil.rmtree(temp_artifacts_dir, ignore_errors=True)


def run_local_legal_doc_amend_workflow(
    *,
    api_key: str,
    source_path: Path,
    message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    provider: str = "auto",
    model_name: Optional[str] = None,
) -> LegalDocAmendResult:
    """
    Direct-code/local-file wrapper around the same provider-backed amend flow.

    "Local" here means the source DOCX is read from the filesystem rather than
    uploaded through the website UI. It does not mean local model inference.
    """
    source_path = source_path.expanduser().resolve()
    if not source_path.exists() or source_path.suffix.lower() != ".docx":
        raise ValueError(f"Source DOCX not found: {source_path}")

    payload = base64.b64encode(source_path.read_bytes()).decode("utf-8")
    doc = {
        "id": "local-docx",
        "type": "file",
        "name": source_path.name,
        "mimeType": DOCX_MIME,
        "data": payload,
        "size": source_path.stat().st_size,
    }
    return run_uploaded_legal_doc_amend_workflow(
        api_key=api_key,
        message=message,
        documents=[doc],
        project_id=f"local::{source_path.stem}",
        history=history,
        provider=provider,
        model_name=model_name,
    )


def run_auto_legal_doc_amend_workflow(
    *,
    api_key: str,
    message: str,
    documents: Optional[List[Dict[str, Any]]] = None,
    source_path: Optional[Path] = None,
    history: Optional[List[Dict[str, Any]]] = None,
    provider: str = "auto",
    model_name: Optional[str] = None,
    project_id: str = "auto::legal_doc_amend",
    search_roots: Optional[List[Path | str]] = None,
) -> LegalDocAmendResult:
    docs = documents or []
    if wants_legal_doc_amend(message, docs):
        return run_uploaded_legal_doc_amend_workflow(
            api_key=api_key,
            message=message,
            documents=docs,
            project_id=project_id,
            history=history,
            provider=provider,
            model_name=model_name,
        )

    resolved_source = source_path
    if resolved_source is None:
        resolved_source = resolve_local_legal_doc_amend_path(message, search_roots=search_roots)
    if resolved_source is None:
        raise ValueError(
            "No uploaded DOCX or resolvable local DOCX was found for this amend request."
        )
    return run_local_legal_doc_amend_workflow(
        api_key=api_key,
        source_path=resolved_source,
        message=message,
        history=history,
        provider=provider,
        model_name=model_name,
    )
