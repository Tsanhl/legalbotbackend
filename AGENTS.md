# Codex Project Instructions

This repository is backend-only. Do not look for or rebuild a frontend unless the user explicitly asks for one.

## Source Of Truth

Use these entrypoints as the canonical backend flows:

- `backend_answer_runtime.send_complete_answer_with_docs(...)`
  - Complete essay/problem/chat answers.
  - Uses indexed legal RAG plus the shared subject/code-guide prompt system.
  - Complete essay/problem answers must pass the strict backend supervisor/verification layer; do not expose a normal-answer bypass for these tasks.
  - Returns chat/API text by default; do not create a Desktop file unless the user asks for one.
- `backend_answer_runtime.send_complete_answer_with_output(...)`
  - Same answer-generation path as above, then renders `.md` or `.docx` if requested.
  - Do not create a separate generation path for document output.
- `legal_doc_tools.workflow.run_auto_legal_doc_amend_workflow(...)`
  - DOCX amend/rewrite workflow.
  - Uses the legal amend guide, document extraction, RAG/source controls, delivery gates, and the amend-specific supervisor retry when a generated JSON plan or delivery gate fails.
  - Output should be a Desktop DOCX artifact unless the user explicitly asks for a different destination.
- `backend_answer_runtime.send_sqe_question_set_with_docs(...)`
  - SQE1/SQE2 question generation.
- `backend_answer_runtime.send_sqe2_marking_with_docs(...)`
  - SQE2 written-answer marking.

## Default Legal Answer Policy

For legal answers and amendments, assume this order:

1. Use indexed RAG first.
2. Apply the code-guide/subject-guide instructions.
3. If indexed RAG is thin, outdated, or missing required authority, use online-search fallback when configured or allowed.
   Complete answers should be RAG + code guide + online search where needed, not stuck in RAG-only mode. "Online search" means broad discovery of all materially relevant current/updated sources for the prompt, plus validation against primary/official sources where available; it is not satisfied by a token search for one citation.
4. Keep final output grounded: no fake citations, no local source-path leakage, and no invented source claims.
5. Default citation style is inline OSCOLA unless the user requests another style.
6. In exam-style complete-answer mode, integrate authorities inline. Do not append "sources checked", bibliography, or research-source lists unless the user expressly asks for them.
7. Every complete-answer request is a top-band Codex supervisor workflow by default across every law subject. Treat it as xhigh-equivalent reasoning: benchmark decomposition, RAG/local source sweep, online current-source validation where needed, issue-source mapping, generation, strict supervisor check, and revision before output. Do not require the user to say "supervisor", "first class", or "think harder".

## Interactive Codex Supervisor Route

When working inside Codex Desktop, provider/API access or nested `codex exec` network access may be unavailable. That must not lower answer quality.

If a backend generation call returns an `[INTERACTIVE CODEX SUPERVISOR HANDOFF]` block, or fails because no provider/API/nested Codex route can complete, the interactive Codex agent must continue directly in chat using the same quality pipeline:

1. RAG/local folder reading: use the retrieved RAG context first, then read any user-named folders, syllabi, notes, cases, guides, or uploaded documents needed for the task.
2. Code guide/AGENTS rules: apply this project guide, matched subject guides, output shape, citation style, word limits, and explicit user requirements.
3. Online official-source verification: use direct Codex web/search tools for current-law and authority validation, plus discovery of materially relevant updated sources. Prefer official/primary sources, then authoritative journal/publisher metadata where scholarship matters. Do not send confidential full prompts or local materials to untrusted external search routes unless the user has explicitly approved that risk.
4. Generation: draft the requested answer, amendment, marking, question set, or other output only after RAG plus required verification are considered.
5. Strict supervisor checker: review exact statutory/procedural tests, current-law position, authority accuracy, issue coverage, counterarguments, assumptions or missing facts, remedy/practical outcome, citation placement, word count, and local-source leakage.
6. Retry/revise: if the supervisor check finds a material weakness, revise before final output.

