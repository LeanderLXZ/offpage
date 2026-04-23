<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `角色A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# Operational Conventions

Rules easy to forget during long sessions. Dilution self-check triggers
live in `CLAUDE.md` / `AGENTS.md`.

## Logging

`docs/logs/` uses a three-timepoint contract (PRE / POST / REVIEW) — one
log file spans one `/go` → `/after-check` lifecycle. Filename:
`YYYY-MM-DD_HHMMSS_slug.md` (HHMMSS mandatory —
`TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'`).

- **PRE** (`/go` Step 1) — context / decision / planned action list / verification criteria
- **POST** (`/go` Step 7) — landed changes / diff vs plan / verification results / DONE|BLOCKED
- **REVIEW** (`/after-check` Step 5) — two-track review summary + REVIEWED-PASS|PARTIAL|FAIL

Rules:

- No PRE log → `/go` must not modify files.
- `/after-check` is the only skill allowed to write back to logs.
- Pre-contract single-timepoint logs stay as-is.

Full text → `.claude/commands/go.md`, `.claude/commands/after-check.md`.

## Cross-File Alignment

When a concept changes, update every file in its row:

| Changed | Also update |
|---------|-------------|
| `schemas/**/*.schema.json` | `docs/architecture/schema_reference.md`, `schemas/README.md`, prompt templates, `automation/persona_extraction/validator.py` |
| `docs/requirements.md` | `ai_context/requirements.md`, `ai_context/decisions.md` |
| Loading strategy | `simulation/retrieval/load_strategy.md`, `simulation/flows/startup_load.md`, `simulation/retrieval/index_and_rag.md`, `docs/architecture/data_model.md`, `ai_context/architecture.md` |
| Extraction workflow | `docs/architecture/extraction_workflow.md`, `automation/prompt_templates/`, `automation/persona_extraction/`, `ai_context/architecture.md` |
| Runtime prompts | `simulation/prompt_templates/`, `simulation/` |
| Any durable decision | `ai_context/decisions.md` |
| `/go` or `/after-check` run | `docs/logs/` PRE / POST / REVIEW segments all present |

After any change, grep for the old phrasing to catch stale references.

## Naming and Identifiers

- Chinese works → Chinese `work_id`, `character_id`, path segments.
- `stage_id` = `S###` (3-digit zero-pad), aligned with the
  `M-S###-##` / `E-S###-##` / `SC-S###-##` / `SN-S###-##` ID family.
- `stage_title` = human-readable short name (≤15 chars, work language);
  sibling of `stage_id` in `stage_plan.json` and every
  `stage_catalog.json` entry; label shown at bootstrap stage selection.
- `ai_context/` stays English. JSON field names may be English;
  content text follows work language.

## Generic Placeholders

Canonical docs (`schemas/`, `docs/requirements.md`, `docs/architecture/`,
`ai_context/`, `prompts/`, `automation/prompt_templates/`) stay
work-agnostic:

- No real book / character / place / plot names.
- Examples use structural placeholders (`<character_id>`, `S001`).
- Schema `description` examples stay structural, not narrative (or omitted).
- No history narration ("legacy", "deprecated", "formerly", "renamed from").

Exempt (history is the point): `docs/logs/`, `docs/review_reports/`,
`works/*/` sample outputs, git commit messages.

## Data Separation — Hard Schema Gates

- User data under `users/`; never write canon from user context.
- Baseline files = extraction anchors only — not runtime-loaded.
- Stage snapshots are **self-contained** — never merged with baseline at runtime.
- Length gates (hard):
  - World + character `stage_events` — 50–80 CJK chars per entry
  - `memory_timeline.event_description` — 150–200 CJK chars
  - `memory_timeline.digest_summary` — 30–50 CJK chars
  - `knowledge_scope` items — ≤ 50 CJK chars each
  - `relationships[*].relationship_history_summary` — ≤ 300 CJK chars (tunable via `[repair_agent].relationship_history_summary_max_chars`)
- Count caps (hard): `knowledge_scope.knows` ≤ 50, `does_not_know` ≤ 30, `uncertain` ≤ 30. Over-limit → trim least relevant (drop commonsense / early untriggered / items already in `memory_timeline`).

## Git

- Default branch = `master`. Stay on `master` unless actively running extraction.
- Code / schema / prompt / docs / `ai_context/` commits go to `master` first; extraction branch syncs via `git merge master`.
- Extraction branch carries stage outputs only. Squash-merge to `master` on completion.
- Enforcement: orchestrator `try/finally: checkout_master(...)` + `.claude/hooks/session_branch_check.sh`. Detail → `architecture.md` §Git Branch Model.
- Never commit: novels, databases, embeddings, caches, real user packages.
- Don't amend others' commits.

## Post-Change Checklist

1. All aligned files updated? (table above)
2. PRE log at `/go` Step 1, POST at Step 7 (same file)?
3. `ai_context/` updated only if durable?
4. Grepped for stale old references?
5. Python import smoke test if code / schema changed?
