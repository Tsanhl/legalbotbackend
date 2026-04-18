"""
Regression checks for the user's internal complete-answer subject set.

These assertions verify two things for each prompt:
1. the backend retrieval/profile layer routes to the correct legal topic; and
2. the direct backend answer prompt includes the intended topic-specific writing guide.
"""

from model_applicable_service import (
    _backend_request_requires_mandatory_rag,
    _build_legal_answer_quality_gate,
    _build_local_code_rag_answer_prompt_block,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
)


CASES = [
    {
        "title": "Civil Procedure",
        "prompt": """Civil Procedure — Essay Question

Critically evaluate whether the modern civil procedure system in England and Wales achieves an appropriate balance between efficiency, proportionality, and access to justice.

In your answer, consider:

the overriding objective,
judicial case management,
disclosure,
costs and cost control,
sanctions for non-compliance,
and the role of settlement and ADR.""",
        "expected_topic": "civil_procedure_justice_balance",
        "must_cover_terms": ["civil procedure rules", "denton", "halsey"],
        "guide_terms": [
            "organise the essay around the tension between efficiency, proportionality, and access to justice",
        ],
        "subquery_terms": [
            "overriding objective, efficiency, and access to justice",
            "judicial case management, disclosure, costs, and sanctions",
            "settlement, adr, and the overall balance",
        ],
    },
    {
        "title": "Patent Law",
        "prompt": """Patent Law — Problem Question

Mediscan Ltd develops a portable diagnostic device that can detect a blood condition within minutes. It applies for a patent. Six months later, a rival company, BioSense plc, markets a similar device with minor design changes and argues that:

the invention was obvious,
the patent is invalid because similar research had already been presented at a medical conference,
and in any event its own device does not infringe.

A former Mediscan employee also claims he, rather than the company, should be treated as the true inventor.

Advise the parties. In particular, consider:

patentability,
novelty and inventive step,
ownership of the invention,
infringement,
and remedies.""",
        "expected_topic": "patent_validity_infringement_ownership",
        "must_cover_terms": ["patents act 1977", "pozzoli", "actavis uk ltd v eli lilly and co"],
        "guide_terms": [
            "separate validity, entitlement/ownership, infringement, and remedies into distinct sections",
        ],
        "subquery_terms": [
            "patentability, novelty, and inventive step",
            "entitlement, ownership, and the true inventor dispute",
            "infringement, design changes, and remedies",
        ],
    },
    {
        "title": "Prison Law",
        "prompt": """Prison Law — Essay Question

Critically evaluate whether prisoners in England and Wales retain meaningful legal protection against arbitrary or disproportionate treatment by the state.

In your answer, consider:

the legal status of prisoners,
judicial review of prison decisions,
procedural fairness,
rights under the European Convention on Human Rights,
and the extent to which courts defer to prison administration.""",
        "expected_topic": "prison_law_state_treatment_review",
        "must_cover_terms": ["prison act 1952", "simms", "bourgass"],
        "guide_terms": [
            "start with the prisoner's continuing legal status",
        ],
        "subquery_terms": [
            "the prisoner's continuing legal status",
            "judicial review, procedural fairness, and prison decision-making",
            "convention rights, deference, and meaningful protection",
        ],
    },
    {
        "title": "Education Law",
        "prompt": """Education Law — Problem Question

A secondary school permanently excludes Tariq, a 15-year-old pupil, after a series of disruptive incidents. Tariq's parents argue that:

the school failed to take proper account of his diagnosed ADHD,
they were not given key evidence before the exclusion hearing,
the governing body upheld the decision without proper reasons,
and the exclusion will seriously affect his exam prospects.

Advise Tariq's parents. In particular, consider:

procedural fairness,
public law challenge,
equality law issues,
relevance of special educational needs,
and possible remedies.""",
        "expected_topic": "education_school_exclusion_send",
        "must_cover_terms": ["education act 2002", "send code of practice", "doody"],
        "guide_terms": [
            "run the problem in this order: exclusion procedure, fairness/reasons/evidence, send-disability duties, then remedies",
        ],
        "subquery_terms": [
            "exclusion procedure, evidence, and reasons",
            "adhd, send, and equality duties",
            "public-law challenge and remedies",
        ],
    },
    {
        "title": "Public Procurement",
        "prompt": """Public Procurement Law — Essay Question

Critically evaluate whether the law governing public procurement strikes the right balance between transparency, competition, and practical flexibility in public contracting.

In your answer, consider:

equal treatment and non-discrimination,
transparency,
discretion in award decisions,
challenges by unsuccessful bidders,
and whether procurement law is too formalistic or an essential safeguard against misuse of public funds.""",
        "expected_topic": "public_procurement_award_challenges",
        "must_cover_terms": ["procurement act 2023", "procurement regulations 2024", "faraday development ltd v west berkshire council"],
        "guide_terms": [
            "separate the procurement objectives and transparency/equal-treatment constraints from the authority's operational flexibility",
        ],
        "subquery_terms": [
            "transparency, equal treatment, and competition",
            "award discretion, flexibility, and practical contracting needs",
            "challenges, remedies, and whether formalism is justified",
        ],
    },
    {
        "title": "Pensions Law",
        "prompt": """Pensions Law — Problem Question

Northgate Engineering Ltd closes its final salary pension scheme and replaces it with a less generous defined contribution arrangement. Employees say they were repeatedly told by managers and scheme representatives that their accrued expectations were "fully protected" and that the changes would make "no real difference" to retirement outcomes. Some employees now claim significant financial loss.

Advise the employees. In particular, consider:

the legal status of accrued pension rights,
possible claims based on misleading statements,
duties of trustees and employers,
consultation obligations,
and the practical difficulties in establishing loss and remedy.""",
        "expected_topic": "pensions_scheme_change_misrepresentation",
        "must_cover_terms": ["pensions act 1995", "section 67 pensions act 1995", "scally v southern health and social services board"],
        "guide_terms": [
            "front-load the pensions context and separate accrued-rights protection from softer expectations about future accrual or retirement outcomes",
        ],
        "subquery_terms": [
            "accrued rights and the scheme-change baseline",
            "misleading statements, estoppel, and misrepresentation",
            "trustee or employer duties, consultation, loss, and remedy",
        ],
    },
    {
        "title": "Product Liability",
        "prompt": """Product Liability — Essay Question

Critically evaluate whether the modern law of product liability provides an adequate framework for protecting consumers in an age of complex supply chains and advanced technology.

In your answer, consider:

negligence,
strict liability,
proof of defect,
causation,
the position of manufacturers, importers, and retailers,
and whether current doctrine is well suited to software-enabled and AI-assisted products.""",
        "expected_topic": "product_liability_consumer_protection",
        "must_cover_terms": ["consumer protection act 1987", "a v national blood authority", "wilkes v depuy international ltd"],
        "guide_terms": [
            "separate negligence, strict liability under the 1987 act, proof of defect, causation, and defendant categories",
        ],
        "subquery_terms": [
            "negligence and strict liability under the consumer protection act",
            "defect, causation, and defendant categories in complex supply chains",
            "software-enabled products, ai, and overall adequacy",
        ],
    },
    {
        "title": "Election Law",
        "prompt": """Election Law — Problem Question

During a closely fought local election campaign, a candidate's team publishes targeted online advertisements that are not properly recorded in the official spending return. It also later emerges that a substantial donation came through an intermediary with possible links to an overseas source. The losing candidate wants to challenge the result.

Advise the losing candidate. In particular, consider:

campaign finance regulation,
reporting and donation rules,
possible consequences of unlawful spending,
challenge to the election result,
and the practical and evidential difficulties involved.""",
        "expected_topic": "election_law_campaign_finance",
        "must_cover_terms": ["political parties, elections and referendums act 2000", "representation of the people act 1983", "morgan v simpson"],
        "guide_terms": [
            "separate spending/reporting breaches, donation legality, criminal or regulatory consequences, and challenge to the result",
        ],
        "subquery_terms": [
            "spending returns, online campaigning, and donation legality",
            "criminal, regulatory, and petition consequences",
            "evidence, causation, and realistic challenge outcome",
        ],
    },
    {
        "title": "Secured Transactions",
        "prompt": """Secured Transactions / Personal Property — Essay Question

Critically evaluate whether the law governing security over personal property is coherent and commercially workable.

In your answer, consider:

fixed and floating charges,
retention of title clauses,
priority disputes,
registration and transparency,
and whether the present law produces unnecessary complexity for lenders, insolvency practitioners, and unsecured creditors.""",
        "expected_topic": "secured_transactions_priority",
        "must_cover_terms": ["companies act 2006 part 25", "spectrum plus", "romalpa"],
        "guide_terms": [
            "separate fixed charges, floating charges, and retention-of-title clauses before evaluating priority",
        ],
        "subquery_terms": [
            "fixed charges, floating charges, and retention of title",
            "priority, registration, and insolvency distribution",
            "commercial workability and overall coherence",
        ],
    },
    {
        "title": "Art and Cultural Property",
        "prompt": """Art and Cultural Property Law — Problem Question

A London gallery sells a painting to a private collector. Two years later, a foreign state claims that the work was unlawfully removed from a public museum during a period of civil unrest and demands its return. The collector says he bought in good faith, paid full value, and had no notice of any problem with title.

Advise the parties. In particular, consider:

title to stolen or unlawfully exported cultural objects,
good faith purchase,
limitation and recovery issues,
the possible relevance of international conventions,
and the remedies that may be available.""",
        "expected_topic": "cultural_heritage_illicit_trafficking",
        "must_cover_terms": ["unesco 1970 convention", "unidroit 1995 convention", "dealing in cultural objects (offences) act 2003"],
        "guide_terms": [
            "separate unesco or unidroit frameworks from domestic property or criminal routes",
        ],
        "subquery_terms": [
            "international framework and timing",
            "title, lex situs, and good-faith acquisition",
            "recovery routes and practical outcome",
        ],
    },
]


