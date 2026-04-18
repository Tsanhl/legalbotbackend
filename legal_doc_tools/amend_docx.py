#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import re
import shutil
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from lxml import etree
from word_count_rules import (
    amend_requested_word_count_window,
    count_words_for_targeting,
    preserve_original_length_window,
)

try:
    from .refine_docx_from_amended import (
        DESKTOP_ROOT,
        NS,
        _apply_diff_to_paragraph,
        _apply_full_replace_to_paragraph,
        _assert_markup_detectable,
        _build_footnote_case_reference_map,
        _build_footnote_search_text_map,
        _build_new_footnote_from_template,
        _ensure_reference_marker_first,
        _ensure_space_after_reference_marker,
        _copy_source_to_temp_if_same_as_output,
        _first_textual_run_in_paragraph,
        _iter_body_paragraphs,
        _iter_footnote_nodes_by_id,
        _iter_footnote_paragraphs_by_id,
        _footnote_reference_runs_with_positions,
        _normalize_body_footnote_reference_positions,
        _normalize_body_footnote_reference_styles_from_original,
        _normalize_body_italics,
        _normalize_case_italics_in_footnotes,
        _normalize_footnote_styles_from_original,
        _normalize_downstream_footnote_citations,
        _normalize_new_footnote_citation_text,
        _normalize_to_final_output_path,
        _paragraph_is_simple,
        _paragraph_contains_effective_italics,
        _paragraph_text_all_runs,
        _require_desktop_root_output,
        _reference_insert_index_for_text_pos,
        _require_markup_enabled,
        _template_paragraphs_for_new_footnote,
        _write_docx_with_replaced_parts,
        _load_docx_xml,
        _load_docx_xml_if_exists,
        _emit_changed_text,
        _rewrite_paragraph_in_place,
        _sanitize_footnote_plain_text,
        w_tag,
    )
    from .validate_delivery_gates import (
        _count_bibliography_entries,
        _extract_docx_comment_ids,
        _extract_footnote_ids,
        _extract_inline_written_comments,
    )
except ImportError:
    from refine_docx_from_amended import (
        DESKTOP_ROOT,
        NS,
        _apply_diff_to_paragraph,
        _apply_full_replace_to_paragraph,
        _assert_markup_detectable,
        _build_footnote_case_reference_map,
        _build_footnote_search_text_map,
        _build_new_footnote_from_template,
        _ensure_reference_marker_first,
        _ensure_space_after_reference_marker,
        _copy_source_to_temp_if_same_as_output,
        _first_textual_run_in_paragraph,
        _iter_body_paragraphs,
        _iter_footnote_nodes_by_id,
        _iter_footnote_paragraphs_by_id,
        _footnote_reference_runs_with_positions,
        _normalize_body_footnote_reference_positions,
        _normalize_body_footnote_reference_styles_from_original,
        _normalize_body_italics,
        _normalize_case_italics_in_footnotes,
        _normalize_footnote_styles_from_original,
        _normalize_downstream_footnote_citations,
        _normalize_new_footnote_citation_text,
        _normalize_to_final_output_path,
        _paragraph_is_simple,
        _paragraph_contains_effective_italics,
        _paragraph_text_all_runs,
        _require_desktop_root_output,
        _reference_insert_index_for_text_pos,
        _require_markup_enabled,
        _template_paragraphs_for_new_footnote,
        _write_docx_with_replaced_parts,
        _load_docx_xml,
        _load_docx_xml_if_exists,
        _emit_changed_text,
        _rewrite_paragraph_in_place,
        _sanitize_footnote_plain_text,
        w_tag,
    )
    from validate_delivery_gates import (
        _count_bibliography_entries,
        _extract_docx_comment_ids,
        _extract_footnote_ids,
        _extract_inline_written_comments,
    )


def _one_off_temp_dirs() -> set[Path]:
    dirs = {
        Path("/tmp").resolve(),
        Path(tempfile.gettempdir()).resolve(),
        (Path(__file__).resolve().parent.parent / "tmp").resolve(),
    }
    env_tmp = os.environ.get("TMPDIR")
    if env_tmp:
        dirs.add(Path(env_tmp).expanduser().resolve())
    return dirs


ONE_OFF_TEMP_DIRS = _one_off_temp_dirs()
PROJECT_ROOT = Path(__file__).resolve().parent.parent.resolve()
TRUTHY_REVIEW_VALUES = {"1", "true", "yes", "y", "done", "complete", "completed", "checked", "verified"}
URL_IN_ANGLE_BRACKETS_RE = re.compile(r"<(https?://[^<>\s]+)>")
RAW_URL_RE = re.compile(r"(?<!<)(?<!://)\b(?:https?://|www\.)\S+")
FOOTNOTE_CROSSREF_RE = re.compile(r"\(n\s*(\d+)\)")
AUTOMATIC_AUTHORITY_TRUTH_MODES = {
    "automatic",
    "automatic_report",
    "automatic_full",
    "automatic_truth_report",
    "full_automatic",
}
AUTOMATIC_SENTENCE_SUPPORT_MODES = {
    "automatic",
    "automatic_report",
    "automatic_full",
    "automatic_support_report",
    "full_automatic",
}
INFERENTIAL_SENTENCE_SUPPORT_LEVELS = {
    "inferential",
    "application",
    "analytical",
    "synthesis",
    "mixed",
}
QUESTION_GUIDANCE_MODES = {
    "guide_if_needed",
    "guided_if_needed",
    "question_guide_if_needed",
}
QUESTION_GUIDANCE_ALLOWED_STATUSES = {
    "added",
    "already_covered",
    "not_needed",
}

COMMON_ONE_OFF_CLEANUP_CONFIG_KEYS: tuple[str, ...] = (
    "verification_ledger_path",
    "authority_verification_report_path",
    "sentence_support_report_path",
    "argumentative_sentence_support_report_path",
)
DOC_SPECIFIC_ONE_OFF_CLEANUP_CONFIG_KEYS: tuple[str, ...] = (
    "one_off_instruction_path",
    "one_off_instruction_paths",
    "one_off_prompt_path",
    "one_off_prompt_paths",
    "one_off_helper_path",
    "one_off_helper_paths",
    "one_off_helper_code_path",
    "one_off_helper_code_paths",
    "one_off_test_path",
    "one_off_test_paths",
    "one_off_helper_test_path",
    "one_off_helper_test_paths",
)
ONE_OFF_WORKSPACE_FILE_SUFFIXES: tuple[str, ...] = (
    ".docx",
    ".doc",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".py",
)
ONE_OFF_WORKSPACE_NAME_HINTS: tuple[str, ...] = (
    "one_off",
    "one-off",
    "doc_specific",
    "doc-specific",
    "question",
    "rubric",
    "context",
    "prompt",
    "instruction",
    "helper",
    "test",
    "draft",
    "temp",
    "tmp",
    "notes",
    "ledger",
    "verification",
    "artifact",
    "render",
    "report",
)
AMEND_REQUIRED_TRUE_FLAGS: tuple[tuple[str, str], ...] = (
    ("content_checked", "content sentence-by-sentence review"),
    ("sentence_by_sentence_checked", "sentence-by-sentence perfection review"),
    ("sentence_to_source_audit_checked", "sentence-to-source / proposition-to-authority audit"),
    ("argumentative_sentence_support_checked", "argumentative sentence-by-sentence source-support audit"),
    ("perfection_pass", "top-band perfection pass"),
    ("microscopic_style_polish_checked", "final microscopic style-level polish pass"),
    ("logical_coherence_checked", "logical coherence and paragraph-to-paragraph flow review"),
    (
        "weak_or_overstated_propositions_corrected",
        "weak, overstated, or unsupported propositions were corrected or removed",
    ),
    ("citation_accuracy_checked", "citation and authority-chain accuracy audit"),
    ("citation_link_accuracy_checked", "citation link/URL accuracy audit"),
)
BENCHMARK_QUALITY_FLAGS: tuple[tuple[str, str], ...] = (
    (
        "question_answered_checked",
        "the draft was checked to ensure it actually answers the user’s question or prompt",
    ),
    (
        "question_answer_accuracy_checked",
        "question-based answer and argument accuracy were reviewed and corrected where needed",
    ),
    (
        "question_argument_coverage_checked",
        "question-led coverage of the strongest available arguments, missing issue branches, and conclusion structure",
    ),
    (
        "counterarguments_checked",
        "explicit counterarguments and rebuttals were considered and added where they improved top-band quality",
    ),
    (
        "added_points_authority_support_checked",
        "every added substantive point or counterargument received verified authority support in the active citation style where needed",
    ),
)
ALLOWED_AMEND_DEPTHS = {"default_perfection", "deeper_on_request"}
ALLOWED_TARGET_STANDARDS = {"10/10", "90+", "10/10;90+", "90+;10/10"}
ALLOWED_WORD_COUNT_MODES = {"preserve_original_length", "near_target", "at_or_below_max"}


