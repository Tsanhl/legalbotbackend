"""
Full routing regression matrix for every specific topic in gemini_service.py.

This is a planner/routing/fan-out sanity test only. It does not call live LLM APIs.
"""

import re
from pathlib import Path

from gemini_service import _infer_retrieval_profile, _subissue_queries_for_unit


def essay(title: str, body: str) -> str:
    return f"2000 words\nEssay Question — {title}\n{body}".strip()


def problem(title: str, body: str) -> str:
    return f"2000 words\nProblem Question — {title}\n{body}".strip()


ROUTING_CASES = [
    {
        "topic": "medical_end_of_life_mca2005",
        "kind": "essay",
        "prompt": essay(
            "Medical Law – End of Life",
            "Critically discuss assisted suicide, withdrawal of treatment, CANH, persistent vegetative state, Suicide Act 1961, Airedale, Bland, Pretty v DPP, and Nicklinson.",
        ),
    },
    {
        "topic": "medical_consent_capacity",
        "kind": "problem",
        "prompt": problem(
            "Medical Law – Consent and Capacity",
            "Advise on material risk disclosure, Montgomery, Mental Capacity Act 2005, emergency treatment without consent, and whether a patient lacks capacity.",
        ),
    },
    {
        "topic": "aviation_passenger_injury_montreal",
        "kind": "problem",
        "prompt": problem(
            "Aviation Law – Passenger Injury",
            "A passenger is injured during turbulence on an international flight. Advise on carrier liability, the Montreal Convention, Article 17, applicable conventions, and limits on damages.",
        ),
    },
    {
        "topic": "clinical_negligence_causation_loss_of_chance",
        "kind": "problem",
        "prompt": problem(
            "Clinical Negligence – Causation and Lost Chance",
            "Advise on delayed diagnosis, failure to refer, Gregg v Scott, Bailey v Ministry of Defence, loss of chance, and medical causation.",
        ),
    },
    {
        "topic": "defamation_media_privacy",
        "kind": "essay",
        "prompt": essay(
            "Defamation and Media Liability",
            "Analyse the Defamation Act 2013, serious harm, honest opinion, truth defence, public interest defence, Lachaux, Monroe v Hopkins, and Serafin.",
        ),
    },
    {
        "topic": "land_home_coownership_estoppel_priority",
        "kind": "problem",
        "prompt": problem(
            "Land Law – Family Home Rights and Priority",
            "An unmarried couple buy a family home in the sole name of one partner. The other claims a beneficial interest, proprietary estoppel, and actual occupation against a later registered charge over the home.",
        ),
    },
    {
        "topic": "land_proprietary_estoppel",
        "kind": "problem",
        "prompt": problem(
            "Land Law – Proprietary Estoppel",
            "Advise on proprietary estoppel where an assurance about inheriting a farm caused detriment and reliance. Discuss Thorner v Major, Guest v Guest, and unconscionability.",
        ),
    },
    {
        "topic": "contract_misrepresentation_exclusion",
        "kind": "problem",
        "prompt": problem(
            "Contract – Misrepresentation and Exclusion",
            "Advise on fraudulent misrepresentation, negligent misrepresentation under section 2(1), an entire agreement clause, a non-reliance clause, rescission, and whether an exclusion clause is effective under the Misrepresentation Act.",
        ),
    },
    {
        "topic": "contract_sale_of_goods_implied_terms_remedies",
        "kind": "problem",
        "prompt": problem(
            "Sale of Goods – Implied Terms and Remedies",
            "Advise on the Sale of Goods Act 1979, satisfactory quality, fitness for purpose, sale by description, acceptance of goods, the right to reject, and lost profits.",
        ),
    },
    {
        "topic": "insolvency_corporate",
        "kind": "problem",
        "prompt": problem(
            "Corporate Insolvency",
            "Advise a liquidator on wrongful trading, fraudulent trading, transactions at an undervalue, preferences, misfeasance, creditor duty, and Sequana under the Insolvency Act 1986.",
        ),
    },
    {
        "topic": "generic_access_to_justice",
        "kind": "essay",
        "prompt": essay(
            "Access to Justice",
            "Critically evaluate access to justice, legal aid, court fees, UNISON, effective remedies, representation, and whether practical barriers undermine formal rights of access to court.",
        ),
    },
    {
        "topic": "generic_administrative_law",
        "kind": "essay",
        "prompt": essay(
            "Administrative Law – Procedural Fairness",
            "Critically evaluate whether procedural fairness in public decision-making rests on a coherent set of principles, including consultation, hearing affected persons, reasons, legitimacy, and good administration.",
        ),
    },
    {
        "topic": "generic_agency_law",
        "kind": "essay",
        "prompt": essay(
            "Agency Law",
            "Critically evaluate whether the modern law of agency adequately protects third parties dealing with uncertain authority, including actual authority, apparent authority, ratification, and principal and agent liability.",
        ),
    },
    {
        "topic": "generic_commercial_law",
        "kind": "problem",
        "prompt": problem(
            "Commercial Law – Supply Agreement Remedies",
            "A supplier breaches a long-term supply agreement. Advise on repudiatory breach, termination, mitigation, lost profits, specific performance, and the best realistic commercial remedy.",
        ),
    },
    {
        "topic": "generic_land_law",
        "kind": "problem",
        "prompt": problem(
            "Land Law – Lease or Licence",
            "X allows Y to occupy a flat for a monthly fee but retains a right to enter at any time. Advise on whether Y has a lease or licence, Street v Mountford, Antoniades v Villiers, and the legal consequences.",
        ),
    },
    {
        "topic": "generic_international_trade_law",
        "kind": "essay",
        "prompt": essay(
            "Trade Law – Fairness",
            "Critically evaluate whether global trade rules promote fairness, including most-favoured-nation treatment, market access, development asymmetry, and dispute settlement.",
        ),
    },
    {
        "topic": "generic_consumer_protection_law",
        "kind": "essay",
        "prompt": essay(
            "Consumer Protection Law",
            "Critically evaluate whether consumer protection law adequately protects modern consumers, with reference to the Consumer Rights Act 2015, unfair commercial practices, unfair terms, information asymmetry, and enforcement weaknesses.",
        ),
    },
    {
        "topic": "generic_devolution_law",
        "kind": "essay",
        "prompt": essay(
            "Devolution Law",
            "Critically assess whether devolution has strengthened or weakened the UK constitution, discussing the Scotland Act 1998, Government of Wales Act 2006, Northern Ireland Act 1998, the Sewel Convention, and constitutional asymmetry.",
        ),
    },
    {
        "topic": "generic_environmental_law",
        "kind": "essay",
        "prompt": essay(
            "Environmental Law",
            "Critically evaluate whether environmental law effectively balances economic development and environmental protection through sustainable development, the precautionary principle, polluter pays, the Environmental Protection Act 1990, and the Climate Change Act 2008.",
        ),
    },
    {
        "topic": "generic_eu_law",
        "kind": "essay",
        "prompt": essay(
            "EU Law Post-Brexit",
            "Critically evaluate whether EU law is still relevant post-Brexit, including retained or assimilated law, the European Union (Withdrawal) Act 2018, Article 267 TFEU, and the Trade and Cooperation Agreement.",
        ),
    },
    {
        "topic": "generic_financial_regulation_law",
        "kind": "essay",
        "prompt": essay(
            "Financial Regulation Law",
            "Critically evaluate whether modern financial regulation effectively prevents systemic risk while promoting market efficiency, with reference to the Financial Services and Markets Act 2000, Basel III, prudential regulation, the FCA, and the Senior Managers and Certification Regime.",
        ),
    },
    {
        "topic": "generic_freedom_of_expression_law",
        "kind": "problem",
        "prompt": problem(
            "Freedom of Expression",
            "A protester is arrested for offensive speech. Advise on Article 10 ECHR, the Human Rights Act 1998, proportionality, Handyside, and whether the restriction is justified.",
        ),
    },
    {
        "topic": "generic_housing_law",
        "kind": "problem",
        "prompt": problem(
            "Housing Law – Deposit, Repairs, and Lock Change",
            "A private landlord fails to protect a deposit, ignores basic repairs, and changes the locks after the tenant complains to the council. Advise on tenancy protections, repairing duties, unlawful eviction, and remedies.",
        ),
    },
    {
        "topic": "generic_international_law",
        "kind": "essay",
        "prompt": essay(
            "International Law Theory",
            "Critically evaluate whether international law can be considered truly law, discussing Article 38(1) of the ICJ Statute, state consent, treaties, custom, and enforcement objections.",
        ),
    },
    {
        "topic": "generic_ai_law",
        "kind": "essay",
        "prompt": essay(
            "AI Law and Regulation",
            "Critically evaluate whether existing legal frameworks are sufficient to regulate artificial intelligence, including data protection, discrimination, product liability, human rights, explainability, and governance gaps.",
        ),
    },
    {
        "topic": "generic_charity_law",
        "kind": "essay",
        "prompt": essay(
            "Charity Law",
            "Critically evaluate whether the modern law of charitable trusts and regulation of charities provides an effective framework for accountability, including charitable purpose, public benefit, trustees' duties, the Charity Commission, and misuse of charitable funds and powers.",
        ),
    },
    {
        "topic": "generic_criminology",
        "kind": "essay",
        "prompt": essay(
            "Criminology – Deterrence",
            "Critically evaluate whether criminal law effectively deters crime, with reference to general deterrence, specific deterrence, rational choice, certainty, celerity, severity, and empirical limits of deterrence.",
        ),
    },
    {
        "topic": "generic_criminal_law",
        "kind": "essay",
        "prompt": essay(
            "Criminal Law – Murder Reform",
            "Critically evaluate whether the law of murder should be reformed, with reference to the fault element, the mandatory life sentence, and Law Commission reform proposals.",
        ),
    },
    {
        "topic": "generic_sentencing_law",
        "kind": "problem",
        "prompt": problem(
            "Sentencing Law – Appeal",
            "A judge imposes a severe sentence. Advise on appeal, including the Sentencing Act 2020, Sentencing Council guidance, wrong in principle, manifest excess, and the likely appellate outcome.",
        ),
    },
    {
        "topic": "generic_extradition_law",
        "kind": "problem",
        "prompt": problem(
            "Extradition and Human Rights",
            "A requested person faces extradition under the Extradition Act 2003 to a state with poor prison conditions. Advise on Article 3 ECHR, assurances, fair-trial concerns, and grounds to resist extradition.",
        ),
    },
    {
        "topic": "generic_legal_history",
        "kind": "essay",
        "prompt": essay(
            "Legal History and Common Law Reasoning",
            "Critically evaluate how the writ system, equity, precedent, stare decisis, and historical development have shaped modern common law reasoning.",
        ),
    },
    {
        "topic": "generic_rule_of_law",
        "kind": "essay",
        "prompt": essay(
            "Rule of Law",
            "Critically evaluate competing conceptions of the rule of law, including formal and substantive accounts associated with Dicey, Raz, Bingham, and Fuller.",
        ),
    },
    {
        "topic": "tort_duty_of_care_framework",
        "kind": "essay",
        "prompt": essay(
            "Tort – Duty of Care",
            "Critically evaluate the neighbour principle, Donoghue v Stevenson, Anns, Caparo, incremental development, pure economic loss, psychiatric harm, and corrective justice in modern negligence.",
        ),
    },
    {
        "topic": "tort_economic_loss_negligent_misstatement",
        "kind": "problem",
        "prompt": problem(
            "Tort – Negligence and Economic Loss",
            "Advise on negligent misstatement, pure economic loss, assumption of responsibility, Hedley Byrne, Caparo, an investment report, third-party reliance, and competitor loss.",
        ),
    },
    {
        "topic": "company_personality_veil_lifting",
        "kind": "essay",
        "prompt": essay(
            "Company Law – Separate Personality and Veil Lifting",
            "Discuss separate legal personality, limited liability, Salomon v Salomon, Prest v Petrodel, Adams v Cape, Gilford Motor, Jones v Lipman, and veil lifting.",
        ),
    },
    {
        "topic": "company_directors_minorities",
        "kind": "problem",
        "prompt": problem(
            "Company Law – Directors’ Duties and Minority Remedies",
            "Advise on company law, Companies Act 2006, directors' duties, section 172, section 175, derivative claim, unfair prejudice, and minority shareholder remedies.",
        ),
    },
    {
        "topic": "tax_avoidance_gaar",
        "kind": "essay",
        "prompt": essay(
            "Taxation – Avoidance and GAAR",
            "Discuss tax avoidance, Ramsay, Duke of Westminster, Furniss v Dawson, Barclays Mercantile, GAAR, HMRC, TCGA 1992, and Finance Act 2013.",
        ),
    },
    {
        "topic": "sports_governance_fairness",
        "kind": "essay",
        "prompt": essay(
            "Sports Law – Governance and Fairness",
            "Critically evaluate whether legal intervention in sports governance promotes fairness or undermines autonomy. Discuss natural justice, restraint of trade, competition law, anti-doping, disciplinary sanctions, and CAS.",
        ),
    },
    {
        "topic": "corporate_bhr_parent_liability",
        "kind": "essay",
        "prompt": essay(
            "Business and Human Rights",
            "Critically assess parent company liability, parent duty of care, Vedanta, Okpabi, Chandler v Cape, UN Guiding Principles, home state litigation, and supply chain due diligence.",
        ),
    },
    {
        "topic": "wto_trade_security_exceptions",
        "kind": "essay",
        "prompt": essay(
            "WTO Law – Security Exceptions",
            "Analyse GATT Article XXI, the national security exception, Russia – Traffic in Transit, Saudi Arabia – IP Rights, economic sanctions, and trade restrictions justified by security.",
        ),
    },
    {
        "topic": "climate_state_responsibility",
        "kind": "essay",
        "prompt": essay(
            "Public International Law – Climate Responsibility",
            "Discuss climate damage, greenhouse gas emissions, sea-level rise, loss and damage, the no-harm principle, common but differentiated responsibilities, and state responsibility for climate harm.",
        ),
    },
    {
        "topic": "human_rights_proportionality_adjudication",
        "kind": "essay",
        "prompt": essay(
            "Human Rights Law – Proportionality",
            "Critically evaluate whether proportionality provides a more coherent and effective method of rights adjudication than traditional common law approaches. Discuss Daly, Bank Mellat, de Freitas, Pham, and structured rights review.",
        ),
    },
    {
        "topic": "employment_redundancy_unfair_dismissal",
        "kind": "problem",
        "prompt": problem(
            "Employment – Redundancy and Unfair Dismissal",
            "Advise on redundancy, unfair dismissal, consultation duties, selection criteria, Polkey, Williams v Compair Maxam, automatic unfair dismissal, and maternity protection.",
        ),
    },
    {
        "topic": "employment_unfair_dismissal_misconduct",
        "kind": "problem",
        "prompt": problem(
            "Employment – Social Media Dismissal",
            "An employee is dismissed for social media posts criticising the employer. Advise on unfair dismissal, misconduct, employer reputation, employee rights, and Article 10.",
        ),
    },
    {
        "topic": "employment_equal_pay_flexible_working",
        "kind": "problem",
        "prompt": problem(
            "Employment – Equal Pay and Flexible Working",
            "Advise on equal pay, comparators, like work, equal value, material factor, flexible working, childcare, part-time status, and bonus eligibility under the Equality Act.",
        ),
    },
    {
        "topic": "employment_discrimination_eqa2010",
        "kind": "problem",
        "prompt": problem(
            "Employment – Equality Act 2010",
            "Advise on direct discrimination, indirect discrimination, a PCP, objective justification, harassment, victimisation, reasonable adjustments, and the burden of proof under section 136 of the Equality Act 2010.",
        ),
    },
    {
        "topic": "employment_restrictive_covenants",
        "kind": "problem",
        "prompt": problem(
            "Employment – Restrictive Covenants",
            "Advise an employer on a non-compete clause, a non-solicitation covenant, garden leave, a post-termination restriction, and whether a senior employee who joined a competitor can be restrained.",
        ),
    },
    {
        "topic": "employment_worker_status",
        "kind": "problem",
        "prompt": problem(
            "Employment – Worker Status",
            "Advise on worker status in the gig economy, personal service, mutuality, holiday pay, and the relevance of Ready Mixed Concrete, Autoclenz, Uber, and Pimlico Plumbers.",
        ),
    },
    {
        "topic": "data_protection",
        "kind": "essay",
        "prompt": essay(
            "Data Protection",
            "Discuss UK GDPR, data protection, Article 22, Article 17, automated decisions, and the role of the ICO.",
        ),
    },
    {
        "topic": "legal_ethics_conflicts",
        "kind": "essay",
        "prompt": essay(
            "Legal Ethics – Lawyers’ Duties and Conflicts",
            "Critically evaluate whether current rules on lawyers' professional ethics adequately manage conflicts of interest. Discuss confidentiality, duty to the court, legal professional privilege, former-client conflicts, information barriers, the SRA Code, and Bolkiah.",
        ),
    },
    {
        "topic": "criminal_evidence_hearsay",
        "kind": "essay",
        "prompt": essay(
            "Criminal Evidence – Hearsay",
            "Discuss criminal evidence, hearsay, the Criminal Justice Act 2003, sections 114 and 116, confrontation rights, Horncastle, Al-Khawaja, and Tahery.",
        ),
    },
    {
        "topic": "evidence_admissibility_fair_trial",
        "kind": "essay",
        "prompt": essay(
            "Evidence Law – Admissibility and Fair Trials",
            "Critically evaluate whether rules of evidence and admissibility strike the right balance between truth-finding and fairness. Discuss confessions, hearsay, PACE 1984, exclusion of evidence, and Article 6.",
        ),
    },
    {
        "topic": "consumer_digital_content",
        "kind": "problem",
        "prompt": problem(
            "Consumer Law – Digital Content",
            "Advise on a faulty app, faulty software, downloadable content, a streaming service, in-app purchases, and consumer rights for digital content under CRA 2015.",
        ),
    },
    {
        "topic": "ip_copyright_digital_innovation",
        "kind": "essay",
        "prompt": essay(
            "Copyright – Digital Innovation",
            "Critically evaluate whether copyright law adequately balances protection of creators with technological innovation, including exceptions, fair dealing, digital use, and online dissemination.",
        ),
    },
    {
        "topic": "ip_copyright_ai_originality",
        "kind": "essay",
        "prompt": essay(
            "Intellectual Property – Copyright and AI",
            "Discuss copyright, section 9(3) CDPA, computer-generated work, AI-generated outputs, originality, Infopaq, Painer, Nova Productions, Mazooma, and Thaler v Perlmutter.",
        ),
    },
    {
        "topic": "ip_trademark_shapes",
        "kind": "essay",
        "prompt": essay(
            "Trade Marks – Shape Marks",
            "Discuss trade mark protection for a shape mark, section 3(2), technical result, and the exclusion of functional shapes.",
        ),
    },
    {
        "topic": "statutory_interpretation",
        "kind": "essay",
        "prompt": essay(
            "Public Law – Statutory Interpretation",
            "Discuss statutory interpretation, the literal rule, the golden rule, the mischief rule, and purposive interpretation.",
        ),
    },
    {
        "topic": "refugee_maritime_non_refoulement",
        "kind": "essay",
        "prompt": essay(
            "Refugee Law – Maritime Interdiction",
            "Discuss maritime interception, high seas returns, offshore processing, effective control at sea, non-refoulement, and chain refoulement in refugee law.",
        ),
    },
    {
        "topic": "maritime_cargo_damage",
        "kind": "problem",
        "prompt": problem(
            "Maritime Law – Cargo Damage",
            "Goods transported by sea are damaged due to poor stowage. Advise on carrier liability, a bill of lading, contractual terms, Hague-Visby rules, seaworthiness, and international rules governing carriage.",
        ),
    },
    {
        "topic": "immigration_asylum_deportation",
        "kind": "problem",
        "prompt": problem(
            "Immigration – Asylum and Deportation",
            "Advise on asylum, deportation, the Illegal Migration Act, the Nationality and Borders Act, small boats policy, and sections 117B and 117C of the 2002 Act.",
        ),
    },
    {
        "topic": "family_private_children_arrangements",
        "kind": "problem",
        "prompt": problem(
            "Family Law – Children Arrangements",
            "Advise on a Children Act 1989 dispute over child arrangements, a specific issue order, a prohibited steps order, the welfare checklist, and internal relocation within the UK.",
        ),
    },
    {
        "topic": "family_child_abduction_hague1980",
        "kind": "problem",
        "prompt": problem(
            "Family Law – Child Abduction",
            "Advise on the Hague Convention 1980, habitual residence, wrongful removal, rights of custody, Article 13(b), grave risk, and the child's objections defence.",
        ),
    },
    {
        "topic": "international_human_rights_derogation_extraterritoriality",
        "kind": "essay",
        "prompt": essay(
            "International Human Rights – Derogation and Extraterritoriality",
            "Discuss Article 15 ECHR derogation, a public emergency threatening the life of the nation, Article 1 ECHR extraterritoriality, Al-Skeini, Al-Jedda, Bankovic, and ICCPR Article 4.",
        ),
    },
    {
        "topic": "public_law_article8_proportionality",
        "kind": "essay",
        "prompt": essay(
            "Public Law – Article 8 Proportionality",
            "Discuss Article 8, private and family life, whether an interference is necessary in a democratic society, and the proportionality analysis applied by courts.",
        ),
    },
    {
        "topic": "banking_quincecare_fraud",
        "kind": "problem",
        "prompt": problem(
            "Banking Law – Quincecare",
            "Advise on a bank that processed suspicious transactions which turned out to be fraudulent. Discuss duty of care, Quincecare, Singularis, Philipp, and potential liability.",
        ),
    },
    {
        "topic": "insurance_non_disclosure_misrepresentation",
        "kind": "problem",
        "prompt": problem(
            "Insurance Law – Non-Disclosure",
            "Advise where an insured failed to disclose a material circumstance when entering an insurance contract. Discuss fair presentation, inducement, remedies available to the insurer, and the impact on the claim.",
        ),
    },
    {
        "topic": "public_law_judicial_review_deference",
        "kind": "essay",
        "prompt": essay(
            "Public Law – Judicial Review and Deference",
            "Critically discuss judicial review, deference, respect for democratic decision-making, illegality, irrationality, procedural impropriety, proportionality, the Human Rights Act 1998, the rule of law, and parliamentary sovereignty.",
        ),
    },
    {
        "topic": "constitutional_prerogative_justiciability",
        "kind": "essay",
        "prompt": essay(
            "Constitutional Law – Prerogative and Justiciability",
            "Discuss the royal prerogative, justiciability, separation of powers, parliamentary sovereignty, prerogative powers, Miller I, Miller II, De Keyser, Fire Brigades Union, GCHQ, and prorogation.",
        ),
    },
    {
        "topic": "public_law_privacy_expression",
        "kind": "essay",
        "prompt": essay(
            "Privacy and Expression",
            "Discuss Article 8 ECHR, Article 10 ECHR, misuse of private information, privacy, freedom of expression, Campbell v MGN, and PJS.",
        ),
    },
    {
        "topic": "public_law_legitimate_expectation",
        "kind": "problem",
        "prompt": problem(
            "Public Law – Legitimate Expectation",
            "Advise on substantive legitimate expectation, procedural legitimate expectation, Coughlan, Ng Yuen Shiu, Paponette, fettering discretion, and whether an overriding public interest defeats the expectation.",
        ),
    },
    {
        "topic": "cybercrime_ransomware_jurisdiction",
        "kind": "problem",
        "prompt": problem(
            "Cybercrime – Ransomware and Jurisdiction",
            "Advise on ransomware and jurisdiction where phishing emails, cryptocurrency ransom payments, servers in country A, cash-out services in country B, MLA, the Budapest Convention, and extradition are involved.",
        ),
    },
    {
        "topic": "space_law_debris_liability",
        "kind": "essay",
        "prompt": essay(
            "Space Law – Debris Liability",
            "Discuss the Outer Space Treaty, the Liability Convention, launching state responsibility, Article II, Article III, space debris, and in-orbit collision liability.",
        ),
    },
    {
        "topic": "ai_algorithmic_discrimination",
        "kind": "essay",
        "prompt": essay(
            "AI Regulation – Algorithmic Discrimination",
            "Discuss algorithmic discrimination, automated decision-making, proxy discrimination, feedback loops, explainability, impact assessment, algorithmic fairness, and the AI Act.",
        ),
    },
    {
        "topic": "cultural_heritage_illicit_trafficking",
        "kind": "problem",
        "prompt": problem(
            "Cultural Heritage – Illicit Trafficking",
            "Advise on looted statues, UNESCO 1970, UNIDROIT 1995, stolen cultural property, lex situs, source-state vesting law, restitution, and the position of a good-faith purchaser.",
        ),
    },
    {
        "topic": "competition_margin_squeeze_refusal",
        "kind": "essay",
        "prompt": essay(
            "Competition Law – Margin Squeeze and Refusal to Supply",
            "Discuss Article 102, abuse of dominance, margin squeeze, the as-efficient competitor test, wholesale and retail spread, refusal to supply, essential facilities, Bronner, IMS Health, and Deutsche Telekom.",
        ),
    },
    {
        "topic": "competition_abuse_dominance",
        "kind": "essay",
        "prompt": essay(
            "Competition Law – Abuse of Dominance",
            "Discuss Article 102 TFEU, abuse of dominance, dominance, market share, self-preferencing, tying, bundling, predatory pricing, AKZO, Microsoft, Google Shopping, and objective justification.",
        ),
    },
    {
        "topic": "cyber_computer_misuse_harassment",
        "kind": "problem",
        "prompt": problem(
            "Cyber Law – Computer Misuse and Harassment",
            "Advise on the Computer Misuse Act 1990, section 1, section 3, section 3ZA, unauthorised access, a DDoS attack, online harassment, blackmail, and the Communications Act 2003.",
        ),
    },
    {
        "topic": "criminal_nonfatal_offences_self_defence",
        "kind": "problem",
        "prompt": problem(
            "Criminal Law – Non-Fatal Offences and Self-Defence",
            "Advise on OAPA 1861 offences, section 18, section 20, section 47, GBH, ABH, assault, battery, self-defence, reasonable force, mistaken belief, and Gladstone Williams.",
        ),
    },
    {
        "topic": "criminal_omissions_homicide_defences",
        "kind": "problem",
        "prompt": problem(
            "Criminal Law – Omissions and Homicide Defences",
            "Advise on omissions, duty to act, gross negligence manslaughter, Adomako, Miller, Evans, Stone and Dobinson, self-defence, and loss of control.",
        ),
    },
    {
        "topic": "criminal_mens_rea_intention_recklessness",
        "kind": "essay",
        "prompt": essay(
            "Criminal Law – Mens Rea",
            "Discuss mens rea, direct intent, oblique intent, Woollin, Nedrick, Moloney, Cunningham, Caldwell, R v G, foresight of consequences, transferred malice, and moral blameworthiness.",
        ),
    },
    {
        "topic": "criminal_property_offences_dishonesty",
        "kind": "problem",
        "prompt": problem(
            "Criminal Law – Property Offences",
            "Advise on theft, robbery, fraud by false representation, dishonesty, Ivey, Barton, the Theft Act 1968, the Fraud Act 2006, and intention to permanently deprive.",
        ),
    },
    {
        "topic": "partnership_law_pa1890",
        "kind": "problem",
        "prompt": problem(
            "Partnership Law",
            "Advise on the Partnership Act 1890, partnership at will, joint and several liability, secret profits, a rogue partner, dissolution, and winding up.",
        ),
    },
    {
        "topic": "family_cohabitation_reform",
        "kind": "essay",
        "prompt": essay(
            "Family Law – Cohabitation and Reform",
            "Critically evaluate cohabitation, cohabiting couples, marriage, civil partnership, property disputes, trusts, proprietary estoppel, and legal reform in England and Wales.",
        ),
    },
    {
        "topic": "criminal_complicity",
        "kind": "essay",
        "prompt": essay(
            "Criminal Law – Complicity",
            "Discuss joint enterprise, complicity, parasitic accessorial liability, and the significance of Jogee.",
        ),
    },
    {
        "topic": "restitution_mistake",
        "kind": "essay",
        "prompt": essay(
            "Restitution – Mistake",
            "Discuss unjust enrichment, money paid by mistake, mistake of law, change of position, Lipkin Gorman, and Kleinwort Benson.",
        ),
    },
    {
        "topic": "tort_negligence_omissions",
        "kind": "problem",
        "prompt": problem(
            "Tort – Negligence and Omissions",
            "Advise on negligence, duty of care, breach, causation, omission, omissions, Caparo, Robinson, Michael v Chief Constable, Stovin v Wise, Barnett, and loss of chance.",
        ),
    },
    {
        "topic": "tort_occupiers_liability",
        "kind": "problem",
        "prompt": problem(
            "Tort – Occupiers’ Liability",
            "Advise on occupiers' liability, OLA 1957, OLA 1984, the duty to a visitor, the duty to a trespasser, and Tomlinson v Congleton.",
        ),
    },
    {
        "topic": "construction_delay_defects",
        "kind": "problem",
        "prompt": problem(
            "Construction Law – Delay and Defects",
            "A contractor delivers a project late and with defects. Advise on breach of contract, extension of time, liquidated damages, defects liability, adjudication, and available remedies.",
        ),
    },
    {
        "topic": "equity_fiduciary_duties",
        "kind": "essay",
        "prompt": essay(
            "Equity – Fiduciary Duties",
            "Discuss fiduciary duties, the no profit rule, the no conflict rule, self-dealing, Regal (Hastings), Boardman v Phipps, Keech v Sandford, and FHR European Ventures.",
        ),
    },
    {
        "topic": "consumer_unfair_terms_cra2015",
        "kind": "essay",
        "prompt": essay(
            "Consumer Law – Unfair Terms",
            "Discuss the Consumer Rights Act 2015, unfair terms, section 62, significant imbalance, good faith, section 64, transparent and prominent terms, the grey list, and OFT v Ashbourne.",
        ),
    },
    {
        "topic": "eu_supremacy_direct_effect_preliminary_references",
        "kind": "essay",
        "prompt": essay(
            "EU Law – Supremacy and Direct Effect",
            "Discuss supremacy, direct effect, directives, Article 267 TFEU, Van Gend en Loos, Costa v ENEL, Simmenthal, Marshall, Marleasing, Francovich, CILFIT, and Foto-Frost.",
        ),
    },
    {
        "topic": "eu_free_movement_workers_residence",
        "kind": "problem",
        "prompt": problem(
            "EU Law – Workers and Residence Rights",
            "Advise on free movement of workers, retained worker status, Article 45, Directive 2004/38, Lawrie-Blum, Saint Prix, Antonissen, Vatsouras, and residence rights.",
        ),
    },
    {
        "topic": "ihl_targeting_proportionality_civilians",
        "kind": "essay",
        "prompt": essay(
            "International Humanitarian Law – Targeting",
            "Discuss targeting, distinction, precautions in attack, Article 48, Article 51, Article 57 of Additional Protocol I, dual-use infrastructure, incidental civilian harm, and proportionality.",
        ),
    },
    {
        "topic": "eu_free_movement_goods",
        "kind": "essay",
        "prompt": essay(
            "EU Law – Free Movement of Goods",
            "Discuss Article 34 TFEU, MEQRs, Dassonville, Cassis de Dijon, mutual recognition, mandatory requirements, Keck, selling arrangements, and Article 36.",
        ),
    },
    {
        "topic": "land_easements_freehold_covenants",
        "kind": "problem",
        "prompt": problem(
            "Land Law – Easements and Freehold Covenants",
            "Advise on a land law dispute about an easement, a right of way between a dominant tenement and a servient tenement, a freehold covenant, Tulk v Moxhay, and section 62 LPA.",
        ),
    },
    {
        "topic": "land_coownership_constructive_trusts",
        "kind": "problem",
        "prompt": problem(
            "Land Law – Constructive Trusts",
            "Advise on a family home, common intention, beneficial ownership, a constructive trust, cohabitation, Stack v Dowden, Jones v Kernott, Lloyds Bank v Rosset, and TOLATA.",
        ),
    },
    {
        "topic": "land_leasehold_covenants",
        "kind": "problem",
        "prompt": problem(
            "Land Law – Leasehold Covenants",
            "Advise on the Landlord and Tenant (Covenants) Act 1995, original tenant liability, an authorised guarantee agreement, assignment of a lease, section 17, section 19, and K/S Victoria Street.",
        ),
    },
    {
        "topic": "international_commercial_arbitration",
        "kind": "essay",
        "prompt": essay(
            "International Commercial Arbitration",
            "Discuss party autonomy, the seat of arbitration, the New York Convention, the UNCITRAL Model Law, Kompetenz-Kompetenz, separability, the Arbitration Act 1996, Fiona Trust, and section 67.",
        ),
    },
    {
        "topic": "private_international_law_post_brexit",
        "kind": "problem",
        "prompt": problem(
            "Private International Law",
            "Advise on a cross-border dispute involving Rome I, Rome II, Brussels I Recast, Hague 2005, a choice of court clause, anti-suit injunctions, service out, and forum conveniens.",
        ),
    },
    {
        "topic": "public_international_law_customary_sources",
        "kind": "essay",
        "prompt": essay(
            "Public International Law – Sources",
            "Discuss customary international law, opinio juris, state practice, Article 38(1)(b), North Sea Continental Shelf, the persistent objector doctrine, and the ILC Conclusions on Identification of Customary International Law.",
        ),
    },
    {
        "topic": "public_international_law_state_responsibility_attribution",
        "kind": "essay",
        "prompt": essay(
            "Public International Law – Attribution",
            "Discuss state responsibility, attribution of conduct, the ILC Articles on State Responsibility, ARSIWA, Article 8, effective control, overall control, Nicaragua, Bosnia Genocide, and Tadić.",
        ),
    },
    {
        "topic": "public_international_law_immunities_icc",
        "kind": "essay",
        "prompt": essay(
            "Public International Law – Immunities and the ICC",
            "Discuss state immunity, immunity ratione personae, immunity ratione materiae, the Arrest Warrant case, Pinochet, universal jurisdiction, the Rome Statute, the International Criminal Court, Article 27, and Article 98.",
        ),
    },
    {
        "topic": "public_international_law_use_of_force",
        "kind": "essay",
        "prompt": essay(
            "Public International Law – Use of Force",
            "Discuss Article 2(4), Article 51, self-defence, anticipatory self-defence, Caroline, humanitarian intervention, responsibility to protect, Nicaragua, Oil Platforms, and cyber attacks.",
        ),
    },
    {
        "topic": "jurisprudence_hart_fuller",
        "kind": "essay",
        "prompt": essay(
            "Jurisprudence – Hart and Fuller",
            "Discuss jurisprudence, Hart, Fuller, legal positivism, natural law, the separation thesis, the internal morality of law, the rule of recognition, and the grudge informer debate.",
        ),
    },
]


