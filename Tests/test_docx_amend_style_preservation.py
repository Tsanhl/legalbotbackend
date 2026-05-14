"""
Regression checks for preserving user local typography on highlighted amend insertions.
"""

from lxml import etree

from legal_doc_tools.amend_docx import _clone_paragraph_for_insertion
from legal_doc_tools.refine_docx_from_amended import (
    NS,
    _apply_full_replace_to_paragraph,
    _has_effective_bold,
    _has_effective_italic,
)


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _parse_paragraph(xml: str) -> etree._Element:
    return etree.fromstring(xml)


def _text_runs(paragraph: etree._Element) -> list[etree._Element]:
    return [
        run
        for run in paragraph.xpath("./w:r", namespaces=NS)
        if "".join(run.xpath("./w:t/text()", namespaces=NS))
    ]


def _assert_rpr_matches_user_style(run: etree._Element) -> None:
    rpr = run.find("w:rPr", namespaces=NS)
    assert rpr is not None, "Expected direct run properties on amended text."

    rfonts = rpr.find("w:rFonts", namespaces=NS)
    assert rfonts is not None, "Expected amended run to inherit user font settings."
    assert (rfonts.get(f"{{{WORD_NS}}}ascii") or "") == "Times New Roman"
    assert (rfonts.get(f"{{{WORD_NS}}}hAnsi") or "") == "Times New Roman"

    size = rpr.find("w:sz", namespaces=NS)
    assert size is not None and (size.get(f"{{{WORD_NS}}}val") or "") == "24"

    lang = rpr.find("w:lang", namespaces=NS)
    assert lang is not None and (lang.get(f"{{{WORD_NS}}}val") or "") == "en-HK"

    color = rpr.find("w:color", namespaces=NS)
    assert color is not None and (color.get(f"{{{WORD_NS}}}val") or "") == "000000"

    highlight = rpr.find("w:highlight", namespaces=NS)
    assert highlight is not None and (highlight.get(f"{{{WORD_NS}}}val") or "") == "yellow"


def _assert_run_not_effectively_bold_or_italic(run: etree._Element) -> None:
    rpr = run.find("w:rPr", namespaces=NS)
    assert not _has_effective_bold(rpr), "Amended text should not inherit inline bold from the template run."
    assert not _has_effective_italic(rpr), "Amended text should not inherit inline italics from the template run."


base_template = _parse_paragraph(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:pPr>
    <w:spacing w:after="240" w:line="360" w:lineRule="auto"/>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:color w:val="000000"/>
      <w:lang w:val="en-HK"/>
    </w:rPr>
  </w:pPr>
  <w:r><w:t>Original table text</w:t></w:r>
</w:p>"""
)

full_replace_para = _parse_paragraph(etree.tostring(base_template, encoding="unicode"))
assert _apply_full_replace_to_paragraph(
    full_replace_para,
    "Changed table text",
    markup=True,
) is True
replaced_runs = _text_runs(full_replace_para)
assert len(replaced_runs) == 1
_assert_rpr_matches_user_style(replaced_runs[0])
_assert_run_not_effectively_bold_or_italic(replaced_runs[0])

bold_template = _parse_paragraph(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:pPr>
    <w:spacing w:after="240" w:line="360" w:lineRule="auto"/>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:color w:val="000000"/>
      <w:lang w:val="en-HK"/>
    </w:rPr>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:color w:val="000000"/>
      <w:lang w:val="en-HK"/>
      <w:b w:val="1"/>
      <w:bCs w:val="1"/>
    </w:rPr>
    <w:t>Bold template text</w:t>
  </w:r>
</w:p>"""
)

bold_full_replace_para = _parse_paragraph(etree.tostring(bold_template, encoding="unicode"))
assert _apply_full_replace_to_paragraph(
    bold_full_replace_para,
    "Changed plain text",
    markup=True,
) is True
bold_replaced_runs = _text_runs(bold_full_replace_para)
assert len(bold_replaced_runs) == 1
_assert_rpr_matches_user_style(bold_replaced_runs[0])
assert _has_effective_bold(bold_replaced_runs[0].find("w:rPr", namespaces=NS))
assert not _has_effective_italic(bold_replaced_runs[0].find("w:rPr", namespaces=NS))

italic_style_template = _parse_paragraph(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:pPr>
    <w:spacing w:after="240" w:line="360" w:lineRule="auto"/>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:color w:val="000000"/>
      <w:lang w:val="en-HK"/>
    </w:rPr>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:color w:val="000000"/>
      <w:lang w:val="en-HK"/>
      <w:rStyle w:val="Emphasis"/>
    </w:rPr>
    <w:t>Italic template text</w:t>
  </w:r>
</w:p>"""
)

italic_insert = _clone_paragraph_for_insertion(italic_style_template, "Inserted plain text")
italic_insert_runs = _text_runs(italic_insert)
assert len(italic_insert_runs) == 1
_assert_rpr_matches_user_style(italic_insert_runs[0])
assert not _has_effective_bold(italic_insert_runs[0].find("w:rPr", namespaces=NS))
assert _has_effective_italic(italic_insert_runs[0].find("w:rPr", namespaces=NS))

paragraph_default_styled_template = _parse_paragraph(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:pPr>
    <w:spacing w:after="240" w:line="360" w:lineRule="auto"/>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:color w:val="000000"/>
      <w:lang w:val="en-HK"/>
      <w:b w:val="1"/>
      <w:bCs w:val="1"/>
      <w:i w:val="1"/>
      <w:iCs w:val="1"/>
    </w:rPr>
  </w:pPr>
  <w:r><w:t>Paragraph-level styled text</w:t></w:r>
</w:p>"""
)

paragraph_default_insert = _clone_paragraph_for_insertion(
    paragraph_default_styled_template,
    "Inserted plain text",
)
paragraph_default_runs = _text_runs(paragraph_default_insert)
assert len(paragraph_default_runs) == 1
_assert_rpr_matches_user_style(paragraph_default_runs[0])
_assert_run_not_effectively_bold_or_italic(paragraph_default_runs[0])

first_insert = _clone_paragraph_for_insertion(base_template, "First inserted text")
second_insert = _clone_paragraph_for_insertion(first_insert, "Second inserted text")
bold_insert = _clone_paragraph_for_insertion(bold_template, "Inserted plain text")
repeat_bold_insert = _clone_paragraph_for_insertion(bold_insert, "Inserted plain text again")

for paragraph in (first_insert, second_insert, bold_insert, repeat_bold_insert):
    pPr = paragraph.find("w:pPr", namespaces=NS)
    assert pPr is not None, "Inserted paragraph must preserve original paragraph properties."
    spacing = pPr.find("w:spacing", namespaces=NS)
    if spacing is not None:
        assert (spacing.get(f"{{{WORD_NS}}}after") or "") == "240"
        assert (spacing.get(f"{{{WORD_NS}}}line") or "") == "360"

    runs = _text_runs(paragraph)
    assert len(runs) == 1
    _assert_rpr_matches_user_style(runs[0])
    text = "".join(runs[0].xpath("./w:t/text()", namespaces=NS))
    if paragraph in (bold_insert, repeat_bold_insert):
        assert _has_effective_bold(runs[0].find("w:rPr", namespaces=NS)), text
        assert not _has_effective_italic(runs[0].find("w:rPr", namespaces=NS)), text
    else:
        _assert_run_not_effectively_bold_or_italic(runs[0])

print("DOCX amend style preservation regression checks passed.")
