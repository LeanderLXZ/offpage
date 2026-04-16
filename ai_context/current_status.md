# Current Status

## Project Stage

Architecture scaffold done. One work package under automated extraction
(Phase 2.5 / Phase 3 in progress). No runtime code yet.

## What Exists

### Infrastructure

- Full directory scaffold, architecture docs, schemas
- `ai_context/` handoff set
- `simulation/` runtime-engine design (flows, contracts, retrieval) +
  `simulation/prompt_templates/` (historical recall, cognitive conflict,
  memory retrieval, anti-dilution)
- `prompts/` reduced to 4 manual-scenario templates (ingest, review,
  supplement, cold start)
- Character-package schemas for deep roleplay:
  `identity` (`core_wounds`, `key_relationships`), `voice_rules`,
  `behavior_rules` (`core_goals` + `obsessions`), `memory_timeline_entry`
  (misunderstanding / concealment), `boundaries`, `failure_modes`,
  `stage_snapshot` (`stage_delta`, `character_arc`, `behavior_state`,
  `emotional_baseline`)
- User package template at `users/_template/`
- `docs/architecture/schema_reference.md` — complete schema index

### First Work Package

- One Chinese web novel (500+ chapters)
- Phase 0–1 complete; 2 target characters confirmed; Phase 2.5–3 in
  progress

### Automated Extraction Orchestrator

Python package `automation/persona_extraction` with CLI `persona-extract`.
Supports Claude CLI and Codex CLI backends. Full pipeline design in
`architecture.md`. Key features:

- Stage-internal parallelism (1+N LLM calls per stage). Character
  extraction does not read world snapshot — cross-consistency verified
  at commit gate. Every stage may correct baselines.
- Programmatic post-processing (0 token, idempotent): generates
  `memory_digest.jsonl`, `world_event_digest.jsonl`, and upserts
  `stage_catalog.json`.
- Parallel review lanes (world + each character): schema autofix →
  validate → semantic review → targeted fix.
- Commit gate — structural + identifier level; warn-only cross-entity
  reference resolution. Content conflicts = character reviewer's job.
- **Lane-attributed retry** unified across initial extraction, review,
  and gate (shared `lane_max_retries`=2). Full-stage rollback is last
  resort (`max_retries`=2).
- Gate failure cascade by category: `catalog_missing` /
  `digest_missing` / `world_event_digest_missing` → free PP rerun;
  `snapshot_*` / `lane_review` → lane re-extract; else → full rollback.
  Gate emits hard errors when catalogs / digests are absent (no silent
  skip).
- Three-level JSON repair (L1 regex → L2 LLM 600s → L3 full re-run) in
  Phase 0 and Phase 3.
- Phase 0 parallel summarization + completion gate blocks Phase 1.
- Git integration: dedicated branch, per-stage commits, auto-rollback,
  squash-merge to main. Commit-ordering contract prevents fake-committed
  drift.
- Phase 3.5 cross-stage consistency checker (8 programmatic checks, 0
  token).
- Resume auto-reset of blocked stages; progress / end-stage separation
  with strict prefix semantics for finalization.
- Phase 4 scene archive: per-chapter parallel, independent PID lock,
  programmatic validation only, circuit breaker (≥8 failures / 60s →
  180s pause).
- Baseline recovery tracked via `baseline_done`; Phase 2.5 exit
  validation runs on both fresh and `--resume` paths (re-runs Phase 2.5
  if existing baseline fails validation).
- Smart resume skips extraction if output already on disk.
- Disk reconcile self-heal on every startup (Phase 0/3/4); Phase 3
  verifies `committed_sha` via `git cat-file -e`.
- Process guard (PID lock), git preflight, SIGINT/SIGTERM graceful
  shutdown.
- Background mode (`--background`), runtime limit (`--max-runtime`),
  30s heartbeat.
- Fast empty-failure backoff (30s → 60s → 120s); token / context errors
  not retried.
- `jsonschema` is a HARD dependency (no silent gate downgrade).

### Memory System and Retrieval Design

Three-layer design finalized (see `architecture.md`). Two-level funnel
(jieba + FTS5 default; embedding tool-use fallback). Proactive
context-state keyword association. No implementation yet — awaiting
extraction completion.

## Current Gaps

- Stage extraction in progress; no finished character package yet
- No real user package (only template)
- No simulation-engine service implementation
- No terminal adapter implementation
- No retrieval implementation (design finalized, pending extraction)
- World schemas incomplete (no formal schema for foundation, timeline,
  events, locations, maps, state snapshots)
- No final roleplay prompt produced

## Rules In Effect

- Content language = work language; `ai_context/` stays English
- Real user packages stay local, not committed
- No novels, databases, indexes, or large artifacts in git
- `works/*/analysis/`: only `world_overview`, `stage_plan`,
  `candidate_characters`, `consistency_report` are tracked;
  `progress/`, `chapter_summaries/`, `scene_splits/`, `evidence/*` local
- `works/*/world/`, `works/*/characters/`, `works/*/indexes/` tracked;
  `works/*/retrieval/` local-only
- `docs/logs/` write-mostly; do not proactively read
- No per-stage report files; update progress in-place
- Stages split by natural story boundaries (target 10, min 5, max 15)
