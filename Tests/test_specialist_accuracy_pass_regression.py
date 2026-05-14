"""
Regression checks for strict first-class specialist accuracy tuning.

These checks lock in the final-pass rules that catch technical traps rather
than merely producing broadly correct legal summaries.
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


def _contract(prompt: str) -> str:
    profile = _infer_retrieval_profile(prompt)
    return "\n".join([
        _build_local_code_rag_answer_prompt_block(prompt, enforce_long_response_split=False),
        _build_legal_answer_quality_gate(prompt, profile),
    ]).lower()


def test_general_specialist_accuracy_pass_is_default_for_legal_answers() -> None:
    combined = _contract("Contract Law problem question on misrepresentation, exclusion clauses and remedies.")
    assert "[specialist accuracy pass" in combined
    assert "exact statutory gateway" in combined
    assert "procedural requirement" in combined
    assert "timing/date trap" in combined
    assert "strongest route, weakest route" in combined
    assert "define the central contested concept" in combined


def test_land_priority_traps_are_forced() -> None:
    combined = _contract(
        "Land Law registered priority problem: six-year business lease, actual occupation, "
        "purchase-price contribution, refinancing bank, driveway right, option and overreaching."
    )
    assert "landlord and tenant act 1954" in combined
    assert "resulting trust" in combined
    assert "registered charge" in combined
    assert "official search with priority" in combined
    assert "appointment and payment to two trustees must be valid" in combined


def test_evidence_procedural_traps_are_forced() -> None:
    combined = _contract(
        "Evidence Law problem: video identification after social media naming, facial mapping expert, "
        "confession after threats, silence, co-suspect hearsay and old burglary conviction."
    )
    assert "pace code d" in combined
    assert "transparent methodology" in combined
    assert "s 76(2)(b)" in combined
    assert "later fact relied on" in combined
    assert "co-defendant/non-defendant status" in combined


def test_article_102_current_digital_precision_is_forced() -> None:
    combined = _contract(
        "Competition Law Article 102 essay in 2026: critically evaluate whether Google Shopping, "
        "Bronner and the DMA show that digital platform abuse is now effects-based."
    )
    assert "actual effects, likely effects, capability" in combined
    assert "self-preferencing is not per se abusive" in combined
    assert "bronner indispensability" in combined
    assert "digital markets act" in combined
    assert "commission's first-guidelines process" in combined
    assert "[current-law / freshness gate]" in combined


if __name__ == "__main__":
    test_general_specialist_accuracy_pass_is_default_for_legal_answers()
    test_land_priority_traps_are_forced()
    test_evidence_procedural_traps_are_forced()
    test_article_102_current_digital_precision_is_forced()
    print("Specialist accuracy pass regression passed.")
