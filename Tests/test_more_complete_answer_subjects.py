"""
Regression checks for the second internal complete-answer subject set.

These assertions verify:
1. the backend retrieval/profile layer routes each prompt to the intended topic;
2. mandatory RAG is still enforced for these legal complete-answer prompts; and
3. the legal answer quality gate contains the subject-specific writing guide.
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
        "title": "Contract Law",
        "prompt": """Contract Law — Essay Question

Critically evaluate whether the modern law of contract takes a coherent approach to the control of unfairness.

In your answer, consider:

consideration,
promissory estoppel,
misrepresentation,
duress,
undue influence,
and whether the law relies too heavily on indirect controls rather than a general doctrine of unfairness.""",
        "expected_topic": "contract_unfairness_controls",
        "must_cover_terms": ["foakes v beer", "high trees", "etridge"],
        "guide_terms": [
            "absence of a general doctrine of unfairness",
        ],
        "subquery_terms": [
            "why unfairness is controlled indirectly",
            "bargain-enforcement limits: consideration and promissory estoppel",
            "consent-based controls: misrepresentation, duress, and undue influence",
            "coherent restraint or fragmented patchwork?",
        ],
    },
    {
        "title": "Tort Law",
        "prompt": """Tort Law — Problem Question

Finch Architects prepares a report for a property developer stating that a city-centre building is structurally suitable for conversion into luxury flats. The developer shows the report to a lender, which advances funds on the strength of it. After work begins, major defects are discovered. The developer suffers heavy losses and the lender is left undersecured.

Advise the developer and the lender. In particular, consider:

duty of care,
negligent misstatement,
assumption of responsibility,
pure economic loss,
and any limits on recovery.""",
        "expected_topic": "tort_economic_loss_negligent_misstatement",
        "must_cover_terms": ["hedley byrne", "caparo", "smith v eric s bush"],
        "guide_terms": [
            "for each claimant, ask separately whether there was an assumption of responsibility",
        ],
        "subquery_terms": [
            "direct reader: negligent misstatement and assumption of responsibility",
            "downstream reader: second-hand reliance and scope of duty",
            "competitor: market loss and pure economic loss limits",
            "remoteness, disclaimers, and overall recoverability",
        ],
    },
    {
        "title": "Criminal Law",
        "prompt": """Criminal Law — Essay Question

Critically evaluate whether the modern law on complicity in England and Wales is conceptually coherent and morally justified.

In your answer, consider:

the basis of accessory liability,
intention and foresight,
the significance of Jogee,
withdrawal,
and whether the law draws a convincing distinction between principal and accessory responsibility.""",
        "expected_topic": "criminal_complicity",
        "must_cover_terms": ["accessories and abettors act 1861", "jogee", "joint enterprise"],
        "guide_terms": [
            "do not treat foresight as the substantive complicity test after jogee",
        ],
        "subquery_terms": [
            "jogee and the mental element for complicity",
            "participation, withdrawal, and overreach",
            "fairness, certainty, and evaluation",
        ],
    },
    {
        "title": "Public Law",
        "prompt": """Public Law — Problem Question

Parliament passes the Public Order Management Act 2026, giving the Home Secretary power to issue "binding operational guidance" to local authorities for the protection of public calm. The Home Secretary issues guidance stating that protests "likely to provoke strong feelings" should normally be prohibited. A council refuses permission for a peaceful demonstration criticising government housing policy, relying entirely on the guidance.

Advise the organisers. In particular, consider:

amenability to judicial review,
legality of the guidance,
fettering of discretion,
freedom of expression and assembly,
and possible remedies.""",
        "expected_topic": "public_law_fettering_expression_assembly",
        "must_cover_terms": ["article 10 echr", "british oxygen", "laporte"],
        "guide_terms": [
            "separate the legality of central guidance, the council's possible fettering of discretion, and the articles 10 and 11 proportionality analysis",
        ],
        "subquery_terms": [
            "legality of the guidance and effect of the ouster clause",
            "policy versus rule, fettering, and opaque decision-support",
            "procedural fairness, reasons, legitimate expectation, and convention rights",
            "remedies and likely challenge outcome",
        ],
    },
    {
        "title": "Land Law",
        "prompt": """Land Law — Essay Question

Critically evaluate whether the law on overriding interests under the system of registered land is justified.

In your answer, consider:

the goals of registration,
actual occupation,
protection of third-party rights,
certainty for purchasers,
and whether overriding interests are a necessary safeguard or an unacceptable qualification of the register.""",
        "expected_topic": "land_registered_overriding_interests",
        "must_cover_terms": ["land registration act 2002", "schedule 3 paragraph 2", "boland"],
        "guide_terms": [
            "separate the registration ideal from the survival of overriding interests",
        ],
        "subquery_terms": [
            "registration goals and the ideal of certainty",
            "actual occupation and off-register protection",
            "safeguard or unacceptable qualification?",
        ],
    },
    {
        "title": "Equity and Trusts",
        "prompt": """Equity and Trusts — Problem Question

