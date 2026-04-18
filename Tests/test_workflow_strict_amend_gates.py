"""
Regression checks for the strict default legal-document amend workflow.
"""

import json
import tempfile
import zipfile
from pathlib import Path

import legal_doc_tools.amend_docx as amend_docx
import legal_doc_tools.refine_docx_from_amended as refine
import legal_doc_tools.validate_delivery_gates as delivery_gates
import legal_doc_tools.workflow as workflow


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _write_docx_with_footnote(path: Path) -> None:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{WORD_NS}">
  <w:body>
    <w:p><w:r><w:t>Question: Critically analyse whether the doctrine is coherent.</w:t></w:r></w:p>
    <w:p>
      <w:r><w:t>This draft argues the doctrine is uncertain.</w:t></w:r>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteReference w:id="1"/></w:r>
    </w:p>
  </w:body>
</w:document>
"""
    footnotes_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="-1" w:type="separator">
    <w:p><w:r><w:t>separator</w:t></w:r></w:p>
  </w:footnote>
  <w:footnote w:id="0" w:type="continuationSeparator">
    <w:p><w:r><w:t>continuation</w:t></w:r></w:p>
  </w:footnote>
  <w:footnote w:id="1">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t>Donoghue v Stevenson [1932] AC 562.</w:t></w:r>
    </w:p>
  </w:footnote>
</w:footnotes>
"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>
</Types>
"""
    root_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{PKG_REL_NS}">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
    document_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{PKG_REL_NS}">
  <Relationship Id="rIdFootnotes" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/>
</Relationships>
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/footnotes.xml", footnotes_xml)
        archive.writestr("word/_rels/document.xml.rels", document_rels)


def _strict_response(include_reports: bool = True) -> str:
    payload = {
        "summary": "Strict amend workflow regression output.",
        "paragraphs": [
            {"index": 0, "text": "Question: Critically analyse whether the doctrine is coherent."},
            {
                "index": 1,
                "text": "This amended draft argues the doctrine is only partly coherent and needs clearer judicial reasoning.",
            },
        ],
        "footnotes": [
            {"id": 1, "text": "Donoghue v Stevenson [1932] AC 562 (HL)."},
        ],
        "authority_verification_report": {
            "automatic": True,
            "verification_mode": "automatic_report",
            "summary": {"unverified": 0},
            "footnotes": [
                {"id": 1, "verified": True, "source_exists": True, "metadata_matches": True},
            ],
        },
        "sentence_support_report": {
            "automatic": True,
            "verification_mode": "automatic_report",
            "summary": {
                "unsupported": 0,
                "overstated": 0,
                "weak": 0,
                "all_argumentative_sentences_covered": True,
                "argumentative_sentences": 1,
            },
            "sentences": [
                {
                    "id": 1,
                    "text": "This amended draft argues the doctrine is only partly coherent and needs clearer judicial reasoning.",
                    "supported": True,
                    "proposition_accuracy_checked": True,
                    "sources_checked": ["Footnote 1"],
                    "support_level": "direct",
                }
            ],
        },
        "question_guidance_report": {
            "mode": "guide_if_needed",
            "summary": {"unresolved": 0},
            "issues": [
                {"id": 1, "issue": "Directly answers the question.", "status": "already_covered"},
                {"id": 2, "issue": "Analytical conclusion.", "status": "added"},
            ],
        },
    }
    if not include_reports:
        payload.pop("authority_verification_report")
    return json.dumps(payload)


with tempfile.TemporaryDirectory() as tmp_dir:
    root = Path(tmp_dir)
    desktop = (root / "Desktop").resolve()
    desktop.mkdir()
    source = desktop / "essay.docx"
    _write_docx_with_footnote(source)

    original_workflow_desktop = workflow.DESKTOP_ROOT
    original_refine_desktop = refine.DESKTOP_ROOT
    original_amend_desktop = amend_docx.DESKTOP_ROOT
    original_gate_desktop = delivery_gates.DESKTOP_ROOT
    original_send = workflow.send_message_with_docs

    workflow.DESKTOP_ROOT = desktop
    refine.DESKTOP_ROOT = desktop
    amend_docx.DESKTOP_ROOT = desktop
    delivery_gates.DESKTOP_ROOT = desktop
    workflow.send_message_with_docs = lambda *args, **kwargs: ((_strict_response(), None), None)
    try:
        result = workflow.run_local_legal_doc_amend_workflow(
            api_key="test-key",
            source_path=source,
            message="Please amend this to a 90+ standard. Question: Critically analyse whether the doctrine is coherent.",
        )
        assert result.output_path == desktop / "essay_amended_marked_final.docx"
        assert result.output_path.exists()
        amended_root = refine._load_docx_xml(result.output_path, "word/document.xml")
        amended_texts = [refine._paragraph_text_all_runs(p) for p in refine._iter_body_paragraphs(amended_root)]
        assert amended_texts[1] == "This amended draft argues the doctrine is only partly coherent and needs clearer judicial reasoning."
        assert refine._count_yellow_highlight_runs_in_root(amended_root) > 0
        assert result.changed_paragraphs == 1
        assert result.changed_footnotes == 1
    finally:
        workflow.DESKTOP_ROOT = original_workflow_desktop
        refine.DESKTOP_ROOT = original_refine_desktop
        amend_docx.DESKTOP_ROOT = original_amend_desktop
        delivery_gates.DESKTOP_ROOT = original_gate_desktop
        workflow.send_message_with_docs = original_send


