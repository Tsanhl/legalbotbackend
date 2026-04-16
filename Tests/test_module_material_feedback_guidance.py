"""
Regression checks for generalised guidance learned from module feedback/materials.

These assertions verify that the backend now carries the module-level lessons
as general subject guidance, rather than tying them to specific marked scripts.

The topic-specific guidance blocks currently live inside the runtime answer path
in ``send_message_with_docs(...)`` rather than the small local-code wrapper.
This regression therefore verifies the live source text plus the pensions
retrieval profile that is used at runtime.
"""

from pathlib import Path

from gemini_service import _infer_retrieval_profile


source = Path("gemini_service.py").read_text().lower()


# Private international law
assert "do not drift back into choice-of-law material" in source
assert "serious issue to be tried, good arguable case, proper place" in source
assert "hague 2005 and hague 2019 on first mention" in source or (
    "hague 2005" in source and "hague 2019" in source
)
assert "asymmetry between english jurisdiction-taking and restrictive recognition" in source


# International commercial mediation
assert "states ratify or accede to the convention" in source
assert "commercial parties do not" in source
assert "new york convention" in source
assert "applicable standards, serious breach, and causation/confidentiality" in source
assert "non-binding guidance rather than mediation rules" in source


# Law and medicine
assert "stay within the taught topic map" in source
assert "do not centre a consent answer on montgomery/negligence" in source
assert "e v northern care alliance" in source
assert "human tissue act 2004 s 32" in source


# Pensions retrieval profile and guidance
pensions_prompt = """Pensions Law — Problem Question

Employees challenge an occupational pension scheme amendment and allege misleading pension communications.

Advise them on accrued rights, amendment powers, trustee/employer duties, and remedies."""

pensions_profile = _infer_retrieval_profile(pensions_prompt)
assert pensions_profile["topic"] == "pensions_scheme_change_misrepresentation"
assert any("re courage group" in item.lower() for item in pensions_profile["must_cover"])
assert any("dalgleish" in item.lower() for item in pensions_profile["must_cover"])
assert any("barnardo" in item.lower() for item in pensions_profile["must_cover"])
assert int((pensions_profile.get("source_mix_min") or {}).get("cases", 0)) >= 5
assert any("section 67 as exhausting the amendment question" in item.lower() for item in pensions_profile["must_avoid"])
assert "amendment power, proper purpose, and good-faith/rationality review separate from section 67" in source


print("Module-material guidance regression passed.")
