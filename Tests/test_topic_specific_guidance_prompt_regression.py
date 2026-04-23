"""
Regression checks for output-facing topic-guidance injection.

These tests capture the compiled prompt sent through send_message_with_docs(...)
and assert that the expected topic-specific guidance block is actually included
for difficult prompts, rather than only checking that the source text exists.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import model_applicable_service as service
from model_applicable_service import _infer_retrieval_profile


CASE_MATRIX: List[Dict[str, Any]] = [
    {
        "name": "private_international_law",
        "prompt": """Private International Law - Problem Question

Aurora Build Ltd, an English claimant, sues a German manufacturer, a Dutch consultant, and a French insurer after defects in a Manchester project. The contract contains an exclusive jurisdiction clause in favour of the courts of Hamburg and a German-law choice-of-law clause for contractual questions. Concurrent proceedings have begun in Hamburg, and Aurora later wants recognition and enforcement of an English judgment against assets in Spain.

Advise on exclusive jurisdiction, choice of law, concurrent proceedings, any stay/forum arguments, and recognition and enforcement.""",
        "expected_topic": "private_international_law_post_brexit",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — PRIVATE INTERNATIONAL LAW]",
        "snippets": [
            "Keep the sequence strict: jurisdiction first, then applicable law, then recognition/enforcement or stay/forum arguments if relevant.",
            "Where a jurisdiction clause is in play, test clause scope before assuming Hague 2005 applies; flag its exclusions and the difference between contract and non-contract claims.",
        ],
    },
    {
        "name": "civil_procedure",
        "prompt": """Civil Procedure - Problem Question

Lena sues Vantage MedTech Ltd in the High Court just before limitation expires. Over the next year there are repeated failures to comply with directions, vague particulars, late disclosure by both sides, a late expert report, mediation, summary judgment, strike out, an application for relief from sanctions, and disputes over indemnity costs.

Advise the parties and the court on case management, CPR sanctions, ADR, costs, proportionality, fairness, and efficiency.""",
        "expected_topic": "civil_procedure_justice_balance",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — CIVIL PROCEDURE]",
        "snippets": [
            "Use the overriding objective as the spine of the essay, then test case management, disclosure, costs, sanctions, and ADR against it.",
            "Keep Mitchell/Denton sanctions analysis distinct from the separate questions of cost control, disclosure burden, and settlement pressure.",
        ],
    },
    {
        "name": "product_liability",
        "prompt": """Product Liability - Problem Question

PulseHome sells a software-enabled wearable device in the UK under its own brand. After a remotely deployed firmware patch, some devices fail to warn of arrhythmia, others give false alerts causing unnecessary treatment, and others overheat and cause property damage. The claimants want to sue the manufacturer, importers, and retailers.

Advise on product liability and consumer protection under the Consumer Protection Act 1987, including defect, negligence, strict liability, causation, proof of defect, software-enabled products, and supply-chain responsibility.""",
        "expected_topic": "product_liability_consumer_protection",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — PRODUCT LIABILITY]",
        "snippets": [
            "Compare negligence and CPA strict liability directly rather than discussing them in isolation.",
            "For software-enabled or AI-assisted products, explain whether the problem is doctrinal fit, evidential opacity, or both.",
        ],
    },
    {
        "name": "public_procurement",
        "prompt": """Public Procurement - Problem Question

Under the Procurement Act 2023, a contracting authority awards a major public technology contract. An unsuccessful bidder alleges undisclosed changes to the evaluation methodology, an undisclosed prior relationship between an evaluator and the winning subcontractor, and failure to investigate an abnormally low tender, then considers a challenge to the award decision.