with tempfile.TemporaryDirectory() as tmp_dir:
    root = Path(tmp_dir)
    desktop = (root / "Desktop").resolve()
    desktop.mkdir()
    source = desktop / "essay.docx"
    _write_docx_with_footnote(source)
    (desktop / "essay_amended_marked_final.docx").write_bytes(b"prior-final")

    original_workflow_desktop = workflow.DESKTOP_ROOT
    original_refine_desktop = refine.DESKTOP_ROOT
    original_amend_desktop = amend_docx.DESKTOP_ROOT
    original_gate_desktop = delivery_gates.DESKTOP_ROOT
    original_send = workflow.send_message_with_docs

    workflow.DESKTOP_ROOT = desktop
    refine.DESKTOP_ROOT = desktop
    amend_docx.DESKTOP_ROOT = desktop
    delivery_gates.DESKTOP_ROOT = desktop
    workflow.send_message_with_docs = lambda *args, **kwargs: ((_strict_response(), None), None)
    try:
        result = workflow.run_local_legal_doc_amend_workflow(
            api_key="test-key",
            source_path=source,
            message="Please amend this to a 90+ standard. Question: Critically analyse whether the doctrine is coherent.",
        )
        assert result.output_path == desktop / "essay_amended_marked_final_v2.docx"
        assert result.output_path.exists()
        assert (desktop / "essay_amended_marked_final.docx").read_bytes() == b"prior-final"
    finally:
        workflow.DESKTOP_ROOT = original_workflow_desktop
        refine.DESKTOP_ROOT = original_refine_desktop
        amend_docx.DESKTOP_ROOT = original_amend_desktop
        delivery_gates.DESKTOP_ROOT = original_gate_desktop
        workflow.send_message_with_docs = original_send


with tempfile.TemporaryDirectory() as tmp_dir:
    root = Path(tmp_dir)
    desktop = (root / "Desktop").resolve()
    desktop.mkdir()
    source = desktop / "essay.docx"
    _write_docx_with_footnote(source)

    original_workflow_desktop = workflow.DESKTOP_ROOT
    original_refine_desktop = refine.DESKTOP_ROOT
    original_amend_desktop = amend_docx.DESKTOP_ROOT
    original_gate_desktop = delivery_gates.DESKTOP_ROOT
    original_send = workflow.send_message_with_docs

    workflow.DESKTOP_ROOT = desktop
    refine.DESKTOP_ROOT = desktop
    amend_docx.DESKTOP_ROOT = desktop
    delivery_gates.DESKTOP_ROOT = desktop
    workflow.send_message_with_docs = lambda *args, **kwargs: ((_strict_response(include_reports=False), None), None)
    try:
        try:
            workflow.run_local_legal_doc_amend_workflow(
                api_key="test-key",
                source_path=source,
                message="Please amend this to a 90+ standard. Question: Critically analyse whether the doctrine is coherent.",
            )
            raise AssertionError("Expected strict workflow to reject missing verification artifacts.")
        except ValueError as exc:
            assert "authority_verification_report" in str(exc)
        assert not (desktop / "essay_amended_marked_final.docx").exists()
    finally:
        workflow.DESKTOP_ROOT = original_workflow_desktop
        refine.DESKTOP_ROOT = original_refine_desktop
        amend_docx.DESKTOP_ROOT = original_amend_desktop
        delivery_gates.DESKTOP_ROOT = original_gate_desktop
        workflow.send_message_with_docs = original_send


print("Strict workflow amend gate regression passed.")
