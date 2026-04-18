"""
Regression checks for uploaded legal-document amend/review handling.
"""

import base64
import io
import tempfile
import zipfile
from pathlib import Path

from model_applicable_service import (
    _build_legal_doc_workflow_prompt_block,
    _build_uploaded_material_query_context,
    _collect_uploaded_materials,
    _detect_legal_doc_workflow,
)
from legal_doc_tools.workflow import (
    _build_structured_amend_prompt,
    _enforce_requested_word_count_rule,
    _snapshot_from_docx,
    wants_legal_doc_amend,
)
from word_count_rules import (
    amend_requested_word_count_window,
    complete_word_count_window,
    extract_requested_word_count_rule,
)


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _make_minimal_docx_bytes() -> bytes:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{WORD_NS}">
  <w:body>
    <w:p><w:r><w:t>Question: Critically analyse whether the doctrine is coherent.</w:t></w:r></w:p>
    <w:p><w:r><w:t>This draft argues the law is unclear and needs refinement.</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    footnotes_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="-1" w:type="separator">
    <w:p><w:r><w:t>separator</w:t></w:r></w:p>
  </w:footnote>
  <w:footnote w:id="1">
    <w:p><w:r><w:t>Donoghue v Stevenson [1932] AC 562.</w:t></w:r></w:p>
  </w:footnote>
</w:footnotes>
"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/footnotes.xml", footnotes_xml)
    return buffer.getvalue()


docx_payload = base64.b64encode(_make_minimal_docx_bytes()).decode("utf-8")
docx_documents = [
    {
        "id": "docx-1",
        "type": "file",
        "name": "draft.docx",
        "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "data": docx_payload,
        "size": len(docx_payload),
    }
]

materials = _collect_uploaded_materials(docx_documents)
assert len(materials) == 1
assert materials[0]["kind"] == "docx"
assert "Question: Critically analyse whether the doctrine is coherent." in materials[0]["text"]
assert "Footnote 1: Donoghue v Stevenson [1932] AC 562." in materials[0]["text"]

workflow = _detect_legal_doc_workflow(
    "Please amend my uploaded docx essay to a 90+ standard.",
    docx_documents,
    materials,
)
assert workflow["active"] is True
assert workflow["mode"] == "amend"
assert workflow["has_docx"] is True
exact_phrase_workflow = _detect_legal_doc_workflow(
    "use the code and rag amend this docx",
    docx_documents,
    materials,
)
assert exact_phrase_workflow["active"] is True
assert exact_phrase_workflow["mode"] == "amend"
typo_phrase_workflow = _detect_legal_doc_workflow(
    "use the code and rag amedn this docx",
    docx_documents,
    materials,
)
assert typo_phrase_workflow["active"] is True
assert typo_phrase_workflow["mode"] == "amend"
assert wants_legal_doc_amend("Please improve this to a 90+ standard and amend it.", docx_documents) is True
assert wants_legal_doc_amend("Please review this generally.", docx_documents) is True
assert wants_legal_doc_amend("Please check and polish this uploaded docx.", docx_documents) is True
assert wants_legal_doc_amend("use the code and rag amend this docx", docx_documents) is True
assert wants_legal_doc_amend("use the code and rag amedn this docx", docx_documents) is True

query_context = _build_uploaded_material_query_context(materials, max_total_chars=4000)
assert "Uploaded docx: draft.docx" in query_context
assert "Benchmarks:" in query_context
assert "Question: Critically analyse whether the doctrine is coherent." in query_context

prompt_block = _build_legal_doc_workflow_prompt_block(workflow, materials)
assert "[LEGAL DOCUMENT AMEND MODE]" in prompt_block
assert "Google Search grounding as a second layer" in prompt_block
assert "Shared legal backend guide anchors:" in prompt_block
assert "same substantive standard as the local legal-review amend workflow" in prompt_block
assert "downstream DOCX engine preserves styling and applies yellow-highlight-only markup" in prompt_block
assert "OSCOLA bibliography format is not OSCOLA footnote format" in prompt_block
assert "REVIEW/UPGRADE" not in prompt_block
assert "Website/API rule" not in prompt_block

harvard_prompt_block = _build_legal_doc_workflow_prompt_block(
    workflow,
    materials,
    citation_style="harvard",
)
assert "Harvard author-date because the user expressly requested Harvard referencing" in harvard_prompt_block
assert "Standard Harvard is not a footnote citation system" in harvard_prompt_block
assert "References" in harvard_prompt_block
assert "OSCOLA bibliography format is not OSCOLA footnote format" not in harvard_prompt_block

