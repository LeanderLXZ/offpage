<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `Character A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# Key Decisions — Compressed ADRs

One line decision + one line rationale + pointer to authoritative
source. Long discussion chains live in `logs/change_logs/`.

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

11a. `identity.json` carries `core_wounds` (root traumas + behavioral impact) + `key_relationships` (relationship arcs with initial state / evolution / turning points). Loaded with the stage snapshot. **Only character-level constant file** — voice / behavior / boundary / failure_modes are inlined into stage_snapshot (#11d).
11b. `behavior_state` separates `core_goals` (rational, re-prioritizable) from `obsessions` (irrational, trauma- / emotion-tied, not cost-benefit). `emotional_baseline` mirrors with `active_goals` + `active_obsessions`.
11c. `character_arc` in `stage_snapshot` = bird's-eye stage 1 → current. Complements `stage_delta` (last step only).
11d. **4-piece character baseline deprecated.** `voice_rules.json` /
     `behavior_rules.json` / `boundaries.json` / `failure_modes.json`
     removed. voice / behavior / boundary state already lived in
     `stage_snapshot.{voice_state,behavior_state,boundary_state}`;
     `failure_modes` is inlined as a new top-level field on `stage_snapshot`
     (4 sub-classes `common_failures` / `tone_traps` / `relationship_traps`
     / `knowledge_leaks`; sub-class maxItems carried over from the
     historical baseline schema). Each stage records the full active
     failure-mode set (carried-over + newly active; resolved drops out)
     so runtime reads only the current snapshot. S001 derives a baseline
     seed from source + identity; S002+ evolves from prev snapshot.
     `stage_delta` stays free-text (no structural changed/removed/added
     upgrade in this round). `identity` and `target_baseline` are the
     character-level constants (both produced in phase 2); runtime loads
     identity + target_baseline + current stage_snapshot.
11e. **maxItems-aware truncation rule (universal).** All extraction
     prompts must instruct the LLM to sort + truncate at the
     `maxItems` cap during extraction (rather than overflow + schema
     fail), with priority anchors: current-stage relevance →
     identity-anchor relation (core_wounds / key_relationships) →
     coverage breadth → cross-stage stability (for full-state evolving
     fields like `failure_modes`). Sub-classes count maxItems
     independently; no cross-field global cap. Spec → 
     `automation/prompt_templates/character_snapshot_extraction.md`
     §maxItems 触顶时的裁剪规则.
11f. **prev_stage four-state extraction rule.** Char snapshot prompt
     enforces four explicit states for handling prev_snapshot during
     extraction: (A) absent → inherit verbatim; (B) present + changed →
     rewrite from current source, note key changes in stage_delta;
     (C) present + unchanged → keep prev (must still fill required
     fields, "no change" ≠ "skip"); (D) resolved / revealed / overcome
     (for misunderstandings / concealments / failure_modes etc.) →
     drop the entry and write the resolution reason in stage_delta.
     Distinct from maxItems truncation: truncation is "no room"
     (not in stage_delta); resolution is "semantic closure" (must be
     in stage_delta). `stage_delta` stays free-text (per #11d) but is
     expected to capture (B) and (D); the "无明显变化" cop-out is
     explicitly forbidden. Spec →
     `automation/prompt_templates/character_snapshot_extraction.md`
     §核心规则 #2 (B/C/D 三态规则 + per-stage 推演原则).
     → `schemas/character/` + `docs/architecture/schema_reference.md`.

## Extraction Model

12. stage (extraction) = stage (runtime), 1:1. Natural story boundaries
    (target 10, min 5, max 15). Cumulative 1..N. `stage_id` = `S###`;
    sibling `stage_title` (short label; cap in schema).
