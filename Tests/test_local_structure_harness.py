"""
Local deterministic harness for long multi-question structure and allocation.
No model/API calls.
"""

from collections import defaultdict

from gemini_service import (
    _build_single_question_long_part_guidance,
    _expected_internal_part_heading_from_history,
    _finalize_model_output_text,
    _int_to_roman,
    detect_essay_core_policy_violation,
    detect_long_essay,
    detect_unit_structure_policy_violation,
)


def _question_budgets(plan: dict) -> dict:
    budgets = defaultdict(int)
    for d in (plan.get("deliverables") or []):
        budgets[int(d.get("question_index", 0) or 0)] += int(d.get("target_words", 0) or 0)
    return dict(sorted(budgets.items()))


def run() -> None:
    short_essay_1500 = "Write a 1500 word essay on contract law."
    short_essay_2000 = "Write a 2000 word essay on negligence."
    long_essay_2001 = "Write a 2001 word essay on public law."
    long_essay_3000 = "Write a 3000 word essay on tort law."
    long_essay_4000 = "Write a 4000 word essay on equity."

    prompt_4500 = """4500 words
1. Company Law – Essay Question (Directors’ Duties and Conflicts of Interest)
Discuss directors' duties and conflicts of interest.

2. Land Law – Problem Question (Lease vs Licence and Forfeiture)
Advise Ava and Blue Estates.
"""

    prompt_5500 = """5500 words
1. Criminal Law – Problem Question (Theft, Robbery, Burglary)
Advise on Dan's liability.

2. Tort Law – Problem Question (Pure Economic Loss and Negligent Misstatement)
Advise EcoConsult, SafeBank and the neighbouring landowner.

3. Evidence – Short Problem Question (Hearsay and Exceptions)
Advise on hearsay and exceptions.
"""

    print("=" * 80)
    print("LOCAL STRUCTURE HARNESS")
    print("=" * 80)

    print("\nRoman numeral helper")
    assert _int_to_roman(1) == "I"
    assert _int_to_roman(4) == "IV"
    assert _int_to_roman(12) == "XII"

    print("\nWord-count boundary checks")
    boundary_expectations = [
        (800, False, 0),
        (1500, False, 0),
        (2000, False, 0),
        (2001, True, 2),
        (3000, True, 2),
        (4000, True, 2),
        (4500, True, 3),
        (5500, True, 3),
    ]
    for words, expect_long, expect_parts in boundary_expectations:
        plan = detect_long_essay(f"Write a {words} word essay on contract law")
        print(words, plan.get("is_long_essay"), plan.get("suggested_parts"), plan.get("words_per_part"))
        assert bool(plan.get("is_long_essay")) is expect_long
        assert int(plan.get("suggested_parts") or 0) == expect_parts

    for label, prompt, expected_long, expected_parts in [
        ("short 1500", short_essay_1500, False, 0),
        ("short 2000", short_essay_2000, False, 0),
        ("long 2001", long_essay_2001, True, 2),
        ("long 3000", long_essay_3000, True, 2),
        ("long 4000", long_essay_4000, True, 2),
    ]:
        plan = detect_long_essay(prompt)
        print(label, "->", plan.get("is_long_essay"), plan.get("suggested_parts"))
        assert bool(plan.get("is_long_essay")) is expected_long
        assert int(plan.get("suggested_parts") or 0) == expected_parts

    for label, prompt, expected_parts, expected_budgets in [
        ("4500 / 2q", prompt_4500, 4, {1: 2250, 2: 2250}),
        ("5500 / 3q", prompt_5500, 3, {1: 1834, 2: 1833, 3: 1833}),
    ]:
        plan = detect_long_essay(prompt)
        budgets = _question_budgets(plan)
        print(f"\n{label}")
        print("split_mode:", plan.get("split_mode"))
        print("suggested_parts:", plan.get("suggested_parts"))
        print("deliverable targets:", [int(d.get("target_words", 0) or 0) for d in (plan.get("deliverables") or [])])
        print("question budgets:", budgets)
        print("question indices:", [int(d.get("question_index", 0) or 0) for d in (plan.get("deliverables") or [])])
        print("unit kinds:", [str(d.get("unit_kind") or "") for d in (plan.get("deliverables") or [])])

        assert plan.get("split_mode") == "by_units"
        assert plan.get("suggested_parts") == expected_parts
        assert budgets == expected_budgets
        assert all(len(d.get("fragments") or []) == 1 for d in (plan.get("deliverables") or []))

    print("\nSingle-question long-part coherence helper")
    single_q_part1 = _build_single_question_long_part_guidance(
        total_words=5500,
        num_parts=3,
        current_part=1,
        is_problem=False,
    )
    single_q_part2 = _build_single_question_long_part_guidance(
        total_words=5500,
        num_parts=3,
        current_part=2,
        is_problem=False,
    )
    single_q_part3 = _build_single_question_long_part_guidance(
        total_words=5500,
        num_parts=3,
        current_part=3,
        is_problem=True,
    )
    print(single_q_part1)
    assert "Part 1 must establish the thesis/answer direction once" in single_q_part1
    assert "Do NOT use any heading containing 'Conclusion' or 'Conclusion and Advice' in Part 1." in single_q_part1
    assert "Start with the next unresolved Part-numbered heading" in single_q_part2
    assert "Do NOT use any heading containing 'Conclusion' or 'Conclusion and Advice' in this non-final part." in single_q_part2
    assert "Finish the remaining major issue cluster(s)" in single_q_part3
    assert "must still contain substantial remaining analysis before the final conclusion" in single_q_part3
    assert "keep the same party/issue order across parts" in single_q_part3

    heading_history = [
        {"role": "user", "text": "Write a 4000 word essay on public law."},
        {"role": "assistant", "text": "Part I: Introduction\n\nOpening.\n\nPart II: Doctrine\n\nBody.\n\nWill Continue to next part, say continue"},
    ]
    assert _expected_internal_part_heading_from_history("continue", heading_history) == 3

    open_heading_history = [
        {"role": "user", "text": "Write a 4000 word essay on public law."},
        {"role": "assistant", "text": "Part I: Introduction\n\nOpening.\n\nPart II: Doctrine\n\nA.\n\nWill Continue to next part, say continue"},
    ]
    assert _expected_internal_part_heading_from_history("continue", open_heading_history) == 2

    bad_essay_cont = """Question 1: Company Law – Essay Question

Part V: Continued Analysis

A. Issue

This continuation drifts into problem-question formatting.
"""
    print("\nBad essay continuation:", detect_unit_structure_policy_violation(
        bad_essay_cont,
        unit_kind="essay",
        require_question_heading=True,
        expected_question_number=1,
        is_same_topic_continuation=True,
    ))
    print("Essay OSCOLA/core policy:", detect_essay_core_policy_violation(bad_essay_cont, is_continuation=True))
    assert detect_unit_structure_policy_violation(
        bad_essay_cont,
        unit_kind="essay",
        require_question_heading=True,
        expected_question_number=1,
        is_same_topic_continuation=True,
    )[0] is True

    good_essay_cont = """Question 1: Company Law – Essay Question

Part V: Protection of Shareholders and Creditors

A. Shareholder protection

The statutory framework uses disclosure and approval to manage conflicts.
"""
    assert detect_unit_structure_policy_violation(
        good_essay_cont,
        unit_kind="essay",
        require_question_heading=True,
        expected_question_number=1,
        is_same_topic_continuation=True,
    )[0] is False

    good_short_essay = """Part I: Introduction

The modern law of contract balances certainty with fairness.

Part II: Formation and Principle

1. Offer and acceptance

The orthodox formation rules remain central to contractual liability.

Part III: Doctrinal Development

1.1 Contemporary flexibility

Modern case law recognises more nuanced commercial settings.

Part IV: Critical Evaluation

The main doctrinal tension lies between certainty and contextual justice.

Part V: Conclusion

The preferable view is that the law should preserve certainty while allowing narrow corrective flexibility.
"""
    assert detect_essay_core_policy_violation(
        good_short_essay,
        is_continuation=False,
        is_short_single_essay=True,
        require_part_v_conclusion=True,
    )[0] is False

    good_short_essay_part_iv = """Part I: Introduction

The modern law of contract balances certainty with fairness.

Part II: Construction

The courts now read exclusion clauses through ordinary contractual interpretation.

Part III: Statutory Control

UCTA 1977 and the CRA 2015 impose structured limits where fairness demands it.

Part IV: Conclusion

The better view is that freedom of contract survives, but only within a disciplined framework of construction and statutory control.
"""
    assert detect_essay_core_policy_violation(
        good_short_essay_part_iv,
        is_continuation=False,
        is_short_single_essay=True,
        require_part_v_conclusion=True,
    )[0] is False

    bad_short_essay = """Part I: Introduction

This essay begins adequately.

Part II: Analysis

Caparo Industries plc v Dickman.
"""
    bad_short_essay_violation = detect_essay_core_policy_violation(
        bad_short_essay,
        is_continuation=False,
        is_short_single_essay=True,
        require_part_v_conclusion=True,
    )
    print("Bad short essay:", bad_short_essay_violation)
    assert bad_short_essay_violation[0] is True

    bad_pb = """Question 2: Land Law – Problem Question

Part I: Introduction

A. Issue

The threshold issue is whether the agreement created a lease.
"""
    print("Bad PB structure:", detect_unit_structure_policy_violation(
        bad_pb,
        unit_kind="problem",
        require_question_heading=True,
        expected_question_number=2,
        is_same_topic_continuation=False,
    ))
    assert detect_unit_structure_policy_violation(
        bad_pb,
        unit_kind="problem",
        require_question_heading=True,
        expected_question_number=2,
        is_same_topic_continuation=False,
    )[0] is True

    bad_employment_pb = """Question 1: Discrimination / Employment Law – Problem Question

Part I: Introduction

The central legal issue concerns Amira's request to reduce her working hours.

A. Issue

The primary procedural issue is whether the claim should be framed as equal pay or indirect discrimination.
"""
    bad_employment_pb_violation = detect_unit_structure_policy_violation(
        bad_employment_pb,
        unit_kind="problem",
        require_question_heading=True,
        expected_question_number=1,
        is_same_topic_continuation=False,
    )
    print("Bad employment PB structure:", bad_employment_pb_violation)
    assert bad_employment_pb_violation[0] is True

    wrong_question_q3 = """Question 1: Discrimination / Employment Law – Problem Question

Part III: Further Analysis

A. Issue

The employer's justification defence must now be considered.
"""
    wrong_question_q3_violation = detect_unit_structure_policy_violation(
        wrong_question_q3,
        unit_kind="problem",
        require_question_heading=True,
        expected_question_number=2,
        is_same_topic_continuation=False,
    )
    print("Wrong-question continuation:", wrong_question_q3_violation)
    assert wrong_question_q3_violation[0] is True
    assert "wrong question heading" in wrong_question_q3_violation[1].lower()

    good_new_q2_part1 = """Question 2: Land Law – Problem Question

Part I: Introduction

This problem concerns lease classification, forfeiture, and remedies.
The analysis will first address whether the arrangement is a lease or licence,
then examine forfeiture and eviction, before turning to remedies and final advice.
"""
    assert detect_unit_structure_policy_violation(
        good_new_q2_part1,
        unit_kind="problem",
        require_question_heading=True,
        expected_question_number=2,
        expected_part_number=1,
        starts_new_question=True,
        enforce_single_top_level_part=True,
    )[0] is False

    bad_new_q2_part3 = """Question 2: Land Law – Problem Question

Part III: Introduction and Lease or Licence

Body.
"""
    bad_new_q2_part3_violation = detect_unit_structure_policy_violation(
        bad_new_q2_part3,
        unit_kind="problem",
        require_question_heading=True,
        expected_question_number=2,
        expected_part_number=1,
        starts_new_question=True,
        enforce_single_top_level_part=True,
    )
    print("Bad new-question Part carry-over:", bad_new_q2_part3_violation)
    assert bad_new_q2_part3_violation[0] is True
    assert "wrong part heading" in bad_new_q2_part3_violation[1].lower()

    bad_global_same_q_intro = """Question 1: Company Law – Essay Question

Part II: Introduction and Further Analysis

Body.
"""
    bad_global_same_q_intro_violation = detect_unit_structure_policy_violation(
        bad_global_same_q_intro,
        unit_kind="essay",
        require_question_heading=True,
        expected_question_number=1,
        expected_part_number=2,
        starts_new_question=False,
        enforce_single_top_level_part=True,
    )
    print("Bad global continuation intro:", bad_global_same_q_intro_violation)
    assert bad_global_same_q_intro_violation[0] is True
    assert "continuation" in bad_global_same_q_intro_violation[1].lower() or "introductory" in bad_global_same_q_intro_violation[1].lower()

    good_pb = """Question 2: Land Law – Problem Question

Part I: Introduction

This problem concerns lease classification, forfeiture, and remedies.

Part II: Lease or Licence

A. Issue

The first issue is whether the agreement created a lease.

B. Rule

Exclusive possession for a term at a rent strongly indicates a tenancy.

C. Application

Ava appears to have exclusive possession of the flat as her home.

D. Conclusion

The agreement is highly likely to be a lease.

Part III: Forfeiture and Eviction

A. Issue

The next issue is whether Blue Estates could lawfully forfeit and evict.

B. Rule

Residential forfeiture requires proper legal process and self-help is prohibited.

C. Application

Changing the locks without a court order is highly likely to be unlawful.

D. Conclusion

Blue Estates likely acted unlawfully in purporting to forfeit and evict.

Part IV: Remedies / Liability

Ava should seek damages and possession-based relief, while Blue Estates faces serious difficulty justifying self-help eviction.

Part V: Final Conclusion

The better view is that Ava has strong merits on classification and unlawful eviction, and Blue Estates is unlikely to justify self-help forfeiture.
"""
    assert detect_unit_structure_policy_violation(
        good_pb,
        unit_kind="problem",
        require_question_heading=True,
        expected_question_number=2,
        is_same_topic_continuation=False,
    )[0] is False

    cleaned = _finalize_model_output_text("""Part V: Continued Analysis

Question 2: Land Law – Problem Question

Part I: Introduction

Body.
""")
    print("\nCleaned transition:\n", cleaned)
    assert cleaned.startswith("Question 2: Land Law – Problem Question")

    empty_d = """Question 2: Land Law – Problem Question

Part I: Introduction

Part II: Lease or Licence

A. Issue

The threshold issue is classification.

B. Rule

Exclusive possession is the key indicator.

C. Application

Ava has exclusive possession.

D.
"""
    empty_d_violation = detect_unit_structure_policy_violation(
        empty_d,
        unit_kind="problem",
        require_question_heading=True,
        expected_question_number=2,
        is_same_topic_continuation=False,
    )
    print("Empty D violation:", empty_d_violation)
    assert empty_d_violation[0] is True
    assert "empty subsection" in empty_d_violation[1].lower() or "bare lettered" in empty_d_violation[1].lower()

    empty_part = """Question 1: Company Law – Essay Question

Part I: Introduction

This answer introduces the topic.

Part II: Balancing Strict Rules with Commercial Reality

Part III: Conclusion

The law balances strict duties with practical management.
"""
    empty_part_violation = detect_unit_structure_policy_violation(
        empty_part,
        unit_kind="essay",
        require_question_heading=True,
        expected_question_number=1,
        is_same_topic_continuation=False,
    )
    print("Empty Part violation:", empty_part_violation)
    assert empty_part_violation[0] is True
    assert "part heading" in empty_part_violation[1].lower()

    with open("gemini_service.py", "r", encoding="utf-8") as fh:
        src = fh.read()
    assert "A. [subtitle] / B. [subtitle] / C. [subtitle] / D. [subtitle]" in src
    assert "Each question/unit has its OWN independent Part numbering (Part I, Part II, etc.) - do NOT continue numbering from a previous question." in src
    assert "Preferred essay shape: Part I: Introduction -> Part II: issue/theme 1" in src
    assert "Preferred problem-question shape: Question X -> Part I: Introduction -> Part II: Issue 1" in src

    print("\nAll local structure harness checks passed.")


if __name__ == "__main__":
    run()
