"""
Regression check for the local plan-based large-DOCX amend path on Topic headings.
"""

import json
import tempfile
import zipfile
from pathlib import Path

import legal_doc_tools.amend_large_docx_sections as amend_large
import legal_doc_tools.refine_docx_from_amended as refine
from legal_doc_tools.amend_large_docx_sections import main
from legal_doc_tools.refine_docx_from_amended import (
    _count_yellow_highlight_runs_in_root,
    _iter_body_paragraphs,
    _load_docx_xml,
    _paragraph_text_all_runs,
)


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _write_minimal_docx(path: Path) -> None:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{WORD_NS}">
  <w:body>
    <w:p><w:r><w:t>ADVANCED UK PENSIONS LAW</w:t></w:r></w:p>
    <w:p><w:r><w:t>Contents</w:t></w:r></w:p>
    <w:p><w:r><w:t>Topic 1. Snapshot rights</w:t></w:r></w:p>
    <w:p><w:r><w:t>Topic 2. Amendment powers</w:t></w:r></w:p>
    <w:p><w:r><w:t>Topic 1. Snapshot rights</w:t></w:r></w:p>
    <w:p><w:r><w:t>This draft states the section 67 rule too loosely.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Topic 2. Amendment powers</w:t></w:r></w:p>
    <w:p><w:r><w:t>This draft conflates validity and statutory protection.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Bibliography</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("word/document.xml", document_xml)


with tempfile.TemporaryDirectory() as tmp_dir:
    root = Path(tmp_dir)
    desktop = root / "Desktop"
    desktop.mkdir()
    source_path = root / "sample_topics.docx"
    plans_dir = root / "plans"
    requested_output_path = root / "sample_topics_amended.docx"
    expected_output_path = desktop / "sample_topics_amended_marked_final.docx"
    _write_minimal_docx(source_path)

    original_tool_desktop = amend_large.DESKTOP_ROOT
    original_refine_desktop = refine.DESKTOP_ROOT
    amend_large.DESKTOP_ROOT = desktop
    refine.DESKTOP_ROOT = desktop

    try:
        assert main(
            [
                str(source_path),
                "--export-plan-dir",
                str(plans_dir),
                "--sections",
                "topic_1",
                "--rag-chunks",
                "0",
            ]
        ) == 0

        plan_path = plans_dir / "topic_1.plan.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        assert plan["_meta"]["mode"] == "codex_direct_amend"
        assert plan["_meta"]["section_name"] == "topic_1"
        editable_indexes = [
            paragraph["index"]
            for paragraph in plan["paragraphs"]
            if paragraph["index"] not in set(plan["_meta"]["frozen_paragraph_indexes"])
        ]
        assert editable_indexes == [1]
        for paragraph in plan["paragraphs"]:
            if paragraph["index"] == 1:
                paragraph["text"] = (
                    "This draft states the section 67 rule precisely by using the immediate-cessation snapshot."
                )
                break
        plan["summary"] = "Codex local topic-plan regression test."
        plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")

        assert main(
            [
                str(source_path),
                "--plan-dir",
                str(plans_dir),
                "--sections",
                "topic_1",
                "--output",
                str(requested_output_path),
            ]
        ) == 0

        assert source_path.exists()
        assert not requested_output_path.exists()
        assert expected_output_path.exists()

        amended_root = _load_docx_xml(expected_output_path, "word/document.xml")
        amended_texts = [_paragraph_text_all_runs(p) for p in _iter_body_paragraphs(amended_root)]
        assert amended_texts[5] == "This draft states the section 67 rule precisely by using the immediate-cessation snapshot."
        assert _count_yellow_highlight_runs_in_root(amended_root) > 0
    finally:
        amend_large.DESKTOP_ROOT = original_tool_desktop
        refine.DESKTOP_ROOT = original_refine_desktop

print("Codex local topic amend path regression passed.")
