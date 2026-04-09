# Current Status

## Project Stage

Architecture scaffold created. First real work package onboarded. Automated
extraction orchestrator built and partially tested (batch_001 committed).
No runtime implementation code yet.

## What Exists

### Infrastructure

- Full directory scaffold, architecture docs, schemas
- `ai_context/` handoff set
- `simulation/` runtime-engine design docs (flows, contracts, retrieval) +
  `simulation/prompt_templates/` (runtime LLM behavior rules: historical
  recall, cognitive conflict, memory retrieval, anti-dilution checklist)
- `prompts/` reduced to 4 manual-scenario templates (ingest, review,
  supplement, cold start); extraction prompts in `automation/prompt_templates/`,
  runtime prompts in `simulation/prompt_templates/`
- First-pass schemas for all major entities (work, world, character, user,
  session, context, role binding, relationship core, long-term profile,
  runtime request, context character state)
- Expanded character-package schemas for deep roleplay support:
  - `identity.schema.json` — baseline identity + `core_wounds` (root
    psychological traumas) + `key_relationships` (cross-story relationship
    arcs with evolution and turning points)
  - `voice_rules.schema.json` — per-emotion, per-target voice model
  - `behavior_rules.schema.json` — per-emotion reaction patterns, triggers;
    `core_drives` split into `core_goals` + `obsessions`
  - `memory_timeline_entry.schema.json` — subjective memory with
    misunderstanding/concealment tracking
  - `boundaries.schema.json` — hard/soft boundaries, common misconceptions
  - `failure_modes.schema.json` — AI roleplay failure prevention
  - `stage_snapshot.schema.json` — enhanced with misunderstandings,
    concealments, stage_delta, `character_arc` (bird's-eye arc from stage 1
    to current), `core_goals`/`obsessions` split in behavior_state,
    `active_goals`/`active_obsessions` split in emotional_baseline
- User package template at `users/_template/`

### First Work Package: 我和女帝的九世孽缘

- Source: `sources/works/我和女帝的九世孽缘/` — 537 normalized chapters from epub
- Canon directory: `works/我和女帝的九世孽缘/` — Phase 0-2.5 complete, Phase 3
  in progress
- Phase 0: 22/22 chapter summary chunks produced (537/537 chapters)
- Phase 1: `world_overview.json`, `source_batch_plan.json` (40 batches),
  `candidate_characters.json` (30 candidates) produced
- Phase 2: Target characters confirmed: 姜寒汐, 王枫
- Phase 2.5: World foundation + character identity baselines — pending
  re-extraction (test products cleaned for schema update retest)
- Phase 3: All 40 batches reset to pending. Extraction runs on branch
  `extraction/我和女帝的九世孽缘`

### Automated Extraction Orchestrator

- `automation/` directory with Python package `persona_extraction`
- CLI entry point: `persona-extract` command
- LLM backend abstraction supporting Claude CLI and Codex CLI
- Progress tracking with state machine (pending → extracting → extracted →
  post_processing → reviewing → passed → committed)
- Programmatic post-processing (`post_processing.py`): after extraction,
  automatically generates `memory_digest.jsonl` from `memory_timeline` and
  maintains `stage_catalog.json` from snapshot metadata (0 token, idempotent)
- Parallel review lanes (`review_lanes.py`): world + each character gets
  an independent validate → review → fix pipeline, running in parallel.
  Commit gate (提交门控) performs programmatic cross-consistency check
  before batch commit. All lanes must pass; any failure → full batch rollback.
- Two-layer quality check per lane: programmatic (jsonschema) + semantic
  (LLM reviewer with narrowed input scope)
- Failure triage: reviewer findings classified as fixable (≤5 specific field
  errors) → targeted fix agent (minimal edits + re-validate); systemic
  (file missing, structural, understanding-level) → full rollback + retry
- Three-level JSON repair pipeline (`json_repair.py`): L1 programmatic regex
  (zero tokens) → L2 LLM repair (600s timeout, configurable via
  `repair_timeout`) → L3 full re-run (caller-implemented, max 1 attempt).
  Integrated into Phase 0 skip-check/post-write and Phase 3 validator for
  both JSON and JSONL files.
- Phase 0 parallel summarization: multiple chunks processed concurrently
  via `ThreadPoolExecutor` (`--concurrency`, default 10). L3 auto-retry on
  JSON repair failure. Completion gate blocks Phase 1 if any chunk missing.
  Completed chunk files auto-skipped on resume.
- Git integration: extraction branch, per-batch commits, auto-rollback
  (full-repo scope), squash-merge to main on completion
- Phase 3.5 cross-batch consistency checker (`consistency_checker.py`):
  8 programmatic checks (zero tokens) after all batches commit;
  importance-based thresholds for target_map example counts
  (主角≥5, 重要配角≥3, others≥1)
