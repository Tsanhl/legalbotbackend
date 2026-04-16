"""
Regression checks for the 50-question broad legal prompt batch.
"""

from gemini_service import _infer_retrieval_profile, _subissue_queries_for_unit


CASES = [
    {
        "title": "Constitutional Law - Essay",
        "body": "Critically evaluate whether the UK constitution provides sufficient checks on executive power.",
        "expected_topic": "constitutional_prerogative_justiciability",
        "must_cover_terms": ["rule of law", "fire brigades union"],
        "subquery_terms": ["parliamentary and political accountability", "judicial control and constitutional principle"],
    },
    {
        "title": "Judicial Review - Problem",
        "body": "A minister makes a policy change without consultation affecting thousands. Advise on grounds for judicial review.",
        "expected_topic": "public_law_legitimate_expectation",
        "must_cover_terms": ["moseley", "coughlan"],
        "subquery_terms": ["procedural fairness and consultation", "illegality, fettering, and review grounds"],
    },
    {
        "title": "Human Rights Law - Essay",
        "body": "Is proportionality a superior method of judicial reasoning compared to Wednesbury unreasonableness?",
        "expected_topic": "human_rights_proportionality_adjudication",
        "must_cover_terms": ["de freitas", "r (daly)"],
        "subquery_terms": ["structure of proportionality", "traditional common-law alternatives"],
    },
    {
        "title": "Freedom of Expression - Problem",
        "body": "A protester is arrested for offensive speech. Advise on Article 10 rights.",
        "expected_topic": "generic_freedom_of_expression_law",
        "must_cover_terms": ["article 10 echr", "handyside"],
        "subquery_terms": ["article 10 engagement and the speech context", "legitimate aim, necessity, and proportionality"],
    },
    {
        "title": "Devolution Law - Essay",
        "body": "Critically assess whether devolution has strengthened or weakened the UK constitution.",
        "expected_topic": "generic_devolution_law",
        "must_cover_terms": ["scotland act 1998", "sewel convention"],
        "subquery_terms": ["democratic decentralisation and constitutional redesign", "strengthened legitimacy or weakened coherence?"],
    },
    {
        "title": "Criminal Law (Homicide) - Essay",
        "body": "Critically evaluate whether the law of murder should be reformed.",
        "expected_topic": "generic_criminal_law",
        "must_cover_terms": ["mandatory life sentence", "law commission"],
        "subquery_terms": ["breadth of murder and the fault element", "what reform is justified?"],
    },
    {
        "title": "Criminal Law (Defences) - Problem",
        "body": "A defendant uses force believing they are under threat. Advise on self-defence.",
        "expected_topic": "criminal_nonfatal_offences_self_defence",
        "must_cover_terms": ["criminal law act 1967", "section 76"],
        "subquery_terms": ["honest belief, necessity, and reasonable force", "mistake, excessive force, and likely liability outcome"],
    },
    {
        "title": "Criminal Justice - Essay",
        "body": "Does the criminal justice system prioritise fairness over efficiency?",
        "expected_topic": "general_legal",
        "must_cover_terms": ["legal aid", "trial delay"],
        "subquery_terms": ["what fairness and efficiency mean in criminal process", "overall balance in the current system"],
    },
    {
        "title": "Sentencing Law - Problem",
        "body": "A judge imposes a severe sentence. Advise on appeal.",
        "expected_topic": "generic_sentencing_law",
        "must_cover_terms": ["sentencing act 2020", "manifestly excessive"],
        "subquery_terms": ["appeal threshold and route", "likely outcome on appeal"],
    },
    {
        "title": "Criminology - Essay",
        "body": "Critically assess whether punishment deters crime effectively.",
        "expected_topic": "generic_criminology",
        "must_cover_terms": ["general deterrence", "certainty, celerity, and severity"],
        "subquery_terms": ["deterrence theory and what criminal law is supposed to deter", "deterrence versus other functions of criminal law"],
    },
    {
        "title": "Contract Formation - Essay",
        "body": "Is the doctrine of consideration still necessary?",
        "expected_topic": "general_legal",
        "must_cover_terms": ["foakes v beer", "williams v roffey bros"],
        "subquery_terms": ["classical consideration and certainty", "necessary doctrine or hollow shell?"],
    },
    {
        "title": "Contract Terms - Problem",
        "body": "A contract contains vague terms. Advise on enforceability.",
        "expected_topic": "general_legal",
        "must_cover_terms": ["scammell v ouston", "hillas v arcos"],
        "subquery_terms": ["certainty and construction", "enforceability and practical outcome"],
    },
    {
        "title": "Misrepresentation - Essay",
        "body": "Critically evaluate the role of misrepresentation in contract law.",
        "expected_topic": "contract_misrepresentation_exclusion",
        "must_cover_terms": ["misrepresentation act 1967", "section 2(1)"],
        "subquery_terms": ["representation, term, and contractual allocation of risk", "misrepresentation remedies and contract overlap"],
    },
    {
        "title": "Commercial Law - Problem",
        "body": "A supplier breaches a long-term supply agreement. Advise on remedies.",
        "expected_topic": "generic_commercial_law",
        "must_cover_terms": ["repudiatory breach", "mitigation"],
        "subquery_terms": ["nature of the breach and termination question", "best commercial remedy"],
    },
    {
        "title": "Consumer Law - Essay",
        "body": "Does consumer protection law adequately protect modern consumers?",
        "expected_topic": "generic_consumer_protection_law",
        "must_cover_terms": ["consumer rights act 2015", "digital content"],
        "subquery_terms": ["substantive rights and unfairness control", "adequacy of current protection"],
    },
    {
        "title": "Negligence - Essay",
        "body": "Is the duty of care concept coherent?",
        "expected_topic": "general_legal",
        "must_cover_terms": ["donoghue v stevenson", "caparo industries plc v dickman"],
        "subquery_terms": ["why duty of care exists", "coherence versus pragmatic boundary control"],
    },
    {
        "title": "Occupiers' Liability - Problem",
        "body": "A visitor is injured on premises. Advise on liability.",
        "expected_topic": "tort_occupiers_liability",
        "must_cover_terms": ["occupiers' liability act 1957", "tomlinson v congleton"],
        "subquery_terms": ["entrant status and governing regime", "defences and likely liability outcome"],
    },
    {
        "title": "Nuisance - Essay",
        "body": "Does nuisance law strike a fair balance between landowners?",
        "expected_topic": "general_legal",
        "must_cover_terms": ["sturges v bridgman", "coventry v lawrence"],
        "subquery_terms": ["reasonableness and reciprocal land use", "does nuisance strike a fair balance?"],
    },
    {
        "title": "Defamation - Problem",
        "body": "A social media post harms reputation. Advise on liability.",
        "expected_topic": "defamation_media_privacy",
        "must_cover_terms": ["defamation act 2013", "section 1"],
        "subquery_terms": ["meaning, reference, and serious harm", "remedies and likely liability outcome"],
    },
    {
        "title": "Economic Loss - Essay",
        "body": "Should the law allow broader recovery for pure economic loss?",
        "expected_topic": "tort_economic_loss_negligent_misstatement",
        "must_cover_terms": ["spartan steel", "hedley byrne v heller"],
        "subquery_terms": ["the exclusionary baseline", "should recovery be broader?"],
    },
    {
        "title": "Land Law - Essay",
        "body": "Is the system of registered land effective?",
        "expected_topic": "generic_land_law",
        "must_cover_terms": ["land registration act 2002", "overriding interests"],
        "subquery_terms": ["objectives of title registration", "is the system effective overall?"],
    },
    {
        "title": "Co-ownership - Problem",
        "body": "Two parties dispute ownership of a home. Advise on rights.",
        "expected_topic": "general_legal",
        "must_cover_terms": ["stack v dowden", "trusts of land and appointment of trustees act 1996"],
        "subquery_terms": ["acquisition of beneficial interests", "tolata and practical rights"],
    },
    {
        "title": "Trusts Law - Essay",
        "body": "Are constructive trusts predictable?",
        "expected_topic": "land_coownership_constructive_trusts",
        "must_cover_terms": ["oxley v hiscock", "common intention constructive trust"],
        "subquery_terms": ["creation of common-intention constructive trusts", "predictability and doctrinal legitimacy"],
    },
    {
        "title": "Fiduciary Duties - Problem",
        "body": "A trustee profits from a position. Advise on liability.",
        "expected_topic": "equity_fiduciary_duties",
        "must_cover_terms": ["keech v sandford", "boardman v phipps"],
        "subquery_terms": ["existence and content of fiduciary duty", "remedies and likely outcome"],
    },
    {
        "title": "Proprietary Estoppel - Essay",
        "body": "Is proprietary estoppel too uncertain?",
        "expected_topic": "land_proprietary_estoppel",
        "must_cover_terms": ["thorner v major", "guest v guest"],
        "subquery_terms": ["assurance and expectation", "satisfying the equity"],
    },
    {
        "title": "Company Law - Essay",
        "body": "Do directors' duties ensure corporate accountability?",
        "expected_topic": "company_directors_minorities",
        "must_cover_terms": ["companies act 2006", "section 172"],
        "subquery_terms": ["directors' duties and the accountability claim", "do the duties ensure accountability?"],
    },
    {
        "title": "Shareholder Rights - Problem",
        "body": "A minority shareholder is unfairly treated. Advise on remedies.",
        "expected_topic": "company_directors_minorities",
        "must_cover_terms": ["section 994", "o'neill v phillips"],
        "subquery_terms": ["unfair-prejudice gateway", "likely minority remedy"],
    },
    {
        "title": "Corporate Governance - Essay",
        "body": "Is shareholder primacy justified?",
        "expected_topic": "company_directors_minorities",
        "must_cover_terms": ["companies act 2006", "section 172"],
        "subquery_terms": ["what shareholder primacy means", "is primacy justified?"],
    },
    {
        "title": "Insolvency - Problem",
        "body": "A company cannot pay debts. Advise on creditor rights.",
        "expected_topic": "insolvency_corporate",
        "must_cover_terms": ["insolvency act 1986", "section 214"],
        "subquery_terms": ["wrongful-trading gateway", "liability and remedial outcome"],
    },
    {
        "title": "Corporate Veil - Essay",
        "body": "Should the corporate veil be more easily pierced?",
        "expected_topic": "company_personality_veil_lifting",
        "must_cover_terms": ["salomon v a salomon & co ltd", "prest v petrodel resources ltd"],
        "subquery_terms": ["separate legal personality and the salomon baseline", "alternative routes and critical evaluation"],
    },
    {
        "title": "EU Law - Essay",
        "body": "Is EU law still relevant post-Brexit?",
        "expected_topic": "generic_eu_law",
        "must_cover_terms": ["european union (withdrawal) act 2018", "retained eu law"],
        "subquery_terms": ["retained or assimilated eu law inside uk law", "how relevant is eu law now?"],
    },
    {
        "title": "Direct Effect - Problem",
        "body": "An individual relies on EU law rights. Advise on enforceability.",
        "expected_topic": "eu_supremacy_direct_effect_preliminary_references",
        "must_cover_terms": ["van gend en loos", "article 288 tfeu"],
        "subquery_terms": ["source of the eu right and direct effect", "enforceability against the defendant"],
    },
    {
        "title": "International Law - Essay",
        "body": "Is international law enforceable?",
        "expected_topic": "generic_international_law",
        "must_cover_terms": ["article 38(1) of the icj statute", "state consent"],
        "subquery_terms": ["sources, consent, and the basic claim to legality", "whether international law is truly law"],
    },
    {
        "title": "State Responsibility - Problem",
        "body": "A state breaches an international obligation. Advise on consequences.",
        "expected_topic": "public_international_law_state_responsibility_attribution",
        "must_cover_terms": ["articles on state responsibility", "reparation"],
        "subquery_terms": ["attribution and breach", "invocation and practical consequences"],
    },
    {
        "title": "Trade Law - Essay",
        "body": "Do global trade rules promote fairness?",
        "expected_topic": "generic_international_trade_law",
        "must_cover_terms": ["gatt 1994", "most-favoured-nation"],
        "subquery_terms": ["formal trade equality and market access", "do global trade rules promote fairness?"],
    },
    {
        "title": "Family Law - Essay",
        "body": "Should cohabitants have the same rights as spouses?",
        "expected_topic": "family_cohabitation_reform",
        "must_cover_terms": ["burns v burns", "civil partnership act 2004"],
        "subquery_terms": ["status distinction: marriage, civil partnership, and cohabitation", "proprietary estoppel as a fallback route"],
    },
    {
        "title": "Child Law - Problem",
        "body": "A dispute arises over child custody. Advise on best interests.",
        "expected_topic": "family_private_children_arrangements",
        "must_cover_terms": ["children act 1989", "section 1(3)"],
        "subquery_terms": ["welfare principle and the order sought", "likely order and practical arrangements"],
    },
    {
        "title": "Medical Law - Essay",
        "body": "Is patient autonomy adequately protected?",
        "expected_topic": "medical_consent_capacity",
        "must_cover_terms": ["mental capacity act 2005", "section 1"],
        "subquery_terms": ["from paternalism to patient autonomy", "ongoing tensions and limits"],
    },
    {
        "title": "Mental Capacity - Problem",
        "body": "A patient refuses treatment. Advise on legality.",
        "expected_topic": "medical_consent_capacity",
        "must_cover_terms": ["mental capacity act 2005", "section 4"],
        "subquery_terms": ["capacity under the mental capacity act 2005", "best interests, emergency treatment, and practical outcome"],
    },
    {
        "title": "Employment Law - Essay",
        "body": "Does employment law adequately protect workers?",
        "expected_topic": "general_legal",
        "must_cover_terms": ["employment rights act 1996", "worker status"],
        "subquery_terms": ["substantive protections and who gets them", "adequacy of modern worker protection"],
    },
    {
        "title": "Data Protection - Essay",
        "body": "Is data protection law effective in the digital age?",
        "expected_topic": "data_protection",
        "must_cover_terms": ["uk gdpr", "article 22"],
        "subquery_terms": ["core uk gdpr structure and protected interests", "enforcement, remedies, and evaluation"],
    },
    {
        "title": "Privacy Law - Problem",
        "body": "A company misuses personal data. Advise on liability.",
        "expected_topic": "data_protection",
        "must_cover_terms": ["article 5", "article 82"],
        "subquery_terms": ["processing activity and lawful basis", "liability, enforcement, and remedies"],
    },
    {
        "title": "Intellectual Property - Essay",
        "body": "Does copyright law stifle innovation?",
        "expected_topic": "ip_copyright_ai_originality",
        "must_cover_terms": ["copyright, designs and patents act 1988", "fair dealing"],
        "subquery_terms": ["why copyright might support innovation", "does copyright stifle innovation?"],
    },
    {
        "title": "Cyber Law - Problem",
        "body": "A hacker steals confidential data. Advise on legal consequences.",
        "expected_topic": "cyber_computer_misuse_harassment",
        "must_cover_terms": ["computer misuse act 1990", "section 3za"],
        "subquery_terms": ["unauthorised access and core cma liability", "likely charges and defences"],
    },
    {
        "title": "AI Law - Essay",
        "body": "Can existing legal systems regulate artificial intelligence?",
        "expected_topic": "generic_ai_law",
        "must_cover_terms": ["uk gdpr", "ai act"],
        "subquery_terms": ["existing legal frameworks and what they already regulate", "sufficiency, reform, and the better view"],
    },
    {
        "title": "Jurisprudence - Essay",
        "body": "Is law inherently moral?",
        "expected_topic": "jurisprudence_hart_fuller",
        "must_cover_terms": ["hart", "fuller"],
        "subquery_terms": ["hart: positivism, separability, and the rule of recognition", "fuller: internal morality of law and legality"],
    },
    {
        "title": "Legal Ethics - Problem",
        "body": "A lawyer faces a conflict of interest. Advise on duties.",
        "expected_topic": "legal_ethics_conflicts",
        "must_cover_terms": ["sra principles", "sra code of conduct"],
        "subquery_terms": ["classifying the conflict", "safest professional outcome"],
    },
    {
        "title": "Environmental Law - Essay",
        "body": "Is environmental regulation effective?",
        "expected_topic": "generic_environmental_law",
        "must_cover_terms": ["precautionary principle", "climate change act 2008"],
        "subquery_terms": ["environmental principles and the development-protection balance", "effectiveness, trade-offs, and evaluative conclusion"],
    },
    {
        "title": "Financial Regulation - Problem",
        "body": "A bank fails compliance rules. Advise on liability.",
        "expected_topic": "generic_financial_regulation_law",
        "must_cover_terms": ["financial services and markets act 2000", "senior managers and certification regime"],
        "subquery_terms": ["regulatory breach and governing rule set", "likely regulatory outcome"],
    },
    {
        "title": "Access to Justice - Essay",
        "body": "Is access to justice a reality or an illusion?",
        "expected_topic": "generic_access_to_justice",
        "must_cover_terms": ["article 6 echr", "r (unison) v lord chancellor"],
        "subquery_terms": ["costs, legal aid, and affordability barriers", "adequacy of protection and reform"],
    },
]


for case in CASES:
    prompt = f"4500 words\n{case['title']}\nQuestion:\n{case['body']}"
    profile = _infer_retrieval_profile(prompt)
    assert profile.get("topic") == case["expected_topic"], (case["title"], profile.get("topic"))

    must_cover_blob = " || ".join(profile.get("must_cover") or []).lower()
    subqueries = [label for label, _ in _subissue_queries_for_unit(case["title"], prompt)]
    subquery_blob = " || ".join(subqueries).lower()

    for term in case.get("must_cover_terms", []):
        assert term in must_cover_blob, (case["title"], "must_cover", term, must_cover_blob)
    for term in case.get("subquery_terms", []):
        assert term in subquery_blob, (case["title"], "subqueries", term, subquery_blob)

print("Fourth-batch prompt regression passed.")
