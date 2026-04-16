import backend_answer_runtime as runtime


assert runtime.resolve_backend_answer_output_mode(
    "Please return this directly in chat."
) == runtime.BACKEND_ANSWER_OUTPUT_CHAT
assert runtime.resolve_backend_answer_output_mode(
    "Please give me the answer in markdown."
) == runtime.BACKEND_ANSWER_OUTPUT_MARKDOWN
assert runtime.resolve_backend_answer_output_mode(
    "Save it as .md after answering."
) == runtime.BACKEND_ANSWER_OUTPUT_MARKDOWN

direct_window = runtime._resolve_complete_answer_word_window(
    "Write a 4500 word essay on public law.",
    [],
    enforce_long_response_split=False,
)
split_window = runtime._resolve_complete_answer_word_window(
    "Write a 4500 word essay on public law.",
    [],
    enforce_long_response_split=True,
)
assert direct_window == (4455, 4500)
assert split_window is not None
assert split_window[1] < direct_window[1]

issues = runtime._strict_complete_answer_issues(
    "Part I: Introduction\n\nThis answer is very short and only discusses illegality.\n\n(End of Answer)",
    """Public Law — Essay Question

Critically evaluate whether judicial review is constitutionally legitimate.

In your answer, consider:

illegality,
irrationality,
procedural unfairness,
legitimate expectation,
and proportionality.

2000 words.""",
    [],
    enforce_long_response_split=False,
)
assert any("strict complete-answer word window" in issue.lower() for issue in issues)
assert any("prompt-map asks appear under-covered" in issue.lower() for issue in issues)


captured_calls = []
provider_responses = [
    (("FIRST DRAFT", ["first-meta"]), "Authority: Judicial Review and Courts Act 2022."),
    (("SECOND DRAFT", ["second-meta"]), "Authority: Judicial Review and Courts Act 2022."),
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
    captured_calls.append(
        {
            "message": message,
            "stream": stream,
            "provider": provider,
            "enforce_long_response_split": enforce_long_response_split,
        }
    )
    idx = min(len(captured_calls) - 1, len(provider_responses) - 1)
    return provider_responses[idx]


def fake_strict_complete_answer_issues(
    answer_text,
    prompt_text,
    messages,
    *,
    enforce_long_response_split,
):
    if answer_text == "FIRST DRAFT":
        return [
            "Answer is below the strict complete-answer word window (1200 words; need at least 1980).",
            "Prompt-map asks appear under-covered: irrationality; procedural unfairness",
        ]
    return []


original_provider = runtime._provider_send_message_with_docs
original_issue_checker = runtime._strict_complete_answer_issues
try:
    runtime._provider_send_message_with_docs = fake_provider_send_message_with_docs
    runtime._strict_complete_answer_issues = fake_strict_complete_answer_issues

    (response_text, response_meta), rag_context = runtime.send_complete_answer_with_docs(
        api_key="",
        message="""Public Law — Essay Question

Critically evaluate whether judicial review in England and Wales strikes an appropriate balance between protecting individuals from unlawful public power and respecting democratic decision-making by Parliament and the executive.

In your answer, consider:

the constitutional foundations of judicial review,
illegality, irrationality, and procedural unfairness,
the role of legitimate expectation,
proportionality and its relationship with traditional grounds of review,
the impact of the Human Rights Act 1998,
judicial deference or restraint in matters of policy, resources, and national security,
and whether the modern law of judicial review is principled, coherent, and constitutionally legitimate.

2000 words.""",
        documents=[],
        project_id="proj",
        history=[],
        stream=False,
    )
finally:
    runtime._provider_send_message_with_docs = original_provider
    runtime._strict_complete_answer_issues = original_issue_checker

assert len(captured_calls) == 2
assert captured_calls[0]["enforce_long_response_split"] is False
assert "[BACKEND STRICT COMPLETE-ANSWER REWRITE]" in captured_calls[1]["message"]
assert "strict complete-answer window: 1980-2000 words" in captured_calls[1]["message"]
assert response_text == "SECOND DRAFT"
assert response_meta == ["second-meta"]
assert "Authority:" in rag_context

print("Backend runtime complete-answer entrypoint checks passed.")