Advise on public procurement, transparency, equal treatment, challenges by unsuccessful bidders, remedies, and the authority's commercial discretion.""",
        "expected_topic": "public_procurement_award_challenges",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — PUBLIC PROCUREMENT]",
        "snippets": [
            "Separate procurement objectives and transparency/equal-treatment controls from the authority's commercial discretion.",
            "If challenging an award, identify the actual breach of statutory duty and its practical consequences before discussing remedies.",
        ],
    },
    {
        "name": "criminal_omissions",
        "prompt": """Criminal Law - Essay Question

Critically evaluate whether English criminal law takes a coherent and morally defensible approach to liability for omissions.

In your answer, consider recognised duties arising from relationship, voluntary assumption of responsibility, creation of danger, homicide, gross negligence manslaughter, causation, and whether the act/omission distinction is principled or artificial.""",
        "expected_topic": "criminal_omissions_homicide_defences",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — CRIMINAL LAW (OMISSIONS)]",
        "snippets": [
            "Duty anchors required: relationship (Gibbins & Proctor; Instan), assumption (Stone & Dobinson), creation of danger (Miller; Evans).",
            "After duty categories, give a direct yes/no mini-conclusion on whether a recognised duty exists on these facts.",
        ],
    },
    {
        "name": "contract_misrepresentation",
        "prompt": """Contract Law - Problem Question

Vertex Live Ltd books Regent Hall Group Ltd for a major investor event. Before contracting, Regent says the venue has a valid late-night licence, a reliable streaming system, and an experienced technical team. The written contract contains an entire agreement clause, a non-reliance clause, and an exclusion clause for indirect or consequential loss. The licence had already expired, the streaming system had recently failed, and the event collapses commercially.

Advise on whether the statements are terms or representations, misrepresentation, frustration, contractual estoppel, exclusion clauses, statutory control, rescission, damages, remoteness, and practical outcome.""",
        "expected_topic": "contract_misrepresentation_exclusion",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — CONTRACT (MISREPRESENTATION / FRUSTRATION)]",
        "snippets": [
            "For misrepresentation, keep sequence strict: actionable statement -> inducement -> category -> remedies.",
            "For frustration, keep risk allocation central: radical difference, not mere hardship; connect to force-majeure/contractual risk allocation.",
        ],
    },
    {
        "name": "criminal_evidence_hearsay",
        "prompt": """Criminal Evidence - Hearsay - Essay Question

Critically evaluate whether the modern law of hearsay in criminal proceedings strikes an appropriate balance between evidential flexibility and fairness to the accused.

In your answer, consider the rationale of the hearsay rule, the principal statutory gateways under the Criminal Justice Act 2003, fear, absence, reliability, Article 6, and the judicial safeguards.""",
        "expected_topic": "criminal_evidence_hearsay",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — CRIMINAL EVIDENCE (HEARSAY)]",
        "snippets": [
            "Anchor the regime expressly in the CJA 2003 and identify the main gateways plus safeguards.",
            "Finish the safeguards section fully: exclusion power, jury directions, and stop-the-case protection.",
        ],
    },
    {
        "name": "data_protection_legitimate_interests",
        "prompt": """Data Protection - Legitimate Interests - Problem Question

VistaAds Ltd profiles users across websites and apps and relies on legitimate interests rather than consent. It combines browsing data, location signals, purchase history, and inferred political and health-related interests for targeted advertising.

Advise on the Article 6(1)(f) legitimate interests basis, necessity, balancing, transparency, special category concerns, objection rights, enforcement, and compensation.""",
        "expected_topic": "data_protection",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — DATA PROTECTION (LEGITIMATE INTERESTS)]",
        "snippets": [
            "Run the three-stage test expressly: legitimate purpose -> necessity -> balancing.",
            "Distinguish legitimate interests from consent/contract/legal obligation rather than blurring lawful bases.",
        ],
    },
    {
        "name": "media_privacy_mpi",
        "prompt": """Media / Privacy - MPI / Injunctions - Problem Question

A newspaper plans to publish details of Theo, a well-known actor, receiving treatment at a private clinic for addiction and severe anxiety, together with leaked messages and photographs outside the clinic. Theo seeks an urgent injunction.

Advise on misuse of private information, reasonable expectation of privacy, breach of confidence, Article 8 and Article 10, public interest, and interim relief.""",
        "expected_topic": "public_law_privacy_expression",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — MEDIA & PRIVACY (MPI / INJUNCTIONS)]",
        "snippets": [
            "Keep the two-stage MPI structure clear: reasonable expectation of privacy first, then the Article 8/10 balancing exercise.",
            "For injunction questions, address prior restraint, urgency, anonymity, public-domain arguments, and whether damages are an adequate remedy.",
        ],
    },
    {
        "name": "education_exclusion_send",
        "prompt": """Education Law - Exclusion / SEND - Problem Question

Fifteen-year-old Malik is permanently excluded after aggression and a physical altercation. His mother argues that he has suspected but unassessed autism and ADHD, the school failed to follow up earlier referrals, important material was not disclosed before the exclusion panel, and the reasons were generic.

Advise on procedural fairness, SEND duties, equality law, public law challenge, and realistic remedies.""",
        "expected_topic": "education_school_exclusion_send",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — EDUCATION LAW (EXCLUSION / SEND)]",
        "snippets": [
            "Use this order: exclusion procedure -> fairness/evidence/reasons -> Equality Act and SEND issues -> remedies.",
            "Keep ordinary public-law unfairness separate from disability/SEND duties; ADHD should not vanish into generic misconduct analysis.",
        ],
    },
    {
        "name": "legal_services_professional_regulation",
        "prompt": """Legal Services / Professional Regulation - Problem Question

A solicitor at Blackstone Legal LLP gives an undertaking without authority, former-client confidential information becomes relevant, the firm continues despite an emerging conflict between associated corporate clients, and a partner tells the client not to disclose a problematic internal document unless specifically asked for it. The regulator is informed and SRA issues arise.

Advise on duties to the client, duties to the court and the administration of justice, confidentiality, conflicts, undertakings, and possible disciplinary consequences.""",
        "expected_topic": "legal_ethics_conflicts",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — LEGAL SERVICES / PROFESSIONAL REGULATION]",
        "snippets": [
            "Identify the regulatory question first: reserved activity, authorisation, professional-conduct breach, or service-standard complaint.",
            "If SRA-style duties are engaged, keep conflicts, confidentiality, independence, and undertakings distinct rather than rolling them into a generic ethics paragraph.",
        ],
    },
    {
        "name": "pensions_law",
        "prompt": """Pensions Law - Problem Question

Northbridge Engineering Ltd closes its final salary pension scheme and replaces it with a less generous defined contribution arrangement. Employees were told their core retirement expectations were secure and that long-serving staff would not be worse off in any meaningful sense.

Advise on accrued rights, amendment powers, trustee and employer duties, misleading statements, estoppel-style arguments, causation, pension loss, and remedies.""",
        "expected_topic": "pensions_scheme_change_misrepresentation",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — PENSIONS LAW]",
        "snippets": [
            "Front-load the pensions setting; do not begin as if this were generic trust or misrepresentation law.",
            "Keep amendment power, proper purpose, and good-faith/rationality review separate from section 67 subsisting-rights analysis; one route may do real work before the other is reached.",
        ],
    },
]


