# Architecture Snapshot

For full details see `docs/architecture/system_overview.md` and
`docs/architecture/data_model.md`. This file is the compressed summary.

## Top-Level Structure

- `sources/` — raw novel inputs and normalized source work packages
- `works/` — source-grounded canonical work packages (world, characters,
  analysis, indexes)
- `users/` — all user-specific mutable state, grouped by `user_id`
- `simulation/` — runtime-engine lifecycle, retrieval, service contracts
- `prompts/` — manual-only prompts (ingest, review, supplement, cold start)
- `schemas/` — persistence and runtime-request schemas
- `interfaces/` — future terminal adapters (agent, app, MCP)
- `automation/` — automated stage extraction orchestrator (Python)
- `docs/architecture/` — formal architecture docs (incl. schema reference)
- `ai_context/` — compressed handoff for future AI sessions

## System Layers

1. **Source** (`sources/works/{work_id}/`) — raw text, normalized chapters,
   metadata
2. **Extraction** (`works/{work_id}/analysis/`) — stage extraction progress,
   evidence, conflicts
3. **World** (`works/{work_id}/world/`) — world foundation, stages, events,
   locations, factions, cast
4. **Character** (`works/{work_id}/characters/{character_id}/`) — identity,
   memory (timeline + digest), voice, behavior, boundaries, stage snapshots
5. **User** (`users/{user_id}/`) — one locked binding per user; role binding,
   long-term profile, relationship core, contexts, sessions
6. **Simulation Engine** (`simulation/`) — bootstrap, load, retrieval,
   continuous writeback, close/merge flow
7. **Interface** (`interfaces/`) — terminal adapters (future)

## Key Boundaries

- Work-scoped canon under `works/`, user-mutable state under `users/`.
- User conversations never rewrite canonical world or character data.
- One `user_id` = one locked work-target-counterpart binding.
- Chinese works use Chinese identifiers and path segments by default.
- JSON field names may remain English; content text follows work language.

## Runtime Load Formula

Startup loads (in order):

1. World foundation (`foundation.json` + `fixed_relationships.json`)
   + selected world-stage snapshot
2. Target character `identity.json` (incl. `core_wounds`, `key_relationships`)
   + `failure_modes.json` + selected self-contained stage snapshot
   (voice/behavior/boundary/relationship state all included; no baseline
   merge needed)
3. Memory_timeline: recent 2 stages (N + N-1) full text
3b. Memory_digest.jsonl: stage 1..N filtered (distant-history awareness)
3c. World_event_digest.jsonl: stage 1..N filtered (world event timeline)
4. Scene_archive: most recent `scene_fulltext_window` full_text scenes
   (**default 10**; summaries are NOT loaded — they live in FTS5 only)
5. Vocab dict (`works/{work_id}/indexes/vocab_dict.txt`) into jieba
6. User role binding + long-term profile + relationship core
7. Current context manifest + character_state (single per-context file that
   also carries relationship_delta and context_memories)
8. Recent session summaries

On-demand: events, locations, factions, history, full transcripts, archive
records, raw source chapters, FTS5/embedding retrieval from scene_archive
and memory_timeline.

See `simulation/retrieval/load_strategy.md` for the full tier model.

## Stage Model

- **stage (extraction) = stage (runtime), 1:1.** "Stage" is the pipeline
  term (which processing unit); "stage" is the content/runtime term (which
  story phase). They share the same `stage_id`. Both names are kept because
  they serve different audiences.
- World package exposes a `stage_catalog.json` (bootstrap stage selector,
  not loaded at runtime) and `world_event_digest.jsonl` (incremental world
  event timeline, loaded at startup filtered to stage 1..N).
- Character packages project the same `stage_id` into character-specific state.
- Stage N is cumulative through 1..N; the latest stage is the active present.
- User selects a stage at setup; it applies to target character and any
  canon-backed user-side role by default.

## Context Lifecycle

