import os

import model_applicable_service as service


TEST_QUESTIONS = [
    {
        "label": "planning_law_rag_thin",
        "prompt": (
            "Use the code guide and RAG to write a 1500 word Planning Law essay. "
            "Critically evaluate how English planning law balances the development plan, "
            "material considerations, and local authority discretion when deciding planning applications. "
            "Consider TCPA 1990 section 70(2), PCPA 2004 section 38(6), the NPPF, "
            "planning conditions, legitimate expectations, reasons, and judicial/statutory review."
        ),
        "expected_topic": "generic_planning_law",
    },
    {
        "label": "bhr_supply_chain_rag_thin",
        "prompt": (
            "Use the code guide and RAG to write a 1500 word Business and Human Rights essay "
            "on supply-chain due diligence, lower-tier suppliers, audit fatigue, and mandatory "
            "human rights due diligence laws."
        ),
        "expected_topic": "corporate_bhr_parent_liability",
    },
    {
        "label": "ihl_article36_rag_thin",
        "prompt": (
            "Use the code guide and RAG to write a 1500 word International Humanitarian Law essay "
            "on Additional Protocol I, distinction, proportionality, precautions in attack, "
            "and Article 36 weapons reviews."
        ),
        "expected_topic": "ihl_targeting_proportionality_civilians",
    },
]


captured_prompts = []
captured_queries = []


def fake_rag(query, max_chunks=None, query_type=None):
    captured_queries.append(
        {
            "query": query,
            "max_chunks": max_chunks,
            "query_type": query_type,
        }
    )
    return "[RAG CONTEXT - INTERNAL - DO NOT OUTPUT]\nAuthority: thin placeholder only.\n[END RAG CONTEXT]"


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
        "This is a no-provider-API Codex backend answer using RAG and search fallback.\n\n"
        "Part II: Conclusion\n\n"
        "The answer ends in the required scaffold.\n\n"
        "(End of Answer)"
    )


def run_case(case):
    profile = service._infer_retrieval_profile(case["prompt"])
    assert profile["topic"] == case["expected_topic"], (case["label"], profile["topic"])

    captured_prompts.clear()
    captured_queries.clear()
    (response, meta), rag_context = service.send_message_with_docs(
        api_key="",
        message=case["prompt"],
        documents=[],
        project_id=f"proj-no-api-{case['label']}",
        history=[],
        stream=False,
        provider="auto",
        model_name=None,
        enforce_long_response_split=False,
    )

    assert meta == []
    assert "Part I: Introduction" in response
    assert "thin placeholder" in rag_context
    assert captured_queries, case["label"]
    assert len(captured_prompts) == 1, case["label"]
    prompt = captured_prompts[0]["full_message"]
    assert captured_prompts[0]["allow_web_search"] is True, case["label"]
    assert "[LOCAL CODE + RAG LEGAL ANSWER MODE]" in prompt
    assert "[CODEX ONLINE SEARCH FALLBACK ACTIVE]" in prompt
    assert "[GOOGLE GROUNDING FALLBACK ACTIVE]" not in prompt
    assert "Gemini Google-grounded" not in prompt
    assert "Every parenthetical authority reference must be a FULL OSCOLA citation" in prompt
    assert case["prompt"] in prompt


original_rag_available = service.RAG_AVAILABLE
original_get_relevant_context = service.get_relevant_context
original_find_codex_cli = service._find_codex_cli
original_local_adapter = service._generate_with_codex_local_adapter
original_codex_supports_option = service._codex_exec_supports_option
original_env = {
    key: os.environ.get(key)
    for key in [
        "LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED",
        "LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE",
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
        "LEGAL_AI_REQUIRE_ONLINE_VERIFICATION",
        "LEGAL_AI_FORCE_CODEX_LOCAL_ADAPTER",
    ]
}

try:
    service.RAG_AVAILABLE = True
    service.get_relevant_context = fake_rag
    service._find_codex_cli = lambda: "codex"
    service._codex_exec_supports_option = lambda cli, option: option == "--search"
    service._generate_with_codex_local_adapter = fake_local_codex_adapter
    os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = "1"
    os.environ["LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"] = "1"
    for key in [
        "BRAVE_SEARCH_API_KEY",
        "GOOGLE_CSE_API_KEY",
        "GOOGLE_CUSTOM_SEARCH_API_KEY",
        "GOOGLE_CSE_ID",
        "GOOGLE_CUSTOM_SEARCH_ENGINE_ID",
        "GOOGLE_SEARCH_ENGINE_ID",
        "SERPAPI_API_KEY",
        "TAVILY_API_KEY",
    ]:
        os.environ.pop(key, None)
    os.environ["LEGAL_AI_ALLOW_KEYLESS_JINA_SEARCH"] = "0"
    os.environ.pop("LEGAL_AI_ONLINE_SEARCH_PROVIDER", None)

    for question in TEST_QUESTIONS:
        run_case(question)

    captured_prompts.clear()
    os.environ["LEGAL_AI_FORCE_CODEX_LOCAL_ADAPTER"] = "1"
    (forced_response, forced_meta), forced_rag_context = service.send_message_with_docs(
        api_key="AIzaRealLookingProviderKey",
        message=TEST_QUESTIONS[0]["prompt"],
        documents=[],
        project_id="proj-force-codex-local-even-with-key",
        history=[],
        stream=False,
        provider="gemini",
        model_name=None,
        enforce_long_response_split=False,
    )
    assert forced_meta == []
    assert "Part I: Introduction" in forced_response
    assert "thin placeholder" in forced_rag_context
    assert len(captured_prompts) == 1
    assert captured_prompts[0]["allow_web_search"] is True
    assert "[LOCAL CODE + RAG LEGAL ANSWER MODE]" in captured_prompts[0]["full_message"]
finally:
    service.RAG_AVAILABLE = original_rag_available
    service.get_relevant_context = original_get_relevant_context
    service._find_codex_cli = original_find_codex_cli
    service._codex_exec_supports_option = original_codex_supports_option
    service._generate_with_codex_local_adapter = original_local_adapter
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


print("No-provider-API Codex RAG + online-search backend tests passed.")
