import base64
import backend_answer_runtime as runtime
import model_applicable_service as provider_service
import os
import tempfile
from pathlib import Path

from docx import Document


assert runtime.resolve_backend_answer_output_mode(
    "Please return this directly in chat."
) == runtime.BACKEND_ANSWER_OUTPUT_CHAT
assert runtime.resolve_backend_answer_output_mode(
    "Please give me the answer in markdown."
) == runtime.BACKEND_ANSWER_OUTPUT_MARKDOWN
assert runtime.resolve_backend_answer_output_mode(
    "Save it as .md after answering."
) == runtime.BACKEND_ANSWER_OUTPUT_MARKDOWN
assert runtime.resolve_backend_answer_delivery_mode(
    "Please return this directly in chat."
) == runtime.BACKEND_ANSWER_OUTPUT_CHAT
assert runtime.resolve_backend_answer_delivery_mode(
    "Please give me the answer in markdown."
) == runtime.BACKEND_ANSWER_OUTPUT_MARKDOWN
assert runtime.resolve_backend_answer_delivery_mode(
    "Save it as .md after answering."
) == runtime.BACKEND_ANSWER_OUTPUT_MARKDOWN_ARTIFACT
assert runtime.resolve_backend_answer_delivery_mode(
    "Put the final answer in a DOCX Word document on Desktop."
) == runtime.BACKEND_ANSWER_OUTPUT_DOCX_ARTIFACT

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
assert "Chat/API delivery does NOT relax the required Part-numbered answer scaffold." in captured_calls[1]["message"]
assert "strict complete-answer window: 1980-2000 words" in captured_calls[1]["message"]
assert response_text == "SECOND DRAFT"
assert response_meta == ["second-meta"]
assert "Authority:" in rag_context

long_problem_prompt = """Professional Negligence — Problem Question

Advise the parties. In particular, consider:

the existence and scope of each professional’s duty of care,
contractual and tortious liability,
breach of duty,
causation,
loss of a chance,
remoteness,
SAAMCO / scope-of-duty issues,
contributory negligence,
apportionment between multiple professionals,
limitation risks if proceedings are delayed,
and the remedies likely to be available.

2500 words.

Please return this directly in chat."""

unstructured_long_problem_answer = " ".join(["analysis"] * 2488)
long_problem_issues = runtime._strict_complete_answer_issues(
    unstructured_long_problem_answer,
    long_problem_prompt,
    [],
    enforce_long_response_split=False,
)
assert any(
    ("direct complete-answer structure violation" in issue.lower())
    or ("missing part headings" in issue.lower())
    for issue in long_problem_issues
), long_problem_issues

sentence_support_issues = runtime._strict_complete_answer_issues(
    """Part I: Introduction

The court will probably order Leo's return because wrongful removal is plainly established.

Part II: Habitual Residence

Leo remained habitually resident in Spain because mere plans to move do not displace an existing residence (*A v A* [2013] UKSC 60).
Daniel was exercising rights of custody at the time of removal.

Part III: Final Conclusion

Daniel is therefore likely to succeed.

(End of Answer)""",
    """Child Abduction / Hague 1980 — Problem Question

Advise the parties. In particular, consider habitual residence, rights of custody, wrongful removal or retention, grave risk, settlement, child objections, undertakings, and the likely approach of the court.

1200 words.""",
    [],
    enforce_long_response_split=False,
)
assert any(
    "argumentative sentence-support verification failed" in issue.lower()
    for issue in sentence_support_issues
), sentence_support_issues

artifact_response = (
    "Part I: Introduction\n\nThis is the final backend answer.\n\nPart II: Final Conclusion\n\nNorthbridge should sue promptly.\n\n(End of Answer)",
    ["artifact-meta"],
)


