"""
Regression checks for DOCX footnote formatting and shorthand handling.
"""

from copy import deepcopy

from lxml import etree

from legal_doc_tools.amend_docx import (
    _lint_amended_footnote_citations,
    _replace_exact_text_in_paragraph,
    _replace_existing_footnote_text,
)
from legal_doc_tools.refine_docx_from_amended import (
    NS,
    _build_footnote_case_reference_map,
    _case_name_spans,
    _footnote_reference_runs_with_positions,
    _has_effective_italic,
    _italicize_case_name_runs_in_footnote,
    _mark_run_formatting_change,
    _normalize_downstream_footnote_citations,
    _normalize_new_footnote_citation_text,
    _normalize_body_footnote_reference_positions,
    _normalize_footnote_paragraph_style_from_template,
)


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _parse(xml: str) -> etree._Element:
    return etree.fromstring(xml)


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


footnotes_root = _parse(
    f"""<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="1">
    <w:p>
      <w:r>
        <w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr>
        <w:footnoteRef/>
      </w:r>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
          <w:sz w:val="24"/>
          <w:szCs w:val="24"/>
        </w:rPr>
        <w:t xml:space="preserve"> Google LLC and Alphabet Inc v Commission (Google Shopping) (Case C-48/22 P) EU:C:2024:726.</w:t>
      </w:r>
    </w:p>
  </w:footnote>
</w:footnotes>"""
)
before = etree.tostring(footnotes_root, encoding="unicode")
assert _replace_existing_footnote_text(
    footnotes_root,
    footnote_id=1,
    new_text="*Google LLC and Alphabet Inc v Commission* (Google Shopping) (Case C-48/22 P) EU:C:2024:726.",
) is False
after = etree.tostring(footnotes_root, encoding="unicode")
assert before == after


template_para = _parse(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:r>
    <w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr>
    <w:footnoteRef/>
  </w:r>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
    </w:rPr>
    <w:t xml:space="preserve"> Template text.</w:t>
  </w:r>
</w:p>"""
)
current_para = _parse(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:r>
    <w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr>
    <w:footnoteRef/>
  </w:r>
  <w:r><w:t xml:space="preserve"> Changed text.</w:t></w:r>
</w:p>"""
)
assert _normalize_footnote_paragraph_style_from_template(current_para, template_para) >= 1
text_run = current_para.xpath("./w:r[2]", namespaces=NS)[0]
rpr = text_run.find("w:rPr", namespaces=NS)
assert rpr is not None
assert rpr.find("./w:rFonts", namespaces=NS) is not None
assert (rpr.find("./w:rFonts", namespaces=NS).get(f"{{{WORD_NS}}}ascii") or "") == "Times New Roman"
assert (rpr.find("./w:sz", namespaces=NS).get(f"{{{WORD_NS}}}val") or "") == "24"
assert rpr.find("./w:rStyle", namespaces=NS) is None or (
    (rpr.find("./w:rStyle", namespaces=NS).get(f"{{{WORD_NS}}}val") or "") != "FootnoteReference"
)


styled_footnotes = _parse(
    f"""<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="7">
    <w:p>
      <w:r>
        <w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr>
        <w:footnoteRef/>
      </w:r>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
          <w:sz w:val="24"/>
          <w:szCs w:val="24"/>
          <w:b w:val="1"/>
          <w:bCs w:val="1"/>
        </w:rPr>
        <w:t xml:space="preserve"> Bold lead</w:t>
      </w:r>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
          <w:sz w:val="24"/>
          <w:szCs w:val="24"/>
        </w:rPr>
        <w:t xml:space="preserve"> normal tail.</w:t>
      </w:r>
    </w:p>
  </w:footnote>
</w:footnotes>"""
)
assert _replace_existing_footnote_text(
    styled_footnotes,
    footnote_id=7,
    new_text="Bold lead updated tail.",
) is True
styled_para = styled_footnotes.xpath("/w:footnotes/w:footnote[@w:id='7']/w:p", namespaces=NS)[0]
styled_runs = [
    run
    for run in styled_para.xpath("./w:r", namespaces=NS)
    if "".join(run.xpath("./w:t/text()", namespaces=NS))
]
assert styled_para.xpath("./w:r[w:footnoteRef]", namespaces=NS), "Footnote marker run must be preserved."
assert any(
    "Bold lead" in "".join(run.xpath("./w:t/text()", namespaces=NS))
    and _has_bold(run)
    and not _has_yellow_highlight(run)
    for run in styled_runs
)
assert any(
    "".join(run.xpath("./w:t/text()", namespaces=NS)) == "updated"
    and not _has_bold(run)
    and _has_yellow_highlight(run)
    for run in styled_runs
)
assert any(
    "".join(run.xpath("./w:t/text()", namespaces=NS)) == " tail."
    and not _has_yellow_highlight(run)
    for run in styled_runs
)