def _load_config(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON config at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Amendment config root must be a JSON object.")
    return data


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _truthy_review_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().casefold() in TRUTHY_REVIEW_VALUES
    return False


def _coerce_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _positive_int_review_value(value: Any, *, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Amend default quality gate failed: review_context field '{field}' must be a positive integer."
        ) from exc
    if parsed <= 0:
        raise ValueError(
            f"Amend default quality gate failed: review_context field '{field}' must be a positive integer."
        )
    return parsed


def _require_review_context_flags(
    review_context: dict[str, Any],
    requirements: tuple[tuple[str, str], ...],
    *,
    benchmarked: bool = False,
) -> None:
    prefix = (
        "Amend default quality gate failed: when a question/rubric is provided, review_context must confirm "
        if benchmarked
        else "Amend default quality gate failed: review_context must confirm "
    )
    for key, label in requirements:
        if not _truthy_review_flag(review_context.get(key)):
            raise ValueError(f"{prefix}{label} (set '{key}': true).")


def _validate_word_count_review_context(review_context: dict[str, Any]) -> None:
    word_count_instruction = str(review_context.get("word_count_instruction") or "").strip()
    if not word_count_instruction:
        raise ValueError(
            "Amend default quality gate failed: review_context must record the active word-count instruction "
            "(for example 'max 4000 words', 'target 2500 words', or 'preserve original length')."
        )

    word_count_mode = str(review_context.get("word_count_mode") or "").strip()
    if word_count_mode not in ALLOWED_WORD_COUNT_MODES:
        raise ValueError(
            "Amend default quality gate failed: review_context must declare word-count handling "
            "(set 'word_count_mode' to 'preserve_original_length', 'near_target', or 'at_or_below_max')."
        )
    if not _truthy_review_flag(review_context.get("word_count_followed")):
        raise ValueError(
            "Amend default quality gate failed: review_context must confirm the amended output followed the active "
            "word-count instruction (set 'word_count_followed': true)."
        )
    if word_count_mode == "near_target":
        _positive_int_review_value(review_context.get("target_word_count"), field="target_word_count")
    if word_count_mode == "at_or_below_max":
        _positive_int_review_value(review_context.get("max_word_count"), field="max_word_count")


def _review_context_has_benchmark(review_context: dict[str, Any]) -> bool:
    return bool(
        str(review_context.get("question") or "").strip()
        or str(review_context.get("rubric") or "").strip()
    )


def _validate_benchmarked_amend_review_context(review_context: dict[str, Any]) -> None:
    if not _truthy_review_flag(review_context.get("question_based_amend")):
        raise ValueError(
            "Amend default quality gate failed: a question/rubric was provided, so review_context must confirm "
            "question-based amendment (set 'question_based_amend': true)."
        )
    _require_review_context_flags(
        review_context,
        BENCHMARK_QUALITY_FLAGS,
        benchmarked=True,
    )
    fit_verdict = str(review_context.get("fit_verdict") or "").strip().casefold()
    if fit_verdict != "fully fits target":
        raise ValueError(
            "Amend default quality gate failed: when a question/rubric is provided, fit_verdict must be "
            "'Fully fits target'."
        )


def _count_body_words_in_doc_root(doc_root: etree._Element) -> int:
    body_text = "\n".join(_paragraph_text_all_runs(p) for p in _iter_body_paragraphs(doc_root))
    return count_words_for_targeting(body_text)


def _enforce_review_context_word_count(
    *,
    source: Path,
    amended_doc_root: etree._Element,
    review_context: dict[str, Any],
) -> None:
    if not isinstance(review_context, dict):
        return

    mode = str(review_context.get("word_count_mode") or "").strip()
    if not mode:
        return

    final_words = _count_body_words_in_doc_root(amended_doc_root)
    if mode == "near_target":
        target = _positive_int_review_value(review_context.get("target_word_count"), field="target_word_count")
        lower, upper = amend_requested_word_count_window(target)
        if not (lower <= final_words <= upper):
            raise ValueError(
                f"Amend word-count rule failed: final body-word count is {final_words}; "
                f"required {lower}-{upper} for the requested {target}-word target."
            )
        return

    if mode == "at_or_below_max":
        max_words = _positive_int_review_value(review_context.get("max_word_count"), field="max_word_count")
        lower, upper = amend_requested_word_count_window(max_words)
        if not (lower <= final_words <= upper):
            raise ValueError(
                f"Amend word-count rule failed: final body-word count is {final_words}; "
                f"required {lower}-{upper} for the requested {max_words}-word cap."
            )
        return

    if mode == "preserve_original_length":
        original_root = _load_docx_xml(source, "word/document.xml")
        original_words = _count_body_words_in_doc_root(original_root)
        lower, upper = preserve_original_length_window(original_words)
        if not (lower <= final_words <= upper):
            raise ValueError(
                f"Amend word-count rule failed: final body-word count is {final_words}; "
                f"required {lower}-{upper} to preserve the original {original_words}-word length."
            )


def _paragraph_match_prefix(text: str, prefix: str) -> bool:
    return _normalize_space(text).startswith(_normalize_space(prefix))


def _string_list(values: Any) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise ValueError("Expected a list of strings.")
    return values


def _int_list(values: Any) -> list[int]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValueError("Expected a list of integers.")
    out: list[int] = []
    for item in values:
        try:
            out.append(int(item))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Expected integer value, got {item!r}.") from exc
    return out


def _read_optional_text_path(path: Optional[Path]) -> Optional[str]:
    if path is None:
        return None
    return path.read_text(encoding="utf-8").strip()


def _path_is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def _is_one_off_artifact(path: Optional[Path]) -> bool:
    if path is None:
        return False
    resolved = path.expanduser().resolve()
    return any(_path_is_within(resolved, temp_dir) for temp_dir in ONE_OFF_TEMP_DIRS)


def _name_has_one_off_hint(path: Path) -> bool:
    low = path.name.casefold()
    return any(hint in low for hint in ONE_OFF_WORKSPACE_NAME_HINTS)


def _is_workspace_one_off_artifact(path: Optional[Path]) -> bool:
    if path is None:
        return False
    resolved = path.expanduser().resolve()
    if resolved == PROJECT_ROOT or not _path_is_within(resolved, PROJECT_ROOT):
        return False

    relevant_nodes = [resolved, *resolved.parents]
    if resolved.is_dir():
        return any(
            node != PROJECT_ROOT and _path_is_within(node, PROJECT_ROOT) and _name_has_one_off_hint(node)
            for node in relevant_nodes
        )

    if resolved.suffix.lower() not in ONE_OFF_WORKSPACE_FILE_SUFFIXES:
        return False
    return any(
        node != PROJECT_ROOT and _path_is_within(node, PROJECT_ROOT) and _name_has_one_off_hint(node)
        for node in relevant_nodes
    )


def _is_cleanup_candidate(path: Optional[Path]) -> bool:
    return _is_one_off_artifact(path) or _is_workspace_one_off_artifact(path)


def _string_path_list(values: Any) -> list[Path]:
    if values is None:
        return []
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise ValueError("Expected a list of path strings.")
    return [Path(item).expanduser().resolve() for item in values if item.strip()]


def _collect_cleanup_config_paths(config: dict[str, Any], *keys: str) -> list[Path]:
    paths: list[Path] = []
    for key in keys:
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            paths.append(Path(value).expanduser().resolve())
            continue
        if isinstance(value, list):
            paths.extend(_string_path_list(value))
    return paths


def _cleanup_one_off_artifacts(paths: list[Path], *, protected_paths: Optional[list[Path]] = None) -> int:
    seen: set[Path] = set()
    removed = 0
    protected_nodes = {
        p.expanduser().resolve()
        for p in (protected_paths or [])
        if p is not None
    }
    protected_dirs = {
        Path.home().resolve(),
        DESKTOP_ROOT.expanduser().resolve(),
        PROJECT_ROOT,
    }
    for path in paths:
        resolved = path.expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved in protected_nodes:
            continue
        if resolved.is_dir():
            if resolved in protected_dirs:
                continue
            try:
                shutil.rmtree(resolved, ignore_errors=False)
                removed += 1
            except OSError:
                continue
            continue
        try:
            resolved.unlink(missing_ok=True)
            removed += 1
        except OSError:
            continue
    return removed


def _collect_registered_cleanup_targets(
    config: dict[str, Any],
    *,
    include_question_guidance_report: bool,
) -> list[Path]:
    cleanup_targets: list[Path] = []
    cleanup_targets.extend(_collect_cleanup_config_paths(config, *COMMON_ONE_OFF_CLEANUP_CONFIG_KEYS))
    if include_question_guidance_report:
        cleanup_targets.extend(_collect_cleanup_config_paths(config, "question_guidance_report_path"))
    cleanup_targets.extend(_collect_cleanup_config_paths(config, *DOC_SPECIFIC_ONE_OFF_CLEANUP_CONFIG_KEYS))
    cleanup_targets.extend(_string_path_list(config.get("cleanup_paths")))
    return cleanup_targets


def _collect_one_off_cleanup_targets(
    *,
    config: dict[str, Any],
    config_path: Path,
    question_path: Optional[Path],
    rubric_path: Optional[Path],
    context_out_path: Optional[Path],
) -> list[Path]:
    cleanup_targets = _collect_registered_cleanup_targets(
        config,
        include_question_guidance_report=True,
    )

    if _is_cleanup_candidate(config_path):
        cleanup_targets.append(config_path)
    if question_path is not None and _is_cleanup_candidate(question_path):
        cleanup_targets.append(question_path)
    if rubric_path is not None and _is_cleanup_candidate(rubric_path):
        cleanup_targets.append(rubric_path)
    if context_out_path is not None and _is_cleanup_candidate(context_out_path):
        cleanup_targets.append(context_out_path)

    return cleanup_targets


def _collect_embedded_one_off_cleanup_targets(config: dict[str, Any]) -> list[Path]:
    return _collect_registered_cleanup_targets(
        config,
        include_question_guidance_report=True,
    )


def _cleanup_embedded_one_off_artifacts(
    config: dict[str, Any],
    *,
    protected_paths: Optional[list[Path]] = None,
) -> int:
    return _cleanup_one_off_artifacts(
        _collect_embedded_one_off_cleanup_targets(config),
        protected_paths=protected_paths,
    )


def _lint_oscola_online_citation_text(text: str, *, context: str, bibliography_entry: bool) -> None:
    stripped = text.strip()
    urls = URL_IN_ANGLE_BRACKETS_RE.findall(stripped)
    raw_url_match = RAW_URL_RE.search(stripped)
    if raw_url_match:
        raise ValueError(
            f"{context} failed OSCOLA URL lint: raw URL must be enclosed in angle brackets, found {raw_url_match.group(0)!r}."
        )
    if not urls:
        return

    expected_suffix = ">" if bibliography_entry else ">."
    if not stripped.endswith(expected_suffix):
        location = "bibliography entry" if bibliography_entry else "footnote"
        raise ValueError(
            f"{context} failed OSCOLA URL lint: amended {location} with online source must end with {expected_suffix!r}."
        )

    for url in urls:
        if not re.match(r"^https?://[^\s<>]+$", url):
            raise ValueError(f"{context} failed OSCOLA URL lint: malformed URL {url!r}.")
        if url[-1] in ".,;:":
            raise ValueError(
                f"{context} failed OSCOLA URL lint: trailing punctuation must be outside angle brackets, got {url!r}."
            )


def _lint_amended_footnote_citations(
    footnotes_root: Optional[etree._Element],
    *,
    corrected_ids: set[int],
    added_ids: set[int],
) -> None:
    if footnotes_root is None:
        return

    target_ids = corrected_ids | added_ids
    if not target_ids:
        return

    nodes_by_id = _iter_footnote_nodes_by_id(footnotes_root)
    existing_ids = set(nodes_by_id)
    for fid in sorted(target_ids):
        node = nodes_by_id.get(fid)
        if node is None:
            raise ValueError(f"Amend citation lint failed: footnote {fid} not found after amendment.")
        text = "".join(node.xpath(".//w:t/text()", namespaces=NS)).strip()
        _lint_oscola_online_citation_text(
            text,
            context=f"Amended footnote {fid}",
            bibliography_entry=False,
        )
        for match in FOOTNOTE_CROSSREF_RE.finditer(text):
            target = int(match.group(1))
            if target not in existing_ids:
                raise ValueError(
                    f"Amend citation lint failed: footnote {fid} cross-refers to missing footnote (n {target})."
                )
            if target >= fid:
                raise ValueError(
                    f"Amend citation lint failed: footnote {fid} has forward/self cross-reference (n {target}). "
                    "Replace it with a valid earlier cross-reference or a full citation."
                )


def _normalize_authority_report_entries(
    value: Any,
    *,
    label: str,
    id_fields: tuple[str, ...],
) -> dict[int, dict[str, Any]]:
    if value is None:
        return {}

    raw_entries: list[dict[str, Any]] = []
    if isinstance(value, list):
        for idx, item in enumerate(value, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"Automatic authority verification failed: {label} item {idx} must be a JSON object.")
            raw_entries.append(item)
    elif isinstance(value, dict):
        for raw_key, payload in value.items():
            entry = dict(payload) if isinstance(payload, dict) else {"value": payload}
            entry.setdefault(id_fields[0], raw_key)
            raw_entries.append(entry)
    else:
        raise ValueError(f"Automatic authority verification failed: {label} must be a JSON object or array.")

    entries_by_id: dict[int, dict[str, Any]] = {}
    for idx, entry in enumerate(raw_entries, start=1):
        raw_id = next((entry.get(field) for field in id_fields if entry.get(field) is not None), None)
        entry_id = _coerce_nonnegative_int(raw_id)
        if entry_id is None or entry_id <= 0:
            raise ValueError(
                f"Automatic authority verification failed: {label} item {idx} is missing a positive identifier "
                f"({', '.join(id_fields)})."
            )
        entries_by_id[entry_id] = entry
    return entries_by_id


def _entry_has_true_flag(entry: dict[str, Any], field_names: tuple[str, ...]) -> bool:
    for field_name in field_names:
        if field_name in entry and _truthy_review_flag(entry.get(field_name)):
            return True
    return False


def _validate_authority_report_entry(entry: dict[str, Any], *, context: str) -> None:
    required_flags: tuple[tuple[tuple[str, ...], str], ...] = (
        (("verified",), "verified"),
        (("source_exists", "authority_exists"), "source existence"),
        (("metadata_matches", "metadata_verified", "citation_matches_source"), "metadata match"),
    )
    for field_names, label in required_flags:
        if not _entry_has_true_flag(entry, field_names):
            raise ValueError(
                f"Automatic authority verification failed: {context} must confirm {label} "
                f"({', '.join(field_names)} = true)."
            )

    has_url_signal = any(
        entry.get(field) not in (None, "", False)
        for field in ("url", "source_url", "access_url", "url_present", "online_source")
    )
    if has_url_signal and not _entry_has_true_flag(entry, ("link_checked", "url_checked", "access_checked")):
        raise ValueError(
            f"Automatic authority verification failed: {context} includes an online source, so link accuracy must be "
            "confirmed (link_checked/url_checked/access_checked = true)."
        )


def _validate_authority_verification_report(
    report_path: Path,
    *,
    footnote_ids: set[int],
    bibliography_count: int,
) -> None:
    if not report_path.exists():
        raise ValueError(f"Automatic authority verification failed: report does not exist: {report_path}")

    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Automatic authority verification failed: report must be valid JSON: {report_path}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError("Automatic authority verification failed: report root must be a JSON object.")

    mode = str(data.get("verification_mode") or data.get("mode") or "").strip().casefold()
    if not (_truthy_review_flag(data.get("automatic")) or mode in AUTOMATIC_AUTHORITY_TRUTH_MODES):
        raise ValueError(
            "Automatic authority verification failed: report must declare automatic verification "
            "(set 'automatic': true or use verification_mode='automatic_report')."
        )

    summary = data.get("summary")
    summary_unverified = None
    if isinstance(summary, dict):
        summary_unverified = _coerce_nonnegative_int(summary.get("unverified"))
    if summary_unverified is None:
        summary_unverified = _coerce_nonnegative_int(data.get("unverified"))
    if summary_unverified != 0:
        raise ValueError(
            "Automatic authority verification failed: report must confirm zero unverified authorities "
            "(summary.unverified or unverified must equal 0)."
        )

    footnote_entries = _normalize_authority_report_entries(
        data.get("footnotes") or data.get("footnote_entries"),
        label="footnotes",
        id_fields=("id", "footnote_id", "number"),
    )
    if footnote_ids:
        missing = footnote_ids - set(footnote_entries)
        if missing:
            sample = sorted(missing)[:10]
            raise ValueError(
                "Automatic authority verification failed: report does not cover every amended footnote "
                f"(missing IDs: {sample})."
            )
        for fid in sorted(footnote_ids):
            _validate_authority_report_entry(footnote_entries[fid], context=f"Footnote {fid}")

    bibliography_entries = _normalize_authority_report_entries(
        data.get("bibliography_entries")
        or data.get("reference_entries")
        or data.get("bibliography")
        or data.get("references"),
        label="bibliography entries",
        id_fields=("entry", "id", "number", "reference_entry"),
    )
    if bibliography_count > 0:
        expected_ids = set(range(1, bibliography_count + 1))
        missing = expected_ids - set(bibliography_entries)
        if missing:
            sample = sorted(missing)[:10]
            raise ValueError(
                "Automatic authority verification failed: report does not cover every bibliography/reference entry "
                f"(missing entries: {sample})."
            )
        for entry_id in sorted(expected_ids):
            _validate_authority_report_entry(
                bibliography_entries[entry_id],
                context=f"Bibliography entry {entry_id}",
            )


def _normalize_sentence_support_entries(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(
            "Automatic sentence-support verification failed: report must contain a 'sentences', "
            "'sentence_entries', or 'argumentative_sentences' array."
        )
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"Automatic sentence-support verification failed: sentence entry {idx} must be a JSON object."
            )
        normalized.append(item)
    return normalized


def _validate_sentence_support_report_entry(entry: dict[str, Any], *, context: str) -> None:
    entry_id = _coerce_nonnegative_int(entry.get("id") or entry.get("number"))
    if entry_id is None or entry_id <= 0:
        raise ValueError(
            f"Automatic sentence-support verification failed: {context} must include a positive 'id' or 'number'."
        )

    sentence_text = str(entry.get("text") or entry.get("sentence") or "").strip()
    if not sentence_text:
        raise ValueError(
            f"Automatic sentence-support verification failed: {context} must include the audited sentence text."
        )

    if not _entry_has_true_flag(
        entry,
        ("supported", "source_supported", "proposition_supported", "support_confirmed"),
    ):
        raise ValueError(
            f"Automatic sentence-support verification failed: {context} must confirm source support "
            "(supported/source_supported/proposition_supported/support_confirmed = true)."
        )

    if not _entry_has_true_flag(
        entry,
        ("proposition_accuracy_checked", "accuracy_checked", "sentence_accuracy_checked"),
    ):
        raise ValueError(
            f"Automatic sentence-support verification failed: {context} must confirm proposition accuracy was "
            "checked (proposition_accuracy_checked/accuracy_checked/sentence_accuracy_checked = true)."
        )

    sources_checked = entry.get("sources_checked") or entry.get("authorities_checked") or entry.get("supporting_sources")
    if not isinstance(sources_checked, list) or not any(str(item).strip() for item in sources_checked):
        raise ValueError(
            f"Automatic sentence-support verification failed: {context} must list the checked supporting sources "
            "('sources_checked' / 'authorities_checked' / 'supporting_sources')."
        )

    for field_name in ("unsupported", "overstated", "weak"):
        if _truthy_review_flag(entry.get(field_name)):
            raise ValueError(
                f"Automatic sentence-support verification failed: {context} is still marked {field_name!r}; "
                "the final amended output must have zero unresolved unsupported/overstated/weak propositions."
            )

    support_level = str(entry.get("support_level") or entry.get("support_kind") or "").strip().casefold()
    if support_level in INFERENTIAL_SENTENCE_SUPPORT_LEVELS and not _entry_has_true_flag(
        entry,
        ("framed_as_inference", "clearly_presented_as_inference"),
    ):
        raise ValueError(
            f"Automatic sentence-support verification failed: {context} uses inferential/applicative support, so "
            "the report must confirm it is framed as inference "
            "(framed_as_inference/clearly_presented_as_inference = true)."
        )


def _validate_sentence_support_report(report_path: Path) -> None:
    if not report_path.exists():
        raise ValueError(f"Automatic sentence-support verification failed: report does not exist: {report_path}")

    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Automatic sentence-support verification failed: report must be valid JSON: {report_path}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError("Automatic sentence-support verification failed: report root must be a JSON object.")

    mode = str(data.get("verification_mode") or data.get("mode") or "").strip().casefold()
    if not (_truthy_review_flag(data.get("automatic")) or mode in AUTOMATIC_SENTENCE_SUPPORT_MODES):
        raise ValueError(
            "Automatic sentence-support verification failed: report must declare automatic verification "
            "(set 'automatic': true or use verification_mode='automatic_report')."
        )

    summary = data.get("summary")
    summary_dict = summary if isinstance(summary, dict) else {}
    for field_name in ("unsupported", "overstated", "weak"):
        count = _coerce_nonnegative_int(summary_dict.get(field_name))
        if count is None:
            count = _coerce_nonnegative_int(data.get(field_name))
        if count != 0:
            raise ValueError(
                "Automatic sentence-support verification failed: report must confirm zero unresolved "
                f"{field_name} propositions (summary.{field_name} or {field_name} must equal 0)."
            )

    if not _truthy_review_flag(
        summary_dict.get("all_argumentative_sentences_covered")
        or data.get("all_argumentative_sentences_covered")
    ):
        raise ValueError(
            "Automatic sentence-support verification failed: report must confirm that all argumentative sentences "
            "were checked ('all_argumentative_sentences_covered': true)."
        )

    sentence_entries = _normalize_sentence_support_entries(
        data.get("sentences") or data.get("sentence_entries") or data.get("argumentative_sentences")
    )
    expected_count = _coerce_nonnegative_int(summary_dict.get("argumentative_sentences"))
    if expected_count is None:
        expected_count = _coerce_nonnegative_int(data.get("argumentative_sentences"))
    if expected_count is None:
        raise ValueError(
            "Automatic sentence-support verification failed: report must record the number of argumentative "
            "sentences checked (summary.argumentative_sentences or argumentative_sentences)."
        )
    if expected_count != len(sentence_entries):
        raise ValueError(
            "Automatic sentence-support verification failed: report sentence count does not match the supplied "
            f"entries (expected {expected_count}, got {len(sentence_entries)})."
        )

    seen_ids: set[int] = set()
    for idx, entry in enumerate(sentence_entries, start=1):
        entry_id = _coerce_nonnegative_int(entry.get("id") or entry.get("number"))
        if entry_id is None or entry_id <= 0:
            raise ValueError(
                f"Automatic sentence-support verification failed: sentence entry {idx} must include a positive "
                "'id' or 'number'."
            )
        if entry_id in seen_ids:
            raise ValueError(
                f"Automatic sentence-support verification failed: duplicate sentence entry id {entry_id}."
            )
        seen_ids.add(entry_id)
        _validate_sentence_support_report_entry(entry, context=f"Sentence entry {entry_id}")


def _validate_question_guidance_report(report_path: Path) -> None:
    if not report_path.exists():
        raise ValueError(f"Question guidance validation failed: report does not exist: {report_path}")

    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Question guidance validation failed: report must be valid JSON: {report_path}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError("Question guidance validation failed: report root must be a JSON object.")

    mode = str(data.get("guide_mode") or data.get("mode") or "").strip().casefold()
    if mode not in QUESTION_GUIDANCE_MODES:
        raise ValueError(
            "Question guidance validation failed: report must declare a supported guide mode "
            f"({sorted(QUESTION_GUIDANCE_MODES)})."
        )

    summary = data.get("summary")
    unresolved = None
    if isinstance(summary, dict):
        unresolved = _coerce_nonnegative_int(summary.get("unresolved"))
    if unresolved is None:
        unresolved = _coerce_nonnegative_int(data.get("unresolved"))
    if unresolved != 0:
        raise ValueError(
            "Question guidance validation failed: report must confirm zero unresolved benchmark gaps "
            "(summary.unresolved or unresolved must equal 0)."
        )

    items = data.get("issues") or data.get("findings") or data.get("gaps")
    if not isinstance(items, list):
        raise ValueError(
            "Question guidance validation failed: report must contain an 'issues', 'findings', or 'gaps' array."
        )

    seen_ids: set[int] = set()
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Question guidance validation failed: item {idx} must be a JSON object.")
        item_id = _coerce_nonnegative_int(item.get("id") or item.get("number"))
        if item_id is None or item_id <= 0:
            raise ValueError(
                f"Question guidance validation failed: item {idx} is missing a positive 'id' or 'number'."
            )
        if item_id in seen_ids:
            raise ValueError(f"Question guidance validation failed: duplicate item id {item_id}.")
        seen_ids.add(item_id)

        status = str(item.get("status") or "").strip().casefold()
        if status not in QUESTION_GUIDANCE_ALLOWED_STATUSES:
            raise ValueError(
                f"Question guidance validation failed: item {item_id} has unsupported status {status!r}. "
                f"Use one of {sorted(QUESTION_GUIDANCE_ALLOWED_STATUSES)}."
            )

        issue_text = str(item.get("issue") or item.get("gap") or "").strip()
        if not issue_text:
            raise ValueError(
                f"Question guidance validation failed: item {item_id} must describe the benchmark gap or issue."
            )

        if status == "not_needed":
            reason = str(item.get("reason") or item.get("rationale") or "").strip()
            if not reason:
                raise ValueError(
                    f"Question guidance validation failed: item {item_id} marked 'not_needed' must include a reason."
                )


def _cleanup_one_off_artifacts_after_amend(
    *,
    config: dict[str, Any],
    config_path: Path,
    question_path: Optional[Path],
    rubric_path: Optional[Path],
    context_out_path: Optional[Path],
    source_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> int:
    return _cleanup_one_off_artifacts(
        _collect_one_off_cleanup_targets(
            config=config,
            config_path=config_path,
            question_path=question_path,
            rubric_path=rubric_path,
            context_out_path=context_out_path,
        ),
        protected_paths=[source_path, output_path],
    )


def _build_context(
    *,
    source: Path,
    config: dict[str, Any],
    question_text: Optional[str],
    rubric_text: Optional[str],
    based_on_comments: bool,
) -> dict[str, Any]:
    review_context = config.get("review_context") or {}
    if review_context and not isinstance(review_context, dict):
        raise ValueError("'review_context' must be a JSON object when provided.")

    question = question_text or review_context.get("question")
    rubric = rubric_text or review_context.get("rubric")

    docx_comment_ids: list[int] = []
    inline_comments: list[str] = []
    if based_on_comments or review_context.get("based_on_comments"):
        docx_comment_ids = _extract_docx_comment_ids(source)
        inline_comments = _extract_inline_written_comments(source)

    addressed_docx_comments = _int_list(review_context.get("docx_comments_addressed"))
    addressed_inline_comments = _int_list(review_context.get("inline_comments_addressed"))

    if based_on_comments or review_context.get("based_on_comments"):
        missing_docx = sorted(set(docx_comment_ids) - set(addressed_docx_comments))
        missing_inline = sorted(set(range(1, len(inline_comments) + 1)) - set(addressed_inline_comments))
        if missing_docx:
            raise ValueError(
                "Comment-based amend requires explicit coverage for all DOCX comments. "
                f"Missing IDs: {missing_docx}"
            )
        if missing_inline:
            raise ValueError(
                "Comment-based amend requires explicit coverage for all inline written comments. "
                f"Missing indexes: {missing_inline}"
            )

    return {
        "question": question,
        "rubric": rubric,
        "based_on_comments": bool(based_on_comments or review_context.get("based_on_comments")),
        "docx_comment_ids": docx_comment_ids,
        "inline_comments": inline_comments,
        "docx_comments_addressed": addressed_docx_comments,
        "inline_comments_addressed": addressed_inline_comments,
        "fit_verdict": review_context.get("fit_verdict"),
    }


def _require_default_amend_quality_context(source: Path, review_context: dict[str, Any], config: dict[str, Any]) -> None:
    if not isinstance(review_context, dict):
        raise ValueError(
            "Amend default quality gate requires a 'review_context' object recording sentence-level, citation, "
            "and benchmark-fit coverage."
        )

    _require_review_context_flags(review_context, AMEND_REQUIRED_TRUE_FLAGS)

    amend_depth = str(review_context.get("amend_depth") or "").strip()
    if amend_depth not in ALLOWED_AMEND_DEPTHS:
        raise ValueError(
            "Amend default quality gate failed: review_context must declare amend depth "
            "(set 'amend_depth' to 'default_perfection' or 'deeper_on_request')."
        )
    if amend_depth == "deeper_on_request" and not _truthy_review_flag(review_context.get("deeper_pass_requested")):
        raise ValueError(
            "Amend default quality gate failed: 'deeper_on_request' requires review_context to confirm the user "
            "explicitly asked for a deeper pass (set 'deeper_pass_requested': true)."
        )

    perfection_target = str(review_context.get("target_standard") or "").strip()
    if perfection_target not in ALLOWED_TARGET_STANDARDS:
        raise ValueError(
            "Amend default quality gate failed: review_context must declare the target standard "
            "(set 'target_standard' to '10/10' or '90+')."
        )

    _validate_word_count_review_context(review_context)

    if _extract_footnote_ids(source) and not _truthy_review_flag(review_context.get("footnotes_checked")):
        raise ValueError(
            "Amend default quality gate failed: source DOCX contains footnotes, so review_context must confirm "
            "line-by-line footnote verification (set 'footnotes_checked': true)."
        )

    if _count_bibliography_entries(source) > 0 and not _truthy_review_flag(review_context.get("bibliography_checked")):
        raise ValueError(
            "Amend default quality gate failed: source DOCX contains bibliography/reference entries, so "
            "review_context must confirm bibliography verification (set 'bibliography_checked': true)."
        )

    if _review_context_has_benchmark(review_context):
        _validate_benchmarked_amend_review_context(review_context)


def _enforce_default_structured_verification_requirements(
    source: Path,
    review_context: dict[str, Any],
    config: dict[str, Any],
) -> None:
    has_footnotes = bool(_extract_footnote_ids(source))
    has_bibliography = _count_bibliography_entries(source) > 0

    authority_mode = str(review_context.get("authority_truth_check_mode") or "").strip().casefold()
    authority_report_path_raw = config.get("authority_verification_report_path")
    if has_footnotes or has_bibliography:
        if not authority_mode:
            review_context["authority_truth_check_mode"] = "automatic_report"
        if not isinstance(authority_report_path_raw, str) or not authority_report_path_raw.strip():
            raise ValueError(
                "Every amend run, including the user's first amend request, with footnotes or bibliography entries requires "
                "'authority_verification_report_path' so each footnote/reference is checked against the "
                "underlying source before delivery."
            )

    sentence_support_mode = str(
        review_context.get("sentence_support_check_mode")
        or review_context.get("argumentative_sentence_support_mode")
        or ""
    ).strip().casefold()
    sentence_support_report_path_raw = (
        config.get("sentence_support_report_path") or config.get("argumentative_sentence_support_report_path")
    )
    if not sentence_support_mode:
        review_context["sentence_support_check_mode"] = "automatic_report"
    if not isinstance(sentence_support_report_path_raw, str) or not sentence_support_report_path_raw.strip():
        raise ValueError(
            "Every amend run, including the user's first amend request, requires 'sentence_support_report_path' "
            "so each argumentative sentence is checked against source support and any weak, overstated, or "
            "unsupported proposition is corrected before delivery."
        )


def _match_body_paragraph(
    paragraphs: list[etree._Element],
    *,
    paragraph_prefix: Optional[str] = None,
    paragraph_index: Optional[int] = None,
    occurrence: int = 1,
) -> etree._Element:
    if paragraph_index is not None:
        if paragraph_index < 0 or paragraph_index >= len(paragraphs):
            raise ValueError(f"paragraph_index {paragraph_index} is out of range for body paragraph list.")
        return paragraphs[paragraph_index]

    if not paragraph_prefix:
        raise ValueError("Each paragraph-targeting amendment must provide paragraph_prefix or paragraph_index.")

    matches = [
        paragraph
        for paragraph in paragraphs
        if _paragraph_match_prefix(_paragraph_text_all_runs(paragraph), paragraph_prefix)
    ]
    if not matches:
        raise ValueError(f"No paragraph found with prefix: {paragraph_prefix!r}")
    if occurrence < 1 or occurrence > len(matches):
        raise ValueError(
            f"Paragraph prefix {paragraph_prefix!r} matched {len(matches)} paragraph(s), "
            f"but requested occurrence {occurrence}."
        )
    return matches[occurrence - 1]


def _match_paragraph_index_in_parent(paragraph: etree._Element) -> tuple[etree._Element, int]:
    parent = paragraph.getparent()
    if parent is None:
        raise ValueError("Target paragraph has no parent node.")
    siblings = list(parent)
    try:
        idx = siblings.index(paragraph)
    except ValueError as exc:
        raise ValueError("Could not locate paragraph among parent children.") from exc
    return parent, idx


def _ensure_unique_substring(text: str, needle: str, *, label: str) -> int:
    first = text.find(needle)
    if first < 0:
        raise ValueError(f"Could not find {label} {needle!r} in paragraph.")
    second = text.find(needle, first + len(needle))
    if second >= 0:
        raise ValueError(f"{label.capitalize()} {needle!r} is ambiguous within paragraph; provide a more specific anchor.")
    return first


def _replace_exact_text_in_paragraph(
    paragraph: etree._Element,
    *,
    old: str,
    new: str,
) -> bool:
    current = _paragraph_text_all_runs(paragraph)
    start = _ensure_unique_substring(current, old, label="text")
    updated = current[:start] + new + current[start + len(old) :]
    return _rewrite_body_paragraph_preserving_footnotes(paragraph, updated)


def _append_text_to_paragraph(paragraph: etree._Element, text: str) -> bool:
    updated = _paragraph_text_all_runs(paragraph) + text
    return _rewrite_body_paragraph_preserving_footnotes(paragraph, updated)


def _insert_text_after_anchor(paragraph: etree._Element, *, anchor: str, text: str) -> bool:
    current = _paragraph_text_all_runs(paragraph)
    start = _ensure_unique_substring(current, anchor, label="anchor")
    insert_at = start + len(anchor)
    updated = current[:insert_at] + text + current[insert_at:]
    return _rewrite_body_paragraph_preserving_footnotes(paragraph, updated)


def _restore_missing_body_footnote_references(
    paragraph: etree._Element,
    original_refs: list[tuple[etree._Element, int, str]],
) -> None:
    if not original_refs:
        return

    current_refs = _footnote_reference_runs_with_positions(paragraph)
    current_counts = Counter(ref_id for _run, _pos, ref_id in current_refs)
    required_counts = Counter(ref_id for _run, _pos, ref_id in original_refs)
    missing_counts = required_counts - current_counts
    if not missing_counts:
        return

    for run, pos, ref_id in original_refs:
        if missing_counts[ref_id] <= 0:
            continue
        paragraph.insert(_reference_insert_index_for_text_pos(paragraph, pos), deepcopy(run))
        missing_counts[ref_id] -= 1


def _rewrite_body_paragraph_preserving_footnotes(paragraph: etree._Element, new_text: str) -> bool:
    original_refs = _footnote_reference_runs_with_positions(paragraph)
    if _paragraph_is_simple(paragraph):
        changed = _apply_diff_to_paragraph(
            paragraph,
            new_text,
            markup=True,
            preserve_projected_inline_italics=True,
        )
    else:
        changed = _apply_full_replace_to_paragraph(
            paragraph,
            new_text,
            markup=True,
            preserve_projected_inline_italics=True,
        )
    if changed:
        _restore_missing_body_footnote_references(paragraph, original_refs)
    return changed


def _body_footnote_reference_id_counts(doc_root: etree._Element) -> Counter[str]:
    counts: Counter[str] = Counter()
    for paragraph in _iter_body_paragraphs(doc_root):
        for _run, _pos, ref_id in _footnote_reference_runs_with_positions(paragraph):
            counts[ref_id] += 1
    return counts


def _assert_original_footnotes_preserved_if_relevant(
    *,
    original_doc_root: etree._Element,
    amended_doc_root: etree._Element,
    original_footnotes_root: Optional[etree._Element],
    amended_footnotes_root: Optional[etree._Element],
    explicitly_corrected_ids: set[int],
) -> None:
    if original_footnotes_root is None:
        return
    if amended_footnotes_root is None:
        raise ValueError(
            "Amend footnote safety gate failed: source DOCX has footnotes, but amended output lost the footnotes part."
        )

    original_ids = {int(fid) for fid in _extract_footnote_ids_from_root(original_footnotes_root)}
    amended_ids = {int(fid) for fid in _extract_footnote_ids_from_root(amended_footnotes_root)}
    missing_ids = sorted(original_ids - amended_ids)
    if missing_ids:
        raise ValueError(
            "Amend footnote safety gate failed: amended output removed original footnote IDs "
            f"{missing_ids[:10]}."
        )

    original_text_map = _build_footnote_search_text_map(original_footnotes_root)
    amended_text_map = _build_footnote_search_text_map(amended_footnotes_root)
    for fid in sorted(original_ids - explicitly_corrected_ids):
        original_text = original_text_map.get(fid, "")
        amended_text = amended_text_map.get(fid, "")
        if original_text != amended_text:
            raise ValueError(
                "Amend footnote safety gate failed: original footnote text changed without an explicit "
                f"correction instruction (footnote {fid})."
            )

    original_ref_counts = _body_footnote_reference_id_counts(original_doc_root)
    amended_ref_counts = _body_footnote_reference_id_counts(amended_doc_root)
    removed_ref_ids = sorted(
        int(ref_id)
        for ref_id, count in original_ref_counts.items()
        if amended_ref_counts.get(ref_id, 0) < count
    )
    if removed_ref_ids:
        raise ValueError(
            "Amend footnote safety gate failed: amended output removed original body footnote references "
            f"for IDs {removed_ref_ids[:10]}."
        )


def _extract_footnote_ids_from_root(footnotes_root: etree._Element) -> list[str]:
    return [
        node.get(w_tag("id"))
        for node in footnotes_root.xpath("/w:footnotes/w:footnote[@w:id>=1]", namespaces=NS)
        if node.get(w_tag("id")) is not None
    ]


def _clone_paragraph_for_insertion(template: etree._Element, text: str) -> etree._Element:
    paragraph = deepcopy(template)
    pPr = paragraph.find("w:pPr", namespaces=NS)
    for child in list(paragraph):
        if child is pPr:
            continue
        paragraph.remove(child)

    context_run = _first_textual_run_in_paragraph(template)
    new_children = _emit_changed_text(text, context_run, markup=True)
    _rewrite_paragraph_in_place(paragraph, new_children)
    return paragraph


def _next_footnote_id(footnotes_root: etree._Element) -> int:
    ids = [int(node.get(w_tag("id"))) for node in footnotes_root.xpath("/w:footnotes/w:footnote[@w:id>=1]", namespaces=NS)]
    return (max(ids) + 1) if ids else 1


def _make_footnote_reference_run(fid: int) -> etree._Element:
    run = etree.Element(w_tag("r"))
    rpr = etree.SubElement(run, w_tag("rPr"))
    etree.SubElement(rpr, w_tag("rStyle")).set(w_tag("val"), "FootnoteReference")
    etree.SubElement(rpr, w_tag("vertAlign")).set(w_tag("val"), "superscript")
    etree.SubElement(rpr, w_tag("noProof"))
    ref = etree.SubElement(run, w_tag("footnoteReference"))
    ref.set(w_tag("id"), str(fid))
    return run


def _new_amended_paragraph(text: str) -> etree._Element:
    paragraph = etree.Element(w_tag("p"))
    run = etree.SubElement(paragraph, w_tag("r"))
    text_node = etree.SubElement(run, w_tag("t"))
    text_node.text = text
    return paragraph


def _append_new_footnote(
    footnotes_root: etree._Element,
    *,
    footnote_text: str,
) -> int:
    footnote_text = _sanitize_footnote_plain_text(footnote_text)
    new_id = _next_footnote_id(footnotes_root)
    footnote_text = _normalize_new_footnote_citation_text(
        footnote_text,
        footnotes_root=footnotes_root,
        current_footnote_id=new_id,
    )
    nodes_by_id = _iter_footnote_nodes_by_id(footnotes_root)
    template_paras = _template_paragraphs_for_new_footnote(nodes_by_id, new_id)
    if not template_paras:
        raise ValueError("Cannot add a new footnote because the source DOCX has no footnote template paragraphs.")

    search_map = _build_footnote_search_text_map(footnotes_root)
    case_map = _build_footnote_case_reference_map(footnotes_root)
    new_node = _build_new_footnote_from_template(
        new_id,
        [_new_amended_paragraph(footnote_text)],
        template_paras,
        markup=True,
        rewrite_crossrefs=True,
        force_full_replace=False,
        footnote_search_text_by_id=search_map,
        case_reference_names_by_footnote=case_map,
    )
    footnotes_root.append(new_node)
    return new_id


def _replace_existing_footnote_text(
    footnotes_root: etree._Element,
    *,
    footnote_id: int,
    new_text: str,
) -> bool:
    new_text = _sanitize_footnote_plain_text(new_text)
    new_text = _normalize_new_footnote_citation_text(
        new_text,
        footnotes_root=footnotes_root,
        current_footnote_id=footnote_id,
    )
    nodes_by_id = _iter_footnote_nodes_by_id(footnotes_root)
    current_node = nodes_by_id.get(footnote_id)
    if current_node is None:
        raise ValueError(f"Cannot correct footnote {footnote_id}: ID not found in DOCX.")
    current_text = _sanitize_footnote_plain_text(
        " ".join(_paragraph_text_all_runs(p) for p in current_node.xpath("./w:p", namespaces=NS))
    ).strip()
    if current_text == new_text.strip():
        return False

    template_paras = current_node.xpath("./w:p", namespaces=NS)
    if not template_paras:
        template_paras = _template_paragraphs_for_new_footnote(nodes_by_id, footnote_id)

    search_map = _build_footnote_search_text_map(footnotes_root)
    case_map = _build_footnote_case_reference_map(footnotes_root)
    replacement_node = _build_new_footnote_from_template(
        footnote_id,
        [_new_amended_paragraph(new_text)],
        template_paras,
        markup=True,
        rewrite_crossrefs=False,
        force_full_replace=False,
        footnote_search_text_by_id=search_map,
        case_reference_names_by_footnote=case_map,
    )

    parent = current_node.getparent()
    if parent is None:
        raise ValueError(f"Cannot replace footnote {footnote_id}: node has no parent.")
    idx = list(parent).index(current_node)
    parent.remove(current_node)
    parent.insert(idx, replacement_node)
    return True


def _apply_paragraph_replacements(doc_root: etree._Element, items: list[dict[str, Any]]) -> int:
    paragraphs = _iter_body_paragraphs(doc_root)
    changed = 0
    for item in items:
        paragraph = _match_body_paragraph(
            paragraphs,
            paragraph_prefix=item.get("paragraph_prefix"),
            paragraph_index=item.get("paragraph_index"),
            occurrence=int(item.get("occurrence", 1)),
        )
        old = item.get("old")
        new = item.get("new")
        if not isinstance(old, str) or not isinstance(new, str):
            raise ValueError("inline_replacements and sentence_replacements require string 'old' and 'new' values.")
        if _replace_exact_text_in_paragraph(paragraph, old=old, new=new):
            changed += 1
    return changed


def _apply_paragraph_appends(doc_root: etree._Element, items: list[dict[str, Any]]) -> int:
    paragraphs = _iter_body_paragraphs(doc_root)
    changed = 0
    for item in items:
        paragraph = _match_body_paragraph(
            paragraphs,
            paragraph_prefix=item.get("paragraph_prefix"),
            paragraph_index=item.get("paragraph_index"),
            occurrence=int(item.get("occurrence", 1)),
        )
        text = item.get("text")
        if not isinstance(text, str):
            raise ValueError("paragraph_appends require string 'text' values.")
        if _append_text_to_paragraph(paragraph, text):
            changed += 1
    return changed


def _apply_sentence_insertions(doc_root: etree._Element, items: list[dict[str, Any]]) -> int:
    paragraphs = _iter_body_paragraphs(doc_root)
    changed = 0
    for item in items:
        paragraph = _match_body_paragraph(
            paragraphs,
            paragraph_prefix=item.get("paragraph_prefix"),
            paragraph_index=item.get("paragraph_index"),
            occurrence=int(item.get("occurrence", 1)),
        )
        anchor = item.get("after_sentence") or item.get("sentence")
        text = item.get("text")
        if not isinstance(anchor, str) or not isinstance(text, str):
            raise ValueError("sentence_appends require string 'after_sentence'/'sentence' and 'text' values.")
        if _insert_text_after_anchor(paragraph, anchor=anchor, text=text):
            changed += 1
    return changed


def _apply_new_paragraphs(doc_root: etree._Element, items: list[dict[str, Any]]) -> int:
    paragraphs = _iter_body_paragraphs(doc_root)
    changed = 0
    for item in items:
        paragraph = _match_body_paragraph(
            paragraphs,
            paragraph_prefix=item.get("after_prefix"),
            paragraph_index=item.get("paragraph_index"),
            occurrence=int(item.get("occurrence", 1)),
        )
        text = item.get("text")
        if not isinstance(text, str):
            raise ValueError("new_paragraphs_after require string 'text' values.")

        parent, idx = _match_paragraph_index_in_parent(paragraph)
        new_paragraph = _clone_paragraph_for_insertion(paragraph, text)
        parent.insert(idx + 1, new_paragraph)
        paragraphs = _iter_body_paragraphs(doc_root)
        changed += 1
    return changed


def _apply_conclusion_replacement(doc_root: etree._Element, value: dict[str, Any]) -> int:
    if not value:
        return 0
    old_prefixes = _string_list(value.get("old_prefixes"))
    new_paragraphs = _string_list(value.get("new_paragraphs"))
    if not old_prefixes or not new_paragraphs:
        raise ValueError("conclusion_replacement requires 'old_prefixes' and 'new_paragraphs'.")

    body_paragraphs = _iter_body_paragraphs(doc_root)
    targets = [
        _match_body_paragraph(body_paragraphs, paragraph_prefix=prefix, occurrence=1)
        for prefix in old_prefixes
    ]
    first_parent, first_idx = _match_paragraph_index_in_parent(targets[0])
    template = targets[0]

    for paragraph in targets:
        parent, idx = _match_paragraph_index_in_parent(paragraph)
        if parent is not first_parent:
            raise ValueError("conclusion_replacement paragraphs must share the same parent container.")
        parent.remove(paragraph)
        if idx < first_idx:
            first_idx = idx

    insert_at = first_idx
    for text in new_paragraphs:
        new_paragraph = _clone_paragraph_for_insertion(template, text)
        first_parent.insert(insert_at, new_paragraph)
        insert_at += 1
    return len(new_paragraphs)


def _apply_new_authorities(
    doc_root: etree._Element,
    footnotes_root: Optional[etree._Element],
    items: list[dict[str, Any]],
    *,
    default_kind: str = "footnote",
) -> int:
    paragraphs = _iter_body_paragraphs(doc_root)
    changed = 0

    for item in items:
        paragraph = _match_body_paragraph(
            paragraphs,
            paragraph_prefix=item.get("paragraph_prefix"),
            paragraph_index=item.get("paragraph_index"),
            occurrence=int(item.get("occurrence", 1)),
        )
        sentence = item.get("sentence") or item.get("after_sentence")
        if not isinstance(sentence, str):
            raise ValueError("new_authorities_after_sentences require string 'sentence' or 'after_sentence' values.")

        paragraph_text = _paragraph_text_all_runs(paragraph)
        start = _ensure_unique_substring(paragraph_text, sentence, label="sentence")
        insert_at = start + len(sentence)
        citation_mode = str(item.get("kind") or default_kind).strip().lower()

        if citation_mode in {"inline", "parenthetical"}:
            citation_text = item.get("citation_text") or item.get("footnote_text")
            if not isinstance(citation_text, str):
                raise ValueError("Inline authority insertion requires 'citation_text' or 'footnote_text'.")
            formatted = citation_text.strip()
            if formatted and not formatted.startswith("("):
                formatted = f" ({formatted})"
            if _insert_text_after_anchor(paragraph, anchor=sentence, text=formatted):
                changed += 1
            continue

        if citation_mode != "footnote":
            raise ValueError(f"Unsupported authority insertion kind: {citation_mode!r}")
        if footnotes_root is None:
            raise ValueError("Cannot add a new footnote authority because the source DOCX has no footnotes.xml part.")

        footnote_text = item.get("footnote_text") or item.get("citation_text")
        if not isinstance(footnote_text, str):
            raise ValueError("Footnote authority insertion requires 'footnote_text' or 'citation_text'.")

        new_id = _append_new_footnote(footnotes_root, footnote_text=footnote_text)
        ref_run = _make_footnote_reference_run(new_id)
        paragraph.insert(_reference_insert_index_for_text_pos(paragraph, insert_at), ref_run)
        changed += 1

    return changed


def _infer_reference_presentation_style(source: Path) -> str:
    if _extract_footnote_ids(source):
        return "footnotes"
    return "parenthetical"


def apply_amendments(
    *,
    source: Path,
    output: Path,
    config: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    _require_markup_enabled(True)
    _require_desktop_root_output(output)
    _require_default_amend_quality_context(source, config.get("review_context") or {}, config)
    doc_root = _load_docx_xml(source, "word/document.xml")
    doc_template = _load_docx_xml(source, "word/document.xml")
    footnotes_root = _load_docx_xml_if_exists(source, "word/footnotes.xml")
    footnotes_template = _load_docx_xml_if_exists(source, "word/footnotes.xml")
    original_footnote_ids = (
        {int(fid) for fid in _extract_footnote_ids_from_root(footnotes_template)}
        if footnotes_template is not None
        else set()
    )

    changed = 0
    changed += _apply_paragraph_replacements(doc_root, list(config.get("inline_replacements") or []))
    changed += _apply_paragraph_replacements(doc_root, list(config.get("sentence_replacements") or []))
    changed += _apply_paragraph_appends(doc_root, list(config.get("paragraph_appends") or []))
    changed += _apply_sentence_insertions(doc_root, list(config.get("sentence_appends") or []))
    changed += _apply_new_paragraphs(doc_root, list(config.get("new_paragraphs_after") or []))
    changed += _apply_conclusion_replacement(doc_root, dict(config.get("conclusion_replacement") or {}))
    default_authority_kind = "parenthetical" if _infer_reference_presentation_style(source) == "parenthetical" else "footnote"
    changed += _apply_new_authorities(
        doc_root,
        footnotes_root,
        list(config.get("new_authorities_after_sentences") or []),
        default_kind=default_authority_kind,
    )
    changed += _apply_new_authorities(
        doc_root,
        footnotes_root,
        list(config.get("inline_authorities_after_sentences") or []),
        default_kind="inline",
    )
    changed += _apply_new_authorities(
        doc_root,
        footnotes_root,
        list(config.get("parenthetical_authorities_after_sentences") or []),
        default_kind="parenthetical",
    )

    footnote_corrections = config.get("footnote_corrections") or {}
    if not isinstance(footnote_corrections, dict):
        raise ValueError("'footnote_corrections' must be a JSON object keyed by footnote id.")
    if footnote_corrections and footnotes_root is None:
        raise ValueError("Config contains footnote corrections, but the source DOCX has no footnotes.xml part.")
    for raw_id, new_text in sorted(footnote_corrections.items(), key=lambda item: int(item[0])):
        if not isinstance(new_text, str):
            raise ValueError("Each footnote correction value must be a string.")
        changed += 1 if _replace_existing_footnote_text(footnotes_root, footnote_id=int(raw_id), new_text=new_text) else 0

    corrected_footnote_ids = {int(raw_id) for raw_id in footnote_corrections}
    added_footnote_ids = (
        {int(fid) for fid in _extract_footnote_ids_from_root(footnotes_root)} - original_footnote_ids
        if footnotes_root is not None
        else set()
    )
    downstream_changed_footnote_ids: set[int] = set()
    affected_footnote_ids = corrected_footnote_ids | added_footnote_ids
    if footnotes_root is not None and affected_footnote_ids:
        downstream_changed_footnote_ids = _normalize_downstream_footnote_citations(
            footnotes_root,
            start_footnote_id=min(affected_footnote_ids),
        )
        changed += len(downstream_changed_footnote_ids)
    _lint_amended_footnote_citations(
        footnotes_root,
        corrected_ids=corrected_footnote_ids | downstream_changed_footnote_ids,
        added_ids=added_footnote_ids,
    )

    review_context = config.get("review_context") or {}
    _enforce_default_structured_verification_requirements(source, review_context, config)
    has_benchmark = bool(
        str(review_context.get("question") or "").strip() or str(review_context.get("rubric") or "").strip()
    )
    authority_truth_mode = str(review_context.get("authority_truth_check_mode") or "").strip().casefold()
    authority_report_path_raw = config.get("authority_verification_report_path")
    if authority_truth_mode and authority_truth_mode not in AUTOMATIC_AUTHORITY_TRUTH_MODES:
        raise ValueError(
            "Automatic authority verification failed: unsupported authority_truth_check_mode. "
            f"Use one of: {sorted(AUTOMATIC_AUTHORITY_TRUTH_MODES)}."
        )
    if authority_truth_mode and (not isinstance(authority_report_path_raw, str) or not authority_report_path_raw.strip()):
        raise ValueError(
            "Automatic authority verification failed: authority_truth_check_mode requires "
            "'authority_verification_report_path'."
        )
    if isinstance(authority_report_path_raw, str) and authority_report_path_raw.strip():
        _validate_authority_verification_report(
            Path(authority_report_path_raw).expanduser().resolve(),
            footnote_ids=(
                {int(fid) for fid in _extract_footnote_ids_from_root(footnotes_root)}
                if footnotes_root is not None
                else set()
            ),
            bibliography_count=_count_bibliography_entries(source),
        )

    sentence_support_mode = str(
        review_context.get("sentence_support_check_mode")
        or review_context.get("argumentative_sentence_support_mode")
        or ""
    ).strip().casefold()
    sentence_support_report_path_raw = (
        config.get("sentence_support_report_path") or config.get("argumentative_sentence_support_report_path")
    )
    if sentence_support_mode and sentence_support_mode not in AUTOMATIC_SENTENCE_SUPPORT_MODES:
        raise ValueError(
            "Automatic sentence-support verification failed: unsupported sentence_support_check_mode. "
            f"Use one of: {sorted(AUTOMATIC_SENTENCE_SUPPORT_MODES)}."
        )
    if sentence_support_mode and (
        not isinstance(sentence_support_report_path_raw, str) or not sentence_support_report_path_raw.strip()
    ):
        raise ValueError(
            "Automatic sentence-support verification failed: sentence_support_check_mode requires "
            "'sentence_support_report_path'."
        )
    if isinstance(sentence_support_report_path_raw, str) and sentence_support_report_path_raw.strip():
        _validate_sentence_support_report(Path(sentence_support_report_path_raw).expanduser().resolve())

    question_guidance_mode = str(review_context.get("question_guidance_mode") or "").strip().casefold()
    question_guidance_report_path_raw = config.get("question_guidance_report_path")
    if question_guidance_mode and question_guidance_mode not in QUESTION_GUIDANCE_MODES:
        raise ValueError(
            "Question guidance validation failed: unsupported question_guidance_mode. "
            f"Use one of: {sorted(QUESTION_GUIDANCE_MODES)}."
        )
    if question_guidance_mode and not has_benchmark:
        raise ValueError(
            "Question guidance validation failed: question_guidance_mode requires a question or rubric in review_context."
        )
    if question_guidance_mode and (
        not isinstance(question_guidance_report_path_raw, str) or not question_guidance_report_path_raw.strip()
    ):
        raise ValueError(
            "Question guidance validation failed: question_guidance_mode requires 'question_guidance_report_path'."
        )
    if isinstance(question_guidance_report_path_raw, str) and question_guidance_report_path_raw.strip():
        _validate_question_guidance_report(Path(question_guidance_report_path_raw).expanduser().resolve())

    parts_to_write: dict[str, etree._Element] = {"word/document.xml": doc_root}
    if footnotes_root is not None:
        if footnotes_template is not None:
            style_fixed = _normalize_footnote_styles_from_original(footnotes_template, footnotes_root)
            changed += style_fixed
        italicized = _normalize_case_italics_in_footnotes(footnotes_root)
        changed += italicized
        parts_to_write["word/footnotes.xml"] = footnotes_root

    body_ref_style_fixed = _normalize_body_footnote_reference_styles_from_original(doc_template, doc_root)
    body_refs_fixed = _normalize_body_footnote_reference_positions(doc_root, footnotes_root)
    body_italics_fixed = _normalize_body_italics(
        doc_root,
        footnotes_root,
    )
    changed += body_refs_fixed + body_italics_fixed
    parts_to_write["word/document.xml"] = doc_root

    _assert_original_footnotes_preserved_if_relevant(
        original_doc_root=doc_template,
        amended_doc_root=doc_root,
        original_footnotes_root=footnotes_template,
        amended_footnotes_root=footnotes_root,
        explicitly_corrected_ids={int(raw_id) for raw_id in footnote_corrections},
    )
    _enforce_review_context_word_count(
        source=source,
        amended_doc_root=doc_root,
        review_context=review_context,
    )

    _write_docx_with_replaced_parts(source, output, parts_to_write)
    _assert_markup_detectable(source, output, changed)
    _cleanup_embedded_one_off_artifacts(
        config,
        protected_paths=[source, output],
    )
    return changed, config.get("review_context") or {}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Apply structured sentence-level, paragraph-level, footnote, and new-authority amendments "
            "to a DOCX while preserving original styling."
        )
    )
    parser.add_argument("--source", type=Path, required=True, help="Path to the original source DOCX.")
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Requested amended output DOCX path. The amend flow always writes to a protected "
            "Desktop final path for the source (<source>_amended_marked_final.docx, then _v2, "
            "_v3, etc. if prior amended finals already exist). Any other requested filename is "
            "normalized back to that Desktop output policy. The original source DOCX is never overwritten."
        ),
    )
    parser.add_argument("--config", type=Path, required=True, help="Path to the JSON amendment config.")
    parser.add_argument("--question-file", type=Path, help="Optional question/prompt text file for review context.")
    parser.add_argument("--rubric-file", type=Path, help="Optional rubric/criteria text file for review context.")
    parser.add_argument("--based-on-comments", action="store_true", help="Extract comments and require config coverage.")
    parser.add_argument("--context-out", type=Path, help="Optional JSON path to write extracted question/rubric/comment context.")
    args = parser.parse_args(argv)

    requested_source = args.source.expanduser().resolve()
    config_path = args.config.expanduser().resolve()
    if not requested_source.exists():
        raise SystemExit(f"Source DOCX does not exist: {requested_source}")
    if requested_source.suffix.lower() != ".docx":
        raise SystemExit(f"Source must be a DOCX: {requested_source}")
    if not config_path.exists():
        raise SystemExit(f"Config does not exist: {config_path}")

    source = requested_source.expanduser().resolve()
    output, normalized_output = _normalize_to_final_output_path(requested_source, args.output)
    source, temp_source_dir = _copy_source_to_temp_if_same_as_output(source, output)
    _require_desktop_root_output(output)
    requested_output = output
    if normalized_output:
        print(f"[OUTPUT] Requested output path normalized to protected Desktop final DOCX: {requested_output}")

    try:
        config = _load_config(config_path)
        question_text = _read_optional_text_path(args.question_file.expanduser().resolve()) if args.question_file else None
        rubric_text = _read_optional_text_path(args.rubric_file.expanduser().resolve()) if args.rubric_file else None
        context = _build_context(
            source=source,
            config=config,
            question_text=question_text,
            rubric_text=rubric_text,
            based_on_comments=args.based_on_comments,
        )
        existing_review_context = config.get("review_context") or {}
        if existing_review_context and not isinstance(existing_review_context, dict):
            raise ValueError("'review_context' must be a JSON object when provided.")
        config["review_context"] = {**existing_review_context, **context}
        if args.context_out is not None:
            context_out = args.context_out.expanduser().resolve()
            context_out.write_text(json.dumps(context, indent=2, ensure_ascii=False), encoding="utf-8")

        changed, _ = apply_amendments(source=source, output=output, config=config)
    except Exception as exc:
        raise SystemExit(str(exc)) from exc
    finally:
        if temp_source_dir is not None:
            shutil.rmtree(temp_source_dir, ignore_errors=True)

    removed_one_off_artifacts = _cleanup_one_off_artifacts_after_amend(
        config=config,
        config_path=config_path,
        question_path=args.question_file.expanduser().resolve() if args.question_file is not None else None,
        rubric_path=args.rubric_file.expanduser().resolve() if args.rubric_file is not None else None,
        context_out_path=args.context_out.expanduser().resolve() if args.context_out is not None else None,
        source_path=source,
        output_path=output,
    )

    print(f"[amend] wrote {output}")
    print(f"[amend] changed items detected: {changed}")
    print(f"[amend] one-off artifacts cleaned: {removed_one_off_artifacts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
