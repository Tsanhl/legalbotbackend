import os

import rag_service
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
assert _backend_request_requires_mandatory_rag("Give me an SQE2 hard legal writing practice task.") is True
assert _backend_request_requires_mandatory_rag("Give me a legal research answer structure.") is True
assert _backend_request_requires_mandatory_rag("Land registered priority problem: advise the buyer.") is True
assert _backend_request_requires_mandatory_rag("Pensions problem on accrued rights and misleading statements.") is True
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

current_law_rag = (
    "R (Doody) v Secretary of State for the Home Department [1994] 1 AC 531. "
    "R (UNISON) v Lord Chancellor [2017] UKSC 51. "
    "S and Marper v United Kingdom (2009) 48 EHRR 50. "
    "Bank Mellat v HM Treasury (No 2) [2013] UKSC 39. "
    "R (Daly) v Secretary of State for the Home Department [2001] UKHL 26. "
    "Associated Provincial Picture Houses Ltd v Wednesbury Corporation [1948] 1 KB 223. "
    * 350
)
current_law_decision = service._backend_online_search_fallback_decision(
    query=(
        "Public law essay on Article 22, automated public decision-making, "
        "meaningful human involvement, UK GDPR and data-driven administration."
    ),
    rag_context=current_law_rag,
)
assert current_law_decision["use_online_search"] is True
assert "Data (Use and Access) Act 2025" in current_law_decision["reason"]

digital_competition_decision = service._backend_online_search_fallback_decision(
    query=(
        "Competition law problem on an online marketplace: Chapter II Competition Act 1998, "
        "Article 102, self-preferencing, third-party seller data, premium visibility, "
        "price parity and the DMCC strategic market status regime."
    ),
    rag_context=current_law_rag,
)
assert digital_competition_decision["use_online_search"] is True
assert "DMCC/SMS" in digital_competition_decision["reason"]

assert service._hard_online_verification_required(
    "Use online verification and RAG for a Law and Medicine Montgomery consent problem."
) is True
assert service._hard_online_verification_required(
    "Use online vertification and RAG for an Evidence Law PACE confession problem."
) is True
original_require_all_online = os.environ.get("LEGAL_AI_REQUIRE_ONLINE_VERIFICATION")
try:
    os.environ["LEGAL_AI_REQUIRE_ONLINE_VERIFICATION"] = "1"
    assert service._hard_online_verification_required(
        "Tort law negligence problem question: advise the claimant and defendant."
    ) is True
finally:
    if original_require_all_online is None:
        os.environ.pop("LEGAL_AI_REQUIRE_ONLINE_VERIFICATION", None)
    else:
        os.environ["LEGAL_AI_REQUIRE_ONLINE_VERIFICATION"] = original_require_all_online

original_codex_search_allow = os.environ.get("LEGAL_AI_CODEX_LOCAL_ALLOW_SEARCH")
original_codex_supports_option = service._codex_exec_supports_option
try:
    os.environ["LEGAL_AI_CODEX_LOCAL_ALLOW_SEARCH"] = "1"
    service._codex_exec_supports_option = lambda cli, option: option == "--search"
    assert service._online_verification_route_available(
        resolved_provider="openai",
        resolved_api_key=None,
        local_codex_generation_path=True,
        codex_cli="codex",
    ) is True
    service._codex_exec_supports_option = lambda cli, option: False
    assert service._online_verification_route_available(
        resolved_provider="openai",
        resolved_api_key=None,
        local_codex_generation_path=True,
        codex_cli="codex",
    ) is False
finally:
    service._codex_exec_supports_option = original_codex_supports_option
    if original_codex_search_allow is None:
        os.environ.pop("LEGAL_AI_CODEX_LOCAL_ALLOW_SEARCH", None)
    else:
        os.environ["LEGAL_AI_CODEX_LOCAL_ALLOW_SEARCH"] = original_codex_search_allow

