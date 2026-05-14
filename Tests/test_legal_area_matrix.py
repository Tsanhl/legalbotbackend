"""
Single-run regression matrix for the main legal subject areas and split/chunk routing.

This is a local planner/routing test only. It does NOT call the live Gemini API.
"""

from model_applicable_service import (
    QUERY_CHUNK_CONFIG,
    _extract_split_units,
    _chunk_count_for_query_type,
    _infer_retrieval_profile,
    _query_type_for_unit_kind,
    _resolve_long_response_info,
    _subissue_queries_for_unit,
    detect_long_essay,
)


AREA_CASES = [
    {
        "name": "Tort",
        "kind": "Problem Question",
        "expected_unit_kind": "problem",
        "prompt": """
4500 words
1. Tort – Problem Question (Negligence and Omissions)
Sofia, an off-duty nurse, witnesses a road collision and hesitates before assisting. A child suffers hypoxic brain injury. Advise on negligence, omissions, causation, and any gross-negligence-manslaughter issues.
""".strip(),
    },
    {
        "name": "Public Law / Human Rights",
        "kind": "Essay Question",
        "expected_unit_kind": "essay",
        "prompt": """
4500 words
1. Public Law / Human Rights – Essay Question (Article 8 and Proportionality)
“Article 8 ECHR protects a broad right to respect for private and family life, home and correspondence, but this right is qualified and may be restricted where necessary in a democratic society.” Discuss.
""".strip(),
    },
    {
        "name": "Contract",
        "kind": "Problem Question",
        "expected_unit_kind": "problem",
        "prompt": """
4500 words
1. Contract – Problem Question (Misrepresentation and Frustration)
Advise the parties on whether the contract was induced by misrepresentation, whether frustration applies after a supervening event, and what remedies are available.
""".strip(),
    },
    {
        "name": "Equity / Land",
        "kind": "Problem Question",
        "expected_unit_kind": "problem",
        "prompt": """
4500 words
1. Equity / Land – Problem Question (Common Intention Constructive Trusts: Cohabitation)
Alex and Jamie dispute beneficial ownership of 12 Oak Road after years of cohabitation, renovations, bill-sharing, and caring responsibilities. Advise Jamie.
""".strip(),
    },
    {
        "name": "Criminal Law",
        "kind": "Problem Question",
        "expected_unit_kind": "problem",
        "prompt": """
4500 words
1. Criminal Law – Problem Question (Omissions and Self-Defence)
Advise on possible liability for omissions, gross negligence manslaughter, and whether self-defence or loss of control may arise on the facts.
""".strip(),
    },
    {
        "name": "Criminal Evidence",
        "kind": "Essay Question",
        "expected_unit_kind": "essay",
        "prompt": """
4500 words
1. Criminal Evidence – Essay Question (Hearsay)
“The modern statutory scheme on hearsay in criminal proceedings has moved from a rigid exclusionary rule with narrow exceptions to a more flexible admissibility regime based on necessity and safeguards.” Discuss.
""".strip(),
    },
    {
        "name": "EU Law",
        "kind": "Problem Question",
        "expected_unit_kind": "problem",
        "prompt": """
4500 words
1. EU Law – Problem Question (Free Movement of Workers and Residence Rights)
Advise whether Luca remains a worker or retained worker after involuntary unemployment, and whether the host state may lawfully remove him.
""".strip(),
    },
    {
        "name": "Data Protection",
        "kind": "Essay Question",
        "expected_unit_kind": "essay",
        "prompt": """
4500 words
1. Data Protection – Essay Question (Legitimate Interests)
“Legitimate interests under the GDPR has become a flexible lawful basis that risks operating as a catch-all ground for data processing.” Discuss.
""".strip(),
    },
    {
        "name": "Medical Law",
        "kind": "Problem Question",
        "expected_unit_kind": "problem",
        "prompt": """
4500 words
1. Medical Law – Problem Question (Consent and Capacity)
Advise Dr Khan on consent, material-risk disclosure, capacity, and emergency treatment without consent in relation to two patients.
""".strip(),
    },
    {
        "name": "International Commercial Arbitration",
        "kind": "Essay Question",
        "expected_unit_kind": "essay",
        "prompt": """
4500 words
1. International Commercial Arbitration – Essay Question
“Party autonomy is often described as the cornerstone of international commercial arbitration, yet in practice it operates within a framework of mandatory rules imposed by the law of the seat and by international public policy.” Discuss.
""".strip(),
    },
    {
        "name": "Private International Law",
        "kind": "Problem Question",
        "expected_unit_kind": "problem",
        "prompt": """
4500 words
1. Private International Law – Problem Question (Jurisdiction, Choice of Law, Forum)
Advise whether the English court has jurisdiction, whether there should be a stay on forum non conveniens grounds, and what law governs the contractual and tortious claims.
""".strip(),
    },
]


