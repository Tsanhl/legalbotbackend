"""
Test script for the two new features:
1. detect_specific_para_improvement
2. should_use_google_search_grounding
"""

# Import the functions from the canonical backend service module
from model_applicable_service import (
    detect_specific_para_improvement,
    should_use_google_search_grounding,
    extract_word_targets_from_prompt,
    _infer_retrieval_profile,
    _build_legal_answer_quality_gate,
    _extract_units_with_text,
    _profile_local_index_coverage,
)
from backend_answer_runtime import _essay_quality_issues

print("=" * 80)
print("TESTING FEATURE 1: Specific Paragraph Improvement Detection")
print("=" * 80)

# Test Case 1: Which paragraphs can be improved
test1 = "Can you tell me which paragraphs in my essay need improvement?"
result1 = detect_specific_para_improvement(test1)
print(f"\nTest 1: '{test1}'")
print(f"Result: {result1}")
assert result1['is_para_improvement'] == True
assert result1['improvement_type'] == 'specific_paras'
print("✅ PASSED")

# Test Case 2: Improve whole essay
test2 = "Improve my entire essay"
result2 = detect_specific_para_improvement(test2)
print(f"\nTest 2: '{test2}'")
print(f"Result: {result2}")
assert result2['is_para_improvement'] == True
assert result2['improvement_type'] == 'whole_essay'
print("✅ PASSED")

# Test Case 3: Improve specific paragraphs
test3 = "improve para 2 and para 4"
result3 = detect_specific_para_improvement(test3)
print(f"\nTest 3: '{test3}'")
print(f"Result: {result3}")
assert result3['is_para_improvement'] == True
assert result3['improvement_type'] == 'specific_paras'
assert 'para 2' in result3['which_paras']
assert 'para 4' in result3['which_paras']
print("✅ PASSED")

# Test Case 4: Not a paragraph improvement request
test4 = "Write an essay on contract law"
result4 = detect_specific_para_improvement(test4)
print(f"\nTest 4: '{test4}'")
print(f"Result: {result4}")
assert result4['is_para_improvement'] == False
print("✅ PASSED")

print("\n" + "=" * 80)
print("TESTING FEATURE 2: Google Search Grounding Detection")
print("=" * 80)

# Test Case 5: Essay request (should trigger Google Search)
test5 = "Write a 3000 word essay on AI regulation"
result5 = should_use_google_search_grounding(test5, rag_context="Some context")
print(f"\nTest 5: '{test5}'")
print(f"Result: {result5}")
assert result5['use_google_search'] == True
assert result5['enforce_oscola'] == True
print("✅ PASSED")

# Test Case 6: Recent case request
test6 = "What are the recent cases on data protection in 2025?"
result6 = should_use_google_search_grounding(test6, rag_context="Some context")
print(f"\nTest 6: '{test6}'")
print(f"Result: {result6}")
assert result6['use_google_search'] == True
print("✅ PASSED")

# Test Case 7: Insufficient RAG context
test7 = "What is vicarious liability?"
result7 = should_use_google_search_grounding(test7, rag_context="")  # Empty RAG
print(f"\nTest 7: '{test7}' (with empty RAG context)")
print(f"Result: {result7}")
assert result7['use_google_search'] == True
assert result7['reason'] == 'RAG context insufficient'
print("✅ PASSED")

# Test Case 8: RAG context sufficient + no special indicators
test8 = "What is the definition of consideration?"
long_rag = "This is sufficient RAG context. " * 50  # Make it > 500 chars
result8 = should_use_google_search_grounding(test8, rag_context=long_rag)
print(f"\nTest 8: '{test8}' (with sufficient RAG context)")
print(f"Result: {result8}")
assert result8['use_google_search'] == False  # Should not trigger
print("✅ PASSED")

print("\n" + "=" * 80)
print("TESTING FEATURE 3: Canonical Word Target Parser")
print("=" * 80)

# Test Case 9: Mixed transcript (historical 4500 + latest 2000) should resolve latest active request
test9 = """
test
4500 words
QUESTION 1 ...
part 1 ...
Will Continue to next part, say continue

test again
2000 words
QUESTION 2 ...
"""
parsed9 = extract_word_targets_from_prompt(test9, min_words=300)
print(f"\nTest 9 active targets: {parsed9['active_targets']}, used_latest_segment={parsed9['used_latest_segment']}")
assert parsed9["active_targets"] == [2000]
assert parsed9["used_latest_segment"] is True
print("✅ PASSED")

# Test Case 10: True multi-question prompt keeps left-to-right targets
test10 = """
QUESTION 1
3000 words
QUESTION 2
2000 words
"""
parsed10 = extract_word_targets_from_prompt(test10, min_words=300)
print(f"\nTest 10 active targets: {parsed10['active_targets']}")
assert parsed10["active_targets"] == [3000, 2000]
print("✅ PASSED")

