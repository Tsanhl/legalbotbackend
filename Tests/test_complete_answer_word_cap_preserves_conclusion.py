import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backend_answer_runtime as runtime


def _long_complete_answer() -> str:
    intro = "Part I: Introduction\n\nThis answer starts with a thesis and applies the legal test."
    body_sentence = (
        "The analysis applies the rule to the facts and ranks the likely outcome."
    )
    body = " ".join([body_sentence] * 245)
    conclusion = (
        "Part V: Conclusion\n\n"
        "The final answer is that the claimant has the stronger route, the defendant has a narrow counterargument, "
        "and the practical outcome is a declaration plus damages rather than an injunction.\n\n"
        "(End of Answer)"
    )
    return f"{intro}\n\nPart II: Analysis\n\n{body}\n\n{conclusion}"


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
    captured_calls.append(message)
    return ((_long_complete_answer(), ["meta"]), "Authority: test")


def fake_strict_complete_answer_issues(
    answer_text,
    prompt_text,
    messages,
    *,
    enforce_long_response_split,
    rag_context=None,
):
    if "Part V: Conclusion" not in (answer_text or ""):
        return [
            "No visible concluding section.",
            "Answer ends abruptly or with an incomplete final sentence.",
        ]
    return ["Answer exceeds the strict complete-answer word window (1800 words; cap is 1500)."]


original_provider = runtime._provider_send_message_with_docs
original_issue_checker = runtime._strict_complete_answer_issues
try:
    runtime._provider_send_message_with_docs = fake_provider_send_message_with_docs
    runtime._strict_complete_answer_issues = fake_strict_complete_answer_issues

    (response_text, response_meta), rag_context = runtime.send_complete_answer_with_docs(
        api_key="",
        message=(
            "Land Law — Essay Question\n\n"
            "Critically evaluate priority in registered land.\n\n"
            "1500 words."
        ),
        documents=[],
        project_id="word-cap-preserves-conclusion",
        history=[],
        stream=False,
    )
finally:
    runtime._provider_send_message_with_docs = original_provider
    runtime._strict_complete_answer_issues = original_issue_checker


assert len(captured_calls) == 3
assert "Part V: Conclusion" in response_text
assert "practical outcome" in response_text
assert response_text.strip().endswith("(End of Answer)")
assert response_meta == ["meta"]
assert rag_context == "Authority: test"
