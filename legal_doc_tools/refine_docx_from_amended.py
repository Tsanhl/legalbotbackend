#!/usr/bin/env python3
"""
Refine a DOCX by copying *textual* amendments from an "amended" DOCX into the
original DOCX while preserving the original's formatting, footnotes, fonts,
sizes, spacing, and layout.

All inserted/replaced wording is marked with **yellow highlight**.

This script intentionally does NOT use python-docx to write the output because
python-docx does not preserve certain Word features (notably footnotes) and can
normalize styles.
"""

from __future__ import annotations

import argparse
import difflib
import re
import shutil
import sys
import tempfile
import zipfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"w": W_NS}
DESKTOP_ROOT = (Path.home() / "Desktop").resolve()
FINAL_OUTPUT_SUFFIX = "_amended_marked_final.docx"
FINAL_OUTPUT_STEM_SUFFIX = FINAL_OUTPUT_SUFFIX.removesuffix(".docx")


def w_tag(local: str) -> str:
    return f"{{{W_NS}}}{local}"


def _t(text: str) -> etree._Element:
    el = etree.Element(w_tag("t"))
    if text.startswith((" ", "\t", "\n")) or text.endswith((" ", "\t", "\n")):
        el.set(f"{{{XML_NS}}}space", "preserve")
    el.text = text
    return el


TOKEN_RE = re.compile(r"\s+|[^\s]+", re.UNICODE)
BODY_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’&./-]*", re.UNICODE)
BIBLIOGRAPHY_HEADINGS = {"bibliography", "references", "reference list", "works cited"}
TABLE_OF_CASES_HEADINGS = {"table of cases", "table of authorities"}
BIBLIOGRAPHY_SECTION_HEADINGS = {
    "table of cases",
    "table of authorities",
    "table of legislation",
    "journal articles",
    "books",
    "other sources",
    "online sources",
    "official and regulatory materials",
    "primary sources",
    "secondary sources",
    "european commission decisions",
    "legislation",
    "cases",
    "treaties",
}
NON_BIBLIOGRAPHY_SECTION_HEADINGS = {
    "table of legislation",
    "list of abbreviations",
}
MAX_BODY_CASE_NAME_TOKENS = 6
GENERIC_BODY_REFERENCE_ANCHORS = {
    "analysis",
    "approach",
    "argument",
    "authority",
    "benefit",
    "benefits",
    "case",
    "cases",
    "claim",
    "claims",
    "context",
    "coordination",
    "court",
    "courts",
    "defence",
    "dispute",
    "disputes",
    "effect",
    "effects",
    "enforcement",
    "feature",
    "features",
    "forum",
    "framework",
    "judgment",
    "judgments",
    "law",
    "laws",
    "point",
    "points",
    "position",
    "positions",
    "practical",
    "principle",
    "principles",
    "problem",
    "problems",
    "proposition",
    "propositions",
    "remedy",
    "remedies",
    "rule",
    "rules",
    "scope",
    "sentence",
    "sentences",
    "system",
    "systems",
    "theory",
    "use",
    "value",
    "values",
    "view",
    "winning",
}
AMBIGUOUS_SINGLE_WORD_CASE_REFERENCES = {
    "bank",
    "court",
    "group",
    "state",
    "trust",
}
BODY_CASE_NAME_HEADWORD_BLACKLIST = AMBIGUOUS_SINGLE_WORD_CASE_REFERENCES.union(
    {
        "company",
        "commission",
        "council",
        "department",
        "director",
        "general",
        "government",
        "holdings",
        "industries",
        "international",
        "kingdom",
        "maritime",
        "ministry",
        "republic",
        "services",
        "union",
    }
)
LOW_VALUE_BODY_REFERENCE_ANCHORS = {
    "and",
    "as",
    "at",
    "because",
    "before",
    "but",
    "if",
    "in",
    "inside",
    "into",
    "it",
    "its",
    "of",
    "on",
    "or",
    "outside",
    "that",
    "the",
    "their",
    "this",
    "to",
    "under",
    "when",
    "where",
    "which",
    "while",
    "within",
}
AMBIGUOUS_CASE_SHORT_FORM_POSITIVE_CUES = {
    "applied",
    "applies",
    "authority",
    "case",
    "cases",
    "confirmed",
    "confirms",
    "court",
    "courts",
    "decision",
    "decisions",
    "distinguished",
    "distinguishes",
    "followed",
    "follows",
    "held",
    "holding",
    "holdings",
    "judgment",
    "judgments",
    "precedent",
    "precedents",
    "reaffirmed",
    "reaffirms",
    "remains",
    "ruling",
    "rulings",
}
AMBIGUOUS_CASE_SHORT_FORM_NEGATIVE_CUES = {
    "ai",
    "algorithm",
    "algorithms",
    "announced",
    "announces",
    "business",
    "businesses",
    "company",
    "companies",
    "developer",
    "developers",
    "firm",
    "firms",
    "model",
    "models",
    "platform",
    "platforms",
    "product",
    "products",
    "service",
    "services",
    "startup",
    "startups",
    "technology",
    "technologies",
    "tool",
    "tools",
}
AMBIGUOUS_CASE_SHORT_FORM_NEGATIVE_PRECEDING_CUES = {
    "against",
    "for",
    "from",
    "into",
    "of",
    "toward",
    "towards",
}
CASE_SEQUEL_SUFFIX_RE = re.compile(r"(\s+(?:I|II|III|IV|V|VI|VII|VIII|IX|X))\b")
YEAR_RE = re.compile(r"\b(?:1[89]\d{2}|20\d{2}|21\d{2})\b")
FULL_DATE_RE = re.compile(
    r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
    re.IGNORECASE,
)
LATIN_FUNCTION_WORDS = {
    "a",
    "ab",
    "ad",
    "contra",
    "cum",
    "de",
    "et",
    "ex",
    "in",
    "inter",
    "non",
    "per",
    "pro",
    "re",
    "sub",
}
LATIN_PHRASE_LEADING_FUNCTION_WORDS = {
    "de",
    "ex",
    "in",
    "inter",
    "per",
    "pro",
    "re",
    "sine",
    "sub",
}
LATIN_WORD_LEXICON = LATIN_FUNCTION_WORDS.union(
    {
        "audi",
        "aequo",
        "alia",
        "alteram",
        "ante",
        "bona",
        "bono",
        "casus",
        "causa",
        "causae",
        "caveat",
        "certiorari",
        "cogens",
        "conveniens",
        "curiam",
        "damni",
        "decidendi",
        "decisis",
        "delicti",
        "dicta",
        "dire",
        "emptor",
        "facie",
        "facto",
        "fide",
        "fori",
        "forum",
        "generis",
        "jure",
        "jus",
        "lex",
        "lis",
        "loci",
        "loquitur",
        "major",
        "mens",
        "minimis",
        "mutandis",
        "mutatis",
        "nisi",
        "novo",
        "nullius",
        "obiter",
        "omissus",
        "pari",
        "partem",
        "partes",
        "passu",
        "pendens",
        "personam",
        "post",
        "prima",
        "prius",
        "prorogatum",
        "qua",
        "rata",
        "ratio",
        "rea",
        "rebus",
        "rem",
        "res",
        "se",
        "sic",
        "stantibus",
        "stare",
        "sui",
        "terra",
        "turpi",
        "ultra",
        "vires",
        "vis",
        "voir",
    }
)
LATIN_CONTENT_WORDS = LATIN_WORD_LEXICON.difference(LATIN_FUNCTION_WORDS).union(
    {
        "facto",
        "jure",
    }
)
# OSCOLA: common legal-Latin terms absorbed into English — do NOT italicise.
LATIN_NATURALIZED_PHRASES = {
    "obiter dicta",
    "obiter dictum",
    "ratio decidendi",
    "stare decisis",
    "ultra vires",
    "intra vires",
}
PROCEDURAL_DESCRIPTOR_WORDS = {
    "application",
    "brief",
    "claim",
    "complaint",
    "consent",
    "decision",
    "decree",
    "defence",
    "draft",
    "file",
    "filing",
    "injunction",
    "judgment",
    "motion",
    "no",
    "notice",
    "opinion",
    "order",
    "petition",
    "reply",
    "settlement",
    "statement",
}


def _tokenize(s: str) -> List[str]:
    if not s:
        return []
    return TOKEN_RE.findall(s)


def _paragraph_has_non_whitespace_text(paragraph: etree._Element) -> bool:
    return bool((_paragraph_text_all_runs(paragraph) or "").strip())


def _align_amended_paragraphs_to_original_blank_structure(
    orig_paras: List[etree._Element],
    amend_paras: List[etree._Element],
) -> Optional[List[Optional[etree._Element]]]:
    if len(orig_paras) == len(amend_paras):
        return list(amend_paras)

    amend_nonblank = [paragraph for paragraph in amend_paras if _paragraph_has_non_whitespace_text(paragraph)]
    if sum(1 for paragraph in orig_paras if _paragraph_has_non_whitespace_text(paragraph)) != len(amend_nonblank):
        return None

    aligned: List[Optional[etree._Element]] = []
    amend_idx = 0
    for paragraph in orig_paras:
        if _paragraph_has_non_whitespace_text(paragraph):
            aligned.append(amend_nonblank[amend_idx])
            amend_idx += 1
        else:
            aligned.append(None)
    return aligned


def _align_amended_text_to_original_blank_structure(
    orig_paras: List[etree._Element],
    amended_paras: List[str],
) -> Optional[List[str]]:
    if len(orig_paras) == len(amended_paras):
        return list(amended_paras)

    amended_nonblank = [paragraph for paragraph in amended_paras if paragraph.strip()]
    if sum(1 for paragraph in orig_paras if _paragraph_has_non_whitespace_text(paragraph)) != len(amended_nonblank):
        return None

    aligned: List[str] = []
    amended_idx = 0
    for paragraph in orig_paras:
        if _paragraph_has_non_whitespace_text(paragraph):
            aligned.append(amended_nonblank[amended_idx])
            amended_idx += 1
        else:
            aligned.append("")
    return aligned


def _require_markup_enabled(markup: bool) -> None:
    if not markup:
        raise ValueError(
            "Amendment markup hard rule: changed wording must always use yellow highlight. "
            "Unmarked amend output is not permitted."
        )


def _expected_final_output_path(original_path: Path) -> Path:
    root_stem = _root_stem_for_source(original_path)
    return DESKTOP_ROOT / f"{root_stem}{FINAL_OUTPUT_SUFFIX}"


def _root_stem_for_source(path: Path) -> str:
    stem = path.stem
    while stem.endswith(FINAL_OUTPUT_STEM_SUFFIX):
        stem = stem[: -len(FINAL_OUTPUT_STEM_SUFFIX)]
    return stem


def _system_output_name_pattern(root_stem: str) -> re.Pattern[str]:
    return re.compile(
        rf"^{re.escape(root_stem)}(?:{re.escape(FINAL_OUTPUT_STEM_SUFFIX)})+(?:_v\d+)?\.docx$",
        flags=re.IGNORECASE,
    )


def _iter_system_outputs_for_root(root_stem: str) -> Iterable[Path]:
    pattern = _system_output_name_pattern(root_stem)
    for candidate in DESKTOP_ROOT.iterdir():
        if candidate.is_file() and pattern.match(candidate.name):
            yield candidate.resolve()


def _latest_system_output_for_source(path: Path) -> Optional[Path]:
    root_stem = _root_stem_for_source(path)
    candidates = sorted(
        _iter_system_outputs_for_root(root_stem),
        key=lambda item: (item.stat().st_mtime_ns, item.name),
    )
    return candidates[-1] if candidates else None


def _resolve_latest_amendable_source(path: Path) -> tuple[Path, bool]:
    latest = _latest_system_output_for_source(path)
    if latest is None:
        return path.expanduser().resolve(), False
    resolved = path.expanduser().resolve()
    return latest, latest != resolved


def _system_output_version(path: Path, root_stem: str) -> int:
    resolved = path.expanduser().resolve()
    canonical = DESKTOP_ROOT / f"{root_stem}{FINAL_OUTPUT_SUFFIX}"
    if resolved == canonical:
        return 1
    m = re.search(r"_v(\d+)\.docx$", resolved.name, flags=re.IGNORECASE)
    if m:
        return max(1, int(m.group(1)))
    return 1


def _next_versioned_output_path(original_path: Path) -> Path:
    root_stem = _root_stem_for_source(original_path)
    canonical = _expected_final_output_path(original_path)
    candidates = list(_iter_system_outputs_for_root(root_stem))
    if not candidates and not canonical.exists():
        return canonical

    highest = 1
    for candidate in candidates:
        highest = max(highest, _system_output_version(candidate, root_stem))
    if canonical.exists():
        highest = max(highest, 1)
    return DESKTOP_ROOT / f"{root_stem}{FINAL_OUTPUT_STEM_SUFFIX}_v{highest + 1}.docx"


def _normalize_to_final_output_path(original_path: Path, requested_path: Optional[Path]) -> tuple[Path, bool]:
    expected = _next_versioned_output_path(original_path)
    if requested_path is None:
        return expected, False
    requested = requested_path.expanduser().resolve()
    return expected, requested != expected


def _require_desktop_root_output(path: Path) -> None:
    resolved = path.expanduser().resolve()
    desktop_root = DESKTOP_ROOT.expanduser().resolve()
    if resolved.parent != desktop_root:
        raise ValueError(f"Output must be saved directly in Desktop root ({desktop_root}).")


def _copy_source_to_temp_if_same_as_output(source_path: Path, output_path: Path) -> tuple[Path, Optional[Path]]:
    if source_path != output_path:
        return source_path, None
    temp_dir = Path(tempfile.mkdtemp(prefix="legal_doc_latest_source_"))
    temp_source = temp_dir / source_path.name
    shutil.copy2(source_path, temp_source)
    return temp_source.resolve(), temp_dir




def _prune_output_versions(path: Path) -> int:
    # Non-destructive output policy: preserve prior amended Desktop outputs.
    # This helper is retained for backwards compatibility but no longer removes
    # any files.
    return 0

def _set_yellow_highlight_markup(rPr: etree._Element) -> None:
    highlight = rPr.find("w:highlight", namespaces=NS)
    if highlight is None:
        highlight = etree.Element(w_tag("highlight"))
        rPr.append(highlight)
    highlight.set(w_tag("val"), "yellow")


def _has_yellow_highlight(rPr: Optional[etree._Element]) -> bool:
    if rPr is None:
        return False
    highlight = rPr.find("w:highlight", namespaces=NS)
    if highlight is None:
        return False
    return (highlight.get(w_tag("val")) or "").strip().lower() == "yellow"


def _mark_run_formatting_change(run: etree._Element) -> int:
    if (
        run.find("w:footnoteReference", namespaces=NS) is not None
        or run.find("w:footnoteRef", namespaces=NS) is not None
    ):
        return 0
    rPr = run.find("w:rPr", namespaces=NS)
    if rPr is None:
        rPr = etree.Element(w_tag("rPr"))
        run.insert(0, rPr)
    before = etree.tostring(rPr, encoding="unicode")
    _set_yellow_highlight_markup(rPr)
    after = etree.tostring(rPr, encoding="unicode")
    return 1 if before != after else 0


VISIBLE_FORMATTING_TAGS = ("i", "iCs", "u", "uCs", "strike", "dstrike", "caps", "smallCaps")


def _visible_formatting_signature(rPr: Optional[etree._Element]) -> tuple[tuple[str, str], ...]:
    if rPr is None:
        return ()
    signature: list[tuple[str, str]] = []
    for tag in VISIBLE_FORMATTING_TAGS:
        node = rPr.find(f"w:{tag}", namespaces=NS)
        if node is None:
            continue
        signature.append((tag, (node.get(w_tag("val")) or "1").strip().lower()))
    return tuple(signature)


def _run_rPr(run: etree._Element) -> Optional[etree._Element]:
    return run.find("w:rPr", namespaces=NS)


def _clone_run_with_rPr(src_run: Optional[etree._Element]) -> etree._Element:
    r = etree.Element(w_tag("r"))
    if src_run is not None:
        for k, v in src_run.attrib.items():
            r.set(k, v)
        rPr = _run_rPr(src_run)
        if rPr is not None:
            r.append(deepcopy(rPr))
    return r


def _clone_run_for_changed_text(context_run: Optional[etree._Element], *, markup: bool) -> etree._Element:
    r = _clone_run_with_rPr(context_run)
    if not markup:
        return r
    rPr = r.find("w:rPr", namespaces=NS)
    if rPr is None:
        rPr = etree.Element(w_tag("rPr"))
        r.insert(0, rPr)
    # Prevent accidental italic carry-over for normal amended wording.
    for tag in ("i", "iCs"):
        for node in rPr.findall(f"w:{tag}", namespaces=NS):
            rPr.remove(node)
    _set_yellow_highlight_markup(rPr)
    return r


def _replace_run_rpr(run: etree._Element, new_rPr: Optional[etree._Element]) -> bool:
    existing = run.find("w:rPr", namespaces=NS)
    if existing is not None:
        run.remove(existing)
    if new_rPr is not None:
        run.insert(0, deepcopy(new_rPr))
    return True


def _canonical_body_footnote_reference_rpr() -> etree._Element:
    rPr = etree.Element(w_tag("rPr"))
    etree.SubElement(rPr, w_tag("rStyle")).set(w_tag("val"), "FootnoteReference")
    etree.SubElement(rPr, w_tag("vertAlign")).set(w_tag("val"), "superscript")
    etree.SubElement(rPr, w_tag("noProof"))
    return rPr


def _run_contains_textual_content(run: etree._Element) -> bool:
    return any(
        child.tag in (w_tag("t"), w_tag("tab"), w_tag("br"), w_tag("noBreakHyphen"), w_tag("softHyphen"))
        for child in run
    )


def _paragraph_text_all_runs(p: etree._Element) -> str:
    # Include text from nested runs (e.g., inside hyperlinks) in document order.
    parts: List[str] = []
    for r in p.xpath(".//w:r", namespaces=NS):
        for child in r:
            if child.tag == w_tag("t"):
                parts.append(child.text or "")
            elif child.tag == w_tag("tab"):
                parts.append("\t")
            elif child.tag == w_tag("br"):
                parts.append("\n")
            elif child.tag == w_tag("noBreakHyphen"):
                parts.append("\u2011")
            elif child.tag == w_tag("softHyphen"):
                parts.append("\u00ad")
    return "".join(parts)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _paragraph_is_simple(p: etree._Element) -> bool:
    # We only rewrite paragraphs that are "run-only" with pPr first.
    children = list(p)
    pPr = p.find("w:pPr", namespaces=NS)
    if pPr is not None and children and children[0] is not pPr:
        # Avoid reordering odd/rare paragraphs where pPr isn't first.
        return False
    # Skip hyperlinks/fields; rewriting them safely needs more logic.
    if p.xpath(".//w:hyperlink|.//w:fldChar|.//w:instrText", namespaces=NS):
        return False
    return True


