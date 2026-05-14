"""
Cross-subject complete-answer contract checks.

These tests do not call a live model. They verify that representative legal
subjects receive the same complete-answer stack: indexed RAG policy, subject
guide/code-guide anchors, online-search fallback policy, inline OSCOLA, and the
high-first specialist accuracy pass.
"""

from __future__ import annotations

import os

import model_applicable_service as service


PROMPTS = [
    ("competition", "Competition Law problem: UK online marketplace self-preferencing, third-party seller data, tying, wide price parity, Chapter II Competition Act 1998, Article 102 TFEU and DMCC strategic market status.", "competition_abuse_dominance"),
    ("medicine", "Law and Medicine problem: professional violinist was not warned of right-wrist stiffness risk; surgeon also performs non-urgent left-hand procedure without consent; advise on Montgomery, battery, necessity, causation and damages.", "medical_consent_capacity"),
    ("occupiers", "Tort Law problem: child trespasser injured in unstable shed and jogger injured by unlit lake path; advise on Occupiers' Liability Act 1957 and 1984, warnings, age, obvious risk, causation and damages.", "tort_occupiers_liability"),
    ("sovereignty", "Constitutional Law essay: critically evaluate parliamentary sovereignty, constitutional statutes, devolution, Human Rights Act 1998, judicial review and post-Brexit assimilated EU law.", "constitutional_prerogative_justiciability"),
    ("land_trusts", "Equity and Land Law problem: sole registered owner, unmarried partner, common intention constructive trust, proprietary estoppel, actual occupation, overriding interest, overreaching and mortgagee sale.", "land_home_coownership_estoppel_priority"),
    ("automated_public_law", "Public Law and Data Governance essay: automated public decision-making, Article 8 ECHR, Article 14 ECHR, UK GDPR, Data Protection Act 2018, Article 22, meaningful human involvement and remedies.", "public_law_automated_decision_making"),
    ("evidence", "Evidence Law problem: visual identification, PACE Code D, confession after pressure, hearsay, bad character, expert facial mapping and Article 6 fairness.", "evidence_admissibility_fair_trial"),
    ("private_international", "Private International Law problem: jurisdiction clause, service out, Rome I, Rome II, forum non conveniens, anti-suit relief and enforcement.", "private_international_law_post_brexit"),
    ("contract", "Contract Law problem: misrepresentation, exclusion clause, breach, repudiation, rescission, damages and Consumer Rights Act 2015 controls.", "contract_misrepresentation_exclusion"),
    ("employment", "Employment Law problem: worker status, unfair dismissal, redundancy, discrimination, restrictive covenant and remedies.", "employment_redundancy_unfair_dismissal"),
    ("criminal", "Criminal Law problem: non-fatal offences, sporting consent, self-defence, causation and transferred malice.", "criminal_nonfatal_offences_self_defence"),
    ("ip", "Intellectual Property Law problem: AI copyright, trade mark infringement, passing off, patent obviousness and remedies.", "patent_validity_infringement_ownership"),
    ("tax", "Tax Law problem in 2026: VAT, HMRC discovery assessment, GAAR, CGT relief, penalties and appeal route.", "tax_avoidance_gaar"),
]


RICH_RAG = (
    "[RAG CONTEXT - INTERNAL - DO NOT OUTPUT]\n"
    "Occupiers' Liability Act 1957, s 2(2). Occupiers' Liability Act 1984, ss 1(3)-1(5). "
    "Jolley v Sutton London Borough Council [2000] 1 WLR 1082. Tomlinson v Congleton Borough Council [2003] UKHL 47. "
    "Competition Act 1998, s 18. Case C-48/22 P Google LLC and Alphabet Inc v Commission ECLI:EU:C:2024:726. "
    "Montgomery v Lanarkshire Health Board [2015] UKSC 11. Chester v Afshar [2004] UKHL 41. "
    "Land Registration Act 2002, sch 3 para 2. Stack v Dowden [2007] UKHL 17. Jones v Kernott [2011] UKSC 53. "
    "Human Rights Act 1998, ss 3-4. UK GDPR, art 22. Data Protection Act 2018. "
    "Police and Criminal Evidence Act 1984. Criminal Justice Act 2003. Consumer Rights Act 2015. "
    "European Union (Withdrawal) Act 2018. Retained EU Law (Revocation and Reform) Act 2023. "
    "[END RAG CONTEXT]\n"
    + ("Authority support for cross-subject prompt-contract testing. " * 500)
)


