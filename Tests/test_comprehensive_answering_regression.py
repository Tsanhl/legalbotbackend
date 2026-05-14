"""
Regression checks for fuller legal-answer routing and issue coverage on
comprehensive essay/problem prompts.
"""

from model_applicable_service import (
    _build_legal_answer_quality_gate,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
    detect_long_essay,
    extract_word_targets_from_prompt,
)


COMPREHENSIVE_PROMPT_CASES = [
    {
        "label": "Private International Law — Problem Question",
        "prompt": """Private International Law — Problem Question

Word target: about 2,200 words

Harbour Glass Ltd, an English construction supplier, contracts with Solis SA, a French manufacturer, for specialist facade panels for a hotel project in Manchester. The written contract provides that:

“the courts of Paris shall have exclusive jurisdiction”; and
“French law shall govern this contract.”

Before the contract is signed, Solis’s Dutch engineering consultant sends technical assurances directly to Harbour in England stating that the panels comply with UK fire standards and are suitable for the Manchester project. Those assurances are not repeated in the final written contract.

After installation, serious defects emerge. Harbour brings proceedings in England against:

Solis for breach of contract and misrepresentation;
the Dutch consultant for negligent misstatement;
and Solis’s insurer, based in Spain, under a direct action route said to arise under foreign law.

At the same time:

Solis has already started proceedings in Paris seeking a declaration of non-liability;
the consultant argues that any tort claim belongs in the Netherlands, not England;
Solis says the jurisdiction clause prevents English proceedings altogether;
and Harbour later obtains an English judgment against the consultant and wants to enforce it against assets in Italy.

Advise the parties. In particular, consider:

jurisdiction over the contract, tort, and insurance-related claims;
the effect and scope of the exclusive jurisdiction clause;
the separation between jurisdiction, choice of law, and recognition/enforcement;
concurrent proceedings and case-management consequences;
and the practical enforcement issues that may arise if different courts give different outcomes.
""",
        "topic": "private_international_law_post_brexit",
        "issue_terms": ["jurisdiction", "choice of law", "recognition/enforcement", "practical litigation"],
        "subquery_terms": ["service-out", "choice of law", "practical outcome"],
    },
    {
        "label": "Civil Procedure — Essay Question",
        "prompt": """Civil Procedure — Essay Question

Word target: about 2,200 words

Critically evaluate whether the modern civil procedure system in England and Wales strikes an appropriate balance between efficiency, procedural discipline, and access to justice.

In your answer, consider:

the overriding objective,
judicial case management;
disclosure and the cost of document-heavy litigation;
expert evidence and control of trial scope;
sanctions for non-compliance and relief from sanctions;
settlement, mediation, and costs consequences for refusing ADR;
and whether procedural enforcement mechanisms such as strike out, costs sanctions, unless orders, and relief-from-sanctions jurisprudence promote justice or risk subordinating merits to management.

You should also engage with the counterargument that strict procedural discipline is necessary to prevent delay, tactical abuse, inequality of arms, and disproportionate cost, and should assess whether the modern system is coherent, fair, and sustainable in practice.
""",
        "topic": "civil_procedure_justice_balance",
        "issue_terms": ["efficiency", "proportionality", "access to justice", "sanctions"],
        "subquery_terms": ["overriding objective", "disclosure", "adr"],
    },
    {
        "label": "Patent Law — Problem Question",
        "prompt": """Patent Law — Problem Question

Word target: about 2,200 words

NeuroPulse Ltd develops a wearable device that predicts seizure risk by combining biosensor hardware with a data-processing method and an adaptive machine-learning model. It files a UK patent application claiming:

the hardware arrangement,
the prediction method,
and a software-driven system for generating intervention alerts.

Six months before filing, researchers from NeuroPulse had presented preliminary findings at an academic conference, and one of the slides appears to describe part of the prediction process. A year later, a rival company, Synapse Medical plc, launches a competing device and argues that:

the patent is invalid for lack of novelty because of the conference disclosure;
the alleged invention is obvious in light of earlier publications in the field;
part of the claim is really directed to excluded subject matter rather than a true technical invention;
and in any event its own product uses a different architecture and so does not infringe.

At the same time, Dr Malik, a former employee of NeuroPulse, claims that he was the true inventor of the core predictive feature and that the patent should not belong entirely to the company.

NeuroPulse seeks:

an injunction,
damages or an account of profits,
and correction of the register if necessary.

Advise the parties. In particular, consider:

patentability,
novelty,
inventive step,
excluded subject matter and technical contribution,
inventorship and ownership,
infringement,
validity challenges as a defence,
and the remedies most likely to matter in practice.
""",
        "topic": "patent_validity_infringement_ownership",
        "issue_terms": ["patentability", "novelty", "excluded subject matter", "inventorship"],
        "subquery_terms": ["novelty", "excluded subject matter", "inventor", "infringement"],
    },
    {
        "label": "Public Procurement — Problem Question",
        "prompt": """Public Procurement — Problem Question

Word target: about 2,200 words

Eastborough Council runs a procurement for a ten-year integrated housing and care platform contract. The tender documents state that award will be based on:

price,
technical quality,
implementation capacity,
data security,
and social value.

Three final tenders are submitted. The contract is awarded to UrbanAxis Ltd. A losing bidder, Civic Digital plc, challenges the award and alleges that:

the authority changed the practical emphasis given to implementation risk during moderation without clearly notifying bidders;
one evaluator had recently worked for a subcontractor now named in UrbanAxis’s bid;
the evaluators relied on undisclosed concerns about Civic Digital’s performance on unrelated public projects;
and UrbanAxis’s bid was suspiciously low but no proper inquiry was made.

The Council responds that:

moderation is part of ordinary evaluation and no unlawful change of criteria occurred;
any conflict was minor and managed internally;
the authority was entitled to use relevant commercial experience when assessing delivery risk;
and even if there were defects, they made no material difference to the result.

Civic Digital wants the contract award set aside. The Council is about to sign the contract. UrbanAxis says the challenge is really just an attempt to re-run the merits.

Advise the parties. In particular, consider:

transparency and equal treatment;
undisclosed criteria or changes in weighting;
evaluator conflict and apparent bias;
treatment of abnormally low tenders;
remedies before and after contract signature;
and the strongest counterarguments the authority and winning bidder are likely to rely on.
""",
        "topic": "public_procurement_award_challenges",
        "issue_terms": ["transparency", "equal-treatment", "conflict", "abnormally low"],
        "subquery_terms": ["altered criteria", "conflict", "abnormally low", "court approach"],
    },
    {
        "label": "Prison Law — Essay Question",
        "prompt": """Prison Law — Essay Question

Critically evaluate whether prisoners in England and Wales retain meaningful legal protection against arbitrary or disproportionate treatment by the state.

In your answer, consider:

the legal status of prisoners,
procedural fairness in prison decision-making,
judicial review,
Convention rights,
deference to prison administration,
and whether the present law provides real accountability or only limited supervision.
""",
        "topic": "prison_law_state_treatment_review",
        "issue_terms": ["legal status", "judicial review", "Convention rights", "deference"],
        "subquery_terms": ["legal status", "procedural fairness", "meaningful protection"],
    },
    {
        "label": "Wills and Administration of Estates — Problem Question",
        "prompt": """Wills and Administration of Estates — Problem Question

Margaret makes a will leaving her estate equally to her two daughters. After a serious illness, she later signs a new will leaving almost everything to her live-in carer. The carer arranged the solicitor’s visit and was present for much of the discussion. After Margaret’s death:

one daughter argues that Margaret lacked testamentary capacity,
the other argues undue influence,
and the carer says the final will reflects Margaret’s genuine wishes.

Advise the parties. In particular, consider:

testamentary capacity,
knowledge and approval,
undue influence,
suspicious circumstances,
and what happens if the later will is held invalid.
""",
        "topic": "succession_wills_validity",
        "issue_terms": ["testamentary capacity", "knowledge and approval", "undue influence", "suspicious circumstances"],
        "subquery_terms": ["capacity", "suspicious circumstances", "probate consequence"],
    },
    {
        "label": "Product Liability — Problem Question",
        "prompt": """Product Liability — Problem Question

Word target: about 2,200 words

PulseHome Ltd markets a smart home battery and energy-management system for domestic use. The product consists of:

physical battery hardware manufactured abroad,
installation by accredited local contractors,
a software platform updated remotely by PulseHome,
and an AI-driven monitoring feature designed to optimise charging cycles and detect safety risks.

Several incidents occur:

one unit overheats and causes a serious house fire;
another repeatedly issues false danger alerts, causing severe anxiety and expensive emergency callouts;
and in a third case the system fails to warn of a battery fault, leading to property damage and minor personal injury.

PulseHome argues that:

the hardware met all required standards when sold;
any failures were caused by installer error or by consumers ignoring update instructions;
and the software provider, not PulseHome, was responsible for the defective monitoring function.

Claimants argue that:

the product as supplied and maintained was defective;
safety warnings were inadequate;
and PulseHome, as the branded seller and updater of the system, cannot shift blame so easily.

Advise the parties. In particular, consider:

negligence,
strict product liability,
defect,
causation,
the role of software, updates, and post-sale control;
responsibility of manufacturer, installer, software supplier, importer, and brand owner;
possible defences, including misuse and contributory negligence;
and the remedies likely to be most important in practice.
""",
        "topic": "product_liability_consumer_protection",
        "issue_terms": ["strict product liability", "defect", "software", "post-sale control"],
        "subquery_terms": ["strict product liability", "software", "installer", "contributory negligence"],
    },
    {
        "label": "Company Law — Essay Question",
        "prompt": """Company Law — Essay Question

Word target: about 2,200 words

Critically evaluate whether modern English company law takes a coherent approach to separate corporate personality, veil piercing, and parent-company liability.

In your answer, consider:

the continuing significance of Salomon;
the narrowness of veil piercing and the distinction between concealment and evasion;
whether the doctrine after Prest is principled or merely residual;
the difference between piercing the veil and imposing direct liability on a parent company;
the significance of group structures, control, assumption of responsibility, and corporate reporting;
the relationship between company law reasoning and tort-based parent liability;
and whether the present law protects commercial certainty while still allowing justice in hard cases.

You should also address the counterargument that English law is not confused at all: it simply has one strict rule for veil piercing and a separate, ordinary law route for direct liability, especially in parent-subsidiary cases. Conclude with a reasoned view on whether the law is coherent, workable, and normatively defensible.
""",
        "topic": "company_personality_veil_lifting",
        "issue_terms": ["salomon", "prest", "parent-company", "assumption of responsibility"],
        "subquery_terms": ["salomon", "prest", "parent-company", "critical evaluation"],
    },
    {
        "label": "International Commercial Arbitration — Problem Question",
        "prompt": """International Commercial Arbitration — Problem Question

Word target: about 2,200 words

Atlas Energy Ltd, an English company, enters into a drilling-services contract with Meridian Drilling SA, a company incorporated in State X. The contract contains:

a London seat arbitration clause;
a provision that disputes are to be resolved under institutional arbitration rules;
and a clause stating that the tribunal may award “all remedies available under the governing law.”

A dispute arises after Meridian terminates the contract and withholds equipment. Atlas commences arbitration in London. Meridian argues that:

the arbitration clause does not cover Atlas’s fraud and bribery allegations because those are “non-contractual”;
one arbitrator should resign because of previous professional links to Atlas’s counsel;
and key evidence was excluded unfairly during the hearing.

The tribunal rejects Meridian’s jurisdiction objection, proceeds with the hearing, and makes a substantial award for Atlas, including lost profits and declaratory relief.

Meridian refuses to pay. It:

applies at the seat to set aside the award for excess of jurisdiction and serious procedural unfairness;
resists enforcement in State Y, where it has assets, on public policy grounds;
and argues that the tribunal effectively decided issues never properly submitted to it.

Atlas wants to enforce the award in multiple jurisdictions.

Advise the parties. In particular, consider:

the distinction between challenges at the seat and resistance to enforcement abroad;
jurisdictional objections and scope of the arbitration agreement;
apparent bias and arbitrator impartiality;
fair-hearing arguments;
public policy objections;
recognition and enforcement under the New York Convention;
and the practical significance of the difference between supervisory review and enforcement-stage review.
""",
        "topic": "international_commercial_arbitration",
        "issue_terms": ["seat", "jurisdictional objections", "public policy", "new york convention"],
        "subquery_terms": ["seat", "apparent bias", "public policy", "enforcement"],
    },
    {
        "label": "Constitutional / Devolution Law — Essay Question",
        "prompt": """Constitutional / Devolution Law — Essay Question

Word target: about 2,200 words

Critically evaluate whether devolution has transformed the United Kingdom constitution in substance, or whether it remains a legally limited and politically fragile qualification of parliamentary sovereignty.

In your answer, consider:

the legal basis of devolved power;
legislative competence and its limits;
Westminster’s continuing sovereignty;
the constitutional significance of conventions, especially where they concern legislative consent;
the role of courts in policing the boundaries of devolved authority;
intergovernmental conflict and constitutional friction;
and the extent to which legal remedies, judicial review, statutory interpretation, and constitutional principle can or cannot enforce the devolution settlement.

You should address the counterargument that devolution has not legally altered the core constitutional order because Parliament remains sovereign and conventions are not generally judicially enforceable, and you should conclude with a reasoned view on whether the present settlement is coherent, durable, and constitutionally legitimate.
""",
        "topic": "generic_devolution_law",
        "issue_terms": ["decentralisation", "sovereignty", "intergovernmental conflict", "coherence"],
        "subquery_terms": ["decentralisation", "sovereignty", "coherence"],
    },
]