CHUNK_EXPECTATIONS = [
    ("problem", 900, "pb", 10),
    ("problem", 1000, "pb_1500", 15),
    ("problem", 1500, "pb_1500", 15),
    ("problem", 2000, "pb_2000_plus", 20),
    ("problem", 2250, "pb_2000_plus", 20),
    ("essay", 900, "essay", 10),
    ("essay", 1000, "essay_1500", 15),
    ("essay", 1500, "essay_1500", 15),
    ("essay", 2000, "essay_2000_plus", 20),
    ("essay", 2250, "essay_2000_plus", 20),
]


def _assert_single_area_split() -> None:
    print("=" * 80)
    print("AREA SPLIT MATRIX")
    print("=" * 80)
    for case in AREA_CASES:
        result = detect_long_essay(case["prompt"])
        deliverables = result.get("deliverables") or []
        total = sum(int(d.get("target_words") or 0) for d in deliverables)
        kinds = {d.get("unit_kind") for d in deliverables}

        print(f"\n[{case['name']}]")
        print("kind:", case["kind"])
        print("requested_words:", result.get("requested_words"))
        print("deliverables:", len(deliverables))
        print("unit_kinds:", sorted(kinds))
        print("target_total:", total)

        assert result.get("requested_words") == 4500
        assert result.get("is_long_essay") is True
        assert len(deliverables) >= 2
        assert total == 4500
        assert kinds == {case["expected_unit_kind"]}


def _assert_mixed_two_question_split() -> None:
    prompt = """
4500 words
1. Equity / Land – Problem Question (Common Intention Constructive Trusts: Cohabitation)
Alex and Jamie dispute beneficial ownership after cohabitation, renovations, bill-sharing, and caring responsibilities.

2. Criminal Evidence – Essay Question (Hearsay)
“The modern statutory scheme on hearsay in criminal proceedings has moved from a rigid exclusionary rule with narrow exceptions to a more flexible admissibility regime based on necessity and safeguards.” Discuss.
""".strip()
    result = detect_long_essay(prompt)
    deliverables = result.get("deliverables") or []

    print("\n" + "=" * 80)
    print("MIXED QUESTION SPLIT")
    print("=" * 80)
    for d in deliverables:
        print(
            {
                "target_words": d.get("target_words"),
                "question_index": d.get("question_index"),
                "starting_question_index": d.get("starting_question_index"),
                "ending_question_index": d.get("ending_question_index"),
                "unit_kind": d.get("unit_kind"),
                "question_indices": d.get("question_indices"),
            }
        )

    assert len(deliverables) == 4
    assert [d.get("target_words") for d in deliverables] == [1125, 1125, 1125, 1125]
    assert deliverables[0].get("question_indices") == [1]
    assert deliverables[1].get("question_indices") == [1]
    assert deliverables[2].get("question_indices") == [2]
    assert deliverables[3].get("question_indices") == [2]
    assert deliverables[0].get("starting_question_index") == 1
    assert deliverables[1].get("starting_question_index") == 1
    assert deliverables[1].get("ending_question_index") == 1
    assert deliverables[2].get("starting_question_index") == 2
    assert all(len(d.get("question_indices") or []) == 1 for d in deliverables)
    assert all(d.get("unit_kind") in {"problem", "essay"} for d in deliverables)


