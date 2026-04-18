"""
Test the intelligent part division system
"""

from model_applicable_service import (
    detect_long_essay,
    _resolve_long_response_info,
    _finalize_model_output_text,
    detect_essay_core_policy_violation,
    detect_unit_structure_policy_violation,
    get_dynamic_chunk_count,
)
from model_applicable_service import LONG_RESPONSE_PART_WORD_CAP

print("=" * 80)
print("INTELLIGENT PART DIVISION SYSTEM - TEST")
print("=" * 80)

test_cases = [
    ("Write a 6000 word essay on contract law", 6000),
    ("Write a 8000 word essay on tort law", 8000),
    ("Write a 10000 word essay on criminal law", 10000),
    ("Write a 12000 word essay on EU law", 12000),
    ("Write a 16000 word essay on human rights", 16000),
    ("Write a 20000 word dissertation on medical law", 20000),
    ("Write a 24000 word dissertation on property law", 24000),
    ("Write a 40000 word thesis on international law", 40000),
]

for prompt, expected_words in test_cases:
    result = detect_long_essay(prompt)
    print(f"\n{'=' * 80}")
    print(f"📝 REQUEST: {expected_words:,} words")
    print(f"{'=' * 80}")
    print(f"Suggested parts: {result['suggested_parts']}")
    print(f"Words per part: ~{result['words_per_part']:,}")
    print(f"Total: {result['suggested_parts']} × {result['words_per_part']:,} = {result['suggested_parts'] * result['words_per_part']:,} words")
    print(f"\n📋 Recommendation Message:")
    print(result['suggestion_message'])
    
    # Validate
    words_per_part = result['words_per_part']
    if words_per_part > LONG_RESPONSE_PART_WORD_CAP:
        raise AssertionError(f"Per-part cap violated: {words_per_part} > {LONG_RESPONSE_PART_WORD_CAP}")
    if expected_words > 2000 and not result['is_long_essay']:
        raise AssertionError("Expected long-essay split for >2,000 words, but is_long_essay=False")
    if expected_words <= 2000 and result['is_long_essay']:
        raise AssertionError("Did not expect split for ≤2,000 words, but is_long_essay=True")
    print(f"\n✅ OK: Each part ≤ {LONG_RESPONSE_PART_WORD_CAP:,} words")

print("\n" + "=" * 80)
print("ADDITIONAL PARSING CHECKS")
print("=" * 80)

# Exactly 4000 should still be treated as long/splittable workflow metadata.
exact_4000 = detect_long_essay("Write a 4000 words essay on constitutional law")
print(f"4000 words -> is_long_essay={exact_4000['is_long_essay']}, requested={exact_4000['requested_words']}")
assert exact_4000["requested_words"] == 4000
assert exact_4000["is_long_essay"] is True

# Mixed transcript should resolve to the latest active test segment.
mixed_prompt = """
test
4500 words
QUESTION 1 ...
Will Continue to next part, say continue

test again
2000 words
QUESTION 2 ...
"""
mixed = detect_long_essay(mixed_prompt)
print(f"Mixed transcript -> active targets={mixed.get('active_word_targets')}, requested={mixed.get('requested_words')}")
assert mixed.get("requested_words") == 2000
assert mixed.get("active_word_targets") == [2000]

# Multi-question long answers should not mix Question 1 and Question 2 inside one response part.
multi_q_prompt = """
4500 words
1. Public Law – Problem Question (Prerogative Powers and Separation of Powers)
Facts for question 1.

2. Equity – Problem Question (Undue Influence and Gifts to Caregivers)
Facts for question 2.
"""
multi_q = detect_long_essay(multi_q_prompt)
print(f"Multi-question split -> mode={multi_q.get('split_mode')}, parts={multi_q.get('suggested_parts')}")
assert multi_q.get("split_mode") == "by_units"
assert multi_q.get("suggested_parts", 0) >= 4
assert all(len(d.get("question_indices") or []) == 1 for d in (multi_q.get("deliverables") or []))

