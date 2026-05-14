<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `Character A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# Architecture Snapshot

Compressed summary. Authoritative sources:
`docs/architecture/system_overview.md`, `data_model.md`,
`schema_reference.md`, `extraction_workflow.md`,
`extraction/README.md`, `extraction/repair/`.

## Top-Level Structure

- `sources/` — raw novel inputs + normalized source packages
- `works/` — source-grounded canonical packages (world / characters / analysis / indexes)
- `users/` — user-specific mutable state, grouped by `user_id`
- `simulation/` — runtime-engine lifecycle, retrieval, service contracts
- `prompts/` — manual-only (ingest / review / supplement / cold start)
- `schemas/` — persistence + runtime-request schemas
- `interfaces/` — future terminal adapters
- `extraction/` — extraction orchestrator (Python)
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
2. Target character `identity.json` (incl. `core_wounds`, `key_relationships`) + self-contained stage snapshot (carries inline `failure_modes` / `voice_state` / `behavior_state` / `boundary_state`)
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
boundary_state, `failure_modes` (inline 4 sub-classes), relationships,
personality, mood, knowledge, `character_arc`). Runtime loads a single
snapshot — no baseline merge required.

- `identity.json` + `target_baseline.json` are the character-level constants (both Phase 2 outputs, immutable from Phase 3 onward) — load alongside the stage snapshot. `target_baseline` anchors phase 3 stage_snapshot target keys (cross-file hard fail; see #13).
- voice / behavior / boundary / failure_modes have **no separate baseline files**; their state is carried by the stage_snapshot evolution chain (S001 derives a baseline seed from source + identity; S002+ evolves from prev snapshot).
- `target_voice_map` / `target_behavior_map` (all entries key by `target_character_id`, detail level varies by tier — 核心 / 重要 targets carry ≥3–5 examples, 次要 / 普通 / never-appeared targets stay terse / empty per D4 state 3) filtered by user role: canon role → exact `target_character_id` match; OC role → fallback via the entry's `target_type` sibling label per role_binding. Fallback for absent matches = backward scan through previous snapshots (pure code I/O).

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

- Idle = `main`. Orchestrator auto-checks out `extraction/{work_id}` **before Phase 0** (the very first LLM call) and returns to `main` on any exit via `try / finally: checkout_main(...)` in `extraction/persona_extraction/orchestrator.py::run_full`. All five phases (0 chunk summaries / 1 analysis fan-out / 1.5 user confirmation + works manifest write / 2 baseline / 3+ stage extraction) run on the extraction branch — no phase is exempt. Resume paths inherit the same invariant: phase 1.5 not done → fresh-start path's outer try block switches; phase 1.5 done → `run_extraction_loop`'s inner try block switches.
- `checkout_main` / `preflight_check` accept `scope_paths`; orchestrator passes `["works/{work_id}/"]` — only scope-internal dirt blocks; scope-external dirt tolerated.
- Code / schema / prompt / docs / `ai_context/` commits → `main` first, then `git merge main` from extraction and library branches.
- Extraction-data commits (baseline + Phase 3+ products) belong only on the extraction branch. `_offer_squash_merge` squash-merges to **`library`** (configurable via `[git].squash_merge_target`, default `library`) interactively after all stages `COMMITTED` — never to `main`, so the public-facing branch stays artefact-free.
- After a successful squash-merge the orchestrator interactively offers (`[y/N]`, default N) to delete the source `extraction/{work_id}` branch (`git branch -D`) and run `git gc --prune=now`, reclaiming the accumulated regen commits. Branch deletion is destructive, so the prompt always runs even when `[git].auto_squash_merge=true`; the user must explicitly opt in. Once disposed, the `library` squash is the only retained record; until then `extraction/{work_id}` is preserved as a disposable scratchpad — failed regens may be committed freely without polluting `library` history or long-term disk usage.
- `library` absorbs framework updates via periodic `git merge main`; never flows back to main.
- Anomaly guard: SessionStart hook (`.claude/hooks/session_branch_check.sh`) warns when working tree is non-main yet no orchestrator process is running.

## Automated Extraction Pipeline

Orchestrator: `extraction/persona_extraction/`. Each phase step = fresh
`claude -p` or `codex` call, no shared session, file-based context.

Phases (full detail → `extraction/README.md` +
`docs/architecture/extraction_workflow.md`):

- **Phase 0** — chapter summarization, parallel chunks; 3-level JSON repair (L1 regex / L2 LLM / L3 full re-run max 1) **+ jsonschema gate against `schemas/analysis/chapter_summary_chunk.schema.json`** — schema fail routes to L3 with the failure injected as `prior_error` so the LLM gets the bound violation in the retry prompt; gate blocks Phase 1. **Dual-mode dispatch** via source manifest `structure_mode` (schema-required, no default-fill): `monolithic` runs token-budget chunking (`chunk_size` chapters per chunk); `light_novel` sets `1 chunk = 1 chapter = 1 sub-section` (degenerate single-element chunks, no token-budget batch logic) — chunk_summary output schema / path unchanged. Chunk schema carries per-summary fields (`chapter` / `title` / `summary` 150–200 CJK chars / `characters_present` / `emotional_tone` / `identity_notes`) **plus** chunk-level secondary fields aggregating the world / power / faction / region / arc signals across the chunk (`chunk_arc_summary` required, `chunk_world_rules[].{rule,description,observed_impact}` / `chunk_power_levels[].{name,description}` / `chunk_factions[].{name,description,members_present}` / `chunk_regions[].{name,description}` empty arrays when absent); all sub-objects `additionalProperties: false` + `required: [name|rule]`. Phase 1 foundation lane reads these as direct signals to populate `world/foundation/foundation.json` (no genre-template fallback); Phase 2 baseline does NOT re-synthesise foundation (decision #54 — phase 2 缩水到仅补 `key_figures`).
- **Phase 1** — global analysis fan-out into independent lanes (each = one `claude -p` + projected chunks subset + per-lane jsonschema gate + per-lane `correction_feedback`-style retry). **Monolithic mode = 3 lanes parallel** (`foundation` / `stage_plan` / `candidate_characters`); **light_novel mode = 2 lanes parallel** (`foundation` + `candidate_characters`) plus orchestrator-side programmatic `stage_plan` derivation (zero LLM call — `_build_light_novel_stage_plan` builds 1:1 from `chapter_index` with `stage_id = S{n:03d}`, `chapters = f"{chapter_id}-{chapter_id}"` degenerate single-chapter range, `chapter_count = 1`, `stage_title = chapter_index[i].title` soft-truncated to schema cap + `…`; STAGE_MIN/MAX bypassed). Each lane's chunk inputs are pre-projected and staged at `works/{work_id}/analysis/.phase1_lane_inputs/{lane}/chunk_NNN.json` (gitignored, cleaned on run_analysis exit) — narrow field projection per lane (foundation = chunk-level secondary fields ONLY, `summaries[]` dropped — full-book setting writeup needs no per-chapter anchor; stage_plan = `chunk_arc_summary` + `chunk_regions` + per-summary `chapter` + `summary` only — `characters_present` / `emotional_tone` / `identity_notes` dropped, orthogonal to chapter-boundary plot-arc merging; candidate_characters = per-summary `chapter` + `summary` + `characters_present` + `identity_notes` + `chunk_factions[].{name,members_present}` — `summary` carries event context for cross-chunk identity merging beyond what short `identity_notes` covers). **Foundation lane 输出路径** = `works/{work_id}/world/foundation/foundation.json`（decision #54 — foundation 由 phase 1 直接产到 world 域，phase 2 不再二次综合）；**`major_factions[].key_figures` 双阶段语义**（决策 #54 修订段）：phase 1 lane 写 raw 名（chunk_factions[].members_present[] 跨 chunk 合并去重，化名 / 真名 / 称呼任一），phase 2 baseline LLM 替换能匹配 candidate_characters.aliases 的 raw 名为 character_id，匹配不上保留 raw 名。Per-lane retry budget `[phase1].exit_validation_max_retry` is **independent per lane** (no shared pool); failed lanes inject schema/limit error as `prior_error` into the next attempt's prompt (same pattern as Phase 0 / Phase 4) while successful lanes' artifacts persist; `--resume` reconcile skips schema-valid produced files lane-by-lane. Phase 2+ does not branch on `structure_mode` — `stage_plan` is the single contract downstream. → decision #52 + #54.
- **Phase 1.5** — user confirms targets + stages. Default-recommended set = candidates with `importance == "主角"` (rule-based program selection; user may add / remove). The `recommended` boolean field on candidates is removed (decision #53); the `RECOMMENDED` display label is now derived from `importance`.
- **Phase 2** — baseline production. Phase 1 foundation lane 已落 `world/foundation/foundation.json`；phase 2 produces: world `fixed_relationships.json` + per-character `identity.json` + per-character `target_baseline.json` + per-character `manifest.json`，**plus** 在同一次 baseline_prompt LLM call 内**替换** `foundation.major_factions[].key_figures` 的 raw 名为 character_id——输入 phase 1 落盘 foundation（含 raw 名 key_figures）+ candidate_characters（含 character_id + aliases）+ 已确认目标清单；LLM 对每个 raw 名 lookup `candidates[*].aliases`，能匹配换为对应 character_id，匹配不上保留 raw 名（不报错、不删除）；schema 不抓 character_id 合法性，key_figures 最终是 character_id + 未合并 raw 名混合（decision #54 修订段）。**Validation-triggered recovery 与 `--start-phase 2` force_baseline 前置 guard**（决策 #56）：调用 `run_baseline_production` 重写 `target_baseline.json` 前检测已有 phase 3 committed 产物（`phase3_stages.json` 任一 stage state == `COMMITTED` 或扫磁盘 `world/stage_snapshots/*.json` + `characters/*/canon/stage_snapshots/*.json` 非空）；存在 → daemon 模式 hard stop + `sys.exit(1)` 打印清理清单 / 前台 `input("Continue and overwrite phase 3 artifacts? [y/N]: ")` 非 y 退出。`--reset-phase3-after-baseline-change` 自动清理 flag 不实现（二期 todo）。`target_baseline.json` is the full-book-view roster of every target character (with `tier` ∈ {核心 / 重要 / 次要 / 普通} + `relationship_type` flexible Chinese-string with 14 default candidates / out-of-list fallback allowed + ≤100-char description) — **准入门槛 = 本角色与目标角色在 chapter_summaries 摘要描述中被反映为有过 dialogue / action 交互**（decision #54，替换原"宁可多列、不可漏列、被点名提及即纳入"原则；血亲不再默认核心 tier）。`targets` array cap shared via `schemas/character/targets_cap.schema.json` $ref (downstream stage_snapshot's three target structures inherit the same cap, single-source — fragment lives in the character domain since both producer and consumers do). Phase 3 stage_snapshot three structures (`voice_state.target_voice_map` / `behavior_state.target_behavior_map` / top-level `relationships`) MUST be **set-equal** to `targets[].target_character_id` (bidirectional cross-file hard fail; tri-state via content emptiness, fixed_relationship exception). Validation at the phase 3 single-stage validate layer routes violations through the file-level repair lifecycle (L1/L2/L3 per #25 disambiguation——phase 3 stage 抽取产物的 repair framework lifecycle，与 phase 0 JSON repair L1/L2/L3 同名不同物); baseline immutable from phase 3 onward.
- **Phase 3** — per-stage loop: (1) 1+2N extraction (1 world + N char_snapshot + N char_support) → (2) programmatic post-processing (digests + catalog; summaries 1:1 copy of source) → (3) `repair` per file in parallel → (4) post-repair PP rerun **before** `transition(PASSED)` → (5) commit-ordering contract (commit first; non-empty SHA → `COMMITTED`; empty → `FAILED`). JSONL slice write-back merges by key so prior stages cannot be truncated. Extraction prompts do NOT read digests or catalog (programmatic post-processing handles them); char extraction does NOT read world snapshot. **char_snapshot sub-lane split** (`[phase3].char_snapshot_sub_lanes`, default `true`): each char_snapshot lane internally fans out **4** parallel sub-lanes (`char_expression` / `char_decision` / `char_internal` / `char_social`) sharing one prompt template (placeholder `{lane_scope}` switches the field subset). Sub-lane partials land at `.partial/{stage_id}_{lane}.json` and merge programmatically via `extraction/persona_extraction/phases/snapshot_merge.py` — hard gates: per-lane top-level field set equals its allocation, `failure_modes` 4-subkey mutual-exclusion across **3** lanes (`tone_traps`→expression / `{knowledge_leaks, common_failures}`→internal / `relationship_traps`→social), `stage_delta` 6-subkey mutual-exclusion across `char_decision` (3 subkeys) / `char_social` (3 subkeys), `behavior_state` 8-subkey mutual-exclusion across `char_decision` (7 self-behaviour subkeys: `core_goals` / `obsessions` / `decision_making_style` / `emotional_triggers` / `emotional_reaction_map` / `habitual_behaviors` / `stress_response`) / `char_social` (`target_behavior_map`), tri-target keys set-equal to `target_baseline.targets[].target_character_id` (reuses `extraction/repair/checkers/targets_keys_eq_baseline.py` as merge pre-flight); the (D) drop semantics from decision #11f are honoured because merge **does not** check partial entry count ≥ prev. **Prev snapshot 4-way slice** — orchestrator slices `stage_snapshots/{prev}.json` into `.partial_prev/{prev_stage_id}_{lane}.json` per-lane projections (via `snapshot_merge.slice_snapshot_for_lane`) before each stage runs; `char_expression` / `char_decision` read only their own slice, `char_internal` / `char_social` each read both internal + social slices (covers the knowledge ↔ relationships coupling). Per-lane prev context drops from ~30 KB (whole snapshot) to ~7–13 KB. Slice lifecycle mirrors `.partial/`: R3 cleanup before stage start (unconditional re-write for freshness), explicit clear after repair + before `[5/5] Git commit`, and on sub-lane / merge failure. **2-character peak LLM concurrency** = 1 world + 2×4 snapshot sub-lanes + 2 support = **11**; sub-lane off = 5; both ≤ `[phase3].concurrency=12` cap (raised from 10 in 3-lane era). N≥3 characters peak `1 + 4N + N` exceeds cap and falls back to RateLimitController pause — tracked in todo `T-PHASE3-PEAK-CAP-N-CHARS`. `lane_states` granularity stays `snapshot:{char_id}` — any sub-lane or merge failure re-runs the whole snapshot lane, PENDING / ERROR `.partial/` files are wiped (not re-used). Repair lifecycle 2 T3 regen routes through the same 4-sub-lane re-extract + merge path (each sub-lane prompt injects `prior_attempt_context` ≤600 char summary + error info), preserving `max_lifecycles_per_file = 2` + `T3_EXHAUSTED` semantics. CLI `--char-snapshot-sub-lanes` / `--no-char-snapshot-sub-lanes` overrides toml; light_novel mode keeps the same single bool + flag (no mode-aware default) — switch per-work manually when single-stage size makes sub-lane overhead > savings. → decision #55.
- **Phase 3.5** — programmatic cross-stage consistency checks (0 token), incl. `memory_digest` / `world_event_digest` 1:1 equality gates. The D4 `targets keys == baseline` rule no longer lives here — it is now enforced in the phase 3 single-stage validate layer (per file, with file-level repair). `consistency_report.json` committed regardless of pass/fail; errors block Phase 4.
- **Phase 4** — scene archive (independent; needs only `stage_plan.json`). Per-chapter parallel LLM + programmatic extraction → `works/{work_id}/retrieval/scene_archive.jsonl` (git-ignored). `validate_scene_split` runs hand-written line-coverage checks **+ jsonschema gate against `schemas/analysis/scene_split.schema.json`**; any failure (manual or schema) feeds the existing `prior_error` retry path (`build_scene_split_prompt(prior_error=...)`) so the LLM sees the bound violation on retry. Same-run retry budget `[phase4].max_retries_per_chapter` (default 2); circuit breaker `[phase4].circuit_breaker_*`. CLI `--start-phase 4`. Stage assignment (`stage_id` and the `S###` segment of `SC-S###-##`) is program-level: chapter → `stage_plan` range. A new `stage_plan` can be applied to an existing `scene_archive.jsonl` via pure remap (re-derive `stage_id` and renumber per-stage seq) without re-running per-chapter LLM extraction.

### Key Design

- **Lane-level resume (Phase 3)**: `StageEntry.lane_states` per-lane completion; `--resume` re-runs only missing / corrupt lanes. `phase3_stages.json` atomic write.
- Phase 3 + Phase 4 independent PID locks (can run in parallel).
- Fast empty-failure backoff (`[backoff].fast_empty_failure_backoff_s`); token / context errors not retried.
- **Token-limit auto-pause** (§11.13) — `RateLimitController` + flock-merged `rate_limit_pause.json`; failed prompt re-runs without consuming a retry slot. Hard-stops exit 2. Pause excluded from `--max-runtime`. → `extraction/persona_extraction/core/rate_limit.py` + `docs/requirements.md` §11.13.
- `--end-stage` strict prefix: finalization only after all stages `COMMITTED`.
- `jsonschema` = HARD dep. Disk reconcile self-heal on every startup (Phase 0/3/4); Phase 3 verifies `committed_sha` via `git cat-file -e`.
- **Length-bound tolerance gate** — final safety valve after every LLM phase exhausts its strict retry budget (Phase 0 L3, Phase 1 `exit_validation_max_retry`, Phase 2 单次 baseline LLM + validate_baseline 失败, Phase 4 `max_retries_per_chapter`, **Phase 3 repair `T3_EXHAUSTED`**——repair 仅在 phase 3 接入，见决策 #25 disambiguation). If the surviving violations are **only** `minLength`/`maxLength` and a relaxed schema (×0.9 floor / ×1.1 ceil) passes, accept as PASS; otherwise keep the strict failure. All other constraints stay strict. Not applied to `post_processing.py` program-only outputs. → `extraction/validation/gates/phase2_baseline.py::validate_with_length_tolerance` + decision #48.
- **Phase 0 recovery sweep** — after the main phase 0 ThreadPool finishes, any chunk whose `state == 'failed'` with error matching `'timed out'` or `'error_max_turns'` AND `recovery_attempted == False` reruns once via `_run_recovery_sweep` using `effort='high'` (per-call `LLMBackend.run` kwarg, no backend swap). ThreadPoolExecutor reuses `phase0.concurrency`; full L1/L2/L3 + tolerance pipeline still applies inside `_summarize_chunk`. `recovery_attempted=True` set unconditionally afterward — `--resume` skips already-swept chunks (no救火 loop). Default `[phase0].recovery_effort = 'high'`. → `extraction/persona_extraction/orchestrator.py::_run_recovery_sweep` + decision #49.
- **CLI `--resume` phase-agnostic resume** — `run_full` is the sole resume entry point: per-phase skip-detection (Phase 0 schema-gated chunk skip / Phase 1 per-lane product check — schema-valid `world/foundation/foundation.json` (decision #54) / `stage_plan.json` / `candidate_characters.json` each independently skips its lane / Phase 1.5 `--characters` bypass / Phase 3 `reconcile_with_disk` + rebuild `phase3_stages.json` from `stage_plan.json`). `--resume` only silences the `'Resume from existing progress?'` prompt inside `run_full`. `--background` validation is stage-aware via `pipeline.json::phases.phase_1_5`: not done → require `--characters` (else daemon hits `confirm_with_user` character-selection stdin); done → require `--resume` or `--characters` (else daemon hits the resume prompt). `--end-stage` 不传 = 全跑（daemon EOFError 路径 `preset_end_stage = None` 兜底，决策 #56）。 → `extraction/persona_extraction/cli.py` + `orchestrator.py::run_full(auto_resume=...)` + decisions #51 & #56.
- Config: single-source TOML at `extraction/config.toml`; override priority CLI > `config.local.toml` > `config.toml` > dataclass defaults.

Schema docs → `docs/architecture/schema_reference.md`.