13. Phase 2 produces world foundation + per-character `identity.json`
    + per-character `target_baseline.json` drafts from full-book context
    (no separate voice / behavior / boundary / failure_modes baseline
    files — those live inside `stage_snapshot`). `target_baseline.json`
    lists every target character (with `tier` ∈ {核心 / 重要 / 次要 /
    路人} + `relationship_type` enum + ≤100-char description) the
    subject character ever interacts with across the whole book; it is
    immutable from phase 3 onward. **Phase 3 hard constraint**: every
    `stage_snapshot.target_voice_map` / `target_behavior_map` /
    `relationships` key MUST be ⊆ `target_baseline.targets[].target_character_id`
    — violations are cross-file hard fail (no escape hatch; if phase 2
    misses a target, fix the baseline by hand and re-run the affected
    stages). Phase 3 does 1+2N split extraction per stage (1 world + N
    char_snapshot + N char_support); any stage may correct identity (via
    char_support) but **never** writes to target_baseline.
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
25. Per-stage quality gate = `repair_agent` (unified check + fix + verify). Checkers L0–L3 × fixers T0–T3, orthogonal; field-level json_path patches. Phase B L3 gate catches false "fixed" claims. Per file at most `max_lifecycles_per_file=2` complete check→fix→verify lifecycles: lifecycle 1 may invoke T3 (with `prior_attempt_context` summarising what the previous lifecycle fixed and what still failed); the moment T3 fires the lifecycle returns and the state machine resets into lifecycle 2; lifecycle 2 disables T3 — any escalation that would call T3 ends with `T3_EXHAUSTED`. Phase 3 dispatches per file in parallel (default concurrency 10); cross-file consistency lives in Phase 3.5. → `automation/repair_agent/` + `docs/requirements.md` §11.4.
25a. Source-discrepancy triage (`triage_enabled=True`) — two accept paths share `accept_cap_per_file=5` per lifecycle: (A) L3 `source_inherent` (LLM) accepts author-bug residuals with verbatim-quote evidence (literal substring + SHA-256 anchored); (B) L2 `coverage_shortage` (0 token) accepts `min_examples` shortages after one T2 attempt via program-chosen SourceNote. Both persist to `{entity}/canon/extraction_notes/{stage_id}.jsonl` (or `world/extraction_notes/`) append-only. Runtime does NOT consume (audit-only). Phase 3.5 treats valid SourceNote as equivalent to meeting `min_examples`. Lifecycle 2 reads back already-accepted fingerprints from disk so the same issue is never written twice. T3 output flows directly into lifecycle 2 — no immediate post-T3 corruption gate. → `automation/repair_agent/` + `docs/requirements.md` §11.4.
26. Extraction runs on `extraction/{work_id}` branch. Each passing stage committed. Rollback = `git reset`. **Squash-merge to `library` on completion** (never to `main`). Three-branch model: `main` = framework only, pushed to remote; `extraction/{work_id}` = per-work in-progress, local; `library` = completed-works archive, local. `library` absorbs framework updates via periodic `git merge main`; nothing flows back to main, keeping the public-facing branch artefact-free. Squash target controlled by `[git].squash_merge_target` (default `library`). **After a successful squash the orchestrator interactively offers (`[y/N]`, default N) to delete the source `extraction/{work_id}` branch (`git branch -D`) and run `git gc --prune=now`** so accumulated regen commits become unreachable and are reclaimed. Dispose is always interactive — even when `[git].auto_squash_merge=true` the dispose prompt still asks, because branch deletion is irreversible. Once the user opts in, the `library` squash is the only retained record. This makes `extraction/{work_id}` a disposable scratchpad: failed regens may be committed freely without polluting `library` history or long-term disk usage.
26a. Branch discipline enforced via orchestrator `try/finally: checkout_main(...)` + SessionStart hook (`.claude/hooks/session_branch_check.sh`). No PreToolUse commit wrapper. → `architecture.md` §Git Branch Model.
27. Orchestrator pre-computes per-call read list (latest snapshot + memory_timeline only). Agents don't explore freely.
27a. Manifests split by writer: `sources/*/manifest.json` hand-written (validator-gated); `works/*/manifest.json` + `works/*/world/manifest.json` programmatic. Live phase state in `analysis/progress/`, not manifests.
27b. **Bounds-only-in-schema.** All `maxLength` / `minLength` / `maxItems` live in `schemas/**.schema.json` exclusively — no duplicates in `config.toml`, L2, docs, ai_context, or prompts. L2 keeps only checks schema can't express. Single program fallback (`StructuralChecker.relationship_history_summary_max_chars`) must track `stage_snapshot.schema.json`.
27c. No schema (world / character baselines / `stage_snapshot` / `memory_timeline`) carries `evidence_refs` / `source_type` / `scene_refs`. Chapter back-tracing lives outside the schemas; runtime anchoring uses `timeline_anchor` (+ `location_anchor` on world) and `memory_timeline`.
27d. Digest + memory time-location: required short anchors copied from world snapshot's `timeline_anchor` / `location_anchor`. `memory_timeline.scene_refs` removed (FTS5 on `scene_archive`).
27e. `foundation` / `fixed_relationships` / `stage_catalog` bound-collapsed. `fixed_relationships.{source_type,evidence_refs}` removed; `stage_catalog.order` removed (lex sort by `stage_id`); character catalog at `schemas/character/stage_catalog.schema.json`; placeholder `*_summary` fields deleted.
27f. Character `stage_snapshot` full-body bound-collapsed: required `timeline_anchor` + `snapshot_summary` added; `boundary_state.hard_boundaries` added (peer of baseline).
27g. `stage_snapshot` structural prunes: `character_arc` is a short string (was object); top-level `memory_refs` / `evidence_refs` removed; per-item `evidence_ref` removed from every `dialogue_examples` / `action_examples`.
27h. `world_stage_snapshot` structural prunes: `character_status_changes` removed (per-character status changes belong on character `stage_snapshot` / `memory_timeline`; world snapshot keeps only the public-world layer); `evidence_refs` removed (no schema keeps chapter anchors). Field-level `maxItems` / `maxLength` tightened in schema; `stage_events` widened from 50–80 to 50–100 CJK chars.
27i. **schema-gate-as-retry-trigger pattern.** L1 `jsonschema` validation acts as another retry trigger for LLM output failure (peer with JSON-parse failure, stage-limit violation, etc.); the first failure is injected into the next retry's prompt: Phase 0 / Phase 4 via `{retry_note}` placeholder + `prior_error` argument; Phase 1 via `correction_feedback` code-side append (reusing the existing stage-limit retry channel, schema fails are merged into it). Covers 5 schemas: `schemas/analysis/{chapter_summary_chunk,scene_split,world_overview,stage_plan,candidate_characters}.schema.json`. Plumbing → `automation/persona_extraction/orchestrator.py:_summarize_chunk + run_analysis`, `scene_archive.py:validate_scene_split`, `prompt_builder.py:build_summarization_prompt(prior_error) + build_scene_split_prompt(prior_error) + build_analysis_prompt(correction_feedback)`. Pairs with #27b (Bounds-only-in-schema): bounds defined in schema, enforcement applied in the pipeline through the existing retry path.

