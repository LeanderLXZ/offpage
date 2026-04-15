# Current Status

## Project Stage

Architecture scaffold created. First real work package onboarded. Automated
extraction orchestrator built and under iterative testing. No runtime
implementation code yet.

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
  - `behavior_rules.schema.json` — per-emotion reaction patterns, triggers,
    `core_goals` (rational) + `obsessions` (non-rational) split
  - `memory_timeline_entry.schema.json` — subjective memory with
    misunderstanding/concealment tracking
  - `boundaries.schema.json` — hard/soft boundaries, common misconceptions
  - `failure_modes.schema.json` — AI roleplay failure prevention
  - `stage_snapshot.schema.json` — misunderstandings, concealments,
    stage_delta, `character_arc` (bird's-eye arc from stage 1 to current),
    `behavior_state` with `core_goals` + `obsessions`, `emotional_baseline`
    with `active_goals` + `active_obsessions`
- User package template at `users/_template/`

### First Work Package

- One Chinese web novel onboarded (500+ chapters)
- Phase 0-1 complete (chapter summaries + global analysis)
- Phase 2 target characters confirmed (2 characters)
- Phase 2.5-3 in progress (baseline + stage extraction)

### Automated Extraction Orchestrator

- `automation/` directory with Python package `persona_extraction`
- CLI entry point: `persona-extract` command
- LLM backend abstraction supporting Claude CLI and Codex CLI
- Progress tracking with state machine (pending → extracting → extracted →
  post_processing → reviewing → passed → committed)
- **Stage-internal parallelism**: world + N character extractions run
  fully parallel within each stage (1+N LLM calls via ThreadPoolExecutor).
  Character extraction does not read world snapshot — both read the same
  source text independently; cross-consistency verified at commit gate.
  Every stage can correct and supplement baseline files (not just stage 1).
- Programmatic post-processing (`post_processing.py`): after extraction,
  automatically generates `memory_digest.jsonl` from `memory_timeline`
  (summary copied 1:1 from each entry's `digest_summary`),
  `world_event_digest.jsonl` from world snapshot `stage_events` (50–80
  字 per entry, 5-level importance inferred by keyword), and maintains
  `stage_catalog.json` from snapshot metadata (0 token, idempotent).
  IDs use `{TYPE}-S{stage:03d}-{seq:02d}` format (e.g. `M-S003-02`,
  `E-S001-05`); stage is encoded in the ID so digest entries omit
  redundant `stage_id` fields, and the runtime loader filters via regex.
- Parallel review lanes (`review_lanes.py`): world + each character gets
  an independent validate → review → fix pipeline, running in parallel.
  Commit gate (提交门控) is structural + identifier level only — it verifies
  snapshot existence, stage_id field alignment, catalog/digest entry coverage,
  and runs a warn-only cross-entity reference resolution (world snapshot
  mentions resolve via world cast or active character aliases). Content-level
  world-vs-character conflicts remain the character lane semantic reviewer's
  job. Memory digest gate parses the stage segment out of `memory_id`
  (`M-S{stage:03d}-`), not from a `stage_id` field — the schema forbids
  that field. All lanes must pass; any failure → full stage rollback.
- Two-layer quality check per lane: programmatic (`jsonschema` is a HARD
  dependency — see `automation/pyproject.toml`) + semantic (LLM reviewer
  with narrowed input scope)
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
- Git integration: extraction branch, per-stage commits, auto-rollback
  (full-repo scope), squash-merge to main on completion. Commit ordering
  contract: `git commit` first — only a non-empty SHA transitions the stage
  to `COMMITTED`. Empty/failed commit → stage reverts to `FAILED` so resume
  can retry (prevents "progress says committed, git has no object" drift).
  `--end-stage` has strict prefix semantics: Phase 3.5, squash-merge prompt,
  and Phase 4 only run after **all** stages are `COMMITTED`. Prefix runs
  print a "re-run without --end-stage to finalize" hint and exit.
- Phase 3.5 cross-stage consistency checker (`consistency_checker.py`):
  8 programmatic checks (zero tokens) after all stages commit;
  importance-based thresholds for target_map example counts
  (主角≥5, 重要配角≥3, others≥1)
- Resume auto-reset: blocked stages automatically reset to pending on
  `--resume`, no manual progress file editing needed
- Progress/end-stage separation (Phase 4 pattern): progress always
  contains full stage plan; `--end-stage` is runtime-only limit with strict
  prefix semantics (no Phase 3.5 / squash / Phase 4 until all stages commit).
  Defensive expansion at extraction loop entry for edge cases
- Phase 4 scene archive (`scene_archive.py`): per-chapter parallel
  LLM calls for scene boundary annotation, programmatic validation,
  full_text extraction by line number. `--start-phase 4` standalone,
  `--concurrency` for parallelism. Output: `works/{work_id}/retrieval/`.
  Independent PID lock (`.scene_archive.lock`) — can run parallel
  with Phase 3. Intermediate `analysis/scene_splits/`
  is git-ignored (must not be tracked) and preserved from Phase 3
  rollback. Resume verifies split files exist on disk — missing files
  reset to pending. Global circuit breaker: 60s window, ≥8 failures →
  pause 180s
- Prompt templates: analysis, world extraction, character extraction,
  world semantic review, character semantic review, targeted fix,
  scene split. Character extraction prompt embeds the self-contained
  snapshot contract directly and dynamically injects importance-based
  quality requirements (min examples per target). Extraction prompts do
  not read or write `memory_digest.jsonl` or `stage_catalog.json`
  (programmatic). Character extraction prompt does not read the world
  snapshot — it runs in parallel with world extraction
- Breakpoint recovery via progress file; token/context limit errors
  distinguished from rate limits (not retried — same prompt will fail again).
  Fast empty failures (<5s + empty stderr) also retried with exponential
  backoff (30s → 60s → 120s)
- Baseline recovery: `baseline_done` tracked in progress; `--resume`
  auto-detects incomplete baseline and re-runs Phase 2.5
- Phase 2.5 exit validation: `validate_baseline()` checks schema
  compliance and required field non-null for identity/manifest/foundation
  before allowing Phase 3 to start
- Smart resume: PENDING stage with extraction output already on disk
  skips LLM extraction, jumps to post-processing (saves tokens)
- Disk reconcile self-heal: every startup, Phase 0/3/4 progress files
  call `reconcile_with_disk()` to align state vs on-disk artifacts —
  terminal+missing → revert PENDING; PENDING+present → purge as
  partial; intermediate → purge+revert. Phase 3 also verifies
  `committed_sha` reachability via `git cat-file -e` (lost commits
  treated as missing). Phase 3 also self-heals missing/corrupt
  `phase3_stages.json` by rebuilding from `stage_plan.json`
- Process guard: PID lockfile (prevents duplicate runs; Phase 3 uses
  `.extraction.lock`, Phase 4 uses `.scene_archive.lock` — independent),
  startup git preflight check (Phase 3 only), SIGINT/SIGTERM graceful
  shutdown
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
- memory_timeline schema uses `time`, `location`, `scene_refs` fields;
  `memory_id` pattern `M-S###-##`; `event_description` 150–200 字 and
  `digest_summary` 30–50 字 (both hard schema gates).
- scene_archive schema uses `scene_id` (pattern `SC-S###-##`), `time`,
  `location`, plus scene boundaries and `characters_present`.
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

- Stage extraction in progress — no finished character package yet
- No real user package yet (only template)
- No simulation-engine service implementation
- No terminal adapter implementation
- No retrieval implementation yet (design finalized, pending extraction
  completion)
- World schemas incomplete (no formal schema for foundation, timeline, events,
  locations, maps, state snapshots)
- No final roleplay prompt produced
- Automated extraction pipeline built, iterative testing in progress

## Rules In Effect

- Content language follows work language (Chinese for Chinese works)
- `ai_context/` is English for AI handoff
- Real user packages stay local (not committed)
- Full novels, databases, indexes, large artifacts not committed
- Under `works/*/analysis/`, only durable analysis products are git-tracked
  (`world_overview.json`, `stage_plan.json`, `candidate_characters.json`,
  `consistency_report.json`). `progress/`, `chapter_summaries/`,
  `scene_splits/`, `evidence/*` are local-only runtime artifacts per
  `.gitignore`. `works/*/world/`, `works/*/characters/`, and
  `works/*/indexes/` are git-tracked canon assets; `works/*/retrieval/`
  is local-only.
- `docs/logs/` is write-mostly; do not proactively read
- No per-stage report files; use progress files in-place
- Stages split by natural story boundaries (target 10 ch, min 5, max 15)
