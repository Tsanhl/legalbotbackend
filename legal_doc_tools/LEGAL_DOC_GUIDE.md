---
name: review-docx
description: Perform a professional, lawyer-grade review of a DOCX essay or document. Use when the user asks to "review a docx", "check my essay", "proofread my paper", or "review my assignment". Covers grammar, fluency/coherence/structure, content/footnote/bibliography accuracy, and a final holistic pass — outputting a polished, 10/10 standard essay that stays near a user-requested target/limit (or near the original if none is given), while keeping all original DOCX formatting unchanged. If the user requests implemented changes, only the changed wording is marked in **yellow highlight**.
---

# Workflow


## Architecture (required)

Use one main agent (orchestrator) plus specialist sub-agents run sequentially. Each pass builds on the previous one. The orchestrator owns the final output and ensures nothing is missed.

### Main agent (orchestrator) responsibilities

- Receive the user's DOCX file (and essay question / marking rubric, if provided).
- Determine the governing question source using this default priority:
  1. question/prompt pasted by the user in chat or terminal;
  2. question/prompt explicitly stated as included inside the DOCX (for example a `Question:` block at the top);
  3. if no question is provided, infer topic/thesis from the document and use that as the benchmark.
- If the user provides a target benchmark (`tgt`) such as question/prompt/rubric/marking criteria, run an explicit fit check and verify whether the essay fully satisfies that target before final delivery.
- If the user provides a question/prompt/rubric, run a mandatory question-led enhancement pass, not just a fit check: identify missing issues, missing arguments, missing counterarguments, weak rebuttals, and underdeveloped evaluative steps that are needed to reach a genuine top-band / 90+ answer.
- Parse terminal prompt instructions first (scope, exclusions, word-count target/limit, and any "exclude bibliography/abbreviations" directions).
- Extract the full text, footnotes, and bibliography from the DOCX.
- In every `amend` or `review + amend` workflow, run a mandatory sentence-by-sentence perfection pass across the full amendable text and a line-by-line verification pass across every footnote and bibliography/reference entry. This is baseline amend scope, not an optional extra pass.
- In every `amend` or `review + amend` workflow, identify the remaining inferential, evidence-sensitive, or potentially overstated propositions and either (a) densify their authority support or (b) reframe them expressly as inference, investigation, or contingent application points. Do not leave this for a later follow-up unless the user explicitly narrows scope.
- In every `amend` or `review + amend` workflow, run a final microscopic style-level polish pass across the full amendable text after the main perfection pass. This last-mile pass must remove residual micro defects such as comma noise, punctuation friction, awkward cadence, minor repetition, register wobble, hyphenation inconsistency, and other tiny style issues without materially increasing length unless the user explicitly allows it.
- Treat the user's first amend request as `default_perfection` by default, and treat `default_perfection` as the full comprehensive amend standard: no withheld “last margin”, no lighter first pass, and no deliberate reservation of inferential-source tightening for a later run. Only switch to a deeper-than-default amend intensity if the user explicitly asks for deeper/perfection-beyond-default work.
- Detect and extract reviewer comments from both sources when present: (a) Word/DOCX comment-function comments, and (b) inline written comments in document text (for example `Comment:`, `Feedback:`, `Note:`, `Issue:`, `Query:`, `Request:`, or `Instruction:`, including bracketed or parenthesised forms).
- If the user says "based on comments" for either `review` or `amend`, treat extracted comments as mandatory primary scope, then run an additional full-document improvement pass to fix issues beyond those comments.
- Keep all original document formatting unchanged (font family, font size, spacing, indentation, heading styles, numbering, margins, and layout); do not normalise or restyle any content.
- Run all four review passes in order: Grammar → Fluency/Coherence/Structure → Accuracy → Final Holistic Check.
- Merge all corrections into a single final output.
- Enforce word count targeting: keep the amended output near the user's requested target or word-limit for the whole essay. If no target/limit is given, preserve the original length (default ±2%).
- Record the active word-count instruction in the amend context and ensure the final output follows it. If the user gives a maximum, do not exceed it. If the user gives a target, stay near it. If the user gives neither, preserve original length by default.
- When adding new analysis to satisfy a user-provided question, prompt, or rubric, also add any missing authority support needed for those new points in the active citation style (default OSCOLA) and then compress elsewhere if necessary so the final output still satisfies the active word-count rule.
- Present a summary of all changes made, grouped by category.
- When generating a refined DOCX (Pass 5), preserve the original DOCX styling exactly. For any implemented amendment, apply **yellow highlight** to changed wording.

## Top-Band Production Layer (mandatory when the user asks for 90+, 10/10, distinction, first-class, top-band, or "make this better")

- Run an explicit **benchmark-decomposition step** before drafting or amending: identify the command word, legal issues, issue order, thesis position, required counterarguments, likely authorities, and the word-budget per issue.
- Build a **gap map** against the benchmark and the draft: what is missing, under-supported, repetitive, too descriptive, insufficiently analytical, weakly concluded, or not yet tied back to the question.
- For essays, make every body section carry a clear **evaluative job** (for example doctrinal tension, policy consequence, theoretical critique, institutional explanation, or reform argument). Descriptive sections without an evaluative job must be upgraded or cut.
- For problem questions, run an explicit **outcome map** for each party / issue: threshold, governing test, strongest argument, strongest counterargument, likely result, practical remedy, and immediate next step.
- Run an **authority hierarchy check**: primary authorities first (legislation, cases, official materials), then journal commentary, then textbooks only as support. Added scholarship must sharpen analysis, not merely decorate it.
- Run a **critical-density check**: each substantive paragraph should contain a legal proposition, authority support, analysis of why it matters, and a mini-link back to the benchmark or overall thesis.
- Run a **redundancy audit** before delivery: remove repeated case explanations, repeated policy points, repeated quotations, repeated conclusions, and repeated scene-setting that spend word count without adding marks.
- Run a **weakness-rescue pass**: identify propositions that sound absolute, under-evidenced, too broad, or too certain; either add verified support or reframe them in calibrated terms.
- Run a **section-end verdict rule**: each major section must end with a short evaluative or outcome sentence; do not leave sections hanging as neutral summaries.

## RAG + Search Augmentation (mandatory for answer-production and amend workflows when available)

- Use indexed law materials as the **first retrieval layer** for both fresh drafting and amend/review work. The system must actively check whether indexed materials reveal stronger cases, legislation, journal commentary, counterarguments, or rebuttals than those currently used in the draft.
- For legal answer-generation and amend/review generation, the backend must trigger this indexed retrieval layer automatically before drafting. Do not treat RAG as optional for those requests.
- For amend/review requests, treat the uploaded draft as a **primary working document** and compare it against the indexed corpus to identify what can be added, corrected, strengthened, verified, or cut.
- If indexed coverage is thin, outdated, or missing a needed authority, use **online search as a second layer** to verify or supplement the answer. Search is for verification and gap-filling, not for padding or speculative citation.
- When online search is used, prefer **primary and official sources first** (courts, legislation databases, official guidance, publishers with authoritative metadata), then high-quality secondary commentary if needed.
- Recent-law / current-awareness trigger: if the issue may have changed recently (new case, new statute, new consultation, current enforcement position, recent academic debate), perform a targeted verification search before treating the proposition as settled.
- RAG + search must be used to test whether the draft is missing: newer authority, a better leading case, a stronger statutory hook, a stronger counterargument, a rebuttal, a more precise remedy point, or a better academic dispute.
- Never carry unverified search results straight into the final answer. Added material must be checked for existence, relevance, and metadata accuracy before it is treated as established authority.

## Direct-Code And Website Execution Modes

- **Direct-code / terminal mode:** if the user asks to amend/review a DOCX, extract the draft text, apply the full review standard, use RAG plus search to strengthen it, and then either (a) produce amendment-ready replacement text / instructions for the amend engine or (b) run the amend DOCX flow when the implementation path is available.
- **Direct-code mode meaning (clarification):** this mode is separate from website multipart/UI delivery. By default, direct-code answer/amend text generation uses whichever backend provider the user selected or configured (`Gemini`, `OpenAI`, `Anthropic/Claude`, or `xAI`). When no usable provider key is configured, the backend may fall back to a local Codex adapter for direct-code answer/amend generation if the Codex CLI is available. Separately, the large-DOCX amend runner also supports a Codex/local no-provider workflow via exported section-plan JSON files (`--export-plan-dir` then `--plan-dir`), with the local DOCX read/apply/refine/highlight pipeline applying those plans after review.
- **Website mode:** uploaded DOCX/text/PDF drafts must be read as substantive input, not merely listed by filename. The website flow must use the uploaded draft text together with RAG plus search and these rules to produce either a review, a direct amended version, or amendment-ready replacement paragraphs depending on the user's request.
- **Website amend delivery:** when the user requests implemented amendments, the website should generate the amended DOCX through the backend/API workflow, present a chat confirmation, and expose the file via a download action for the user.
- **Website/API rule (clarification):** website generation always needs a configured provider key/model for the selected backend provider. The Codex local adapter is for direct-code/backend mode only. Website mode differs from direct-code mode mainly in UI delivery and long-answer split enforcement.
- In both modes, if the user provides the question / rubric in chat, that overrides any inferred benchmark; if the user says the question is inside the document, extract it and use it.
- In both modes, if the user asks for amendments rather than a report, prefer **directly usable amended wording** over vague feedback.