def _fake_rag(query: str, max_chunks: int = 0, query_type: Optional[str] = None) -> str:
    return (
        "Authority: Example Authority [2024] UKSC 1.\n"
        f"Query type: {query_type or 'unknown'}.\n"
        "Notes: indexed retrieval available for structure and authority anchors."
    )


def _fake_complete_answer_for_prompt(full_message: str) -> str:
    lower = (full_message or "").lower()
    if "problem question" in lower:
        return """Part I: Introduction

The answer follows the requested issue order.

Part II: Liability / Remedies

The compiled prompt keeps the doctrinal sequence explicit.

Part III: Final Conclusion

The answer follows the required backend scaffold.

(End of Answer)"""
    return """Part I: Introduction

The answer follows the requested issue order.

Part II: Core Analysis

The compiled prompt keeps the doctrinal sequence explicit.

Part III: Conclusion

The answer follows the required backend scaffold.

(End of Answer)"""


def _capture_compiled_prompt(prompt: str, project_id: str) -> Dict[str, Any]:
    captured_prompts: List[Dict[str, Any]] = []

    def _fake_local_adapter(
        full_message: str,
        system_instruction: Optional[str],
        history: Optional[List[Dict[str, Any]]],
        project_id: str,
        allow_web_search: bool,
    ) -> str:
        captured_prompts.append(
            {
                "full_message": full_message,
                "system_instruction": system_instruction,
                "history": history,
                "project_id": project_id,
                "allow_web_search": allow_web_search,
            }
        )
        return _fake_complete_answer_for_prompt(full_message)

    original_rag_available = service.RAG_AVAILABLE
    original_get_relevant_context = getattr(service, "get_relevant_context")
    original_find_codex_cli = service._find_codex_cli
    original_local_adapter = service._generate_with_codex_local_adapter
    original_allow_env = os.environ.get("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED")

    try:
        service.RAG_AVAILABLE = True
        service.get_relevant_context = _fake_rag
        service._find_codex_cli = lambda: "codex"
        service._generate_with_codex_local_adapter = _fake_local_adapter
        os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = "1"

        (response_text, response_meta), _rag_context = service.send_message_with_docs(
            api_key="",
            message=prompt,
            documents=[],
            project_id=project_id,
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

    assert response_meta == []
    assert "Part I: Introduction" in response_text
    assert "backend scaffold" in response_text
    assert len(captured_prompts) >= 1
    return captured_prompts[0]


def run() -> None:
    print("=" * 80)
    print("TOPIC-SPECIFIC GUIDANCE PROMPT REGRESSION")
    print("=" * 80)

    for case in CASE_MATRIX:
        print(f"Checking {case['name']} ...")
        profile = _infer_retrieval_profile(case["prompt"])
        topic = (profile or {}).get("topic")
        print("  routed topic:", topic)
        expected_topic = case.get("expected_topic")
        if expected_topic is not None:
            assert topic == expected_topic, (case["name"], topic, expected_topic)

        compiled = _capture_compiled_prompt(
            case["prompt"],
            f"topic-guidance-{case['name']}",
        )
        full_message = compiled["full_message"]

        assert "[MANDATORY BACKEND RAG POLICY]" in full_message
        assert "[LOCAL CODE + RAG LEGAL ANSWER MODE]" in full_message
        assert "[DIRECT-CODE / BACKEND DELIVERY MODE]" in full_message
        assert case["expected_header"] in full_message
        assert case["prompt"].splitlines()[0] in full_message
        for snippet in case["snippets"]:
            assert snippet in full_message, (case["name"], snippet)

    print("Topic-specific guidance prompt regression checks passed.")


if __name__ == "__main__":
    run()