EXCLUDED_TOPICS = {"general_legal", "mixed_legal_multi_unit"}
BANNED_GENERIC_SUBQUERY_LABELS = {
    "Question",
    "Events",
    "After moving in",
    "Before the purchase",
    "Leila wants to",
    "Duty of care",
    "Breach / standard",
    "Causation / scope / remoteness",
    "Doctrine / tests",
    "Policy / critique",
    "Cross-regime interface",
    "Immunity / jurisdiction framework",
    "Human rights & ECHR compatibility",
    "Reform / customary IL evolution",
    "Wrongful trading / s 214",
    "Misfeasance / undervalue / preferences",
    "Phoenix liability / disqualification / enforcement",
    "s 1 authorization",
    "s 3A tools offence",
    "s 3/3ZA + jurisdiction",
    "Salvage doctrine & reward",
    "Environmental salvage & SCOPIC",
    "Policy / reform / broader maritime",
    "Thomas: assisted suicide criminal liability",
    "Thomas: autonomy and Article 8",
    "Eleanor: CANH withdrawal framework",
    "Eleanor: MCA best interests and procedural route",
    "Leo: assault, battery, and transferred injury",
    "Maya: self-defence against the perceived second attack",
    "Ryan: causation and refusal of medical treatment",
    "Noah: excessive force by the security guard",
    "Clara: negligent misstatement and assumption of responsibility",
    "Daniel: downstream reliance and scope of duty",
    "Ethan: competitor loss and pure economic loss limits",
    "Arjun: conflicts, disclosure, and loyalty duties",
    "Lina and Marcus: care, skill, diligence, and oversight",
    "Dev: derivative claim and unfair-prejudice alternatives",
    "Amira: beneficial interest under trust",
    "Amira and Elias: proprietary estoppel",
    "Rapid Finance: priority, actual occupation, and overreaching",
    "Leila and remedies under TOLATA / equity",
    "Amira: resulting / constructive trust",
    "Rapid Finance: priority, actual occupation, overreaching",
    "Leila and remedies",
}


