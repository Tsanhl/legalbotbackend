#!/usr/bin/env python3
"""
Live backend benchmark QA for legal complete-answer quality.

This script deliberately uses the canonical backend route:
backend_answer_runtime.send_complete_answer_with_docs(...).

By default it only prints the benchmark set. Use --live to run generation.
Reports are written to /private/tmp unless --output is supplied.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import backend_answer_runtime as runtime
import model_applicable_service as model_service


BENCHMARKS: List[Dict[str, str]] = [
    {
        "id": "contract_misrep_exclusion",
        "subject": "Contract Law",
        "prompt": """Contract Law - Problem Question

Word target: about 2,000-2,500 words

Orion contracts with Silvergate for a product launch. Silvergate made pre-contract statements about a late-night licence, livestreaming suitability and experienced technical staff. The written contract contains entire-agreement, non-reliance, exclusion of indirect/consequential loss including profit/goodwill/business opportunity, and no-oral-variation clauses. The licence had expired, livestreaming had recently failed, support was outsourced, the event ended early, and an investor withdrew.

Advise Orion and Silvergate. Consider terms/representations, misrepresentation, breach, entire-agreement/non-reliance clauses, exclusion/statutory control, remoteness, lost funding, rescission, affirmation, damages, set-off and practical outcome.""",
    },
    {
        "id": "public_law_protest_guidance",
        "subject": "Public Law",
        "prompt": """Public Law - Problem Question

Word target: about 2,000-2,500 words

The Secretary of State issues non-statutory guidance saying local authorities should normally refuse demonstrations likely to cause serious community unease or damage confidence in institutions. Eastford Council treats it as binding and refuses a peaceful housing protest after using an undisclosed algorithmic risk score. The Council had published a charter promising peaceful civic participation will remain central to local democracy.

Advise the group. Consider legal status of guidance, fettering, procedural fairness, reasons, algorithmic risk score, legitimate expectation, Articles 10 and 11 ECHR, proportionality, traditional JR grounds, interim relief, quashing and declarations.""",
    },
    {
        "id": "evidence_robbery",
        "subject": "Evidence Law",
        "prompt": """Evidence Law - Problem Question

Word target: about 2,000-2,500 words

Kai is charged with robbery. The prosecution relies on CCTV of a masked person, a weak eyewitness identification after social-media exposure, a confession after six hours in custody without a solicitor, silence when asked about a jacket, an absent frightened friend statement, and a previous burglary conviction.

Advise on admissibility and likely weight. Consider identification, CCTV/expert evidence, PACE confession rules, adverse inferences, hearsay/absent witnesses, bad character, exclusionary discretion, Article 6 fairness and overall case strength.""",
    },
    {
        "id": "law_medicine_consent",
        "subject": "Law and Medicine",
        "prompt": """Law and Medicine - Problem Question

Word target: about 2,000-2,500 words

Maya has aggressive but treatable cancer. Her consultant recommends immediate surgery and chemotherapy. Maya says fertility, early menopause and long-term cognitive effects matter because she hopes to have a child and cares for her mother. The consultant does not fully explain permanent infertility, fertility preservation, long-term fatigue/cognitive side effects or brief delay before chemotherapy. Treatment succeeds but Maya is infertile and fatigued. She says she would still have treatment but would have delayed chemotherapy for fertility preservation.

Advise Maya and the hospital. Consider Montgomery, material risks, reasonable alternatives, personal values, clinical judgment, causation where she would delay rather than refuse, recoverable loss and remedies.""",
    },
    {
        "id": "tort_occupiers_causation",
        "subject": "Tort Law",
        "prompt": """Tort Law - Problem Question

Word target: about 2,000-2,500 words

A visitor is injured at a leisure venue after ignoring warning signs near a closed diving area. The venue knew visitors often crossed the barrier and that lighting was poor. The visitor had been drinking. Medical evidence says earlier rescue might have reduced but not certainly avoided the final injury.

