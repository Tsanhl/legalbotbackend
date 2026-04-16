#!/usr/bin/env python3
"""
Generate a DOCX review report from plain text or markdown-like input.

This script is intentionally lightweight so agents can always emit a report
artifact (`.docx`) as a mandatory deliverable.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

DESKTOP_ROOT = (Path.home() / "Desktop").resolve()


def _is_numbered(line: str) -> bool:
    i = 0
    while i < len(line) and line[i].isdigit():
        i += 1
    return i > 0 and i + 1 < len(line) and line[i] == "." and line[i + 1] == " "


def _strip_markdown_inline(text: str) -> str:
    # Remove common markdown wrappers while preserving readable plain text.
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text


def _strip_numeric_prefix(text: str) -> str:
    # "12. Something" -> "Something"
    return re.sub(r"^\s*\d+\.\s+", "", text)


def _normalize_ledger_item(text: str) -> str:
    """
    Normalize citation-ledger line labels so DOCX output is clean:
    - [n] ...
    - Footnote xx: ...
    - [Number]. ...
    """
    t = _strip_markdown_inline(text).strip()
    t = _strip_numeric_prefix(t)
    t = t.strip()

    # If line starts like "[12]. ..." preserve exactly.
    if re.match(r"^\[\d+\]\.\s+", t):
        return t
    # If line starts like "[12] ..." preserve exactly.
    if re.match(r"^\[\d+\]\s+", t):
        return t
    # If line starts like "Footnote 12..." preserve.
    if re.match(r"^Footnote\s+\d+\b", t, flags=re.IGNORECASE):
        return t
    return t


def build_docx(input_text: str, out_path: Path) -> None:
    doc = Document()
    in_ledger = False

    for raw in input_text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            doc.add_paragraph("")
            continue

        if stripped.startswith("# "):
            doc.add_heading(stripped[2:].strip(), level=1)
            continue
        if stripped.startswith("## "):
            heading = _strip_markdown_inline(stripped[3:].strip())
            doc.add_heading(heading, level=2)
            in_ledger = "verification ledger" in heading.lower()
            continue
        if stripped.startswith("### "):
            heading = _strip_markdown_inline(stripped[4:].strip())
            doc.add_heading(heading, level=3)
            in_ledger = "verification ledger" in heading.lower()
            continue
        if stripped.startswith("- "):
            doc.add_paragraph(_strip_markdown_inline(stripped[2:].strip()), style="List Bullet")
            continue
        if _is_numbered(stripped):
            item = _strip_numeric_prefix(stripped)
            item = _normalize_ledger_item(item) if in_ledger else _strip_markdown_inline(item)
            doc.add_paragraph(item, style="List Number")
            continue

        doc.add_paragraph(_strip_markdown_inline(line))

    # Enforce report typography: Calibri, 12pt throughout.
    for style_name in (
        "Normal",
        "Heading 1",
        "Heading 2",
        "Heading 3",
        "List Bullet",
        "List Number",
    ):
        try:
            doc.styles[style_name].font.name = "Calibri"
            doc.styles[style_name].font.size = Pt(12)
        except KeyError:
            pass

    for para in doc.paragraphs:
        for run in para.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(12)
            if run._element.rPr is not None:
                run._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
                run._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
                run._element.rPr.rFonts.set(qn("w:cs"), "Calibri")
                run._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")

    doc.save(out_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate DOCX review report from text/markdown."
    )
    parser.add_argument("--input", required=True, help="Path to .md/.txt report input")
    parser.add_argument("--out", required=True, help="Path to output .docx")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if out_path.parent != DESKTOP_ROOT:
        raise ValueError(
            "Output report must be written directly to Desktop root "
            f"({DESKTOP_ROOT}), not inside a folder: {out_path}"
        )
    if out_path.suffix.lower() != ".docx":
        raise ValueError(f"Output report must be a .docx file: {out_path}")

    text = input_path.read_text(encoding="utf-8")
    build_docx(text, out_path)
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