def _assert_question_heading_mixed_format_split() -> None:
    prompt = """
4500 words
1. Essay / discussion question

Question 1: Constitutional and Rule of Law Essay

Critically evaluate whether the modern constitutional order in the United Kingdom provides sufficient protection against the arbitrary exercise of public power.

2. Problem question

Question 2: Public Law / Judicial Review Problem Question

Advise the parties on any potential public law claims they may bring.
""".strip()
    units = _extract_split_units(prompt)
    result = detect_long_essay(prompt)
    deliverables = result.get("deliverables") or []

    print("\n" + "=" * 80)
    print("QUESTION-HEADING MIXED FORMAT")
    print("=" * 80)
    print("units:", units)
    for d in deliverables:
        print(
            {
                "question_index": d.get("question_index"),
                "unit_kind": d.get("unit_kind"),
                "question_titles": d.get("question_titles"),
                "target_words": d.get("target_words"),
            }
        )

    assert len(units) == 2
    assert [u.get("kind") for u in units] == ["essay", "problem"]
    assert units[0].get("question_title") == "Constitutional and Rule of Law Essay"
    assert units[1].get("question_title") == "Public Law / Judicial Review Problem Question"
    assert len(deliverables) == 4
    assert [d.get("unit_kind") for d in deliverables] == ["essay", "essay", "problem", "problem"]


def _assert_direct_code_vs_website_split_policy() -> None:
    prompt = "using the rag + current code generate a 4500 words answer on constitutional law"
    direct = _resolve_long_response_info(prompt, enforce_long_response_split=False)
    website = _resolve_long_response_info(prompt, enforce_long_response_split=True)

    print("\n" + "=" * 80)
    print("DIRECT VS WEBSITE SPLIT POLICY")
    print("=" * 80)
    print("direct:", direct)
    print("website:", website)

    assert direct.get("requested_words") == 4500
    assert direct.get("is_long_essay") is False
    assert direct.get("suggested_parts") == 0
    assert direct.get("split_disabled_for_direct_use") is True

    assert website.get("requested_words") == 4500
    assert website.get("is_long_essay") is True
    assert int(website.get("suggested_parts") or 0) >= 3


def _assert_criminal_mens_rea_topic_routing() -> None:
    prompt = """
4500 words
1. Criminal Law – Intention, Recklessness, and Moral Blameworthiness
Critically evaluate whether the current approach to mens rea in English criminal law achieves fair and principled outcomes.

In your answer, analyse direct and oblique intent, Woollin, Cunningham, Caldwell, R v G,
foresight of consequences, transferred malice, and whether reform is necessary.
""".strip()
    profile = _infer_retrieval_profile(prompt)

    print("\n" + "=" * 80)
    print("CRIMINAL MENS REA ROUTING")
    print("=" * 80)
    print(profile)

    assert profile.get("topic") == "criminal_mens_rea_intention_recklessness"
    must_cover = profile.get("must_cover") or []
    assert "R v Woollin" in must_cover
    assert "R v Cunningham" in must_cover
    assert "R v G" in must_cover
    assert "R v Latimer" in must_cover
    assert "Theft Act 1968" not in must_cover


