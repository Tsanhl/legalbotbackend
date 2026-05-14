"""
Regression checks for backend answer-quality contracts.

These tests do not call a live model. They verify that the backend prompt layer
keeps first-class answer instructions, topic-specific rubrics, drift guards and
privacy boundaries intact.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend_answer_runtime import build_sqe2_marking_prompt, build_sqe_question_set_prompt  # noqa: E402
from legal_answer_quality_controls import ANTI_GENERIC_QUALITY_RULES  # noqa: E402
from model_applicable_service import (  # noqa: E402
    _build_active_citation_style_override,
    _build_active_citation_style_quality_gate,
    _build_active_citation_style_reminder,
    _build_legal_answer_quality_gate,
    _build_local_code_rag_answer_prompt_block,
    _detect_requested_citation_style,
    _infer_retrieval_profile,
    _infer_subject_guide_slug,
)


PRIVATE_OR_INTERNAL_MARKERS = (
    "/Users/",
    "\\Users\\",
    "Gold Standard Output Shapes",
    "Internal QA only",
    "Do not copy this wording into user answers",
    "Dur" + "ham",
    "LAW" + "3071",
)

SUBJECT_CASES = (
    {
        "name": "law_medicine_course",
        "prompt": "Law and Medicine course-bound essay: stay within the module syllabus and critically examine HFEA reform in 2026.",
        "slug": "law_medicine",
        "template": "[SUBJECT TEMPLATE — LAW AND MEDICINE]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — LAW AND MEDICINE]",
        "freshness": True,
    },
    {
        "name": "competition_article_102",
        "prompt": "Competition Law Article 102 digital platform self-preferencing problem: advise on dominance, foreclosure, effects and objective justification in 2026.",
        "slug": "competition_law",
        "template": "[SUBJECT TEMPLATE — COMPETITION LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — COMPETITION LAW]",
        "freshness": True,
    },
    {
        "name": "pensions",
        "prompt": "Pensions Law problem on DB scheme amendment, section 67, Barber equalisation, trustee duties and member communications.",
        "slug": "pensions_law",
        "template": "[SUBJECT TEMPLATE — PENSIONS LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — PENSIONS LAW]",
        "freshness": False,
    },
    {
        "name": "mediation",
        "prompt": "International commercial mediation essay on the Singapore Convention, confidentiality, Article 5 and agreements to mediate.",
        "slug": "mediation_law",
        "template": "[SUBJECT TEMPLATE — MEDIATION]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — MEDIATION]",
        "freshness": False,
    },
    {
        "name": "land",
        "prompt": "Land Law problem on registered land priority, actual occupation, overreaching, an option and an easement.",
        "slug": "land_law",
        "template": "[SUBJECT TEMPLATE — LAND LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — LAND LAW]",
        "freshness": False,
    },
    {
        "name": "trusts",
        "prompt": "Trusts Law problem on secret trusts, private purpose trusts, certainty, mixed-fund tracing and proprietary remedies.",
        "slug": "trusts_law",
        "template": "[SUBJECT TEMPLATE — EQUITY / TRUSTS]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — EQUITY / TRUSTS]",
        "freshness": False,
    },
    {
        "name": "business",
        "prompt": "Company Law problem on director conflict, substantial property transaction, minority remedies and insolvency office-holder claims.",
        "slug": "business_law",
        "template": "[SUBJECT TEMPLATE — BUSINESS / COMPANY LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — BUSINESS / COMPANY LAW]",
        "freshness": False,
    },
    {
        "name": "evidence",
        "prompt": "Evidence Law problem on hearsay, bad character, confession, identification, expert evidence and Article 6 fairness.",
        "slug": "evidence_law",
        "template": "[SUBJECT TEMPLATE — EVIDENCE LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — EVIDENCE LAW]",
        "freshness": False,
    },
    {
        "name": "public",
        "prompt": "Public Law problem on legitimate expectation, improper purpose, proportionality, reasons and judicial review remedies.",
        "slug": "public_law",
        "template": "[SUBJECT TEMPLATE — PUBLIC LAW / JUDICIAL REVIEW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — PUBLIC LAW / JUDICIAL REVIEW]",
        "freshness": False,
    },
    {
        "name": "criminal",
        "prompt": "Criminal Law problem on non-fatal offences, sports consent, causation and transferred malice.",
        "slug": "criminal_law",
        "template": "[SUBJECT TEMPLATE — CRIMINAL LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — CRIMINAL LAW]",
        "freshness": False,
    },
    {
        "name": "tort",
        "prompt": "Tort Law problem on psychiatric harm, public authority omission, causation, defences and damages.",
        "slug": "tort_law",
        "template": "[SUBJECT TEMPLATE — TORT LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — TORT LAW]",
        "freshness": False,
    },
    {
        "name": "contract",
        "prompt": "Contract Law problem on misrepresentation, exclusion clauses, repudiatory breach, damages and rescission.",
        "slug": "contract_law",
        "template": "[SUBJECT TEMPLATE — CONTRACT LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — CONTRACT LAW]",
        "freshness": False,
    },
    {
        "name": "commercial",
        "prompt": "Commercial Law problem on sale of goods, nemo dat, retention of title, risk and insolvency priority.",
        "slug": "commercial_law",
        "template": "[SUBJECT TEMPLATE — COMMERCIAL LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — COMMERCIAL LAW]",
        "freshness": False,
    },
    {
        "name": "employment",
        "prompt": "Employment Law problem on worker status, unfair dismissal, redundancy, discrimination and restrictive covenants.",
        "slug": "employment_law",
        "template": "[SUBJECT TEMPLATE — EMPLOYMENT LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — EMPLOYMENT LAW]",
        "freshness": True,
    },
    {
        "name": "family",
        "prompt": "Family Law problem on child arrangements, domestic abuse, financial remedies and public law threshold.",
        "slug": "family_law",
        "template": "[SUBJECT TEMPLATE — FAMILY LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — FAMILY LAW]",
        "freshness": False,
    },
    {
        "name": "intellectual_property",
        "prompt": "Intellectual Property Law problem on AI copyright, trade marks, passing off, patent validity and remedies.",
        "slug": "intellectual_property_law",
        "template": "[SUBJECT TEMPLATE — INTELLECTUAL PROPERTY LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — INTELLECTUAL PROPERTY LAW]",
        "freshness": True,
    },
    {
        "name": "tax",
        "prompt": "Tax Law problem on VAT, HMRC discovery, GAAR, CGT relief, penalties and appeal route in 2026.",
        "slug": "tax_law",
        "template": "[SUBJECT TEMPLATE — TAX LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — TAX LAW]",
        "freshness": True,
    },
    {
        "name": "eu",
        "prompt": "EU Law problem on direct effect, free movement, proportionality and post-Brexit assimilated EU law.",
        "slug": "eu_law",
        "template": "[SUBJECT TEMPLATE — EU LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — EU LAW]",
        "freshness": True,
    },
    {
        "name": "private_international",
        "prompt": "Private International Law problem on jurisdiction, Rome I, service out, freezing relief and enforcement.",
        "slug": "private_international_law",
        "template": "[SUBJECT TEMPLATE — PRIVATE INTERNATIONAL LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — PRIVATE INTERNATIONAL LAW]",
        "freshness": False,
    },
    {
        "name": "public_international",
        "prompt": "Public International Law problem on state responsibility, use of force, immunity, IHL and remedies.",
        "slug": "public_international_law",
        "template": "[SUBJECT TEMPLATE — PUBLIC INTERNATIONAL LAW]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — PUBLIC INTERNATIONAL LAW]",
        "freshness": False,
    },
    {
        "name": "biolaw_ai_data",
        "prompt": "Biolaw AI Data Protection essay on medical AI, GDPR, algorithmic bias and medical-device regulation.",
        "slug": "biolaw_ai_data",
        "template": "[SUBJECT TEMPLATE — BIOLAW / AI / DATA]",
        "rubric": "[TOPIC-SPECIFIC MARKING RUBRIC — BIOLAW / AI / DATA]",
        "freshness": True,
    },
)


def _contract(prompt: str) -> tuple[str, dict, str]:
    profile = _infer_retrieval_profile(prompt)
    slug = _infer_subject_guide_slug(str(profile.get("topic") or ""), prompt)
    combined = "\n".join([
        _build_local_code_rag_answer_prompt_block(prompt, enforce_long_response_split=False),
        _build_legal_answer_quality_gate(prompt, profile),
    ])
    return slug, profile, combined


def test_major_subject_quality_contracts_are_present() -> None:
    for case in SUBJECT_CASES:
        slug, _profile, combined = _contract(str(case["prompt"]))
        assert slug == case["slug"], (case["name"], slug)
        assert case["template"] in combined, case["name"]
        assert case["rubric"] in combined, case["name"]
        assert "[SOURCE QUALITY PRIORITY GATE]" in combined, case["name"]
        assert "[ANSWER SPECIFICITY / ANTI-GENERIC GATE]" in combined, case["name"]
        assert "[SPECIALIST ACCURACY PASS — TOP FIRST-CLASS STANDARD]" in combined, case["name"]
        if case["freshness"]:
            assert "[CURRENT-LAW / FRESHNESS GATE]" in combined, case["name"]
        for marker in PRIVATE_OR_INTERNAL_MARKERS:
            assert marker not in combined, (case["name"], marker)


def test_negative_drift_guards_are_present() -> None:
    law_med_course = _contract(
        "Law and Medicine course-bound essay: stay within the module syllabus and discuss abortion reform."
    )[2].lower()
    assert "[law and medicine source mode: course-bound]" in law_med_course
    assert "do not drift into clinical negligence/montgomery" in law_med_course
    assert "mental health law" in law_med_course

    law_med_no_limit = _contract(
        "Law and Medicine no syllabus limit essay: discuss bodily autonomy broadly."
    )[2].lower()
    assert "[law and medicine source mode: no syllabus limit]" in law_med_no_limit
    assert "course-bound exclusions do not apply" in law_med_no_limit

    mediation = _contract(
        "International commercial mediation problem on a mediated settlement agreement, confidentiality and the Singapore Convention."
    )[2].lower()
    assert "do not treat mediation as arbitration" in mediation or "treating mediated settlements as arbitral awards" in mediation

    pensions = _contract(
        "Pensions Law problem on occupational pension scheme amendment, section 67 and trustee duties."
    )[2].lower()
    assert "do not treat pensions as generic trusts law" in pensions

    competition = _contract(
        "Competition Law Article 102 platform self-preferencing problem with digital markets and foreclosure."
    )[2].lower()
    assert "policy-only digital-market discussion" in competition or "do not become policy essays" in competition
    assert "define `effects-based`" in competition
    assert "bronner" in competition
    assert "digital markets act" in competition


def test_structure_clarity_contracts_do_not_conflict() -> None:
    essay = _contract(
        "Law and Medicine course-bound essay: stay within the module syllabus and critically examine HFEA reform."
    )[2]
    assert "Part I thesis" in essay
    assert "2-3 focused syllabus examples" in essay
    assert "statutory route" in essay

    problem = _contract(
        "Land Law problem on registered land priority, actual occupation and overreaching."
    )[2].lower()
    assert "apply to facts before moving to the next issue" in problem
    assert "rank likely/arguable/weak outcomes" in problem
    assert "state remedy/next step before ending" in problem

    sqe_task = build_sqe_question_set_prompt(
        "Give me one hard SQE2 legal drafting task in Business Organisations. I will answer later; do not give the model answer.",
        exam_stage="sqe2",
    )
    assert "Candidate instructions" in sqe_task
    assert "Client/matter facts" in sqe_task
    assert "Documents/extracts" in sqe_task
    assert "Specific task" in sqe_task
    assert "Do not reveal answers" in sqe_task
    assert "Part I: Introduction" not in sqe_task

    marking = build_sqe2_marking_prompt(
        question="SQE2 legal writing task: write a client email.",
        candidate_answer="The seller breached. We can sue.",
        skill="legal writing",
    )
    assert "SQE2 marking result" in marking
    assert "A-F scale" in marking
    assert "corrected high-scoring answer" in marking
    assert "Next targeted practice" in marking


def test_anti_generic_rules_are_injected_for_every_major_subject() -> None:
    expected = [rule.lower() for rule in ANTI_GENERIC_QUALITY_RULES]
    for case in SUBJECT_CASES:
        combined = _contract(str(case["prompt"]))[2].lower()
        for rule in expected:
            assert rule in combined, (case["name"], rule)


def test_review_feedback_traps_are_locked_into_specialist_guidance() -> None:
    land = _contract(
        "Land Law problem on registered land priority: six-year workshop business lease, "
        "purchase-money contribution, bank refinancing, driveway parking, option notice and overreaching."
    )[2].lower()
    assert "landlord and tenant act 1954" in land
    assert "resulting trust" in land
    assert "official search with priority" in land
    assert "overreaching clears beneficial interests under a trust only" in land

    evidence = _contract(
        "Evidence Law problem on video identification after social-media contamination, facial mapping, "
        "confession threats, silence, co-suspect hearsay and old burglary conviction."
    )[2].lower()
    assert "pace code d" in evidence
    assert "s 76(2)(b)" in evidence
    assert "later fact relied on" in evidence
    assert "co-defendant/non-defendant status" in evidence

    competition = _contract(
        "Competition Law Article 102 essay: critically evaluate whether digital platform self-preferencing "
        "shows Article 102 is now effects-based in light of Google Shopping, Bronner and the DMA."
    )[2].lower()
    assert "actual effects, likely effects, capability" in competition
    assert "self-preferencing is not per se abusive" in competition
    assert "bronner indispensability" in competition
    assert "commission's first-guidelines process" in competition


def test_inline_oscola_is_default_and_other_styles_are_explicit_overrides() -> None:
    default_prompt = (
        "Land Law problem on registered land priority, actual occupation, "
        "overreaching, an option and an easement."
    )
    style = _detect_requested_citation_style(default_prompt)
    assert style == "oscola"

    oscola_contract = "\n".join([
        _build_active_citation_style_reminder(style),
        _build_active_citation_style_quality_gate(style),
        _build_active_citation_style_override(style),
    ]).lower()
    assert "[oscola inline house style" in oscola_contract
    assert "full oscola citations in parentheses immediately after the relevant sentence" in oscola_contract
    assert "the citation must sit directly after the sentence it supports" in oscola_contract
    assert "do not use ibid or short-form" in oscola_contract
    assert "do not output local file paths" in oscola_contract

    subject_contract = _contract(default_prompt)[2].lower()
    assert "put oscola citations immediately after supporting proposition sentences" in subject_contract
    assert "most analytical paragraphs should carry at least one immediate inline oscola citation" in subject_contract
    assert "every parenthetical authority reference must be a full oscola citation" in subject_contract

    harvard_prompt = "Use Harvard referencing. " + default_prompt
    harvard_style = _detect_requested_citation_style(harvard_prompt)
    assert harvard_style == "harvard"
    harvard_contract = "\n".join([
        _build_active_citation_style_reminder(harvard_style),
        _build_active_citation_style_quality_gate(harvard_style),
        _build_active_citation_style_override(harvard_style),
    ]).lower()
    assert "[harvard author-date style" in harvard_contract
    assert "ignore any earlier instruction that requires oscola" in harvard_contract
    assert "do not use citation footnotes" in harvard_contract
    assert "do not drift into oscola" in harvard_contract or "oscola short-form" in harvard_contract


def test_sqe2_practice_generation_withholds_answers() -> None:
    task = build_sqe_question_set_prompt(
        "Give me one hard SQE2 legal research task. This is testing mode and I will answer later.",
        exam_stage="sqe2",
    ).lower()
    assert "withhold answers unless they expressly request" in task
    assert "do not reveal answers" in task
    assert "if answers were requested" in task
    assert "otherwise omit all answers" in task


if __name__ == "__main__":
    test_major_subject_quality_contracts_are_present()
    test_negative_drift_guards_are_present()
    test_structure_clarity_contracts_do_not_conflict()
    test_anti_generic_rules_are_injected_for_every_major_subject()
    test_inline_oscola_is_default_and_other_styles_are_explicit_overrides()
    test_sqe2_practice_generation_withholds_answers()
    print("Backend answer quality contract regression passed.")
