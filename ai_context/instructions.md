# Instructions For Future AI Agents

## Entry Point

`ai_context/` is the handoff entry point. Do not reread full chat history,
the novel, or large artifact directories by default. Do not load `prompts/`
unless the user asks.

After finishing `ai_context/`, **stop and wait for the next instruction.**
Do not start modifying code, schemas, prompts, or docs on your own
initiative — even if you spot something that looks off. Reading
`ai_context/` is context loading, not a task brief. Only act when the user
gives an explicit request.

## Reading Order

1. `conventions.md` ← short, re-read periodically
2. `project_background.md`
3. `requirements.md`
4. `read_scope.md`
5. `current_status.md`
6. `architecture.md`
7. `decisions.md`
8. `next_steps.md`
9. `handoff.md`

## Dilution Protection

Long sessions cause forgetting. Re-read the relevant file when:

- Writing to `works/` or `users/` → `decisions.md` (data separation,
  Chinese identifiers, canon vs inference)
- Modifying schemas or architecture → `architecture.md`
- Switching task types → the relevant `ai_context/` file
- Forgetting `work_id` / `character_id` / `stage_id` / prior decisions →
  stop and re-read, do not guess
- Every 3–4 tasks in a long session → `conventions.md` in full
- Before creating any `docs/logs/` file → run
  `TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'` for the exact timestamp

## Update Expectations

Update `ai_context/` only for durable repository truth (instructions,
prompts, schemas, architecture, directory rules, data-model conventions,
retrieval strategy). Runtime / extraction progress goes in work-local or
user-local progress files.

For durable changes, update the relevant subset of: `current_status.md`,
`handoff.md`, `next_steps.md`, `architecture.md`, `decisions.md`, plus one
timestamped entry under `docs/logs/`.

## Logging (critical)

Every meaningful change outside `ai_context/` → write a log at
`docs/logs/{YYYY-MM-DD_HHMMSS}_{slug}.md`. HHMMSS is mandatory. See
`conventions.md` for the full checklist and alignment table.

Layer summary:
- `ai_context/` — compressed current truth
- `docs/architecture/` — formal architecture documentation
- `docs/logs/` — timestamped historical records (write-mostly)

## Project Focus

The core is decision logic, memory logic, and relationship logic — not
surface tone mimicry. Keep layers separate (objective plot, character
definition, memory, misunderstanding, voice, behavior, conflicts). The
original novel is the highest authority. Explicit canon vs inference.
Stage differences preserved. Runtime uses retrieval + compilation, not
one giant prompt.
