#!/usr/bin/env python3
"""
Local-only difficult prompt sampling for the legal answer backend.

This does not call an external model. It compiles the real backend prompt through
`send_message_with_docs()` while replacing final model generation with a local
capture stub, so guide injection, routing, word-count policy, RAG policy, and
search-fallback instructions can be audited safely.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import model_applicable_service as service


SAMPLES: List[Dict[str, Any]] = [
    {
        "id": "1500_evidence_hearsay",
        "words": 1500,
        "subject": "Evidence / Criminal Evidence",
        "expected_topic": "criminal_evidence_hearsay",
        "prompt": """Evidence Law - Essay Question

Write 1500 words. Critically evaluate whether the modern law on hearsay evidence in criminal proceedings strikes the right balance between evidential flexibility and fairness to the accused.

In your answer, consider the Criminal Justice Act 2003 gateways, reliability, the absent-witness problem, Article 6 ECHR, judicial directions, exclusionary discretion, and whether reform should make reliability a stronger threshold requirement.""",
        "must_compile_terms": ["hearsay", "Article 6", "Criminal Justice Act 2003"],
    },
    {
        "id": "2000_land_registered_family_home",
        "words": 2000,
        "subject": "Land Law",
        "expected_topic": "land_home_coownership_estoppel_priority",
        "prompt": """Land Law - Problem Question

Write 2000 words. A is the sole registered proprietor of a house. B has lived there for eight years, paid for major renovations, cared for A's disabled sibling, and says A repeatedly promised that "this is really our home and half will be yours". A later grants a legal charge to Bank C. B was visibly living in the house when C's agent inspected, but C made no enquiries. Advise B and C.

In your answer, consider common intention constructive trusts, proprietary estoppel, actual occupation, overriding interests, overreaching, inquiry, priority, and the likely remedy.""",
        "must_compile_terms": ["actual occupation", "constructive trust", "proprietary estoppel"],
    },
    {
        "id": "2500_law_medicine_end_of_life",
        "words": 2500,
        "subject": "Law and Medicine",
        "expected_topic": "medical_end_of_life_mca2005",
        "prompt": """Law and Medicine - Problem Question

Write 2500 words. P has advanced motor neurone disease. Six months ago, while capacitous, P signed and witnessed a document refusing clinically assisted nutrition and hydration if P lost capacity and could no longer communicate. P now lacks capacity. P's partner says P changed their mind informally before losing capacity, but clinicians are unsure. P's adult child insists treatment must continue because P is not dying immediately. Advise the hospital.

In your answer, consider contemporaneous refusal, advance decisions, validity and applicability, Mental Capacity Act 2005 best interests, CANH, family views, court involvement, and the limits of assisted dying arguments.""",
        "must_compile_terms": ["Mental Capacity Act 2005", "advance", "best interests"],
    },
    {
        "id": "3000_competition_digital_platform",
        "words": 3000,
        "subject": "Competition Law",
        "expected_topic": "competition_margin_squeeze_refusal",
        "prompt": """Competition Law - Essay/Problem Question

Write 3000 words. Critically evaluate the best abuse-of-dominance theory against a dominant app-store operator that requires developers to use its payment rail, gives its own cloud-gaming service preferential search placement, restricts rivals' access to real-time performance analytics, and argues that all measures are justified by platform security and investment incentives.

In your answer, consider market definition, dominance, self-preferencing, tying, refusal to supply or constructive refusal, indispensability, effects-based analysis, objective justification, remedies, and over-enforcement risks.""",
        "must_compile_terms": ["Article 102", "dominance", "objective justification"],
    },
    {
        "id": "3500_private_international_parallel_claims",
        "words": 3500,
        "subject": "Private International Law",
        "expected_topic": "private_international_law_post_brexit",
        "prompt": """Private International Law - Problem Question

Write 3500 words. An English manufacturer contracts with a French distributor under a non-exclusive English jurisdiction clause and English law clause. Performance takes place partly in Germany. The distributor sues in France alleging pre-contractual misrepresentation made in Paris and anti-competitive termination. The manufacturer starts English proceedings for debt and seeks an anti-suit injunction. Advise on jurisdiction, applicable law, and strategy.

In your answer, consider the post-Brexit jurisdiction framework, service out, forum conveniens, Hague Choice of Court Convention, anti-suit relief, Rome I, Rome II, tort/contract classification, mandatory rules, and parallel proceedings.""",
        "must_compile_terms": ["Rome I", "Rome II", "Hague Choice of Court"],
    },
    {
        "id": "4000_tax_avoidance_gaar",
        "words": 4000,
        "subject": "Tax Law",
        "expected_topic": "tax_avoidance_gaar",
        "prompt": """Tax Law - Essay Question

Write 4000 words. Critically evaluate whether modern UK tax avoidance doctrine has moved from respecting legal form to prioritising economic substance.