- States: `ephemeral` → `persistent` → `merged`
- Session/context state updates **continuously** during live roleplay.
- `character_state.json` in each context tracks real-time character changes
  (mood, personality drift, voice drift, agreements, events, memories).
- `long_term_profile` and `relationship_core` update **only after explicit
  merge confirmation** at session close.
- Merge is append-first, not destructive overwrite.

## Self-Contained Stage Snapshots

Each `stage_snapshots/{stage_id}.json` is **self-contained**: it includes the
complete character state for that stage (voice_state, behavior_state with
`core_goals`/`obsessions`, boundary_state, relationships, personality, mood,
knowledge, `character_arc`). Runtime loads a single snapshot directly — no
baseline merge needed.

Baseline files (`voice_rules.json`, `behavior_rules.json`, `boundaries.json`)
still exist as extraction anchors but are **not loaded at runtime**. Only
`identity.json`, `failure_modes.json`, and `hard_boundaries` are loaded
alongside the stage snapshot.

**Filtered loading**: `target_voice_map` (in voice_state) and
`target_behavior_map` (in behavior_state) are loaded only for entries
matching the user's role — canon character exact match, OC by closest
relationship type. This keeps prompt budget focused on the active
interaction. Only main characters and important supporting characters
require detailed entries (3-5 examples each); generic types are brief.

**Fallback for absent characters**: if the current stage snapshot lacks
a matching target entry (e.g. the character was absent for several stages
and extraction inheritance was missed), the engine scans backwards through
previous `stage_snapshots/` files to find the most recent snapshot
containing that entry. This is pure code-level I/O before the LLM call —
no extra LLM invocation needed.

See `simulation/contracts/baseline_merge.md` for the full model description.

## Three-Layer Memory System

Three layers with distinct granularity, no redundancy:

1. **stage_snapshot** — aggregated conclusion ("I trust him now"). One per
   stage. Loaded: current stage only at startup.

2. **memory_timeline** — subjective process per event ("After he took that
   sword for me, I started to waver"). First-person, summarized (not raw
   text). Each entry: `memory_id` (`M-S###-##`), `time`, `location`,
   `event_summary` (≤50 chars), `subjective_experience`, `scene_refs`.
   Loaded: recent 2 stages (N + N-1) full at startup; distant stages via
   `memory_digest.jsonl` (compressed index, ~30-40 tokens/entry —
   `{memory_id, summary ≤50, importance, time?, location?}`, stage encoded
   in the ID prefix for loader filtering) + FTS5/embedding on-demand for
   detail.

3. **scene_archive** — original text split by scene. Fields: `scene_id`
   (`SC-S###-##`), `stage_id`, `chapter`, `time`, `location`,
   `characters_present`, `summary`, `full_text`. Work-level asset, not
   per-character. Stored under `works/{work_id}/retrieval/scene_archive.jsonl`.
   Loaded: only the most recent `scene_fulltext_window` (default 10)
   `full_text` scenes for the target at startup; **summaries are NOT in
   Tier 0** — they live in FTS5 and surface on demand.

## Inter-Character Relationship Evolution

- `relationships` in each stage snapshot records per-target attitude, trust,
  intimacy, guardedness, voice/behavior shifts, driving events, target's
  known status (as perceived by this character), and a relationship history
  summary from stage 1 to present.
- `stage_delta.personality_changes` and `stage_delta.relationship_changes`
  are structured objects that require attribution (which character or event
  caused the change).
- Memory timeline is split per-stage: `canon/memory_timeline/{stage_id}.json`.

## Historical Recall and Cognitive Conflict

- Historical recall (past nicknames, speech habits, knowledge state) is served
  by memory_timeline + relationship_history_summary at startup. Past stage
  snapshots are loaded on-demand for deeper detail.
- Cognitive conflict (e.g., character believes someone is dead but they appear)
  is handled by runtime prompt rules, not pre-written scenario data.
