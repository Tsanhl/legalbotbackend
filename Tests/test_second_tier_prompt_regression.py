"""
Regression checks for the second-tier mixed prompt batch.

These assertions verify:
1. each prompt routes to the intended primary topic;
2. mandatory RAG stays on for the whole batch;
3. representative must-cover anchors survive; and
4. mixed prompts keep prompt-shaped subqueries and guide text.
"""

from model_applicable_service import (
    _backend_request_requires_mandatory_rag,
    _build_legal_answer_quality_gate,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
)


CASES = [
    {
        "title": "Aviation + Clinical Negligence",
        "label": "Aviation + Clinical Negligence - Problem Question",
        "prompt": """Aviation + Clinical Negligence - Problem Question

On an international flight from London to Toronto, Olivia is injured when severe turbulence causes an overhead storage unit to open and heavy luggage falls onto her head and shoulder. After an emergency landing in Dublin, she is taken to hospital where doctors fail to diagnose an internal vascular injury for several hours. She later suffers permanent weakness in her dominant arm. Medical experts say earlier treatment would not certainly have prevented the outcome, but it would have given her a significantly better chance of avoiding permanent disability.

Advise Olivia. In particular, consider:

airline liability under the Montreal Convention,
what counts as an "accident,"
recoverable heads of loss,
clinical negligence against the hospital team,
causation and loss of chance,
and how the two routes of liability may interact.""",
        "expected_topic": "clinical_negligence_causation_loss_of_chance",
        "must_cover_terms": ["montreal convention 1999", "article 17", "gregg v scott"],
        "subquery_terms": [
            "montreal convention route, article 17 accident, and airline exposure",
            "hospital negligence, delayed diagnosis, and causation",
            "loss of chance, recoverable loss, and interaction between the two claims",
        ],
        "guide_terms": [
            "separate the montreal convention route against the airline from the later hospital-negligence route after the emergency landing",
            "do not let the convention exclusivity point swallow the separate post-flight negligence claim against the hospital team",
        ],
    },
    {
        "title": "Consumer Goods / Digital Content / Unfair Terms",
        "label": "Consumer Goods / Digital Content / Unfair Terms - Problem Question",
        "prompt": """Consumer Goods / Digital Content / Unfair Terms - Problem Question

Ravi buys a premium smart-home package online from HomeSphere Ltd. The package includes:

a physical hub and two cameras,
a subscription-based AI monitoring service,
and app-controlled software updates.

The website describes the system as "fully secure," "compatible with all major home networks," and "ideal for continuous family protection." The standard terms include:

a clause allowing HomeSphere to change key software features at any time,
a term excluding liability for "all service interruption, data loss, and consequential loss,"
and a term stating that any complaint must be brought within 14 days of delivery.

After two months:

the cameras repeatedly disconnect,
a software update removes a key night-monitoring feature,
and a security flaw allows a third party to access Ravi's household footage.

HomeSphere argues that the hardware worked when delivered, the software service is separate, and the contract terms allow changes.

Advise Ravi. In particular, consider:

rights relating to goods and digital content,
implied standards of quality, fitness, and conformity,
unfair terms under the Consumer Rights Act 2015,
remedies,
and whether HomeSphere can rely on its standard terms.""",
        "expected_topic": "consumer_digital_content",
        "must_cover_terms": ["consumer rights act 2015", "section 9", "section 62"],
        "subquery_terms": [
            "goods, digital content, and service classification",
            "conformity, quality, and post-contract feature changes",
            "unfair terms, security failure, and remedies",
        ],
        "guide_terms": [
            "classify the physical hub and cameras, subscription monitoring, and software updates separately before applying the cra regime",
            "do not treat boilerplate unilateral-change, exclusion, or 14-day complaint clauses as capable of displacing cra statutory rights without fairness analysis",
        ],
    },
    {
        "title": "Company Personality + Parent Liability",
        "label": "Company Personality + Parent Liability - Essay Question",
        "prompt": """Company Personality + Parent Liability - Essay Question

Critically evaluate whether modern English law takes a coherent approach to company personality, veil lifting, and parent-company liability for harm caused by subsidiaries.

In your answer, consider:

the continuing significance of Salomon,
the narrowness of veil piercing,
the distinction between veil lifting and direct liability,
parent-company responsibility in group structures,
business and human rights litigation,
and whether the present law keeps separate doctrines separate or has become conceptually blurred.""",
        "expected_topic": "company_personality_veil_lifting",
        "must_cover_terms": ["salomon v a salomon & co ltd", "prest v petrodel resources ltd", "vedanta resources plc v lungowe"],
        "subquery_terms": [
            "separate personality and the parent-duty route",
            "chandler, vedanta, okpabi, and evidence of control",
            "accountability, forum, and doctrinal coherence",
        ],
    },
    {
        "title": "Competition Law",
        "label": "Competition Law - Problem Question",
        "prompt": """Competition Law - Problem Question

CoreGrid plc controls the only nationwide electricity-balancing platform through which independent generators must trade in order to access major industrial customers. CoreGrid also runs its own downstream retail energy supply business.

Independent suppliers complain that CoreGrid:

raised wholesale platform access charges,
lowered its own downstream prices in the same period,
refused one rival access to real-time technical data needed to compete effectively,
and justified its conduct by saying that tighter control was needed to protect network integrity and investment incentives.

Advise the rival suppliers. In particular, consider:

dominance,
margin squeeze,
refusal to supply,
abuse of dominance,
objective justification,
and the role of economic effects in the analysis.""",
        "expected_topic": "competition_margin_squeeze_refusal",
        "must_cover_terms": ["article 102 tfeu", "deutsche telekom", "bronner"],
        "subquery_terms": [
            "market definition, dominance, and downstream dependence",
            "margin squeeze and foreclosure in wholesale / retail pricing",
            "refusal to supply, interoperability information, and indispensability",
        ],
    },
    {
        "title": "Construction Law",
        "label": "Construction Law - Problem Question",
        "prompt": """Construction Law - Problem Question

Northbank Developments Ltd hires Apex Build Ltd under a standard-form construction contract to complete a commercial office project by 1 September. The contract includes:

liquidated damages for delay,
an extension of time mechanism,
a defects rectification regime,
and a right to adjudicate.

During the works:

Northbank issues major design changes late,
site access is delayed by Northbank's failure to clear neighbouring land,
Apex faces labour shortages and bad weather,
completion is delayed by 16 weeks,
and after practical completion serious waterproofing and HVAC defects emerge.

Northbank deducts liquidated damages. Apex says the employer caused critical delay and that the prevention principle prevents Northbank from enforcing the completion date. Both sides threaten adjudication.

Advise the parties. In particular, consider:

extensions of time,
liquidated damages,
the prevention principle,
liability for defects,
adjudication,
and the practical strengths and weaknesses of each side's case.""",
        "expected_topic": "construction_delay_defects",
        "must_cover_terms": ["housing grants, construction and regeneration act 1996", "extension of time", "prevention principle"],
        "subquery_terms": [
            "delay, time machinery, and extension of time",
            "defects, quality obligations, and breach",
            "remedies, adjudication, and practical outcome",
        ],
    },
    {
        "title": "Criminal Law Problem",
        "label": "Criminal Law - Problem Question",
        "prompt": """Criminal Law - Problem Question

Late at night, Tarek enters a corner shop carrying a metal bar. He demands cash from the owner, Mr Singh, saying he only wants "what the insurance will cover." Mr Singh reaches below the counter. Believing Mr Singh is reaching for a weapon, Tarek strikes him on the arm, causing a fracture. Tarek then takes money from the till and runs outside, where he drops his phone. His friend Imran, who had driven him there, later returns and picks up the phone to "protect" Tarek.

Tarek says:

he only intended to scare Mr Singh,
he honestly believed force was necessary,
and he thought taking insured cash was not truly wrongful.

Advise Tarek and Imran. In particular, consider:

robbery and theft,
dishonesty,
non-fatal offences,
self-defence,
and any possible secondary liability.""",
        "expected_topic": "criminal_nonfatal_offences_self_defence",
        "must_cover_terms": ["theft act 1968", "section 8", "ivey v genting casinos"],
        "subquery_terms": [
            "robbery, theft, and dishonesty",
            "non-fatal offence and self-defence",
            "imran's position, secondary liability, and practical outcome",
        ],
        "guide_terms": [
            "separate robbery and theft analysis from the later non-fatal-offence and self-defence issues instead of letting the violence swallow the property route",
            "do not treat the belief that insured cash is not truly wrongful as a self-answering denial of dishonesty",
        ],
    },
    {
        "title": "Criminal Omissions Essay",
        "label": "Criminal Law - Essay Question",
        "prompt": """Criminal Law - Essay Question

Critically evaluate whether English criminal law takes a coherent approach to liability for homicide by omission.

In your answer, consider:

the general rule against liability for omissions,
recognised duties to act,
gross negligence manslaughter,
causation,
defences and excuses where the defendant faces conflict, fear, or incapacity,
and whether the present law reflects principle or piecemeal development.""",
        "expected_topic": "criminal_omissions_homicide_defences",
        "must_cover_terms": ["gibbins and proctor", "adomako", "gross negligence manslaughter"],
        "subquery_terms": [
            "duties to act and homicide by omission",
            "gross negligence manslaughter and the structure of blame",
            "principle or patchwork?",
        ],
    },
    {
        "title": "Criminal Evidence Essay",
        "label": "Criminal Evidence - Essay Question",
        "prompt": """Criminal Evidence - Essay Question

Critically evaluate whether the modern law of hearsay in criminal proceedings strikes an appropriate balance between evidential flexibility and fairness to the accused.

In your answer, consider:

the rationale of the hearsay rule,
the statutory gateways,
fear, absence, and reliability concerns,
judicial safeguards,
the relationship with Article 6,
and whether the current framework is coherent or mainly pragmatic.""",
        "expected_topic": "criminal_evidence_hearsay",
        "must_cover_terms": ["criminal justice act 2003", "section 114", "article 6"],
        "subquery_terms": [
            "statutory architecture and the absence of a single reliability test",
            "reliability, safeguards, and the practical weakness of safeguards",
            "article 6 sequence and evaluative conclusion",
        ],
    },
    {
        "title": "Employment Status + Equality",
        "label": "Employment Status + Equality - Problem Question",
        "prompt": """Employment Status + Equality - Problem Question

Sana works for BrightRoute Ltd through a contract describing her as an "independent consultant." In practice:

she must perform the work personally,
she works fixed hours,
she is integrated into the company's staffing rota,
she uses company systems and equipment,
and she cannot realistically refuse assignments.

She later discovers that:

a male comparator doing equivalent work is paid substantially more,
her request for flexible working after childbirth was rejected with minimal explanation,
and managers made dismissive comments about her caring responsibilities and religious dress.

BrightRoute says she is not an employee, so equal-pay and unfair-treatment rules are limited.

Advise Sana. In particular, consider:

employment status,
worker and employee tests,
discrimination,
equal pay,
flexible working,
and the remedies that may be available.""",
        "expected_topic": "employment_worker_status",
        "must_cover_terms": ["employment rights act 1996", "section 230", "equality act 2010"],
        "subquery_terms": [
            "status: employee, worker, or self-employed",
            "equal pay and discrimination routes",
            "flexible working, caring responsibilities, and remedies",
        ],
        "guide_terms": [
            "classify status first: employee, limb-b worker, or genuinely self-employed",
            "do not jump into equal-pay or flexible-working doctrine before identifying whether sana is likely to be an employee, a worker, or neither",
        ],
    },
    {
        "title": "Employment Redundancy + Misconduct + Covenants",
        "label": "Employment Redundancy + Misconduct + Covenants - Problem Question",
        "prompt": """Employment Redundancy + Misconduct + Covenants - Problem Question

Harper & Cole Advisory Ltd announces a restructuring. James, a senior consultant, is told his role is "at risk of redundancy," but during the consultation he is also criticised for attitude, client handling, and "disruptive conduct." He is dismissed and the company later hires another consultant into a similar role with a slightly different title.

James's contract also contains:

a 12-month non-compete clause,
a non-solicitation clause covering all former clients,
and broad confidentiality obligations.

After dismissal, James joins a competitor. Harper & Cole threatens proceedings.

Advise James and Harper & Cole. In particular, consider:

genuine redundancy,
unfair dismissal,
overlap between redundancy and misconduct reasoning,
consultation,
restrictive covenants,
and the likely enforceability of the post-termination restrictions.""",
        "expected_topic": "employment_redundancy_unfair_dismissal",
        "must_cover_terms": ["employment rights act 1996", "section 139", "tillman v egon zehnder ltd"],
        "subquery_terms": [
            "real reason for dismissal: redundancy, misconduct, or both",
            "consultation, fairness, and likely unfair-dismissal outcome",
            "restrictive covenants, confidentiality, and enforcement",
        ],
        "guide_terms": [
            "identify the real reason for dismissal before separating redundancy, misconduct, and post-termination restraints",
            "do not let the covenant analysis obscure the prior question whether the dismissal itself was for redundancy, misconduct, or an incoherent mixture of both",
        ],
    },
    {
        "title": "Equity Essay",
        "label": "Equity - Essay Question",
        "prompt": """Equity - Essay Question

Critically evaluate whether the strictness of fiduciary duties in English law is justified.

In your answer, consider:

the nature of fiduciary loyalty,
no-conflict and no-profit rules,
allowances,
proprietary and personal remedies,
commercial relationships,
and whether the law is too strict, too narrow, or appropriately protective.""",
        "expected_topic": "equity_fiduciary_duties",
        "must_cover_terms": ["bristol and west building society v mothew", "keech v sandford", "boardman v phipps"],
        "subquery_terms": [
            "nature and rationale of fiduciary loyalty",
            "no-conflict and no-profit rules",
            "remedies and proprietary accountability",
        ],
    },
    {
        "title": "EU Law Mixed",
        "label": "EU Law - Mixed Essay / Problem Question",
        "prompt": """EU Law - Mixed Essay / Problem Question

Member State A introduces legislation requiring all energy drinks sold domestically to use only locally approved recycled containers and to carry a national sustainability logo. Imported products may still be sold, but only after a costly secondary certification process. A distributor of drinks lawfully marketed in two other Member States challenges the rules.

Advise the distributor. In particular, consider:

free movement of goods,
measures equivalent to quantitative restrictions,
mutual recognition,
possible justifications,
proportionality,
and the constitutional significance of free movement within the wider structure of EU law.""",
        "expected_topic": "eu_free_movement_goods",
        "must_cover_terms": ["article 34 tfeu", "cassis de dijon", "commission v italy"],
        "subquery_terms": [
            "dassonville, cassis, and product requirements",
            "keck, market access, and selling arrangements",
            "justification, proportionality, and coherence",
        ],
    },
    {
        "title": "Family Hague + Children",
        "label": "Family Hague + Children - Problem Question",
        "prompt": """Family Hague + Children - Problem Question

Marta removes her 7-year-old daughter, Eva, from Spain to England without the consent of Eva's father, Daniel. Daniel applies for summary return under the Hague Convention 1980. Marta argues that:

Spain was no longer Eva's habitual residence,
Daniel was not truly exercising rights of custody,
Eva would face a grave risk of harm if returned because of Daniel's controlling behaviour,
and in any event Eva is now settled in England.

If Eva is not returned, both parents also seek child arrangements orders in England.

Advise the parties. In particular, consider:

habitual residence,
rights of custody,
wrongful removal,
grave risk,
settlement,
child objections,
and the relationship between Hague return proceedings and later welfare-based child arrangements decisions.""",
        "expected_topic": "family_child_abduction_hague1980",
        "must_cover_terms": ["convention on the civil aspects of international child abduction 1980", "article 13(b)", "children act 1989"],
        "subquery_terms": [
            "habitual residence, rights of custody, and wrongful removal",
            "grave risk, settlement, and child objections",
            "return outcome and relationship to later child-arrangements proceedings",
        ],
        "guide_terms": [
            "separate the summary return question under the hague framework from any later welfare-based child-arrangements dispute if the child remains in england",
        ],
    },
    {
        "title": "Family Cohabitation Essay",
        "label": "Family Cohabitation Essay",
        "prompt": """Family Law - Essay Question

Critically evaluate whether the law in England and Wales adequately protects cohabitants on relationship breakdown.

In your answer, consider:

the absence of a general status-based regime,
trusts and proprietary estoppel,
economic disadvantage and domestic contribution,
arguments for and against reform,
and whether the current law is principled, outdated, or unjust.""",
        "expected_topic": "family_cohabitation_reform",
        "must_cover_terms": ["burns v burns", "stack v dowden", "jones v kernott"],
        "subquery_terms": [
            "status distinction: marriage, civil partnership, and cohabitation",
            "property disputes and the limits of trusts law",
            "reform debate and fair outcomes",
        ],
    },
    {
        "title": "Public Law / HR Problem",
        "label": "Public Law / Human Rights - Problem Question",
        "prompt": """Public Law / Human Rights - Problem Question

A local authority launches a "Community Integrity Programme" aimed at reducing online harassment and misinformation about public services. It announces that:

repeated publication of "destabilising content" about local housing policy may justify exclusion from council-run venues and consultation forums,
personal data from complainants may be shared internally to assess "reputational risk,"
and community groups should expect "responsible messaging standards."

A tenants' campaign group is then denied access to a council hall after publishing strongly critical material about a redevelopment scheme. One organiser also discovers that the council compiled a profile of her online posts and personal associations without telling her.

The group says the council had previously promised that "robust public participation will remain central to local democracy."

Advise the group and organiser. In particular, consider:

legitimate expectation,
freedom of expression,
privacy,
Article 8 and Article 10,
proportionality,
procedural fairness,
and the remedies most likely to be available.""",
        "expected_topic": "public_law_fettering_expression_assembly",
        "must_cover_terms": ["article 8 echr", "article 10 echr", "r (coughlan) v north and east devon health authority"],
        "subquery_terms": [
            "policy legality, vagueness, and fettering",
            "venue exclusion, expression, and proportionality",
            "profiling, privacy, and procedural fairness",
            "legitimate expectation, remedies, and likely outcome",
        ],
        "guide_terms": [
            "separate the policy-level challenge to the council programme from the specific denial of venue or forum access and from the undisclosed data-profiling complaint",
            "do not treat this as a private-media privacy dispute; the core question is public-authority legality, fairness, and rights-based review",
        ],
    },
    {
        "title": "Devolution Essay",
        "label": "Devolution Law - Essay Question",
        "prompt": """Devolution Law - Essay Question

Critically evaluate whether devolution has strengthened or destabilised the constitutional structure of the United Kingdom.

In your answer, consider:

the legal nature of devolved competence,
Westminster's continuing sovereignty,
constitutional conventions,
legislative overlap and intergovernmental tension,
the role of courts,
and whether the current settlement is coherent and durable.""",
        "expected_topic": "generic_devolution_law",
        "must_cover_terms": ["scotland act 1998", "sewel convention", "r (miller) v secretary of state for exiting the european union"],
        "subquery_terms": [
            "democratic decentralisation and constitutional redesign",
            "asymmetry, sovereignty, and intergovernmental strain",
            "strengthened legitimacy or weakened coherence?",
        ],
    },
    {
        "title": "IP AI Originality Essay",
        "label": "IP AI Originality Essay",
        "prompt": """Intellectual Property - Essay Question

Critically evaluate whether copyright law takes a coherent approach to originality and authorship in the age of AI-assisted creativity.

In your answer, consider:

originality standards,
human intellectual creation,
AI-assisted and AI-generated outputs,
derivative use of training materials,
infringement and exceptions,
and whether current copyright doctrine is adaptable or under strain.""",
        "expected_topic": "ip_copyright_ai_originality",
        "must_cover_terms": ["section 9(3)", "infopaq", "painer"],
        "subquery_terms": [
            "originality, authorship, and human intellectual creation",
            "ai-assisted outputs, training materials, and infringement pressure points",
            "coherence, adaptability, and the better view",
        ],
        "guide_terms": [
            "separate originality and authorship from the different question whether training, input, or output stages may infringe existing copyright",
        ],
    },
    {
        "title": "Land Coownership + Estoppel",
        "label": "Land Coownership + Estoppel - Problem Question",
        "prompt": """Land Coownership + Estoppel - Problem Question

Nadia and Lewis are an unmarried couple. Willow House is bought in Lewis's sole name. Before completion, Lewis tells Nadia: "The title is only in my name for mortgage reasons, but half of this house is yours." Over the next seven years:

Nadia spends GBP70,000 on structural repairs and an extension,
pays most household bills,
makes several lump-sum transfers to Lewis, some marked "mortgage,"
and reduces her working hours to care for Lewis's father and their child.

Lewis later denies that Nadia has any beneficial interest.

Advise Nadia. In particular, consider:

common intention constructive trust,
proprietary estoppel,
the significance of express assurances,
direct and indirect contributions,
and quantification of any beneficial share.""",
        "expected_topic": "land_home_coownership_estoppel_priority",
        "must_cover_terms": ["trusts of land and appointment of trustees act 1996", "stack v dowden", "grant v edwards"],
        "subquery_terms": [
            "beneficial interest: resulting trust weakness and common-intention constructive trust",
            "proprietary estoppel and assurance-based equity",
            "quantification and practical remedies",
        ],
    },
    {
        "title": "Land Easements + Covenants",
        "label": "Land Easements + Covenants - Problem Question",
        "prompt": """Land Easements + Covenants - Problem Question

Greenacre is sold off in plots. Years later, disputes arise between neighbouring freehold owners. One owner claims a right of way over a driveway long used for access to workshops at the rear. Another seeks to stop a neighbour from using land for short-term holiday lets, relying on an old covenant requiring the land to be used only for "private residential purposes."

Advise the parties. In particular, consider:

easements,
acquisition and scope,
freehold covenants,
enforceability in equity,
remedies,
and the practical difficulties in old land-obligation disputes.""",
        "expected_topic": "land_easements_freehold_covenants",
        "must_cover_terms": ["re ellenborough park", "tulk v moxhay", "austerberry v oldham corporation"],
        "subquery_terms": [
            "easement validity and creation",
            "successor enforceability and freehold covenants",
            "interference and remedies",
        ],
    },
    {
        "title": "PIL Attribution + Force",
        "label": "PIL Attribution + Force - Problem Question",
        "prompt": """Public International Law - Problem Question

State A funds, trains, and equips an armed group operating in neighbouring State B. The group attacks military depots and also damages civilian infrastructure. State B responds with cross-border strikes against camps used by the group inside State A's territory, claiming self-defence. State A denies responsibility and says the group acts independently.

Advise the parties. In particular, consider:

attribution,
state responsibility,
use of force,
armed attack and self-defence,
necessity and proportionality,
and the legal significance of indirect support to non-state actors.""",
        "expected_topic": "public_international_law_use_of_force",
        "must_cover_terms": ["article 2(4)", "article 51", "articles on state responsibility"],
        "subquery_terms": [
            "attribution of the armed group and responsibility for indirect support",
            "use of force, armed attack, and self-defence",
            "necessity, proportionality, and likely interstate consequences",
        ],
        "guide_terms": [
            "separate attribution of the armed group's conduct from the distinct question whether state b may use force in self-defence inside state a's territory",
        ],
    },
    {
        "title": "Tort Occupiers Liability",
        "label": "Tort Occupiers Liability - Problem Question",
        "prompt": """Tort Law - Problem Question

A heritage attraction opens its grounds for a night festival. Visitors are directed through a partially lit path where a damaged stone step has been reported several times but not repaired. Warning signs are small and partly obscured by decorations. A visitor, Leah, trips and suffers serious injury. Nearby, a teenager who entered a restricted rooftop area through a broken gate also falls and is injured.

Advise the parties. In particular, consider:

occupiers' liability to visitors and non-visitors,
warnings,
state of repair,
foreseeability,
and how the law treats different categories of entrant.""",
        "expected_topic": "tort_occupiers_liability",
        "must_cover_terms": ["occupiers' liability act 1957", "occupiers' liability act 1984", "tomlinson v congleton"],
        "subquery_terms": [
            "entrant status and governing regime",
            "duty, breach, warnings, and obvious risk",
            "defences and likely liability outcome",
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


print("Second-tier prompt regression passed.")