For complete-answer requests, run this route at top-band/xhigh-equivalent depth for every law subject. Do not downgrade because backend API keys, nested Codex, or network-backed search are unavailable; use the interactive Codex agent's available RAG/local reading and direct web tools instead, and be explicit if a specific verification path was unavailable.

For DOCX amendment work, if the backend cannot produce the JSON amend plan because generation is unavailable, the interactive agent should use the same extraction, RAG/source, amendment, verification, and render/delivery-gate discipline directly rather than stopping at the backend failure. Do not claim the automated backend supervisor completed unless the backend route actually generated and passed.

## Output And Cleanup Policy

- Complete-answer, SQE question-set, SQE2 guide, and SQE2 marking output goes to chat/API by default.
- Do not save complete-answer or SQE output into the project unless the user explicitly asks for a `.md`, `.docx`, or other artifact.
- If a one-off helper script, prompt dump, answer sample, or QA output is needed, create it in `/private/tmp` and delete it before finishing unless the user asked to keep it.
- If a backend call accepts `cleanup_paths`, register temporary helper files/directories there so the runtime can remove them after successful delivery.
- The repository should not accumulate ad hoc files such as `backend_*_answers.md`, `one_off_*`, `task_specific_*`, prompt dumps, or answer scratch files.

## Codex Runtime Distinction

When the user works inside Codex Desktop, there are two different Codex roles:

- Interactive Codex agent: the current coding assistant editing and testing this repository.
- Backend local Codex adapter: the backend spawning a nested `codex exec` generation process when no provider API key is configured, or when `LEGAL_AI_FORCE_CODEX_LOCAL_ADAPTER=1` is set.

The nested local adapter can be slower because it loads RAG, composes the full guide prompt, and starts a separate model subprocess. It cannot bypass a network-blocked Codex Desktop sandbox. This env var only acknowledges the trusted-testing risk; it does not create network access:

```bash
LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED=1
```

Use that only for trusted local testing. If `CODEX_SANDBOX_NETWORK_DISABLED=1` is present, the backend now prepares an interactive Codex supervisor handoff by default instead of wasting time on an impossible nested generation call. Set `LEGAL_AI_ENABLE_INTERACTIVE_CODEX_HANDOFF=0` only when you deliberately want backend-only fail-fast behaviour. Oversized nested prompts are compacted before execution. The nested adapter uses quality-first `xhigh` reasoning by default; set `LEGAL_AI_CODEX_REASONING_EFFORT=low` only for quick smoke tests. Set `LEGAL_AI_FORCE_CODEX_LOCAL_ADAPTER=1` for a no-API local setup that must ignore provider keys. The reliable choices remain: run the backend outside the Codex sandbox, configure a provider API key, or use the current interactive Codex chat with the same indexed RAG/code-guide policy. The default nested-adapter timeout is 360 seconds; set `LEGAL_AI_CODEX_TIMEOUT_SEC` higher only for deliberately long live backend QA.

## Quality Rules

When tuning the backend, preserve these answer-shape guarantees:

- Essay: thesis first, issue-led Parts, critical tension, authority after relevant propositions, final synthesis.
- Problem question: issue route, exact gateway/test, application to facts, counterargument, likelihood ranking, remedy/next step, final practical outcome.
- SQE2 practice: candidate-facing task first; do not reveal answers unless the user asks for marking/correction.
- SQE2 marking: criteria, score/band, issue-by-issue feedback, corrected answer, next practice.
- Law and Medicine: respect course-bound vs no-syllabus-limit mode.
- Before output, run a specialist accuracy pass: exact statutory test, current-law update, correct doctrine separation, strongest/weakest arguments, remedy, and no overstated authority.

Before treating live output as passing, check that it has a real final conclusion/outcome and does not only append `(End of Answer)` to a truncated analysis.
