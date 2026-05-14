"""
Regression coverage for the remaining high-value boundary prompts.

These checks harden the final overlap areas where realistic mixed prompts can
still drift between adjacent topics unless routing, guide text, and subqueries
stay prompt-shaped.
"""

from model_applicable_service import (
    _backend_request_requires_mandatory_rag,
    _build_legal_answer_quality_gate,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
)


CASES = [
    {
        "title": "Equity Fiduciary / Tracing Boundary",
        "label": "Equity - Problem Question",
        "prompt": """Equity - Problem Question

Imogen is trustee of a family settlement that owns a long lease of riverside land. While negotiating redevelopment on the trust's behalf, she arranges for a separate company owned by her partner to take a profitable side-deal opportunity that arose only because of her position as trustee. The profits are then used partly to reduce the mortgage on her own flat and partly to buy shares that later rise sharply in value. The beneficiaries say Imogen acted in a conflict of interest and made an unauthorised profit, but they also want to trace into the mortgage saving and the shares.

Advise the beneficiaries. In particular, consider:

the nature of fiduciary loyalty,
no-conflict and no-profit principles,
whether Imogen can claim any allowance,
personal and proprietary remedies,
and how the proprietary claims interact with tracing into substitute assets.""",
        "expected_topic": "equity_fiduciary_duties",
        "must_cover_terms": ["fhr european ventures", "guinness plc v saunders", "boardman v phipps"],
        "subquery_terms": [
            "fiduciary position, conflict, and the side-deal opportunity",
            "no-profit liability, honesty, and allowance",
            "mortgage saving, shares, and proprietary consequences",
        ],
        "guide_terms": [
            "separate the existence and breach of fiduciary duty from the later question whether the beneficiaries can follow or trace the profit into substitute assets",
        ],
    },
    {
        "title": "Equity Tracing Boundary",
        "label": "Equity and Trusts - Problem Question",
        "prompt": """Equity and Trusts - Problem Question

Arun transfers GBP400,000 to Karim saying in an email that the money is to be held "for the family education fund until I give instructions." Karim pays part of the money into his trading account, uses some to discharge the mortgage on his house, and buys shares with the rest. He later tells Arun that he believed he could use the money temporarily because he intended to replace it. Arun says there was a valid trust and wants recovery against Karim, the house, and the shares. Karim replies that no trust was properly created and that, in any event, Arun is really complaining about Karim's disloyal behaviour.

Advise Arun. In particular, consider:

the three certainties,
whether a trust arose,
breach of trust,
common-law and equitable tracing,
claims against the mortgage saving and the shares,
and the relationship between proprietary and personal remedies.""",
        "expected_topic": "equity_trust_creation_tracing",
        "must_cover_terms": ["knight v knight", "re hallett's estate", "foskett v mckeown"],
        "subquery_terms": [
            "was a trust created?",
            "breach of trust and tracing through the mixed fund",
            "mortgage discharge, appreciating shares, and insolvency",
        ],
    },
    {
        "title": "Equity Fiduciary Essay Residual",
        "label": "Equity and Trusts - Essay Question",
        "prompt": """Equity and Trusts - Essay Question

Critically evaluate whether the law on breach of fiduciary duty is justified in imposing strict liability for conflicts of interest and unauthorised profits. In your answer, consider the no-conflict and no-profit rules, the rationale of fiduciary loyalty, allowances, and whether modern commercial practice requires a more flexible approach.""",
        "expected_topic": "equity_fiduciary_duties",
        "must_cover_terms": ["keech v sandford", "regal (hastings) ltd v gulliver", "boardman v phipps"],
        "subquery_terms": [
            "nature and rationale of fiduciary loyalty",
            "no-conflict and no-profit rules",
            "commercial flexibility and reform critique",
        ],
    },
    {
        "title": "AI Discrimination With DP Detail",
        "label": "AI / Algorithmic Discrimination - Problem Question",
        "prompt": """AI / Algorithmic Discrimination - Problem Question

A metropolitan borough uses an AI-assisted homelessness triage system to decide who receives urgent temporary accommodation. Internal audits show that disabled applicants, survivors of domestic abuse, and applicants with limited English are disproportionately scored as low priority. The borough says the software vendor is only a processor, while campaigners argue the borough and vendor are joint controllers because they jointly designed the risk categories and review rules. Applicants are given only a short automated outcome notice and caseworkers almost always confirm the score without real reconsideration.

Advise Maya, who was denied urgent accommodation. In particular, consider:

discrimination law,
public law fairness,
controller and processor status,
lawful basis and special category data,
Article 22, transparency, and explainability,
human review,
and remedies for both Maya and the wider campaign group.""",
        "expected_topic": "ai_algorithmic_discrimination",
        "must_cover_terms": ["equality act 2010", "article 22", "article 9"],
        "subquery_terms": [
            "discrimination routes, proxies, and proof difficulty",
            "controllers, lawful basis, and special-category processing",
            "automated notice, article 22, and meaningful human review",
        ],
        "guide_terms": [
            "separate discrimination and public-law fairness from the controller or processor allocation and lawful-basis questions",
        ],
    },
    {
        "title": "Data Protection With AI Bias",
        "label": "Data Protection / AI Triage - Problem Question",
        "prompt": """Data Protection / AI Triage - Problem Question

CarePath Ltd supplies an AI risk-scoring tool to several NHS trusts and a private telehealth provider. The model uses health histories, medication patterns, and free-text symptom descriptions to rank patients for urgent appointments. Disabled users and users whose first language is not English appear to receive consistently worse scores. CarePath says each trust is the controller and it is only a processor; one trust says the parties are joint controllers because CarePath keeps using patient data to refine the model across the network. Patients receive automated messages saying they are low priority and are offered only a narrow right to request review.

Advise the affected patients. In particular, consider:

controller and processor status,
lawful basis,
special category data,
Article 22 and meaningful human review,
transparency,
accuracy and fairness,
and the interaction between data protection and discrimination concerns.""",
        "expected_topic": "data_protection",
        "must_cover_terms": ["uk gdpr", "article 22", "data protection act 2018"],
        "subquery_terms": [
            "controllers, processors, and the data-sharing chain",
            "health data, lawful basis, special-category conditions, and transparency",
            "bias, accuracy, individual remedies, and ico enforcement",
        ],
    },
    {
        "title": "Public-Law Fettering Boundary",
        "label": "Public Law / Human Rights - Problem Question",
        "prompt": """Public Law / Human Rights - Problem Question

A city council adopts a "Civic Trust and Safety Protocol" stating that groups which repeatedly spread "destabilising narratives" about regeneration policy may be denied access to council halls, consultation forums, and grant-funded events. The protocol also permits officers to compile profiles of organisers' online activity and personal associations when assessing "reputational risk." A tenants' union that has sharply criticised a redevelopment project is excluded from a public consultation venue. The council had previously promised in a published participation charter that robust criticism would remain central to local democracy.

Advise the tenants' union. In particular, consider:

fettering of discretion,
freedom of expression and assembly,
privacy and data profiling,
legitimate expectation,
proportionality,
procedural fairness,
and likely remedies.""",
        "expected_topic": "public_law_fettering_expression_assembly",
        "must_cover_terms": ["article 10 echr", "article 8 echr", "r (coughlan) v north and east devon health authority"],
        "subquery_terms": [
            "policy legality, vagueness, and fettering",
            "venue exclusion, expression, and proportionality",
            "profiling, privacy, and procedural fairness",
        ],
        "guide_terms": [
            "separate the policy-level challenge to the council programme from the specific denial of venue or forum access and from the undisclosed data-profiling complaint",
        ],
    },
    {
        "title": "Public-Law Legitimate Expectation Boundary",
        "label": "Public Law - Problem Question",
        "prompt": """Public Law - Problem Question

A regional authority publishes a relocation policy promising that any community centre facing closure will receive a full local consultation and that existing user groups will be able to make representations before final decisions are taken. A year later, after strong online criticism of its spending plans, the authority abruptly withdraws funding from a long-standing migrant support centre, refuses the group access to the usual consultation hall, and circulates internal briefing notes summarising the organiser's social-media activity. The authority says the earlier policy was only guidance and that concerns about misinformation justified tighter control.

Advise the support centre. In particular, consider:

legitimate expectation,
procedural fairness,
freedom of expression,
privacy concerns arising from the internal profiling,
proportionality,
and remedies.""",
        "expected_topic": "public_law_legitimate_expectation",
        "must_cover_terms": ["attorney-general of hong kong v ng yuen shiu", "r v north and east devon health authority, ex p coughlan"],
        "subquery_terms": [
            "promise quality, amenability, and expectation route",
            "consultation expectation, fairness, and reliance",
            "venue restriction, profiling, and rights overlap",
        ],
        "guide_terms": [
            "state clearly whether the stronger route is a procedural expectation to be consulted or a harder substantive claim to continuation of funding or access",
        ],
    },
    {
        "title": "Public-Law Privacy / Expression Boundary",
        "label": "Public Law / Privacy / Expression - Problem Question",
        "prompt": """Public Law / Privacy / Expression - Problem Question

A police force publishes on its website a "community transparency" report about a protest campaign. The report names one organiser, reproduces screenshots from her private social-media account, refers to her counselling history obtained from police notes, and links the material to criticism of the force's crowd-control tactics. The organiser says publication of the material intrudes on her private life and chills her speech. The force argues that the public had a right to know who was fuelling hostile online commentary.

Advise the organiser. In particular, consider:

Article 8 and Article 10,
reasonable expectation of privacy,
public-interest arguments,
misuse of private information or public-law privacy principles,
proportionality,
and remedies.""",
        "expected_topic": "public_law_privacy_expression",
        "must_cover_terms": ["article 8 echr", "article 10 echr", "campbell v mgn ltd"],
        "subquery_terms": [
            "reasonable expectation of privacy and the claimant's strongest point",
            "article 8, article 10, and public-interest resistance",
            "interim injunction and realistic relief",
        ],
    },
    {
        "title": "Competition Margin / Refusal Boundary",
        "label": "Competition Law - Problem Question",
        "prompt": """Competition Law - Problem Question

GateAxis plc controls the only nationwide app-store payment rail and developer analytics feed required for independent cloud-gaming providers to reach most mobile users. GateAxis also sells its own cloud-gaming subscription. Over six months it raises wholesale access fees for rivals, cuts the retail price of its own subscription, and withholds real-time performance data unless rivals buy a premium compliance package. GateAxis says the measures protect platform security and investment incentives.

Advise the rival providers. In particular, consider:

dominance,
margin squeeze,
refusal to supply access to data,
objective justification,
competitive effects,
and remedies.""",
        "expected_topic": "competition_margin_squeeze_refusal",
        "must_cover_terms": ["deutsche telekom", "teliasonera", "bronner"],
        "subquery_terms": [
            "market definition, dominance, and dependence on the platform rail",
            "margin squeeze between wholesale access fees and downstream pricing",
            "analytics data, constructive refusal, and indispensability",
        ],
    },
    {
        "title": "Competition Abuse Boundary",
        "label": "Competition Law - Problem Question",
        "prompt": """Competition Law - Problem Question

MealSquare plc operates the dominant restaurant-delivery marketplace in the UK and also runs its own chain of ghost kitchens. It increases commission charges for independent restaurants, gives its own kitchens preferential search placement, and tells restaurants that access to customer-order analytics will be reduced unless they use MealSquare's in-house logistics and sponsored-promotion tools. Restaurants say the strategy squeezes them commercially and disadvantages rivals; MealSquare says the package improves quality control and user trust.

Advise the restaurants. In particular, consider:

dominance,
self-preferencing and tying,
unfair trading terms,
the significance of access to platform data,
objective justification,
and possible abuse of dominance.""",
        "expected_topic": "competition_abuse_dominance",
        "must_cover_terms": ["section 18", "article 102 tfeu", "google shopping"],
        "subquery_terms": [
            "market definition, dominance, and platform power",
            "tying, foreclosure, and objective justification",
            "remedies and likely competition outcome",
        ],
        "guide_terms": [
            "separate market definition and dominance from the alleged tying or self-preferencing abuse",
        ],
    },
    {
        "title": "Employment Status / Equality Boundary",
        "label": "Employment Law - Problem Question",
        "prompt": """Employment Law - Problem Question

Noura provides translation and case-support services for CityBridge Support Ltd under a contract calling her an independent consultant. In practice she must perform the work personally, is rostered for fixed weekly shifts, uses the employer's systems, attends mandatory supervision meetings, and is penalised if she turns down assignments. After returning from maternity leave, she discovers that a male colleague doing equivalent work is paid more, her request to work compressed hours is rejected without reasons, and managers criticise her childcare commitments and headscarf.

Advise Noura. In particular, consider:

employment status,
worker and employee tests,
equal pay,
discrimination,
flexible working,
and remedies.""",
        "expected_topic": "employment_worker_status",
        "must_cover_terms": ["employment rights act 1996", "section 230", "autoclenz ltd v belcher"],
        "subquery_terms": [
            "status: employee, worker, or self-employed",
            "equal pay and discrimination routes",
            "flexible working, caring responsibilities, and remedies",
        ],
        "guide_terms": [
            "classify status first: employee, limb-b worker, or genuinely self-employed",
        ],
    },
    {
        "title": "Insurance Non-Disclosure Boundary",
        "label": "Insurance Law - Problem Question",
        "prompt": """Insurance Law - Problem Question

Harbour Estates seeks indemnity under a commercial property policy after a warehouse fire. During placement, its broker did not mention that the site had twice failed electrical inspections and that a previous insurer had threatened cancellation unless wiring defects were remedied. The insured says the proposal form did not ask specific follow-up questions and argues that the insurer is relying on generic complaints about non-disclosure and inadequate disclosure rather than identifying any material circumstance that induced the underwriter. The insurer says there was no fair presentation and threatens to avoid the policy entirely.

Advise the parties. In particular, consider:

the duty of fair presentation,
material circumstance,
reasonable search,
inducement,
statutory remedies under the Insurance Act 2015,
and the effect on the present claim.""",
        "expected_topic": "insurance_non_disclosure_misrepresentation",
        "must_cover_terms": ["insurance act 2015", "schedule 1", "pan atlantic insurance co ltd v pine top insurance co ltd"],
        "subquery_terms": [
            "fair presentation and material circumstance",
            "inducement and statutory remedies",
            "impact on the claim",
        ],
    },
]


for case in CASES:
    profile = _infer_retrieval_profile(case["prompt"])
    assert profile.get("topic") == case["expected_topic"], (case["title"], profile.get("topic"))
    assert _backend_request_requires_mandatory_rag(case["prompt"]), case["title"]

    must_cover_blob = " || ".join(profile.get("must_cover", [])).lower()
    for term in case.get("must_cover_terms", []):
        assert term in must_cover_blob, (case["title"], term, profile.get("must_cover", [])[:12])

    subquery_blob = " || ".join(
        item[0].lower() for item in _subissue_queries_for_unit(case["label"], case["prompt"])
    )
    for term in case.get("subquery_terms", []):
        assert term in subquery_blob, (case["title"], term, subquery_blob)

    guide_blob = _build_legal_answer_quality_gate(case["prompt"], profile).lower()
    for term in case.get("guide_terms", []):
        assert term in guide_blob, (case["title"], term)


print("Remaining boundary prompt regression passed.")
