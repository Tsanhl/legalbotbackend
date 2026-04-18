"""
Regression checks for two harder 4,500-5,000 word complete-answer prompts.

These assertions verify:
1. mandatory RAG remains active;
2. each prompt routes to the intended topic profile;
3. the long-form quality gate includes the broader issue coverage added for these variants; and
4. the subquery planner keeps the deeper structure explicit.
"""

from model_applicable_service import (
    _backend_request_requires_mandatory_rag,
    _build_legal_answer_quality_gate,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
)


CASES = [
    {
        "title": "Public Law 5000 Essay",
        "label": "Public Law / Constitutional Law — Essay Question",
        "prompt": """Public Law / Constitutional Law — Essay Question

Critically evaluate whether the modern law of judicial review in England and Wales can still be justified as a constitutionally legitimate control of public power, or whether it has developed into an unstable and insufficiently bounded judicial jurisdiction.

In your answer, discuss and assess:

the constitutional foundations of judicial review, including parliamentary sovereignty, the rule of law, and the debate between ultra vires and common-law constitutionalism;
the classic grounds of review and whether illegality, irrationality, and procedural unfairness remain a coherent organising framework;
the significance of legal error, ouster clauses, and judicial control of attempts to insulate executive action from review;
the development and limits of procedural and substantive legitimate expectation;
the relationship between common-law rights and Convention rights;
proportionality, including whether it should remain confined to rights-based review or now be understood as a general ground of review;
judicial restraint, deference, and institutional competence in areas such as national security, resource allocation, and polycentric policy-making;
the impact of the Human Rights Act 1998, including sections 3, 4, and 6, on the structure and intensity of review;
the constitutional significance of review in cases involving the prerogative, access to justice, and the protection of Parliament’s constitutional role;
and whether the present law is best understood as principled, pragmatic, or internally unstable.""",
        "expected_topic": "public_law_judicial_review_deference",
        "must_cover_terms": [
            "anisminic ltd v foreign compensation commission",
            "r (privacy international) v investigatory powers tribunal",
            "section 3 human rights act 1998",
            "section 4 human rights act 1998",
            "section 6 human rights act 1998",
            "r (miller) v secretary of state for exiting the european union",
            "case of proclamations",
            "attorney general v de keyser",
        ],
        "guide_terms": [
            "common-law rights reasoning from convention-rights review",
            "prerogative review, access to justice, and protection of parliament's constitutional role",
            "use anisminic and later legal-error authority",
        ],
        "subquery_terms": [
            "constitutional foundations: ultra vires, common-law principle, or mixed account",
            "grounds of review, control of legal error, and ouster clauses",
            "legitimate expectation, common-law rights, proportionality, and the human rights act",
            "deference, institutional competence, and constitutional legitimacy",
            "prerogative, access to justice, and parliament's constitutional role",
        ],
    },
    {
        "title": "Company Insolvency 5000 Problem",
        "label": "Company Law / Insolvency — Problem Question",
        "prompt": """Company Law / Insolvency — Problem Question

Orion Dynamics Ltd is a rapidly expanding technology company specialising in software for public-sector logistics. Its board consists of:

Leena, chief executive officer and majority shareholder;
Marcus, finance director;
Priya, operations director;
Daniel, non-executive director.

The company’s articles contain no special modification of directors’ duties.

Over an 18-month period, the following occurs:

1. Leena causes Orion to enter into a long-term procurement contract with Vector Source Ltd, a company secretly owned by her brother. The contract price is substantially above market rate, and alternative suppliers were available on better terms. Leena does not disclose her connection to Vector Source to the board.

2. Marcus receives internal cash-flow forecasts showing that Orion is unlikely to meet major liabilities falling due within the next few months unless it secures new investment or drastically cuts expenditure. He nevertheless continues to reassure major creditors that the company is “financially stable” and signs off management accounts that materially overstate short-term liquidity.

3. Priya repeatedly raises concerns about the Vector Source contract, the company’s worsening cash position, and the accuracy of internal reporting. Leena tells her that these are “finance issues” and that she should “focus on operations.” Priya does not resign, notify creditors, or take further formal action.

4. Daniel rarely attends meetings, reads little board material, and says he relied on Leena and Marcus to manage the company. He approves major transactions by email without reading the accompanying papers.

5. Six months before insolvency, Orion repays in full a substantial unsecured loan previously advanced by Leena. At the same time, trade creditors are left unpaid and payment terms with suppliers are repeatedly extended.

6. Three months later, Orion grants a floating charge to Northbridge Bank plc to secure existing indebtedness and a small amount of new working capital. The company’s financial position continues to deteriorate rapidly.

7. Two months before liquidation, Orion transfers a highly valuable software module and associated IP rights to NovaEdge Ltd, a company controlled by Leena’s long-term business associate, for a price well below a recent internal valuation.

8. During this period, Orion continues to take advance payments from several public-sector customers despite serious doubts within management about whether the company can complete the projects on time or at all.

9. Shortly before liquidation, Leena proposes that the company declare a dividend on the basis of the optimistic management accounts approved by Marcus. The dividend is paid to Leena and a small number of other shareholders.

10. A minority shareholder, Amir, who owns 12% of the shares, repeatedly asks for explanations about related-party dealings, liquidity problems, and the transfer of assets. He is told that the board’s commercial decisions are confidential and that the company remains profitable.

Orion Dynamics Ltd then enters insolvent liquidation.

The following parties now seek advice:

the liquidator;
Amir, the minority shareholder;
several unpaid trade creditors;
Northbridge Bank plc;
Leena, Marcus, Priya, and Daniel.

Advise the parties. In particular, consider:

directors’ duties under the Companies Act 2006, including conflicts of interest, the duty to promote the success of the company, and the duty of care, skill and diligence;
the significance of non-disclosure, passivity, and reliance on others;
the shift from shareholder interests to creditor interests as insolvency approaches;
wrongful trading, fraudulent trading, misfeasance, and any other relevant insolvency-based claims;
preferences, transactions at an undervalue, transactions defrauding creditors, and the legal consequences of the repayment to Leena and the transfer to NovaEdge Ltd;
the validity and vulnerability of the floating charge granted to Northbridge Bank plc;
unlawful distributions and the dividend payment;
possible claims arising from taking advance payments when the company’s financial position was grave;
derivative claims, unfair prejudice, ratification, and the practical obstacles facing Amir;
remedies available to the liquidator, creditors, and shareholders;
and any realistic disqualification consequences for the directors.""",
        "expected_topic": "insolvency_corporate",
        "must_cover_terms": [
            "section 213",
            "section 830",
            "section 847",
            "re produce marketing consortium ltd (no 2)",
            "re d'jan of london ltd",
            "aveling barford ltd v perion ltd",
        ],
        "guide_terms": [
            "wrongful trading from fraudulent trading",
            "dividends and other distributions as their own company-law problem",
            "customer advance-payment facts suggesting conscious exposure of creditors or clients to non-performance risk",
        ],
        "subquery_terms": [
            "directors' duties, conflicts, and creditor interests",
            "wrongful trading, misfeasance, and director-specific liability / fraudulent trading and advance payments",
            "preferences, undervalue transactions, and floating-charge vulnerability / section 423 and unlawful distributions",
            "standing, shareholder remedies, ratification, and disqualification / practical outcomes for creditors and the bank",
        ],
    },
]


for case in CASES:
    profile = _infer_retrieval_profile(case["prompt"])
    assert profile["topic"] == case["expected_topic"], case["title"]
    assert _backend_request_requires_mandatory_rag(case["prompt"], {"active": False}) is True, case["title"]

    must_cover_blob = " || ".join(profile.get("must_cover") or []).lower()
    for term in case["must_cover_terms"]:
        assert term in must_cover_blob, (case["title"], "must_cover", term, must_cover_blob)

    gate = _build_legal_answer_quality_gate(case["prompt"], profile).lower()
    for term in case["guide_terms"]:
        assert term in gate, (case["title"], "guide", term, gate[:7000])

    subquery_blob = " || ".join(
        title.lower() for title, _ in _subissue_queries_for_unit(case["label"], case["prompt"])
    )
    for term in case["subquery_terms"]:
        assert term in subquery_blob, (case["title"], "subqueries", term, subquery_blob)


print("Two 5000-word prompt regression passed.")
