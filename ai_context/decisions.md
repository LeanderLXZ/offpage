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
10a. `chapter_id` = `^C[0-9]{4}$` (4-digit), `volume_id` = `^V[0-9]{3}$` (3-digit, light_novel sources only). Width split = expected cardinality (chapters per work ≤ 9999, volumes ≤ 999); letter prefix aligns with the `S###` / `M-S###-##` ID family. `chapter_index.schema.json` `items` is `oneOf` over **monolithic** profile (single-volume non-structured works — forbids the 6 light_novel-only fields) and **light_novel** profile (multi-volume structured works — required `volume_id` + `volume_seq` + `original_chapter_seq` + `original_sub_chapter_seq` triple-layer seq, optional `volume_title` + `original_chapter_title`). Profile is dispatched by `manifest.structure_mode`. **No standalone `volume_index.json`** — `chapter_index` carries the cross-product. Each `C####` is one ingestion unit (sub-section in light_novel; chapter in monolithic). **Phase 0 / 1 / 3 / 4 schemas + prompts + code consume `C####` end-to-end** (`chapter_summary_chunk.chapter`, `stage_plan.chapters` as `C####-C####`; light_novel uses degenerate range `C####-C####` with start == end so phase 2/3/4 consumers parse it identically); `automation/persona_extraction/{prompt_builder,scene_archive}.py` build paths and chapter→stage mappings with the `C` prefix. Volume / original-chapter display info lives on `chapter_index` profile-B fields and is surfaced via the derived `title`, not on `stage_plan.chapters`. Identifier rename audits use the 4-form checklist in `conventions.md` §Cross-File Alignment.
    → `conventions.md` §Naming + §Cross-File Alignment, `schemas/work/chapter_index.schema.json`, `schemas/analysis/{chapter_summary_chunk,stage_plan}.schema.json`.

## Character Depth

11a. `identity.json` carries `core_wounds` (root traumas + behavioral impact) + `key_relationships` (relationship arcs with initial state / evolution / turning points). Loaded with the stage snapshot. **Character-level constant file alongside `target_baseline.json` (#13)** — voice / behavior / boundary / failure_modes are inlined into stage_snapshot (#11d).
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
    普通} + `relationship_type` Chinese short token, **flexible string
    (no enum gate)**, 14 default candidates 至亲 / 恋人 / 挚友 / 师长 /
    弟子 / 朋友 / 同僚 / 主人 / 下属 / 宠物 / 武器 / 对手 / 敌人 / 路人,
    fallback to a more precise out-of-list term allowed when none of the
    14 fits — must explain the divergence in `description`; `tier` and
    `relationship_type` are orthogonal axes — tier 普通 ≠ relationship
    路人) + ≤100-char description. `targets` array capacity is bounded
    by `schemas/character/targets_cap.schema.json` (single-source $ref;
    downstream stage_snapshot.{target_voice_map, target_behavior_map,
    relationships} share the same fragment so adjusting the cap touches
    one file only). The baseline is immutable from phase 3 onward.
    **Phase 3 hard constraint (bidirectional)**: the three structures
    `stage_snapshot.{voice_state.target_voice_map,
    behavior_state.target_behavior_map, relationships}` MUST have keys
    **set-equal** to `target_baseline.targets[].target_character_id` —
    missing or extra both hard fail. All three structures key by
    `target_character_id` (voice_map / behavior_map moved from prior
    `target_type` keying; `target_type` retained as sibling metadata).
    Tri-state encoded in **content emptiness**, not in key presence:
    appeared (cumulative) → key present, fields filled normally; seen
    before but not in this stage → key present, inherits prev; never
    appeared → key present, fields empty. **fixed_relationship
    exception**: a `relationships[]` entry whose target is bound by a
    `world/foundation/fixed_relationships.json` entry may pre-fill the
    relationship fields even when the target has never appeared (other
    structures like voice_map / behavior_map still empty). Validation
    runs at the **phase 3 single-stage validate layer** (peer of
    schema validate); violations route into the file-level repair
    lifecycle (L1 json_repair → L2 repair_agent cross-file checker
    `targets_keys_eq_baseline` → L3 re-extract). Phase 3.5
    `consistency_checker.py` no longer carries this rule. No escape
    hatch; if phase 2 misses a target, fix the baseline by hand and
    re-run the affected stages. Phase 3
    does 1+2N split extraction per stage (1 world + N char_snapshot +
    N char_support); any stage may correct identity (via char_support)
    but **never** writes to target_baseline.
