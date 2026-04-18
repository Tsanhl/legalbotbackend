"""
All-topics legal regression harness.

Checks:
- every routed topic has supporting config coverage
- every explicit router topic can be hit by a realistic synthetic prompt
- every topic profile carries the core answer-quality controls
- long-answer split planning remains coherent for each topic
- core validators still reject bibliography/footnote drift

This is an offline regression harness. It does not call the live model API.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple

from model_applicable_service import (
    _build_legal_answer_quality_gate,
    _infer_retrieval_profile,
    detect_essay_core_policy_violation,
    detect_inline_oscola_policy_violation,
    detect_long_essay,
    detect_unit_structure_policy_violation,
)


SOURCE = Path("model_applicable_service.py").read_text(encoding="utf-8")


def _extract_literal_dict(anchor: str):
    idx = SOURCE.index(anchor)
    start = SOURCE.index("{", idx)
    depth = 0
    end = None
    for i in range(start, len(SOURCE)):
        if SOURCE[i] == "{":
            depth += 1
        elif SOURCE[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise RuntimeError(f"Could not parse dict for {anchor}")
    return ast.literal_eval(SOURCE[start:end])


MUST_COVER: Dict[str, List[str]] = _extract_literal_dict("must_cover: Dict[str, List[str]] = {")
SOURCE_MIX: Dict[str, Dict[str, int]] = _extract_literal_dict("source_mix_min_by_topic: Dict[str, Dict[str, int]] = {")
SOURCE_TYPES: Dict[str, str] = _extract_literal_dict("source_type_hint_by_topic: Dict[str, str] = {")
TOPIC_GUIDANCE_EXACT: Dict[str, Dict[str, List[str]]] = _extract_literal_dict(
    "topic_guidance_exact: Dict[str, Dict[str, List[str]]] = {"
)

ROUTED_TOPICS = sorted(
    {
        topic
        for topic in re.findall(r'topic = "([a-z0-9_]+)"', SOURCE)
        if topic not in {"general_legal", "mixed_legal_multi_unit"}
    }
)

PROBLEM_TOPICS = {
    "company_directors_minorities",
    "consumer_digital_content",
    "criminal_complicity",
    "criminal_evidence_hearsay",
    "criminal_nonfatal_offences_self_defence",
    "criminal_omissions_homicide_defences",
    "criminal_property_offences_dishonesty",
    "cyber_computer_misuse_harassment",
    "cybercrime_ransomware_jurisdiction",
    "employment_equal_pay_flexible_working",
    "employment_restrictive_covenants",
    "employment_worker_status",
    "family_child_abduction_hague1980",
    "family_private_children_arrangements",
    "immigration_asylum_deportation",
    "insolvency_corporate",
    "land_coownership_constructive_trusts",
    "land_easements_freehold_covenants",
    "land_leasehold_covenants",
    "medical_consent_capacity",
    "medical_end_of_life_mca2005",
    "partnership_law_pa1890",
    "private_international_law_post_brexit",
    "public_international_law_immunities_icc",
    "public_international_law_state_responsibility_attribution",
    "public_international_law_use_of_force",
    "refugee_maritime_non_refoulement",
    "restitution_mistake",
    "space_law_debris_liability",
    "tort_negligence_omissions",
    "tort_occupiers_liability",
}

PROMPT_OVERRIDES: Dict[str, str] = {
    "clinical_negligence_causation_loss_of_chance": """
4500 words
1. Medical Law - Essay Question (Clinical Negligence Causation)
Discuss whether the law on delayed diagnosis and loss of chance is coherent, with reference to Gregg v Scott, Bailey v Ministry of Defence, Williams v Bermuda Hospitals Board, and material contribution reasoning.
""".strip(),
    "company_directors_minorities": """