def _first_textual_run_in_paragraph(p: etree._Element) -> Optional[etree._Element]:
    runs = p.xpath(".//w:r[w:t]", namespaces=NS)
    if runs:
        return runs[0]
    runs = p.xpath(".//w:r", namespaces=NS)
    return runs[0] if runs else None


def _paragraph_contains_effective_italics(p: etree._Element) -> bool:
    for run in p.xpath(".//w:r", namespaces=NS):
        if _has_effective_italic(run.find("w:rPr", namespaces=NS)):
            return True
    return False


def _looks_like_table_of_cases_entry(text: str) -> bool:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if not collapsed:
        return False
    if re.search(r"\b(?:Case|Joined Cases?)\s+[CTF]?[–-]?\d", collapsed):
        return True
    if re.search(r"\([CTF]?[–-]?\d+/\d+\)\s+\[[12]\d{3}\]\s", collapsed):
        return True
    if re.search(r"\[[12]\d{3}\]\s+(?:ECR|CMLR|AC|QB|Ch|Fam|WLR|All ER|OJ)\b", collapsed):
        return True
    return False


def _apply_full_replace_to_paragraph(
    p: etree._Element,
    new_text: str,
    *,
    markup: bool,
    preserve_projected_inline_italics: bool = False,
) -> bool:
    old_text = _paragraph_text_all_runs(p)
    if old_text == new_text:
        return False
    atoms: List[Atom] = []
    atom_text = ""
    old_italic_rpr_spans: List[Tuple[int, int, etree._Element]] = []
    if preserve_projected_inline_italics:
        atoms, atom_text = _paragraph_atoms(p)
        old_italic_rpr_spans = _existing_italic_rpr_spans_from_atoms(atoms)
    context_run = _first_textual_run_in_paragraph(p)
    new_children = _emit_changed_text(new_text, context_run, markup=markup)
    _rewrite_paragraph_in_place(p, new_children)
    if preserve_projected_inline_italics and old_italic_rpr_spans:
        _restore_projected_inline_italic_styles(
            p,
            old_text=atom_text,
            new_text=new_text,
            old_italic_rpr_spans=old_italic_rpr_spans,
        )
    _clear_orphaned_non_alnum_italic_runs(p)
    return True


@dataclass(frozen=True)
class Atom:
    kind: str  # text|tab|br|fn|endnote|run_special|p_special
    start: int
    end: int
    run: Optional[etree._Element]
    elem: etree._Element
    text: str = ""


def _existing_italic_rpr_spans_from_atoms(
    atoms: List[Atom],
) -> List[Tuple[int, int, etree._Element]]:
    spans: List[Tuple[int, int, etree._Element]] = []
    for atom in atoms:
        if atom.run is None or atom.start >= atom.end or atom.kind not in {"text", "tab", "br"}:
            continue
        rPr = atom.run.find("w:rPr", namespaces=NS)
        if rPr is None or not _has_effective_italic(rPr):
            continue
        spans.append((atom.start, atom.end, deepcopy(rPr)))
    return spans


def _restore_projected_inline_italic_styles(
    p: etree._Element,
    *,
    old_text: str,
    new_text: str,
    old_italic_rpr_spans: List[Tuple[int, int, etree._Element]],
) -> int:
    if not old_text or not new_text or not old_italic_rpr_spans:
        return 0
    projected_rpr_spans = _project_preserved_rpr_spans(
        old_text,
        new_text,
        old_italic_rpr_spans,
        preserve_changed_text=False,
    )
    if not projected_rpr_spans:
        return 0
    return _apply_rpr_spans_to_runs(p, projected_rpr_spans)


def _clear_orphaned_non_alnum_italic_runs(p: etree._Element) -> int:
    changed = 0
    run_segments = _paragraph_text_run_segments(p)
    for idx, (run, _start, _end, text) in enumerate(run_segments):
        rPr = run.find("w:rPr", namespaces=NS)
        if rPr is None or not _has_effective_italic(rPr):
            continue
        if re.search(r"[A-Za-z0-9]", text):
            continue

        prev_has_alnum_italic = False
        if idx > 0:
            prev_run, _s, _e, prev_text = run_segments[idx - 1]
            prev_has_alnum_italic = bool(
                re.search(r"[A-Za-z0-9]", prev_text)
                and _has_effective_italic(prev_run.find("w:rPr", namespaces=NS))
            )

        next_has_alnum_italic = False
        if idx + 1 < len(run_segments):
            next_run, _s, _e, next_text = run_segments[idx + 1]
            next_has_alnum_italic = bool(
                re.search(r"[A-Za-z0-9]", next_text)
                and _has_effective_italic(next_run.find("w:rPr", namespaces=NS))
            )

        if prev_has_alnum_italic or next_has_alnum_italic:
            continue

        cleared = _clear_italic(rPr)
        changed += cleared
        if cleared:
            changed += _mark_run_formatting_change(run)
    return changed


def _paragraph_atoms(p: etree._Element) -> Tuple[List[Atom], str]:
    atoms: List[Atom] = []
    pos = 0
    for child in p:
        if child.tag == w_tag("pPr"):
            continue
        if child.tag != w_tag("r"):
            atoms.append(Atom("p_special", pos, pos, None, child))
            continue

        run = child
        for rc in run:
            if rc.tag == w_tag("rPr"):
                continue
            if rc.tag == w_tag("t"):
                txt = rc.text or ""
                if txt:
                    atoms.append(Atom("text", pos, pos + len(txt), run, rc, txt))
                    pos += len(txt)
                else:
                    atoms.append(Atom("text", pos, pos, run, rc, ""))
            elif rc.tag == w_tag("tab"):
                atoms.append(Atom("tab", pos, pos + 1, run, rc, "\t"))
                pos += 1
            elif rc.tag == w_tag("br"):
                atoms.append(Atom("br", pos, pos + 1, run, rc, "\n"))
                pos += 1
            elif rc.tag == w_tag("noBreakHyphen"):
                atoms.append(Atom("text", pos, pos + 1, run, rc, "\u2011"))
                pos += 1
            elif rc.tag == w_tag("softHyphen"):
                atoms.append(Atom("text", pos, pos + 1, run, rc, "\u00ad"))
                pos += 1
            elif rc.tag == w_tag("footnoteReference"):
                atoms.append(Atom("fn", pos, pos, run, rc))
            elif rc.tag == w_tag("endnoteReference"):
                atoms.append(Atom("endnote", pos, pos, run, rc))
            else:
                atoms.append(Atom("run_special", pos, pos, run, rc))
    old_text = "".join(a.text for a in atoms if a.kind in ("text", "tab", "br"))
    return atoms, old_text


def _context_run_for_pos(atoms: List[Atom], pos: int) -> Optional[etree._Element]:
    # Prefer body-text runs so inserted text does not inherit footnote/endnote
    # superscript styling when edits occur adjacent to references.
    for a in atoms:
        if a.run is not None and a.kind in ("text", "tab", "br") and a.start <= pos < a.end:
            return a.run
        if a.run is not None and a.kind == "text" and a.start == pos and a.end == pos:
            return a.run

    # If no direct hit, prefer the nearest textual run behind the insertion
    # point, then the nearest textual run ahead.
    for a in reversed(atoms):
        if a.run is not None and a.kind in ("text", "tab", "br") and a.end <= pos:
            return a.run
    for a in atoms:
        if a.run is not None and a.kind in ("text", "tab", "br") and a.start >= pos:
            return a.run

    # Last resort for non-text-only paragraphs.
    for a in reversed(atoms):
        if a.run is not None:
            return a.run
    return None


def _emit_atom(atom: Atom, *, text_override: Optional[str] = None) -> etree._Element:
    if atom.kind == "p_special":
        return deepcopy(atom.elem)

    run = _clone_run_with_rPr(atom.run)
    if atom.kind == "text":
        effective_text = text_override if text_override is not None else atom.text
        if atom.elem.tag == w_tag("noBreakHyphen") and effective_text == "\u2011":
            run.append(deepcopy(atom.elem))
        elif atom.elem.tag == w_tag("softHyphen") and effective_text == "\u00ad":
            run.append(deepcopy(atom.elem))
        else:
            run.append(_t(effective_text))
    elif atom.kind == "tab":
        run.append(deepcopy(atom.elem))
    elif atom.kind == "br":
        run.append(deepcopy(atom.elem))
    else:
        run.append(deepcopy(atom.elem))
    return run


def _emit_changed_text(text: str, context_run: Optional[etree._Element], *, markup: bool) -> List[etree._Element]:
    out: List[etree._Element] = []
    if not text:
        return out

    # Preserve tabs/line breaks as Word elements, not literal characters.
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\t":
            r = _clone_run_for_changed_text(context_run, markup=markup)
            r.append(etree.Element(w_tag("tab")))
            out.append(r)
            i += 1
            continue
        if ch == "\n":
            r = _clone_run_for_changed_text(context_run, markup=markup)
            r.append(etree.Element(w_tag("br")))
            out.append(r)
            i += 1
            continue
        if ch == "\u2011":
            r = _clone_run_for_changed_text(context_run, markup=markup)
            r.append(etree.Element(w_tag("noBreakHyphen")))
            out.append(r)
            i += 1
            continue
        if ch == "\u00ad":
            r = _clone_run_for_changed_text(context_run, markup=markup)
            r.append(etree.Element(w_tag("softHyphen")))
            out.append(r)
            i += 1
            continue

        j = i
        while j < len(text) and text[j] not in ("\t", "\n", "\u2011", "\u00ad"):
            j += 1
        chunk = text[i:j]
        r = _clone_run_for_changed_text(context_run, markup=markup)
        r.append(_t(chunk))
        out.append(r)
        i = j
    return out


def _rewrite_paragraph_in_place(p: etree._Element, new_children: List[etree._Element]) -> None:
    pPr = p.find("w:pPr", namespaces=NS)
    for child in list(p):
        if child is pPr:
            continue
        p.remove(child)
    if pPr is None:
        for c in new_children:
            p.append(c)
        return
    insert_at = list(p).index(pPr) + 1
    for c in new_children:
        p.insert(insert_at, c)
        insert_at += 1


def _apply_diff_to_paragraph(
    p: etree._Element,
    new_text: str,
    *,
    markup: bool,
    preserve_projected_inline_italics: bool = False,
) -> bool:
    atoms, old_text = _paragraph_atoms(p)
    if old_text == new_text:
        return False
    old_italic_rpr_spans = (
        _existing_italic_rpr_spans_from_atoms(atoms) if preserve_projected_inline_italics else []
    )

    old_tokens = _tokenize(old_text)
    new_tokens = _tokenize(new_text)

    sm = difflib.SequenceMatcher(a=old_tokens, b=new_tokens, autojunk=False)
    opcodes = sm.get_opcodes()

    # Precompute token -> char offsets.
    old_tok_starts: List[int] = []
    cur = 0
    for tok in old_tokens:
        old_tok_starts.append(cur)
        cur += len(tok)
    old_total = cur

    new_tok_starts: List[int] = []
    cur = 0
    for tok in new_tokens:
        new_tok_starts.append(cur)
        cur += len(tok)

    def old_char_range(i1: int, i2: int) -> Tuple[int, int]:
        if i1 == i2:
            return (old_tok_starts[i1] if i1 < len(old_tok_starts) else old_total, old_tok_starts[i1] if i1 < len(old_tok_starts) else old_total)
        start = old_tok_starts[i1]
        end = old_tok_starts[i2 - 1] + len(old_tokens[i2 - 1])
        return start, end

    def new_char_range(j1: int, j2: int) -> Tuple[int, int]:
        if j1 == j2:
            at = new_tok_starts[j1] if j1 < len(new_tok_starts) else len(new_text)
            return at, at
        start = new_tok_starts[j1]
        end = new_tok_starts[j2 - 1] + len(new_tokens[j2 - 1])
        return start, end

    emitted_specials: set[int] = set()

    def emit_old_segment(start: int, end: int, *, include_text: bool) -> List[etree._Element]:
        out: List[etree._Element] = []
        for a in atoms:
            if a.kind == "text":
                if not include_text:
                    continue
                if a.end <= start or a.start >= end:
                    continue
                s = max(start, a.start)
                e = min(end, a.end)
                if s >= e:
                    continue
                slice_text = a.text[s - a.start : e - a.start]
                out.append(_emit_atom(a, text_override=slice_text))
            elif a.kind in ("tab", "br"):
                if not include_text:
                    continue
                if a.start >= start and a.end <= end:
                    out.append(_emit_atom(a))
            else:
                # Zero-length or anchored elements: preserve them even when text is replaced/deleted.
                if start <= a.start <= end and id(a.elem) not in emitted_specials:
                    emitted_specials.add(id(a.elem))
                    out.append(_emit_atom(a))
        return out

    new_children: List[etree._Element] = []
    for tag, i1, i2, j1, j2 in opcodes:
        o_start, o_end = old_char_range(i1, i2)
        n_start, n_end = new_char_range(j1, j2)

        if tag == "equal":
            new_children.extend(emit_old_segment(o_start, o_end, include_text=True))
            continue

        context_run = _context_run_for_pos(atoms, o_start)
        inserted = new_text[n_start:n_end]

        if tag in ("replace", "insert"):
            new_children.extend(_emit_changed_text(inserted, context_run, markup=markup))

        # Preserve anchored elements that were in the replaced/deleted old range (not its old text).
        if tag in ("replace", "delete"):
            new_children.extend(emit_old_segment(o_start, o_end, include_text=False))

    _rewrite_paragraph_in_place(p, new_children)
    if preserve_projected_inline_italics and old_italic_rpr_spans:
        _restore_projected_inline_italic_styles(
            p,
            old_text=old_text,
            new_text=new_text,
            old_italic_rpr_spans=old_italic_rpr_spans,
        )
    _clear_orphaned_non_alnum_italic_runs(p)
    return True


def _iter_body_paragraphs(doc_root: etree._Element) -> List[etree._Element]:
    return doc_root.xpath("/w:document/w:body//w:p", namespaces=NS)


def _load_docx_xml(path: Path, part: str) -> etree._Element:
    with zipfile.ZipFile(path, "r") as zf:
        data = zf.read(part)
    return etree.fromstring(data)


def _load_docx_xml_if_exists(path: Path, part: str) -> Optional[etree._Element]:
    with zipfile.ZipFile(path, "r") as zf:
        if part not in zf.namelist():
            return None
        data = zf.read(part)
    return etree.fromstring(data)


def _write_docx_with_replaced_part(original_path: Path, out_path: Path, part: str, xml_root: etree._Element) -> None:
    _write_docx_with_replaced_parts(original_path, out_path, {part: xml_root})


def _write_docx_with_replaced_parts(
    original_path: Path, out_path: Path, xml_roots_by_part: dict[str, etree._Element]
) -> None:
    xml_bytes_by_part = {
        part: etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone=False)
        for part, root in xml_roots_by_part.items()
    }
    with zipfile.ZipFile(original_path, "r") as zin:
        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename in xml_bytes_by_part:
                    data = xml_bytes_by_part[info.filename]
                zout.writestr(info, data)


def _count_yellow_highlight_runs_in_root(root: Optional[etree._Element]) -> int:
    if root is None:
        return 0
    total = 0
    for run in root.xpath(".//w:r", namespaces=NS):
        rPr = run.find("w:rPr", namespaces=NS)
        if rPr is None:
            continue
        highlight = rPr.find("w:highlight", namespaces=NS)
        if highlight is None:
            continue
        if (highlight.get(w_tag("val")) or "").strip().lower() != "yellow":
            continue
        total += 1
    return total


def _yellow_highlight_run_texts_in_root(root: Optional[etree._Element]) -> list[str]:
    if root is None:
        return []
    texts: list[str] = []
    for run in root.xpath(".//w:r", namespaces=NS):
        rPr = run.find("w:rPr", namespaces=NS)
        if rPr is None:
            continue
        highlight = rPr.find("w:highlight", namespaces=NS)
        if highlight is None:
            continue
        if (highlight.get(w_tag("val")) or "").strip().lower() != "yellow":
            continue
        texts.append("".join(run.xpath(".//w:t/text()", namespaces=NS)))
    return texts


def _assert_markup_detectable(original_docx: Path, amended_docx: Path, changed_count: int) -> None:
    if changed_count <= 0:
        return
    original_total = 0
    amended_total = 0
    original_marked_texts: list[str] = []
    amended_marked_texts: list[str] = []
    xml_changed = False
    for part in ("word/document.xml", "word/footnotes.xml"):
        original_root = _load_docx_xml_if_exists(original_docx, part)
        amended_root = _load_docx_xml_if_exists(amended_docx, part)
        original_total += _count_yellow_highlight_runs_in_root(original_root)
        amended_total += _count_yellow_highlight_runs_in_root(amended_root)
        original_marked_texts.extend(_yellow_highlight_run_texts_in_root(original_root))
        amended_marked_texts.extend(_yellow_highlight_run_texts_in_root(amended_root))
        original_xml = etree.tostring(original_root, encoding="unicode") if original_root is not None else ""
        amended_xml = etree.tostring(amended_root, encoding="unicode") if amended_root is not None else ""
        if original_xml != amended_xml:
            xml_changed = True
    if xml_changed and amended_total > 0:
        return
    if amended_total <= original_total and amended_marked_texts == original_marked_texts:
        try:
            amended_docx.unlink(missing_ok=True)
        except OSError:
            pass
        raise ValueError(
            "Amendment markup hard rule failed: output does not contain detectable added "
            "yellow-highlighted changes."
        )


def _iter_footnote_paragraphs_by_id(root: etree._Element) -> dict[int, List[etree._Element]]:
    by_id: dict[int, List[etree._Element]] = {}
    for fn in root.xpath("/w:footnotes/w:footnote", namespaces=NS):
        raw_id = fn.get(w_tag("id"))
        if raw_id is None:
            continue
        try:
            fid = int(raw_id)
        except ValueError:
            continue
        # Skip separators/continuations and any non-user footnotes.
        if fid <= 0:
            continue
        by_id[fid] = fn.xpath("./w:p", namespaces=NS)
    return by_id


def _iter_footnote_nodes_by_id(root: etree._Element) -> dict[int, etree._Element]:
    by_id: dict[int, etree._Element] = {}
    for fn in root.xpath("/w:footnotes/w:footnote", namespaces=NS):
        raw_id = fn.get(w_tag("id"))
        if raw_id is None:
            continue
        try:
            fid = int(raw_id)
        except ValueError:
            continue
        if fid <= 0:
            continue
        by_id[fid] = fn
    return by_id


def _direct_run_text_length(run: etree._Element) -> int:
    total = 0
    for child in run:
        if child.tag == w_tag("t"):
            total += len(child.text or "")
        elif child.tag in (w_tag("tab"), w_tag("br"), w_tag("noBreakHyphen"), w_tag("softHyphen")):
            total += 1
    return total


def _footnote_reference_runs_with_positions(p: etree._Element) -> List[Tuple[etree._Element, int, str]]:
    refs: List[Tuple[etree._Element, int, str]] = []
    pos = 0
    for child in p:
        if child.tag == w_tag("pPr"):
            continue
        if child.tag != w_tag("r"):
            continue
        ref = child.find("w:footnoteReference", namespaces=NS)
        if ref is not None:
            ref_id = ref.get(w_tag("id"))
            if ref_id is not None:
                refs.append((deepcopy(child), pos, ref_id))
            continue
        pos += _direct_run_text_length(child)
    return refs


