"""
Regression check for the local plan-based large-DOCX amend path.
"""

import json
import tempfile
import zipfile
from pathlib import Path

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
    <w:p><w:r><w:t>Abstract</w:t></w:r></w:p>
    <w:p><w:r><w:t>This draft argues that privacy law needs reform.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Table of Contents</w:t></w:r></w:p>
    <w:p><w:r><w:t>Chapter 1: Introduction</w:t></w:r></w:p>
    <w:p><w:r><w:t>Current doctrine is fragmented and reactive.</w:t></w:r></w:p>
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
    source_path = root / "sample_large.docx"
    plans_dir = root / "plans"
    output_path = root / "sample_large_amended.docx"
    _write_minimal_docx(source_path)

    assert main(
        [
            str(source_path),
            "--export-plan-dir",
            str(plans_dir),
            "--sections",
            "abstract",
            "--rag-chunks",
            "0",
        ]
    ) == 0

    plan_path = plans_dir / "abstract.plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["_meta"]["mode"] == "codex_direct_amend"
    assert plan["_meta"]["section_name"] == "abstract"
    editable_indexes = [
        paragraph["index"]
        for paragraph in plan["paragraphs"]
        if paragraph["index"] not in set(plan["_meta"]["frozen_paragraph_indexes"])
    ]
    assert editable_indexes == [1]
    for paragraph in plan["paragraphs"]:
        if paragraph["index"] == 1:
            paragraph["text"] = (
                "This draft argues that United States privacy law needs structural reform."
            )
            break
    plan["summary"] = "Codex local plan regression test."
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")

    assert main(
        [
            str(source_path),
            "--plan-dir",
            str(plans_dir),
            "--sections",
            "abstract",
            "--output",
            str(output_path),
        ]
    ) == 0

    amended_root = _load_docx_xml(output_path, "word/document.xml")
    amended_texts = [_paragraph_text_all_runs(p) for p in _iter_body_paragraphs(amended_root)]
    assert amended_texts[1] == "This draft argues that United States privacy law needs structural reform."
    assert _count_yellow_highlight_runs_in_root(amended_root) > 0

print("Codex local amend path regression passed.")