def _assert_targeted_prompt_profiles_and_fanout() -> None:
    tort_prompt = """
2000 words
1. Essay question — Tort Law
Question: Tort Law – Negligence, Duty of Care, and Incremental Development
Critically evaluate whether the modern English law of negligence takes a coherent and principled approach to the existence and scope of a duty of care.

In your answer, discuss:

the significance of the neighbour principle,

the development from Donoghue v Stevenson to Anns and the retreat from Anns,

the role of the Caparo criteria,

the modern preference for incremental development by analogy,

the treatment of omissions, pure economic loss, and psychiatric harm,

the relationship between policy concerns and doctrinal principle,

whether the law draws convincing boundaries around liability,

and whether the current law promotes fairness, certainty, and corrective justice.
""".strip()
    land_prompt = """
2000 words
2. Problem question — Land Law
Question: Land Law – Co-ownership, Trusts of Land, Proprietary Estoppel, and Third-Party Rights
Amira and Joseph buy Maple House in Joseph's sole name. Joseph tells Amira that half of it is really hers.

After moving in:
Amira pays for renovations and contributes informally to mortgage payments.
Elias later moves into the garage conversion, spends money adapting it for disability needs, and Joseph says the place will always be here for family.

Joseph grants a registered charge to Rapid Finance Ltd without telling Amira or Elias. Leila later claims sole ownership and seeks sale and possession.

Advise the parties. In particular, consider:
whether Amira has acquired a beneficial interest under a resulting or constructive trust,
whether Amira may alternatively claim proprietary estoppel,
whether Elias has any rights arising from proprietary estoppel or otherwise,
whether any interests are capable of overriding Rapid Finance Ltd’s charge,
the relevance of actual occupation,
and what remedies a court might grant.
""".strip()
    public_law_prompt = """
2000 words
1. Essay Question — Public Law
Question: Judicial Review, Deference, and the Role of the Courts
Critically evaluate whether the courts in England and Wales strike an appropriate balance between judicial scrutiny and respect for democratic decision-making in judicial review.

In your answer, discuss:

the constitutional foundations of judicial review,
the relationship between the rule of law and parliamentary sovereignty,
the development and application of the grounds of review (illegality, irrationality, procedural impropriety),
the emergence of proportionality and its relationship with traditional grounds,
the intensity of review in different contexts (e.g. national security, economic policy, fundamental rights),
the concept of judicial deference (or “respect”) and when it is justified,
the impact of the Human Rights Act 1998,
and recent tensions between the judiciary and the executive.
""".strip()
    company_prompt = """
2000 words
2. Problem Question — Company Law
Question: Company Law – Directors’ Duties, Shareholder Remedies, and Corporate Governance
TechNova Ltd has Arjun, Lina, and Marcus on the board. Arjun enters an above-market deal with a company secretly owned by his spouse. Lina ignores reporting irregularities. Marcus rarely attends meetings and says he relied on the executive directors.

Dev, a 10% shareholder, wants advice. In particular, consider:
Whether Arjun, Lina, and Marcus have breached their duties under the Companies Act 2006 (including duties relating to conflicts of interest, care, skill and diligence, and promoting the success of the company)
Whether TechNova Ltd itself can take action
Whether Dev can bring a derivative claim, and the requirements for doing so
Whether Dev has an alternative remedy under unfair prejudice
The role of shareholder approval or ratification
Any potential defences available to the directors
""".strip()

    tort_profile = _infer_retrieval_profile(tort_prompt)
    land_profile = _infer_retrieval_profile(land_prompt)
    public_profile = _infer_retrieval_profile(public_law_prompt)
    company_profile = _infer_retrieval_profile(company_prompt)

    tort_subqueries = [label for label, _ in _subissue_queries_for_unit("Essay Question — Tort Law", tort_prompt)]
    land_subqueries = [label for label, _ in _subissue_queries_for_unit("Problem Question — Land Law", land_prompt)]
    company_subqueries = [label for label, _ in _subissue_queries_for_unit("Problem Question — Company Law", company_prompt)]

    print("\n" + "=" * 80)
    print("TARGETED PROMPT ROUTING / FANOUT")
    print("=" * 80)
    print("tort:", tort_profile.get("topic"), tort_profile.get("prompt_map_asks"), tort_subqueries)
    print("land:", land_profile.get("topic"), land_profile.get("prompt_map_asks"), land_subqueries)
    print("public:", public_profile.get("topic"), public_profile.get("prompt_map_asks"))
    print("company:", company_profile.get("topic"), company_profile.get("prompt_map_asks"), company_subqueries)

    assert tort_profile.get("topic") == "tort_duty_of_care_framework"
    assert "the significance of the neighbour principle" in (tort_profile.get("prompt_map_asks") or [])
    assert "From neighbour principle to Caparo and Robinson" in tort_subqueries

    assert land_profile.get("topic") == "land_home_coownership_estoppel_priority"
    assert any("actual occupation" in ask.lower() for ask in (land_profile.get("prompt_map_asks") or []))
    assert land_subqueries[0] == "Acquisition of beneficial interests"

    assert public_profile.get("topic") == "public_law_judicial_review_deference"
    assert "the constitutional foundations of judicial review" in (public_profile.get("prompt_map_asks") or [])
    assert any("judicial deference" in ask.lower() for ask in (public_profile.get("prompt_map_asks") or []))

    assert company_profile.get("topic") == "company_directors_minorities"
    must_cover = company_profile.get("must_cover") or []
    assert not any("Marcus have breached" in item for item in must_cover)
    assert company_subqueries[0] == "Conflicted director: disclosure and loyalty duties"


