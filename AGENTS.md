# Persona Engine — Agent Entry Point

This file is auto-loaded at session start. Keep it short — detailed context
lives in `ai_context/`, not here.

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

## Sync with CLAUDE.md

This file and `CLAUDE.md` are kept **identical** except for the title line
("Agent Entry Point" vs. "Claude Entry Point"). Any change to one MUST be
mirrored to the other in the same commit.
