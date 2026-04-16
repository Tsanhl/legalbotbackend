# legalbotbackend

This repository is now backend-only. The Streamlit/UI layer and old frontend assets have been removed so the project focuses on two backend flows:

1. `backend_answer_runtime.send_complete_answer_with_docs(...)`
   Canonical backend complete-answer entrypoint. Uses direct/backend mode by default, keeps legal RAG + code-guide routing active, and applies the stricter complete-answer verification layer.
2. `legal_doc_tools.workflow.run_auto_legal_doc_amend_workflow(...)`
   Runs the automatic DOCX amend workflow for uploaded or local documents.

## Core backend modules

- `gemini_service.py`: main answer-generation logic and prompt/routing policy.
- `model_applicable_service.py`: provider-agnostic import surface for answer generation.
- `backend_answer_runtime.py`: deterministic answer-shaping, continuation, and output-quality helpers.
- `legal_doc_tools/workflow.py`: auto-amend workflow entrypoint.
- `rag_service.py` and `knowledge_base.py`: retrieval/index support.

## Quick start

1. Create a Python environment and install `requirements.txt`.
2. Configure the backend provider the user wants to use, for example `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `XAI_API_KEY`. Direct-code/backend requests can also fall back to the local Codex adapter when no usable provider key is configured and Codex CLI access is available.
3. Call the backend functions directly from code or tests.

## Example entrypoints

```python
from backend_answer_runtime import send_complete_answer_with_docs
from legal_doc_tools.workflow import run_auto_legal_doc_amend_workflow
```

For legal answer and amend requests, indexed RAG retrieval is automatic and mandatory before generation. Complete answers return direct chat/API text by default; if the user explicitly asks for Markdown, the backend treats that as markdown-compatible direct text rather than a required file write. The backend instructions and test coverage remain in place. Only the frontend/UI layer was removed.
