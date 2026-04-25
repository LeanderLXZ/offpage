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

`logs/change_logs/` uses a three-timepoint contract (PRE / POST / REVIEW) — one
log file spans one `/go` → `/post-check` lifecycle. Filename:
`YYYY-MM-DD_HHMMSS_slug.md` (HHMMSS mandatory —
`TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'`).

- **PRE** (`/go` Step 1) — context / decision / planned action list / verification criteria
- **POST** (`/go` Step 7) — landed changes / diff vs plan / verification results / DONE|BLOCKED
- **REVIEW** (`/post-check` Step 5) — two-track review summary + REVIEWED-PASS|PARTIAL|FAIL

Rules:

- No PRE log → `/go` must not modify files.
- `/post-check` is the only skill allowed to write back to logs.
- Pre-contract single-timepoint logs stay as-is.

Full text → `.claude/commands/go.md`, `.claude/commands/post-check.md`.

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
| `/go` or `/post-check` run | `logs/change_logs/` PRE / POST / REVIEW segments all present |

After any change, grep for the old phrasing to catch stale references.

## Naming and Identifiers

- Chinese works → Chinese `work_id`, `character_id`, path segments.
- `stage_id` = `S###` (3-digit zero-pad), aligned with the
  `M-S###-##` / `E-S###-##` / `SC-S###-##` / `SN-S###-##` ID family.
- `stage_title` = human-readable short name (work language; length cap in schema);
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

Exempt (history is the point): `logs/change_logs/`, `logs/review_reports/`,
`works/*/` sample outputs, git commit messages.

## Data Separation — Hard Schema Gates

- User data under `users/`; never write canon from user context.
- Baseline files = extraction anchors only — not runtime-loaded.
- Stage snapshots are **self-contained** — never merged with baseline at runtime.
- **Bounds only in schema.** All `maxLength` / `minLength` / `maxItems` / `required` live in `schemas/**.schema.json`; no duplicates anywhere else. Exact values → schema file. Index → `docs/architecture/schema_reference.md`.
- **Bounds are caps, not targets.** Every extraction prompt template must explicitly tell the LLM that `maxLength` / `maxItems` are **hard ceilings, not quotas** — write what's actually in the source, do not pad / inflate / invent items to fill the cap. Without this, models default to writing exactly N items per array because "the schema says ≤N".
- **No chapter anchors on snapshots.** No schema (world / character baselines / `stage_snapshot` / `memory_timeline`) carries `evidence_refs` / `source_type` / `scene_refs`; no per-item `evidence_ref` in `dialogue_examples` / `action_examples`. Anchoring uses `timeline_anchor` (+ `location_anchor` for world) and `memory_timeline`.
- **Unified vocabulary**: `behavior_rules` uses `target_behavior_map` / `target_type` (same as stage `behavior_state`).
- **`stage_catalog`** at `schemas/{world,character}/stage_catalog.schema.json`; bootstrap-only, not runtime-loaded; sort by `stage_id` lex (no `order` field).

## Git

Three-branch model (master is the only branch ever pushed to remote):

| Branch | Role | Pushes to remote? |
|---|---|---|
| `master` | Framework only — code / schema / prompt / docs / `ai_context/` / skills. Never carries real work IDs, source novels, or extraction artefacts. | ✅ |
| `extraction/{work_id}` | Per-work in-progress extraction. Each passing stage committed. | ❌ local only |
| `library` | Archive of completed works. Each finished `extraction/{work_id}` squash-merges here. | ❌ local only |

Flow rules:

- Default branch = `master`. Stay on `master` unless actively running extraction.
- Code / schema / prompt / docs / `ai_context/` / skill commits go to `master` first; extraction and library branches sync via `git merge master`.
- `extraction/{work_id}` carries stage outputs only. **Squash-merge to `library` on completion** (never to master — master must stay artefact-free).
- `library` periodically `git merge master` to absorb framework updates; never flows back to master.
- Enforcement: orchestrator `try/finally: checkout_master(...)` + `.claude/hooks/session_branch_check.sh`. Detail → `architecture.md` §Git Branch Model.
- Never commit: novels, databases, embeddings, caches, real user packages, real `work_id`-named manifests on `master`.
- Don't amend others' commits.
- `/go` git contract: when not already on master-clean, `/go` automatically opens `../<repo>-master` as a `git worktree`, does all edits + commit there, then `git worktree remove --force` after commit. Main checkout is never moved off its branch during Steps 1–8, so in-flight extraction / dirty work continues undisturbed. Step 9 fast-forwards master into each non-master branch and asks **exactly once at the very end** whether to `git checkout master` — no inline prompts between steps or between branches.

## Post-Change Checklist

1. All aligned files updated? (table above)
2. PRE log at `/go` Step 1, POST at Step 7 (same file)?
3. `ai_context/` updated only if durable?
4. Grepped for stale old references?
5. Python import smoke test if code / schema changed?
