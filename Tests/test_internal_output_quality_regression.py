"""
Regression checks for internal output-quality validation on full answer text.

This covers both sides of the quality gate:
1. compliant single-shot essay/problem fixtures pass the runtime validator;
2. the saved full-answer artifacts stay validator-clean; and
3. inline authority detection keeps accepting subsection cites and older
   round-bracket year case citations.
"""

from pathlib import Path

from backend_answer_runtime import _complete_answer_sentence_support_issues, _essay_quality_issues


REPO_ROOT = Path(__file__).resolve().parents[1]


COMPLIANT_ESSAY_PROMPT = """700 words
Constitutional / Devolution Law - Essay Question
Critically evaluate whether devolution has transformed the United Kingdom constitution in substance, or whether it remains a legally limited and politically fragile qualification of parliamentary sovereignty.
"""


COMPLIANT_ESSAY_OUTPUT = """Part I: Introduction

Devolution has transformed the practical constitution of the United Kingdom, but it has not displaced the legal proposition that Westminster remains sovereign. The settlement is therefore best understood as a constitutionally significant distribution of authority within a unitary state rather than a federal transfer of ultimate power. Its legal basis remains statutory, and the core legislation preserves parliamentary supremacy even while creating politically entrenched institutions (Scotland Act 1998, section 28).

Part II: Statutory Basis and Legislative Competence

Devolution matters in substance because the devolved legislatures do not exercise merely delegated administrative discretion. They possess primary law-making competence within fields defined by statute. In Scotland, the basic validity question is whether devolved legislation falls within the competence framework laid down by Parliament (Scotland Act 1998, section 29).

Equivalent competence boundaries exist elsewhere in the settlement, although Wales and Northern Ireland use different statutory architectures shaped by their own constitutional histories (Government of Wales Act 2006, section 108A; Northern Ireland Act 1998, section 6). That matters in practice because devolved institutions can adopt different legal choices on health, education, housing, and parts of environmental policy. Citizens therefore encounter territorially distinct legal regimes, and devolved ministers exercise genuine democratic authority inside those fields.

The statutory source of that authority also marks its limit. Law officers may refer competence disputes for judicial resolution, which confirms that devolved legislation remains subject to a legality review structured by Parliament itself (Scotland Act 1998, section 33). Devolution therefore reshapes governance without altering the ultimate legal hierarchy.

Part III: Sovereignty, Conventions, and Political Entrenchment

The strongest argument that devolution has not legally altered the constitution is the continued force of Westminster sovereignty. The Scottish settlement says so expressly, making clear that the creation of devolved institutions does not remove the power of the United Kingdom Parliament to legislate for Scotland (Scotland Act 1998, section 28).

The convention regulating consent expectations does not change that legal position. It shapes the expected manner of Westminster legislation in devolved fields, but it does not turn political restraint into a judicial veto over parliamentary authority (Scotland Act 1998, section 28).

At the same time, it would be too narrow to say that nothing changed. Legislative consent, political expectation, and electoral legitimacy shape the actual operation of the constitution. If Westminster repeatedly legislated in devolved areas without consent, the legal position would remain intact, but the political legitimacy of the settlement would be damaged. Devolution therefore qualifies sovereignty in practice even while leaving it untouched in law.

Part IV: Courts, Friction, and Institutional Durability

The courts contribute to constitutional transformation not by enforcing a federal compact, but by policing the statutory boundaries of devolved power. Competence challenges and executive review disputes are resolved through legal criteria rather than pure political bargaining, which strengthens the rule-of-law dimension of the settlement (Scotland Act 1998, section 29; Northern Ireland Act 1998, section 6).

Even so, litigation cannot resolve the deepest tensions. Many disputes concern finance, political mandate, policy divergence, or constitutional principle rather than a clean competence question. Powers allowing central intervention in exceptional circumstances show both the continuing supremacy of the centre and the sensitivity of the settlement when conflict intensifies (Scotland Act 1998, section 35).

The durability of devolution therefore depends on cooperative politics as well as adjudication. If courts are asked to bear too much of the strain, the settlement appears legalistic without becoming fully stable. That institutional dependence on political trust helps explain why the settlement can feel entrenched in ordinary times yet exposed during constitutional stress.

Part V: Conclusion

Devolution has transformed the United Kingdom constitution in substance, but not by displacing parliamentary sovereignty. The devolved institutions exercise real law-making authority within statutory competence boundaries, and courts supervise those boundaries through a structured legality framework (Scotland Act 1998, section 29; Scotland Act 1998, section 33). Westminster nevertheless retains legal authority to legislate for the devolved territories, and the statutes say so expressly (Scotland Act 1998, section 28). The best view is therefore mixed: devolution has produced a constitutionally important redistribution of governing power, yet it remains legally vulnerable because political entrenchment has moved further than legal entrenchment (Scotland Act 1998, section 28).
"""


