import base64
import io
import os
import zipfile

import backend_answer_runtime as runtime
import model_applicable_service as service
from legal_doc_tools import workflow


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _minimal_docx_payload() -> str:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{WORD_NS}">
  <w:body>
    <w:p><w:r><w:t>Question: Advise on a legal issue.</w:t></w:r></w:p>
    <w:p><w:r><w:t>This draft needs legal amendment.</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


original_env = {
    key: os.environ.get(key)
    for key in [
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "XAI_API_KEY",
        "CODEX_SANDBOX_NETWORK_DISABLED",
        "LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED",
        "LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE",
        "LEGAL_AI_ENABLE_INTERACTIVE_CODEX_HANDOFF",
        "LEGAL_AI_REQUIRE_ONLINE_VERIFICATION",
        "BRAVE_SEARCH_API_KEY",
        "GOOGLE_CSE_API_KEY",
        "GOOGLE_CUSTOM_SEARCH_API_KEY",
        "GOOGLE_CSE_ID",
        "GOOGLE_CUSTOM_SEARCH_ENGINE_ID",
        "GOOGLE_SEARCH_ENGINE_ID",
        "SERPAPI_API_KEY",
        "TAVILY_API_KEY",
        "LEGAL_AI_ALLOW_KEYLESS_JINA_SEARCH",
        "LEGAL_AI_ONLINE_SEARCH_PROVIDER",
    ]
}
original_rag_available = service.RAG_AVAILABLE
original_get_relevant_context = service.get_relevant_context
original_find_codex_cli = service._find_codex_cli
original_codex_supports_option = service._codex_exec_supports_option
original_generate_with_codex = service._generate_with_codex_local_adapter
original_provider_send = runtime._provider_send_message_with_docs
original_strict_issues = runtime._strict_complete_answer_issues
original_workflow_send = workflow.send_message_with_docs

try:
    for key in original_env:
        os.environ.pop(key, None)
    os.environ["CODEX_SANDBOX_NETWORK_DISABLED"] = "1"
    os.environ["LEGAL_AI_REQUIRE_ONLINE_VERIFICATION"] = "1"
    os.environ["LEGAL_AI_ENABLE_INTERACTIVE_CODEX_HANDOFF"] = "1"
    os.environ["LEGAL_AI_ALLOW_KEYLESS_JINA_SEARCH"] = "0"
    os.environ["LEGAL_AI_ONLINE_SEARCH_PROVIDER"] = "off"

    rag_calls = {"count": 0}

    def fake_rag(query, max_chunks=None, query_type=None):
        rag_calls["count"] += 1
        return (
            "[RAG CONTEXT - INTERNAL - DO NOT OUTPUT]\n"
            "Authority: Donoghue v Stevenson [1932] AC 562. Occupiers' Liability Act 1957 s 2.\n"
            "[END RAG CONTEXT]\n"
            + ("Source support. " * 200)
        )

    service.RAG_AVAILABLE = True
    service.get_relevant_context = fake_rag
    service._find_codex_cli = lambda: "codex"
    service._codex_exec_supports_option = lambda cli, option: False
    service._generate_with_codex_local_adapter = lambda **kwargs: (_ for _ in ()).throw(
        AssertionError("nested generation should not run for sandbox handoff")
    )

    (response, meta), rag_context = service.send_message_with_docs(
        api_key="",
        message="Use RAG and online verification to answer a Tort Law problem question.",
        documents=[],
        project_id="interactive-handoff-service",
        history=[],
        stream=False,
        provider="auto",
        model_name=None,
        enforce_long_response_split=False,
    )
    assert service.is_interactive_codex_supervisor_handoff(response)
    assert "Required direct-chat workflow" in response
    assert "RAG/local folder reading" in response
    assert "Online official-source verification" in response
    assert "updated-source discovery" in response
    assert "Strict supervisor checker" in response
    assert "top-band/xhigh-equivalent depth for every law subject" in response
    assert "Do not downgrade" in response
    assert "Donoghue v Stevenson" in response
    assert "This is not a final answer" in response
    assert meta and meta[0]["type"] == "interactive_codex_supervisor_handoff"
    assert rag_calls["count"] >= 1
    assert "Donoghue v Stevenson" in rag_context

    handoff_text = (
        service.INTERACTIVE_CODEX_HANDOFF_MARKER
        + "\nThis is not a final answer.\nRequired direct-chat workflow:\nRAG -> code guide -> online verification -> supervisor."
    )
    strict_called = {"value": False}

    def fake_provider(*args, **kwargs):
        return (handoff_text, [{"type": "interactive_codex_supervisor_handoff"}]), "[RAG CONTEXT]"

    def fail_strict(*args, **kwargs):
        strict_called["value"] = True
        raise AssertionError("complete-answer strict checker must not treat handoff as final answer")

    runtime._provider_send_message_with_docs = fake_provider
    runtime._strict_complete_answer_issues = fail_strict
    (runtime_response, runtime_meta), _ = runtime.send_complete_answer_with_docs(
        api_key="",
        message="Write a 1500 word Tort Law problem answer. Advise the parties.",
        documents=[],
        project_id="interactive-handoff-runtime",
        history=[],
        stream=False,
        provider="auto",
        model_name=None,
        enforce_long_response_split=False,
    )
    assert runtime_response == handoff_text
    assert runtime_meta[0]["type"] == "interactive_codex_supervisor_handoff"
    assert strict_called["value"] is False

    workflow.send_message_with_docs = lambda *args, **kwargs: (
        (handoff_text, [{"type": "interactive_codex_supervisor_handoff"}]),
        "[RAG CONTEXT]",
    )
    try:
        workflow.run_uploaded_legal_doc_amend_workflow(
            api_key="",
            message="Please amend this uploaded DOCX to a first class legal standard.",
            documents=[
                {
                    "id": "docx-1",
                    "type": "file",
                    "name": "draft.docx",
                    "mimeType": workflow.DOCX_MIME,
                    "data": _minimal_docx_payload(),
                    "size": 100,
                }
            ],
            project_id="interactive-handoff-amend",
            history=[],
            provider="auto",
            model_name=None,
        )
        raise AssertionError("Expected DOCX amend workflow to surface the interactive handoff")
    except RuntimeError as exc:
        assert "Interactive Codex handoff required for DOCX amendment generation" in str(exc)
        assert service.INTERACTIVE_CODEX_HANDOFF_MARKER in str(exc)
finally:
    service.RAG_AVAILABLE = original_rag_available
    service.get_relevant_context = original_get_relevant_context
    service._find_codex_cli = original_find_codex_cli
    service._codex_exec_supports_option = original_codex_supports_option
    service._generate_with_codex_local_adapter = original_generate_with_codex
    runtime._provider_send_message_with_docs = original_provider_send
    runtime._strict_complete_answer_issues = original_strict_issues
    workflow.send_message_with_docs = original_workflow_send
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


print("Interactive Codex supervisor handoff tests passed.")
