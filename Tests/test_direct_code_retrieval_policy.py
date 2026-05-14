from model_applicable_service import (
    _build_local_code_rag_answer_prompt_block,
    get_dynamic_chunk_count,
    _resolve_long_response_info,
)


direct_long = _resolve_long_response_info(
    "Write a 4500 word essay on constitutional law",
    enforce_long_response_split=False,
)
website_long = _resolve_long_response_info(
    "Write a 4500 word essay on constitutional law",
    enforce_long_response_split=True,
)

assert direct_long.get("requested_words") == 4500
assert direct_long.get("is_long_essay") is False
assert direct_long.get("split_disabled_for_direct_use") is True
assert website_long.get("is_long_essay") is True

direct_chunks = get_dynamic_chunk_count(
    "Write a 4500 word essay on constitutional law",
    enforce_long_response_split=False,
)
website_chunks = get_dynamic_chunk_count(
    "Write a 4500 word essay on constitutional law",
    enforce_long_response_split=True,
)

assert 28 <= direct_chunks <= 40
assert website_chunks <= 20
assert direct_chunks > website_chunks

direct_answer_prompt = _build_local_code_rag_answer_prompt_block(
    "Answer this judicial review problem question using code + rag.",
    enforce_long_response_split=False,
)
assert "[LOCAL CODE + RAG LEGAL ANSWER MODE]" in direct_answer_prompt
assert "complete end-product answer" in direct_answer_prompt
assert "Use indexed RAG material first." in direct_answer_prompt
assert "Shared legal backend guide anchors:" in direct_answer_prompt
assert "Marker-feedback clarity rules are mandatory." in direct_answer_prompt
assert "Feedback abstraction and privacy rule is mandatory." in direct_answer_prompt
assert "Fact-matched actor labels are mandatory." in direct_answer_prompt
assert "Implicit-question clarity rule is mandatory." in direct_answer_prompt
assert "Comparative and superlative claims must be quantified or calibrated." in direct_answer_prompt
assert "Chapter-integration rule is mandatory." in direct_answer_prompt
assert "generalise the drafting lesson and apply it across analogous issues" in direct_answer_prompt

website_answer_prompt = _build_local_code_rag_answer_prompt_block(
    "Answer this judicial review problem question using code + rag.",
    enforce_long_response_split=True,
)
assert "[DEFAULT BACKEND RAG + CODE GUIDE MODE]" in website_answer_prompt
assert "The user does not need to say `use RAG`, `use backend`, or `use code guide`" in website_answer_prompt
assert "Obey website/multipart continuation controls" in website_answer_prompt
assert "Use indexed RAG material first." in website_answer_prompt
assert "Shared legal backend guide anchors:" in website_answer_prompt
assert "Matched subject guide anchors:" in website_answer_prompt

forced_docx_prompt = _build_local_code_rag_answer_prompt_block(
    "Please amend this DOCX draft.",
    enforce_long_response_split=True,
    force=True,
)
assert "[DEFAULT BACKEND RAG + CODE GUIDE MODE]" in forced_docx_prompt
assert "legal answer, topic-notes, and amend/review requests" in forced_docx_prompt

assert _build_local_code_rag_answer_prompt_block(
    "Tell me a joke using code + rag.",
    enforce_long_response_split=False,
) == ""

print(
    "Direct-code retrieval policy checks passed:",
    {
        "direct_chunks": direct_chunks,
        "website_chunks": website_chunks,
    },
)