- Resume auto-reset: blocked batches automatically reset to pending on
  `--resume`, no manual progress file editing needed
- Progress/end-batch separation (Phase 4 pattern): progress always
  contains full batch plan; `--end-batch` is runtime-only limit.
  Defensive expansion at extraction loop entry for edge cases
- Phase 4 scene archive (`scene_archive.py`): per-chapter parallel
  LLM calls for scene boundary annotation, programmatic validation,
  full_text extraction by line number. `--start-phase 4` standalone,
  `--concurrency` for parallelism. Output: `works/{work_id}/rag/`
- Prompt templates: analysis, world extraction, character extraction,
  world semantic review, character semantic review, targeted fix,
  scene split (coordinated_extraction.md kept for legacy; unified
  semantic_review.md kept for backward compat). Character extraction
  prompt embeds self-contained snapshot contract directly (no longer
  reads `simulation/contracts/baseline_merge.md`). Prompt dynamically
  injects importance-based quality requirements (min examples per target).
  Extraction prompts do not read or write `memory_digest.jsonl` or
  `stage_catalog.json` (programmatic now)
- Breakpoint recovery via progress file; token/context limit errors
  distinguished from rate limits (not retried — same prompt will fail again)
- Baseline recovery: `baseline_done` tracked in progress; `--resume`
  auto-detects incomplete baseline and re-runs Phase 2.5
- Phase 2.5 exit validation: `validate_baseline()` checks schema
  compliance and required field non-null for identity/manifest/foundation
  before allowing Phase 3 to start
- REVIEWING state recovery: verifies extraction output exists on disk
  before continuing review; resets to PENDING if files missing
- Process guard: PID lockfile (prevents duplicate runs), startup git
  preflight check, SIGINT/SIGTERM graceful shutdown
- Background mode (`--background`): survives SSH disconnect, log to
  `extraction.log`, requires `--resume` or `--characters`
- Runtime limit (`--max-runtime`): graceful stop after N minutes
- Progress monitoring: 30s heartbeat with PID, memory (RSS), elapsed time,
  per-step timing and ETA estimates

### Schema Documentation

- `docs/architecture/schema_reference.md` — complete index of all schemas
  with usage, locations, and runtime loading rules

### Memory System and Retrieval Design

- Three-layer memory design finalized: stage_snapshot (aggregated state) +
  memory_timeline (first-person subjective process) + scene_archive (original
  text by scene). No separate dialogue corpus.
- Two-level retrieval funnel:
  Level 1 (default, <20ms): jieba + work-level vocab dict + FTS5 → top-K
  summaries in prompt. LLM judges relevance. No match = no retrieval.
  Level 2 (fallback, rare): LLM tool use (`search_memory`) → embedding
  search on summary vectors → second LLM call.
- Proactive character association: engine extracts context-state keywords
  (location, recent events, emotion) for jieba matching each turn, enabling
  the character to naturally recall related memories without being asked.
- memory_timeline schema updated: added `time_in_story`, `location`,
  `scene_refs` fields.
- scene_archive schema defined (8 fields including `time_in_story`, `location`).
- scene_archive produced in Phase 4 (independent stage, after Phase 3.5).
- Tech: `jieba` (segmentation), `sqlite FTS5` (primary), `bge-large-zh-v1.5`
  (optional embedding fallback). Single SQLite file, no separate vector DB.
- Vocab dict (`works/{work_id}/indexes/vocab_dict.txt`) auto-generated from
  extraction output, loaded into jieba at startup.
- Runtime prompt includes `search_memory` tool definition, retrieval
  instructions, and proactive association guidelines.
- No implementation yet — design only. Build after extraction completes.
- See `docs/requirements.md` §12, `simulation/retrieval/index_and_rag.md`.

## Current Gaps

- First batch extracted but no finished character package yet (39 batches
  remaining)
- No real user package yet (only template)
- No simulation-engine service implementation
- No terminal adapter implementation
- Phase 4 (scene archive) extraction implemented; integration bugs fixed
  (lock bypass, chapter parsing, stage_id mapping, character validation)
- No retrieval implementation yet (design finalized, pending extraction
  completion)
- World schemas incomplete (no formal schema for foundation, timeline, events,
  locations, maps, state snapshots)
- Character baseline files (relationships.json, bible.md) still lack schemas
- No final roleplay prompt produced
- Automated extraction pipeline partially tested (batch_001 end-to-end pass)

## Rules In Effect

- Content language follows work language (Chinese for Chinese works)
- `ai_context/` is English for AI handoff
- Real user packages stay local (not committed)
- Full novels, databases, indexes, large artifacts not committed
- `works/*/analysis/incremental/` and `works/*/indexes/` are git-tracked
- `docs/logs/` is write-mostly; do not proactively read
- No per-batch report files; use progress files in-place
- Batches split by natural story boundaries (target 10 ch, min 5, max 15)
