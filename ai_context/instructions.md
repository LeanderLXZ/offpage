<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `角色A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# Instructions For Future AI Agents

## Entry Point

`ai_context/` is the handoff entry. Don't re-read full chat history, the
novel, or large artifact directories by default. Don't load `prompts/`
unless the user asks.

After finishing `ai_context/`, **stop and wait** for the next
instruction. Reading `ai_context/` is context loading, not a task brief.
Only act on explicit user requests.

## Reading Order

1. `conventions.md`
2. `project_background.md`
3. `requirements.md`
4. `read_scope.md`
5. `current_status.md`
6. `architecture.md`
7. `decisions.md`
8. `next_steps.md`
9. `handoff.md`

Dilution self-check (when to re-read which file) lives in `CLAUDE.md` /
`AGENTS.md`.

## Update Expectations

Update `ai_context/` only for **durable repository truth** (instructions,
schemas, architecture, data-model conventions, retrieval strategy).
Runtime / extraction progress belongs in work-local or user-local
progress files, not here.

## Logging

Every change outside `ai_context/` → one log at
`docs/logs/YYYY-MM-DD_HHMMSS_slug.md` (HHMMSS mandatory), written across
three timepoints:

- **PRE** — `/go` Step 1, before any file change
- **POST** — `/go` Step 7, before commit
- **REVIEW** — `/post-check` Step 5

Full contract → `conventions.md` §Logging. `/go` + `/post-check` skills
own the format; do not duplicate it here.

## TODO List

`docs/todo_list.md` — Chinese working queue of planned-but-unfinished
tasks. Read-on-demand, **not** part of the session-start reading order.
Usage rules live inside the file's `## 文件说明` section.

## Project Focus

Decision logic, memory logic, and relationship logic — not surface tone.
Layered separation (objective plot / character canon / memory / voice /
behavior / user / runtime). Stage-aware. Canon vs inference labelled.
Original novel = highest authority. Runtime = retrieval + compilation,
not one giant prompt.
