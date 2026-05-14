#!/usr/bin/env python3
"""
Print the backend legal quality audit suite and prompt-layer gate checks.

This is a no-LLM dry audit by default. It is intended for quick QA after guide
or prompt changes: it confirms that the key prompts route to the expected
quality gates before anyone spends time reviewing live model output.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legal_answer_quality_controls import (  # noqa: E402
    GOLDEN_OUTPUT_AUDIT_SUITE,
    LIVE_PROMPT_AUDIT_SUITE,
    build_golden_output_audit_prompt,
    build_live_prompt_audit_checklist,
)
from backend_answer_runtime import build_sqe2_marking_prompt, build_sqe_question_set_prompt  # noqa: E402
from model_applicable_service import (  # noqa: E402
    _build_legal_answer_quality_gate,
    _build_local_code_rag_answer_prompt_block,
    _infer_retrieval_profile,
    _infer_subject_guide_slug,
)


def _check_prompt(prompt: str) -> dict[str, object]:
    profile = _infer_retrieval_profile(prompt)
    slug = _infer_subject_guide_slug(str(profile.get("topic") or ""), prompt)
    block = _build_local_code_rag_answer_prompt_block(prompt, enforce_long_response_split=False)
    gate = _build_legal_answer_quality_gate(prompt, profile)
    low = prompt.lower()
    sqe2_block = ""
    if "sqe2" in low or "sqe 2" in low:
        if "mark" in low:
            sqe2_block = build_sqe2_marking_prompt(
                question=prompt,
                candidate_answer="[dry-audit candidate answer placeholder]",
                enquiry=prompt,
            )
        else:
            sqe2_block = build_sqe_question_set_prompt(prompt, exam_stage="sqe2")
    combined = f"{block}\n{gate}\n{sqe2_block}"
    return {
        "topic": profile.get("topic"),
        "subject_guide": slug,
        "has_subject_template": "[SUBJECT TEMPLATE" in combined,
        "has_source_quality_gate": "[SOURCE QUALITY PRIORITY GATE]" in combined,
        "has_anti_generic_gate": "[ANSWER SPECIFICITY / ANTI-GENERIC GATE]" in combined,
        "has_freshness_gate": "[CURRENT-LAW / FRESHNESS GATE]" in combined,
        "has_law_medicine_mode": "[LAW AND MEDICINE SOURCE MODE:" in combined,
        "has_sqe2_loop": "[SQE2 HARD PRACTICE + MARKING LOOP]" in combined,
    }


def main() -> int:
    print(build_golden_output_audit_prompt())
    print()
    print(build_live_prompt_audit_checklist())
    print()
    print("[PROMPT-LAYER DRY AUDIT]")
    for item in list(GOLDEN_OUTPUT_AUDIT_SUITE) + list(LIVE_PROMPT_AUDIT_SUITE):
        prompt = str(item["prompt"])
        result = _check_prompt(prompt)
        print(f"- {item['name']}: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
