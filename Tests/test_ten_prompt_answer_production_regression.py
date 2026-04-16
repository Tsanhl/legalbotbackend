"""
Regression checks for ten representative prompt shapes that should now route to
topic-specific answer-production guidance rather than generic or wrong-topic paths.
"""

from gemini_service import _infer_retrieval_profile, _subissue_queries_for_unit


CASES = [
    {
        "title": "Legal Ethics",
        "body": "Critically evaluate whether a lawyer’s duty of loyalty to the client should ever be subordinated to wider duties to the court, the administration of justice, or the public interest. In your answer, consider: confidentiality and privilege, duties not to mislead the court, conflicts of interest, professional independence, and whether the current balance is coherent.",
        "expected_topic": "legal_ethics_conflicts",
        "must_cover_terms": ["sra principles", "duty to the court", "bolkiah"],
        "issue_terms": ["conflict of interest", "duty to the court"],
        "subquery_terms": ["conflict taxonomy", "former-client protection"],
    },
    {
        "title": "Planning",
        "body": "A local authority grants planning permission for a large mixed-use development on the edge of a town. Local residents argue that the council failed to consider traffic impact, flood risk, and the effect on a nearby conservation area. They also say key documents were published too late for meaningful comment. Advise the residents. In particular, consider: grounds for challenging the permission, procedural fairness, material considerations, irrationality, and the remedies a court may grant.",
        "expected_topic": "generic_planning_law",
        "must_cover_terms": ["town and country planning act 1990", "section 70(2)", "material considerations"],
        "issue_terms": ["material considerations", "procedural fairness"],
        "subquery_terms": ["planning framework", "late documents", "irrationality"],
    },
    {
        "title": "Succession",
        "body": "Marina makes a will leaving her estate equally to her two sons. Two years later, after a serious illness, she signs a new will leaving almost everything to her live-in carer, who had arranged the meeting with the solicitor and was present for much of the discussion. One son argues that Marina lacked capacity; the other argues that the will was procured by undue influence. Advise the parties. In particular, consider: testamentary capacity, knowledge and approval, undue influence, suspicious circumstances, and the likely consequences if the later will is invalid.",
        "expected_topic": "succession_wills_validity",
        "must_cover_terms": ["wills act 1837", "banks v goodfellow", "knowledge and approval"],
        "issue_terms": ["testamentary capacity", "knowledge and approval"],
        "subquery_terms": ["testamentary capacity", "suspicious circumstances", "probate consequence"],
    },
    {
        "title": "Equality",
        "body": "Critically evaluate whether the law on discrimination in England and Wales provides an effective framework for achieving substantive equality rather than merely formal equal treatment. In your answer, consider: direct and indirect discrimination, justification, protected characteristics, positive action, and whether the present law addresses structural disadvantage effectively.",
        "expected_topic": "equality_substantive_framework",
        "must_cover_terms": ["section 149", "section 158", "section 159"],
        "issue_terms": ["structural disadvantage", "positive action"],
        "subquery_terms": ["formal equality", "structural disadvantage", "positive action"],
    },
    {
        "title": "Banking",
        "body": "A company director instructs the company’s bank to transfer a series of large sums to overseas accounts. The bank’s compliance team notices unusual features in the pattern of payments but processes them anyway. It later turns out the director was defrauding the company. Advise the company and the bank. In particular, consider: the bank’s duty when faced with suspicious instructions, attribution issues, causation and loss, possible defences, and the practical limits of bank liability.",
        "expected_topic": "banking_quincecare_fraud",
        "must_cover_terms": ["quincecare", "philipp", "singularis"],
        "issue_terms": ["quincecare qualification", "attribution"],
        "subquery_terms": ["mandate rule", "modern scope", "causation"],
    },
    {
        "title": "PIL",
        "body": "Critically evaluate whether the modern rules on jurisdiction and choice of law in cross-border private disputes achieve a satisfactory balance between certainty, fairness, and forum control. In your answer, consider: connecting factors, party autonomy, forum disputes, parallel proceedings, and whether the present rules are overly technical or appropriately structured.",
        "expected_topic": "private_international_law_post_brexit",
        "must_cover_terms": ["rome i regulation", "rome ii regulation", "hague choice of court agreements convention 2005"],
        "issue_terms": ["service out", "choice of law"],
        "subquery_terms": ["jurisdiction and service-out", "choice of law", "anti-suit relief"],
    },
    {
        "title": "Consumer Credit",
        "body": "Lena enters into a high-interest consumer credit agreement to finance home improvements. The salesperson pressures her into signing immediately, key charges are not clearly explained, and the contractor’s work later proves defective. Lena stops repayments and the lender threatens enforcement. Advise Lena. In particular, consider: enforceability of the credit agreement, unfair relationships, linked transactions, possible claims connected to the defective work, and the remedies available.",
        "expected_topic": "consumer_credit_unfair_relationship",
        "must_cover_terms": ["consumer credit act 1974", "section 75", "section 140a"],
        "issue_terms": ["unfair-relationship analysis", "connected supplier liability"],
        "subquery_terms": ["agreement enforceability", "linked supplier liability", "enforcement resistance"],
    },
    {
        "title": "Insolvency",
        "body": "Critically evaluate whether the modern law of corporate insolvency strikes the right balance between rescue culture and creditor protection. In your answer, consider: rescue procedures, liquidation, office-holder powers, directors’ conduct before insolvency, and whether the present framework promotes efficient and fair outcomes.",
        "expected_topic": "insolvency_corporate",
        "must_cover_terms": ["insolvency act 1986", "section 214", "sequana"],
        "issue_terms": ["office-holder standing", "statutory test"],
        "subquery_terms": ["wrongful trading", "preferences", "phoenix liability"],
    },
    {
        "title": "Extradition",
        "body": "Arman is sought by a foreign state to stand trial for fraud. He argues that extradition should be refused because prison conditions in the requesting state are poor, the trial process is politically influenced, and extradition would seriously disrupt the life of his partner and child in the UK. Advise Arman. In particular, consider: human rights objections, prison conditions, fair trial concerns, family and private life arguments, and the approach the court is likely to take.",
        "expected_topic": "generic_extradition_law",
        "must_cover_terms": ["extradition act 2003", "article 8 echr", "othman"],
        "issue_terms": ["family-life", "prison-conditions"],
        "subquery_terms": ["article 3", "family life", "statutory route"],
    },
    {
        "title": "Jurisprudence",
        "body": "Critically evaluate whether legal certainty is a more important value in a legal system than substantive justice. In your answer, consider: predictability and the rule of law, discretion and hard cases, the relationship between certainty and fairness, positivist and anti-positivist perspectives, and whether law can remain legitimate if it sacrifices too much justice for certainty.",
        "expected_topic": "jurisprudence_legal_certainty_justice",
        "must_cover_terms": ["joseph raz", "the rule of law and its virtue", "law's empire"],
        "issue_terms": ["hard cases", "legal legitimacy"],
        "subquery_terms": ["legal certainty", "hard cases", "legitimacy"],
    },
]


for case in CASES:
    prompt = f"4500 words\n{case['title']}\nQuestion:\n{case['body']}"
    profile = _infer_retrieval_profile(prompt)
    assert profile.get("topic") == case["expected_topic"], (case["title"], profile.get("topic"))

    must_cover_blob = " || ".join(profile.get("must_cover") or []).lower()
    issue_blob = " || ".join(profile.get("issue_bank") or []).lower()
    subquery_blob = " || ".join(label for label, _ in _subissue_queries_for_unit(case["title"], prompt)).lower()

    for term in case["must_cover_terms"]:
        assert term in must_cover_blob, (case["title"], "must_cover", term, must_cover_blob)
    for term in case["issue_terms"]:
        assert term in issue_blob, (case["title"], "issue_bank", term, issue_blob)
    for term in case["subquery_terms"]:
        assert term in subquery_blob, (case["title"], "subqueries", term, subquery_blob)

print("Ten-prompt answer-production regression passed.")