def _footnote_reference_run_nodes_with_positions(p: etree._Element) -> List[Tuple[etree._Element, int, str]]:
    refs: List[Tuple[etree._Element, int, str]] = []
    pos = 0
    for child in p:
        if child.tag == w_tag("pPr"):
            continue
        if child.tag != w_tag("r"):
            continue
        ref = child.find("w:footnoteReference", namespaces=NS)
        if ref is not None:
            ref_id = ref.get(w_tag("id"))
            if ref_id is not None:
                refs.append((child, pos, ref_id))
            continue
        pos += _direct_run_text_length(child)
    return refs


def _remove_footnote_reference_runs(p: etree._Element) -> int:
    removed = 0
    for run in list(p.xpath("./w:r[w:footnoteReference]", namespaces=NS)):
        p.remove(run)
        removed += 1
    return removed


def _dedupe_adjacent_body_footnote_reference_runs(p: etree._Element) -> int:
    changed = 0
    last_ref_id: Optional[str] = None
    last_ref_pos: Optional[int] = None
    cursor = 0

    for child in list(p):
        if child.tag != w_tag("r"):
            continue

        ref = child.find("w:footnoteReference", namespaces=NS)
        if ref is not None:
            ref_id = ref.get(w_tag("id"))
            if ref_id is not None and ref_id == last_ref_id and cursor == last_ref_pos:
                p.remove(child)
                changed += 1
                continue
            last_ref_id = ref_id
            last_ref_pos = cursor
            continue

        run_len = _direct_run_text_length(child)
        if run_len > 0:
            cursor += run_len
            last_ref_id = None
            last_ref_pos = None

    return changed


def _split_simple_text_run_at(p: etree._Element, run: etree._Element, offset: int) -> Optional[int]:
    children = [child for child in list(run) if child.tag != w_tag("rPr")]
    if len(children) != 1 or children[0].tag != w_tag("t"):
        return None

    text = children[0].text or ""
    if offset <= 0 or offset >= len(text):
        return None

    left = _clone_run_with_rPr(run)
    left.append(_t(text[:offset]))
    right = _clone_run_with_rPr(run)
    right.append(_t(text[offset:]))

    idx = list(p).index(run)
    p.remove(run)
    p.insert(idx, left)
    p.insert(idx + 1, right)
    return idx + 1


def _reference_insert_index_for_text_pos(p: etree._Element, pos: int) -> int:
    children = list(p)
    pPr = p.find("w:pPr", namespaces=NS)
    start_idx = children.index(pPr) + 1 if pPr is not None else 0
    cursor = 0
    idx = start_idx

    while idx < len(children):
        child = children[idx]
        if child.tag != w_tag("r"):
            idx += 1
            continue

        run_len = _direct_run_text_length(child)
        if run_len <= 0:
            idx += 1
            continue

        end = cursor + run_len
        if pos < end:
            if pos <= cursor:
                return idx
            split_idx = _split_simple_text_run_at(p, child, pos - cursor)
            return split_idx if split_idx is not None else idx
        if pos == end:
            return idx + 1

        cursor = end
        idx += 1

    return len(list(p))


def _sync_footnote_reference_runs_from_amended(p_orig: etree._Element, p_amend: etree._Element) -> int:
    original_refs = [(ref_id, pos) for _run, pos, ref_id in _footnote_reference_runs_with_positions(p_orig)]
    amended_refs = _footnote_reference_runs_with_positions(p_amend)
    amended_signature = [(ref_id, pos) for _run, pos, ref_id in amended_refs]

    if original_refs == amended_signature:
        return 0
    if original_refs and not amended_signature:
        # Preserve the user's live markers when an amended export loses them.
        # We only resync body references when the amended source carries an
        # explicit replacement marker set.
        return 0

    removed = _remove_footnote_reference_runs(p_orig)
    inserted = 0
    for run_copy, pos, _ref_id in amended_refs:
        insert_at = _reference_insert_index_for_text_pos(p_orig, pos)
        p_orig.insert(insert_at, deepcopy(run_copy))
        inserted += 1

    return 1 if removed or inserted or original_refs or amended_signature else 0


def _remove_reference_runs(p: etree._Element) -> None:
    for run in list(p.xpath("./w:r", namespaces=NS)):
        if _is_reference_run(run):
            p.remove(run)


def _anchor_word_before_position(text: str, pos: int) -> Optional[re.Match[str]]:
    match: Optional[re.Match[str]] = None
    for candidate in BODY_WORD_RE.finditer(text):
        if candidate.end() > pos:
            break
        match = candidate
    return match


def _sentence_bounds_for_position(text: str, pos: int) -> Tuple[int, int]:
    start = 0
    for match in re.finditer(r"[.!?]", text):
        if match.end() <= pos:
            start = match.end()
            continue
        return start, match.end()
    return start, len(text)


def _body_reference_target_pos_for_low_value_anchor(text: str, pos: int) -> Optional[int]:
    anchor_match = _anchor_word_before_position(text, pos)
    if anchor_match is None:
        return None

    anchor_word = _normalize_case_reference_name(anchor_match.group(0))
    if anchor_word not in LOW_VALUE_BODY_REFERENCE_ANCHORS:
        return None

    sentence_start, _sentence_end = _sentence_bounds_for_position(text, pos)
    return sentence_start if sentence_start > 0 else None


def _find_case_name_candidate_spans(text: str, candidate_names: set[str]) -> List[Tuple[int, int]]:
    if not text or not candidate_names:
        return []

    tokens = list(BODY_WORD_RE.finditer(text))
    spans: List[Tuple[int, int]] = []
    for start_idx in range(len(tokens)):
        for end_idx in range(start_idx, min(start_idx + MAX_BODY_CASE_NAME_TOKENS, len(tokens))):
            phrase = " ".join(tokens[idx].group(0) for idx in range(start_idx, end_idx + 1))
            normalized = _normalize_case_reference_name(phrase)
            if not normalized:
                continue
            if end_idx == start_idx and normalized in AMBIGUOUS_SINGLE_WORD_CASE_REFERENCES:
                continue
            if normalized in candidate_names:
                spans.append((tokens[start_idx].start(), tokens[end_idx].end()))
    return _merge_spans(spans)


def _context_supports_ambiguous_case_short_form(
    text: str,
    token_match: re.Match[str],
) -> bool:
    sentence_start, sentence_end = _sentence_bounds_for_position(text, token_match.start())
    sentence = text[sentence_start:sentence_end]
    words = [match.group(0).casefold() for match in BODY_WORD_RE.finditer(sentence)]
    if not words:
        return False

    local_start = token_match.start() - sentence_start
    local_end = token_match.end() - sentence_start
    token_index: Optional[int] = None
    sentence_word_matches = list(BODY_WORD_RE.finditer(sentence))
    for idx, match in enumerate(sentence_word_matches):
        if match.start() == local_start and match.end() == local_end:
            token_index = idx
            break
    if token_index is None:
        return False

    score = 0
    window_start = max(0, token_index - 4)
    window_end = min(len(words), token_index + 5)
    nearby_words = words[window_start:window_end]
    if any(word in AMBIGUOUS_CASE_SHORT_FORM_POSITIVE_CUES for word in nearby_words):
        score += 2
    if any(word in {"authority", "precedent", "holding", "judgment", "ruling"} for word in nearby_words):
        score += 1
    if any(word in AMBIGUOUS_CASE_SHORT_FORM_NEGATIVE_CUES for word in nearby_words):
        score -= 2

    if token_index > 0 and words[token_index - 1] in {"in", "under", "per", "see", "cf"}:
        score += 1
    if token_index >= 2 and words[token_index - 2 : token_index] == ["the", "case"]:
        score += 2
    if token_index >= 2 and words[token_index - 2 : token_index] == ["in", "favour"]:
        score -= 2
    if token_index >= 3 and words[token_index - 3 : token_index] == ["in", "favour", "of"]:
        score -= 3
    if token_index > 0 and words[token_index - 1] in AMBIGUOUS_CASE_SHORT_FORM_NEGATIVE_PRECEDING_CUES:
        score -= 1

    return score >= 2


def _ambiguous_case_short_form_spans(
    text: str,
    ambiguous_short_forms: set[str],
) -> List[Tuple[int, int]]:
    if not text or not ambiguous_short_forms:
        return []

    spans: List[Tuple[int, int]] = []
    for token_match in BODY_WORD_RE.finditer(text):
        normalized = _normalize_case_reference_name(token_match.group(0))
        if normalized not in ambiguous_short_forms:
            continue
        if _context_supports_ambiguous_case_short_form(text, token_match):
            spans.append((token_match.start(), token_match.end()))
    return _merge_spans(spans)


def _body_reference_target_pos_for_case_name(
    text: str,
    pos: int,
    ref_id: int,
    *,
    case_reference_names_by_footnote: dict[int, set[str]],
) -> Optional[int]:
    candidate_names = case_reference_names_by_footnote.get(ref_id, set())
    if not candidate_names:
        return _body_reference_target_pos_for_low_value_anchor(text, pos)

    spans = _find_case_name_candidate_spans(text, candidate_names)
    containing_spans = [(start, end) for start, end in spans if start < pos < end]
    if containing_spans:
        return containing_spans[0][1]

    preceding_spans = [(start, end) for start, end in spans if end <= pos]
    if not preceding_spans:
        return _body_reference_target_pos_for_low_value_anchor(text, pos)
    nearest_start, nearest_end = preceding_spans[-1]
    if abs(pos - nearest_end) <= 2:
        return None

    anchor_match = _anchor_word_before_position(text, pos)
    if anchor_match is None:
        return nearest_end

    anchor_start, anchor_end = anchor_match.start(), anchor_match.end()
    anchor_word = _normalize_case_reference_name(anchor_match.group(0))
    anchor_inside_matching_span = any(start <= anchor_start and anchor_end <= end for start, end in spans)
    if anchor_inside_matching_span:
        return nearest_end

    if anchor_word in GENERIC_BODY_REFERENCE_ANCHORS or anchor_word in LOW_VALUE_BODY_REFERENCE_ANCHORS:
        return nearest_end

    sentence_start, sentence_end = _sentence_bounds_for_position(text, pos)
    sentence_spans = [
        (start, end)
        for start, end in spans
        if sentence_start <= start and end <= pos
    ]
    if len(sentence_spans) == 1:
        return sentence_spans[0][1]

    if pos - nearest_end > 8:
        return nearest_end

    if anchor_match.group(0)[0].isupper():
        return nearest_end

    return None


def _template_paragraphs_for_new_footnote(
    orig_nodes_by_id: dict[int, etree._Element], fid: int
) -> List[etree._Element]:
    if not orig_nodes_by_id:
        return []

    ids = sorted(orig_nodes_by_id)
    lower_ids = [candidate for candidate in ids if candidate < fid]
    higher_ids = [candidate for candidate in ids if candidate > fid]
    template_id = lower_ids[-1] if lower_ids else higher_ids[0]
    return orig_nodes_by_id[template_id].xpath("./w:p", namespaces=NS)


def _build_new_footnote_from_template(
    fid: int,
    amended_paras: List[etree._Element],
    template_paras: List[etree._Element],
    *,
    markup: bool,
    rewrite_crossrefs: bool = True,
    force_full_replace: bool = False,
    footnote_search_text_by_id: dict[int, str],
    case_reference_names_by_footnote: dict[int, set[str]],
    existing_footnotes_root: Optional[etree._Element] = None,
) -> etree._Element:
    footnote = etree.Element(w_tag("footnote"))
    footnote.set(w_tag("id"), str(fid))

    for idx, p_amend in enumerate(amended_paras):
        if not template_paras:
            raise ValueError(f"Cannot build new footnote {fid}: no original footnote template is available.")
        template_para = template_paras[min(idx, len(template_paras) - 1)]
        template_run_segments = _paragraph_text_run_segments(
            template_para,
            after_reference_marker=(idx == 0),
        )
        template_text = "".join(seg[3] for seg in template_run_segments)
        p_new = deepcopy(template_para)
        if idx > 0:
            _remove_reference_runs(p_new)
        original_refs = _collect_reference_runs(p_new)
        raw_text = _sanitize_footnote_plain_text(_paragraph_text_all_runs(p_amend))
        new_text = (
            _rewrite_cross_reference_numbers_in_text(
                raw_text,
                footnote_search_text_by_id=footnote_search_text_by_id,
                case_reference_names_by_footnote=case_reference_names_by_footnote,
                current_footnote_id=fid,
            )
            if rewrite_crossrefs
            else raw_text
        )
        if existing_footnotes_root is not None and len(amended_paras) == 1:
            new_text = _normalize_new_footnote_citation_text(
                new_text,
                footnotes_root=existing_footnotes_root,
                current_footnote_id=fid,
            )
        preserve_template_italic_spans = (
            force_full_replace
            and _sanitize_footnote_plain_text(template_text).strip() == new_text.strip()
        )
        template_italic_rpr_spans = (
            _existing_italic_rpr_spans(template_run_segments)
            if preserve_template_italic_spans
            else []
        )
        template_italic_spans = (
            _existing_italic_spans(template_run_segments)
            if preserve_template_italic_spans
            else []
        )
        if not force_full_replace and _paragraph_is_simple(p_new):
            _apply_diff_to_paragraph(p_new, new_text, markup=markup)
        else:
            _apply_full_replace_to_paragraph(p_new, new_text, markup=markup)
        if idx == 0:
            _restore_reference_runs_if_missing(p_new, original_refs)
            _ensure_reference_marker_first(p_new)
            _ensure_space_after_reference_marker(p_new)
        if template_italic_rpr_spans:
            current_text = "".join(
                seg[3]
                for seg in _paragraph_text_run_segments(
                    p_new,
                    after_reference_marker=(idx == 0),
                )
            )
            preserved_rpr_spans = _project_preserved_rpr_spans(
                template_text,
                current_text,
                template_italic_rpr_spans,
            )
            if preserved_rpr_spans:
                _apply_rpr_spans_to_runs(
                    p_new,
                    preserved_rpr_spans,
                    after_reference_marker=(idx == 0),
                )
        if template_italic_spans:
            current_text = "".join(
                seg[3]
                for seg in _paragraph_text_run_segments(
                    p_new,
                    after_reference_marker=(idx == 0),
                )
            )
            preserved_spans = _project_preserved_italic_spans(
                template_text,
                current_text,
                template_italic_spans,
            )
            if preserved_spans:
                _apply_italic_spans_to_runs(
                    p_new,
                    preserved_spans,
                    after_reference_marker=(idx == 0),
                    additive_only=True,
                )
        _italicize_case_name_runs_in_footnote(p_new)
        footnote.append(p_new)

    return footnote


def _collect_reference_runs(p: etree._Element) -> List[etree._Element]:
    refs: List[etree._Element] = []
    for r in p.xpath("./w:r", namespaces=NS):
        if r.find("w:footnoteRef", namespaces=NS) is not None or r.find("w:endnoteReference", namespaces=NS) is not None:
            refs.append(deepcopy(r))
    return refs


def _restore_reference_runs_if_missing(p: etree._Element, original_refs: List[etree._Element]) -> None:
    if not original_refs:
        return
    current_refs = p.xpath("./w:r[w:footnoteRef or w:endnoteReference]", namespaces=NS)
    missing = len(original_refs) - len(current_refs)
    if missing <= 0:
        return
    pPr = p.find("w:pPr", namespaces=NS)
    insert_at = list(p).index(pPr) + 1 if pPr is not None else 0
    for ref_run in original_refs[:missing]:
        p.insert(insert_at, deepcopy(ref_run))
        insert_at += 1


def _is_reference_run(run: etree._Element) -> bool:
    return (
        run.find("w:footnoteRef", namespaces=NS) is not None
        or run.find("w:endnoteReference", namespaces=NS) is not None
    )


def _ensure_reference_marker_first(p: etree._Element) -> None:
    runs = p.xpath("./w:r", namespaces=NS)
    marker_index = next((idx for idx, run in enumerate(runs) if _is_reference_run(run)), None)
    if marker_index is None or marker_index <= 0:
        return

    textual_prefix_runs = [run for run in runs[:marker_index] if run.xpath("./w:t|./w:tab|./w:br", namespaces=NS)]
    if not textual_prefix_runs:
        return

    for run in textual_prefix_runs:
        p.remove(run)

    current_runs = p.xpath("./w:r", namespaces=NS)
    marker_run = next((run for run in current_runs if _is_reference_run(run)), None)
    if marker_run is None:
        return

    insert_at = list(p).index(marker_run) + 1
    for run in textual_prefix_runs:
        p.insert(insert_at, run)
        insert_at += 1


def _set_italic(rPr: etree._Element) -> None:
    italic = rPr.find("w:i", namespaces=NS)
    if italic is None:
        italic = etree.Element(w_tag("i"))
        rPr.append(italic)
    italic.set(w_tag("val"), "1")

    italic_cs = rPr.find("w:iCs", namespaces=NS)
    if italic_cs is None:
        italic_cs = etree.Element(w_tag("iCs"))
        rPr.append(italic_cs)
    italic_cs.set(w_tag("val"), "1")


def _set_bold(rPr: etree._Element) -> None:
    bold = rPr.find("w:b", namespaces=NS)
    if bold is None:
        bold = etree.Element(w_tag("b"))
        rPr.append(bold)
    bold.set(w_tag("val"), "1")

    bold_cs = rPr.find("w:bCs", namespaces=NS)
    if bold_cs is None:
        bold_cs = etree.Element(w_tag("bCs"))
        rPr.append(bold_cs)
    bold_cs.set(w_tag("val"), "1")


def _clear_bold(rPr: etree._Element) -> int:
    changed = 0
    for tag in ("b", "bCs"):
        bold = rPr.find(f"w:{tag}", namespaces=NS)
        if bold is not None:
            rPr.remove(bold)
            changed += 1
    return changed


def _clear_italic(rPr: etree._Element) -> int:
    changed = 0
    for tag in ("i", "iCs"):
        italic = rPr.find(f"w:{tag}", namespaces=NS)
        if italic is not None:
            rPr.remove(italic)
            changed += 1
    r_style = rPr.find("w:rStyle", namespaces=NS)
    if r_style is not None:
        style_name = (r_style.get(w_tag("val")) or "").strip().casefold()
        if "emphasis" in style_name:
            for tag in ("i", "iCs"):
                italic = rPr.find(f"w:{tag}", namespaces=NS)
                if italic is None:
                    italic = etree.Element(w_tag(tag))
                    rPr.append(italic)
                    changed += 1
                current_val = (italic.get(w_tag("val")) or "").strip().lower()
                if current_val not in {"0", "false", "off", "no"}:
                    italic.set(w_tag("val"), "0")
                    changed += 1
    return changed