footnotes_for_short_form = _parse(
    f"""<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="15">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Google LLC and Alphabet Inc v Commission (Google Shopping) (Case C-48/22 P) EU:C:2024:726.</w:t></w:r>
    </w:p>
  </w:footnote>
  <w:footnote w:id="16">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Google Shopping (n 15).</w:t></w:r>
    </w:p>
  </w:footnote>
</w:footnotes>"""
)
case_map = _build_footnote_case_reference_map(footnotes_for_short_form)
footnote_16_para = footnotes_for_short_form.xpath("/w:footnotes/w:footnote[@w:id='16']/w:p", namespaces=NS)[0]
assert _italicize_case_name_runs_in_footnote(footnote_16_para, case_reference_names_by_footnote=case_map) >= 1
runs = footnote_16_para.xpath("./w:r", namespaces=NS)
seen_google_shopping_italic = False
seen_crossref_not_italic = False
for run in runs:
    text = "".join(run.xpath("./w:t/text()", namespaces=NS))
    if not text:
        continue
    is_italic = _has_effective_italic(run.find("w:rPr", namespaces=NS))
    if "Google Shopping" in text and is_italic:
        seen_google_shopping_italic = True
    if "(n 15)" in text and not is_italic:
        seen_crossref_not_italic = True
assert seen_google_shopping_italic
assert seen_crossref_not_italic


already_correct_short_form_para = _parse(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:i w:val="1"/>
      <w:iCs w:val="1"/>
    </w:rPr>
    <w:t xml:space="preserve"> Hoffmann-La Roche</w:t>
  </w:r>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
    </w:rPr>
    <w:t xml:space="preserve"> (n 5).</w:t>
  </w:r>
</w:p>"""
)
case_map_with_hoffmann = _build_footnote_case_reference_map(
    _parse(
        f"""<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="5">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Case C-413/14 P Intel Corp Inc v Commission EU:C:2017:632; Case 85/76 Hoffmann-La Roche &amp; Co AG v Commission [1979] ECR 461.</w:t></w:r>
    </w:p>
  </w:footnote>
</w:footnotes>"""
    )
)
before_runs = [
    ("".join(run.xpath("./w:t/text()", namespaces=NS)), _has_effective_italic(run.find("w:rPr", namespaces=NS)))
    for run in already_correct_short_form_para.xpath("./w:r", namespaces=NS)
    if "".join(run.xpath("./w:t/text()", namespaces=NS))
]
assert _italicize_case_name_runs_in_footnote(
    already_correct_short_form_para,
    case_reference_names_by_footnote=case_map_with_hoffmann,
) >= 0
after_runs = [
    ("".join(run.xpath("./w:t/text()", namespaces=NS)), _has_effective_italic(run.find("w:rPr", namespaces=NS)))
    for run in already_correct_short_form_para.xpath("./w:r", namespaces=NS)
    if "".join(run.xpath("./w:t/text()", namespaces=NS))
]
assert any("Hoffmann-La Roche" in text and is_italic for text, is_italic in after_runs)
assert any("(n 5)" in text and not is_italic for text, is_italic in after_runs)


intel_short_form_para = _parse(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
  <w:r><w:t xml:space="preserve"> Intel (n 5).</w:t></w:r>
</w:p>"""
)
assert _italicize_case_name_runs_in_footnote(
    intel_short_form_para,
    case_reference_names_by_footnote=case_map_with_hoffmann,
) >= 1
intel_runs = [
    ("".join(run.xpath("./w:t/text()", namespaces=NS)), _has_effective_italic(run.find("w:rPr", namespaces=NS)))
    for run in intel_short_form_para.xpath("./w:r", namespaces=NS)
    if "".join(run.xpath("./w:t/text()", namespaces=NS))
]
assert any("Intel" in text and is_italic for text, is_italic in intel_runs)
assert any("(n 5)" in text and not is_italic for text, is_italic in intel_runs)


forward_crossref_footnotes = _parse(
    f"""<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="10">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Brownlie (n 25), [27]-[29].</w:t></w:r>
    </w:p>
  </w:footnote>
  <w:footnote w:id="25">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> FS Cairo (Nile Plaza) LLC v Brownlie [2021] UKSC 45, [2022] AC 995.</w:t></w:r>
    </w:p>
  </w:footnote>
</w:footnotes>"""
)
try:
    _lint_amended_footnote_citations(
        forward_crossref_footnotes,
        corrected_ids={10},
        added_ids=set(),
    )
    raise AssertionError("Expected forward/self footnote cross-reference lint failure.")