print("\n" + "=" * 80)
print("TESTING FEATURE 4: Retrieval Profile Routing")
print("=" * 80)

topic_cases = [
    ("WTO Article XXI national security exception and trade restrictions", "wto_trade_security_exceptions"),
    ("Parent company liability under Vedanta and Okpabi for overseas harm", "corporate_bhr_parent_liability"),
    ("State responsibility for climate damage, no-harm principle and attribution", "climate_state_responsibility"),
    ("Maritime interception, non-refoulement and extraterritorial control", "refugee_maritime_non_refoulement"),
    ("Medical law problem question on consent, material-risk disclosure, capacity, and emergency treatment", "medical_consent_capacity"),
    ("Criminal evidence essay on hearsay under the Criminal Justice Act 2003 and Article 6 fairness", "criminal_evidence_hearsay"),
    ("Public law essay on Article 8 ECHR proportionality and necessity in a democratic society", "public_law_article8_proportionality"),
    ("Criminal law problem question on omissions, gross negligence manslaughter, self-defence, and loss of control", "criminal_omissions_homicide_defences"),
    ("Tort problem question on negligence, omissions, breach, and causation after Robinson and Michael", "tort_negligence_omissions"),
    ("EU law problem question on worker status, retained worker, and residence rights under Article 45 TFEU", "eu_free_movement_workers_residence"),
    ("Land law problem question on common intention constructive trusts, cohabitation, Stack v Dowden, and Jones v Kernott", "land_coownership_constructive_trusts"),
    ("International commercial arbitration essay on party autonomy, the seat, separability, and the New York Convention", "international_commercial_arbitration"),
    (
        "Family law problem question on child arrangements, prohibited steps order, internal relocation, welfare checklist, Children Act 1989, wishes and feelings, and parental involvement.",
        "family_private_children_arrangements",
    ),
    (
        "International humanitarian law essay on distinction, proportionality, precautions in attack, Additional Protocol I Articles 48 51 57, Article 36 weapons reviews, Rome Statute clearly excessive, EWIPA, and dual-use objects.",
        "ihl_targeting_proportionality_civilians",
    ),
    (
        "Advise on misrepresentation, non-reliance clause, and section 3 Misrepresentation Act 1967 reasonableness.",
        "contract_misrepresentation_exclusion",
    ),
    (
        "Business and human rights essay on supply-chain due diligence, lower-tier suppliers, audit fatigue, and mandatory human rights due diligence laws.",
        "corporate_bhr_parent_liability",
    ),
]
for prompt, expected_topic in topic_cases:
    prof = _infer_retrieval_profile(prompt)
    actual_topic = prof.get("topic")
    print(f"- {expected_topic}: {actual_topic}")
    assert actual_topic == expected_topic
print("✅ PASSED")

print("\n" + "=" * 80)
print("TESTING FEATURE 5: Mixed-Question Unit Extraction")
print("=" * 80)
mixed_prompt = """
5000 words
1. Environmental / ESG – Problem Question (Corporate Environmental Liability)
GreenChem plc faces contaminated-land, off-site waste, and ESG disclosure issues.

2. Business & Human Rights – Essay Question (Supply-Chain Due Diligence)
"Companies increasingly rely on complex global supply chains, yet serious human rights abuses continue to surface in lower-tier suppliers. Voluntary corporate social responsibility programmes have proven insufficient, leading to calls for mandatory human rights due diligence laws." Discuss.
""".strip()
mixed_units = _extract_units_with_text(mixed_prompt)
print("Mixed units:", mixed_units)
assert len(mixed_units) == 2
assert mixed_units[0]["question_index"] == 1
assert mixed_units[1]["question_index"] == 2
assert "Environmental / ESG" in mixed_units[0]["label"]
assert "Business & Human Rights" in mixed_units[1]["label"]
print("✅ PASSED")

print("\n" + "=" * 80)
print("TESTING FEATURE 6: Contract Misrepresentation Quality Gate")
print("=" * 80)
misrep_prompt = (
    "Advise on fraudulent and negligent misrepresentation, entire agreement/non-reliance clauses, "
    "and the effect of MA 1967 s 3 and UCTA reasonableness."
)
misrep_profile = _infer_retrieval_profile(misrep_prompt)
gate = _build_legal_answer_quality_gate(misrep_prompt, misrep_profile)
print(gate[:400] + "...")
assert "construction first" in gate.lower()
assert "fraud cannot be excluded" in gate.lower()
assert "rescission bars" in gate.lower()
assert "insufficient to satisfy derry v peek" in gate.lower()
assert "do not restate the same superior-knowledge/reliance narrative" in gate.lower()
print("✅ PASSED")