def _has_effective_italic(rPr: Optional[etree._Element]) -> bool:
    if rPr is None:
        return False
    explicit_false = False
    for tag in ("i", "iCs"):
        italic = rPr.find(f"w:{tag}", namespaces=NS)
        if italic is None:
            continue
        val = (italic.get(w_tag("val")) or "").strip().lower()
        if val in {"0", "false", "off", "no"}:
            explicit_false = True
            continue
        return True
    if explicit_false:
        return False
    r_style = rPr.find("w:rStyle", namespaces=NS)
    if r_style is not None:
        style_name = (r_style.get(w_tag("val")) or "").strip().casefold()
        if "emphasis" in style_name:
            return True
    return False


CASE_NAME_PATTERN = re.compile(
    r"(?:\b(?:In\s+re|Re)\s+\(?[A-Z][A-Za-z0-9&'.,()/\-]*(?:\s+(?:\(?[A-Z][A-Za-z0-9&'.,()/\-]*|of|the|and|for|de|la|le|del|du|van|von|da|di|al))*"
    r"|\bIn\s+the\s+Matter\s+of\s+\(?[A-Z][A-Za-z0-9&'.,()/\-]*(?:\s+(?:\(?[A-Z][A-Za-z0-9&'.,()/\-]*|of|the|and|for|de|la|le|del|du|van|von|da|di|al))*"
    r"|\b\(?[A-Z][A-Za-z0-9&'.,()/\-]*(?:\s+(?:\(?[A-Z][A-Za-z0-9&'.,()/\-]*|of|the|and|for|de|la|le|del|du|van|von|da|di|al))*\s+v\s+"
    r"\(?[A-Z][A-Za-z0-9&'.,()/\-]*(?:\s+(?:\(?[A-Z][A-Za-z0-9&'.,()/\-]*|of|the|and|for|de|la|le|del|du|van|von|da|di|al))*)"
)

CASE_TOKEN = r"\(?[A-Z][A-Za-z0-9&'.,()/\-]*"
CASE_SUFFIX_TOKEN = r"(?:plc|ltd|limited|llc|sa|ag|nv|spa|sas|corp|corporation|inc|co|company|gmbh|llp|lp|bv|sarl)"
CASE_JOINER = rf"(?:\(?[A-Z][A-Za-z0-9&'.,()/\-]*|&|{CASE_SUFFIX_TOKEN}|of|the|and|for|de|la|le|del|du|van|von|da|di|al)"
CASE_V_PATTERN = re.compile(
    rf"\b{CASE_TOKEN}(?:\s+{CASE_JOINER})*\s+v\s+{CASE_TOKEN}(?:\s+{CASE_JOINER})*(?=\s*(?:\([^)]*\)|\[\d{{4}}]|EU:|ECLI:|[.;,]|$))"
)
RE_CASE_PATTERN = re.compile(
    rf"\b(?:In\s+re|Re)\s+{CASE_TOKEN}(?:\s+{CASE_JOINER})*(?=\s*(?:\([^)]*\)|\[\d{{4}}]|[.;,]|$))"
)
MATTER_CASE_PATTERN = re.compile(
    rf"\bIn\s+the\s+Matter\s+of\s+{CASE_TOKEN}(?:\s+{CASE_JOINER})*(?=\s*(?:\([^)]*\)|\[\d{{4}}]|[.;,]|$))"
)
SHIP_CASE_PATTERN = re.compile(
    rf"\bThe\s+{CASE_TOKEN}(?:\s+{CASE_TOKEN}){{0,3}}(?=\s*(?:\[[0-9]{{4}}\]|\([0-9]{{4}}\)))"
)
SHORT_CASE_CROSSREF_PATTERN = re.compile(
    rf"\b({CASE_TOKEN}(?:\s+{CASE_JOINER})*)\s*\(n\s+(\d+)\)",
    flags=re.IGNORECASE,
)
SHORT_CASE_WITH_CASE_NUMBER_PATTERN = re.compile(
    rf"\b({CASE_TOKEN}(?:\s+{CASE_JOINER})*)(?=\s*\(Case\s+[^)]*\))",
    flags=re.IGNORECASE,
)
GENERIC_CROSSREF_NUMBER_PATTERN = re.compile(r"\(n\s+(\d+)\)", flags=re.IGNORECASE)
PARTY_DESCRIPTOR_SUFFIX_RE = re.compile(
    r"(?:\s+(?:and\s+)?(?:others?|another|anor\.?|ors?\.?))+$",
    flags=re.IGNORECASE,
)
CASE_SHORT_FORM_PARENTHETICAL_RE = re.compile(r"\(([^)]{1,80})\)")
MAX_CROSSREF_ANCHOR_TOKENS = 6
CROSSREF_CONNECTOR_WORDS = {
    "&",
    "and",
    "de",
    "del",
    "di",
    "du",
    "for",
    "in",
    "la",
    "le",
    "of",
    "the",
    "van",
    "von",
}
CROSSREF_LEADING_STOPWORDS = {"cf", "compare", "contra", "see"}
CORPORATE_SUFFIXES = {
    "plc",
    "ltd",
    "limited",
    "llc",
    "sa",
    "ag",
    "nv",
    "spa",
    "sas",
    "corp",
    "corporation",
    "inc",
    "co",
    "company",
    "gmbh",
    "llp",
    "lp",
    "bv",
    "sarl",
}


def _looks_like_case_name_text(text: str) -> bool:
    t = re.sub(r"\s+", " ", text).strip()
    if not t:
        return False
    if re.search(r"\bibid\b", t, flags=re.IGNORECASE):
        return False
    return bool(
        CASE_V_PATTERN.search(t)
        or RE_CASE_PATTERN.search(t)
        or MATTER_CASE_PATTERN.search(t)
        or SHIP_CASE_PATTERN.search(t)
    )