### Sub-agents (specialists)

1) **Grammar sub-agent (Pass 1)**
2) **Fluency, Coherence & Structure sub-agent (Pass 2)**
3) **Accuracy & Citations sub-agent (Pass 3)**
4) **Final Holistic sub-agent (Pass 4)**

If sub-agents are not available, emulate this architecture by running these roles sequentially and labelling outputs clearly.

---

## Operation Modes (mandatory)

### Mode A — Review

Required deliverable:
1. **Review report DOCX** only.

### Mode B — Review + Amend

Required deliverables:
1. **Review report DOCX** (must include content-improvement comments/roadmap).
2. **Amended DOCX** with marked changes (yellow highlight by default).

### Mode C — Amend

Required deliverable:
1. **Amended DOCX** only (marked changes by default: yellow highlight).
2. **Process requirement:** still run all four passes (Grammar, Fluency/Coherence/Structure, Accuracy/Citations, Final Holistic) before producing the amended DOCX.

Default amended variant policy: generate one amended DOCX variant only (marked: yellow highlight).

---

## Non-negotiables

- **ABSOLUTE ORIGINAL-FILE PROTECTION (NEVER VIOLATE).** The user's original DOCX is read-only. Never save, overwrite, or amend the original file path in place.
- **COPY-FIRST AMENDMENT FLOW (MANDATORY).** For every `amend` or `review + amend` task, create a new copy first and apply all changes only to that copy.
- **MARKUP-ONLY AMENDMENT RULE (MANDATORY).** Implemented amendments must be shown using **yellow highlight only**.
- **DEFAULT-MARKUP ENFORCEMENT (MANDATORY).** In `amend` and `review + amend`, yellow highlight is automatic by default; do not wait for the user to request markup.
- **NO NO-MARKUP EXCEPTIONS (HARD).** Do not produce unmarked/plain amended outputs. Every implemented amendment must remain yellow-highlighted.
- **NO DIRECT IN-PLACE OUTPUT.** If any command/script would write output to the original source path, stop and reroute output to a new amended file path before execution.
- **RUNTIME PATH-EQUALITY BLOCK (HARD).** Treat `output == original source path` as a hard error. Do not bypass; output must always be a new file path.
- **Protected Desktop-output rule.** Never overwrite the user's original source DOCX, and do not silently overwrite a prior final amended Desktop DOCX either. Use the canonical Desktop final filename first, then allocate `_v2`, `_v3`, and so on for later amend runs.
- **Zero tolerance for introduced errors.** Every correction must improve the original — never introduce new mistakes.
- **Comment-first + beyond-comments rule is mandatory.** When the user requests `review` or `amend` "based on comments", resolve every DOCX/inline comment first, then perform a second independent pass to identify and fix further improvements not mentioned in comments.
- **Comment coverage evidence is mandatory for comment-based requests.** The verification ledger/report must include `Comments Unresolved: 0`, `DOCX Comment N:` entries for all Word comment-function comments, and `Inline Comment N:` entries for all inline written comments detected.
- **Target-fit verification is mandatory.** If the user provides an essay target (`tgt`) such as prompt/rubric/criteria, explicitly assess fit and close all material gaps so the final output fully matches the target.
- **Question-led argument expansion is mandatory.** When the user provides a question/prompt/rubric, do not stop at checking whether the current draft roughly answers it. Actively add any missing argument, counterargument, rebuttal, qualification, or evaluative comparison needed for a strong top-band answer.
- **Top-band counterargument duty is mandatory.** For benchmarked legal essays, add concise counterarguments and rebuttals wherever they materially improve analytical balance, precision, or persuasiveness.
- **Authority support for added analysis is mandatory.** If the amend pass adds a new substantive legal point, counterargument, or rebuttal, add a real and verified supporting authority where the point would otherwise be under-supported, using the active citation style (default OSCOLA).
- **Marker-feedback clarity rules are mandatory.** Remove unnecessary scope disclaimers, define the geographical/jurisdictional referent where a forum or court is mentioned, and avoid deictic phrasing such as `this development`, `that contrast`, `that structure`, `this approach`, `that rule`, `it`, or `the former/latter` unless the antecedent is explicit in the immediately surrounding text. If a shorthand noun phrase is used, name the underlying doctrine or concept again (for example `that obligation-based structure` rather than `that structure`).
- **Marker-feedback repetition handling is mandatory.** If a marker comment says a point has already been made, do not merely trim both versions. Remove the earlier or weaker instance and keep the stronger formulation in the paragraph that actually performs the analytical work, usually as that paragraph's topic sentence.
- **Jurisdiction-specific wording discipline is mandatory.** Do not use vague locational qualifiers such as `particularly in the UK context` unless the sentence also explains the legal reason that geography matters (for example, a term is legally inapt under UK law or a disclosure claim is not confined to a UK legal duty or court order).
- **Fact-matched actor labels are mandatory.** Use the noun that best matches the problem facts and legal relation. If the facts are framed in terms of consumers, prefer `consumer choice` / `consumers` rather than drifting between `users`, `consumers`, and `customers` without reason.
- **Competition-law abuse-selection discipline is mandatory.** In Article 102 / Chapter II work, locate dominance and abuse in the undertaking rather than the product; do not over-plead `self-preferencing`, `discrimination`, or other weaker abuse labels where the facts mainly support tying, defaults, pre-installation, exploitative terms, or another stronger route.
- **Competition-law pricing-characterisation discipline is mandatory.** If proposed end-user discounts or price rises do not satisfy the orthodox equivalent-transactions / competitive-disadvantage template for discriminatory abuse, treat them as contextual support for a broader exploitative theory unless the facts genuinely justify a standalone section 18(2)(c) / Article 102(c) analysis.
- **Competition-law objective-justification specificity is mandatory.** When a defence is based on court orders, statutory duties, security, or technical integration, identify the specific duty or legitimate aim, then test evidence, proportionality, and less restrictive alternatives. Do not accept broad, over-inclusive wording as justified merely because it invokes compliance or security.
- **Section-placement discipline is mandatory.** A paragraph must sit in the section whose work it actually performs. Transitional or contrast-setting paragraphs must open the section they introduce, not trail the previous section.
- **No unexplained contrasts or first-use shortcuts.** Do not write `that contrast`, `this limit`, `the earlier point`, or a comparable shortcut unless the underlying concept has already been expressly identified. If necessary, name both sides again rather than relying on vague shorthand.
- **Related demerits must be integrated.** Where two adjacent sentences describe the same limitation, weakness, or caveat, present them as a single coherent analytical unit rather than splitting the same criticism awkwardly across sentences or paragraphs.
- **Conclusion anti-duplication rule is mandatory.** Do not place a mini-conclusion or section-ending paragraph that simply repeats the final conclusion. Section endings may narrow, qualify, or transition the point, but the final conclusion must retain distinct closing work.
- **Preserve the author's voice and intent.** Do not rewrite the essay in a different style. Enhance, do not replace.
- **Tone default and override.** Default tone is formal, academic, and professional (lawyer-grade). If the user explicitly requests a different tone, follow the user’s tone request.
- **Preserve DOCX typography.** In refined DOCX output, retain the font family/size/style used by the user (including heading/body differences). Do not switch to a different default font.
- **User style lock (including footnotes).** Preserve the user’s font family, font size, paragraph style, spacing, and local typography in body text and footnotes; do not restyle content.
- **User-original style is the only style source.** All amendments must be based on the user’s original DOCX font, font size, and paragraph style at the exact local position. Never substitute styles from another file or from application defaults.
- **Run-level style inheritance is mandatory (global rule).** For every inserted/amended DOCX segment (including bibliography lines), inherit typography from the nearest unchanged local run/paragraph in the same section: same font family, font size, paragraph style, spacing, indentation, and alignment. Never apply direct font-name or font-size overrides that differ from the user’s local style.
- **Inserted-text local style parity is mandatory.** Any newly added or replaced wording must match the user’s nearby unchanged content in font family, font size, paragraph style, spacing, and local emphasis pattern. No inserted text may fall back to application-default styling.
- **Font-weight/emphasis integrity is mandatory.** Preserve the user’s original run emphasis (bold/italic/underline/small caps/case formatting) on unchanged text. For inserted or replaced text, clone local run emphasis first, then apply amendment markup additively only.
- **Bibliography bolding rule (mandatory).** In bibliography/reference sections, bold only the section headings such as `Bibliography`, `Table of Cases`, `Table of Legislation`, `Journal Articles`, `Books`, and comparable source-type headings. Do not bold the case entries, journal entries, legislation entries, or other source entries themselves unless the user explicitly requests a different house style.
- **Local font/style parity means exact user styling.** In body text and footnotes alike, amended wording must keep the same local font family, font size, paragraph style, spacing, and emphasis pattern that the user used at that exact location. The engine must not restyle content merely because OSCOLA normalisation is being applied.
- **Paragraph property inheritance is mandatory.** For inserted/amended lines, clone paragraph properties (`style`, line spacing, space before/after, indents, alignment) from adjacent unchanged paragraphs in the same section. Never leave inserted lines with default/blank paragraph properties when neighbors use explicit settings.
- **No formatting mutations are allowed.** Improve content only. Do not change any existing formatting attribute (font, size, colour, italics, underline, spacing, alignment, indentation, list formatting, page layout, headers/footers, tables, captions, or styles). Only permitted formatting change: for implemented amendments, apply **yellow highlight** to changed/added wording only.
- **Desktop-root output hard rule (runtime-enforced).** For legal review workflows, every final artifact (`review_report.docx` and/or amended DOCX) must be saved directly in the user Desktop root (`/Users/hltsang/Desktop`) and never inside subfolders.
- **No output subfolders.** Do not create or use nested output folders for final artifacts.
- **Workspace-output prohibition.** Never deliver final artifacts inside `/Users/hltsang/Desktop/Skills`.
- **Path disambiguation is mandatory.** If similarly named DOCX files exist in multiple Desktop folders, resolve and use the exact user-intended absolute path before editing. Do not assume Desktop root when an active project subfolder contains the target file.
- **Non-destructive amendment workflow is mandatory.** Never directly amend the user’s source DOCX file in place. First create a copy, apply amendments to that copy, and deliver a new output DOCX.
- **Word count compliance.** Keep the amended output near the user-requested target or declared word limit for the whole essay.
  - Terminal prompt constraints override defaults for amendment scope, but quality checks (accuracy, coherence, structure, citation integrity) still apply to the full submitted material unless the user explicitly says review scope is limited.
  - If the user gives a target number (for example, 2500 words), aim to stay within about ±2% unless the user asks for exact matching.
  - If the user gives a maximum limit, do not exceed it; target the upper band (about 95-100% of the limit) unless instructed otherwise.
  - If no target/limit is provided, keep the final output approximately the same length as the original (±2%).
  - Do not pad or cut content without purpose.