## Memory System

28. Three-layer memory (`stage_snapshot` / `memory_timeline` / `scene_archive`). No separate dialogue corpus.
29. ID convention `{TYPE}-S{stage:03d}-{seq:02d}` for `M-` / `E-` / `SC-`. 3-digit stage ≤999, 2-digit seq ≤99 per stage. Stage encoded in ID; digest / archive entries carry no separate `stage_id` field. Story-time field = `time` across all three.
30. Simulating character A loads only scenes where A is in `characters_present` and A's own `memory_timeline`.
31. `stage_events` is world-public only (50–100 CJK chars, hard gate). Personal / internal items belong in character `memory_timeline`, never in world.
32. `world_event_digest.summary` = 1:1 copy of source `stage_events` (enforced at write time by prompt + repair agent). 5-level importance inferred by keyword; default significant.
33. `memory_digest.summary` = 1:1 copy of `digest_summary` (30–50 CJK chars, hard gate).
34. Character `stage_snapshot.stage_events` = this stage only (50–80 CJK chars, hard gate), not accumulated. Cross-stage history lives in `memory_timeline` + `memory_digest` + `world_event_digest`.
35. `fixed_relationships.json` (blood / lineage / faction) not stage-dependent. Phase 2 skeleton; later stages may correct. Runtime Tier 0.

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
43. `logs/change_logs/` + `logs/review_reports/` write-mostly — do not proactively read.
44. `prompts/` = manual scenarios only (ingest / review / supplement / cold start). Extraction prompts in `automation/prompt_templates/`; runtime rules in `simulation/prompt_templates/`. Self-contained modules.
47. `/go` git flow is contract-driven: **zero mid-flow questions, exactly one question at the very end**. When not starting on main-clean, `/go` auto-opens `../<repo>-main` as a `git worktree`, does all edits + commit there, then `git worktree remove --force` post-commit. Main checkout never moves during Steps 1–8 — in-flight extraction / dirty work is preserved. Step 9 merges main into each non-main branch; only after every branch is synced and HEAD != main does `/go` ask "checkout main?" once. Rationale: the old flow asked N+1 times (commit time + after each branch merge), violating the "one decision per run" principle. → `.claude/commands/go.md` Step 0 / 8 / 9.
