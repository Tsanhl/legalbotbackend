"""
Regression checks for exact user-style complete-answer prompt shapes that exposed
gaps during internal testing.
"""

from model_applicable_service import (
    _expand_sparse_unit_query,
    _extract_split_units,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
    detect_long_essay,
    extract_word_targets_from_prompt,
)


def run() -> None:
    multi_question_prompt = """Answer both questions. Write about 1,500 words for each answer.

Question 1 — Public Law / Judicial Review (Essay)

Critically evaluate whether the modern law of judicial review in England and Wales strikes an appropriate balance between legality, fairness, and democratic decision-making.

In your answer, consider:

illegality, irrationality, and procedural unfairness,
legitimate expectation,
proportionality,
the impact of the Human Rights Act 1998,
and whether the present law is principled or overly flexible.

Question 2 — Tort Law (Problem)

Northgate Council owns and manages a public leisure complex. Staff had repeatedly reported that:

a stairwell handrail was loose,
water regularly gathered on the tiled entrance floor during rain,
and one emergency exit door often failed to close properly.

During a busy evening event:

Leah slips on the wet entrance floor and fractures her wrist,
Adam falls against the loose handrail and suffers a head injury,
and an intruder enters through the faulty exit door and assaults a visitor, Priya.

The claimants seek advice. The Council argues that:

accidents sometimes happen even on well-run premises,
warnings were displayed near the entrance,
and the criminal assault by the intruder breaks the chain of causation.

Advise the parties. In particular, consider:

negligence,
occupiers’ liability,
breach of duty,
causation,
intervening acts,
and the likely remedies or damages issues."""

    parsed = extract_word_targets_from_prompt(multi_question_prompt, min_words=300)
    assert parsed["active_targets"] == [1500, 1500], parsed
    assert parsed["requested_words"] == 3000, parsed

    units = _extract_split_units(multi_question_prompt)
    assert len(units) == 2, units
    assert [str(u.get("kind") or "") for u in units] == ["essay", "problem"], units
    assert "Public Law / Judicial Review" in str(units[0].get("question_title") or ""), units[0]
    assert "Tort Law" in str(units[1].get("question_title") or ""), units[1]

    long_plan = detect_long_essay(multi_question_prompt)
    assert long_plan["is_long_essay"] is True, long_plan
    assert long_plan["split_mode"] == "by_section", long_plan
    deliverables = long_plan.get("deliverables") or []
    assert [int(d.get("target_words", 0) or 0) for d in deliverables] == [1500, 1500], deliverables

    state_responsibility_prompt = """Write a complete answer of about 4,500 words to the following public international law essay question:

Critically evaluate whether the modern law of state responsibility provides a coherent and effective framework for attributing wrongful conduct to states and determining the legal consequences of internationally wrongful acts.

In your answer, consider:

attribution,
breach of international obligation,
circumstances precluding wrongfulness,
causation and evidential difficulty,
reparation,
the role of countermeasures,
the relationship between primary and secondary rules,
and whether the law of state responsibility is principled, workable, and suited to modern international disputes."""

    state_profile = _infer_retrieval_profile(state_responsibility_prompt)
    assert state_profile.get("topic") == "public_international_law_state_responsibility_attribution", state_profile
    state_subqueries = [label for label, _ in _subissue_queries_for_unit("Essay", state_responsibility_prompt)]
    state_blob = " || ".join(state_subqueries).lower()
    assert "attribution of conduct and the architecture of secondary rules" in state_blob, state_subqueries
    assert "breach, excuses, and evidential difficulty" in state_blob, state_subqueries
    assert "reparation, countermeasures, and overall coherence" in state_blob, state_subqueries

    sparse_company_prompt = "Write a complete answer on company law."
    company_profile = _infer_retrieval_profile(sparse_company_prompt)
    assert company_profile.get("topic") == "company_directors_minorities", company_profile
    company_enriched = _expand_sparse_unit_query("Main", sparse_company_prompt).lower()
    assert "directors' duties under companies act 2006" in company_enriched, company_enriched
    assert "derivative claims" in company_enriched, company_enriched
    assert "unfair-prejudice" in company_enriched, company_enriched
    company_subqueries = [label for label, _ in _subissue_queries_for_unit("Essay", sparse_company_prompt)]
    company_blob = " || ".join(company_subqueries).lower()
    assert "directors' duties and the accountability claim" in company_blob, company_subqueries
    assert "enforcement architecture: ratification, derivative claims, and unfair prejudice" in company_blob, company_subqueries
    assert "do the duties ensure accountability?" in company_blob, company_subqueries

    print("User prompt-shape regression checks passed.")


if __name__ == "__main__":
    run()
