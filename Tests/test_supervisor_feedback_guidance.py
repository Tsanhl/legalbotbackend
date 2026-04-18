from model_applicable_service import (
    _build_legal_answer_quality_gate,
    _infer_retrieval_profile,
)


contract_prompt = """Contract Law — Problem Question

Advise the claimant in a misrepresentation and exclusion-clause dispute.

In particular, consider:

whether pre-contract statements are terms or representations,
how non-reliance and exclusion clauses should be analysed,
whether consequential-loss wording is narrow or widened by extra drafting,
how lost commercial opportunities should be analysed,
and which remedies are realistically strongest."""

contract_profile = _infer_retrieval_profile(contract_prompt)
assert contract_profile["topic"] == "contract_misrepresentation_exclusion"
contract_gate = _build_legal_answer_quality_gate(contract_prompt, contract_profile).lower()
assert "term or collateral-warranty argument hard" in contract_gate
assert "lost opportunities or similar commercial expectancy loss" in contract_gate
assert "separate remoteness from causation/proof" in contract_gate
assert "whole contract price or fee" in contract_gate
assert "rank routes expressly as primary, fallback, or weak/theoretical" in contract_gate
assert "multiple limbs, exceptions, disqualifiers, or provisos" in contract_gate
assert "several distinct statements, interests, rights, options, claims, or remedies" in contract_gate
assert "if the facts are materially silent or ambiguous" in contract_gate


public_law_prompt = """Public Law — Essay Question

Critically evaluate whether judicial review is constitutionally legitimate.

In your answer, consider:

the constitutional foundations of judicial review,
irrationality and proportionality,
legitimate expectation,
judicial restraint or deference,
and whether the law is coherent."""

public_profile = _infer_retrieval_profile(public_law_prompt)
assert public_profile["topic"] == "public_law_judicial_review_deference"
public_gate = _build_legal_answer_quality_gate(public_law_prompt, public_profile).lower()
assert "legislative intention/ultra vires, common-law constitutional principle, or a mixed account" in public_gate
assert "proportionality has displaced wednesbury in substance" in public_gate
assert "institutional competence, democratic legitimacy, evidential advantage, and constitutional role" in public_gate
assert "state a sharper thesis early" in public_gate
assert "integrate named academic disagreement or deeper constitutional/jurisprudential theory" in public_gate
assert "after discussing a case line or doctrinal sequence" in public_gate


pensions_prompt = """Pensions Law — Problem Question

Advise on an occupational pension scheme amendment and trustee decision.

In particular, consider:

scheme wording,
member rights,
trustee duties,
consultation,
and remedies."""

pensions_profile = _infer_retrieval_profile(pensions_prompt)
assert pensions_profile["topic"] == "pensions_scheme_change_misrepresentation"
assert any("scheme wording first" in item.lower() for item in pensions_profile["issue_bank"])
assert any(
    "legislation uses similar language" in item.lower()
    for item in pensions_profile["must_avoid"]
)
pensions_gate = _build_legal_answer_quality_gate(pensions_prompt, pensions_profile).lower()
assert "do not assume that a pensions term means the same thing in the scheme rules merely because legislation uses similar language" in pensions_gate
assert "rectification or declaration issues" in pensions_gate
assert "distinguish subsisting rights, employer communication, trustee process, and remedial proof" in pensions_gate

print("General supervisor-feedback guidance regression passed.")
