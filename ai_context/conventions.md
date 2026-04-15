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
| `schemas/*.schema.json` | `docs/architecture/schema_reference.md`, prompt templates, validator.py |
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

## Data Separation — Hard Rules

- User data under `users/` — never touch `works/` canon from user context.
- Baseline files = extraction anchors only, **not loaded at runtime**.
- Stage snapshots are **self-contained** — never merge with baseline at
  runtime.
- Length rules are hard schema gates: world + character `stage_events`
  50–80 字 per entry; memory_timeline `event_description` 150–200 字,
  `digest_summary` 30–50 字; `knowledge_scope` items ≤ 50 字 each.
- Count caps (hard schema gates): `knowledge_scope.knows` ≤ 50,
  `does_not_know` ≤ 30, `uncertain` ≤ 30. Over-limit → trim by dropping
  items least relevant to current-stage decisions / core_wounds /
  active_obsessions / active relationships; prefer dropping daily
  commonsense, early details without triggers, items already in
  `memory_timeline`.

## Git

- Do not commit: novels, databases, embeddings, caches, user packages.
- Extraction runs on a dedicated branch; squash-merge to main when done.
- Do not amend others' commits.

## Post-Change Checklist

After completing a task, run through:

1. Did I update all aligned files? (See table above)
2. Did I write a log with HHMMSS timestamp?
3. Did I update `ai_context/` if the change is durable?
4. Did I grep for stale references to the old state?
5. Did I run the relevant Python imports to verify no breakage?
