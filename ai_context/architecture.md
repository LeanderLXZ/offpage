<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `角色A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# Architecture Snapshot

Compressed summary. Authoritative sources:
`docs/architecture/system_overview.md`, `data_model.md`,
`schema_reference.md`, `extraction_workflow.md`,
`automation/README.md`, `automation/repair_agent/`.

## Top-Level Structure

- `sources/` — raw novel inputs + normalized source packages
- `works/` — source-grounded canonical packages (world / characters / analysis / indexes)
- `users/` — user-specific mutable state, grouped by `user_id`
- `simulation/` — runtime-engine lifecycle, retrieval, service contracts
- `prompts/` — manual-only (ingest / review / supplement / cold start)
- `schemas/` — persistence + runtime-request schemas
- `interfaces/` — future terminal adapters
- `automation/` — extraction orchestrator (Python)
- `docs/architecture/` — formal architecture docs (incl. schema reference)
- `ai_context/` — this compressed handoff

## System Layers

1. **Source** — raw text, normalized chapters, metadata
2. **Extraction** — `works/{work_id}/analysis/` (progress, evidence, conflicts)
3. **World** — `works/{work_id}/world/` (foundation, stages, events, locations, factions, cast)
4. **Character** — `works/{work_id}/characters/{character_id}/` (identity, memory, voice, behavior, boundaries, stage snapshots)
5. **User** — `users/{user_id}/` (locked binding, long-term profile, relationship core, contexts, sessions)
6. **Simulation Engine** — bootstrap, load, retrieval, writeback, close/merge
7. **Interface** — terminal adapters (future)

## Key Boundaries

- Work-scoped canon under `works/`; user-mutable under `users/`.
- User conversations never rewrite canonical world / character data.
- One `user_id` = one locked work-target-counterpart binding.
- Chinese works use Chinese identifiers and path segments.
- JSON field names may remain English; content text = work language.

## Runtime Load Formula

Startup order:

1. World foundation (`foundation.json` + `fixed_relationships.json`) + selected world-stage snapshot
2. Target character `identity.json` (incl. `core_wounds`, `key_relationships`) + `failure_modes.json` + self-contained stage snapshot
3. `memory_timeline` recent 2 stages full; `memory_digest.jsonl` + `world_event_digest.jsonl` stage 1..N filtered
4. `scene_archive` most recent `scene_fulltext_window` `full_text` scenes (default 10; summaries via FTS5 only)
5. Vocab dict → jieba
6. User role binding + long-term profile + relationship core
7. Current context manifest + `character_state.json` (relationship_delta + context_memories)
8. Recent session summaries

On-demand: events, locations, factions, history, full transcripts,
archive records, raw chapters, FTS5 / embedding retrieval.

Full tier model → `simulation/retrieval/load_strategy.md`.

## Stage Model

- stage (extraction) = stage (runtime), 1:1 on `stage_id`.
- `stage_catalog.json` = bootstrap selector (not runtime-loaded).
- `world_event_digest.jsonl` = startup-loaded, filtered 1..N.
- Stage N cumulative through 1..N; latest = active present.
- User picks stage at setup; applies to target + canon-backed user roles.

## Context Lifecycle

`ephemeral` → `persistent` → `merged`. Session state updates
continuously during live roleplay; `long_term_profile` +
`relationship_core` update only after explicit merge at close. Merge is
append-first (never destructive overwrite).

## Self-Contained Stage Snapshots

Each `stage_snapshots/{stage_id}.json` carries full character state
(voice_state, behavior_state with `core_goals` / `obsessions`,
boundary_state, relationships, personality, mood, knowledge,
`character_arc`). Runtime loads a single snapshot — no baseline merge.

- Baseline files (`voice_rules.json`, `behavior_rules.json`, `boundaries.json`) = extraction anchors only, not runtime-loaded.
- Only `identity.json`, `failure_modes.json`, `hard_boundaries` load alongside the stage snapshot.
- `target_voice_map` / `target_behavior_map` filtered by user role; fallback = backward scan through previous snapshots (pure code I/O).

Contract → `simulation/contracts/baseline_merge.md`.

## Three-Layer Memory

1. **stage_snapshot** — aggregated state per stage ("I trust him now"). Runtime loads current stage only.
2. **memory_timeline** — subjective process per event. `memory_id` (`M-S###-##`), required short `time` / `location` anchors, `event_description`, `digest_summary`, `subjective_experience` (exact bounds in `schemas/character/memory_timeline_entry.schema.json`). Recent 2 stages full at startup; distant via `memory_digest.jsonl` + FTS5 / embedding on demand.
3. **scene_archive** — original text split by scene. `scene_id` (`SC-S###-##`), `stage_id`, `chapter`, `time`, `location`, `characters_present`, `summary`, `full_text`. Work-level. Only most recent `scene_fulltext_window` `full_text` loaded; summaries via FTS5 only.

