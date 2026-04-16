"""Public entry points for legal-document amendment workflows."""

from .workflow import (
    DOCX_MIME,
    LegalDocAmendResult,
    resolve_local_legal_doc_amend_path,
    run_auto_legal_doc_amend_workflow,
    run_local_legal_doc_amend_workflow,
    run_uploaded_legal_doc_amend_workflow,
    wants_legal_doc_amend,
    wants_local_legal_doc_amend,
)

__all__ = [
    "DOCX_MIME",
    "LegalDocAmendResult",
    "resolve_local_legal_doc_amend_path",
    "run_auto_legal_doc_amend_workflow",
    "run_local_legal_doc_amend_workflow",
    "run_uploaded_legal_doc_amend_workflow",
    "wants_legal_doc_amend",
    "wants_local_legal_doc_amend",
]
