"""
Regression checks for folder-derived subject-guide refinements.

These tests keep the local-material lessons as privacy-safe abstract rules in
the backend guide layer. They do not load private source files and do not call
live LLM APIs.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE_DIR = ROOT / "legal_doc_tools" / "law_guides"


def _guide(slug: str) -> str:
    return (GUIDE_DIR / f"{slug}.md").read_text(encoding="utf-8")


def test_folder_material_rules_are_present_in_subject_guides() -> None:
    expected = {
        "law_medicine": [
            "compulsory problem question plus one essay question",
            "section 5 General Legal Authority",
            "two or three examples in depth",
            "DBD/DCD",
            "Human Tissue Act 2004 section 1 requires appropriate consent",
            "full, limited or no moral status",
            "section 1(1)(a) social ground from section 1(1)(d)",
            "Schedule 3 consent",
            "DPP consent",
        ],
        "pensions_law": [
            "Define acronyms on first use",
            "Calculation questions need visible workings",
            "inaccurate pinpointing",
            "section 62 of the Pensions Act 1995 itself changes a normal retirement age",
            "Pensions Ombudsman determinations need their own authority discipline",
        ],
        "criminal_law": [
            "go straight into offence analysis",
            "injury, culpability, aggravating factors",
            "express/implied consent",
            "visible battery/ABH/GBH ladder",
            "same-crime limit",
        ],
        "contract_law": [
            "break the question into its actual sub-questions",
            "modern law genuinely clarifies earlier authority",
        ],
        "land_law": [
            "whether the land is registered",
            "who is being advised",
            "quotation or proposition",
            "Landlord and Tenant Act 1954",
            "official search with priority",
            "identify the legal issues, state the relevant legal principles",
        ],
        "tort_law": [
            "no-general-duty-to-act baseline",
            "operational negligence from failure to confer a public benefit",
            "serious-harm threshold",
        ],
        "private_international_law": [
            "three backbone questions",
            "Foreign mandatory-rule problems",
            "CPR 6.36/6.37 and PD6B gateway discipline",
            "front-end jurisdiction question from the back-end recognition",
        ],
        "mediation_law": [
            "binding law from soft-law instruments",
            "commercial relationship preservation",
            "critical mass",
            "default lex mediationis",
        ],
        "competition_law": [
            "which goal of competition law",
            "Article 102 problem answers should use this spine",
            "define the term",
            "Google Shopping analysis",
            "Bronner distinction",
            "Chapter II / section 18 Competition Act 1998 route",
            "default architecture",
        ],
        "evidence_law": [
            "PACE Code D",
            "Facial mapping",
            "CJPOA s 34",
        ],
        "biolaw_ai_data": [
            "research-led technology governance",
            "neuroscience and law",
            "artificial placenta technology",
        ],
        "commercial_law": [
            "business/commercial sales as the centre of gravity",
            "why the rule matters commercially",
        ],
        "trusts_law": [
            "Variation of Trusts Act 1958 approval",
            "Benjamin order",
            "Apply the law, do not just state it",
        ],
        "environmental_law": [
            "standing/proprietary interest -> private nuisance amenity harm",
            "Permits and substantial compliance are relevant evidence",
            "local authority investigation, abatement notice",
        ],
        "succession_wills": [
            "formal validity/due execution -> testamentary capacity",
            "Banks v Goodfellow",
            "golden rule is evidential best practice",
        ],
    }

    for slug, phrases in expected.items():
        text = _guide(slug)
        for phrase in phrases:
            assert phrase in text, (slug, phrase)


def test_every_subject_guide_has_strong_first_class_accuracy_pass() -> None:
    guide_files = sorted(
        path for path in GUIDE_DIR.glob("*.md")
        if path.name != "README.md"
    )
    assert guide_files, "No subject guides found"
    for path in guide_files:
        text = path.read_text(encoding="utf-8")
        assert "## Strong First-Class Accuracy Pass" in text, path.name
        assert "## Avoid" in text, path.name


if __name__ == "__main__":
    test_folder_material_rules_are_present_in_subject_guides()
    test_every_subject_guide_has_strong_first_class_accuracy_pass()
    print("Folder material guidance regression passed.")
