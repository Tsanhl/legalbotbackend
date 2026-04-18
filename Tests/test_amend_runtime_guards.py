"""
Regression checks for amend runtime guards that must hold even for direct function calls.
"""

import tempfile
import zipfile
from pathlib import Path

from legal_doc_tools import amend_docx
from legal_doc_tools import refine_docx_from_amended as refine


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _write_minimal_docx(path: Path, text: str = "Original text.") -> None:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{WORD_NS}">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document_xml)


def _minimal_review_context() -> dict[str, object]:
    return {
        "content_checked": True,
        "sentence_by_sentence_checked": True,
        "sentence_to_source_audit_checked": True,
        "argumentative_sentence_support_checked": True,
        "perfection_pass": True,
        "microscopic_style_polish_checked": True,
        "logical_coherence_checked": True,
        "weak_or_overstated_propositions_corrected": True,
        "citation_accuracy_checked": True,
        "citation_link_accuracy_checked": True,
        "amend_depth": "default_perfection",
        "target_standard": "90+",
        "word_count_followed": True,
        "word_count_instruction": "preserve original length",
        "word_count_mode": "preserve_original_length",
        "question_based_amend": False,
        "fit_verdict": "Fully fits target",
        "footnotes_checked": False,
        "bibliography_checked": False,
    }


with tempfile.TemporaryDirectory() as tmp_dir:
    root = Path(tmp_dir)
    desktop = root / "Desktop"
    desktop.mkdir()

    original_amend_desktop = amend_docx.DESKTOP_ROOT
    original_refine_desktop = refine.DESKTOP_ROOT
    amend_docx.DESKTOP_ROOT = desktop
    refine.DESKTOP_ROOT = desktop
    try:
        source = desktop / "essay.docx"
        _write_minimal_docx(source)

        bad_output = root / "project" / "essay_amended_marked_final.docx"
        bad_output.parent.mkdir()
        try:
            amend_docx.apply_amendments(
                source=source,
                output=bad_output,
                config={},
            )
            raise AssertionError("Expected Desktop-root guard failure for direct apply_amendments call.")
        except ValueError as exc:
            assert "Desktop root" in str(exc)
    finally:
        amend_docx.DESKTOP_ROOT = original_amend_desktop
        refine.DESKTOP_ROOT = original_refine_desktop


with tempfile.TemporaryDirectory() as tmp_dir:
    root = Path(tmp_dir)
    desktop = root / "Desktop"
    desktop.mkdir()

    original_amend_desktop = amend_docx.DESKTOP_ROOT
    original_refine_desktop = refine.DESKTOP_ROOT
    amend_docx.DESKTOP_ROOT = desktop
    refine.DESKTOP_ROOT = desktop
    try:
        source = desktop / "essay.docx"
        _write_minimal_docx(source)
        output = desktop / "essay_amended_marked_final.docx"
        project = root / "project"
        project.mkdir()

        verification_path = root / "verification.json"
        authority_path = root / "authority.json"
        sentence_path = root / "sentences.json"
        notes_md = project / "topic_notes.md"
        helper_py = project / "render_topic_notes.py"
        draft_docx = project / "topic_notes.docx"
        unrelated_readme = project / "README.md"
        for path in (verification_path, authority_path, sentence_path, notes_md, helper_py, draft_docx):
            path.write_text("{}", encoding="utf-8")
        unrelated_readme.write_text("keep", encoding="utf-8")

        # Monkeypatch validators so this regression only tests runtime cleanup/output guards.
        original_validate_authority = amend_docx._validate_authority_verification_report
        original_validate_sentence = amend_docx._validate_sentence_support_report
        amend_docx._validate_authority_verification_report = lambda *args, **kwargs: None
        amend_docx._validate_sentence_support_report = lambda *args, **kwargs: None
        try:
            changed, _review_context = amend_docx.apply_amendments(
                source=source,
                output=output,
                config={
                    "inline_replacements": [{"paragraph_index": 0, "old": "Original", "new": "Amended"}],
                    "verification_ledger_path": str(verification_path),
                    "authority_verification_report_path": str(authority_path),
                    "sentence_support_report_path": str(sentence_path),
                    "cleanup_paths": [str(notes_md), str(helper_py), str(draft_docx), str(source), str(output)],
                    "review_context": _minimal_review_context(),
                },
            )
            assert changed >= 1
            assert source.exists()
            assert output.exists()
            assert not verification_path.exists()
            assert not authority_path.exists()
            assert not sentence_path.exists()
            assert not notes_md.exists()
            assert not helper_py.exists()
            assert not draft_docx.exists()
            assert unrelated_readme.exists()
        finally:
            amend_docx._validate_authority_verification_report = original_validate_authority
            amend_docx._validate_sentence_support_report = original_validate_sentence
    finally:
        amend_docx.DESKTOP_ROOT = original_amend_desktop
        refine.DESKTOP_ROOT = original_refine_desktop


print("Amend runtime guard regression passed.")