COMPLIANT_PROBLEM_PROMPT = """800 words
Contract Law - Problem Question
Advise the buyer on satisfactory quality, fitness for purpose, description, misrepresentation, exclusion terms, and the remedies likely to be available.
"""


COMPLIANT_PROBLEM_OUTPUT = """Part I: Introduction

The buyer's strongest claim is likely to be under the Consumer Rights Act 2015 because domestic machinery sold by a trader must match description, be of satisfactory quality, and be fit for any disclosed purpose (Consumer Rights Act 2015, sections 9 to 11). Any attempt to exclude those core rights is tightly controlled, and the seller may also face a misrepresentation claim if pre-contractual assurances induced the purchase (Consumer Rights Act 2015, section 31; Misrepresentation Act 1967, section 2).

Part II: Conformity of the Goods

A. Issue

The first issue is whether the machinery breached the statutory standards of quality, fitness for purpose, or conformity with description.

B. Rule

Goods supplied by a trader to a consumer must be of satisfactory quality, fit for any particular purpose made known to the trader, and consistent with the description used to market or sell them (Consumer Rights Act 2015, sections 9 to 11). Those standards ask whether a reasonable buyer would regard the goods as acceptable and whether the product delivered matched the promises that induced purchase (Consumer Rights Act 2015, sections 9 to 11).

C. Application

If the machinery overheated, failed to perform the domestic storage function promised, or differed materially from the seller's description of being safe for ordinary household use, the buyer has a strong conformity claim (Consumer Rights Act 2015, sections 9 to 11).

The seller will try to blame installation choices or later user conduct. That answer is weaker if the problem reflects the inherent state of the goods at delivery, because the statutory scheme is designed to protect the consumer against simple blame-shifting where the product was defective from the outset (Consumer Rights Act 2015, section 19).

D. Conclusion

On the facts given, breach of the statutory quality and fitness standards is likely to be the buyer's clearest primary claim.

Part III: Misrepresentation and Exclusion Terms

A. Issue

The second issue is whether pre-contractual assurances created an additional misrepresentation claim and whether any exclusion language can defeat the buyer's rights.

B. Rule

If the seller made a false statement of fact that induced the contract, the buyer may claim damages unless the seller can establish the statutory defence (Misrepresentation Act 1967, section 2). Terms that try to exclude liability for misrepresentation are subject to statutory control, and consumer legislation separately blocks attempts to contract out of the core quality rights (Misrepresentation Act 1967, section 3; Consumer Rights Act 2015, section 31).

C. Application

A marketing statement that the machinery was safe for domestic use and suitable for long-term household storage could readily induce purchase if the buyer relied on it when choosing the product. If that statement was false, the buyer can advance a parallel misrepresentation claim in addition to the conformity claim (Misrepresentation Act 1967, section 2).

The seller gains little from boilerplate disclaimer language if it tries to neutralise specific assurances or the statutory guarantees, because both statutes impose firm controls on that strategy (Misrepresentation Act 1967, section 3; Consumer Rights Act 2015, section 31).

D. Conclusion

The buyer therefore has a realistic secondary claim in misrepresentation, and exclusion language is unlikely to remove the main statutory protections.

Part IV: Remedies / Liability

If the defect is established, the buyer can invoke the statutory remedies ladder. Prompt rejection is available first; if that stage has passed, the buyer may require repair or replacement and, if those responses fail or are disproportionate, may seek a price reduction or final rejection (Consumer Rights Act 2015, sections 20 to 24). Damages for misrepresentation may also be available if the false assurance induced entry into the contract (Misrepresentation Act 1967, section 2). Liability will fall primarily on the seller who supplied the goods, although installer fault may matter on the facts if overheating resulted solely from an independent installation error rather than an inherent defect.

Part V: Final Conclusion

The buyer is likely to succeed if the overheating reflects a defect present at delivery or a mismatch between the product delivered and the trader's domestic-safety assurances. The strongest route is the Consumer Rights Act 2015 because the statutory duties on satisfactory quality, fitness for purpose, and description directly address that kind of failure (Consumer Rights Act 2015, sections 9 to 11). The buyer also has a meaningful misrepresentation argument if the seller's safety statements induced the transaction and turned out to be false (Misrepresentation Act 1967, section 2). Any term attempting to exclude those protections faces serious statutory difficulty (Consumer Rights Act 2015, section 31; Misrepresentation Act 1967, section 3). The practical remedy analysis then turns on timing, because rejection, repair or replacement, price reduction, and final rejection sit in a structured sequence rather than a free choice of responses (Consumer Rights Act 2015, sections 20 to 24).
"""


