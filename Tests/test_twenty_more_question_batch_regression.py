"""
Regression coverage for the additional 20-question internal test batch.
"""

from model_applicable_service import _infer_retrieval_profile, _subissue_queries_for_unit


CASES = [
    {
        "title": "Administrative Law — Essay Question",
        "body": (
            "Critically evaluate whether the modern law on procedural fairness in public "
            "decision-making rests on a coherent set of principles. In your answer, consider "
            "the flexible nature of fairness, consultation, duties to hear affected persons, "
            "duties to give reasons, and the relationship between fairness, legitimacy, and "
            "good administration."
        ),
        "expected_topic": "generic_administrative_law",
        "must_cover_terms": ["ridge v baldwin", "doody", "consultation"],
        "subquery_terms": ["procedural fairness", "consultation, participation, and reasons", "better view"],
    },
    {
        "title": "Criminal Law — Problem Question",
        "body": (
            "Noah buys chemicals, studies a building's closing routine, and enters the site "
            "at night carrying matches and fuel. He is arrested before starting a fire. "
            "Advise on attempt, acts more than merely preparatory, impossibility, and any "
            "other inchoate liability that may arise."
        ),
        "expected_topic": "generic_criminal_law",
        "must_cover_terms": ["criminal attempts act 1981", "r v gullefer", "r v geddes"],
        "subquery_terms": ["intent for the full offence", "more-than-merely-preparatory conduct", "impossibility"],
    },
    {
        "title": "Equity and Trusts — Essay Question",
        "body": (
            "Critically evaluate whether the law on breach of fiduciary duty is justified in "
            "imposing strict liability for conflicts of interest and unauthorised profits. In "
            "your answer, consider the no-conflict and no-profit rules, the rationale of "
            "fiduciary loyalty, allowances, and whether modern commercial practice requires a "
            "more flexible approach."
        ),
        "expected_topic": "equity_fiduciary_duties",
        "must_cover_terms": ["keech v sandford", "regal (hastings) ltd v gulliver", "boardman v phipps"],
        "subquery_terms": ["fiduciary loyalty", "no-conflict and no-profit rules", "commercial flexibility"],
    },
    {
        "title": "Land Law — Problem Question",
        "body": (
            "Priya has used a path across Omar's land for 18 years to access her workshop. "
            "Omar now blocks the path and says she has no right to use it. Advise Priya. In "
            "particular, consider easements, prescription, the significance of long use, and "
            "any remedies available."
        ),
        "expected_topic": "land_easements_freehold_covenants",
        "must_cover_terms": ["re ellenborough park", "wheeldon v burrows", "section 62"],
        "subquery_terms": ["easement validity", "creation", "interference and remedies"],
    },
    {
        "title": "Company Law — Essay Question",
        "body": (
            "Critically evaluate whether derivative claims provide an effective mechanism for "
            "enforcing directors' duties. In your answer, consider the rule in Foss v "
            "Harbottle, the statutory derivative claim, permission-stage controls, "
            "alternative remedies, and the practical barriers facing minority shareholders."
        ),
        "expected_topic": "company_directors_minorities",
        "must_cover_terms": ["companies act 2006", "section 260", "section 175"],
        "subquery_terms": ["foss v harbottle", "permission-stage controls", "enforce duties effectively"],
    },
    {
        "title": "Competition Law — Problem Question",
        "body": (
            "A dominant digital platform changes its terms so that third-party sellers must "
            "use its in-house payment service and logistics package if they want prominent "
            "listing on the site. Several smaller sellers claim the terms are exclusionary "
            "and unfair. Advise the sellers. In particular, consider dominance, abuse, tying "
            "or bundling concerns, objective justification, and possible remedies."
        ),
        "expected_topic": "competition_abuse_dominance",
        "must_cover_terms": ["section 18", "article 102 tfeu", "tying"],
        "subquery_terms": ["platform power", "objective justification", "likely competition outcome"],
    },
    {
        "title": "Family Law — Essay Question",
        "body": (
            "Critically evaluate whether the welfare principle provides sufficient guidance "
            "and restraint in disputes concerning children. In your answer, consider the best "
            "interests standard, judicial discretion, parental rights and responsibilities, "
            "and whether the welfare approach is too open-ended."
        ),
        "expected_topic": "family_private_children_arrangements",
        "must_cover_terms": ["children act 1989", "section 1(1)", "section 1(3)"],
        "subquery_terms": ["welfare as principle", "source of discretion", "better view"],
    },
    {
        "title": "Private International Law — Problem Question",
        "body": (
            "A UK-based buyer sues a French manufacturer and a Singapore distributor after "
            "defective machinery causes large business losses. Each defendant argues the "
            "English court is not the proper forum. Advise on jurisdiction, forum "
            "challenges, choice of law, and enforcement issues that may later arise."
        ),
        "expected_topic": "private_international_law_post_brexit",
        "must_cover_terms": ["rome i regulation", "rome ii regulation", "civil jurisdiction and judgments act 1982"],
        "subquery_terms": ["jurisdiction and service-out framework", "choice of law under rome i and rome ii", "practical outcome"],
    },
    {
        "title": "Insurance Law — Essay Question",
        "body": (
            "Critically evaluate whether the modern duty of fair presentation in commercial "
            "insurance achieves a fair balance between insurer protection and insured burden. "
            "In your answer, consider material circumstance, inducement, deliberate, "
            "reckless, and innocent non-disclosure, proportional remedies, and whether "
            "reform has made the law more coherent."
        ),
        "expected_topic": "insurance_non_disclosure_misrepresentation",
        "must_cover_terms": ["insurance act 2015", "section 3", "schedule 1"],
        "subquery_terms": ["informational need", "proportional remedies", "better balance"],
    },
    {
        "title": "Media and Privacy Law — Problem Question",
        "body": (
            "A newspaper plans to publish photographs and private messages relating to a "
            "well-known actor's medical treatment. The paper argues that the actor publicly "
            "promotes a lifestyle brand built on health and authenticity. Advise the actor. "
            "In particular, consider misuse of private information, reasonable expectation of "
            "privacy, Article 8 and Article 10, public interest, and interim injunctions."
        ),
        "expected_topic": "public_law_privacy_expression",
        "must_cover_terms": ["article 8 echr", "article 10 echr", "campbell v mgn ltd"],
        "subquery_terms": ["reasonable expectation of privacy", "public-interest resistance", "interim injunction"],
    },
    {
        "title": "Agency Law — Essay Question",
        "body": (
            "Critically evaluate whether the modern law of agency adequately protects third "
            "parties who deal with agents whose authority is uncertain. In your answer, "
            "consider actual authority, apparent authority, ratification, liability of "
            "principal and agent, and the commercial need for certainty."
        ),
        "expected_topic": "generic_agency_law",
        "must_cover_terms": ["freeman & lockyer", "hely-hutchinson", "armagas"],
        "subquery_terms": ["actual authority", "apparent authority", "risk allocation"],
    },
    {
        "title": "Maritime Law — Problem Question",
        "body": (
            "A cargo of machinery is badly damaged during sea transport. The carrier argues "
            "the damage resulted from poor packing by the shipper; the shipper argues the "
            "ship was unseaworthy and the cargo badly stowed. Advise the parties. In "
            "particular, consider seaworthiness, stowage, carrier responsibility, exclusion "
            "clauses, and the likely legal framework governing carriage by sea."
        ),
        "expected_topic": "maritime_cargo_damage",
        "must_cover_terms": ["carriage of goods by sea act 1971", "article iii rule 1", "article iii rule 2"],
        "subquery_terms": ["governing carriage regime", "carrier breach: stowage, care, and seaworthiness", "exceptions, limitation, and damages"],
    },
    {
        "title": "Tax Law — Essay Question",
        "body": (
            "Critically evaluate whether modern anti-avoidance doctrine draws a clear and "
            "workable distinction between legitimate tax planning and abusive tax avoidance. "
            "In your answer, consider statutory interpretation, purposive approaches, "
            "anti-avoidance rules, commercial substance, and the tension between certainty "
            "and anti-abuse control."
        ),
        "expected_topic": "tax_avoidance_gaar",
        "must_cover_terms": ["finance act 2013", "general anti-abuse rule", "w t ramsay"],
        "subquery_terms": ["westminster doctrine", "gaar", "form vs substance"],
    },
    {
        "title": "Housing Law — Problem Question",
        "body": (
            "Leila rents a flat from a private landlord. The landlord never protected her "
            "deposit, fails to carry out basic repairs, and then changes the locks while she "
            "is away after she complained to the council. Advise Leila. In particular, "
            "consider tenancy protections, deposit obligations, repairing duties, unlawful "
            "eviction, and possible remedies."
        ),
        "expected_topic": "generic_housing_law",
        "must_cover_terms": ["protection from eviction act 1977", "housing act 2004", "section 11"],
        "subquery_terms": ["tenancy status", "deposit protection", "practical outcome"],
    },
    {
        "title": "Medical Law — Essay Question",
        "body": (
            "Critically evaluate whether the law relating to mental capacity and best "
            "interests adequately protects both autonomy and welfare. In your answer, "
            "consider the statutory principles, substituted judgment and best interests, "
            "refusal of treatment, judicial oversight, and whether the framework is "
            "sufficiently rights-sensitive."
        ),
        "expected_topic": "medical_consent_capacity",
        "must_cover_terms": ["mental capacity act 2005", "section 4", "aintree"],
        "subquery_terms": ["statutory framework", "wishes, and welfare", "better balance"],
    },
    {
        "title": "Employment Law — Essay Question",
        "body": (
            "Critically evaluate whether the current law on employment status provides a "
            "coherent distinction between employees, workers, and the genuinely "
            "self-employed. In your answer, consider control, personal service, mutuality "
            "and economic reality, platform work, and whether the present categories remain "
            "fit for purpose."
        ),
        "expected_topic": "employment_worker_status",
        "must_cover_terms": ["ready mixed concrete", "autoclenz", "pimlico"],
        "subquery_terms": ["competing status tests", "platform labour", "better framework"],
    },
    {
        "title": "Restitution / Unjust Enrichment — Problem Question",
        "body": (
            "A catering company pays a deposit to a venue for a large event. The event is "
            "cancelled after the venue loses its licence. The venue refuses repayment, saying "
            "it had already spent the money preparing for the event. Advise the catering "
            "company. In particular, consider failure of basis, total or partial failure, "
            "restitutionary recovery, defences, and the interaction with contractual "
            "allocation of risk."
        ),
        "expected_topic": "restitution_mistake",
        "must_cover_terms": ["fibrosa", "failure of basis", "change of position"],
        "subquery_terms": ["contractual basis of the payment", "failure of basis, expenditure, and defences", "restitutionary recovery"],
    },
    {
        "title": "Data Protection / Digital Governance — Essay Question",
        "body": (
            "Critically evaluate whether the law on automated decision-making and data-driven "
            "administration provides adequate protection against opacity and unfairness. In "
            "your answer, consider transparency, reasons, human review, procedural fairness, "
            "and the limits of existing legal controls."
        ),
        "expected_topic": "data_protection",
        "must_cover_terms": ["article 22", "transparency", "human review"],
        "subquery_terms": ["automated decisions", "human review", "strongest criticism"],
    },
    {
        "title": "Environmental Law — Problem Question",
        "body": (
            "A company obtains permits for an industrial facility, but nearby residents "
            "complain of persistent fumes, vibrations, and contamination of a local "
            "watercourse. The regulator has not yet taken action. Advise the residents. In "
            "particular, consider nuisance, regulatory enforcement, judicial review of "
            "regulatory inaction, causation problems, and practical remedies."
        ),
        "expected_topic": "generic_environmental_law",
        "must_cover_terms": ["private nuisance", "environmental protection act 1990", "judicial review"],
        "subquery_terms": ["statutory nuisance", "regulatory inaction", "practical remedies"],
    },
    {
        "title": "Jurisprudence — Essay Question",
        "body": (
            "Critically evaluate whether the rule of law is best understood as a formal "
            "ideal, a substantive moral principle, or an essentially contested concept. In "
            "your answer, consider thin and thick conceptions, legality, certainty, and "
            "access to justice, the relationship between rule of law and democracy, and "
            "whether the concept has become too vague to do useful work."
        ),
        "expected_topic": "generic_rule_of_law",
        "must_cover_terms": ["dicey", "joseph raz", "fuller"],
        "subquery_terms": ["formal or thin conceptions", "substantive or thick conceptions", "better view"],
    },
]


for case in CASES:
    prompt = f"1500 words\n{case['title']}\nQuestion:\n{case['body']}"
    profile = _infer_retrieval_profile(prompt)
    assert profile.get("topic") == case["expected_topic"], (case["title"], profile.get("topic"))

    must_cover_blob = " || ".join(profile.get("must_cover") or []).lower()
    subquery_blob = " || ".join(label for label, _ in _subissue_queries_for_unit(case["title"], prompt)).lower()

    for term in case["must_cover_terms"]:
        assert term in must_cover_blob, (case["title"], "must_cover", term, must_cover_blob)
    for term in case["subquery_terms"]:
        assert term in subquery_blob, (case["title"], "subqueries", term, subquery_blob)


print("Twenty-more-question batch regression passed.")
