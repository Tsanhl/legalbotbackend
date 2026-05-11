"""
Regression checks for split subject-guide loading.

These tests do not call live LLM APIs. They verify that prompts/profiles pull
the matching privacy-safe guide instead of relying only on generic legal rules.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_applicable_service import (
    _build_legal_answer_quality_gate,
    _build_local_code_rag_answer_prompt_block,
    _infer_retrieval_profile,
    _infer_subject_guide_slug,
    _subject_guide_excerpt_for_query,
)


CASES = [
    {
        "name": "competition_article_102",
        "prompt": "Competition Law essay: critically evaluate Article 102 abuse of dominance in digital markets, including self-preferencing and objective justification.",
        "slug": "competition_law",
        "snippet": "Article 102/Chapter II",
    },
    {
        "name": "pensions_amendment",
        "prompt": "Pensions Law problem question: advise on an occupational pension scheme amendment, section 67, Barber equalisation, trustee duties and employer good faith.",
        "slug": "pensions_law",
        "snippet": "scheme wording",
    },
    {
        "name": "law_medicine_hfea",
        "prompt": "Law and Medicine essay: is the HFEA framework fit for assisted reproduction, embryo consent, welfare of the child and saviour siblings?",
        "slug": "law_medicine",
        "snippet": "Course-bound mode is default",
    },
    {
        "name": "public_law_planning",
        "prompt": "Planning law essay: evaluate section 70(2), section 38(6), the NPPF, material considerations, conditions, reasons and judicial review.",
        "slug": "public_law",
        "snippet": "Planning-law prompts need",
    },
    {
        "name": "mediation_settlement",
        "prompt": "International commercial mediation essay: evaluate confidentiality, agreements to mediate, mandatory ADR, mediated settlement enforcement and the Singapore Convention.",
        "slug": "mediation_law",
        "snippet": "Singapore Convention",
    },
    {
        "name": "employment_restrictive_covenant",
        "prompt": "Employment law problem: advise on a senior employee's restrictive covenant, garden leave, unfair dismissal risk, worker status and employer remedies.",
        "slug": "employment_law",
        "snippet": "restraint of trade",
    },
    {
        "name": "tax_vat_supply",
        "prompt": "Tax law problem: advise on VAT, taxable supply, input tax, corporation tax and HMRC penalties.",
        "slug": "tax_law",
        "snippet": "VAT sequence",
    },
]


def test_subject_guide_slug_and_excerpt() -> None:
    for case in CASES:
        profile = _infer_retrieval_profile(case["prompt"])
        slug = _infer_subject_guide_slug(profile.get("topic", ""), case["prompt"])
        assert slug == case["slug"], (case["name"], profile.get("topic"), slug)
        excerpt = _subject_guide_excerpt_for_query(case["prompt"], profile)
        assert f"[SUBJECT GUIDE — {case['slug']}]" in excerpt
        assert case["snippet"] in excerpt


def test_quality_gate_includes_matching_subject_guide() -> None:
    prompt = CASES[0]["prompt"]
    profile = _infer_retrieval_profile(prompt)
    gate = _build_legal_answer_quality_gate(prompt, profile)
    assert "[SUBJECT GUIDE — competition_law]" in gate
    assert "Case Brief Bank" in gate
    assert "Avoid" in gate


def test_direct_code_prompt_includes_matching_subject_guide() -> None:
    block = _build_local_code_rag_answer_prompt_block(
        CASES[2]["prompt"] + " Use code guide and RAG.",
        enforce_long_response_split=False,
    )
    assert "Matched subject guide anchors:" in block
    assert "[SUBJECT GUIDE — law_medicine]" in block


def test_short_subject_keywords_do_not_false_match_inside_words() -> None:
    profile = _infer_retrieval_profile("Private law essay: discuss obligations, remedies and certainty.")
    slug = _infer_subject_guide_slug(profile.get("topic", ""), "Private law essay: discuss obligations, remedies and certainty.")
    assert slug != "tax_law"


if __name__ == "__main__":
    test_subject_guide_slug_and_excerpt()
    test_quality_gate_includes_matching_subject_guide()
    test_direct_code_prompt_includes_matching_subject_guide()
    test_short_subject_keywords_do_not_false_match_inside_words()
    print("Subject guide loader regression passed.")
