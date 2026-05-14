import os

import model_applicable_service as service


captured_prompts = []


def fake_rag(query, max_chunks=None, query_type=None):
    return (
        "[RAG CONTEXT - INTERNAL - DO NOT OUTPUT]\n"
        "Authority: Occupiers' Liability Act 1957; Occupiers' Liability Act 1984.\n"
        "[END RAG CONTEXT]"
    )


def fake_local_codex_adapter(
    *,
    full_message,
    system_instruction,
    history,
    project_id,
    allow_web_search,
):
    captured_prompts.append(
        {
            "full_message": full_message,
            "system_instruction": system_instruction,
            "history": history,
            "project_id": project_id,
            "allow_web_search": allow_web_search,
        }
    )
    return (
        "Part I: Introduction\n\n"
        "The compiled prompt uses the default RAG and code-guide policy.\n\n"
        "Part II: Conclusion\n\n"
        "(End of Answer)"
    )


def run_case(message, expected_snippets):
    captured_prompts.clear()
    (response, meta), rag_context = service.send_message_with_docs(
        api_key="",
        message=message,
        documents=[],
        project_id="default-rag-guide-policy",
        history=[],
        stream=False,
        provider="auto",
        model_name=None,
        enforce_long_response_split=False,
    )

    assert meta == []
    assert "Part I: Introduction" in response
    assert "Occupiers' Liability Act" in rag_context
    assert len(captured_prompts) == 1
    full_message = captured_prompts[0]["full_message"]
    assert "[DIRECT-CODE / BACKEND DELIVERY MODE]" in full_message
    assert "[LOCAL CODE + RAG LEGAL ANSWER MODE]" in full_message
    assert "[MANDATORY BACKEND RAG POLICY]" in full_message
    assert "Use indexed RAG material first." in full_message
    assert "Complete-answer requests must run the Codex supervisor workflow" in full_message
    assert "Shared legal backend guide anchors:" in full_message
    for snippet in expected_snippets:
        assert snippet in full_message


original_rag_available = service.RAG_AVAILABLE
original_get_relevant_context = service.get_relevant_context
original_find_codex_cli = service._find_codex_cli
original_codex_exec_supports_option = service._codex_exec_supports_option
original_local_adapter = service._generate_with_codex_local_adapter
original_env = os.environ.get("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED")
original_assume_env = os.environ.get("LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE")

try:
    service.RAG_AVAILABLE = True
    service.get_relevant_context = fake_rag
    service._find_codex_cli = lambda: "codex"
    service._codex_exec_supports_option = lambda _cli, option: option == "--search"
    service._generate_with_codex_local_adapter = fake_local_codex_adapter
    os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = "1"
    os.environ["LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"] = "1"

    run_case(
        "Write a 1200 word essay any topic.",
        ["TORT LAW: Occupiers", "Matched subject guide anchors:"],
    )
    run_case(
        "Land registered priority problem: advise the buyer.",
        ["registered priority problem", "Matched subject guide anchors:"],
    )
finally:
    service.RAG_AVAILABLE = original_rag_available
    service.get_relevant_context = original_get_relevant_context
    service._find_codex_cli = original_find_codex_cli
    service._codex_exec_supports_option = original_codex_exec_supports_option
    service._generate_with_codex_local_adapter = original_local_adapter
    if original_env is None:
        os.environ.pop("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED", None)
    else:
        os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = original_env
    if original_assume_env is None:
        os.environ.pop("LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE", None)
    else:
        os.environ["LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"] = original_assume_env


print("Default backend RAG + code-guide policy checks passed.")
