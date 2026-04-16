from __future__ import annotations

import math
import re
from typing import Any, Optional


WORD_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’&./-]*")
WORD_COUNT_NUMBER_RE = r"(\d{1,2},?\d{3,4}|\d{3,5})"
WORD_COUNT_UNIT_RE = r"(?:words?|wrods?)"
AMEND_TARGET_SHORTFALL_WORDS = 30
PRESERVE_ORIGINAL_DRIFT_RATIO = 0.02
PRESERVE_ORIGINAL_MIN_DRIFT_WORDS = 30

_MAX_WORD_COUNT_PATTERNS = tuple(
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in (
        rf"\b(?:max(?:imum)?|under|below|within|up to|at most|no more than|not more than|keep within|cap(?:ped)? at|limit(?:ed)? to)\s+{WORD_COUNT_NUMBER_RE}\s*{WORD_COUNT_UNIT_RE}\b",
        rf"\b{WORD_COUNT_NUMBER_RE}\s*{WORD_COUNT_UNIT_RE}\s*(?:max(?:imum)?|cap(?:ped)?|limit(?:ed)?|ceiling)\b",
    )
)
_TARGET_WORD_COUNT_PATTERNS = tuple(
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in (
        rf"\b(?:target|aim for|around|about|approximately|approx\.?|roughly|exactly)\s+{WORD_COUNT_NUMBER_RE}\s*{WORD_COUNT_UNIT_RE}\b",
    )
)
_GENERIC_WORD_COUNT_PATTERN = re.compile(
    rf"\b{WORD_COUNT_NUMBER_RE}\s*{WORD_COUNT_UNIT_RE}\b",
    flags=re.IGNORECASE,
)


def count_words_for_targeting(text: str) -> int:
    return len(WORD_TOKEN_RE.findall(text or ""))


def count_words_for_targeting_from_texts(texts: list[str]) -> int:
    return count_words_for_targeting("\n".join(texts))


def complete_word_count_floor(target_words: int) -> int:
    target = max(1, int(target_words or 0))
    return min(target, max(1, int(math.ceil(target * 0.99))))


def complete_word_count_window(target_words: int) -> tuple[int, int]:
    target = max(1, int(target_words or 0))
    return complete_word_count_floor(target), target


def amend_requested_word_count_window(requested_words: int) -> tuple[int, int]:
    requested = max(1, int(requested_words or 0))
    upper = max(1, requested - 1)
    lower = max(1, requested - AMEND_TARGET_SHORTFALL_WORDS)
    if lower > upper:
        lower = upper
    return lower, upper


def preserve_original_length_window(original_words: int) -> tuple[int, int]:
    original = max(1, int(original_words or 0))
    drift = max(
        PRESERVE_ORIGINAL_MIN_DRIFT_WORDS,
        int(math.ceil(original * PRESERVE_ORIGINAL_DRIFT_RATIO)),
    )
    return max(1, original - drift), original + drift


def _coerce_word_count(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    cleaned = re.sub(r"[^\d]", "", str(raw))
    if not cleaned:
        return None
    value = int(cleaned)
    if value < 300:
        return None
    return value


def extract_requested_word_count_rule(text: str) -> Optional[dict[str, int | str]]:
    source = text or ""

    max_matches: list[tuple[int, int]] = []
    for pattern in _MAX_WORD_COUNT_PATTERNS:
        for match in pattern.finditer(source):
            count = _coerce_word_count(match.group(1))
            if count is None:
                continue
            max_matches.append((match.end(), count))
    if max_matches:
        _, count = max(max_matches, key=lambda item: item[0])
        lower, upper = amend_requested_word_count_window(count)
        return {
            "mode": "at_or_below_max",
            "count": count,
            "lower_bound": lower,
            "upper_bound": upper,
        }

    target_matches: list[tuple[int, int]] = []
    for pattern in _TARGET_WORD_COUNT_PATTERNS:
        for match in pattern.finditer(source):
            count = _coerce_word_count(match.group(1))
            if count is None:
                continue
            target_matches.append((match.end(), count))
    if target_matches:
        _, count = max(target_matches, key=lambda item: item[0])
        lower, upper = amend_requested_word_count_window(count)
        return {
            "mode": "near_target",
            "count": count,
            "lower_bound": lower,
            "upper_bound": upper,
        }

    generic_matches = [
        (match.end(), count)
        for match in _GENERIC_WORD_COUNT_PATTERN.finditer(source)
        if (count := _coerce_word_count(match.group(1))) is not None
    ]
    if not generic_matches:
        return None

    _, count = max(generic_matches, key=lambda item: item[0])
    lower, upper = amend_requested_word_count_window(count)
    return {
        "mode": "near_target",
        "count": count,
        "lower_bound": lower,
        "upper_bound": upper,
    }
