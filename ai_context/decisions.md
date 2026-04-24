<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `角色A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# Key Decisions — Compressed ADRs

One line decision + one line rationale + pointer to authoritative
source. Long discussion chains live in `docs/logs/`.

## Roleplay Philosophy

1. Priority = deep behavior / decision consistency, not tone mimicry.
   Chain: memory + relationship → psych reaction → behavior → language.
2. Objective fact vs subjective cognition must be separated — characters may misunderstand, conceal, distort.
3. Stage differences preserved; no flattening into a timeless static profile.
   → `project_background.md`, `simulation/prompt_templates/`.

## Data Separation

4. User data separate from canonical character data. No user drift into canon.
5. World is a first-class layer, not inside character notes.
6. World canon revised only by source-text evidence — never by user conversation.
7. Conflicts / revisions recorded explicitly, not silently overwritten.
   → `conventions.md` §Data Separation + `docs/architecture/data_model.md`.

## Work Scope

8. Each novel = independent namespace (`work_id`). User flow picks work before character.
9. Chinese works: Chinese `work_id`, entity names, identifier values, path segments.
10. `ai_context/` stays English. JSON field names may be English.
    → `conventions.md` §Naming.

## Character Depth

11a. `identity.json` carries `core_wounds` (root traumas + behavioral impact) + `key_relationships` (relationship arcs with initial state / evolution / turning points). Loaded with the stage snapshot.
11b. `behavior_state` separates `core_goals` (rational, re-prioritizable) from `obsessions` (irrational, trauma- / emotion-tied, not cost-benefit). `emotional_baseline` mirrors with `active_goals` + `active_obsessions`.
11c. `character_arc` in `stage_snapshot` = bird's-eye stage 1 → current. Complements `stage_delta` (last step only).
     → `schemas/character/` + `docs/architecture/schema_reference.md`.

## Extraction Model

12. stage (extraction) = stage (runtime), 1:1. Natural story boundaries
    (target 10, min 5, max 15). Cumulative 1..N. `stage_id` = `S###`;
    sibling `stage_title` ≤15 chars.
13. Phase 2.5 produces world foundation + character baseline drafts
    from full-book context. Phase 3 does 1+2N split extraction per stage
    (1 world + N char_snapshot + N char_support); any stage may correct
    any existing baseline (via char_support) or asset across the work package.
14. No per-stage report files; progress in-place.
15. `target_voice_map` / `target_behavior_map` use specific names for
    main / important chars (≥3–5 examples); generic types brief or
    omitted. Runtime loads only entries matching user role; fallback =
    backward scan previous snapshots (pure code I/O).
    → `architecture.md` §Automated Extraction Pipeline + `automation/README.md`.

## User Model

16. One `user_id` = one locked work-target-counterpart binding. Setup locks; changes need new package or explicit migration.
17. Canon-backed user roles inherit target stage by default.
18. Session / context state updates continuously. Long-term profile + relationship core update only after explicit merge confirmation.
19. Per-context `character_state.json` tracks real-time mood, personality, voice, agreements, relationship delta, events, memories — promoted to long-term only at merge.
20. Merge is append-first. Events / memories added, never overwritten.
21. Session close explicit. System asks about merge.
22. Full transcripts stay local; startup loads summary layer only.
22a. `relationship_core/` split — `manifest.json` (single-object state) + `pinned_memories.jsonl` (append-only). Merge writes only append. Schema: `schemas/user/pinned_memory_entry.schema.json`.
22b. Append-only streams use `.jsonl`; single-object state uses `.json`. Authoritative extension list → `docs/architecture/data_model.md`.

## Automated Extraction (non-obvious)

23. Each phase call is a fresh `claude -p` / `codex` — no shared session
    memory. Context between steps is file-based.