def _assert_critical_shape_guidance_and_fanout() -> None:
    criminal_essay = """
1500 words
1. Criminal Law — Essay Question
Critically evaluate whether the law on self-defence in English criminal law strikes the right balance between protecting victims and preventing excessive private violence.
In your answer, consider necessity, reasonableness, mistaken belief, proportionality, householder cases, and whether the current law is coherent and fair.
""".strip()
    contract_problem = """
1500 words
2. Contract Law — Problem Question
Nova Furnishings Ltd agrees to buy 200 custom office desks from CraftBuild Ltd. CraftBuild says the desks will be made from premium oak suitable for heavy commercial use. The written contract excludes liability for representations not contained in the agreement. The desks arrive late and many warp within a month.
Advise on whether the statement is a term or representation, breach, misrepresentation, the effect of the clause, and remedies.
""".strip()
    tort_essay = """
1500 words
3. Tort Law — Essay Question
Critically evaluate whether the modern law of negligence takes a coherent approach to pure economic loss.
Discuss the exclusionary rule, negligent misstatement, assumption of responsibility, indeterminate liability, and whether the distinctions are principled or artificial.
""".strip()
    public_problem = """
1500 words
4. Public Law — Problem Question
The Minister for Transport announces that a subsidy scheme for rural bus services will remain in place for at least the next three years. Local councils rely on the promise. One year later the Minister withdraws the scheme without consultation because of budget pressure.
Advise on judicial review, legitimate expectation, consultation, other grounds, and remedies.
""".strip()
    land_problem = """
1500 words
5. Land Law / Equity — Problem Question
Sofia and Daniel are an unmarried couple. Daniel buys a house in his sole name but tells Sofia that half of it is hers. Sofia spends £30,000 on renovations and pays household expenses. The relationship ends and Daniel denies she has any interest.
Advise on common intention constructive trust, proprietary estoppel, the significance of the assurance and contributions, and remedies.
""".strip()
    medical_problem = """
1500 words
6. Medical Law — Problem Question
Advise on material risk disclosure, Montgomery, emergency treatment without consent, whether the patient lacks capacity, and the Mental Capacity Act 2005.
""".strip()

    criminal_profile = _infer_retrieval_profile(criminal_essay)
    contract_profile = _infer_retrieval_profile(contract_problem)
    tort_profile = _infer_retrieval_profile(tort_essay)
    public_profile = _infer_retrieval_profile(public_problem)
    land_profile = _infer_retrieval_profile(land_problem)
    medical_profile = _infer_retrieval_profile(medical_problem)

    criminal_subqueries = [label for label, _ in _subissue_queries_for_unit("Essay Question — Criminal Law", criminal_essay)]
    contract_subqueries = [label for label, _ in _subissue_queries_for_unit("Problem Question — Contract Law", contract_problem)]
    tort_subqueries = [label for label, _ in _subissue_queries_for_unit("Essay Question — Tort Law", tort_essay)]
    public_subqueries = [label for label, _ in _subissue_queries_for_unit("Problem Question — Public Law", public_problem)]
    land_subqueries = [label for label, _ in _subissue_queries_for_unit("Problem Question — Land Law", land_problem)]
    medical_subqueries = [label for label, _ in _subissue_queries_for_unit("Problem Question — Medical Law", medical_problem)]

    print("\n" + "=" * 80)
    print("CRITICAL SHAPE / FANOUT")
    print("=" * 80)
    print("criminal:", criminal_profile.get("topic"), criminal_subqueries)
    print("contract:", contract_profile.get("topic"), contract_subqueries)
    print("tort:", tort_profile.get("topic"), tort_subqueries)
    print("public:", public_profile.get("topic"), public_subqueries)
    print("land:", land_profile.get("topic"), land_subqueries)
    print("medical:", medical_profile.get("topic"), medical_subqueries)

    assert criminal_profile.get("topic") == "criminal_nonfatal_offences_self_defence"
    assert "Householder cases and the grossly disproportionate test" in criminal_subqueries
    assert criminal_subqueries[0] == "Necessity, mistaken belief, and the defender's perspective"

    assert contract_profile.get("topic") == "contract_misrepresentation_exclusion"
    assert contract_subqueries[0] == "Statement classification: term, collateral warranty, or representation"
    assert "Remedies: damages, rejection, rescission, and consequential loss" in contract_subqueries

    assert tort_profile.get("topic") == "tort_economic_loss_negligent_misstatement"
    assert tort_subqueries[0] == "The exclusionary rule and indeterminate-liability policy"
    assert "Junior Books, White v Jones, and the charge of artificial distinctions" in tort_subqueries

    assert public_profile.get("topic") == "public_law_legitimate_expectation"
    assert public_subqueries[0] == "Amenability, standing, and promise quality"
    assert "Budget pressure, public interest, and remedies" in public_subqueries

    assert land_profile.get("topic") == "land_home_coownership_estoppel_priority"
    assert land_subqueries[0] == "Beneficial interest: resulting trust weakness and common-intention constructive trust"
    assert "Quantification and practical remedies" in land_subqueries

    assert medical_profile.get("topic") == "medical_consent_capacity"
    assert medical_subqueries[0] == "Valid consent and material risk disclosure"
    assert "Capacity under the Mental Capacity Act 2005" in medical_subqueries


