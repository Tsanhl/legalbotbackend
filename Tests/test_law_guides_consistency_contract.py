from __future__ import annotations

import re
from pathlib import Path

from model_applicable_service import SUBJECT_GUIDE_KEYWORDS, SUBJECT_GUIDE_TOPIC_PREFIXES


ROOT = Path(__file__).resolve().parents[1]
GUIDE_DIR = ROOT / "legal_doc_tools" / "law_guides"


GUIDE_FILES = sorted(
    path for path in GUIDE_DIR.glob("*.md")
    if path.name != "README.md"
)


BANNED_GUIDE_PATTERNS = {
    r"\bdo\s+not\s+use\s+rag\b": "guide cannot suppress indexed RAG",
    r"\bignore\s+rag\b": "guide cannot suppress indexed RAG",
    r"\bskip\s+rag\b": "guide cannot suppress indexed RAG",
    r"\bwithout\s+rag\b": "guide cannot suppress indexed RAG",
    r"\bdo\s+not\s+search\b": "guide cannot suppress online/search fallback",
    r"\bdo\s+not\s+use\s+online\b": "guide cannot suppress online/search fallback",
    r"\bnever\s+use\s+online\b": "guide cannot suppress online/search fallback",
    r"\bavoid\s+online\s+search\b": "guide cannot suppress online/search fallback",
    r"\bdo\s+not\s+use\s+search\b": "guide cannot suppress online/search fallback",
    r"\bdo\s+not\s+fact[-\s]?check\b": "guide cannot suppress final/current-law verification",
    r"\bsummary\s+only\b": "guide cannot force condensed answer output",
    r"\bbrief\s+answer\s+only\b": "guide cannot force condensed answer output",
    r"\bshort\s+answer\s+only\b": "guide cannot force condensed answer output",
    r"\bno\s+citations\b": "guide cannot suppress authority support",
    r"\bdo\s+not\s+use\s+authorit(?:y|ies)\b": "guide cannot suppress authority support",
    r"/Users/|Desktop/|Law resources": "guide must not leak local source paths",
}


ALLOWED_PATTERN_CONTEXTS = (
    "Do not cite Article 6 as a free-standing override before applying the domestic statutory route.",
)


def _strip_allowed_contexts(text: str) -> str:
    cleaned = text
    for allowed in ALLOWED_PATTERN_CONTEXTS:
        cleaned = cleaned.replace(allowed, "")
    return cleaned


def test_all_subject_guides_have_required_quality_sections() -> None:
    assert len(GUIDE_FILES) >= 40
    missing = []
    for path in GUIDE_FILES:
        text = path.read_text(encoding="utf-8")
        for heading in ("## Answer Method", "## Strong First-Class Accuracy Pass", "## Avoid"):
            if heading not in text:
                missing.append(f"{path.name}: missing {heading}")
    assert not missing


def test_subject_guides_do_not_contradict_backend_rag_search_quality_route() -> None:
    violations = []
    for path in GUIDE_FILES:
        text = _strip_allowed_contexts(path.read_text(encoding="utf-8"))
        for pattern, reason in BANNED_GUIDE_PATTERNS.items():
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append(f"{path.name}: {reason}: /{pattern}/")
    assert not violations


def test_every_subject_guide_is_reachable_and_every_mapping_exists() -> None:
    guide_slugs = {path.stem for path in GUIDE_FILES}
    keyword_slugs = {slug for slug, _keywords in SUBJECT_GUIDE_KEYWORDS}
    prefix_slugs = {slug for _prefix, slug in SUBJECT_GUIDE_TOPIC_PREFIXES}
    mapped_slugs = keyword_slugs | prefix_slugs

    assert not sorted(guide_slugs - mapped_slugs)
    assert not sorted(mapped_slugs - guide_slugs)


def test_subject_guides_are_not_stub_depth() -> None:
    too_short = []
    for path in GUIDE_FILES:
        lines = [
            line for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(lines) < 35:
            too_short.append(f"{path.name}: only {len(lines)} nonblank lines")
    assert not too_short


def test_subject_guides_keep_problem_and_essay_quality_signals() -> None:
    missing = []
    for path in GUIDE_FILES:
        text = path.read_text(encoding="utf-8").lower()
        if not any(term in text for term in ("problem", "advise", "essay", "thesis", "evaluate")):
            missing.append(f"{path.name}: missing answer-form signal")
        if not any(term in text for term in ("remedy", "remedies", "outcome", "relief", "sanction", "sentence", "conclusion")):
            missing.append(f"{path.name}: missing remedy/outcome signal")
        if not any(term in text for term in ("strong first-class accuracy pass", "current", "verify", "check", "update-sensitive", "latest")):
            missing.append(f"{path.name}: missing current-law/final-check signal")
    assert not missing


if __name__ == "__main__":
    test_all_subject_guides_have_required_quality_sections()
    test_subject_guides_do_not_contradict_backend_rag_search_quality_route()
    test_every_subject_guide_is_reachable_and_every_mapping_exists()
    test_subject_guides_are_not_stub_depth()
    test_subject_guides_keep_problem_and_essay_quality_signals()
    print("Law guide consistency contract passed.")
