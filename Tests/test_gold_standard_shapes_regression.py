"""
Regression checks for internal-only gold-standard output shapes.

The files are QA benchmarks derived from private course/feedback materials.
They must remain privacy-safe and must not be injected into user-facing answer
prompts.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_applicable_service import (  # noqa: E402
    _build_legal_answer_quality_gate,
    _build_local_code_rag_answer_prompt_block,
    _infer_retrieval_profile,
)


SHAPE_DIR = ROOT / "legal_doc_tools" / "gold_standard_shapes"


def _shape(name: str) -> str:
    return (SHAPE_DIR / name).read_text(encoding="utf-8")


def test_gold_standard_shapes_exist_and_are_privacy_safe() -> None:
    required = {
        "README.md": ["Internal QA only", "must not be copied into generated user answers", "Law and Medicine", "Competition Article 102"],
        "law_medicine.md": ["Course-Bound", "No-Syllabus-Limit", "governing legal route", "Does not drift"],
        "competition_law.md": ["Article 102", "self-preferencing", "objective justification", "foreclosure"],
        "land_law.md": ["registered land", "actual occupation", "overreaching", "right-by-right"],
        "trusts_law.md": ["beneficiary principle", "secret trust", "mixed fund", "proprietary remedies"],
        "business_law.md": ["Director Conflict", "related-party", "majority shareholding", "insolvency"],
        "evidence_law.md": ["classifies evidence", "statutory gateway", "Article 6", "likely ruling"],
        "public_law.md": ["power source", "legitimate expectation", "proportionality", "discretionary"],
        "pensions_law.md": ["NRA", "visible workings", "non-financial investment", "member consensus", "employer covenant"],
        "mediation_law.md": ["Singapore Convention", "Article 5", "critical mass", "enforceability gap", "confidentiality"],
    }
    blocked = ["/Users/", "\\Users\\", Path.home().name, "LAW" + "3071", "Dur" + "ham"]

    for filename, phrases in required.items():
        text = _shape(filename)
        text_low = text.lower()
        for phrase in phrases:
            assert phrase.lower() in text_low, (filename, phrase)
        for token in blocked:
            assert token not in text, (filename, token)


def test_gold_standard_shapes_are_not_prompt_injected() -> None:
    prompts = [
        "Law and Medicine course-bound essay on HFEA, welfare of the child and reproductive autonomy.",
        "Competition Law Article 102 problem on platform self-preferencing and objective justification.",
        "Land Law registered priority problem with actual occupation and overreaching.",
        "Trusts Law problem on secret trusts, purpose trusts and mixed-fund tracing.",
        "Company Law problem on director conflict, substantial property transaction and insolvency.",
        "Evidence Law problem on hearsay, confession, bad character and expert evidence.",
        "Public Law problem on legitimate expectation, reasons and proportionality.",
        "Pensions Law problem on NRA equalisation, Barber timing, section 67, commutation factors and calculations.",
        "International commercial mediation essay on the Singapore Convention, Article 5 mediator misconduct and critical mass.",
    ]
    for prompt in prompts:
        profile = _infer_retrieval_profile(prompt)
        combined = "\n".join([
            _build_local_code_rag_answer_prompt_block(prompt, enforce_long_response_split=False),
            _build_legal_answer_quality_gate(prompt, profile),
        ])
        assert "Gold Standard Output Shapes" not in combined
        assert "Internal QA only" not in combined
        assert "Do not copy this wording into user answers" not in combined


if __name__ == "__main__":
    test_gold_standard_shapes_exist_and_are_privacy_safe()
    test_gold_standard_shapes_are_not_prompt_injected()
    print("Gold-standard shape regression passed.")
