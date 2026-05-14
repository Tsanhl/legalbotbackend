# Quick Start

The project is backend-only now. Use the Python services directly instead of a frontend app. Do not recreate a frontend unless the user explicitly asks for one.

## Main entrypoints

- `backend_answer_runtime.send_complete_answer_with_docs(...)`
  Canonical backend complete-answer path. Defaults to direct/backend delivery, keeps legal RAG and code-guide routing active, forces the stricter complete-answer verification layer for complete essay/problem answers, and can now honour chat / `.md` / `.docx` delivery requests from the same path.
- `backend_answer_runtime.send_complete_answer_with_output(...)`
  Canonical delivery wrapper. Chat output, project `.md` files, and Desktop `.docx` files all derive from the same backend-generated and verified answer text, and registered temporary task-specific helper artifacts can be cleaned after a successful answer run.
- `backend_answer_runtime.send_sqe_question_set_with_docs(...)`
  Dedicated backend SQE question-set path. It supports FLK1, FLK2, SQE1, and SQE2 task generation, can attach official sample PDFs as style benchmarks, defaults to chat/API output, uses indexed RAG plus any backend search context supplied by the provider route, and disables essay-style complete-answer verification for question sets.
- `backend_answer_runtime.send_sqe2_marking_with_docs(...)`
  Dedicated SQE2 written-answer marking path. It marks candidate answers against the relevant written-skill criteria, uses indexed RAG plus any backend search context supplied by the provider route, uses the A-F simulated judgment scale, and can attach SQE2 sample/performance-indicator PDFs for guidance.
- `legal_doc_tools.workflow.run_auto_legal_doc_amend_workflow(...)`
  Automatic amend pipeline for uploaded or local DOCX files, using amend-specific validation, delivery gates, and a supervisor retry when the generated plan/gate fails.

## Setup For Personal Codex Use

1. Create and activate a Python virtual environment.
2. Install dependencies from `requirements.txt`.
3. For deterministic guide/routing work, use Codex to edit the backend and run tests.
4. For live backend generation, either set a provider key (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `XAI_API_KEY`) or use the local Codex adapter. If no usable provider key is configured, direct-code mode can fall back to the local Codex adapter only when nested Codex CLI access has real network access. For a no-API local setup, set `LEGAL_AI_FORCE_CODEX_LOCAL_ADAPTER=1` so entered/env provider keys are ignored and generation must use local Codex.

Inside Codex Desktop, the local Codex adapter is a nested `codex exec` subprocess. It can take longer than normal interactive Codex because it loads RAG, composes the full guide prompt, and starts a separate model run. It cannot bypass a network-blocked Codex sandbox. This env var only acknowledges the risk; it does not create network access:

```bash
LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED=1
```

If `CODEX_SANDBOX_NETWORK_DISABLED=1` is present, the backend now fails fast unless `LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE=1` is set in a runtime where nested `codex exec` is known to have network access. The nested adapter compacts oversized backend prompts before calling Codex, uses quality-first `xhigh` reasoning by default, and has a default timeout of 360 seconds. Set `LEGAL_AI_CODEX_REASONING_EFFORT=low` only for quick smoke tests. Increase `LEGAL_AI_CODEX_TIMEOUT_SEC` only for deliberately long live backend QA. Set `LEGAL_AI_FORCE_CODEX_LOCAL_ADAPTER=1` when you want complete answers, amendments, and SQE routes to use the local Codex adapter rather than provider APIs.

## Relevant backend files

- `model_applicable_service.py`
  Internal provider/RAG prompt builder; do not use it as the user-facing route for complete legal answers.
- `backend_answer_runtime.py`
- `legal_doc_tools/workflow.py`
- `NEW_FEATURES.md`

## Validation

Use the backend regression tests in `Tests/` to verify the answer and amend flows after changes. Legal answer and amend requests automatically run through indexed RAG before generation, then apply the code guide and subject guides. Legal answers are hard-gated for online verification by default (`LEGAL_AI_REQUIRE_ONLINE_VERIFICATION=1` unless explicitly disabled). Local Codex can run the backend path with no provider API key only when nested `codex exec --search` is network-capable; optional search providers (`BRAVE_SEARCH_API_KEY`, Google CSE, SerpAPI, Tavily, or opt-in Jina) can also supply shared backend search context.

Complete answers return direct text by default. If you need a saved `.md` or `.docx`, either complete-answer entrypoint keeps the same backend answer pipeline and renders the artifact from that verified answer.

Default legal-answer policy:

1. Indexed RAG first.
2. Code guide / subject guide second.
3. Online search where RAG coverage is thin, outdated, current-law verification is needed, or the user asks for online verification; hard-fail rather than claim verification when mandatory online verification cannot actually run.
4. Inline OSCOLA by default unless the user requests another citation style.
5. No local source-path leakage, fake citations, or hidden gold-standard examples in user output.

Default delivery policy:

- Complete essay/problem/chat answers return to chat/API unless the caller asks for `.md` or `.docx`.
- SQE question sets, SQE2 written guides, and SQE2 marking also return to chat/API unless the caller explicitly asks for an artifact.
- Amend/rewrite workflows produce the amended DOCX artifact for the user's Desktop by default.
- One-off helper files, prompt dumps, answer samples, and QA outputs should use `/private/tmp` and be deleted before the run finishes. If generated through a backend call, pass them through `cleanup_paths` where possible.