for case in CASES:
    profile = _infer_retrieval_profile(case["prompt"])
    assert profile.get("topic") == case["expected_topic"], (case["title"], profile.get("topic"))
    assert _backend_request_requires_mandatory_rag(case["prompt"]) is True, case["title"]

    must_cover_blob = " || ".join(profile.get("must_cover") or []).lower()
    for term in case["must_cover_terms"]:
        assert term in must_cover_blob, (case["title"], "must_cover", term, must_cover_blob)

    source_type_hint = (profile.get("source_type_hint") or "").lower()
    assert source_type_hint and source_type_hint != "statute | judgment | core textbook", (
        case["title"],
        "source_type_hint",
        source_type_hint,
    )
    source_mix = profile.get("source_mix_min") or {}
    assert int(source_mix.get("cases", 0)) >= 2, (case["title"], "source_mix_cases", source_mix)
    assert int(source_mix.get("secondary", 0)) >= 1, (case["title"], "source_mix_secondary", source_mix)

    answer_prompt = _build_local_code_rag_answer_prompt_block(
        case["prompt"],
        enforce_long_response_split=False,
    ).lower()
    assert "[local code + rag legal answer mode]" in answer_prompt, case["title"]

    subquery_blob = " || ".join(
        label for label, _ in _subissue_queries_for_unit(case["title"], case["prompt"])
    ).lower()
    for term in case["subquery_terms"]:
        assert term in subquery_blob, (case["title"], "subqueries", term, subquery_blob)

    quality_gate = _build_legal_answer_quality_gate(case["prompt"], profile).lower()
    assert "[legal quality gate]" in quality_gate, case["title"]
    for term in case["guide_terms"]:
        assert term in quality_gate, (case["title"], "guide", term, quality_gate[:3000])


print("Internal complete-answer subject routing + guide regression passed.")
