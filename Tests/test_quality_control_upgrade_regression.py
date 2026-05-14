"""
Regression checks for the backend quality-control upgrade.

The tests verify prompt-layer contracts without calling live LLM APIs.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend_answer_runtime import build_sqe2_marking_prompt, build_sqe_question_set_prompt
from legal_answer_quality_controls import (
    GOLDEN_OUTPUT_AUDIT_SUITE,
    LIVE_PROMPT_AUDIT_SUITE,
    TOPIC_SPECIALIST_SEQUENCE_RULES,
    build_golden_output_audit_prompt,
    build_live_prompt_audit_checklist,
    build_topic_specialist_sequence_block,
    build_topic_marking_rubric_block,
    law_medicine_syllabus_mode,
)
from model_applicable_service import (
    _build_legal_answer_quality_gate,
    _build_local_code_rag_answer_prompt_block,
    _infer_retrieval_profile,
)


def test_quality_control_module_is_privacy_safe() -> None:
    text = (ROOT / "legal_answer_quality_controls.py").read_text(encoding="utf-8")
    blocked = ["/Users/", "\\Users\\", Path.home().name, "LAW" + "3071", "Dur" + "ham"]
    for token in blocked:
        assert token not in text


def test_golden_and_live_audit_suites_are_available() -> None:
    assert len(GOLDEN_OUTPUT_AUDIT_SUITE) >= 4
    assert len(LIVE_PROMPT_AUDIT_SUITE) >= 4
    golden = build_golden_output_audit_prompt()
    live = build_live_prompt_audit_checklist()
    assert "law_medicine_course_bound_autonomy" in golden
    assert "competition_article_102_problem" in golden
    assert "pensions_nra_equalisation_gold_shape" in golden
    assert "mediation_singapore_convention_gold_shape" in golden
    assert "SQE2 written marking/practice" in live
    assert "Pensions NRA/equalisation stress" in live
    assert "Mediation Singapore Convention stress" in live
    assert "must show" in golden
    assert "checks:" in live


def test_law_medicine_syllabus_toggle_is_explicit() -> None:
    course_prompt = "Law and Medicine essay: stay within the module syllabus and discuss abortion reform."
    no_limit_prompt = "Law and Medicine no syllabus limit essay: discuss bodily autonomy broadly."

    assert law_medicine_syllabus_mode(course_prompt) == "course_bound"
    assert law_medicine_syllabus_mode(no_limit_prompt) == "no_limit"

    course_block = _build_local_code_rag_answer_prompt_block(course_prompt, enforce_long_response_split=False)
    no_limit_block = _build_local_code_rag_answer_prompt_block(no_limit_prompt, enforce_long_response_split=False)

    assert "[LAW AND MEDICINE SOURCE MODE: COURSE-BOUND]" in course_block
    assert "Do not drift into clinical negligence/Montgomery" in course_block
    assert "[LAW AND MEDICINE SOURCE MODE: NO SYLLABUS LIMIT]" in no_limit_block
    assert "distinguish course-core material from wider English medical-law material" in no_limit_block


def test_freshness_and_source_quality_gates_are_injected() -> None:
    prompt = "Competition Law Article 102 problem: advise on current digital markets self-preferencing and objective justification."
    profile = _infer_retrieval_profile(prompt)
    gate = _build_legal_answer_quality_gate(prompt, profile)

    assert "[SOURCE QUALITY PRIORITY GATE]" in gate
    assert "official_primary" in gate
    assert "feedback_marking" in gate
    assert "[ANSWER SPECIFICITY / ANTI-GENERIC GATE]" in gate
    assert "[SPECIALIST ACCURACY PASS — TOP FIRST-CLASS STANDARD]" in gate
    gate_low = gate.lower()
    assert "rank likely/arguable/weak outcomes" in gate_low
    assert "do not survey the topic" in gate_low
    assert "exact statutory gateway" in gate_low
    assert "[CURRENT-LAW / FRESHNESS GATE]" in gate
    assert "CMA/EU" in gate
    assert "[SUBJECT TEMPLATE — COMPETITION LAW]" in gate
    assert "Article 102 problem: undertaking -> market definition -> dominance" in gate
    assert "define `effects-based`" in gate


def test_subject_templates_cover_core_prompts() -> None:
    prompts = [
        ("Law and Medicine course-bound problem on end-of-life best interests.", "[SUBJECT TEMPLATE — LAW AND MEDICINE]"),
        ("Pensions Law problem on amendment power and Barber equalisation.", "[SUBJECT TEMPLATE — PENSIONS LAW]"),
        ("Criminal Law problem question on non-fatal offences and consent.", "[SUBJECT TEMPLATE — CRIMINAL LAW]"),
        ("Land Law problem on registered land priority and proprietary estoppel.", "[SUBJECT TEMPLATE — LAND LAW]"),
    ]
    for prompt, expected in prompts:
        block = _build_local_code_rag_answer_prompt_block(prompt, enforce_long_response_split=False)
        assert expected in block, prompt


def test_topic_specific_marking_rubrics_cover_core_subjects() -> None:
    cases = [
        ("Land Law problem on registered land, actual occupation and overreaching.", "land_law", "Schedule 3 para 2"),
        ("Tort Law problem on psychiatric harm and police omissions.", "tort_law", "Alcock controls"),
        ("Company Law problem on directors duties, conflicts and insolvency.", "business_law", "Model Articles quorum/conflicts"),
        ("Trusts Law problem on purpose trusts, secret trusts and tracing.", "trusts_law", "purpose-trust beneficiary principle"),
        ("Evidence Law problem on hearsay, bad character and confession evidence.", "evidence_law", "CJA 2003 hearsay gateways"),
        ("Public Law problem on legitimate expectation and remedies.", "public_law", "legitimate expectation clarity"),
        ("Pensions Law problem on Barber equalisation and section 67.", "pensions_law", "Barber/equalisation timing"),
        ("International commercial mediation essay on the Singapore Convention.", "mediation_law", "Article 5(1)(e) serious breach"),
    ]
    for prompt, expected_slug, expected_phrase in cases:
        profile = _infer_retrieval_profile(prompt)
        gate = _build_legal_answer_quality_gate(prompt, profile)
        assert f"[TOPIC-SPECIFIC MARKING RUBRIC —" in gate
        assert expected_phrase in gate, (expected_slug, gate[:3000])

    land_gate = _build_legal_answer_quality_gate(
        "Land Law problem on a six-year business lease, actual occupation and late option notice.",
        _infer_retrieval_profile("Land Law problem on a six-year business lease, actual occupation and late option notice."),
    )
    assert "Landlord and Tenant Act 1954" in land_gate
    assert "official-search-with-priority" in land_gate

    evidence_gate = _build_legal_answer_quality_gate(
        "Evidence Law problem on video identification, confession threats and silence.",
        _infer_retrieval_profile("Evidence Law problem on video identification, confession threats and silence."),
    )
    assert "PACE Code D" in evidence_gate
    assert "s.34 needs a later relied-on fact" in evidence_gate or "later fact relied on" in evidence_gate

    fallback = build_topic_marking_rubric_block("", topic="company_directors_minorities")
    assert "BUSINESS / COMPANY LAW" in fallback


def test_specialist_sequence_matrix_covers_all_routed_topics() -> None:
    from Tests.test_all_topics_regression import ROUTED_TOPICS

    assert len(TOPIC_SPECIALIST_SEQUENCE_RULES) >= 30
    misses = []
    for topic in ROUTED_TOPICS:
        block = build_topic_specialist_sequence_block(topic=topic, query=f"{topic} problem")
        if "[SPECIALIST SEQUENCE MATRIX — GENERAL LEGAL]" in block:
            misses.append(topic)
    assert not misses, misses

    checks = {
        "tax_avoidance_gaar": "transfer pricing/TAAR/specific rule -> GAAR",
        "generic_environmental_law": "standing/source -> private or regulatory route",
        "succession_wills_validity": "formal validity -> capacity -> knowledge and approval",
        "public_procurement_award_challenges": "standstill/limitation",
        "international_commercial_arbitration": "agreement/scope -> seat/law",
        "product_liability_consumer_protection": "CRA rights, unfair terms, strict product liability",
    }
    for topic, phrase in checks.items():
        assert phrase in build_topic_specialist_sequence_block(topic=topic, query=topic)


def test_sqe2_hard_practice_marking_loop_is_prompted() -> None:
    task_prompt = build_sqe_question_set_prompt(
        "Give me an SQE2 legal research task, harder than the sample, then I will answer.",
        exam_stage="sqe2",
    )
    marking_prompt = build_sqe2_marking_prompt(
        question="SQE2 legal research task: advise on whether a spouse can be compelled.",
        candidate_answer="The spouse is competent and may not be compellable.",
        skill="legal research",
    )

    assert "[SQE2 HARD PRACTICE + MARKING LOOP]" in task_prompt
    assert "withhold answers unless they expressly request" in task_prompt
    assert "[SQE2 HARD PRACTICE + MARKING LOOP]" in marking_prompt
    assert "Next targeted practice" in marking_prompt


if __name__ == "__main__":
    test_quality_control_module_is_privacy_safe()
    test_golden_and_live_audit_suites_are_available()
    test_law_medicine_syllabus_toggle_is_explicit()
    test_freshness_and_source_quality_gates_are_injected()
    test_subject_templates_cover_core_prompts()
    test_topic_specific_marking_rubrics_cover_core_subjects()
    test_specialist_sequence_matrix_covers_all_routed_topics()
    test_sqe2_hard_practice_marking_loop_is_prompted()
    print("Quality-control upgrade regression passed.")