print("\n" + "=" * 80)
print("TESTING FEATURE 6B: B2B Misrepresentation Profile Calibration")
print("=" * 80)
b2b_misrep_prompt = """
Contract Law – Problem Question (Approx. 2000 words)
Misrepresentation and Remedies

FreshTaste Ltd runs a chain of restaurants. It decides to purchase a new commercial food-processing machine from KitchenPro Equipment Ltd.
Maria, the director, relies on statements about 300 meals per hour and suitability for continuous daily operation.
KitchenPro relies on a non-reliance / estimates clause.
""".strip()
b2b_profile = _infer_retrieval_profile(b2b_misrep_prompt)
print("B2B profile must_cover:", b2b_profile.get("must_cover"))
print("B2B query keywords:", b2b_profile.get("query_keywords"))
assert b2b_profile.get("topic") == "contract_misrepresentation_exclusion"
assert "Consumer Rights Act 2015" not in (b2b_profile.get("must_cover") or [])
assert "consumer rights act" not in [str(x).lower() for x in (b2b_profile.get("expected_keywords") or [])]
assert not {"approx", "freshtaste", "kitchenpro", "maria", "runs"} & {str(x).lower() for x in (b2b_profile.get("query_keywords") or [])}
b2b_index_coverage = _profile_local_index_coverage(b2b_profile)
print("B2B local index coverage:", b2b_index_coverage)
assert b2b_index_coverage.get("thin") is True
print("✅ PASSED")

print("\n" + "=" * 80)
print("TESTING FEATURE 6C: Short Problem Introduction Control")
print("=" * 80)
overlong_intro_answer = """Part I: Introduction

This dispute concerns alleged misrepresentation by KitchenPro to FreshTaste. The facts describe statements about output, reliability, and suitability for continuous operation, and they also include a boilerplate clause in the written contract. The answer will examine whether the statements were actionable, whether they induced the contract, whether they amount to fraudulent, negligent, or innocent misrepresentation, whether the written clause prevents liability, what remedies arise, how rescission operates, how damages operate, whether breach of contract also matters, and what FreshTaste should do. The answer will also explain the facts again, including Maria's reliance, the superior knowledge of KitchenPro, the overheating, the reduced capacity, the extra staff costs, the shutdown, and the practical consequences for the business before the legal analysis begins. It will further describe the negotiations, the commercial context, the role of the machine in the restaurant chain, the meaning of continuous operation, and the significance of the manager's language before turning to doctrine. It will also restate the likely order of issues, the significance of the boilerplate clause, the possible remedies, the differences between rescission and damages, and the practical impact on FreshTaste in some detail before any substantive legal analysis starts.

Part II: Actionable Representations

A. Issue
Whether the pre-contractual statements were actionable representations.

B. Rule
An actionable misrepresentation requires a false statement of fact which induced the contract (Misrepresentation Act 1967, s 2(1)).

C. Application
The statements were specific and relied upon.

D. Conclusion
There is a strong argument for actionable representation.

Part III: Remedies and Liability

Damages and rescission are both arguable.

Part IV: Final Conclusion

FreshTaste likely has a strong claim."""
overlong_intro_issues = _essay_quality_issues(
    overlong_intro_answer,
    "Contract Law – Problem Question (Approx. 2000 words)\nAdvise FreshTaste on misrepresentation and remedies.",
    False,
    is_problem_mode=True,
)
print(overlong_intro_issues)
assert any("overlong introduction" in issue.lower() for issue in overlong_intro_issues)
print("✅ PASSED")

print("\n" + "=" * 80)
print("TESTING FEATURE 7: Structural Quality Gate Refinements")
print("=" * 80)

constitutional_prompt = "Public law essay question on parliamentary sovereignty, constitutional dialogue, and constitutional statutes."
constitutional_profile = _infer_retrieval_profile(constitutional_prompt)
constitutional_gate = _build_legal_answer_quality_gate(constitutional_prompt, constitutional_profile)
print(constitutional_gate[:500] + "...")
assert "Use one introduction only per question" in constitutional_gate
assert "issue + thesis/provisional answer + route-map only" in constitutional_gate
assert "Prefer calibrated conclusions on contested points" in constitutional_gate
assert "UK Supreme Court" in constitutional_gate
assert "Optional A. / B. / C. / D. subsections may appear inside a Part" in constitutional_gate
print("✅ PASSED")

print("\n" + "=" * 80)
print("ALL TESTS PASSED! ✅")
print("=" * 80)
print("\nThe new features are working correctly:")
print("1. ✅ Paragraph improvement detection (specific vs whole essay)")
print("2. ✅ Google Search grounding detection with OSCOLA enforcement")
print("3. ✅ Canonical word-target parsing (mixed transcript + multi-question)")
print("4. ✅ Retrieval-profile routing for hard legal domains")
print("5. ✅ Structural quality-gate refinements for concise intros and calibrated conclusions")
print("\nYou can now use these features in the backend answer flow.")
