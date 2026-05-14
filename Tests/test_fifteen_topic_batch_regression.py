"""
Regression checks for the 15-topic mixed complete-answer batch.

These assertions verify:
1. mandatory RAG remains active for these legal complete-answer prompts;
2. each topic routes to the intended retrieval profile;
3. the must-cover authority pack contains core subject anchors; and
4. the subquery planner stays subject-specific instead of collapsing into generic analysis.
"""

from model_applicable_service import (
    _backend_request_requires_mandatory_rag,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
)


CASES = [
    {
        "title": "Private International Law",
        "label": "Private International Law — Problem Question",
        "prompt": """Private International Law — Problem Question

Harbour Design Ltd, an English company, contracts with Solaris SA, a French manufacturer, for specialist facade panels for a hotel project in London. The written supply agreement states that:

* "the courts of Paris shall have exclusive jurisdiction"; and
* "this contract shall be governed by French law."

During negotiations, Solaris's German engineering consultant sends technical assurances directly to Harbour Design in London, stating that the panels are suitable for the project and comply with UK fire standards.

After installation, serious defects emerge. Harbour Design suffers major losses in England and sues:

* Solaris SA in England for breach of contract and misrepresentation; and
* the German consultant in England for negligent misstatement.

At the same time:

* Solaris has already begun proceedings in Paris seeking a declaration of non-liability;
* Harbour Design later obtains an English judgment against the consultant and wants to enforce it against assets in Spain;
* Solaris argues that any English proceedings should be stayed and that the Paris judgment, once obtained, should be recognised.

Advise the parties. In particular, consider:

* jurisdiction over the contractual and tort claims,
* the effect of the exclusive jurisdiction clause,
* concurrent proceedings,
* choice of law for contract, tort, and misrepresentation issues,
* and the recognition and enforcement problems that may arise.""",
        "expected_topic": "private_international_law_post_brexit",
        "must_cover_terms": ["rome i regulation", "rome ii regulation", "hague choice of court agreements convention 2005"],
        "subquery_terms": [
            "jurisdiction over solaris and the consultant",
            "exclusive jurisdiction clause, concurrent paris proceedings, and any stay",
            "choice of law for contract, tort, and misrepresentation",
            "recognition and enforcement: paris judgment and english judgment in spain",
        ],
    },
    {
        "title": "Competition Law",
        "label": "Competition Law — Problem Question",
        "prompt": """Competition Law — Problem Question

TeleSphere plc controls the only nationwide wholesale fibre network in the UK and also operates a large retail broadband business. Rival providers must buy wholesale access from TeleSphere in order to compete in downstream retail broadband supply.

Over time:

* TeleSphere raises wholesale access prices substantially,
* simultaneously cuts its own retail prices in major cities,
* refuses to provide certain technical interoperability information to smaller rivals,
* and tells one competitor, NexLink Ltd, that access to a new premium business-service product will not be granted because TeleSphere wants to "protect network integrity and investment incentives."

NexLink complains that TeleSphere is:

* abusing a dominant position,
* engaging in a margin squeeze,
* unlawfully refusing to supply an essential input,
* and using vague objective-justification arguments to shield exclusionary conduct.

Advise NexLink Ltd. In particular, consider:

* dominance,
* abuse of dominance,
* margin squeeze,
* refusal to supply,
* the role of economic effects and foreclosure,
* possible objective justifications,
* and the remedies or enforcement routes likely to be available.""",
        "expected_topic": "competition_margin_squeeze_refusal",
        "must_cover_terms": ["article 102 tfeu", "deutsche telekom", "bronner"],
        "subquery_terms": [
            "market definition, dominance, and downstream dependence",
            "margin squeeze and foreclosure in wholesale / retail pricing",
            "refusal to supply, interoperability information, and indispensability",
            "objective justification, enforcement routes, and remedies",
        ],
    },
    {
        "title": "International Commercial Mediation / Arbitration",
        "label": "International Commercial Mediation / Arbitration — Problem Question",
        "prompt": """International Commercial Mediation / Arbitration — Problem Question

Vertex Commodities Ltd (England) and Meridian Trading LLC (UAE) enter into a long-term commodities contract containing a London-seated arbitration clause. A dispute arises over defective shipments. Before arbitration begins, the parties attend a mediation in Singapore and sign a written settlement agreement under which Meridian agrees to pay instalments and provide replacement shipments.

Meridian then defaults. Vertex wants to enforce the settlement. Meridian argues that:

* the mediation was non-binding in nature,
* the settlement should not be enforced because it was reached under commercial pressure,
* and in any event certain statements made during the mediation are confidential and cannot be used in later proceedings.

Vertex responds by:

* commencing arbitration in London,
* relying on the mediated settlement,
* and alternatively seeking to have the settlement recognised abroad where Meridian has assets.

Advise the parties. In particular, consider:

* the legal nature of mediation and mediated settlements,
* confidentiality and without-prejudice protection,
* enforcement of international mediated settlements,
* the significance of the Singapore Convention,
* comparison with the New York Convention and arbitral awards,
* the relevance of UNCITRAL instruments,
* and the practical differences between non-binding mediation and binding arbitration.""",
        "expected_topic": "international_commercial_arbitration",
        "must_cover_terms": ["arbitration act 1996", "new york convention", "uncitral model law"],
        "subquery_terms": [
            "mediation, confidentiality, and without-prejudice limits",
            "legal status and enforceability of the mediated settlement",
            "singapore convention, uncitral instruments, and comparison with arbitral awards",
            "arbitration fallback, enforcement strategy, and practical outcome",
        ],
    },
    {
        "title": "Data Protection / AI Regulation",
        "label": "Data Protection / AI Regulation — Problem Question",
        "prompt": """Data Protection / AI Regulation — Problem Question

CarePath Ltd provides an AI-driven triage platform to NHS bodies and also operates a consumer health app. The system:

* collects health data, behavioural data, and location data,
* uses a third-party model developer to refine risk-scoring tools,
* automatically categorises some users as "low priority" for urgent clinical review,
* and generates refusal messages with only short standard explanations.

Several users later discover that:

* some urgent cases were wrongly downgraded,
* data was shared across CarePath, the NHS body, and the external model developer without clear transparency,
* one user's complaint was rejected automatically without meaningful human review,
* and internal documents show that engineers were aware of bias problems affecting disabled users.

Affected individuals seek advice. The ICO also begins investigating.

Advise the parties. In particular, consider:

* controller and processor status,
* lawful basis and special category data,
* transparency and explainability,
* automated decision-making,
* human review,
* accuracy and fairness obligations,
* damages claims by individuals,
* regulatory enforcement,
* and the relationship between data protection, administrative fairness, and rights-based analysis.""",
        "expected_topic": "data_protection",
        "must_cover_terms": ["uk gdpr", "article 22", "data protection act 2018"],
        "subquery_terms": [
            "controllers, processors, and the data-sharing chain",
            "health data, lawful basis, special-category conditions, and transparency",
            "automated triage, article 22, explainability, and meaningful human review",
            "bias, accuracy, individual remedies, and ico enforcement",
        ],
    },
    {
        "title": "Defamation / Privacy / Media Law",
        "label": "Defamation / Privacy / Media Law — Problem Question",
        "prompt": """Defamation / Privacy / Media Law — Problem Question

A national newspaper publishes an online article about Elias, a well-known entrepreneur, and his company NovaCore Ltd. The article alleges that:

* Elias manipulated public contracts through political connections,
* NovaCore's internal culture involved intimidation and harassment,
* and Elias secretly received treatment for addiction while presenting himself as a "model of discipline and resilience."

The article is based on:

* leaked emails,
* anonymous sources,
* and photographs taken outside a private medical clinic.

After publication:

* NovaCore loses a major commercial opportunity,
* Elias says the allegations are false and that the clinic information is deeply private,
* the newspaper argues truth, honest opinion, and public interest,
* and it says the clinic information is relevant because Elias built a public brand around wellness and self-control.

Advise Elias and NovaCore Ltd. In particular, consider:

* serious harm,
* defamation routes for the individual and the company,
* truth,
* honest opinion,
* public interest,
* misuse of private information,
* Articles 8 and 10,
* and how the claims should be prioritised.""",
        "expected_topic": "defamation_media_privacy",
        "must_cover_terms": ["defamation act 2013", "lachaux", "chase v news group newspapers"],
        "subquery_terms": [
            "meaning, reference, and serious harm / serious financial loss",
            "truth, honest opinion, and public-interest defences",
            "clinic information, misuse of private information, and articles 8 and 10",
            "claim prioritisation, remedies, and practical litigation strategy",
        ],
    },
    {
        "title": "Immigration / Asylum / Deportation",
        "label": "Immigration / Asylum / Deportation — Problem Question",
        "prompt": """Immigration / Asylum / Deportation — Problem Question

Samir entered the UK lawfully as a student and has lived in the UK for 12 years. He later formed a relationship with a British citizen and they have a 7-year-old child. He is convicted of a drug-related offence and sentenced to 20 months' imprisonment. The Home Secretary decides to deport him.

Before removal, Samir:

* makes a fresh protection claim based on political activity in his home state,
* says conditions there have changed and he now faces a real risk of persecution,
* argues deportation would breach his Article 8 rights,
* and challenges the timing and lawfulness of his detention pending removal.

He also says the Home Office failed to consider key documents about his child's needs and gave inadequate reasons for rejecting parts of his representations.

Advise Samir. In particular, consider:

* deportation and the public interest,
* Article 8 proportionality,
* asylum and protection issues,
* procedural fairness,
* detention pending removal,
* timing and practical feasibility of removal,
* and the likely strengths and weaknesses of his claims.""",
        "expected_topic": "immigration_asylum_deportation",
        "must_cover_terms": ["article 8 echr", "kiarie and byndloss", "doody"],
        "subquery_terms": [
            "deportation framework, criminality, and the public interest",
            "fresh protection claim, persecution risk, and non-refoulement",
            "article 8, the child",
            "detention pending removal, procedural fairness, and likely outcome",
        ],
    },
    {
        "title": "Family Law",
        "label": "Family Law — Problem Question",
        "prompt": """Family Law — Problem Question

Nadia and Thomas are separated parents of an 8-year-old child, Lila. Lila lives primarily with Nadia. Thomas seeks a shared care arrangement. Nadia opposes this and applies for permission to relocate permanently to Canada with Lila, saying:

* she has a firm job offer there,
* her extended family can support her,
* and the move would improve stability for both her and Lila.

Thomas argues that:

* the move would seriously damage his relationship with Lila,
* Nadia has frequently undermined contact,
* and allegations she makes about his controlling behaviour are exaggerated or false.

Nadia alleges:

* coercive and controlling behaviour during the relationship,
* several incidents of threatening behaviour after separation,
* and that direct co-parenting has become unsafe.

Advise the parties. In particular, consider:

* the welfare principle,
* fact-finding where domestic abuse is alleged,
* relocation,
* child arrangements,
* the significance of welfare factors and parental involvement,
* and the likely approach of the court.""",
        "expected_topic": "family_private_children_arrangements",
        "must_cover_terms": ["children act 1989", "section 1", "section 1(2a)"],
        "subquery_terms": [
            "fact-finding, domestic abuse allegations, and the welfare lens",
            "relocation to canada and the welfare checklist",
            "shared care, parental involvement",
            "likely order, safeguards, and practical family-court outcome",
        ],
    },
    {
        "title": "Child Abduction / Hague 1980",
        "label": "Child Abduction / Hague 1980 — Problem Question",
        "prompt": """Child Abduction / Hague 1980 — Problem Question

Marta and Daniel lived in Spain with their 6-year-old son, Leo. Marta then brought Leo to England without Daniel's consent and now refuses to return. Daniel promptly applies under the Hague Convention 1980 for Leo's summary return.

Marta argues that:

* Spain was no longer Leo's habitual residence because the family had already been planning to move,
* Daniel did not truly exercise rights of custody,
* returning Leo would expose him to a grave risk of harm because of Daniel's abusive behaviour,
* and in any event Leo is now settled in England because over a year has passed before the final hearing.

Leo, now 7, also says he does not want to go back.

Advise the parties. In particular, consider:

* habitual residence,
* rights of custody,
* wrongful removal or retention,
* grave risk,
* settlement,
* child objections,
* undertakings,
* and the likely approach of the court.""",
        "expected_topic": "family_child_abduction_hague1980",
        "must_cover_terms": ["hague convention 1980", "article 12", "article 13"],
        "subquery_terms": [
            "habitual residence, rights of custody, and wrongful removal",
            "article 13(b) grave risk and protective measures",
            "settlement, child objections, and the passage of time",
            "undertakings, discretion, and likely return outcome",
        ],
    },
    {
        "title": "Construction Law",
        "label": "Construction Law — Problem Question",
        "prompt": """Construction Law — Problem Question

Atlas Developments Ltd engages Stonebridge Contractors Ltd to construct a commercial office building under a standard-form building contract. The contract includes:

* a completion date,
* liquidated damages for delay,
* an extension of time mechanism,
* employer instruction clauses,
* and a right to adjudicate disputes.

During the project:

* Atlas issues major design changes late,
* key site access is delayed by problems on Atlas's side,
* Stonebridge encounters weather problems and labour shortages,
* completion is delayed,
* Atlas deducts liquidated damages,
* and after practical completion serious defects are discovered in waterproofing and mechanical systems.

Stonebridge says:

* Atlas's acts caused critical delay and triggered the prevention principle,
* it is entitled to extensions of time,
* and the defects are partly design-related and not its responsibility.

Atlas starts adjudication. Stonebridge resists enforcement of the adjudicator's decision.

Advise the parties. In particular, consider:

* extension of time,
* liquidated damages,
* the prevention principle,
* defects liability,
* adjudication and enforcement,
* and the practical strengths and weaknesses of each party's position.""",
        "expected_topic": "construction_delay_defects",
        "must_cover_terms": ["housing grants, construction and regeneration act 1996", "extension of time", "liquidated damages"],
        "subquery_terms": [
            "delay, time machinery, and extension of time",
            "defects, quality obligations, and breach",
            "remedies, adjudication, and practical outcome",
        ],
    },
    {
        "title": "Consumer Credit / Unfair Relationship",
        "label": "Consumer Credit / Unfair Relationship — Problem Question",
        "prompt": """Consumer Credit / Unfair Relationship — Problem Question

Mrs Patel enters into a credit agreement to finance the installation of a solar panel and home battery system. A salesperson visits her at home, pressures her into signing immediately, and assures her that:

* the system will eliminate most of her electricity bills,
* the finance is "government-backed and low risk,"
* and the lender has approved only "fully vetted" installers.

The agreement is later found to contain irregularities in execution. The installer performs defective work, and the promised savings never materialise. Mrs Patel stops repayments. The lender threatens enforcement and says any complaint is really against the supplier, not the finance company.

Advise Mrs Patel. In particular, consider:

* execution defects,
* enforceability,
* unfair relationship under section 140A,
* linked lender liability,
* supplier misconduct,
* and the remedies that may be available.""",
        "expected_topic": "consumer_credit_unfair_relationship",
        "must_cover_terms": ["consumer credit act 1974", "section 75", "section 140a"],
        "subquery_terms": [
            "execution defects and enforceability of the credit agreement",
            "pressure selling, supplier misconduct, and section 140a unfair relationship",
            "linked lender liability for defective installation and false assurances",
            "enforcement resistance, remedies, and practical outcome",
        ],
    },
    {
        "title": "Tax Law",
        "label": "Tax Law — Essay Question",
        "prompt": """Tax Law — Essay Question

Critically evaluate whether modern UK tax law draws a coherent and workable distinction between legitimate tax planning, abusive tax avoidance, and unlawful evasion.

In your answer, consider:

* purposive statutory construction,
* the significance of the Ramsay line of authority,
* the role and limits of the GAAR,
* commercial substance,
* certainty versus anti-abuse control,
* and whether the present framework is principled or excessively dependent on judicial characterisation.""",
        "expected_topic": "tax_avoidance_gaar",
        "must_cover_terms": ["duke of westminster", "w t ramsay", "general anti-abuse rule"],
        "subquery_terms": [
            "westminster doctrine and the era of form",
            "ramsay principle and purposive construction",
            "gaar and modern anti-avoidance",
            "certainty, form vs substance, and critical evaluation",
        ],
    },
    {
        "title": "Company Personality / Parent Liability",
        "label": "Company Personality / Parent Liability — Essay Question",
        "prompt": """Company Personality / Parent Liability — Essay Question

Critically evaluate whether English law now takes a coherent approach to company personality, veil piercing, and parent-company liability.

In your answer, consider:

* the continuing significance of Salomon,
* the limits of veil piercing after Prest,
* the distinction between piercing the veil and imposing direct liability on a parent,
* the relevance of Chandler, Vedanta, and Okpabi,
* and whether the current law keeps separate doctrines separate or risks conceptual confusion.""",
        "expected_topic": "company_personality_veil_lifting",
        "must_cover_terms": ["salomon", "prest", "vedanta"],
        "subquery_terms": [
            "separate legal personality and the salomon baseline",
            "prest, facade, and true veil piercing",
            "alternative routes and critical evaluation",
        ],
    },
    {
        "title": "Public International Law",
        "label": "Public International Law — Problem Question",
        "prompt": """Public International Law — Problem Question

State A supports an armed group operating in State B. The group carries out repeated attacks on infrastructure in State B, including a cyber operation that shuts down hospital systems. State B responds with limited cross-border strikes against camps used by the group inside State A's territory, claiming self-defence.

At the same time:

* victims in England sue State A and a state-owned logistics company linked to the armed group,
* State A argues sovereign immunity,
* State B says the armed group's conduct is attributable to State A,
* and several states dispute whether the cyber operation amounted to a use of force or armed attack.

Advise the parties. In particular, consider:

* attribution,
* state responsibility,
* countermeasures,
* use of force and self-defence,
* sovereign immunity,
* the position of state-owned entities,
* and the structure of the legal analysis required.""",
        "expected_topic": "public_international_law_use_of_force",
        "must_cover_terms": ["article 2(4)", "article 51", "nicaragua"],
        "subquery_terms": [
            "attribution of the armed group and the structure of state responsibility",
            "use of force, armed attack, and self-defence by state b",
            "countermeasures, cyber operations, and evidential uncertainty",
            "sovereign immunity, state-owned entities, and the english proceedings",
        ],
    },
    {
        "title": "Evidence Law",
        "label": "Evidence Law — Essay Question",
        "prompt": """Evidence Law — Essay Question

Critically evaluate whether the modern law of criminal evidence strikes an acceptable balance between truth-finding and fairness to the accused.

In your answer, consider:

* hearsay,
* bad character,
* confession evidence,
* exclusionary discretions,
* the significance of Article 6,
* and whether the present law is best understood as coherent principle or a patchwork of compromises.""",
        "expected_topic": "evidence_admissibility_fair_trial",
        "must_cover_terms": ["section 76", "section 78", "criminal justice act 2003"],
        "subquery_terms": [
            "truth-finding and admissibility framework",
            "confessions, hearsay, and exclusionary discretion",
            "overall balance and critique",
        ],
    },
    {
        "title": "Employment Status",
        "label": "Employment Status — Problem Question",
        "prompt": """Employment Status — Problem Question

MoveFast Ltd operates a logistics platform. It treats all individuals delivering parcels through the platform as independent contractors. Three individuals seek advice:

* Ava, who works five days a week, must wear MoveFast branding, is allocated routes by an app, and in practice is expected to accept most jobs, though her contract says she is free to decline work.
* Ben, who can send substitutes from an approved list but only with prior app approval and almost never does so in practice.
* Cara, who invoices through her own company, works mainly for MoveFast, attends mandatory team meetings, and is subject to detailed performance targets and disciplinary procedures.

Each wants to know whether they are an employee, a worker, or genuinely self-employed.

Advise the parties. In particular, consider:

* personal service,
* control,
* substitution,
* integration,
* mutuality and economic reality,
* contractual labels versus practical reality,
* and why different individuals on one platform may fall into different legal categories.""",
        "expected_topic": "employment_worker_status",
        "must_cover_terms": ["ready mixed concrete", "autoclenz", "pimlico"],
        "subquery_terms": [
            "ava: personal service, control, and worker or employee status",
            "ben: substitution, app approval, and whether personal service remains dominant",
            "cara: service-company form, integration, and contractual reality",
            "why platform workers may fall into different status categories",
        ],
    },
]


for case in CASES:
    profile = _infer_retrieval_profile(case["prompt"])
    assert profile["topic"] == case["expected_topic"], case["title"]
    assert _backend_request_requires_mandatory_rag(case["prompt"], {"active": False}), case["title"]

    for term in case.get("must_cover_terms", []):
        assert any(term in item.lower() for item in profile.get("must_cover", [])), (
            f"{case['title']} missing must-cover term: {term}"
        )

    subqueries = [title.lower() for title, _ in _subissue_queries_for_unit(case["label"], case["prompt"])]
    for term in case["subquery_terms"]:
        assert any(term in title for title in subqueries), f"{case['title']} missing subquery term: {term}"


print("Fifteen-topic mixed regression passed.")
