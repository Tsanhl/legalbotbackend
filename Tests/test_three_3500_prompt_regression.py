"""
Regression checks for three harder 3500-word complete-answer prompts.

These assertions verify:
1. mandatory RAG remains active;
2. each prompt still routes to the intended topic profile;
3. the quality gate now reflects the deeper issues added for this harder batch; and
4. the subquery planner keeps the long-form issue structure explicit.
"""

from model_applicable_service import (
    _backend_request_requires_mandatory_rag,
    _build_legal_answer_quality_gate,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
)


CASES = [
    {
        "title": "Public Law 3500 Problem",
        "label": "Public Law — Problem Question",
        "prompt": """Public Law — Problem Question

Parliament enacts the Civic Order and Community Confidence Act 2027. The Act empowers the Secretary of State to issue guidance to local authorities on the management of public assemblies “for the protection of community confidence, institutional trust, and public calm.” It also provides that local authorities may refuse permission for large public events where this is “necessary in the interests of social stability.”

The Act contains a clause stating:

“A decision made under this Part shall not be questioned in any court except on grounds of bad faith.”

Six months later, the Secretary of State publishes the National Community Stability Guidance 2027. It states that local authorities should ordinarily refuse permission for demonstrations that are likely to generate:

“intense public controversy,”
“serious reputational damage to local institutions,” or
“sustained social unease.”

The Guidance was not laid before Parliament. No consultation took place before it was issued.

Eastmere Council then refuses permission for a peaceful march proposed by Parents for Safe Housing, a group campaigning against a government-backed redevelopment scheme involving the demolition of local social housing. The refusal letter states only that:

the event is inconsistent with the national Guidance,
the event may undermine public confidence in local authorities,
and permission is therefore refused.

No fuller reasons are given.

It later emerges that:

Council officers treated the Guidance as binding,
no independent consideration was given to the particular facts of the proposed march,
a private contractor, CivicMetrics Ltd, had generated a “risk score” for the event using undisclosed criteria,
and the Council had previously published a community charter promising that “peaceful civic participation will remain central to local democratic life in Eastmere.”

At the same time, Eastmere Council cancels a booking made by Tenants for Accountability, a related group, to use a council-owned hall for a public meeting on the redevelopment plans. The Council says the meeting may attract “politically charged messaging” and create “community instability.”

The groups seek legal advice.

Advise the groups. In particular, consider:

the legal status of the Guidance,
whether the Guidance is lawful, advisory, or in substance an unlawful rule,
fettering of discretion,
the effect of the ouster clause,
procedural fairness and adequacy of reasons,
the significance of undisclosed algorithmic decision-support,
legitimate expectation arising from the Council’s charter,
Articles 10 and 11 ECHR,
proportionality and traditional judicial review grounds,
and the remedies most likely to be granted.""",
        "expected_topic": "public_law_fettering_expression_assembly",
        "must_cover_terms": ["anisminic", "privacy international"],
        "guide_terms": [
            "challenge to the statutory framework, challenge to the guidance",
            "ouster clause or restricted-review formula",
            "private contractor or algorithmic risk score",
            "council-owned hall or venue",
            "policy language can still be lawful",
        ],
        "subquery_terms": [
            "legality of the guidance and effect of the ouster clause",
            "policy versus rule, fettering, and opaque decision-support",
            "procedural fairness, reasons, legitimate expectation, and convention rights",
            "remedies and likely challenge outcome",
        ],
    },
    {
        "title": "Land 3500 Problem",
        "label": "Land Law / Equity and Trusts — Problem Question",
        "prompt": """Land Law / Equity and Trusts — Problem Question

Adrian purchases a registered property called Willow House in his sole name. His partner, Leila, is not placed on the title because she had recently left salaried employment to start a small business and Adrian said that a sole-name mortgage would be easier to arrange.

Before completion, Adrian tells Leila:

“This is our home. I know the title is only in my name, but half of this place is yours.”

Over the next eight years:

Leila spends £90,000 from an inheritance on a loft conversion, structural repairs, and adaptations for Adrian’s disabled mother, who later moves into the house.
Leila pays most household bills and food costs.
She makes a series of bank transfers to Adrian, some marked “mortgage” and others unlabelled.
She reduces her working hours to care for Adrian’s mother and for the couple’s child.
In text messages and emails, Adrian and Leila repeatedly refer to Willow House as “our house” and “our family home.”

Five years after purchase, Adrian secretly transfers the legal title into the joint names of himself and his sister Naomi, stating that this is for “family asset protection.” Naomi pays nothing for the transfer. Adrian then persuades Naomi to join him in granting a legal charge over Willow House to Redwood Bank plc to secure Adrian’s failing business debts. The loan advance is paid into an account controlled by Adrian and Naomi jointly.

Before taking the charge, Redwood sends a valuer to inspect the property. The valuer sees:

Leila living there,
Adrian’s mother occupying a ground-floor adapted bedroom,
family photographs and documents throughout the house,
and a child’s bedroom used by Adrian and Leila’s son.

No enquiry is made of Leila about any rights she may have.

Adrian later defaults on the loan and dies unexpectedly. Naomi argues that:

Leila never contributed to the purchase price,
household expenditure is legally irrelevant,
any beneficial interest Leila may once have had was overreached when the bank advanced money to two legal owners,
and Redwood is therefore entitled to possession and sale free of Leila’s claim.

Leila seeks advice. Redwood and Naomi also seek advice.

Advise Leila, Naomi, and Redwood Bank plc. In particular, consider:

common intention constructive trust,
proprietary estoppel,
the significance of express assurances,
direct and indirect contributions,
the legal relevance of domestic and caring contributions,
the transfer into joint names and its significance,
overreaching,
actual occupation and overriding interests,
the lender’s position,
quantification of any beneficial share,
and the remedies likely to be available.""",
        "expected_topic": "land_home_coownership_estoppel_priority",
        "guide_terms": [
            "transfer into joint names or to a volunteer",
            "capital money to two trustees",
            "the claimant's earlier equity persists",
        ],
        "subquery_terms": [
            "beneficial interest: resulting trust weakness and common-intention constructive trust",
            "proprietary estoppel and assurance-based equity",
            "later transfer into joint names and effect on the earlier equity",
            "priority, actual occupation, and binding effect on third parties",
            "quantification and practical remedies",
        ],
    },
    {
        "title": "Employment 3500 Problem",
        "label": "Employment Law — Problem Question",
        "prompt": """Employment Law — Problem Question

Dr Sana Rahman works for AppWell Health Ltd, a private company developing an AI-assisted medical triage platform for use by NHS providers. For six years, Sana has worked full-time for AppWell under a contract describing her as an “independent consultant” engaged through her own service company. However:

she must perform the work personally,
she works fixed hours at AppWell’s offices,
she is integrated into AppWell’s management structure,
she uses AppWell’s equipment and email systems,
she must comply with internal policies,
and she is not permitted to provide similar services to competitors without permission.

Over time:

Sana repeatedly raises internal concerns that the AI system is generating unsafe dosage recommendations for some patients,
she tells senior management that safety-testing data is being presented misleadingly to potential NHS purchasers,
and she later reports her concerns to an external healthcare regulator.

Shortly after doing so, Sana is excluded from key meetings and removed from a major clinical oversight role.

A year later, Sana goes on maternity leave. While she is away:

her responsibilities are redistributed,
the company recruits a new “Clinical Strategy Lead,”
and management begins describing Sana’s role internally as “commercially non-essential.”

On her return from maternity leave:

she is told her role has “changed significantly,”
she is required to sign a new agreement containing a broad confidentiality clause and a strict social-media policy,
and she is warned after posting on her personal account that “patient safety must come before growth targets in health tech.”

Two weeks later, AppWell terminates the relationship, stating that:

Sana is not an employee,
her contract is being ended because of “loss of trust and confidence,”
her social-media comments damaged the company,
and in any event the business is undergoing restructuring.

Sana says the real reason is that she raised safety concerns and returned from maternity leave. She also says that the company’s insistence that she contract through a service company was never a real reflection of the working relationship.

Advise Sana and AppWell Health Ltd. In particular, consider:

employment status,
employee and worker tests,
unfair dismissal,
automatic unfair dismissal and protected disclosures,
whistleblowing detriment,
the significance of external regulatory disclosure,
pregnancy and maternity discrimination,
possible sex discrimination,
the employer’s stated reasons for termination,
the relevance of social-media expression,
remedies and practical litigation strategy,
and the likely strengths and weaknesses of Sana’s claims.""",
        "expected_topic": "employment_whistleblowing_unfair_dismissal",
        "must_cover_terms": [
            "section 230",
            "section 43f",
            "ready mixed concrete",
            "autoclenz",
            "uber",
            "section 18",
        ],
        "guide_terms": [
            "decide status first",
            "pregnancy or maternity discrimination route",
            "service company",
            "social-media complaints",
        ],
        "subquery_terms": [
            "employment status: employee, worker, and service-company structure",
            "protected disclosure, external reporting, and causation",
            "maternity return, discrimination, and employer reasons",
            "claims, remedies, and practical litigation strategy",
        ],
    },
]


for case in CASES:
    profile = _infer_retrieval_profile(case["prompt"])
    assert profile["topic"] == case["expected_topic"], case["title"]
    assert _backend_request_requires_mandatory_rag(case["prompt"], {"active": False}) is True, case["title"]

    must_cover_blob = " || ".join(profile.get("must_cover") or []).lower()
    for term in case.get("must_cover_terms", []):
        assert term in must_cover_blob, (case["title"], "must_cover", term, must_cover_blob)

    gate = _build_legal_answer_quality_gate(case["prompt"], profile).lower()
    for term in case["guide_terms"]:
        assert term in gate, (case["title"], "guide", term, gate[:7000])

    subquery_blob = " || ".join(
        title.lower() for title, _ in _subissue_queries_for_unit(case["label"], case["prompt"])
    )
    for term in case["subquery_terms"]:
        assert term in subquery_blob, (case["title"], "subqueries", term, subquery_blob)


print("Three 3500-word prompt regression passed.")
