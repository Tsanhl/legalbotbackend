#!/usr/bin/env python3
"""
Run live backend QA prompts through the canonical chat/API entrypoints.

This script performs real model calls when a backend provider key is available.
It writes output artifacts to /private/tmp and prints only summaries/checks.

Privacy guard: live runs can send prompts plus retrieved RAG/course-material
context to the configured external model provider. For that reason, real model
calls require:

    LEGAL_AI_LIVE_AUDIT_SEND_EXTERNAL=1

Without that explicit opt-in, the script exits before generation.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend_answer_runtime import (  # noqa: E402
    send_complete_answer_with_docs,
    send_sqe2_marking_with_docs,
    send_sqe_question_set_with_docs,
)


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text or ""))


def _contains_any(text: str, needles: List[str]) -> bool:
    low = (text or "").lower()
    return any(n.lower() in low for n in needles)


def _no_source_leakage(text: str) -> bool:
    low = (text or "").lower()
    leaked_markers = [
        "/users/",
        "/desktop/",
        "rag context",
        "retrieved chunk",
        "source path",
        "law resouces",
        "learnultra",
    ]
    return not any(marker in low for marker in leaked_markers)


def _score_output(name: str, text: str) -> Dict[str, Any]:
    checks: Dict[str, bool] = {}
    low = (text or "").lower()
    if name == "law_medicine_course_bound":
        checks = {
            "uses_course_mode": _contains_any(text, ["course-bound", "module syllabus", "within the syllabus", "syllabus"]),
            "uses_focused_examples": _contains_any(text, ["two", "three", "focused example", "examples"]),
            "has_statutory_route": _contains_any(text, ["MCA 2005", "Abortion Act", "Human Tissue Act", "HFEA", "statutory"]),
            "avoids_obvious_excluded_drift": not _contains_any(text, ["Montgomery v Lanarkshire", "clinical negligence", "mental health law", "deprivation of liberty"]),
            "no_source_leakage": _no_source_leakage(text),
        }
    elif name == "law_medicine_no_limit":
        checks = {
            "labels_wider_material": _contains_any(text, ["wider", "beyond the module", "no syllabus", "not confined", "broader"]),
            "has_current_law_caution": _contains_any(text, ["current", "verify", "as at", "recent", "status"]),
            "has_statutory_route": _contains_any(text, ["MCA 2005", "Abortion Act", "Human Tissue Act", "HFEA", "statutory"]),
            "not_generic_summary": _contains_any(text, ["the better view", "therefore", "because", "reform"]),
            "no_source_leakage": _no_source_leakage(text),
        }
    elif name == "competition_article_102":
        checks = {
            "separates_dominance": "dominance" in low,
            "identifies_abuse_theory": _contains_any(text, ["self-preferencing", "refusal", "tying", "foreclosure", "abuse theory"]),
            "uses_effects_evidence": _contains_any(text, ["effects", "foreclosure", "counterfactual", "evidence"]),
            "addresses_objective_justification": "objective justification" in low or "efficiencies" in low,
            "states_remedy": _contains_any(text, ["remedy", "penalty", "fine", "enforcement", "commitment"]),
            "no_source_leakage": _no_source_leakage(text),
        }
    elif name == "sqe2_task":
        checks = {
            "is_practical_task": all(token in low for token in ["candidate instructions", "client/matter facts", "documents/extracts", "specific task"]),
            "substantive_length": _word_count(text) >= 300,
            "withholds_answers": not _contains_any(text, ["model answer", "correct answer", "marking points"]),
            "harder_than_sample": _contains_any(text, ["professional conduct", "missing", "ambiguity", "timing", "trap"]),
            "no_source_leakage": _no_source_leakage(text),
        }
    elif name == "sqe2_marking":
        checks = {
            "starts_marking_result": low.strip().startswith("sqe2 marking result"),
            "uses_criteria": _contains_any(text, ["criterion", "criteria", "A-F", "score", "subtotal"]),
            "has_corrected_answer": _contains_any(text, ["corrected", "model answer", "high-scoring", "outline"]),
            "has_next_targeted_practice": "next targeted practice" in low,
            "no_source_leakage": _no_source_leakage(text),
        }
    return {
        "word_count": _word_count(text),
        "checks": checks,
        "passed": bool(checks) and all(checks.values()),
    }


def _response_text(response: Any) -> str:
    if isinstance(response, tuple) and response:
        return str(response[0] or "")
    return str(response or "")


def main() -> int:
    _load_env_file(ROOT / ".env.local")
    if os.getenv("LEGAL_AI_LIVE_AUDIT_SEND_EXTERNAL", "").strip().lower() not in {"1", "true", "yes"}:
        print("[LIVE AUDIT BLOCKED]")
        print("Real live audit would send prompts plus retrieved local RAG/course-material context to the configured external model provider.")
        print("Set LEGAL_AI_LIVE_AUDIT_SEND_EXTERNAL=1 only after explicit user approval for that data flow.")
        print("For no-model prompt-layer checks, run: PYTHONPATH=. python3 scripts/run_legal_quality_audit.py")
        return 3

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("/private/tmp") / f"legal_runtime_audit_{run_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = [
        {
            "name": "law_medicine_course_bound",
            "kind": "complete",
            "prompt": (
                "Law and Medicine - Essay Question. Stay within the module syllabus. "
                "Critically examine whether English law protects bodily autonomy adequately. "
                "Use two or three focused syllabus examples only. Return about 850 words."
            ),
        },
        {
            "name": "law_medicine_no_limit",
            "kind": "complete",
            "prompt": (
                "Law and Medicine broad-all / no syllabus limit essay. Critically examine bodily autonomy "
                "across English medical law. Label wider material and note current-law sensitivity. Return about 850 words."
            ),
        },
        {
            "name": "competition_article_102",
            "kind": "complete",
            "prompt": (
                "Competition Law - Problem Question. Advise a digital platform on Article 102 / Chapter II risk "
                "where it gives its own service preferential ranking, restricts rival data access, and argues "
                "quality-control efficiencies. Address dominance, abuse theory, effects, objective justification, "
                "enforcement and remedy. Return about 850 words."
            ),
        },
        {
            "name": "sqe2_task",
            "kind": "sqe2_task",
            "prompt": (
                "Give me an SQE2 legal research practical task, harder than the sample, in Dispute Resolution. "
                "Do not reveal the answer because I will answer later."
            ),
        },
        {
            "name": "sqe2_marking",
            "kind": "sqe2_marking",
            "question": (
                "SQE2 legal research task: You act for a defendant charged with ABH against a neighbour. "
                "The only eyewitness is the defendant's spouse, who gave a police statement but now refuses to attend. "
                "Advise whether the prosecution can compel the spouse and whether the statement may be admitted."
            ),
            "candidate_answer": (
                "The spouse is competent and the prosecution can probably force attendance because ABH is serious. "
                "The police statement can be used if the spouse does not attend. The client should speak to the spouse "
                "to ask them not to come to court."
            ),
        },
    ]

    results: List[Dict[str, Any]] = []
    for case in cases:
        name = case["name"]
        print(f"[LIVE AUDIT] Running {name}...")
        if case["kind"] == "complete":
            response, rag_context = send_complete_answer_with_docs(
                api_key="",
                message=case["prompt"],
                documents=[],
                project_id=f"live_audit_{run_id}_{name}",
                history=[],
                stream=False,
                provider="auto",
                output_mode="chat",
                strict_complete_answer_verification=False,
            )
            text = _response_text(response)
        elif case["kind"] == "sqe2_task":
            response, rag_context = send_sqe_question_set_with_docs(
                api_key="",
                enquiry=case["prompt"],
                documents=[],
                project_id=f"live_audit_{run_id}_{name}",
                history=[],
                stream=False,
                provider="auto",
                exam_stage="sqe2",
                include_default_samples=True,
                output_mode="chat",
            )
            text = _response_text(response)
        else:
            response, rag_context = send_sqe2_marking_with_docs(
                api_key="",
                question=case["question"],
                candidate_answer=case["candidate_answer"],
                documents=[],
                project_id=f"live_audit_{run_id}_{name}",
                history=[],
                stream=False,
                provider="auto",
                skill="legal research",
                practice_area="Criminal Litigation",
                output_mode="chat",
            )
            text = _response_text(response)

        score = _score_output(name, text)
        result = {
            "name": name,
            "kind": case["kind"],
            "score": score,
            "output_file": str(out_dir / f"{name}.md"),
            "rag_chars": len(rag_context or ""),
        }
        (out_dir / f"{name}.md").write_text(text, encoding="utf-8")
        results.append(result)
        print(f"[LIVE AUDIT] {name}: passed={score['passed']} words={score['word_count']} checks={score['checks']}")

    summary = {
        "run_id": run_id,
        "out_dir": str(out_dir),
        "results": results,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[LIVE AUDIT] Saved outputs to {out_dir}")
    return 0 if all(item["score"]["passed"] for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
