"""
Regression checks for the user's latest output-quality feedback on:
1. registered-land essays; and
2. equity/tracing problem answers.
"""

from model_applicable_service import (
    _build_legal_answer_quality_gate,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
)


LAND_PROMPT = """Write a complete answer of about 2,000 words to the following essay question:

Critically evaluate whether the system of registered land in England and Wales strikes an appropriate balance between certainty of title and the protection of informal rights.

In your answer, consider:

the aims of registration,
the mirror principle, curtain principle, and insurance principle,
overriding interests,
actual occupation,
the position of purchasers and third parties,
and whether the current system is coherent, fair, and effective."""


TRUSTS_PROMPT = """Write a complete answer of about 2,500 words to the following equity and trusts problem question. Advise the parties.

Aisha transfers £300,000 to her brother Karim, telling him to “hold it for the family until I decide what should be done with it.” Karim places:

£120,000 into his personal trading account,
£80,000 into a mixed account already containing his own money,
£50,000 towards repayment of his mortgage,
and uses the remaining £50,000 to buy shares, which later increase significantly in value.

Karim then becomes insolvent. Before insolvency:

he paid £20,000 from the mixed account to his friend Nadia in repayment of a personal debt,
and gifted £15,000 from the same account to his son.

Aisha says a trust was created and wants to recover as much as possible. Karim says the words used were too vague to create a trust and that, in any event, the funds can no longer be identified clearly.

Advise the parties. In particular, consider:

certainty of intention, subject matter, and objects,
whether a trust was created,
breach of trust,
following and tracing at common law and in equity,
mixed funds,
claims against Karim and third parties,
proprietary and personal remedies,
insolvency implications,
and the likely practical outcome."""


def run() -> None:
    land_profile = _infer_retrieval_profile(LAND_PROMPT)
    assert land_profile.get("topic") == "land_registered_overriding_interests", land_profile
    land_issue_blob = " || ".join(land_profile.get("issue_bank") or []).lower()
    assert "notices, restrictions, overreaching, rectification, and indemnity" in land_issue_blob, land_issue_blob
    assert "inspection costs, conveyancing risk, intermittent occupation" in land_issue_blob, land_issue_blob

    land_gate = _build_legal_answer_quality_gate(LAND_PROMPT, land_profile).lower()
    assert "broaden the essay beyond actual occupation alone" in land_gate, land_gate
    assert "inspection and inquiry costs" in land_gate, land_gate
    assert "fact-sensitive off-register doctrines" in land_gate, land_gate

    land_subqueries = _subissue_queries_for_unit("Land", LAND_PROMPT)
    land_query_blob = " || ".join(text.lower() for _, text in land_subqueries)
    assert "notices and restrictions" in land_query_blob, land_query_blob
    assert "rectification/indemnity" in land_query_blob, land_query_blob
    assert "conveyancing risk" in land_query_blob, land_query_blob

    trusts_profile = _infer_retrieval_profile(TRUSTS_PROMPT)
    assert trusts_profile.get("topic") == "equity_trust_creation_tracing", trusts_profile
    trusts_issue_blob = " || ".join(trusts_profile.get("issue_bank") or []).lower()
    assert "incomplete disposition" in trusts_issue_blob, trusts_issue_blob
    assert "run the answer asset by asset" in trusts_issue_blob, trusts_issue_blob
    assert "lowest intermediate balance" in trusts_issue_blob, trusts_issue_blob

    trusts_gate = _build_legal_answer_quality_gate(TRUSTS_PROMPT, trusts_profile).lower()
    assert "subrogation to the discharged security is not identical to lien-style recognition of value fed into the property" in trusts_gate, trusts_gate
    assert "a repayment recipient who takes for value stands differently from a volunteer donee" in trusts_gate, trusts_gate
    assert "prioritise the appreciating shares and the property-based claim" in trusts_gate, trusts_gate

    trusts_subqueries = _subissue_queries_for_unit("Trusts", TRUSTS_PROMPT)
    trusts_query_blob = " || ".join(text.lower() for _, text in trusts_subqueries)
    assert "incomplete beneficial disposition may be the real difficulty" in trusts_query_blob, trusts_query_blob
    assert "lowest intermediate balance" in trusts_query_blob, trusts_query_blob
    assert "subrogation to the discharged mortgagee's security" in trusts_query_blob, trusts_query_blob
    assert "value versus volunteer status" in trusts_query_blob, trusts_query_blob

    print("Land/trusts feedback-guidance regression passed.")


if __name__ == "__main__":
    run()