hard_fail_provider_env = [
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "XAI_API_KEY",
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
    "LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED",
    "LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE",
    "LEGAL_AI_ENABLE_INTERACTIVE_CODEX_HANDOFF",
]
hard_fail_original_env = {key: os.environ.get(key) for key in hard_fail_provider_env}
original_hard_fail_rag_available = service.RAG_AVAILABLE
original_hard_fail_rag = service.get_relevant_context
original_hard_fail_find_codex = service._find_codex_cli
original_hard_fail_codex_supports = service._codex_exec_supports_option
original_hard_fail_local_adapter = service._generate_with_codex_local_adapter
try:
    for key in hard_fail_provider_env:
        os.environ.pop(key, None)
    os.environ["LEGAL_AI_ALLOW_KEYLESS_JINA_SEARCH"] = "0"
    os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = "1"
    os.environ["LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"] = "1"
    os.environ["LEGAL_AI_ENABLE_INTERACTIVE_CODEX_HANDOFF"] = "0"
    service.RAG_AVAILABLE = True
    service.get_relevant_context = lambda *args, **kwargs: (
        "[RAG CONTEXT - INTERNAL - DO NOT OUTPUT]\n"
        "Police and Criminal Evidence Act 1984, s 76. R v Turnbull [1977] QB 224.\n"
        "[END RAG CONTEXT]\n"
        + ("Authority support. " * 1200)
    )
    service._find_codex_cli = lambda: "codex"
    service._codex_exec_supports_option = lambda cli, option: False
    service._generate_with_codex_local_adapter = lambda **kwargs: (_ for _ in ()).throw(
        AssertionError("Generation must not run when mandatory online verification is unavailable")
    )
    try:
        service.send_message_with_docs(
            api_key="",
            message="Use online vertification and RAG for an Evidence Law PACE confession problem.",
            documents=[],
            project_id="hard-online-unavailable",
            history=[],
            stream=False,
            provider="auto",
            model_name=None,
            enforce_long_response_split=False,
        )
        raise AssertionError("Expected mandatory online verification to fail without a working search route")
    except Exception as exc:
        assert "Online verification is required" in str(exc)
        assert "no working online-verification route is available" in str(exc)
finally:
    service.RAG_AVAILABLE = original_hard_fail_rag_available
    service.get_relevant_context = original_hard_fail_rag
    service._find_codex_cli = original_hard_fail_find_codex
    service._codex_exec_supports_option = original_hard_fail_codex_supports
    service._generate_with_codex_local_adapter = original_hard_fail_local_adapter
    for key, value in hard_fail_original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

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

ledger_block = service._build_issue_source_ledger_gate(
    query=(
        "Public Law - Problem Question\n"
        "In your answer, consider:\n"
        "- fettering of discretion;\n"
        "- procedural fairness and adequacy of reasons;\n"
        "- Articles 10 and 11 ECHR."
    ),
    rag_context=(
        "[RAG CONTEXT - INTERNAL - DO NOT OUTPUT]\n"
        "R (UNISON) v Lord Chancellor [2017] UKSC 51. "
        "Human Rights Act 1998. Article 10 ECHR. Article 11 ECHR.\n"
        "[END RAG CONTEXT]"
    ),
    profile={"topic": "public_law_fettering_expression_assembly", "must_cover": ["Article 10 ECHR"]},
    audit={"score": 4.0, "primary_total": 3, "missing_must_cover": []},
)
assert "[ISSUE-SOURCE LEDGER" in ledger_block
assert "fettering of discretion" in ledger_block
assert "procedural fairness and adequacy of reasons" in ledger_block
assert "Article 10 ECHR" in ledger_block

anchors = service._extract_query_authority_anchors(
    "Criminal problem: consider R v Jogee [2016] UKSC 8, Theft Act 1968, s 9 and Article 6 ECHR."
)
assert "R v Jogee" in anchors
assert "Theft Act 1968" in anchors
assert any(anchor.lower().startswith("s 9") for anchor in anchors)
assert "Article 6" in anchors

