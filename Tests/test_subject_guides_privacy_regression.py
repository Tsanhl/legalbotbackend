"""
Privacy checks for generated subject guides and injected guide excerpts.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_applicable_service import _infer_retrieval_profile, _subject_guide_excerpt_for_query


GUIDE_DIR = ROOT / "legal_doc_tools" / "law_guides"
BLOCKED = [
    "/Users/",
    "\\Users\\",
    Path.home().name,
    "LAW" + "3071",
    "Dur" + "ham",
]


def test_subject_guides_do_not_store_private_identifiers() -> None:
    guide_files = sorted(GUIDE_DIR.glob("*.md"))
    assert guide_files
    for path in guide_files:
        text = path.read_text(encoding="utf-8")
        for token in BLOCKED:
            assert token not in text, (path.name, token)


def test_injected_subject_guide_excerpts_are_privacy_safe() -> None:
    prompt = "Law and Medicine essay about consent, capacity, refusal and end of life."
    profile = _infer_retrieval_profile(prompt)
    excerpt = _subject_guide_excerpt_for_query(prompt, profile)
    assert excerpt
    for token in BLOCKED:
        assert token not in excerpt


if __name__ == "__main__":
    test_subject_guides_do_not_store_private_identifiers()
    test_injected_subject_guide_excerpts_are_privacy_safe()
    print("Subject guide privacy regression passed.")
