# Architecture Snapshot

For full details see `docs/architecture/system_overview.md` and
`docs/architecture/data_model.md`. This file is the compressed summary.

## Top-Level Structure

- `sources/` — raw novel inputs and normalized source work packages
- `works/` — source-grounded canonical work packages (world, characters,
  analysis, indexes)
- `users/` — user-specific mutable state, grouped by `user_id`
- `simulation/` — runtime-engine lifecycle, retrieval, service contracts
- `prompts/` — manual-only prompts (ingest, review, supplement, cold start)
- `schemas/` — persistence and runtime-request schemas
- `interfaces/` — future terminal adapters
- `automation/` — automated stage extraction orchestrator (Python)
- `docs/architecture/` — formal architecture docs (incl. schema reference)
- `ai_context/` — compressed handoff

## System Layers

1. **Source** — raw text, normalized chapters, metadata
2. **Extraction** (`works/{work_id}/analysis/`) — progress, evidence, conflicts
3. **World** (`works/{work_id}/world/`) — foundation, stages, events,
   locations, factions, cast
4. **Character** (`works/{work_id}/characters/{character_id}/`) — identity,
   memory (timeline + digest), voice, behavior, boundaries, stage snapshots
5. **User** (`users/{user_id}/`) — one locked binding; role binding,
   long-term profile, relationship core, contexts, sessions
6. **Simulation Engine** — bootstrap, load, retrieval, writeback, close/merge
7. **Interface** — terminal adapters (future)

## Key Boundaries

- Work-scoped canon under `works/`; user-mutable state under `users/`.
- User conversations never rewrite canonical world or character data.
- One `user_id` = one locked work-target-counterpart binding.
- Chinese works use Chinese identifiers and path segments by default.
- JSON field names may remain English; content text follows work language.

## Runtime Load Formula

Startup loads (in order):

1. World foundation (`foundation.json` + `fixed_relationships.json`) +
   selected world-stage snapshot
2. Target character `identity.json` (incl. `core_wounds`,
   `key_relationships`) + `failure_modes.json` + selected self-contained
   stage snapshot (voice / behavior / boundary / relationship all
   included; no baseline merge)
3. memory_timeline: recent 2 stages (N + N-1) full
   3b. memory_digest.jsonl: stage 1..N filtered
   3c. world_event_digest.jsonl: stage 1..N filtered
4. scene_archive: most recent `scene_fulltext_window` full_text scenes
   (default 10; summaries NOT loaded — FTS5 only)
5. Vocab dict → jieba
6. User role binding + long-term profile + relationship core
7. Current context manifest + `character_state.json` (carries
   relationship_delta and context_memories)
8. Recent session summaries

On-demand: events, locations, factions, history, full transcripts,
archive records, raw source chapters, FTS5 / embedding retrieval.

See `simulation/retrieval/load_strategy.md` for the full tier model.

## Stage Model

- stage (extraction) = stage (runtime), 1:1. Same `stage_id`.
- World package exposes `stage_catalog.json` (bootstrap selector, not
  loaded at runtime) and `world_event_digest.jsonl` (startup-loaded,
  filtered 1..N).
- Character packages project the same `stage_id` into character state.
- Stage N cumulative through 1..N; latest stage = active present.
- User selects stage at setup; applies to target + canon-backed user roles.

## Context Lifecycle

- States: `ephemeral` → `persistent` → `merged`
- Session / context state updates **continuously** during live roleplay.
- `character_state.json` per context tracks real-time change (mood,
  personality drift, voice drift, agreements, events, memories).
- `long_term_profile` and `relationship_core` update **only after
  explicit merge confirmation** at session close.
- Merge is append-first, not destructive overwrite.

## Self-Contained Stage Snapshots

Each `stage_snapshots/{stage_id}.json` is **self-contained**: full
character state for that stage (voice_state, behavior_state with
`core_goals` / `obsessions`, boundary_state, relationships, personality,
mood, knowledge, `character_arc`). Runtime loads a single snapshot
directly — no baseline merge.

Baseline files (`voice_rules.json`, `behavior_rules.json`,
`boundaries.json`) exist as extraction anchors but are **not loaded at
runtime**. Only `identity.json`, `failure_modes.json`, and
`hard_boundaries` are loaded alongside the stage snapshot.

**Filtered loading**: `target_voice_map` / `target_behavior_map` loaded
only for entries matching the user's role (canon = exact, OC = closest
relationship type). Only main / important supporting chars need detailed
entries (3–5 examples); generic types brief.

**Fallback for absent characters**: if the current snapshot lacks a
matching target entry, the engine scans backwards through previous
snapshots. Pure code-level I/O — no extra LLM call.

See `simulation/contracts/baseline_merge.md`.

## Three-Layer Memory