def test_comprehensive_prompts_route_to_the_right_topics_and_surface_core_issue_terms():
    for case in COMPREHENSIVE_PROMPT_CASES:
        profile = _infer_retrieval_profile(case["prompt"])
        assert profile.get("topic") == case["topic"], (case["label"], profile.get("topic"))
        issue_blob = " || ".join(profile.get("issue_bank") or []).lower()
        for term in case["issue_terms"]:
            assert term.lower() in issue_blob, (case["label"], term)


def test_comprehensive_subissue_queries_surface_the_real_pressure_points():
    for case in COMPREHENSIVE_PROMPT_CASES:
        query_blob = " || ".join(
            label + " || " + guidance
            for label, guidance in _subissue_queries_for_unit(case["label"], case["prompt"])
        ).lower()
        for term in case["subquery_terms"]:
            assert term.lower() in query_blob, (case["label"], term)


def test_comment_derived_answer_quality_rules_remain_active():
    quality_gate = _build_legal_answer_quality_gate(
        "Essay Question: critically evaluate whether reform is justified and address cost objections.",
        {"topic": "general_legal"},
    )
    for line in [
        "Use measured register.",
        "Define acronyms and specialist shorthands on first use.",
        "do not claim it proved more than it actually established",
        "give the relevant comparator figures where available",
        "When introducing an authority, say briefly why it matters",
        "address that parity objection expressly",
    ]:
        assert line in quality_gate, line


