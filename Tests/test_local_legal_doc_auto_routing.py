"""
Regression checks for local DOCX amend auto-detection and routing.
"""

import tempfile
from pathlib import Path

import legal_doc_tools.workflow as workflow


with tempfile.TemporaryDirectory() as tmp_dir:
    root = Path(tmp_dir)
    desktop = root / "Desktop"
    desktop.mkdir()

    principles = desktop / "Principles.docx"
    principles.write_bytes(b"local-docx")

    assert workflow.wants_local_legal_doc_amend(
        "Please amend Principles.docx to a 90+ standard.",
        search_roots=[desktop],
    ) is True
    assert workflow.wants_local_legal_doc_amend(
        'Please based on code guide amend "Principles.docx".',
        search_roots=[desktop],
    ) is True
    assert workflow.resolve_local_legal_doc_amend_path(
        "Please amend Principles.docx to a 90+ standard.",
        search_roots=[desktop],
    ) == principles.resolve()

    spaced = desktop / "Principles notes.docx"
    spaced.write_bytes(b"local-docx")
    assert workflow.resolve_local_legal_doc_amend_path(
        'use code + rag amend locally "Principles notes.docx"',
        search_roots=[desktop],
    ) == spaced.resolve()

    assert workflow.wants_local_legal_doc_amend(
        "Answer the question using Principles.docx only.",
        search_roots=[desktop],
    ) is False


with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
    root_a = Path(tmp_a)
    root_b = Path(tmp_b)
    first = root_a / "essay.docx"
    second = root_b / "essay.docx"
    first.write_bytes(b"a")
    second.write_bytes(b"b")

    try:
        workflow.resolve_local_legal_doc_amend_path(
            "Please amend essay.docx.",
            search_roots=[root_a, root_b],
        )
        raise AssertionError("Expected ambiguous local DOCX detection to fail.")
    except ValueError as exc:
        assert "ambiguous" in str(exc).lower()


captured: dict[str, object] = {}
original_local = workflow.run_local_legal_doc_amend_workflow
original_uploaded = workflow.run_uploaded_legal_doc_amend_workflow
try:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        desktop = root / "Desktop"
        desktop.mkdir()
        source = desktop / "Principles.docx"
        source.write_bytes(b"local-docx")

        def _fake_local(**kwargs):
            captured["mode"] = "local"
            captured["source_path"] = kwargs["source_path"]
            captured["message"] = kwargs["message"]
            return "local-result"

        def _fake_uploaded(**kwargs):
            captured["mode"] = "uploaded"
            return "uploaded-result"

        workflow.run_local_legal_doc_amend_workflow = _fake_local
        workflow.run_uploaded_legal_doc_amend_workflow = _fake_uploaded

        result = workflow.run_auto_legal_doc_amend_workflow(
            api_key="test-key",
            message="Please amend Principles.docx and keep yellow highlights.",
            documents=[],
            search_roots=[desktop],
        )
        assert result == "local-result"
        assert captured["mode"] == "local"
        assert captured["source_path"] == source.resolve()
        assert captured["message"] == "Please amend Principles.docx and keep yellow highlights."
finally:
    workflow.run_local_legal_doc_amend_workflow = original_local
    workflow.run_uploaded_legal_doc_amend_workflow = original_uploaded


print("Local legal-doc auto-routing checks passed.")
