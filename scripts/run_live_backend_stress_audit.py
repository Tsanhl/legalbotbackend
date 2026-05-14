#!/usr/bin/env python3
"""
Run a broader live backend stress audit with self-drafted realistic prompts.

This complements run_live_backend_audit.py. It targets prompts that are likely
to reveal generic, over-broad, legally thin, or source-leaking outputs:

- Law and Medicine course-bound essay variants.
- Law and Medicine no-limit / current-law sensitive essays.
- Competition Article 102 economic problem variants.
- SQE2 hard task generation across written skills.
- SQE2 marking of weak candidate answers.

Privacy guard: live runs can send prompts plus retrieved RAG/course-material
context to the configured external model provider. For that reason, real model
calls require:

    LEGAL_AI_LIVE_AUDIT_SEND_EXTERNAL=1
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend_answer_runtime import (  # noqa: E402
    send_complete_answer_with_docs,
    send_sqe2_marking_with_docs,
    send_sqe_question_set_with_docs,
)

_PROVIDER_ENV_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "xai": "XAI_API_KEY",
}

_PROVIDER_ALIASES = {
    "google": "gemini",
    "google ai": "gemini",
    "gemini api": "gemini",
    "chatgpt": "openai",
    "gpt": "openai",
    "openai api": "openai",
    "claude": "anthropic",
    "anthropic api": "anthropic",
    "x.ai": "xai",
    "grok": "xai",
}

_PLACEHOLDER_KEY_MARKERS = (
    "placeholder",
    "replace_me",
    "change_me",
    "your_api_key",
    "your_gemini_api_key",
    "your_openai_api_key",
    "your_anthropic_api_key",
    "api_key_here",
    "enter_api_key",
    "paste_api_key",
)


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _normalise_provider_name(provider: str) -> str:
    raw = (provider or "").strip().lower()
    normalised = _PROVIDER_ALIASES.get(raw, raw)
    return normalised if normalised in _PROVIDER_ENV_KEYS else "gemini"


def _is_placeholder_api_key(api_key: str) -> bool:
    key = (api_key or "").strip()
    if not key:
        return False
    normalised = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
    return any(marker in normalised for marker in _PLACEHOLDER_KEY_MARKERS)


def _resolve_live_provider_config() -> Dict[str, str]:
    provider = _normalise_provider_name(
        os.getenv("LEGAL_AI_LIVE_AUDIT_PROVIDER")
        or os.getenv("LEGAL_AI_PROVIDER")
        or "gemini"
    )
    key_env = (
        os.getenv("LEGAL_AI_LIVE_AUDIT_API_KEY_ENV")
        or _PROVIDER_ENV_KEYS.get(provider, "")
    ).strip()
    api_key = (
        os.getenv("LEGAL_AI_LIVE_AUDIT_API_KEY", "")
        or (os.getenv(key_env, "") if key_env else "")
    ).strip()
    model_name = (
        os.getenv("LEGAL_AI_LIVE_AUDIT_MODEL", "")
        or os.getenv(f"{provider.upper()}_MODEL", "")
    ).strip()
    return {
        "provider": provider,
        "api_key": api_key,
        "key_env": key_env,
        "model_name": model_name,
    }


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text or ""))


def _contains_any(text: str, needles: List[str]) -> bool:
    low = (text or "").lower()
    return any(n.lower() in low for n in needles)


def _contains_all(text: str, needles: List[str]) -> bool:
    low = (text or "").lower()
    return all(n.lower() in low for n in needles)


def _no_source_leakage(text: str) -> bool:
    low = (text or "").lower()
    leaked_markers = [
        "/users/",
        "/desktop/",
        "rag context",
        "retrieved chunk",
        "source path",
        "law resouces",
        "learnultra",
    ]
    return not any(marker in low for marker in leaked_markers)


def _not_generic(text: str) -> bool:
    return _contains_any(text, ["because", "therefore", "the better view", "on these facts", "risk", "reform"])


def _score_output(name: str, text: str) -> Dict[str, Any]:
    low = (text or "").lower()
    common = {
        "substantive_length": _word_count(text) >= 300,
        "no_source_leakage": _no_source_leakage(text),
        "not_generic": _not_generic(text),
    }
    checks: Dict[str, bool]
    if name == "law_med_abortion_course":
        checks = {
            **common,
            "course_bound": _contains_any(text, ["course-bound", "module syllabus", "within the syllabus", "syllabus"]),
            "uses_abortion_act": _contains_any(text, ["Abortion Act 1967", "Abortion Act", "AA 1967"]),
            "covers_fetal_abnormality_ground": _contains_any(text, ["s.1(1)(d)", "section 1(1)(d)", "fetal abnormality", "foetal abnormality"]),
            "covers_social_ground": _contains_any(text, ["s.1(1)(a)", "section 1(1)(a)", "social ground"]),
            "has_reform_thesis": _contains_any(text, ["reform", "legislative reform", "discrimination", "disability"]),
            "avoids_excluded_drift": not _contains_any(text, ["clinical negligence", "mental health law", "deprivation of liberty"]),
        }
    elif name == "law_med_hfea_course":
        checks = {
            **common,
            "course_bound": _contains_any(text, ["course-bound", "module syllabus", "within the syllabus", "syllabus"]),
            "uses_hfea": _contains_any(text, ["Human Fertilisation and Embryology Act 1990", "HFEA 1990", "HFEA"]),
            "uses_welfare_child": _contains_any(text, ["s.13(5)", "section 13(5)", "welfare of the child"]),
            "uses_pgt_or_embryo": _contains_any(text, ["PGT", "preimplantation", "embryo", "embryos"]),
            "has_reform_thesis": _contains_any(text, ["unfit", "fit for purpose", "reform", "ripe for reform"]),
        }
    elif name == "law_med_assisted_no_limit":
        checks = {
            **common,
            "labels_no_limit": _contains_any(text, ["no syllabus", "no-limit", "wider", "broader", "not confined"]),
            "current_law_caution": _contains_any(text, ["current", "verify", "bill", "recent", "as at", "status"]),
            "autonomy_and_safeguards": _contains_all(text, ["autonomy", "safeguard"]),
            "article_or_hra": _contains_any(text, ["Article 8", "Human Rights Act", "HRA"]),
        }
    elif name == "competition_margin_squeeze":
        checks = {
            **common,
            "dominance": "dominance" in low,
            "margin_squeeze": _contains_any(text, ["margin squeeze", "price-cost", "spread", "as-efficient", "AEC"]),
            "refusal_access": _contains_any(text, ["refusal", "access", "indispensable", "essential"]),
            "effects_evidence": _contains_any(text, ["effects", "foreclosure", "counterfactual", "evidence"]),
            "objective_justification": _contains_any(text, ["objective justification", "efficiencies", "justification"]),
            "remedy": _contains_any(text, ["remedy", "commitment", "fine", "enforcement"]),
        }
    elif name == "competition_exclusive_data":
        checks = {
            **common,
            "dominance": "dominance" in low,
            "exclusive_or_loyalty": _contains_any(text, ["exclusive", "exclusivity", "loyalty", "rebate"]),
            "data_or_interop": _contains_any(text, ["data", "interoperability", "API", "access"]),
            "effect_analysis": _contains_any(text, ["effects", "foreclosure", "counterfactual", "evidence"]),
            "justification": _contains_any(text, ["objective justification", "efficiencies", "security", "privacy"]),
        }
    elif name == "land_registered_priority":
        checks = {
            **common,
            "registered_status": _contains_any(text, ["registered land", "LRA 2002", "Land Registration Act 2002"]),
            "registrable_disposition": _contains_any(text, ["s.27", "section 27", "registrable disposition"]),
            "priority": _contains_any(text, ["s.29", "section 29", "priority"]),
            "actual_occupation": _contains_any(text, ["actual occupation", "Schedule 3", "para 2", "paragraph 2"]),
            "overreaching": _contains_any(text, ["overreaching", "LPA 1925", "ss.2", "section 2"]),
            "separate_rights": _contains_any(text, ["option", "easement", "lease", "restriction", "notice"]),
        }
    elif name == "tort_psychiatric_public_authority":
        checks = {
            **common,
            "recognised_psychiatric_injury": _contains_any(text, ["recognised psychiatric", "psychiatric illness", "mere distress"]),
            "primary_secondary": _contains_all(text, ["primary", "secondary"]),
            "alcock_controls": _contains_any(text, ["Alcock", "control mechanisms", "proximity", "sudden"]),
            "public_authority_route": _contains_any(text, ["public authority", "police", "ambulance", "fire service"]),
            "omissions_policy": _contains_any(text, ["omission", "operational", "policy", "resource"]),
            "remedy_or_outcome": _contains_any(text, ["damages", "liable", "duty", "unlikely"]),
        }
    elif name == "business_company_conflict_insolvency":
        checks = {
            **common,
            "directors_duties": _contains_any(text, ["s.172", "section 172", "s.175", "section 175", "directors' duties"]),
            "approval_conflict": _contains_any(text, ["conflict", "Model Articles", "quorum", "declaration"]),
            "spt_or_related_party": _contains_any(text, ["substantial property", "s.190", "section 190", "related-party"]),
            "shareholder_routes": _contains_any(text, ["derivative", "unfair prejudice", "ratification"]),
            "insolvency_creditors": _contains_any(text, ["creditor", "insolvency", "wrongful trading", "liquidation"]),
            "remedies": _contains_any(text, ["account of profit", "rescission", "indemnify", "compensation"]),
        }
    elif name == "trusts_purpose_secret_tracing":
        checks = {
            **common,
            "beneficiary_principle": _contains_any(text, ["beneficiary principle", "Morice", "purpose trust"]),
            "three_certainties": _contains_any(text, ["three certainties", "certainty of intention", "certainty of subject", "certainty of objects"]),
            "secret_trust": _contains_any(text, ["secret trust", "communication", "acceptance"]),
            "tracing_or_proprietary": _contains_any(text, ["tracing", "proprietary", "mixed fund", "substitute asset"]),
            "perpetuity_capricious": _contains_any(text, ["perpetuity", "capricious", "administrative unworkability"]),
            "remedy_consequence": _contains_any(text, ["resulting trust", "personal claim", "proprietary claim", "insolvency"]),
        }
    elif name == "evidence_hearsay_bad_character":
        checks = {
            **common,
            "classifies_evidence": _contains_any(text, ["hearsay", "bad character", "confession", "identification"]),
            "statutory_gateway": _contains_any(text, ["gateway", "CJA 2003", "Criminal Justice Act 2003", "PACE"]),
            "fairness_exclusion": _contains_any(text, ["s.78", "section 78", "fairness", "Article 6"]),
            "admissibility_weight": _contains_all(text, ["admissib", "weight"]),
            "direction_or_safeguard": _contains_any(text, ["direction", "warning", "safeguard", "edited"]),
            "likely_ruling": _contains_any(text, ["likely", "admit", "exclude", "ruling"]),
        }
    elif name == "public_law_legitimate_expectation":
        checks = {
            **common,
            "power_source": _contains_any(text, ["statutory power", "power source", "decision-maker", "amenability"]),
            "legitimate_expectation": _contains_any(text, ["legitimate expectation", "representation", "promise", "practice"]),
            "clarity_reliance_fairness": _contains_any(text, ["clear", "unambiguous", "reliance", "fairness"]),
            "overriding_interest": _contains_any(text, ["overriding public interest", "public interest", "frustrate"]),
            "remedy_discretion": _contains_any(text, ["quashing", "declaration", "mandatory", "discretionary"]),
            "not_merits_review": _contains_any(text, ["merits", "legality", "review intensity", "intensity"]),
        }
    elif name == "criminal_sports_consent_transferred_malice":
        checks = {
            **common,
            "offence_selection": _contains_any(text, ["s.47", "section 47", "s.20", "section 20", "assault", "battery"]),
            "ar_mr": _contains_all(text, ["actus reus", "mens rea"]),
            "sports_consent": _contains_any(text, ["consent", "sports", "Barnes", "within the game"]),
            "transferred_malice": _contains_any(text, ["transferred malice", "Latimer", "unintended victim"]),
            "causation": _contains_any(text, ["causation", "but for", "legal causation"]),
            "ranked_outcome": _contains_any(text, ["strong", "arguable", "weak", "likely", "unlikely"]),
        }
    elif name == "pensions_nra_equalisation":
        checks = {
            **common,
            "barber_window": _contains_any(text, ["Barber", "Barber window", "17 May 1990", "equalisation"]),
            "nra_and_scheme_amendment": _contains_any(text, ["normal retirement age", "NRA", "scheme amendment", "amending power"]),
            "accrued_rights": _contains_any(text, ["section 67", "s.67", "accrued rights", "subsisting rights"]),
            "calculation_visible": _contains_any(text, ["worked", "calculation", "period", "tranche", "before", "after"]),
            "registration_tax_consent": _contains_any(text, ["registered", "tax", "consent", "actuarial", "certificate"]),
            "trustee_next_steps": _contains_any(text, ["trustee", "next step", "deed", "member", "records"]),
        }
    elif name == "pensions_non_financial_investment":
        checks = {
            **common,
            "trustee_power_purpose": _contains_any(text, ["trustee", "investment power", "scheme purpose", "best interests"]),
            "financial_vs_non_financial": _contains_any(text, ["financial factor", "non-financial", "ethical", "ESG"]),
            "member_consensus": _contains_any(text, ["member", "consensus", "survey", "beneficiaries", "deferred"]),
            "financial_detriment": _contains_any(text, ["financial detriment", "risk-adjusted", "return", "covenant"]),
            "db_dc_distinction": _contains_any(text, ["defined benefit", "DB", "defined contribution", "DC", "employer covenant"]),
            "decision_process": _contains_any(text, ["minutes", "advice", "investment consultant", "statement of investment principles", "SIP"]),
        }
    elif name == "mediation_singapore_convention":
        checks = {
            **common,
            "singapore_convention": _contains_any(text, ["Singapore Convention", "Singapore Convention on Mediation"]),
            "ny_convention_benchmark": _contains_any(text, ["New York Convention", "arbitration", "award"]),
            "enforceability_gap": _contains_any(text, ["enforceability gap", "cross-border", "settlement agreement"]),
            "article_5_defences": _contains_any(text, ["Article 5", "serious breach", "mediator", "public policy"]),
            "confidentiality_tension": _contains_any(text, ["confidentiality", "evidence", "disclosure", "privilege"]),
            "reform_or_protocol": _contains_any(text, ["reform", "protocol", "safe harbour", "standards"]),
        }
    elif name == "mediation_process_problem":
        checks = {
            **common,
            "agreement_to_mediate": _contains_any(text, ["agreement to mediate", "stay", "condition precedent", "enforceable"]),
            "process_and_conduct": _contains_any(text, ["mediator", "impartial", "conflict", "process"]),
            "confidentiality_privilege": _contains_any(text, ["confidentiality", "without prejudice", "privilege"]),
            "settlement_enforcement": _contains_any(text, ["settlement agreement", "enforce", "consent order", "contract"]),
            "cross_border_route": _contains_any(text, ["Singapore Convention", "cross-border", "seat", "jurisdiction"]),
            "practical_advice": _contains_any(text, ["next step", "draft", "advise", "risk"]),
        }
    elif name.startswith("sqe2_task_"):
        checks = {
            **common,
            "task_scaffold": _contains_all(text, ["candidate instructions", "client/matter facts", "documents/extracts", "specific task"]),
            "withholds_answers": not _contains_any(text, ["model answer", "correct answer", "marking points"]),
            "hard_traps": _contains_any(text, ["professional conduct", "missing", "ambiguity", "timing", "trap", "evidence gap"]),
        }
    elif name.startswith("sqe2_marking_"):
        checks = {
            **common,
            "starts_marking_result": low.strip().startswith("sqe2 marking result"),
            "criterion_scoring": _contains_any(text, ["criterion", "criteria"]) and _contains_any(text, ["A-F", "score", "subtotal"]),
            "corrected_answer": _contains_any(text, ["corrected", "high-scoring", "model answer", "outline"]),
            "next_targeted_practice": "next targeted practice" in low,
            "not_too_generous": _contains_any(text, ["below pass", "borderline", "D", "E", "F"]),
        }
    else:
        checks = common
    return {
        "word_count": _word_count(text),
        "checks": checks,
        "passed": bool(checks) and all(checks.values()),
    }


def _response_text(response: Any) -> str:
    if isinstance(response, tuple) and response:
        return str(response[0] or "")
    return str(response or "")


def _cases() -> List[Dict[str, str]]:
    return [
        {
            "name": "law_med_abortion_course",
            "kind": "complete",
            "prompt": (
                "Law and Medicine essay. Stay within the module syllabus. Critically examine the view that abortion "
                "on grounds of fetal abnormality is in need of legislative reform. Use only the course materials' "
                "type of structure: precise statutory route, two or three focused points, and a clear thesis. Return about 900 words."
            ),
        },
        {
            "name": "law_med_hfea_course",
            "kind": "complete",
            "prompt": (
                "Law and Medicine essay. Stay within the module syllabus. Critically examine whether the Human "
                "Fertilisation and Embryology Act 1990 is unfit for the purpose of governing assisted reproduction. "
                "Focus on the Act's regulatory architecture, welfare of the child, PGT/embryo selection, and reform. Return about 900 words."
            ),
        },
        {
            "name": "law_med_assisted_no_limit",
            "kind": "complete",
            "prompt": (
                "Law and Medicine no syllabus limit / broad-all essay. Critically examine whether English law should "
                "recognise assisted dying for capacitous adults with terminal illness. Label wider material and add current-law caution. "
                "Use autonomy, sanctity of life, vulnerability safeguards, Article 8/HRA and institutional competence. Return about 900 words."
            ),
        },
        {
            "name": "competition_margin_squeeze",
            "kind": "complete",
            "prompt": (
                "Competition Law problem question. Advise a dominant wholesale network operator that also sells retail services. "
                "It sets wholesale access prices close to retail prices, delays API access to retail rivals, and argues network "
                "security and investment incentives. Address Article 102 / Chapter II, market definition, dominance, margin squeeze, "
                "refusal/access, effects evidence, objective justification, and remedy. Return about 900 words."
            ),
        },
        {
            "name": "competition_exclusive_data",
            "kind": "complete",
            "prompt": (
                "Competition Law problem question. A dominant app-store platform imposes exclusive default placement on device makers, "
                "restricts rival wallet interoperability data, and says the restrictions protect privacy and fraud prevention. "
                "Advise under Article 102 / Chapter II using economic evidence, foreclosure, counterfactual, objective justification, "
                "and likely commitments/remedies. Return about 900 words."
            ),
        },
        {
            "name": "land_registered_priority",
            "kind": "complete",
            "prompt": (
                "Land Law problem question. Advise a purchaser of registered land. Before completion: an express easement was granted "
                "but not registered; a 10-year lease and an option to purchase were granted to an occupier; a non-owning partner "
                "contributed to purchase price and lives at the property; sale proceeds were paid to two trustees; no restriction or notice "
                "appears on the register. Analyse LRA 2002/LPA 1925 priority, actual occupation, overreaching, options/easements, and remedies. "
                "Return about 900 words."
            ),
        },
        {
            "name": "tort_psychiatric_public_authority",
            "kind": "complete",
            "prompt": (
                "Tort Law problem question. A police call handler records repeated threats from a known offender but officers do not attend. "
                "Later, during an arrest operation, officers negligently knock an elderly bystander over. The victim's sibling watches a live "
                "phone video shortly after and develops PTSD; an officer involved also develops PTSD. Advise on psychiatric harm, omissions, "
                "third-party danger, public-authority duty, primary/secondary victims, and damages. Return about 900 words."
            ),
        },
        {
            "name": "business_company_conflict_insolvency",
            "kind": "complete",
            "prompt": (
                "Company/Business Law problem question. A private company with Model Articles has four directors. One director causes the company "
                "to buy software from a company owned by her brother at an overvalue and hides the link. Another director approves dividends using "
                "optimistic accounts while cash-flow forecasts show insolvency risk. A minority shareholder asks about derivative and unfair prejudice "
                "routes; a later liquidator considers creditor-interest, wrongful trading, transactions at undervalue and remedies. Return about 950 words."
            ),
        },
        {
            "name": "trusts_purpose_secret_tracing",
            "kind": "complete",
            "prompt": (
                "Equity and Trusts problem question. A will leaves money for a humorous monument, animal care, a confidential gift to a former partner "
                "via a friend, income from a portfolio for one child with capital to 'my other family', and a residue. After death, a trustee misapplies "
                "trust money into shares and pays a personal mortgage. Advise on purpose trusts, beneficiary principle, three certainties, secret trusts, "
                "tracing, personal/proprietary remedies, and insolvency consequences. Return about 950 words."
            ),
        },
        {
            "name": "evidence_hearsay_bad_character",
            "kind": "complete",
            "prompt": (
                "Evidence Law problem question. The prosecution seeks to rely on an absent witness statement, a defendant's previous conviction, "
                "a confession made after delayed legal advice, disputed CCTV identification, and expert phone-location evidence. Advise on admissibility, "
                "statutory gateways, PACE/CJA routes, Article 6 fairness, directions/warnings, and likely rulings. Return about 900 words."
            ),
        },
        {
            "name": "public_law_legitimate_expectation",
            "kind": "complete",
            "prompt": (
                "Public Law/Judicial Review problem question. A regulator published a clear policy promising consultation and a transitional period "
                "before revoking licences. It later revokes a licence immediately after private ministerial pressure and gives brief reasons. Advise on "
                "legitimate expectation, fettering/improper purpose, relevant considerations, reasons, intensity of review, and remedies. Return about 900 words."
            ),
        },
        {
            "name": "criminal_sports_consent_transferred_malice",
            "kind": "complete",
            "prompt": (
                "Criminal Law problem question. During a hostile football final, one player makes a reckless high tackle breaking another's nose; "
                "a teammate threatens retaliation; another player swings a metal pole at the teammate but accidentally hits the referee causing brain injury. "
                "Advise on offences, actus reus/mens rea, causation, consent in sport, transferred malice, and likely liability. Return about 900 words."
            ),
        },
        {
            "name": "pensions_nra_equalisation",
            "kind": "complete",
            "prompt": (
                "Pensions Law problem question. A DB occupational pension scheme historically had NRA 60 for women and 65 for men. "
                "After Barber, trustees announced equalisation by member newsletter but the formal deed amendment was executed years later. "
                "The deed also purports to alter late-retirement factors and reduce an early-retirement underpin for deferred members. "
                "Advise trustees on equalisation, Barber-window benefits, amendment power/formalities, section 67/accrued rights, tax/registration "
                "or actuarial-consent issues, and practical next steps. Show the workings approach rather than a generic summary. Return about 950 words."
            ),
        },
        {
            "name": "pensions_non_financial_investment",
            "kind": "complete",
            "prompt": (
                "Pensions Law essay/problem hybrid. Trustees of a large DB scheme want to divest from fossil fuel and defence stocks for ethical reasons. "
                "An active-member survey supports divestment but deferred members and pensioners were not consulted. The employer covenant is weakening, "
                "and the investment consultant says the change may increase tracking error and reduce expected returns. Critically advise whether trustees "
                "may take non-financial factors into account, distinguishing financial ESG risks from ethical preferences, member consensus, significant "
                "financial detriment, DB/DC context, and decision-process safeguards. Return about 950 words."
            ),
        },
        {
            "name": "mediation_singapore_convention",
            "kind": "complete",
            "prompt": (
                "International Commercial Mediation essay. Critically examine whether the Singapore Convention on Mediation solves the enforcement problem "
                "for international mediated settlement agreements. Use the New York Convention as a benchmark but do not write a generic arbitration essay. "
                "Analyse enforceability gap, Article 5 refusal grounds, mediator misconduct/standards, confidentiality/evidence tension, ratification/critical "
                "mass, and possible protocol or reform solutions. Return about 950 words."
            ),
        },
        {
            "name": "mediation_process_problem",
            "kind": "complete",
            "prompt": (
                "International Commercial Mediation problem question. Two companies have a tiered dispute clause requiring good-faith negotiation then mediation "
                "before litigation. One party starts court proceedings early. During mediation, the mediator privately suggests legal merits to one side, later "
                "discloses a prior relationship with that party, and the parties sign a short settlement term sheet with payment and confidentiality clauses. "
                "Advise on enforcing the mediation clause/stay, mediator conduct, confidentiality/without-prejudice issues, settlement enforceability, and any "
                "cross-border Singapore Convention route. Return about 950 words."
            ),
        },
        {
            "name": "sqe2_task_legal_writing",
            "kind": "sqe2_task",
            "prompt": (
                "Give me one hard SQE2 legal writing task in Property Practice. It must be harder than the official sample, "
                "include a professional conduct trap, and withhold the answer because I will answer later."
            ),
        },
        {
            "name": "sqe2_task_legal_drafting",
            "kind": "sqe2_task",
            "prompt": (
                "Give me one hard SQE2 legal drafting task in Business Organisations. It must involve board/shareholder approval, "
                "conflict nuance and a drafting trap. Do not include model answer or marking points."
            ),
        },
        {
            "name": "sqe2_marking_legal_writing",
            "kind": "sqe2_marking",
            "skill": "legal writing",
            "practice_area": "Property Practice",
            "question": (
                "SQE2 legal writing task: Write a client email. Contracts exchanged on a house purchase. Completion was due yesterday. "
                "The buyer client was ready but the seller failed to complete because they had not moved out. Explain options, notice to complete, "
                "compensation, specific performance and next steps. Keep it plain English."
            ),
            "candidate_answer": (
                "Dear Client, the seller breached the contract. You can sue them. We should tell them to complete soon. "
                "You might get all your costs. If they do not complete we can go to court. Regards."
            ),
        },
        {
            "name": "sqe2_marking_case_analysis",
            "kind": "sqe2_marking",
            "skill": "case and matter analysis",
            "practice_area": "Business Organisations, Rules and Procedures",
            "question": (
                "SQE2 case and matter analysis task: Prepare a note to a partner. A private company with Model Articles has two directors/shareholders. "
                "One director caused the company to buy equipment from a company owned by that director's spouse for 90,000 pounds. Net assets are 300,000 pounds. "
                "No board minutes or shareholder approval are found. The other director asks whether the transaction can be challenged and who we act for."
            ),
            "candidate_answer": (
                "The company can probably buy the equipment because the director owns most of the shares. The other director can complain if the price is unfair. "
                "We should ask the director to approve it now and then write to the seller. There is no major issue because it is still a commercial decision."
            ),
        },
    ]


def main() -> int:
    _load_env_file(ROOT / ".env.local")
    if os.getenv("LEGAL_AI_LIVE_AUDIT_SEND_EXTERNAL", "").strip().lower() not in {"1", "true", "yes"}:
        print("[LIVE STRESS AUDIT BLOCKED]")
        print("Real stress audit would send prompts plus retrieved local RAG/course-material context to the configured external model provider.")
        print("Set LEGAL_AI_LIVE_AUDIT_SEND_EXTERNAL=1 only after explicit user approval for that data flow.")
        return 3

    os.environ.setdefault("LEGAL_AI_DISABLE_CODEX_LOCAL_ADAPTER", "1")
    provider_config = _resolve_live_provider_config()
    if (not provider_config["api_key"]) or _is_placeholder_api_key(provider_config["api_key"]):
        print("[LIVE STRESS AUDIT BLOCKED]")
        print(
            "No usable non-placeholder API key was found for "
            f"{provider_config['provider']} via {provider_config['key_env'] or 'configured live audit key env'}."
        )
        print("Set LEGAL_AI_LIVE_AUDIT_PROVIDER and the matching provider API key before running a live backend audit.")
        return 4
    print(
        "[LIVE STRESS AUDIT] Using provider="
        f"{provider_config['provider']} key_env={provider_config['key_env'] or 'LEGAL_AI_LIVE_AUDIT_API_KEY'}"
    )

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("/private/tmp") / f"legal_runtime_stress_audit_{run_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for case in _cases():
        name = case["name"]
        print(f"[LIVE STRESS AUDIT] Running {name}...")
        if case["kind"] == "complete":
            response, rag_context = send_complete_answer_with_docs(
                api_key=provider_config["api_key"],
                message=case["prompt"],
                documents=[],
                project_id=f"live_stress_{run_id}_{name}",
                history=[],
                stream=False,
                provider=provider_config["provider"],
                model_name=provider_config["model_name"] or None,
                output_mode="chat",
                strict_complete_answer_verification=False,
            )
        elif case["kind"] == "sqe2_task":
            response, rag_context = send_sqe_question_set_with_docs(
                api_key=provider_config["api_key"],
                enquiry=case["prompt"],
                documents=[],
                project_id=f"live_stress_{run_id}_{name}",
                history=[],
                stream=False,
                provider=provider_config["provider"],
                model_name=provider_config["model_name"] or None,
                exam_stage="sqe2",
                include_default_samples=True,
                output_mode="chat",
            )
        else:
            response, rag_context = send_sqe2_marking_with_docs(
                api_key=provider_config["api_key"],
                question=case["question"],
                candidate_answer=case["candidate_answer"],
                documents=[],
                project_id=f"live_stress_{run_id}_{name}",
                history=[],
                stream=False,
                provider=provider_config["provider"],
                model_name=provider_config["model_name"] or None,
                skill=case.get("skill"),
                practice_area=case.get("practice_area"),
                output_mode="chat",
            )

        text = _response_text(response)
        score = _score_output(name, text)
        output_file = out_dir / f"{name}.md"
        output_file.write_text(text, encoding="utf-8")
        result = {
            "name": name,
            "kind": case["kind"],
            "score": score,
            "output_file": str(output_file),
            "rag_chars": len(rag_context or ""),
        }
        results.append(result)
        print(f"[LIVE STRESS AUDIT] {name}: passed={score['passed']} words={score['word_count']} checks={score['checks']}")

    summary = {
        "run_id": run_id,
        "out_dir": str(out_dir),
        "results": results,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[LIVE STRESS AUDIT] Saved outputs to {out_dir}")
    return 0 if all(item["score"]["passed"] for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