def test_arbitration_prompts_now_surface_post_2025_english_law_pressure_points():
    arbitration_case = next(
        case for case in COMPREHENSIVE_PROMPT_CASES
        if case["topic"] == "international_commercial_arbitration"
    )
    profile = _infer_retrieval_profile(arbitration_case["prompt"])
    must_cover_blob = " || ".join(profile.get("must_cover") or []).lower()
    issue_blob = " || ".join(profile.get("issue_bank") or []).lower()
    query_blob = " || ".join(
        label + " || " + guidance
        for label, guidance in _subissue_queries_for_unit(arbitration_case["label"], arbitration_case["prompt"])
    ).lower()

    for term in [
        "arbitration act 2025",
        "section 70",
        "halliburton",
        "law governing the arbitration agreement",
        "summary disposal",
    ]:
        assert term in must_cover_blob, term

    for term in [
        "post-2025 section 67",
        "article v(1)(b)",
        "section 70 filter",
        "codified disclosure duty",
    ]:
        assert term in (issue_blob + " || " + query_blob), term


def test_user_supplied_2200_word_prompt_shapes_trigger_long_answer_detection():
    for case in COMPREHENSIVE_PROMPT_CASES:
        if "Word target: about 2,200 words" not in case["prompt"]:
            continue
        parsed = extract_word_targets_from_prompt(case["prompt"], min_words=300)
        assert parsed.get("active_targets") == [2200], case["label"]
        long_info = detect_long_essay(case["prompt"])
        assert long_info.get("requested_words") == 2200, case["label"]
        assert long_info.get("is_long_essay") is True, case["label"]
        assert long_info.get("suggested_parts", 0) >= 2, case["label"]


def test_mixed_2000_4000_5000_word_targets_preserve_prompt_routing():
    scenarios = [
        ("Private International Law — Problem Question", 2200, "private_international_law_post_brexit"),
        ("Public Procurement — Problem Question", 4000, "public_procurement_award_challenges"),
        ("Civil Procedure — Essay Question", 5000, "civil_procedure_justice_balance"),
        ("Constitutional / Devolution Law — Essay Question", 4000, "generic_devolution_law"),
    ]
    prompts_by_label = {case["label"]: case["prompt"] for case in COMPREHENSIVE_PROMPT_CASES}
    for label, requested_words, topic in scenarios:
        prompt = prompts_by_label[label].replace("2,200", f"{requested_words:,}")
        parsed = extract_word_targets_from_prompt(prompt, min_words=300)
        assert parsed.get("active_targets") == [requested_words], label
        profile = _infer_retrieval_profile(prompt)
        assert profile.get("topic") == topic, (label, profile.get("topic"))
        long_info = detect_long_essay(prompt)
        assert long_info.get("requested_words") == requested_words, label
        assert long_info.get("is_long_essay") is True, label
        assert long_info.get("suggested_parts", 0) >= 2, label
