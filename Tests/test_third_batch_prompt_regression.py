"""
Regression checks for the third batch of open-domain legal prompts.
"""

from model_applicable_service import _infer_retrieval_profile, _subissue_queries_for_unit


CASES = [
    {
        "title": "Essay — Administrative Justice",
        "body": "Critically evaluate whether modern systems of administrative justice (tribunals, ombudsmen, and judicial review) provide effective accountability for public decision-making.",
        "expected_topic": "general_legal",
        "must_cover_terms": ["tribunals, courts and enforcement act 2007", "parliamentary commissioner act 1967"],
        "issue_terms": ["distinct accountability routes", "accessibility, expertise, remedial strength"],
        "subquery_terms": ["tribunals, ombudsmen, and judicial review as accountability routes", "overall accountability and the better view"],
    },
    {
        "title": "Problem — Immigration Law",
        "body": "An individual's visa is revoked on national security grounds without detailed reasons. Advise on procedural fairness, human rights challenges, and possible remedies.",
        "expected_topic": "immigration_asylum_deportation",
        "must_cover_terms": ["special immigration appeals commission act 1997", "ex p doody"],
        "issue_terms": ["procedural-fairness objections to secrecy and lack of reasons", "national-security confidentiality"],
        "subquery_terms": ["procedural fairness, reasons, and national-security secrecy", "human rights challenge and effective appeal"],
    },
    {
        "title": "Essay — Jurisprudence (Natural Law vs Positivism)",
        "body": "Critically evaluate whether law must be morally justified to be valid.",
        "expected_topic": "jurisprudence_hart_fuller",
        "must_cover_terms": ["aquinas", "finnis"],
        "issue_terms": ["conceptual validity question", "gross immorality affects legal validity"],
        "subquery_terms": ["positivism, the separability thesis, and legal validity", "natural-law claims about morality and validity"],
    },
    {
        "title": "Problem — Insurance Law",
        "body": "A policyholder fails to disclose a material fact when entering an insurance contract. Advise on duty of disclosure, remedies for the insurer, and modern reforms.",
        "expected_topic": "insurance_non_disclosure_misrepresentation",
        "must_cover_terms": ["insurance act 2015", "schedule 1"],
        "issue_terms": ["material circumstance, knowledge, inducement", "avoidance, proportionate reduction, altered terms, or no remedy"],
        "subquery_terms": ["fair presentation and material circumstance", "inducement and statutory remedies"],
    },
    {
        "title": "Essay — Environmental Law",
        "body": "Critically evaluate whether environmental law effectively balances economic development and environmental protection.",
        "expected_topic": "generic_environmental_law",
        "must_cover_terms": ["precautionary principle", "climate change act 2008"],
        "issue_terms": ["separate environmental principles, regulatory techniques, and enforcement reality", "development is constrained by precaution"],
        "subquery_terms": ["environmental principles and the development-protection balance", "effectiveness, trade-offs, and evaluative conclusion"],
    },
    {
        "title": "Problem — Competition Law",
        "body": "A dominant company refuses to supply a smaller competitor. Advise on abuse of dominance, and potential remedies.",
        "expected_topic": "competition_margin_squeeze_refusal",
        "must_cover_terms": ["bronner", "ims health"],
        "issue_terms": ["outright refusal-to-supply analysis", "indispensability, elimination of effective competition"],
        "subquery_terms": ["dominance, market power, and the input at issue", "refusal to supply, indispensability, and objective justification"],
    },
    {
        "title": "Essay — Constitutional Reform",
        "body": "Critically evaluate whether constitutional reform should be driven by courts or Parliament.",
        "expected_topic": "general_legal",
        "must_cover_terms": ["constitutional reform act 2005", "jackson v attorney general"],
        "issue_terms": ["constitutional reform through adjudication", "institutional competence, democratic legitimacy"],
        "subquery_terms": ["courts, parliament, and constitutional authority", "who should drive reform and why"],
    },
    {
        "title": "Problem — Media Law (Defamation)",
        "body": "A journalist publishes an article damaging a business's reputation. Advise on defamation, defences, and remedies.",
        "expected_topic": "defamation_media_privacy",
        "must_cover_terms": ["section 1(2)", "lachaux"],
        "issue_terms": ["serious harm or serious financial loss", "public-interest defences"],
        "subquery_terms": ["meaning, reference, and serious financial loss", "remedies and likely publication outcome"],
    },
    {
        "title": "Essay — Law and Economics",
        "body": "Critically evaluate the usefulness of economic analysis in legal decision-making.",
        "expected_topic": "general_legal",
        "must_cover_terms": ["ronald coase", "richard posner"],
        "issue_terms": ["descriptive or explanatory tool", "efficiency claims against distribution"],
        "subquery_terms": ["efficiency, incentives, and the core law-and-economics claim", "limits, rival values, and overall usefulness"],
    },
    {
        "title": "Problem — Agency Law",
        "body": "An agent exceeds authority when entering into a contract. Advise on liability of principal and agent, and third-party rights.",
        "expected_topic": "generic_agency_law",
        "must_cover_terms": ["freeman & lockyer", "collen v wright"],
        "issue_terms": ["actual authority from apparent authority", "warranty of authority"],
        "subquery_terms": ["actual authority and internal limits", "principal liability, agent liability, and warranty of authority"],
    },
    {
        "title": "Essay — Feminist Legal Theory",
        "body": "Critically evaluate the claim that the law reflects and reinforces gender inequality.",
        "expected_topic": "general_legal",
        "must_cover_terms": ["catharine mackinnon", "carol smart"],
        "issue_terms": ["legal doctrine actively reproduces gender hierarchy", "formal neutrality against substantive equality"],
        "subquery_terms": ["formal neutrality, gendered power, and structural critique", "how far law reflects and reinforces gender inequality"],
    },
    {
        "title": "Problem — Cybercrime Law",
        "body": "A person hacks into a company's system and steals data. Advise on criminal liability, and possible defences.",
        "expected_topic": "cyber_computer_misuse_harassment",
        "must_cover_terms": ["computer misuse act 1990", "section 3za"],
        "issue_terms": ["section 1 unauthorised access from section 3 or section 3za", "authorisation, intent"],
        "subquery_terms": ["unauthorised access and core computer misuse act liability", "possible defences and likely charge structure"],
    },
    {
        "title": "Essay — Evidence Law",
        "body": "Critically evaluate whether rules on admissibility of evidence ensure fair trials.",
        "expected_topic": "evidence_admissibility_fair_trial",
        "must_cover_terms": ["section 76", "section 114"],
        "issue_terms": ["truth-finding rationales from fairness-based exclusionary rules", "hearsay, confessions"],
        "subquery_terms": ["truth-finding and admissibility framework", "overall balance and critique"],
    },
    {
        "title": "Problem — Maritime Law",
        "body": "Goods are damaged during sea transport. Advise on liability of carrier, and applicable legal regimes.",
        "expected_topic": "maritime_cargo_damage",
        "must_cover_terms": ["carriage of goods by sea act 1971", "article iii rule 2"],
        "issue_terms": ["governing carriage regime and transport document", "seaworthiness or due-diligence issues"],
        "subquery_terms": ["governing carriage regime and document", "exceptions, limitation, and damages"],
    },
    {
        "title": "Essay — Legal Ethics",
        "body": "Critically evaluate whether lawyers should prioritise client interests over broader justice.",
        "expected_topic": "legal_ethics_conflicts",
        "must_cover_terms": ["sra principles", "prince jefri bolkiah v kpmg"],
        "issue_terms": ["conflict of interest, confidentiality, privilege, and duty to the court", "concurrent-client conflict, former-client conflict"],
        "subquery_terms": ["nature of professional duties and conflict taxonomy", "adequacy of the current framework"],
    },
    {
        "title": "Problem — Tax Law",
        "body": "A company structures transactions to minimise tax liability. Advise on legality vs avoidance, and anti-avoidance rules.",
        "expected_topic": "tax_avoidance_gaar",
        "must_cover_terms": ["finance act 2013", "w t ramsay ltd v inland revenue commissioners"],
        "issue_terms": ["legal tax planning from avoidance", "ramsay purposive construction distinct from the statutory gaar analysis"],
        "subquery_terms": ["tax planning, avoidance, and the transaction structure", "hmrc challenge and likely tax outcome"],
    },
    {
        "title": "Essay — Restorative Justice",
        "body": "Critically evaluate whether restorative justice is a viable alternative to traditional punishment.",
        "expected_topic": "general_legal",
        "must_cover_terms": ["john braithwaite", "victim-offender mediation"],
        "issue_terms": ["process model from the stronger claim that it can replace punishment", "victim participation, accountability, repair"],
        "subquery_terms": ["repair, participation, and restorative aims", "viability and the better overall view"],
    },
    {
        "title": "Problem — Sports Law",
        "body": "An athlete is banned for doping and challenges the decision. Advise on procedural fairness, and legal remedies.",
        "expected_topic": "sports_governance_fairness",
        "must_cover_terms": ["world anti-doping code", "court of arbitration for sport"],
        "issue_terms": ["anti-doping substantive liability from procedural fairness", "route of challenge"],
        "subquery_terms": ["anti-doping liability and the disciplinary route", "appeal route, remedies, and likely outcome"],
    },
    {
        "title": "Essay — Freedom of Information Law",
        "body": "Critically evaluate whether freedom of information laws promote transparency effectively.",
        "expected_topic": "generic_freedom_of_information_law",
        "must_cover_terms": ["freedom of information act 2000", "section 35"],
        "issue_terms": ["basic right of access from qualified and absolute exemptions", "transparency claims against delay"],
        "subquery_terms": ["access rights, exemptions, and the public-interest structure", "how effectively foi promotes transparency"],
    },
    {
        "title": "Problem — Aviation Law",
        "body": "Passengers suffer delays and claim compensation. Advise on airline liability, and passenger rights.",
        "expected_topic": "generic_aviation_law",
        "must_cover_terms": ["regulation (ec) no 261/2004", "article 19 of the montreal convention"],
        "issue_terms": ["fixed-sum passenger-rights compensation from montreal convention delay damages", "extraordinary-circumstances"],
        "subquery_terms": ["passenger-compensation regime and threshold entitlement", "remedies and likely recovery"],
    },
]


for case in CASES:
    prompt = f"4500 words\n{case['title']}\nQuestion:\n{case['body']}"
    profile = _infer_retrieval_profile(prompt)
    assert profile.get("topic") == case["expected_topic"], (case["title"], profile.get("topic"))

    must_cover_blob = " || ".join(profile.get("must_cover") or []).lower()
    issue_blob = " || ".join(profile.get("issue_bank") or []).lower()
    subqueries = [label for label, _ in _subissue_queries_for_unit(case["title"], prompt)]
    subquery_blob = " || ".join(subqueries).lower()

    for term in case["must_cover_terms"]:
        assert term in must_cover_blob, (case["title"], "must_cover", term, must_cover_blob)
    for term in case["issue_terms"]:
        assert term in issue_blob, (case["title"], "issue_bank", term, issue_blob)
    for term in case["subquery_terms"]:
        assert term in subquery_blob, (case["title"], "subqueries", term, subquery_blob)

print("Third-batch prompt regression passed.")