except ValueError as exc:
    assert "forward/self cross-reference" in str(exc)


case_map_with_meo = _build_footnote_case_reference_map(
    _parse(
        f"""<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="34">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Case C-525/16 MEO — Serviços de Comunicações e Multimédia SA v Autoridade da Concorrência [2018] EU:C:2018:270.</w:t></w:r>
    </w:p>
  </w:footnote>
</w:footnotes>"""
    )
)
assert "meo" in case_map_with_meo[34]

meo_short_form_para = _parse(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
  <w:r><w:t xml:space="preserve"> MEO (n 34).</w:t></w:r>
</w:p>"""
)
assert _italicize_case_name_runs_in_footnote(
    meo_short_form_para,
    case_reference_names_by_footnote=case_map_with_meo,
) >= 1
meo_runs = [
    ("".join(run.xpath("./w:t/text()", namespaces=NS)), _has_effective_italic(run.find("w:rPr", namespaces=NS)))
    for run in meo_short_form_para.xpath("./w:r", namespaces=NS)
    if "".join(run.xpath("./w:t/text()", namespaces=NS))
]
assert any("MEO" in text and is_italic for text, is_italic in meo_runs)
assert any("(n 34)" in text and not is_italic for text, is_italic in meo_runs)


meta_case_footnotes = _parse(
    f"""<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="17">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Case C-252/21 Meta Platforms Inc and Others v Bundeskartellamt EU:C:2023:537.</w:t></w:r>
    </w:p>
  </w:footnote>
</w:footnotes>"""
)
meta_case_map = _build_footnote_case_reference_map(meta_case_footnotes)
assert "meta platforms" in meta_case_map[17]


case_number_first_text = " Case C-48/22 P Google LLC and Alphabet Inc v Commission (Google Shopping) EU:C:2024:726."
spans = _case_name_spans(case_number_first_text)
assert spans
assert [case_number_first_text[start:end] for start, end in spans] == [
    "Google LLC and Alphabet Inc v Commission"
]


italic_case_number_para = _parse(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:i w:val="1"/>
      <w:iCs w:val="1"/>
    </w:rPr>
    <w:t xml:space="preserve"> Case C-48/22 P Google LLC and Alphabet Inc v Commission (Google Shopping) EU:C:2024:726.</w:t>
  </w:r>
</w:p>"""
)
# Existing user italics are preserved in additive-only mode, even if OSCOLA
# would ordinarily keep the case-number metadata in roman text.
assert _italicize_case_name_runs_in_footnote(italic_case_number_para) >= 0
case_run_status = [
    ("".join(run.xpath("./w:t/text()", namespaces=NS)), _has_effective_italic(run.find("w:rPr", namespaces=NS)))
    for run in italic_case_number_para.xpath("./w:r", namespaces=NS)
    if "".join(run.xpath("./w:t/text()", namespaces=NS))
]
assert (
    " Case C-48/22 P Google LLC and Alphabet Inc v Commission (Google Shopping) EU:C:2024:726.",
    True,
) in case_run_status


emphasis_case_number_para = _parse(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
  <w:r>
    <w:rPr>
      <w:rStyle w:val="Emphasis"/>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
    </w:rPr>
    <w:t xml:space="preserve"> Case C-95/04 P British Airways plc v Commission of the European Communities [2007] ECR I-02331.</w:t>
  </w:r>
</w:p>"""
)
# Word's Emphasis style is treated as effective italics, so additive-only
# normalization preserves the user's existing formatting here as well.
assert _italicize_case_name_runs_in_footnote(emphasis_case_number_para) >= 0
emphasis_case_runs = [
    ("".join(run.xpath("./w:t/text()", namespaces=NS)), _has_effective_italic(run.find("w:rPr", namespaces=NS)))
    for run in emphasis_case_number_para.xpath("./w:r", namespaces=NS)
    if "".join(run.xpath("./w:t/text()", namespaces=NS))
]
assert (
    " Case C-95/04 P British Airways plc v Commission of the European Communities [2007] ECR I-02331.",
    True,
) in emphasis_case_runs


ibid_para = _parse(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:i w:val="1"/>
      <w:iCs w:val="1"/>
    </w:rPr>
    <w:t xml:space="preserve"> ibid.</w:t>
    </w:r>
</w:p>"""
)
# Existing italic `ibid` is preserved in additive-only mode.
assert _italicize_case_name_runs_in_footnote(ibid_para) >= 0
ibid_run = ibid_para.xpath("./w:r[2]", namespaces=NS)[0]
assert _has_effective_italic(ibid_run.find("w:rPr", namespaces=NS))


