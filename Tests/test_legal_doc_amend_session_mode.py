"""
Regression checks for legal-doc amend session acceptance cleanup.
"""

import tempfile
from pathlib import Path

from model_applicable_service import (
    detect_legal_doc_amend_session_signal,
    register_legal_doc_amend_cleanup_paths,
    send_message_with_docs,
)


history = [
    {"role": "user", "text": "Please amend my uploaded docx essay to a 90+ standard."},
    {"role": "assistant", "text": "Amended DOCX ready."},
]

accept_signal = detect_legal_doc_amend_session_signal(
    "done, accept delivery",
    history,
    active=True,
)
assert accept_signal["is_acceptance"] is True
assert accept_signal["is_amendment"] is False

amend_signal = detect_legal_doc_amend_session_signal(
    "also amend abstract, table of contents, bibliography and keep my style",
    history,
    active=True,
)
assert amend_signal["is_acceptance"] is False
assert amend_signal["is_amendment"] is True

runtime_dir = Path(".codex_runtime")
runtime_dir.mkdir(exist_ok=True)

with tempfile.TemporaryDirectory() as tmp_dir:
    root = Path(tmp_dir)
    helper_dir = root / "doc_specific_helper_code"
    helper_dir.mkdir()
    helper_file = helper_dir / "helper.py"
    helper_file.write_text("temp helper", encoding="utf-8")

    runtime_hint = runtime_dir / "legal_doc_verification_ledger_acceptance_test.txt"
    runtime_hint.write_text("temp ledger", encoding="utf-8")

    project_id = "legal_doc_acceptance_cleanup_test"
    register_legal_doc_amend_cleanup_paths(project_id, [helper_dir])

    (accept_text, _accept_meta), _accept_rag = send_message_with_docs(
        api_key="",
        message="delivery accepted",
        documents=[],
        project_id=project_id,
        history=history,
        stream=False,
    )

    assert "legal-doc amend session and temporary amend artifacts have been cleared" in accept_text
    assert not helper_dir.exists()
    assert not runtime_hint.exists()

print("Legal-doc amend session cleanup checks passed.")
