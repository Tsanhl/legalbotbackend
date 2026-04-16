"""
Regression checks for broader open-domain legal prompts that previously routed
to generic or incorrect profiles.
"""

from gemini_service import _infer_retrieval_profile, _subissue_queries_for_unit


CASES = [
    {
        "title": "Essay — Financial Regulation Law",
        "body": "Critically evaluate whether modern financial regulation effectively prevents systemic risk while promoting market efficiency.",
        "expected_topic": "generic_financial_regulation_law",
        "must_cover_terms": ["financial services and markets act 2000", "basel iii"],
        "issue_terms": ["macroprudential control", "efficiency means liquidity and innovation"],
        "subquery_terms": ["systemic risk, prudential tools, and crisis prevention", "overall balance"],
    },
    {
        "title": "Problem — Data Protection Law",
        "body": "A tech company collects user data without clear consent and shares it with third parties. Advise users on lawful processing, consent requirements, and remedies under data protection law.",
        "expected_topic": "data_protection",
        "must_cover_terms": ["article 6", "article 82"],
        "issue_terms": ["lawful basis", "third-party disclosure obligations"],
        "subquery_terms": ["lawful processing and controller obligations", "consent validity, transparency, and third-party sharing"],
    },
    {
        "title": "Essay — Comparative Law",
        "body": "Critically evaluate the value of comparative law in understanding and developing domestic legal systems.",
        "expected_topic": "generic_comparative_law",
        "must_cover_terms": ["alan watson", "pierre legrand"],
        "issue_terms": ["comparative law is for", "functionalist claims"],
        "subquery_terms": ["purposes and methods of comparative law", "functionalism, legal transplants, and contextual critique"],
    },
    {
        "title": "Problem — Arbitration Law",
        "body": "Two companies agree to arbitration, but one party later refuses to comply with the award. Advise on enforceability, court intervention, and limits of arbitration.",
        "expected_topic": "international_commercial_arbitration",
        "must_cover_terms": ["new york convention", "section 66"],
        "issue_terms": ["simple enforcement of the award", "court supervision"],
        "subquery_terms": ["award enforceability and the main enforcement route", "court intervention, challenge, and supervisory limits"],
    },
    {
        "title": "Essay — Legal History",
        "body": "Critically evaluate how historical development has shaped modern common law reasoning.",
        "expected_topic": "generic_legal_history",
        "must_cover_terms": ["writ system", "precedent"],
        "issue_terms": ["historical inheritances", "methodological claims"],
        "subquery_terms": ["historical foundations of common-law method", "equity, precedent, and reasoning by analogy"],
    },
    {
        "title": "Problem — Consumer Protection Law",
        "body": "A consumer buys goods online that turn out to be faulty and not as described. Advise on statutory rights, remedies, and trader obligations.",
        "expected_topic": "generic_consumer_protection_law",
        "must_cover_terms": ["consumer rights act 2015", "section 20"],
        "issue_terms": ["conformity breach", "cra remedy ladder"],
        "subquery_terms": ["consumer statutory rights and the conformity breach", "repair, replacement, rejection, and refund"],
    },
    {
        "title": "Essay — International Law",
        "body": "Critically evaluate whether international law can be considered truly law.",
        "expected_topic": "generic_international_law",
        "must_cover_terms": ["article 38(1) of the icj statute", "austin"],
        "issue_terms": ["existence of legal rules", "centralised enforcement"],
        "subquery_terms": ["sources, consent, and the basic claim to legality", "whether international law is truly law"],
    },
    {
        "title": "Problem — Extradition Law",
        "body": "A person is requested for extradition to another country where prison conditions are poor. Advise on human rights considerations, and grounds to resist extradition.",
        "expected_topic": "generic_extradition_law",
        "must_cover_terms": ["extradition act 2003", "soering v united kingdom"],
        "issue_terms": ["statutory extradition route", "prison-conditions evidence"],
        "subquery_terms": ["extradition framework and statutory route", "prison conditions, article 3, and assurances"],
    },
    {
        "title": "Essay — Criminology",
        "body": "Critically evaluate whether criminal law effectively deters crime.",
        "expected_topic": "generic_criminology",
        "must_cover_terms": ["general deterrence", "certainty, celerity, and severity"],
        "issue_terms": ["deterrence theory", "certainty, speed, and severity"],
        "subquery_terms": ["deterrence theory and what criminal law is supposed to deter", "deterrence versus other functions of criminal law"],
    },
    {
        "title": "Problem — Professional Negligence",
        "body": "A solicitor gives incorrect legal advice causing financial loss. Advise on duty of care, breach, and damages.",
        "expected_topic": "tort_economic_loss_negligent_misstatement",
        "must_cover_terms": ["hedley byrne v heller", "scope of duty"],
        "issue_terms": ["assumption-of-responsibility route", "scope-of-duty"],
        "subquery_terms": ["duty of care and assumption of responsibility", "scope of duty, causation, and damages"],
    },
    {
        "title": "Essay — Legal Theory (Rule of Law)",
        "body": "Critically evaluate competing conceptions of the rule of law.",
        "expected_topic": "generic_rule_of_law",
        "must_cover_terms": ["dicey", "lord bingham"],
        "issue_terms": ["formal or thin conceptions", "substantive or thick conceptions"],
        "subquery_terms": ["formal or thin conceptions of the rule of law", "competing conceptions and the better view"],
    },
    {
        "title": "Problem — Housing Law",
        "body": "A tenant is evicted without proper notice. Advise on legality of eviction, tenant protections, and remedies.",
        "expected_topic": "generic_housing_law",
        "must_cover_terms": ["protection from eviction act 1977", "court order"],
        "issue_terms": ["tenancy or licence status", "defective notice"],
        "subquery_terms": ["tenancy status and the lawful possession route", "deposit protection, repairs, and self-help eviction"],
    },
    {
        "title": "Essay — Corporate Insolvency Policy",
        "body": "Critically evaluate whether insolvency law balances the interests of creditors and debtors fairly.",
        "expected_topic": "insolvency_corporate",
        "must_cover_terms": ["insolvency act 1986", "pari passu"],
        "issue_terms": ["distributional function", "rescue culture"],
        "subquery_terms": ["objectives of insolvency law and creditor protection", "fairness, distribution, and evaluative conclusion"],
    },
    {
        "title": "Problem — Partnership Law",
        "body": "One partner enters into a contract without authority. Advise on liability of the partnership, and third-party rights.",
        "expected_topic": "partnership_law_pa1890",
        "must_cover_terms": ["partnership act 1890", "section 5"],
        "issue_terms": ["external liability to the third party", "ordinary course of partnership business"],
        "subquery_terms": ["authority of the partner and the ordinary course of business", "liability of the firm and rights of the third party"],
    },
    {
        "title": "Essay — Sentencing Law",
        "body": "Critically evaluate whether current sentencing principles achieve justice and consistency.",
        "expected_topic": "generic_sentencing_law",
        "must_cover_terms": ["sentencing act 2020", "sentencing council"],
        "issue_terms": ["guidelines and appellate oversight", "justice requires substantial individualisation"],
        "subquery_terms": ["purposes of sentencing and proportionality", "guidelines, discretion, and consistency"],
    },
    {
        "title": "Problem — Charity Law",
        "body": "A charity uses funds for purposes outside its stated objectives. Advise on breach of duty, and regulatory consequences.",
        "expected_topic": "generic_charity_law",
        "must_cover_terms": ["charities act 2011", "charity commission"],
        "issue_terms": ["charity's objects", "breach-of-duty question"],
        "subquery_terms": ["objects of the charity and misuse of funds", "regulatory consequences and practical outcome"],
    },
    {
        "title": "Essay — Legal Technology / AI Law",
        "body": "Critically evaluate whether existing legal frameworks are sufficient to regulate artificial intelligence.",
        "expected_topic": "generic_ai_law",
        "must_cover_terms": ["uk gdpr", "equality act 2010"],
        "issue_terms": ["existing legal frameworks by function", "fragmentation"],
        "subquery_terms": ["existing legal frameworks and what they already regulate", "sufficiency, reform, and the better view"],
    },
    {
        "title": "Problem — Energy Law",
        "body": "A company breaches environmental and licensing conditions in energy production. Advise on regulatory enforcement, and liability.",
        "expected_topic": "generic_energy_law",
        "must_cover_terms": ["ofgem", "environment agency"],
        "issue_terms": ["licence compliance", "enforcement ladder"],
        "subquery_terms": ["licensing and permit obligations", "regulatory enforcement and sanctions"],
    },
    {
        "title": "Essay — Access to Justice",
        "body": "Critically evaluate whether access to justice is adequately protected in modern legal systems.",
        "expected_topic": "generic_access_to_justice",
        "must_cover_terms": ["article 6 echr", "r (unison) v lord chancellor"],
        "issue_terms": ["formal court access", "effective remedy"],
        "subquery_terms": ["costs, legal aid, and affordability barriers", "adequacy of protection and reform"],
    },
    {
        "title": "Problem — International Trade Law",
        "body": "A country imposes tariffs that appear to violate trade agreements. Advise on legality under international trade law, and possible remedies.",
        "expected_topic": "generic_international_trade_law",
        "must_cover_terms": ["gatt 1994", "article ii"],
        "issue_terms": ["trade measure precisely", "prima facie breach"],
        "subquery_terms": ["classifying the trade measure and prima facie legality", "dispute settlement and practical remedies"],
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

print("Second-batch prompt regression passed.")