body_reference_footnotes = _parse(
    f"""<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="41">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Schibsby v Westenholz (1870) LR 6 QB 155.</w:t></w:r>
    </w:p>
  </w:footnote>
  <w:footnote w:id="42">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Emanuel v Symon [1908] 1 KB 302.</w:t></w:r>
    </w:p>
  </w:footnote>
</w:footnotes>"""
)
body_document = _parse(
    f"""<w:document xmlns:w="{WORD_NS}">
  <w:body>
    <w:p>
      <w:r><w:t>Sc</w:t></w:r>
      <w:r><w:footnoteReference w:id="41"/></w:r>
      <w:r><w:t>hibsby</w:t></w:r>
      <w:r><w:footnoteReference w:id="41"/></w:r>
      <w:r><w:t xml:space="preserve"> and E</w:t></w:r>
      <w:r><w:footnoteReference w:id="42"/></w:r>
      <w:r><w:t>manuel</w:t></w:r>
      <w:r><w:t xml:space="preserve"> remain central.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>"""
)
assert _normalize_body_footnote_reference_positions(body_document, body_reference_footnotes) >= 1
body_paragraph = body_document.xpath("/w:document/w:body/w:p", namespaces=NS)[0]
normalized_refs = [
    (pos, ref_id) for _run, pos, ref_id in _footnote_reference_runs_with_positions(body_paragraph)
]
assert normalized_refs == [(8, "41"), (20, "42")]
child_signature = []
for child in body_paragraph.xpath("./w:r", namespaces=NS):
    ref = child.find("w:footnoteReference", namespaces=NS)
    if ref is not None:
        child_signature.append(f"[fn:{ref.get(f'{{{WORD_NS}}}id')}]")
        continue
    child_signature.append("".join(child.xpath("./w:t/text()", namespaces=NS)))
assert child_signature == [
    "Sc",
    "hibsby",
    "[fn:41]",
    " and E",
    "manuel",
    "[fn:42]",
    " remain central.",
]


meta_body_document = _parse(
    f"""<w:document xmlns:w="{WORD_NS}">
  <w:body>
    <w:p>
      <w:r><w:t xml:space="preserve">Meta</w:t></w:r>
      <w:r><w:footnoteReference w:id="17"/></w:r>
      <w:r><w:t xml:space="preserve"> Platforms is an important referenced case.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>"""
)
assert _normalize_body_footnote_reference_positions(meta_body_document, meta_case_footnotes) >= 1
meta_paragraph = meta_body_document.xpath("/w:document/w:body/w:p", namespaces=NS)[0]
meta_signature = []
for child in meta_paragraph.xpath("./w:r", namespaces=NS):
    ref = child.find("w:footnoteReference", namespaces=NS)
    if ref is not None:
        meta_signature.append(f"[fn:{ref.get(f'{{{WORD_NS}}}id')}]")
        continue
    meta_signature.append("".join(child.xpath("./w:t/text()", namespaces=NS)))
assert meta_signature == [
    "Meta",
    " Platforms",
    "[fn:17]",
    " is an important referenced case.",
]
meta_refs = [
    (pos, ref_id) for _run, pos, ref_id in _footnote_reference_runs_with_positions(meta_paragraph)
]
assert meta_refs == [(14, "17")]


ibid_short_form_root = _parse(
    f"""<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="17">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Case C-252/21 Meta Platforms Inc and Others v Bundeskartellamt EU:C:2023:537.</w:t></w:r>
    </w:p>
  </w:footnote>
  <w:footnote w:id="18">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Competition Act 1998, s 18.</w:t></w:r>
    </w:p>
  </w:footnote>
</w:footnotes>"""
)
assert (
    _normalize_new_footnote_citation_text(
        "Case C-252/21 Meta Platforms Inc and Others v Bundeskartellamt EU:C:2023:537.",
        footnotes_root=ibid_short_form_root,
        current_footnote_id=19,
    )
    == "Meta Platforms (n 17)."
)

ibid_immediate_root = deepcopy(ibid_short_form_root)
ibid_immediate_root.append(
    _parse(
        f"""<w:footnote xmlns:w="{WORD_NS}" w:id="19">
  <w:p>
    <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
    <w:r><w:t xml:space="preserve"> Meta Platforms (n 17).</w:t></w:r>
  </w:p>
</w:footnote>"""
    )
)
assert (
    _normalize_new_footnote_citation_text(
        "Case C-252/21 Meta Platforms Inc and Others v Bundeskartellamt EU:C:2023:537.",
        footnotes_root=ibid_immediate_root,
        current_footnote_id=20,
    )
    == "ibid."
)


