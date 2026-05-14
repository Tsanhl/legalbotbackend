"""
Regression checks for SQE2 written-skill guide and marking prompts.
"""

import backend_answer_runtime as runtime


def run() -> None:
    guide_prompt = runtime.build_sqe2_written_guide_prompt(
        "Give me a guide for SQE2 legal research answers and marking.",
        skill="legal research",
    )
    assert "SQE2 has 12 written stations over three half-days." in guide_prompt
    assert "Each written day contains one case/matter analysis, one legal drafting, one legal research, and one legal writing assessment." in guide_prompt
    assert "Selected skill: Legal research" in guide_prompt
    assert "Timing: 60 minutes" in guide_prompt
    assert "Identify and use relevant sources and information." in guide_prompt
    assert "For legal research, require selective use of provided sources and key source citation" in guide_prompt
    assert runtime.SQE_RAG_SEARCH_POLICY_LINE in guide_prompt

    writing_task_prompt = runtime.build_sqe_question_set_prompt(
        "Give me an SQE2 legal writing task like the sample but harder.",
        exam_stage="sqe2",
    )
    assert "Selected written skill: Legal writing" in writing_task_prompt
    assert "Skill timing: 30 minutes" in writing_task_prompt
    assert "Include relevant facts." in writing_task_prompt
    assert "Use a logical structure." in writing_task_prompt
    assert "mark it criterion-by-criterion using the SQE2 written-skills A-F scale" in writing_task_prompt
    assert runtime.SQE_RAG_SEARCH_POLICY_LINE in writing_task_prompt

    marking_prompt = runtime.build_sqe2_marking_prompt(
        question="SQE2 legal research task: advise whether the prosecution can compel a spouse to give evidence.",
        candidate_answer="Sara is competent but not compellable because the assault was not against her.",
        skill="legal research",
        practice_area="Criminal Litigation",
    )
    assert "[BACKEND SQE2 WRITTEN ANSWER MARKING MODE]" in marking_prompt
    assert "Skill to mark: Legal research" in marking_prompt
    assert "A = 5" in marking_prompt
    assert "F = 0" in marking_prompt
    assert "Skills subtotal" in marking_prompt
    assert "Application of law subtotal" in marking_prompt
    assert "provided sources selectively" in marking_prompt
    assert runtime.SQE_RAG_SEARCH_POLICY_LINE in marking_prompt

    captured_calls = []

    def fake_provider_send_message_with_docs(
        api_key,
        message,
        documents,
        project_id,
        history=None,
        stream=False,
        provider="auto",
        model_name=None,
        enforce_long_response_split=False,
    ):
        captured_calls.append(
            {
                "message": message,
                "documents": documents,
                "project_id": project_id,
                "enforce_long_response_split": enforce_long_response_split,
            }
        )
        return ("SQE2 marking result", ["meta"]), "RAG context"

    def fail_if_complete_answer_checker_runs(*args, **kwargs):
        raise AssertionError("SQE2 marking must not run essay complete-answer verification.")

    original_provider = runtime._provider_send_message_with_docs
    original_issue_checker = runtime._strict_complete_answer_issues
    try:
        runtime._provider_send_message_with_docs = fake_provider_send_message_with_docs
        runtime._strict_complete_answer_issues = fail_if_complete_answer_checker_runs
        (response_text, response_meta), rag_context = runtime.send_sqe2_marking_with_docs(
            api_key="",
            question="SQE2 legal writing task: draft an email to the client.",
            candidate_answer="Dear client, you should serve notice. Regards.",
            project_id="sqe2-mark",
            skill="legal writing",
            include_default_samples=False,
        )
    finally:
        runtime._provider_send_message_with_docs = original_provider
        runtime._strict_complete_answer_issues = original_issue_checker

    assert response_text == "SQE2 marking result"
    assert response_meta == ["meta"]
    assert rag_context == "RAG context"
    assert len(captured_calls) == 1
    assert captured_calls[0]["project_id"] == "sqe2-mark"
    assert captured_calls[0]["enforce_long_response_split"] is False
    assert "Skill to mark: Legal writing" in captured_calls[0]["message"]

    def refusal_provider_send_message_with_docs(
        api_key,
        message,
        documents,
        project_id,
        history=None,
        stream=False,
        provider="auto",
        model_name=None,
        enforce_long_response_split=False,
    ):
        return ("No SQE2 task was provided. Please provide facts.", []), "RAG context"

    original_provider = runtime._provider_send_message_with_docs
    try:
        runtime._provider_send_message_with_docs = refusal_provider_send_message_with_docs
        repaired_task, _ = runtime.send_sqe_question_set_with_docs(
            api_key="",
            enquiry="Give me an SQE2 legal research task, harder than the sample, in Dispute Resolution.",
            project_id="sqe2-task-repair",
            exam_stage="sqe2",
            include_default_samples=False,
        )
    finally:
        runtime._provider_send_message_with_docs = original_provider

    assert "Candidate instructions" in repaired_task
    assert "Client/matter facts" in repaired_task
    assert "Documents/extracts" in repaired_task
    assert "Specific task" in repaired_task
    assert "Assessment traps" in repaired_task
    assert "Model answer" not in repaired_task
    assert "marking points" not in repaired_task.lower()
    assert len(repaired_task.split()) > 300

    try:
        runtime._provider_send_message_with_docs = refusal_provider_send_message_with_docs
        repaired_writing, _ = runtime.send_sqe2_marking_with_docs(
            api_key="",
            question=(
                "SQE2 legal writing task: Write a client email. Contracts exchanged on a house purchase. "
                "Completion was due yesterday. The buyer was ready but the seller failed to complete. "
                "Explain notice to complete, compensation, specific performance and next steps."
            ),
            candidate_answer="Dear Client, the seller breached. You can sue and get all your costs.",
            project_id="sqe2-writing-repair",
            skill="legal writing",
            practice_area="Property Practice",
            include_default_samples=False,
        )
        repaired_case, _ = runtime.send_sqe2_marking_with_docs(
            api_key="",
            question=(
                "SQE2 case and matter analysis task: A private company with Model Articles has two directors/shareholders. "
                "One director caused the company to buy equipment from a company owned by that director's spouse for 90000. "
                "No board minutes or shareholder approval are found."
            ),
            candidate_answer="The company can buy it because the director owns most shares.",
            project_id="sqe2-case-repair",
            skill="case and matter analysis",
            practice_area="Business Organisations, Rules and Procedures",
            include_default_samples=False,
        )
    finally:
        runtime._provider_send_message_with_docs = original_provider

    assert "notice to complete" in repaired_writing.lower()
    assert "specific performance" in repaired_writing.lower()
    assert "spouse evidence" not in repaired_writing.lower()
    assert "substantial-property" in repaired_case.lower() or "substantial property" in repaired_case.lower()
    assert "client identity" in repaired_case.lower()
    assert "spouse evidence" not in repaired_case.lower()

    print("SQE2 written guide and marking checks passed.")


if __name__ == "__main__":
    run()
