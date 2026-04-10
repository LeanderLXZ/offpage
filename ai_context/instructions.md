# Instructions For Future AI Agents

## Primary Rule

Use `ai_context/` as the default handoff entry point. Do not begin by
rereading full chat history, the full novel corpus, or large artifact
directories. Do not proactively load `prompts/` content unless the user
explicitly asks for a prompt-driven workflow.

## Default Reading Order

1. `ai_context/conventions.md` ← short, re-read periodically during session
2. `ai_context/project_background.md`
3. `ai_context/requirements.md`
4. `ai_context/read_scope.md`
5. `ai_context/current_status.md`
6. `ai_context/architecture.md`
7. `ai_context/decisions.md`
8. `ai_context/next_steps.md`
9. `ai_context/handoff.md`

## Update Expectations

After a meaningful project change, update `ai_context/` deliberately.

**Do not update `ai_context/` or `docs/logs/` for routine runtime-state or
extraction-progress updates.** Those should go into work-local or user-local
progress files. Only promote into `ai_context/` or `docs/logs/` when the
change affects durable repository truth (instructions, prompts, schemas,
architecture, directory rules, data-model conventions, retrieval strategy).

When a durable change occurs, update the relevant subset of:

- `current_status.md`
- `handoff.md`
- `next_steps.md`
- `architecture.md` (if architecture changed)
- `decisions.md` (if a durable decision was added or reversed)
- one timestamped entry under `docs/logs/` (for major changes)

## Dilution Protection

Long sessions cause you to forget what you read earlier. These rules help:

1. **Before writing to `works/` or `users/`** — re-read `decisions.md`
   (data separation, Chinese identifiers, canon vs inference).
2. **Before modifying schemas or architecture** — re-read `architecture.md`
   (self-contained snapshots, baseline role, key boundaries).
3. **When switching task types** — re-read the relevant `ai_context/` file.
4. **If you cannot recall** `work_id`, `character_id`, `stage_id`, or what
   was decided earlier in this conversation — stop and re-read, do not guess.
5. **After completing any task** — re-read `conventions.md` and run through
   its Post-Change Checklist. Check whether you also missed logging a
   previous task in this session.
6. **Every 3-4 tasks in a long session** — re-read `conventions.md` in full.
   This file is short and designed for periodic refreshing. Pay special
   attention to the cross-file alignment table and the log timestamp format.
7. **Before creating any file in `docs/logs/`** — run
   `TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'` to get the exact
   timestamp. Do not guess or approximate the time.

## Logging Rules — CRITICAL

**Every meaningful change must produce a log entry under `docs/logs/`.** This
is not optional. If you changed schemas, architecture, prompts, simulation
docs, directory structure, or made any decision that a future AI session would
need to understand, you must write a timestamped log before moving on. The log
is the only durable record that survives across conversations.

Checklist — after completing a task, ask yourself:

1. Did I change any file outside of `ai_context/`? → Write a log.
2. Did I add, remove, or rename a schema, template, or directory? → Write a
   log.
3. Did I make a design decision or reverse a prior one? → Write a log.
4. Did I only update `ai_context/` text with no other file changes? → Log is
   optional.

Log format:

- Location: `docs/logs/{timestamp}_{slug}.md`
- Timestamp format: `YYYY-MM-DD_HHMMSS` — **HHMMSS is mandatory, never omit
  the time portion.** Bad: `2026-04-03_foo.md`. Good:
  `2026-04-03_020841_foo.md`. Always run the date command below to get the
  exact timestamp before creating the file.
- Timezone: `America/New_York` (use `TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'`)
- Content: what changed, which files, and why

Layer summary:

- `ai_context/` = compressed current truth (updated after durable changes)
- `docs/architecture/` = formal architecture documentation
- `docs/logs/` = timestamped historical change records (write-mostly; do not
  proactively read, but always write after changes)

## Git And Repository Size Rules

- Keep the repository lightweight
- Do not commit: full novels, databases, vector indexes, embeddings, caches,
  full user histories, large runtime artifacts
- Schemas, templates, code, docs, and config are fine to commit
- Real user packages under `users/` stay local
- `works/*/analysis/` and `works/*/indexes/` are git-tracked
- Only commit at coherent milestones

## Project-Specific Guidance

- The core is decision logic, memory logic, and relationship logic recovery —
  not surface tone mimicry
- Keep layers separate: objective plot, character definition, character memory,
  character misunderstandings, voice style, behavior rules, conflicts
- The original novel is the highest authority
- Distinguish explicit canon from reasonable inference
- Preserve stage differences
- The runtime should not degrade into one giant prompt — prefer retrieval and
  compilation