Advise the parties. Consider occupiers' liability, breach, obvious risk, contributory negligence, causation, loss of chance/material contribution limits, defences and damages.""",
    },
    {
        "id": "land_overriding_priority",
        "subject": "Land Law",
        "prompt": """Land Law - Problem Question

Word target: about 2,000-2,500 words

A registered proprietor sells a family home. A partner contributed to purchase price and lives there, a neighbour claims a right of way and parking, an option to purchase was protected late, and a bank takes a charge after inspection. Completion is imminent.

Advise on beneficial interests, overreaching, actual occupation, easements/parking, options/notices, priority, remedies and practical steps.""",
    },
    {
        "id": "employment_whistleblowing_maternity",
        "subject": "Employment Law",
        "prompt": """Employment Law - Problem Question

Word target: about 2,000-2,500 words

An employee raises safety concerns, then goes on maternity leave. On return she is selected for redundancy after duties were reallocated and a replacement was kept. She is pressured to sign new terms and dismissed after criticising the employer online.

Advise on worker/employee status if relevant, whistleblowing, pregnancy/maternity discrimination, ordinary and automatic unfair dismissal, redundancy fairness, social-media misconduct, remedies and compensation adjustments.""",
    },
    {
        "id": "trusts_tracing_fiduciary",
        "subject": "Trusts Law",
        "prompt": """Trusts Law - Problem Question

Word target: about 2,000-2,500 words

A trustee invests trust money in a mixed account, pays personal debts, buys shares now worth more, and makes a profit from an opportunity learned through trusteeship. One recipient spent money in good faith; another knew the source was suspicious.

Advise beneficiaries and recipients. Consider fiduciary duties, no-profit/no-conflict rules, tracing, mixed funds, knowing receipt/dishonest assistance, change of position, proprietary and personal remedies.""",
    },
    {
        "id": "tax_avoidance_transfer_pricing",
        "subject": "Tax Law",
        "prompt": """Tax Law - Problem Question

Word target: about 2,000-2,500 words

A UK group transfers valuable IP to an offshore affiliate, pays large royalties, routes sales through a low-tax entity with few staff, claims deductions and loss relief, and says all steps are formally lawful. HMRC challenges the arrangement.

Advise. Consider charge/computation assumptions, transfer pricing or specific anti-avoidance routes, Ramsay, GAAR, avoidance/evasion distinction, penalties, disclosure, settlement, appeal and practical outcome.""",
    },
    {
        "id": "competition_platform_abuse",
        "subject": "Competition Law",
        "prompt": """Competition Law - Problem Question

Word target: about 2,000-2,500 words

An online marketplace uses seller transaction data to launch rival products, ranks its own products more prominently, imposes wide price-parity clauses, and says this improves quality and consumer trust. Sellers claim foreclosure.

Advise under UK/EU competition law. Consider market definition, dominance, Article 102/Chapter II, self-preferencing, data advantage, parity clauses, effects, objective justification, digital markets regulation and remedies.""",
    },
    {
        "id": "human_rights_expression_assembly",
        "subject": "Human Rights Law",
        "prompt": """Human Rights Law - Problem Question

Word target: about 2,000-2,500 words

A local authority restricts a controversial vigil and removes online posts criticising the decision. It cites public order and community cohesion. Organisers say the measure suppresses political expression and assembly.

Advise. Consider HRA route, Articles 10 and 11, legality, legitimate aim, necessity, proportionality, margin/discretion, remedies and damages.""",
    },
    {
        "id": "insurance_fair_presentation",
        "subject": "Insurance Law",
        "prompt": """Insurance Law - Problem Question

Word target: about 2,000-2,500 words

A business insured fails to disclose previous near-miss incidents and a change in security arrangements. A theft occurs. The insurer says it would have charged more or excluded the risk. The insured says the broker knew enough and the policy wording is ambiguous.

Advise. Consider fair presentation, knowledge/reasonable search, materiality, inducement, proportionate remedies, policy construction, warranties/conditions, claims handling and practical outcome.""",
    },
]


