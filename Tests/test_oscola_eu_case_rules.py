"""
Regression checks for OSCOLA EU case-law guidance and Table of Cases handling.
"""

from pathlib import Path

from lxml import etree

from legal_doc_tools.refine_docx_from_amended import (
    NS,
    _normalize_bibliography_bold,
    _normalize_body_italics,
    _normalize_case_italics_in_footnotes,
)
from legal_doc_tools.validate_delivery_gates import _oscola_issues


ROOT = Path("/Users/hltsang/Desktop/doc-ai copy *latest copy 2 (self) (17 feb) copy 7")
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


guide_text = (ROOT / "legal_doc_tools" / "LEGAL_DOC_GUIDE.md").read_text(encoding="utf-8")
gemini_text = (ROOT / "model_applicable_service.py").read_text(encoding="utf-8")

assert "Do not auto-italicise `Table of Cases` entries" in guide_text
assert "For EU cases, use `para` / `paras` after a comma for pinpoint paragraph references" in guide_text
assert "Case C-527/15 Stichting Brein v Jack Frederik Wullems [2017] OJ C195/02." in guide_text
assert "If the user has already italicised a short-form case name correctly" in guide_text
assert "keep case names in roman by default" in guide_text
assert "same local font family, font size, paragraph style, spacing, and emphasis pattern" in guide_text
assert "Added-support rule for DOCX amendments" in guide_text
assert "Body-italics preservation rule (mandatory)" in guide_text
assert "Footnote/bibliography italics preservation rule (mandatory)" in guide_text
assert "Plain-text inline OSCOLA typography rule (mandatory)" in guide_text
assert "Bibliography bolding rule (mandatory)" in guide_text
assert "OSCOLA author-name separation rule (mandatory)" in guide_text
assert "In footnotes, give personal author/editor names in the form used in the publication" in guide_text
assert "In bibliography/reference entries, invert personal names to `Surname Initial,`" in guide_text
assert "e.g. `Hart HLA, *The Concept of Law* (2nd edn, Clarendon Press 1994)`" in guide_text
assert "e.g. `Ashworth A, ‘Testing Fidelity to Legal Values’ (2000) 63 MLR 633`" in guide_text
assert "For EU case law, use the OSCOLA order with the case number first" in gemini_text
assert "add the new authority in parentheses immediately after that sentence" in gemini_text
assert "Case C-176/03 *Commission v Council* [2005] ECR I-7879, paras 47-48" in gemini_text
assert "Italicise case names inside those parenthetical OSCOLA citations as well" in gemini_text
assert "keep case names in roman there by default" in gemini_text
assert "OSCOLA bibliography format is not OSCOLA footnote format" in gemini_text


document_root = etree.fromstring(
    f"""<w:document xmlns:w="{WORD_NS}">
  <w:body>
    <w:p><w:r><w:t>Table of Cases</w:t></w:r></w:p>
    <w:p><w:r><w:t>Arne Mathisen AS v Council (T-344/99) [2002] ECR II-2905</w:t></w:r></w:p>
    <w:p><w:r><w:t>Introduction</w:t></w:r></w:p>
    <w:p><w:r><w:t>Commission v Council [2005] ECR I-7879 remains central.</w:t></w:r></w:p>
  </w:body>
</w:document>"""
)

assert _normalize_body_italics(document_root, None) >= 1

table_entry_runs = document_root.xpath("/w:document/w:body/w:p[2]/w:r", namespaces=NS)
assert table_entry_runs, "Expected Table of Cases entry runs."
assert not any(run.xpath("./w:rPr/w:i|./w:rPr/w:iCs", namespaces=NS) for run in table_entry_runs)
body_case_runs = document_root.xpath("/w:document/w:body/w:p[4]/w:r", namespaces=NS)
assert any(run.xpath("./w:rPr/w:i|./w:rPr/w:iCs", namespaces=NS) for run in body_case_runs)

issues = _oscola_issues(
    document_text="Table of Cases\nArne Mathisen AS v Council (T-344/99) [2002] ECR II-2905\nIntroduction\nCommission v Council [2005] ECR I-7879 remains central.",
    footnotes_text="",
    footnotes_root=None,
    document_root=document_root,
)
assert not any("Arne Mathisen" in issue for issue in issues), issues