Aisha transfers £200,000 to her brother Karim to hold "for the family" until she decides how it should be used. Karim pays £80,000 into his personal trading account, uses £40,000 to pay off his mortgage, and later buys shares that increase significantly in value. He then becomes insolvent.

Advise Aisha. In particular, consider:

certainty of intention, subject matter, and objects,
whether a trust was created,
breach of trust,
tracing at common law and in equity,
and remedies against Karim and third parties.""",
        "expected_topic": "equity_trust_creation_tracing",
        "must_cover_terms": ["knight v knight", "re hallett", "foskett v mckeown"],
        "guide_terms": [
            "decide first whether a valid trust was created, then keep breach, tracing, and remedy analysis distinct",
        ],
        "subquery_terms": [
            "was a trust created?",
            "breach of trust and tracing through the mixed fund",
            "mortgage discharge, appreciating shares, and insolvency",
            "best remedies against karim and others",
        ],
    },
    {
        "title": "EU Law",
        "prompt": """EU Law — Essay Question

Critically evaluate whether the doctrine of state liability provides a satisfactory solution to the limits of direct effect in EU law.

In your answer, consider:

Francovich,
Brasserie du Pêcheur,
the relationship between direct effect, indirect effect, and state liability,
effectiveness and uniformity,
and whether the doctrine is principled or mainly remedial pragmatism.""",
        "expected_topic": "eu_supremacy_direct_effect_preliminary_references",
        "must_cover_terms": ["francovich", "brasserie", "article 267"],
        "guide_terms": [
            "state the francovich/brasserie conditions explicitly",
        ],
        "subquery_terms": [
            "supremacy and constitutional authority",
            "direct effect and the horizontal gap",
            "indirect effect and state liability as compensatory techniques",
            "national constitutional resistance and legitimacy",
        ],
    },
    {
        "title": "Company Law",
        "prompt": """Company Law — Problem Question

Velora Ltd has four directors. One director causes the company to enter into a long-term services contract with a business owned by her partner without disclosure. A second director approves the deal without reading the papers. A third raises concerns but takes no further action. The fourth is a non-executive director who rarely attends meetings. Minority shareholders want action, but the majority shareholder refuses to challenge the board.

Advise the minority shareholders. In particular, consider:

directors' duties,
conflicts of interest,
care, skill and diligence,
ratification,
derivative claims,
and unfair prejudice.""",
        "expected_topic": "company_directors_minorities",
        "must_cover_terms": ["companies act 2006", "section 175", "section 994"],
        "guide_terms": [
            "separate clarity from effectiveness. codification under the companies act 2006 may make duties easier to state without making accountability materially easier to enforce",
        ],
        "subquery_terms": [
            "unfair-prejudice gateway",
            "alternative routes and litigation strategy",
            "likely minority remedy",
        ],
    },
    {
        "title": "Family Law",
        "prompt": """Family Law — Essay Question

Critically evaluate whether the current law in England and Wales takes a coherent approach to financial provision on divorce.

In your answer, consider:

judicial discretion,
needs, sharing, and compensation,
the tension between flexibility and certainty,
the treatment of non-matrimonial property,
and whether reform is needed.""",
        "expected_topic": "family_financial_provision_divorce",
        "must_cover_terms": ["matrimonial causes act 1973", "white v white", "radmacher"],
        "guide_terms": [
            "organise the essay around section 25 discretion, then the modern organising principles of needs, sharing, and compensation",
        ],
        "subquery_terms": [
            "section 25 discretion and the search for structure",
            "needs, sharing, and compensation",
            "non-matrimonial property and certainty pressures",
            "is reform needed?",
        ],
    },
    {
        "title": "Employment Law",
        "prompt": """Employment Law — Problem Question

Rina has worked for a retail chain for six years. After repeated complaints about unpaid overtime and understaffing, she sends an internal email to senior management alleging that the company is manipulating working-time records. Two weeks later she is dismissed for "disruptive conduct and loss of trust." The employer says the dismissal was about her attitude, not the substance of her complaints.

Advise Rina. In particular, consider:

unfair dismissal,
whistleblowing protection,
causation,
the employer's stated reason for dismissal,
and the remedies that may be available.""",
        "expected_topic": "employment_whistleblowing_unfair_dismissal",
        "must_cover_terms": ["section 43b", "jhuti", "chesterton"],
        "guide_terms": [
            "decide status first where the working arrangement is dressed up as consultancy or a service company",
        ],
        "subquery_terms": [
            "employment status: employee, worker, and service-company structure",
            "protected disclosure, external reporting, and causation",
            "claims, remedies, and practical litigation strategy",
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
        assert term in quality_gate, (case["title"], "guide", term, quality_gate[:4000])


print("More complete-answer subject routing + guide regression passed.")