BENCHMARKS.extend([
    {
        "id": "criminal_secondary_liability_jogee",
        "subject": "Criminal Law",
        "prompt": """Criminal Law - Problem Question

Word target: about 2,000-2,500 words

Liam and Noah agree to burgle a warehouse at night. Liam says they should avoid violence, but Noah secretly brings a knife. Liam waits outside as getaway driver. Noah is confronted by a guard, stabs him, takes laptops and returns with blood on his clothes. Liam drives him away and later hides the laptops.

Advise Liam and Noah. Consider burglary, theft, robbery, aggravated burglary, non-fatal offences, secondary liability after Jogee, foresight/conditional intent, withdrawal, assisting an offender, handling stolen goods, defences and likely charging outcome.""",
    },
    {
        "id": "equity_family_tracing_insolvency",
        "subject": "Equity and Trusts",
        "prompt": """Equity and Trusts - Problem Question

Word target: about 2,000-2,500 words

Sofia transfers 250,000 pounds to Malik saying: keep this safe for the family until I decide exactly how it should be divided. Malik pays some into his business account, some into a mixed account, some to reduce his mortgage and some to buy shares that double in value. From the mixed account he repays Zara for an old debt, gives money to his daughter and spends the rest. Malik becomes insolvent.

Advise Sofia, Malik, Zara and the daughter. Consider certainty, express/resulting trust, breach, common law and equitable tracing, mixed funds, shares, mortgage repayment, recipient claims, insolvency and asset-by-asset remedies.""",
    },
    {
        "id": "family_relocation_financial_abuse",
        "subject": "Family Law",
        "prompt": """Family Law - Problem Question

Word target: about 2,000-2,500 words

After separation, Priya wants to relocate with two children to Scotland for work and family support. Daniel opposes, alleging alienation and seeking shared care. Priya alleges coercive control and financial abuse. The family home is jointly owned, Daniel runs a small company, and Priya seeks interim maintenance, occupation protection and a final financial order.

Advise both parties. Consider welfare, child arrangements, relocation, domestic abuse fact-finding, occupation/non-molestation, financial remedies, disclosure, business assets, needs/sharing/compensation, interim relief and likely orders.""",
    },
    {
        "id": "commercial_title_agency_retention",
        "subject": "Commercial Law",
        "prompt": """Commercial Law - Problem Question

Word target: about 2,000-2,500 words

Delta Supplies sells machines to Apex on retention-of-title terms. Apex resells one machine to a good-faith sub-buyer, grants a bank floating charge over stock, and asks an agent to order components while exceeding authority. The machines partly fail and Apex becomes insolvent.

Advise Delta, Apex, the sub-buyer, the agent and the bank. Consider sale of goods terms, title and risk, nemo dat exceptions, agency authority, retention of title, floating charges, insolvency priority, remedies and practical recovery.""",
    },
    {
        "id": "company_insolvency_directors",
        "subject": "Company and Insolvency Law",
        "prompt": """Company and Insolvency Law - Problem Question

Word target: about 2,000-2,500 words

NovaTech Ltd is cash-flow insolvent but directors keep trading to complete a risky contract. They pay a connected creditor, sell an asset to a director's spouse at undervalue, take investor money after optimistic statements, and exclude a minority shareholder from management. Administration follows.

Advise the company, directors, administrator and minority shareholder. Consider directors' duties, creditor duty, wrongful/fraudulent trading, preferences, transactions at undervalue, misrepresentation, unfair prejudice, remedies, disqualification and practical outcome.""",
    },
    {
        "id": "eu_directive_free_movement_state_liability",
        "subject": "EU Law",
        "prompt": """EU Law - Problem Question

Word target: about 2,000-2,500 words

A Member State fails to implement a directive protecting platform workers by the deadline. A worker employed by a private platform relies on the directive against the company and a public regulator. The same State restricts imported plant-based foods unless they use local certification, citing consumer protection and health.

Advise the worker, platform and importer. Consider direct effect, indirect effect, state emanations, state liability, retained/withdrawal issues if relevant, free movement of goods, justification, proportionality and remedies.""",
    },
    {
        "id": "public_international_use_force_immunity",
        "subject": "Public International Law",
        "prompt": """Public International Law - Problem Question

Word target: about 2,000-2,500 words

State A launches cyber operations and limited missile strikes against facilities in State B after attacks by a non-state group allegedly operating from B. A senior official of A visits State C and victims seek arrest and civil damages. State B brings claims before an international court.

Advise the parties. Consider sources of international law, use of force, self-defence, attribution, necessity/proportionality, state responsibility, countermeasures, immunities, human rights or humanitarian law overlap, jurisdiction and remedies.""",
    },
    {
        "id": "immigration_deportation_article8",
        "subject": "Immigration and Refugee Law",
        "prompt": """Immigration and Refugee Law - Problem Question

Word target: about 2,000-2,500 words

Amir arrived irregularly, claims asylum after political detention in his home state, and has a British partner and child. The Home Office rejects credibility, certifies the claim as clearly unfounded, and pursues deportation after a criminal conviction. Amir relies on Refugee Convention risk, humanitarian protection and Article 8.

Advise Amir and the Home Office. Consider asylum status, credibility, exclusion, modern statutory framework and current-law checks, Article 3, Article 8, best interests of the child, public interest, appeals, interim relief and practical outcome.""",
    },
    {
        "id": "housing_possession_repair_homelessness",
        "subject": "Housing Law",
        "prompt": """Housing Law - Problem Question

Word target: about 2,000-2,500 words

Tara rents a private flat with serious damp and electrical defects. The landlord serves possession papers after she complains, increases rent and refuses repairs. Tara falls into arrears after illness and applies to the council as homeless with two children.

Advise Tara, the landlord and the council. Consider current possession reform checks, disrepair, retaliatory eviction, rent increase, deposit/licensing if relevant, equality or vulnerability issues, homelessness duties, defences, counterclaims, injunctions and remedies.""",
    },
    {
        "id": "cyber_online_safety_ransomware",
        "subject": "Cybercrime and Online Safety Law",
        "prompt": """Cybercrime and Online Safety Law - Problem Question

Word target: about 2,000-2,500 words

A teenager uses stolen credentials to access a school system, copies exam files and joins a group chat sharing ransomware tools. A platform receives reports that users are posting threats and intimate images but delays action. Police seize devices and ask the platform for data.

Advise the teenager, platform and investigators. Consider Computer Misuse Act offences, fraud/communications/intimate image offences, Online Safety Act duties, platform risk systems, evidence powers, privacy, defences, sentencing/remedies and current-law checkpoints.""",
    },
    {
        "id": "financial_reg_consumer_duty_crypto",
        "subject": "Financial Regulation Law",
        "prompt": """Financial Regulation Law - Problem Question

Word target: about 2,000-2,500 words

FinWave markets high-risk crypto tokens and complex mini-bonds to retail customers through influencers. Risk warnings are buried, vulnerable customers are targeted, complaint handling is slow, and senior managers say compliance was outsourced. Losses follow after the issuer collapses.

Advise FinWave, customers and the regulator. Consider authorisation, financial promotions, cryptoasset rules, Consumer Duty, suitability/appropriateness, vulnerable customers, SMCR, enforcement, redress, current-law checks and practical outcome.""",
    },
    {
        "id": "public_procurement_transition_remedies",
        "subject": "Public Procurement Law",
        "prompt": """Public Procurement Law - Problem Question

Word target: about 2,000-2,500 words

A contracting authority awards an IT framework after using unclear scoring, undisclosed moderation, a late clarification favouring the incumbent and a direct-award extension for urgent needs. The procurement began near a regime transition date. A losing bidder seeks to stop signature.

Advise the bidder and authority. Consider applicable regime, transparency, equal treatment, conflicts, scoring reasons, direct award/urgency, standstill, automatic suspension/interim relief, damages, ineffectiveness or set-aside, and current-law transition checks.""",
    },
    {
        "id": "ip_ai_copyright_trademark",
        "subject": "Intellectual Property Law",
        "prompt": """Intellectual Property Law - Problem Question

Word target: about 2,000-2,500 words

An AI design company trains on a photographer's images, generates similar advertising visuals for a client, uses a competitor's trade mark as a hidden keyword, and publishes code under a disputed open-source licence. The photographer, competitor and client threaten claims.

Advise. Consider copyright subsistence/infringement, text/data mining or fair dealing if relevant, authorship/ownership, passing off and trade marks, keyword advertising, confidential information, licence breach, remedies and practical outcome.""",
    },
    {
        "id": "environmental_permit_jr_nuisance",
        "subject": "Environmental Law",
        "prompt": """Environmental Law - Problem Question

Word target: about 2,000-2,500 words

A council grants permission and an environmental permit for a waste facility near homes and a protected habitat. Consultation documents understated odour and traffic impacts, the environmental statement omitted cumulative emissions, and residents suffer noise and dust after operations begin.

Advise residents, operator and council. Consider planning/environmental assessment, habitat duties, permitting, public participation, judicial review, statutory nuisance/private nuisance, regulatory enforcement, remedies, time limits and practical strategy.""",
    },
    {
        "id": "succession_capacity_undue_influence",
        "subject": "Succession and Wills",
        "prompt": """Succession and Wills - Problem Question

Word target: about 2,000-2,500 words

Eleanor changes her will shortly before death, leaving most assets to a carer and excluding her adult children. She had fluctuating dementia, the carer arranged the solicitor meeting, one attesting witness may not have been present throughout, and a lifetime gift was made from Eleanor's account.

Advise the estate, carer and children. Consider formal validity, testamentary capacity, knowledge and approval, undue influence, fraudulent calumny, lifetime gifts, proprietary claims, Inheritance Act claims, remedies and likely outcome.""",
    },
    {
        "id": "restitution_mistake_failure_basis",
        "subject": "Restitution Law",
        "prompt": """Restitution Law - Problem Question

Word target: about 2,000-2,500 words

BlueCo pays 2 million pounds to GreenCo believing a supply contract is binding. The contract is void for mistake or lack of authority. GreenCo spends part repaying debts, invests part profitably and says BlueCo delayed after discovering the problem. A third party received some funds.

Advise. Consider unjust enrichment, mistake, failure of basis, change of position, tracing/proprietary restitution, ministerial receipt or agency, defences, limitation and remedies.""",
    },
    {
        "id": "equality_disability_algorithm",
        "subject": "Equality Law",
        "prompt": """Equality Law - Problem Question

Word target: about 2,000-2,500 words

MetroBank uses an algorithm to screen job applicants and loan customers. Disabled applicants are downgraded for employment gaps, women returning from maternity leave score lower, and minority customers are more often asked for extra documentation. The bank says the model is neutral and commercially necessary.

Advise affected individuals and the bank. Consider direct and indirect discrimination, disability discrimination and reasonable adjustments, pregnancy/maternity or sex discrimination, services/employment routes, algorithmic evidence, justification, burden of proof, remedies and regulatory overlap.""",
    },
    {
        "id": "civil_procedure_relief_disclosure",
        "subject": "Civil Procedure",
        "prompt": """Civil Procedure - Problem Question

Word target: about 2,000-2,500 words

In commercial litigation, a claimant serves particulars late, misses disclosure deadlines, withholds adverse documents as privileged, and seeks permission for expert evidence after directions. The defendant applies for strike out, unless order and security for costs. Settlement offers have been made.

Advise both parties. Consider overriding objective, statements of case, relief from sanctions, disclosure and privilege, expert evidence, strike out/summary judgment if relevant, costs, Part 36, case management orders and practical outcome.""",
    },
])