# Direct code/backend usage should keep long answers as one-shot unless the website opts into split enforcement.
direct_long = _resolve_long_response_info("Write a 4500 word essay on constitutional law", enforce_long_response_split=False)
website_long = _resolve_long_response_info("Write a 4500 word essay on constitutional law", enforce_long_response_split=True)
print(
    "Direct-vs-website split policy:",
    {"direct_is_long": direct_long.get("is_long_essay"), "website_is_long": website_long.get("is_long_essay")}
)
assert direct_long.get("requested_words") == 4500
assert direct_long.get("is_long_essay") is False
assert direct_long.get("split_disabled_for_direct_use") is True
assert website_long.get("is_long_essay") is True

direct_chunks = get_dynamic_chunk_count(
    "Write a 4500 word essay on constitutional law",
    enforce_long_response_split=False,
)
website_chunks = get_dynamic_chunk_count(
    "Write a 4500 word essay on constitutional law",
    enforce_long_response_split=True,
)
print("Direct-vs-website retrieval chunks:", {"direct": direct_chunks, "website": website_chunks})
assert 28 <= direct_chunks <= 40
assert website_chunks <= 20
assert direct_chunks > website_chunks

# Finalizer should keep exactly one end marker at the end and drop stray bare subsection markers.
dirty_output = """Part I: Introduction

Analysis paragraph.

A.

(End of Answer)

More leaked text

(End of Answer)
"""
cleaned = _finalize_model_output_text(dirty_output)
print(f"Normalized ending -> {cleaned.splitlines()[-1]}")
assert cleaned.count("(End of Answer)") == 1
assert cleaned.endswith("(End of Answer)")
assert "\nA.\n" not in f"\n{cleaned}\n"

with open("model_applicable_service.py", "r", encoding="utf-8") as fh:
    gemini_src = fh.read()
assert 'Each NEW MAJOR issue cluster expressly asked by the question MUST start under its OWN Part-numbered subtitle' in gemini_src

# Finalizer should repair common continuation artefacts from the user's failing sample.
messy_continuation = """Part II: Continued Analysis

A. Issue
The

primary issue to determine is the remedy point.

The rule of law dictates that the government and all other public bodies are strictly bound by the law, which includes legislation enacted by Parliament

enacted by Parliament. If the executive requires the statutory framework to be amended, it must return to Parliament.

D. Conclusion
The claimants are highly likely to secure a declaration that the suspension of.

Will Continue to next part, say continue
"""
messy_cleaned = _finalize_model_output_text(messy_continuation)
print("Cleaned continuation sample:", messy_cleaned)
assert "The\n\nprimary issue" not in messy_cleaned
assert "enacted by Parliament enacted by Parliament" not in messy_cleaned
assert "suspension of." in messy_cleaned  # cleanup should not invent content
assert messy_cleaned.endswith("Will Continue to next part, say continue")

inline_subheading = """Part III: Burglary

Some analysis under section 9(1). D. Conclusion
Dan is highly likely to be liable.
"""
inline_cleaned = _finalize_model_output_text(inline_subheading)
print("Inline subheading cleanup:", inline_cleaned)
assert "section 9(1). D. Conclusion" not in inline_cleaned
assert "\n\nD. Conclusion\n\nDan is highly likely to be liable." in inline_cleaned

# Essay-core validator should catch continuation restarts and broken OSCOLA placement.
essay_cont_restart = """Part II: Introduction

This section restarts improperly.
"""
violates, reason = detect_essay_core_policy_violation(
    essay_cont_restart,
    is_continuation=True,
)
print("Essay continuation restart:", violates, reason)
assert violates is True
assert "introduction" in reason.lower()

essay_missing_immediate_cite = (
    "The leading authority is Caparo Industries plc v Dickman. "
    "It establishes the modern duty framework."
)
violates, reason = detect_essay_core_policy_violation(essay_missing_immediate_cite)
print("Essay missing immediate cite:", violates, reason)
assert violates is True
assert "immediate oscola" in reason.lower()