In your answer, consider the Westminster principle, Ramsay-style purposive construction, statutory interpretation, certainty, taxpayer autonomy, HMRC powers, the General Anti-Abuse Rule, targeted anti-avoidance rules, and whether the current balance is principled or too uncertain.""",
        "must_compile_terms": ["Westminster", "Ramsay", "General Anti-Abuse Rule"],
    },
    {
        "id": "4500_public_international_proxy_force",
        "words": 4500,
        "subject": "Public International Law",
        "expected_topic": "public_international_law_use_of_force",
        "prompt": """Public International Law - Problem/Essay Question

Write 4500 words. State A funds, trains, equips, and provides intelligence to an armed group operating from State A's territory. The group launches repeated cross-border attacks into State B. State B conducts air strikes inside State A against the group and some State A military facilities. State A argues that the strikes violate Article 2(4) of the UN Charter. State B claims self-defence.

Critically evaluate the legality of State B's response under Article 51 of the UN Charter. In your answer, consider attribution, effective control, armed attack, necessity, proportionality, unwilling or unable arguments, evidence problems, state responsibility, and systemic risks of over-expanding self-defence.""",
        "must_compile_terms": ["Article 2(4)", "Article 51", "attribution"],
    },
    {
        "id": "6000_public_law_planning_human_rights",
        "words": 6000,
        "subject": "Public Law / Planning Law",
        "expected_topic": "generic_planning_law",
        "prompt": """Planning and Public Law - Problem Question

Write 6000 words. A local planning authority grants permission for a large waste-processing facility beside a residential estate. The development plan supports industrial uses on part of the site but also protects residential amenity. The officer's report relies heavily on the National Planning Policy Framework and a late noise report uploaded the night before the committee meeting. Objectors say they had a legitimate expectation of consultation under the authority's published statement of community involvement. The committee grants permission with conditions on operating hours and noise monitoring but gives brief reasons. Residents seek to challenge the decision.

Advise the residents. In your answer, consider Town and Country Planning Act 1990 section 70(2), Planning and Compulsory Purchase Act 2004 section 38(6), the development plan, material considerations, NPPF weight, planning conditions, legitimate expectation, reasons, procedural fairness, irrationality, statutory review/judicial review route, remedies, and the limits of merits review.""",
        "must_compile_terms": ["section 70(2)", "section 38(6)", "NPPF"],
    },
]


def all_topic_samples() -> List[Dict[str, Any]]:
    """Build compile-audit samples from the full routing matrix."""
    from Tests.test_full_topic_routing_matrix import ROUTING_CASES

    samples: List[Dict[str, Any]] = []
    for index, case in enumerate(ROUTING_CASES, start=1):
        topic = str(case["topic"])
        prompt = str(case["prompt"])
        profile = service._infer_retrieval_profile(prompt)
        must_terms = [
            str(term)
            for term in (profile.get("must_cover") or [])
            if str(term).strip()
        ][:3]
        samples.append(
            {
                "id": f"alltopic_{index:03d}_{topic}",
                "words": int(service._extract_requested_word_count(prompt) or 2000),
                "subject": topic,
                "expected_topic": topic,
                "prompt": prompt,
                "must_compile_terms": must_terms,
                "require_subject_guide": False,
            }
        )
    return samples


def _fake_answer_for_prompt(full_message: str) -> str:
    if "Problem Question" in full_message or "Advise" in full_message:
        return (
            "Part I: Introduction\n\n"
            "Captured prompt only.\n\n"
            "Part II: Liability / Remedies\n\n"
            "Captured prompt only.\n\n"
            "Part III: Final Conclusion\n\n"
            "Captured prompt only.\n\n"
            "(End of Answer)"
        )
    return (
        "Part I: Introduction\n\n"
        "Captured prompt only.\n\n"
        "Part II: Core Analysis\n\n"
        "Captured prompt only.\n\n"
        "Part III: Conclusion\n\n"
        "Captured prompt only.\n\n"
        "(End of Answer)"
    )


def _fake_rag(query: str, max_chunks: int = 0, query_type: Optional[str] = None) -> str:
    return (
        "[RAG CONTEXT - INTERNAL - DO NOT OUTPUT]\n"
        f"Query type: {query_type or 'unknown'}.\n"
        f"Chunk budget: {max_chunks}.\n"
        "Authority: Example Authority [2024] UKSC 1.\n"
        "Notes: indexed retrieval placeholder for safe compile-only sampling.\n"
        "[END RAG CONTEXT]"
    )


