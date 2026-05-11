# Quick Start

The project is backend-only now. Use the Python services directly instead of a frontend app.

## Main entrypoints

- `backend_answer_runtime.send_complete_answer_with_docs(...)`
  Canonical backend complete-answer path. Defaults to direct/backend delivery, keeps legal RAG and code-guide routing active, runs the stricter complete-answer verification layer, and can now honour chat / `.md` / `.docx` delivery requests from the same path.
- `backend_answer_runtime.send_complete_answer_with_output(...)`
  Canonical delivery wrapper. Chat output, project `.md` files, and Desktop `.docx` files all derive from the same backend-generated and verified answer text, and registered temporary task-specific helper artifacts can be cleaned after a successful answer run.
- `backend_answer_runtime.send_sqe_question_set_with_docs(...)`
  Dedicated backend SQE question-set path. It supports FLK1, FLK2, SQE1, and SQE2 task generation, can attach official sample PDFs as style benchmarks, defaults to chat/API output, and disables essay-style complete-answer verification for question sets.
- `backend_answer_runtime.send_sqe2_marking_with_docs(...)`
  Dedicated SQE2 written-answer marking path. It marks candidate answers against the relevant written-skill criteria, uses the A-F simulated judgment scale, and can attach SQE2 sample/performance-indicator PDFs for guidance.
- `legal_doc_tools.workflow.run_auto_legal_doc_amend_workflow(...)`
  Automatic amend pipeline for uploaded or local DOCX files.

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies from `requirements.txt`.
3. Set the backend provider key the user wants to use, for example `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `XAI_API_KEY`. If no usable provider key is configured, direct-code mode can fall back to the local Codex adapter when Codex CLI access is available.

## Relevant backend files

- `model_applicable_service.py`
- `backend_answer_runtime.py`
- `legal_doc_tools/workflow.py`
- `NEW_FEATURES.md`

## Validation

Use the backend regression tests in `Tests/` to verify the answer and amend flows after changes. Legal answer and amend requests automatically run through indexed RAG before generation. If RAG is thin, local Codex can run the backend path with its own web-search capability and no provider API key; optional search providers (`BRAVE_SEARCH_API_KEY`, Google CSE, SerpAPI, Tavily, or opt-in Jina) can also supply shared backend search context. Complete answers return direct text by default; if you need a saved `.md` or `.docx`, either complete-answer entrypoint keeps the same backend answer pipeline and renders the artifact from that verified answer.