4500 words
1. Company Law - Problem Question (Directors' Duties and Minority Shareholders)
Advise whether the directors breached Companies Act 2006 sections 171 to 177, whether an unfair-prejudice petition or derivative claim is available, and what remedy the minority shareholder should pursue.
""".strip(),
    "consumer_digital_content": """
4500 words
1. Consumer Law - Problem Question (Digital Content)
Advise whether faulty downloaded software and streamed digital content breach the Consumer Rights Act 2015 and what repair, replacement, price reduction, and device-damage remedies are available.
""".strip(),
    "generic_consumer_protection_law": """
4500 words
1. Consumer Protection Law - Essay Question
Critically evaluate whether consumer protection law adequately protects modern consumers, with reference to the Consumer Rights Act 2015, unfair commercial practices, unfair terms, information asymmetry, and enforcement.
In your answer, address:
- substantive consumer rights
- unfair commercial practices and unfair terms
- digital and modern-market vulnerabilities
- whether enforcement makes the protections effective in practice
""".strip(),
    "generic_devolution_law": """
4500 words
1. Devolution Law - Essay Question
Critically assess whether devolution has strengthened or weakened the UK constitution, discussing the Scotland Act 1998, Government of Wales Act 2006, the Northern Ireland Act 1998, constitutional asymmetry, and the Sewel Convention.
In your answer, address:
- democratic decentralisation and constitutional legitimacy
- asymmetry and intergovernmental strain
- parliamentary sovereignty and the Sewel Convention
- whether devolution strengthens or weakens constitutional coherence
""".strip(),
    "generic_environmental_law": """
4500 words
1. Environmental Law - Essay Question
Critically evaluate whether environmental law effectively balances economic development and environmental protection through sustainable development, the precautionary principle, polluter pays, and the Climate Change Act 2008.
In your answer, address:
- environmental principles
- regulatory tools and enforcement
- the pressure between development and protection
- whether the current framework is effective overall
""".strip(),
    "generic_eu_law": """
4500 words
1. EU Law - Essay Question
Critically evaluate whether EU law is still relevant post-Brexit, with reference to retained or assimilated law, the European Union (Withdrawal) Act 2018, the Trade and Cooperation Agreement, and Article 267 TFEU.
In your answer, address:
- retained or assimilated EU law
- interpretive legacy and Article 267
- the loss of supremacy and direct effect
- whether EU law remains legally relevant after Brexit
""".strip(),
    "consumer_unfair_terms_cra2015": """
4500 words
1. Consumer Law - Essay Question (Unfair Terms)
Discuss whether CRA 2015 sections 62 and 64 strike the right balance between consumer protection and contractual certainty, with reference to First National Bank and Ashbourne.
""".strip(),
    "contract_sale_of_goods_implied_terms_remedies": """
4500 words
1. Commercial / Sale of Goods - Problem Question (Implied Terms and Remedies)
Advise on satisfactory quality, fitness for purpose, description, acceptance, rejection, damages, repair or replacement under the Sale of Goods Act 1979 and, if classification is uncertain, the Consumer Rights Act 2015.
""".strip(),
    "cyber_computer_misuse_harassment": """
4500 words
1. Cyber Law - Problem Question (Computer Misuse and Harassment)
Advise on liability for unauthorised access under the Computer Misuse Act 1990, denial-of-service activity, and malicious or harassing online communications under the Communications Act 2003.
""".strip(),
    "criminal_nonfatal_offences_self_defence": """
4500 words
1. Criminal Law - Problem Question (Non-Fatal Offences and Self-Defence)
Advise Daniel on liability under the Offences Against the Person Act 1861 for injuries caused during two confrontations, including self-defence, mistaken belief, reasonable force, and the likely charge under sections 18, 20, or 47.
""".strip(),
    "cybercrime_ransomware_jurisdiction": """
4500 words
1. Cybercrime - Problem Question (Ransomware Jurisdiction)
Advise on jurisdiction, mutual legal assistance, extradition, and the Budapest Convention where ransomware actors, servers, victims, and cash-out services are spread across several states.
""".strip(),
    "employment_equal_pay_flexible_working": """
4500 words
1. Employment Law - Problem Question (Equal Pay and Flexible Working)
Advise whether a part-time woman comparator has an equal-pay claim, whether any childcare-related PCP amounts to indirect sex discrimination under the Equality Act 2010, and whether the employer can justify the arrangements.
""".strip(),
    "employment_restrictive_covenants": """
4500 words
1. Employment Law - Problem Question (Restrictive Covenants)
Advise whether a non-compete, non-solicitation, and garden-leave clause are enforceable against a departing senior employee, with reference to Herbert Morris, Tillman, and legitimate business interests.
""".strip(),
    "employment_worker_status": """
4500 words
1. Employment Law - Problem Question (Worker Status)
Advise whether Mina is an employee, limb-b worker, or genuinely self-employed for Employment Rights Act 1996 and Working Time Regulations purposes, with reference to Ready Mixed Concrete, Autoclenz, Pimlico, and Uber.
""".strip(),
    "generic_financial_regulation_law": """
4500 words
1. Financial Regulation Law - Essay Question
Critically evaluate whether modern financial regulation effectively prevents systemic risk while promoting market efficiency, with reference to the Financial Services and Markets Act 2000, Basel III, prudential supervision, the FCA, and the Senior Managers and Certification Regime.
In your answer, address:
- systemic risk and macroprudential control
- conduct regulation and firm governance
- enforcement and accountability
- whether regulation balances stability and market efficiency effectively
""".strip(),
    "generic_freedom_of_expression_law": """
4500 words
1. Freedom of Expression - Problem Question
A protester is arrested for offensive speech. Advise on Article 10 ECHR, the Human Rights Act 1998, proportionality, and whether the restriction is justified.
In your answer, consider:
- whether Article 10 is engaged
- whether the restriction pursues a legitimate aim and is proportionate
- whether offensive speech remains protected on these facts
- what remedy or outcome is most likely
""".strip(),
    "generic_land_law": """
4500 words
1. Land Law - Problem Question
Advise whether Y has a lease or licence where X grants occupation of a flat for a monthly fee but reserves a right of entry, with reference to Street v Mountford, Antoniades v Villiers, exclusive possession, and the legal consequences of classification.
""".strip(),
    "generic_international_trade_law": """
4500 words
1. Trade Law - Essay Question
Critically evaluate whether global trade rules promote fairness, with reference to most-favoured-nation treatment, market access, development asymmetry, and dispute settlement.
In your answer, address:
- formal trade equality and non-discrimination
- development and structural inequality
- enforcement and bargaining power
- whether the regime promotes fairness in substance or only in form
""".strip(),
    "generic_international_law": """
4500 words
1. International Law - Essay Question
Critically evaluate whether international law can be considered truly law, discussing Article 38(1) of the ICJ Statute, state consent, treaties, custom, and enforcement objections.
In your answer, address:
- sources and validity
- state consent and obligation
- enforcement and compliance
- whether international law should be regarded as law
""".strip(),
    "generic_charity_law": """
4500 words
1. Charity Law - Essay Question
Critically evaluate whether the modern law of charitable trusts and regulation of charities provides an effective framework for accountability, with reference to the Charities Act 2011, charitable purpose, public benefit, trustees' duties, the Charity Commission, and misuse of charitable funds and powers.
In your answer, address:
- the legal meaning of charitable purpose
- the public benefit requirement
- trustees' duties and governance
- whether the present framework prevents misuse effectively in practice
""".strip(),
    "private_international_law_post_brexit": """
4500 words
1. Private International Law - Problem Question
Advise on jurisdiction, Rome I, Rome II, Brussels I Recast, the Hague 2005 Convention, and post-Brexit conflict-of-laws issues in a cross-border dispute.
In your answer, address:
- jurisdiction and forum
- choice of law
- enforcement and recognition
- the effect of Brexit on the applicable framework
""".strip(),
    "family_private_children_arrangements": """
4500 words
1. Family Law - Problem Question (Private Children)
Advise on a child-arrangements order, the welfare checklist under section 1 of the Children Act 1989, and whether a proposed internal relocation is compatible with the child's welfare.
""".strip(),
    "immigration_asylum_deportation": """
4500 words
1. Immigration Law - Problem Question (Asylum and Deportation)
Advise on refugee status, non-refoulement, Article 8 ECHR, and whether deportation is proportionate under Razgar and Part 5A of the Nationality, Immigration and Asylum Act 2002.
""".strip(),
    "international_commercial_arbitration": """
4500 words
1. International Commercial Arbitration - Essay Question
Discuss party autonomy, the seat of arbitration, separability, kompetenz-kompetenz, and the supervisory role of the Arbitration Act 1996, with reference to Fiona Trust and Enka v Chubb.
""".strip(),
    "ip_trademark_shapes": """
4500 words
1. Intellectual Property - Essay Question (Trade Marks and Shape Marks)
Discuss the limits on registering a shape mark under Trade Marks Act 1994 section 3(2), including the technical-result and substantial-value exclusions.
""".strip(),
    "land_leasehold_covenants": """
4500 words
1. Land Law - Problem Question (Leasehold Covenants)
Advise on assignment, the Landlord and Tenant (Covenants) Act 1995, authorised guarantee agreements, and whether the original tenant remains liable after assignment.
""".strip(),
    "medical_end_of_life_mca2005": """
4500 words
1. Medical Law - Problem Question (End of Life)
Advise on the legality of withdrawing treatment, the Mental Capacity Act 2005 best-interests analysis, and whether any assisted-dying or suicide-act issue arises, with reference to Bland, Pretty, and Nicklinson.
""".strip(),
    "public_international_law_customary_sources": """
4500 words
1. Public International Law - Essay Question (Customary International Law)
Discuss state practice, opinio juris, persistent objectors, specially affected states, and the ILC Conclusions on the identification of customary international law, with reference to North Sea Continental Shelf.
""".strip(),
    "public_international_law_immunities_icc": """
4500 words
1. Public International Law - Problem Question (Immunities and the ICC)
Advise whether a serving foreign minister or defence minister may invoke immunity ratione personae or immunity ratione materiae in domestic proceedings or before the ICC, with reference to Arrest Warrant, Pinochet, and Rome Statute articles 27 and 98.
""".strip(),
    "public_international_law_state_responsibility_attribution": """
4500 words
1. Public International Law - Problem Question (Attribution)
Advise whether conduct by proxy armed groups is attributable to State A under the law of state responsibility and ARSIWA articles 4 and 8, with reference to Nicaragua, Bosnia Genocide, and Tadic.
""".strip(),
    "public_international_law_use_of_force": """
4500 words
1. Public International Law - Problem Question (Use of Force)
Advise whether State A may rely on Article 51 self-defence after an alleged armed attack, with reference to Article 2(4), Article 51, Nicaragua, Oil Platforms, and Caroline.
""".strip(),
    "public_law_privacy_expression": """
4500 words
1. Public Law - Essay Question (Privacy and Expression)
Discuss how Article 8 and Article 10 should be balanced in privacy and expression disputes, with reference to Campbell v MGN Ltd, PJS, and section 12 Human Rights Act 1998.
""".strip(),
    "public_law_legitimate_expectation": """
4500 words
1. Public Law / Administrative Law - Essay Question (Legitimate Expectation and the Limits of Judicial Review)
“Over the past decades the doctrine of legitimate expectation has evolved from a procedural protection into a potential constraint on administrative policy change.”
Discuss.

In your answer, you should:
Explain the distinction between procedural and substantive legitimate expectation.
Analyse the role of clarity, reliance, fairness, and overriding public interest.
Evaluate whether the doctrine now places meaningful limits on administrative policy change.
""".strip(),
    "statutory_interpretation": """
4500 words
1. Public Law - Essay Question (Statutory Interpretation)
Discuss the literal rule, golden rule, mischief rule, and purposive interpretation, and evaluate the modern significance of Pepper v Hart and constitutional principle in statutory interpretation.
""".strip(),
    "tort_occupiers_liability": """
4500 words
1. Tort Law - Problem Question (Occupiers' Liability)
Advise whether the occupier owes duties under the Occupiers' Liability Acts 1957 and 1984 to a lawful visitor and a trespasser, with reference to Tomlinson v Congleton and Herrington.
""".strip(),
}


def _pretty_topic(topic: str) -> str:
    text = topic.replace("_", " ").replace(" tfeu", " TFEU").replace(" echr", " ECHR")
    text = text.replace(" icc", " ICC").replace(" ihl", " IHL").replace(" mca2005", " MCA 2005")
    text = text.replace(" eqa2010", " Equality Act 2010").replace(" cra2015", " CRA 2015")
    text = text.replace(" gaar", " GAAR").replace(" bhr", " BHR").replace(" pa1890", " Partnership Act 1890")
    return text.title()


def _build_prompt(topic: str) -> str:
    if topic in PROMPT_OVERRIDES:
        return PROMPT_OVERRIDES[topic]

    authorities = MUST_COVER.get(topic, [])[:4]
    if not authorities:
        authorities = [topic.replace("_", " ")]
    auth_line = "; ".join(authorities)
    qtype = "Problem Question" if topic in PROBLEM_TOPICS else "Essay Question"
    lead = "Advise on the issues raised." if qtype == "Problem Question" else "Discuss."
    asks = (
        "Identify the governing rules.\nApply them to the facts.\nAddress the strongest defence, remedy, or practical outcome."
        if qtype == "Problem Question"
        else "Explain the governing legal framework.\nAnalyse the significance of "
        + auth_line
        + ".\nEvaluate the main controversy, counterargument, or reform issue."
    )
    return f"""4500 words
1. {_pretty_topic(topic)} - {qtype}
{lead}

In your answer, you should:
{asks}
""".strip()


def _assert_config_coverage() -> None:
    missing_must_cover = [t for t in ROUTED_TOPICS if t not in MUST_COVER]
    missing_source_mix = [t for t in ROUTED_TOPICS if t not in SOURCE_MIX]
    missing_source_type = [t for t in ROUTED_TOPICS if t not in SOURCE_TYPES]
    missing_exact = [t for t in ROUTED_TOPICS if t not in TOPIC_GUIDANCE_EXACT]

    print("Config coverage:")
    print("  must_cover missing:", missing_must_cover)
    print("  source_mix missing:", missing_source_mix)
    print("  source_type missing:", missing_source_type)
    print("  exact missing:", missing_exact)

    assert not missing_must_cover
    assert not missing_source_mix
    assert not missing_source_type
    assert not missing_exact
    assert "Council of Civil Service Unions v Minister for the Civil Service" in MUST_COVER["public_law_legitimate_expectation"]
    assert "R (Bancoult) v Secretary of State for Foreign and Commonwealth Affairs" in MUST_COVER["public_law_legitimate_expectation"]
    assert SOURCE_MIX["public_law_legitimate_expectation"]["secondary"] >= 2


def _assert_topic_routing_and_gate() -> None:
    failures: List[Tuple[str, str]] = []
    for topic in ROUTED_TOPICS:
        prompt = _build_prompt(topic)
        profile = _infer_retrieval_profile(prompt)
        gate = _build_legal_answer_quality_gate(prompt, profile)
        plan = detect_long_essay(prompt)

        if profile.get("topic") != topic:
            failures.append((topic, f"routed to {profile.get('topic')}"))
        if not profile.get("must_cover"):
            failures.append((topic, "profile missing must_cover"))
        if not profile.get("source_mix_min"):
            failures.append((topic, "profile missing source_mix_min"))
        if not profile.get("source_type_hint"):
            failures.append((topic, "profile missing source_type_hint"))
        if not profile.get("issue_bank"):
            failures.append((topic, "profile missing issue_bank"))
        if not profile.get("prompt_map_asks"):
            failures.append((topic, "prompt map asks missing"))

        if "sentence (citation)." not in gate:
            failures.append((topic, "quality gate missing inline OSCOLA sentence pattern"))
        if "Keep the outer Part scaffold fixed" not in gate:
            failures.append((topic, "quality gate missing fixed outer Part scaffold rule"))

        is_problem = "Problem Question" in prompt
        if is_problem and "Problem format:" not in gate:
            failures.append((topic, "problem-format gate missing"))
        if (not is_problem) and "Essay format:" not in gate:
            failures.append((topic, "essay-format gate missing"))

        deliverables = plan.get("deliverables") or []
        if not plan.get("is_long_essay"):
            failures.append((topic, "4500-word prompt did not trigger long-answer split"))
        elif sum(int(d.get("target_words") or 0) for d in deliverables) != 4500:
            failures.append((topic, "deliverable word budget does not sum to 4500"))
        elif not deliverables:
            failures.append((topic, "no deliverables returned"))
        else:
            expected_kind = "problem" if is_problem else "essay"
            kinds = {str(d.get("unit_kind") or "") for d in deliverables}
            if kinds != {expected_kind}:
                failures.append((topic, f"deliverable kinds {sorted(kinds)} != {expected_kind}"))

    print("\nTopic routing / gate failures:")
    for topic, reason in failures:
        print(" ", topic, "->", reason)
    assert not failures


def _assert_core_validators() -> None:
    footnote_text = """Part I: Introduction

The doctrine applies.

Footnotes:
1 Competition Act 1998, s 18.
"""
    bibliography_text = """Part I: Introduction

Text.

Bibliography
Competition Act 1998
"""
    requested_bibliography_text = """Part I: Introduction

The essay states its thesis briefly.

Part II: Analysis

The analysis follows with inline support (Competition Act 1998, s 18).

Part III: Conclusion

The answer ends clearly.

Bibliography

Table of legislation
Competition Act 1998
"""
    bad_problem = """Question 1: Tort Law - Problem Question

Part I: Introduction

A. Issue

The main issue is duty of care.
"""
    good_essay = """Part I: Introduction

The essay states its thesis briefly.

Part II: Analysis

The analysis follows.

Part III: Conclusion

The answer ends clearly.
"""
    titled_essay = """Title: Administrative Law and Legitimate Expectation

Part I: Introduction

The essay states its thesis briefly.

Part II: Analysis

The analysis follows.

Part III: Conclusion

The answer ends clearly.
"""
    duplicate_heading_essay = """Part I: Introduction

The essay states its thesis and route-map briefly before moving into the key authorities and limits of intervention.

Part II: Overriding Public Interest and Policy Change

The first body section examines how fairness, public interest, and policy revision interact in substantive expectation cases, with doctrinal support and mini-conclusion.

Part III: Public Interest and Policy Change

The next section repeats the same issue cluster in slightly different words, restating fairness, restraint, and policy change rather than progressing to a new issue.

Part IV: Conclusion

The answer ends clearly and synthetically.
"""
    bad_short_form_oscola = """Part I: Introduction

The orthodox account is often associated with Paul Craig (Craig).

Part II: Conclusion

The answer ends clearly.
"""

    assert detect_essay_core_policy_violation(footnote_text)[0] is True
    assert detect_essay_core_policy_violation(bibliography_text)[0] is True
    assert detect_essay_core_policy_violation(requested_bibliography_text, allow_reference_section=True)[0] is False
    assert detect_unit_structure_policy_violation(
        bad_problem,
        unit_kind="problem",
        require_question_heading=True,
        expected_question_number=1,
        is_same_topic_continuation=False,
    )[0] is True
    assert detect_essay_core_policy_violation(good_essay)[0] is False
    assert detect_essay_core_policy_violation(titled_essay, forbid_title_line=True)[0] is True
    assert detect_essay_core_policy_violation(duplicate_heading_essay)[0] is True
    assert detect_inline_oscola_policy_violation(bad_short_form_oscola)[0] is True


def _assert_mixed_prompt_split() -> None:
    prompt = """
4500 words
1. Company Law - Essay Question
Discuss separate legal personality and veil lifting.

2. Land Law - Problem Question
Advise on an easement of way and a restrictive covenant.
""".strip()
    plan = detect_long_essay(prompt)
    deliverables = plan.get("deliverables") or []
    indices = [d.get("question_indices") for d in deliverables]
    print("\nMixed split deliverables:", indices)
    assert plan.get("split_mode") == "by_units"
    assert all(len(qs or []) == 1 for qs in indices)


def _assert_split_ranges_and_problem_duplicates() -> None:
    expected_single_parts = {
        2500: 2,
        3000: 2,
        3500: 2,
        4000: 2,
        4500: 3,
        5000: 3,
        5500: 3,
        6000: 3,
        6500: 4,
        7000: 4,
        7500: 4,
    }
    for words, expected_parts in expected_single_parts.items():
        essay_prompt = f"""{words} words
1. Administrative Law - Essay Question
Discuss legitimate expectation, fairness, policy change, proportionality, and the leading case law.
""".strip()
        essay_plan = detect_long_essay(essay_prompt)
        essay_deliverables = essay_plan.get("deliverables") or []
        assert essay_plan.get("is_long_essay") is True
        assert essay_plan.get("split_mode") == "equal_parts"
        assert essay_plan.get("suggested_parts") == expected_parts
        assert len(essay_deliverables) == expected_parts
        assert sum(int(d.get("target_words") or 0) for d in essay_deliverables) == words
        assert {str(d.get("unit_kind") or "") for d in essay_deliverables} == {"essay"}

        problem_prompt = f"""{words} words
1. Tort Law - Problem Question
Advise on duty, breach, causation, remoteness, defences, and remedies.
""".strip()
        problem_plan = detect_long_essay(problem_prompt)
        problem_deliverables = problem_plan.get("deliverables") or []
        assert problem_plan.get("is_long_essay") is True
        assert problem_plan.get("split_mode") == "equal_parts"
        assert problem_plan.get("suggested_parts") == expected_parts
        assert len(problem_deliverables) == expected_parts
        assert sum(int(d.get("target_words") or 0) for d in problem_deliverables) == words
        assert {str(d.get("unit_kind") or "") for d in problem_deliverables} == {"problem"}

        mixed_prompt = f"""{words} words
1. Administrative Law - Essay Question
Discuss legitimate expectation and policy change.

2. Tort Law - Problem Question
Advise on negligence, causation, and remedies.
""".strip()
        mixed_plan = detect_long_essay(mixed_prompt)
        mixed_deliverables = mixed_plan.get("deliverables") or []
        assert mixed_plan.get("is_long_essay") is True
        assert mixed_plan.get("split_mode") == "by_units"
        assert sum(int(d.get("target_words") or 0) for d in mixed_deliverables) == words
        assert all(len(d.get("fragments") or []) == 1 for d in mixed_deliverables)
        assert {int(d.get("question_index", 0) or 0) for d in mixed_deliverables} == {1, 2}

    duplicate_problem = """Question 1: Administrative Law - Problem Question

Part I: Introduction

The problem concerns whether the public authority can depart from its prior representation.

Part II: Issue 1 - Overriding Public Interest and Policy Change

A. Issue

The first issue is whether the authority can rely on overriding public interest and policy change.

B. Rule

The court asks whether there is a sufficient public-interest justification for departing from the earlier position.

C. Application

The authority argues that resource pressure justifies the new position.

D. Conclusion

That issue is arguable but unresolved without fuller balancing.

Part III: Issue 2 - Public Interest and Policy Change

A. Issue

The next section repeats the same public-interest and policy-change issue under a near-duplicate heading.

B. Rule

The same fairness and overriding public-interest framework is restated.

C. Application

The same balancing factors are repeated rather than advancing to a distinct issue.

D. Conclusion

This duplication should be rejected.

Part IV: Remedies / Liability

If the claimant succeeds, relief may include quashing relief and a mandatory reconsideration of the published policy.

Part V: Final Conclusion

The claimant's strongest route is therefore the legitimate-expectation claim, subject to the court's public-interest assessment.
"""
    assert detect_unit_structure_policy_violation(
        duplicate_problem,
        unit_kind="problem",
        require_question_heading=True,
        expected_question_number=1,
        starts_new_question=True,
        require_problem_terminal_sections=True,
    )[0] is True


def run() -> None:
    print("=" * 80)
    print("ALL TOPICS REGRESSION")
    print("=" * 80)
    print("Routed topics:", len(ROUTED_TOPICS))
    _assert_config_coverage()
    _assert_topic_routing_and_gate()
    _assert_core_validators()
    _assert_mixed_prompt_split()
    _assert_split_ranges_and_problem_duplicates()
    print("\nAll topic regression checks passed.")


if __name__ == "__main__":
    run()
