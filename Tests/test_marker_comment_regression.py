"""
Regression checks derived from recurring marker-comment patterns.

Purpose:
- catch drift where thin topics lose counterargument depth
- catch drift where issue banks become too shallow to surface real fault lines
- preserve the cross-topic drafting lessons abstracted from marker feedback

This is an offline regression harness. It does not call live model APIs.
"""

from __future__ import annotations

import ast
from pathlib import Path

from model_applicable_service import _infer_retrieval_profile, _subissue_queries_for_unit


SOURCE = Path("model_applicable_service.py").read_text(encoding="utf-8")


def _extract_literal_dict(anchor: str):
    idx = SOURCE.index(anchor)
    start = SOURCE.index("{", idx)
    depth = 0
    end = None
    for i in range(start, len(SOURCE)):
        if SOURCE[i] == "{":
            depth += 1
        elif SOURCE[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise RuntimeError(f"Could not parse dict for {anchor}")
    return ast.literal_eval(SOURCE[start:end])


TOPIC_GUIDANCE_EXACT = _extract_literal_dict("topic_guidance_exact: Dict[str, Dict[str, List[str]]] = {")


THIN_EVALUATIVE_TOPICS = [
    "company_directors_minorities",
    "contract_misrepresentation_exclusion",
    "consumer_unfair_terms_cra2015",
    "data_protection",
    "defamation_media_privacy",
    "employment_discrimination_eqa2010",
    "clinical_negligence_causation_loss_of_chance",
    "banking_quincecare_fraud",
    "criminal_complicity",
    "criminal_evidence_hearsay",
    "constitutional_prerogative_justiciability",
    "competition_margin_squeeze_refusal",
    "consumer_digital_content",
    "family_child_abduction_hague1980",
    "international_commercial_arbitration",
    "public_law_privacy_expression",
    "restitution_mistake",
    "tort_negligence_omissions",
]


THIN_ISSUE_BANK_TOPICS = [
    "constitutional_prerogative_justiciability",
    "competition_margin_squeeze_refusal",
    "consumer_digital_content",
    "criminal_complicity",
    "criminal_evidence_hearsay",
    "family_child_abduction_hague1980",
    "international_commercial_arbitration",
    "public_law_privacy_expression",
    "restitution_mistake",
    "tort_negligence_omissions",
]


MARKER_PATTERN_CASES = [
    {
        "topic": "human_rights_proportionality_adjudication",
        "kind": "essay",
        "prompt": (
            "4500 words\nEssay Question — Human Rights Law – Proportionality\n"
            "Critically evaluate whether proportionality under the Human Rights Act 1998 has improved rights protection "
            "in the UK. Discuss Wednesbury, Daly, Huang, Bank Mellat, legitimacy, and judicial intrusiveness."
        ),
        "expected_subquery_terms": ["traditional", "common-law", "legitimacy"],
    },
    {
        "topic": "company_directors_minorities",
        "kind": "essay",
        "prompt": (
            "4500 words\nEssay Question — Company Law – Directors' Duties and Accountability\n"
            "Critically evaluate whether the statutory statement of directors' duties in the Companies Act 2006 provides "
            "a clear and effective framework for corporate accountability."
        ),
        "expected_issue_terms": ["section 172", "enforcement"],
        "expected_counter_terms": ["stakeholder", "derivative"],
    },
    {
        "topic": "private_international_law_post_brexit",
        "kind": "problem",
        "prompt": (
            "4500 words\nProblem Question — Private International Law – Jurisdiction and Enforcement\n"
            "Advise on service out, gateways, Hague instruments, forum conveniens, Rome I, and enforcement of a foreign judgment after Brexit."
        ),
        "expected_issue_terms": ["gateway", "service out"],
        "expected_subquery_terms": ["service-out", "choice of law", "practical outcome"],
    },
    {
        "topic": "employment_unfair_dismissal_misconduct",
        "kind": "problem",
        "prompt": (
            "4500 words\nProblem Question — Employment – Misconduct Dismissal\n"
            "Advise an employee dismissed for social media posts criticising management. Discuss unfair dismissal, policy, warnings, process fairness, Article 10, and proportionality."
        ),
        "expected_issue_terms": ["warning", "lesser sanctions"],
        "expected_subquery_terms": ["fairness", "employee rights"],
    },
    {
        "topic": "medical_consent_capacity",
        "kind": "problem",
        "prompt": (
            "4500 words\nProblem Question — Medical Law – Consent\n"
            "A patient consents to surgery on one knee, but the surgeon operates on the other knee as well without express consent. "
            "Advise on consent, battery, negligence, and remedies."
        ),
        "expected_issue_terms": ["scope of the consent", "battery"],
        "expected_subquery_terms": ["consent", "best interests", "practical outcome"],
    },
    {
        "topic": "ip_copyright_digital_innovation",
        "kind": "essay",
        "prompt": (
            "4500 words\nEssay Question — Intellectual Property – Copyright and Innovation\n"
            "Critically evaluate whether modern copyright law strikes an appropriate balance between protecting creators and allowing access, innovation, and freedom of expression. "
            "Discuss exclusive rights, fair dealing, platform enforcement, text and data mining, and copyright reform in the digital environment."
        ),
        "expected_issue_terms": ["incentive", "public interest"],
        "expected_subquery_terms": ["justifications", "exceptions", "reform"],
    },
]


def test_thin_evaluative_topics_now_carry_counterarguments():
    missing = [
        topic
        for topic in THIN_EVALUATIVE_TOPICS
        if not TOPIC_GUIDANCE_EXACT.get(topic, {}).get("counterargument_focus")
    ]
    assert missing == [], f"Missing counterargument_focus for: {missing}"


def test_thin_topics_now_have_richer_issue_banks():
    weak = [
        (topic, len(TOPIC_GUIDANCE_EXACT.get(topic, {}).get("issue_bank", [])))
        for topic in THIN_ISSUE_BANK_TOPICS
        if len(TOPIC_GUIDANCE_EXACT.get(topic, {}).get("issue_bank", [])) < 3
    ]
    assert weak == [], f"Issue banks still too thin: {weak}"


def test_shared_marker_comment_drafting_rules_present():
    for phrase in [
        "Define technical terms",
        "Start each major doctrinal section with its organising principle",
        "When using a sequence of cases or statutory changes, explain the progression",
        "Do not rely on unexplained shorthand",
        "If the answer depends on a central tension, asymmetry, or contrast, surface that frame early",
        "If a sentence could prompt 'Compared with what?', 'From what?', 'Harmed how?', 'With what effect?'",
        "Quantify or calibrate comparative and superlative claims",
        "Do not create thin sections or standalone headings for one short point",
        "AI-discrimination focus: if you rely on empirical bias or error-rate disparities",
        "[TOPIC-SPECIFIC GUIDANCE — AI / TECH GOVERNANCE (REGULATION / LIABILITY / PRIVACY)]",
    ]:
        assert phrase in SOURCE, f"Missing shared drafting rule: {phrase}"


def test_marker_pattern_cases_hold():
    for case in MARKER_PATTERN_CASES:
        profile = _infer_retrieval_profile(case["prompt"])
        assert profile.get("topic") == case["topic"], (case["topic"], profile.get("topic"))

        topic_guidance = TOPIC_GUIDANCE_EXACT[case["topic"]]
        issue_bank = " || ".join(topic_guidance.get("issue_bank", [])).lower()
        counter = " || ".join(topic_guidance.get("counterargument_focus", [])).lower()

        for term in case.get("expected_issue_terms", []):
            assert term.lower() in issue_bank, f"{case['topic']} missing issue term: {term}"
        for term in case.get("expected_counter_terms", []):
            assert term.lower() in counter, f"{case['topic']} missing counterargument term: {term}"

        unit_label = f"{case['kind'].title()} Question — Regression"
        subqueries = " || ".join(label for label, _ in _subissue_queries_for_unit(unit_label, case["prompt"])).lower()
        for term in case.get("expected_subquery_terms", []):
            assert term.lower() in subqueries, f"{case['topic']} missing subquery term: {term}"


if __name__ == "__main__":
    test_thin_evaluative_topics_now_carry_counterarguments()
    test_thin_topics_now_have_richer_issue_banks()
    test_shared_marker_comment_drafting_rules_present()
    test_marker_pattern_cases_hold()
    print("Marker-comment regression passed.")
