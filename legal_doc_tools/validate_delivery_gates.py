#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
BIBLIOGRAPHY_HEADINGS = {"bibliography", "references", "reference list", "works cited"}
TABLE_OF_CASES_HEADINGS = {"table of cases", "table of authorities"}
NON_BIBLIOGRAPHY_SECTION_HEADINGS = {
    "table of legislation",
    "list of abbreviations",
}
DESKTOP_ROOT = (Path.home() / "Desktop").resolve()
QUALITY_LEDGER_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "Sentence-Level Issues",
        (
            r"\b(?:Sentence(?:-Level)?|Sentence-by-Sentence)\s+Issues?\b\s*[:=]\s*(\d+)",
            r"\b(?:Sentence(?:-Level)?|Sentence-by-Sentence)\s+Issues?\b\s*\|\s*(\d+)",
        ),
        (
            r"\b(?:Sentence(?:-Level)?|Sentence-by-Sentence)\s+Issues?\b",
        ),
    ),
    (
        "Logic Gaps",
        (
            r"\bLogic\s+Gaps?\b\s*[:=]\s*(\d+)",
            r"\bLogic\s+Gaps?\b\s*\|\s*(\d+)",
        ),
        (r"\bLogic\s+Gaps?\b",),
    ),
    (
        "Coherence Issues",
        (
            r"\bCoherence\s+Issues?\b\s*[:=]\s*(\d+)",
            r"\bCoherence\s+Issues?\b\s*\|\s*(\d+)",
        ),
        (r"\bCoherence\s+Issues?\b",),
    ),
    (
        "Fluency Issues",
        (
            r"\bFluency\s+Issues?\b\s*[:=]\s*(\d+)",
            r"\bFluency\s+Issues?\b\s*\|\s*(\d+)",
        ),
        (r"\bFluency\s+Issues?\b",),
    ),
    (
        "Clarity Issues",
        (
            r"\bClarity\s+Issues?\b\s*[:=]\s*(\d+)",
            r"\bClarity\s+Issues?\b\s*\|\s*(\d+)",
        ),
        (r"\bClarity\s+Issues?\b",),
    ),
)
INLINE_COMMENT_PATTERNS = (
    re.compile(
        r"^\s*(?:comment|comments|review\s*comment|reviewer\s*comment|feedback|annotation|note|issue|query|request|instruction)\s*(?:#?\d+)?\s*[:\-]",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\[(?:comment|review\s*comment|reviewer\s*comment|feedback|annotation|note|issue|query|request|instruction)\s*(?:#?\d+)?\]",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^\s*\((?:comment|review\s*comment|reviewer\s*comment|feedback|annotation|note|issue|query|request|instruction)\s*(?:#?\d+)?\s*[:\-]",
        flags=re.IGNORECASE,
    ),
)
TOKEN_RE = re.compile(r"\s+|[^\s]+", re.UNICODE)
BODY_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’&./-]*", re.UNICODE)
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
LEGAL_LATIN_PHRASE_PATTERNS = tuple(
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in (
        r"\bforum\s+non\s+conveniens\b",
        r"\blex\s+loci\s+damni\b",
        r"\blex\s+fori\b",
        r"\blex\s+causae\b",
        r"\blis\s+pendens\b",
    )
)
CASE_TOKEN = r"[A-Z][A-Za-z0-9&'.,()\\-]*"
CASE_SUFFIX_TOKEN = r"(?:plc|ltd|limited|llc|sa|ag|nv|spa|sas|corp|corporation|inc|co|company|gmbh|llp|lp|bv|sarl)"
CASE_JOINER = rf"(?:[A-Z][A-Za-z0-9&'.,()\\-]*|&|{CASE_SUFFIX_TOKEN}|of|the|and|for|de|la|le|del|du|van|von|da|di|al)"
CASE_V_PATTERN = re.compile(
    rf"\\b{CASE_TOKEN}(?:\\s+{CASE_JOINER})*\\s+v\\s+{CASE_TOKEN}(?:\\s+{CASE_JOINER})*(?=\\s*(?:\\[\\d{{4}}|\\(\\d{{4}}|EU:|ECLI:|[.;,]|$))"
)
RE_CASE_PATTERN = re.compile(
    rf"\\b(?:In\\s+re|Re)\\s+{CASE_TOKEN}(?:\\s+{CASE_JOINER})*(?=\\s*(?:\\[\\d{{4}}|\\(\\d{{4}}|[.;,]|$))"
)
SHIP_CASE_PATTERN = re.compile(
    rf"\bThe\s+{CASE_TOKEN}(?:\s+{CASE_TOKEN}){{0,3}}(?=\s*(?:\[[0-9]{{4}}\]|\([0-9]{{4}}\)))"
)
SHORT_CASE_CROSSREF_PATTERN = re.compile(
    rf"\\b({CASE_TOKEN}(?:\\s+{CASE_JOINER})*)\\s*\\(n\\s+(\\d+)\\)",
    flags=re.IGNORECASE,
)
GENERIC_CROSSREF_NUMBER_PATTERN = re.compile(r"\(n\s+(\d+)\)", flags=re.IGNORECASE)
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


def _normalize_mode(mode: str) -> str:
    m = mode.strip().lower().replace("_", "-")
    aliases = {
        "review+amend": "review+amend",
        "review-amend": "review+amend",
        "reviewandamend": "review+amend",
        "review": "review",
        "amend": "amend",
    }
    if m not in aliases:
        raise ValueError(f"Unsupported mode '{mode}'. Use: review, review+amend, amend.")
    return aliases[m]


def _assert_docx(path: Path, label: str, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"{label} does not exist: {path}")
        return
    if path.suffix.lower() != ".docx":
        errors.append(f"{label} must be a .docx file: {path}")
        return
    try:
        with zipfile.ZipFile(path, "r"):
            pass
    except zipfile.BadZipFile:
        errors.append(f"{label} is not a valid DOCX/zip package: {path}")


def _is_desktop_root_output(path: Path) -> bool:
    resolved = path.expanduser().resolve()
    return resolved.parent == DESKTOP_ROOT


def _extract_version_for_original(amended_path: Path, original_path: Path) -> int | None:
    pattern = re.compile(
        rf"^{re.escape(original_path.stem)}_amended_marked_v(\d+)\.docx$",
        flags=re.IGNORECASE,
    )
    match = pattern.match(amended_path.name)
    if not match:
        return None
    return int(match.group(1))


def _highest_version_for_original_in_desktop(original_path: Path) -> int | None:
    pattern = re.compile(
        rf"^{re.escape(original_path.stem)}_amended_marked_v(\d+)\.docx$",
        flags=re.IGNORECASE,
    )
    highest: int | None = None
    for candidate in DESKTOP_ROOT.iterdir():
        if not candidate.is_file():
            continue
        match = pattern.match(candidate.name)
        if not match:
            continue
        version = int(match.group(1))
        if highest is None or version > highest:
            highest = version
    return highest


def _read_xml_part(docx_path: Path, part: str) -> etree._Element | None:
    with zipfile.ZipFile(docx_path, "r") as zf:
        if part not in zf.namelist():
            return None
        return etree.fromstring(zf.read(part))


def _extract_footnote_ids(docx_path: Path) -> list[int]:
    root = _read_xml_part(docx_path, "word/footnotes.xml")
    if root is None:
        return []
    ids: list[int] = []
    for node in root.xpath("./w:footnote", namespaces=NS):
        raw = node.get(f"{{{W_NS}}}id")
        if raw is None:
            continue
        try:
            fid = int(raw)
        except ValueError:
            continue
        if fid >= 1:
            ids.append(fid)
    return ids


def _extract_body_footnote_reference_ids(docx_path: Path) -> list[int]:
    root = _read_xml_part(docx_path, "word/document.xml")
    if root is None:
        return []
    ids: list[int] = []
    for ref in root.xpath(".//w:footnoteReference", namespaces=NS):
        raw = ref.get(f"{{{W_NS}}}id")
        if raw is None:
            continue
        try:
            fid = int(raw)
        except ValueError:
            continue
        if fid >= 1:
            ids.append(fid)
    return ids


def _footnote_nodes_by_id(root: etree._Element | None) -> dict[int, etree._Element]:
    if root is None:
        return {}
    nodes: dict[int, etree._Element] = {}
    for node in root.xpath("./w:footnote", namespaces=NS):
        raw = node.get(f"{{{W_NS}}}id")
        if raw is None:
            continue
        try:
            fid = int(raw)
        except ValueError:
            continue
        if fid >= 1:
            nodes[fid] = node
    return nodes


def _canonical_xml_fragment(node: etree._Element | None) -> str:
    if node is None:
        return ""
    xml = etree.tostring(node, encoding="unicode")
    return re.sub(r">\s+<", "><", xml).strip()


def _nearest_original_footnote_node(nodes_by_id: dict[int, etree._Element], fid: int) -> etree._Element | None:
    if not nodes_by_id:
        return None
    ids = sorted(nodes_by_id)
    lower_ids = [candidate for candidate in ids if candidate < fid]
    if lower_ids:
        return nodes_by_id[lower_ids[-1]]
    higher_ids = [candidate for candidate in ids if candidate > fid]
    if higher_ids:
        return nodes_by_id[higher_ids[0]]
    return None


def _leading_text_before_footnote_marker(paragraph: etree._Element) -> str:
    parts: list[str] = []
    for run in paragraph.xpath("./w:r", namespaces=NS):
        if run.find("w:footnoteRef", namespaces=NS) is not None:
            break
        parts.extend(run.xpath("./w:t/text()", namespaces=NS))
    return "".join(parts)


def _first_text_run_after_footnote_marker(paragraph: etree._Element) -> etree._Element | None:
    marker_seen = False
    for run in paragraph.xpath("./w:r", namespaces=NS):
        if run.find("w:footnoteRef", namespaces=NS) is not None:
            marker_seen = True
            continue
        if not marker_seen:
            continue
        if "".join(run.xpath("./w:t/text()", namespaces=NS)) != "":
            return run
    return None


def _run_contains_textual_content(run: etree._Element) -> bool:
    return bool(run.xpath("./w:t|./w:tab|./w:br|./w:noBreakHyphen|./w:softHyphen", namespaces=NS))


def _first_non_marker_textual_run(paragraph: etree._Element) -> etree._Element | None:
    marker_seen = False
    for run in paragraph.xpath("./w:r", namespaces=NS):
        if run.find("w:footnoteRef", namespaces=NS) is not None:
            marker_seen = True
            continue
        if not marker_seen:
            continue
        if _run_contains_textual_content(run):
            return run
    return None


def _template_text_style_rpr_for_footnote_paragraph(paragraph: etree._Element) -> etree._Element | None:
    run = _first_non_marker_textual_run(paragraph)
    if run is not None:
        rPr = run.find("./w:rPr", namespaces=NS)
        if rPr is not None:
            return rPr
    pPr = paragraph.find("./w:pPr", namespaces=NS)
    if pPr is None:
        return None
    return pPr.find("./w:rPr", namespaces=NS)


def _run_has_effective_italic(run: etree._Element) -> bool:
    rPr = run.find("./w:rPr", namespaces=NS)
    if rPr is None:
        return False
    explicit_false = False
    for tag in ("i", "iCs"):
        italic = rPr.find(f"./w:{tag}", namespaces=NS)
        if italic is None:
            continue
        val = (italic.get(f"{{{W_NS}}}val") or "").strip().lower()
        if val in {"0", "false", "off", "no"}:
            explicit_false = True
            continue
        return True
    if explicit_false:
        return False
    r_style = rPr.find("./w:rStyle", namespaces=NS)
    if r_style is not None:
        style_name = (r_style.get(f"{{{W_NS}}}val") or "").strip().casefold()
        if "emphasis" in style_name:
            return True
    return False


def _run_style_signature(run: etree._Element, *, ignore_tags: set[str] | None = None) -> tuple[tuple[str, str], ...]:
    ignore_tags = ignore_tags or set()
    rPr = run.find("./w:rPr", namespaces=NS)
    signature: list[tuple[str, str]] = []
    for tag in ("rFonts", "sz", "szCs", "vertAlign", "lang", "color", "shd", "rStyle"):
        if tag in ignore_tags:
            continue
        node = rPr.find(f"./w:{tag}", namespaces=NS) if rPr is not None else None
        signature.append((tag, _canonical_xml_fragment(node)))
    return tuple(signature)


def _paragraph_text_style_segments(
    paragraph: etree._Element,
    *,
    ignore_tags: set[str] | None = None,
) -> tuple[str, list[tuple[int, int, tuple[tuple[str, str], ...]]]]:
    text_parts: list[str] = []
    segments: list[tuple[int, int, tuple[tuple[str, str], ...]]] = []
    pos = 0
    for run in paragraph.xpath("./w:r", namespaces=NS):
        if run.find("w:footnoteRef", namespaces=NS) is not None:
            continue
        txt = "".join(run.xpath("./w:t/text()", namespaces=NS))
        if not txt:
            continue
        text_parts.append(txt)
        segments.append((pos, pos + len(txt), _run_style_signature(run, ignore_tags=ignore_tags)))
        pos += len(txt)
    return "".join(text_parts), segments


def _signature_covering(
    segments: list[tuple[int, int, tuple[tuple[str, str], ...]]],
    start: int,
    end: int,
) -> tuple[tuple[str, str], ...] | None:
    for seg_start, seg_end, sig in segments:
        if seg_start <= start and end <= seg_end:
            return sig
    return None


def _same_text_local_style_matches(original_paragraph: etree._Element, amended_paragraph: etree._Element) -> bool:
    original_text, original_segments = _paragraph_text_style_segments(original_paragraph, ignore_tags={"i", "iCs"})
    amended_text, amended_segments = _paragraph_text_style_segments(amended_paragraph, ignore_tags={"i", "iCs"})
    if original_text != amended_text:
        return False
    boundaries = {0, len(original_text)}
    for seg_start, seg_end, _sig in original_segments + amended_segments:
        boundaries.add(seg_start)
        boundaries.add(seg_end)
    ordered = sorted(boundaries)
    for start, end in zip(ordered, ordered[1:]):
        if start >= end:
            continue
        if _signature_covering(original_segments, start, end) != _signature_covering(amended_segments, start, end):
            return False
    return True


def _run_style_mismatch_labels(run: etree._Element, template_rPr: etree._Element | None) -> list[str]:
    if template_rPr is None:
        return []

    current_rPr = run.find("./w:rPr", namespaces=NS)
    mismatches: list[str] = []
    for tag in ("rFonts", "sz", "szCs", "vertAlign", "lang", "color", "shd"):
        template_node = template_rPr.find(f"./w:{tag}", namespaces=NS)
        current_node = current_rPr.find(f"./w:{tag}", namespaces=NS) if current_rPr is not None else None
        template_xml = _canonical_xml_fragment(template_node)
        current_xml = _canonical_xml_fragment(current_node)
        if template_xml != current_xml:
            mismatches.append(tag)
    return mismatches


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
    return {variant for variant in variants if variant}


def _trim_case_span_leading_eu_case_number_metadata(
    text: str, span: tuple[int, int]
) -> tuple[int, int]:
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


def _eu_case_name_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in EU_CASE_REFERENCE_SPAN_PATTERN.finditer(text):
        snippet = match.group("name")
        if not snippet:
            continue
        collapsed = re.sub(r"\s+", " ", snippet)
        if " v " not in collapsed:
            continue
        start = match.start("name")
        end = match.end("name")
        spans.append((start, end))
    return spans


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

    for pattern in (RE_CASE_PATTERN, SHIP_CASE_PATTERN):
        for match in pattern.finditer(text):
            names.update(_case_reference_variants(match.group(0)))

    return names


def _build_footnote_case_reference_map(root: etree._Element | None) -> dict[int, set[str]]:
    try:
        from legal_doc_tools.refine_docx_from_amended import (
            _build_footnote_case_reference_map as _refiner_build_footnote_case_reference_map,
        )

        return _refiner_build_footnote_case_reference_map(root)
    except Exception:
        try:
            from refine_docx_from_amended import (
                _build_footnote_case_reference_map as _refiner_build_footnote_case_reference_map,
            )

            return _refiner_build_footnote_case_reference_map(root)
        except Exception:
            pass

    if root is None:
        return {}

    by_id: dict[int, set[str]] = {}
    footnote_text_by_id: dict[int, str] = {}
    for node in root.xpath("./w:footnote", namespaces=NS):
        raw_id = node.get(f"{{{W_NS}}}id")
        if raw_id in ("-1", "0", None):
            continue
        try:
            fid = int(raw_id)
        except ValueError:
            continue
        text = "".join(node.xpath(".//w:t/text()", namespaces=NS))
        footnote_text_by_id[fid] = text
        by_id[fid] = _extract_case_reference_names(text)

    for _ in range(3):
        changed = False
        for fid, text in footnote_text_by_id.items():
            for match in SHORT_CASE_CROSSREF_PATTERN.finditer(text):
                candidate_variants = _case_reference_variants(match.group(1))
                ref_id = int(match.group(2))
                if candidate_variants.intersection(by_id.get(ref_id, set())) and not candidate_variants.issubset(
                    by_id[fid]
                ):
                    by_id[fid].update(candidate_variants)
                    changed = True
        if not changed:
            break

    return by_id


def _normalize_reference_search_text(text: str) -> str:
    cleaned = text.replace("’", "'")
    cleaned = re.sub(r"[^A-Za-z0-9'&./-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().casefold()
    return f" {cleaned} " if cleaned else " "


def _build_footnote_search_text_map(root: etree._Element | None) -> dict[int, str]:
    try:
        from legal_doc_tools.refine_docx_from_amended import (
            _build_footnote_search_text_map as _refiner_build_footnote_search_text_map,
        )

        return _refiner_build_footnote_search_text_map(root)
    except Exception:
        try:
            from refine_docx_from_amended import (
                _build_footnote_search_text_map as _refiner_build_footnote_search_text_map,
            )

            return _refiner_build_footnote_search_text_map(root)
        except Exception:
            pass

    if root is None:
        return {}

    by_id: dict[int, str] = {}
    for node in root.xpath("./w:footnote", namespaces=NS):
        raw_id = node.get(f"{{{W_NS}}}id")
        if raw_id in ("-1", "0", None):
            continue
        try:
            fid = int(raw_id)
        except ValueError:
            continue
        text = "".join(node.xpath(".//w:t/text()", namespaces=NS))
        by_id[fid] = _normalize_reference_search_text(text)
    return by_id


def _extract_cross_reference_anchor(text: str, crossref_start: int) -> str | None:
    prefix = text[:crossref_start]
    tokens = list(BODY_WORD_RE.finditer(prefix))
    if not tokens:
        return None

    anchor_tokens: list[str] = []
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
    current_footnote_id: int | None = None,
) -> int | None:
    anchor_variants = _reference_anchor_variants(anchor)
    if not anchor_variants:
        return None

    cited_refs = case_reference_names_by_footnote.get(cited_id, set())
    if anchor_variants.intersection(cited_refs):
        return cited_id

    cited_search_text = footnote_search_text_by_id.get(cited_id, "")
    if cited_search_text and any(f" {variant} " in cited_search_text for variant in anchor_variants):
        return cited_id

    direct_matches = sorted(
        fid
        for fid, refs in case_reference_names_by_footnote.items()
        if (current_footnote_id is None or fid != current_footnote_id) and anchor_variants.intersection(refs)
    )
    if direct_matches:
        return direct_matches[0]

    text_matches = sorted(
        fid
        for fid, search_text in footnote_search_text_by_id.items()
        if (current_footnote_id is None or fid != current_footnote_id)
        and any(f" {variant} " in search_text for variant in anchor_variants)
    )
    if text_matches:
        return text_matches[0]
    return None


def _cross_reference_number_issues(
    text: str,
    *,
    location: str,
    footnote_search_text_by_id: dict[int, str],
    case_reference_names_by_footnote: dict[int, set[str]],
    current_footnote_id: int | None = None,
) -> list[str]:
    issues: list[str] = []
    if "(n " not in text.lower():
        return issues

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
        issues.append(
            f"{location} has a stale '(n {cited_id})' cross-reference after '{anchor}'; "
            f"the uniquely matching footnote is {resolved_id}."
        )
    return issues


def _build_body_case_reference_names(case_reference_names_by_footnote: dict[int, set[str]]) -> set[str]:
    del case_reference_names_by_footnote
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

    for pattern in (RE_CASE_PATTERN, SHIP_CASE_PATTERN):
        for match in pattern.finditer(text):
            for variant in _case_reference_variants(match.group(0)):
                if not variant or " " in variant or variant in BODY_CASE_NAME_HEADWORD_BLACKLIST:
                    continue
                candidates.add(variant)

    return candidates


def _build_requested_body_short_form_case_names(footnotes_root: etree._Element | None) -> set[str]:
    if footnotes_root is None:
        return set()

    candidates: set[str] = set()
    for footnote in footnotes_root.xpath("/w:footnotes/w:footnote[@w:id>=1]", namespaces=NS):
        text = "".join(footnote.xpath(".//w:t/text()", namespaces=NS))
        candidates.update(_single_word_body_short_form_candidates_from_text(text))
    return candidates


def _legal_latin_phrase_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for pattern in LEGAL_LATIN_PHRASE_PATTERNS:
        for match in pattern.finditer(text):
            spans.append((match.start(), match.end()))
    return spans


def _extend_case_span_with_sequel_suffix(text: str, span: tuple[int, int]) -> tuple[int, int]:
    start, end = span
    match = CASE_SEQUEL_SUFFIX_RE.match(text[end:])
    if match is None:
        return span
    return start, end + match.end(1)


def _body_reference_runs_with_positions(paragraph: etree._Element) -> list[tuple[int, int]]:
    refs: list[tuple[int, int]] = []
    pos = 0
    for run in paragraph.xpath("./w:r", namespaces=NS):
        ref = run.find("w:footnoteReference", namespaces=NS)
        if ref is not None:
            raw_id = ref.get(f"{{{W_NS}}}id")
            if raw_id is not None:
                try:
                    refs.append((int(raw_id), pos))
                except ValueError:
                    pass
            continue

        for child in run:
            if child.tag == f"{{{W_NS}}}t":
                pos += len(child.text or "")
            elif child.tag in (
                f"{{{W_NS}}}tab",
                f"{{{W_NS}}}br",
                f"{{{W_NS}}}noBreakHyphen",
                f"{{{W_NS}}}softHyphen",
            ):
                pos += 1
    return refs


def _body_run_data(paragraph: etree._Element) -> list[tuple[str, bool, int, int]]:
    run_data: list[tuple[str, bool, int, int]] = []
    pos = 0
    for run in paragraph.xpath("./w:r", namespaces=NS):
        if run.find("w:footnoteReference", namespaces=NS) is not None:
            continue
        txt = "".join(run.xpath("./w:t/text()", namespaces=NS))
        if not txt:
            continue
        is_italic = _run_has_effective_italic(run)
        run_data.append((txt, is_italic, pos, pos + len(txt)))
        pos += len(txt)
    return run_data


def _footnote_run_data(paragraph: etree._Element) -> list[tuple[str, bool, int, int]]:
    run_data: list[tuple[str, bool, int, int]] = []
    pos = 0
    for run in paragraph.xpath("./w:r", namespaces=NS):
        if run.find("w:footnoteRef", namespaces=NS) is not None:
            continue
        txt = "".join(run.xpath("./w:t/text()", namespaces=NS))
        if not txt:
            continue
        is_italic = _run_has_effective_italic(run)
        run_data.append((txt, is_italic, pos, pos + len(txt)))
        pos += len(txt)
    return run_data


def _span_is_fully_italicized(
    run_data: list[tuple[str, bool, int, int]],
    start: int,
    end: int,
) -> bool:
    for _, is_italic, run_start, run_end in run_data:
        if run_start < end and run_end > start:
            if not is_italic:
                return False
    return True


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


def _anchor_word_before_position(text: str, pos: int) -> re.Match[str] | None:
    match: re.Match[str] | None = None
    for candidate in BODY_WORD_RE.finditer(text):
        if candidate.end() > pos:
            break
        match = candidate
    return match


def _sentence_bounds_for_position(text: str, pos: int) -> tuple[int, int]:
    start = 0
    for match in re.finditer(r"[.!?]", text):
        if match.end() <= pos:
            start = match.end()
            continue
        return start, match.end()
    return start, len(text)


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not spans:
        return []
    spans = sorted(spans)
    merged = [spans[0]]
    for start, end in spans[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _find_case_name_candidate_spans(text: str, candidate_names: set[str]) -> list[tuple[int, int]]:
    if not text or not candidate_names:
        return []

    tokens = list(BODY_WORD_RE.finditer(text))
    spans: list[tuple[int, int]] = []
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


def _body_case_name_spans(
    text: str,
    *,
    case_reference_names_by_footnote: dict[int, set[str]],
    body_case_reference_names: set[str],
    enforce_body_short_form_case_italics: bool = False,
) -> list[tuple[int, int]]:
    del body_case_reference_names
    del enforce_body_short_form_case_italics
    spans: list[tuple[int, int]] = []

    for pattern in (CASE_V_PATTERN, RE_CASE_PATTERN, SHIP_CASE_PATTERN):
        for match in pattern.finditer(text):
            spans.append((match.start(), match.end()))

    for match in SHORT_CASE_CROSSREF_PATTERN.finditer(text):
        candidate_variants = _case_reference_variants(match.group(1))
        ref_id = int(match.group(2))
        if candidate_variants.intersection(case_reference_names_by_footnote.get(ref_id, set())):
            spans.append((match.start(1), match.end(1)))

    spans.extend(_legal_latin_phrase_spans(text))
    spans = [_extend_case_span_with_sequel_suffix(text, span) for span in spans]
    return _merge_spans(spans)


def _context_supports_ambiguous_case_short_form(text: str, token_match: re.Match[str]) -> bool:
    sentence_start, sentence_end = _sentence_bounds_for_position(text, token_match.start())
    sentence = text[sentence_start:sentence_end]
    words = [match.group(0).casefold() for match in BODY_WORD_RE.finditer(sentence)]
    if not words:
        return False

    local_start = token_match.start() - sentence_start
    local_end = token_match.end() - sentence_start
    token_index: int | None = None
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
    if token_index == 1 and words[0] == "in":
        score += 1

    return score >= 2


def _ambiguous_case_short_form_spans(text: str, candidate_names: set[str]) -> list[tuple[int, int]]:
    if not text or not candidate_names:
        return []

    spans: list[tuple[int, int]] = []
    for token_match in BODY_WORD_RE.finditer(text):
        normalized = _normalize_case_reference_name(token_match.group(0))
        if normalized not in candidate_names:
            continue
        if _context_supports_ambiguous_case_short_form(text, token_match):
            spans.append((token_match.start(), token_match.end()))
    return _merge_spans(spans)


def _body_reference_low_value_anchor_issue(paragraph_text: str, pos: int) -> tuple[str, str] | None:
    anchor_match = _anchor_word_before_position(paragraph_text, pos)
    if anchor_match is None:
        return None

    anchor_word = _normalize_case_reference_name(anchor_match.group(0))
    if anchor_word not in LOW_VALUE_BODY_REFERENCE_ANCHORS:
        return None

    sentence_start, _sentence_end = _sentence_bounds_for_position(paragraph_text, pos)
    if sentence_start <= 0:
        return None

    prior_sentence_excerpt = paragraph_text[:sentence_start].rstrip()
    if not prior_sentence_excerpt:
        return None

    return anchor_match.group(0), prior_sentence_excerpt[-80:]


def _body_reference_case_anchor_issue(
    paragraph_text: str,
    pos: int,
    ref_id: int,
    *,
    case_reference_names_by_footnote: dict[int, set[str]],
) -> tuple[str, str] | None:
    candidate_names = case_reference_names_by_footnote.get(ref_id, set())
    if not candidate_names:
        return _body_reference_low_value_anchor_issue(paragraph_text, pos)

    spans = _find_case_name_candidate_spans(paragraph_text, candidate_names)
    containing_spans = [(start, end) for start, end in spans if start < pos < end]
    if containing_spans:
        case_start, case_end = containing_spans[0]
        anchor_match = _anchor_word_before_position(paragraph_text, pos)
        anchor_word = anchor_match.group(0) if anchor_match is not None else ""
        return anchor_word, paragraph_text[case_start:case_end].strip()

    preceding_spans = [(start, end) for start, end in spans if end <= pos]
    if not preceding_spans:
        return _body_reference_low_value_anchor_issue(paragraph_text, pos)
    case_start, case_end = preceding_spans[-1]
    if abs(pos - case_end) <= 2:
        return None

    anchor_match = _anchor_word_before_position(paragraph_text, pos)
    if anchor_match is None:
        return "", paragraph_text[case_start:case_end].strip()

    anchor_start, anchor_end = anchor_match.start(), anchor_match.end()
    anchor_word = _normalize_case_reference_name(anchor_match.group(0))
    anchor_inside_matching_span = any(start <= anchor_start and anchor_end <= end for start, end in spans)
    if anchor_inside_matching_span:
        return anchor_match.group(0), paragraph_text[case_start:case_end].strip()

    if anchor_word in GENERIC_BODY_REFERENCE_ANCHORS or anchor_word in LOW_VALUE_BODY_REFERENCE_ANCHORS:
        return anchor_match.group(0), paragraph_text[case_start:case_end].strip()

    sentence_start, sentence_end = _sentence_bounds_for_position(paragraph_text, pos)
    sentence_spans = [
        (start, end)
        for start, end in spans
        if sentence_start <= start and end <= pos
    ]
    if len(sentence_spans) == 1:
        case_start, case_end = sentence_spans[0]
        return anchor_match.group(0), paragraph_text[case_start:case_end].strip()

    if pos - case_end > 8 or anchor_match.group(0)[0].isupper():
        return anchor_match.group(0), paragraph_text[case_start:case_end].strip()

    return None


def _validate_footnote_reference_integrity(original_docx: Path, amended_docx: Path) -> list[str]:
    issues: list[str] = []
    original_footnotes_root = _read_xml_part(original_docx, "word/footnotes.xml")
    amended_footnotes_root = _read_xml_part(amended_docx, "word/footnotes.xml")
    amended_document_root = _read_xml_part(amended_docx, "word/document.xml")

    if amended_document_root is None:
        issues.append("Cannot validate footnote-reference integrity because amended DOCX is missing document.xml.")
        return issues

    body_reference_ids = set(_extract_body_footnote_reference_ids(amended_docx))
    if amended_footnotes_root is None:
        if not body_reference_ids:
            return issues
        issues.append("Cannot validate footnote-reference integrity because amended DOCX is missing footnotes.xml.")
        return issues

    original_nodes_by_id = _footnote_nodes_by_id(original_footnotes_root) if original_footnotes_root is not None else {}
    amended_nodes_by_id = _footnote_nodes_by_id(amended_footnotes_root)
    original_ids = set(original_nodes_by_id)
    amended_ids = set(amended_nodes_by_id)

    missing_footnote_defs = sorted(body_reference_ids - amended_ids)
    if missing_footnote_defs:
        issues.append(
            "Document contains footnote references with no matching footnote definition "
            f"(sample IDs: {missing_footnote_defs[:10]})."
        )

    unreferenced_added_ids = sorted((amended_ids - original_ids) - body_reference_ids)
    if unreferenced_added_ids:
        issues.append(
            "Added footnotes must remain linked from the document body, but these new IDs have no body reference "
            f"(sample IDs: {unreferenced_added_ids[:10]})."
        )

    for fid, footnote in sorted(amended_nodes_by_id.items()):
        paragraphs = footnote.xpath("./w:p", namespaces=NS)
        if not paragraphs:
            issues.append(f"Footnote {fid} has no paragraphs.")
            continue

        first_para = paragraphs[0]
        marker_run = next(
            (run for run in first_para.xpath("./w:r", namespaces=NS) if run.find("w:footnoteRef", namespaces=NS) is not None),
            None,
        )
        if marker_run is None:
            issues.append(f"Footnote {fid} is missing a real footnote marker run.")
            continue

        leading_text = re.sub(r"\s+", " ", _leading_text_before_footnote_marker(first_para)).strip()
        if leading_text:
            issues.append(f"Footnote {fid} has visible text before the marker ('{leading_text[:40]}').")

        marker_rstyle = marker_run.find("./w:rPr/w:rStyle", namespaces=NS)
        if marker_rstyle is None or (marker_rstyle.get(f"{{{W_NS}}}val") or "").strip() != "FootnoteReference":
            issues.append(f"Footnote {fid} marker run is missing the FootnoteReference style.")

        first_text_run = _first_text_run_after_footnote_marker(first_para)
        if first_text_run is not None:
            first_text = "".join(first_text_run.xpath("./w:t/text()", namespaces=NS))
            if re.match(rf"^\s*{fid}(?!\d)\b", first_text):
                issues.append(f"Footnote {fid} appears to start with a typed note number instead of the live marker.")
            text_rstyle = first_text_run.find("./w:rPr/w:rStyle", namespaces=NS)
            if text_rstyle is not None and (text_rstyle.get(f"{{{W_NS}}}val") or "").strip() == "FootnoteReference":
                issues.append(f"Footnote {fid} body text is incorrectly styled as FootnoteReference.")

        template_node = original_nodes_by_id.get(fid)
        if template_node is None:
            template_node = _nearest_original_footnote_node(original_nodes_by_id, fid)
        if template_node is None:
            continue

        template_paragraphs = template_node.xpath("./w:p", namespaces=NS)
        if not template_paragraphs:
            continue

        template_first_para = template_paragraphs[0]
        if _canonical_xml_fragment(first_para.find("./w:pPr", namespaces=NS)) != _canonical_xml_fragment(
            template_first_para.find("./w:pPr", namespaces=NS)
        ):
            issues.append(
                f"Footnote {fid} paragraph style block does not match the original footnote template."
            )

        template_marker_run = next(
            (run for run in template_first_para.xpath("./w:r", namespaces=NS) if run.find("w:footnoteRef", namespaces=NS) is not None),
            None,
        )
        if template_marker_run is not None:
            if _canonical_xml_fragment(marker_run.find("./w:rPr", namespaces=NS)) != _canonical_xml_fragment(
                template_marker_run.find("./w:rPr", namespaces=NS)
            ):
                issues.append(
                    f"Footnote {fid} marker styling does not match the original footnote template."
                )

        original_text, _original_segments = _paragraph_text_style_segments(template_first_para, ignore_tags={"i", "iCs"})
        amended_text, _amended_segments = _paragraph_text_style_segments(first_para, ignore_tags={"i", "iCs"})
        if original_text == amended_text:
            if not _same_text_local_style_matches(template_first_para, first_para):
                issues.append(
                    f"Footnote {fid} local text styling diverges from the original footnote styling."
                )
        else:
            template_text_rPr = _template_text_style_rpr_for_footnote_paragraph(template_first_para)
            for run in first_para.xpath("./w:r", namespaces=NS):
                if run.find("w:footnoteRef", namespaces=NS) is not None:
                    continue
                if not _run_contains_textual_content(run):
                    continue
                mismatches = _run_style_mismatch_labels(run, template_text_rPr)
                if mismatches:
                    issues.append(
                        f"Footnote {fid} text styling diverges from the original footnote template "
                        f"({', '.join(mismatches)})."
                    )
                    break

    case_reference_names_by_footnote = _build_footnote_case_reference_map(amended_footnotes_root)
    footnote_search_text_by_id = _build_footnote_search_text_map(amended_footnotes_root)
    for fid, footnote in sorted(amended_nodes_by_id.items()):
        footnote_text = "".join(footnote.xpath(".//w:t/text()", namespaces=NS))
        issues.extend(
            _cross_reference_number_issues(
                footnote_text,
                location=f"Footnote {fid}",
                footnote_search_text_by_id=footnote_search_text_by_id,
                case_reference_names_by_footnote=case_reference_names_by_footnote,
                current_footnote_id=fid,
            )
        )

    for para_idx, paragraph in enumerate(amended_document_root.xpath("/w:document/w:body/w:p", namespaces=NS), start=1):
        paragraph_text = "".join(paragraph.xpath(".//w:t/text()", namespaces=NS))
        if not paragraph_text.strip():
            continue

        issues.extend(
            _cross_reference_number_issues(
                paragraph_text,
                location=f"Body paragraph {para_idx}",
                footnote_search_text_by_id=footnote_search_text_by_id,
                case_reference_names_by_footnote=case_reference_names_by_footnote,
            )
        )

        paragraph_refs = _body_reference_runs_with_positions(paragraph)

        for idx, (ref_id, pos) in enumerate(paragraph_refs):
            if idx > 0:
                prev_ref_id, prev_pos = paragraph_refs[idx - 1]
                if prev_ref_id == ref_id and prev_pos == pos:
                    issues.append(
                        "Body footnote reference placement contains a duplicated marker "
                        f"(paragraph {para_idx}, footnote {ref_id})."
                    )

            anchor_issue = _body_reference_case_anchor_issue(
                paragraph_text,
                pos,
                ref_id,
                case_reference_names_by_footnote=case_reference_names_by_footnote,
            )
            if anchor_issue is None:
                continue

            anchor_word, case_anchor = anchor_issue
            issues.append(
                "Body footnote reference placement looks detached from the cited authority "
                f"(paragraph {para_idx}, footnote {ref_id}: attached after '{anchor_word}' instead of near '{case_anchor}')."
            )

    return issues


def _extract_docx_comment_ids(docx_path: Path) -> list[int]:
    root = _read_xml_part(docx_path, "word/comments.xml")
    if root is None:
        return []
    ids: list[int] = []
    for node in root.xpath("./w:comment", namespaces=NS):
        raw = node.get(f"{{{W_NS}}}id")
        if raw is None:
            continue
        try:
            cid = int(raw)
        except ValueError:
            continue
        if cid >= 0:
            ids.append(cid)
    return ids


def _extract_inline_written_comments(docx_path: Path) -> list[str]:
    snippets: list[str] = []
    seen: set[str] = set()
    for part in ("word/document.xml", "word/footnotes.xml"):
        root = _read_xml_part(docx_path, part)
        if root is None:
            continue
        for node in root.xpath(".//w:p", namespaces=NS):
            raw_text = "".join(node.xpath(".//w:t/text()", namespaces=NS))
            text = re.sub(r"\s+", " ", raw_text).strip()
            if not text:
                continue
            if any(pattern.search(text) for pattern in INLINE_COMMENT_PATTERNS):
                key = text.lower()
                if key not in seen:
                    seen.add(key)
                    snippets.append(text)
    return snippets


def _xml_text(root: etree._Element | None) -> str:
    if root is None:
        return ""
    return "".join(root.xpath(".//w:t/text()", namespaces=NS))


def _run_has_yellow_highlight(run: etree._Element) -> bool:
    rpr = run.find("w:rPr", namespaces=NS)
    if rpr is None:
        return False
    highlight = rpr.find("w:highlight", namespaces=NS)
    if highlight is None:
        return False
    return (highlight.get(f"{{{W_NS}}}val") or "").strip().lower() == "yellow"


def _paragraph_text_and_run_spans(
    paragraph: etree._Element,
) -> tuple[str, list[tuple[etree._Element, int, int]]]:
    text_parts: list[str] = []
    spans: list[tuple[etree._Element, int, int]] = []
    pos = 0
    for run in paragraph.xpath(".//w:r", namespaces=NS):
        run_parts: list[str] = []
        for child in run:
            if child.tag == f"{{{W_NS}}}t":
                run_parts.append(child.text or "")
            elif child.tag == f"{{{W_NS}}}tab":
                run_parts.append("\t")
            elif child.tag == f"{{{W_NS}}}br":
                run_parts.append("\n")
            elif child.tag == f"{{{W_NS}}}noBreakHyphen":
                run_parts.append("-")
            elif child.tag == f"{{{W_NS}}}softHyphen":
                run_parts.append("-")
        run_text = "".join(run_parts)
        if not run_text:
            continue
        start = pos
        end = pos + len(run_text)
        spans.append((run, start, end))
        text_parts.append(run_text)
        pos = end
    return "".join(text_parts), spans


def _merge_char_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []
    merged: list[tuple[int, int]] = [ranges[0]]
    for start, end in ranges[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def _changed_char_ranges_in_new_text(original_text: str, amended_text: str) -> list[tuple[int, int]]:
    if original_text == amended_text:
        return []
    old_tokens = TOKEN_RE.findall(original_text) if original_text else []
    new_tokens = TOKEN_RE.findall(amended_text) if amended_text else []
    if not new_tokens:
        return []

    new_tok_starts: list[int] = []
    cur = 0
    for tok in new_tokens:
        new_tok_starts.append(cur)
        cur += len(tok)

    changed_ranges: list[tuple[int, int]] = []
    sm = difflib.SequenceMatcher(a=old_tokens, b=new_tokens, autojunk=False)
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        if tag == "equal" or j1 == j2:
            continue
        start = new_tok_starts[j1]
        end = new_tok_starts[j2 - 1] + len(new_tokens[j2 - 1])
        if start < end:
            changed_ranges.append((start, end))
    changed_ranges.sort()
    return _merge_char_ranges(changed_ranges)


def _paragraphs_for_markup_validation(root: etree._Element, part: str) -> list[etree._Element]:
    if part == "word/document.xml":
        return root.xpath("/w:document/w:body//w:p", namespaces=NS)
    if part == "word/footnotes.xml":
        return root.xpath("/w:footnotes/w:footnote/w:p", namespaces=NS)
    raise ValueError(f"Unsupported part for markup validation: {part}")


def _footnote_paragraphs_by_id(root: etree._Element) -> dict[int, list[etree._Element]]:
    by_id: dict[int, list[etree._Element]] = {}
    for fn in root.xpath("/w:footnotes/w:footnote", namespaces=NS):
        raw = fn.get(f"{{{W_NS}}}id")
        if raw is None:
            continue
        try:
            fid = int(raw)
        except ValueError:
            continue
        if fid < 1:
            continue
        by_id[fid] = fn.xpath("./w:p", namespaces=NS)
    return by_id


def _validate_markup_hard_rule(original_docx: Path, amended_docx: Path) -> tuple[int, list[str]]:
    checked_runs = 0
    issues: list[str] = []
    for part in ("word/document.xml", "word/footnotes.xml"):
        label = "document" if part == "word/document.xml" else "footnotes"
        original_root = _read_xml_part(original_docx, part)
        amended_root = _read_xml_part(amended_docx, part)

        if original_root is None and amended_root is None:
            continue
        if original_root is None or amended_root is None:
            issues.append(
                f"{label}: cannot validate markup strictly because {part} is missing in one DOCX."
            )
            continue

        if part == "word/footnotes.xml":
            original_by_id = _footnote_paragraphs_by_id(original_root)
            amended_by_id = _footnote_paragraphs_by_id(amended_root)
            paragraph_pairs: list[tuple[str, etree._Element, etree._Element]] = []
            for fid in sorted(set(original_by_id).intersection(amended_by_id)):
                original_paragraphs = original_by_id[fid]
                amended_paragraphs = amended_by_id[fid]
                if len(original_paragraphs) != len(amended_paragraphs):
                    issues.append(
                        f"{label}: cannot validate markup strictly for footnote {fid} because paragraph count differs "
                        f"(original={len(original_paragraphs)}, amended={len(amended_paragraphs)})."
                    )
                    continue
                for idx, (original_para, amended_para) in enumerate(
                    zip(original_paragraphs, amended_paragraphs), start=1
                ):
                    paragraph_pairs.append((f"footnote {fid} paragraph {idx}", original_para, amended_para))
        else:
            original_paragraphs = _paragraphs_for_markup_validation(original_root, part)
            amended_paragraphs = _paragraphs_for_markup_validation(amended_root, part)
            if len(original_paragraphs) != len(amended_paragraphs):
                issues.append(
                    f"{label}: cannot validate markup strictly because paragraph count differs "
                    f"(original={len(original_paragraphs)}, amended={len(amended_paragraphs)})."
                )
                continue
            paragraph_pairs = [
                (f"paragraph {index}", original_para, amended_para)
                for index, (original_para, amended_para) in enumerate(
                    zip(original_paragraphs, amended_paragraphs), start=1
                )
            ]

        for location_label, original_para, amended_para in paragraph_pairs:
            original_text, _ = _paragraph_text_and_run_spans(original_para)
            amended_text, amended_spans = _paragraph_text_and_run_spans(amended_para)
            if original_text == amended_text:
                continue

            changed_ranges = _changed_char_ranges_in_new_text(original_text, amended_text)
            if not changed_ranges:
                # Deletion-only edits can legitimately have no new text spans in the
                # amended paragraph to validate for yellow-highlight markup.
                continue

            seen_runs: set[int] = set()
            for start, end in changed_ranges:
                overlapping_runs = [
                    (run, run_start, run_end)
                    for run, run_start, run_end in amended_spans
                    if run_start < end and run_end > start
                ]
                if not overlapping_runs:
                    issues.append(
                        f"{label} {location_label}: changed range ({start}-{end}) has no textual run coverage."
                    )
                    continue

                for run, _run_start, _run_end in overlapping_runs:
                    run_key = id(run)
                    if run_key in seen_runs:
                        continue
                    seen_runs.add(run_key)
                    run_text = "".join(run.xpath("./w:t/text()", namespaces=NS))
                    if run_text.strip() == "":
                        continue
                    checked_runs += 1
                    if _run_has_yellow_highlight(run):
                        continue
                    snippet = re.sub(r"\s+", " ", run_text).strip() or "<tab/br>"
                    issues.append(
                        f"{label} {location_label}: changed run is missing yellow-highlight markup ({snippet[:80]})."
                    )

    return checked_runs, issues


def _count_yellow_highlight_runs(docx_path: Path) -> int:
    total = 0
    for part in ("word/document.xml", "word/footnotes.xml"):
        root = _read_xml_part(docx_path, part)
        if root is None:
            continue
        for run in root.xpath(".//w:r", namespaces=NS):
            if not run.xpath("./w:t|./w:tab|./w:br", namespaces=NS):
                continue
            if _run_has_yellow_highlight(run):
                total += 1
    return total


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _count_unverified_in_json(obj: Any) -> int:
    if isinstance(obj, dict):
        total = 0
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() == "unverified" and isinstance(v, int):
                total += v
            total += _count_unverified_in_json(v)
        return total
    if isinstance(obj, list):
        return sum(_count_unverified_in_json(v) for v in obj)
    if isinstance(obj, str):
        return 1 if obj.strip().lower() == "unverified" else 0
    return 0


def _has_unverified_key_in_json(obj: Any) -> bool:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() == "unverified":
                return True
            if _has_unverified_key_in_json(v):
                return True
    elif isinstance(obj, list):
        return any(_has_unverified_key_in_json(v) for v in obj)
    return False


def _count_named_unverified_in_json(obj: Any, names: set[str]) -> int:
    if isinstance(obj, dict):
        total = 0
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in names and isinstance(v, int):
                total += v
            total += _count_named_unverified_in_json(v, names)
        return total
    if isinstance(obj, list):
        return sum(_count_named_unverified_in_json(v, names) for v in obj)
    return 0


def _has_named_key_in_json(obj: Any, names: set[str]) -> bool:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in names:
                return True
            if _has_named_key_in_json(v, names):
                return True
    elif isinstance(obj, list):
        return any(_has_named_key_in_json(v, names) for v in obj)
    return False


def _coerce_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _collect_int_set(value: Any) -> set[int]:
    out: set[int] = set()
    maybe_int = _coerce_nonnegative_int(value)
    if maybe_int is not None:
        out.add(maybe_int)
        return out
    if isinstance(value, list):
        for item in value:
            out.update(_collect_int_set(item))
        return out
    if isinstance(value, dict):
        for candidate in ("id", "comment_id", "docx_comment_id", "inline_comment_id", "index", "number"):
            maybe = _coerce_nonnegative_int(value.get(candidate))
            if maybe is not None:
                out.add(maybe)
        return out
    return out


def _collect_named_int_set_in_json(obj: Any, names: set[str]) -> set[int]:
    if isinstance(obj, dict):
        out: set[int] = set()
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in names:
                out.update(_collect_int_set(v))
            out.update(_collect_named_int_set_in_json(v, names))
        return out
    if isinstance(obj, list):
        out: set[int] = set()
        for item in obj:
            out.update(_collect_named_int_set_in_json(item, names))
        return out
    return set()


def _parse_ledger(ledger_path: Path) -> tuple[int | None, set[int], bool, int | None, set[int], bool]:
    text = ledger_path.read_text(encoding="utf-8", errors="replace")
    footnote_ids = {int(x) for x in re.findall(r"\bFootnote\s+(\d+)\b", text, flags=re.IGNORECASE)}
    bibliography_ids = {
        int(m.group(1) or m.group(2))
        for m in re.finditer(
            r"\bBibliography\s+Entry\s+(\d+)\b|\bReference\s+Entry\s+(\d+)\b",
            text,
            flags=re.IGNORECASE,
        )
    }

    # JSON-first parsing for structured ledgers.
    try:
        data = json.loads(text)
        parsed_unverified = _count_unverified_in_json(data)
        has_unverified = _has_unverified_key_in_json(data)
        bib_unverified_names = {"bibliography_unverified", "reference_unverified", "references_unverified"}
        parsed_bib_unverified = _count_named_unverified_in_json(data, bib_unverified_names)
        has_bib_unverified = _has_named_key_in_json(data, bib_unverified_names)
        return (
            parsed_unverified,
            footnote_ids,
            has_unverified,
            parsed_bib_unverified if has_bib_unverified else None,
            bibliography_ids,
            has_bib_unverified,
        )
    except json.JSONDecodeError:
        pass

    # Text/markdown summary parsing.
    unverified_patterns = [
        r"\bUnverified\b\s*[:=]\s*(\d+)",
        r"\bUnverified\b\s*\|\s*(\d+)",
    ]
    counts: list[int] = []
    for pat in unverified_patterns:
        counts.extend(int(m) for m in re.findall(pat, text, flags=re.IGNORECASE))

    bib_patterns = [
        r"\b(?:Bibliography|References?)\s*Unverified\b\s*[:=]\s*(\d+)",
        r"\b(?:Bibliography|References?)\s*Unverified\b\s*\|\s*(\d+)",
    ]
    bib_counts: list[int] = []
    for pat in bib_patterns:
        bib_counts.extend(int(m) for m in re.findall(pat, text, flags=re.IGNORECASE))
    if counts:
        return (
            max(counts),
            footnote_ids,
            True,
            max(bib_counts) if bib_counts else None,
            bibliography_ids,
            bool(bib_counts),
        )

    # Fall back to status rows if explicit summary is unavailable.
    status_rows = re.findall(r"\bUnverified\b", text, flags=re.IGNORECASE)
    if status_rows:
        # If only status rows exist with no numeric summary, parsing is ambiguous.
        return None, footnote_ids, True, None, bibliography_ids, False

    return None, footnote_ids, False, None, bibliography_ids, False


def _parse_quality_ledger(ledger_path: Path) -> dict[str, tuple[bool, int | None]]:
    text = ledger_path.read_text(encoding="utf-8", errors="replace")
    parsed: dict[str, tuple[bool, int | None]] = {}
    for label, numeric_patterns, signal_patterns in QUALITY_LEDGER_RULES:
        counts: list[int] = []
        for pattern in numeric_patterns:
            counts.extend(int(m) for m in re.findall(pattern, text, flags=re.IGNORECASE))
        has_signal = any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in signal_patterns)
        parsed[label] = (has_signal, max(counts) if counts else None)
    return parsed


def _parse_comment_coverage(
    ledger_path: Path,
) -> tuple[int | None, bool, set[int], set[int], int, int]:
    text = ledger_path.read_text(encoding="utf-8", errors="replace")
    docx_comment_ids = {
        int(m.group(1))
        for m in re.finditer(
            r"\b(?:DOCX|Word)\s+Comment\s*#?\s*(\d+)\b",
            text,
            flags=re.IGNORECASE,
        )
    }
    inline_comment_ids = {
        int(m.group(1))
        for m in re.finditer(
            r"\bInline\s+Comment\s*#?\s*(\d+)\b",
            text,
            flags=re.IGNORECASE,
        )
    }
    docx_comment_rows = len(
        re.findall(
            r"^\s*(?:[-*+]|\d+\.)?\s*(?:DOCX|Word)\s+Comment(?:\s*#?\s*\d+)?\s*[:\-]",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )
    inline_comment_rows = len(
        re.findall(
            r"^\s*(?:[-*+]|\d+\.)?\s*Inline\s+Comment(?:\s*#?\s*\d+)?\s*[:\-]",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )

    parsed_comment_unresolved: int | None = None
    has_comment_signal = False

    # JSON-first parsing for structured ledgers.
    try:
        data = json.loads(text)
        comment_unresolved_names = {
            "comment_unverified",
            "comments_unverified",
            "comment_unresolved",
            "comments_unresolved",
            "docx_comment_unverified",
            "docx_comments_unverified",
            "docx_comment_unresolved",
            "docx_comments_unresolved",
            "inline_comment_unverified",
            "inline_comments_unverified",
            "inline_comment_unresolved",
            "inline_comments_unresolved",
        }
        parsed_comment_unresolved = _count_named_unverified_in_json(data, comment_unresolved_names)
        has_comment_signal = _has_named_key_in_json(data, comment_unresolved_names)
        docx_comment_ids.update(
            _collect_named_int_set_in_json(
                data,
                {"docx_comment_ids", "word_comment_ids", "docx_comments", "word_comments"},
            )
        )
        inline_comment_ids.update(
            _collect_named_int_set_in_json(
                data,
                {"inline_comment_ids", "written_comment_ids", "inline_comments", "written_comments"},
            )
        )
    except json.JSONDecodeError:
        pass

    # Text/markdown summary parsing.
    comment_patterns = [
        r"\b(?:Comments?|DOCX\s+Comments?|Inline\s+Comments?)\s*(?:Unverified|Unresolved)\b\s*[:=]\s*(\d+)",
        r"\b(?:Comments?|DOCX\s+Comments?|Inline\s+Comments?)\s*(?:Unverified|Unresolved)\b\s*\|\s*(\d+)",
    ]
    comment_counts: list[int] = []
    for pat in comment_patterns:
        comment_counts.extend(int(m) for m in re.findall(pat, text, flags=re.IGNORECASE))
    if comment_counts:
        has_comment_signal = True
        numeric = max(comment_counts)
        parsed_comment_unresolved = numeric if parsed_comment_unresolved is None else max(parsed_comment_unresolved, numeric)
    elif re.search(r"\b(?:Comments?|DOCX\s+Comments?|Inline\s+Comments?)\s*(?:Unverified|Unresolved)\b", text, flags=re.IGNORECASE):
        has_comment_signal = True

    return (
        parsed_comment_unresolved,
        has_comment_signal,
        docx_comment_ids,
        inline_comment_ids,
        docx_comment_rows,
        inline_comment_rows,
    )


def _parse_target_fit_ledger(ledger_path: Path) -> tuple[bool, bool | None]:
    text = ledger_path.read_text(encoding="utf-8", errors="replace")

    try:
        data = json.loads(text)
        for key in ("target_fit", "question_fit", "benchmark_fit", "rubric_fit"):
            value = data.get(key)
            if value is None:
                continue
            if isinstance(value, str):
                normalized = value.strip().casefold()
                if normalized == "fully fits target":
                    return True, True
                if normalized in {"partially fits target", "does not yet fit target"}:
                    return True, False
            return True, None
    except json.JSONDecodeError:
        pass

    match = re.search(
        r"\b(?:Target|Question|Benchmark|Rubric)\s+Fit\b\s*[:=]\s*(Fully fits target|Partially fits target|Does not yet fit target)",
        text,
        flags=re.IGNORECASE,
    )
    if match is not None:
        verdict = match.group(1).strip().casefold()
        return True, verdict == "fully fits target"

    if re.search(r"\b(?:Target|Question|Benchmark|Rubric)\s+Fit\b", text, flags=re.IGNORECASE):
        return True, None

    return False, None


def _body_paragraph_texts(docx_path: Path) -> list[str]:
    root = _read_xml_part(docx_path, "word/document.xml")
    if root is None:
        return []
    out: list[str] = []
    for node in root.xpath("/w:document/w:body/w:p", namespaces=NS):
        text = "".join(node.xpath(".//w:t/text()", namespaces=NS)).strip()
        if text:
            out.append(text)
    return out


def _looks_like_bibliography_entry(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    normalized = _normalize_text(t)
    if normalized in BIBLIOGRAPHY_HEADINGS:
        return False
    if re.search(r"https?://", t, flags=re.IGNORECASE):
        return True
    if re.search(r"\b(v|no|case no|ftc file no|usc|f3d|reg sess|pub l no|arxiv|doi)\b", t, flags=re.IGNORECASE):
        return True
    if re.search(r"\(\d{4}\)", t):
        return True
    if "," in t and len(t.split()) >= 4:
        return True
    return False


def _count_bibliography_entries(docx_path: Path) -> int:
    paragraphs = _body_paragraph_texts(docx_path)
    if not paragraphs:
        return 0

    start_idx: int | None = None
    for i, paragraph in enumerate(paragraphs):
        if _normalize_text(paragraph) in BIBLIOGRAPHY_HEADINGS:
            start_idx = i + 1
            break
    if start_idx is None:
        return 0

    count = 0
    for paragraph in paragraphs[start_idx:]:
        if _looks_like_bibliography_entry(paragraph):
            count += 1
    return count


def _oscola_issues(
    document_text: str,
    footnotes_text: str,
    footnotes_root: etree._Element | None,
    document_root: etree._Element | None,
    *,
    check_body_short_form_case_italics: bool = False,
) -> list[str]:
    del check_body_short_form_case_italics
    issues: list[str] = []
    combined = f"{document_text}\n{footnotes_text}"

    # OSCOLA shorthand/reporter checks should apply to citation text (footnotes),
    # not general body prose where terms may be discussed descriptively.
    if re.search(r"\bIbid\b", footnotes_text):
        issues.append("Found 'Ibid' (OSCOLA requires lowercase 'ibid').")

    footnote_checks_ci = [
        (r"\bsupra\b", "Found 'supra' (not OSCOLA shorthand)."),
        (r"\bop\.?\s+cit\b", "Found 'op cit' (not OSCOLA shorthand)."),
        (r"\b\d+\s+US\s+(?:\d+|___)\b", "Found 'US' reporter format; use 'U.S.'."),
        (r"U\.S\.\s+___", "Found placeholder 'U.S. ___' where complete citation should be used."),
        (r"\*\*[^*\n]+\*\*|(?<!\*)\*[^*\n]+\*(?!\*)", "Found literal markdown emphasis markers in footnote text."),
    ]
    for pattern, message in footnote_checks_ci:
        if re.search(pattern, footnotes_text, flags=re.IGNORECASE):
            issues.append(message)

    # URL formatting can appear in footnotes or bibliography text in the body.
    url_checks = [
        (r"<\s+https?://", "Found OSCOLA URL bracket spacing issue: '< https://...>'."),
        (r"(?<!<)https?://[^\s>]+", "Found bare URL not enclosed in angle brackets."),
    ]
    for pattern, message in url_checks:
        if re.search(pattern, combined, flags=re.IGNORECASE):
            issues.append(message)

    # OSCOLA italic rules (require footnotes XML for run-level inspection)
    if footnotes_root is not None:
        try:
            from legal_doc_tools.refine_docx_from_amended import (
                _case_name_spans as _refiner_case_name_spans,
            )
        except Exception:
            try:
                from refine_docx_from_amended import (
                    _case_name_spans as _refiner_case_name_spans,
                )
            except Exception:
                _refiner_case_name_spans = None

        case_token = r"[A-Z][A-Za-z0-9&'.,()\-]*"
        case_suffix_token = r"(?:plc|ltd|limited|llc|sa|ag|nv|spa|sas|corp|corporation|inc|co|company|gmbh|llp|lp|bv|sarl)"
        case_joiner = rf"(?:[A-Z][A-Za-z0-9&'.,()\-]*|{case_suffix_token}|of|the|and|for|de|la|le|del|du|van|von|da|di|al)"
        case_v_re = re.compile(
            rf"\b{case_token}(?:\s+{case_joiner})*\s+v\s+{case_token}(?:\s+{case_joiner})*(?=\s*(?:\[\d{{4}}|\(\d{{4}}|[.;,]|$))"
        )
        ship_name_re = re.compile(
            rf"\bThe\s+{case_token}(?:\s+{case_token}){{0,3}}(?=\s*(?:\[[0-9]{{4}}\]|\([0-9]{{4}}\)))"
        )
        re_case_re = re.compile(
            rf"\b(?:In\s+re|Re)\s+{case_token}(?:\s+{case_joiner})*(?=\s*(?:\[\d{{4}}|\(\d{{4}}|[.;,]|$))"
        )
        short_case_crossref_re = re.compile(
            rf"\b({case_token}(?:\s+{case_joiner})*)\s*\(n\s+(\d+)\)",
            flags=re.IGNORECASE,
        )
        corporate_suffixes = {
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
        procedural_descriptor_words = {
            "application",
            "brief",
            "claim",
            "complaint",
            "consent",
            "decision",
            "decree",
            "defence",
            "draft",
            "filing",
            "injunction",
            "judgment",
            "motion",
            "notice",
            "opinion",
            "order",
            "petition",
            "reply",
            "settlement",
            "statement",
        }

        def normalize_case_name(text: str) -> str:
            collapsed = re.sub(r"\s+", " ", text).strip(" \t\n\r;:,.")
            collapsed = collapsed.replace("’", "'")
            return collapsed.casefold()

        def strip_corporate_suffixes(text: str) -> str:
            tokens = re.split(r"\s+", text.strip())
            while tokens:
                tail = re.sub(r"[.,;:]+$", "", tokens[-1]).casefold()
                if tail not in corporate_suffixes:
                    break
                tokens.pop()
            return " ".join(tokens).strip()

        def case_variants(text: str) -> set[str]:
            cleaned = re.sub(r"\s+", " ", text).strip(" \t\n\r;:,.")
            if not cleaned:
                return set()
            variants = {normalize_case_name(cleaned)}
            stripped = strip_corporate_suffixes(cleaned)
            if stripped and stripped != cleaned:
                variants.add(normalize_case_name(stripped))
            return {variant for variant in variants if variant}

        def trim_case_span_procedural_suffix(text: str, start: int, end: int) -> int:
            snippet = text[start:end]
            if "," not in snippet:
                return end
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
                if words and any(word in procedural_descriptor_words for word in words):
                    break
                consumed_len += len(part) + 1
                rebuilt = snippet[:consumed_len]
            return start + len(rebuilt.rstrip(" \t\n\r,;:."))

        case_refs_by_id = _build_footnote_case_reference_map(footnotes_root)

        ibid_italic_count = 0
        case_not_italic_count = 0
        case_not_italic_samples: list[str] = []

        for fn in footnotes_root.xpath(".//w:footnote", namespaces=NS):
            fn_id = fn.get(f"{{{NS['w']}}}id")
            if fn_id in ("-1", "0"):
                continue

            for para in fn.xpath("./w:p", namespaces=NS):
                runs = para.xpath("./w:r", namespaces=NS)
                if not runs:
                    continue

                run_data = _footnote_run_data(para)

                full_text = "".join(t for t, _, _, _ in run_data)
                if not full_text.strip():
                    continue

                # Check 1: ibid must NOT be italic
                for m in re.finditer(r"\bibid\b", full_text, flags=re.IGNORECASE):
                    for _, is_italic, rs, re_end in run_data:
                        if rs < m.end() and re_end > m.start() and is_italic:
                            ibid_italic_count += 1
                            break

                # Check 2-4: case names and valid short-form case cross-references
                # MUST be italic, but only within the case-name span itself.
                if _refiner_case_name_spans is not None:
                    case_spans = _refiner_case_name_spans(
                        full_text,
                        case_reference_names_by_footnote=case_refs_by_id,
                    )
                else:
                    case_spans = []
                    for m in case_v_re.finditer(full_text):
                        case_spans.append((m.start(), trim_case_span_procedural_suffix(full_text, m.start(), m.end())))
                    for pattern in (ship_name_re, re_case_re):
                        for m in pattern.finditer(full_text):
                            case_spans.append((m.start(), m.end()))
                    for m in short_case_crossref_re.finditer(full_text):
                        candidate = normalize_case_name(m.group(1))
                        ref_id = int(m.group(2))
                        if candidate in case_refs_by_id.get(ref_id, set()):
                            case_spans.append((m.start(1), m.end(1)))

                for case_start, case_end in case_spans:
                    span_italic = True
                    for _, is_italic, rs, re_end in run_data:
                        if rs < case_end and re_end > case_start:
                            if not is_italic:
                                span_italic = False
                                break
                    if not span_italic and case_not_italic_count < 3:
                        case_not_italic_samples.append(
                            f"FN {fn_id}: '{full_text[case_start:case_end].strip()[:50]}'"
                        )
                    if not span_italic:
                        case_not_italic_count += 1

        footnote_doctrinal_not_italic_count = 0
        footnote_doctrinal_not_italic_samples: list[str] = []

        for footnote in footnotes_root.xpath("/w:footnotes/w:footnote[@w:id>=1]", namespaces=NS):
            fn_id = footnote.get(f"{{{W_NS}}}id") or "?"
            for paragraph in footnote.xpath("./w:p", namespaces=NS):
                run_data = _footnote_run_data(paragraph)
                full_text = "".join(t for t, _, _, _ in run_data)
                if not full_text.strip():
                    continue

                for start, end in _legal_latin_phrase_spans(full_text):
                    span_italic = True
                    for _, is_italic, rs, re_end in run_data:
                        if rs < end and re_end > start:
                            if not is_italic:
                                span_italic = False
                                break
                    if span_italic:
                        continue
                    if footnote_doctrinal_not_italic_count < 3:
                        footnote_doctrinal_not_italic_samples.append(
                            f"FN {fn_id}: '{full_text[start:end].strip()[:50]}'"
                        )
                    footnote_doctrinal_not_italic_count += 1

        if ibid_italic_count > 0:
            issues.append(
                f"Found {ibid_italic_count} italicized 'ibid' occurrence(s) "
                f"(OSCOLA requires non-italic)."
            )
        if case_not_italic_count > 0:
            samples_str = "; ".join(case_not_italic_samples)
            issues.append(
                f"Found {case_not_italic_count} case name(s) not italicised in footnotes "
                f"(OSCOLA requires italic case names). Samples: {samples_str}"
            )
        if footnote_doctrinal_not_italic_count > 0:
            samples_str = "; ".join(footnote_doctrinal_not_italic_samples)
            issues.append(
                f"Found {footnote_doctrinal_not_italic_count} footnote doctrinal / legal-Latin span(s) "
                f"not italicised (samples: {samples_str})."
            )

    if document_root is not None:
        case_reference_names_by_footnote = _build_footnote_case_reference_map(footnotes_root)
        body_not_italic_count = 0
        body_not_italic_samples: list[str] = []

        in_bibliography = False
        in_table_of_cases = False
        for para_idx, paragraph in enumerate(document_root.xpath("/w:document/w:body//w:p", namespaces=NS), start=1):
            run_data = _body_run_data(paragraph)
            full_text = "".join(text for text, _is_italic, _start, _end in run_data)
            if not full_text.strip():
                continue

            normalized_heading = _normalize_text(full_text)
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
            elif in_table_of_cases and not _looks_like_table_of_cases_entry(full_text):
                in_table_of_cases = False

            if in_table_of_cases:
                continue

            spans = (
                _legal_latin_phrase_spans(full_text)
                if in_bibliography
                else _body_case_name_spans(
                    full_text,
                    case_reference_names_by_footnote=case_reference_names_by_footnote,
                    body_case_reference_names=set(),
                )
            )
            for start, end in spans:
                if _span_is_fully_italicized(run_data, start, end):
                    continue
                if body_not_italic_count < 4:
                    body_not_italic_samples.append(
                        f"P{para_idx}: '{full_text[start:end].strip()[:60]}'"
                    )
                body_not_italic_count += 1

        if body_not_italic_count > 0:
            samples_str = "; ".join(body_not_italic_samples)
            issues.append(
                f"Found {body_not_italic_count} body-text case name / doctrinal phrase span(s) not italicised "
                f"(samples: {samples_str})."
            )

    return issues


def _print_header(title: str) -> None:
    print(f"[gate] {title}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate mandatory delivery runtime gates.")
    parser.add_argument("--mode", required=True, help="review | review+amend | amend")
    parser.add_argument("--report", help="Path to report DOCX artifact.")
    parser.add_argument("--amended", help="Path to amended DOCX artifact.")
    parser.add_argument("--original", help="Path to original DOCX for footnote-ID parity checks.")
    parser.add_argument("--active-style", default="OSCOLA", help="Citation style name. Default: OSCOLA.")
    parser.add_argument(
        "--based-on-comments",
        action="store_true",
        help="Enable mandatory comment-coverage checks when delivery is based on DOCX/inline comments.",
    )
    parser.add_argument(
        "--verification-ledger",
        help=(
            "Path to verification ledger/report (json/md/txt). Mandatory for amend and review+amend, "
            "and must include explicit sentence-level, footnote, bibliography, and quality evidence."
        ),
    )
    parser.add_argument(
        "--benchmark-provided",
        action="store_true",
        help=(
            "Require explicit target-fit evidence in the verification ledger because the user supplied "
            "a question, prompt, rubric, or other benchmark."
        ),
    )
    parser.add_argument(
        "--check-body-short-form-case-italics",
        action="store_true",
        help=(
            "Deprecated no-op kept for backwards compatibility. Bare body-text "
            "short-form case names are no longer auto-enforced by the OSCOLA gate."
        ),
    )
    args = parser.parse_args(argv)

    errors: list[str] = []
    mode = _normalize_mode(args.mode)
    style = args.active_style.strip().lower()

    report = Path(args.report).expanduser() if args.report else None
    amended = Path(args.amended).expanduser() if args.amended else None
    original = Path(args.original).expanduser() if args.original else None
    ledger = Path(args.verification_ledger).expanduser() if args.verification_ledger else None

    if mode in {"review+amend", "amend"} and amended is not None and original is not None:
        if amended.expanduser().resolve() == original.expanduser().resolve():
            errors.append(
                "Amended artifact path cannot be the same as original artifact path. "
                "Non-destructive copy-first rule requires a new output DOCX path."
            )

    _print_header(f"Mode = {mode}")

    # Gate 1: required artifacts by mode.
    _print_header("Checking required artifacts")
    if mode == "review":
        if report is None:
            errors.append("review mode requires --report.")
        else:
            _assert_docx(report, "Report artifact", errors)
    elif mode == "review+amend":
        if report is None:
            errors.append("review+amend mode requires --report.")
        else:
            _assert_docx(report, "Report artifact", errors)
        if amended is None:
            errors.append("review+amend mode requires --amended.")
        else:
            _assert_docx(amended, "Amended artifact", errors)
    elif mode == "amend":
        if amended is None:
            errors.append("amend mode requires --amended.")
        else:
            _assert_docx(amended, "Amended artifact", errors)

    # Gate 1B: output location must be Desktop root (not inside subfolders).
    _print_header(f"Checking output location rule ({DESKTOP_ROOT})")
    if mode in {"review", "review+amend"} and report is not None:
        if not _is_desktop_root_output(report):
            errors.append(
                "Report artifact must be saved directly in Desktop root "
                f"({DESKTOP_ROOT}), not inside a folder: {report}"
            )
        else:
            print(f"[gate] Report artifact location OK: {report}")
    if mode in {"review+amend", "amend"} and amended is not None:
        if not _is_desktop_root_output(amended):
            errors.append(
                "Amended artifact must be saved directly in Desktop root "
                f"({DESKTOP_ROOT}), not inside a folder: {amended}"
            )
        else:
            print(f"[gate] Amended artifact location OK: {amended}")

    # Gate 1C: if using versioned naming, amended artifact must be the latest version.
    if mode in {"review+amend", "amend"} and amended is not None:
        if original is None:
            errors.append("Latest-version gate requires --original in amend modes.")
        else:
            selected_version = _extract_version_for_original(amended, original)
            if selected_version is None:
                print("[gate] Amended artifact naming is non-versioned; latest-version check skipped.")
            else:
                highest_version = _highest_version_for_original_in_desktop(original)
                if highest_version is not None and selected_version < highest_version:
                    errors.append(
                        "Amended artifact must use the latest versioned output in Desktop. "
                        f"Selected v{selected_version}, latest is v{highest_version}."
                    )
                else:
                    print(f"[gate] Amended artifact version OK: v{selected_version} (latest available).")

    # Gate 2: Unverified must be zero for amend modes (derived from ledger only).
    if mode in {"review+amend", "amend"}:
        _print_header("Checking verification gate (Unverified == 0)")
        if ledger is None:
            errors.append("amend modes require --verification-ledger.")
            unverified = None
            ledger_footnotes: set[int] = set()
            bibliography_unverified = None
            ledger_bibliography_entries: set[int] = set()
            has_bibliography_unverified_signal = False
        elif not ledger.exists():
            errors.append(f"Verification ledger does not exist: {ledger}")
            unverified = None
            ledger_footnotes = set()
            bibliography_unverified = None
            ledger_bibliography_entries = set()
            has_bibliography_unverified_signal = False
        else:
            (
                unverified,
                ledger_footnotes,
                has_unverified_signal,
                bibliography_unverified,
                ledger_bibliography_entries,
                has_bibliography_unverified_signal,
            ) = _parse_ledger(ledger)
            if not has_unverified_signal:
                errors.append("Verification ledger is missing an explicit 'Unverified' summary/value.")
            if unverified is None:
                errors.append("Could not parse numeric Unverified count from verification ledger.")
            else:
                print(f"[gate] Unverified count = {unverified}")
                if unverified != 0:
                    errors.append(f"Unverified must be 0 for amend delivery (got {unverified}).")

            quality_checks = _parse_quality_ledger(ledger)
            for label, (has_signal, numeric_value) in quality_checks.items():
                if not has_signal:
                    errors.append(f"Verification ledger is missing an explicit '{label}' summary/value.")
                    continue
                if numeric_value is None:
                    errors.append(f"Could not parse numeric {label} count from verification ledger.")
                    continue
                print(f"[gate] {label} count = {numeric_value}")
                if numeric_value != 0:
                    errors.append(f"{label} must be 0 for amend delivery (got {numeric_value}).")

            if args.benchmark_provided:
                has_target_fit_signal, fully_fits_target = _parse_target_fit_ledger(ledger)
                if not has_target_fit_signal:
                    errors.append(
                        "Verification ledger is missing explicit target-fit evidence "
                        "(for example 'Target Fit: Fully fits target')."
                    )
                elif fully_fits_target is None:
                    errors.append("Could not parse a target-fit verdict from verification ledger.")
                elif not fully_fits_target:
                    errors.append(
                        "Target-fit verdict must be 'Fully fits target' when a benchmark/question is provided."
                    )
                else:
                    print("[gate] Target-fit verdict = Fully fits target")

    # Gate 3: footnote numbering integrity.
    if mode in {"review+amend", "amend"} and amended is not None:
        _print_header("Checking footnote numbering integrity")
        if original is None:
            errors.append("Footnote numbering gate requires --original in amend modes.")
        else:
            _assert_docx(original, "Original artifact", errors)
            if not errors:
                original_ids = _extract_footnote_ids(original)
                amended_ids = _extract_footnote_ids(amended)
                original_set = set(original_ids)
                amended_set = set(amended_ids)
                missing_original_ids = sorted(original_set - amended_set)
                extra_ids = sorted(amended_set - original_set)
                max_original = max(original_ids, default=0)
                expected_extra_ids = (
                    list(range(max_original + 1, max_original + 1 + len(extra_ids)))
                    if extra_ids
                    else []
                )

                if missing_original_ids:
                    errors.append(
                        "Amended output is missing original footnote IDs "
                        f"(missing {len(missing_original_ids)} ids, sample: {missing_original_ids[:10]})."
                    )
                elif extra_ids and extra_ids != expected_extra_ids:
                    errors.append(
                        "Additional footnotes must be appended sequentially after the original set "
                        f"(expected extras {expected_extra_ids[:10]}, got {extra_ids[:10]})."
                    )
                else:
                    if extra_ids:
                        print(
                            "[gate] Original footnote IDs preserved "
                            f"({len(original_ids)} original IDs; {len(extra_ids)} new sequential IDs added)."
                        )
                    else:
                        print(f"[gate] Footnote IDs unchanged ({len(original_ids)} IDs).")
                if ledger is not None and ledger.exists():
                    missing = amended_set - ledger_footnotes
                    if missing:
                        sample = sorted(missing)[:10]
                        errors.append(
                            "Verification ledger does not cover all amended footnotes. "
                            f"Missing {len(missing)} footnote IDs, sample: {sample}"
                        )
                    else:
                        print(f"[gate] Verification ledger covers all {len(amended_ids)} amended footnotes.")

                for issue in _validate_footnote_reference_integrity(original, amended):
                    errors.append(f"Footnote integrity failed: {issue}")

    # Gate 3B: markup enforcement for amended wording.
    if mode in {"review+amend", "amend"} and amended is not None:
        _print_header("Checking amendment markup rule (yellow highlight)")
        if original is None:
            errors.append("Markup gate requires --original in amend modes.")
        else:
            _assert_docx(original, "Original artifact", errors)
            if original.exists() and amended.exists():
                original_markup = _count_yellow_highlight_runs(original)
                amended_markup = _count_yellow_highlight_runs(amended)
                print(
                    "[gate] Yellow-highlighted runs "
                    f"(original={original_markup}, amended={amended_markup})."
                )
                checked_runs, markup_issues = _validate_markup_hard_rule(original, amended)
                print(f"[gate] Changed amended runs checked for strict markup: {checked_runs}")
                if checked_runs == 0:
                    errors.append(
                        "Amended output must contain detectable changed wording with yellow highlight markup."
                    )
                for issue in markup_issues:
                    errors.append(f"Markup hard-rule violation: {issue}")

    # Gate 4: bibliography/reference coverage for amend modes.
    if mode in {"review+amend", "amend"} and original is not None and original.exists():
        _print_header("Checking bibliography/reference verification coverage")
        expected_bibliography_entries = _count_bibliography_entries(original)
        if expected_bibliography_entries > 0:
            print(f"[gate] Bibliography/reference entries detected: {expected_bibliography_entries}")
            if ledger is None or not ledger.exists():
                errors.append("Bibliography/reference coverage check requires --verification-ledger.")
            else:
                if not has_bibliography_unverified_signal:
                    errors.append(
                        "Verification ledger is missing explicit 'Bibliography Unverified' or 'Reference Unverified' summary."
                    )
                if bibliography_unverified is None:
                    errors.append(
                        "Could not parse numeric bibliography/reference unverified count from verification ledger."
                    )
                elif bibliography_unverified != 0:
                    errors.append(
                        "Bibliography/reference unverified count must be 0 for amend delivery "
                        f"(got {bibliography_unverified})."
                    )

                expected_ids = set(range(1, expected_bibliography_entries + 1))
                missing_bibliography_entries = expected_ids - ledger_bibliography_entries
                if missing_bibliography_entries:
                    sample = sorted(missing_bibliography_entries)[:10]
                    errors.append(
                        "Verification ledger does not cover all bibliography/reference entries. "
                        f"Missing {len(missing_bibliography_entries)} entries, sample: {sample}"
                    )
                else:
                    print(
                        f"[gate] Verification ledger covers all {expected_bibliography_entries} bibliography/reference entries."
                    )
        else:
            print("[gate] No bibliography/reference section detected in original DOCX.")

    # Gate 5: citation style checks.
    if mode in {"review+amend", "amend"} and amended is not None and amended.exists():
        _print_header(f"Checking citation style rules ({style})")
        footnotes_root = _read_xml_part(amended, "word/footnotes.xml")
        document_root = _read_xml_part(amended, "word/document.xml")
        footnotes_text = _xml_text(footnotes_root)
        document_text = _xml_text(document_root)
        if style == "oscola":
            issues = _oscola_issues(
                document_text,
                footnotes_text,
                footnotes_root,
                document_root,
            )
            if issues:
                for issue in issues:
                    errors.append(f"OSCOLA check failed: {issue}")
            else:
                print("[gate] OSCOLA checks passed.")
        else:
            print("[gate] Non-OSCOLA style selected; only artifact/verification/footnote gates enforced.")

    # Gate 6: comment-driven coverage checks.
    if args.based_on_comments:
        _print_header("Checking comment-driven coverage")
        if original is None:
            errors.append("Comment-driven gate requires --original.")
        else:
            _assert_docx(original, "Original artifact", errors)
            if original.exists() and original.suffix.lower() == ".docx":
                try:
                    original_docx_comment_ids = set(_extract_docx_comment_ids(original))
                    original_inline_comments = _extract_inline_written_comments(original)
                except zipfile.BadZipFile:
                    errors.append(f"Original artifact is not a valid DOCX/zip package: {original}")
                    original_docx_comment_ids = set()
                    original_inline_comments = []

                expected_docx_comments = len(original_docx_comment_ids)
                expected_inline_comments = len(original_inline_comments)
                if expected_docx_comments == 0 and expected_inline_comments == 0:
                    print("[gate] No DOCX/inline comments detected in original DOCX.")
                else:
                    print(
                        "[gate] Comment review scope detected: "
                        f"{expected_docx_comments} DOCX comments, {expected_inline_comments} inline written comments."
                    )
                    if ledger is None:
                        errors.append(
                            "Comment-driven delivery requires --verification-ledger with comment coverage."
                        )
                    elif not ledger.exists():
                        errors.append(f"Verification ledger does not exist: {ledger}")
                    else:
                        (
                            comments_unresolved,
                            has_comment_signal,
                            ledger_docx_comment_ids,
                            ledger_inline_comment_ids,
                            ledger_docx_comment_rows,
                            ledger_inline_comment_rows,
                        ) = _parse_comment_coverage(ledger)
                        if not has_comment_signal:
                            errors.append(
                                "Verification ledger is missing explicit comment summary (for example 'Comments Unresolved: 0')."
                            )
                        if comments_unresolved is None:
                            errors.append(
                                "Could not parse numeric comment unresolved count from verification ledger."
                            )
                        elif comments_unresolved != 0:
                            errors.append(
                                "Comment unresolved/unverified count must be 0 for comment-based delivery "
                                f"(got {comments_unresolved})."
                            )

                        if expected_docx_comments > 0:
                            if ledger_docx_comment_ids:
                                missing = original_docx_comment_ids - ledger_docx_comment_ids
                                if missing:
                                    sample = sorted(missing)[:10]
                                    errors.append(
                                        "Verification ledger does not cover all DOCX comments. "
                                        f"Missing {len(missing)} comment IDs, sample: {sample}"
                                    )
                                else:
                                    print(
                                        f"[gate] Verification ledger covers all {expected_docx_comments} DOCX comments."
                                    )
                            elif ledger_docx_comment_rows < expected_docx_comments:
                                errors.append(
                                    "Verification ledger does not include enough DOCX comment entries. "
                                    f"Expected {expected_docx_comments}, found {ledger_docx_comment_rows}."
                                )

                        if expected_inline_comments > 0:
                            inline_covered = (
                                len(ledger_inline_comment_ids)
                                if ledger_inline_comment_ids
                                else ledger_inline_comment_rows
                            )
                            if inline_covered < expected_inline_comments:
                                errors.append(
                                    "Verification ledger does not include enough inline written comment entries. "
                                    f"Expected {expected_inline_comments}, found {inline_covered}."
                                )
                            else:
                                print(
                                    f"[gate] Verification ledger covers inline written comments ({inline_covered}/{expected_inline_comments})."
                                )

    if errors:
        print("\nGATE CHECK: FAIL")
        for i, err in enumerate(errors, start=1):
            print(f"{i}. {err}")
        return 1

    print("\nGATE CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
