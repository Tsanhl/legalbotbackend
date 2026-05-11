import model_applicable_service as service
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

assert service.get_dynamic_chunk_count(
    "Private International Law - Problem Question. Advise on jurisdiction and choice of law.",
    [],
    enforce_long_response_split=False,
) == 10

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

online_decision = service._backend_online_search_fallback_decision(
    query="Planning law essay on section 70(2), section 38(6), NPPF and judicial review.",
    rag_context="",
)
assert online_decision["use_online_search"] is True
assert "RAG context" in online_decision["reason"]

original_search_runner = service._run_backend_online_search
try:
    service._run_backend_online_search = lambda query, max_results=6: (
        [
            {
                "title": "Town and Country Planning Act 1990",
                "url": "https://www.legislation.gov.uk/ukpga/1990/8/section/70",
                "snippet": "Section 70 concerns determination of planning applications.",
            }
        ],
        "test",
        None,
    )
    search_block, search_meta = service._build_backend_online_search_context_block(
        query="Planning law essay",
        retrieval_profile={"topic": "generic_planning_law", "must_cover": ["section 70(2)"]},
        citation_style="oscola",
        reason="RAG context insufficient",
    )
finally:
    service._run_backend_online_search = original_search_runner

assert search_meta["result_count"] == 1
assert "[BACKEND ONLINE SEARCH CONTEXT - INTERNAL - DO NOT OUTPUT]" in search_block
assert "Every parenthetical authority reference must be a FULL OSCOLA citation" in search_block

print("Provider routing + mandatory RAG policy checks passed.")