- **Exclusion handling is mandatory.** If the user provides bibliography and/or abbreviations content but marks it as excluded from amendment, do not edit those excluded sections; still run checks on them and report any accuracy/coherence/citation issues.
- **Every footnote and bibliography entry must be verified.** If a citation cannot be verified, flag it clearly — never silently remove or fabricate citations.
- **Absolute source integrity is mandatory.** Final delivered output must contain zero fake content, zero fake citations, zero fake footnotes, and zero fake bibliography entries.
- **Real-source integrity is mandatory.** Check that each reference exists and that its metadata is internally correct for that source type (for example: author-title-journal-volume/issue/year/pages; case name-neutral citation/court/year; legislation title/year/jurisdiction).
- **User-source and amendment-source parity is mandatory.** Apply the same 100% real-and-accurate verification standard to: (a) all sources already present in the user's original footnotes/bibliography, and (b) every source added, replaced, corrected, or amended during review. Never keep or introduce an unverified source.
- **No hallucinated references.** Never invent sources, page numbers, dates, or case names.
- **Missing-citation completion rule.** If a substantive legal claim lacks supporting authority, add a real and verified source in the active citation style (default OSCOLA unless user requests another style). In DOCX amend workflows, do not create a brand-new Word footnote by default for that added support; if no relevant existing footnote can be corrected or reused, place the added authority in inline parentheses `(...)` immediately after the relevant sentence.
- **Default full-verification on every review request.** For both `review` and `review + amend`, verify all substantive content claims and all footnotes/references/bibliography entries (if present).
- **Default full-verification on every amend request.** For `amend` and `review + amend`, perform sentence-by-sentence improvement review across the full amendable text and line-by-line verification of every footnote and bibliography/reference entry by default. This is not a second-pass extra; it is the default amend standard.
- **Amend quality gate is mandatory.** In `review + amend` and `amend`, the amended output must meet top-mark (10/10) quality and be fully verified, including all footnotes.
- **Code-level amend quality gate is active.** The amend engine must reject runs unless review context explicitly records sentence-by-sentence checking, content/perfection review, and footnote/bibliography verification where present. If a question or rubric is provided, the amend run must also record question-based amendment and `Fully fits target`.
- **Benchmarked-amend code gate is active.** If a question or rubric is provided, the amend engine must also reject runs unless review context explicitly records question-led argument coverage, explicit counterargument/rebuttal review, and verified authority support for any added substantive points.
- **Microscopic style-excellence gate is active.** The amend engine must also reject runs unless review context explicitly confirms that a final microscopic style polish was completed across the whole amendable text and that no residual micro-level style defects were knowingly left unresolved.
- **Amended citation/link accuracy gate is active.** If an amend run adds or corrects footnotes/references, the amend engine must also reject the run unless review context explicitly confirms that amended citations were accuracy-checked and amended URLs/links were checked for accuracy.
- **Default-depth + word-count gate is active.** The amend engine must also reject runs unless review context explicitly records the amend depth (`default_perfection` or `deeper_on_request`) and the active word-count rule (`preserve_original_length`, `near_target`, or `at_or_below_max`) together with confirmation that the rule was followed.
- **Logical-coherence gate is active.** The amend engine must also reject runs unless review context explicitly confirms that logical flow, paragraph-to-paragraph coherence, and the absence of unresolved illogical jumps were checked.
- **Original-footnote preservation gate is active.** The amend engine must reject runs that silently remove original body footnote markers or alter original footnote text without an explicit correction instruction.
- **Reader-experience excellence gate is mandatory.** Final amended writing must read as clear, coherent, and fluent expert-level prose with no unresolved logical gaps.
- **90+ mark / 10/10 perfection standard (mandatory).** Every amended output must meet the standard of a 90+ mark, professionally exceptional lawyer-grade piece of writing. This means: zero grammar/spelling errors, flawless coherence and logical flow, 100% citation accuracy in the active style (default OSCOLA), no unsupported claims, publication-ready prose quality, and full question/rubric alignment where provided.
- **Last-mile polish is mandatory.** Default `amend` quality includes tiny style refinement, not only substantive correction. Unless the user requests otherwise, do not stop at “good enough” if small wording, punctuation, rhythm, or consistency improvements can still be made without harming meaning or word-count compliance.
- **No shortcut amend pass.** Do not output an amended DOCX from patch-only edits unless the user explicitly requests a narrow-scope fix; default `amend` requires full content check first.
- **Live footnote numbering integrity is mandatory.** Preserve the user's real Word footnote markers/IDs; do not delete, renumber, or break them. However, textual cross-references such as `(n 12)` must be corrected whenever the cited note number is wrong or stale, and updated to the latest accurate footnote number.
- **Relevant-and-correct original footnotes must be preserved.** Do not delete or rewrite a user’s original footnote if it remains relevant and accurate. Only change an original footnote when there is a concrete correction reason, and record that change explicitly.
- **Accurate original footnotes are default-preserve.** If the user’s existing footnote text is already accurate and compliant enough for the active footnote style, leave it exactly as it is. Do not restyle, expand, or convert it merely for cosmetic consistency.
- **Reference-presentation preservation is mandatory.** If the user’s document uses Word footnotes/endnotes, preserve the existing live footnotes/endnotes and amend their text or placement where needed, but do not add brand-new Word footnotes by default in DOCX amend workflows. If an amended sentence needs extra support beyond the existing notes, place that added authority in inline parentheses `(...)` immediately after the relevant sentence instead, because newly inserted DOCX footnotes may render empty in this workflow. If the user’s document already uses inline parenthetical references in `(...)`, preserve that system and add support in `(...)` after the relevant sentence. Only switch presentation style if the user explicitly requests it.
- **Footnote marker position integrity (hard rule).** In every footnote/endnote paragraph, keep the Word footnote number/reference marker at the start; all amended wording must appear after that marker.
- **No `ibid.37` order errors (hard rule).** Never place amended wording before the footnote number marker. Enforce number-first rendering (for example, `37 ibid.` not `ibid.37`).
- **DOCX footnote text must be plain text only.** In amendment plans and scripted footnote replacements, do not emit literal markdown emphasis markers such as `*...*`, `**...**`, or backticks. The DOCX engine applies formatting separately; footnote text itself must not contain literal markdown punctuation.
- **Body-text footnote placement integrity (hard rule).** In the main document body, every footnote reference marker must remain attached to the exact word, case name, clause, proposition, or sentence it supports. Never let body footnote markers drift to arbitrary later words because of text amendment or character-offset syncing.
- **Body-text footnote relevance review (mandatory).** Whenever a sentence or paragraph is materially rewritten, recheck each body footnote marker manually and reposition it if necessary so the citation sits at the correct legal authority or sentence-ending point. Do not leave a marker stranded in the middle of an unrelated phrase (for example, after a generic noun such as `value` or `winning` when the authority cited is actually *Schibsby* or *Abouloff*).
- **Body-text footnote code guard (mandatory).** The refinement/gate scripts must also apply a code-level safeguard: auto-normalise clearly stray body footnote markers back to a unique cited case-name anchor where the current anchor is a generic word, and fail the gate if suspicious detached markers still remain.
- **No-fake-source default for all outputs.** In every final output (review report and/or amended DOCX), do not present fake or unverified sources as valid. Anything unverified must be clearly marked unverified and must not be treated as established fact.
- **If the user provides the essay question or marking rubric, every structural and content decision must be evaluated against it.**
- **Benchmark-fit gate applies in amend modes too.** If the user provides a question, prompt, rubric, or other benchmark, `amend` and `review + amend` must verify and reach `Fully fits target` before delivery.
- **Question-source flexibility is default.** The governing question may come from chat/terminal text or from inside the DOCX when the user says it is included there.
- **All four passes are mandatory.** Do not skip or merge passes.
- **The final output must be publication-ready.** It must read as a polished, 10/10 piece of academic writing at professional lawyer standard.
- **When the user requests amendments (implemented output):** deliver only fully verified content/citations. No unresolved verification items may remain in the amended DOCX.
- **Report artifact rules are mode-driven.** `review` requires report DOCX; `review + amend` requires report DOCX + amended DOCX; `amend` requires amended DOCX only.
- **Amend default delivery.** For amend requests, deliver the amended DOCX by default.
- **First-pass completeness gate.** Required artifacts must exist per mode before completion.
- **Runtime gate enforcement is mandatory.** Before final delivery, run `scripts/validate_delivery_gates.py` for the active mode and do not deliver output unless the script exits with code `0`.
- **Verification-ledger gate input is mandatory for amend modes.** For `amend` and `review + amend`, provide a verification ledger to the gate script; it must include a numeric `Unverified` summary and `Footnote N:` entries covering all original footnotes.
- **Internal markdown artifacts are non-deliverables by default.** Files such as `*_verification_ledger.md` (for example `Test_verification_ledger.md`) and any other intermediate `*.md` notes are runtime/internal artifacts only and must not be shown or listed to the user unless the user explicitly requests them.
- **One-off artifact cleanup is mandatory.** Any temporary, amend-specific artifact created only for a single run (for example one-off JSON configs, temp question/rubric files, transient context dumps, verification ledgers, or throwaway helper files in `/tmp` or `legal_doc_tools/tmp`) must be deleted automatically after a successful amend run. Keep only general reusable scripts and permanent project files.
- **One-off helper code cleanup is mandatory.** Any throwaway helper script or helper directory created solely to complete one amend run must be deleted automatically after a successful amend run when it is explicitly registered as a cleanup target.
- **Doc-specific instruction/test cleanup is mandatory.** If a run creates temporary instruction files, prompt files, helper test files, or one-off helper code tied only to one user DOCX, register them as one-off cleanup targets and delete them automatically after the amend succeeds, even when that helper directory is outside the temp folders.
- **Workspace deliverable cleanup is mandatory.** Do not leave behind one-off deliverable copies or draft source packs inside the project/workspace. Any task-specific `*.docx`, `*.md`, `*.txt`, `*.json`, or similar helper artifact created only to prepare one user's final output must be deleted after successful completion unless the user explicitly asks to keep it.
- **Desktop-DOCX-only final-output rule is mandatory for one-off document jobs.** When a task's intended deliverable is a final DOCX, keep the final deliverable as the Desktop DOCX only. Do not retain note-source markdown, one-off render scripts, or duplicate workspace DOCX copies once the final DOCX has been produced successfully.
- **No essay-specific or problem-question-specific hardcoding in permanent workflow code.** Do not leave behind reusable-code changes that are specific to one essay, one coursework question, one problem question, one student file, one case list, or one source pack. Any such task-specific helper logic must live only in a recognised one-off temp location and must be auto-deleted after the run.
- **Source-specific prompt/rule cleanup is mandatory.** If a run requires custom instructions tied only to a single document or benchmark, keep them in transient runtime context or a one-off temp artifact; do not persist them in permanent workflow prompts, guides, or application defaults after the task completes.
- **Protected Desktop final path is mandatory.** After a successful amend run, keep the final amended DOCX in Desktop root using the canonical filename if available, or the next protected versioned sibling (`_v2`, `_v3`, and so on) if an earlier final output already exists.
- **Report format when requested.** If a report is requested, produce it as DOCX by default.
- **Amendment markup default is mandatory.** Every implemented amendment output must visibly mark changed wording in **yellow highlight** only.
- **Amended DOCX variant default.** For amend requests, generate exactly one amended DOCX variant for that run: the marked version (yellow highlight).
- **Single-run output policy.** For each amend run, generate one final marked DOCX and present only that run's final file path. Do not overwrite the source DOCX or a prior final amended Desktop output.
- **Dual-delivery scope clarification.** “Dual-delivery” means amended DOCX + review report DOCX.
- **Explicit user requirements override defaults.** If the user gives a specific word count, citation style, exclusion, bibliography/reference instruction, delivery location, or formatting constraint, follow that instruction over generic workflow defaults unless a higher-priority rule forbids it.
- **Citation style lock:** If the user requests a citation style, follow that style. If no style is requested, default to OSCOLA.
- **Harvard override rule (mandatory when Harvard is expressly requested).** If the user expressly asks for Harvard referencing, switch the active style from OSCOLA to Harvard author-date and keep that style consistent across the whole output.
- **Standard Harvard structure (mandatory when Harvard is active).** Use in-text author-date citations plus a final `References` section when references are requested or required by the task. Do not use citation footnotes, `ibid`, `op. cit.`, or OSCOLA short-form cross-references in standard Harvard mode.
- **Harvard pinpoint rule (mandatory when Harvard is active).** For direct quotations, include page numbers where verified; for online sources without page numbers, use paragraph numbers where available.
- **Harvard author rule (mandatory when Harvard is active).** Use the organisation as author where appropriate; if there is no author, use the source title. Distinguish same-author same-year items with `2024a`, `2024b`, and so on where needed.
- **Harvard legal-material caveat (mandatory when Harvard is active).** Cases and legislation in law assignments may follow an institution-specific legal-Harvard variant. If the user provides a house style or the draft clearly uses one, preserve that institutional pattern consistently rather than defaulting back to OSCOLA.
- **OSCOLA correction duty (footnotes/references).** When OSCOLA is active, if user-provided footnotes or bibliography/reference entries are non-compliant, amend them to OSCOLA-compliant form in the output.
- **OSCOLA author-name separation rule (mandatory).** Under OSCOLA, bibliography name formatting is not the same as footnote name formatting. In footnotes, give personal author/editor names in the form used in the publication. In bibliography/reference entries, invert personal names to `Surname Initial,` (surname first, then initial(s), followed by a comma). Do not reuse footnote-style name order in bibliography entries.
- **OSCOLA `ibid` typography hard rule.** In footnotes/endnotes, `ibid` must always be lowercase, roman text (not italicised, not underlined, not quoted).
- **OSCOLA footnote shorthand rule (DOCX footnote mode).** In real footnotes/endnotes, use ordinary OSCOLA shorthand where appropriate: `ibid` for the immediately preceding source, and a short-form case name plus `(n X)` for later non-consecutive references. This shorthand rule applies to DOCX footnote workflows only; it does not override the project's separate plain-text inline-citation house style.
- **OSCOLA `ibid` with pinpoints (DOCX footnote mode).** If the immediately preceding footnote cites the same source but a different pinpoint is needed, use `ibid, para X.` / `ibid, paras X-Y.` / `ibid, 123.` as appropriate.
- **OSCOLA case short forms in footnotes (DOCX footnote mode).** For a later non-consecutive citation to the same case, use a short-form case name followed by `(n X)`, for example `Google Shopping (n 15).` Add the pinpoint after the cross-reference where needed.
- **OSCOLA short-form case-name preservation/correction rule (DOCX footnote mode).** If the user has already italicised a short-form case name correctly (for example `Hoffmann-La Roche (n 5).` or `Intel (n 5).` with only the case-name portion italicised), preserve that formatting. If the user omitted required italics for a genuine case-name short form, add the missing italics to the case-name portion only. Do not italicise the `(n X)` cross-reference itself.
- **When OSCOLA is the active style (footnotes/endnotes):** online URLs must be enclosed in angle brackets and formatted as `<link>.` (full stop after the closing bracket). If user entries use plain URLs, normalise them.
- **When OSCOLA is the active style (bibliography/references):** online URLs must be enclosed in angle brackets and formatted as `<link>` (no trailing full stop). If user entries use plain URLs, normalise them.
- **When OSCOLA is the active style (US case reports):** use `U.S.` reporter abbreviation (for example, `389 U.S. 347`), not `US`.
- **When OSCOLA is the active style (full citation requirement):** do not leave reporter placeholders (for example, `U.S. ___`) where a complete report citation is available. Use the complete citation.
- **Case-name typography (mandatory):** italicise case names in footnotes/endnotes, running-text citations, and ordinary bibliography case entries under OSCOLA. Do not auto-italicise `Table of Cases` entries: OSCOLA tables of cases keep case names in roman unless the user expressly asks for italic table formatting. Apply italics as formatting, not by inserting literal `*...*` characters.
- **Preserve-correctly / fix-only-when-missing rule.** If the user’s existing case-name italics are already compliant, preserve them. Only add or adjust italics where the current formatting is missing or clearly wrong under OSCOLA.
- **Body-italics preservation rule (mandatory).** In DOCX amend/review flows, body-text italic normalisation is additive only. Preserve the user’s existing italics, emphasis, and local run styling unless the formatting is clearly wrong under OSCOLA and requires a targeted correction. Do not strip user italics from ordinary prose merely because OSCOLA would not require italics there.
- **Footnote/bibliography italics preservation rule (mandatory).** In DOCX amend/review flows, footnote and bibliography italic correction is also additive only. Preserve the user’s existing italics and local emphasis choices; only add missing OSCOLA italics where a case name or other clearly required italic span has been omitted. Do not remove user-applied italics merely because the workflow could restyle them differently. `Table of Cases` entries are excluded from automatic italic addition unless the user expressly asks for italic table formatting.
- **Case-name typography in body text (mandatory):** when a case is discussed in the main body, italicise the case name there as well. This always applies to clear case-name forms (`X v Y`, `Re X`, `The Ship`) and explicit short-form cross-references tied to `(n X)`. For bare one-word body short forms such as `Brownlie` or `Spiliada`, preserve user italics if present, but do not auto-flatten other user italics or auto-infer italics from weak heuristics alone.
- **Case-name italic scope (mandatory):** "case name" means ALL of the following types, not just `X v Y`:
  - **Standard cases:** `X v Y` (e.g. *Adams v Cape Industries plc*).
  - **Ship name cases:** `The [ShipName]` (e.g. *The Eleftheria*, *The Angelic Grace*) — the entire case name including "The" is italicised.
  - **Re / In re cases:** `Re X` or `In re X` (e.g. *Re Spectrum Plus*) — the entire name including "Re"/"In re" is italicised.
  - **Short-form case name cross-references:** when a case name appears as a short form before `(n X)` in footnotes (e.g. *FS Cairo* (n 12), *Lungowe* (n 6)), the case name portion is italicised; the `(n X)` part is NOT italicised. (Note: ensure it is actually a case name; do not italicise short forms of journals, articles, books, or author names).
  - A **Table of Cases** is handled separately: keep case names in roman by default and preserve any existing user formatting there unless the user expressly asks for italic table formatting.
