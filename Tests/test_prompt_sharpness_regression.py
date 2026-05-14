"""
Regression checks for sharper legal-answer guidance and hearsay-specific precision.
"""

from model_applicable_service import (
    _build_legal_answer_quality_gate,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
)


def run() -> None:
    hearsay_prompt = (
        "1500 words\n"
        "Evidence Law — Essay Question\n"
        "Question:\n"
        "Critically evaluate whether the modern law on hearsay evidence in criminal "
        "proceedings strikes an appropriate balance between evidential flexibility and the "
        "defendant's right to a fair trial. In your answer, consider the reasons for the "
        "traditional exclusionary rule, the main statutory exceptions, the relationship "
        "between hearsay and Article 6 ECHR, judicial safeguards, and whether the present "
        "approach is principled and coherent."
    )
    profile = _infer_retrieval_profile(hearsay_prompt)
    assert profile.get("topic") == "criminal_evidence_hearsay"

    must_cover_blob = " || ".join(profile.get("must_cover") or []).lower()
    expected_blob = " || ".join(profile.get("expected_keywords") or []).lower()
    issue_blob = " || ".join(profile.get("issue_bank") or []).lower()
    subquery_blob = " || ".join(label for label, _ in _subissue_queries_for_unit("Evidence Law — Essay Question", hearsay_prompt)).lower()

    for term in [
        "section 114(2)",
        "schatschaschwili v germany",
        "good reason",
        "sole or decisive",
        "counterbalancing factors",
        "reliability",
    ]:
        assert term in (must_cover_blob + " || " + expected_blob), term

    assert "managed compromise" in issue_blob
    assert "single reliability test" in subquery_blob
    assert "article 6 sequence" in subquery_blob

    quality_gate = _build_legal_answer_quality_gate(
        "Problem Question: advise on liability, remedy, and likely outcome.",
        {"topic": "general_legal"},
    )
    for line in [
        "Rank the arguments.",
        "Separate doctrine from policy openly",
        "state the realistic remedy, forum, and practical litigation position",
        "do NOT append a bibliography, source list, web links, or 'primary sources checked' section",
        "convert it into a reusable drafting rule and sweep the whole answer for the same problem",
        "Do not retain or repeat document-specific confidential facts, names, quotations, or authority lists",
        "replace shorthand with explicit doctrine, comparator, mechanism, actor, and consequence",
        "run a final prompt-map sweep",
        "Remove vague referents.",
        "Use the available word budget on the hardest issues.",
        "Where a recent statute, commencement, or appellate reform materially changes the law",
        "Distinguish between points that are merely arguable",
        "identify which reform actually changes the analysis on these facts",
        "Use measured register.",
        "Define acronyms and specialist shorthands on first use.",
        "do not claim it proved more than it actually established",
        "give the relevant comparator figures where available",
        "When introducing an authority, say briefly why it matters",
        "address that parity objection expressly",
    ]:
        assert line in quality_gate, line

    with open("model_applicable_service.py", "r", encoding="utf-8") as fh:
        src = fh.read()
    assert "do NOT append a bibliography, source list, web links, or 'primary sources checked' section" in src
    assert "feedback abstraction and privacy rule is mandatory" in src.lower()
    assert "stronger hearsay essays explain that the 2003 Act mixes necessity" in src

    print("Prompt sharpness regression passed.")


if __name__ == "__main__":
    run()
