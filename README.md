# legalbotbackend

This repository is now backend-only. The Streamlit/UI layer and old frontend assets have been removed so the project focuses on two backend flows:

1. `backend_answer_runtime.send_complete_answer_with_docs(...)`
   Canonical backend complete-answer entrypoint. Uses direct/backend mode by default, keeps legal RAG + code-guide routing active, applies the stricter complete-answer verification layer, and now honours chat / `.md` / `.docx` delivery requests without switching generation pipelines.
2. `backend_answer_runtime.send_complete_answer_with_output(...)`
   Canonical delivery wrapper. It always generates through `send_complete_answer_with_docs(...)` first, then optionally saves that same verified answer as a project `.md` artifact or a Desktop `.docx` artifact. It can also clean registered one-off helper artifacts after a successful complete-answer run.
3. `legal_doc_tools.workflow.run_auto_legal_doc_amend_workflow(...)`
   Runs the automatic DOCX amend workflow for uploaded or local documents.

## Core backend modules

- `model_applicable_service.py`: canonical answer-generation logic and provider-agnostic prompt/routing policy.
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
from backend_answer_runtime import send_complete_answer_with_output
from legal_doc_tools.workflow import run_auto_legal_doc_amend_workflow
```

For legal answer and amend requests, indexed RAG retrieval is automatic and mandatory before generation. Complete answers return direct chat/API text by default; if the caller wants a saved `.md` or `.docx`, both complete-answer entrypoints now keep the same backend answer pipeline and render the artifact from that verified answer text rather than through a separate generation path. The backend instructions and test coverage remain in place. Only the frontend/UI layer was removed.
