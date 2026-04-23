"""
Regression checks for dedicated MCQ correction/generation workflow prompts.
"""

from model_applicable_service import (
    _build_mcq_workflow_override_block,
    _build_mcq_workflow_prompt_block,
    detect_mcq_workflow_request,
)


def run() -> None:
    correction_prompt = """correct me set 25

Question 1 – Contract / Common mistake / allocation of risk

Question
A collector contracts to buy a painting described by both parties during negotiations as “an original work by X.”

Which statement best reflects the strongest analysis?

A. The contract is automatically void because both parties shared the same mistaken assumption about authenticity.
B. A common mistake claim succeeds whenever the subject matter is worth materially less than both parties believed.
C. A common mistake claim is much weaker where the contract itself allocates the relevant risk to one party.
D. The contract is only voidable, not void, because the mistake concerns quality rather than identity.
E. The buyer can avoid the contract only if it proves the seller knew of the forgery.

My answer: C
Result: Correct
Correct answer: C
"""

    correction_mode = detect_mcq_workflow_request(correction_prompt)
    assert correction_mode["active"] is True, correction_mode
    assert correction_mode["mode"] == "correction", correction_mode
    assert correction_mode["question_count"] == 1, correction_mode
    assert correction_mode["response_detail"] == "full_explanations", correction_mode

    correction_block = _build_mcq_workflow_prompt_block(correction_mode, citation_style="oscola")
    assert "[MCQ QUESTION-SET CORRECTION MODE]" in correction_block
    assert "Corrected overall result" in correction_block
    assert "My answer: X" in correction_block
    assert "Correct answer: X" in correction_block
    assert "Knowledge point tested" in correction_block
    assert "Do NOT add legal citations by default in this correction format." in correction_block

    correction_override = _build_mcq_workflow_override_block(correction_mode)
    assert "[MCQ WORKFLOW OVERRIDE — HIGHEST PRIORITY]" in correction_override
    assert "Do NOT output `Part I: Introduction`" in correction_override
    assert "question blocks only" in correction_override

    generation_prompt = "Give me 15 SQE contract law MCQs. No repeated questions with previous sets. Questions only."
    generation_mode = detect_mcq_workflow_request(generation_prompt)
    assert generation_mode["active"] is True, generation_mode
    assert generation_mode["mode"] == "generation", generation_mode
    assert generation_mode["question_count"] == 15, generation_mode
    assert generation_mode["sqe_requested"] is True, generation_mode
    assert generation_mode["no_repeat_requested"] is True, generation_mode
    assert generation_mode["response_detail"] == "questions_only", generation_mode

    generation_block = _build_mcq_workflow_prompt_block(generation_mode, citation_style="oscola")
    assert "[MCQ GENERATION MODE]" in generation_block
    assert "Generate exactly 15 MCQ question(s)." in generation_block
    assert "Do not reuse or lightly reword questions" in generation_block
    assert "Default output for a test-only MCQ request is questions only." in generation_block
    assert "Question 1 – [topic / subtopic / issue]" in generation_block

    print("MCQ workflow prompt regression checks passed.")


if __name__ == "__main__":
    run()