essay_detached_cite = """Caparo establishes the modern duty framework.

(Caparo Industries plc v Dickman [1990] 2 AC 605 (HL))
"""
violates, reason = detect_essay_core_policy_violation(essay_detached_cite)
print("Essay detached citation:", violates, reason)
assert violates is True
assert "citation-only paragraph" in reason.lower()

essay_good = """Part I: Introduction

Caparo Industries plc v Dickman ([1990] 2 AC 605 (HL)) frames the modern duty analysis.

Part V: Conclusion

The duty issue should therefore be resolved cautiously.
"""
violates, reason = detect_essay_core_policy_violation(
    essay_good,
    is_short_single_essay=True,
    require_part_v_conclusion=True,
)
print("Essay clean sample:", violates, reason)
assert violates is False

essay_wrong_continuation_shape = """Question 1: Company Law – Essay Question

Part V: Continued Analysis

A. Issue

This should not happen in an essay continuation.
"""
violates, reason = detect_unit_structure_policy_violation(
    essay_wrong_continuation_shape,
    unit_kind="essay",
    require_question_heading=True,
    expected_question_number=1,
    is_same_topic_continuation=True,
)
print("Essay continuation structure:", violates, reason)
assert violates is True
assert "continued analysis" in reason.lower() or "irac" in reason.lower()

essay_good_continuation = """Question 1: Company Law – Essay Question

Part V: Protection of Shareholders and Creditors in Practice

The analysis now turns to the practical adequacy of the managed-conflict model.
"""
violates, reason = detect_unit_structure_policy_violation(
    essay_good_continuation,
    unit_kind="essay",
    require_question_heading=True,
    expected_question_number=1,
    is_same_topic_continuation=True,
)
print("Essay good continuation structure:", violates, reason)
assert violates is False

pb_missing_part_section = """Question 2: Land Law – Problem Question

Part I: Introduction

A. Issue

The threshold issue is whether the agreement created a lease.
"""
violates, reason = detect_unit_structure_policy_violation(
    pb_missing_part_section,
    unit_kind="problem",
    require_question_heading=True,
    expected_question_number=2,
    is_same_topic_continuation=False,
)
print("Problem missing Part section:", violates, reason)
assert violates is True
assert (
    "part-numbered" in reason.lower()
    or "part i: introduction" in reason.lower()
    or "roadmap" in reason.lower()
)

employment_pb_missing_part_section = """Question 1: Discrimination / Employment Law – Problem Question

Part I: Introduction

The central legal issue concerns Amira's request to reduce her hours.

A. Issue

The first issue is whether her claim sounds in equal pay or indirect discrimination.
"""
violates, reason = detect_unit_structure_policy_violation(
    employment_pb_missing_part_section,
    unit_kind="problem",
    require_question_heading=True,
    expected_question_number=1,
    is_same_topic_continuation=False,
)
print("Employment PB missing Part II:", violates, reason)
assert violates is True
assert (
    "part-numbered" in reason.lower()
    or "part i: introduction" in reason.lower()
    or "roadmap" in reason.lower()
)

wrong_question_continuation = """Question 1: Discrimination / Employment Law – Problem Question

Part III: Further Analysis

A. Issue

The employer's justification defence must now be considered.
"""
violates, reason = detect_unit_structure_policy_violation(
    wrong_question_continuation,
    unit_kind="problem",
    require_question_heading=True,
    expected_question_number=2,
    is_same_topic_continuation=False,
)
print("Wrong question continuation:", violates, reason)
assert violates is True
assert "wrong question heading" in reason.lower()

stray_continued_before_new_question = """Part V: Continued Analysis

Question 2: Land Law – Problem Question

Part I: Introduction

Body.
"""
stripped = _finalize_model_output_text(stray_continued_before_new_question)
print("Stripped stray continued-analysis heading:", stripped.splitlines()[:4])
assert not stripped.startswith("Part V: Continued Analysis")
assert stripped.startswith("Question 2: Land Law – Problem Question")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
print("\nKey Observations:")
print("- Requests >2,000 words are split into parts")
print("- Each part is capped at 2,000 words")
print("- System provides a per-part plan for continuation")