strict_requery = service._build_strict_requery(
    "Criminal problem: consider R v Jogee [2016] UKSC 8 and Theft Act 1968, s 9.",
    {
        "topic": "criminal_secondary_liability",
        "jurisdiction": "england_wales",
        "must_cover": ["R v Jogee", "Theft Act 1968"],
        "query_keywords": ["burglary", "secondary liability"],
        "source_mix_min": {"statutes": 1, "cases": 1, "secondary": 0},
    },
    {"mix": {"statutes": 0, "cases": 0, "secondary": 0}, "missing_must_cover": ["R v Jogee"]},
)
assert "STRICT RETRIEVAL FILTER" in strict_requery
assert "R v Jogee" in strict_requery
assert "Theft Act 1968" in strict_requery

original_rag_available = service.RAG_AVAILABLE
original_get_relevant_context = service.get_relevant_context
original_find_codex_cli = service._find_codex_cli
provider_env_keys = [
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "XAI_API_KEY",
]
guard_env_keys = [
    "CODEX_SANDBOX_NETWORK_DISABLED",
    "LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED",
    "LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE",
    "LEGAL_AI_ENABLE_INTERACTIVE_CODEX_HANDOFF",
]
original_env = {key: os.environ.get(key) for key in provider_env_keys + guard_env_keys}
rag_called = {"value": False}


def fail_if_rag_called(*args, **kwargs):
    rag_called["value"] = True
    raise AssertionError("RAG should not run when no generation backend is available")


try:
    for key in provider_env_keys:
        os.environ.pop(key, None)
    os.environ["CODEX_SANDBOX_NETWORK_DISABLED"] = "1"
    os.environ.pop("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED", None)
    os.environ.pop("LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE", None)
    os.environ["LEGAL_AI_ENABLE_INTERACTIVE_CODEX_HANDOFF"] = "0"
    service.RAG_AVAILABLE = True
    service.get_relevant_context = fail_if_rag_called
    service._find_codex_cli = lambda: "codex"

    try:
        service.send_message_with_docs(
            api_key="",
            message="Tort Law problem question. Advise on occupiers' liability with inline OSCOLA.",
            documents=[],
            project_id="provider-fail-fast-before-rag",
            history=[],
            stream=False,
            provider="auto",
            model_name=None,
            enforce_long_response_split=False,
        )
        raise AssertionError("Expected no-provider sandbox guard to fail fast")
    except Exception as exc:
        assert "subprocess network access is disabled" in str(exc)
        assert rag_called["value"] is False
finally:
    service.RAG_AVAILABLE = original_rag_available
    service.get_relevant_context = original_get_relevant_context
    service._find_codex_cli = original_find_codex_cli
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

original_disable_bm25 = os.environ.get("LEGAL_AI_DISABLE_BM25")
try:
    os.environ["LEGAL_AI_DISABLE_BM25"] = "1"
    rag = object.__new__(rag_service.RAGService)
    rag._ensure_bm25_index = lambda: (_ for _ in ()).throw(
        AssertionError("BM25 index should not be built when LEGAL_AI_DISABLE_BM25=1")
    )
    assert rag_service.RAGService._get_bm25_results(rag, "occupiers liability", 10) == {}
finally:
    if original_disable_bm25 is None:
        os.environ.pop("LEGAL_AI_DISABLE_BM25", None)
    else:
        os.environ["LEGAL_AI_DISABLE_BM25"] = original_disable_bm25

original_force_large_bm25 = os.environ.get("LEGAL_AI_FORCE_LARGE_BM25")
original_bm25_max = os.environ.get("LEGAL_AI_BM25_MAX_CHUNKS")
try:
    os.environ.pop("LEGAL_AI_DISABLE_BM25", None)
    os.environ.pop("LEGAL_AI_FORCE_LARGE_BM25", None)
    os.environ["LEGAL_AI_BM25_MAX_CHUNKS"] = "10"
    rag = object.__new__(rag_service.RAGService)
    rag.collection_count = 999999
    rag._bm25_large_index_skip_logged = False
    rag._ensure_bm25_index = lambda: (_ for _ in ()).throw(
        AssertionError("BM25 index should not be built for a large index in fast mode")
    )
    assert rag_service.RAGService._get_bm25_results(rag, "occupiers liability", 10) == {}
