"""
Law & Medicine course-guidance regression checks.

These tests keep course-bound Law and Medicine prompts out of the generic legal path and
ensure the course-bound guide rules remain visible in the repository guide.
They do not call live LLM APIs.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_applicable_service import (
    _build_local_code_rag_answer_prompt_block,
    _infer_retrieval_profile,
    _subissue_queries_for_unit,
)


COURSE_PROMPTS = [
    {
        "name": "eve_anna_otto_problem",
        "expected_topic": "medical_end_of_life_mca2005",
        "prompt": """Law and Medicine - Problem Question

Eve has spinal-cord injuries and will need a ventilator for life. She dictates a letter asking for the ventilator to be withdrawn in four days, then suffers brain damage and repeatedly says 'no die'. Anna, aged seven, needs a kidney transplant but her father refuses consent. Otto, aged 18, signs an organ donation form during moments of consciousness before dying, but a relative objects to use of his organs.

Advise the hospital on advance refusal, capacity, best interests, child treatment, and deceased organ donation.""",
        "subquery_terms": [
            "Capacity, communication, and prior wishes",
            "Best interests and withdrawal of life-sustaining treatment",
        ],
    },
    {
        "name": "transplantation_reform",
        "expected_topic": "medical_transplantation_hta2004",
        "prompt": """Law and Medicine - Essay Question

Make the case for reforming one or more aspects of the law on transplantation within the module syllabus. Consider the Human Tissue Act 2004, appropriate consent, deemed consent, living donors, deceased donors, conditional donation, directed donation, requested allocation, and section 32 commercialisation.""",
        "subquery_terms": [
            "HTA consent framework",
            "Commercialisation and reform",
        ],
    },
    {
        "name": "fetal_abnormality_reform",
        "expected_topic": "medical_abortion_aa1967",
        "prompt": """Law and Medicine - Essay Question

Critically examine the view that abortion on grounds of fetal abnormality is in need of legislative reform. Consider the criminal background, Abortion Act 1967 section 1(1)(a), section 1(1)(d), Crowter, Jepson, disability discrimination, decriminalisation, and possible time-limit reform.""",
        "subquery_terms": [
            "Criminal framework and statutory gateway",
            "Precise Abortion Act ground",
        ],
    },
    {
        "name": "hfea_fitness",
        "expected_topic": "medical_reproductive_hfea",
        "prompt": """Law and Medicine - Essay Question

Critically examine whether the Human Fertilisation and Embryology Act 1990 is unfit for the purpose of governing assisted reproduction. Discuss HFEA licensing, IVF, Schedule 3 consent, section 13(5) welfare of the child, legal parenthood, PGT, saviour siblings, and embryo research.""",
        "subquery_terms": [
            "HFEA regulatory architecture",
            "PGT, saviour siblings, embryo research, and reform",
        ],
    },
]


def test_law_medicine_course_prompts_route_and_split() -> None:
    for case in COURSE_PROMPTS:
        profile = _infer_retrieval_profile(case["prompt"])
        assert profile["topic"] == case["expected_topic"], case["name"]
        assert profile["topic"] != "general_legal", case["name"]
        assert profile["must_cover"], case["name"]
        assert profile["issue_bank"], case["name"]

        subquery_labels = [label for label, _ in _subissue_queries_for_unit("Essay Question", case["prompt"])]
        if "Problem Question" in case["prompt"]:
            subquery_labels = [label for label, _ in _subissue_queries_for_unit("Problem Question", case["prompt"])]
        for expected in case["subquery_terms"]:
            assert expected in subquery_labels, (case["name"], expected, subquery_labels)


def test_law_medicine_guide_contains_course_bound_rules() -> None:
    guide = Path("legal_doc_tools/LEGAL_DOC_GUIDE.md").read_text(encoding="utf-8")
    required = [
        "Course-bound mode is the default",
        "the exam is one compulsory problem question plus one essay question",
        "do not centre Montgomery/negligence unless expressly asked",
        "Model-introduction learning rule",
        "extract only the technique",
        "Reform-introduction rule",
        "No-limitation clarification",
        "separate deceased donation, living donation, allocation, and commercialisation",
        "Distinguish section 1(1)(a) social ground, section 1(1)(d) fetal abnormality",
        "Separate Schedule 3 consent, section 13(5) welfare-of-child screening",
    ]
    for phrase in required:
        assert phrase in guide

    subject_guide = Path("legal_doc_tools/law_guides/law_medicine.md").read_text(encoding="utf-8")
    subject_required = [
        "Essay Introduction Method",
        "Source Modes",
        "No-limitation mode",
        "Material-Led Emphasis",
        "Use four moves: define the legal field/statutory scheme",
        "Fetal abnormality abortion reform",
        "HFEA / assisted reproduction fitness",
        "Never reproduce slide wording",
    ]
    for phrase in subject_required:
        assert phrase in subject_guide


def test_law_medicine_no_limitation_mode_is_clear_in_prompt() -> None:
    prompt = (
        "Law and Medicine broad-all / no syllabus limit essay: evaluate informed consent, "
        "clinical negligence, Montgomery, mental health law and public health alongside the module topics."
    )
    block = _build_local_code_rag_answer_prompt_block(prompt, enforce_long_response_split=False)
    required = [
        "Course-bound mode and no-limitation mode share the same essay technique",
        "the above exclusions no longer operate as exclusions",
        "No-limitation mode",
    ]
    for phrase in required:
        assert phrase in block


def run() -> None:
    test_law_medicine_course_prompts_route_and_split()
    test_law_medicine_guide_contains_course_bound_rules()
    test_law_medicine_no_limitation_mode_is_clear_in_prompt()
    print("Law & Medicine course-guidance regression passed.")


if __name__ == "__main__":
    run()
