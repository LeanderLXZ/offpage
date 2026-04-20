# Persona Engine — Claude Entry Point

This file is auto-loaded at session start. Keep it short — detailed context
lives in `ai_context/`, not here.

## Worker-Mode Short-Circuit

If your system prompt contains `[extraction_worker_mode]` or
`[simulation_runtime_mode]`, **stop reading this file**. Do not load
`ai_context/`. Do not self-check. Follow the user prompt verbatim — that
prompt is self-contained and the only source of truth for this invocation.

## Session Start: Read ai_context/ Once

At the beginning of **every new session**, read the entire `ai_context/`
folder in the order specified by `ai_context/instructions.md`:

1. `conventions.md`
2. `project_background.md`
3. `requirements.md`
4. `read_scope.md`
5. `current_status.md`
6. `architecture.md`
7. `decisions.md`
8. `next_steps.md`
9. `handoff.md`

After finishing, **stop and wait for the user's instruction.** Do not start
modifying code, schemas, prompts, or docs on your own initiative.

## What Not To Load By Default

- `prompts/` — only when the user asks or the task is prompt-related
- `sources/`, full `users/.../sessions/`, `works/.../analysis/evidence/`,
  `docs/logs/`, `docs/review_reports/` — only when the task explicitly
  requires them
- Databases, vector stores, indexes, large generated artifacts

See `ai_context/read_scope.md` for the full rule.

## Acting vs. Loading

Reading `ai_context/` is context loading, not a task brief. Only act on
explicit user requests. If something looks off while reading, note it and
wait — do not fix proactively.

## Dilution Self-Check

Long sessions cause silent forgetting. Before editing code, schema,
prompt, or docs — and after any task-type switch — pause and answer:

1. **Scope check**: Am I doing exactly what the user asked, or am I
   expanding into proactive refactor / "while I'm here" fixes? If
   expanding → stop and ask first.
2. **Right layer**: Does the file I'm about to edit sit in the right
   module / layer for this concern? If unsure → re-read
   `ai_context/architecture.md`.
3. **Alignment check**: Before closing a change set, consult the
   Cross-File Alignment table in `ai_context/conventions.md` — did I
   update every downstream file?

If any answer is "I don't remember" or "I'm guessing" → re-read the
relevant `ai_context/` file before proceeding.

## Sync with AGENTS.md

This file and `AGENTS.md` are kept **identical** except for the title line
("Claude Entry Point" vs. "Agent Entry Point"). Any change to one MUST be
mirrored to the other in the same commit.
