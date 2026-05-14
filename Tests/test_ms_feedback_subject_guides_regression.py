"""
Regression checks for subject-guide lessons abstracted from marked-solution
and reviewer-comment DOCX files.

The source DOCX comments are private working material. These checks verify only
the reusable, privacy-safe rules now carried by the backend subject guides.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDES = ROOT / "legal_doc_tools" / "law_guides"


def _guide(name: str) -> str:
    return (GUIDES / name).read_text(encoding="utf-8").lower()


def test_competition_ms_feedback_rules_present() -> None:
    text = _guide("competition_law.md")
    assert "ranking, default placement, interoperability" in text
    assert "self-preferencing must be tied to a concrete theory of harm" in text
    assert "excessive-pricing or discriminatory-pricing analysis needs cost, margin, comparator" in text
    assert "market definition must serve the abuse theory" in text
    assert "chapter ii / section 18 competition act 1998 route" in text
    assert "data-use, voice-recording, retention or one-sided access terms" in text
    assert "effects-based" in text
    assert "google shopping analysis" in text
    assert "bronner distinction should be central" in text


def test_private_international_law_ms_feedback_rules_present() -> None:
    text = _guide("private_international_law.md")
    assert "keep the introduction separate from the substantive parts" in text
    assert "define technical labels on first use" in text
    assert "do not present cases as detached snippets" in text
    assert "end each major section with the current position and litigation implication" in text
    assert "cpr 6.36/6.37 and pd6b gateway discipline" in text
    assert "company is not automatically present in england merely because a group company or subsidiary is present" in text


def test_mediation_ms_feedback_rules_present() -> None:
    text = _guide("mediation_law.md")
    assert "states sign, ratify, accede to, implement, or incorporate treaties" in text
    assert "private companies and commercial parties use the regime" in text
    assert "distinguish signature, ratification/accession, entry into force" in text
    assert "do not call soft-law notes, protocols, model clauses, or institutional guidance" in text
    assert "new york convention only as a benchmark" in text
    assert "article 5(1)(e)-style" in text


def test_pensions_ms_feedback_rules_present() -> None:
    text = _guide("pensions_law.md")
    assert "start non-financial investment answers with the scheme purpose" in text
    assert "member consensus must be informed" in text
    assert "db/dc status, employer covenant, member consultation evidence" in text
    assert "trustee impartiality matters where members are divided" in text
    assert "section 62 of the pensions act 1995 itself changes a normal retirement age" in text
    assert "palestine/local-government pension-fund line" in text


def test_biolaw_ms_feedback_rules_present() -> None:
    text = _guide("biolaw_ai_data.md")
    assert "avoid absolute or comparative claims unless the comparator and evidence are stated" in text
    assert "bias examples must explain the proxy, dataset, model" in text
    assert "thin one-paragraph sections should be merged or expanded" in text
    assert "comparative jurisdiction sections must explain the function of the comparison" in text


if __name__ == "__main__":
    test_competition_ms_feedback_rules_present()
    test_private_international_law_ms_feedback_rules_present()
    test_mediation_ms_feedback_rules_present()
    test_pensions_ms_feedback_rules_present()
    test_biolaw_ms_feedback_rules_present()
    print("MS feedback subject-guide regression passed.")
