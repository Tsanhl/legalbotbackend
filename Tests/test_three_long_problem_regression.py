"""
Regression checks for three longer problem-question prompts.

These assertions verify:
1. mandatory RAG remains active;
2. each prompt routes to the intended topic profile;
3. the upgraded must-cover packs include the sharper statutory/case anchors; and
4. the quality gate and subquery planner now reflect the fuller problem structure.
"""

from gemini_service import (
    _backend_request_requires_mandatory_rag,
    _build_legal_answer_quality_gate,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
)


CASES = [
    {
        "title": "Evidence and Criminal Procedure",
        "label": "Evidence and Criminal Procedure — Problem Question",
        "prompt": """Evidence and Criminal Procedure — Problem Question

Rafi is charged with aggravated burglary and causing grievous bodily harm with intent after an attack on a convenience store owner, Mr Patel, during a late-night break-in.

The prosecution case relies on the following material:

Mr Patel gave a detailed statement to police identifying Rafi as one of the attackers. Before trial, Mr Patel leaves the jurisdiction to care for an ill relative and says he is too frightened to return because he has received threats from unidentified callers.
A neighbour, Kim, told police on the night that she saw Rafi running from the shop carrying a metal bar. By the time of trial, Kim says she was mistaken and cannot now remember clearly what she saw.
Rafi’s co-accused, Leon, was interviewed under caution and said: “Rafi planned it and hit the shopkeeper first.” Leon later pleads guilty and refuses to give evidence at Rafi’s trial.
The prosecution also seeks to adduce evidence that, three years earlier, Rafi was convicted of possession of a knife in a public place and, one year ago, had been arrested but not charged after an unrelated allegation of threatening behaviour.
During police interview in the present case, Rafi gave “no comment” answers throughout. At trial he says for the first time that he was nearby only because Leon had asked him for a lift and that he had no idea violence was planned.
Police obtained messages from Rafi’s phone after stopping him in the street two days after the offence. The stop was based on a vague anonymous tip. The phone was searched after officers pressured Rafi to unlock it without legal advice. The messages include references to “sorting Patel out” and “bringing the iron.”

Rafi argues that the prosecution evidence is unfair and unreliable.

Advise the court and the parties. In particular, consider:

hearsay and the admissibility of Mr Patel’s statement,
fear, absence, and the significance of good reason for non-attendance,
Kim’s earlier statement and the effect of claimed memory loss,
the status of Leon’s interview statement,
bad character evidence and its possible gateways,
the distinction between charged and uncharged misconduct,
exclusionary discretion and fairness,
the admissibility of the phone evidence,
possible arguments under PACE and Article 6,
adverse inferences from silence,
and the overall fairness of the trial.""",
        "expected_topic": "evidence_admissibility_fair_trial",
        "must_cover_terms": [
            "section 116",
            "section 119",
            "section 34",
        ],
        "guide_terms": [
            "each witness or item of evidence separate",
            "distinguish the statutory gateway from the fairness backstop",
        ],
        "subquery_terms": [
            "unavailable complainant statement: hearsay, fear, and good reason for absence",
            "memory loss witness and co-accused statement",
            "bad character and charged versus uncharged misconduct",
            "phone evidence, silence, exclusion, and overall fairness",
        ],
    },
    {
        "title": "Company Law and Insolvency",
        "label": "Company Law and Insolvency — Problem Question",
        "prompt": """Company Law and Insolvency — Problem Question

Solstice Robotics Ltd is a fast-growing technology company. Its board consists of:

Maya, CEO and majority shareholder,
Arjun, finance director,
Beth, operations director,
and Omar, a non-executive director.

Over an 18-month period, the following occurs:

Maya causes Solstice to enter into a long-term supply contract with Quantum Parts Ltd, a company secretly owned by her brother. The prices are substantially above market rate. She does not disclose the connection to the board.
Arjun becomes aware from internal forecasts that Solstice is unlikely to meet its debts within months. He nevertheless approves continued trading and signs off optimistic management accounts to reassure creditors and investors.
Beth repeatedly raises concerns about the company’s cash position and the Quantum contract, but takes no further action after Maya tells her to “leave finance and strategy to the people who understand it.”
Omar rarely attends meetings, reads little board material, and says he assumed executive directors were dealing with matters competently.
Solstice repays in full a large unsecured loan made by Maya six months earlier, at a time when trade creditors are going unpaid.
Solstice grants a floating charge to Northern Capital Bank to secure pre-existing borrowing. The charge is granted shortly before insolvency and at a time when the company’s financial position is deteriorating rapidly.
Solstice sells valuable software assets to Nova Edge Ltd, another company connected to Maya, for substantially less than an independent valuation.

Two months later, Solstice enters insolvent liquidation. The liquidator, minority shareholders, unpaid suppliers, and Northern Capital Bank all seek advice.

Advise the parties. In particular, consider:

directors’ duties under the Companies Act 2006,
conflicts of interest and secret connected-party dealings,
the duty of care, skill and diligence,
the significance of inaction by Beth and Omar,
the shift toward creditor interests as insolvency approaches,
wrongful trading and related insolvency-based liability,
misfeasance,
preferences,
transactions at an undervalue,
the validity and vulnerability of the floating charge,
ratification and its limits,
derivative claims and unfair prejudice,
remedies available to the liquidator and shareholders,
and possible disqualification consequences.""",
        "expected_topic": "insolvency_corporate",
        "must_cover_terms": [
            "section 212",
            "section 245",
            "section 171",
            "company directors disqualification act 1986",
            "west mercia safetywear ltd v dodd",
        ],
        "guide_terms": [
            "for mixed company/insolvency facts",
            "analyse each director separately where conduct differs",
        ],
        "subquery_terms": [
            "directors' duties, conflicts, and creditor interests",
            "wrongful trading, misfeasance, and director-specific liability",
            "preferences, undervalue transactions, and floating-charge vulnerability",
            "standing, shareholder remedies, ratification, and disqualification",
        ],
    },
    {
        "title": "Medical Law",
        "label": "Medical Law — Problem Question",
        "prompt": """Medical Law — Problem Question

Elena is a 34-year-old concert pianist. After a cycling accident, she is admitted to hospital with a badly damaged left wrist. The treating surgeon tells her that surgery is recommended and obtains her signed consent for an operation on the left wrist. During the consultation:

Elena says she is due to begin an international concert tour in four months and is especially worried about any loss of finger dexterity.
The surgeon does not mention a small but recognised risk of lasting weakness and reduced fine motor control, believing that disclosure would only alarm her and that the operation is clearly in her best interests.

During the operation on Elena’s left wrist, the surgeon notices an unrelated abnormality in her right hand. It is not life-threatening, but he believes it may cause future pain and may eventually require surgery. Without waking Elena or obtaining any further consent, he performs an additional procedure on the right hand.

After surgery, Elena develops complications and loses blood. She is heavily medicated and intermittently confused. At one point she says, “No more treatment, just leave me alone.” Later, when doctors say a transfusion is advisable, she says, “I don’t want anything else done.” Her partner insists she would want all necessary treatment. Her sister produces old messages in which Elena said she would never want to be kept alive by invasive medical intervention if there were serious consequences for her independence and career.

The clinical team concludes that Elena lacks capacity at the relevant time and authorises the transfusion in her best interests.

Separately, because Elena is the lead performer on a major commercial tour, the consultant sends a short email to the tour director stating that there have been complications and that Elena’s hand function may be affected for months. Elena later says she never consented to this disclosure and that the email caused her to lose performance opportunities.

Elena now alleges:

that the undisclosed risk on the left-wrist operation materialised,
that the right-hand procedure was completely unauthorised,
that the transfusion was unlawful,
and that the disclosure to the tour director was a breach of confidentiality.

Advise Elena and the hospital. In particular, consider:

the legal significance of consent,
the distinction between battery and negligence,
disclosure of material risks,
the relevance of patient autonomy,
scope of consent and unauthorised additional procedures,
capacity and fluctuating decision-making,
best interests under the Mental Capacity Act 2005,
the significance of Elena’s statements and past wishes,
confidentiality and disclosure to third parties,
causation and damages,
and the remedies likely to be available.""",
        "expected_topic": "medical_consent_capacity",
        "must_cover_terms": [
            "chatterton v gerson",
            "re t (adult: refusal of medical treatment)",
            "re b (adult: refusal of medical treatment)",
            "w v egdell",
        ],
        "guide_terms": [
            "medical-consent focus: keep four routes distinct",
            "do not let montgomery swallow the whole problem",
            "keep confidentiality separate from treatment law",
        ],
        "subquery_terms": [
            "left-wrist consent and material-risk disclosure",
            "right-hand procedure: scope of consent, battery, and negligence",
            "transfusion: fluctuating capacity, refusal, and best interests",
            "confidentiality, causation, and remedies",
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
        assert term in gate, (case["title"], "guide", term, gate[:5000])

    subquery_blob = " || ".join(
        title.lower() for title, _ in _subissue_queries_for_unit(case["label"], case["prompt"])
    )
    for term in case["subquery_terms"]:
        assert term in subquery_blob, (case["title"], "subqueries", term, subquery_blob)


print("Three long-problem regression passed.")
