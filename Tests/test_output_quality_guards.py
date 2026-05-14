"""
Regression checks for output-quality guards raised by the user:
- OSCOLA parenthetical integrity
- Immediate citation placement detection
- Draft continuation leakage stripping
- Legal retrieval jurisdiction hard-gating
"""

import re

from backend_answer_runtime import (
    _ensure_problem_terminal_sections_within_cap,
    _essay_quality_issues,
    _enforce_deterministic_title_policy,
    _enforce_part_ending_by_history,
    _final_output_integrity_cleanup,
    _enforce_expected_part_heading,
    _ensure_clean_terminal_sentence,
    _current_unit_mode_from_history,
    _complete_answer_sentence_support_issues,
    _complete_answer_citation_trace_issues,
    _subject_specific_problem_route_issues,
    _complete_answer_forbidden_source_list_issues,
    _subject_specific_final_outcome_issues,
    _expected_internal_part_heading_from_history,
    _normalize_short_essay_output,
    _normalize_short_problem_output,
    _last_assistant_requires_same_logical_part,
    _history_aware_structure_issues,
    _is_abrupt_answer_ending,
    _has_visible_conclusion,
    _resolve_word_window_from_history,
    _trim_regressive_part_restart,
    _expected_unit_structure_state_from_history,
    AUTO_HARD_FAILURE_REGEN_MAX_ATTEMPTS,
    AUTO_INTERMEDIATE_UNDERLENGTH_FIX_MAX_ATTEMPTS,
    ENABLE_RAG_DEBUG_UI,
)
from model_applicable_service import (
    sanitize_output_against_allowlist,
    _infer_retrieval_profile,
    _plan_deliverables_by_units,
    _assistant_should_hold_same_part,
    detect_essay_core_policy_violation,
    detect_long_essay,
)
from rag_service import RAGService


