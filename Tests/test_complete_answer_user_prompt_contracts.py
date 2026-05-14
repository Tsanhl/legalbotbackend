import os

import model_applicable_service as service


PROMPTS = [
    (
        "tort_occupiers_liability",
        """Tort Law — Problem Question

Word target: about 1,500-2,000 words

Riverside Council owns a public park containing a children's play area, a boating lake, and a disused maintenance shed. The Council knows that the fence around the lake has been broken for several months; the shed is sometimes entered by teenagers despite warning signs; staff reported that the shed roof was unstable; and previous complaints had been made about poor lighting near the lake path.

One evening, 13-year-old Mia enters the shed with friends and is injured when part of the roof collapses. Later the same night, Daniel, an adult jogger, slips near the lake path and falls into shallow water, suffering a serious leg injury. The Council argues that Mia was trespassing, Daniel should have used a torch, and that warning signs near the shed were enough.

Advise Mia and Daniel.

In your answer, consider occupiers' liability to visitors and trespassers; the Occupiers' Liability Act 1957 and 1984; foreseeability of harm; warnings; contributory negligence; the relevance of age and obvious risks; and likely remedies.""",
        ["Occupiers' Liability Act 1957", "Occupiers' Liability Act 1984", "TORT LAW"],
    ),
    (
        "constitutional_sovereignty",
        """Constitutional Law — Essay Question

Word target: about 1,500-2,000 words

Critically evaluate whether parliamentary sovereignty remains the central principle of the UK constitution.

In your answer, consider the orthodox Diceyan view of parliamentary sovereignty; the relationship between parliamentary sovereignty and the rule of law; constitutional statutes; devolution; the Human Rights Act 1998; judicial review; retained EU law and post-Brexit constitutional change; and whether modern constitutional practice has transformed, limited, or merely qualified parliamentary sovereignty.""",
        ["parliamentary sovereignty", "Human Rights Act 1998", "constitutional"],
    ),
    (
        "equity_trusts_land_home",
        """Equity / Trusts / Land Law — Problem Question

Word target: about 3,500 words

Maya and Daniel are unmarried partners. Daniel buys Rosewood House, a registered freehold property, in his sole name. Maya is not put on the legal title because she has recently become self-employed and Daniel says that the mortgage will be easier if it is just in his name.

Before completion, Daniel tells Maya: "This is our home. The paperwork is only in my name, but half of the house is really yours."

Over the next eight years, Maya pays GBP85,000 from an inheritance towards a loft conversion and structural repairs; she makes several bank transfers to Daniel, some marked "mortgage help"; she pays most household bills and childcare costs; she gives up full-time work for three years to care for Daniel's elderly father; and Daniel repeatedly refers to the property in texts and emails as "our house" and "our family home."

Daniel later secretly grants a legal charge over Rosewood House to Northbank Finance Ltd. Northbank's surveyor sees Maya living there, notices children belongings and family photographs, and is told by a neighbour that Maya has lived there for years. Northbank makes no enquiry of Maya. Daniel defaults. Northbank seeks possession and sale.

Advise Maya, Daniel, and Northbank Finance Ltd. Consider common intention constructive trust; resulting trust; proprietary estoppel; express assurance; financial, domestic, and caring contributions; quantification; actual occupation and overriding interests under the Land Registration Act 2002; failure to enquire; overreaching; mortgagee remedies; Maya's remedies; and practical outcome.""",
        ["Land Registration Act 2002", "common intention constructive trust", "actual occupation"],
    ),
    (
        "public_law_ai_data_governance",
        """Public Law / Human Rights / Data Governance — Essay Question

Word target: about 4,000 words

Critically evaluate whether modern public law in the United Kingdom provides adequate control over automated and data-driven public decision-making.

In your answer, discuss the constitutional foundations of judicial review; legality, rationality, procedural fairness, and the duty to give reasons; algorithmic tools by public authorities; transparency and explainability; fettering discretion through automated recommendations; human review and lawful decision-making; Article 8 ECHR and informational privacy; Article 14 ECHR and discrimination; proportionality under the Human Rights Act 1998; data protection principles under the UK GDPR and Data Protection Act 2018; automated decision-making safeguards; legitimate expectations and public trust; remedies including quashing orders, declarations, injunctions and damages; and whether existing public law tools are sufficient or whether specific statutory reform is needed.""",
        ["Article 8 ECHR", "UK GDPR", "Data Protection Act 2018"],
    ),
]