Inter-character relationship evolution: `relationships` per stage snapshot
records per-target attitude, trust, intimacy, guardedness, voice / behavior
shifts, driving events, perceived status, history 1..N.
`stage_delta.*_changes` carry attribution. Memory timeline split per-stage
at `canon/memory_timeline/{stage_id}.json`.

## Historical Recall and Cognitive Conflict

- Historical recall served by `memory_timeline` + `relationship_history_summary` at startup. Past snapshots on demand.
- Cognitive conflict handled by runtime prompt rules, not pre-written data.
- → `simulation/prompt_templates/历史回忆处理规则.md`, `认知冲突处理规则.md`.

## Roleplay Logic Chain

`memory + relationship → psychological reaction → behavior decision → language realization`

Not: `surface tone imitation → generic reply`.

## Memory Retrieval

Two libraries (`scene_archive` + `memory_timeline`), two-level funnel:
Level 1 (default, <20ms) — jieba + vocab dict + FTS5 top-K summaries;
Level 2 (rare, 200–300ms) — LLM `search_memory` tool → embedding on
summary vectors. Proactive context-state keyword association each turn.
Tech: `jieba` + `sqlite FTS5` primary + `bge-large-zh-v1.5` optional.
Single SQLite, no separate vector DB.
→ `docs/requirements.md` §12 + `simulation/retrieval/index_and_rag.md`.

## Git Branch Model

Three-branch model — `main` is the only branch ever pushed to remote:

- `main` = framework only (code / schema / prompt / docs / `ai_context/` / skills). No real `work_id`-named directories or manifests; `_template/` scaffolding only.
- `extraction/{work_id}` = per-work in-progress extraction. Local only.
- `library` = archive of completed extractions. Each finished `extraction/{work_id}` squash-merges here. Local only.

Flow:

- Idle = `main`. Orchestrator auto-checks out `extraction/{work_id}` and returns to `main` on any exit via `try / finally: checkout_main(...)` in `automation/persona_extraction/orchestrator.py`.
- `checkout_main` / `preflight_check` accept `scope_paths`; orchestrator passes `["works/{work_id}/"]` — only scope-internal dirt blocks; scope-external dirt tolerated.
- Code / schema / prompt / docs / `ai_context/` commits → `main` first, then `git merge main` from extraction and library branches.
- Extraction-data commits (baseline + Phase 3+ products) belong only on the extraction branch. `_offer_squash_merge` squash-merges to **`library`** (configurable via `[git].squash_merge_target`, default `library`) interactively after all stages `COMMITTED` — never to `main`, so the public-facing branch stays artefact-free.
- After squash-merge, delete the source `extraction/{work_id}` branch (`git branch -D`) and run `git gc --prune=now` to reclaim the accumulated regen commits. The `library` squash is the only retained record; `extraction/{work_id}` is a disposable scratchpad — failed regens may be committed freely without polluting `library` history or long-term disk usage.
- `library` absorbs framework updates via periodic `git merge main`; never flows back to main.
- Anomaly guard: SessionStart hook (`.claude/hooks/session_branch_check.sh`) warns when working tree is non-main yet no orchestrator process is running.

