# Quick Start

The project is backend-only now. Use the Python services directly instead of a frontend app.

## Main entrypoints

- `backend_answer_runtime.send_complete_answer_with_docs(...)`
  Canonical backend complete-answer path. Defaults to direct/backend delivery, keeps legal RAG and code-guide routing active, and runs the stricter complete-answer verification layer.
- `legal_doc_tools.workflow.run_auto_legal_doc_amend_workflow(...)`
  Automatic amend pipeline for uploaded or local DOCX files.

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies from `requirements.txt`.
3. Set the backend provider key the user wants to use, for example `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `XAI_API_KEY`. If no usable provider key is configured, direct-code mode can fall back to the local Codex adapter when Codex CLI access is available.

## Relevant backend files

- `gemini_service.py`
- `model_applicable_service.py`
- `backend_answer_runtime.py`
- `legal_doc_tools/workflow.py`
- `NEW_FEATURES.md`

## Validation

Use the backend regression tests in `Tests/` to verify the answer and amend flows after changes. Legal answer and amend requests automatically run through indexed RAG before generation. Complete answers return direct text by default; explicit Markdown requests are treated as markdown-compatible direct output rather than mandatory `.md` file generation.
