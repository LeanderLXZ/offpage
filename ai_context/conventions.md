# Operational Conventions — RE-READ WHEN IN DOUBT

This file lists operational rules that are easy to forget during long
sessions. **Re-read this file** before writing output files and after
completing any significant task.

## Logging

- **Every meaningful change** → write a log to `docs/logs/`.
- Filename format: `YYYY-MM-DD_HHMMSS_slug.md`
  - **HHMMSS is mandatory.** Get it with:
    `TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'`
  - Bad: `2026-04-08_foo.md` — Good: `2026-04-08_012400_foo.md`
- Content: what changed, which files, why.
- If you completed a task without writing a log → write it now before
  moving on.

## Cross-File Alignment

When you change a concept, update **all** files that reference it. The
alignment graph:

| Changed | Also update |
|---------|-------------|
| `schemas/**/*.schema.json` | `docs/architecture/schema_reference.md`, `schemas/README.md`, prompt templates, validator.py |
| `docs/requirements.md` | `ai_context/requirements.md`, `ai_context/decisions.md` |
| Loading strategy | `simulation/retrieval/load_strategy.md`, `simulation/flows/startup_load.md`, `simulation/retrieval/index_and_rag.md`, `docs/architecture/data_model.md`, `ai_context/architecture.md` |
| Extraction workflow | `docs/architecture/extraction_workflow.md`, `automation/prompt_templates/`, `automation/persona_extraction/`, `ai_context/architecture.md` |
| Runtime prompts | `simulation/prompt_templates/`, `simulation/` |
| Any durable decision | `ai_context/decisions.md` |

After changes, grep for the old phrasing to catch stale references.

## Naming and Identifiers

- Chinese works → Chinese `work_id`, `character_id`, `stage_id`, path
  segments.
- `ai_context/` remains English.
- JSON field names may be English; content text follows work language.

## Generic Placeholders in Canonical Docs

`schemas/`, `docs/requirements.md`, `docs/architecture/`, `ai_context/`,
`prompts/`, and `automation/prompt_templates/` describe the current
design and are read by LLMs at extraction time. They must stay
work-agnostic:

- No real book titles, character names, place names, plot details.
- Schema `description` examples stay structural ("例如：某关键他人做出
  自我牺牲行为"), not narrative; or omit the example entirely.
- Field identifiers in examples use placeholders like
  `<character_id>` / `<stage_id>` / `阶段XX_<slug>`.
- Do not narrate history ("旧 / legacy / 已废弃 / 原为 / 已移除 /
  renamed from"). History lives in `docs/logs/` + git.

Exempt (history is the point): `docs/logs/`, `docs/review_reports/`,
`works/*/` sample outputs, git commit messages.

## Data Separation — Hard Rules

- User data under `users/` — never touch `works/` canon from user context.
- Baseline files = extraction anchors only, **not loaded at runtime**.
- Stage snapshots are **self-contained** — never merge with baseline at
  runtime.
- Length rules are hard schema gates: world + character `stage_events`
  50–80 字 per entry; memory_timeline `event_description` 150–200 字,
  `digest_summary` 30–50 字; `knowledge_scope` items ≤ 50 字 each;
  `relationships[*].relationship_history_summary` ≤ 300 字 (default; tunable
  via `[repair_agent].relationship_history_summary_max_chars`).
- Count caps (hard schema gates): `knowledge_scope.knows` ≤ 50,
  `does_not_know` ≤ 30, `uncertain` ≤ 30. Over-limit → trim by dropping
  items least relevant to current-stage decisions / core_wounds /
  active_obsessions / active relationships; prefer dropping daily
  commonsense, early details without triggers, items already in
  `memory_timeline`.

## Git

- Do not commit: novels, databases, embeddings, caches, user packages.
- Do not amend others' commits.
- **Default branch is `master`.** Always stay on `master` unless actively
  running extraction. Checkout extraction branch only when starting or
  resuming `python -m automation.persona_extraction`. When extraction
  pauses or finishes, checkout back to `master` immediately.
- **Code changes go to `master` first.** All modifications to code,
  schemas, prompts, docs, and `ai_context/` must be committed on
  `master`, then merged into the extraction branch (`git merge master`
  from the extraction branch). Never develop directly on the extraction
  branch.
- Extraction branch is for extraction data commits only (stage outputs).
  Squash-merge to `master` when all stages complete.

## Post-Change Checklist

After completing a task, run through:

1. Did I update all aligned files? (See table above)
2. Did I write a log with HHMMSS timestamp?
3. Did I update `ai_context/` if the change is durable?
4. Did I grep for stale references to the old state?
5. Did I run the relevant Python imports to verify no breakage?
