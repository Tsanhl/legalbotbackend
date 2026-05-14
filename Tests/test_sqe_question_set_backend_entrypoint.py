"""
Regression checks for the dedicated backend SQE question-set entrypoint.
"""

import base64
import tempfile
from pathlib import Path

import backend_answer_runtime as runtime
from model_applicable_service import detect_mcq_workflow_request


def _valid_sqe1_set(count: int = 20) -> str:
    blocks = []
    for i in range(1, count + 1):
        blocks.append(
            "\n".join(
                [
                    f"Question {i} - Contract / formation / offer",
                    "Question",
                    "Which statement best reflects the legal position on the facts?",
                    "A. The claimant has the strongest argument because the offer was accepted before withdrawal.",
                    "B. The claimant fails because every commercial negotiation is automatically non-binding.",
                    "C. The defendant succeeds because silence always amounts to rejection in contract law.",
                    "D. The defendant succeeds because consideration is never needed in business contracts.",
                    "E. Both parties are bound only if the agreement was executed as a deed.",
                ]
            )
        )
    return "\n\n".join(blocks)


def run() -> None:
    prompt = runtime.build_sqe_question_set_prompt(
        "Give me set 24 FLK1 using the sample style, much more difficult than real FLK1, no repeat with previous sets 1-23.",
    )
    assert "[BACKEND SQE QUESTION-SET GENERATION]" in prompt
    assert "Exam track: SQE1 FLK1" in prompt
    assert "Set number: 24" in prompt
    assert "Question count: exactly 20" in prompt
    assert "correct answer must not be routinely longer" in prompt.lower()
    assert "Output route: chat/API response body only." in prompt
    assert runtime.SQE_RAG_SEARCH_POLICY_LINE in prompt

    sqe2_prompt = runtime.build_sqe_question_set_prompt(
        "Give me an SQE2 legal writing task like the sample but harder.",
        exam_stage="sqe2",
    )
    assert "[BACKEND SQE2 PRACTICAL TASK GENERATION]" in sqe2_prompt
    assert "Generate SQE2 assessment-style practical task(s), not an essay and not an SQE1 objective-test set." in sqe2_prompt
    assert "Task count: exactly 1" in sqe2_prompt
    assert runtime.SQE_RAG_SEARCH_POLICY_LINE in sqe2_prompt
    assert detect_mcq_workflow_request(sqe2_prompt)["active"] is False

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
        return (_valid_sqe1_set(), ["meta"]), "Authority context"

    def fail_if_complete_answer_checker_runs(*args, **kwargs):
        raise AssertionError("SQE question-set entrypoint must not run complete-answer essay verification.")

    original_provider = runtime._provider_send_message_with_docs
    original_issue_checker = runtime._strict_complete_answer_issues
    try:
        runtime._provider_send_message_with_docs = fake_provider_send_message_with_docs
        runtime._strict_complete_answer_issues = fail_if_complete_answer_checker_runs
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_path = Path(tmpdir) / "sqe1-flk1-sample-questions-updated-01-april-25.pdf"
            sample_bytes = b"%PDF-1.4 fake sqe sample"
            sample_path.write_bytes(sample_bytes)

            (response_text, response_meta), rag_context = runtime.send_sqe_question_set_with_docs(
                api_key="",
                enquiry="Give me set 24 FLK1 using the sample style, much more difficult than sample, no repeat.",
                documents=[],
                project_id="proj-sqe",
                provider="openai",
                sample_pdf_paths=[str(sample_path)],
                include_default_samples=False,
            )
    finally:
        runtime._provider_send_message_with_docs = original_provider
        runtime._strict_complete_answer_issues = original_issue_checker

    assert response_text == _valid_sqe1_set()
    assert response_meta == ["meta"]
    assert rag_context == "Authority context"
    assert len(captured_calls) == 1
    call = captured_calls[0]
    assert call["project_id"] == "proj-sqe"
    assert call["enforce_long_response_split"] is False
    assert "[BACKEND SQE QUESTION-SET GENERATION]" in call["message"]
    assert "Set number: 24" in call["message"]
    assert "Output route: chat/API response body only." in call["message"]
    assert len(call["documents"]) == 1
    sample_doc = call["documents"][0]
    assert sample_doc["mimeType"] == "application/pdf"
    assert sample_doc["name"] == "sqe1-flk1-sample-questions-updated-01-april-25.pdf"
    assert base64.b64decode(sample_doc["data"]) == sample_bytes

    malformed = "Question 1 - Contract\nQuestion\nBad stem\nA. Short\nB. Short\nC. Short\nD. Short\nD. Duplicate"
    issues = runtime._sqe1_question_set_issues(malformed, expected_count=1, wants_answers=False)
    assert any("A-E option sequence" in issue for issue in issues)

    print("SQE backend question-set entrypoint checks passed.")


if __name__ == "__main__":
    run()
