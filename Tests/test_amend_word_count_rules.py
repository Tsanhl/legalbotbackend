from pathlib import Path

from lxml import etree

from legal_doc_tools.amend_docx import _enforce_review_context_word_count


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _doc_with_word_count(word_count: int) -> etree._Element:
    text = ("word " * max(1, int(word_count))).strip()
    return etree.fromstring(
        f"""<w:document xmlns:w="{WORD_NS}">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
  </w:body>
</w:document>"""
    )


_enforce_review_context_word_count(
    source=Path("."),
    amended_doc_root=_doc_with_word_count(3985),
    review_context={
        "word_count_mode": "at_or_below_max",
        "max_word_count": 4000,
    },
)

try:
    _enforce_review_context_word_count(
        source=Path("."),
        amended_doc_root=_doc_with_word_count(4000),
        review_context={
            "word_count_mode": "at_or_below_max",
            "max_word_count": 4000,
        },
    )
    raise AssertionError("Expected at_or_below_max enforcement failure.")
except ValueError as exc:
    assert "requested 4000-word cap" in str(exc)

_enforce_review_context_word_count(
    source=Path("."),
    amended_doc_root=_doc_with_word_count(2475),
    review_context={
        "word_count_mode": "near_target",
        "target_word_count": 2500,
    },
)

try:
    _enforce_review_context_word_count(
        source=Path("."),
        amended_doc_root=_doc_with_word_count(2469),
        review_context={
            "word_count_mode": "near_target",
            "target_word_count": 2500,
        },
    )
    raise AssertionError("Expected near_target enforcement failure.")
except ValueError as exc:
    assert "requested 2500-word target" in str(exc)

print("Amend word-count rule regression passed.")