MANUAL_REVIEW_CHECKLIST = [
    "issue coverage against every prompt limb",
    "citation accuracy and inline OSCOLA placement after relevant propositions",
    "per-question word target and no underdeveloped blocks",
    "final remedy/outcome section with ranked practical advice",
    "no fake authorities, detached source logs, or local path leakage",
]


AUTHORITY_PARENTHESES_RE = re.compile(
    r"\([^()\n]*(?:"
    r"\[[12][0-9]{3}\]|"
    r"\b[12][0-9]{3}\b|"
    r"\b(?:UKSC|UKHL|EWCA|EWHC|AC|WLR|QB|Ch|EHRR|ICJ Rep|Act|Code|Regulation|Convention|Treaty)\b"
    r")[^()\n]*\)"
)


def _count_words(text: str) -> int:
    return len((text or "").split())


def _citation_parenthetical_count(text: str) -> int:
    return len(AUTHORITY_PARENTHESES_RE.findall(text or ""))


def _guide_authority_mix(subject_guide: str) -> Dict[str, int]:
    """Estimate whether the matched subject guide can backstop thin local RAG."""
    if not subject_guide:
        return {"statutes": 0, "cases": 0, "secondary": 0}
    anchors = model_service._extract_query_authority_anchors(  # type: ignore[attr-defined]
        subject_guide,
        limit=80,
    )
    return model_service._count_authority_mix_from_allowlist(anchors)  # type: ignore[attr-defined]