with tempfile.TemporaryDirectory() as tmp_dir:
    source_path = Path(tmp_dir) / "draft.docx"
    source_path.write_bytes(_make_minimal_docx_bytes())
    snapshot = _snapshot_from_docx(source_path)
    amend_prompt = _build_structured_amend_prompt(
        "Please amend this based on comments and keep my style.",
        snapshot,
    )
    assert "follow the backend legal guidance in `model_applicable_service.py` together with `LEGAL_DOC_GUIDE.md`" in amend_prompt
    assert "the user's original DOCX is read-only. Never overwrite the original source file path." in amend_prompt
    assert "implemented amendment markup is yellow highlight only." in amend_prompt
    assert "final amend delivery is one protected amended DOCX saved directly in Desktop root." in amend_prompt
    assert "amend quality target is a genuine 90+ / 10/10 standard" in amend_prompt
    assert "apply marker-feedback discipline on structure and clarity" in amend_prompt
    assert "do not mention excluded limbs or irrelevant scope limits unless they genuinely orient the answer" in amend_prompt
    assert "\"that structure\", \"this approach\", \"that rule\"" in amend_prompt
    assert "\"that obligation-based structure\" rather than \"that structure\"" in amend_prompt
    assert "keep bridge paragraphs in the section they actually introduce" in amend_prompt
    assert "do not repeat in a section-ending paragraph what is already reserved for the final conclusion" in amend_prompt
    assert "if a marker flags repetition, remove the earlier or weaker instance" in amend_prompt
    assert "do not use loose jurisdictional qualifiers such as \"particularly in the UK context\"" in amend_prompt
    assert "prefer fact-matched labels, for example \"consumer choice\"" in amend_prompt
    assert "locate dominance and abuse in the undertaking, not the product" in amend_prompt
    assert "do not over-plead self-preferencing or discrimination" in amend_prompt
    assert "keep OSCOLA bibliography format separate from OSCOLA footnote format" in amend_prompt
    assert "invert them to `Surname Initial,`" in amend_prompt
    assert "`authority_verification_report` and `sentence_support_report` are always required" in amend_prompt
    assert "\"authority_verification_report\"" in amend_prompt
    assert "\"sentence_support_report\"" in amend_prompt
    assert "\"question_guidance_report\"" in amend_prompt
    assert "\"comment_coverage\"" in amend_prompt

    harvard_amend_prompt = _build_structured_amend_prompt(
        "Please amend this using Harvard referencing and keep my style.",
        snapshot,
    )
    assert "active citation style: Harvard author-date" in harvard_amend_prompt
    assert "standard Harvard is not a footnote citation system" in harvard_amend_prompt
    assert "Harvard-style `References` format" in harvard_amend_prompt
    assert "do not use `ibid`, `op. cit.`" in harvard_amend_prompt
    assert "plain OSCOLA text only" not in harvard_amend_prompt

    amend_prompt_with_limit = _build_structured_amend_prompt(
        "Please amend this to 4000 words max.",
        snapshot,
    )
    assert "between 3970 and 3999 words" in amend_prompt_with_limit
    assert "requested ceiling" in amend_prompt_with_limit

    amend_prompt_with_benchmark = _build_structured_amend_prompt(
        "Please amend this.",
        snapshot,
        question_text="Critically analyse whether the doctrine is coherent.",
        rubric_text="Address coherence, authority support and conclusion quality.",
        source_path=source_path,
    )
    assert "Benchmark context:" in amend_prompt_with_benchmark
    assert "Question/Prompt: Critically analyse whether the doctrine is coherent." in amend_prompt_with_benchmark
    assert "Rubric/Criteria: Address coherence, authority support and conclusion quality." in amend_prompt_with_benchmark
    assert "`question_guidance_report` is required when benchmark context is supplied above" in amend_prompt_with_benchmark

    extracted_rule = extract_requested_word_count_rule("Please amend this to 4000 words max.")
    assert extracted_rule == {
        "mode": "at_or_below_max",
        "count": 4000,
        "lower_bound": 3970,
        "upper_bound": 3999,
    }
    assert complete_word_count_window(4000) == (3960, 4000)
    assert amend_requested_word_count_window(4000) == (3970, 3999)
    _enforce_requested_word_count_rule(
        ["word " * 3985],
        requested_word_rule=extracted_rule,
    )
    try:
        _enforce_requested_word_count_rule(
            ["Too short. " * 80],
            requested_word_rule=extracted_rule,
        )
        raise AssertionError("Expected amend word-count enforcement failure.")
    except ValueError as exc:
        assert "requested max-window" in str(exc)

research_only_documents = [
    {
        "id": "pdf-1",
        "type": "file",
        "name": "authorities.pdf",
        "mimeType": "application/pdf",
        "data": base64.b64encode(b"%PDF-1.4 fake pdf body").decode("utf-8"),
        "size": 24,
    }
]
research_workflow = _detect_legal_doc_workflow(
    "Write a 90+ essay on contract law using the uploaded research materials.",
    research_only_documents,
    [],
)
assert research_workflow["active"] is False

docx_answer_workflow = _detect_legal_doc_workflow(
    "Answer the legal question using my uploaded docx.",
    docx_documents,
    materials,
)
assert docx_answer_workflow["active"] is False

print("Uploaded legal-document workflow checks passed.")
