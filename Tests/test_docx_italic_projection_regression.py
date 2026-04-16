"""
Regression checks for DOCX amendment italic projection.
"""

from lxml import etree

from legal_doc_tools.amend_docx import _rewrite_body_paragraph_preserving_footnotes
from legal_doc_tools.refine_docx_from_amended import (
    NS,
    _has_effective_italic,
    _normalize_body_italics,
)


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _parse_paragraph(xml: str) -> etree._Element:
    return etree.fromstring(xml)


def _run_text_and_italic_flags(paragraph: etree._Element) -> list[tuple[str, bool]]:
    pairs: list[tuple[str, bool]] = []
    for run in paragraph.xpath("./w:r", namespaces=NS):
        text = "".join(run.xpath("./w:t/text()", namespaces=NS))
        if not text:
            continue
        rpr = run.find("w:rPr", namespaces=NS)
        pairs.append((text, _has_effective_italic(rpr)))
    return pairs


def _make_document(paragraph: etree._Element) -> etree._Element:
    xml = etree.tostring(paragraph, encoding="unicode")
    return etree.fromstring(
        f"""<w:document xmlns:w="{WORD_NS}">
  <w:body>
    {xml}
  </w:body>
</w:document>"""
    )


def _has_yellow_highlight(run: etree._Element) -> bool:
    rpr = run.find("w:rPr", namespaces=NS)
    if rpr is None:
        return False
    highlight = rpr.find("w:highlight", namespaces=NS)
    if highlight is None:
        return False
    return (highlight.get(f"{{{WORD_NS}}}val") or "").strip().lower() == "yellow"


def _has_bold(run: etree._Element) -> bool:
    rpr = run.find("w:rPr", namespaces=NS)
    if rpr is None:
        return False
    bold = rpr.find("w:b", namespaces=NS)
    return bold is not None and (bold.get(f"{{{WORD_NS}}}val") or "1").strip().lower() not in {"0", "false", "off", "no"}


old_para_xml = f"""<w:p xmlns:w="{WORD_NS}">
  <w:r>
    <w:rPr><w:i w:val="1"/></w:rPr>
    <w:t>Old italic segment</w:t>
  </w:r>
  <w:r><w:t xml:space="preserve"> and normal tail.</w:t></w:r>
</w:p>"""

new_normal_text = "Completely new normal content without any case names."

diff_para = _parse_paragraph(old_para_xml)
assert _rewrite_body_paragraph_preserving_footnotes(diff_para, new_normal_text) is True
diff_pairs = _run_text_and_italic_flags(diff_para)
assert diff_pairs, "Diff paragraph should contain text runs."
assert all(not is_italic for _text, is_italic in diff_pairs), diff_pairs

full_replace_para = _parse_paragraph(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:hyperlink w:anchor="x">
    <w:r>
      <w:rPr><w:i w:val="1"/></w:rPr>
      <w:t>Old italic segment</w:t>
    </w:r>
  </w:hyperlink>
  <w:r><w:t xml:space="preserve"> and normal tail.</w:t></w:r>
</w:p>"""
)
assert _rewrite_body_paragraph_preserving_footnotes(full_replace_para, new_normal_text) is True
full_replace_pairs = _run_text_and_italic_flags(full_replace_para)
assert full_replace_pairs, "Full-replace paragraph should contain text runs."
assert all(not is_italic for _text, is_italic in full_replace_pairs), full_replace_pairs

normalized_para = _parse_paragraph(old_para_xml)
assert _rewrite_body_paragraph_preserving_footnotes(normalized_para, new_normal_text) is True
doc_root = _make_document(normalized_para)
_normalize_body_italics(doc_root, None)
normalized_pairs = _run_text_and_italic_flags(normalized_para)
assert normalized_pairs, "Normalized paragraph should contain text runs."
assert all(not is_italic for _text, is_italic in normalized_pairs), normalized_pairs

styled_para = _parse_paragraph(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Garamond" w:hAnsi="Garamond"/>
      <w:sz w:val="28"/>
      <w:b w:val="1"/>
      <w:bCs w:val="1"/>
    </w:rPr>
    <w:t>Heading </w:t>
  </w:r>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Garamond" w:hAnsi="Garamond"/>
      <w:sz w:val="24"/>
      <w:i w:val="1"/>
      <w:iCs w:val="1"/>
    </w:rPr>
    <w:t>italic case</w:t>
  </w:r>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Garamond" w:hAnsi="Garamond"/>
      <w:sz w:val="24"/>
    </w:rPr>
    <w:t xml:space="preserve"> normal tail.</w:t>
  </w:r>
</w:p>"""
)
assert _rewrite_body_paragraph_preserving_footnotes(styled_para, "Heading italic case updated tail.") is True
styled_runs = [
    run
    for run in styled_para.xpath("./w:r", namespaces=NS)
    if "".join(run.xpath("./w:t/text()", namespaces=NS))
]
assert any(
    "".join(run.xpath("./w:t/text()", namespaces=NS)) == "Heading "
    and _has_bold(run)
    and not _has_yellow_highlight(run)
    for run in styled_runs
)
assert any(
    "".join(run.xpath("./w:t/text()", namespaces=NS)) == "italic case"
    and _has_effective_italic(run.find("w:rPr", namespaces=NS))
    and not _has_yellow_highlight(run)
    for run in styled_runs
)
assert any(
    "".join(run.xpath("./w:t/text()", namespaces=NS)) == "updated"
    and not _has_bold(run)
    and not _has_effective_italic(run.find("w:rPr", namespaces=NS))
    and _has_yellow_highlight(run)
    for run in styled_runs
)
assert any(
    "".join(run.xpath("./w:t/text()", namespaces=NS)) == " tail."
    and not _has_yellow_highlight(run)
    for run in styled_runs
)

print("DOCX italic projection regression checks passed.")
