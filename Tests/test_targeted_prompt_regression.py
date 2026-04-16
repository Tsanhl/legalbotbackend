"""
Targeted regression checks for prompt shapes that were previously falling into
generic routing or weak subquery fan-out.
"""

from gemini_service import _infer_retrieval_profile, _subissue_queries_for_unit


CASES = [
    {
        "title": "Essay — Administrative Law (Delegated Legislation)",
        "body": "Critically evaluate whether judicial control of delegated legislation provides an effective safeguard against misuse of executive power.",
        "expected_topic": "generic_administrative_law",
        "must_cover_terms": ["statutory instruments act 1946", "aylesbury"],
        "issue_terms": ["delegated power", "parliamentary scrutiny"],
        "subquery_terms": ["substantive and procedural ultra vires", "executive power"],
    },
    {
        "title": "Problem — Criminal Law (Attempts)",
        "body": "D buys petrol, pours it around a building intending to set it on fire, but is arrested before lighting it. Advise on liability for attempt, what counts as more than merely preparatory, and whether impossibility would matter.",
        "expected_topic": "generic_criminal_law",
        "must_cover_terms": ["criminal attempts act 1981", "shivpuri"],
        "issue_terms": ["more-than-merely-preparatory", "impossibility"],
        "subquery_terms": ["more-than-merely-preparatory", "impossibility and likely liability"],
    },
    {
        "title": "Essay — Equity (Undue Influence)",
        "body": "Critically evaluate whether the doctrine of undue influence strikes an appropriate balance between protecting vulnerable parties and respecting autonomy.",
        "expected_topic": "general_legal",
        "must_cover_terms": ["etridge", "o'brien"],
        "issue_terms": ["actual undue influence", "presumed undue influence"],
        "subquery_terms": ["actual and presumed undue influence", "autonomy"],
    },
    {
        "title": "Problem — Trusts Law (Trustees' Duties)",
        "body": "Trustees invest trust funds in a high-risk venture that later fails. Advise on breach of trust, standard of care, and possible remedies.",
        "expected_topic": "generic_trusts_law",
        "must_cover_terms": ["trustee act 2000", "nestle"],
        "issue_terms": ["power to invest", "standard of care"],
        "subquery_terms": ["power to invest and the trustee standard of care", "causation, loss, and remedies"],
    },
    {
        "title": "Essay — Constitutional Law",
        "body": "Critically evaluate whether the principle of parliamentary sovereignty remains the central principle of the UK constitution.",
        "expected_topic": "constitutional_prerogative_justiciability",
        "must_cover_terms": ["jackson", "thoburn", "human rights act 1998"],
        "issue_terms": ["orthodox legal supremacy", "common-law constitutionalism"],
        "subquery_terms": ["diceyan orthodoxy", "hra, eu legacy"],
    },
    {
        "title": "Problem — EU Law (Free Movement)",
        "body": "A Member State restricts access to certain jobs to its own nationals. Advise on free movement of workers, possible justifications, and proportionality.",
        "expected_topic": "eu_free_movement_workers_residence",
        "must_cover_terms": ["article 45(4) tfeu", "commission v belgium"],
        "issue_terms": ["public-service exception", "access-to-employment"],
        "subquery_terms": ["article 45 access-to-employment discrimination", "public-service exception"],
    },
    {
        "title": "Essay — Commercial Law (Agency)",
        "body": "Critically evaluate whether the law of agency provides adequate protection for third parties dealing with agents.",
        "expected_topic": "generic_agency_law",
        "must_cover_terms": ["freeman & lockyer", "hely-hutchinson"],
        "issue_terms": ["actual authority", "apparent authority"],
        "subquery_terms": ["apparent authority", "third-party protection"],
    },
    {
        "title": "Problem — Land Law (Leases vs Licences)",
        "body": "X allows Y to occupy a flat for a monthly fee but retains a right to enter at any time. Advise on whether Y has a lease or licence, and the legal consequences.",
        "expected_topic": "generic_land_law",
        "must_cover_terms": ["street v mountford", "antoniades"],
        "issue_terms": ["exclusive possession", "substance over label"],
        "subquery_terms": ["exclusive possession", "legal consequences"],
    },
    {
        "title": "Essay — Criminal Procedure",
        "body": "Critically evaluate whether the current rules on police powers of stop and search strike an appropriate balance between crime prevention and civil liberties.",
        "expected_topic": "general_legal",
        "must_cover_terms": ["police and criminal evidence act 1984", "gillan and quinton"],
        "issue_terms": ["reasonable-suspicion", "suspicionless"],
        "subquery_terms": ["pace reasonable suspicion", "crime control, civil liberties"],
    },
    {
        "title": "Problem — Restitution / Unjust Enrichment",
        "body": "A bank mistakenly transfers 50000 pounds into B's account. B spends part of it before discovering the mistake. Advise on whether the money is recoverable, possible defences, and remedies.",
        "expected_topic": "restitution_mistake",
        "must_cover_terms": ["lipkin gorman", "change of position"],
        "issue_terms": ["unjust-enrichment structure", "change of position"],
        "subquery_terms": ["unjust enrichment and mistake as unjust factor", "change of position"],
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

print("Targeted prompt regression passed.")