24. Extraction prompts do NOT read `simulation/contracts/baseline_merge.md`, `memory_digest.jsonl`, `world_event_digest.jsonl`, or `stage_catalog.json`. Self-contained snapshot contract embedded in prompt; digests / catalog are programmatically maintained by `post_processing.py` (0 token, idempotent).
25. Per-stage quality gate = `repair_agent` (unified check + fix + verify). Checkers L0–L3 × fixers T0–T3, orthogonal; field-level json_path patches. Phase B L3 gate catches false "fixed" claims. T3 globally capped `t3_max_per_file=1`. Phase 3 dispatches per file in parallel (default concurrency 10); cross-file consistency lives in Phase 3.5. → `automation/repair_agent/` + `docs/requirements.md` §11.4.
25a. Source-discrepancy triage (`triage_enabled=True`) — two accept paths share `accept_cap_per_file=5`: (A) L3 `source_inherent` (LLM) accepts author-bug residuals with verbatim-quote evidence (literal substring + SHA-256 anchored); (B) L2 `coverage_shortage` (0 token) accepts `min_examples` shortages after one T2 attempt via program-chosen SourceNote. Both persist to `{entity}/canon/extraction_notes/{stage_id}.jsonl` (or `world/extraction_notes/`). Runtime does NOT consume (audit-only). Phase 3.5 treats valid SourceNote as equivalent to meeting `min_examples`. Post-T3 scoped L0–L2 check aborts with `T3_CORRUPTED` (no triage). → `automation/repair_agent/` + `docs/requirements.md` §11.4.
26. Extraction runs on `extraction/{work_id}` branch. Each passing stage committed. Rollback = `git reset`. Squash-merge to `master` on completion.
26a. Branch discipline enforced via orchestrator `try/finally: checkout_master(...)` + SessionStart hook (`.claude/hooks/session_branch_check.sh`). No PreToolUse commit wrapper. → `architecture.md` §Git Branch Model.
27. Orchestrator pre-computes read list per call. Only most recent snapshot + memory_timeline included. Agents don't explore freely.
27a. Manifest split by writer — `sources/works/{work_id}/manifest.json` hand-written at ingestion (validator-gated); both `works/{work_id}/manifest.json` + `works/{work_id}/world/manifest.json` programmatic at Phase 2 / 2.5 end. No `build_status` in manifests — live phase state in `analysis/progress/` only.
27b. Field-level bounds (maxLength / minLength / maxItems) live in JSON schema only — no parallel tunables in `config.toml`, no duplicate length gates in L2 `StructuralChecker`. Rationale: multi-location drift caused silent divergence; schema is the single source of truth. L2 only keeps checks that schema can't express (e.g. `driving_events` / `relationship_history_summary` non-empty warnings). One internal fallback remains — `StructuralChecker.relationship_history_summary_max_chars = 100` — used only as a program-side cap for the super-cap error path; value must track `stage_snapshot.schema.json`. → `schemas/character/*.schema.json`, `automation/repair_agent/checkers/structural.py`.
27c. Character baseline schemas (`identity` / `voice_rules` / `behavior_rules` / `boundaries` / `failure_modes`) and `memory_timeline_entry` carry NO chapter-trace fields (`evidence_refs`) and NO provenance tags (`source_type`). Chapter anchors live on `stage_snapshot.evidence_refs` + `world_stage_snapshot.evidence_refs`. Rationale: baseline files are extraction anchors (not runtime-loaded) and baseline-level chapter trace duplicated stage_snapshot evidence, bloating Tier 0 prompt for no simulation value; `source_type` was never read by runtime or repair agent. → `schemas/character/*.schema.json`.
27d. Digest / memory time-location anchors are hard ≤15-char required fields: `world_event_digest_entry.time` / `location` (copied from world snapshot's newly-required stage-level `timeline_anchor` + `location_anchor`, both ≤15 chars), `memory_digest_entry.time` / `location` (copied from memory_timeline per-event `time` / `location`, also required ≤15), `memory_timeline_entry.time` / `location` (required, ≤15 chars). `knowledge_gained` widened to 10 items × 50 chars. `scene_refs` removed from `memory_timeline_entry` — scene back-pointers are no longer a schema contract; scene lookups resolve via FTS5 on `scene_archive` when needed. Rationale: time/location were used but un-gated, leading to empty or bloated anchors; `scene_refs` was never populated end-to-end and the retrieval path already tolerates its absence. → `schemas/world/{world_stage_snapshot,world_event_digest_entry}.schema.json`, `schemas/character/{memory_digest_entry,memory_timeline_entry}.schema.json`, `automation/persona_extraction/{post_processing,consistency_checker}.py`, `automation/prompt_templates/world_extraction.md`.
27e. `foundation` + `fixed_relationships` + `stage_catalog` field-level caps collapsed into schema. `foundation`: `tone` ≤100, structure / system `summary` ≤200, sub-item descriptive strings ≤50; arrays `major_regions` / `core_rules` / `world_lines` / `major_factions` ≤20, `power_system.levels` ≤15, `major_factions[].key_figures` ≤10. `fixed_relationships`: `description` ≤100; `source_type` + `evidence_refs` removed (was never read). `stage_catalog`: `order` field removed (world + character), sort by `stage_id` lexicographic (`S###` zero-padded); character catalog schema moved from `schemas/work/stage_catalog.schema.json` to `schemas/character/stage_catalog.schema.json`; legacy `*_summary` fields (experience / relationship / personality / current_status / current_mood / voice_shift / knowledge_boundary) deleted — they were schema placeholders never populated by any code path. → `schemas/world/foundation.schema.json`, `schemas/world/fixed_relationships.schema.json`, `schemas/world/world_stage_catalog.schema.json`, `schemas/character/stage_catalog.schema.json`, `automation/persona_extraction/post_processing.py`, `automation/persona_extraction/{orchestrator,prompt_builder}.py`.
27f. Character `stage_snapshot` full-body field-level caps collapsed into schema. Required additions: `timeline_anchor` (≤50) + `snapshot_summary` (100–200). Bounded arrays: `active_aliases.active_names` / `hidden_identities` ≤ 5, `known_as` ≤ 10 properties; `current_status` / `current_personality` / `current_mood` items ≤ 50 chars; `emotional_baseline.dominant_traits` ≤ 10 items × 15 chars, `active_goals` / `active_obsessions` / `active_fears` / `active_wounds` ≤ 10 × 50. `voice_state`: `tone_summary` ≤ 100; `speech_patterns` / `vocabulary_preferences` ≤ 15 × 50; `signature_phrases` ≤ 30 × 10; `taboo_patterns` ≤ 15 × 30; `dialogue_examples` ≤ 10 (quote ≤ 30, context ≤ 50); `emotional_voice_map` ≤ 15 (emotion ≤ 10, voice_shift ≤ 50, typical_expressions ≤ 10 × 15, nested dialogue_examples same bounds); `target_voice_map` ≤ 10 (target_type ≤ 15, rest mirrors emotional_voice_map). `behavior_state`: `core_goals` / `obsessions` ≤ 10 × 50; `decision_making_style` 50–200; `emotional_triggers` ≤ 15 (trigger ≤ 50, reaction ≤ 100); `emotional_reaction_map` ≤ 15 (emotion ≤ 10, typical_actions ≤ 5 × 50); `target_behavior_map` ≤ 10 (target_type ≤ 15, behavior_shift ≤ 100, typical_actions ≤ 5 × 50, action_examples ≤ 5 with action ≤ 50 / context ≤ 100); `habitual_behaviors` ≤ 15 × 50; `stress_response.*` ≤ 50. `boundary_state`: `hard_boundaries` added (≤ 15, rule ≤ 50 + reason ≤ 50, structural peer of baseline boundaries.hard_boundaries); `soft_boundaries` ≤ 15 (rule / exception_condition / stage_note ≤ 50); `common_misconceptions` ≤ 15 (misconception ≤ 50, reality ≤ 100). `relationships`: `target_label` ≤ 30, `summary` / `attitude` / `voice_shift` / `behavior_shift` / `target_known_status` ≤ 50, `driving_events` ≤ 10 × 50, `relationship_history_summary` tightened from 300 → 100. `misunderstandings` / `concealments` tightened from 20 → 15 each (content / truth / cause / reason ≤ 50). `stage_delta`: `trigger_events` ≤ 10 × 50, `personality_changes` / `relationship_changes` ≤ 10 (change ≤ 50, influenced_by ≤ 30, driving_event ≤ 50), `mood_shift` / `voice_shift` ≤ 100. Rationale: same bounds-only-in-schema discipline — L2 `relationship_history_summary_max_chars` constant must track 100 now. → `schemas/character/stage_snapshot.schema.json`, `automation/repair_agent/checkers/structural.py`.
27g. Character `stage_snapshot` structural prunes: `character_arc` reshaped from object (arc_summary + arc_stages[] + current_position) to a single ≤200-char string; top-level `memory_refs` and `evidence_refs` removed (and removed from `required`); `timeline_anchor` added to `required`. Chapter anchors now live only on `world_stage_snapshot.evidence_refs` — character side relies on `timeline_anchor` + `memory_timeline` self-anchors. Per-item `evidence_ref` property removed from all `dialogue_examples` / `action_examples` containers (top-level + inside emotional / target maps) in both `stage_snapshot` and `voice_rules`. `behavior_rules.relationship_behavior_map` renamed to `target_behavior_map`; inner `relationship_type` renamed to `target_type` (≤15 chars) — baseline now uses the same term as stage snapshot. `emotional_reaction_map.emotion` capped at 10 chars, `typical_actions` capped at 5 items. Rationale: reduce redundancy with runtime data flow (character evidence_refs never drove any simulation path), unify baseline-to-snapshot vocabulary, and converge arc summary into a single scannable string. → `schemas/character/stage_snapshot.schema.json`, `schemas/character/voice_rules.schema.json`, `schemas/character/behavior_rules.schema.json`, `automation/persona_extraction/consistency_checker.py`, `automation/prompt_templates/{character_snapshot_extraction,baseline_production}.md`.

## Memory System

28. Three-layer memory (`stage_snapshot` / `memory_timeline` / `scene_archive`). No separate dialogue corpus.
29. ID convention `{TYPE}-S{stage:03d}-{seq:02d}` for `M-` / `E-` / `SC-`. 3-digit stage ≤999, 2-digit seq ≤99 per stage. Stage encoded in ID; digest / archive entries carry no separate `stage_id` field. Story-time field = `time` across all three.
30. Simulating character A loads only scenes where A is in `characters_present` and A's own `memory_timeline`.
31. `stage_events` is world-public only (50–80 CJK chars, hard gate). Personal / internal items belong in character `memory_timeline`, never in world.
32. `world_event_digest.summary` = 1:1 copy of source `stage_events` (enforced at write time by prompt + repair agent). 5-level importance inferred by keyword; default significant.
33. `memory_digest.summary` = 1:1 copy of `digest_summary` (30–50 CJK chars, hard gate).
34. Character `stage_snapshot.stage_events` = this stage only (50–80 CJK chars, hard gate), not accumulated. Cross-stage history lives in `memory_timeline` + `memory_digest` + `world_event_digest`.
35. `fixed_relationships.json` (blood / lineage / faction) not stage-dependent. Phase 2.5 skeleton; later stages may correct. Runtime Tier 0.

## Retrieval

36. Two-level funnel: Level 1 jieba + vocab dict + FTS5 (<20ms, default); Level 2 embedding via LLM tool use (rare). Single SQLite — no separate vector DB.
37. Proactive context-state association: engine extracts location / recent events / emotion / conversation partner for jieba matching each turn — not just user input.
38. Vocab dict (work-level, jieba custom format) auto-generated from extraction output. `works/{work_id}/indexes/vocab_dict.txt` (committed).
39. Retrieval artifacts under `works/{work_id}/retrieval/` (not committed). Phase 4 intermediate `works/{work_id}/analysis/scene_splits/` must not be git-tracked (otherwise rollback `git checkout --` silently destroys them). `scene_archive.jsonl` fully regenerated on merge.
39a. Phase 4 chapter-level same-run retry — FAILED chapters requeue inside the same pass with `prior_error` injected. Budget `[phase4].max_retries_per_chapter` (default 2; total attempts = 1 + budget). Exhausted → ERROR, deferred to `--resume`. Circuit breaker only counts terminal-failed chapters.
     → `architecture.md` §Automated Extraction Pipeline → Phase 4.

## JSON Repair

40. LLM-produced JSON often has format errors (unescaped quotes,
    trailing commas, truncation) while content is intact. Three-level
    repair in Phase 0: L1 regex (0 token) → L2 LLM on broken JSON only
    (minimal) → L3 full re-run (last resort).
    → `automation/persona_extraction/json_repair.py`.

## Configuration & Runtime Resilience

45. Single-source TOML config at `automation/config.toml` (loader
    `automation/persona_extraction/config.py`). Override priority:
    CLI > `config.local.toml` > `config.toml` > dataclass defaults.
    Sections: `stage / phase0 / phase1 / phase3 / phase4 / repair_agent
    / backoff / rate_limit / runtime / logging / git`.
46. Token-limit auto-pause (subscription model, §11.13) — `RateLimitController` parses DST-aware reset, writes flock-merged `rate_limit_pause.json`, blocks pre-launch + every `run_with_retry`, re-runs failed prompt after reset without consuming a retry slot. Unparseable resets → probe loop (single elected leader). Hard-stops (weekly ≥ `weekly_max_wait_h` default 12h; probe ≥ `probe_max_wait_h` default 6h) → exit 2 + `rate_limit_exit.log`. Pause excluded from `--max-runtime` (deduped by `resume_at`). → `docs/requirements.md` §11.13 + `automation/persona_extraction/rate_limit.py`.

## Repository

41. No novels / databases / indexes / large artifacts / real user packages in git.
42. `works/*/analysis/` + `works/*/indexes/` tracked as canonical; `works/*/retrieval/` local-only.
43. `docs/logs/` + `docs/review_reports/` write-mostly — do not proactively read.
44. `prompts/` = manual scenarios only (ingest / review / supplement / cold start). Extraction prompts in `automation/prompt_templates/`; runtime rules in `simulation/prompt_templates/`. Self-contained modules.
47. `/go` git flow is contract-driven: **zero mid-flow questions, exactly one question at the very end**. When not starting on master-clean, `/go` auto-opens `../<repo>-master` as a `git worktree`, does all edits + commit there, then `git worktree remove --force` post-commit. Main checkout never moves during Steps 1–8 — in-flight extraction / dirty work is preserved. Step 9 merges master into each non-master branch; only after every branch is synced and HEAD != master does `/go` ask "checkout master?" once. Rationale: the old flow asked N+1 times (commit time + after each branch merge), violating the "one decision per run" principle. → `.claude/commands/go.md` Step 0 / 8 / 9.
