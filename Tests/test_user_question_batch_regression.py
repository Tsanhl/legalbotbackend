"""
Regression checks for the user-provided legal question batch.
"""

from gemini_service import _infer_retrieval_profile, _subissue_queries_for_unit


CASES = [
    {
        "title": "Evidence Law — Essay Question",
        "body": (
            "Critically evaluate whether the modern law on hearsay evidence in criminal proceedings "
            "strikes an appropriate balance between evidential flexibility and the defendant’s right "
            "to a fair trial. In your answer, consider the reasons for the traditional exclusionary "
            "rule, the main statutory exceptions, the relationship between hearsay and Article 6 ECHR, "
            "judicial safeguards, and whether the present approach is principled and coherent."
        ),
        "expected_topic": "criminal_evidence_hearsay",
        "must_cover_terms": ["section 114", "section 116", "article 6"],
        "subquery_terms": ["statutory architecture", "practical weakness of safeguards", "article 6 sequence"],
    },
    {
        "title": "Arbitration Law — Problem Question",
        "body": (
            "Alpha Marine Ltd and Orion Logistics Ltd enter into a commercial contract containing an "
            "arbitration clause. A dispute arises over delayed delivery and defective performance. "
            "The tribunal makes an award in favour of Alpha Marine Ltd. Orion refuses to comply, "
            "arguing that the tribunal exceeded its jurisdiction, it was not given a fair opportunity "
            "to present part of its case, and the award is contrary to public policy. Advise Alpha "
            "Marine Ltd and Orion Logistics Ltd. In particular, consider the role of the courts in "
            "supporting and supervising arbitration, jurisdictional challenge, procedural fairness, "
            "enforcement of arbitral awards, and the limits of court intervention."
        ),
        "expected_topic": "international_commercial_arbitration",
        "must_cover_terms": ["section 66", "section 67", "section 68", "public policy"],
        "subquery_terms": ["award enforceability", "court intervention", "practical outcome"],
    },
    {
        "title": "Charity Law — Essay Question",
        "body": (
            "Critically evaluate whether the modern law of charitable trusts and regulation of "
            "charities provides an effective framework for accountability. In your answer, discuss "
            "the legal meaning of charitable purpose, the public benefit requirement, trustees’ duties, "
            "the role of the Charity Commission, and whether the present law sufficiently prevents "
            "misuse of charitable funds and powers."
        ),
        "expected_topic": "generic_charity_law",
        "must_cover_terms": ["charities act 2011", "public benefit", "charity commission"],
        "subquery_terms": ["charitable purpose", "trustee duties", "misuse"],
    },
    {
        "title": "Administrative Justice — Problem Question",
        "body": (
            "Maya applies for disability support through a government benefits system. Her claim is "
            "rejected automatically by an algorithm-based decision-making process. She receives a short "
            "notice stating only that she did not meet the eligibility criteria. Repeated requests for "
            "a fuller explanation are refused. She believes relevant medical evidence was overlooked. "
            "Advise Maya. In particular, consider whether the decision is amenable to judicial review, "
            "procedural fairness, duties to give reasons, the legality of automated public decision-making, "
            "and what remedies may be available."
        ),
        "expected_topic": "general_legal",
        "must_cover_terms": ["procedural fairness", "reasons", "automated decision-making"],
        "subquery_terms": ["amenability", "human review", "remedies"],
    },
    {
        "title": "Privacy and Media Law — Essay Question",
        "body": (
            "Critically evaluate whether the modern action for misuse of private information strikes "
            "an appropriate balance between privacy and freedom of expression. In your answer, consider "
            "the development of the action, the relationship between Articles 8 and 10 ECHR, the "
            "reasonable expectation of privacy, the role of public interest, and whether the law is "
            "sufficiently clear and predictable."
        ),
        "expected_topic": "public_law_privacy_expression",
        "must_cover_terms": ["article 8 echr", "article 10 echr", "campbell v mgn"],
        "subquery_terms": ["evolution", "threshold", "public interest"],
    },
    {
        "title": "Professional Negligence — Problem Question",
        "body": (
            "A solicitor advises a client, Imran, to enter into a commercial lease without warning him "
            "about a break clause that is heavily restricted in practice. Imran later discovers that he "
            "cannot terminate the lease without major financial penalty and suffers significant business "
            "losses. Advise Imran. In particular, consider the existence and scope of the solicitor’s "
            "duty of care, breach of duty, causation, remoteness of loss, and the remedies that may be available."
        ),
        "expected_topic": "tort_economic_loss_negligent_misstatement",
        "must_cover_terms": ["hedley byrne", "scope of duty", "manchester building society"],
        "subquery_terms": ["assumption of responsibility", "breach", "damages"],
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


print("User-question batch regression passed.")
