"""
Regression checks for long-response word-count planning consistency.
"""

from model_applicable_service import (
    LONG_RESPONSE_PART_WORD_CAP,
    _compute_equal_part_targets,
    _extract_split_units,
    detect_long_essay,
)
from word_count_rules import complete_word_count_window


def _base_label(label: str) -> str:
    return (label or "").split(" (Part ", 1)[0].strip().lower()


def run() -> None:
    print("=" * 80)
    print("WORD COUNT CONSISTENCY REGRESSION TESTS")
    print("=" * 80)

    # Single-target checks requested by user
    cases = {
        2000: {"is_long": False, "parts": 0},
        4000: {"is_long": True, "parts": 2},
        5000: {"is_long": True, "parts": 3},
        6000: {"is_long": True, "parts": 3},
    }
    for words, expected in cases.items():
        prompt = f"Write a {words} word essay on contract law."
        plan = detect_long_essay(prompt)
        print(
            f"{words} words -> is_long={plan['is_long_essay']} "
            f"parts={plan['suggested_parts']} mode={plan.get('split_mode')}"
        )
        assert plan["is_long_essay"] == expected["is_long"]
        assert plan["suggested_parts"] == expected["parts"]
        if plan["is_long_essay"]:
            deliverables = plan.get("deliverables") or []
            assert deliverables, "Long plan must expose deliverables with per-part targets"
            targets = [int(d.get("target_words", 0) or 0) for d in deliverables]
            assert all(1 <= t <= LONG_RESPONSE_PART_WORD_CAP for t in targets)
            assert sum(targets) == words, f"Targets must sum exactly to request ({sum(targets)} != {words})"

    assert complete_word_count_window(4000) == (3960, 4000)
    assert complete_word_count_window(1501) == (1486, 1501)

    # Exact current split for 5000 under the active part-target planner
    t5000 = _compute_equal_part_targets(5000, 3)
    print(f"5000 exact part targets: {t5000}")
    assert t5000 == [2000, 1500, 1500]
    assert sum(t5000) == 5000

    # Multi-target by-section sequencing
    multi_section_prompt = """
QUESTION 1
2500 words
QUESTION 2
2500 words
"""
    section_plan = detect_long_essay(multi_section_prompt)
    assert section_plan["split_mode"] == "by_section"
    sec = section_plan.get("deliverables") or []
    assert len(sec) == 4
    expected = [(1, 1, 2, 1250), (1, 2, 2, 1250), (2, 1, 2, 1250), (2, 2, 2, 1250)]
    actual = [
        (
            int(d.get("section_index", 0)),
            int(d.get("part_in_section", 0)),
            int(d.get("parts_in_section", 0)),
            int(d.get("target_words", 0)),
        )
        for d in sec
    ]
    print(f"By-section 2500+2500 plan: {actual}")
    assert actual == expected
    assert sum(v[3] for v in actual) == 5000

    # Multi-topic by-units anti-duplication planning: no oscillation A->B->A.
    multi_topic_prompt = """
CONTRACT LAW
ESSAY QUESTION: Critically evaluate penalties doctrine.

TORT LAW
PROBLEM QUESTION: Advise all parties on negligence.

5000 words
"""
    unit_plan = detect_long_essay(multi_topic_prompt)
    assert unit_plan["split_mode"] == "by_units"
    unit_deliverables = unit_plan.get("deliverables") or []
    unit_bases = [_base_label((d.get("unit_labels") or [""])[0]) for d in unit_deliverables]
    print(f"By-units bases: {unit_bases}")
    assert sum(int(d.get("target_words", 0) or 0) for d in unit_deliverables) == 5000
    assert all(
        int(d.get("target_words", 0) or 0) <= LONG_RESPONSE_PART_WORD_CAP for d in unit_deliverables
    )
    for i in range(2, len(unit_bases)):
        assert not (
            unit_bases[i] == unit_bases[i - 2] and unit_bases[i] != unit_bases[i - 1]
        ), "Oscillating topic order can re-trigger duplicate-part generation"

    # Single total word count + explicit Question headings must still split by question.
    plain_multi_question_prompt = """
6000 words

Question 1: Administrative Law
Discuss whether modern judicial review means the courts now decide merits rather than legality.

Question 2: Equity and Trusts
Discuss whether English law prioritises certainty over fairness in constructive trusts.

Question 3: Problem Question
Ahmed, Beth and Chris dispute ownership and sale of a home. Advise them.
"""
    plain_units = _extract_split_units(plain_multi_question_prompt)
    print(f"Plain Question-heading units: {[u.get('question_title') for u in plain_units]}")
    assert len(plain_units) == 3
    assert [str(u.get("kind") or "") for u in plain_units] == ["essay", "essay", "problem"]

    plain_plan = detect_long_essay(plain_multi_question_prompt)
    print(
        f"Plain Question-heading 6000 plan: mode={plain_plan.get('split_mode')} "
        f"parts={plain_plan.get('suggested_parts')}"
    )
    assert plain_plan["split_mode"] == "by_units"
    assert plain_plan["suggested_parts"] == 3
    plain_deliverables = plain_plan.get("deliverables") or []
    assert [int(d.get("target_words", 0) or 0) for d in plain_deliverables] == [2000, 2000, 2000]
    assert [int(d.get("question_index", 0) or 0) for d in plain_deliverables] == [1, 2, 3]

    # Static contradiction check in current runtime source
    with open("model_applicable_service.py", "r", encoding="utf-8") as fh:
        src = fh.read()
    assert "Do not intentionally exceed {words_per_part + 100} words." not in src

    print("All consistency checks passed.")


if __name__ == "__main__":
    run()
