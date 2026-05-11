"""
Checks that subject guides use compact paraphrased case briefs.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE_DIR = ROOT / "legal_doc_tools" / "law_guides"


REQUIRED_GUIDES = [
    "law_medicine.md",
    "competition_law.md",
    "pensions_law.md",
    "private_international_law.md",
    "land_law.md",
    "trusts_law.md",
    "contract_law.md",
    "commercial_law.md",
    "criminal_law.md",
    "family_law.md",
    "tort_law.md",
    "eu_law.md",
    "public_international_law.md",
    "evidence_law.md",
    "tax_law.md",
    "intellectual_property_law.md",
    "biolaw_ai_data.md",
    "mediation_law.md",
    "public_law.md",
    "business_law.md",
    "employment_law.md",
]


def test_case_brief_banks_have_required_fields() -> None:
    for name in REQUIRED_GUIDES:
        text = (GUIDE_DIR / name).read_text(encoding="utf-8")
        assert "## Case Brief Bank" in text, name
        assert "Facts:" in text, name
        assert "Held:" in text, name
        assert "Reasoning:" in text, name
        assert "Answer use:" in text, name


def test_guides_use_common_answer_structure() -> None:
    for name in REQUIRED_GUIDES:
        text = (GUIDE_DIR / name).read_text(encoding="utf-8")
        for heading in [
            "## Answer Method",
            "## Topic Map",
            "## Material-Led Emphasis",
            "## For Each Topic Include",
            "## Case Brief Bank",
            "## Feedback Rules",
            "## Avoid",
        ]:
            assert heading in text, (name, heading)


def test_identified_weak_guides_are_now_strengthened() -> None:
    for name in ["tax_law.md", "evidence_law.md", "mediation_law.md"]:
        text = (GUIDE_DIR / name).read_text(encoding="utf-8")
        word_count = len(text.split())
        case_count = sum(
            1
            for line in text.splitlines()
            if line.lstrip().startswith("- ") and "Facts:" in line and "Held:" in line
        )
        assert word_count >= 500, (name, word_count)
        assert case_count >= 8, (name, case_count)


if __name__ == "__main__":
    test_case_brief_banks_have_required_fields()
    test_guides_use_common_answer_structure()
    print("Case brief bank regression passed.")
