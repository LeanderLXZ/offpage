<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `Character A`, `S001`).
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
| Project-specific anchors used by skills (background processes, protected branch prefix, main-branch policy, do-not-commit paths, source / example-artifact directories, core-component keywords, sensitive-content rules, timezone) | `ai_context/skills_config.md` corresponding section |

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
- `identity.json` + `target_baseline.json` are the character-level constant baselines (Phase 2 produced, immutable from Phase 3 onward); voice / behavior / boundary / failure_modes live inline in `stage_snapshot` and evolve per stage. Phase 3 stage_snapshot three structures (`voice_state.target_voice_map` / `behavior_state.target_behavior_map` / top-level `relationships`) MUST have keys **set-equal** to `target_baseline.targets[].target_character_id` (bidirectional cross-file hard fail; tri-state via content emptiness — appeared = filled, seen-before = inherited, never-appeared = empty entry; fixed_relationship exception may pre-fill the relationships entry's relationship fields when bound by `world/foundation/fixed_relationships.json`). Validation runs at the phase 3 single-stage validate layer (peer of schema validate), violations route through the file-level repair lifecycle (L1/L2/L3); fix the baseline by hand and re-run the affected stages when phase 2 misses a target.
- Stage snapshots are **self-contained** — runtime loads identity + current stage_snapshot; no baseline merge.
- **Bounds only in schema.** All `maxLength` / `minLength` / `maxItems` / `required` live in `schemas/**.schema.json`; no duplicates anywhere else. Exact values → schema file. Index → `docs/architecture/schema_reference.md`. Cross-schema sharing of a single bound is done via `$ref` to a shared fragment located near the schemas it serves — placed in the directory of the domain that uses it (e.g. target-array cap is shared by `target_baseline.targets` + stage_snapshot's three target structures, both in `schemas/character/`, so the fragment lives there as `schemas/character/targets_cap.schema.json`). Still single-source, no duplication.
- **Bounds are caps, not targets.** Every extraction prompt template must explicitly tell the LLM that `maxLength` / `maxItems` are **hard ceilings, not quotas** — write what's actually in the source, do not pad / inflate / invent items to fill the cap. Without this, models default to writing exactly N items per array because "the schema says ≤N".
- **maxItems-aware truncation.** When a field exceeds its `maxItems` cap, the LLM ranks + truncates during extraction (not afterwards via schema fail). Priority anchors: current-stage relevance → identity-anchor relation → coverage breadth → cross-stage stability (for full-state evolving fields like `failure_modes`). Sub-classes count maxItems independently. → `automation/prompt_templates/character_snapshot_extraction.md` §maxItems 触顶时的裁剪规则.
- **No chapter anchors on snapshots.** No schema (world / character / `stage_snapshot` / `memory_timeline`) carries `evidence_refs` / `source_type` / `scene_refs`; no per-item `evidence_ref` in `dialogue_examples` / `action_examples`. Anchoring uses `timeline_anchor` (+ `location_anchor` for world) and `memory_timeline`.
- **`stage_catalog`** at `schemas/{world,character}/stage_catalog.schema.json`; bootstrap-only, not runtime-loaded; sort by `stage_id` lex (no `order` field).

## Git

Three-branch model (main is the only branch ever pushed to remote):

| Branch | Role | Pushes to remote? |
|---|---|---|
| `main` | Framework only — code / schema / prompt / docs / `ai_context/` / skills. Never carries real work IDs, source novels, or extraction artefacts. | ✅ |
| `extraction/{work_id}` | Per-work in-progress extraction. Each passing stage committed. | ❌ local only |
| `library` | Archive of completed works. Each finished `extraction/{work_id}` squash-merges here. | ❌ local only |

Flow rules:

- Default branch = `main`. Stay on `main` unless actively running extraction.
- Code / schema / prompt / docs / `ai_context/` / skill commits go to `main` first; extraction and library branches sync via `git merge main`.
- `extraction/{work_id}` carries stage outputs only. **Squash-merge to `library` on completion** (never to main — main must stay artefact-free).
- **After a successful squash-merge the orchestrator interactively offers (`[y/N]`, default N) to delete the source `extraction/{work_id}` branch (`git branch -D`) and run `git gc --prune=now`** so accumulated regen commits become unreachable and are reclaimed. Branch deletion is destructive — the prompt always runs even when `[git].auto_squash_merge=true`. Once the user opts in, the `library` squash is the only retained record; `extraction/{work_id}` is a disposable scratchpad.
- `library` periodically `git merge main` to absorb framework updates; never flows back to main.
- Enforcement: orchestrator `try/finally: checkout_main(...)` + `.claude/hooks/session_branch_check.sh`. Detail → `architecture.md` §Git Branch Model.
- Never commit: novels, databases, embeddings, caches, real user packages, real `work_id`-named manifests on `main`.
- Don't amend others' commits.
- `/go` git contract: when not already on main-clean, `/go` automatically opens `../<repo>-main` as a `git worktree`, does all edits + commit there, then `git worktree remove --force` after commit. Main checkout is never moved off its branch during Steps 1–8, so in-flight extraction / dirty work continues undisturbed. Step 9 fast-forwards main into each non-main branch and asks **exactly once at the very end** whether to `git checkout main` — no inline prompts between steps or between branches.

## Post-Change Checklist

1. All aligned files updated? (table above)
2. PRE log at `/go` Step 1, POST at Step 7 (same file)?
3. `ai_context/` updated only if durable?
4. Grepped for stale old references?
5. Python import smoke test if code / schema changed?