- **Case-name italic boundary (mandatory):** Only the case name itself is italicised. Years, volume numbers, page numbers, court abbreviations, report series, and all citation metadata are NEVER italicised.
- **Table of Cases ordering (mandatory):** In a Table of Cases, list cases alphabetically by first significant word and keep the case name in roman text by default. For EU cases not separately listed by jurisdiction, list them alphabetically by first party name with the case number following the case name in brackets, for example `Arne Mathisen AS v Council (T-344/99) [2002] ECR II-2905`.
- **EU case law format (mandatory when OSCOLA is active):** In footnotes/endnotes, give the case number first in roman text and then the case name in italics, with no punctuation between them. Since 1989 use `C-` for ECJ/CJEU cases, `T-` for General Court cases, and `F-` for Civil Service Tribunal cases; do not add `C-` to pre-1989 cases. In DOCX footnote workflows, do not represent those italics with literal `*...*` markers.
- **EU report preference (mandatory):** Prefer the European Court Reports (`ECR`) where available. ECJ/CJEU cases are reported in `ECR I-`; GC/CFI cases are reported in `ECR II-`. If no `ECR` citation is available, the second-best report is usually `CMLR`, unless the case appears in the Law Reports, the Weekly Law Reports, or the All England Law Reports (European Cases), which may be cited in preference to `CMLR`.
- **EU unreported cases (mandatory):** If an EU case is unreported, cite the relevant `OJ` notice. If it is not yet reported in the `OJ`, cite the case number and case name followed by the court and date of judgment in brackets.
- **EU pinpoints (mandatory):** For EU cases, use `para` / `paras` after a comma for pinpoint paragraph references; do not use square-bracket paragraph pinpoints in OSCOLA footnotes/endnotes for EU case law.
- **`ibid` is NEVER italicised (mandatory).** Under OSCOLA, `ibid` must always be lowercase roman text. Never apply italic formatting to `ibid`.
- **Author names are NEVER italicised.** In footnote cross-references like `Ungerer (n 1)` or `Lin and Guan (n 120)`, the author surname is not a case name and must not be italicised.
- **Non-case short forms are NEVER italicised (mandatory).** If a short form cross-reference before `(n X)` in a footnote refers to a journal article, book, website, or authors (e.g. Lin and Guan (n 120)), it is NOT a case name and MUST NOT be italicised. Italicise ONLY if the short form is actually a case name.
- **Short-form case-name hard rule (mandatory).** If a shorthand before `(n X)` is a case name, italicise it even when shortened (for example, `Adams (n 4)`, `VTB Capital (n 5)`, `Brownlie (n 10)`). This applies even where the referenced footnote contains mixed authorities. Journal titles, article titles, book titles, websites, and author-name shorthand must remain roman text.
- **DOCX short-form preservation rule (mandatory).** In DOCX amend/review flows, preserve an already-correct user-formatted short-form case citation exactly as formatted. If the user already has `Hoffmann-La Roche (n 5)` or `Intel (n 5)` correctly italicised in the case-name portion, do not restyle it. If the user omitted the required italics, add italics only to the case-name words and keep `(n 5)` in roman text.
- **Added-support rule for DOCX amendments (mandatory).** If the user missed a relevant supporting authority for a newly added point or for a sentence that needs support, do not create a new live Word footnote ID just to add it. Add the new authority in parentheses immediately after the relevant sentence in OSCOLA-style citation content instead, for example `... sentence. (Competition Act 1998, s 18; Case C-95/04 P British Airways plc v Commission [2007] ECR I-2331.)`
- **Plain-text inline OSCOLA typography rule (mandatory).** In bare text output that uses the project’s inline OSCOLA house style, italicise case names inside the parenthetical citation as well, using markdown italics where needed, for example `(...; Case C-95/04 P *British Airways plc v Commission* [2007] ECR I-2331.)`. Keep citation metadata such as case numbers, years, report series, page numbers, and `(n X)` cross-references in roman text.
- **Latin doctrinal phrase typography (mandatory where applicable):** italicise foreign-language doctrinal labels that have not been absorbed into English, including core private-international-law phrases such as *forum non conveniens*, *lex loci damni*, *lex fori*, *lex causae*, *lis pendens*, and comparable legal-Latin terms such as *terra nullius*, *mens rea*, *prima facie*, *inter alia*. Do NOT italicise common legal-Latin terms fully absorbed into English: *ratio decidendi*, *obiter dicta*/*obiter dictum*, *ultra vires*, *intra vires*, *stare decisis*.
- **No automatic title/bibliography italics rule (mandatory):** do not automatically add italics to bibliography entry names, bibliography titles, book/report/article titles, or comparable title-like text unless the active style clearly requires it. Automatic additions are reserved for case names and true legal-Latin/doctrinal terms only. Preserve user-applied italics unless they conflict with a clear OSCOLA prohibition.
- **Footnote-reference marker rule (mandatory):** Word footnote reference numbers/markers in the main text must never be bolded, highlighted, or otherwise marked merely because adjacent wording was amended. Markup belongs on changed wording, not on the live footnote reference marker itself.
- **Italic scope follows the active style and the user’s request.** Under OSCOLA by default, italicise case names and true foreign-language doctrinal terms only; do not italicise authors, ordinary descriptive words, or citation metadata unless the active style specifically requires it.
- **Local DOCX typography is authoritative in amend/review modes.** When amending a DOCX, preserve the user's local font family, font size, paragraph style, spacing, colour, and non-erroneous emphasis pattern at the exact location being amended. Do not flatten a footnote or paragraph into one generic template style if the user originally used mixed local styling.
- **Bibliography-only requests are check-first.** If the user asks to review/amend the bibliography specifically, the primary task is to verify accuracy (real source, correct author/title/year/journal/court/legislation details, and compliance with the active citation style). Do not rewrite entries for style unless a concrete error is found.
- **Bibliography/reference amend trigger is mandatory.** If the user asks to amend/check bibliography/references, or if bibliography/reference sections are detected, run full source-by-source verification for every bibliography/reference entry before delivery: existence, metadata accuracy, link validity, and date accuracy.
- **Bibliography/reference ledger coverage is mandatory in amend modes.** When bibliography/reference sections are present, the verification ledger must include `Bibliography Unverified: 0` (or `Reference Unverified: 0`) and `Bibliography Entry N:` (or `Reference Entry N:`) lines covering every entry.
- **When OSCOLA is the active style:** do not add a trailing full stop at the end of bibliography entries (for example, `Author, Title (Year)` not `Author, Title (Year).`).
- **When OSCOLA is the active style:** case names must be italicised in footnotes/endnotes and ordinary bibliography case entries. `Table of Cases` entries stay in roman text by default unless the user expressly asks for italic table formatting. In DOCX footnotes, this means real italic formatting rather than literal markdown markers.
- **OSCOLA citation format templates (mandatory when OSCOLA is active).** Use these exact formats when checking, correcting, or generating citations:
  - **Cases — footnote:** `Case name [year] volume Report page (court).` e.g. `Donoghue v Stevenson [1932] AC 562 (HL).` Case name italicised by formatting in DOCX output; do not type literal `*...*`.
  - **Cases — ordinary bibliography/reference list:** `Donoghue v Stevenson [1932] AC 562 (HL)` with the case name italicised by formatting where applicable.
  - **Cases — Table of Cases:** `Donoghue v Stevenson [1932] AC 562 (HL)`.
  - **EU cases — footnote:** `Case C-176/03 Commission v Council [2005] ECR I-7879, paras 47-48.`; `Case T-344/99 Arne Mathisen AS v Council [2002] ECR II-2905.`; `Case C-527/15 Stichting Brein v Jack Frederik Wullems [2017] OJ C195/02.` Case name italicised by formatting in DOCX output; do not type literal `*...*`.
  - **EU cases — footnote (not yet in OJ):** `Case T-277/08 Bayer Healthcare v OHMI—Uriach Aquilea OTC (CFI, 11 November 2009).`
  - **Footnote cross-reference shorthand:** `ibid.`; `ibid, para 72.`; `Google Shopping (n 15).`; `Google Shopping (n 15), para 118.`
  - **EU cases — Table of Cases:** `Commission v Council (C-176/03) [2005] ECR I-7879`; `Arne Mathisen AS v Council (T-344/99) [2002] ECR II-2905`.
  - **Legislation — footnote:** `Act name year, s section.` e.g. `Human Rights Act 1998, s 6.`
  - **Legislation — bibliography (Table of Legislation):** `Act name year` e.g. `Human Rights Act 1998`
  - **Books — footnote:** `Author, *Title* (edition, publisher year) page.` e.g. `HLA Hart, *The Concept of Law* (2nd edn, Clarendon Press 1994) 135.`
  - **Books — bibliography:** `Surname Initial, *Title* (edition, publisher year)` e.g. `Hart HLA, *The Concept of Law* (2nd edn, Clarendon Press 1994)`
  - **Journal articles — footnote:** `Author, ‘Article title’ (year) volume Journal page.` e.g. `Andrew Ashworth, ‘Testing Fidelity to Legal Values’ (2000) 63 MLR 633.`
  - **Journal articles — bibliography:** `Surname Initial, ‘Article title’ (year) volume Journal page` e.g. `Ashworth A, ‘Testing Fidelity to Legal Values’ (2000) 63 MLR 633`
  - **Chapters in edited books — footnote:** `Author, ‘Chapter title’ in Editor (ed), *Book title* (publisher year) page.` e.g. `John Smith, ‘Negligence and Duty of Care’ in Peter Cane (ed), *Tort Law* (OUP 2010) 120.`
  - **Chapters in edited books — bibliography:** `Surname Initial, ‘Chapter title’ in Editor (ed), *Book title* (publisher year)` e.g. `Smith J, ‘Negligence and Duty of Care’ in Cane P (ed), *Tort Law* (OUP 2010)`
  - **Websites — footnote:** `Author/Organisation, ‘Title’ (website, date) <URL> accessed date.` e.g. `UK Supreme Court, ‘Judgments’ (UKSC, 2023) <https://www.supremecourt.uk> accessed 2 March 2024.`
  - **Websites — bibliography:** `Organisation/Author, ‘Title’ (website, year) <URL>` e.g. `UK Supreme Court, ‘Judgments’ (UKSC, 2023) <https://www.supremecourt.uk>`
  - **Newspapers — footnote:** `Author, ‘Article title’ Newspaper (place, date) page.` e.g. `John Smith, ‘Court Reform Debate’ The Times (London, 12 March 2022) 6.`
  - **Newspapers — bibliography:** `Surname Initial, ‘Article title’ Newspaper (place, date)` e.g. `Smith J, ‘Court Reform Debate’ The Times (London, 12 March 2022)`
- **OSCOLA italics rules (mandatory when OSCOLA is active).** What to italicise and what NOT to:
  - **Italicise:** case names (full and short-form), book titles, ship names in case titles, foreign-language doctrinal terms not yet absorbed into English (e.g. *forum non conveniens*, *lex fori*, *lis pendens*, *mens rea*, *prima facie*, *inter alia*).
  - **Do NOT italicise:** `ibid`, `cf`, law report abbreviations (AC, QB, WLR), court names, statute/legislation names, journal titles, article titles (use single quotes instead), author names, citation metadata (years, volumes, pages), common legal-Latin terms fully absorbed into English (*ratio decidendi*, *obiter dicta*, *ultra vires*, *stare decisis*).
- **OSCOLA short-form case name rule (body text).** Short-form case names before `(n X)` must be italicised, and clear full-form body case names must be italicised. Bare body short forms without an explicit cross-reference may be preserved if already italicised by the user, but are not auto-normalised from heuristic inference alone.
- **Quote/apostrophe style preference.** Use typographic curly quotes/apostrophes in edited bibliography text (for example, `’…’` and `’`), unless the user explicitly asks for straight quotes.

---

## Pass 1 — Grammar Check

**Agent: Grammar sub-agent**

Systematically review every sentence for:

1. **Spelling** — correct all misspellings; respect British vs American English consistency (detect which the user uses and maintain it throughout).
2. **Punctuation** — commas, semicolons, colons, apostrophes, quotation marks (single vs double), hyphens vs en-dashes vs em-dashes, full stops.
3. **Subject-verb agreement** — singular/plural concordance.
4. **Tense consistency** — maintain the dominant tense; flag and fix unwarranted shifts.
5. **Article usage** — correct missing, extra, or wrong articles (a/an/the).
6. **Pronoun reference** — ensure every pronoun has a clear, unambiguous antecedent.
7. **Parallelism** — fix faulty parallel structures in lists and comparisons.
8. **Sentence fragments and run-ons** — fix without altering meaning.
9. **Word choice / malapropisms** — flag words used incorrectly (e.g., "effect" vs "affect", "principle" vs "principal").
10. **Preposition usage** — correct non-standard or awkward prepositional phrases.

**Output:** Corrected text with a changelog listing every grammar fix (original → corrected, with line/sentence reference).

---

## Pass 2 — Fluency, Coherence & Structure

**Agent: Fluency/Coherence/Structure sub-agent**

Using the essay question (if provided) as the benchmark, review:

### 2A — Sentence-level fluency
- Eliminate awkward phrasing, redundancy, and wordiness.
- Improve readability without changing meaning.
- Vary sentence length and structure to avoid monotony.
- Replace vague language with precise terms.

### 2B — Paragraph-level coherence
- Each paragraph must have a clear topic sentence.
- Logical flow between sentences within each paragraph.
- Effective use of transition words and linking phrases.
- No abrupt jumps in logic.

### 2C — Essay-level structure
- **Introduction:** Does it clearly state the thesis/argument? Does it outline the structure of the essay? Does it engage the reader?
- **Body paragraphs:** Does each paragraph advance the argument? Are they in the most logical order? Is there a clear progression of ideas?
- **Conclusion:** Does it summarise the key arguments? Does it answer the essay question directly? Does it avoid introducing new material?
- **Overall arc:** Is the argument sustained and developed throughout? Is the essay balanced (no section disproportionately long or short)?

### 2D — Question alignment (if essay question provided)
- Does every section directly address the question asked?
- Are all parts of the question answered?
- Is the thesis responsive to the specific prompt?
- Flag any off-topic or tangential sections.
- Provide a clear target-fit verdict (`Fully fits target` / `Partially fits target` / `Does not yet fit target`) and amend until it reaches `Fully fits target`.

**Output:** Revised text with a changelog listing every fluency/coherence/structure change, grouped by sub-category (2A/2B/2C/2D).

---

## Pass 3 — Accuracy of Content, Footnotes & Bibliography

**Agent: Accuracy & Citations sub-agent**

### 3A — Content accuracy
- Verify factual claims, dates, statistics, case names, legislation titles, and named principles.
- Verify each material factual/legal claim against reliable primary or authoritative sources where possible.
- If a claim appears incorrect or unsupported, flag it with a correction or a note requesting the user to verify.
- Ensure legal/technical terminology is used correctly (if applicable).
- Check that any quoted material matches the cited source (to the extent verifiable).

### 3B — Footnote accuracy & fake-source replacement
- Every footnote must be checked for:
  - **Scope parity (mandatory)** — this applies equally to user-original footnotes and any new/replacement/amended footnotes created during review.
  - **Existence and authenticity** — verify that the cited source actually exists. Use web search to confirm the source is real (correct author, title, publication, year). If a footnote references a **fabricated, non-existent, or hallucinated source**:
    1. Flag it clearly as fake/unverifiable.
    2. **Find a real, relevant, and accurate replacement source** that supports the same claim in the text. Search for genuine academic sources, case law, legislation, or authoritative publications that make the same or a closely related point.
    3. Replace the fake footnote with the verified real source, formatted in the active citation style (default OSCOLA if no style is requested).
    4. Log the replacement in the changelog: `Fake: [original fake citation] → Replaced with: [real citation]`.
    5. If no suitable real source can be found to support the claim, flag the claim itself as unsupported and recommend the user either remove the claim or provide their own source.
  - **Correct citation format** — follow the user-requested citation style; if no style is requested, use OSCOLA. Convert mixed citations to the active style consistently across all footnotes.
  - **User-error correction mandate** — if a user-provided footnote is wrong for the active style (including OSCOLA), amend it to the correct style format rather than leaving the error.
  - **Missing-footnote insertion mandate** — if a substantive claim has no support, add a real, verified authority in the active citation style. In DOCX amend workflows, prefer correcting/reusing an existing relevant footnote where possible; otherwise place the added authority in inline parentheses `(...)` immediately after the relevant sentence rather than creating a brand-new Word footnote.
  - **Metadata match (mandatory)** — ensure cited metadata matches the real source record:
    - Journal/article sources: author(s), article title, journal title, year, volume/issue, and first page/pinpoint must align.
    - Cases: case name, neutral citation or report citation, court, and year must align exactly.
    - Legislation: instrument title, year, section/regulation reference, and jurisdiction must align.
    - Books/chapters: author/editor, title, edition/year, publisher, and pinpoint (if used) must align.
  - **Author name(s)** — correctly spelled and in correct order for the active citation style.
  - **Title** — italicised or quoted correctly per source type (book, journal article, case, legislation, online source).
  - **Year, volume, issue, page numbers** — present and correctly formatted.
  - **Pinpoint references** — if a specific page or paragraph is cited, check it appears reasonable in context.
  - **Court and jurisdiction** — for case citations, ensure the court name and year are correct format.
  - **URL and access date** — for online sources, ensure URL is present and access date is included if required by the style. When OSCOLA is active, footnote URLs must be in angle brackets and formatted as `<link>.`.
  - **Cross-reference shorthand** — used correctly and referring to the right prior footnote. When OSCOLA is active: use 'ibid' (lowercase, not italicised) for immediately preceding source; use '(n X)' for earlier footnotes; do not use 'supra' or 'op cit' in OSCOLA. If the user cites the wrong footnote number in `(n X)`, amend it to the current accurate note number rather than preserving the mistake.
  - **Footnote marker order (hard)** — preserve the Word footnote reference marker/number at the start of each footnote paragraph; all amended text must follow the marker.
  - **`ibid` typography (hard)** — when OSCOLA is active, `ibid` must be lowercase roman only (never italicised).
  - **Sequential numbering** — footnotes must be numbered sequentially with no gaps or duplicates.
- Cross-reference: every in-text citation must have a corresponding footnote, and every footnote must correspond to a claim in the text.

### 3C — Bibliography / Reference List accuracy
- Every source cited in footnotes must appear in the bibliography (and vice versa — flag orphan entries).
- Apply the same verification standard to both user-original entries and any entries added/replaced/amended during review.
- Bibliography entries must follow the active citation style (default OSCOLA if no style is requested).
- **Legal OSCOLA format separation is mandatory.** In legal-doc mode with OSCOLA active, bibliography must use OSCOLA bibliography format (not OSCOLA footnote format); do not copy footnote formatting conventions into bibliography entries.
- If user-provided bibliography/reference entries are non-compliant with the active style, amend them to compliant format in the output.
- For bibliography/reference amend tasks (or when bibliography/reference sections are detected), verification must be source-by-source for every entry:
  - verify source existence/authenticity;
  - verify metadata fields (author, title, year, venue, volume/issue/pages, court/jurisdiction or legislation identifiers, as applicable);
  - verify URL reachability/validity where URLs are provided;
  - verify date fields (publication/adoption/filing/update/access dates) and correct any inaccuracies.
- For bibliography-focused requests, run an **accuracy audit first** and make only error-driven amendments:
  - Check for fake/non-existent sources.
  - Check for wrong author/title/year/volume/issue/page/court/jurisdiction metadata.
  - Check for wrong source type formatting under the active citation style.
  - Avoid unnecessary stylistic rewrites when an entry is already accurate.
- **When OSCOLA is the active style, apply OSCOLA bibliography rules:**
  - Divide into sections by source type: **Primary Sources** (Cases, Legislation, Treaties) and **Secondary Sources** (Books, Chapters in edited books, Journal articles, Online sources, etc.).
  - Within each section, list alphabetically by author surname (or case name / legislation title for primary sources).
  - In footnotes, personal author/editor names stay in the form used in the publication; in bibliography/reference entries, invert personal names to `Surname Initial,`.
  - Do NOT include pinpoint page references in bibliography entries (those belong only in footnotes).
  - Do NOT include 'ibid' or '(n X)' references in the bibliography.
  - Do NOT end bibliography entries with a full stop.
  - For online sources, present URLs as `<link>` in bibliography entries (angle brackets, no trailing full stop); if absent in user OSCOLA entries, add/normalise during amendment.
  - If a **Table of Cases** is requested, keep the same ordering discipline but, under OSCOLA, leave case names in roman by default unless the user expressly asks for italic table formatting. EU cases should be listed alphabetically by first party name with the case number in brackets after the case name; if the table is divided by jurisdiction, ECJ/CJEU, GC/CFI, and Commission decisions may be listed separately in chronological and numerical order, omitting the word `Case`.
- Correct formatting per source type (book, journal, case, legislation, treaty, online source, etc.).
- No duplicate entries.
- Consistent punctuation and formatting across all entries, including typographic curly quotes/apostrophes where applicable.
- If any fake/replaced footnotes were corrected in 3B, update the bibliography to reflect the real replacement sources.

### 3D — Bibliography generation/writing (on request)
- If the user requests to write/create bibliography/reference entries, generate them in the active citation style (default OSCOLA).
- If bibliography/reference already exists and the user requests bibliography/reference work, keep the existing list as the base and:
  1. verify/amend incorrect entries,
  2. add missing cited sources,
  3. keep already-correct entries unchanged.
- If the essay has **no bibliography / reference list** and the user requests one (or if the essay is academic and a bibliography is expected):
  1. Compile every unique source cited across all footnotes.
  2. Generate a complete bibliography in the active citation style (default OSCOLA).
  3. If OSCOLA is active, organise into OSCOLA sections: **Primary Sources** (Cases, Legislation, Treaties) and **Secondary Sources** (Books, Chapters, Journal Articles, Online Sources, etc.).
  4. Sort alphabetically within each section.
  5. Append the bibliography at the end of the essay.
  6. Log in the changelog: `Bibliography generated from X footnote sources.`

### 3E — Cross-referencing
- Verify internal cross-references ("as discussed in Part II above" — does Part II actually discuss that?).
- Check that any "see above" / "see below" / "supra" / "infra" references are accurate.

**Output:** Revised text with footnotes and bibliography corrected in the active citation style (default OSCOLA). Changelog listing every citation fix. A separate "Verification flags" list for any claims or citations that could not be fully verified (with suggestions).

### 3F — Verification gate before amendment delivery
- Build a verification ledger for all substantive claims and footnotes with statuses: `Verified`, `Corrected+Verified`, or `Unverified`.
- When bibliography/reference sections are present, extend the ledger with `Bibliography Unverified` (or `Reference Unverified`) and one line per entry (`Bibliography Entry N:` / `Reference Entry N:`), covering all entries.
- For comment-based requests ("based on comments"), extend the ledger with:
  1. `Comments Unresolved: 0`
  2. one line per DOCX comment: `DOCX Comment N: Resolved ...`
  3. one line per inline written comment: `Inline Comment N: Resolved ...`
- For standard review output, report all `Unverified` items clearly in Verification flags.
- If the user requests implemented amendments/refined DOCX, resolve all `Unverified` items first by:
  1. replacing with verified sources, or
  2. rewriting/removing unsupported claims.
- Do not deliver amended final DOCX while any `Unverified` item remains.
- This zero-`Unverified` gate applies to both `review + amend` and `amend`.

---

## Pass 4 — Final Holistic Check

**Agent: Final Holistic sub-agent**

This is the quality-assurance pass. Read the entire essay as a unified piece and check:

1. **Read-through:** Read the full essay start to finish. Does it flow naturally? Does it read as a polished, professional piece?
2. **Argument strength:** Is the argument convincing? Are there any logical gaps, unsupported claims, or weak links in reasoning?
3. **Consistency:** Terminology, spelling conventions (British/American), formatting, heading styles, numbering — all consistent throughout.
4. **Tone:** Appropriate academic register throughout. No informal language, contractions (unless stylistically intentional), or colloquialisms.
5. **Formatting:**
   - Heading hierarchy is consistent and logical.
   - Quotations are correctly formatted (short quotes inline, long quotes block-indented, per style guide).
   - Lists and enumerations are formatted consistently.
6. **Word count check:** Confirm the final word count stays near the user-requested target or within the user-specified limit. If no target/limit is provided, confirm original parity (±2%).
7. **10/10 standard test:** Would this essay receive top marks from a demanding marker? If not, identify precisely what prevents this and make targeted improvements.
8. **Final proofread:** One last character-by-character scan for any remaining typos, spacing issues, or formatting glitches.

**Output:** The final, polished essay — ready for submission.

---

## Pass 5 (Optional) — Implement Improvements Into Refined DOCX

**Agent: Main agent (orchestrator), only when user explicitly requests implementation**

This pass runs **after** the review is complete and only if the user asks in terminal to apply the improvements (for example: "implement improvements", "apply changes", "generate final refined docx").

**Implementation tip (local):** If you already have an "amended" DOCX whose wording is correct but whose formatting is broken, prefer copying only the text changes back into the original using `legal_doc_tools/refine_docx_from_amended.py` (preserves fonts/spacing/footnotes and marks changes with yellow highlight).

1. Use the fully reviewed result (all accepted changes from Passes 1-4) as the source of truth.
2. Create the refined output as a copy of the original DOCX and edit only the required wording runs; do not rebuild/reflow the document from plain text.
   - Do not edit the user’s original file in place at any stage.
   - Keep the original file unchanged and produce a separate amended file path.
3. Preserve all original formatting exactly:
   - Keep the same font family, font size, style hierarchy, paragraph formatting, and page/layout settings everywhere.
   - For each amended run, keep all pre-existing run attributes and add **yellow highlight** only to the changed wording.
   - For newly inserted wording or lines, clone local run/paragraph properties from adjacent unchanged content in the same section (do not fall back to document defaults).
   - Preserve mixed inline styling patterns where present (for example, italicised titles inside bibliography entries); do not flatten an inserted entry into one uniform run style.
   - For bibliography amendments specifically, ensure inserted/replaced entries inherit the same paragraph spacing and line spacing as neighboring bibliography entries.
   - Do not perform any document-wide style replacement or formatting cleanup.
4. Apply all refinements to the document text, footnotes, and bibliography, including correcting wrong/stale `(n X)` cross-reference numbers to the current accurate note number while preserving live Word footnote markers.
5. Mark every refinement in **yellow highlight**:
   - Highlight only changed/added wording where possible.
   - Do not bold or highlight unchanged text.
   - Do not remove or alter existing formatting on unchanged text.
   - Do not add any formatting other than yellow highlight to changed wording.
6. Keep word count compliance: stay near the user-requested target or within the user-specified word limit for the whole essay; if neither is provided, remain within ±2% of original.
7. Output location and naming:
   - Save every final artifact directly in `/Users/hltsang/Desktop` (Desktop root only).
   - Do not write final artifacts to `/Users/hltsang/Desktop/Skills` or any Desktop subfolder.
   - Use the canonical final filename per source (recommended suffix: `_amended_marked_final.docx`) when available. If an earlier final output already exists, allocate the next versioned Desktop path (`_v2`, `_v3`, and so on) instead of overwriting it.
8. Save as a new file and never overwrite the original source DOCX.
9. Before delivery, confirm there are zero unresolved verification items (all claims/citations verified or corrected).
10. Return the final file path/name in terminal and confirm that refinements are **yellow-highlighted** and the original font styling is preserved.
11. Run a final formatting integrity check: confirm that no style/layout change occurred outside amended runs.
12. Run an amended-line style parity check before delivery: for each amended paragraph/run, verify parity with neighboring unchanged content for font family, font size, paragraph style, line spacing, and space before/after. If mismatch exists, fix before output.
13. Run a final path/output integrity check: verify the delivered file exists at the exact target path and is a real `.docx` document (not only a temporary lock file like `~$...docx`).

**Output by mode:**
1. `review + amend`: amended DOCX (marked) + review report DOCX.
2. `amend`: amended DOCX (marked) only.
3. In `amend`, a review report DOCX is optional only when explicitly requested.

---

## Output Format

### Review

- Return the absolute path of the review report DOCX only.
- Report must include content-improvement comments/roadmap.
- For comment-based requests, report must include a comment-resolution matrix and a separate "Additional improvements beyond comments" section.

### Review + Amend

- Return:
  - the absolute path of the review report DOCX, and
  - the absolute path of the single final amended marked DOCX.
- Do not return internal/intermediate markdown artifact paths (for example `*_verification_ledger.md`) unless explicitly requested.
- Confirm amended wording is yellow highlight.
- Confirm live footnote numbering is preserved and any wrong/stale `(n X)` cross-references were corrected to the latest accurate note number.
- For comment-based requests, confirm all DOCX comments and inline written comments are resolved, then list additional non-comment improvements applied.

### Amend

- Return only:
  - the absolute path of the single final amended marked DOCX, and
  - a short confirmation that amended wording is yellow highlight.
- Do not output multiple amended DOCX artifacts for the same run.

### Report delivery in amend mode (only when explicitly requested)

- Deliver a review report as a `.docx` file and return its absolute path.
- Keep report content concise and focused on key corrections and verification notes.

### Delivery Gate

Before final response, confirm required artifacts exist on disk:
- `review`: review report DOCX exists.
- `review + amend`: review report DOCX and amended DOCX both exist.
- `amend`: one amended marked DOCX exists at the final Desktop path.
- Run `python3 legal_doc_tools/validate_delivery_gates.py ...` for the active mode and require `PASS` (exit code `0`) before delivery.
- In amend modes, the gate invocation must include `--verification-ledger` and pass ledger coverage checks.
- If the user requested "based on comments", run the gate with `--based-on-comments` and include `--verification-ledger` even in `review` mode.

If any required file is missing, generate it first and only then return completion.

---

## Special Instructions

- **If the user provides the essay question:** Use it as the primary benchmark for structural and content evaluation. State at the top of your review what question is being answered.
- **If no essay question is provided:** Infer the topic and thesis from the essay itself, and evaluate structure and content against that inferred thesis. State your inference and ask the user to confirm.
- **Terminal prompt scope is authoritative.** Apply amendments according to the latest terminal prompt instructions first (including include/exclude directives and word-count constraints).
- **Comment-based request trigger.** If user wording includes "based on comments" (or equivalent) for `review` or `amend`, enforce comment-first processing from both Word comment-function comments and inline written comments, then complete an additional beyond-comments excellence pass.
- **If bibliography/abbreviations are supplied but marked as excluded:** do not amend those excluded sections, but still check and report accuracy, coherence, structure relevance, and citation integrity issues found there.
- **Citation style:** follow the user-requested style; if no style is requested, default to OSCOLA. If mixed styles are found, normalise to the active style.
- **Bibliography/reference writing on request:** if the user asks to write bibliography/references, provide them directly. In legal-doc mode with OSCOLA active, output OSCOLA bibliography format (which differs from OSCOLA footnote format).
- **Bibliography-only mode (when requested):** prioritise verification and error detection over rewriting. Amend only entries with identified issues (fake source, wrong metadata, wrong citation-style format).
- **Existing bibliography default remains active.** If bibliography already exists, default behaviour is still to verify/amend that existing bibliography rather than replacing it wholesale.
- **When OSCOLA is the active style:** do not place a full stop at the end of bibliography entries.
- **Quote style in bibliography edits:** prefer typographic curly quotes/apostrophes (`‘…’`, `’`) rather than straight quotes.
- **Jurisdiction awareness:** If the essay is legal in nature, detect the jurisdiction from context (cases cited, legislation referenced) and ensure authorities and legal terminology are jurisdiction-accurate while keeping the active citation style formatting (default OSCOLA).
- **No word count limit on the review process.** However many words the user wrote is how many words you review and output.
- **If the user requests a specific final word count or gives an essay word limit:** Keep the amended output near that target/limit (default tolerance about ±2% unless the user asks for stricter matching). If a maximum limit is given, do not exceed it.
- **If the user asks to amend/implement improvements:** treat this as a request for a top-mark (10/10), professionally excellent lawyer-standard refined version, subject to strict verification and the active citation-style gate above (default OSCOLA if not requested otherwise).
- **Desktop-root output is mandatory for amended DOCX.** Save amended outputs directly in `/Users/hltsang/Desktop` only (no subfolders, no workspace delivery).
- **General DOCX amendment rule:** inserted/amended text must visually match user local style in font and size; amendment markup must be additive only and must not alter local typography.
- **If the DOCX contains images, tables, or charts:** Note their presence and positions but focus review on text content. Flag if any caption or label contains errors.
