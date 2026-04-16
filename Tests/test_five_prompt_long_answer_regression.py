"""
Regression checks for five longer complete-answer prompts.

These assertions verify:
1. mandatory RAG remains active for each legal complete-answer prompt;
2. each prompt routes to the intended topic profile;
3. the answer-quality gate contains the topic-specific guide; and
4. the subquery planner asks the right deeper questions for retrieval.
"""

from gemini_service import (
    _backend_request_requires_mandatory_rag,
    _build_legal_answer_quality_gate,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
)


CASES = [
    {
        "title": "Public Law",
        "label": "Public Law — Essay Question",
        "prompt": """Public Law — Essay Question

Critically evaluate whether the modern law of judicial review in England and Wales is best understood as a doctrine of parliamentary intention, a doctrine of the rule of law, or a pragmatic mixture of both.

In your answer, consider:

the constitutional foundations of judicial review,
illegality, irrationality, and procedural unfairness,
the significance of Anisminic and the control of legal error,
substantive and procedural legitimate expectation,
proportionality and the Human Rights Act 1998,
judicial restraint, deference, and institutional competence,
and whether the present law is coherent and constitutionally legitimate.""",
        "expected_topic": "public_law_judicial_review_deference",
        "guide_terms": [
            "legislative intention/ultra vires, common-law constitutional principle, or a mixed account",
            "control of jurisdictional and non-jurisdictional error",
            "institutional competence, democratic legitimacy, evidential advantage, and constitutional role",
        ],
        "subquery_terms": [
            "constitutional foundations",
            "grounds of review and control of legal error",
            "legitimate expectation, proportionality, and the human rights act",
            "deference, institutional competence, and constitutional legitimacy",
        ],
    },
    {
        "title": "Contract Law",
        "label": "Contract Law — Problem Question",
        "prompt": """Contract Law — Problem Question

Vertex Media Ltd organises a major international product launch. It contracts with Aurora Venue Group Ltd for the use of a conference space, technical support, and live-streaming facilities.

During negotiations, Aurora states that:

the venue is fully licensed for late-night events,
the in-house broadcasting system is “industry standard” and suitable for international streaming,
and the venue has an experienced technical team used to handling events of this scale.

Vertex makes clear that:

the event must run until midnight,
live streaming is essential because most attendees will join remotely,
and several investors will be attending with a view to negotiating future commercial partnerships.

A written contract is later signed. It contains:

an entire agreement clause,
a non-reliance clause,
a clause excluding liability for “all indirect or consequential loss, including loss of business opportunity,”
and a clause requiring all variations to be in writing.

Five days before the event, Vertex discovers that:

the venue’s late-night licence expired before the contract was made,
the streaming system has repeatedly failed in recent events,
and Aurora has outsourced technical support to a freelance contractor with no experience of events of this scale.

Vertex proceeds because no replacement venue is realistically available. On the day:

the event must stop at 9.30 pm,
the stream repeatedly fails,
remote attendees miss key presentations,
and one major investor withdraws from a planned funding arrangement, citing the poor event performance.

Vertex refuses to pay the full contract price and seeks advice.

Advise Vertex Media Ltd. In particular, consider:

whether the pre-contract statements are terms or representations,
whether there is actionable misrepresentation,
the effect of the entire agreement and non-reliance clauses,
breach of contract,
exclusion clauses and statutory controls,
remoteness and loss of commercial opportunity,
rescission, damages, and set-off,
and the likely practical outcome.""",
        "expected_topic": "contract_misrepresentation_exclusion",
        "guide_terms": [
            "venue, facilities, and service disputes should be analysed through express promises",
            "lost opportunities or similar commercial expectancy loss",
            "withholding the whole contract price or fee is riskier",
        ],
        "subquery_terms": [
            "statement classification: term, collateral warranty, or representation",
            "contractual breach: licensing, streaming capability, and technical support competence",
            "misrepresentation and clause control",
            "remedies: damages, rejection, rescission, and consequential loss",
        ],
    },
    {
        "title": "Tort Law",
        "label": "Tort Law — Essay Question",
        "prompt": """Tort Law — Essay Question

Critically evaluate whether the modern law of negligence draws coherent boundaries around liability for omissions, pure economic loss, and negligent misstatements.

In your answer, consider:

the general duty framework,
the distinction between acts and omissions,
assumption of responsibility,
the treatment of public authorities,
pure economic loss and policy concerns about indeterminate liability,
negligent misstatement,
the relationship between principle and policy in limiting negligence,
and whether the present law is best understood as coherent doctrine or controlled pragmatism.""",
        "expected_topic": "tort_duty_of_care_framework",
        "guide_terms": [
            "whether modern negligence has one duty framework or a series of controlled boundary doctrines",
            "keep omissions, public-authority liability, pure economic loss, and negligent misstatement distinct",
            "what caparo still does after robinson",
        ],
        "subquery_terms": [
            "the general framework: neighbour principle, caparo, and robinson",
            "omissions and public-authority limits",
            "pure economic loss and negligent misstatement",
            "principle, policy, and coherence",
        ],
    },
    {
        "title": "Land Law / Equity and Trusts",
        "label": "Land Law / Equity and Trusts — Problem Question",
        "prompt": """Land Law / Equity and Trusts — Problem Question

Mariam and Elias are an unmarried couple. They move into a registered property called Cedar House, purchased in Elias’s sole name because Mariam was then self-employed and had irregular income. Elias pays the deposit and takes out the mortgage in his sole name.

Before completion, Elias tells Mariam:
“This is our home. I know the paperwork is only in my name, but half of this place is really yours.”

Over the next six years:

Mariam pays £60,000 from an inheritance for a loft conversion and major structural repairs,
she regularly pays household bills and food costs,
she also makes several large bank transfers to Elias which she says were intended to help with the mortgage,
and she gives up full-time work for a period to care for Elias’s elderly mother, who also lives at the property.

Later, Elias starts a business and grants a legal charge over Cedar House to Mercantile Finance Ltd. The lender inspects the house, sees that Mariam is plainly living there, but makes no enquiry about her interest. Elias then defaults. Mercantile seeks possession and sale. Elias argues that Mariam has no beneficial interest because she made no direct contribution to the purchase price and the legal title is solely his.

Advise Mariam, Elias, and Mercantile Finance Ltd. In particular, consider:

common intention constructive trust,
proprietary estoppel,
the significance of express assurances,
direct and indirect contributions,
actual occupation and overriding interests,
the lender’s position,
quantification of any beneficial share,
and the remedies likely to be granted.""",
        "expected_topic": "land_home_coownership_estoppel_priority",
        "guide_terms": [
            "separate resulting trust, common-intention constructive trust, proprietary estoppel, priority, and remedies into distinct stages",
            "the real fight is usually constructive trust or estoppel",
            "rank practical remedies",
        ],
        "subquery_terms": [
            "beneficial interest: resulting trust weakness and common-intention constructive trust",
            "proprietary estoppel and assurance-based equity",
            "priority, actual occupation, and binding effect on third parties",
            "quantification and practical remedies",
        ],
    },
    {
        "title": "Criminal Law",
        "label": "Criminal Law — Essay Question",
        "prompt": """Criminal Law — Essay Question

Critically evaluate whether the modern law of criminal liability in England and Wales takes a coherent approach to participation in crime through complicity, joint enterprise, and inchoate liability.

In your answer, consider:

the basis of accessory liability,
the significance of intention and foresight after Jogee,
withdrawal from participation,
the relationship between principal and accessory responsibility,
attempts and the “more than merely preparatory” test,
conspiracy and the logic of anticipatory criminalisation,
the relationship between moral blameworthiness and preventive justice,
and whether the current law is principled, fair, and sufficiently clear.""",
        "expected_topic": "criminal_participation_inchoate_liability",
        "guide_terms": [
            "separate complicity after jogee from inchoate liability for attempt and conspiracy",
            "compare intention, foresight as evidence, conditional intent, withdrawal, and principal or accessory responsibility",
            "whether accessory doctrine and anticipatory offences reflect different and only loosely reconciled aims",
        ],
        "subquery_terms": [
            "complicity, joint enterprise, and the post-jogee mental element",
            "withdrawal, escalation, and limits of secondary participation",
            "attempt, conspiracy, and anticipatory criminalisation",
            "coherence, fairness, and overall criminal participation",
        ],
    },
]


for case in CASES:
    profile = _infer_retrieval_profile(case["prompt"])
    assert profile["topic"] == case["expected_topic"], case["title"]
    assert _backend_request_requires_mandatory_rag(case["prompt"], profile), case["title"]

    gate = _build_legal_answer_quality_gate(case["prompt"], profile).lower()
    for term in case["guide_terms"]:
        assert term in gate, f"{case['title']} missing guide term: {term}"

    subqueries = [title.lower() for title, _ in _subissue_queries_for_unit(case["label"], case["prompt"])]
    for term in case["subquery_terms"]:
        assert any(term in title for title in subqueries), f"{case['title']} missing subquery term: {term}"


print("Five-prompt long-answer regression passed.")