- See `simulation/prompt_templates/历史回忆处理规则.md` and
  `simulation/prompt_templates/认知冲突处理规则.md`.

## Roleplay Logic Chain

`memory and relationship → psychological reaction → behavior decision → language realization`

Not: `surface tone imitation → generic reply`

## Memory Retrieval System

Two retrieval libraries (scene_archive + memory_timeline) with a
**two-level funnel**:

**Level 1 — jieba + vocab dict + FTS5 (default, <20ms):**
Every turn, jieba segments user input + context-state keywords (location,
recent events, emotion), matches against work-level vocab dict, queries
FTS5 for top-K summaries. Candidates are injected into the main LLM
prompt — no extra LLM call. No match = no retrieval.

**Level 2 — Embedding via LLM tool use (fallback, 200-300ms):**
LLM calls `search_memory` tool when Level 1 candidates are insufficient.
Engine runs embedding search on summary vectors. Rare — most turns end
at Level 1.

**Proactive association:** Engine also extracts context-state keywords
(current location, recent events, emotion) for jieba matching, enabling
the character to naturally recall related memories without being asked.

Tech: `jieba` (segmentation), `sqlite FTS5` (primary), `bge-large-zh-v1.5`
(optional embedding fallback). Single SQLite file — no separate vector DB
(chromadb/faiss not used).

See `docs/requirements.md` §12 and `simulation/retrieval/index_and_rag.md`.

## Automated Extraction Pipeline

The `automation/` directory contains a Python orchestrator that drives
multi-stage extraction via CLI calls (`claude -p` or `codex`).

### Pipeline phases

- **Phase 0 — Chapter summarization**: Split all chapters into chunks
  (~25 ch/chunk), multiple chunks processed in parallel via
  `ThreadPoolExecutor` (`--concurrency`, default 10). Each chunk is one
  LLM call. Three-level JSON repair (L1 programmatic → L2 LLM 600s →
  L3 full re-run, max 1). Completion gate: all chunks must succeed
  before Phase 1 proceeds. Produces per-chapter structured summaries
  under `analysis/chapter_summaries/`.
- **Phase 1 — Global analysis** (from summaries): cross-chunk character
  identity merging → world overview (`world_overview.json`) → stage plan
  (`stage_plan.json`) → candidate characters
  (`candidate_characters.json`). Exit validation: programmatic check of
  stage chapter counts (5-15 limit); violating stages trigger LLM re-run
  with corrective feedback (up to 2 retries); aborts if still violating.
- **Phase 2 — User confirmation**: user selects target characters and
  confirms stage boundaries.
- **Phase 2.5 — Baseline production**: with full-book context and
  confirmed characters, produce world foundation
  (`world/foundation/foundation.json`, `fixed_relationships.json`) and
  character baselines (`identity.json`, `manifest.json` + 4 skeleton
  baselines) for each target character. These are drafts — any subsequent
  stage may correct them.
- **Phase 3 — Coordinated stage extraction**: per-stage loop:
  1. World + character extraction (1+N LLM calls, **all parallel within
     stage** — no dependency between world and characters)
  2. Programmatic post-processing: L1 JSON repair + generate
     `memory_digest.jsonl` from `memory_timeline` + generate
     `world_event_digest.jsonl` from world snapshot `stage_events`
     (5-level importance inferred by keyword; IDs use
     `{TYPE}-S{stage:03d}-{seq:02d}` so stage is encoded in the ID) +
     upsert `stage_catalog.json` from snapshot metadata (0 token)
  3. Parallel review lanes: world + each character independently runs
     validate → semantic review → targeted fix. Lanes run in parallel
     via ThreadPoolExecutor.
  4. Commit gate (提交门控): structural + identifier-level check only
     (snapshot existence, `stage_id` field alignment, catalog/digest
     coverage; digest stage parsed from `memory_id` prefix — no
     `stage_id` field per schema). Warn-only cross-entity reference
     resolution against world cast + character aliases. Content-level
     conflict detection is the character lane's responsibility.
     Any lane FAIL or hard gate FAIL → full stage rollback.
  5. Git commit — commit-ordering contract: git commit first, then
     transition `PASSED → COMMITTED` only on non-empty SHA; empty SHA
     reverts to `FAILED` so resume retries. Prevents fake-committed drift.
  Every stage may correct any existing baseline (not just stage 1).
  Character extraction does NOT read world snapshot — both read the same
  source chapters independently; cross-consistency verified at commit gate.
  Extraction prompts do NOT read `baseline_merge.md`, `memory_digest.jsonl`,
  or `stage_catalog.json` — self-contained snapshot contract is embedded in
  the prompt; digest and catalog are programmatically maintained.
