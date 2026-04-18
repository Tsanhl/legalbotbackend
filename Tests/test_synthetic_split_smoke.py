"""
Synthetic smoke tests for split-answer planning and continuation state.

These focus on the bug classes repeatedly seen in real prompts:
- short single-question answers
- one-question long answers split across 2-3 parts
- mixed multi-question papers
- explicit by-section split prompts
"""

from model_applicable_service import detect_long_essay
from backend_answer_runtime import (
    _current_unit_mode_from_history,
    _expected_internal_part_heading_from_history,
    _expected_unit_structure_state_from_history,
    _history_aware_structure_issues,
    _resolve_word_window_from_history,
)


def run() -> None:
    print("=" * 80)
    print("SYNTHETIC SPLIT SMOKE TESTS")
    print("=" * 80)

    short_essay = """2000 words
EU Law – Essay Question (Supremacy and Parliamentary Sovereignty)
Discuss whether EU supremacy transformed the constitutional role of national courts."""
    short_problem = """1800 words
Criminal Law – Problem Question
Advise Lina on theft, robbery, and possible defences."""
    long_single_4000 = """4000 words
Competition Law – Essay Question
Critically assess whether Article 102 TFEU is capable of regulating self-preferencing by digital gatekeepers."""
    long_single_5500 = """5500 words
Public Law – Essay Question
Critically assess whether proportionality should replace Wednesbury as the general ground of judicial review."""
    mixed_4000 = """4000 words
1. Contract Law – Essay Question
Discuss whether exclusion clauses reflect freedom of contract or judicial control.

2. Tort Law – Problem Question
Advise Maya on negligence, psychiatric harm, and remoteness."""
    three_q_6000 = """6000 words
Question 1: Administrative Law
Critically assess the growth of proportionality review.

Question 2: Equity and Trusts
Discuss whether English law should recognise the remedial constructive trust.

Question 3: EU Law
Discuss whether the limits on directive direct effect make the doctrine incomplete."""
    explicit_split = """3000 words
1. Land Law – Problem Question
Advise Aisha and Ben on co-ownership and sale.

3000 words
2. Human Rights – Essay Question
Discuss proportionality under Article 8 ECHR."""

    hist_4000 = [
        {"role": "user", "text": long_single_4000},
        {
            "role": "assistant",
            "text": (
                "Part I: Introduction\n\n"
                "This essay argues that Article 102 can regulate self-preferencing, "
                "but only through a careful effects-led analysis.\n\n"
                "Part II: Orthodox Abuse Framework\n\n"
                "Dominance and abuse remain the central starting points.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
        {"role": "user", "text": "continue"},
    ]

    hist_5500 = [
        {"role": "user", "text": long_single_5500},
        {
            "role": "assistant",
            "text": (
                "Title: Public Law – Essay Question\n\n"
                "Part I: Introduction\n\n"
                "This essay argues that proportionality has stronger analytical discipline "
                "but full replacement remains contested.\n\n"
                "Part II: Wednesbury and Orthodoxy\n\n"
                "The traditional test preserves institutional restraint.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
        {"role": "user", "text": "continue"},
        {
            "role": "assistant",
            "text": (
                "Part III: Proportionality and Rights-Based Review\n\n"
                "Rights review has sharpened scrutiny through a more structured method.\n\n"
                "Part IV: Institutional Competence and Residual Deference\n\n"
                "The strongest objection is that replacement may flatten context.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
        {"role": "user", "text": "continue"},
    ]

    hist_mixed_4000_p2 = [
        {"role": "user", "text": mixed_4000},
        {
            "role": "assistant",
            "text": (
                "Question 1: Contract Law – Essay Question\n\n"
                "Part I: Introduction\n\n"
                "This essay argues that English law preserves autonomy but subjects it to structured control.\n\n"
                "Part II: Incorporation and Construction\n\n"
                "The common law historically mediated harsh boilerplate terms.\n\n"
                "Part III: Statutory Control\n\n"
                "UCTA and CRA now frame the modern limits.\n\n"
                "Part IV: Conclusion\n\n"
                "Freedom of contract survives, but only in a disciplined form.\n\n"
                "(End of Answer)"
            ),
        },
        {"role": "user", "text": "continue"},
    ]

    hist_6000_q3 = [
        {"role": "user", "text": three_q_6000},
        {
            "role": "assistant",
            "text": (
                "Question 1: Administrative Law\n\n"
                "Part I: Introduction\n\n"
                "Administrative law now uses more calibrated intensity of review.\n\n"
                "Part II: Orthodoxy\n\n"
                "Wednesbury remains the historical baseline.\n\n"
                "Part III: Proportionality\n\n"
                "Structured review has expanded in rights contexts.\n\n"
                "Part IV: Conclusion\n\n"
                "Proportionality has grown, but not wholly displaced orthodoxy.\n\n"
                "(End of Answer)"
            ),
        },
        {"role": "user", "text": "continue"},
        {
            "role": "assistant",
            "text": (
                "Question 2: Equity and Trusts\n\n"
                "Part I: Introduction\n\n"
                "English law favours institutional certainty over remedial discretion.\n\n"
                "Part II: Institutional Model\n\n"
                "Westdeutsche anchors the orthodox resistance to remedial invention.\n\n"
                "Part III: Domestic Context\n\n"
                "Family-home cases preserve limited flexibility.\n\n"
                "Part IV: Conclusion\n\n"
                "The better view is to retain the institutional model.\n\n"
                "(End of Answer)"
            ),
        },
        {"role": "user", "text": "continue"},
    ]

    hist_explicit = [
        {"role": "user", "text": explicit_split},
        {
            "role": "assistant",
            "text": (
                "Part I: Introduction\n\n"
                "The first issue concerns beneficial ownership.\n\n"
                "Part II: Ownership and Quantification\n\n"
                "Stack and Jones frame the dispute.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
        {"role": "user", "text": "continue"},
        {
            "role": "assistant",
            "text": (
                "Part III: Sale and Advice\n\n"
                "TOLATA ss 14-15 guide any sale application.\n\n"
                "Part IV: Conclusion and Advice\n\n"
                "A sale is likely unless a buyout occurs.\n\n"
                "(End of Answer)"
            ),
        },
        {"role": "user", "text": "continue"},
    ]

    print("Short 2000 essay long-split flag:", detect_long_essay(short_essay).get("is_long_essay"))
    assert detect_long_essay(short_essay).get("is_long_essay") is False
    print("Short 1800 problem long-split flag:", detect_long_essay(short_problem).get("is_long_essay"))
    assert detect_long_essay(short_problem).get("is_long_essay") is False

    state_4000 = _expected_unit_structure_state_from_history("continue", hist_4000)
    print("Single 4000 continuation state:", state_4000)
    assert state_4000["is_same_topic_continuation"] is True
    assert state_4000["question_final_part"] is True
    assert state_4000["expected_part_number"] == 3
    assert _expected_internal_part_heading_from_history("continue", hist_4000) == 3
    assert _resolve_word_window_from_history("continue", hist_4000) == (1980, 2000)

    state_5500 = _expected_unit_structure_state_from_history("continue", hist_5500)
    print("Single 5500 continuation state:", state_5500)
    assert state_5500["is_same_topic_continuation"] is True
    assert state_5500["question_final_part"] is True
    assert state_5500["expected_part_number"] == 5
    assert _expected_internal_part_heading_from_history("continue", hist_5500) == 5

    state_mixed_p1 = _expected_unit_structure_state_from_history(mixed_4000, [])
    print("Mixed 4000 part 1 state:", state_mixed_p1)
    assert state_mixed_p1["question_index"] == 1
    assert state_mixed_p1["expected_part_number"] == 1
    assert state_mixed_p1["question_heading"].startswith("Question 1:")

    state_mixed_p2 = _expected_unit_structure_state_from_history("continue", hist_mixed_4000_p2)
    print("Mixed 4000 part 2 state:", state_mixed_p2)
    assert state_mixed_p2["question_index"] == 2
    assert state_mixed_p2["expected_part_number"] == 1
    assert state_mixed_p2["question_heading"].startswith("Question 2:")
    assert _current_unit_mode_from_history("continue", hist_mixed_4000_p2)["is_problem_mode"] is True

    state_6000_q3 = _expected_unit_structure_state_from_history("continue", hist_6000_q3)
    print("Three-question 6000 state:", state_6000_q3)
    assert state_6000_q3["question_index"] == 3
    assert state_6000_q3["expected_part_number"] == 1
    assert state_6000_q3["question_heading"].startswith("Question 3:")

    state_explicit = _expected_unit_structure_state_from_history("continue", hist_explicit)
    print("Explicit split section 2 state:", state_explicit)
    assert state_explicit["starts_new_question"] is True
    assert state_explicit["is_same_topic_continuation"] is False
    assert state_explicit["expected_part_number"] == 1
    assert state_explicit["question_final_part"] is False

    valid_mixed_q2_output = (
        "Question 2: Tort Law – Problem Question (Negligence and Psychiatric Harm)\n\n"
        "Part I: Introduction\n\n"
        "This problem concerns duty, psychiatric harm, and remoteness.\n\n"
        "Part II: Duty and Breach\n\n"
        "A. Issue\n\n"
        "The first issue is whether Maya owes a duty of care.\n\n"
        "B. Rule\n\n"
        "The claimant must establish foreseeability, proximity, and fairness.\n\n"
        "C. Application\n\n"
        "On these facts, proximity is likely present.\n\n"
        "D. Conclusion\n\n"
        "Duty is likely established.\n\n"
        "Will Continue to next part, say continue"
    )
    valid_mixed_q2_issues = _history_aware_structure_issues(
        valid_mixed_q2_output,
        "continue",
        hist_mixed_4000_p2,
    )
    print("Valid mixed Question 2 issues:", valid_mixed_q2_issues)
    assert not valid_mixed_q2_issues

    bad_q3_repeat = (
        "Question 2: Equity and Trusts\n\n"
        "Part I: Introduction\n\n"
        "English law favours institutional certainty over remedial discretion.\n\n"
        "Part II: Institutional Model\n\n"
        "Westdeutsche anchors the orthodox resistance to remedial invention.\n\n"
        "Part III: Domestic Context\n\n"
        "Family-home cases preserve limited flexibility.\n\n"
        "Part IV: Conclusion\n\n"
        "The better view is to retain the institutional model.\n\n"
        "(End of Answer)"
    )
    bad_q3_repeat_issues = _history_aware_structure_issues(
        bad_q3_repeat,
        "continue",
        hist_6000_q3,
    )
    print("Bad repeated Question 2 issues:", bad_q3_repeat_issues)
    assert any("wrong Question heading" in issue for issue in bad_q3_repeat_issues)
    assert any("repeat the previous question" in issue.lower() for issue in bad_q3_repeat_issues)

    print("All synthetic split smoke tests passed.")


if __name__ == "__main__":
    run()