def _run_local_rag_audit(item: Dict[str, str], *, audit_max_chars: int) -> Dict[str, Any]:
    """Audit local routing/RAG/guide coverage without calling external providers."""
    prompt = item["prompt"]
    profile = model_service._infer_retrieval_profile(prompt)  # type: ignore[attr-defined]
    query_type = model_service.detect_query_type(prompt, [])  # type: ignore[attr-defined]
    all_query_types = model_service.detect_all_query_types(prompt, [])  # type: ignore[attr-defined]
    chunk_count = int(getattr(model_service, "QUERY_CHUNK_CONFIG", {}).get(query_type, 20) or 20)
    rag_context = model_service.get_relevant_context(  # type: ignore[attr-defined]
        prompt,
        max_chunks=chunk_count,
        query_type=query_type,
        max_chars=max(4000, int(audit_max_chars or 18000)),
    )
    rag_audit = model_service._rag_quality_audit(rag_context, profile)  # type: ignore[attr-defined]
    initial_rag_audit = dict(rag_audit)
    strict_requery_used = False
    if rag_audit.get("needs_retry"):
        strict_query = model_service._build_strict_requery(prompt, profile, rag_audit)  # type: ignore[attr-defined]
        strict_context = model_service.get_relevant_context(  # type: ignore[attr-defined]
            strict_query,
            max_chunks=max(chunk_count, 20),
            query_type=query_type,
            max_chars=max(4000, int(audit_max_chars or 18000)),
        )
        strict_audit = model_service._rag_quality_audit(strict_context, profile)  # type: ignore[attr-defined]
        old_score = float(rag_audit.get("score", 0.0) or 0.0)
        new_score = float(strict_audit.get("score", 0.0) or 0.0)
        if (
            (bool(rag_audit.get("needs_retry")) and not bool(strict_audit.get("needs_retry")))
            or new_score >= old_score
            or len(strict_context or "") > len(rag_context or "")
        ):
            rag_context = strict_context
            rag_audit = strict_audit
            strict_requery_used = True
    subject_slug = model_service._infer_subject_guide_slug(  # type: ignore[attr-defined]
        str(profile.get("topic") or ""),
        prompt,
    )
    subject_guide = model_service._subject_guide_excerpt_for_query(  # type: ignore[attr-defined]
        prompt,
        profile,
        max_lines=48,
    )
    guide_mix = _guide_authority_mix(subject_guide)
    guide_primary_total = int(guide_mix.get("statutes", 0) or 0) + int(guide_mix.get("cases", 0) or 0)
    guide_statutes = int(guide_mix.get("statutes", 0) or 0)
    guide_cases = int(guide_mix.get("cases", 0) or 0)
    guide_backstop_available = (
        bool(subject_guide)
        and guide_primary_total >= 3
        and (
            (guide_statutes >= 1 and guide_cases >= 1)
            or guide_cases >= 4
            or guide_statutes >= 3
            or (profile.get("topic") or "") in {
                "cyber_computer_misuse_harassment",
                "cybercrime_ransomware_jurisdiction",
                "space_law_debris_liability",
                "generic_financial_regulation_law",
                "public_procurement_award_challenges",
            }
        )
    )
    index_coverage = model_service._profile_local_index_coverage(profile)  # type: ignore[attr-defined]
    missing_must_cover = [
        str(item)
        for item in (rag_audit.get("missing_must_cover") or [])
        if str(item).strip()
    ]
    coverage_gap = bool(rag_audit.get("needs_retry")) or bool(index_coverage.get("thin"))
    raw_materially_weak = (
        not rag_context
        or float(rag_audit.get("score", 0.0) or 0.0) < 6.0
        or int(rag_audit.get("primary_total", 0) or 0) < 3
        or int(rag_audit.get("unique_docs", 0) or 0) < 2
    )
    guide_backstop_used = False
    if raw_materially_weak and guide_backstop_available and rag_context and subject_guide:
        merged_context = model_service._merge_rag_contexts(  # type: ignore[attr-defined]
            [
                ("Base Retrieval", rag_context),
                ("Subject Guide Authority Backstop", subject_guide),
            ]
        )
        merged_audit = model_service._rag_quality_audit(merged_context, profile)  # type: ignore[attr-defined]
        if (
            float(merged_audit.get("score", 0.0) or 0.0) >= float(rag_audit.get("score", 0.0) or 0.0)
            or int(merged_audit.get("primary_total", 0) or 0) > int(rag_audit.get("primary_total", 0) or 0)
        ):
            rag_context = merged_context
            rag_audit = merged_audit
            guide_backstop_used = True
            missing_must_cover = [
                str(item)
                for item in (rag_audit.get("missing_must_cover") or [])
                if str(item).strip()
            ]
            coverage_gap = bool(rag_audit.get("needs_retry")) or bool(index_coverage.get("thin"))
    materially_weak = (
        not rag_context
        or float(rag_audit.get("score", 0.0) or 0.0) < 6.0
        or int(rag_audit.get("primary_total", 0) or 0) < 3
        or int(rag_audit.get("unique_docs", 0) or 0) < 2
    )
    if not subject_slug or not subject_guide:
        status = "guide_missing"
    elif not rag_context:
        status = "retrieval_missing"
    elif materially_weak and not guide_backstop_available:
        status = "retrieval_weak"
    elif materially_weak:
        status = "needs_online_or_index_update"
    elif coverage_gap:
        status = "needs_online_or_index_update"
    else:
        status = "audit_pass"
    return {
        "id": item["id"],
        "subject": item["subject"],
        "status": status,
        "topic": profile.get("topic", ""),
        "query_type": query_type,
        "all_query_types": all_query_types,
        "subject_guide_slug": subject_slug,
        "subject_guide_found": bool(subject_guide),
        "subject_guide_lines": len([ln for ln in (subject_guide or "").splitlines() if ln.strip()]),
        "guide_authority_mix": guide_mix,
        "guide_backstop_available": guide_backstop_available,
        "guide_backstop_used": guide_backstop_used,
        "rag_chars": len(rag_context or ""),
        "strict_requery_used": strict_requery_used,
        "initial_rag_score": round(float(initial_rag_audit.get("score", 0.0) or 0.0), 2),
        "initial_rag_needs_retry": bool(initial_rag_audit.get("needs_retry")),
        "rag_score": round(float(rag_audit.get("score", 0.0) or 0.0), 2),
        "rag_needs_retry": bool(rag_audit.get("needs_retry")),
        "coverage_gap": coverage_gap,
        "materially_weak": materially_weak,
        "rag_mix": rag_audit.get("mix") or {},
        "unique_docs": int(rag_audit.get("unique_docs", 0) or 0),
        "unique_families": int(rag_audit.get("unique_families", 0) or 0),
        "primary_total": int(rag_audit.get("primary_total", 0) or 0),
        "missing_must_cover_count": len(missing_must_cover),
        "missing_must_cover_preview": missing_must_cover[:8],
        "index_matched_count": int(index_coverage.get("matched_count", 0) or 0),
        "index_target_count": int(index_coverage.get("target_count", 0) or 0),
        "index_thin": bool(index_coverage.get("thin")),
        "manual_review_required": True,
        "manual_review_checklist": MANUAL_REVIEW_CHECKLIST,
    }


