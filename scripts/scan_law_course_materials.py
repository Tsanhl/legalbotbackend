#!/usr/bin/env python3
"""
Inventory course-led law materials without extracting private content.

The script is intentionally non-destructive by default. It prints a JSON
summary to stdout and only writes a file if --json-output is supplied.
Displayed paths are sanitised to avoid exposing local usernames.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


SUBJECT_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("law_medicine", ("law and medicine", "medical", "abortion", "transplant", "hfea", "consent")),
    ("competition_law", ("competition", "antitrust", "article 101", "article 102", "dma")),
    ("pensions_law", ("pension", "barber", "occupational scheme")),
    ("private_international_law", ("private international", "conflict of laws", "rome i", "rome ii", "brussels")),
    ("land_law", ("land law", "tolata", "easement", "overriding", "leasehold")),
    ("trusts_law", ("trust", "equity", "fiduciary", "tracing")),
    ("contract_law", ("contract", "consideration", "misrepresentation", "duress")),
    ("commercial_law", ("commercial", "sale of goods", "nemo dat", "retention of title")),
    ("criminal_law", ("criminal", "homicide", "theft", "robbery", "sentencing")),
    ("family_law", ("family", "children act", "financial remedy", "welfare")),
    ("tort_law", ("tort", "negligence", "nuisance", "defamation")),
    ("eu_law", ("eu law", "free movement", "direct effect", "supremacy")),
    ("public_international_law", ("public international", "state responsibility", "ihl", "immunity", "use of force")),
    ("evidence_law", ("evidence", "hearsay", "bad character", "confession")),
    ("tax_law", ("tax", "vat", "capital gains", "ramsay")),
    ("intellectual_property_law", ("intellectual property", "copyright", "patent", "trade mark", "trademark")),
    ("biolaw_ai_data", ("biolaw", "data protection", "artificial intelligence", "ai", "gdpr", "robotics")),
    ("mediation_law", ("mediation", "adr", "settlement")),
    ("public_law", ("constitutional", "admin law", "judicial review", "planning law", "human rights")),
    ("business_law", ("business law", "company law", "directors", "insolvency", "partnership")),
)

PURPOSE_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("lecture_outline", ("outline", "handout")),
    ("lecture_slide", ("lecture", "slides", "ppt")),
    ("tutorial", ("tutorial", "seminar", "questions")),
    ("exam_guidance", ("exam", "examination", "question", "summative")),
    ("feedback", ("feedback", "formative", "marked", " ms", "- ms")),
    ("statute", ("act 19", "act 20", "regulations", "code of practice", "statute")),
    ("case", (" v ", "judgment", "ewca", "ewhc", "uksc", "ac ", "qb ", "wlr")),
    ("commentary", ("journal", "review", "chapter", "book", "article", "press")),
)

def default_roots() -> List[Path]:
    desktop = Path.home() / "Desktop"
    return [
        desktop / "Law",
        desktop / "Law and medicine",
        Path.cwd() / "Law resouces  copy 2",
    ]


def normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("_", " ").replace("-", " ")).strip().lower()


def sanitise_path(path: Path) -> str:
    ext = path.suffix.lower() or "no-extension"
    return f"[{ext} file path redacted]"


def classify_subject(path: Path) -> str:
    haystack = normalise_text(" ".join(path.parts[-5:]))
    hits: List[Tuple[int, str]] = []
    for subject, patterns in SUBJECT_PATTERNS:
        score = sum(1 for pattern in patterns if pattern in haystack)
        if score:
            hits.append((score, subject))
    if not hits:
        return "general"
    hits.sort(key=lambda item: (-item[0], item[1]))
    return hits[0][1]


def classify_purpose(path: Path) -> str:
    haystack = normalise_text(path.name)
    for purpose, patterns in PURPOSE_PATTERNS:
        if any(pattern in haystack for pattern in patterns):
            return purpose
    return "resource"


def iter_files(roots: Iterable[Path]) -> Iterable[Path]:
    allowed = {".pdf", ".docx", ".doc", ".ppt", ".pptx", ".txt", ""}
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix.lower() in allowed:
                yield root
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in allowed:
                yield path


def build_inventory(roots: Iterable[Path]) -> Dict[str, Any]:
    seen = set()
    by_subject: Dict[str, Counter[str]] = defaultdict(Counter)
    examples: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    total = 0
    duplicates = 0

    for path in iter_files(roots):
        try:
            stat = path.stat()
        except OSError:
            continue
        dedupe_key = (normalise_text(path.name), stat.st_size)
        if dedupe_key in seen:
            duplicates += 1
            continue
        seen.add(dedupe_key)

        total += 1
        subject = classify_subject(path)
        purpose = classify_purpose(path)
        ext = path.suffix.lower() or "[no extension]"
        by_subject[subject][purpose] += 1
        by_subject[subject][ext] += 1

        if len(examples[subject]) < 12:
            examples[subject].append({
                "path": sanitise_path(path),
                "purpose": purpose,
                "extension": ext,
            })

    return {
        "total_unique_files": total,
        "deduplicated_files_skipped": duplicates,
        "subjects": {
            subject: {
                "counts": dict(counter),
                "examples": examples.get(subject, []),
            }
            for subject, counter in sorted(by_subject.items())
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory law course/index materials by subject and purpose.")
    parser.add_argument("roots", nargs="*", type=Path, help="Optional roots to scan; defaults to Desktop law folders and indexed resources.")
    parser.add_argument("--json-output", type=Path, help="Optional path to write the JSON inventory.")
    args = parser.parse_args()

    roots = args.roots or default_roots()
    inventory = build_inventory(roots)
    output = json.dumps(inventory, indent=2, ensure_ascii=False)
    if args.json_output:
        args.json_output.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
