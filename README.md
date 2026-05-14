# legalbotbackend

This repository is backend-only. The Streamlit/UI layer and old frontend assets have been removed; do not rebuild a frontend unless that is explicitly requested. The project focuses on the backend legal-answer and legal-document workflows below.

1. `backend_answer_runtime.send_complete_answer_with_docs(...)`
   Canonical backend complete-answer entrypoint. Uses direct/backend mode by default, keeps legal RAG + code-guide routing active, forces the stricter complete-answer verification layer for complete essay/problem answers, and now honours chat / `.md` / `.docx` delivery requests without switching generation pipelines.
2. `backend_answer_runtime.send_complete_answer_with_output(...)`
   Canonical delivery wrapper. It always generates through `send_complete_answer_with_docs(...)` first, then optionally saves that same verified answer as a project `.md` artifact or a Desktop `.docx` artifact. It can also clean registered temporary task-specific helper artifacts after a successful complete-answer run.
3. `backend_answer_runtime.send_sqe_question_set_with_docs(...)`
   Dedicated backend SQE question-set entrypoint for FLK1, FLK2, SQE1, and SQE2. It can attach official sample PDFs as style benchmarks, defaults to chat/API output, enforces harder/non-repeat SQE drafting instructions, uses indexed RAG plus any backend search context supplied by the provider route, and avoids essay-style complete-answer verification.
4. `backend_answer_runtime.send_sqe2_marking_with_docs(...)`
   Dedicated SQE2 written-answer marking entrypoint. It marks candidate answers against the relevant SQE2 written-skill criteria using the A-F simulated judgment scale, uses indexed RAG plus any backend search context supplied by the provider route, and can attach SQE2 sample/performance-indicator PDFs.
5. `legal_doc_tools.workflow.run_auto_legal_doc_amend_workflow(...)`
   Runs the automatic DOCX amend workflow for uploaded or local documents, using amend-specific JSON-plan validation, delivery gates, and a supervisor retry when the plan/gate fails.

## Core backend modules

- `model_applicable_service.py`: internal provider/RAG prompt builder and provider-agnostic routing policy. Do not expose it as the user-facing route for complete legal answers.
- `backend_answer_runtime.py`: canonical complete-answer supervisor, deterministic answer-shaping, continuation, and output-quality helpers.
- `legal_doc_tools/workflow.py`: auto-amend workflow entrypoint.
- `rag_service.py` and `knowledge_base.py`: retrieval/index support.

## Quick start for personal Codex use

1. Create a Python environment and install `requirements.txt`.
2. Call the backend functions directly from code or tests.
3. For normal Codex work in this repository, use the current interactive Codex agent to inspect code, patch guides, run deterministic tests, and review generated artifacts.
4. For live backend generation, either configure a provider key (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `XAI_API_KEY`) or let direct-code/backend mode fall back to the local Codex adapter when Codex CLI access is available outside a network-blocked sandbox. To make a no-API local setup explicit, set `LEGAL_AI_FORCE_CODEX_LOCAL_ADAPTER=1`; this ignores entered/env provider keys and requires the local Codex adapter.

Important runtime distinction: the interactive Codex agent is not the same thing as the backend local Codex adapter. The adapter starts a nested `codex exec` subprocess when no provider API key is configured. That nested path can be slower and it cannot bypass a Codex Desktop sandbox that blocks subprocess network access. `LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED=1` only acknowledges that risk; it is not a network bypass. If `CODEX_SANDBOX_NETWORK_DISABLED=1` is present, the backend now fails fast instead of hanging unless `LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE=1` is set in a runtime where nested `codex exec` genuinely has network access.
The nested adapter compacts oversized backend prompts before calling `codex exec`, uses quality-first `xhigh` reasoning by default, and has a default timeout of 360 seconds. Set `LEGAL_AI_CODEX_REASONING_EFFORT=low` only for quick smoke tests. Increase `LEGAL_AI_CODEX_TIMEOUT_SEC` only for deliberately long live backend QA. Set `LEGAL_AI_FORCE_CODEX_LOCAL_ADAPTER=1` when you want every backend generation route to use local Codex whenever it is technically available.

## Example entrypoints

```python
from backend_answer_runtime import send_complete_answer_with_docs
from backend_answer_runtime import send_complete_answer_with_output
from backend_answer_runtime import send_sqe_question_set_with_docs
from backend_answer_runtime import send_sqe2_marking_with_docs
from legal_doc_tools.workflow import run_auto_legal_doc_amend_workflow
```

For legal answer and amend requests, indexed RAG retrieval is automatic and mandatory before generation. The backend then applies the shared code-guide and subject-guide instructions. All legal answers are hard-gated for online verification by default (`LEGAL_AI_REQUIRE_ONLINE_VERIFICATION=1` unless explicitly disabled). If no real online route is available, generation stops instead of presenting an unverified answer as web-checked. No provider API is required only when the local Codex backend can actually run `codex exec --search` with network access; inside this Codex Desktop sandbox, use the current Codex chat for no-key RAG/code-guide work or configure a provider key for the backend. Gemini can use native Google Search grounding; OpenAI, Anthropic, xAI, and non-Codex backend paths can use the shared backend online-search context (`BRAVE_SEARCH_API_KEY`, Google CSE, SerpAPI, Tavily, or opt-in Jina). Complete answers return direct chat/API text by default; if the caller wants a saved `.md` or `.docx`, both complete-answer entrypoints keep the same backend answer pipeline and render the artifact from that verified answer text rather than through a separate generation path.

Default legal-answer policy:

1. Indexed RAG first.
2. Code guide / subject guide second.
3. Online search where RAG coverage is thin, outdated, current-law verification is needed, or the user asks for online verification; hard-fail rather than claim verification when mandatory online verification cannot actually run.
4. Inline OSCOLA by default unless the user requests another style.
5. No local source-path leakage, fake citations, or hidden gold-standard examples in user output.

Default delivery policy:

- Complete essay/problem/chat answers return to chat/API unless the caller asks for `.md` or `.docx`.
- SQE question sets, SQE2 written guides, and SQE2 marking also return to chat/API unless the caller explicitly asks for an artifact.
- Amend/rewrite workflows produce the amended DOCX artifact for the user's Desktop by default.
- One-off helper files, prompt dumps, answer samples, and QA outputs should use `/private/tmp` and be deleted before the run finishes. If generated through a backend call, pass them through `cleanup_paths` where possible.
