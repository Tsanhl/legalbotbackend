from model_applicable_service import (
    _backend_request_requires_mandatory_rag,
    _build_backend_rag_requirement_block,
    detect_provider_from_api_key,
    get_provider_model_placeholder,
    normalize_llm_provider,
)


assert normalize_llm_provider("claude") == "anthropic"
assert normalize_llm_provider("anthropic api") == "anthropic"
assert detect_provider_from_api_key("sk-ant-api03-testkey") == "anthropic"
assert get_provider_model_placeholder("anthropic") == "claude-sonnet-4-0"

assert _backend_request_requires_mandatory_rag("Advise whether the defendant is liable in negligence.") is True
assert _backend_request_requires_mandatory_rag("Tell me a joke.") is False
assert _backend_request_requires_mandatory_rag(
    "Please amend this DOCX draft.",
    {"active": True, "mode": "amend", "has_docx": True},
) is True

thin_block = _build_backend_rag_requirement_block(
    rag_required=True,
    rag_context="[RAG] No relevant content found",
    legal_doc_workflow={"active": True, "mode": "amend", "has_docx": True},
)
assert "[MANDATORY BACKEND RAG POLICY]" in thin_block
assert "Retrieval was attempted" in thin_block
assert "compare the draft against the retrieved corpus" in thin_block

ok_block = _build_backend_rag_requirement_block(
    rag_required=True,
    rag_context="Authority: Occupiers' Liability Act 1957, s 2(2).",
    legal_doc_workflow={"active": False, "mode": None, "has_docx": False},
)
assert "Retrieval succeeded" in ok_block

print("Provider routing + mandatory RAG policy checks passed.")
