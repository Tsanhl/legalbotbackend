"""
Regression checks for additional previously untested subject-specific routes.

These assertions verify:
1. mandatory RAG remains active for these legal complete-answer prompts;
2. each prompt routes to the intended topic profile;
3. the profile still carries core subject anchors; and
4. the subquery planner stays specific to the subject instead of drifting into generic fallback analysis.
"""

from gemini_service import (
    _backend_request_requires_mandatory_rag,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
)


CASES = [
    {
        "title": "Contract Sale of Goods",
        "label": "Contract Law — Problem Question",
        "prompt": """Contract Law — Problem Question

Northpoint Retail Ltd contracts with DeviceWorks plc for the supply of 8,000 specialist tablets for resale in the Christmas market. The written agreement describes the tablets as "new commercial stock, fit for business use, and compliant with UK safety standards". When the tablets arrive, many units overheat, battery life is dramatically below the stated specification, and some are found to contain refurbished internal components. Northpoint rejects part of the consignment, has already resold some units, and faces complaints from downstream customers.

Advise the parties. In particular, consider implied terms as to description, satisfactory quality, and fitness for purpose, acceptance and rejection, partial rejection, damages, and the practical consequences of resale and customer claims.""",
        "expected_topic": "contract_sale_of_goods_implied_terms_remedies",
        "must_cover_terms": ["sale of goods act 1979", "section 13 sale of goods act 1979", "section 14 sale of goods act 1979"],
        "subquery_terms": [
            "governing regime and implied terms",
            "rejection, acceptance, and timing",
            "remedies and loss",
        ],
    },
    {
        "title": "Consumer Digital Content",
        "label": "Consumer Law — Problem Question",
        "prompt": """Consumer Law — Problem Question

Jade downloads a premium fitness app and later buys an additional AI coaching package and connected meal-planning subscription. The trader advertises the service as compatible with her phone, free from major bugs, and capable of producing personalised plans using her health metrics. After purchase, the app crashes repeatedly, the AI coaching feature gives obviously unsuitable training advice, the subscription locks her out after an update, and several functions advertised on the product page never appear.

Advise Jade. In particular, consider the consumer rights applicable to digital content and digital services, conformity standards, repair or replacement, price reduction, refund rights, and any practical limits where some features were accessed before complaint.""",
        "expected_topic": "consumer_digital_content",
        "must_cover_terms": ["consumer rights act", "digital content", "price reduction"],
        "subquery_terms": [
            "digital content classification and conformity",
            "repair, replacement, and price reduction",
            "damage to device and practical remedy outcome",
        ],
    },
    {
        "title": "Consumer Unfair Terms",
        "label": "Consumer Law — Problem Question",
        "prompt": """Consumer Law — Problem Question

HomeShield Storage Ltd contracts with Mr Khan for long-term household storage while he works abroad. The standard terms provide that the company may vary the monthly price at any time, exclude liability for damage caused by its subcontractors, treat all customer complaints as time-barred after seven days, and permit immediate disposal of stored goods if any payment is missed. After serious water damage to the goods, HomeShield relies on the terms and says Mr Khan accepted them by clicking online.

Advise Mr Khan. In particular, consider incorporation, fairness under the Consumer Rights Act 2015, transparency, core terms, imbalance, and the likely effect of any unfair term finding.""",
        "expected_topic": "consumer_unfair_terms_cra2015",
        "must_cover_terms": ["consumer rights act 2015", "director general of fair trading v first national bank", "oft v ashbourne"],
        "subquery_terms": [
            "incorporation, transparency, and the cra 2015 framework",
            "core terms, fairness, and significant imbalance",
            "effect of unfairness findings and practical remedies",
        ],
    },
    {
        "title": "Clinical Negligence",
        "label": "Medical Law — Problem Question",
        "prompt": """Medical Law — Problem Question

Daniel attends hospital with symptoms suggesting an evolving stroke. The emergency team delays imaging and discharge him with a diagnosis of migraine. Twelve hours later he collapses and suffers major neurological damage. Experts agree that prompt treatment would not have guaranteed a full recovery, but it would have given Daniel a significantly better prospect of avoiding severe disability. He also says he was not warned that immediate admission was being considered and would have stayed had the risks been properly explained.

Advise Daniel. In particular, consider breach of duty, causation, loss of chance, material contribution, informed consent, and the practical difficulties in proving recoverable loss.""",
        "expected_topic": "clinical_negligence_causation_loss_of_chance",
        "must_cover_terms": ["gregg v scott", "bailey v ministry of defence", "loss of chance"],
        "subquery_terms": [
            "breach of duty and diagnostic / treatment delay",
            "but-for causation, material contribution, and delayed-treatment analysis",
            "loss of chance, consent, and proof of recoverable loss",
        ],
    },
    {
        "title": "Aviation Montreal",
        "label": "Aviation Law — Problem Question",
        "prompt": """Aviation Law — Problem Question

Mira flies from London to Toronto with Skybridge Air. During boarding, a cabin bag falls from an overhead locker and strikes her head. On the return flight, her checked cello is badly damaged and she also arrives more than 24 hours late after a missed connection caused by an aircraft technical fault. Skybridge says the technical problem was unavoidable, the cello was packed inadequately, and any personal injury claim must be pursued only in negligence.

Advise Mira. In particular, consider the Montreal Convention, passenger injury, baggage damage, delay, the relationship with domestic negligence claims, and the likely heads of recovery.""",
        "expected_topic": "aviation_passenger_injury_montreal",
        "must_cover_terms": ["montreal convention 1999", "article 17", "article 29"],
        "subquery_terms": [
            "convention regime, exclusivity, and heads of claim",
            "passenger injury and article 17 accident",
            "baggage damage, delay, and carrier defences",
            "recoverable loss and practical outcome",
        ],
    },
    {
        "title": "Employment Discrimination",
        "label": "Employment Law — Problem Question",
        "prompt": """Employment Law — Problem Question

Farah works for a consulting firm. After returning from a period of stress-related sickness connected to anxiety, she is moved away from client-facing work. Her manager says clients need someone "more resilient" and later jokes that Farah is "too fragile for leadership". A promotion goes to a less experienced colleague. Farah also alleges that an office social event was held in a venue she could not access because of her mobility impairment, despite earlier requests for adjustments.

Advise Farah. In particular, consider direct discrimination, discrimination arising from disability, reasonable adjustments, harassment, and remedies.""",
        "expected_topic": "employment_discrimination_eqa2010",
        "must_cover_terms": ["equality act 2010", "section 13", "section 136"],
        "subquery_terms": [
            "route classification under the equality act 2010",
            "comparator, pcp, burden, and justification",
            "liability and remedies",
        ],
    },
    {
        "title": "Employment Equal Pay Flexible Working",
        "label": "Employment Law — Problem Question",
        "prompt": """Employment Law — Problem Question

Sophie and Mark work for the same publishing group in different divisions. Sophie discovers that Mark is paid substantially more for work she says is of equal value. Shortly after Sophie returns from parental leave, she requests flexible working to compress her hours over four days. The employer refuses in a short email saying that senior editorial roles require "full visible commitment across the week" and that compressed working would send the wrong signal. Sophie says men in comparable roles have been allowed informal scheduling flexibility.

Advise Sophie. In particular, consider equal pay, comparators, material factor defences, flexible working, indirect sex discrimination, and likely remedies.""",
        "expected_topic": "employment_equal_pay_flexible_working",
        "must_cover_terms": ["equality act 2010", "section 66", "section 69"],
        "subquery_terms": [
            "equal pay and comparator structure",
            "material factor and indirect discrimination",
            "flexible working and remedies",
        ],
    },
    {
        "title": "Employment Redundancy",
        "label": "Employment Law — Problem Question",
        "prompt": """Employment Law — Problem Question

GreenGrid Ltd announces a restructuring and reduces its project-management team from ten to six. Imran is selected for redundancy after a brief scoring exercise based partly on "attitude" and "future culture fit". He is not shown the scoring matrix, receives only one short consultation meeting, and is not told about two alternative vacancies until after dismissal. Younger employees with lower appraisal records are retained.

Advise Imran. In particular, consider redundancy as a potentially fair reason, consultation, selection fairness, alternative employment, age discrimination, and remedies.""",
        "expected_topic": "employment_redundancy_unfair_dismissal",
        "must_cover_terms": ["employment rights act 1996", "section 98", "polkey"],
        "subquery_terms": [
            "redundancy gateway and selection process",
            "consultation, procedure, and alternatives",
            "likely unfair-dismissal outcome and remedies",
        ],
    },
    {
        "title": "Employment Restrictive Covenants",
        "label": "Employment Law — Problem Question",
        "prompt": """Employment Law — Problem Question

Lena leaves her role as a senior account director at a marketing analytics company and joins a rival. Her old contract contains a 12-month non-compete clause covering any competing business in the UK, a non-solicitation clause covering all clients she had contact with in the previous two years, and a confidentiality clause drafted in very broad terms. The former employer seeks an injunction, saying Lena has knowledge of pricing models and strategic pipeline information.

Advise the parties. In particular, consider legitimate business interests, reasonableness, severance, confidentiality, and the practical likelihood of injunctive relief.""",
        "expected_topic": "employment_restrictive_covenants",
        "must_cover_terms": ["herbert morris ltd v saxelby", "tillman v egon zehnder ltd", "thomas v farr"],
        "subquery_terms": [
            "legitimate interest and covenant construction",
            "reasonableness, severance, and garden leave",
            "practical enforcement outcome",
        ],
    },
    {
        "title": "Employment Unfair Dismissal Misconduct",
        "label": "Employment Law — Problem Question",
        "prompt": """Employment Law — Problem Question

Owen is dismissed by MetroRail Services after an internal investigation concludes that he falsified overtime records and behaved aggressively toward a supervisor. Owen says the investigation ignored witness evidence in his favour, relied on selective CCTV footage, and denied him representation at a key disciplinary meeting. MetroRail argues it had a genuine belief in his misconduct after a reasonable investigation.

Advise Owen. In particular, consider the Burchell test, procedural fairness, range of reasonable responses, wrongful dismissal, and remedies.""",
        "expected_topic": "employment_unfair_dismissal_misconduct",
        "must_cover_terms": ["employment rights act 1996", "burchell", "range of reasonable responses"],
        "subquery_terms": [
            "potentially fair reason and misconduct gateway",
            "fairness of investigation and decision to dismiss",
            "employer reputation versus employee rights",
        ],
    },
    {
        "title": "Criminal Omissions Homicide Defences",
        "label": "Criminal Law — Essay Question",
        "prompt": """Criminal Law — Essay Question

Critically evaluate whether the modern criminal law takes a coherent approach to liability for homicide by omission and the availability of defences where the defendant claims panic, fear, or loss of self-control.

In your answer, consider duties to act, special relationships, creation of danger, gross negligence manslaughter, voluntary manslaughter, diminished responsibility, loss of control, and whether the present law is principled or patchwork.""",
        "expected_topic": "criminal_omissions_homicide_defences",
        "must_cover_terms": ["gross negligence manslaughter", "stone and dobinson", "loss of control"],
        "subquery_terms": [
            "duties to act and homicide by omission",
            "gross negligence manslaughter and the structure of blame",
            "loss of control, diminished responsibility, and fairness under pressure",
            "principle or patchwork",
        ],
    },
    {
        "title": "Criminal Property Offences",
        "label": "Criminal Law — Essay Question",
        "prompt": """Criminal Law — Essay Question

Critically evaluate whether the modern law governing theft, fraud, and related property offences draws a coherent line between dishonesty, deception, and commercial sharp practice.

In your answer, consider appropriation, property, intention to permanently deprive, fraud by false representation, abuse of position, the modern test for dishonesty, and whether the law is conceptually clear or overly elastic.""",
        "expected_topic": "criminal_property_offences_dishonesty",
        "must_cover_terms": ["theft act 1968", "fraud act 2006", "ivey v genting casinos"],
        "subquery_terms": [
            "from ghosh to ivey/barton",
            "objective standards vs defendant belief",
            "theft/fraud architecture after ivey",
            "critical evaluation and limits",
        ],
    },
    {
        "title": "EU Free Movement Goods",
        "label": "EU Law — Essay Question",
        "prompt": """EU Law — Essay Question

Critically evaluate whether the modern law on the free movement of goods under EU law strikes a coherent balance between market integration and legitimate national regulatory autonomy.

In your answer, consider customs duties and charges having equivalent effect, internal taxation, quantitative restrictions and measures having equivalent effect, mandatory requirements, Article 36, Keck, market access, and whether the doctrine is principled or unstable.""",
        "expected_topic": "eu_free_movement_goods",
        "must_cover_terms": ["article 34", "cassis", "keck"],
        "subquery_terms": [
            "dassonville, cassis, and product requirements",
            "keck, market access, and selling arrangements",
            "justification, proportionality, and coherence",
        ],
    },
    {
        "title": "Corporate BHR Parent Liability",
        "label": "Company Law / Tort — Essay Question",
        "prompt": """Company Law / Tort — Essay Question

Critically evaluate whether English law now takes a coherent approach to holding parent companies responsible for overseas human rights and environmental harm caused within corporate groups.

In your answer, consider separate legal personality, direct duty of care, Chandler, Vedanta, Okpabi, corporate group control, and whether the present law delivers genuine accountability or only limited doctrinal workarounds.""",
        "expected_topic": "corporate_bhr_parent_liability",
        "must_cover_terms": ["chandler v cape", "vedanta", "okpabi"],
        "subquery_terms": [
            "separate personality and the parent-duty route",
            "chandler, vedanta, okpabi, and evidence of control",
            "accountability, forum, and doctrinal coherence",
        ],
    },
]


for case in CASES:
    profile = _infer_retrieval_profile(case["prompt"])
    assert profile["topic"] == case["expected_topic"], case["title"]
    assert _backend_request_requires_mandatory_rag(case["prompt"], {"active": False}), case["title"]

    for term in case.get("must_cover_terms", []):
        assert any(term in item.lower() for item in profile.get("must_cover", [])), (
            f"{case['title']} missing must-cover term: {term}"
        )

    subqueries = [title.lower() for title, _ in _subissue_queries_for_unit(case["label"], case["prompt"])]
    for term in case["subquery_terms"]:
        assert any(term in title for title in subqueries), f"{case['title']} missing subquery term: {term}"


print("Missing-topic route regression passed.")
