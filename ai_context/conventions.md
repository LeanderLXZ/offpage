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
- Length gates (hard): declared in JSON schema only (`schemas/**.schema.json`) — no parallel tunables in `config.toml`. Spot examples: `stage_events` items 50–80 chars, `memory_timeline.event_description` 150–200, `memory_timeline.digest_summary` 30–50, `memory_timeline.subjective_experience` 100–200, `memory_timeline.time / location` ≤ 15 (mirrored by `memory_digest.time / location` and `world_event_digest.time / location`, all required), `relationship_history_summary` ≤ 300, `knowledge_scope` items ≤ 50, character baseline string fields (`identity` / `voice_rules` / `behavior_rules` / `boundaries` / `failure_modes`) typically 50 / 100 / 200; `voice_rules.signature_phrases` items ≤ 10 chars, `voice_rules.typical_expressions` items ≤ 15 chars (tighter because they are verbatim phrases). `foundation` caps: `tone` ≤ 100, `world_structure.summary` / `power_system.summary` ≤ 200, sub-item `description` / `impact` / `core_conflict` / `setting_features` ≤ 50. `fixed_relationships.description` ≤ 100.
- Count caps (hard): schema `maxItems`. Spot examples: `knowledge_scope.knows` ≤ 50, `does_not_know` ≤ 30, `uncertain` ≤ 30, `memory_timeline.knowledge_gained` ≤ 10 (item ≤ 50 chars), `memory_timeline.misunderstanding / concealment` ≤ 5 each, `behavior_rules.core_goals / obsessions` ≤ 10, `behavior_rules.emotional_reaction_map` ≤ 15, `identity.core_wounds` ≤ 15, `identity.key_relationships` ≤ 10, `identity.distinguishing_features` ≤ 20, `voice_rules.emotional_voice_map` ≤ 15, `voice_rules.target_voice_map` ≤ 10, `voice_rules.signature_phrases` ≤ 30, `boundaries.*` ≤ 15, `failure_modes.*` ≤ 10–15. `foundation` counts: `major_regions` / `core_rules` / `world_lines` / `major_factions` ≤ 20, `power_system.levels` ≤ 15, `major_factions[].key_figures` ≤ 10. Over-limit → trim least relevant.
- Baseline `evidence_refs` / `source_type` removed across: `identity` / `voice_rules` / `behavior_rules` / `boundaries` / `failure_modes` / `memory_timeline_entry` / `fixed_relationships`. Chapter anchors live only on `stage_snapshot` (`evidence_refs`) and `world_stage_snapshot` (`evidence_refs`); `memory_timeline` no longer carries `scene_refs` (scene back-pointers, if needed, resolve via FTS5 on `scene_archive`).
- `stage_catalog` schema position: world at `schemas/world/world_stage_catalog.schema.json`, character at `schemas/character/stage_catalog.schema.json`. Entries carry `stage_id` / `stage_title` / `summary` / `snapshot_path` (+ optional `timeline_anchor` / `chapter_scope`) only; no `order` field — `stage_id` (`S###`, zero-padded) is lexicographic and the sole sort key. Catalog files are bootstrap-only; not runtime-loaded.

## Git

- Default branch = `master`. Stay on `master` unless actively running extraction.
- Code / schema / prompt / docs / `ai_context/` commits go to `master` first; extraction branch syncs via `git merge master`.
- Extraction branch carries stage outputs only. Squash-merge to `master` on completion.
- Enforcement: orchestrator `try/finally: checkout_master(...)` + `.claude/hooks/session_branch_check.sh`. Detail → `architecture.md` §Git Branch Model.
- Never commit: novels, databases, embeddings, caches, real user packages.
- Don't amend others' commits.
- `/go` git contract: when not already on master-clean, `/go` automatically opens `../<repo>-master` as a `git worktree`, does all edits + commit there, then `git worktree remove --force` after commit. Main checkout is never moved off its branch during Steps 1–8, so in-flight extraction / dirty work continues undisturbed. Step 9 fast-forwards master into each non-master branch and asks **exactly once at the very end** whether to `git checkout master` — no inline prompts between steps or between branches.

## Post-Change Checklist

1. All aligned files updated? (table above)
2. PRE log at `/go` Step 1, POST at Step 7 (same file)?
3. `ai_context/` updated only if durable?
4. Grepped for stale old references?
5. Python import smoke test if code / schema changed?
