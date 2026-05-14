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
        "name": "tort_occupiers_liability_children",
        "prompt": """Tort Law - Problem Question

Riverside Council owns a public park with a children’s play area, boating lake, and disused maintenance shed. The fence around the lake is broken, teenagers enter the shed despite warning signs, staff know the shed roof is unstable, and lighting complaints have been made near the lake path. Mia, aged 13, is injured when the shed roof collapses. Daniel, an adult jogger, slips near the lake path and falls into shallow water.

Advise Mia and Daniel on occupiers' liability to visitors and trespassers, warnings, contributory negligence, age, obvious risks, causation, and remedies.""",
        "expected_topic": "tort_occupiers_liability",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — TORT (OCCUPIERS' LIABILITY)]",
        "snippets": [
            "For children or teenagers entering dangerous structures, test Jolley v Sutton London Borough Council alongside Tomlinson.",
            "For path/lake injuries, segment causation: did lighting cause the slip, did a broken fence cause or worsen the fall, and what injury would have occurred even with reasonable precautions?",
        ],
    },
    {
        "name": "constitutional_parliamentary_sovereignty",
        "prompt": """Constitutional Law - Essay Question

Critically evaluate whether parliamentary sovereignty remains the central principle of the UK constitution. In your answer, consider Dicey, constitutional statutes, devolution, the Human Rights Act 1998, judicial review, retained EU law, post-Brexit constitutional change, and the rule of law.""",
        "expected_topic": "constitutional_prerogative_justiciability",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — CONSTITUTIONAL LAW (PARLIAMENTARY SOVEREIGNTY / CONSTITUTIONAL DIALOGUE)]",
        "snippets": [
            "Add the manner-and-form/self-embracing-sovereignty issue when constitutional statutes or future Parliaments are discussed;",
            "Update the EU-derived-law discussion for the post-Brexit position: Parliament can restate, revoke, replace, and assimilate EU-derived rules",
        ],
    },
    {
        "name": "public_law_automated_decision_making",
        "prompt": """Public Law / Human Rights / Data Governance - Essay Question

Critically evaluate whether modern public law in the United Kingdom provides adequate control over automated and data-driven public decision-making. Discuss judicial review, procedural fairness, reasons, fettering discretion, Article 8, Article 14, proportionality, UK GDPR, Data Protection Act 2018, automated decision-making safeguards, and remedies.""",
        "expected_topic": "public_law_automated_decision_making",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — PUBLIC LAW / DATA GOVERNANCE (AUTOMATED DECISIONS)]",
        "snippets": [
            "Current-law update required: account for the Data (Use and Access) Act 2025 reforms to automated decision-making",
            "Define meaningful human review concretely: authority to depart, understanding of the tool's basis, access to relevant data/reasons",
        ],
    },
    {
        "name": "competition_digital_marketplace_abuse",
        "prompt": """Competition Law - Problem Question

MarketHub plc operates the largest online marketplace for independent retailers in the UK. It controls around 72% of online third-party marketplace sales in several categories. It uses third-party seller data to launch private-label products, gives its own products more prominent placement in search results, requires premium visibility sellers to use its own payment and delivery systems, and links analytics tools to price restrictions on rival platforms.

Advise the sellers and MarketHub on market definition, dominance, self-preferencing, tying or bundling, seller data, objective justification, Chapter II Competition Act 1998, Article 102 TFEU, remedies, and enforcement routes.""",
        "expected_topic": "competition_abuse_dominance",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — COMPETITION LAW (ABUSE OF DOMINANCE / DIGITAL PLATFORMS)]",
        "snippets": [
            "For UK-focused facts, start with Chapter II Competition Act 1998 as the primary domestic route; use Article 102 TFEU as an analytical comparator or where EU trade/markets are affected, not as an automatic domestic cause of action.",
            "Treat Amazon/CMA or Commission commitments as regulatory evidence of concern about seller data, Buy Box/ranking, and fulfilment access, not as binding infringement authority or a settled legal test.",
            "If the DMCC/SMS regime is relevant, frame it as a current UK digital-markets route alongside, not instead of, Chapter II enforcement.",
        ],
    },
    {
        "name": "law_medicine_surgical_consent_battery",
        "prompt": """Law and Medicine - Problem Question

Amelia, a 29-year-old professional violinist, undergoes surgery on her right wrist after telling the surgeon that even a small loss of fine motor control could end her career. The surgeon explains general benefits but does not mention a recognised risk of permanent stiffness and reduced dexterity. During the operation, the surgeon discovers a non-urgent abnormality in Amelia's left hand and corrects it without Amelia's consent. Amelia develops right-wrist stiffness and left-hand pain.

Advise Amelia and the hospital on informed consent, material risk, reasonable alternatives, battery, necessity, causation, and damages.""",
        "expected_topic": "medical_consent_capacity",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — LAW AND MEDICINE (SURGICAL CONSENT / UNAUTHORISED PROCEDURE)]",
        "snippets": [
            "State the Montgomery materiality test exactly: a risk is material if a reasonable person in the patient's position would likely attach significance to it, or the doctor is or should reasonably be aware that this particular patient would likely attach significance to it.",
            "For a different procedure or different body part without consent, classify battery separately from negligence.",
            "Treat Chester v Afshar cautiously as exceptional.",
        ],
    },
    {
        "name": "tax_offshore_ip_avoidance",
        "prompt": """Tax Law - Problem Question

HelioTech Ltd enters into a series of transactions designed by advisers to reduce its corporation tax liability. It sells intellectual property to a newly incorporated offshore subsidiary, licenses the IP back at a high annual fee, routes payments through intermediary companies in low-tax jurisdictions, and says the structure supports overseas growth.

Advise HelioTech on avoidance, evasion, Ramsay, transfer pricing, GAAR, disclosure, penalties and HMRC remedies.""",
        "expected_topic": "tax_avoidance_gaar",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — TAX LAW (AVOIDANCE / RAMSAY / GAAR)]",
        "snippets": [
            "Use the specialist sequence: characterise the tax advantage -> ordinary statutory construction/Ramsay -> transfer pricing or other specific anti-avoidance/profit-diversion route -> GAAR -> disclosure, penalties, settlement, and appeal/remedy.",
            "For offshore IP sale/licence-back facts, make transfer pricing central: DEMPE functions, control of risk, funding, real personnel/decision-makers, arm's-length valuation/royalty, and whether intermediaries perform real functions.",
            "GAAR is deliberately high-threshold and targets abusive arrangements; do not use it as a catch-all where transfer pricing or a TAAR is the more practical HMRC route.",
        ],
    },
    {
        "name": "environmental_nuisance_regulatory_inaction",
        "prompt": """Environmental Law / Nuisance - Problem Question

ClearWater Processing Ltd operates a waste-treatment facility near a village. It holds environmental permits, but residents complain of persistent odour, loud night-time machinery, suspected chemical run-off, respiratory symptoms, and loss of enjoyment. The regulator says the site is substantially compliant and takes no formal action.

Advise residents and a campaign group on private nuisance, negligence, statutory nuisance, permits, regulatory inaction, judicial review and remedies.""",
        "expected_topic": "generic_environmental_law",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — ENVIRONMENTAL LAW / NUISANCE]",
        "snippets": [
            "Use the specialist sequence: standing/proprietary interest -> private nuisance amenity harm -> negligence for personal injury/causation -> statutory nuisance procedure -> regulatory/JR route -> ranked remedies.",
            "Treat permits and substantial compliance as relevant but not conclusive; do not let licence status short-circuit common-law nuisance without a clear statutory exclusion.",
            "For statutory nuisance, state the practical route: local authority investigation, abatement notice, possible appeal/defence, and resident magistrates' court proceedings if the authority does not act.",
        ],
    },
    {
        "name": "wills_carer_suspicious_circumstances",
        "prompt": """Wills and Administration of Estates - Problem Question

Eleanor, aged 82, made a 2018 will leaving her estate equally to her children. In 2024, after declining health and dependence on her live-in carer Nina, she executed a new will leaving the house to Nina, a small legacy to one child, nothing to the other, and residue to charity. Nina arranged the solicitor appointment. GP notes record memory lapses, confusion, and good and bad days.

Advise on testamentary capacity, knowledge and approval, suspicious circumstances, undue influence, solicitor evidence, invalidity, and Inheritance Act 1975 claims.""",
        "expected_topic": "succession_wills_validity",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — WILLS AND THE ADMINISTRATION OF ESTATES]",
        "snippets": [
            "For validity, keep the sequence strict: formal validity/due execution -> testamentary capacity -> knowledge and approval -> undue influence/fraud -> effect of invalidity -> any Inheritance Act 1975 claim.",
            "State the probate burden structure expressly: the propounder proves due execution and capacity; real doubt or suspicious circumstances require affirmative proof on the relevant issue.",
            "Treat good-and-bad-day medical evidence as a lucid-interval issue tied to execution time.",
        ],
    },
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
    {
        "name": "law_medicine_ethics",
        "prompt": """Law and Medicine - Essay Question

Critically examine whether the right to determine what shall be done with or to one's body is a fundamental right in English medical law. In your answer, consider medical ethics, bodily autonomy, dignity as empowerment, dignity as constraint, utilitarian, duty-based and rights-based arguments, and focused examples from the module syllabus.""",
        "expected_topic": "medical_ethics",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — LAW AND MEDICINE (MEDICAL ETHICS)]",
        "snippets": [
            "Default mode is COURSE-BOUND for Law and Medicine answers",
            "For autonomy essays, use two or three focused syllabus examples only",
        ],
    },
    {
        "name": "law_medicine_transplantation",
        "prompt": """Law and Medicine - Essay Question

Make the case for reforming one or more aspects of the law on transplantation. In your answer, consider the Human Tissue Act 2004, appropriate consent, deemed consent, living donors, deceased donors, directed donation, conditional donation, requested allocation, and section 32 commercialisation.""",
        "expected_topic": "medical_transplantation_hta2004",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — LAW AND MEDICINE (TRANSPLANTATION)]",
        "snippets": [
            "For deceased donation, apply the section 3 hierarchy",
            "Do not say all directed donation is rejected",
        ],
    },
    {
        "name": "law_medicine_abortion",
        "prompt": """Law and Medicine - Essay Question

Critically examine the view that abortion on grounds of fetal abnormality is in need of legislative reform. In your answer, consider the Offences Against the Person Act 1861, the Infant Life (Preservation) Act 1929, the Abortion Act 1967, section 1(1)(a), section 1(1)(d), Crowter, Jepson, and disability-discrimination objections.""",
        "expected_topic": "medical_abortion_aa1967",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — LAW AND MEDICINE (ABORTION)]",
        "snippets": [
            "Start with OAPA 1861 / ILPA 1929 criminalisation",
            "Keep section 1(1)(a) social ground separate from section 1(1)(d) fetal-abnormality ground.",
        ],
    },
    {
        "name": "law_medicine_reproductive",
        "prompt": """Law and Medicine - Essay Question

Critically examine whether the Human Fertilisation and Embryology Act 1990 is unfit for governing assisted reproduction. In your answer, consider HFEA licensing, IVF, Schedule 3 consent, section 13(5) welfare of the child, legal parenthood, PGT, saviour siblings, and embryo research.""",
        "expected_topic": "medical_reproductive_hfea",
        "expected_header": "[TOPIC-SPECIFIC GUIDANCE — LAW AND MEDICINE (REPRODUCTIVE MEDICINE)]",
        "snippets": [
            "Start with the HFEA 1990/2008 regulatory scheme",
            "Separate consent to embryo/gamete use, welfare-of-child screening under section 13(5), legal parenthood, PGT, saviour siblings, and embryo research.",
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
    original_assume_env = os.environ.get("LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE")

    try:
        service.RAG_AVAILABLE = True
        service.get_relevant_context = _fake_rag
        service._find_codex_cli = lambda: "codex"
        service._generate_with_codex_local_adapter = _fake_local_adapter
        os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = "1"
        os.environ["LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"] = "1"

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
        if original_assume_env is None:
            os.environ.pop("LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE", None)
        else:
            os.environ["LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"] = original_assume_env

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