def _normalize_case_reference_name(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip(" \t\n\r;:,.")
    collapsed = collapsed.replace("’", "'")
    return collapsed.casefold()


def _strip_corporate_suffixes(text: str) -> str:
    tokens = re.split(r"\s+", text.strip())
    while tokens:
        tail = re.sub(r"[.,;:]+$", "", tokens[-1]).casefold()
        if tail not in CORPORATE_SUFFIXES:
            break
        tokens.pop()
    return " ".join(tokens).strip()


def _strip_case_sequel_suffix(text: str) -> str:
    stripped = re.sub(r"\s+(?:I|II|III|IV|V|VI|VII|VIII|IX|X)$", "", text.strip())
    return stripped.strip()


def _strip_party_descriptor_suffix(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip(" \t\n\r;:,.()")
    while True:
        updated = PARTY_DESCRIPTOR_SUFFIX_RE.sub("", cleaned).strip(" \t\n\r;:,.()")
        if updated == cleaned:
            return cleaned
        cleaned = updated


def _strip_trailing_party_connectors(text: str) -> str:
    return re.sub(r"(?:\s+(?:&|and))+$", "", text, flags=re.IGNORECASE).strip(" \t\n\r;:,.()&")


def _clean_case_party_for_short_form(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip(" \t\n\r;:,.()")
    if not cleaned:
        return ""

    while True:
        updated = _strip_case_sequel_suffix(cleaned)
        updated = _strip_party_descriptor_suffix(updated)
        updated = _strip_corporate_suffixes(updated)
        updated = _strip_trailing_party_connectors(updated)
        updated = re.sub(r"\s+", " ", updated).strip(" \t\n\r;:,.()")
        if updated == cleaned:
            return updated
        cleaned = updated


def _is_reasonable_case_short_form_candidate(text: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z&.'-]*", text)
    if not words:
        return False
    if len(words) > 4 and not (len(words) == 1 and words[0].isupper()):
        return False
    if len(words) == 1 and _normalize_case_reference_name(words[0]) in AMBIGUOUS_SINGLE_WORD_CASE_REFERENCES:
        return False
    return True


def _append_unique_case_short_form_candidate(candidates: list[str], candidate: str) -> None:
    cleaned = re.sub(r"\s+", " ", candidate).strip(" \t\n\r;:,.()")
    if not cleaned or not _is_reasonable_case_short_form_candidate(cleaned):
        return
    if cleaned not in candidates:
        candidates.append(cleaned)


def _case_short_form_display_candidates(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip(" \t\n\r;:,.")
    if not cleaned:
        return []

    candidates: list[str] = []
    for match in CASE_SHORT_FORM_PARENTHETICAL_RE.finditer(cleaned):
        inner = re.sub(r"\s+", " ", match.group(1)).strip(" \t\n\r;:,.")
        if not inner or not re.search(r"[A-Z]", inner) or re.search(r"\d", inner):
            continue
        if _looks_like_party_parenthetical_inner(inner):
            continue
        _append_unique_case_short_form_candidate(candidates, inner)

    for start, end in _case_name_spans(cleaned):
        snippet = re.sub(r"\s+", " ", cleaned[start:end]).strip(" \t\n\r;:,.")
        if not snippet:
            continue
        if re.search(r"\s+v\s+", snippet):
            first_party = re.split(r"\s+v\s+", snippet, maxsplit=1)[0]
            trimmed_party = _clean_case_party_for_short_form(first_party)
            _append_unique_case_short_form_candidate(candidates, trimmed_party)
            first_segment = re.split(r"\s+and\s+", trimmed_party, maxsplit=1, flags=re.IGNORECASE)[0]
            if first_segment != trimmed_party:
                _append_unique_case_short_form_candidate(
                    candidates,
                    _clean_case_party_for_short_form(first_segment),
                )
            continue
        if re.match(r"^(?:In\s+re|Re)\s+", snippet):
            stripped_re = re.sub(r"^(?:In\s+re|Re)\s+", "", snippet, flags=re.IGNORECASE)
            _append_unique_case_short_form_candidate(candidates, _clean_case_party_for_short_form(stripped_re))
            continue
        if re.match(r"^In\s+the\s+Matter\s+of\s+", snippet, flags=re.IGNORECASE):
            stripped_matter = re.sub(r"^In\s+the\s+Matter\s+of\s+", "", snippet, flags=re.IGNORECASE)
            _append_unique_case_short_form_candidate(
                candidates,
                _clean_case_party_for_short_form(stripped_matter),
            )

    return candidates


def _leading_case_headword_variant(text: str) -> str:
    tokens = [token for token in re.split(r"\s+", text.strip()) if token]
    if len(tokens) < 2:
        return ""
    head = re.sub(r"[.,;:()]+$", "", tokens[0]).strip()
    if not head or head.casefold() in CROSSREF_CONNECTOR_WORDS or head.casefold() in CROSSREF_LEADING_STOPWORDS:
        return ""
    return _normalize_case_reference_name(head)


def _case_reference_variants(text: str) -> set[str]:
    cleaned = re.sub(r"\s+", " ", text).strip(" \t\n\r;:,.")
    if not cleaned:
        return set()
    variants = {_normalize_case_reference_name(cleaned)}
    stripped_sequel = _strip_case_sequel_suffix(cleaned)
    if stripped_sequel and stripped_sequel != cleaned:
        variants.add(_normalize_case_reference_name(stripped_sequel))
    stripped = _strip_corporate_suffixes(cleaned)
    if stripped and stripped != cleaned:
        variants.add(_normalize_case_reference_name(stripped))
        stripped_combo = _strip_case_sequel_suffix(stripped)
        if stripped_combo and stripped_combo != stripped:
            variants.add(_normalize_case_reference_name(stripped_combo))
        headword_variant = _leading_case_headword_variant(stripped_combo or stripped)
        if headword_variant:
            variants.add(headword_variant)
    else:
        headword_variant = _leading_case_headword_variant(stripped_sequel)
        if headword_variant:
            variants.add(headword_variant)
    for candidate in _case_short_form_display_candidates(cleaned):
        variants.add(_normalize_case_reference_name(candidate))
    return {variant for variant in variants if variant}


def _extract_case_reference_names(text: str) -> set[str]:
    names: set[str] = set()

    for start, end in _eu_case_name_spans(text):
        snippet = re.sub(r"\s+", " ", text[start:end]).strip()
        if not snippet:
            continue
        names.update(_case_reference_variants(snippet))
        parties = re.split(r"\s+v\s+", snippet, maxsplit=1)
        if len(parties) == 2:
            names.update(_case_reference_variants(parties[0]))
            names.update(_case_reference_variants(parties[1]))

    for match in CASE_V_PATTERN.finditer(text):
        span = _trim_case_span_leading_eu_case_number_metadata(text, (match.start(), match.end()))
        snippet = re.sub(r"\s+", " ", text[span[0] : span[1]]).strip()
        if not snippet:
            snippet = re.sub(r"\s+", " ", match.group(0)).strip()
        names.update(_case_reference_variants(snippet))
        parties = re.split(r"\s+v\s+", snippet, maxsplit=1)
        if len(parties) == 2:
            names.update(_case_reference_variants(parties[0]))
            names.update(_case_reference_variants(parties[1]))

    for pattern in (RE_CASE_PATTERN, MATTER_CASE_PATTERN, SHIP_CASE_PATTERN):
        for match in pattern.finditer(text):
            names.update(_case_reference_variants(match.group(0)))

    for match in SHORT_CASE_WITH_CASE_NUMBER_PATTERN.finditer(text):
        names.update(_case_reference_variants(match.group(1)))

    return names


def _build_footnote_case_reference_map(root: etree._Element) -> dict[int, set[str]]:
    by_id: dict[int, set[str]] = {}
    paragraphs_by_id = _iter_footnote_paragraphs_by_id(root)

    for fid, paragraphs in paragraphs_by_id.items():
        joined = " ".join(_paragraph_text_all_runs(p) for p in paragraphs)
        by_id[fid] = _extract_case_reference_names(joined)

    # Propagate valid short-form case names through cross-references so later
    # short references to case-only footnotes remain italicised.
    for _ in range(3):
        changed = False
        for fid, paragraphs in paragraphs_by_id.items():
            joined = " ".join(_paragraph_text_all_runs(p) for p in paragraphs)
            for match in SHORT_CASE_CROSSREF_PATTERN.finditer(joined):
                candidate_variants = _case_reference_variants(match.group(1))
                ref_id = int(match.group(2))
                if candidate_variants.intersection(by_id.get(ref_id, set())) and not candidate_variants.issubset(
                    by_id[fid]
                ):
                    by_id[fid].update(candidate_variants)
                    changed = True
            if not changed:
                continue
        if not changed:
            break

    return by_id


def _normalize_reference_search_text(text: str) -> str:
    cleaned = text.replace("’", "'")
    cleaned = re.sub(r"[^A-Za-z0-9'&./-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().casefold()
    return f" {cleaned} " if cleaned else " "


def _build_footnote_search_text_map(root: etree._Element) -> dict[int, str]:
    by_id: dict[int, str] = {}
    for fid, paragraphs in _iter_footnote_paragraphs_by_id(root).items():
        joined = " ".join(_paragraph_text_all_runs(p) for p in paragraphs)
        by_id[fid] = _normalize_reference_search_text(joined)
    return by_id


def _normalize_footnote_identity_text(text: str) -> str:
    cleaned = _sanitize_footnote_plain_text(text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    return cleaned.casefold()


def _looks_like_ibid_text(text: str) -> bool:
    return bool(re.match(r"^\s*ibid\b", text, flags=re.IGNORECASE))


def _extract_simple_footnote_crossref_target(text: str) -> Optional[int]:
    if ";" in text:
        return None
    matches = list(GENERIC_CROSSREF_NUMBER_PATTERN.finditer(text))
    if len(matches) != 1:
        return None
    return int(matches[0].group(1))


def _build_footnote_source_context(
    root: etree._Element,
) -> tuple[dict[int, str], dict[int, int], dict[int, str]]:
    texts_by_id: dict[int, str] = {}
    source_id_by_note: dict[int, int] = {}
    source_identity_by_note: dict[int, str] = {}
    previous_id: Optional[int] = None

    for fid, paragraphs in sorted(_iter_footnote_paragraphs_by_id(root).items()):
        joined = " ".join(_paragraph_text_all_runs(p) for p in paragraphs)
        text = _sanitize_footnote_plain_text(joined).strip()
        texts_by_id[fid] = text

        source_id = fid
        if _looks_like_ibid_text(text) and previous_id is not None:
            source_id = source_id_by_note.get(previous_id, previous_id)
        else:
            crossref_target = _extract_simple_footnote_crossref_target(text)
            if crossref_target is not None and crossref_target < fid and crossref_target in source_id_by_note:
                source_id = source_id_by_note[crossref_target]

        source_id_by_note[fid] = source_id
        if source_id == fid:
            source_identity_by_note[fid] = _normalize_footnote_identity_text(text)
        else:
            source_identity_by_note[fid] = source_identity_by_note.get(
                source_id,
                _normalize_footnote_identity_text(text),
            )
        previous_id = fid

    return texts_by_id, source_id_by_note, source_identity_by_note


def _preferred_case_short_form_for_text(text: str) -> Optional[str]:
    candidates = _case_short_form_display_candidates(text)
    return candidates[0] if candidates else None


def _normalize_new_footnote_citation_text(
    text: str,
    *,
    footnotes_root: etree._Element,
    current_footnote_id: int,
) -> str:
    sanitized = _sanitize_footnote_plain_text(text).strip()
    if not sanitized:
        return sanitized
    if _looks_like_ibid_text(sanitized) or "(n " in sanitized.casefold() or ";" in sanitized:
        return sanitized

    texts_by_id, source_id_by_note, source_identity_by_note = _build_footnote_source_context(footnotes_root)
    prior_ids = [fid for fid in sorted(texts_by_id) if fid < current_footnote_id]
    if not prior_ids:
        return sanitized

    candidate_identity = _normalize_footnote_identity_text(sanitized)
    if not candidate_identity:
        return sanitized

    previous_id = prior_ids[-1]
    previous_source_id = source_id_by_note.get(previous_id, previous_id)
    if source_identity_by_note.get(previous_source_id) == candidate_identity:
        return "ibid."

    matching_source_ids = [
        fid
        for fid in prior_ids
        if source_id_by_note.get(fid, fid) == fid and source_identity_by_note.get(fid) == candidate_identity
    ]
    if not matching_source_ids:
        return sanitized

    target_id = matching_source_ids[0]
    short_form = _preferred_case_short_form_for_text(texts_by_id.get(target_id, sanitized))
    if not short_form:
        return sanitized

    return f"{short_form} (n {target_id})."


def _canonicalize_existing_footnote_citation_text(
    text: str,
    *,
    footnotes_root: etree._Element,
    current_footnote_id: int,
) -> str:
    sanitized = _sanitize_footnote_plain_text(text).strip()
    if not sanitized:
        return sanitized

    footnote_search_text_by_id = _build_footnote_search_text_map(footnotes_root)
    case_reference_names_by_footnote = _build_footnote_case_reference_map(footnotes_root)
    rewritten = _rewrite_cross_reference_numbers_in_text(
        sanitized,
        footnote_search_text_by_id=footnote_search_text_by_id,
        case_reference_names_by_footnote=case_reference_names_by_footnote,
        current_footnote_id=current_footnote_id,
    )
    if ";" in rewritten:
        return rewritten

    texts_by_id, source_id_by_note, source_identity_by_note = _build_footnote_source_context(footnotes_root)
    prior_ids = [fid for fid in sorted(texts_by_id) if fid < current_footnote_id]
    if not prior_ids:
        return rewritten

    previous_id = prior_ids[-1]
    previous_source_id = source_id_by_note.get(previous_id, previous_id)
    target_id: Optional[int] = None

    if _looks_like_ibid_text(rewritten):
        target_id = previous_source_id
    else:
        short_matches = list(SHORT_CASE_CROSSREF_PATTERN.finditer(rewritten))
        if len(short_matches) == 1:
            match = short_matches[0]
            anchor = re.sub(r"\s+", " ", match.group(1)).strip(" \t\n\r;:,.")
            cited_id = int(match.group(2))
            target_id = _resolve_cross_reference_target(
                anchor,
                cited_id,
                footnote_search_text_by_id=footnote_search_text_by_id,
                case_reference_names_by_footnote=case_reference_names_by_footnote,
                current_footnote_id=current_footnote_id,
            )
            if target_id is None and cited_id < current_footnote_id and cited_id in source_id_by_note:
                target_id = source_id_by_note[cited_id]
        if target_id is None:
            candidate_identity = _normalize_footnote_identity_text(rewritten)
            matching_source_ids = [
                fid
                for fid in prior_ids
                if source_id_by_note.get(fid, fid) == fid and source_identity_by_note.get(fid) == candidate_identity
            ]
            if matching_source_ids:
                target_id = matching_source_ids[0]

    if target_id is None:
        return rewritten
    if previous_source_id == target_id:
        return "ibid."

    short_form = _preferred_case_short_form_for_text(texts_by_id.get(target_id, rewritten))
    if not short_form:
        return rewritten
    return f"{short_form} (n {target_id})."


def _new_plain_text_paragraph(text: str) -> etree._Element:
    paragraph = etree.Element(w_tag("p"))
    run = etree.SubElement(paragraph, w_tag("r"))
    run.append(_t(text))
    return paragraph


def _replace_existing_footnote_text_in_root(
    footnotes_root: etree._Element,
    *,
    footnote_id: int,
    new_text: str,
) -> bool:
    nodes_by_id = _iter_footnote_nodes_by_id(footnotes_root)
    current_node = nodes_by_id.get(footnote_id)
    if current_node is None:
        return False

    current_text = _sanitize_footnote_plain_text(
        " ".join(_paragraph_text_all_runs(p) for p in current_node.xpath("./w:p", namespaces=NS))
    ).strip()
    if current_text == new_text.strip():
        return False

    template_paras = current_node.xpath("./w:p", namespaces=NS)
    search_map = _build_footnote_search_text_map(footnotes_root)
    case_map = _build_footnote_case_reference_map(footnotes_root)
    replacement_node = _build_new_footnote_from_template(
        footnote_id,
        [_new_plain_text_paragraph(new_text)],
        template_paras,
        markup=True,
        rewrite_crossrefs=False,
        force_full_replace=True,
        footnote_search_text_by_id=search_map,
        case_reference_names_by_footnote=case_map,
        existing_footnotes_root=footnotes_root,
    )

    parent = current_node.getparent()
    if parent is None:
        return False
    idx = list(parent).index(current_node)
    parent.remove(current_node)
    parent.insert(idx, replacement_node)
    return True


def _normalize_downstream_footnote_citations(
    footnotes_root: Optional[etree._Element],
    *,
    start_footnote_id: int = 1,
) -> set[int]:
    if footnotes_root is None:
        return set()

    changed_ids: set[int] = set()
    footnote_ids = sorted(_iter_footnote_paragraphs_by_id(footnotes_root))
    for fid in footnote_ids:
        if fid < start_footnote_id:
            continue
        node = _iter_footnote_nodes_by_id(footnotes_root).get(fid)
        if node is None:
            continue
        current_text = _sanitize_footnote_plain_text(
            " ".join(_paragraph_text_all_runs(p) for p in node.xpath("./w:p", namespaces=NS))
        ).strip()
        updated_text = _canonicalize_existing_footnote_citation_text(
            current_text,
            footnotes_root=footnotes_root,
            current_footnote_id=fid,
        )
        if updated_text != current_text:
            if _replace_existing_footnote_text_in_root(
                footnotes_root,
                footnote_id=fid,
                new_text=updated_text,
            ):
                changed_ids.add(fid)
    return changed_ids


def _extract_cross_reference_anchor(text: str, crossref_start: int) -> Optional[str]:
    prefix = text[:crossref_start]
    tokens = list(BODY_WORD_RE.finditer(prefix))
    if not tokens:
        return None

    anchor_tokens: List[str] = []
    for token_match in reversed(tokens):
        token = token_match.group(0)
        lowered = token.casefold()
        is_connector = lowered in CROSSREF_CONNECTOR_WORDS
        is_name_like = bool(token) and token[0].isalpha() and token[0].isupper()
        if not anchor_tokens:
            if not is_name_like:
                break
            anchor_tokens.append(token)
            continue
        if is_name_like or is_connector:
            anchor_tokens.append(token)
            if len(anchor_tokens) >= MAX_CROSSREF_ANCHOR_TOKENS:
                break
            continue
        break

    if not anchor_tokens:
        return None

    anchor_tokens.reverse()
    while len(anchor_tokens) > 1 and (
        anchor_tokens[0].casefold() in CROSSREF_LEADING_STOPWORDS or anchor_tokens[0][0].islower()
    ):
        anchor_tokens.pop(0)
    anchor = " ".join(anchor_tokens).strip()
    return anchor or None


def _reference_anchor_variants(text: str) -> set[str]:
    cleaned = re.sub(r"\s+", " ", text).strip(" \t\n\r;:,.")
    if not cleaned:
        return set()
    variants = {_normalize_case_reference_name(cleaned)}
    stripped_sequel = _strip_case_sequel_suffix(cleaned)
    if stripped_sequel and stripped_sequel != cleaned:
        variants.add(_normalize_case_reference_name(stripped_sequel))
    stripped = _strip_corporate_suffixes(cleaned)
    if stripped and stripped != cleaned:
        variants.add(_normalize_case_reference_name(stripped))
        stripped_combo = _strip_case_sequel_suffix(stripped)
        if stripped_combo and stripped_combo != stripped:
            variants.add(_normalize_case_reference_name(stripped_combo))
    return {variant for variant in variants if variant}


def _resolve_cross_reference_target(
    anchor: str,
    cited_id: int,
    *,
    footnote_search_text_by_id: dict[int, str],
    case_reference_names_by_footnote: dict[int, set[str]],
    current_footnote_id: Optional[int] = None,
) -> Optional[int]:
    anchor_variants = _reference_anchor_variants(anchor)
    if not anchor_variants:
        return None

    def choose_best_match(matches: List[int]) -> Optional[int]:
        if not matches:
            return None
        # General rule: a cross-reference should resolve to the earliest footnote
        # where that authority first appears, not to a later short-form repeat.
        return matches[0]

    direct_matches = sorted(
        fid
        for fid, refs in case_reference_names_by_footnote.items()
        if (current_footnote_id is None or fid != current_footnote_id) and anchor_variants.intersection(refs)
    )
    resolved_direct = choose_best_match(direct_matches)
    if resolved_direct is not None:
        return resolved_direct

    text_matches = sorted(
        fid
        for fid, search_text in footnote_search_text_by_id.items()
        if (current_footnote_id is None or fid != current_footnote_id)
        and any(f" {variant} " in search_text for variant in anchor_variants)
    )
    return choose_best_match(text_matches)


def _rewrite_cross_reference_numbers_in_text(
    text: str,
    *,
    footnote_search_text_by_id: dict[int, str],
    case_reference_names_by_footnote: dict[int, set[str]],
    current_footnote_id: Optional[int] = None,
) -> str:
    if "(n " not in text.lower():
        return text

    updated: List[str] = []
    last = 0
    changed = False

    for match in GENERIC_CROSSREF_NUMBER_PATTERN.finditer(text):
        anchor = _extract_cross_reference_anchor(text, match.start())
        if not anchor:
            continue
        cited_id = int(match.group(1))
        resolved_id = _resolve_cross_reference_target(
            anchor,
            cited_id,
            footnote_search_text_by_id=footnote_search_text_by_id,
            case_reference_names_by_footnote=case_reference_names_by_footnote,
            current_footnote_id=current_footnote_id,
        )
        if resolved_id is None or resolved_id == cited_id:
            continue
        updated.append(text[last:match.start(1)])
        updated.append(str(resolved_id))
        last = match.end(1)
        changed = True

    if not changed:
        return text

    updated.append(text[last:])
    return "".join(updated)


def _legal_latin_phrase_spans(text: str) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    tokens = list(BODY_WORD_RE.finditer(text))
    max_phrase_tokens = 5
    for start_idx in range(len(tokens)):
        best_span: Optional[Tuple[int, int]] = None
        for end_idx in range(min(len(tokens) - 1, start_idx + max_phrase_tokens - 1), start_idx, -1):
            words: List[str] = []
            valid = True
            for idx in range(start_idx, end_idx + 1):
                token_text = tokens[idx].group(0)
                normalized = token_text.replace("’", "'").casefold()
                if normalized not in LATIN_WORD_LEXICON:
                    valid = False
                    break
                words.append(normalized)
                if idx > start_idx:
                    between = text[tokens[idx - 1].end() : tokens[idx].start()]
                    if between.strip():
                        valid = False
                        break
            if not valid:
                continue
            if not any(word in LATIN_CONTENT_WORDS for word in words):
                continue
            if words[0] in LATIN_FUNCTION_WORDS and words[0] not in LATIN_PHRASE_LEADING_FUNCTION_WORDS:
                continue
            if words[-1] not in LATIN_CONTENT_WORDS:
                continue
            phrase = " ".join(words)
            if phrase in LATIN_NATURALIZED_PHRASES:
                continue
            best_span = (tokens[start_idx].start(), tokens[end_idx].end())
            break
        if best_span is not None:
            spans.append(best_span)
    return _merge_spans(spans)


def _existing_italic_spans(run_segments: List[Tuple[etree._Element, int, int, str]]) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    for run, start, end, _run_text in run_segments:
        if start >= end:
            continue
        if _has_effective_italic(run.find("w:rPr", namespaces=NS)):
            spans.append((start, end))
    return _merge_spans(spans)


def _existing_italic_rpr_spans(
    run_segments: List[Tuple[etree._Element, int, int, str]],
) -> List[Tuple[int, int, etree._Element]]:
    spans: List[Tuple[int, int, etree._Element]] = []
    for run, start, end, _run_text in run_segments:
        if start >= end:
            continue
        rPr = run.find("w:rPr", namespaces=NS)
        if rPr is None or not _has_effective_italic(rPr):
            continue
        spans.append((start, end, deepcopy(rPr)))
    return spans


def _looks_like_preserved_legal_latin(text: str) -> bool:
    snippet = text.strip(" \t\n\r,;:()[]")
    if not snippet or snippet != snippet.casefold():
        return False
    spans = _legal_latin_phrase_spans(snippet)
    return len(spans) == 1 and spans[0] == (0, len(snippet))


def _preserved_legal_latin_spans(
    text: str,
    run_segments: List[Tuple[etree._Element, int, int, str]],
) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    for start, end in _existing_italic_spans(run_segments):
        if _looks_like_preserved_legal_latin(text[start:end]):
            spans.append((start, end))
    return spans


def _extend_case_span_with_sequel_suffix(text: str, span: Tuple[int, int]) -> Tuple[int, int]:
    start, end = span
    match = CASE_SEQUEL_SUFFIX_RE.match(text[end:])
    if match is None:
        return span
    return start, end + match.end(1)


def _looks_like_party_parenthetical_inner(inner: str) -> bool:
    stripped_inner = inner.strip("() \t\n\r")
    if not stripped_inner:
        return False
    if not re.search(r"[A-Z]", stripped_inner):
        return False
    if re.search(r"\d", stripped_inner):
        return False
    first_word = next(iter(re.findall(r"[A-Za-z]+", stripped_inner.casefold())), "")
    if first_word in PROCEDURAL_DESCRIPTOR_WORDS or first_word in {"case", "no", "nos"}:
        return False
    words = re.findall(r"[A-Za-z][A-Za-z&.'-]*", stripped_inner)
    if words and all(word[:1].isupper() for word in words):
        return False
    return True


def _extend_case_span_with_party_parenthetical(text: str, span: Tuple[int, int]) -> Tuple[int, int]:
    start, end = span
    match = re.match(r"(\s+\([^)]*\))(?=\s*(?:,|\[\d{4}|\(\d{4}|[.;]|$))", text[end:])
    if match is None:
        return span
    if not _looks_like_party_parenthetical_inner(match.group(1)):
        return span
    return start, end + match.end(1)


def _trim_case_span_trailing_punctuation(text: str, span: Tuple[int, int]) -> Tuple[int, int]:
    start, end = span
    while end > start and text[end - 1].isspace():
        end -= 1
    while end > start and text[end - 1] in {",", ";", ":", "."}:
        end -= 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


EU_CASE_NUMBER_PREFIX_RE = re.compile(
    r"""
    ^\s*
    (?:
        (?:Joined\s+Cases?|Case|Cases)\s+
    )?
    (?:
        [CTF]?[–-]?\d+/\d+(?:\s*P)?
        (?:
            \s*(?:,|and|to|-)\s*
            [CTF]?[–-]?\d+/\d+(?:\s*P)?
        )*
    )
    \s+
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

EU_CASE_REFERENCE_SPAN_PATTERN = re.compile(
    r"""
    (?:
        (?:Joined\s+Cases?|Case|Cases)\s+
    )?
    (?:
        [CTF]?[–-]?\d+/\d+(?:\s*[PRF])?
        (?:
            \s*(?:,|and|to|-)\s*
            [CTF]?[–-]?\d+/\d+(?:\s*[PRF])?
        )*
    )
    \s+
    (?P<name>.+?)
    (?=\s*(?:\[[0-9]{4}\]|EU:|ECLI:|[.;,]|$))
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)


def _trim_case_span_leading_eu_case_number_metadata(
    text: str, span: Tuple[int, int]
) -> Tuple[int, int]:
    start, end = span
    snippet = text[start:end]
    match = EU_CASE_NUMBER_PREFIX_RE.match(snippet)
    if match is None:
        return span

    trimmed_start = start + match.end()
    if trimmed_start >= end:
        return span

    remainder = text[trimmed_start:end]
    if not re.search(r"\bv\b", remainder):
        return span
    if not re.search(r"[A-Z]", remainder):
        return span

    return trimmed_start, end


def _eu_case_name_spans(text: str) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    for match in EU_CASE_REFERENCE_SPAN_PATTERN.finditer(text):
        snippet = match.group("name")
        if not snippet:
            continue
        collapsed = re.sub(r"\s+", " ", snippet)
        if " v " not in collapsed:
            continue
        start = match.start("name")
        end = match.end("name")
        if not re.search(r"[A-Z]", text[start:end]):
            continue
        spans.append((start, end))
    return spans


def _trim_case_span_procedural_suffix(text: str, span: Tuple[int, int]) -> Tuple[int, int]:
    start, end = span
    snippet = text[start:end]
    if "," not in snippet:
        return span

    parts = snippet.split(",")
    rebuilt = parts[0]
    consumed_len = len(parts[0])
    for part in parts[1:]:
        candidate = part.strip()
        if not candidate:
            consumed_len += len(part) + 1
            rebuilt = snippet[:consumed_len]
            continue
        words = re.findall(r"[A-Za-z]+", candidate.casefold())
        if words and any(word in PROCEDURAL_DESCRIPTOR_WORDS for word in words):
            break
        consumed_len += len(part) + 1
        rebuilt = snippet[:consumed_len]

    trimmed_end = start + len(rebuilt.rstrip(" \t\n\r,;:."))
    return start, trimmed_end


def _trim_case_span_trailing_parenthetical_metadata(
    text: str, span: Tuple[int, int]
) -> Tuple[int, int]:
    start, end = span
    while True:
        snippet = text[start:end]
        match = re.search(r"(\s+\([^)]*\))\s*$", snippet)
        if match is None:
            return start, end
        if _looks_like_party_parenthetical_inner(match.group(1)):
            return start, end
        end = start + match.start()


def _case_name_spans(
    text: str, *, case_reference_names_by_footnote: Optional[dict[int, set[str]]] = None
) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    spans.extend(_eu_case_name_spans(text))
    for pattern in (CASE_V_PATTERN, RE_CASE_PATTERN, MATTER_CASE_PATTERN, SHIP_CASE_PATTERN):
        for match in pattern.finditer(text):
            snippet = match.group(0)
            if pattern is not SHIP_CASE_PATTERN and not _looks_like_case_name_text(snippet):
                continue
            spans.append((match.start(), match.end()))
    if case_reference_names_by_footnote and "(n " in text.casefold():
        for match in SHORT_CASE_CROSSREF_PATTERN.finditer(text):
            candidate_variants = _case_reference_variants(match.group(1))
            ref_id = int(match.group(2))
            if candidate_variants.intersection(case_reference_names_by_footnote.get(ref_id, set())):
                spans.append((match.start(1), match.end(1)))
    spans = [
        _trim_case_span_trailing_punctuation(
            text,
            _trim_case_span_trailing_parenthetical_metadata(
                text,
                _trim_case_span_procedural_suffix(
                    text,
                    _trim_case_span_leading_eu_case_number_metadata(
                        text,
                        _extend_case_span_with_party_parenthetical(
                            text,
                            _extend_case_span_with_sequel_suffix(text, span),
                        ),
                    ),
                ),
            ),
        )
        for span in spans
    ]
    return _merge_spans([span for span in spans if span[0] < span[1]])


def _merge_spans(spans: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not spans:
        return []
    spans = sorted(spans)
    merged: List[Tuple[int, int]] = [spans[0]]
    for s, e in spans[1:]:
        ls, le = merged[-1]
        if s <= le:
            merged[-1] = (ls, max(le, e))
        else:
            merged.append((s, e))
    return merged


def _range_fully_covered_by_spans(
    spans: List[Tuple[int, int]],
    start: int,
    end: int,
) -> bool:
    if start >= end:
        return False
    remaining_start = start
    for span_start, span_end in _merge_spans(spans):
        if span_end <= remaining_start:
            continue
        if span_start > remaining_start:
            return False
        remaining_start = max(remaining_start, span_end)
        if remaining_start >= end:
            return True
    return False


def _position_inside_span(spans: List[Tuple[int, int]], pos: int) -> bool:
    return any(start < pos < end for start, end in spans)


def _trim_span_outer_whitespace(text: str, span: Tuple[int, int]) -> Tuple[int, int]:
    start, end = span
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _looks_like_non_case_citation_metadata(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    lower = stripped.casefold()
    if lower.startswith("(n"):
        return True
    if re.fullmatch(r"\(n\s+\d+[a-z]?\)[,;:.]*", stripped, flags=re.IGNORECASE):
        return True
    if re.match(r"^\(case\s+[^)]*\)[,;:.]*$", stripped, flags=re.IGNORECASE):
        return True
    if re.match(r"^\[\d{4}\]\s", stripped):
        return True
    if re.match(r"^\(\d{4}\)\s", stripped):
        return True
    if lower.startswith(("eu:", "ecli:", "oj ")):
        return True
    if " ecr " in lower or lower.startswith("ecr "):
        return True
    if stripped.startswith("(") and ")" not in stripped:
        return True
    if stripped.startswith("(") and ")" in stripped:
        inner = stripped[1:stripped.find(")")].strip()
        if inner and not _looks_like_party_parenthetical_inner(inner):
            return True
    return False


def _project_preserved_italic_spans(
    old_text: str,
    new_text: str,
    old_italic_spans: List[Tuple[int, int]],
    *,
    preserve_changed_text: bool = False,
) -> List[Tuple[int, int]]:
    if not old_text or not new_text or not old_italic_spans:
        return []

    projected: List[Tuple[int, int]] = []

    def is_meaningful_projected_span(start: int, end: int) -> bool:
        if start >= end:
            return False
        segment = new_text[start:end]
        alnum_len = len(re.findall(r"[A-Za-z0-9]", segment))
        if alnum_len == 0:
            return False
        if alnum_len >= 3:
            return True
        left_boundary = start == 0 or not new_text[start - 1].isalnum()
        right_boundary = end == len(new_text) or not new_text[end].isalnum()
        return alnum_len >= 2 and left_boundary and right_boundary

    matcher = difflib.SequenceMatcher(a=old_text, b=new_text, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for span_start, span_end in old_italic_spans:
                overlap_start = max(i1, span_start)
                overlap_end = min(i2, span_end)
                if overlap_start >= overlap_end:
                    continue
                offset = overlap_start - i1
                projected_start = j1 + offset
                projected_end = j1 + offset + (overlap_end - overlap_start)
                if is_meaningful_projected_span(projected_start, projected_end):
                    projected.append((projected_start, projected_end))
            continue

        if (
            tag == "replace"
            and preserve_changed_text
            and _range_fully_covered_by_spans(old_italic_spans, i1, i2)
            and j1 < j2
            and is_meaningful_projected_span(j1, j2)
            and not _looks_like_non_case_citation_metadata(new_text[j1:j2])
        ):
            projected.append((j1, j2))
            continue

        if (
            tag == "insert"
            and preserve_changed_text
            and _position_inside_span(old_italic_spans, i1)
            and j1 < j2
            and is_meaningful_projected_span(j1, j2)
            and not _looks_like_non_case_citation_metadata(new_text[j1:j2])
        ):
            projected.append((j1, j2))

    trimmed = [_trim_span_outer_whitespace(new_text, span) for span in _merge_spans(projected)]
    return _merge_spans([span for span in trimmed if span[0] < span[1]])


def _project_preserved_rpr_spans(
    old_text: str,
    new_text: str,
    old_rpr_spans: List[Tuple[int, int, etree._Element]],
    *,
    preserve_changed_text: bool = False,
) -> List[Tuple[int, int, etree._Element]]:
    projected: List[Tuple[int, int, etree._Element]] = []
    for start, end, rPr in old_rpr_spans:
        for projected_start, projected_end in _project_preserved_italic_spans(
            old_text,
            new_text,
            [(start, end)],
            preserve_changed_text=preserve_changed_text,
        ):
            projected.append((projected_start, projected_end, deepcopy(rPr)))
    return projected


def _subtract_spans(
    spans: List[Tuple[int, int]],
    blocked_spans: List[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    if not spans or not blocked_spans:
        return _merge_spans(spans)

    remaining: List[Tuple[int, int]] = []
    for start, end in _merge_spans(spans):
        fragments = [(start, end)]
        for blocked_start, blocked_end in _merge_spans(blocked_spans):
            updated: List[Tuple[int, int]] = []
            for frag_start, frag_end in fragments:
                if blocked_end <= frag_start or blocked_start >= frag_end:
                    updated.append((frag_start, frag_end))
                    continue
                if frag_start < blocked_start:
                    updated.append((frag_start, blocked_start))
                if blocked_end < frag_end:
                    updated.append((blocked_end, frag_end))
            fragments = updated
            if not fragments:
                break
        remaining.extend(fragment for fragment in fragments if fragment[0] < fragment[1])
    return _merge_spans(remaining)


def _collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_book_publication_parenthetical(text: str) -> bool:
    collapsed = _collapse_spaces(text).strip(" ,;")
    if not collapsed or not YEAR_RE.search(collapsed):
        return False
    if FULL_DATE_RE.search(collapsed):
        return False
    if YEAR_RE.fullmatch(collapsed):
        return False

    lowered = collapsed.casefold()
    if re.search(r"\b\d+(?:st|nd|rd|th)?\s+edn\b", lowered):
        return True
    if re.search(r"\beds?\b", lowered):
        return True
    if re.search(r"\btrans?\b", lowered):
        return True
    if re.search(r"\b[A-Z]{2,6}\b\s+(?:1[89]\d{2}|20\d{2}|21\d{2})\b", collapsed):
        return True

    if re.search(r"\b[A-Za-z][A-Za-z&.'-]*(?:\s+[A-Za-z][A-Za-z&.'-]*){1,6}\s+(?:1[89]\d{2}|20\d{2}|21\d{2})\b", collapsed):
        return True
    return False


def _looks_like_book_title_text(text: str) -> bool:
    collapsed = _collapse_spaces(text).strip(" ,;:.")
    if not collapsed or collapsed[0] in {"'", "’", "\"", "“", "”"}:
        return False
    if _looks_like_case_name_text(collapsed):
        return False

    words = re.findall(r"[A-Za-z][A-Za-z&.'-]*", collapsed)
    return len(words) >= 2


def _oscola_book_title_spans(text: str) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    for match in re.finditer(r"\(([^()]*)\)", text):
        if not _looks_like_book_publication_parenthetical(match.group(1)):
            continue

        prefix = text[: match.start()]
        last_comma = prefix.rfind(",")
        if last_comma == -1:
            continue

        candidate_start = last_comma + 1
        candidate_end = match.start()
        candidate = text[candidate_start:candidate_end]
        leading_ws = len(candidate) - len(candidate.lstrip())
        trailing_ws = len(candidate) - len(candidate.rstrip())
        trimmed = candidate.strip()
        if not trimmed or not _looks_like_book_title_text(trimmed):
            continue

        span_start = candidate_start + leading_ws
        span_end = candidate_end - trailing_ws
        if span_start < span_end:
            spans.append((span_start, span_end))

    return _merge_spans(spans)


def _oscola_quoted_title_spans(text: str) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    for match in re.finditer(r"[‘']([^’']+)[’']", text):
        tail = text[match.end() :]
        if re.match(r"\s*(?:\(|in\b)", tail, flags=re.IGNORECASE):
            spans.append((match.start(), match.end()))
    return _merge_spans(spans)


def _build_body_case_reference_names(_case_reference_names_by_footnote: dict[int, set[str]]) -> set[str]:
    """Legacy compatibility helper.

    Bare body short-form case-name auto-italics are no longer inferred from
    footnotes. Keep the helper for backwards-compatible imports.
    """
    return set()


def _single_word_body_short_form_candidates_from_text(text: str) -> set[str]:
    candidates: set[str] = set()

    for match in CASE_V_PATTERN.finditer(text):
        snippet = re.sub(r"\s+", " ", match.group(0)).strip()
        parties = re.split(r"\s+v\s+", snippet, maxsplit=1)
        if len(parties) != 2:
            continue
        for variant in _case_reference_variants(parties[0]):
            if not variant or " " in variant or variant in BODY_CASE_NAME_HEADWORD_BLACKLIST:
                continue
            candidates.add(variant)

    for match in SHORT_CASE_CROSSREF_PATTERN.finditer(text):
        for variant in _case_reference_variants(match.group(1)):
            if not variant or " " in variant or variant in BODY_CASE_NAME_HEADWORD_BLACKLIST:
                continue
            candidates.add(variant)

    for pattern in (RE_CASE_PATTERN, MATTER_CASE_PATTERN, SHIP_CASE_PATTERN):
        for match in pattern.finditer(text):
            for variant in _case_reference_variants(match.group(0)):
                if not variant or " " in variant or variant in BODY_CASE_NAME_HEADWORD_BLACKLIST:
                    continue
                candidates.add(variant)

    return candidates


def _build_body_short_form_sets(
    footnotes_root: Optional[etree._Element],
) -> Tuple[set[str], set[str]]:
    """Return body short-form candidates derived from actual footnote text.

    Bare body short-form italics are limited to single-word candidates and are
    only used when the caller explicitly opts in.
    """
    if footnotes_root is None:
        return set(), set()

    ambiguous: set[str] = set()
    for paragraphs in _iter_footnote_paragraphs_by_id(footnotes_root).values():
        joined = " ".join(_paragraph_text_all_runs(p) for p in paragraphs)
        ambiguous.update(_single_word_body_short_form_candidates_from_text(joined))
    return set(), ambiguous


def _body_case_name_spans(
    text: str,
    *,
    case_reference_names_by_footnote: dict[int, set[str]],
    safe_body_short_forms: Optional[set[str]] = None,
    ambiguous_body_short_forms: Optional[set[str]] = None,
    body_case_reference_names: Optional[set[str]] = None,
    enable_body_short_form_italics: bool = False,
) -> List[Tuple[int, int]]:
    # Active OSCOLA rule for body text:
    # italicize explicit case-name forms, explicit '(n X)' short-form case
    # references, OSCOLA-style book titles, and approved legal-Latin phrases.
    # Bare short-form body case names are not auto-normalized because the
    # heuristic can over-italicize company names, abbreviations, and other
    # non-case text.
    if body_case_reference_names is not None and safe_body_short_forms is None and ambiguous_body_short_forms is None:
        safe_body_short_forms = set()
        ambiguous_body_short_forms = {
            name
            for name in body_case_reference_names
            if name and " " not in name and name not in BODY_CASE_NAME_HEADWORD_BLACKLIST
        }

    safe_body_short_forms = safe_body_short_forms or set()
    ambiguous_body_short_forms = ambiguous_body_short_forms or set()

    # For body text, stay with explicit case-name forms only. Using the broader
    # generic case-name matcher here is both unnecessary and can become very
    # expensive on ordinary prose paragraphs that contain no real body case
    # citation. This keeps body normalization aligned with the stated OSCOLA
    # policy: explicit `X v Y`, `Re` / `In re`, ship-name forms, and `(n X)`
    # short-form cross-references.
    spans: List[Tuple[int, int]] = []
    spans.extend(_eu_case_name_spans(text))
    for pattern in (CASE_V_PATTERN, RE_CASE_PATTERN, MATTER_CASE_PATTERN, SHIP_CASE_PATTERN):
        for match in pattern.finditer(text):
            snippet = match.group(0)
            if pattern is not SHIP_CASE_PATTERN and not _looks_like_case_name_text(snippet):
                continue
            spans.append((match.start(), match.end()))
    if case_reference_names_by_footnote:
        for match in SHORT_CASE_CROSSREF_PATTERN.finditer(text):
            candidate_variants = _case_reference_variants(match.group(1))
            ref_id = int(match.group(2))
            if candidate_variants.intersection(case_reference_names_by_footnote.get(ref_id, set())):
                spans.append((match.start(1), match.end(1)))
    spans = [
        _trim_case_span_trailing_punctuation(
            text,
            _trim_case_span_procedural_suffix(
                text,
                _extend_case_span_with_party_parenthetical(text, _extend_case_span_with_sequel_suffix(text, span)),
            ),
        )
        for span in spans
    ]
    spans.extend(_oscola_book_title_spans(text))
    spans.extend(_legal_latin_phrase_spans(text))
    return _subtract_spans(spans, _oscola_quoted_title_spans(text))


def _bibliography_case_name_spans(text: str) -> List[Tuple[int, int]]:
    if not _looks_like_case_name_text(text):
        return []
    spans = _case_name_spans(text)
    if not spans:
        return []
    leading_spans = [span for span in spans if span[0] == 0]
    return leading_spans or spans[:1]


def _set_or_insert_space_prefix(t_node: etree._Element) -> None:
    cur = t_node.text or ""
    if cur.startswith((" ", "\t", "\n")):
        return
    t_node.text = " " + cur
    t_node.set(f"{{{XML_NS}}}space", "preserve")


def _remove_leading_space_prefix(t_node: etree._Element) -> None:
    cur = t_node.text or ""
    trimmed = cur.lstrip(" \t\n")
    t_node.text = trimmed
    if trimmed != cur and not trimmed.startswith((" ", "\t", "\n")):
        space_attr = f"{{{XML_NS}}}space"
        if t_node.get(space_attr) == "preserve":
            del t_node.attrib[space_attr]


def _ensure_space_after_reference_marker(p: etree._Element) -> bool:
    runs = p.xpath("./w:r", namespaces=NS)
    marker_idx = next((idx for idx, run in enumerate(runs) if _is_reference_run(run)), None)
    if marker_idx is None:
        return False

    for run in runs[marker_idx + 1 :]:
        # If there is an explicit tab immediately after marker, spacing is already clear.
        if run.find("w:tab", namespaces=NS) is not None:
            return False

        t_nodes = run.xpath("./w:t", namespaces=NS)
        if not t_nodes:
            continue

        first_text = next((n for n in t_nodes if (n.text or "") != ""), None)
        if first_text is None:
            continue

        before = first_text.text or ""
        if before.startswith((" ", "\t", "\n")):
            return False

        _set_or_insert_space_prefix(first_text)
        return True

    return False


def _first_non_marker_textual_run(p: etree._Element) -> Optional[etree._Element]:
    marker_seen = False
    for run in p.xpath("./w:r", namespaces=NS):
        if _is_reference_run(run):
            marker_seen = True
            continue
        if not marker_seen:
            continue
        if _run_contains_textual_content(run):
            return run
    return None


def _normalize_footnote_marker_spacing_from_template(
    p: etree._Element,
    template_p: etree._Element,
) -> int:
    template_run = _first_non_marker_textual_run(template_p)
    current_run = _first_non_marker_textual_run(p)
    if template_run is None or current_run is None:
        return 0

    template_t = next((node for node in template_run.xpath("./w:t", namespaces=NS) if (node.text or "") != ""), None)
    current_t = next((node for node in current_run.xpath("./w:t", namespaces=NS) if (node.text or "") != ""), None)
    if template_t is None or current_t is None:
        return 0

    template_has_space = (template_t.text or "").startswith((" ", "\t", "\n"))
    current_has_space = (current_t.text or "").startswith((" ", "\t", "\n"))
    if template_has_space == current_has_space:
        return 0

    if template_has_space:
        _set_or_insert_space_prefix(current_t)
    else:
        _remove_leading_space_prefix(current_t)
    return 1


def _template_paragraph_for_footnote_index(
    orig_by_id: dict[int, List[etree._Element]],
    orig_nodes_by_id: dict[int, etree._Element],
    fid: int,
    para_idx: int,
) -> Optional[etree._Element]:
    existing = orig_by_id.get(fid)
    if existing and para_idx < len(existing):
        return existing[para_idx]

    template_paras = _template_paragraphs_for_new_footnote(orig_nodes_by_id, fid)
    if not template_paras:
        return None
    return template_paras[min(para_idx, len(template_paras) - 1)]


FOOTNOTE_LOCAL_OVERRIDE_TAGS = {
    "b",
    "bCs",
    "highlight",
    "i",
    "iCs",
    "u",
    "uCs",
    "strike",
    "dstrike",
    "caps",
    "smallCaps",
}


def _strip_markdown_inline_artifacts(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    return text


def _sanitize_footnote_plain_text(text: str) -> str:
    return _strip_markdown_inline_artifacts(text or "")


def _normalized_template_text_run_rpr(template_run: Optional[etree._Element]) -> Optional[etree._Element]:
    if template_run is None:
        return None
    template_rPr = template_run.find("w:rPr", namespaces=NS)
    if template_rPr is None:
        return None
    normalized = deepcopy(template_rPr)
    style_node = normalized.find("w:rStyle", namespaces=NS)
    if style_node is not None and (style_node.get(w_tag("val")) or "").strip() == "FootnoteReference":
        normalized.remove(style_node)
    for local_name in FOOTNOTE_LOCAL_OVERRIDE_TAGS:
        for node in normalized.findall(f"w:{local_name}", namespaces=NS):
            normalized.remove(node)
    return normalized if len(normalized) else None


def _merge_missing_text_run_style_from_template(
    current_rPr: Optional[etree._Element],
    template_rPr: Optional[etree._Element],
) -> Optional[etree._Element]:
    if current_rPr is None and template_rPr is None:
        return None
    merged = deepcopy(current_rPr) if current_rPr is not None else etree.Element(w_tag("rPr"))
    if template_rPr is None:
        return merged
    for template_child in template_rPr:
        local_name = etree.QName(template_child).localname
        if local_name in FOOTNOTE_LOCAL_OVERRIDE_TAGS:
            continue
        if local_name == "rStyle" and (template_child.get(w_tag("val")) or "").strip() == "FootnoteReference":
            continue
        if merged.find(f"w:{local_name}", namespaces=NS) is not None:
            continue
        merged.append(deepcopy(template_child))
    return merged if len(merged) else None


def _normalize_text_run_style_from_template(
    run: etree._Element,
    template_run: Optional[etree._Element],
) -> bool:
    current_rPr = run.find("w:rPr", namespaces=NS)
    template_rPr = _normalized_template_text_run_rpr(template_run)

    merged_rPr = deepcopy(current_rPr) if current_rPr is not None else etree.Element(w_tag("rPr"))
    changed = False
    footnote_ref_style = merged_rPr.find("w:rStyle", namespaces=NS)
    if footnote_ref_style is not None and (footnote_ref_style.get(w_tag("val")) or "").strip() == "FootnoteReference":
        merged_rPr.remove(footnote_ref_style)
        changed = True

    merged_with_template = _merge_missing_text_run_style_from_template(merged_rPr if len(merged_rPr) else None, template_rPr)
    merged_rPr = deepcopy(merged_with_template) if merged_with_template is not None else etree.Element(w_tag("rPr"))
    changed = changed or (
        etree.tostring(current_rPr, encoding="unicode") if current_rPr is not None else ""
    ) != (etree.tostring(merged_rPr, encoding="unicode") if len(merged_rPr) else "")

    current_xml = etree.tostring(current_rPr, encoding="unicode") if current_rPr is not None else ""
    merged_xml = etree.tostring(merged_rPr, encoding="unicode") if len(merged_rPr) else ""
    if current_xml == merged_xml:
        return False

    visible_before = _visible_formatting_signature(current_rPr)
    visible_after = _visible_formatting_signature(merged_rPr)
    _replace_run_rpr(run, merged_rPr if len(merged_rPr) else None)
    if visible_before != visible_after:
        _mark_run_formatting_change(run)
    return True


def _merge_missing_ppr_children_from_template(
    current_pPr: etree._Element,
    template_pPr: etree._Element,
) -> etree._Element:
    merged_pPr = deepcopy(current_pPr)
    for template_child in template_pPr:
        local_name = etree.QName(template_child).localname
        if local_name == "rPr":
            # Existing footnote paragraph typography is authoritative. Never
            # backfill paragraph-level font/size/style defaults from the
            # template into a user footnote that already has paragraph props.
            continue
        if merged_pPr.find(f"w:{local_name}", namespaces=NS) is not None:
            continue
        merged_pPr.append(deepcopy(template_child))
    return merged_pPr


def _normalize_footnote_paragraph_style_from_template(
    p: etree._Element, template_p: etree._Element
) -> int:
    changed = 0

    template_pPr = template_p.find("w:pPr", namespaces=NS)
    current_pPr = p.find("w:pPr", namespaces=NS)
    merged_pPr: Optional[etree._Element]
    if template_pPr is None:
        merged_pPr = current_pPr
    elif current_pPr is None:
        merged_pPr = deepcopy(template_pPr)
    else:
        merged_pPr = _merge_missing_ppr_children_from_template(current_pPr, template_pPr)

    if merged_pPr is not None:
        paragraph_rPr = merged_pPr.find("w:rPr", namespaces=NS)
        if paragraph_rPr is not None:
            paragraph_ref_style = paragraph_rPr.find("w:rStyle", namespaces=NS)
            if paragraph_ref_style is not None and (
                paragraph_ref_style.get(w_tag("val")) or ""
            ).strip() == "FootnoteReference":
                paragraph_rPr.remove(paragraph_ref_style)
            if len(paragraph_rPr) == 0:
                merged_pPr.remove(paragraph_rPr)

    current_pPr_xml = etree.tostring(current_pPr, encoding="unicode") if current_pPr is not None else ""
    merged_pPr_xml = etree.tostring(merged_pPr, encoding="unicode") if merged_pPr is not None else ""
    if current_pPr_xml != merged_pPr_xml:
        if current_pPr is not None:
            p.remove(current_pPr)
        if merged_pPr is not None:
            p.insert(0, merged_pPr)
        changed += 1

    template_marker_run = next(
        (run for run in template_p.xpath("./w:r", namespaces=NS) if _is_reference_run(run)),
        None,
    )
    template_marker_rPr = template_marker_run.find("w:rPr", namespaces=NS) if template_marker_run is not None else None
    template_text_run = _first_non_marker_textual_run(template_p)
    for run in p.xpath("./w:r", namespaces=NS):
        if _is_reference_run(run):
            if template_marker_rPr is None:
                continue
            current_rPr = run.find("w:rPr", namespaces=NS)
            current_xml = etree.tostring(current_rPr, encoding="unicode") if current_rPr is not None else ""
            template_xml = etree.tostring(template_marker_rPr, encoding="unicode")
            if current_xml != template_xml:
                visible_before = _visible_formatting_signature(current_rPr)
                visible_after = _visible_formatting_signature(template_marker_rPr)
                _replace_run_rpr(run, template_marker_rPr)
                if visible_before != visible_after:
                    _mark_run_formatting_change(run)
                changed += 1
            continue

        if not _run_contains_textual_content(run):
            continue

        if _normalize_text_run_style_from_template(run, template_text_run):
            changed += 1

    return changed


def _normalize_footnote_styles_from_original(
    original_root: etree._Element,
    current_root: etree._Element,
) -> int:
    changed = 0
    orig_by_id = _iter_footnote_paragraphs_by_id(original_root)
    orig_nodes_by_id = _iter_footnote_nodes_by_id(original_root)
    current_by_id = _iter_footnote_paragraphs_by_id(current_root)

    for fid, paragraphs in sorted(current_by_id.items()):
        for para_idx, paragraph in enumerate(paragraphs):
            template_p = _template_paragraph_for_footnote_index(orig_by_id, orig_nodes_by_id, fid, para_idx)
            if template_p is None:
                continue
            changed += _normalize_footnote_paragraph_style_from_template(paragraph, template_p)
            changed += _normalize_footnote_marker_spacing_from_template(paragraph, template_p)

    return changed


def _normalize_body_footnote_reference_styles_for_paragraph(
    paragraph: etree._Element,
    template_paragraph: Optional[etree._Element],
) -> int:
    current_runs = paragraph.xpath("./w:r[w:footnoteReference]", namespaces=NS)
    if not current_runs:
        return 0

    template_runs = (
        template_paragraph.xpath("./w:r[w:footnoteReference]", namespaces=NS)
        if template_paragraph is not None
        else []
    )
    changed = 0
    for idx, run in enumerate(current_runs):
        template_run = template_runs[idx] if idx < len(template_runs) else (template_runs[-1] if template_runs else None)
        template_rPr = (
            deepcopy(template_run.find("w:rPr", namespaces=NS))
            if template_run is not None and template_run.find("w:rPr", namespaces=NS) is not None
            else _canonical_body_footnote_reference_rpr()
        )
        current_rPr = run.find("w:rPr", namespaces=NS)
        current_xml = etree.tostring(current_rPr, encoding="unicode") if current_rPr is not None else ""
        template_xml = etree.tostring(template_rPr, encoding="unicode")
        if current_xml == template_xml:
            continue
        visible_before = _visible_formatting_signature(current_rPr)
        visible_after = _visible_formatting_signature(template_rPr)
        _replace_run_rpr(run, template_rPr)
        if visible_before != visible_after:
            _mark_run_formatting_change(run)
        changed += 1
    return changed


def _normalize_body_footnote_reference_styles_from_original(
    original_root: etree._Element,
    current_root: etree._Element,
) -> int:
    changed = 0
    original_paragraphs = _iter_body_paragraphs(original_root)
    current_paragraphs = _iter_body_paragraphs(current_root)
    for idx, paragraph in enumerate(current_paragraphs):
        template_paragraph = original_paragraphs[idx] if idx < len(original_paragraphs) else None
        changed += _normalize_body_footnote_reference_styles_for_paragraph(paragraph, template_paragraph)
    return changed


def _split_run_with_italics(
    p: etree._Element,
    run: etree._Element,
    local_spans: List[Tuple[int, int]],
    *,
    additive_only: bool = False,
) -> int:
    # Only split simple text runs; fallback callers can italicize whole runs.
    children = [c for c in list(run) if c.tag != w_tag("rPr")]
    if len(children) != 1 or children[0].tag != w_tag("t"):
        return 0

    t_node = children[0]
    text = t_node.text or ""
    if not text:
        return 0

    spans = _merge_spans([(max(0, s), min(len(text), e)) for s, e in local_spans if s < e])
    if not spans:
        return 0

    parts: List[Tuple[str, bool]] = []
    cur = 0
    for s, e in spans:
        if cur < s:
            parts.append((text[cur:s], False))
        parts.append((text[s:e], True))
        cur = e
    if cur < len(text):
        parts.append((text[cur:], False))

    # If entire run is case name, avoid splitting and just set italic.
    if len(parts) == 1 and parts[0][1]:
        rPr = run.find("w:rPr", namespaces=NS)
        if rPr is None:
            rPr = etree.Element(w_tag("rPr"))
            run.insert(0, rPr)
        already_italic = _has_effective_italic(rPr)
        if not already_italic:
            _set_italic(rPr)
            return 1 + _mark_run_formatting_change(run)
        return 0

    insert_at = list(p).index(run)
    p.remove(run)
    changed = 0

    for piece_text, is_case in parts:
        if piece_text == "":
            continue
        nr = _clone_run_with_rPr(run)
        rPr = nr.find("w:rPr", namespaces=NS)
        if rPr is None:
            rPr = etree.Element(w_tag("rPr"))
            nr.insert(0, rPr)
        was_italic = _has_effective_italic(rPr)
        if is_case:
            if not was_italic:
                _set_italic(rPr)
                changed += 1 + _mark_run_formatting_change(nr)
        else:
            if was_italic and not additive_only:
                cleared = _clear_italic(rPr)
                changed += cleared
                if cleared:
                    changed += _mark_run_formatting_change(nr)
        nr.append(_t(piece_text))
        p.insert(insert_at, nr)
        insert_at += 1

    return changed


def _split_run_with_cleared_italics(
    p: etree._Element,
    run: etree._Element,
    local_spans: List[Tuple[int, int]],
) -> int:
    children = [c for c in list(run) if c.tag != w_tag("rPr")]
    if len(children) != 1 or children[0].tag != w_tag("t"):
        return 0

    t_node = children[0]
    text = t_node.text or ""
    if not text:
        return 0

    spans = _merge_spans([(max(0, s), min(len(text), e)) for s, e in local_spans if s < e])
    if not spans:
        return 0

    parts: List[Tuple[str, bool]] = []
    cur = 0
    for s, e in spans:
        if cur < s:
            parts.append((text[cur:s], False))
        parts.append((text[s:e], True))
        cur = e
    if cur < len(text):
        parts.append((text[cur:], False))

    if len(parts) == 1 and parts[0][1]:
        rPr = run.find("w:rPr", namespaces=NS)
        if rPr is None or not _has_effective_italic(rPr):
            return 0
        cleared = _clear_italic(rPr)
        if not cleared:
            return 0
        return cleared + _mark_run_formatting_change(run)

    insert_at = list(p).index(run)
    p.remove(run)
    changed = 0

    for piece_text, should_clear in parts:
        if piece_text == "":
            continue
        nr = _clone_run_with_rPr(run)
        rPr = nr.find("w:rPr", namespaces=NS)
        if should_clear and rPr is not None and _has_effective_italic(rPr):
            cleared = _clear_italic(rPr)
            changed += cleared
            if cleared:
                changed += _mark_run_formatting_change(nr)
        nr.append(_t(piece_text))
        p.insert(insert_at, nr)
        insert_at += 1

    return changed


def _paragraph_text_run_segments(
    p: etree._Element,
    *,
    after_reference_marker: bool = False,
) -> List[Tuple[etree._Element, int, int, str]]:
    marker_seen = not after_reference_marker
    run_segments: List[Tuple[etree._Element, int, int, str]] = []
    cursor = 0

    for run in p.xpath("./w:r", namespaces=NS):
        if _is_reference_run(run):
            marker_seen = True
            continue
        if not marker_seen:
            continue

        run_text = "".join(run.xpath("./w:t/text()", namespaces=NS))
        if run_text == "":
            continue

        start, end = cursor, cursor + len(run_text)
        run_segments.append((run, start, end, run_text))
        cursor = end

    return run_segments


def _apply_italic_spans_to_runs(
    p: etree._Element,
    spans: List[Tuple[int, int]],
    *,
    after_reference_marker: bool = False,
    additive_only: bool = False,
) -> int:
    if not spans:
        return 0

    changed = 0
    run_segments = _paragraph_text_run_segments(p, after_reference_marker=after_reference_marker)
    for run, start, end, _run_text in reversed(run_segments):
        local_spans: List[Tuple[int, int]] = []
        for span_start, span_end in spans:
            if span_end <= start or span_start >= end:
                continue
            local_spans.append((max(span_start, start) - start, min(span_end, end) - start))

        if local_spans:
            rPr = run.find("w:rPr", namespaces=NS)
            if additive_only and rPr is not None and _has_effective_italic(rPr):
                continue

            split_changed = _split_run_with_italics(
                p,
                run,
                local_spans,
                additive_only=additive_only,
            )
            if split_changed:
                changed += split_changed
                continue

            if rPr is None:
                rPr = etree.Element(w_tag("rPr"))
                run.insert(0, rPr)
            already_italic = _has_effective_italic(rPr)
            if not already_italic:
                _set_italic(rPr)
                changed += 1 + _mark_run_formatting_change(run)
            continue

        if additive_only:
            continue

        rPr = run.find("w:rPr", namespaces=NS)
        if rPr is not None and _has_effective_italic(rPr):
            cleared = _clear_italic(rPr)
            changed += cleared
            if cleared:
                changed += _mark_run_formatting_change(run)

    return changed


def _clear_italic_spans_to_runs(
    p: etree._Element,
    spans: List[Tuple[int, int]],
    *,
    after_reference_marker: bool = False,
) -> int:
    if not spans:
        return 0

    changed = 0
    run_segments = _paragraph_text_run_segments(p, after_reference_marker=after_reference_marker)
    for run, start, end, _run_text in reversed(run_segments):
        local_spans: List[Tuple[int, int]] = []
        for span_start, span_end in spans:
            if span_end <= start or span_start >= end:
                continue
            local_spans.append((max(span_start, start) - start, min(span_end, end) - start))
        if not local_spans:
            continue

        split_changed = _split_run_with_cleared_italics(p, run, local_spans)
        if split_changed:
            changed += split_changed
            continue

        rPr = run.find("w:rPr", namespaces=NS)
        if rPr is None or not _has_effective_italic(rPr):
            continue
        cleared = _clear_italic(rPr)
        changed += cleared
        if cleared:
            changed += _mark_run_formatting_change(run)

    return changed


def _merge_preserved_span_rpr(
    current_rPr: Optional[etree._Element],
    preserved_rPr: etree._Element,
) -> etree._Element:
    merged_rPr = deepcopy(current_rPr) if current_rPr is not None else etree.Element(w_tag("rPr"))
    for preserved_child in preserved_rPr:
        local_name = etree.QName(preserved_child).localname
        if local_name in {"b", "bCs", "highlight"}:
            if merged_rPr.find(f"w:{local_name}", namespaces=NS) is None:
                merged_rPr.append(deepcopy(preserved_child))
            continue
        for existing in merged_rPr.findall(f"w:{local_name}", namespaces=NS):
            merged_rPr.remove(existing)
        merged_rPr.append(deepcopy(preserved_child))
    style_node = merged_rPr.find("w:rStyle", namespaces=NS)
    if style_node is not None and (style_node.get(w_tag("val")) or "").strip() == "FootnoteReference":
        merged_rPr.remove(style_node)
    return merged_rPr


def _apply_rpr_spans_to_runs(
    p: etree._Element,
    spans: List[Tuple[int, int, etree._Element]],
    *,
    after_reference_marker: bool = False,
) -> int:
    if not spans:
        return 0

    changed = 0
    run_segments = _paragraph_text_run_segments(p, after_reference_marker=after_reference_marker)
    for run, start, end, _run_text in reversed(run_segments):
        local_spans: List[Tuple[int, int, etree._Element]] = []
        for span_start, span_end, span_rPr in spans:
            if span_end <= start or span_start >= end:
                continue
            local_spans.append((max(span_start, start) - start, min(span_end, end) - start, span_rPr))
        if not local_spans:
            continue

        children = [c for c in list(run) if c.tag != w_tag("rPr")]
        if len(children) != 1 or children[0].tag != w_tag("t"):
            current_rPr = run.find("w:rPr", namespaces=NS)
            merged_rPr = _merge_preserved_span_rpr(current_rPr, local_spans[0][2])
            current_xml = etree.tostring(current_rPr, encoding="unicode") if current_rPr is not None else ""
            merged_xml = etree.tostring(merged_rPr, encoding="unicode")
            if current_xml == merged_xml:
                continue
            visible_before = _visible_formatting_signature(current_rPr)
            visible_after = _visible_formatting_signature(merged_rPr)
            _replace_run_rpr(run, merged_rPr)
            if visible_before != visible_after:
                _mark_run_formatting_change(run)
            changed += 1
            continue

        text = children[0].text or ""
        boundaries = {0, len(text)}
        style_by_piece: list[Tuple[int, int, etree._Element]] = []
        for span_start, span_end, span_rPr in local_spans:
            boundaries.add(max(0, span_start))
            boundaries.add(min(len(text), span_end))
            style_by_piece.append((max(0, span_start), min(len(text), span_end), span_rPr))
        ordered_bounds = sorted(boundaries)
        pieces: List[Tuple[str, Optional[etree._Element]]] = []
        for piece_start, piece_end in zip(ordered_bounds, ordered_bounds[1:]):
            if piece_start >= piece_end:
                continue
            piece_text = text[piece_start:piece_end]
            piece_rPr = next(
                (
                    span_rPr
                    for span_start, span_end, span_rPr in style_by_piece
                    if span_start <= piece_start and piece_end <= span_end
                ),
                None,
            )
            pieces.append((piece_text, piece_rPr))

        insert_at = list(p).index(run)
        p.remove(run)
        for piece_text, piece_rPr in pieces:
            nr = _clone_run_with_rPr(run)
            current_rPr = nr.find("w:rPr", namespaces=NS)
            if piece_rPr is not None:
                merged_rPr = _merge_preserved_span_rpr(current_rPr, piece_rPr)
                _replace_run_rpr(nr, merged_rPr)
                changed += 1
            nr.append(_t(piece_text))
            p.insert(insert_at, nr)
            insert_at += 1

    return changed


def _italicize_case_name_runs_in_footnote(
    p: etree._Element, *, case_reference_names_by_footnote: Optional[dict[int, set[str]]] = None
) -> int:
    run_segments = _paragraph_text_run_segments(p, after_reference_marker=True)
    full_text = "".join(seg[3] for seg in run_segments)
    spans = _subtract_spans(
        _merge_spans(
            _case_name_spans(full_text, case_reference_names_by_footnote=case_reference_names_by_footnote)
            + _oscola_book_title_spans(full_text)
            + _legal_latin_phrase_spans(full_text)
            + _preserved_legal_latin_spans(full_text, run_segments)
        ),
        _oscola_quoted_title_spans(full_text),
    )
    if not spans:
        return 0

    # In footnotes, italic correction is additive only: preserve the user's
    # existing italics and add missing OSCOLA italics for case names/legal
    # Latin where needed.
    changed = _apply_italic_spans_to_runs(
        p,
        spans,
        after_reference_marker=True,
        additive_only=True,
    )
    return changed


def _normalize_case_italics_in_footnotes(root: etree._Element) -> int:
    changed = 0
    case_reference_names_by_footnote = _build_footnote_case_reference_map(root)
    for p in root.xpath("/w:footnotes/w:footnote[@w:id>=1]/w:p", namespaces=NS):
        changed += _italicize_case_name_runs_in_footnote(
            p, case_reference_names_by_footnote=case_reference_names_by_footnote
        )
    return changed


def _normalize_body_italics(
    document_root: etree._Element,
    footnotes_root: Optional[etree._Element],
    *,
    enable_body_short_form_italics: bool = False,
) -> int:
    del enable_body_short_form_italics
    changed = 0
    case_reference_names_by_footnote = (
        _build_footnote_case_reference_map(footnotes_root) if footnotes_root is not None else {}
    )

    in_bibliography = False
    in_table_of_cases = False
    for p in _iter_body_paragraphs(document_root):
        paragraph_text = _paragraph_text_all_runs(p)
        normalized_heading = _normalize_text(paragraph_text)
        if normalized_heading in TABLE_OF_CASES_HEADINGS:
            in_table_of_cases = True
            in_bibliography = False
            continue
        if normalized_heading in BIBLIOGRAPHY_HEADINGS:
            in_bibliography = True
            in_table_of_cases = False
        elif normalized_heading in NON_BIBLIOGRAPHY_SECTION_HEADINGS:
            in_bibliography = False
            in_table_of_cases = False
        elif in_table_of_cases and not _looks_like_table_of_cases_entry(paragraph_text):
            in_table_of_cases = False

        if in_table_of_cases:
            # OSCOLA 4th edn: Table of Cases entries are kept in roman text.
            # Preserve any user-applied italics by leaving those entries alone.
            continue

        run_segments: List[Tuple[etree._Element, int, int, str]] = []
        cursor = 0
        for run in p.xpath("./w:r", namespaces=NS):
            if run.find("w:footnoteReference", namespaces=NS) is not None:
                continue
            run_text = "".join(run.xpath("./w:t/text()", namespaces=NS))
            if run_text == "":
                continue
            start, end = cursor, cursor + len(run_text)
            run_segments.append((run, start, end, run_text))
            cursor = end

        full_text = "".join(seg[3] for seg in run_segments)
        if not in_bibliography:
            quick_text = full_text.casefold()
            has_existing_italics = any(
                _has_effective_italic(run.find("w:rPr", namespaces=NS)) for run, _start, _end, _text in run_segments
            )
            quick_case_or_latin_cues = (
                " v " in quick_text
                or "(n " in quick_text
                or quick_text.startswith("re ")
                or " in re " in quick_text
                or " in the matter of " in quick_text
                or " prima facie" in quick_text
                or " inter alia" in quick_text
                or " forum non conveniens" in quick_text
                or " lex " in quick_text
                or " mens rea" in quick_text
                or " terra nullius" in quick_text
                or " mutatis mutandis" in quick_text
            )
            if not has_existing_italics and not quick_case_or_latin_cues:
                continue
        preserved_latin_spans = _preserved_legal_latin_spans(full_text, run_segments)
        spans = (
            _subtract_spans(
                _merge_spans(
                    _bibliography_case_name_spans(full_text)
                    + _oscola_book_title_spans(full_text)
                    + _legal_latin_phrase_spans(full_text)
                    + preserved_latin_spans
                ),
                _oscola_quoted_title_spans(full_text),
            )
            if in_bibliography
            else _subtract_spans(
                _merge_spans(
                    _body_case_name_spans(
                        full_text,
                        case_reference_names_by_footnote=case_reference_names_by_footnote,
                    )
                    + preserved_latin_spans
                )
                ,
                _oscola_quoted_title_spans(full_text),
            )
        )

        for run, start, end, _run_text in reversed(run_segments):
            local_spans: List[Tuple[int, int]] = []
            for span_start, span_end in spans:
                if span_end <= start or span_start >= end:
                    continue
                local_spans.append((max(span_start, start) - start, min(span_end, end) - start))
            if local_spans:
                rPr = run.find("w:rPr", namespaces=NS)
                if rPr is not None and _has_effective_italic(rPr):
                    # Body-text normalization is additive only: never flatten
                    # user italics just because OSCOLA does not require them.
                    continue

                split_changed = _split_run_with_italics(p, run, local_spans)
                if split_changed:
                    changed += split_changed
                    continue

                rPr = run.find("w:rPr", namespaces=NS)
                if rPr is None:
                    rPr = etree.Element(w_tag("rPr"))
                    run.insert(0, rPr)
                already_italic = _has_effective_italic(rPr)
                if not already_italic:
                    _set_italic(rPr)
                    changed += 1 + _mark_run_formatting_change(run)
                continue
    return changed


def _normalize_bibliography_bold(document_root: etree._Element) -> int:
    changed = 0
    in_bibliography = False

    for p in _iter_body_paragraphs(document_root):
        paragraph_text = _paragraph_text_all_runs(p)
        normalized_heading = _normalize_text(paragraph_text)

        if normalized_heading in BIBLIOGRAPHY_HEADINGS:
            in_bibliography = True
            is_heading = True
        elif in_bibliography and normalized_heading in BIBLIOGRAPHY_SECTION_HEADINGS:
            is_heading = True
        elif in_bibliography and normalized_heading in NON_BIBLIOGRAPHY_SECTION_HEADINGS and normalized_heading not in BIBLIOGRAPHY_SECTION_HEADINGS:
            in_bibliography = False
            is_heading = False
        else:
            is_heading = False

        if not in_bibliography:
            continue

        for run in p.xpath("./w:r", namespaces=NS):
            if run.find("w:footnoteReference", namespaces=NS) is not None:
                continue
            if not "".join(run.xpath("./w:t/text()", namespaces=NS)).strip():
                continue
            rPr = run.find("w:rPr", namespaces=NS)
            if rPr is None:
                rPr = etree.Element(w_tag("rPr"))
                run.insert(0, rPr)
            if is_heading:
                before = etree.tostring(rPr, encoding="unicode")
                _set_bold(rPr)
                after = etree.tostring(rPr, encoding="unicode")
                if before != after:
                    changed += 1 + _mark_run_formatting_change(run)
            else:
                cleared = _clear_bold(rPr)
                if cleared:
                    changed += cleared + _mark_run_formatting_change(run)

    return changed


def _normalize_body_footnote_reference_positions(
    document_root: etree._Element,
    footnotes_root: Optional[etree._Element],
) -> int:
    if footnotes_root is None:
        return 0

    case_reference_names_by_footnote = _build_footnote_case_reference_map(footnotes_root)
    changed = 0

    for paragraph in _iter_body_paragraphs(document_root):
        paragraph_text = _paragraph_text_all_runs(paragraph)
        if not paragraph_text.strip():
            continue

        for ref_run, pos, ref_id in _footnote_reference_run_nodes_with_positions(paragraph):
            try:
                fid = int(ref_id)
            except ValueError:
                continue

            target_pos = _body_reference_target_pos_for_case_name(
                paragraph_text,
                pos,
                fid,
                case_reference_names_by_footnote=case_reference_names_by_footnote,
            )
            if target_pos is None or ref_run.getparent() is not paragraph:
                continue

            paragraph.remove(ref_run)
            insert_at = _reference_insert_index_for_text_pos(paragraph, target_pos)
            paragraph.insert(insert_at, ref_run)
            changed += 1

        changed += _dedupe_adjacent_body_footnote_reference_runs(paragraph)

    return changed


def _sync_footnotes_from_amended(

    orig_footnotes_root: etree._Element, amend_footnotes_root: etree._Element, *, markup: bool
) -> Tuple[int, int, int]:
    footnote_search_text_by_id = _build_footnote_search_text_map(amend_footnotes_root)
    case_reference_names_by_footnote = _build_footnote_case_reference_map(amend_footnotes_root)
    orig_by_id = _iter_footnote_paragraphs_by_id(orig_footnotes_root)
    amend_by_id = _iter_footnote_paragraphs_by_id(amend_footnotes_root)
    orig_nodes_by_id = _iter_footnote_nodes_by_id(orig_footnotes_root)

    changed = 0
    skipped_complex = 0
    skipped_structure = 0
    affected_ids: set[int] = set()

    for fid in sorted(set(orig_by_id).intersection(amend_by_id)):
        orig_paras = orig_by_id[fid]
        amend_paras = amend_by_id[fid]
        if len(orig_paras) != len(amend_paras):
            # Preserve original layout when a footnote's paragraph structure diverges.
            skipped_structure += 1
            continue

        for p_orig, p_amend in zip(orig_paras, amend_paras):
            original_refs = _collect_reference_runs(p_orig)
            new_text = _rewrite_cross_reference_numbers_in_text(
                _sanitize_footnote_plain_text(_paragraph_text_all_runs(p_amend)),
                footnote_search_text_by_id=footnote_search_text_by_id,
                case_reference_names_by_footnote=case_reference_names_by_footnote,
                current_footnote_id=fid,
            )
            if len(orig_paras) == 1 and len(amend_paras) == 1:
                new_text = _normalize_new_footnote_citation_text(
                    new_text,
                    footnotes_root=orig_footnotes_root,
                    current_footnote_id=fid,
                )
            if _paragraph_is_simple(p_orig):
                if _apply_diff_to_paragraph(p_orig, new_text, markup=markup):
                    _restore_reference_runs_if_missing(p_orig, original_refs)
                    _ensure_reference_marker_first(p_orig)
                    _ensure_space_after_reference_marker(p_orig)
                    _italicize_case_name_runs_in_footnote(p_orig)
                    changed += 1
                    affected_ids.add(fid)
            else:
                if _apply_full_replace_to_paragraph(p_orig, new_text, markup=markup):
                    _restore_reference_runs_if_missing(p_orig, original_refs)
                    _ensure_reference_marker_first(p_orig)
                    _ensure_space_after_reference_marker(p_orig)
                    _italicize_case_name_runs_in_footnote(p_orig)
                    changed += 1
                    affected_ids.add(fid)
                else:
                    skipped_complex += 1

    if orig_nodes_by_id:
        for fid in sorted(set(amend_by_id) - set(orig_by_id)):
            template_paras = _template_paragraphs_for_new_footnote(orig_nodes_by_id, fid)
            new_node = _build_new_footnote_from_template(
                fid,
                amend_by_id[fid],
                template_paras,
                markup=markup,
                footnote_search_text_by_id=footnote_search_text_by_id,
                case_reference_names_by_footnote=case_reference_names_by_footnote,
                existing_footnotes_root=orig_footnotes_root,
            )
            orig_footnotes_root.append(new_node)
            changed += len(amend_by_id[fid])
            affected_ids.add(fid)

    if affected_ids:
        downstream_changed_ids = _normalize_downstream_footnote_citations(
            orig_footnotes_root,
            start_footnote_id=min(affected_ids),
        )
        changed += len(downstream_changed_ids)

    return changed, skipped_complex, skipped_structure


def refine_from_amended(
    original_docx: Path,
    amended_docx: Path,
    out_docx: Path,
    *,
    markup: bool = True,
    sync_footnotes: bool = True,
    enable_body_short_form_italics: bool = False,
) -> Tuple[int, int]:
    del enable_body_short_form_italics
    _require_markup_enabled(markup)
    part = "word/document.xml"
    footnotes_part = "word/footnotes.xml"
    orig_root = _load_docx_xml(original_docx, part)
    orig_root_template = _load_docx_xml(original_docx, part)
    amend_root = _load_docx_xml(amended_docx, part)
    amend_footnotes = _load_docx_xml_if_exists(amended_docx, footnotes_part)
    footnote_search_text_by_id = (
        _build_footnote_search_text_map(amend_footnotes) if amend_footnotes is not None else {}
    )
    case_reference_names_by_footnote = (
        _build_footnote_case_reference_map(amend_footnotes) if amend_footnotes is not None else {}
    )

    orig_paras = _iter_body_paragraphs(orig_root)
    amend_paras = _iter_body_paragraphs(amend_root)
    aligned_amend_paras = _align_amended_paragraphs_to_original_blank_structure(orig_paras, amend_paras)

    amended_non_ws_chars = sum(len((_paragraph_text_all_runs(p) or "").strip()) for p in amend_paras)
    if amended_non_ws_chars == 0:
        raise ValueError(
            "Amended DOCX appears empty (no textual content detected). "
            "Provide a non-empty amended source DOCX before refinement."
        )

    if aligned_amend_paras is None:
        raise ValueError(
            f"Paragraph count mismatch: original has {len(orig_paras)}, amended has {len(amend_paras)}. "
            "Export the amended DOCX so it preserves paragraph breaks, or extend the script to allow structural edits."
        )

    changed = 0
    skipped = 0
    for p_orig, p_amend in zip(orig_paras, aligned_amend_paras):
        new_text = _paragraph_text_all_runs(p_amend) if p_amend is not None else ""
        if footnote_search_text_by_id:
            new_text = _rewrite_cross_reference_numbers_in_text(
                new_text,
                footnote_search_text_by_id=footnote_search_text_by_id,
                case_reference_names_by_footnote=case_reference_names_by_footnote,
            )
        paragraph_changed = False
        if _paragraph_is_simple(p_orig):
            if _apply_diff_to_paragraph(
                p_orig,
                new_text,
                markup=markup,
                preserve_projected_inline_italics=True,
            ):
                changed += 1
                paragraph_changed = True
        else:
            # Complex paragraphs (e.g., with hyperlinks/fields): use full-text
            # replacement with local-style inheritance and additive markup.
            if _apply_full_replace_to_paragraph(
                p_orig,
                new_text,
                markup=markup,
                preserve_projected_inline_italics=True,
            ):
                changed += 1
                paragraph_changed = True
            else:
                skipped += 1
        added_refs = _sync_footnote_reference_runs_from_amended(p_orig, p_amend) if p_amend is not None else 0
        if added_refs:
            changed += added_refs
            paragraph_changed = True

    parts_to_write: dict[str, etree._Element] = {part: orig_root}

    orig_footnotes = _load_docx_xml_if_exists(original_docx, footnotes_part)
    orig_footnotes_template = _load_docx_xml_if_exists(original_docx, footnotes_part)
    footnote_text_changed = False
    if sync_footnotes:
        if orig_footnotes is not None and amend_footnotes is not None:
            fn_changed, fn_skipped_complex, fn_skipped_structure = _sync_footnotes_from_amended(
                orig_footnotes, amend_footnotes, markup=markup
            )
            footnote_text_changed = fn_changed > 0
            changed += fn_changed
            skipped += fn_skipped_complex + fn_skipped_structure
            parts_to_write[footnotes_part] = orig_footnotes
    if orig_footnotes is not None:
        italicized = _normalize_case_italics_in_footnotes(orig_footnotes)
        if italicized:
            changed += italicized
            parts_to_write[footnotes_part] = orig_footnotes
    else:
        italicized = 0
    if orig_footnotes is not None and orig_footnotes_template is not None and (footnote_text_changed or italicized):
        style_fixed = _normalize_footnote_styles_from_original(orig_footnotes_template, orig_footnotes)
        if style_fixed:
            changed += style_fixed
            parts_to_write[footnotes_part] = orig_footnotes

    body_ref_styles_fixed = _normalize_body_footnote_reference_styles_from_original(orig_root_template, orig_root)
    if body_ref_styles_fixed:
        parts_to_write[part] = orig_root

    body_refs_fixed = _normalize_body_footnote_reference_positions(orig_root, orig_footnotes)
    if body_refs_fixed:
        changed += body_refs_fixed
        parts_to_write[part] = orig_root

    body_italics_fixed = _normalize_body_italics(
        orig_root,
        orig_footnotes,
    )
    if body_italics_fixed:
        changed += body_italics_fixed
        parts_to_write[part] = orig_root

    bibliography_bold_fixed = _normalize_bibliography_bold(orig_root)
    if bibliography_bold_fixed:
        changed += bibliography_bold_fixed
        parts_to_write[part] = orig_root

    _write_docx_with_replaced_parts(original_docx, out_docx, parts_to_write)
    if markup:
        _assert_markup_detectable(original_docx, out_docx, changed)
    return changed, skipped


def _split_amended_text_to_paragraphs(text: str) -> List[str]:
    # Split on blank lines (>=2 newlines). Keep internal single newlines as-is.
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not cleaned:
        return []
    return re.split(r"\n{2,}", cleaned)


def refine_from_amended_text(
    original_docx: Path, amended_text_path: Path, out_docx: Path, *, markup: bool = True
) -> Tuple[int, int]:
    _require_markup_enabled(markup)
    part = "word/document.xml"
    orig_root = _load_docx_xml(original_docx, part)
    orig_paras = _iter_body_paragraphs(orig_root)

    amended_text = amended_text_path.read_text(encoding="utf-8")
    amended_paras = _split_amended_text_to_paragraphs(amended_text)
    aligned_amended_paras = _align_amended_text_to_original_blank_structure(orig_paras, amended_paras)

    if aligned_amended_paras is None:
        raise ValueError(
            f"Paragraph count mismatch: original DOCX has {len(orig_paras)}, amended text has {len(amended_paras)}. "
            "Ensure the amended text preserves paragraph breaks using blank lines between paragraphs."
        )

    changed = 0
    skipped = 0
    for p_orig, new_text in zip(orig_paras, aligned_amended_paras):
        if _paragraph_is_simple(p_orig):
            if _apply_diff_to_paragraph(
                p_orig,
                new_text,
                markup=markup,
                preserve_projected_inline_italics=True,
            ):
                changed += 1
        else:
            if _apply_full_replace_to_paragraph(
                p_orig,
                new_text,
                markup=markup,
                preserve_projected_inline_italics=True,
            ):
                changed += 1
            else:
                skipped += 1

    _write_docx_with_replaced_part(original_docx, out_docx, part, orig_root)
    return changed, skipped


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Copy textual amendments from an amended DOCX into an original DOCX while preserving the original styling. Changes are yellow highlighted."
    )
    ap.add_argument("--original", required=True, type=Path, help="Path to the user's original DOCX (style source).")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--amended", type=Path, help="Path to the amended DOCX (text source).")
    src.add_argument(
        "--amended-txt",
        type=Path,
        help="Path to a UTF-8 text file containing amended content, split into paragraphs by blank lines.",
    )
    ap.add_argument(
        "--out",
        type=Path,
        help=(
            "Output DOCX path. The refine flow always writes to a Desktop final path for "
            "the source (<original>_amended_marked_final.docx, then _v2, _v3, etc. if a "
            "prior final output already exists). Any other requested filename is normalized "
            "back to that protected Desktop output policy. The original source DOCX is never overwritten."
        ),
    )
    ap.add_argument(
        "--no-sync-footnotes",
        action="store_true",
        help="When using --amended DOCX, do not transfer textual changes from word/footnotes.xml.",
    )
    ap.add_argument(
        "--check-body-short-form-case-italics",
        action="store_true",
        help=(
            "Deprecated no-op kept for backwards compatibility. Bare body-text "
            "short-form case names (for example 'In Walters, ...') are no longer "
            "auto-normalized."
        ),
    )
    args = ap.parse_args(argv)

    requested_original = args.original.expanduser().resolve()
    if args.amended is not None:
        args.amended = args.amended.expanduser().resolve()
    if args.amended_txt is not None:
        args.amended_txt = args.amended_txt.expanduser().resolve()

    effective_original = requested_original.expanduser().resolve()
    args.out, normalized_output = _normalize_to_final_output_path(requested_original, args.out)
    _require_desktop_root_output(args.out)
    if args.out.suffix.lower() != ".docx":
        raise ValueError(f"Output DOCX must be a .docx file: {args.out}")
    effective_original, temp_original_dir = _copy_source_to_temp_if_same_as_output(effective_original, args.out)
    args.original = effective_original
    if args.amended is not None and args.out == args.amended:
        raise ValueError(
            "Output path cannot be the same as --amended. "
            "Write to a new output DOCX path to preserve source integrity."
        )

    requested_out = args.out
    if normalized_output:
        print(f"[OUTPUT] Requested output path normalized to protected Desktop final DOCX: {requested_out}")

    try:
        if args.amended is not None:
            changed, skipped = refine_from_amended(
                args.original,
                args.amended,
                args.out,
                markup=True,
                sync_footnotes=not args.no_sync_footnotes,
            )
        else:
            changed, skipped = refine_from_amended_text(args.original, args.amended_txt, args.out, markup=True)
    finally:
        if temp_original_dir is not None:
            shutil.rmtree(temp_original_dir, ignore_errors=True)
    print(f"Wrote: {args.out}")
    print(f"Paragraphs updated: {changed}")
    if skipped:
        print(f"Paragraphs skipped (complex structures): {skipped}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
