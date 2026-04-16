"""
Regression checks for delivery-gate footnote style and cross-reference handling.
"""

from lxml import etree

from legal_doc_tools.validate_delivery_gates import (
    NS,
    _resolve_cross_reference_target,
    _same_text_local_style_matches,
)


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _parse(xml: str) -> etree._Element:
    return etree.fromstring(xml)


original_para = _parse(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
  <w:r><w:rPr><w:rFonts w:asciiTheme="minorHAnsi" w:hAnsiTheme="minorHAnsi"/><w:sz w:val="24"/><w:szCs w:val="24"/><w:rStyle w:val="Strong"/></w:rPr><w:t xml:space="preserve"> Microsoft</w:t></w:r>
  <w:r><w:rPr><w:rFonts w:asciiTheme="minorHAnsi" w:hAnsiTheme="minorHAnsi"/><w:sz w:val="24"/><w:szCs w:val="24"/><w:rStyle w:val="Strong"/></w:rPr><w:t xml:space="preserve"> (n 4).</w:t></w:r>
</w:p>"""
)

amended_para = _parse(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
  <w:r><w:rPr><w:rFonts w:asciiTheme="minorHAnsi" w:hAnsiTheme="minorHAnsi"/><w:sz w:val="24"/><w:szCs w:val="24"/><w:rStyle w:val="Strong"/></w:rPr><w:t xml:space="preserve"> Microsoft</w:t></w:r>
  <w:r><w:rPr><w:rFonts w:asciiTheme="minorHAnsi" w:hAnsiTheme="minorHAnsi"/><w:sz w:val="24"/><w:szCs w:val="24"/><w:rStyle w:val="Strong"/></w:rPr><w:t xml:space="preserve"> (n 4)</w:t></w:r>
  <w:r><w:rPr><w:rFonts w:asciiTheme="minorHAnsi" w:hAnsiTheme="minorHAnsi"/><w:sz w:val="24"/><w:szCs w:val="24"/><w:rStyle w:val="Strong"/></w:rPr><w:t>.</w:t></w:r>
</w:p>"""
)

assert _same_text_local_style_matches(original_para, amended_para)


case_reference_names_by_footnote = {
    3: set(),
    4: {"microsoft", "microsoft corp", "microsoft corp v commission"},
    8: {"microsoft"},
}
footnote_search_text_by_id = {
    3: " case comp c 3 37 792 microsoft 2007 oj l32 23 ",
    4: " case t 201 04 microsoft corp v commission 2007 ecr ii 3601 ",
    8: " microsoft n 4 ",
}

assert _resolve_cross_reference_target(
    "Microsoft",
    4,
    footnote_search_text_by_id=footnote_search_text_by_id,
    case_reference_names_by_footnote=case_reference_names_by_footnote,
    current_footnote_id=8,
) == 4

print("Delivery-gate regression checks passed.")