def run_benchmark(args: argparse.Namespace) -> Dict[str, Any]:
    if args.force_codex:
        os.environ["LEGAL_AI_FORCE_CODEX_LOCAL_ADAPTER"] = "1"
    if args.require_online:
        os.environ["LEGAL_AI_REQUIRE_ONLINE_VERIFICATION"] = "1"
    if args.allow_keyless_jina_search:
        if not (os.getenv("LEGAL_AI_ONLINE_SEARCH_PROVIDER") or "").strip():
            os.environ["LEGAL_AI_ONLINE_SEARCH_PROVIDER"] = "jina"
        os.environ["LEGAL_AI_ALLOW_KEYLESS_JINA_SEARCH"] = "1"

    selected = BENCHMARKS[: max(1, min(args.limit, len(BENCHMARKS)))]
    report: Dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "live": bool(args.live),
        "audit_only": bool(args.audit_only),
        "limit": len(selected),
        "available_benchmarks": len(BENCHMARKS),
        "subjects": sorted({item["subject"] for item in selected}),
        "force_codex": bool(args.force_codex),
        "require_online": bool(args.require_online),
        "allow_keyless_jina_search": bool(args.allow_keyless_jina_search),
        "online_search_provider": os.getenv("LEGAL_AI_ONLINE_SEARCH_PROVIDER", ""),
        "manual_review_checklist": MANUAL_REVIEW_CHECKLIST,
        "results": [],
    }

    for item in selected:
        if args.audit_only:
            try:
                report["results"].append(_run_local_rag_audit(item, audit_max_chars=args.audit_max_chars))
            except Exception as exc:
                report["results"].append({
                    "id": item["id"],
                    "subject": item["subject"],
                    "status": "audit_error",
                    "error": str(exc),
                    "manual_review_required": True,
                    "manual_review_checklist": MANUAL_REVIEW_CHECKLIST,
                })
                if args.fail_fast:
                    break
            continue
        if not args.live:
            report["results"].append({
                "id": item["id"],
                "subject": item["subject"],
                "status": "planned",
                "prompt_words": _count_words(item["prompt"]),
                "word_target": "about 2,000-2,500 words",
                "manual_review_required": True,
            })
            continue
        try:
            (answer_text, _meta), rag_context = runtime.send_complete_answer_with_docs(
                api_key=args.api_key or "",
                message=item["prompt"],
                documents=[],
                project_id=f"benchmark-{item['id']}",
                history=[],
                stream=False,
                provider=args.provider,
                model_name=args.model,
                enforce_long_response_split=False,
            )
            issues = runtime._strict_complete_answer_issues(
                answer_text,
                item["prompt"],
                [],
                enforce_long_response_split=False,
                rag_context=rag_context,
            )
            severe_issues = runtime._severe_complete_answer_issues(issues)
            report["results"].append({
                "id": item["id"],
                "subject": item["subject"],
                "status": "pass" if not issues else "issues",
                "answer_words": _count_words(answer_text),
                "citation_parentheticals": _citation_parenthetical_count(answer_text),
                "issue_count": len(issues),
                "severe_issue_count": len(severe_issues),
                "issues": issues[:12],
                "severe_issues": severe_issues[:8],
                "rag_chars": len(rag_context or ""),
                "manual_review_required": True,
                "manual_review_checklist": MANUAL_REVIEW_CHECKLIST,
            })
        except Exception as exc:
            report["results"].append({
                "id": item["id"],
                "subject": item["subject"],
                "status": "error",
                "error": str(exc),
                "manual_review_required": True,
                "manual_review_checklist": MANUAL_REVIEW_CHECKLIST,
            })
            if args.fail_fast:
                break
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Run live backend generation instead of dry-run planning.")
    parser.add_argument("--audit-only", action="store_true", help="Run local routing/RAG/guide audit without external model/search calls.")
    parser.add_argument("--audit-max-chars", type=int, default=18000, help="Max RAG context chars per prompt in --audit-only mode.")
    parser.add_argument("--limit", type=int, default=30, help="Number of benchmark prompts to run or list.")
    parser.add_argument("--provider", default="auto")
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--force-codex", action="store_true", help="Set LEGAL_AI_FORCE_CODEX_LOCAL_ADAPTER=1 when no API key is configured.")
    parser.add_argument("--no-require-online", dest="require_online", action="store_false", help="Do not force LEGAL_AI_REQUIRE_ONLINE_VERIFICATION=1.")
    parser.add_argument(
        "--allow-keyless-jina-search",
        action="store_true",
        help="Enable LEGAL_AI_ONLINE_SEARCH_PROVIDER=jina and LEGAL_AI_ALLOW_KEYLESS_JINA_SEARCH=1 for provider-neutral online verification.",
    )
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--output", default="")
    parser.set_defaults(require_online=True)
    args = parser.parse_args()

    report = run_benchmark(args)
    out_path = Path(args.output) if args.output else Path("/private/tmp") / (
        f"legal_answer_benchmark_qa_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    )
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(out_path), "results": report["results"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
