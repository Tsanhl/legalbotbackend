"""
Regression checks for the 18 previously uncovered gap-topic prompts.

These assertions verify:
1. each prompt routes to the intended topic profile;
2. mandatory RAG remains active;
3. the profile still carries core subject anchors; and
4. the subquery planner and targeted guide text stay aligned with the prompt.
"""

from model_applicable_service import (
    _backend_request_requires_mandatory_rag,
    _build_legal_answer_quality_gate,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
)


CASES = [
    {
        "title": "AI / Algorithmic Discrimination",
        "label": "AI / Algorithmic Discrimination - Problem Question",
        "prompt": """AI / Algorithmic Discrimination - Problem Question

A local authority introduces an AI-assisted housing allocation system that ranks applicants for emergency accommodation. After several months, advocacy groups discover that:

disabled applicants are disproportionately scored as "lower urgency",
applicants with limited English receive poorer outcomes because the model relies heavily on incomplete written submissions,
and caseworkers almost always follow the system's recommendation without independent reconsideration.

One applicant, Farah, is denied priority accommodation despite evidence of domestic abuse and disability-related needs. When she asks for reasons, the authority provides only a short automated notice.

Advise Farah and the advocacy groups. In particular, consider:

discrimination law,
public law fairness,
transparency and explainability,
human review,
data protection issues,
and the remedies that may be available.""",
        "expected_topic": "ai_algorithmic_discrimination",
        "must_cover_terms": ["equality act 2010", "article 22", "ai act"],
        "subquery_terms": [
            "equality act routes, proxies, and burden of proof",
            "public-law fairness, reasons, and meaningful human review",
            "data protection, transparency, and remedies",
        ],
        "guide_terms": [
            "ai-discrimination problem focus: separate equality act discrimination, public-law fairness, and article 22 / meaningful human review",
            "rubber-stamped human decision-making",
        ],
    },
    {
        "title": "Climate / State Responsibility",
        "label": "Climate / State Responsibility - Essay Question",
        "prompt": """Climate / State Responsibility - Essay Question

Critically evaluate whether existing principles of state responsibility provide an adequate legal framework for addressing responsibility for climate change.

In your answer, consider:

attribution,
breach of international obligations,
causation and evidential difficulty,
shared and cumulative harm,
obligations of prevention and due diligence,
questions of remedy and reparation,
and whether climate harm exposes structural limits in traditional state responsibility doctrine.""",
        "expected_topic": "climate_state_responsibility",
        "must_cover_terms": ["unfccc", "paris agreement", "no-harm principle"],
        "subquery_terms": [
            "primary obligations and climate responsibility",
            "attribution, causation, and responsibility limits",
            "sufficiency of current frameworks and reform",
        ],
    },
    {
        "title": "Criminal Mens Rea",
        "label": "Criminal Law - Mens Rea: Intention and Recklessness - Essay Question",
        "prompt": """Criminal Law - Mens Rea: Intention and Recklessness - Essay Question

Critically evaluate whether English criminal law draws a coherent and morally defensible distinction between intention and recklessness.

In your answer, consider:

direct and oblique intention,
foresight and virtual certainty,
subjective recklessness,
the relationship between fault labels and moral blameworthiness,
difficult borderline cases,
and whether the current law reflects principle or pragmatic compromise.""",
        "expected_topic": "criminal_mens_rea_intention_recklessness",
        "must_cover_terms": ["r v woollin", "r v g", "law commission"],
        "subquery_terms": [
            "intention and the oblique-intent cases",
            "recklessness and fair warning",
            "transferred malice and correspondence",
        ],
    },
    {
        "title": "Cybercrime / Ransomware / Jurisdiction",
        "label": "Cybercrime / Ransomware / Jurisdiction - Problem Question",
        "prompt": """Cybercrime / Ransomware / Jurisdiction - Problem Question

A ransomware group based across several states encrypts the servers of a UK hospital trust, a German logistics company, and a Singaporean law firm. The attackers demand payment in cryptocurrency and threaten to publish stolen patient, employee, and client data. One suspected developer is arrested in England, while the infrastructure used in the attack was hosted partly in the Netherlands and partly in a non-cooperating state.

Advise the relevant authorities and victims. In particular, consider:

criminal liability,
jurisdiction,
cross-border investigation and enforcement,
extradition and evidence-gathering problems,
corporate and public-sector victim issues,
and the practical legal difficulties of attributing and prosecuting ransomware operations.""",
        "expected_topic": "cybercrime_ransomware_jurisdiction",
        "must_cover_terms": ["budapest convention on cybercrime", "article 22", "mutual legal assistance"],
        "subquery_terms": [
            "jurisdictional bases",
            "enforcement and arrest limits",
            "budapest convention and mla",
        ],
    },
    {
        "title": "IHL Targeting",
        "label": "International Humanitarian Law - Targeting, Proportionality, and Civilians - Problem Question",
        "prompt": """International Humanitarian Law - Targeting, Proportionality, and Civilians - Problem Question

During an international armed conflict, State A launches an airstrike on a communications compound used partly by its armed enemy and partly by civilian technicians. Intelligence suggests that a senior military planner may be present, but the information is uncertain. The strike destroys the facility, kills several civilians living nearby, and causes severe damage to a hospital's power supply.

State A argues the target was a lawful military objective and that the anticipated military advantage justified the strike. Human rights organisations disagree.

Advise the parties. In particular, consider:

distinction,
military objectives,
proportionality,
precautions in attack,
treatment of dual-use facilities,
civilian harm,
and the legal significance of uncertainty in targeting decisions.""",
        "expected_topic": "ihl_targeting_proportionality_civilians",
        "must_cover_terms": ["additional protocol i", "article 57", "rome statute"],
        "subquery_terms": [
            "distinction and military objective",
            "proportionality and incidental civilian harm",
            "precautions, accountability, and evaluation",
        ],
    },
    {
        "title": "IHRL Derogation / Extraterritoriality",
        "label": "International Human Rights Law - Derogation and Extraterritoriality - Essay Question",
        "prompt": """International Human Rights Law - Derogation and Extraterritoriality - Essay Question

Critically evaluate whether international human rights law takes a coherent approach to derogation and extraterritorial application in situations of emergency and armed conflict.

In your answer, consider:

the legal basis and limits of derogation,
public emergency and necessity,
non-derogable rights,
jurisdiction outside national territory,
occupation, detention, and overseas operations,
the relationship with international humanitarian law,
and whether the current doctrine is principled or fragmented.""",
        "expected_topic": "international_human_rights_derogation_extraterritoriality",
        "must_cover_terms": ["article 15 echr", "al-skeini v united kingdom", "article 4 iccpr"],
        "subquery_terms": [
            "extraterritorial jurisdiction under article 1 echr",
            "derogation under article 15 echr",
            "non-derogable rights, iccpr comparison, and evaluation",
        ],
    },
    {
        "title": "IP Copyright and Digital Innovation",
        "label": "Intellectual Property - Copyright and Digital Innovation - Essay Question",
        "prompt": """Intellectual Property - Copyright and Digital Innovation - Essay Question

Critically evaluate whether modern copyright law strikes an appropriate balance between protecting creators and promoting access, innovation, and digital reuse.

In your answer, consider:

the justifications for copyright protection,
digital copying and platform-based dissemination,
fair dealing and other exceptions,
text and data mining,
AI-related pressures on copyright doctrine,
and whether the current framework is too restrictive, too permissive, or simply insufficiently adapted to technological change.""",
        "expected_topic": "ip_copyright_digital_innovation",
        "must_cover_terms": ["copyright, designs and patents act 1988", "section 29a", "infopaq"],
        "subquery_terms": [
            "justifications for copyright and innovation pressure points",
            "exclusive rights, exceptions, and technological use",
            "critical evaluation and reform",
        ],
    },
    {
        "title": "IP Trade Marks and Shapes",
        "label": "Intellectual Property - Trade Marks and Shapes - Problem Question",
        "prompt": """Intellectual Property - Trade Marks and Shapes - Problem Question

Forma Home Ltd applies to register the 3D shape of its bestselling minimalist chair as a trade mark. It argues that the chair's silhouette is now strongly associated with its brand. Rivals object, saying:

the shape results from the nature of the goods,
the design gives substantial value to the product,
and consumers buy the chair for its aesthetic appeal rather than because the shape identifies commercial origin.

A competitor then launches a very similar chair and Forma Home threatens infringement proceedings.

Advise the parties. In particular, consider:

registrability of shapes as trade marks,
distinctiveness and acquired distinctiveness,
shape exclusions,
functionality and aesthetic value,
and the difficulties of using trade mark law to protect product design.""",
        "expected_topic": "ip_trademark_shapes",
        "must_cover_terms": ["trade marks act 1994", "section 3(2)", "philips v remington"],
        "subquery_terms": [
            "section 3(2) exclusions and the rationale for excluding shapes",
            "technical result, substantial value, and acquired distinctiveness",
            "competition policy and evaluative conclusion",
        ],
    },
    {
        "title": "Land Leasehold Covenants",
        "label": "Land Law - Leasehold Covenants - Problem Question",
        "prompt": """Land Law - Leasehold Covenants - Problem Question

Mason leases a retail unit for 15 years. The lease contains:

a covenant to keep the premises in repair,
a covenant not to make alterations without consent,
a user covenant restricting use to "high-quality retail purposes,"
and a covenant by the landlord for quiet enjoyment.

Mason later:

converts part of the shop into a small takeaway counter,
installs ventilation equipment without permission,
falls into disrepair in the rear storage area,
and complains that the landlord's redevelopment works have caused severe noise, blocked access, and driven away customers.

The landlord seeks enforcement of the lease terms. Mason seeks relief of his own.

Advise the parties. In particular, consider:

enforceability of leasehold covenants,
breach,
consent to alterations,
quiet enjoyment and derogation from grant,
remedies available to landlord and tenant,
and whether any equitable or statutory protections may arise.""",
        "expected_topic": "land_leasehold_covenants",
        "must_cover_terms": ["landlord and tenant act 1927", "quiet enjoyment", "section 146 law of property act 1925"],
        "subquery_terms": [
            "tenant covenants: repair, user, and alterations",
            "quiet enjoyment, derogation from grant, and landlord interference",
            "enforcement, forfeiture, and practical outcome",
        ],
        "guide_terms": [
            "leasehold-covenant focus: if the facts are about repair, alterations, user clauses, quiet enjoyment, or derogation from grant",
            "tenant covenant breach from landlord interference",
        ],
    },
    {
        "title": "Medical End of Life MCA 2005",
        "label": "Medical Law - End of Life and the Mental Capacity Act 2005 - Problem Question",
        "prompt": """Medical Law - End of Life and the Mental Capacity Act 2005 - Problem Question

Mrs Rahman is a 58-year-old patient with advanced neurodegenerative illness. She is now intermittently conscious and can communicate only briefly. She had previously said to her family that she would not want to be kept alive by invasive treatment if she lost independence and awareness. However, she made no formal advance decision.

Her doctors now believe that continued ventilation and clinically assisted nutrition may prolong her life, but with little prospect of recovery. Her husband says treatment should continue because she is still alive and sometimes responsive. Her adult daughter says treatment should be withdrawn because her mother would not have wanted this.

Advise the hospital and family. In particular, consider:

capacity,
best interests,
the significance of prior wishes and values,
withdrawal of life-sustaining treatment,
the role of the court,
and how end-of-life decision-making is structured under the Mental Capacity Act 2005.""",
        "expected_topic": "medical_end_of_life_mca2005",
        "must_cover_terms": ["mental capacity act 2005", "section 4", "airedale nhs trust v bland"],
        "subquery_terms": [
            "capacity, communication, and prior wishes",
            "best interests and withdrawal of life-sustaining treatment",
            "court involvement, clinical process, and likely outcome",
        ],
    },
    {
        "title": "PIL Customary Sources",
        "label": "Public International Law - Customary International Law and Sources - Essay Question",
        "prompt": """Public International Law - Customary International Law and Sources - Essay Question

Critically evaluate whether customary international law remains a coherent and legitimate source of international legal obligation in modern international law.

In your answer, consider:

state practice,
opinio juris,
specially affected states,
instant custom and evidential difficulty,
the role of international courts and tribunals,
and whether customary law is a genuine source of law or too indeterminate to provide reliable guidance.""",
        "expected_topic": "public_international_law_customary_sources",
        "must_cover_terms": ["article 38(1)(b)", "north sea continental shelf", "persistent objector"],
        "subquery_terms": [
            "orthodox two-element model",
            "nicaragua methodological shift",
            "words vs deeds evidentiary tension",
        ],
    },
    {
        "title": "PIL Immunities and ICC",
        "label": "Public International Law - Immunities and the ICC - Problem Question",
        "prompt": """Public International Law - Immunities and the ICC - Problem Question

A sitting head of state from State X visits State Y, which is a party to the Rome Statute. The ICC has previously issued a warrant for the head of state's arrest for crimes against humanity. State X is not a party to the Rome Statute and argues that personal immunity prevents arrest. State Y is under political pressure both to cooperate with the ICC and to avoid a diplomatic crisis.

Victims' groups seek legal action in State Y's courts, while State X threatens retaliatory measures if the head of state is detained.

Advise State Y. In particular, consider:

immunity ratione personae,
the ICC framework,
the effect of Security Council referrals if relevant,
tensions between treaty obligations and customary immunities,
domestic implementation issues,
and the likely legal and practical outcome.""",
        "expected_topic": "public_international_law_immunities_icc",
        "must_cover_terms": ["rome statute", "article 27", "article 98"],
        "subquery_terms": [
            "personal and functional immunity",
            "national courts, universal jurisdiction, and pinochet/arrest warrant",
            "icc framework and overall evaluation",
        ],
    },
    {
        "title": "Public Law Article 8",
        "label": "Public Law - Article 8 and Proportionality - Problem Question",
        "prompt": """Public Law - Article 8 and Proportionality - Problem Question

A local authority introduces a policy requiring all applicants for social housing to disclose extensive information about family relationships, support arrangements, medical needs, and previous living situations. The authority also cross-checks this data with other agencies. An applicant, Elena, is denied priority and says the information demands were excessive, the policy interferes with her private and family life, and the decision-making process was opaque and insensitive.

Advise Elena. In particular, consider:

Article 8,
proportionality,
legality and legitimate aim,
procedural fairness,
data-sharing and privacy concerns,
and the relationship between traditional judicial review and rights-based review.""",
        "expected_topic": "public_law_article8_proportionality",
        "must_cover_terms": ["article 8 echr", "razgar", "bank mellat"],
        "subquery_terms": [
            "article 8 engagement, data demands, and protected interests",
            "legality, fairness, reasons, and proportionality",
            "remedies, judicial review, and likely outcome",
        ],
        "guide_terms": [
            "public-law article 8 focus: if the facts are about information demands, data-sharing, or opaque priority decisions",
            "traditional judicial-review grounds and rights-based review interact",
        ],
    },
    {
        "title": "Refugee Maritime Non-Refoulement",
        "label": "Refugee Law - Maritime Interception and Non-Refoulement - Problem Question",
        "prompt": """Refugee Law - Maritime Interception and Non-Refoulement - Problem Question

A naval vessel from State A intercepts a crowded boat in international waters carrying asylum seekers fleeing conflict. The vessel prevents the boat from continuing toward State A's territory and transfers the passengers to the authorities of State B, where asylum procedures are poor and there is evidence of onward return to persecution. State A argues that it never formally admitted the passengers and that its obligations were limited because the interception occurred outside its territory.

Human rights groups challenge the operation.

Advise the parties. In particular, consider:

non-refoulement,
jurisdiction at sea,
extraterritorial human rights obligations,
refugee status determination,
maritime interception,
and the legal significance of indirect return through a third state.""",
        "expected_topic": "refugee_maritime_non_refoulement",
        "must_cover_terms": ["article 33", "non-refoulement", "illegal migration act 2023"],
        "subquery_terms": [
            "jurisdiction and effective control at sea",
            "direct and chain refoulement",
            "offshore processing, interdiction, and evaluation",
        ],
    },
    {
        "title": "Space Debris Liability",
        "label": "Space Law - Debris and Liability - Problem Question",
        "prompt": """Space Law - Debris and Liability - Problem Question

A privately operated satellite licensed by State A fragments in orbit after a collision with an inactive military satellite originally launched by State B decades earlier. The debris field damages:

a commercial communications satellite owned by a company in State C,
and a weather-monitoring satellite operated by State D.

State A argues that the old satellite from State B created unreasonable risk by remaining unremoved. State B argues that the immediate cause was the commercial operator's failure to manoeuvre. State C seeks compensation. State D calls for international responsibility to be shared.

Advise the parties. In particular, consider:

liability for space objects,
launching state responsibility,
fault and absolute liability,
attribution,
the role of private operators,
and the extent to which existing space law is suited to modern debris disputes.""",
        "expected_topic": "space_law_debris_liability",
        "must_cover_terms": ["outer space treaty", "liability convention", "article iii"],
        "subquery_terms": [
            "launching state, space object, and attribution",
            "liability convention structure",
            "claims process, proof, and reform gap",
        ],
    },
    {
        "title": "Statutory Interpretation",
        "label": "Statutory Interpretation - Essay Question",
        "prompt": """Statutory Interpretation - Essay Question

Critically evaluate whether the modern approach to statutory interpretation in English law is best understood as textual, purposive, or ultimately pragmatic.

In your answer, consider:

literal, golden, and mischief approaches,
purposive interpretation,
internal and external aids,
the role of context,
constitutional statutes and rights-sensitive interpretation,
and whether the present law gives courts too much or too little interpretive freedom.""",
        "expected_topic": "statutory_interpretation",
        "must_cover_terms": ["human rights act 1998", "pepper v hart", "ghaidan"],
        "subquery_terms": [
            "classical canons and modern judicial method",
            "purposive interpretation, context, and constitutional setting",
            "legitimacy and evaluative conclusion",
        ],
    },
    {
        "title": "Tort Negligence Omissions",
        "label": "Tort Law - Negligence and Omissions - Essay Question",
        "prompt": """Tort Law - Negligence and Omissions - Essay Question

Critically evaluate whether the modern law of negligence draws a coherent and defensible boundary around liability for omissions.

In your answer, consider:

the general rule against liability for omissions,
assumption of responsibility,
control and creation of danger,
liability for third-party acts,
public authority omissions,
and whether the distinction between acts and omissions reflects principle or policy-driven limitation of liability.""",
        "expected_topic": "tort_negligence_omissions",
        "must_cover_terms": ["robinson v chief constable of west yorkshire police", "michael v chief constable of south wales police", "stovin v wise"],
        "subquery_terms": [
            "general no-duty rule and recognised exceptions",
            "public authority and factual application",
            "causation, scope, and overall outcome",
        ],
    },
    {
        "title": "WTO Trade Security Exceptions",
        "label": "WTO Law - Trade and Security Exceptions - Essay Question",
        "prompt": """WTO Law - Trade and Security Exceptions - Essay Question

Critically evaluate whether the WTO security exceptions provide a coherent legal framework for balancing trade obligations against national security claims.

In your answer, consider:

the structure of the security exceptions,
self-judging versus reviewable elements,
recent state reliance on security justifications,
the role of good faith,
the institutional limits of WTO adjudication,
and whether the current framework protects both the trading system and legitimate security interests.""",
        "expected_topic": "wto_trade_security_exceptions",
        "must_cover_terms": ["gatt 1994", "article xxi", "good faith"],
        "subquery_terms": [
            "prima facie breach and article xxi structure",
            "self-judging language, good faith, and russia",
            "balance, deference, and system integrity",
        ],
    },
]


for case in CASES:
    profile = _infer_retrieval_profile(case["prompt"])
    assert profile["topic"] == case["expected_topic"], (case["title"], profile.get("topic"))
    assert _backend_request_requires_mandatory_rag(case["prompt"], {"active": False}) is True, case["title"]

    must_cover_blob = " || ".join(profile.get("must_cover") or []).lower()
    for term in case["must_cover_terms"]:
        assert term in must_cover_blob, (case["title"], "must_cover", term, must_cover_blob)

    subquery_blob = " || ".join(
        label.lower() for label, _ in _subissue_queries_for_unit(case["label"], case["prompt"])
    )
    for term in case["subquery_terms"]:
        assert term in subquery_blob, (case["title"], "subqueries", term, subquery_blob)

    for term in case.get("guide_terms", []):
        gate = _build_legal_answer_quality_gate(case["prompt"], profile).lower()
        assert term in gate, (case["title"], "guide", term, gate[:5000])


print("Gap-topic routing regression passed.")