def _assert_chunk_routing() -> None:
    print("\n" + "=" * 80)
    print("CHUNK ROUTING")
    print("=" * 80)
    for unit_kind, words, expected_type, expected_chunks in CHUNK_EXPECTATIONS:
        qtype = _query_type_for_unit_kind(unit_kind, words)
        chunks = _chunk_count_for_query_type(qtype, words)
        print(unit_kind, words, "->", qtype, chunks)
        assert qtype == expected_type
        assert chunks == expected_chunks

    print("\nSpecial routes:")
    print("advice_mode_c ->", QUERY_CHUNK_CONFIG["advice_mode_c"])
    print("sqe1_notes ->", QUERY_CHUNK_CONFIG["sqe1_notes"])
    print("sqe2_notes ->", QUERY_CHUNK_CONFIG["sqe2_notes"])
    print("sqe_topic ->", QUERY_CHUNK_CONFIG["sqe_topic"])
    print("para_improvements_10k ->", QUERY_CHUNK_CONFIG["para_improvements_10k"])
    print("para_improvements_15k ->", QUERY_CHUNK_CONFIG["para_improvements_15k"])

    assert QUERY_CHUNK_CONFIG["advice_mode_c"] == 15
    assert QUERY_CHUNK_CONFIG["sqe1_notes"] == 20
    assert QUERY_CHUNK_CONFIG["sqe2_notes"] == 20
    assert QUERY_CHUNK_CONFIG["sqe_topic"] == 20
    assert QUERY_CHUNK_CONFIG["para_improvements_10k"] == 25
    assert QUERY_CHUNK_CONFIG["para_improvements_15k"] == 25


def _assert_balanced_multi_count_split() -> None:
    print("\n" + "=" * 80)
    print("MULTI-COUNT BALANCE")
    print("=" * 80)
    base = """
1. Family Law – Problem Question
Amira and Tom dispute child arrangements and a proposed internal relocation.

2. International Humanitarian Law – Essay Question
Discuss targeting, distinction, proportionality, and precautions in attack.
""".strip()
    for total_words, expected_targets in [
        (3000, [1500, 1500]),
        (5000, [1250, 1250, 1250, 1250]),
        (7000, [1750, 1750, 1750, 1750]),
        (8000, [2000, 2000, 2000, 2000]),
    ]:
        result = detect_long_essay(f"{total_words} words\n{base}")
        deliverables = result.get("deliverables") or []
        targets = [int(d.get("target_words") or 0) for d in deliverables]
        qs = [d.get("question_indices") for d in deliverables]
        print(total_words, targets, qs)
        assert targets == expected_targets
        assert all(len(q or []) == 1 for q in qs)
        first_half = targets[: len(targets) // 2]
        second_half = targets[len(targets) // 2 :]
        assert sum(first_half) == total_words // 2
        assert sum(second_half) == total_words - (total_words // 2)


def run() -> None:
    _assert_single_area_split()
    _assert_mixed_two_question_split()
    _assert_question_heading_mixed_format_split()
    _assert_direct_code_vs_website_split_policy()
    _assert_criminal_mens_rea_topic_routing()
    _assert_targeted_prompt_profiles_and_fanout()
    _assert_critical_shape_guidance_and_fanout()
    _assert_chunk_routing()
    _assert_balanced_multi_count_split()
    print("\nAll legal area and split/chunk routing checks passed.")


if __name__ == "__main__":
    run()