## Automated Extraction Pipeline

Orchestrator: `automation/persona_extraction/`. Each phase step = fresh
`claude -p` or `codex` call, no shared session, file-based context.

Phases (full detail → `automation/README.md` +
`docs/architecture/extraction_workflow.md`):

- **Phase 0** — chapter summarization, parallel chunks; 3-level JSON repair (L1 regex / L2 LLM / L3 full re-run max 1) **+ jsonschema gate against `schemas/analysis/chapter_summary_chunk.schema.json`** — schema fail routes to L3 with the failure injected as `prior_error` so the LLM gets the bound violation in the retry prompt; gate blocks Phase 1.
- **Phase 1** — global analysis (identity merge → world overview → stage plan → candidates). Stage chapter-count exit validation (5–15).
- **Phase 1.5** — user confirms targets + stages.
- **Phase 2** — baseline production (world foundation + character baselines, draft).
- **Phase 3** — per-stage loop: (1) 1+2N extraction (1 world + N char_snapshot + N char_support) → (2) programmatic post-processing (digests + catalog; summaries 1:1 copy of source) → (3) `repair_agent` per file in parallel → (4) post-repair PP rerun **before** `transition(PASSED)` → (5) commit-ordering contract (commit first; non-empty SHA → `COMMITTED`; empty → `FAILED`). JSONL slice write-back merges by key so prior stages cannot be truncated. Extraction prompts do NOT read `baseline_merge.md`, digests, or catalog; char extraction does NOT read world snapshot.
- **Phase 3.5** — 10 programmatic cross-stage consistency checks (0 token), incl. `memory_digest` / `world_event_digest` 1:1 equality gates. `consistency_report.json` committed regardless of pass/fail; errors block Phase 4.
- **Phase 4** — scene archive (independent; needs only `stage_plan.json`). Per-chapter parallel LLM + programmatic extraction → `works/{work_id}/retrieval/scene_archive.jsonl` (git-ignored). `validate_scene_split` runs hand-written line-coverage checks **+ jsonschema gate against `schemas/analysis/scene_split.schema.json`**; any failure (manual or schema) feeds the existing `prior_error` retry path (`build_scene_split_prompt(prior_error=...)`) so the LLM sees the bound violation on retry. Same-run retry budget `[phase4].max_retries_per_chapter` (default 2); circuit breaker `[phase4].circuit_breaker_*`. CLI `--start-phase 4`. Stage assignment (`stage_id` and the `S###` segment of `SC-S###-##`) is program-level: chapter → `stage_plan` range. A new `stage_plan` can be applied to an existing `scene_archive.jsonl` via pure remap (re-derive `stage_id` and renumber per-stage seq) without re-running per-chapter LLM extraction.

### Key Design

- **Lane-level resume (Phase 3)**: `StageEntry.lane_states` per-lane completion; `--resume` re-runs only missing / corrupt lanes. `phase3_stages.json` atomic write.
- Phase 3 + Phase 4 independent PID locks (can run in parallel).
- Fast empty-failure backoff (`[backoff].fast_empty_failure_backoff_s`); token / context errors not retried.
- **Token-limit auto-pause** (§11.13) — `RateLimitController` + flock-merged `rate_limit_pause.json`; failed prompt re-runs without consuming a retry slot. Hard-stops exit 2. Pause excluded from `--max-runtime`. → `automation/persona_extraction/rate_limit.py` + `docs/requirements.md` §11.13.
- `--end-stage` strict prefix: finalization only after all stages `COMMITTED`.
- `jsonschema` = HARD dep. Disk reconcile self-heal on every startup (Phase 0/3/4); Phase 3 verifies `committed_sha` via `git cat-file -e`.
- Config: single-source TOML at `automation/config.toml`; override priority CLI > `config.local.toml` > `config.toml` > dataclass defaults.

Schema docs → `docs/architecture/schema_reference.md`.