def _capture_compiled_prompt(sample: Dict[str, Any], *, real_rag: bool) -> Dict[str, Any]:
    captured: List[Dict[str, Any]] = []

    def fake_local_adapter(
        *,
        full_message: str,
        system_instruction: str,
        history: Optional[List[Dict[str, Any]]],
        project_id: str,
        allow_web_search: bool,
    ) -> str:
        captured.append(
            {
                "full_message": full_message,
                "system_instruction": system_instruction,
                "history": history or [],
                "project_id": project_id,
                "allow_web_search": allow_web_search,
            }
        )
        return _fake_answer_for_prompt(full_message)

    original_rag_available = service.RAG_AVAILABLE
    original_get_relevant_context = service.get_relevant_context
    original_find_codex_cli = service._find_codex_cli
    original_local_adapter = service._generate_with_codex_local_adapter
    original_allow_env = os.environ.get("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED")
    try:
        service.RAG_AVAILABLE = True
        if not real_rag:
            service.get_relevant_context = _fake_rag
        service._find_codex_cli = lambda: "codex"
        service._generate_with_codex_local_adapter = fake_local_adapter
        os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = "1"
        (response_text, _response_meta), rag_context = service.send_message_with_docs(
            api_key="",
            message=sample["prompt"],
            documents=[],
            project_id=f"real_output_sampling::{sample['id']}",
            history=[],
            stream=False,
            provider="auto",
            model_name=None,
            enforce_long_response_split=False,
        )
    finally:
        service.RAG_AVAILABLE = original_rag_available
        service.get_relevant_context = original_get_relevant_context
        service._find_codex_cli = original_find_codex_cli
        service._generate_with_codex_local_adapter = original_local_adapter
        if original_allow_env is None:
            os.environ.pop("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED", None)
        else:
            os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = original_allow_env

    return {
        "response_text": response_text,
        "rag_context": rag_context,
        "compiled": captured[0] if captured else {},
    }


def audit_sample(sample: Dict[str, Any], *, real_rag: bool = False) -> Dict[str, Any]:
    prompt = sample["prompt"]
    profile = service._infer_retrieval_profile(prompt)
    detected_topic = profile.get("topic")
    query_type = service.detect_query_type(prompt, [])
    chunk_count = service.get_dynamic_chunk_count(prompt, [], enforce_long_response_split=False)
    word_target = int(service._extract_requested_word_count(prompt) or 0)
    long_info = service.detect_long_essay(prompt)
    subject_guide = service._subject_guide_excerpt_for_query(prompt, profile, max_lines=24)
    compiled_info = _capture_compiled_prompt(sample, real_rag=real_rag)
    full_message = str((compiled_info.get("compiled") or {}).get("full_message") or "")

    must_compile_terms = [term for term in sample["must_compile_terms"] if str(term).strip()]
    subject_guide_present = "[SUBJECT GUIDE" in subject_guide or "[SUBJECT GUIDE" in full_message
    topic_guidance_present = "focus:" in full_message.lower() or "Issue-bank" in full_message
    checks = {
        "topic_matches": detected_topic == sample["expected_topic"],
        "word_target_matches": word_target == sample["words"],
        "chunk_count_positive": chunk_count > 0,
        "guidance_present": subject_guide_present or topic_guidance_present,
        "local_answer_mode_present": "[LOCAL CODE + RAG LEGAL ANSWER MODE]" in full_message,
        "mandatory_rag_policy_present": "[MANDATORY BACKEND RAG POLICY]" in full_message,
        "quality_gate_present": "[LEGAL QUALITY GATE]" in full_message,
        "no_placeholder_instruction": "not a sketch, outline, or placeholder" in full_message,
        "explicit_word_count_present": str(sample["words"]) in full_message,
        "profile_must_terms_available": bool(must_compile_terms),
        "must_terms_preserved": all(term.lower() in full_message.lower() for term in must_compile_terms),
        "external_generation_not_used": (compiled_info.get("response_text") or "").startswith("Part I:"),
    }
    if sample.get("require_subject_guide", True):
        checks["subject_guide_present"] = subject_guide_present
    failures = [name for name, ok in checks.items() if not ok]
    return {
        "id": sample["id"],
        "subject": sample["subject"],
        "words": sample["words"],
        "expected_topic": sample["expected_topic"],
        "detected_topic": detected_topic,
        "query_type": query_type,
        "chunk_count": chunk_count,
        "long_split": {
            "is_long_essay": bool(long_info.get("is_long_essay")),
            "split_mode": long_info.get("split_mode"),
            "deliverable_count": len(long_info.get("deliverables") or []),
        },
        "allow_web_search": bool((compiled_info.get("compiled") or {}).get("allow_web_search")),
        "rag_chars": len(str(compiled_info.get("rag_context") or "")),
        "checks": checks,
        "failures": failures,
    }


def run_audit(
    *,
    real_rag: bool = False,
    samples: Optional[Iterable[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    return [audit_sample(sample, real_rag=real_rag) for sample in (samples or SAMPLES)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local-only difficult prompt sampling audit.")
    parser.add_argument("--real-rag", action="store_true", help="Use the real local RAG retriever instead of a compile-only fake RAG stub.")
    parser.add_argument("--all-topics", action="store_true", help="Audit every topic in the full routing matrix.")
    parser.add_argument("--out", type=Path, default=Path("/tmp/legal_ai_real_output_sampling_audit.json"))
    args = parser.parse_args()

    selected_samples = all_topic_samples() if args.all_topics else SAMPLES
    rows = run_audit(real_rag=bool(args.real_rag), samples=selected_samples)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    print(f"Audited {len(rows)} difficult prompts.")
    for row in rows:
        status = "PASS" if not row["failures"] else "FAIL"
        print(
            f"{status} {row['id']}: topic={row['detected_topic']} "
            f"qtype={row['query_type']} chunks={row['chunk_count']} failures={row['failures']}"
        )
    print(f"Wrote {args.out}")
    return 1 if any(row["failures"] for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
