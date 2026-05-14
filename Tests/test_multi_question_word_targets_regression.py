import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backend_answer_runtime as runtime
import model_applicable_service as service


PROMPT = """
1. Law and Medicine — Problem Question

Word target: about 2,000–2,500 words

Maya, a 46-year-old teacher, is diagnosed with an aggressive but treatable form of cancer.
Advise Maya and the hospital on consent, fertility preservation, causation, recoverable loss,
defences, and remedies.

2. Evidence Law — Problem Question

Word target: about 2,000–2,500 words

Kai is charged with robbery after a masked person enters a convenience store. Advise on
identification, CCTV, confession evidence, silence, hearsay, bad character, exclusionary
discretion, Article 6 fairness, and the overall strength of the prosecution case.
""".strip()


def _pad_to_exact_word_count(text: str, target: int) -> str:
    out = text.strip() + "\n\n"
    while runtime._count_words(out) < target:
        out += " analysis."
    return out


def _full_problem_block(question_no: int, heading: str, target: int = 2500) -> str:
    base = f"""
Question {question_no}: {heading}

Part I: Introduction

Part II: Main Issue

A. Issue

B. Rule

C. Application

D. Conclusion

Part III: Remedies / Liability

Part IV: Final Conclusion
""".strip()
    return _pad_to_exact_word_count(base, target)


def test_repeated_word_ranges_are_per_question_targets_for_direct_backend() -> None:
    parsed = service.extract_word_targets_from_prompt(PROMPT, min_words=500)
    assert parsed["active_targets"] == [2500, 2500]
    assert parsed["requested_words"] == 5000

    direct = service._resolve_long_response_info(PROMPT, enforce_long_response_split=False)
    assert direct["requested_words"] == 5000
    assert direct["word_targets"] == [2500, 2500]
    assert direct["is_long_essay"] is False

    units = service._extract_units_with_text(PROMPT)
    assert [u["kind"] for u in units] == ["problem", "problem"]
    assert [u["question_index"] for u in units] == [1, 2]

    chunks = service.get_dynamic_chunk_count(PROMPT, enforce_long_response_split=False)
    assert chunks == 56


def test_direct_backend_never_uses_website_split_retrieval_plan() -> None:
    assert service._should_narrow_rag_to_split_deliverable(  # type: ignore[attr-defined]
        enforce_long_response_split=False,
        is_internal_control_prompt=False,
        continuation_for_rag={"is_continuation": False},
    ) is False
    assert service._should_narrow_rag_to_split_deliverable(  # type: ignore[attr-defined]
        enforce_long_response_split=True,
        is_internal_control_prompt=False,
        continuation_for_rag={"is_continuation": False},
    ) is True
    assert service._should_narrow_rag_to_split_deliverable(  # type: ignore[attr-defined]
        enforce_long_response_split=False,
        is_internal_control_prompt=False,
        continuation_for_rag={"is_continuation": True},
    ) is True


def test_direct_backend_chunk_budget_scales_with_single_requested_word_target() -> None:
    expected = [
        (800, 10),
        (1200, 14),
        (2000, 20),
        (2500, 26),
        (4000, 36),
        (5000, 44),
        (6000, 52),
        (7500, 60),
        (10000, 70),
    ]
    for words, chunks in expected:
        assert service._chunk_count_for_requested_words(words, query_type="essay") == chunks  # type: ignore[attr-defined]
        assert service._chunk_count_for_requested_words(words, query_type="pb_1500") == min(90, chunks + 2)  # type: ignore[attr-defined]


def test_direct_backend_chunk_budget_sums_per_question_targets() -> None:
    total, per_counts, unit_types = service._chunk_counts_for_requested_word_targets(  # type: ignore[attr-defined]
        PROMPT,
        [2500, 2500],
        query_type="pb_1500",
    )
    assert unit_types == ["pb", "pb"]
    assert per_counts == [28, 28]
    assert total == 56


def test_backend_rejects_condensed_combined_multi_question_answers() -> None:
    no_question_headings = _pad_to_exact_word_count(
        """
Part I: Introduction

Part II: Consent and Evidence

Part III: Final Conclusion
""",
        900,
    )
    missing_heading_issues = runtime._multi_question_complete_answer_issues(no_question_headings, PROMPT)
    assert any("separate Question headings" in issue for issue in missing_heading_issues)

    condensed = "\n\n".join([
        _full_problem_block(1, "Law and Medicine — Problem Question", target=900),
        _full_problem_block(2, "Evidence Law — Problem Question", target=900),
        "(End of Answer)",
    ])
    condensed_issues = runtime._multi_question_complete_answer_issues(condensed, PROMPT)
    assert any("Question 1 under-delivers" in issue for issue in condensed_issues)
    assert any("Question 2 under-delivers" in issue for issue in condensed_issues)


def test_backend_accepts_separate_blocks_at_each_requested_target() -> None:
    full_answer = "\n\n".join([
        _full_problem_block(1, "Law and Medicine — Problem Question", target=2500),
        _full_problem_block(2, "Evidence Law — Problem Question", target=2500),
        "(End of Answer)",
    ])
    assert runtime._multi_question_complete_answer_issues(full_answer, PROMPT) == []
    assert runtime._direct_complete_answer_structure_issues(full_answer, PROMPT, []) == []
    essay_shape_issues = runtime._essay_quality_issues(
        full_answer,
        PROMPT,
        is_short_single_essay=False,
        is_problem_mode=True,
    )
    assert not any("Part numbering regresses" in issue for issue in essay_shape_issues)


if __name__ == "__main__":
    test_repeated_word_ranges_are_per_question_targets_for_direct_backend()
    test_direct_backend_never_uses_website_split_retrieval_plan()
    test_direct_backend_chunk_budget_scales_with_single_requested_word_target()
    test_direct_backend_chunk_budget_sums_per_question_targets()
    test_backend_rejects_condensed_combined_multi_question_answers()
    test_backend_accepts_separate_blocks_at_each_requested_target()
    print("Multi-question word target regression tests passed.")