def fake_rag(query, max_chunks=None, query_type=None):
    return (
        "[RAG CONTEXT - INTERNAL - DO NOT OUTPUT]\n"
        "Occupiers' Liability Act 1957; Occupiers' Liability Act 1984; Tomlinson v Congleton Borough Council [2003] UKHL 47.\n"
        "Parliamentary sovereignty; R (Jackson) v Attorney General [2005] UKHL 56; Human Rights Act 1998; European Union (Withdrawal) Act 2018.\n"
        "Stack v Dowden [2007] UKHL 17; Jones v Kernott [2011] UKSC 53; Williams & Glyn's Bank Ltd v Boland [1981] AC 487; Land Registration Act 2002 sch 3 para 2.\n"
        "R (Bridges) v Chief Constable of South Wales Police [2020] EWCA Civ 1058; Human Rights Act 1998; UK GDPR; Data Protection Act 2018.\n"
        "[END RAG CONTEXT]"
    )


captured = []


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
        "This is a complete-answer prompt-contract test output. The generated answer must use the compiled RAG, subject guide, and inline OSCOLA rules. "
        "The relevant statutory and case-law propositions must be supported immediately after the sentence (Occupiers' Liability Act 1957, s 2; Occupiers' Liability Act 1984, s 1).\n\n"
        "Part II: Conclusion\n\n"
        "The backend returned chat text without creating a project artifact.\n\n"
        "(End of Answer)"
    )


original_rag_available = service.RAG_AVAILABLE
original_get_relevant_context = service.get_relevant_context
original_find_codex_cli = service._find_codex_cli
original_codex_exec_supports_option = service._codex_exec_supports_option
original_local_adapter = service._generate_with_codex_local_adapter
original_env = {
    "LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED": os.environ.get("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"),
    "LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE": os.environ.get("LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"),
}

try:
    service.RAG_AVAILABLE = True
    service.get_relevant_context = fake_rag
    service._find_codex_cli = lambda: "codex"
    service._codex_exec_supports_option = lambda _cli, option: option == "--search"
    service._generate_with_codex_local_adapter = fake_local_adapter
    os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = "1"
    os.environ["LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"] = "1"

    for name, prompt, expected_snippets in PROMPTS:
        captured.clear()
        (response, meta), rag_context = service.send_message_with_docs(
            api_key="",
            message=prompt,
            documents=[],
            project_id=f"complete-answer-contract-{name}",
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
        assert "[DIRECT-CODE / BACKEND DELIVERY MODE]" in full_message
        assert "[LOCAL CODE + RAG LEGAL ANSWER MODE]" in full_message
        assert "[MANDATORY BACKEND RAG POLICY]" in full_message
        assert "Use indexed RAG material first." in full_message
        assert "Complete-answer requests must run the Codex supervisor workflow" in full_message
        assert "Complete-answer mode is always a Codex supervisor workflow" in full_message
        assert "Matched subject guide anchors:" in full_message
        assert "Additional quality-control anchors:" in full_message
        assert "Use full OSCOLA citations in parentheses immediately after the relevant sentence" in full_message
        assert "EVERY parenthetical authority reference must be full OSCOLA" in full_message
        assert "Do NOT solve citation risk by deleting citations" in full_message
        assert "Part I" in full_message or "issue" in full_message.lower()
        for snippet in expected_snippets:
            assert snippet in full_message
finally:
    service.RAG_AVAILABLE = original_rag_available
    service.get_relevant_context = original_get_relevant_context
    service._find_codex_cli = original_find_codex_cli
    service._codex_exec_supports_option = original_codex_exec_supports_option
    service._generate_with_codex_local_adapter = original_local_adapter
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


print("Complete-answer user prompt contract checks passed.")