def run() -> None:
    print("=" * 80)
    print("OUTPUT QUALITY GUARDS REGRESSION")
    print("=" * 80)

    print("Hard-failure regen cap:", AUTO_HARD_FAILURE_REGEN_MAX_ATTEMPTS)
    assert AUTO_HARD_FAILURE_REGEN_MAX_ATTEMPTS == 2
    print("Intermediate underlength fix cap:", AUTO_INTERMEDIATE_UNDERLENGTH_FIX_MAX_ATTEMPTS)
    assert AUTO_INTERMEDIATE_UNDERLENGTH_FIX_MAX_ATTEMPTS == 2
    print("Debug UI enabled:", ENABLE_RAG_DEBUG_UI)
    assert ENABLE_RAG_DEBUG_UI is False

    # Static regression checks for part-length stability:
    # 1) Do not run destructive near-duplicate cleanup in finalization path.
    # 2) Keep continuation repeat-guard active even in fast mode.
    with open("backend_answer_runtime.py", "r", encoding="utf-8") as fh:
        backend_src = fh.read()
    assert "final_response = _dedupe_near_identical_paragraphs(final_response)" not in backend_src
    assert "if (not was_stopped) and allow and (postgen_hard_retry_used < postgen_hard_retry_limit):" not in backend_src
    assert "AUTO_INTERMEDIATE_UNDERLENGTH_FIX_MAX_ATTEMPTS = 2" in backend_src
    assert "def _enforce_part_ending_by_history(" in backend_src
    assert "rescission, damages, or another remedy is the realistic outcome." not in backend_src
    assert "the principal remedy or response available, and any practical limit on relief that follows from the analysis above." in backend_src
    assert "the most likely liability outcome" in backend_src

    with open("model_applicable_service.py", "r", encoding="utf-8") as fh:
        gemini_src = fh.read()
    assert "should_enforce_continuation_repeat_guard = (\n        (not FAST_GENERATION_MODE)" not in gemini_src
    assert "should_enforce_unit_structure_policy = (\n        (not FAST_GENERATION_MODE)" not in gemini_src
    assert "should_enforce_essay_core_policy = (\n        (not FAST_GENERATION_MODE)" not in gemini_src
    assert "if is_internal_control_prompt:\n        long_essay_info = {" in gemini_src
    assert "if continuation_info_rt.get(\"is_continuation\"):" in gemini_src
    assert "[STRUCTURE ENFORCEMENT — CONTINUATION MODE]" in gemini_src
    assert (
        "[OSCOLA PROPOSITION-LEVEL INLINE STYLE — STRICT]" in gemini_src
        or "[OSCOLA INLINE HOUSE STYLE — STRICT]" in gemini_src
    )
    assert "[OSCOLA QUALITY CHECK — APPLY SILENTLY BEFORE OUTPUT]" in gemini_src
    assert "sentence (citation)." in gemini_src
    assert "The first continuation Part heading must NOT be 'Introduction'." in gemini_src
    assert "EVERY response part must visibly identify its active question with a " in gemini_src
    assert "Use ONE Part per major doctrinal issue cluster, not a separate Part for every micro-point." in gemini_src
    assert "Equal Pay / Indirect Discrimination / Justification / Remedies" in gemini_src
    assert "[SUBJECT-SPECIFIC: COMPETITION LAW MARKER-FEEDBACK GUARDRAILS]" in gemini_src
    assert "[SUBJECT-SPECIFIC: INTERNATIONAL COMMERCIAL MEDIATION — MARKER-FEEDBACK GUARDRAILS]" in gemini_src
    assert "Do not create adjacent sections that analyse the same issue twice under slightly different headings." in gemini_src
    assert "No dropped issue: if a section opens an issue, it resolves that issue before the answer moves on." in gemini_src
    assert "In essay form, prefer descriptive subheadings" in gemini_src
    assert "Present Nadarajah cautiously" in gemini_src
    assert "Start with a short general framework section before claimant-by-claimant analysis" in gemini_src
    assert "The integrated advice must state the bottom-line position expressly" in gemini_src
    assert "Do NOT import remedies/defences language from other subjects" in gemini_src
    assert "Keep paragraphs controlled: usually one main analytical move per paragraph" in gemini_src
    assert "Problem format: keep any integrated overall advice/conclusion at the END only" in gemini_src
    assert "Essay format: use descriptive thematic headings/subheadings rather than IRAC labels" in gemini_src
    assert "Keep each D. Conclusion brief and non-redundant." in gemini_src
    assert "the penultimate Part-numbered Remedies / Liability section and the final Part-numbered Final Conclusion section are mandatory" in gemini_src
    assert "[SINGLE-SHOT ESSAY STRUCTURE GUARD]" in gemini_src
    assert "[SINGLE-SHOT PROBLEM STRUCTURE GUARD]" in gemini_src
    assert "Do NOT use a Title line. Start directly with 'Part I: Introduction'." in gemini_src
    assert "Every parenthetical authority reference must be a FULL OSCOLA citation; no bare case names, surnames, Act titles, or source labels in parentheses." in gemini_src
    assert "Optional A. / B. / C. / D. subsections may appear inside a Part when they are descriptive/thematic" in gemini_src
    assert "clinical_negligence_causation_loss_of_chance" in gemini_src
    assert "public_international_law_immunities_icc" in gemini_src
    assert "employment_restrictive_covenants" in gemini_src
    assert "cybercrime_ransomware_jurisdiction" in gemini_src
    assert "[TOPIC-SPECIFIC GUIDANCE — CLINICAL NEGLIGENCE (CAUSATION / LOSS OF CHANCE)]" in gemini_src
    assert "[TOPIC-SPECIFIC GUIDANCE — PIL (IMMUNITIES / UNIVERSAL JURISDICTION / ICC)]" in gemini_src
    assert "[TOPIC-SPECIFIC GUIDANCE — EMPLOYMENT (RESTRICTIVE COVENANTS)]" in gemini_src
    assert "[TOPIC-SPECIFIC GUIDANCE — PUBLIC LAW (LEGITIMATE EXPECTATIONS)]" in gemini_src
    assert "[TOPIC-SPECIFIC GUIDANCE — CONSTITUTIONAL LAW (PARLIAMENTARY SOVEREIGNTY / CONSTITUTIONAL DIALOGUE)]" in gemini_src
    assert "[TOPIC-SPECIFIC GUIDANCE — CRIMINAL LAW (NON-FATAL OFFENCES / CONSENT)]" in gemini_src
    assert "[TOPIC-SPECIFIC GUIDANCE — TORT (PSYCHIATRIC HARM)]" in gemini_src
    assert "[TOPIC-SPECIFIC GUIDANCE — CYBERCRIME (RANSOMWARE / JURISDICTION)]" in gemini_src
    assert "[TOPIC-SPECIFIC GUIDANCE — SPACE LAW (DEBRIS / LIABILITY)]" in gemini_src
    assert "[TOPIC-SPECIFIC GUIDANCE — AI / TECH LAW (ALGORITHMIC DISCRIMINATION)]" in gemini_src
    assert "[TOPIC-SPECIFIC GUIDANCE — CULTURAL HERITAGE (ILLICIT TRAFFICKING / RESTITUTION)]" in gemini_src
    assert "Do NOT duplicate the analysis by having one full section on 'overriding public interest'" in gemini_src
    assert "Use one introduction only. Do not restart with a second introduction" in gemini_src
    assert "Keep Part I short: identify the Diceyan orthodoxy" in gemini_src
    assert "Do not use Dica as the main sports-consent authority." in gemini_src
    assert "Prefer precise institutional language such as 'UK Supreme Court'" in gemini_src
    assert "Do NOT output placeholders or fragments such as '(.C. 432 (2007))' or '(.C. 776 (2011))'" in gemini_src
    assert "Prefer leading authorities over obscure or peripheral cases." in gemini_src
    assert "Cite specific sections, articles, or treaty provisions where they do real work" in gemini_src
    assert "If a doctrine has named conditions, limbs, or stages, state them expressly" in gemini_src
    assert "Avoid over-fragmentation: use one Part per major issue cluster or evaluative move" in gemini_src
    assert "Each Part should have one dominant analytical job." in gemini_src
    assert "Body Part headings must name the actual doctrinal/theme issue." in gemini_src
    assert "Essay format: body Part headings must be specific to the real doctrinal/theme dispute." in gemini_src
    assert "avoid over-fragmentation. For long essays over 2,000 words" in gemini_src
    assert "about 2-3 issue Parts is often enough around 2,500-3,500 words" in gemini_src
    assert "about 4-6 around 4,000-5,500 words" in gemini_src
    assert "5-7 around 6,000-7,500 words" in gemini_src
    assert "for longer essays, short descriptive A. / B. / C. subsections inside a Part can improve clarity" in gemini_src
    assert "use some academic commentary to frame the evaluation or debate" in gemini_src
    assert "R (Daly) v Secretary of State for the Home Department, Kennedy v Charity Commission, Pham v Secretary of State for the Home Department, Belmarsh, and Bank Mellat (No 2)" in gemini_src
    assert "anchor the institutional/remedial distinction in Westdeutsche Landesbank Girozentrale v Islington LBC" in gemini_src
    assert "use FHR European Ventures LLP v Cedar Capital Partners LLC as the leading proprietary-response authority" in gemini_src
    assert "For problem questions on a family home, a stable structure is usually: beneficial ownership of existing legal owners -> any third-party claimant's interest -> TOLATA order for sale/occupation -> integrated final advice." in gemini_src
    assert (
        "the usual core authorities are Van Gend en Loos, Defrenne, Van Duyn, Marshall, Foster, Faccini Dori, Von Colson, Marleasing, and Francovich/Brasserie du Pêcheur" in gemini_src
        or "the usual core authorities are Van Gend en Loos, Costa v ENEL, Van Duyn, Ratti, Marshall, Foster, Faccini Dori, Von Colson, Marleasing, Francovich, and Brasserie du Pêcheur/Factortame III" in gemini_src
    )
    assert "do not write bare forms such as '(Van Duyn v Home Office)', '(Marleasing SA v La Comercial Internacional de)', or '(C-6/90; C-91/92)'" in gemini_src
    assert "the usual core authorities are Van Gend en Loos, Costa v ENEL, Van Duyn, Ratti, Marshall, Foster, Faccini Dori, Von Colson, Marleasing, Francovich, and Brasserie du Pêcheur/Factortame III" in gemini_src
    assert "Part II should normally centre Van Gend en Loos as the foundation of the 'new legal order'" in gemini_src
    assert "say indirect effect and state liability substantially mitigate or partially address the gap, but do not eliminate it" in gemini_src
    assert "conforming interpretation applies only so far as possible" in gemini_src
    assert "State the Francovich/Brasserie conditions explicitly" in gemini_src
    assert "Use Article 288 TFEU for the distinction between regulations and directives, Article 267 TFEU for preliminary references" in gemini_src
    assert "Article II (surface damage), Article III (damage in space), and Article IV" in gemini_src
    assert "Do not sprawl into five overlapping regulatory sections." in gemini_src
    assert "UNESCO 1970 for state-to-state preventive/return obligations" in gemini_src
    assert "never output ellipses, mixed year/report formats, or half-remembered full OSCOLA strings" in gemini_src
    assert "QUESTION-TYPE STRUCTURE MUST MATCH THE PIL ISSUE" in gemini_src
    assert "If the problem is an agreement/cartel/information-exchange question" in gemini_src
    assert "[SUBJECT-SPECIFIC: CLINICAL NEGLIGENCE — CAUSATION / LOSS OF CHANCE]" in gemini_src
    assert "FORUM NON CONVENIENS DISCIPLINE" in gemini_src
    assert "[final length top-up]" in gemini_src.lower()
    assert "current part:" in gemini_src.lower()
    assert "Question 1, Question 2, etc." in gemini_src
    assert "Do NOT use any 'Answer 1:' or 'Answer 2:' wrappers." in gemini_src
    assert "use Answer 1 / Answer 2 headings" not in gemini_src
    assert "[MCQ QUESTION-SET CORRECTION MODE]" in gemini_src
    assert "[MCQ GENERATION MODE]" in gemini_src
    assert "[MCQ WORKFLOW OVERRIDE — HIGHEST PRIORITY]" in gemini_src
    assert "[STRUCTURE ENFORCEMENT — MCQ WORKFLOW MODE]" in gemini_src
    assert "MCQ correction/generation mode requires search-backed verification alongside RAG for answer-key accuracy" in gemini_src
    assert "model_user_message_override: Optional[str] = None" in gemini_src
    assert 'essay_policy_prompt = (original_request_text or message or "")' in gemini_src
    assert "[SINGLE-QUESTION LONG-ANSWER COHERENCE RULES]" in gemini_src
    assert "Part 1 must establish the thesis/answer direction once" in gemini_src
    assert "Start with the next unresolved Part-numbered heading, not a fresh introduction, title, or recap." in gemini_src
    assert "Keep the same thesis/position and analytical order across all parts of this one answer." in gemini_src
    assert "Do NOT use any heading containing 'Conclusion' or 'Conclusion and Advice' in Part 1." in gemini_src
    assert "Keep the depth roughly balanced across parts; do not rush to an overall conclusion early and leave the last part thin." in gemini_src
    assert "model_user_message_override = str(original_request_text).strip()" in gemini_src
    assert "Required terminal headings for this part:" in gemini_src
    assert "_problem_remedies_liability_heading_template()" in gemini_src
    assert "_problem_final_conclusion_heading_template()" in gemini_src
    assert "both substantive, not token-length" in gemini_src
    assert "End this response with a separate final Part-numbered conclusion section using this exact heading" in gemini_src

    # Empty allowlist should not destructively strip all OSCOLA citations.
    preserved, removed = sanitize_output_against_allowlist(
        "Rule from Donoghue v Stevenson [1932] AC 562 remains central.",
        [],
        rag_context_len=4044,
        strict=True,
    )
    assert preserved == "Rule from Donoghue v Stevenson [1932] AC 562 remains central."
    assert removed == []

    malformed = (
        "The approach was accepted "
        "(Springwell Navigation Corpn v JP Morgan Chase Bank [2010] 2 CLC 705, by which the parties agree)."
    )
    cleaned = _final_output_integrity_cleanup(malformed)
    print("Cleaned malformed citation:", cleaned)
    assert "by which the parties agree" not in cleaned
    assert "(Springwell Navigation Corpn v JP Morgan Chase Bank [2010] 2 CLC 705)" in cleaned

    prompt_two_q = """4000 words
1. Family Law – Problem Question (Divorce and Financial Remedies)
Advise Alex and Priya on financial remedies, sharing vs needs, clean break, and likely outcome.

2. Intellectual Property – Essay Question (Copyright and Fair Dealing)
Discuss copyright infringement, fair dealing, and the three-step test.
"""
    assistant_part_1 = """Question 1: Family Law – Problem Question (Divorce and Financial Remedies)

Part I: Introduction

The court will consider the statutory powers and the s 25 factors.

D. Conclusion

On balance, Priya is likely to secure significant housing provision.

Will Continue to next part, say continue"""
    history_two_q = [
        {"role": "user", "text": prompt_two_q},
        {"role": "assistant", "text": assistant_part_1},
        {"role": "user", "text": "continue"},
    ]
    assert _assistant_should_hold_same_part(history_two_q, 0) is False
    assert _last_assistant_requires_same_logical_part([{"role": "assistant", "text": assistant_part_1}]) is False

    broken_part_2 = """Part II: Final Analysis

Question 1: Family Law – Problem Question (Divorce and Financial Remedies)

A. Issue

The court must determine the overall outcome.

Part II: Conclusion and Advice

On balance, the authorities support the analysis above."""
    fixed_part_2 = _enforce_part_ending_by_history(broken_part_2, "continue", history_two_q)
    print("Fixed Part 2:\n", fixed_part_2)
    assert fixed_part_2.startswith("Question 2: Intellectual Property – Essay Question (Copyright and Fair Dealing)")
    fixed_part_headings = re.findall(r"(?im)^\s*Part\s+([IVXLCDM0-9]+)\s*:", fixed_part_2)
    assert len(fixed_part_headings) >= 2
    assert fixed_part_headings[:2] == ["I", "II"]

    structure_issues = _history_aware_structure_issues(broken_part_2, "continue", history_two_q)
    print("New-question routing issues:", structure_issues)
    assert any(
        ("Unit-structure policy violation" in issue) or ("Current part appears to repeat the previous question" in issue)
        for issue in structure_issues
    )

    single_q_prompt = """4000 words
EU Competition Law – Essay Question (Abuse of Dominance in Digital Markets)

Discuss the modern approach to abuse of dominance in digital markets.
"""
    premature_single_q_part1 = """Title: EU Competition Law – Essay Question (Abuse of Dominance in Digital Markets)

Part I: Introduction

This essay frames the modern debate.

Part II: Dominance and Market Power

Digital gatekeepers may enjoy entrenched dominance.

Part III: Conclusion

On balance, the modern law remains sufficiently flexible.

Will Continue to next part, say continue"""
    premature_single_q_issues = _history_aware_structure_issues(
        premature_single_q_part1,
        single_q_prompt,
        [],
    )
    print("Premature single-question conclusion issues:", premature_single_q_issues)
    assert any("not the final planned part" in issue.lower() and "visible conclusion heading" in issue.lower() for issue in premature_single_q_issues)

    single_q_history = [
        {"role": "user", "text": single_q_prompt},
        {
            "role": "assistant",
            "text": (
                "Title: EU Competition Law – Essay Question (Abuse of Dominance in Digital Markets)\n\n"
                "Part I: Introduction\n\n"
                "The orthodox framework requires careful market definition.\n\n"
                "Part II: Dominance and Market Power\n\n"
                "The first stage is establishing substantial and durable market power.\n\n"
                "Part III: Exclusionary Conduct\n\n"
                "The next issue is how exclusionary abuse operates in digital settings.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
        {"role": "user", "text": "continue"},
    ]
    bad_single_q_cont = """EU Competition Law – Essay Question (words)

Part VII: Expanding Abuse Concepts in Modern Digital Case Law

The challenge of adapting traditional doctrines to digital realities has forced competition authorities to rethink exclusionary abuse.
"""
    fixed_single_q_cont = _enforce_expected_part_heading(bad_single_q_cont, "continue", single_q_history)
    print("Fixed single-question continuation heading:", fixed_single_q_cont.splitlines()[:4])
    assert fixed_single_q_cont.startswith("Part IV:")
    assert not fixed_single_q_cont.startswith("EU Competition Law – Essay Question")
    assert _expected_internal_part_heading_from_history("continue", single_q_history) == 4

    detached_cite = (
        "The duty analysis follows the orthodox structure.\n\n"
        "(Caparo Industries plc v Dickman [1990] UKHL 2).\n\n"
        "Further application."
    )
    merged_cite = _final_output_integrity_cleanup(detached_cite)
    print("Merged detached citation:", merged_cite)
    assert "structure. (Caparo Industries plc v Dickman [1990] UKHL 2)." in merged_cite

    cont = (
        "Continuing the examination of contractual interpretation, this objective principle was reinforced.\n\n"
        "Part IX: Contractual Interpretation and the Matrix of Fact (Continued)\n\n"
        "Body text."
    )
    cleaned_cont = _final_output_integrity_cleanup(cont)
    print("Cleaned continuation opener:", cleaned_cont.splitlines()[0])
    assert cleaned_cont.startswith("Part IX:")
    assert "Continuing the examination" not in cleaned_cont

    answer_wrapped_question = (
        "Answer 1: Question 1: Space Law – Problem Question\n\n"
        "Part I: Introduction\n\n"
        "Body."
    )
    cleaned_answer_wrapper = _final_output_integrity_cleanup(answer_wrapped_question)
    print("Cleaned answer wrapper:", cleaned_answer_wrapper.splitlines()[0])
    assert cleaned_answer_wrapper.startswith("Question 1: Space Law – Problem Question")
    assert "Answer 1:" not in cleaned_answer_wrapper

    duplicate_heading_text = (
        "Part II: Classification of the Pre-Contractual Statements\n\n"
        "Part II: Classification of the Pre-Contractual Statements\n\n"
        "Body text."
    )
    cleaned_duplicate_heading = _final_output_integrity_cleanup(duplicate_heading_text)
    print("Collapsed duplicate heading:", cleaned_duplicate_heading.splitlines()[:3])
    assert cleaned_duplicate_heading.count("Part II: Classification of the Pre-Contractual Statements") == 1

    bad_article8_chunk = """Question 1: Human Rights – Essay Question (Article 8 ECHR: Private and Family Life)

Part I: Introduction

Article 8 is broad and flexible (ECHR, art 8(1)). It has been interpreted extensively by the Court. The answer opens at a high level and then keeps moving through broad themes without promoting them to proper Part headings. This keeps the structure loose and makes it harder for the reader to see where the actual argument is developing. The section continues with generic discussion instead of moving quickly to the real analytical pressure points. The explanation stays mostly descriptive and does not yet anchor the breadth of Article 8 in enough concrete authorities.

The Expansive Scope of Protected Interests

Private life covers identity and integrity. Family life covers relationships. Home and correspondence are also broad. The answer continues to explain these points in general terms and keeps adding description without restructuring them into distinct Parts. The paragraph becomes long enough to function as a major section, yet it still sits under a bare heading instead of a Part-numbered heading. That is exactly the kind of drift the validator should catch because a long essay answer should not leave major body sections as unheaded prose. The discussion remains too lightly sourced for the amount of legal work it is trying to do.

The Limitation Clause and Proportionality

Interference must be justified (ECHR, art 8(2)). Proportionality is important. But the answer still does not convert this into a proper Part-numbered section, and it still does not provide enough citation support for a long analytical chunk. It keeps describing legality, legitimate aims, proportionality and margin of appreciation at a very high level. The text is long enough to trigger the bare-heading detector and the citation-density guard because the legal propositions are carrying too much weight without enough immediately visible authority.
"""
    bad_article8_issues = _essay_quality_issues(
        bad_article8_chunk,
        "1. Human Rights – Essay Question (Article 8 ECHR: Private and Family Life)",
        is_short_single_essay=False,
        is_problem_mode=False,
    )
    print("Bad Article 8 chunk issues:", bad_article8_issues)
    assert any("bare headings" in issue.lower() for issue in bad_article8_issues)
    assert any("citation density" in issue.lower() for issue in bad_article8_issues)

    bad_sog_chunk = """Question 2: Commercial / Sale of Goods – Problem Question (Implied Terms and Remedies)

Part III: Introduction

This problem concerns the implied terms and remedies. The answer starts with a general introduction but then moves into large body sections without promoting them to proper Part-numbered headings. That makes the structure harder to follow in a problem answer, particularly when the legal issues should be separated cleanly. The answer also gives almost no citation support for the legal propositions it is asserting.

Sale by Description

The brochure may matter. But the answer leaves this as a bare heading and gives only a thin sentence beneath it. In a properly structured problem answer, this should sit inside a Part-numbered analytical section and normally within A/B/C/D subheadings. Instead, the discussion looks like an unstructured note. The same problem affects the treatment of remedies because the text keeps identifying issues without building a visible analytical scaffold.

Remedies

Sara may reject and claim damages. The answer mentions rejection and damages but does not build them into a proper analytical Part with visible Issue, Rule, Application and Conclusion subheadings. The structure is therefore weak, and the citation density is also weak because the answer barely shows any immediate legal authority despite making statutory and remedial claims.
"""
    bad_sog_issues = _essay_quality_issues(
        bad_sog_chunk,
        "2. Commercial / Sale of Goods – Problem Question (Implied Terms and Remedies)",
        is_short_single_essay=False,
        is_problem_mode=True,
    )
    print("Bad sale-of-goods chunk issues:", bad_sog_issues)
    assert any("irac subheadings" in issue.lower() for issue in bad_sog_issues)

    # Heading drift correction for continuation parts:
    # expected part = II, but model starts at Part X -> must be corrected to Part II.
    msgs = [
        {"role": "user", "text": "4500 words contract law answer"},
        {"role": "assistant", "text": "Part I: Intro\n\nBody.\n\nWill Continue to next part, say continue"},
    ]
    corrected = _enforce_expected_part_heading(
        "Part X: Continued Analysis\n\nBody.",
        "continue",
        msgs,
    )
    print("Corrected continuation heading:", corrected.splitlines()[0])
    assert corrected.startswith("Part II: Further Analysis")

    # Internal part progression should follow prior in-answer Part headings.
    msgs_internal = [
        {"role": "user", "text": "4500 words trusts problem question"},
        {"role": "assistant", "text": "Part I: Intro\n\nBody.\n\nPart II: Rule\n\nBody.\n\nPart III: Application\n\nBody.\n\nPart IV: Evidence\n\nBody.\n\nWill Continue to next part, say continue"},
    ]
    next_internal = _expected_internal_part_heading_from_history("continue", msgs_internal)
    print("Next internal part heading:", next_internal)
    assert next_internal == 5
    corrected_internal = _enforce_expected_part_heading(
        "Part II: Continued Analysis\n\nBody.",
        "continue",
        msgs_internal,
    )
    print("Corrected internal continuation heading:", corrected_internal.splitlines()[0])
    assert corrected_internal.startswith("Part V: Further Analysis")
    corrected_intro_heading = _enforce_expected_part_heading(
        "Part II: Introduction\n\nBody.",
        "continue",
        msgs_internal,
    )
    print("Relabeled continuation intro heading:", corrected_intro_heading.splitlines()[0])
    assert corrected_intro_heading.startswith("Part V: Further Analysis")

    mixed_question_history = [
        {"role": "user", "text": "5500 words\n1. Space Law – Problem Question\n2. AI / Tech Law – Essay Question\n3. Cultural Heritage Law – Problem Question"},
        {
            "role": "assistant",
            "text": (
                "Question 1: Space Law – Problem Question\n\n"
                "Part I: Introduction\n\nBody.\n\n"
                "Part II: Rule\n\nBody.\n\n"
                "Part III: Application\n\nBody.\n\n"
                "Question 2: AI / Tech Law – Essay Question\n\n"
                "Part I: Introduction\n\nBody.\n\n"
                "Part II: Typology\n\nBody.\n\n"
                "Part III: Doctrinal Application\n\nBody.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
    ]
    mixed_question_next_internal = _expected_internal_part_heading_from_history("continue", mixed_question_history)
    print("Mixed-question next internal part heading:", mixed_question_next_internal)
    assert mixed_question_next_internal == 4

    new_question_reset_history = [
        {
            "role": "user",
            "text": (
                "4500 words\n"
                "1. Public Law – Essay Question (Parliamentary Sovereignty)\n"
                "2. Criminal Law – Problem Question (Non-Fatal Offences and Consent)"
            ),
        },
        {
            "role": "assistant",
            "text": (
                "Question 1: Public Law – Essay Question (Parliamentary Sovereignty)\n\n"
                "Part I: Introduction\n\nBody.\n\n"
                "Part II: Orthodoxy\n\nBody.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
        {
            "role": "assistant",
            "text": (
                "Question 1: Public Law – Essay Question (Parliamentary Sovereignty)\n\n"
                "Part III: Rights and Statutes\n\nBody.\n\n"
                "Part IV: Conclusion\n\nBody.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
    ]
    reset_q2 = _enforce_expected_part_heading(
        "Question 2: Criminal Law – Problem Question (Non-Fatal Offences and Consent)\n\nPart X: Introduction\n\nBody.",
        "continue",
        new_question_reset_history,
    )
    print("Question reset heading:", reset_q2.splitlines()[:4])
    assert reset_q2.startswith("Question 2: Criminal Law – Problem Question (Non-Fatal Offences and Consent)")
    assert re.search(r"(?m)^Part I: Introduction$", reset_q2)

    # Continuation regression trim: if a continuation answer regresses to Part I,
    # the restarted tail should be dropped.
    msgs_trim = [
        {"role": "user", "text": "Write a 4000 word essay on constitutional law"},
        {"role": "assistant", "text": "Title: X\n\nPart I: Intro\n\nPart II: Body\n\nPart III: Body\n\nPart IV: Body\n\nWill Continue to next part, say continue"},
    ]
    bad_cont = (
        "Part V: Continued Analysis\n\nValid continuation.\n\n"
        "Part II: Conclusion and Advice\n\nThin conclusion.\n\n"
        "Part I: Introduction\n\nRestarted essay body.\n"
    )
    trimmed_cont = _trim_regressive_part_restart(bad_cont, "continue", msgs_trim)
    assert "Part I: Introduction\n\nRestarted essay body." not in trimmed_cont
    assert trimmed_cont.startswith("Part V:")

    titled_4000 = (
        "Title: EU Competition Law – Essay Question (Abuse of Dominance in Digital Markets)\n\n"
        "Part I: Introduction\n\n"
        "The orthodox framework requires careful market definition."
    )
    title_cleaned_4000 = _enforce_deterministic_title_policy(titled_4000, single_q_prompt, [])
    print("4000-word title cleanup:", title_cleaned_4000.splitlines()[:3])
    assert not title_cleaned_4000.startswith("Title:")
    assert title_cleaned_4000.startswith("Part I: Introduction")

    # Abrupt ending hardening should avoid old inline fallback artefact text.
    abrupt = (
        "Part II: Continued Analysis\n\n"
        "The doctrine applies in this context. However, the objective reality"
    )
    smooth = _ensure_clean_terminal_sentence(abrupt, is_intermediate=True)
    print("Smoothed abrupt ending tail:", smooth.splitlines()[-1])
    assert "This completes the analysis for this part." not in smooth

    article_tail = "Financially, Amira is entitled to comprehensive compensation for any pecuniary loss resulting from the."
    cleaned_article_tail = _ensure_clean_terminal_sentence(article_tail, is_intermediate=False)
    print("Article-tail cleanup:", cleaned_article_tail)
    assert _is_abrupt_answer_ending(article_tail) is True
    assert "resulting from the." not in cleaned_article_tail
    assert cleaned_article_tail.endswith(".")

    short_fragment_tail = (
        "Part II: Evaluating Climate Reasonableness\n\n"
        "The orthodox framework remains highly deferential in climate litigation.\n\n"
        "The perceived."
    )
    cleaned_short_fragment = _ensure_clean_terminal_sentence(short_fragment_tail, is_intermediate=True)
    print("Short-fragment cleanup:", cleaned_short_fragment)
    assert _is_abrupt_answer_ending(short_fragment_tail) is True
    assert "The perceived." not in cleaned_short_fragment

    premature_conclusion = (
        "Part II: Analysis\n\n"
        "Body text.\n\n"
        "Part III: Conclusion and Advice\n\n"
        "This is a conclusion.\n\n"
        "Part IV: Extra Analysis\n\n"
        "Later material means the conclusion was not truly final."
    )
    assert _has_visible_conclusion(premature_conclusion) is False
    assert _has_visible_conclusion("Part 1: Conclusion\n\nFinal text.") is True
    assert _has_visible_conclusion("Part VI: Final Conclusion\n\nFinal advice text.") is True

    open_problem_part = (
        "Question 2: Cybercrime Law – Problem Question\n\n"
        "Part V: The Position of Victims in Country D and Dual Criminality\n\n"
        "A. Issue\n\n"
        "Issue text.\n\n"
        "B. Rule\n\n"
        "Rule text.\n\n"
        "C. Application\n\n"
        "If Country D wishes to assert its own jurisdiction, it could validly do so under the objective territoriality principle, as the affected laptops and the resulting."
    )
    open_problem_issues = _essay_quality_issues(
        open_problem_part,
        "continue",
        False,
        is_problem_mode=True,
    )
    print("Open-problem-part issues:", open_problem_issues)
    assert any("final analytical part is left open" in i.lower() for i in open_problem_issues)
    assert any("no visible concluding section" in i.lower() for i in open_problem_issues)

    msgs_same_part = [
        {"role": "user", "text": "Write 4500 words on administrative law and cybercrime problem questions."},
        {
            "role": "assistant",
            "text": (
                "Part V: Remedies Available in Judicial Review\n\n"
                "A. Issue\n\n"
                "Issue text.\n\n"
                "B. Rule\n\n"
                "Rule text.\n\n"
                "C. Application\n\n"
                "The court will usually quash and remit rather than directly grant leave.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
    ]
    same_part_expected = _expected_internal_part_heading_from_history("continue", msgs_same_part)
    print("Expected same-part continuation heading:", same_part_expected)
    assert same_part_expected == 5

    single_target_window = _resolve_word_window_from_history(
        "2000 words\nTax Law – Problem Question",
        [{"role": "user", "text": "2000 words\nTax Law – Problem Question"}],
    )
    print("Single-target word window:", single_target_window)
    assert single_target_window == (1980, 2000)

    short_target_window = _resolve_word_window_from_history(
        "800 words\nAdministrative Law answer",
        [{"role": "user", "text": "800 words\nAdministrative Law answer"}],
    )
    print("Short-target word window:", short_target_window)
    assert short_target_window == (792, 800)

    bare_case_text = (
        "Part I: Intro\n\n"
        "Rule from Springwell Navigation Corpn v JP Morgan Chase Bank applies here.\n\n"
        "Also Axa Sun Life Services plc v Campbell Martin Ltd supports strict wording.\n\n"
        "Part II: Conclusion\n\n"
        "Done.\n"
    )
    issues = _essay_quality_issues(
        bare_case_text,
        "Write 4000 words on misrepresentation.",
        False,
        is_problem_mode=False,
    )
    print("Citation placement issues:", issues)
    assert any("immediate OSCOLA-style parenthetical" in i for i in issues)

    no_terminal_sentence_support = _complete_answer_sentence_support_issues(
        "The first issue is whether Silvergate's pre-contract statements are terms, representations, or both. "
        "The court asks objectively whether the parties intended the statement to have contractual force, considering importance, timing, expertise and reliance."
    )
    print("No terminal sentence support issues:", no_terminal_sentence_support)
    assert any("sentence (citation)" in i.lower() for i in no_terminal_sentence_support)

    mid_sentence_citation_support = _complete_answer_sentence_support_issues(
        "The Caparo test (Caparo Industries plc v Dickman [1990] 2 AC 605 (HL)) requires foreseeability, proximity and fairness."
    )
    print("Mid-sentence citation support issues:", mid_sentence_citation_support)
    assert any("sentence (citation)" in i.lower() for i in mid_sentence_citation_support)

    terminal_sentence_citation_support = _complete_answer_sentence_support_issues(
        "The court asks objectively whether the parties intended the statement to have contractual force, considering importance, timing, expertise and reliance (Dick Bentley Productions Ltd v Harold Smith (Motors) Ltd [1965] 1 WLR 623 (CA))."
    )
    print("Terminal sentence citation support issues:", terminal_sentence_citation_support)
    assert terminal_sentence_citation_support == []

    contract_route_prompt = (
        "Contract Law - Problem Question. Orion says pre-contract statements were false, "
        "the contract has an entire agreement clause, non-reliance clause, exclusion clause, "
        "and lost investor funding. Advise on misrepresentation, breach, remoteness and remedies."
    )
    shallow_contract_route = _subject_specific_problem_route_issues(
        "Orion has a strong claim because the venue behaved unfairly and damages should be paid.",
        contract_route_prompt,
    )
    print("Shallow contract route issues:", shallow_contract_route)
    assert any("contract_law" in i for i in shallow_contract_route)

    complete_contract_route = _subject_specific_problem_route_issues(
        "The answer classifies each statement as a term, representation or collateral warranty; "
        "then applies misrepresentation, inducement and rescission; breach of condition or warranty; "
        "the entire agreement, non-reliance and exclusion clause with UCTA and Misrepresentation Act 1967 section 3; "
        "Hadley remoteness, causation, proof and loss of chance for business opportunity; "
        "and damages, affirmation, mitigation and set-off remedies.",
        contract_route_prompt,
    )
    print("Complete contract route issues:", complete_contract_route)
    assert complete_contract_route == []

    evidence_route_prompt = (
        "Evidence Law - Problem Question. Kai faces CCTV identification, eyewitness social media identification, "
        "a confession in custody without a solicitor, silence, an absent frightened friend statement, "
        "and a previous burglary conviction. Advise on admissibility and weight."
    )
    shallow_evidence_route = _subject_specific_problem_route_issues(
        "The evidence is probably admissible but the judge may warn the jury.",
        evidence_route_prompt,
    )
    print("Shallow evidence route issues:", shallow_evidence_route)
    assert any("evidence_law" in i for i in shallow_evidence_route)

    trusts_route_prompt = (
        "Equity / Trusts - Problem Question. Sofia transfers money to Malik to keep safe for the family; "
        "Malik mixes funds, pays a mortgage, buys shares that double, pays Zara, gives money to his daughter, "
        "then becomes insolvent. Advise on certainty, express trust, resulting trust, breach of trust, tracing, "
        "mixed funds, recipients, insolvency and remedies."
    )
    shallow_trusts_route = _subject_specific_problem_route_issues(
        "Sofia can recover because Malik behaved badly and equity will help her.",
        trusts_route_prompt,
    )
    print("Shallow trusts route issues:", shallow_trusts_route)
    assert any("trusts_law" in i for i in shallow_trusts_route)

    complete_trusts_route = _subject_specific_problem_route_issues(
        "The answer applies the three certainties: certainty of intention, certainty of subject matter and certainty of objects under Knight and McPhail; "
        "classifies the facts as express trust, resulting trust or no trust depending on beneficial ownership and intention to benefit; "
        "then separates breach of trust, fiduciary misapplication, personal claim and proprietary claim; "
        "tracing is handled through common law tracing, equitable tracing, mixed fund presumptions, Re Hallett, Re Oatway and the lowest intermediate balance rule; "
        "shares and mortgage repayment are analysed through proportionate share, lien, charge, subrogation, Foskett and Boscawen; "
        "Zara and the daughter are treated through recipient, bona fide purchaser, value, volunteer, knowing receipt, notice and unconscionable retention; "
        "and insolvency, proprietary priority, estate reduction and unsecured creditor consequences are ranked.",
        trusts_route_prompt,
    )
    print("Complete trusts route issues:", complete_trusts_route)
    assert complete_trusts_route == []

    criminal_route_prompt = (
        "Criminal Law - Problem Question. Liam and Noah agree to burgle a warehouse; Noah secretly brings a knife, "
        "stabs a security guard, takes laptops, returns with blood, Liam drives away and hides the laptops. "
        "Advise on burglary, theft, robbery, non-fatal offences, Jogee secondary liability, withdrawal, assisting an offender, "
        "handling stolen goods and defences."
    )
    shallow_criminal_route = _subject_specific_problem_route_issues(
        "Noah is guilty of most things and Liam is less guilty because he did not want violence.",
        criminal_route_prompt,
    )
    print("Shallow criminal route issues:", shallow_criminal_route)
    assert any("criminal_law" in i for i in shallow_criminal_route)

    complete_criminal_route = _subject_specific_problem_route_issues(
        "The answer applies burglary under section 9 to trespasser entry into a building and aggravated burglary; "
        "theft is analysed through dishonesty, appropriation, property belonging to another, intention permanently to deprive and Ivey; "
        "robbery is tested through force, section 8, in order to steal and at the time of stealing; "
        "the stabbing is analysed under section 18, section 20, wounding and grievous bodily harm; "
        "Liam is analysed under Jogee secondary liability through assist, encourage, intent, foresight and conditional intent; "
        "withdrawal is addressed through unequivocal withdrawal, neutralise and Becerra continued participation; "
        "after-the-event liability covers assisting an offender, Criminal Law Act 1967, handling stolen goods, section 22 and after the event conduct; "
        "and possible defences include self-defence, panic, duress, intoxication, reasonable force and no substantial defence.",
        criminal_route_prompt,
    )
    print("Complete criminal route issues:", complete_criminal_route)
    assert complete_criminal_route == []

    additional_subject_routes = {
        "tort_law": (
            "Tort Law - Problem Question. Advise on negligence, duty, breach, causation, remoteness, contributory negligence and damages.",
            "The answer applies duty of care through established category, Caparo, Robinson, assumption of responsibility and omission; "
            "breach through standard of care, reasonable person, Bolam, Bolitho and magnitude of risk; "
            "causation through but for, material contribution, scope of duty, novus actus and loss of chance; "
            "remoteness through foreseeability, Wagon Mound, scope of liability and kind of damage; "
            "defences through contributory negligence, volenti, illegality, mitigation and defence; "
            "and remedies through damages, injunction, declaration, quantum and contributory adjustment.",
        ),
        "land_law": (
            "Land Law - Problem Question. Advise a purchaser on registered title, actual occupation, overreaching, co-ownership, easement, covenant and remedies.",
            "The answer starts with registered land, unregistered land, LRA 2002 section 27, section 29 and priority; "
            "classifies legal interest, equitable interest, formality, registration, notice and restriction; "
            "then applies actual occupation, overriding interest, Schedule 3 and two trustees overreaching; "
            "co-ownership uses constructive trust, resulting trust, beneficial shares, TOLATA, Stack and Jones v Kernott; "
            "easement and covenant analysis covers benefit, burden, Re Ellenborough and registration; "
            "and remedies include declaration, injunction, order for sale, possession, damages and priority.",
        ),
        "employment_law": (
            "Employment Law - Problem Question. Advise on employee or worker status, dismissal, discrimination, whistleblowing, restrictive covenant, time limit and remedy.",
            "The answer applies employee, worker, self-employed, personal service, control, mutuality and substitution; "
            "unfair dismissal through potentially fair reason, reasonable investigation, range of reasonable responses, Polkey and redundancy; "
            "discrimination through direct discrimination, indirect discrimination, harassment, victimisation, burden of proof, justification and reasonable adjustments; "
            "whistleblowing through protected disclosure, public interest, detriment, automatic unfair dismissal and causation; "
            "restrictive covenant through restraint of trade, legitimate business interest, reasonableness, severance and injunction; "
            "and time limit, ACAS early conciliation, compensation, reinstatement, re-engagement and remedy.",
        ),
        "family_law": (
            "Family Law - Problem Question. Advise on child arrangements, financial remedy, domestic abuse orders, nuptial agreement, habitual residence and likely orders.",
            "The answer applies welfare, welfare checklist, Children Act 1989, parental responsibility, child arrangements and no order principle; "
            "financial remedy through section 25, Matrimonial Causes Act, needs, sharing, compensation and clean break; "
            "domestic abuse through non-molestation, occupation order, Family Law Act 1996, significant harm and balance of harm; "
            "nuptial agreement through Radmacher, needs, fairness and autonomy; "
            "jurisdiction through habitual residence, relocation, Hague Convention and welfare; "
            "and remedy through order, undertaking, financial order, child arrangements order, injunction and likely outcome.",
        ),
        "commercial_law": (
            "Commercial Law - Problem Question. Advise on sale of goods, title, nemo dat, agency, secured charge, carriage and remedies.",
            "The answer applies Sale of Goods Act, description, satisfactory quality, fitness for purpose, delivery and rejection; "
            "title through nemo dat, title, Sale of Goods Act, voidable title, retention of title and priority; "
            "agency through actual authority, apparent authority, principal, ratification and warranty of authority; "
            "security through fixed charge, floating charge, registration, priority, Companies Act 2006 and security; "
            "carriage through bill of lading, carrier, Hague-Visby, carriage, Incoterms and risk; "
            "and remedies through rejection, damages, price, specific performance, termination and mitigation.",
        ),
        "business_law": (
            "Business Law - Problem Question. Advise on director duties, shareholder unfair prejudice, insolvency, wrongful trading, partnership and remedies.",
            "The answer applies Companies Act 2006 section 171, section 172, section 174, section 175, conflict and authorisation; "
            "shareholder remedies through unfair prejudice, section 994, derivative claim, permission, proper claimant and remedy; "
            "insolvency through administration, liquidation, creditors, wrongful trading, preference and transaction at an undervalue; "
            "director liability through fraudulent trading, misfeasance, section 214, section 213, section 212 and disqualification; "
            "partnership through Partnership Act 1890, partner, agency, fiduciary, dissolution and LLP; "
            "and remedies through compensation, contribution, account of profits, injunction, buy-out and disqualification.",
        ),
        "eu_law": (
            "EU Law - Problem Question. Advise on a directive, direct effect, supremacy, retained EU law, free movement, Article 267 and state liability.",
            "The answer applies direct effect, vertical, horizontal, directive, regulation, treaty article and implementation; "
            "post-Brexit status through supremacy, Withdrawal Act, retained EU law, assimilated law, interpretation and disapplication; "
            "free movement through restriction, market access, justification, proportionality and mandatory requirement; "
            "Article 267 through preliminary reference, Court of Justice, acte clair and acte eclaire; "
            "state liability through Francovich, sufficiently serious breach, causal link and remedy; "
            "and justification through legitimate aim, suitability, necessity, proportionality and derogation.",
        ),
        "human_rights_law": (
            "Human Rights Law - Problem Question. Advise on HRA, public authority, Article 8, Article 10, Article 14, proportionality and remedies.",
            "The answer applies Human Rights Act 1998, public authority, section 6, victim and section 7; "
            "rights through engagement, interference, prescribed by law, legitimate aim, necessity and proportionality; "
            "Article 8 through private life, family life, home, correspondence and fair balance; "
            "Article 10 through freedom of expression, democratic society, necessity and proportionality; "
            "Article 14 through ambit, status, analogous situation and justification; "
            "and remedies through section 3, section 4, declaration of incompatibility, damages, just satisfaction and remedy.",
        ),
        "public_international_law": (
            "Public International Law - Problem Question. Advise on state responsibility, use of force, immunity, treaty interpretation, ICC jurisdiction and remedies.",
            "The answer applies state responsibility, attribution, breach, internationally wrongful act and Articles on State Responsibility; "
            "use of force through Article 2(4), Article 51, armed attack, necessity, proportionality and Security Council; "
            "immunity through state immunity, immunity ratione personae, immunity ratione materiae, State Immunity Act and exception; "
            "sources through customary international law, state practice, opinio juris, Vienna Convention, Article 31 and Article 32; "
            "ICC through Rome Statute, jurisdiction, complementarity, immunity and war crime; "
            "and consequences through reparation, cessation, assurances, countermeasures, declaration and compensation.",
        ),
        "tax_law": (
            "Tax Law - Problem Question. Advise on income tax, capital gains tax, VAT, avoidance, HMRC penalty, relief and appeal.",
            "The answer applies income tax, employment income, trading income, deductible, wholly and exclusively and benefit in kind; "
            "CGT through capital gains tax, disposal, chargeable gain, base cost, relief and principal private residence; "
            "VAT through taxable supply, exempt, input tax, output tax and registration; "
            "avoidance through GAAR, Ramsay, tax advantage, abusive and purposive construction; "
            "administration through assessment, enquiry, penalty, reasonable excuse, appeal and HMRC; "
            "and liability through relief, allowance, loss relief, tax liability, interest, penalty and appeal.",
        ),
    }
    for expected_slug, (route_prompt, complete_route_text) in additional_subject_routes.items():
        shallow_route = _subject_specific_problem_route_issues(
            "The claimant may have a claim and the defendant may have a defence.",
            route_prompt,
        )
        print(f"Shallow {expected_slug} route issues:", shallow_route)
        assert any(expected_slug in i for i in shallow_route), expected_slug
        complete_route = _subject_specific_problem_route_issues(complete_route_text, route_prompt)
        print(f"Complete {expected_slug} route issues:", complete_route)
        assert complete_route == [], expected_slug

    weak_final_outcome = _subject_specific_final_outcome_issues(
        "Part I: Introduction\n\nAnalysis.\n\nPart IV: Final Conclusion\n\nThe claimant has a good argument.",
        "Criminal Law - Problem Question. Advise Liam and Noah on liability.",
    )
    print("Weak final outcome issues:", weak_final_outcome)
    assert any("criminal_law" in i for i in weak_final_outcome)

    strong_final_outcome = _subject_specific_final_outcome_issues(
        "Part I: Introduction\n\nAnalysis.\n\nPart IV: Final Conclusion\n\nNoah is likely guilty of burglary and theft. Liam is liable for burglary assistance but not liable for Noah's stabbing.",
        "Criminal Law - Problem Question. Advise Liam and Noah on liability.",
    )
    print("Strong final outcome issues:", strong_final_outcome)
    assert strong_final_outcome == []

    forbidden_source_log = _complete_answer_forbidden_source_list_issues(
        "Part I: Introduction\n\nAnalysis.\n\nOnline verification used for current statutory anchors: [Act](https://example.test).",
        "Criminal Law - Problem Question. Advise Liam and Noah.",
    )
    print("Forbidden source-log issues:", forbidden_source_log)
    assert any("detached source" in i.lower() for i in forbidden_source_log)

    allowed_source_log = _complete_answer_forbidden_source_list_issues(
        "Part I: Introduction\n\nAnalysis.\n\nOnline verification used for current statutory anchors: [Act](https://example.test).",
        "Criminal Law - Problem Question. Advise Liam and Noah, and include sources list.",
    )
    print("Allowed source-log issues:", allowed_source_log)
    assert allowed_source_log == []

    trace_rag_context = (
        "[RAG CONTEXT - INTERNAL - DO NOT OUTPUT]\n"
        "Caparo Industries plc v Dickman [1990] 2 AC 605\n"
        "Human Rights Act 1998\n"
        "[END RAG CONTEXT]"
    )
    trace_issues = _complete_answer_citation_trace_issues(
        "Duty is established by a fake authority (Imaginary v Fake [2020] UKSC 1).",
        "Tort Law - Problem Question. Advise on negligence.",
        trace_rag_context,
    )
    print("Citation trace issues:", trace_issues)
    assert any("citation trace verification failed" in i.lower() for i in trace_issues)

    detached_cite_issues = _essay_quality_issues(
        "Body proposition.\n\n(Caparo Industries plc v Dickman [1990] UKHL 2).\n\nConclusion.",
        "Write 4000 words on negligence.",
        False,
        is_problem_mode=False,
    )
    print("Detached citation issues:", detached_cite_issues)
    assert any("citation-only paragraph detached" in i for i in detached_cite_issues)

    oversized_para_issues = _essay_quality_issues(
        "Part II: Analysis\n\n"
        + " ".join(["This paragraph develops the same doctrinal point in an excessively long block."] * 40)
        + "\n\nPart III: Conclusion\n\nA proper conclusion follows here with enough substance to count.",
        "Write 4500 words on climate litigation.",
        False,
        is_problem_mode=False,
    )
    print("Oversized paragraph issues:", oversized_para_issues)
    assert any("oversized paragraph blocks" in i.lower() for i in oversized_para_issues)

    bare_wednesbury_paren_issues = _essay_quality_issues(
        "Part II: Further Analysis\n\n"
        "Under the orthodox framework, climate challenges must overcome a highly deferential irrationality threshold "
        "(Associated Picture Houses Ltd v Wednesbury Corporation).",
        "Write 4500 words on climate change and judicial review.",
        False,
        is_problem_mode=False,
    )
    print("Bare Wednesbury parenthetical issues:", bare_wednesbury_paren_issues)
    assert any("proper oscola report/year reference" in i.lower() for i in bare_wednesbury_paren_issues)

    placeholder_numeric_cite_issues = _essay_quality_issues(
        "If the salesperson knew the car was a clocked write-off, the statements were fraudulent ([2 ]).",
        "Write 2000 words on a contract law problem question.",
        False,
        is_problem_mode=True,
    )
    print("Placeholder numeric citation issues:", placeholder_numeric_cite_issues)
    assert any("placeholder numeric citation markers" in i.lower() for i in placeholder_numeric_cite_issues)

    bare_tfeu_cite_issues = _essay_quality_issues(
        "Directives are binding only as to the result to be achieved (TFEU).",
        "Write 2000 words on EU law direct effect.",
        False,
        is_problem_mode=False,
    )
    print("Bare TFEU citation issues:", bare_tfeu_cite_issues)
    assert any("bare treaty citations" in i.lower() for i in bare_tfeu_cite_issues)

    eu_case_number_only_issues = _essay_quality_issues(
        "State liability was established by the Court ((C-6/90; C-9/90)).",
        "Write 2000 words on EU law direct effect.",
        False,
        is_problem_mode=False,
    )
    print("EU case-number-only citation issues:", eu_case_number_only_issues)
    assert any("eu case-number parentheticals" in i.lower() for i in eu_case_number_only_issues)

    ellipsis_case_cite_issues = _essay_quality_issues(
        "The non-reliance clause was discussed in Taberna Europe CDO II Plc v Selskabet af 1 September..., [2017] Q.B. 633 (2016).",
        "Write 4000 words on misrepresentation.",
        False,
        is_problem_mode=False,
    )
    print("Ellipsis citation issues:", ellipsis_case_cite_issues)
    assert any("ellipsis" in i.lower() for i in ellipsis_case_cite_issues)

    continuation_intro_text = (
        "Part II: Introduction\n\n"
        "The analysis continues from prior parts.\n\n"
        "Part III: Conclusion\n\n"
        "Conclusion text.\n"
    )
    continuation_intro_issues = _essay_quality_issues(
        continuation_intro_text,
        "continue",
        False,
        is_problem_mode=False,
    )
    print("Continuation-intro issues:", continuation_intro_issues)
    assert any("restarts with an 'Introduction' heading" in i for i in continuation_intro_issues)

    mixed_question_reset = (
        "Question 2: Business & Human Rights – Essay Question (Supply-Chain Due Diligence)\n\n"
        "Part XII: Conclusion\n\n"
        "The contemporary global economy is heavily reliant upon complex, multi-tiered supply chains."
    )
    cleaned_mixed_question_reset = _final_output_integrity_cleanup(mixed_question_reset)
    print("Cleaned mixed-question reset:", cleaned_mixed_question_reset.splitlines()[:3])
    assert cleaned_mixed_question_reset.startswith(
        "Question 2: Business & Human Rights – Essay Question (Supply-Chain Due Diligence)\n\nPart XII: Conclusion"
    )

    mixed_question_spacing = (
        "End of Question 1 conclusion.\n"
        "Question 2: International Humanitarian Law – Essay Question\n\n"
        "Part I: Introduction\n\nBody."
    )
    spaced_mixed_question = _final_output_integrity_cleanup(mixed_question_spacing)
    print("Mixed-question spacing fix:", spaced_mixed_question.splitlines()[:4])
    assert "conclusion.\n\nQuestion 2:" in spaced_mixed_question

    mixed_question_issues = _essay_quality_issues(
        mixed_question_reset,
        "continue",
        False,
        is_problem_mode=False,
    )
    print("Mixed-question reset issues:", mixed_question_issues)
    assert not any("not immediately followed" in i.lower() for i in mixed_question_issues)

    stray_part_before_new_question = (
        "Part VII: Continued Analysis\n\n"
        "Question 2: Immigration / Asylum Law – Problem Question (Credibility)\n\n"
        "Part I: Introduction\n\nBody."
    )
    cleaned_stray_part = _final_output_integrity_cleanup(stray_part_before_new_question)
    print("Stray pre-question Part heading removed:", cleaned_stray_part.splitlines()[:3])
    assert cleaned_stray_part.startswith(
        "Question 2: Immigration / Asylum Law – Problem Question (Credibility)\n\nPart I: Introduction"
    )

    orphan_letter_heading = (
        "Part VI: The Defence of Publication on a Matter of Public Interest\n\n"
        "A.\n\n"
        "Will Continue to next part, say continue"
    )
    orphan_heading_issues = _essay_quality_issues(
        orphan_letter_heading,
        "continue",
        False,
        is_problem_mode=True,
    )
    print("Orphan letter-heading issues:", orphan_heading_issues)
    assert any("bare lettered subheading" in i.lower() for i in orphan_heading_issues)

    empty_d_conclusion_before_continue = (
        "Part III: Fault-Based Liability\n\n"
        "A. Issue\n\n"
        "Issue text.\n\n"
        "B. Rule\n\n"
        "Rule text.\n\n"
        "C. Application\n\n"
        "Application text.\n\n"
        "D. Conclusion\n\n"
        "Will Continue to next part, say continue"
    )
    empty_d_issues = _essay_quality_issues(
        empty_d_conclusion_before_continue,
        "continue",
        False,
        is_problem_mode=True,
    )
    print("Empty D-before-continue issues:", empty_d_issues)
    assert any("empty lettered subsection" in i.lower() for i in empty_d_issues)
    hold_same_part = _assistant_should_hold_same_part(
        [
            {"role": "user", "text": "5500 words\n1. AI / Tech Law – Essay Question\n2. Cultural Heritage Law – Problem Question"},
            {"role": "assistant", "text": empty_d_conclusion_before_continue},
        ],
        0,
    )
    print("Hold same logical part after orphan D:", hold_same_part)
    assert hold_same_part is False

    empty_titled_subsection = (
        "Part III: The Holistic Assessment of Evidence\n\n"
        "A. Issue\n\n"
        "B. Rule (with authority)\n\n"
        "The tribunal must assess the evidence in the round.\n\n"
        "Part IV: Conclusion\n\n"
        "Conclusion text with enough substance to count."
    )
    empty_subsection_issues = _essay_quality_issues(
        empty_titled_subsection,
        "Write 4000 words on asylum credibility.",
        False,
        is_problem_mode=True,
    )
    print("Empty subsection issues:", empty_subsection_issues)
    assert any("empty lettered subsection" in i.lower() for i in empty_subsection_issues)

    over_reliance_text = (
        "Part I: Introduction\n\n"
        "Karanakaran v Secretary of State for the Home Department [2000] Imm AR 271 is central "
        "(Karanakaran v Secretary of State for the Home Department [2000] Imm AR 271).\n\n"
        "Part II: Evidence\n\n"
        "Karanakaran v Secretary of State for the Home Department [2000] Imm AR 271 remains important "
        "(Karanakaran v Secretary of State for the Home Department [2000] Imm AR 271). "
        "Again, Karanakaran v Secretary of State for the Home Department [2000] Imm AR 271 is cited "
        "(Karanakaran v Secretary of State for the Home Department [2000] Imm AR 271).\n\n"
        "Part III: Tribunal Error\n\n"
        "Once more, Karanakaran v Secretary of State for the Home Department [2000] Imm AR 271 dominates the analysis "
        "(Karanakaran v Secretary of State for the Home Department [2000] Imm AR 271).\n\n"
        "Part IV: Conclusion\n\n"
        "Overall, Karanakaran v Secretary of State for the Home Department [2000] Imm AR 271 is treated as the answer to every point "
        "(Karanakaran v Secretary of State for the Home Department [2000] Imm AR 271)."
    )
    over_reliance_issues = _essay_quality_issues(
        over_reliance_text,
        "Write 4000 words on asylum credibility.",
        False,
        is_problem_mode=False,
    )
    print("Over-reliance issues:", over_reliance_issues)
    assert any("over-relies on a single authority" in i.lower() for i in over_reliance_issues)

    continued_before_new_question = (
        "Part VI: Continued Analysis\n\n"
        "Question 2: Public International Law – Problem Question\n\n"
        "Part I: Introduction\n\nBody."
    )
    continued_before_new_question_issues = _essay_quality_issues(
        continued_before_new_question,
        "continue",
        False,
        is_problem_mode=True,
    )
    print("Continued-before-new-question issues:", continued_before_new_question_issues)
    assert any("continued analysis" in i.lower() and "fresh question" in i.lower() for i in continued_before_new_question_issues)

    malformed_case_parenthetical = (
        "Part I: Introduction\n\n"
        "The risk-based exception is narrow (Fairchild v Glenhaven Funeral Services Ltd10).\n\n"
        "Part II: Conclusion\n\n"
        "Final conclusion text with sufficient substance to avoid threshold issues in this synthetic test."
    )
    malformed_case_parenthetical_issues = _essay_quality_issues(
        malformed_case_parenthetical,
        "Write 4000 words on causation.",
        False,
        is_problem_mode=False,
    )
    print("Malformed case-parenthetical issues:", malformed_case_parenthetical_issues)
    assert any("fused footnote-style digits" in i.lower() for i in malformed_case_parenthetical_issues)

    malformed_statute_parenthetical = (
        "Part I: Introduction\n\n"
        "The criminal route may also be relevant ((Offences) Act 2003).\n\n"
        "Part II: Conclusion\n\n"
        "Final conclusion text with sufficient substance to count."
    )
    malformed_statute_parenthetical_issues = _essay_quality_issues(
        malformed_statute_parenthetical,
        "Write 4000 words on cultural heritage law.",
        False,
        is_problem_mode=False,
    )
    print("Malformed statute-parenthetical issues:", malformed_statute_parenthetical_issues)
    assert any("broken act titles" in i.lower() for i in malformed_statute_parenthetical_issues)

    duplicate_adjacent_parts = (
        "Question 1: Administrative Law – Problem Question\n\n"
        "Part III: Overriding Public Interest and Proportionality\n\n"
        "A. Issue\n\n"
        "Issue text.\n\n"
        "B. Rule\n\n"
        "Rule text.\n\n"
        "C. Application\n\n"
        "Application text.\n\n"
        "D. Conclusion\n\n"
        "Conclusion text.\n\n"
        "Part IV: The Court's Assessment of Overriding Public Interest\n\n"
        "A. Issue\n\n"
        "Issue text.\n\n"
        "B. Rule\n\n"
        "Rule text.\n\n"
        "C. Application\n\n"
        "Application text.\n\n"
        "D. Conclusion\n\n"
        "Conclusion text.\n"
    )
    duplicate_adjacent_issues = _essay_quality_issues(
        duplicate_adjacent_parts,
        "continue",
        False,
        is_problem_mode=True,
    )
    print("Duplicate-adjacent-part issues:", duplicate_adjacent_issues)
    assert any("substantially duplicate the same issue heading" in i.lower() for i in duplicate_adjacent_issues)

    legit_profile = _infer_retrieval_profile(
        "Administrative law problem question on legitimate expectation, published policy, unpublished policy, and overriding public interest."
    )
    print("Legitimate expectation topic:", legit_profile.get("topic"))
    assert legit_profile.get("topic") == "public_law_legitimate_expectation"

    legit_essay_prompt = (
        "4000 words\n"
        "Public Law / Administrative Law\n\n"
        "Legitimate Expectation and the Limits of Judicial Review\n\n"
        "“Over the past decades the doctrine of legitimate expectation has evolved from a procedural "
        "protection into a potential constraint on administrative policy change.”\n\n"
        "Discuss."
    )
    legit_essay_profile = _infer_retrieval_profile(legit_essay_prompt)
    print("Legitimate expectation essay topic:", legit_essay_profile.get("topic"))
    assert legit_essay_profile.get("topic") == "public_law_legitimate_expectation"
    legit_essay_plan = detect_long_essay(legit_essay_prompt)
    print("Legitimate expectation essay plan:", legit_essay_plan.get("split_mode"), legit_essay_plan.get("suggested_parts"))
    assert legit_essay_plan.get("is_long_essay") is True
    assert legit_essay_plan.get("split_mode") == "equal_parts"
    assert legit_essay_plan.get("suggested_parts") == 2

    cyber_profile = _infer_retrieval_profile(
        "Cybercrime law problem question on ransomware, Budapest Convention, objective territorial effects, MLA, and extradition."
    )
    print("Cybercrime jurisdiction topic:", cyber_profile.get("topic"))
    assert cyber_profile.get("topic") == "cybercrime_ransomware_jurisdiction"

    space_profile = _infer_retrieval_profile(
        "Space law problem question on the Outer Space Treaty, Liability Convention, launching State, space debris, and Claims Commission."
    )
    print("Space law debris topic:", space_profile.get("topic"))
    assert space_profile.get("topic") == "space_law_debris_liability"

    ai_disc_profile = _infer_retrieval_profile(
        "AI / Tech Law essay on algorithmic discrimination, proxy discrimination, impact assessments, explainability, and burden of proof under the Equality Act 2010."
    )
    print("AI algorithmic discrimination topic:", ai_disc_profile.get("topic"))
    assert ai_disc_profile.get("topic") == "ai_algorithmic_discrimination"

    employment_eqpay_profile = _infer_retrieval_profile(
        "Employment law problem question on equal pay, equality clause, comparator, part-time bonus eligibility, flexible working, childcare disadvantage, material factor defence, and Vento bands."
    )
    print("Employment equal pay topic:", employment_eqpay_profile.get("topic"))
    assert employment_eqpay_profile.get("topic") == "employment_equal_pay_flexible_working"

    heritage_profile = _infer_retrieval_profile(
        "Cultural heritage law problem question on UNESCO 1970, UNIDROIT 1995, lex situs, due diligence, and restitution of stolen antiquities."
    )
    print("Cultural heritage topic:", heritage_profile.get("topic"))
    assert heritage_profile.get("topic") == "cultural_heritage_illicit_trafficking"

    multi_q_prompt = (
        "4500 words\n"
        "1. Administrative Law – Problem Question (Legitimate Expectations)\n"
        "The Home Office applies an unpublished policy instead of a published one.\n\n"
        "2. Cybercrime Law – Problem Question (Ransomware and Jurisdiction)\n"
        "A ransomware group targets victims in multiple states and Country B relies on the Budapest Convention."
    )
    deliverables = _plan_deliverables_by_units(multi_q_prompt, 4500, 3)
    part_sizes = [int(d.get("target_words", 0) or 0) for d in deliverables]
    print("4500-word multi-question part sizes:", part_sizes)
    assert len(deliverables) == 4
    assert part_sizes == [1125, 1125, 1125, 1125]
    assert all(len(d.get("fragments") or []) == 1 for d in deliverables)
    assert [int(d.get("question_index", 0) or 0) for d in deliverables] == [1, 1, 2, 2]

    long_plan = detect_long_essay(multi_q_prompt)
    print("Long multi-topic suggested parts:", long_plan.get("suggested_parts"))
    assert long_plan.get("suggested_parts") == 4
    assert "Parts: 4" in (long_plan.get("suggestion_message") or "")

    msgs_late_heading = [
        {"role": "user", "text": "Write 5000 words on international humanitarian law"},
        {"role": "assistant", "text": "Part I: Introduction\n\nPart II: Core principles\n\nPart III: Application\n\nPart IV: Challenges\n\nWill Continue to next part, say continue"},
    ]
    late_heading = (
        "conduct a meaningful proportionality assessment. The reliance on uncertain intelligence creates severe risk.\n\n"
        "Part IX: Conclusion\n\n"
        "Final conclusion text."
    )
    corrected_late_heading = _enforce_expected_part_heading(
        late_heading,
        "continue",
        msgs_late_heading,
    )
    print("Corrected late heading:", corrected_late_heading.splitlines()[:4])
    assert corrected_late_heading.startswith("Part IV: Further Analysis")
    assert "\n\nPart IX: Conclusion" in corrected_late_heading

    repeat_history = [
        {
            "role": "user",
            "text": (
                "4500 words\n"
                "1. Discrimination / Employment Law – Problem Question\n"
                "2. International Trade Law – Essay Question"
            ),
        },
        {
            "role": "assistant",
            "text": (
                "Question 1: Discrimination / Employment Law – Problem Question\n\n"
                "Part I: Introduction\n\n"
                "The central legal issue concerns Amira's request to reduce her hours after childbirth and TechBank's refusal to accommodate that request despite the gendered impact of its workplace rules.\n\n"
                "Part II: Equal Pay or Indirect Discrimination\n\n"
                "A. Issue\n\nThe first issue is whether the claim is better framed as equal pay or indirect sex discrimination.\n\n"
                "B. Rule\n\nThe statutory framework separates equality-clause claims from indirect discrimination challenges where the complaint is directed at a workplace policy rather than an unequal contractual term.\n\n"
                "C. Application\n\nAmira is not merely saying that she was paid less for equal work. She is challenging the employer's insistence on rigid full-time presence and evening flexibility, which operates as a structural barrier to women with childcare responsibilities and prevents her from maintaining bonus eligibility.\n\n"
                "D. Conclusion\n\nHer strongest route is therefore an indirect sex discrimination claim focused on the employer's PCPs rather than a pure equal pay claim.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
    ]
    repeated_intermediate = (
        "Question 1: Discrimination / Employment Law – Problem Question\n\n"
        "Part II: Equal Pay or Indirect Discrimination\n\n"
        "A. Issue\n\nThe first issue is whether the claim is better framed as equal pay or indirect sex discrimination.\n\n"
        "B. Rule\n\nThe statutory framework separates equality-clause claims from indirect discrimination challenges where the complaint is directed at a workplace policy rather than an unequal contractual term.\n\n"
        "C. Application\n\nAmira is not merely saying that she was paid less for equal work. She is challenging the employer's insistence on rigid full-time presence and evening flexibility, which operates as a structural barrier to women with childcare responsibilities and prevents her from maintaining bonus eligibility.\n\n"
        "D. Conclusion\n\nHer strongest route is therefore an indirect sex discrimination claim focused on the employer's PCPs rather than a pure equal pay claim.\n\n"
        "Will Continue to next part, say continue"
    )
    history_aware_issues = _history_aware_structure_issues(
        repeated_intermediate,
        "continue",
        repeat_history,
    )
    print("History-aware structure issues:", history_aware_issues)
    assert any("repeats the previous part" in i.lower() for i in history_aware_issues)

    two_question_history = [
        {
            "role": "user",
            "text": (
                "4500 words\n"
                "1. Environmental / Public Law – Essay Question (Climate Change and Judicial Review)\n"
                "2. Criminal Law – Problem Question (Complicity and Joint Enterprise in Homicide)"
            ),
        },
        {
            "role": "assistant",
            "text": (
                "Question 1: Environmental / Public Law – Essay Question (Climate Change and Judicial Review)\n\n"
                "Part I: Introduction\n\n"
                "Climate litigation raises rule-of-law and separation-of-powers concerns.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
    ]
    missing_q1_conclusion = (
        "Question 1: Environmental / Public Law – Essay Question (Climate Change and Judicial Review)\n\n"
        "Part II: Further Analysis\n\n"
        "A distinct climate-reasonableness standard remains controversial because courts risk collapsing legality review into merits review."
    )
    missing_q1_conclusion_issues = _history_aware_structure_issues(
        missing_q1_conclusion,
        "continue",
        two_question_history,
    )
    print("Question-final-part missing-conclusion issues:", missing_q1_conclusion_issues)
    assert any(
        "final planned part for this question" in i.lower() and "no visible conclusion heading" in i.lower()
        for i in missing_q1_conclusion_issues
    )

    q2_history = two_question_history + [
        {
            "role": "assistant",
            "text": (
                "Question 1: Environmental / Public Law – Essay Question (Climate Change and Judicial Review)\n\n"
                "Part II: Conclusion\n\n"
                "Orthodox judicial review remains useful but limited.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
        {
            "role": "assistant",
            "text": (
                "Question 2: Criminal Law – Problem Question (Complicity and Joint Enterprise in Homicide)\n\n"
                "Part III: Introduction\n\n"
                "Leah is the principal and Max is at least a secondary party to robbery.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
    ]
    false_end_final_q2 = (
        "Question 2: Criminal Law – Problem Question (Complicity and Joint Enterprise in Homicide)\n\n"
        "Part IV: Conclusion\n\n"
        "A. Issue\n\n"
        "Max's homicide liability depends on Jogee.\n\n"
        "D.\n\n"
        "(End of Answer)"
    )
    false_end_final_q2_issues = _history_aware_structure_issues(
        false_end_final_q2,
        "continue",
        q2_history,
    )
    print("False-end final-q2 issues:", false_end_final_q2_issues)
    assert any("empty structural headings" in i.lower() for i in false_end_final_q2_issues)
    assert any("end-of-answer marker appears" in i.lower() for i in false_end_final_q2_issues)

    broken_short_problem = (
        "Part I: Introduction\n\n"
        "Chloe has a strong claim in misrepresentation.\n\n"
        "A. Issue\n\n"
        "The issue is whether the clauses are effective.\n\n"
        "C. Application\n\n"
        "Chloe is acting as a consumer\n\n"
        "Part V: Conclusion and Advice\n\n"
        "On balance, the authorities and statutory framework support the integrated analysis set out above.\n\n"
        "purchasing a vehicle for personal use from a commercial dealership.\n\n"
        "If the salesperson knew the car was a clocked write-off, the statements were fraudulent ([2 ]).\n\n"
        "(End of Answer)"
    )
    cleaned_short_problem = _normalize_short_problem_output(broken_short_problem)
    print("Cleaned short-problem output:", cleaned_short_problem)
    assert "Part V: Conclusion and Advice" not in cleaned_short_problem
    assert "([2 ])" not in cleaned_short_problem
    assert "purchasing a vehicle for personal use" in cleaned_short_problem
    assert "Part II:" not in cleaned_short_problem or cleaned_short_problem.index("Part I:") < cleaned_short_problem.index("Part II:")
    ensured_short_problem = _ensure_problem_terminal_sections_within_cap(cleaned_short_problem, 2000)
    print("Ensured short-problem terminals:", ensured_short_problem)
    assert "Remedies / Liability" in ensured_short_problem
    assert "Final Conclusion" in ensured_short_problem

    broken_short_essay = (
        "Part I: Introduction\n\n"
        "English contract law now balances party autonomy with statutory control.\n\n"
        "Part II: Construction\n\n"
        "The modern approach reads exclusion clauses in their commercial context.\n\n"
        "Part III: Statutory Control\n\n"
        "UCTA 1977 and the CRA 2015 recalibrate the freedom/fairness balance.\n\n"
        "Part IV: Conclusion\n\n"
        "On balance, freedom of contract survives but in a disciplined, context-sensitive form.\n\n"
        "Part V: Conclusion\n\n"
        "Generic fallback text that should not survive.\n\n"
        "(End of Answer)"
    )
    cleaned_short_essay = _normalize_short_essay_output(broken_short_essay)
    print("Cleaned short-essay output:", cleaned_short_essay)
    assert cleaned_short_essay.count("Conclusion") == 1
    assert "Part IV: Conclusion" in cleaned_short_essay
    assert "Part V: Conclusion" not in cleaned_short_essay

    short_problem_terminal_issues = _essay_quality_issues(
        "Part I: Introduction\n\n"
        "This problem concerns whether the claimant can rescind.\n\n"
        "Part II: Issue 1 - Misrepresentation\n\n"
        "A. Issue\n\n"
        "The first issue is whether the statement was actionable.\n\n"
        "B. Rule\n\n"
        "A false statement of fact inducing the contract may be actionable.\n\n"
        "C. Application\n\n"
        "The seller's statement is likely actionable.\n\n"
        "D. Conclusion\n\n"
        "The claimant has a strong prima facie claim.\n\n"
        "Part III: Conclusion and Advice\n\n"
        "The claimant should succeed.",
        "2000 words\nContract Law – Problem Question",
        False,
        is_problem_mode=True,
    )
    print("Short-problem terminal issues:", short_problem_terminal_issues)
    assert any("missing the required Part-numbered 'Remedies / Liability' section" in i for i in short_problem_terminal_issues)
    assert any("must use the exact final heading 'Final Conclusion'" in i for i in short_problem_terminal_issues)

    underlength_short_essay = (
        "Part I: Introduction\n\n"
        + ("intro " * 120)
        + "\n\nPart II: Analysis\n\n"
        + ("analysis " * 350)
        + "\n\nPart III: Conclusion\n\n"
        + ("conclusion " * 80)
    )
    short_essay_issues = _essay_quality_issues(
        underlength_short_essay,
        "2000 words essay on contract law",
        is_short_single_essay=True,
        is_problem_mode=False,
    )
    print("Short-essay underlength issues:", short_essay_issues)
    assert any("expected at least 1980" in issue for issue in short_essay_issues)

    overlong_conclusion_short_essay = (
        "Part I: Introduction\n\n"
        + ("intro " * 160)
        + "\n\nPart II: Analysis\n\n"
        + ("analysis " * 1100)
        + "\n\nPart III: Conclusion\n\n"
        + ("conclusion " * 420)
    )
    overlong_conclusion_issues = _essay_quality_issues(
        overlong_conclusion_short_essay,
        "2000 words essay on EU law",
        is_short_single_essay=True,
        is_problem_mode=False,
    )
    print("Short-essay overlong-conclusion issues:", overlong_conclusion_issues)
    assert any("conclusion is disproportionately long" in issue.lower() for issue in overlong_conclusion_issues)

    overfragmented_single_essay = (
        "Part I: Introduction\n\n"
        + ("intro " * 120)
        + "\n\nPart II: Framework\n\n"
        + ("framework " * 120)
        + "\n\nPart III: Doctrine\n\n"
        + ("doctrine " * 120)
        + "\n\nPart IV: Limits\n\n"
        + ("limits " * 120)
        + "\n\nPart V: Evaluation\n\n"
        + ("evaluation " * 120)
        + "\n\nPart VI: Further Evaluation\n\n"
        + ("further " * 120)
        + "\n\nPart VII: More Analysis\n\n"
        + ("analysis " * 120)
        + "\n\nPart VIII: Conclusion\n\n"
        + ("conclusion " * 120)
    )
    overfragmented_single_essay_issues = _essay_quality_issues(
        overfragmented_single_essay,
        "2000 words essay on EU law",
        is_short_single_essay=True,
        is_problem_mode=False,
    )
    print("Over-fragmented essay issues:", overfragmented_single_essay_issues)
    assert any("over-fragmented part structure" in issue.lower() for issue in overfragmented_single_essay_issues)

    vague_heading_essay = (
        "Part I: Introduction\n\n"
        + ("intro " * 90)
        + "\n\nPart II: Analysis\n\n"
        + ("analysis " * 180)
        + "\n\nPart III: Further Analysis\n\n"
        + ("further " * 180)
        + "\n\nPart IV: Conclusion\n\n"
        + ("conclusion " * 110)
    )
    vague_heading_issues = _essay_quality_issues(
        vague_heading_essay,
        "2000 words essay on administrative law",
        is_short_single_essay=True,
        is_problem_mode=False,
    )
    print("Vague-heading essay issues:", vague_heading_issues)
    assert any("vague generic body part headings" in issue.lower() for issue in vague_heading_issues)
    vague_core_violation = detect_essay_core_policy_violation(
        vague_heading_essay,
        is_short_single_essay=True,
        forbid_title_line=True,
    )
    print("Vague-heading core violation:", vague_core_violation)
    assert vague_core_violation[0] is True
    assert "vague generic body-part headings" in vague_core_violation[1].lower()

    duplicate_intro_conclusion_text = (
        "Part I: Introduction\n\n"
        "Short opening.\n\n"
        "Part II: Analysis\n\n"
        "Doctrinal discussion.\n\n"
        "Part III: Introduction\n\n"
        "Repeated opening that should not exist.\n\n"
        "Part IV: Conclusion\n\n"
        "First ending.\n\n"
        "Part V: Conclusion\n\n"
        "Second ending.\n\n"
        "(End of Answer)"
    )
    duplicate_intro_conclusion_issues = _essay_quality_issues(
        duplicate_intro_conclusion_text,
        "2500 words essay on equity",
        is_short_single_essay=False,
        is_problem_mode=False,
    )
    print("Duplicate intro/conclusion issues:", duplicate_intro_conclusion_issues)
    assert any("more than one introduction heading" in issue.lower() for issue in duplicate_intro_conclusion_issues)
    assert any("more than one conclusion heading" in issue.lower() for issue in duplicate_intro_conclusion_issues)

    mixed_prompt = (
        "4000 words\n"
        "1. Administrative Law – Essay Question (Procedural vs Substantive Legitimate Expectation)\n"
        "Discuss the doctrine of legitimate expectation.\n\n"
        "2. Tort Law – Problem Question (Negligence and Psychiatric Harm)\n"
        "Advise CityRail on Sam, Priya and Jonah.\n"
    )
    mixed_part1_mode = _current_unit_mode_from_history(mixed_prompt, [])
    print("Mixed prompt part 1 mode:", mixed_part1_mode)
    assert mixed_part1_mode["is_essay_mode"] is True
    assert mixed_part1_mode["is_problem_mode"] is False

    mixed_part1_output = (
        "Question 1: Administrative Law – Essay Question (Procedural vs Substantive Legitimate Expectation)\n\n"
        "Part I: Introduction\n\n"
        "A. Issue\n\n"
        "The doctrine constrains abrupt administrative change."
    )
    mixed_part1_issues = _history_aware_structure_issues(mixed_part1_output, mixed_prompt, [])
    print("Mixed part 1 issues:", mixed_part1_issues)
    assert any("essay output uses problem-question irac subheadings" in i.lower() for i in mixed_part1_issues)
    assert any("final planned part for this question but has no visible conclusion heading" in i.lower() for i in mixed_part1_issues)

    mixed_messages = [
        {"role": "user", "text": mixed_prompt},
        {
            "role": "assistant",
            "text": (
                "Question 1: Administrative Law – Essay Question (Procedural vs Substantive Legitimate Expectation)\n\n"
                "Part I: Introduction\n\n"
                "Conclusion\n\n"
                "Will Continue to next part, say continue"
            ),
        },
        {"role": "user", "text": "continue"},
    ]
    mixed_part2_mode = _current_unit_mode_from_history("continue", mixed_messages)
    print("Mixed prompt part 2 mode:", mixed_part2_mode)
    assert mixed_part2_mode["is_problem_mode"] is True
    assert mixed_part2_mode["is_essay_mode"] is False

    valid_mixed_q2_output = (
        "Question 2: Tort Law – Problem Question (Negligence and Psychiatric Harm)\n\n"
        "Part I: Introduction\n\n"
        "This problem concerns duty, psychiatric harm, and remoteness.\n\n"
        "Part II: Duty and Breach\n\n"
        "A. Issue\n\n"
        "The first issue is whether Maya owes a duty of care.\n\n"
        "B. Rule\n\n"
        "The claimant must establish foreseeability, proximity, and fairness.\n\n"
        "C. Application\n\n"
        "On these facts, proximity is likely present.\n\n"
        "D. Conclusion\n\n"
        "Duty is likely established.\n\n"
        "Will Continue to next part, say continue"
    )
    valid_mixed_q2_issues = _history_aware_structure_issues(valid_mixed_q2_output, "continue", mixed_messages)
    print("Valid mixed q2 issues:", valid_mixed_q2_issues)
    assert not any("repeat the previous question" in i.lower() for i in valid_mixed_q2_issues)

    explicit_multi_target_prompt = (
        "3000 words\n"
        "1. Equity – Essay Question\n"
        "Discuss fiduciary duties.\n\n"
        "3000 words\n"
        "2. EU Law – Essay Question\n"
        "Discuss direct effect.\n"
    )
    explicit_multi_target_history_p1 = [
        {"role": "user", "text": explicit_multi_target_prompt},
        {
            "role": "assistant",
            "text": (
                "Part I: Introduction\n\n"
                "Equity introduces fiduciary obligation.\n\n"
                "Part II: Loyalty and No-Profit Rules\n\n"
                "The orthodox duties are strict.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
        {"role": "user", "text": "continue"},
    ]
    explicit_multi_target_state_p2 = _expected_unit_structure_state_from_history(
        "continue",
        explicit_multi_target_history_p1,
    )
    print("Explicit multi-target state for section 1 part 2:", explicit_multi_target_state_p2)
    assert explicit_multi_target_state_p2 is not None
    assert explicit_multi_target_state_p2["is_same_topic_continuation"] is True
    assert explicit_multi_target_state_p2["starts_new_question"] is False
    assert explicit_multi_target_state_p2["question_final_part"] is True
    assert explicit_multi_target_state_p2["expected_part_number"] == 3

    explicit_multi_target_history_sec2 = [
        {"role": "user", "text": explicit_multi_target_prompt},
        {
            "role": "assistant",
            "text": (
                "Part I: Introduction\n\n"
                "Equity introduces fiduciary obligation.\n\n"
                "Part II: Loyalty and No-Profit Rules\n\n"
                "The orthodox duties are strict.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
        {"role": "user", "text": "continue"},
        {
            "role": "assistant",
            "text": (
                "Part III: Accountability and Remedies\n\n"
                "Equity also responds through remedies.\n\n"
                "Part IV: Conclusion\n\n"
                "The fiduciary framework remains strict but coherent.\n\n"
                "(End of Answer)"
            ),
        },
        {"role": "user", "text": "continue"},
    ]
    explicit_multi_target_state_sec2 = _expected_unit_structure_state_from_history(
        "continue",
        explicit_multi_target_history_sec2,
    )
    print("Explicit multi-target state for section 2 part 1:", explicit_multi_target_state_sec2)
    assert explicit_multi_target_state_sec2 is not None
    assert explicit_multi_target_state_sec2["is_same_topic_continuation"] is False
    assert explicit_multi_target_state_sec2["starts_new_question"] is True
    assert explicit_multi_target_state_sec2["question_final_part"] is False
    assert explicit_multi_target_state_sec2["expected_part_number"] == 1

    for total_words in [2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000, 7500]:
        split_multi_prompt = (
            f"{total_words} words\n"
            "1. Equity – Essay Question\n"
            "Discuss fiduciary duties and accountability.\n\n"
            "2. Tort Law – Problem Question\n"
            "Advise on duty, breach, causation, and remedies.\n"
        )
        split_multi_state = _expected_unit_structure_state_from_history(split_multi_prompt, [])
        print(f"Split multi-question state ({total_words}):", split_multi_state)
        assert split_multi_state is not None
        assert split_multi_state["question_index"] == 1
        assert split_multi_state["starts_new_question"] is True
        assert split_multi_state["require_question_heading"] is True

    split_2500_prompt = (
        "2500 words\n"
        "1. Equity – Essay Question\n"
        "Discuss fiduciary duties and accountability.\n\n"
        "2. Tort Law – Problem Question\n"
        "Advise on duty, breach, causation, and remedies.\n"
    )
    split_2500_history = [
        {"role": "user", "text": split_2500_prompt},
        {
            "role": "assistant",
            "text": (
                "Question 1: Equity – Essay Question\n\n"
                "Part I: Introduction\n\n"
                "Fiduciary accountability is strict but contested.\n\n"
                "Part II: No-Profit and Loyalty\n\n"
                "The core fiduciary rules remain prophylactic.\n\n"
                "Part III: Conclusion\n\n"
                "The strict approach is justified but not cost-free.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
        {"role": "user", "text": "continue"},
    ]
    split_2500_next_state = _expected_unit_structure_state_from_history("continue", split_2500_history)
    print("2500-word next-question state:", split_2500_next_state)
    assert split_2500_next_state is not None
    assert split_2500_next_state["question_index"] == 2
    assert split_2500_next_state["starts_new_question"] is True
    assert split_2500_next_state["require_question_heading"] is True
    assert split_2500_next_state["expected_part_number"] == 1

    split_4500_prompt = (
        "4500 words\n"
        "1. Equity – Essay Question\n"
        "Discuss fiduciary duties and accountability.\n\n"
        "2. Tort Law – Problem Question\n"
        "Advise on duty, breach, causation, and remedies.\n"
    )
    split_4500_history = [
        {"role": "user", "text": split_4500_prompt},
        {
            "role": "assistant",
            "text": (
                "Question 1: Equity – Essay Question\n\n"
                "Part I: Introduction\n\n"
                "Fiduciary accountability is strict but contested.\n\n"
                "Part II: Loyalty and No-Profit Rules\n\n"
                "The core fiduciary rules remain prophylactic.\n\n"
                "Will Continue to next part, say continue"
            ),
        },
        {"role": "user", "text": "continue"},
    ]
    split_4500_next_state = _expected_unit_structure_state_from_history("continue", split_4500_history)
    print("4500-word same-question continuation state:", split_4500_next_state)
    assert split_4500_next_state is not None
    assert split_4500_next_state["question_index"] == 1
    assert split_4500_next_state["starts_new_question"] is False
    assert split_4500_next_state["require_question_heading"] is True

    spill_prompt = (
        "3000 words\n"
        "1. Human Rights – Essay Question (Article 8 ECHR)\n"
        "Discuss Article 8 ECHR, proportionality, and positive obligations.\n"
    )
    spill_history = [
        {"role": "user", "text": spill_prompt},
        {
            "role": "assistant",
            "text": (
                "Part I: Introduction\n\n"
                "Part II: Scope\n\n"
                "Will Continue to next part, say continue"
            ),
        },
        {"role": "user", "text": "continue"},
    ]
    spill_output = (
        "Part III: Conclusion\n\n"
        "The Court's approach remains flexible but structured.\n\n"
        "Introduction This problem question concerns the sale of machinery and statutory implied terms. "
        "The buyer may rely on satisfactory quality, fitness for purpose, and description."
    )
    spill_issues = _history_aware_structure_issues(spill_output, "continue", spill_history)
    print("Post-conclusion spill issues:", spill_issues)
    assert any(
        ("content continues after a conclusion heading" in i.lower())
        or ("fresh introduction or new question begins after the conclusion" in i.lower())
        for i in spill_issues
    )

    sparse_citation_text = (
        "Part I: Introduction\n\n"
        + ("Article 8 protects private life and requires a structured proportionality analysis. " * 80)
        + "(Article 8 ECHR).\n\n"
        "Part II: Conclusion\n\n"
        "The better view is that the right remains open-textured but not unbounded."
    )
    sparse_citation_issues = _essay_quality_issues(
        sparse_citation_text,
        "1200 words\n1. Human Rights – Essay Question\nDiscuss Article 8 ECHR.",
        False,
        is_problem_mode=False,
    )
    print("Sparse citation issues:", sparse_citation_issues)
    assert any("citation density is too thin" in i.lower() for i in sparse_citation_issues)

    rs = RAGService()
    reject = rs._hard_legal_result_reject(
        query="Advise on UK criminal self-defence law.",
        query_type="pb_2000",
        metadata={"document_name": "Unknown Notes", "category": "General"},
        content="United States federal antitrust analysis in D.D.C under Sherman Act and DOJ policy.",
    )
    print("UK criminal query rejects US-antitrust chunk:", reject)
    assert reject is True

    print("All output-quality guard checks passed.")


if __name__ == "__main__":
    run()