finally:
    if original_force_large_bm25 is None:
        os.environ.pop("LEGAL_AI_FORCE_LARGE_BM25", None)
    else:
        os.environ["LEGAL_AI_FORCE_LARGE_BM25"] = original_force_large_bm25
    if original_bm25_max is None:
        os.environ.pop("LEGAL_AI_BM25_MAX_CHUNKS", None)
    else:
        os.environ["LEGAL_AI_BM25_MAX_CHUNKS"] = original_bm25_max

original_rag_available = service.RAG_AVAILABLE
original_get_relevant_context = service.get_relevant_context
original_find_codex_cli = service._find_codex_cli
original_local_adapter = service._generate_with_codex_local_adapter
original_allow = os.environ.get("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED")
original_assume = os.environ.get("LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE")
original_require_online = os.environ.get("LEGAL_AI_REQUIRE_ONLINE_VERIFICATION")
rewrite_queries = []
rewrite_adapter_prompts = []


def capture_rewrite_rag(query, max_chunks=None, query_type=None):
    rewrite_queries.append(query)
    return (
        "[RAG CONTEXT - INTERNAL - DO NOT OUTPUT]\n"
        "Occupiers' Liability Act 1957, s 2(2). Occupiers' Liability Act 1984, ss 1(3)-1(5). "
        "Tomlinson v Congleton Borough Council [2003] UKHL 47, [2004] 1 AC 46.\n"
        "[END RAG CONTEXT]\n"
        + ("Authority support. " * 1200)
    )


def capture_rewrite_adapter(*, full_message, system_instruction, history, project_id, allow_web_search):
    rewrite_adapter_prompts.append(full_message)
    return (
        "Part I: Introduction\n\n"
        "This repaired answer uses the original prompt for retrieval.\n\n"
        "Part II: Final Conclusion\n\n"
        "The answer ends cleanly.\n\n"
        "(End of Answer)"
    )


try:
    service.RAG_AVAILABLE = True
    service.get_relevant_context = capture_rewrite_rag
    service._find_codex_cli = lambda: "codex"
    service._generate_with_codex_local_adapter = capture_rewrite_adapter
    os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = "1"
    os.environ["LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"] = "1"
    os.environ["LEGAL_AI_REQUIRE_ONLINE_VERIFICATION"] = "0"

    rewrite_message = """Tort Law - Problem Question

Word target: about 1,500-2,000 words

Advise Mia and Daniel on occupiers' liability.

[BACKEND STRICT COMPLETE-ANSWER REWRITE]
Regenerate the full answer.
Current answer was 2378 words and contained a broken citation.
Current answer:
Part IV: Contributory Negligence
This draft text should not be used as the RAG query."""

    service.send_message_with_docs(
        api_key="",
        message=rewrite_message,
        documents=[],
        project_id="strict-rewrite-rag-source",
        history=[],
        stream=False,
        provider="auto",
        model_name=None,
        enforce_long_response_split=False,
    )
    assert rewrite_queries, "Expected RAG query capture"
    assert all("[BACKEND STRICT COMPLETE-ANSWER REWRITE]" not in q for q in rewrite_queries)
    assert all("2378 words" not in q for q in rewrite_queries)
    assert all("This draft text should not be used as the RAG query" not in q for q in rewrite_queries)
    assert "Advise Mia and Daniel" in rewrite_queries[0]
finally:
    service.RAG_AVAILABLE = original_rag_available
    service.get_relevant_context = original_get_relevant_context
    service._find_codex_cli = original_find_codex_cli
    service._generate_with_codex_local_adapter = original_local_adapter
    if original_allow is None:
        os.environ.pop("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED", None)
    else:
        os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = original_allow
    if original_assume is None:
        os.environ.pop("LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE", None)
    else:
        os.environ["LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"] = original_assume
    if original_require_online is None:
        os.environ.pop("LEGAL_AI_REQUIRE_ONLINE_VERIFICATION", None)
    else:
        os.environ["LEGAL_AI_REQUIRE_ONLINE_VERIFICATION"] = original_require_online

print("Provider routing + mandatory RAG policy checks passed.")