14. No per-stage report files; progress in-place.
15. `target_voice_map` / `target_behavior_map` entries all key by
    `target_character_id` (set-equal to `baseline.targets[].target_character_id`,
    see #13); detail level varies by `tier` — 核心 / 重要 targets get
    ≥3–5 examples, 次要 / 普通 targets stay terse, never-appeared
    baseline targets keep empty entries (D4 state 3) so the cross-file
    set-equality holds. Runtime loads only entries matching user role:
    canon role → exact match on `target_character_id`; OC role →
    fallback match via the entry's `target_type` sibling label
    (preserved as metadata) per role_binding affinity. If no matching
    entry in the current snapshot, backward scan previous snapshots
    (pure code I/O).
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
24. Extraction prompts do NOT read `memory_digest.jsonl`, `world_event_digest.jsonl`, or `stage_catalog.json`. Self-contained snapshot contract embedded in prompt; digests / catalog are programmatically maintained by `post_processing.py` (0 token, idempotent).
25. Per-stage quality gate = `repair_agent` (unified check + fix + verify). Checkers L0–L3 × fixers T0–T3, orthogonal; field-level json_path patches. Phase B L3 gate catches false "fixed" claims. Per file at most `max_lifecycles_per_file=2` complete check→fix→verify lifecycles: lifecycle 1 may invoke T3 (with `prior_attempt_context` summarising what the previous lifecycle fixed and what still failed); the moment T3 fires the lifecycle returns and the state machine resets into lifecycle 2; lifecycle 2 disables T3 — any escalation that would call T3 ends with `T3_EXHAUSTED`. Phase 3 dispatches per file in parallel (default concurrency 10); cross-file consistency lives in Phase 3.5. → `automation/repair_agent/` + `docs/requirements.md` §11.4.
25a. Source-discrepancy triage (`triage_enabled=True`) — two accept paths share `accept_cap_per_file=5` per lifecycle: (A) L3 `source_inherent` (LLM) accepts author-bug residuals with verbatim-quote evidence (literal substring + SHA-256 anchored); (B) L2 `coverage_shortage` (0 token) accepts `min_examples` shortages after one T2 attempt via program-chosen SourceNote. Both persist to `{entity}/canon/extraction_notes/{stage_id}.jsonl` (or `world/extraction_notes/`) append-only. Runtime does NOT consume (audit-only). Phase 3.5 treats valid SourceNote as equivalent to meeting `min_examples`. Lifecycle 2 reads back already-accepted fingerprints from disk so the same issue is never written twice. T3 output flows directly into lifecycle 2 — no immediate post-T3 corruption gate. → `automation/repair_agent/` + `docs/requirements.md` §11.4.
26. Extraction runs on `extraction/{work_id}` branch. Each passing stage committed. Rollback = `git reset`. **Squash-merge to `library` on completion** (never to `main`). Three-branch model: `main` = framework only, pushed to remote; `extraction/{work_id}` = per-work in-progress, local; `library` = completed-works archive, local. `library` absorbs framework updates via periodic `git merge main`; nothing flows back to main, keeping the public-facing branch artefact-free. Squash target controlled by `[git].squash_merge_target` (default `library`). **After a successful squash the orchestrator interactively offers (`[y/N]`, default N) to delete the source `extraction/{work_id}` branch (`git branch -D`) and run `git gc --prune=now`** so accumulated regen commits become unreachable and are reclaimed. Dispose is always interactive — even when `[git].auto_squash_merge=true` the dispose prompt still asks, because branch deletion is irreversible. Once the user opts in, the `library` squash is the only retained record. This makes `extraction/{work_id}` a disposable scratchpad: failed regens may be committed freely without polluting `library` history or long-term disk usage.
26a. Branch discipline enforced via orchestrator `try/finally: checkout_main(...)` + SessionStart hook (`.claude/hooks/session_branch_check.sh`). No PreToolUse commit wrapper. **The outer `try` block in `run_full` covers all five phases (0 / 1 / 1.5 / 2 / 3+)** — `create_extraction_branch` runs **before** the first `run_summarization()` call, so even Phase 0 chunk summaries / Phase 1 analysis fan-out / Phase 1.5 confirmation + manifest write happen on the extraction branch (not just Phase 2 baseline + Phase 3 stage loop). `pipeline.extraction_branch` is filled at run_full entry (`f"{prefix}{work_id}"`) — load-from-disk pipelines with empty value are auto-patched, fresh pipelines are constructed with the value pre-filled. The inner `try` in `run_extraction_loop` (resume path with phase 1.5 done) keeps the same invariant. → `architecture.md` §Git Branch Model + `orchestrator.py::run_full`.
27. Orchestrator pre-computes per-call read list (latest snapshot + memory_timeline only). Agents don't explore freely.
27a. Manifests split by writer: `sources/*/manifest.json` hand-written (validator-gated); `works/*/manifest.json` + `works/*/world/manifest.json` programmatic. Live phase state in `analysis/progress/`, not manifests.
27b. **Bounds-only-in-schema.** All `maxLength` / `minLength` / `maxItems` live in `schemas/**.schema.json` exclusively — no duplicates in `config.toml`, L2, docs, ai_context, or prompts. L2 keeps only checks schema can't express. Single program fallback (`StructuralChecker.relationship_history_summary_max_chars`) must track `stage_snapshot.schema.json`. Cross-schema sharing of a single bound number is done by `$ref` to a shared fragment, located in the directory of the domain that uses it (e.g. `schemas/character/targets_cap.schema.json` is shared by `target_baseline.targets` + stage_snapshot's three target structures — both files live in `schemas/character/`, so the fragment goes there). The inlining loader at `automation/persona_extraction/schema_loader.py` resolves these at load time so any draft validator sees a self-contained schema (all current call sites — orchestrator, validator, scene_archive, repair_agent — use `Draft202012Validator` to match `$schema: draft/2020-12/schema` in the schema files). This is **not** a duplicate — still single-source.
27c. No schema (world / character baselines / `stage_snapshot` / `memory_timeline`) carries `evidence_refs` / `source_type` / `scene_refs`. Chapter back-tracing lives outside the schemas; runtime anchoring uses `timeline_anchor` (+ `location_anchor` on world) and `memory_timeline`.
27d. Digest + memory time-location: required short anchors copied from world snapshot's `timeline_anchor` / `location_anchor`. `memory_timeline.scene_refs` removed (FTS5 on `scene_archive`).
27e. `foundation` / `fixed_relationships` / `stage_catalog` bound-collapsed. `fixed_relationships.{source_type,evidence_refs}` removed; `stage_catalog.order` removed (lex sort by `stage_id`); character catalog at `schemas/character/stage_catalog.schema.json`; placeholder `*_summary` fields deleted.
27f. Character `stage_snapshot` full-body bound-collapsed: required `timeline_anchor` + `snapshot_summary` added; `boundary_state.hard_boundaries` added (peer of baseline).
27g. `stage_snapshot` structural prunes: `character_arc` is a short string (was object); top-level `memory_refs` / `evidence_refs` removed; per-item `evidence_ref` removed from every `dialogue_examples` / `action_examples`.
27h. `world_stage_snapshot` structural prunes: `character_status_changes` removed (per-character status changes belong on character `stage_snapshot` / `memory_timeline`; world snapshot keeps only the public-world layer); `evidence_refs` removed (no schema keeps chapter anchors). Field-level `maxItems` / `maxLength` tightened in schema; `stage_events` widened from 50–80 to 50–100 CJK chars.
27i. **schema-gate-as-retry-trigger pattern.** L1 `jsonschema` validation acts as another retry trigger for LLM output failure (peer with JSON-parse failure, stage-limit violation, etc.); the first failure is injected into the next retry's prompt: Phase 0 / Phase 1 / Phase 4 via `{retry_note}` placeholder + `prior_error` argument (Phase 1 fan-outs the pattern across 3 independent lanes, each with its own retry budget — see #52). Covers 5 schemas: `schemas/analysis/{chapter_summary_chunk,scene_split,world_overview,stage_plan,candidate_characters}.schema.json`. Plumbing → `automation/persona_extraction/orchestrator.py:_summarize_chunk + run_analysis`, `scene_archive.py:validate_scene_split`, `prompt_builder.py:build_summarization_prompt(prior_error) + build_scene_split_prompt(prior_error) + build_world_overview_prompt(prior_error) + build_stage_plan_prompt(prior_error) + build_candidate_characters_prompt(prior_error)`. Pairs with #27b (Bounds-only-in-schema): bounds defined in schema, enforcement applied in the pipeline through the existing retry path.
27j. **Phase 0/1 dual-mode dispatch via `structure_mode`.** Source manifest
     carries `structure_mode: "monolithic" | "light_novel"` (**required** —
     schema `required` in both `work_manifest` / `works_manifest`, missing
     value fails schema gate; no implicit default-fill); works manifest
     copies it at Phase 1.5. Source
     manifest is the single source of truth — `automation/ingestion/
     validator.py` cross-checks `structure_mode` against the
     `chapter_index` profile (see #27k); `manifests.write_works_manifest`
     copies the value forward and asserts equality. **`monolithic`** =
     existing token-budget chunking (Phase 0) + LLM stage-boundary
     discovery (Phase 1). **`light_novel`** = `1 sub-section = 1 C-id =
     1 Phase 0 chunk = 1 Phase 1 stage`; Phase 0 sets
     `chunks = [[c] for c in chapter_index]` and skips token-budget
     batching; Phase 1 derives `stage_plan` 1:1 from `chapter_index`
     (no boundary-discovery LLM call) and bypasses STAGE_MIN /
     STAGE_MAX `chapter_count` validation. Phase 2+ does NOT branch —
     consumes `stage_plan` uniformly; volume / printed-chapter
     semantics ride on `chapter_index` profile-B fields, character /
     world schemas untouched. **Identification of `structure_mode`** is
     LLM-driven inside the normalization prompt (`prompts/ingestion/
     原始资料规范化.md` task step 2): scan source TOC / filenames /
     volume markers + chapter sample, emit `判定 + 依据 + 置信度`,
     then gate — confidence ≥ 0.8 fills `manifest.structure_mode`
     directly; < 0.8 stops and asks the user; any signal flagged
     "不确定" caps confidence at 0.7 (forcing the human-confirm path).
     `light_novel` requires all three signals (volume separators +
     volume count ≥ 2 + identifiable in-chapter sub-sections) — the
     single-volume case falls back to `monolithic`.
     → `schemas/work/{work_manifest,works_manifest,chapter_index}.schema.json`
     (both source-side `work_manifest` and canon-side `works_manifest`
     declare the field; canon copy by `manifests.write_works_manifest`),
     `automation/ingestion/validator.py`, `automation/persona_extraction/
     {manifests,orchestrator}.py`.
27k. **`chapter_index.schema.json` `items` = `oneOf` two profiles.**
     **monolithic profile**: `additionalProperties: false`, forbids
     `volume_id` / `volume_title` / `volume_seq` /
     `original_chapter_seq` / `original_sub_chapter_seq` /
     `original_chapter_title`. **light_novel profile**: required
     three-layer seq triple `volume_id` (`^V[0-9]{3}$`) + `volume_seq`
     (≥1) + `original_chapter_seq` (≥1) + `original_sub_chapter_seq`
     (≥1), optional `volume_title` + `original_chapter_title`. The
     three layers map: `volume_seq` = 1-based volume index in book;
     `original_chapter_seq` = 1-based original printed chapter index
     within volume (resets per volume); `original_sub_chapter_seq` =
     1-based sub-section index within original printed chapter (resets
     per original chapter). `title` always required (minLength 1)
     regardless of profile; `chapter_id` (`^C[0-9]{4}$`) / `sequence`
     / `normalized_path` required across both. Downstream Phase 0 /
     3 / 4 consume `chapter_id` only — `stage_plan.chapters` stays
     `C####-C####` in both modes (light_novel uses a degenerate range
     `C####-C####` with start == end so existing parsers work
     unchanged); volume / original-chapter display info rides on
     `chapter_index` profile-B fields and surfaces via the derived
     `title`.
     → `schemas/work/chapter_index.schema.json`, `prompts/ingestion/
     原始资料规范化.md`.
27l. **`title` derived by normalization for `light_novel`.** Formula:
     `f"{volume_title or '第N卷'} {original_chapter_title or '第M章'}
     {original_sub_chapter_seq}"` where `N = volume_seq`,
     `M = original_chapter_seq`. Optional fields with placeholder
     fallbacks ensure `title` (schema-required, minLength 1) is always
     fillable purely from required fields. Example: `volume_seq=1`,
     `volume_title=None`, `original_chapter_seq=2`,
     `original_chapter_title=None`, `original_sub_chapter_seq=3` →
     `title = "第1卷 第2章 3"`. Rule lives in normalization (prompt +
     downstream eventual code path), not in extraction code, so Phase
     1 / Phase 3 consumers see a populated `title` field. Monolithic
     mode: `title` continues to be the human-readable chapter title
     copied from source ToC. **Code-side soft-truncation safeguard**:
     `_build_light_novel_stage_plan` truncates the resulting
     `stage_title` to the schema cap (read dynamically at startup from
     `stage_plan.schema.json::stages.items.properties.stage_title.maxLength`
     via `_stage_title_max_length()`, preserving §27b single-source) with
     `…` ellipsis when the formula's full output would exceed the cap,
     so adversarial long volume_title × original_chapter_title
     combinations cannot trip an infinite Phase 1 retry loop on
     `stage_title.maxLength` schema fail.
     → `schemas/work/chapter_index.schema.json`, `schemas/analysis/
     stage_plan.schema.json` (`stage_title.maxLength`), `prompts/
     ingestion/原始资料规范化.md`, `automation/persona_extraction/
     orchestrator.py::_build_light_novel_stage_plan`.
27m. **Chunk-level secondary fields on `chapter_summary_chunk`.** Phase 0
     chunk schema carries five chunk-level secondary fields aggregating
     the world / power / faction / region / arc signals across each
     chunk, in addition to the per-summary event facts: `chunk_arc_summary`
     (required, ≤200 chars), `chunk_world_rules[]` (maxItems 5, items
     `{rule, description, observed_impact}`, `required: [rule]`),
     `chunk_power_levels[]` (maxItems 20, items `{name, description}`,
     `required: [name]`), `chunk_factions[]` (maxItems 20, items
     `{name, description, members_present[]}` with `members_present`
     storing **raw** chunk-LLM-visible names — alias / true name / form
     of address — not `character_id` since identity merge is post-Phase
     1.5; `required: [name]`), `chunk_regions[]` (maxItems 20, items
     `{name, description}`, `required: [name]`). All sub-objects
     `additionalProperties: false`. Per-summary side: `location` removed
     (covered by `chunk_regions`); `summary` 150–200 CJK chars (must fit
     event description + setting context); `key_events` removed (no Phase 1
     lane projects it after #52 fan-out, Phase 2 baseline does not read
     it — stage boundary signal now comes from per-summary `summary`
     widening + chunk-level `chunk_arc_summary`). `chunk_world_rules.observed_impact` is required-by-prompt
     to fall back to the literal string "未在本 chunk 直接观察" rather
     than silently empty, so Phase 2 LLM has a local anchor when
     synthesising `foundation.core_rules.impact`. Phase 1 mapping:
     `chunk_world_rules → core_rules` / `chunk_power_levels →
     power_system.levels` / `chunk_factions → major_factions` /
     `chunk_regions → world_structure.major_regions` /
     `chunk_arc_summary → world_lines.core_conflict`. Phase 2
     `baseline_production.md` reads the chunk-level fields directly
     (no longer reasoning purely from per-summary natural language).
     Explicitly **NOT added**: `chunk_fixed_relationships[]` (chunk
     view ≤25 chapters cannot judge "spans entire book", would
     contaminate `world/foundation/fixed_relationships.json`);
     `chunk_setting_features` (overlaps `chunk_world_rules` /
     `chunk_power_levels` / `chunk_factions` / `chunk_regions` —
     `world_structure.summary` / `world_lines.setting_features` are
     synthesised by Phase 1 LLM from those four fields). `members_present`
     intentionally **not** mapped 1:1 to `foundation.major_factions.key_figures`
     — Phase 1.5 cross-chunk identity merge maps the raw names to
     `character_id` first.
     → `schemas/analysis/chapter_summary_chunk.schema.json`,
     `automation/prompt_templates/{summarization,analysis_world_overview,baseline_production}.md`,
     `docs/architecture/{extraction_workflow,schema_reference}.md`.
27m. **stage_plan 切分语义 = 拐点先行，章数硬范围；prompt 反锚定 +
     `default_stage_size` 字段下线。** 旧设计在 `analysis.md` §步骤 2 +
     JSON 示例 + schema 字段三处同时锚定 "10 章"，LLM 实际产出落入
     "先按 10 章等分、再给每段挑剧情节点写 boundary_reason" 的偷懒
     模式（实证：537 章 / 53 stage 中前 38 个全是恰好 10 章）。新设计：
     (1) 程序式三子步流程——2.1 通览 chunk 输出列出全书所有剧情拐点
     候选（章号 + 类型 + 一句话事件）；2.2 沿章序把相邻拐点合并成
     stage（章数 5-15 hard，由 `chapter_count.minimum/maximum` schema
     强制 + orchestrator `_check_stage_plan_limits` 兜底 5-15
     monolithic）；2.3 反锚定自检（≥3 连等章数视为机械等分必须重审 +
     `boundary_reason` 必须对应 2.1 拐点章号）。(2) JSON 示例改为非
     整数倍混合（8 章 + 13 章），打破 "10 是甜区" 暗示。(3) schema
     字段 `default_stage_size` 整体删除——单一真源 = `chapter_count`
     bounds；连带删 `Phase3Progress.stage_size` dead metadata 字段
     与 orchestrator 三处读写位、`work_manifest.schema.json::extraction.default_stage_size`
     孤立字段。Plumbing → `schemas/analysis/stage_plan.schema.json`、
     `schemas/work/work_manifest.schema.json`、
     `automation/prompt_templates/analysis_stage_plan.md` §步骤 2（步骤 2.1/2.2/2.3 三子步反锚定自检；详见 #52 Phase 1 三 lane 拆分）、
     `automation/persona_extraction/{orchestrator,progress}.py`、
     `docs/architecture/schema_reference.md`。

## Memory System

28. Three-layer memory (`stage_snapshot` / `memory_timeline` / `scene_archive`). No separate dialogue corpus.
29. ID convention `{TYPE}-S{stage:03d}-{seq:02d}` for `M-` / `E-` / `SC-`. 3-digit stage ≤999, 2-digit seq ≤99 per stage. Stage encoded in ID. **Digest entries** (`memory_digest.jsonl` / `world_event_digest.jsonl`) carry no separate `stage_id` field — the stage is parsed from the ID prefix. **`scene_archive` entries DO carry `stage_id`** (sourced from `stage_plan.json`, see §11.x scene_archive 段) alongside the stage-coded `scene_id`, since runtime retrieval indexes by stage and re-parsing on every query is wasteful. Story-time field = `time` across all three.
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
47. Phase 0 summarize subprocess timeout = `[phase0].summarize_timeout_s` (default 1800s), not the historical borrow of `[phase3].review_timeout_s` (600s). Reason: a Phase 0 chunk reads `chunk_size` chapters (default 20) and produces N× per-summary (100–150 chars) + 5 chunk-level secondary aggregates (`chunk_arc_summary` / `chunk_world_rules` / `chunk_power_levels` / `chunk_factions` / `chunk_regions`) under opus-4-7 effort=max; runtime evidence shows wall > 600s is normal. `phase3.review_timeout_s` stays 600s for the phase 3 reviewer short-chain it actually serves. → `automation/config.toml` `[phase0]`, `automation/persona_extraction/config.py::Phase0Config`, `automation/persona_extraction/orchestrator.py:_summarize_chunk`.
48. **Length-bound tolerance gate (B 方案).** When an LLM-driven phase has exhausted its strict retry budget (Phase 0 L1+L2+L3, Phase 1 `exit_validation_max_retry`, Phase 2 baseline retry, Phase 4 scene-split `max_retries`, Phase 2/3/3.5/4 via repair_agent T3_EXHAUSTED), a final pass calls `validator.validate_with_length_tolerance` (helper at `automation/persona_extraction/validator.py`): if the strict failure list contains **only** `minLength`/`maxLength` violations and a relaxed schema (each `minLength` × 0.9 floor, each `maxLength` × 1.1 ceil) passes, accept the artifact as PASS; otherwise keep the original failure. All other constraints (`required` / `type` / `enum` / `pattern` / `minimum` / `maximum` / `minItems` / `maxItems`) stay strict. **Not applied** to `post_processing.py` program-only digest/catalog outputs — those have no LLM-edge thrash and would mask code bugs. **No metadata marker** on tolerance-accepted artifacts (downstream consumers don't distinguish strict-pass vs tolerance-pass). Pairs with #27i (schema-gate-as-retry-trigger): strict-retry path runs to exhaustion first; tolerance is a final safety valve, not a substitute for retry. Pairs with global `[phase3].max_turns = 80` (was 50) and `--chunk-size` default `20` (was 25) — both reduce the rate at which boundary thrash hits exhaustion. Plumbing → `automation/persona_extraction/validator.py` (helpers), `orchestrator.py:_summarize_chunk + run_analysis + run_baseline_production`, `scene_archive.py:_handle_validation_failure`, `automation/repair_agent/coordinator.py` (T3_EXHAUSTED terminal-state branch).
49. **Phase 0 recovery sweep with downgraded effort (per-chunk targeted救火).** opus-4-7 effort=max on phase 0's多字段 chunk synthesis (read `chunk_size` chapters → write N× per-summary + 5 chunk-level secondary aggregates) stochastically triggers extended server-side thinking that exceeds the 1800s subprocess wall budget. Empirically observed on `<work_id>` chunks 8 across two distinct chapter ranges (v2: C0176-C0200, v3: C0141-C0160) — both timed out with effort=max ×2 retries, both completed in ~14 min wall with effort=high (schema-valid output, equivalent quality). Rather than blanket-downgrade phase 0 to effort=high (which would slightly lower quality on the 95%+ chunks that don't trigger the long-thinking edge case), the orchestrator runs a **recovery sweep** after the main phase 0 ThreadPool finishes: any chunk whose `state == 'failed'` AND `error_message` contains `'timed out'` OR `'error_max_turns'` AND `recovery_attempted == False` is rerun once with `effort='high'` (per-call kwarg via `LLMBackend.run`, no backend instance swap), reusing `phase0.concurrency` (ThreadPoolExecutor max_workers). Outcome marks `recovery_attempted=True` regardless; subsequent `--resume` skips already-attempted chunks (no infinite救火 loop). The full retry pipeline (L1/L2/L3 JSON repair + jsonschema gate + length-bound tolerance #48) runs inside `_summarize_chunk` per the existing contract — sweep just changes effort, not retry semantics. Plumbing → `automation/persona_extraction/llm_backend.py::LLMBackend.run` (new `effort: str | None = None` kwarg), `orchestrator.py::_run_recovery_sweep` (new method, called from `run_summarization` post-main-pool), `progress.py::ChunkEntry` (new `recovery_attempted: bool = False`), `config.py::Phase0Config.recovery_effort` + `automation/config.toml [phase0] recovery_effort`.
50. **Post-processing 对 derived digests 永远走 replace-slice 语义。** `generate_memory_digest` 与 `generate_world_event_digest` 把当前 stage 的派生条目写入 `memory_digest.jsonl` / `world_event_digest.jsonl`：当前 stage 旧条目被新条目替换，其它 stage 条目保留。**当前 stage 派生数组为空（`memory_timeline` 0 条 / `stage_events` 0 条 — schema 合法）也必须落盘 replace-slice**——读 existing → drop `_stage_from_id(...) == current_stage_num` 的旧条目 → write 剩余条目。否则 repair 删空一个 stage 的源数组、再跑 post-processing 时旧 digest slice 留在 JSONL 里，与 #32 / #33 的 1:1 拷贝契约 + Phase 3.5 #27i schema-gate 一致性检查（见 `consistency_checker._check_memory_id_correspondence` / `_check_world_event_digest`）撞车。空源数组仍 emit warning issue 让 caller 收（信息提示，方便人工核查"这阶段是不是真的没事件"），但实际 IO 必须发生。Plumbing → `automation/persona_extraction/post_processing.py::generate_memory_digest` + `generate_world_event_digest`。
51. **CLI `--resume` 阶段无关续跑契约。** `automation/persona_extraction/cli.py` 的 `--resume` 是 `run_full` 的 auto-yes 信号——`run_full` 是 resume entry point，按 phase 顺序自检 + skip + self-heal（Phase 0 schema-gated chunk skip / Phase 1 产物存在则跳过 / Phase 1.5 用 `--characters` 旁路 / Phase 3 reconcile_with_disk + 从 `stage_plan.json` rebuild `phase3_stages.json`）。`--resume` 标志只 silent run_full 内 `input("Resume from existing progress? [Y/n]: ")` 这条交互确认；与磁盘上具体哪个 phase 已落盘无关。`--background` 与 `--resume` 正交：`--background` 校验阶段感知双分支，读 `pipeline.json::phases.phase_1_5`——未 done 则强制要求 `--characters`（避免 daemon 撞 `confirm_with_user` 的 stdin 死锁）；已 done 则强制要求 `--resume` 或 `--characters` 二选一（避免 daemon 撞 run_full 内 `'Resume from existing progress?'` 的 stdin 死锁）。两分支共同保证 daemon 路径上**没有任何**可触发的 stdin prompt。Plumbing → `automation/persona_extraction/cli.py`（无条件走 run_full + 加 `_load_pipeline_status` helper + 阶段感知双分支 background 校验）+ `automation/persona_extraction/orchestrator.py::run_full(auto_resume: bool = False)` + `automation/persona_extraction/_smoke_cli_resume_background_validation.py`（6 场景：phase_1_5 done/pending × {--resume, --characters, 都无} 的 background 校验真值表）。

52. **Phase 1 三 lane 并行 + 字段裁剪 + light_novel stage_plan 跳过 LLM。** 旧设计单次 `claude -p` 串行产出 `world_overview.json` / `stage_plan.json` / `candidate_characters.json` 三件，schema gate 失败时整 lane 重跑且共享一个 `[phase1].exit_validation_max_retry` 池——实证 537 章 monolithic 单 LLM 调用 26min 仍未落盘，wall time 是后续 phase 启动前的硬瓶颈。新设计把 phase 1 内部拆成独立 lane：(1) **monolithic 模式 = 3 lane 并行**（world_overview / stage_plan / candidate_characters，每 lane 独立 prompt template + 独立裁剪 chunks 输入 + 独立 schema gate）；**light_novel 模式 = 2 lane 并行**（world_overview + candidate_characters）+ orchestrator 程序化 `_build_light_novel_stage_plan()` 直接落盘（zero LLM call，stage_plan lane 整体跳过 LLM）。(2) **字段裁剪**：每 lane 只接收自己需要的 chunk 字段，预先 project 后写到 `works/{work_id}/analysis/.phase1_lane_inputs/{lane}/chunk_NNN.json` 并 `.gitignore` 屏蔽——world_overview lane = **仅** chunk-level 二级字段（`chunk_arc_summary` / `chunk_world_rules` / `chunk_power_levels` / `chunk_factions` 去 `members_present` / `chunk_regions`），**`summaries` 整段删除**（全书设定不依赖逐章锚点）；stage_plan lane = `chunk_arc_summary` + `chunk_regions` + per-summary `chapter` + `summary`（**`characters_present` / `emotional_tone` / `identity_notes` 删除**——拐点合并依据是 `chunk_arc_summary` chunk 弧光 + `summary` 事件描述，与身份 / 角色 / 情绪粒度正交，裁掉减 token + 减 LLM thinking 长尾；`key_events` 已从 chunk schema 整体删除，见 #53）；candidate_characters lane = per-summary `chapter` + `summary` + `characters_present` + `identity_notes` + `chunk_factions[].{name,members_present}`（**新增 `summary`**——跨 chunk 身份合并需要事件上下文判断隐含身份链，光看 `identity_notes` 短句不够）。(3) **per-lane retry = schema gate + correction_feedback（per-lane 独立预算）**：每 lane 完成抽取后落盘文件即跑 jsonschema gate（含 stage_plan lane 的 5–15 章 limit 检查）；首条违规作为 `prior_error` 注入下一次重试 prompt（与 phase 0 chunk-level / phase 4 chapter-level prior_error 注入同形态）。`[phase1].exit_validation_max_retry` 语义改为 per-lane 独立预算（不再共享池）。**不集成 `repair_agent.run`**——phase 1 输出是 chunk-level 派生的全书分析，不是 stage-anchored 源文抽取，repair_agent 的 SourceContext + T2 source_patch 假设 stage scoped chapter range 可读，对 phase 1 不成立。(4) **失败语义** = lane 隔离：单 lane fail 不影响其他 lane 已落盘产物，`--resume` 时 `reconcile_with_disk` 检测到 schema-valid 产物即跳过对应 lane 重跑（与 phase 0 chunk-level skip / phase 3 lane-level skip 同形态）。(5) **prompt template 三件套替换 `analysis.md`**：`analysis_world_overview.md` / `analysis_stage_plan.md`（含 #27m 步骤 2.1/2.2/2.3 反锚定自检三子步） / `analysis_candidate_characters.md`（含步骤 1.5 跨 chunk 身份合并）；旧 `analysis.md` 删除，no legacy fallback。(6) **tmpdir 清理**：run_analysis 在 `try/finally` 内 cleanup `.phase1_lane_inputs/`（成功 / 失败 / SIGTERM 均清）。Plumbing → `automation/prompt_templates/analysis_{world_overview,stage_plan,candidate_characters}.md`（新增三件）、`automation/persona_extraction/prompt_builder.py`（删除 `build_analysis_prompt`，新增 `build_world_overview_prompt` / `build_stage_plan_prompt` / `build_candidate_characters_prompt` + 三个 `_project_chunk_for_*` 内部裁剪函数 + `prepare_phase1_lane_inputs`）、`automation/persona_extraction/orchestrator.py::run_analysis`（fan-out 重写）、`automation/config.toml [phase1]` + `automation/persona_extraction/config.py::Phase1Config`（增 `lane_concurrency`，注释更新 `exit_validation_max_retry` per-lane 语义）、`.gitignore`（`works/*/analysis/.phase1_lane_inputs/`）。

53. **Analysis schema 收紧 v2 + Phase 1.5 推荐规则化。** 2026-05-08 跑完一次端到端 phase 0 + 1 + 1.5 + phase 2 部分（被 SIGTERM 中止），看实际产物决定收紧三组 analysis schema。(1) **chunk schema** — 删 `summaries.items.key_events`（经 #52 三 lane 投影后无消费方，Phase 2 baseline 也不读，是死字段）；`summaries.items.summary` 100-150 → 150-200 CJK chars（需要装下事件 + 设定上下文，原范围在实际产出里频繁触底）。决策 #27m 内描述同步修订（key_events 段删除、summary 长度更新）。(2) **candidate_characters schema** — 删 `candidates.items.recommended` boolean（LLM 自报推荐拍脑袋打 boolean，不可靠）；删 `candidates.items.aliases.items.first_appearance` 字符串（如"约第 0042 章"，无下游消费且不可程序检索）。Phase 1.5 默认勾选改为基于 `importance == "主角"` 程序判定（用户仍可手选追加 / 取消），`recommended` 字段在 candidate 级消失但 `RECOMMENDED` 标签字符串保留——展示逻辑改读 `importance`。(3) **world_overview schema** — `world_structure.major_regions.items` 由 `string` 升 `{name (≤15), description (≤30)}` 对象（对齐 `chunk_regions.items` 形态，Phase 2 baseline 直接读用，不再 mid-step 拼对象）；`power_system.levels.items` 同上对齐 `chunk_power_levels.items`；`core_rules.maxItems` 20→30（N chunk × ≤5 条原始规则去重后 30 比 20 合理），`items.maxLength` 100→150（保留字符串数组形态，强制 LLM 重新整理而非照搬 chunk 行）。Plumbing → `schemas/analysis/{chapter_summary_chunk,candidate_characters,world_overview}.schema.json`、`automation/prompt_templates/{summarization,analysis_world_overview,analysis_stage_plan,analysis_candidate_characters,baseline_production}.md`、`automation/persona_extraction/{prompt_builder,orchestrator}.py`、`docs/architecture/{schema_reference,extraction_workflow}.md`、`ai_context/{architecture,decisions}.md`（修订 #27m 描述 + 本条新增）。

## Repository

41. No novels / databases / indexes / large artifacts / real user packages in git.
42. `works/*/analysis/` + `works/*/indexes/` tracked as canonical; `works/*/retrieval/` local-only.
43. `logs/change_logs/` + `logs/review_reports/` write-mostly — do not proactively read.
44. `prompts/` = manual scenarios only (ingest / review / supplement / cold start). Extraction prompts in `automation/prompt_templates/`; runtime rules in `simulation/prompt_templates/`. Self-contained modules.