- **Phase 3.5 — Cross-stage consistency check**: after all Phase 3 stages
  commit, run 9 programmatic checks (zero tokens): alias consistency, field
  completeness, relationship continuity, source_type distribution,
  evidence_refs coverage, memory_digest correspondence, target_map counts,
  stage_id alignment, world_event_digest correspondence. Optional LLM
  adjudication for flagged items only. Errors block Phase 4.
  Report: `consistency_report.json`.
- **Phase 4 — Scene archive**: independent from Phase 3; only requires
  `stage_plan.json` (Phase 1 product). Per-chapter LLM calls mark
  scene boundaries + metadata (start/end line, time, location, characters,
  summary); program extracts `full_text` from source using line numbers.
  Multiple chapters run in parallel (`--concurrency`, default 10).
  Programmatic validation only (line coverage, no overlap, alias matching).
  Output: `works/{work_id}/retrieval/scene_archive.jsonl` (.gitignore).
  `scene_id` format: `SC-S{stage:03d}-{seq:02d}` (e.g. `SC-S003-07`);
  stage number is looked up from `stage_plan.json` (authoritative
  source). scene_archive.jsonl is fully regenerated on each merge.
  Intermediate state: `.scene_archive.lock` +
  `works/{work_id}/analysis/scene_splits/` (local ignored,
  must not be git-tracked; preserved from Phase 3 rollback). Resume
  verifies split files exist — missing resets to pending.
  Progress: `works/{work_id}/analysis/progress/phase4_scenes.json`.
  CLI: `--start-phase 4` runs Phase 4 standalone.

### Key design

- Each stage / phase step is a fresh `claude -p` call (no shared session
  memory)
- Smart resume: if a stage is PENDING but extraction output already exists
  on disk, skip LLM extraction and jump directly to post-processing
- Context between steps is entirely file-based (progress files, previous
  output, schemas, baseline files)
- Three-level JSON repair: programmatic regex (L1, zero tokens) → LLM
  repair on broken JSON only (L2, minimal tokens) → full re-run (L3)
- Three-layer quality check per stage: programmatic validation (free) +
  per-lane semantic review (independent LLM agent) + commit gate
  (programmatic cross-consistency); Phase 4 uses programmatic only
- Extraction runs on a dedicated git branch; each passing stage is committed
- Rollback on failure = `git reset` to last committed stage
- After all stages complete, squash-merge to main (one clean commit);
  extraction branch can be deleted
- Supports Claude CLI and Codex CLI backends
- `--start-phase` selects starting phase; completed phases auto-skip
- Phase 3 and Phase 4 use independent PID locks — can run in parallel
- Fast empty failure backoff (30s exponential) + Phase 4 circuit breaker
  (≥8 failures / 60s → 180s pause)
- `--end-stage` strict prefix: Phase 3.5 / squash-merge prompt / Phase 4
  only after all stages are `COMMITTED`; a prefix run exits with a
  "re-run without --end-stage" hint and skips all finalization steps
- `jsonschema` is a HARD dependency of the automation package; validator
  raises ImportError when missing (no silent gate downgrade)

See `automation/README.md` and `docs/requirements.md` §9–§12 for details.
See `docs/architecture/schema_reference.md` for schema documentation.