def _routed_topics_from_service_source() -> set[str]:
    text = Path("gemini_service.py").read_text()
    return set(re.findall(r'topic\s*=\s*"([^"]+)"', text)) - EXCLUDED_TOPICS


def _assert_case_coverage() -> None:
    routed = _routed_topics_from_service_source()
    covered = {case["topic"] for case in ROUTING_CASES}
    print("=" * 80)
    print("FULL TOPIC COVERAGE")
    print("=" * 80)
    print("service topics:", len(routed))
    print("covered topics:", len(covered))
    missing = sorted(routed - covered)
    extra = sorted(covered - routed)
    print("missing:", missing)
    print("extra:", extra)
    assert not missing
    assert not extra


def _assert_full_topic_routing() -> None:
    print("\n" + "=" * 80)
    print("FULL TOPIC ROUTING")
    print("=" * 80)
    for case in ROUTING_CASES:
        prompt = case["prompt"]
        topic = case["topic"]
        kind = case["kind"]
        label = "Essay Question" if kind == "essay" else "Problem Question"

        profile = _infer_retrieval_profile(prompt)
        subqueries = _subissue_queries_for_unit(label, prompt)
        sub_labels = [name for name, _ in subqueries]

        print(topic, "->", profile.get("topic"), "| subqueries:", sub_labels[:4])

        assert profile.get("topic") == topic
        assert profile.get("must_cover"), topic
        assert profile.get("expected_keywords"), topic
        assert profile.get("source_mix_min"), topic
        assert any(int(v or 0) > 0 for v in (profile.get("source_mix_min") or {}).values()), topic
        assert profile.get("issue_bank"), topic
        assert not any(
            str(authority).strip().lower().startswith(("of the ", "under the ", "and "))
            for authority in (profile.get("must_cover") or [])
        ), topic
        assert not any(label in BANNED_GENERIC_SUBQUERY_LABELS for label in sub_labels), topic


def run() -> None:
    _assert_case_coverage()
    _assert_full_topic_routing()
    print("\nFull topic routing matrix passed.")


if __name__ == "__main__":
    run()