def fake_provider_send_message_with_docs_for_artifacts(
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
    return artifact_response, "Authority: Manchester Building Society v Grant Thornton UK LLP [2021] UKSC 20."


original_provider = runtime._provider_send_message_with_docs
original_issue_checker = runtime._strict_complete_answer_issues
try:
    runtime._provider_send_message_with_docs = fake_provider_send_message_with_docs_for_artifacts
    runtime._strict_complete_answer_issues = lambda *args, **kwargs: []

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = Path.cwd()
        original_desktop_root = runtime.BACKEND_ANSWER_ARTIFACT_DESKTOP_ROOT
        try:
            md_path = Path(tmpdir) / "northbridge_answer.md"
            docx_path = Path(tmpdir) / "northbridge_answer.docx"
            answer_task_artifact_file = Path(tmpdir) / "task_specific_prompt.txt"
            answer_task_artifact_dir = Path(tmpdir) / "task_specific_answer_helper_dir"
            answer_task_artifact_file.write_text("temporary prompt helper", encoding="utf-8")
            answer_task_artifact_dir.mkdir()
            (answer_task_artifact_dir / "draft.json").write_text("{}", encoding="utf-8")
            runtime.BACKEND_ANSWER_ARTIFACT_DESKTOP_ROOT = Path(tmpdir)
            os.chdir(tmpdir)

            (legacy_md_response, legacy_md_meta), legacy_md_rag_context = runtime.send_complete_answer_with_docs(
                api_key="",
                message="Professional Negligence problem question. Save it as .md in the project.",
                documents=[],
                project_id="proj",
                history=[],
                stream=False,
                output_mode="markdown_file",
            )
            assert legacy_md_response == artifact_response[0]
            assert "Authority:" in legacy_md_rag_context
            legacy_md_artifact = runtime._extract_complete_answer_artifact_meta(legacy_md_meta)
            assert legacy_md_artifact is not None
            legacy_md_path = Path(legacy_md_artifact["path"])
            assert legacy_md_artifact["mode"] == runtime.BACKEND_ANSWER_OUTPUT_MARKDOWN_ARTIFACT
            assert legacy_md_path.exists()
            assert legacy_md_path.suffix.lower() == ".md"
            existing_default_md_artifacts = set(Path(tmpdir).glob("*_backend_answer.md"))

            (legacy_docx_response, legacy_docx_meta), legacy_docx_rag_context = runtime.send_complete_answer_with_docs(
                api_key="",
                message="Professional Negligence problem question. Put the final answer in a DOCX Word document on Desktop.",
                documents=[],
                project_id="proj",
                history=[],
                stream=False,
                output_mode="docx",
            )
            assert legacy_docx_response == artifact_response[0]
            assert "Authority:" in legacy_docx_rag_context
            legacy_docx_artifact = runtime._extract_complete_answer_artifact_meta(legacy_docx_meta)
            assert legacy_docx_artifact is not None
            legacy_docx_path = Path(legacy_docx_artifact["path"])
            assert legacy_docx_artifact["mode"] == runtime.BACKEND_ANSWER_OUTPUT_DOCX_ARTIFACT
            assert legacy_docx_path.exists()
            assert legacy_docx_path.suffix.lower() == ".docx"

            (md_response, md_meta), md_rag_context, md_artifact = runtime.send_complete_answer_with_output(
                api_key="",
                message="Professional Negligence problem question. Save it as .md in the project.",
                documents=[],
                project_id="proj",
                history=[],
                stream=False,
                output_mode="markdown_file",
                artifact_path=str(md_path),
                cleanup_paths=[str(answer_task_artifact_file), str(answer_task_artifact_dir)],
            )
            assert md_response == artifact_response[0]
            assert "artifact-meta" in md_meta
            assert "Authority:" in md_rag_context
            assert md_artifact is not None
            assert md_artifact["mode"] == runtime.BACKEND_ANSWER_OUTPUT_MARKDOWN_ARTIFACT
            assert Path(md_artifact["path"]) == md_path.resolve()
            assert md_path.read_text(encoding="utf-8").strip() == artifact_response[0].strip()
            assert not answer_task_artifact_file.exists()
            assert not answer_task_artifact_dir.exists()
            assert set(Path(tmpdir).glob("*_backend_answer.md")) == existing_default_md_artifacts

            (docx_response, docx_meta), docx_rag_context, docx_artifact = runtime.send_complete_answer_with_output(
                api_key="",
                message="Professional Negligence problem question. Put the final answer in a DOCX Word document on Desktop.",
                documents=[],
                project_id="proj",
                history=[],
                stream=False,
                output_mode="docx",
                artifact_path=str(docx_path),
            )
            assert docx_response == artifact_response[0]
            assert "artifact-meta" in docx_meta
            assert "Authority:" in docx_rag_context
            assert docx_artifact is not None
            assert docx_artifact["mode"] == runtime.BACKEND_ANSWER_OUTPUT_DOCX_ARTIFACT
            assert Path(docx_artifact["path"]) == docx_path.resolve()
            doc = Document(docx_path)
            docx_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            assert "Part I: Introduction" in docx_text
            assert "Northbridge should sue promptly." in docx_text
        finally:
            os.chdir(original_cwd)
            runtime.BACKEND_ANSWER_ARTIFACT_DESKTOP_ROOT = original_desktop_root
finally:
    runtime._provider_send_message_with_docs = original_provider
    runtime._strict_complete_answer_issues = original_issue_checker

uploaded_complete_answer_documents = [
    {
        "id": "txt-1",
        "type": "file",
        "name": "contract_upload.txt",
        "mimeType": "text/plain",
        "data": base64.b64encode(
            b"""Question focus: contract law formation and certainty.
Authorities to check: Carlill v Carbolic Smoke Ball Co and RTS Flexible Systems Ltd v Molkerei Alois Muller GmbH.
Use the uploaded materials as source context, not just as filename metadata.
"""
        ).decode("utf-8"),
        "size": 228,
    }
]
captured_uploaded_complete_answer_prompts = []
captured_uploaded_complete_answer_queries = []


def fake_uploaded_complete_answer_rag(query, max_chunks=None, query_type=None):
    captured_uploaded_complete_answer_queries.append(
        {
            "query": query,
            "max_chunks": max_chunks,
            "query_type": query_type,
        }
    )
    return """[RAG CONTEXT - INTERNAL - DO NOT OUTPUT]
Authority: *Carlill v Carbolic Smoke Ball Co* [1893] 1 QB 256.
Authority: *RTS Flexible Systems Ltd v Molkerei Alois Muller GmbH* [2010] UKSC 14.
"""


def fake_uploaded_complete_answer_local_adapter(
    *,
    full_message,
    system_instruction,
    history,
    project_id,
    allow_web_search,
):
    captured_uploaded_complete_answer_prompts.append(
        {
            "full_message": full_message,
            "system_instruction": system_instruction,
            "history": history,
            "project_id": project_id,
            "allow_web_search": allow_web_search,
        }
    )
    return """Part I: Introduction

The uploaded materials and indexed authorities support the answer structure.

Part II: Conclusion

The answer remains in the standard complete-answer scaffold.

(End of Answer)"""


original_provider_rag_available = provider_service.RAG_AVAILABLE
original_provider_rag = getattr(provider_service, "get_relevant_context")
original_provider_find_codex_cli = provider_service._find_codex_cli
original_provider_local_adapter = provider_service._generate_with_codex_local_adapter
original_codex_allow_env = os.environ.get("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED")
try:
    provider_service.RAG_AVAILABLE = True
    provider_service.get_relevant_context = fake_uploaded_complete_answer_rag
    provider_service._find_codex_cli = lambda: "codex"
    provider_service._generate_with_codex_local_adapter = fake_uploaded_complete_answer_local_adapter
    os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = "1"

    (uploaded_complete_answer_response, uploaded_complete_answer_meta), uploaded_complete_answer_rag = provider_service.send_message_with_docs(
        api_key="",
        message="Use the uploaded materials and write a 2000-word contract law answer.",
        documents=uploaded_complete_answer_documents,
        project_id="proj-uploaded-answer",
        history=[],
        stream=False,
        provider="auto",
        model_name=None,
        enforce_long_response_split=False,
    )
finally:
    provider_service.RAG_AVAILABLE = original_provider_rag_available
    provider_service.get_relevant_context = original_provider_rag
    provider_service._find_codex_cli = original_provider_find_codex_cli
    provider_service._generate_with_codex_local_adapter = original_provider_local_adapter
    if original_codex_allow_env is None:
        os.environ.pop("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED", None)
    else:
        os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = original_codex_allow_env

assert uploaded_complete_answer_meta == []
assert "Part I: Introduction" in uploaded_complete_answer_response
assert "standard complete-answer scaffold" in uploaded_complete_answer_response
assert "Carlill" in uploaded_complete_answer_rag
assert len(captured_uploaded_complete_answer_queries) >= 1
assert len(captured_uploaded_complete_answer_prompts) == 1
uploaded_complete_answer_query = captured_uploaded_complete_answer_queries[0]["query"]
uploaded_complete_answer_prompt = captured_uploaded_complete_answer_prompts[0]["full_message"]
assert "[UPLOADED SOURCE CONTEXT FOR RETRIEVAL]" in uploaded_complete_answer_query
assert "Uploaded text: contract_upload.txt" in uploaded_complete_answer_query
assert "Question focus: contract law formation and certainty." in uploaded_complete_answer_query
assert "[UPLOADED MATERIALS - USE DIRECTLY]" in uploaded_complete_answer_prompt
assert "Document: contract_upload.txt (text)" in uploaded_complete_answer_prompt
assert "Use the uploaded materials as source context" in uploaded_complete_answer_prompt
assert "[MANDATORY BACKEND RAG POLICY]" in uploaded_complete_answer_prompt
assert "[DIRECT-CODE / BACKEND DELIVERY MODE]" in uploaded_complete_answer_prompt
assert "[LOCAL CODE + RAG LEGAL ANSWER MODE]" in uploaded_complete_answer_prompt
assert "[STRUCTURE ENFORCEMENT — ZERO TOLERANCE]" in uploaded_complete_answer_prompt
assert 'Your output MUST start with  "Part I: Introduction" as the absolute first line' in uploaded_complete_answer_prompt
assert "Use the uploaded materials and write a 2000-word contract law answer." in uploaded_complete_answer_prompt

print("Backend runtime complete-answer entrypoint checks passed.")