downstream_normalization_root = _parse(
    f"""<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="17">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Case C-252/21 Meta Platforms Inc and Others v Bundeskartellamt EU:C:2023:537.</w:t></w:r>
    </w:p>
  </w:footnote>
  <w:footnote w:id="18">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Competition Act 1998, s 18.</w:t></w:r>
    </w:p>
  </w:footnote>
  <w:footnote w:id="19">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Case C-252/21 Meta Platforms Inc and Others v Bundeskartellamt EU:C:2023:537.</w:t></w:r>
    </w:p>
  </w:footnote>
  <w:footnote w:id="20">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Case C-252/21 Meta Platforms Inc and Others v Bundeskartellamt EU:C:2023:537.</w:t></w:r>
    </w:p>
  </w:footnote>
</w:footnotes>"""
)
downstream_changed_ids = _normalize_downstream_footnote_citations(
    downstream_normalization_root,
    start_footnote_id=17,
)
assert downstream_changed_ids == {19, 20}
downstream_texts = {
    int(node.get(f"{{{WORD_NS}}}id")): "".join(node.xpath(".//w:t/text()", namespaces=NS)).strip()
    for node in downstream_normalization_root.xpath("/w:footnotes/w:footnote", namespaces=NS)
}
assert downstream_texts[17] == "Case C-252/21 Meta Platforms Inc and Others v Bundeskartellamt EU:C:2023:537."
assert downstream_texts[19] == "Meta Platforms (n 17)."
assert downstream_texts[20] == "ibid."


downstream_crossref_root = _parse(
    f"""<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="35">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Case C-525/16 MEO — Serviços de Comunicações e Multimédia SA v Autoridade da Concorrência [2018] EU:C:2018:270.</w:t></w:r>
    </w:p>
  </w:footnote>
  <w:footnote w:id="36">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> Case C-95/04 P British Airways plc v Commission of the European Communities [2007] ECR I-02331.</w:t></w:r>
    </w:p>
  </w:footnote>
  <w:footnote w:id="38">
    <w:p>
      <w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>
      <w:r><w:t xml:space="preserve"> MEO (n 34); British Airways (n 35).</w:t></w:r>
    </w:p>
  </w:footnote>
</w:footnotes>"""
)
downstream_crossref_changed = _normalize_downstream_footnote_citations(
    downstream_crossref_root,
    start_footnote_id=35,
)
assert downstream_crossref_changed == {38}
downstream_crossref_text = "".join(
    downstream_crossref_root.xpath("/w:footnotes/w:footnote[@w:id='38']//w:t/text()", namespaces=NS)
).strip()
assert downstream_crossref_text == "MEO (n 35); British Airways (n 36)."


body_marker_run = _parse(
    f"""<w:r xmlns:w="{WORD_NS}">
  <w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr>
  <w:footnoteReference w:id="9"/>
</w:r>"""
)
assert _mark_run_formatting_change(body_marker_run) == 0
body_marker_rpr = body_marker_run.find("w:rPr", namespaces=NS)
assert body_marker_rpr is not None
assert body_marker_rpr.find("w:highlight", namespaces=NS) is None


body_short_form_para = _parse(
    f"""<w:p xmlns:w="{WORD_NS}">
  <w:r><w:t xml:space="preserve">This separation between the gateway and the proper place matters because it ensures </w:t></w:r>
  <w:r><w:t>that PD 6B does not operate mechanically: the territorial connection opens the door, but </w:t></w:r>
  <w:r>
    <w:rPr>
      <w:i w:val="1"/>
      <w:iCs w:val="1"/>
    </w:rPr>
    <w:t>Spiliada</w:t>
  </w:r>
  <w:r><w:t xml:space="preserve"> decides whether the English court should retain jurisdiction.</w:t></w:r>
</w:p>"""
)
assert _replace_exact_text_in_paragraph(
    body_short_form_para,
    old="that PD 6B does not operate mechanically",
    new="that PD 6B does not operate automatically",
) is True
spiliada_runs = [
    run
    for run in body_short_form_para.xpath("./w:r", namespaces=NS)
    if "Spiliada" in "".join(run.xpath("./w:t/text()", namespaces=NS))
]
assert spiliada_runs
assert any(_has_effective_italic(run.find("w:rPr", namespaces=NS)) for run in spiliada_runs)

print("DOCX footnote regression checks passed.")