bib_case_root = etree.fromstring(
    f"""<w:document xmlns:w="{WORD_NS}">
  <w:body>
    <w:p><w:r><w:t>Bibliography</w:t></w:r></w:p>
    <w:p><w:r><w:t>British Airways plc v Commission [2007] ECR I-2331</w:t></w:r></w:p>
  </w:body>
</w:document>"""
)
assert _normalize_body_italics(bib_case_root, None) >= 1
bib_case_runs = bib_case_root.xpath("/w:document/w:body/w:p[2]/w:r", namespaces=NS)
assert any(run.xpath("./w:rPr/w:i|./w:rPr/w:iCs", namespaces=NS) for run in bib_case_runs)

body_root = etree.fromstring(
    f"""<w:document xmlns:w="{WORD_NS}">
  <w:body>
    <w:p>
      <w:r>
        <w:rPr><w:i w:val="1"/><w:iCs w:val="1"/><w:highlight w:val="yellow"/></w:rPr>
        <w:t>This is ordinary amended prose.</w:t>
      </w:r>
    </w:p>
    <w:p>
      <w:r>
        <w:rPr><w:highlight w:val="yellow"/></w:rPr>
        <w:t>The share creates a prima facie inference of dominance.</w:t>
      </w:r>
    </w:p>
  </w:body>
</w:document>"""
)
assert _normalize_body_italics(body_root, None) >= 1
first_para_runs = body_root.xpath("/w:document/w:body/w:p[1]/w:r", namespaces=NS)
assert first_para_runs
assert first_para_runs[0].xpath("./w:rPr/w:i|./w:rPr/w:iCs", namespaces=NS)
second_para_runs = body_root.xpath("/w:document/w:body/w:p[2]/w:r", namespaces=NS)
assert any(run.xpath("./w:rPr/w:i|./w:rPr/w:iCs", namespaces=NS) for run in second_para_runs)

footnote_root = etree.fromstring(
    f"""<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="2">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:rPr><w:i w:val="1"/><w:iCs w:val="1"/></w:rPr><w:t>United Brands</w:t></w:r>
      <w:r><w:t> (n 32).</w:t></w:r>
    </w:p>
  </w:footnote>
</w:footnotes>"""
)
assert _normalize_case_italics_in_footnotes(footnote_root) >= 0
fn_runs = footnote_root.xpath("/w:footnotes/w:footnote[@w:id='2']/w:p/w:r", namespaces=NS)
assert any('United Brands' in ''.join(run.xpath('./w:t/text()', namespaces=NS)) and run.xpath('./w:rPr/w:i|./w:rPr/w:iCs', namespaces=NS) for run in fn_runs)

bib_root = etree.fromstring(
    f"""<w:document xmlns:w="{WORD_NS}">
  <w:body>
    <w:p><w:r><w:t>Bibliography</w:t></w:r></w:p>
    <w:p><w:r><w:rPr><w:b w:val="1"/><w:bCs w:val="1"/></w:rPr><w:t>British Airways plc v Commission</w:t></w:r></w:p>
    <w:p><w:r><w:t>Journal Articles</w:t></w:r></w:p>
    <w:p><w:r><w:rPr><w:b w:val="1"/><w:bCs w:val="1"/></w:rPr><w:t>Edelman B, ‘Does Google Leverage Market Power through Tying and Bundling?’</w:t></w:r></w:p>
  </w:body>
</w:document>"""
)
assert _normalize_bibliography_bold(bib_root) >= 1
bib_heading_runs = bib_root.xpath("/w:document/w:body/w:p[1]/w:r", namespaces=NS)
assert any(run.xpath("./w:rPr/w:b|./w:rPr/w:bCs", namespaces=NS) for run in bib_heading_runs)
bib_case_runs = bib_root.xpath("/w:document/w:body/w:p[2]/w:r", namespaces=NS)
assert not any(run.xpath("./w:rPr/w:b|./w:rPr/w:bCs", namespaces=NS) for run in bib_case_runs)
journal_heading_runs = bib_root.xpath("/w:document/w:body/w:p[3]/w:r", namespaces=NS)
assert any(run.xpath("./w:rPr/w:b|./w:rPr/w:bCs", namespaces=NS) for run in journal_heading_runs)
journal_entry_runs = bib_root.xpath("/w:document/w:body/w:p[4]/w:r", namespaces=NS)
assert not any(run.xpath("./w:rPr/w:b|./w:rPr/w:bCs", namespaces=NS) for run in journal_entry_runs)

print("OSCOLA EU case-law rule regression checks passed.")