captured = []


def fake_rag(query, max_chunks=None, query_type=None):
    return RICH_RAG


def fake_local_adapter(*, full_message, system_instruction, history, project_id, allow_web_search):
    captured.append(
        {
            "project_id": project_id,
            "full_message": full_message,
            "system_instruction": system_instruction,
            "allow_web_search": allow_web_search,
        }
    )
    return (
        "Part I: Introduction\n\n"
        "This cross-subject contract output is intentionally synthetic and verifies prompt wiring only "
        "(Competition Act 1998, s 18).\n\n"
        "Part II: Final Conclusion\n\n"
        "The response ends with a real conclusion placeholder for the contract test.\n\n"
        "(End of Answer)"
    )


originals = {
    "RAG_AVAILABLE": service.RAG_AVAILABLE,
    "get_relevant_context": service.get_relevant_context,
    "_find_codex_cli": service._find_codex_cli,
    "_codex_exec_supports_option": service._codex_exec_supports_option,
    "_generate_with_codex_local_adapter": service._generate_with_codex_local_adapter,
}
original_env = {
    "LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED": os.environ.get("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"),
    "LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE": os.environ.get("LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"),
}

try:
    service.RAG_AVAILABLE = True
    service.get_relevant_context = fake_rag
    service._find_codex_cli = lambda: "codex"
    service._codex_exec_supports_option = lambda cli, option: option == "--search"
    service._generate_with_codex_local_adapter = fake_local_adapter
    os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = "1"
    os.environ["LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"] = "1"

    for name, prompt, expected_topic in PROMPTS:
        profile = service._infer_retrieval_profile(prompt)
        assert profile.get("topic") == expected_topic, (name, profile.get("topic"), expected_topic)
        assert profile.get("must_cover"), name
        assert profile.get("source_mix_min"), name
        assert profile.get("source_type_hint"), name
        assert service._backend_online_search_fallback_decision(query=prompt, rag_context="")["use_online_search"] is True

        captured.clear()
        (response, meta), rag_context = service.send_message_with_docs(
            api_key="",
            message=prompt,
            documents=[],
            project_id=f"cross-subject-quality-{name}",
            history=[],
            stream=False,
            provider="auto",
            model_name=None,
            enforce_long_response_split=False,
        )

        assert meta == []
        assert "(End of Answer)" in response
        assert "[RAG CONTEXT" in rag_context
        assert len(captured) == 1
        full_message = captured[0]["full_message"]
        combined_prompt = full_message + "\n" + captured[0]["system_instruction"]
        assert "[LOCAL CODE + RAG LEGAL ANSWER MODE]" in full_message
        assert "[MANDATORY BACKEND RAG POLICY]" in full_message
        assert "Use indexed RAG material first." in full_message
        assert "Complete-answer requests must run the Codex supervisor workflow" in full_message
        assert "Complete-answer mode is always a Codex supervisor workflow" in full_message
        assert "Matched subject guide anchors:" in full_message
        assert "Additional quality-control anchors:" in full_message
        assert "High-first specialist answer pass before output" in full_message
        assert "Use full OSCOLA citations in parentheses immediately after the relevant sentence" in full_message
        assert "Do NOT add a bibliography/source list unless the user expressly asks for one" in combined_prompt
        assert "Before finalising any legal answer, run a specialist accuracy pass" in combined_prompt
finally:
    service.RAG_AVAILABLE = originals["RAG_AVAILABLE"]
    service.get_relevant_context = originals["get_relevant_context"]
    service._find_codex_cli = originals["_find_codex_cli"]
    service._codex_exec_supports_option = originals["_codex_exec_supports_option"]
    service._generate_with_codex_local_adapter = originals["_generate_with_codex_local_adapter"]
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


print("Cross-subject complete-answer quality contract checks passed.")
