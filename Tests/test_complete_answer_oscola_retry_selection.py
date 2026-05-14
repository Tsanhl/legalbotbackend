import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backend_answer_runtime as runtime


captured_calls = []

uncited_answer = """
Part I: Introduction

The claimant has a strong proprietary claim and the purchaser is at risk.

Part II: Analysis

The law requires priority to be assessed by classifying the right first. The purchaser should then ask whether the right is registered, overriding, or overreachable.

Part III: Conclusion

The purchaser faces material risk.

(End of Answer)
""".strip()

cited_answer = """
Part I: Introduction

The claimant has a strong proprietary claim and the purchaser is at risk because registered-land priority depends first on the nature of the interest and then on protection or overriding status (Land Registration Act 2002, ss 28-29).

Part II: Analysis

A beneficial interest under a trust may bind a disponee where coupled with actual occupation unless it is overreached by payment to two trustees (Law of Property Act 1925, ss 2, 27; Land Registration Act 2002, sch 3 para 2). Short legal leases can also override without a register entry where the statutory conditions are met (Land Registration Act 2002, sch 3 para 1).

Part III: Conclusion

The purchaser's safest route is to require valid overreaching, inspect occupation, and obtain releases or retentions for non-overreachable rights (Law of Property Act 1925, ss 2, 27).

(End of Answer)
""".strip()


provider_responses = [
    ((uncited_answer, ["uncited-meta"]), "Authority: Land Registration Act 2002."),
    ((cited_answer, ["cited-meta"]), "Authority: Land Registration Act 2002."),
]


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
    idx = min(len(captured_calls) - 1, len(provider_responses) - 1)
    return provider_responses[idx]


def fake_strict_complete_answer_issues(
    answer_text,
    prompt_text,
    messages,
    *,
    enforce_long_response_split,
    rag_context=None,
):
    if answer_text == uncited_answer:
        return [
            "Argumentative sentence-support verification failed: 3 argumentative sentence(s) lack immediate inline authority support.",
            "Inline OSCOLA citation density is too thin for the length of the answer (0 citation parentheticals; expected at least 3).",
        ]
    return []


original_provider = runtime._provider_send_message_with_docs
original_issue_checker = runtime._strict_complete_answer_issues
try:
    runtime._provider_send_message_with_docs = fake_provider_send_message_with_docs
    runtime._strict_complete_answer_issues = fake_strict_complete_answer_issues

    (response_text, response_meta), rag_context = runtime.send_complete_answer_with_docs(
        api_key="",
        message=(
            "Land Law — Problem Question\n\n"
            "Advise the purchaser on registered-land priority.\n\n"
            "1500 words."
        ),
        documents=[],
        project_id="oscola-retry-selection",
        history=[],
        stream=False,
    )
finally:
    runtime._provider_send_message_with_docs = original_provider
    runtime._strict_complete_answer_issues = original_issue_checker


assert len(captured_calls) == 2
assert "[BACKEND STRICT COMPLETE-ANSWER REWRITE]" in captured_calls[1]
assert "Do NOT solve citation risk by deleting citations" in captured_calls[1]
assert response_text == cited_answer
assert response_meta == ["cited-meta"]
assert rag_context == "Authority: Land Registration Act 2002."
