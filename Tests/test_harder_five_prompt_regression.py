"""
Regression checks for five harder 2000-2500 word complete-answer prompts.

These assertions verify:
1. mandatory RAG remains active;
2. each harder prompt still routes to the intended topic profile;
3. the answer-quality gate includes the sharper guide points added for these variants; and
4. the subquery planner keeps the harder issue structure explicit.
"""

from gemini_service import (
    _backend_request_requires_mandatory_rag,
    _build_legal_answer_quality_gate,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
)


CASES = [
    {
        "title": "Public Law Problem",
        "label": "Public Law — Problem Question",
        "prompt": """Public Law — Problem Question

The Secretary of State for Communities issues a published document titled National Civic Stability Guidance 2027. It states that local authorities should “ordinarily refuse” permission for public demonstrations that are likely to generate “serious social unease, reputational damage to local institutions, or intense public controversy.” The Guidance was not laid before Parliament and was issued without consultation.

Relying on the Guidance, Eastborough Council refuses permission for a peaceful protest organised by Parents for Accountable Housing, a group campaigning against local redevelopment plans. The refusal letter says only that the event would be “inconsistent with national guidance and unsuitable in the current community climate.” No further reasons are given.

It later emerges that:

the Council treated the Guidance as binding,
no independent consideration was given to the group’s specific proposal,
and earlier council publicity had stated that “peaceful civic engagement will continue to be welcomed in Eastborough.”

The organisers seek legal advice.

Advise the organisers. In particular, consider:

whether the Guidance is legally binding, advisory, or unlawful,
the distinction between policy and rule,
fettering of discretion,
procedural fairness and adequacy of reasons,
legitimate expectation,
Articles 10 and 11 ECHR,
proportionality and traditional judicial review grounds,
and the remedies a court is most likely to grant.""",
        "expected_topic": "public_law_fettering_expression_assembly",
        "must_cover_terms": ["doody", "coughlan"],
        "guide_terms": [
            "distinguish lawful policy guidance from an unlawful rule or direction",
            "policy language can still be lawful",
            "treat adequacy of reasons and any prior public assurances as separate analytical moves",
            "convention rights are engaged",
        ],
        "subquery_terms": [
            "legality of the guidance and effect of the ouster clause",
            "policy versus rule, fettering, and opaque decision-support",
            "procedural fairness, reasons, legitimate expectation, and convention rights",
            "remedies and likely challenge outcome",
        ],
    },
    {
        "title": "Contract Problem",
        "label": "Contract Law — Problem Question",
        "prompt": """Contract Law — Problem Question

Helix Events Ltd contracts with Sterling Venue Group Ltd for a high-profile technology summit. During negotiations, Sterling states that:

the venue has a valid licence for events until midnight,
the in-house audiovisual system is “fully integrated and suitable for international hybrid broadcasting,”
and the venue’s technical team has “extensive experience” with conferences of this scale.

Helix explains that:

remote participation is essential,
keynote sessions must continue until 11.45 pm,
and several investors will be attending with a view to future commercial collaborations.

A written contract is later signed. It contains:

an entire agreement clause,
a non-reliance clause,
an exclusion clause for “all indirect or consequential loss, including loss of profit, goodwill, and business opportunity,”
and a clause stating that no variation is effective unless in writing and signed by both parties.

Three days before the summit, Helix discovers that:

the late-night licence had expired before the contract was made,
the audiovisual system had failed at several recent events,
and technical support has been outsourced to a freelance contractor with no experience of conferences of this kind.

Helix proceeds because no substitute venue is available. On the day:

the event is forced to end at 9.30 pm,
the livestream fails repeatedly,
several overseas attendees miss core presentations,
and a major investor withdraws from ongoing funding discussions, saying the summit exposed serious organisational weakness.

Sterling sues for the unpaid balance of the price. Helix counterclaims.

Advise the parties. In particular, consider:

whether the pre-contract statements are terms, representations, or both,
whether there is actionable misrepresentation,
the effect of the entire agreement and non-reliance clauses,
exclusion clauses and statutory controls,
affirmation and rescission,
contract damages and misrepresentation damages,
remoteness, causation, and proof of investor-related loss,
set-off,
and the likely practical outcome.""",
        "expected_topic": "contract_misrepresentation_exclusion",
        "guide_terms": [
            "where a pre-contract statement is specific, central to the deal, and made by the party with obvious expertise",
            "if a clause combines a standard indirect/consequential-loss formula with extra wording about lost opportunities",
            "for alleged lost commercial opportunities, separate remoteness from causation/proof",
            "rank damages and set-off against any total refusal to pay",
        ],
        "subquery_terms": [
            "statement classification: term, collateral warranty, or representation",
            "contractual breach: licensing, streaming capability, and technical support competence",
            "misrepresentation and clause control",
            "remedies: damages, rejection, rescission, and consequential loss",
        ],
    },
    {
        "title": "Tort Essay",
        "label": "Tort Law — Essay Question",
        "prompt": """Tort Law — Essay Question

Critically evaluate whether the modern law of negligence draws coherent boundaries around liability for omissions, failures to protect others from third parties, and pure economic loss.

In your answer, consider:

the distinction between acts and omissions,
assumption of responsibility,
control and creation of danger,
liability of public authorities,
negligent misstatement,
the exclusionary treatment of pure economic loss,
the relationship between principle and policy,
and whether the present law reflects a coherent moral theory of responsibility or a series of liability-control devices.""",
        "expected_topic": "tort_duty_of_care_framework",
        "must_cover_terms": ["dorset yacht", "smith v littlewoods"],
        "guide_terms": [
            "treat failures to protect against third parties as a real stress test for omission theory",
            "keep omissions, public-authority liability, pure economic loss, and negligent misstatement distinct",
        ],
        "subquery_terms": [
            "the general framework: neighbour principle, caparo, and robinson",
            "omissions and public-authority limits",
            "pure economic loss and negligent misstatement",
            "principle, policy, and coherence",
        ],
    },
    {
        "title": "Land / Equity Problem",
        "label": "Land Law / Equity and Trusts — Problem Question",
        "prompt": """Land Law / Equity and Trusts — Problem Question

Nadia and Lewis are an unmarried couple. They move into Willow House, a registered property bought in Lewis’s sole name because Nadia had recently left salaried employment to start a business. Lewis pays the deposit and takes out the mortgage in his sole name.

Before completion, Lewis tells Nadia:
“This is our family home. I know the title is only in my name, but half of it is yours.”

Over the next seven years:

Nadia spends £75,000 from an inheritance on structural repairs, an extension, and specialist adaptations for Lewis’s disabled father, who lives with them,
she pays most of the household bills and several large lump sums to Lewis, which she says were to help meet mortgage obligations,
she reduces her working hours to care for Lewis’s father and their child,
and the couple consistently refer to Willow House in messages and emails as “our house.”

Later, without telling Nadia, Lewis grants a legal charge over Willow House to Crest Capital Ltd to secure a business loan. A representative of Crest visits the property, sees clear signs that Nadia and Lewis’s father both live there, but makes no enquiry about their rights. Lewis defaults. Crest seeks possession and sale.

Lewis argues that Nadia has no beneficial interest because:

legal title is solely his,
she made no direct contribution to the purchase price,
and domestic expenditure is legally irrelevant.

Advise Nadia, Lewis, and Crest Capital Ltd. In particular, consider:

common intention constructive trust,
proprietary estoppel,
the significance of express assurances,
direct and indirect financial contributions,
domestic and caring contributions,
actual occupation and overriding interests,
the lender’s position,
quantification of any beneficial share,
and the remedies likely to be available.""",
        "expected_topic": "land_home_coownership_estoppel_priority",
        "guide_terms": [
            "do not dismiss domestic spending or caring sacrifice in one sentence",
            "compare constructive trust and estoppel directly",
        ],
        "subquery_terms": [
            "beneficial interest: resulting trust weakness and common-intention constructive trust",
            "proprietary estoppel and assurance-based equity",
            "priority, actual occupation, and binding effect on third parties",
            "quantification and practical remedies",
        ],
    },
    {
        "title": "Criminal Essay",
        "label": "Criminal Law — Essay Question",
        "prompt": """Criminal Law — Essay Question

Critically evaluate whether the modern law of participation in crime in England and Wales takes a coherent and morally defensible approach to complicity, attempts, and conspiracy.

In your answer, consider:

the basis of accessory liability,
intention, foresight, and the significance of Jogee,
conditional intent and withdrawal,
the relationship between principal and accessory liability,
attempts and the “more than merely preparatory” test,
conspiracy and the logic of anticipatory criminalisation,
preventive justice and moral blameworthiness,
and whether the present law is principled, fair, and sufficiently clear.""",
        "expected_topic": "criminal_participation_inchoate_liability",
        "guide_terms": [
            "compare intention, foresight as evidence, conditional intent, withdrawal, and principal or accessory responsibility",
            "finish with a clear verdict on whether the law is principled and fair overall",
        ],
        "subquery_terms": [
            "complicity, joint enterprise, and the post-jogee mental element",
            "conditional intent, withdrawal, escalation, and limits of secondary participation",
            "attempt, conspiracy, and anticipatory criminalisation",
            "coherence, fairness, and overall criminal participation",
        ],
    },
]


for case in CASES:
    profile = _infer_retrieval_profile(case["prompt"])
    assert profile["topic"] == case["expected_topic"], case["title"]
    assert _backend_request_requires_mandatory_rag(case["prompt"], {"active": False}), case["title"]

    for term in case.get("must_cover_terms", []):
        assert any(term in item.lower() for item in profile.get("must_cover", [])), f"{case['title']} missing must-cover term: {term}"

    gate = _build_legal_answer_quality_gate(case["prompt"], profile).lower()
    for term in case["guide_terms"]:
        assert term in gate, f"{case['title']} missing guide term: {term}"

    subqueries = [title.lower() for title, _ in _subissue_queries_for_unit(case["label"], case["prompt"])]
    for term in case["subquery_terms"]:
        assert any(term in title for title in subqueries), f"{case['title']} missing subquery term: {term}"


print("Harder five-prompt regression passed.")