1. **stage_snapshot** — aggregated conclusion ("I trust him now"). One
   per stage. Loaded: current stage only.
2. **memory_timeline** — subjective process per event. Fields:
   `memory_id` (`M-S###-##`), `time`, `location`, `event_description`
   (150–200 字, hard gate, objective narration), `digest_summary` (30–50
   字, hard gate, independent digest source), `subjective_experience`
   (unbounded, first-person psych / causal), `scene_refs`. Loaded:
   recent 2 stages full at startup; distant via `memory_digest.jsonl`
   (~30–40 tokens/entry, `summary` 1:1 copy of `digest_summary`) + FTS5
   / embedding on demand.
3. **scene_archive** — original text split by scene. Fields: `scene_id`
   (`SC-S###-##`), `stage_id`, `chapter`, `time`, `location`,
   `characters_present`, `summary`, `full_text`. Work-level. Loaded:
   only the most recent `scene_fulltext_window` (default 10)
   `full_text` scenes; summaries NOT in Tier 0 — FTS5 only.

## Inter-Character Relationship Evolution

- `relationships` in each stage snapshot records per-target attitude,
  trust, intimacy, guardedness, voice / behavior shifts, driving events,
  target's perceived status, and relationship history from stage 1 to
  present.
- `stage_delta.personality_changes` and
  `stage_delta.relationship_changes` are structured with attribution
  (which character / event caused the change).
- Memory timeline split per-stage:
  `canon/memory_timeline/{stage_id}.json`.

## Historical Recall and Cognitive Conflict

- Historical recall served by memory_timeline +
  relationship_history_summary at startup. Past stage snapshots on
  demand for deeper detail.
- Cognitive conflict handled by runtime prompt rules, not pre-written
  data.
- See `simulation/prompt_templates/历史回忆处理规则.md` and
  `simulation/prompt_templates/认知冲突处理规则.md`.

## Roleplay Logic Chain

`memory and relationship → psychological reaction → behavior decision → language realization`

Not: `surface tone imitation → generic reply`

## Memory Retrieval

Two retrieval libraries (`scene_archive` + `memory_timeline`),
**two-level funnel**:

- **Level 1 (default, <20ms)**: jieba segments user input +
  context-state keywords (location, recent events, emotion), matches
  work-level vocab dict, queries FTS5 for top-K summaries → injected
  into main prompt. LLM judges relevance. No match = no retrieval.
- **Level 2 (fallback, 200–300ms)**: LLM calls `search_memory` tool when
  Level 1 is insufficient. Engine runs embedding search on summary
  vectors. Rare.

Proactive association: engine extracts context-state keywords each
turn, enabling recall without being asked.

Tech: `jieba`, `sqlite FTS5` (primary), `bge-large-zh-v1.5` (optional
fallback). Single SQLite — no separate vector DB.

See `docs/requirements.md` §12 and
`simulation/retrieval/index_and_rag.md`.

## Automated Extraction Pipeline

Python orchestrator in `automation/`. Each phase step = fresh `claude -p`
or `codex` call, no shared session memory, file-based context.

### Phases

- **Phase 0 — Chapter summarization**: chunks (~25 ch each), parallel via
  `ThreadPoolExecutor` (`--concurrency`, default 10). Three-level JSON
  repair (L1 regex → L2 LLM 600s → L3 full re-run, max 1). Completion
  gate blocks Phase 1. Output: `analysis/chapter_summaries/`.
- **Phase 1 — Global analysis**: cross-chunk identity merging → world
  overview → stage plan → candidate characters. Exit validation: stage
  chapter-count check (5–15); violations re-run LLM (≤2 retries); abort
  if still violating.
- **Phase 2 — User confirmation**: user picks target characters +
  confirms stage boundaries.
- **Phase 2.5 — Baseline production**: world foundation
  (`foundation.json`, `fixed_relationships.json`) + character baselines
  (`identity.json`, `manifest.json` + 4 skeleton baselines) from
  full-book context. Drafts — subsequent stages may correct.