SAVED_OUTPUT_CASES = [
    {
        "path": REPO_ROOT / "generated_answers/q6_wills_and_estates_problem_answer.md",
        "prompt": """2200 words
Wills and Administration of Estates - Problem Question
Advise the parties on testamentary capacity, knowledge and approval, undue influence, suspicious circumstances, and what happens if the later will is invalid.
""",
        "is_short_single_essay": False,
        "is_problem_mode": True,
    },
    {
        "path": REPO_ROOT / "generated_answers/q8_company_law_essay_answer.md",
        "prompt": """2200 words
Company Law - Essay Question
Critically evaluate whether English law now takes a coherent approach to company personality, veil piercing, and parent-company liability.
""",
        "is_short_single_essay": False,
        "is_problem_mode": False,
    },
    {
        "path": REPO_ROOT / "generated_answers/q9_international_commercial_arbitration_problem_answer.md",
        "prompt": """3000 words
International Commercial Arbitration - Problem Question
Advise the parties on challenges at the seat, resistance to enforcement abroad, jurisdictional objections, apparent bias, fair-hearing arguments, public policy, recognition and enforcement under the New York Convention, and the practical significance of the difference between supervisory review and enforcement-stage review.
""",
        "is_short_single_essay": False,
        "is_problem_mode": True,
    },
]


def run() -> None:
    essay_issues = _essay_quality_issues(
        COMPLIANT_ESSAY_OUTPUT,
        COMPLIANT_ESSAY_PROMPT,
        is_short_single_essay=True,
        is_problem_mode=False,
    )
    print("Compliant essay issues:", essay_issues)
    assert essay_issues == []

    problem_issues = _essay_quality_issues(
        COMPLIANT_PROBLEM_OUTPUT,
        COMPLIANT_PROBLEM_PROMPT,
        is_short_single_essay=False,
        is_problem_mode=True,
    )
    print("Compliant problem issues:", problem_issues)
    assert problem_issues == []

    subsection_and_older_case_support = _complete_answer_sentence_support_issues(
        """Part I: Introduction

The settlement remains legally fragile because Westminster still retains the power to legislate for Scotland (Scotland Act 1998, section 28(7)).
The older probate burden still matters where suspicion is raised around preparation of the will (Barry v Butlin (1838) 2 Moo PCC 480).

Part II: Conclusion

The governing citations are still being recognised correctly.
"""
    )
    print("Subsection / older-case support issues:", subsection_and_older_case_support)
    assert subsection_and_older_case_support == []

    convention_roman_article_support = _complete_answer_sentence_support_issues(
        """Part I: Issue

The seat court can review the award directly, while enforcement courts abroad operate only within the New York Convention grounds (New York Convention, arts III, V, VI).

Part II: Conclusion

If the award is annulled at the seat, enforcement may still be refused elsewhere under the Convention framework (New York Convention, art V(1)(e)).
"""
    )
    print("Convention roman-article support issues:", convention_roman_article_support)
    assert convention_roman_article_support == []

    subparagraph_citation_issues = _essay_quality_issues(
        """Part I: Introduction

The debtor can resist recognition only on the Convention grounds, and the key due-process point is the inability-to-present-the-case ground (Convention on the Recognition and Enforcement of Foreign Arbitral Awards (adopted 10 June 1958, entered into force 7 June 1959) 330 UNTS 3 (New York Convention), art V(1)(b)).

Part II: Final Conclusion

The arbitration objection therefore turns on valid subparagraph citation handling rather than placeholder stripping.
""",
        """1200 words
International Commercial Arbitration - Problem Question
Advise the parties on jurisdiction, fair hearing, enforcement, and New York Convention defences.
""",
        is_short_single_essay=False,
        is_problem_mode=True,
    )
    print("Subparagraph citation issues:", subparagraph_citation_issues)
    assert "Contains placeholder citation markers like '(J )'." not in subparagraph_citation_issues

    for case in SAVED_OUTPUT_CASES:
        text = case["path"].read_text(encoding="utf-8")
        issues = _essay_quality_issues(
            text,
            case["prompt"],
            is_short_single_essay=case["is_short_single_essay"],
            is_problem_mode=case["is_problem_mode"],
        )
        print(f"Saved output audit for {case['path'].name}:", issues)
        assert issues == [], (case["path"].name, issues)

    print("Internal output-quality regression passed.")


if __name__ == "__main__":
    run()