- **Phase 3 — Coordinated stage extraction** (per-stage loop):
  1. Extraction: 1+2N LLM calls in parallel (1 world + N char_snapshot
     + N char_support; no inter-lane dependency). Each character is
     split into two independent processes: **char_snapshot** produces
     `stage_snapshots/{stage_id}.json`; **char_support** produces
     `memory_timeline/{stage_id}.json` + baseline corrections.
     char_support does NOT receive the previous snapshot.
  2. Programmatic post-processing (0 token, idempotent): L1 JSON repair
     + generate `memory_digest.jsonl` + `world_event_digest.jsonl` +
     upsert `stage_catalog.json`. `memory_digest.summary` = 1:1 copy of
     `digest_summary`; `world_event_digest.summary` = 1:1 copy of world
     `stage_events` entry. 5-level importance inferred by keyword. IDs
     use `{TYPE}-S{stage:03d}-{seq:02d}`; stage encoded in ID.
  3. Parallel review lanes (1+2N): world + char_snapshot×N +
     char_support×N. Each lane independently runs schema autofix →
     programmatic validate → semantic review → targeted fix (×2) via
     `ThreadPoolExecutor`. No cross-entity reads — each reviewer only
     sees its own lane's outputs.
  4. Commit gate (提交门控) — programmatic (0 token), **structural +
     identifier level only**: snapshot existence, `stage_id` alignment,
     catalog / digest coverage; warn-only cross-entity reference
     resolution. Gate issues attributed to lane types: snapshot checks
     → `char_snapshot`; memory/digest checks → `char_support`.
  5. Git commit — **commit-ordering contract**: git commit first; only
     non-empty SHA → `COMMITTED`; empty SHA reverts to `FAILED` so
     resume retries.

  **Lane-attributed retry** (unified across review and gate): lane FAIL
  → only that lane's products roll back + that lane re-extracts
  (≤ `lane_max_retries`=1); previously PASSED lanes preserved. After
  lane re-extraction, re-run post-processing (idempotent) and re-review
  only the retried lanes (no cross-entity dependency). Gate failures
  cascade by category:
  - `catalog_missing` / `digest_missing` (in
    `POST_PROCESSING_RECOVERABLE`) → free PP rerun + re-gate
  - `snapshot_*` / `lane_review` → lane re-extract sharing the same
    `lane_retries` quota as review failures
  - unattributed structural / exhausted quota → stage ERROR (no
    stage-level retry; `--resume` resets ERROR → PENDING)

  **No stage-level retry**: when any lane exhausts its retry quota, the
  stage goes to ERROR. `--resume` resets to PENDING for a fresh attempt.

  Every stage may correct any existing baseline (via char_support lane).
  Character extraction does NOT read world snapshot. Extraction prompts
  do NOT read `baseline_merge.md`, `memory_digest.jsonl`, or
  `stage_catalog.json` — self-contained snapshot contract embedded in
  prompt.

- **Phase 3.5 — Cross-stage consistency**: after all Phase 3 commits, 8
  programmatic checks (0 token): alias consistency, field completeness,
  relationship continuity, `evidence_refs` coverage, memory_digest
  correspondence, target_map counts (main≥5, important≥3, others≥1),
  stage_id alignment, world_event_digest correspondence. Optional LLM
  adjudication only for flagged items. Errors block Phase 4. Report:
  `consistency_report.json`.
- **Phase 4 — Scene archive**: independent from Phase 3 (only needs
  `stage_plan.json`). Per-chapter LLM calls mark scene boundaries +
  metadata; program extracts `full_text` by line number. Parallel
  (`--concurrency`). Programmatic validation only. Output:
  `works/{work_id}/retrieval/scene_archive.jsonl` (.gitignore).
  `scene_id` = `SC-S{stage:03d}-{seq:02d}`; stage looked up from
  `stage_plan.json` (authoritative). Fully regenerated on merge.
  Intermediate `.scene_archive.lock` +
  `works/{work_id}/analysis/scene_splits/` local ignored (must not be
  git-tracked; preserved from Phase 3 rollback). Resume verifies split
  files — missing resets to pending. CLI: `--start-phase 4`.

### Key Design

- Smart resume: PENDING stage with extraction output already on disk
  skips LLM extraction, jumps to post-processing.
- Three-layer quality check per stage: programmatic validation (free) +
  per-lane semantic review (independent LLM) + commit gate (programmatic
  cross-consistency). Phase 4 = programmatic only.
- Dedicated git branch; each passing stage committed; rollback = `git
  reset`; squash-merge to main on completion.
- Phase 3 and Phase 4 independent PID locks — can run in parallel.
- Fast empty-failure backoff (30s exponential); Phase 4 circuit breaker
  (≥8 failures / 60s → 180s pause).
- `--end-stage` strict prefix: finalization (Phase 3.5, squash-merge
  prompt, Phase 4) only after all stages COMMITTED; prefix run exits
  with a "re-run without --end-stage" hint.
- `jsonschema` is a HARD automation dependency — validator raises
  ImportError when missing (no silent gate downgrade).
- Disk reconcile self-heal on every startup (Phase 0/3/4):
  terminal + missing → PENDING; PENDING + artifact → purge; intermediate
  → purge + revert. Phase 3 verifies `committed_sha` via
  `git cat-file -e` (lost commits treated as missing).
- Token / context-limit errors distinguished from rate limits (not
  retried — same prompt will fail again).

See `automation/README.md` and `docs/requirements.md` §9–§12.
See `docs/architecture/schema_reference.md` for schema documentation.
