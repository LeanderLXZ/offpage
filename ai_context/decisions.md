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
11d. **Character voice / behavior / boundary / failure_modes inlined
     in stage_snapshot.** Voice / behavior / boundary state live in
     `stage_snapshot.{voice_state,behavior_state,boundary_state}`;
     `failure_modes` is a top-level field on `stage_snapshot`
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
    (target 10, min 8, max 15). Cumulative 1..N. `stage_id` = `S###`;
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
25. Per-stage quality gate = `repair_agent` (unified check + fix + verify). Checkers L0–L3 × fixers T0–T3, orthogonal; field-level json_path patches. Phase B L3 gate catches false "fixed" claims. Per file at most `max_lifecycles_per_file=2` complete check→fix→verify lifecycles: lifecycle 1 may invoke T3 (with `prior_attempt_context` summarising what the previous lifecycle fixed and what still failed); the moment T3 fires the lifecycle returns and the state machine resets into lifecycle 2; lifecycle 2 disables T3 — any escalation that would call T3 ends with `T3_EXHAUSTED`. **repair_agent 当前只接入 phase 3 stage loop**（`orchestrator.py::run_extraction_loop` 内唯一 `run_repair(...)` 调用点；phase 0 / 1 / 2 / 3.5 / 4 各自走原生 retry 路径，不经 repair_agent）。Phase 3 dispatches per file in parallel (default concurrency 10); cross-file consistency lives in Phase 3.5. **Disambiguation**：本条 L0–L3 × T0–T3 是 phase 3 stage 抽取产物的 per-file repair lifecycle（checker × fixer 二维矩阵 + Phase A→B→C lifecycle）；与 #40 (phase 0 JSON repair L1/L2/L3) 同名不同物——后者是 JSON 格式修复三档阶梯（L1 regex 0 token / L2 LLM 修破碎 JSON / L3 整 prompt full re-run），互不依赖。同字面 "L1/L2/L3" 在两处语义完全不同。 → `automation/repair_agent/` + `docs/requirements.md` §11.4.
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
27i. **schema-gate-as-retry-trigger pattern.** L1 `jsonschema` validation acts as another retry trigger for LLM output failure (peer with JSON-parse failure, stage-limit violation, etc.); the first failure is injected into the next retry's prompt: Phase 0 / Phase 1 / Phase 4 via `{retry_note}` placeholder + `prior_error` argument (Phase 1 fan-outs the pattern across 3 independent lanes, each with its own retry budget — see #52). Covers 5 schemas: `schemas/analysis/{chapter_summary_chunk,scene_split,stage_plan,candidate_characters}.schema.json` + `schemas/world/foundation.schema.json`（decision #54 — foundation 前移到 phase 1 后 schema 归位 `schemas/world/` 域；原 `schemas/analysis/world_overview.schema.json` 已删除）. Plumbing → `automation/persona_extraction/orchestrator.py:_summarize_chunk + run_analysis`, `scene_archive.py:validate_scene_split`, `prompt_builder.py:build_summarization_prompt(prior_error) + build_scene_split_prompt(prior_error) + build_foundation_prompt(prior_error) + build_stage_plan_prompt(prior_error) + build_candidate_characters_prompt(prior_error)`. Pairs with #27b (Bounds-only-in-schema): bounds defined in schema, enforcement applied in the pipeline through the existing retry path.
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
     than silently empty (历史 anchor，原服务 phase 2 foundation 产出
     时的 `core_rules.impact` 综合；foundation 现由 phase 1 foundation
     lane 直接产，`core_rules` 保留为 `string[]` 形态——见 #54).
     **Phase 1 foundation lane mapping** (decision #52 + #54):
     `chunk_world_rules → foundation.core_rules` (string[] 形态，跨
     chunk 合并去重) / `chunk_power_levels → power_system.levels` /
     `chunk_factions → major_factions`（含 `key_figures` raw 名——
     `members_present[]` 跨 chunk 合并去重直接写入，**双阶段语义**：
     phase 1 写 raw 名 / phase 2 LLM 替换能匹配 candidate_characters.aliases
     的为 character_id，匹配不上保留 raw 名；决策 #54 修订段） /
     `chunk_regions → world_structure.major_regions` /
     `chunk_arc_summary → world_lines.core_conflict`. **Phase 2 no
     longer produces foundation** — foundation 完全由 phase 1
     foundation lane 落盘到 `works/{work_id}/world/foundation/foundation.json`,
     phase 2 只在 baseline 阶段做"替换"工作：把 `foundation.major_factions[].key_figures`
     内 raw 名（phase 1 写入）替换为 character_id（能匹配 candidate_characters.aliases
     的换，匹配不上保留 raw 名；决策 #54 修订段）. Explicitly
     **NOT added**: `chunk_fixed_relationships[]` (chunk view ≤25
     chapters cannot judge "spans entire book", would contaminate
     `world/foundation/fixed_relationships.json`);
     `chunk_setting_features` (overlaps `chunk_world_rules` /
     `chunk_power_levels` / `chunk_factions` / `chunk_regions` —
     `world_structure.summary` / `world_lines.setting_features` are
     synthesised by Phase 1 LLM from those four fields). `members_present`
     **double-pipe to `foundation.major_factions.key_figures`**:
     phase 1 foundation lane 把 `members_present[]` 跨 chunk 合并去重
     直接写入 `key_figures`（raw 名形态，不做身份合并）；phase 2 baseline
     LLM 把能匹配 `candidate_characters.aliases` 的 raw 名替换为
     `character_id`，匹配不上保留 raw 名（决策 #54 修订段）。`members_present`
     同时也由 phase 1 candidate_characters lane 用做跨 chunk 身份合并
     （并行 lane，foundation lane 不依赖 candidate_characters lane 结果）。
     → `schemas/analysis/chapter_summary_chunk.schema.json`,
     `schemas/world/foundation.schema.json`,
     `automation/prompt_templates/{summarization,analysis_foundation,baseline_production}.md`,
     `docs/architecture/{extraction_workflow,schema_reference}.md`.
27m. **stage_plan 切分语义 = 拐点先行，章数硬范围；prompt 反锚定 +
     `default_stage_size` 字段下线。** 旧设计在 `analysis.md` §步骤 2 +
     JSON 示例 + schema 字段三处同时锚定 "10 章"，LLM 实际产出落入
     "先按 10 章等分、再给每段挑剧情节点写 boundary_reason" 的偷懒
     模式（实证：537 章 / 53 stage 中前 38 个全是恰好 10 章）。新设计：
     (1) 程序式三子步流程——2.1 通览 chunk 输出列出全书所有剧情拐点
     候选（章号 + 类型 + 一句话事件）；2.2 沿章序把相邻拐点合并成
     stage（章数 8-15 hard，schema `chapter_count.minimum=8` /
     `maximum=15` 双向硬挡 LLM 输出（monolithic 路径走 schema-gate-as-
     retry-trigger 决策 #27i 注入 prior_error）+ orchestrator
     `_check_stage_plan_limits` 作 belt-and-suspenders 二次兜底；
     light_novel 派生路径事实上不走 schema validate（既不在 phase 1
     `lanes` 列表也无主动 validate 调用），程序产出可信，`chapter_count=1`
     在新 schema 下 schema-invalid 是已知 trade-off——若未来某外部工具
     加入对 light_novel 产物的 schema 校验需切到 schema oneOf + structure_mode
     dispatch 形态，当前没有此调用点）；2.3 反锚定自检（≥3 连等章数视为
     机械等分必须重审 +
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
    (minimal) → L3 full re-run (last resort). **Disambiguation**：本条
    L1/L2/L3 是 phase 0 chunk-level JSON 格式修复三档阶梯（仅 phase 0
    `_summarize_chunk` 使用）；与 #25 (repair_agent L0–L3 × T0–T3)
    同名不同物——后者是 phase 3 stage 抽取产物的 checker × fixer
    二维矩阵 + Phase A→B→C lifecycle。同字面 "L1/L2/L3" 在两处语义
    完全不同；互不依赖。
    → `automation/persona_extraction/json_repair.py`.

## Configuration & Runtime Resilience

45. Single-source TOML config at `automation/config.toml` (loader
    `automation/persona_extraction/config.py`). Override priority:
    CLI > `config.local.toml` > `config.toml` > dataclass defaults.
    Sections: `stage / phase0 / phase1 / phase3 / phase4 / repair_agent
    / backoff / rate_limit / runtime / logging / git`.
46. Token-limit auto-pause (subscription model, §11.13) — `RateLimitController` parses DST-aware reset, writes flock-merged `rate_limit_pause.json`, blocks pre-launch + every `run_with_retry`, re-runs failed prompt after reset without consuming a retry slot. Unparseable resets → probe loop (single elected leader). Hard-stops (weekly ≥ `weekly_max_wait_h` default 12h; probe ≥ `probe_max_wait_h` default 6h) → exit 2 + `rate_limit_exit.log`. Pause excluded from `--max-runtime` (deduped by `resume_at`). → `docs/requirements.md` §11.13 + `automation/persona_extraction/rate_limit.py`.
47. Phase 0 summarize subprocess timeout = `[phase0].summarize_timeout_s` (default 1800s), not the historical borrow of `[phase3].review_timeout_s` (600s). Reason: a Phase 0 chunk reads `chunk_size` chapters (default 20) and produces N× per-summary (100–150 chars) + 5 chunk-level secondary aggregates (`chunk_arc_summary` / `chunk_world_rules` / `chunk_power_levels` / `chunk_factions` / `chunk_regions`) under opus-4-7 effort=max; runtime evidence shows wall > 600s is normal. `phase3.review_timeout_s` stays 600s for the phase 3 reviewer short-chain it actually serves. → `automation/config.toml` `[phase0]`, `automation/persona_extraction/config.py::Phase0Config`, `automation/persona_extraction/orchestrator.py:_summarize_chunk`.
48. **Length-bound tolerance gate (B 方案).** When an LLM-driven phase has exhausted its strict retry budget — phase-specific exhaustion points: Phase 0 `_summarize_chunk` L1+L2+L3 全跑完 / Phase 1 per-lane `exit_validation_max_retry` 耗尽 / Phase 2 单次 baseline LLM + validate_baseline 失败 / Phase 4 scene-split `max_retries_per_chapter` 耗尽 / **Phase 3 repair_agent lifecycle 2 即将 `T3_EXHAUSTED`**（**仅 phase 3 经 repair_agent 路径**——其他 phase 不接入 repair_agent，见 #25 disambiguation），a final pass calls `validator.validate_with_length_tolerance` (helper at `automation/persona_extraction/validator.py`): if the strict failure list contains **only** `minLength`/`maxLength` violations and a relaxed schema (each `minLength` × 0.9 floor, each `maxLength` × 1.1 ceil) passes, accept the artifact as PASS; otherwise keep the original failure. All other constraints (`required` / `type` / `enum` / `pattern` / `minimum` / `maximum` / `minItems` / `maxItems`) stay strict. **Not applied** to `post_processing.py` program-only digest/catalog outputs — those have no LLM-edge thrash and would mask code bugs. **No metadata marker** on tolerance-accepted artifacts (downstream consumers don't distinguish strict-pass vs tolerance-pass). Pairs with #27i (schema-gate-as-retry-trigger): strict-retry path runs to exhaustion first; tolerance is a final safety valve, not a substitute for retry. Pairs with global `[phase3].max_turns = 80` (was 50) and `--chunk-size` default `20` (was 25) — both reduce the rate at which boundary thrash hits exhaustion. Plumbing → `automation/persona_extraction/validator.py` (helpers), `orchestrator.py:_summarize_chunk + run_analysis + run_baseline_production`, `scene_archive.py:_handle_validation_failure`, `automation/repair_agent/coordinator.py` (T3_EXHAUSTED terminal-state branch；phase 3 only).
49. **Phase 0 recovery sweep with downgraded effort (per-chunk targeted救火).** opus-4-7 effort=max on phase 0's多字段 chunk synthesis (read `chunk_size` chapters → write N× per-summary + 5 chunk-level secondary aggregates) stochastically triggers extended server-side thinking that exceeds the 1800s subprocess wall budget. Empirically observed on `<work_id>` chunks 8 across two distinct chapter ranges (v2: C0176-C0200, v3: C0141-C0160) — both timed out with effort=max ×2 retries, both completed in ~14 min wall with effort=high (schema-valid output, equivalent quality). Rather than blanket-downgrade phase 0 to effort=high (which would slightly lower quality on the 95%+ chunks that don't trigger the long-thinking edge case), the orchestrator runs a **recovery sweep** after the main phase 0 ThreadPool finishes: any chunk whose `state == 'failed'` AND `error_message` contains `'timed out'` OR `'error_max_turns'` AND `recovery_attempted == False` is rerun once with `effort='high'` (per-call kwarg via `LLMBackend.run`, no backend instance swap), reusing `phase0.concurrency` (ThreadPoolExecutor max_workers). Outcome marks `recovery_attempted=True` regardless; subsequent `--resume` skips already-attempted chunks (no infinite救火 loop). The full retry pipeline (L1/L2/L3 JSON repair + jsonschema gate + length-bound tolerance #48) runs inside `_summarize_chunk` per the existing contract — sweep just changes effort, not retry semantics. Plumbing → `automation/persona_extraction/llm_backend.py::LLMBackend.run` (new `effort: str | None = None` kwarg), `orchestrator.py::_run_recovery_sweep` (new method, called from `run_summarization` post-main-pool), `progress.py::ChunkEntry` (new `recovery_attempted: bool = False`), `config.py::Phase0Config.recovery_effort` + `automation/config.toml [phase0] recovery_effort`.
50. **Post-processing 对 derived digests 永远走 replace-slice 语义。** `generate_memory_digest` 与 `generate_world_event_digest` 把当前 stage 的派生条目写入 `memory_digest.jsonl` / `world_event_digest.jsonl`：当前 stage 旧条目被新条目替换，其它 stage 条目保留。**当前 stage 派生数组为空（`memory_timeline` 0 条 / `stage_events` 0 条 — schema 合法）也必须落盘 replace-slice**——读 existing → drop `_stage_from_id(...) == current_stage_num` 的旧条目 → write 剩余条目。否则 repair 删空一个 stage 的源数组、再跑 post-processing 时旧 digest slice 留在 JSONL 里，与 #32 / #33 的 1:1 拷贝契约 + Phase 3.5 #27i schema-gate 一致性检查（见 `consistency_checker._check_memory_id_correspondence` / `_check_world_event_digest`）撞车。空源数组仍 emit warning issue 让 caller 收（信息提示，方便人工核查"这阶段是不是真的没事件"），但实际 IO 必须发生。Plumbing → `automation/persona_extraction/post_processing.py::generate_memory_digest` + `generate_world_event_digest`。
51. **CLI `--resume` 阶段无关续跑契约。** `automation/persona_extraction/cli.py` 的 `--resume` 是 `run_full` 的 auto-yes 信号——`run_full` 是 resume entry point，按 phase 顺序自检 + skip + self-heal（Phase 0 schema-gated chunk skip / Phase 1 产物存在则跳过 / Phase 1.5 用 `--characters` 旁路 / Phase 3 reconcile_with_disk + 从 `stage_plan.json` rebuild `phase3_stages.json`）。`--resume` 标志只 silent run_full 内 `input("Resume from existing progress? [Y/n]: ")` 这条交互确认；与磁盘上具体哪个 phase 已落盘无关。`--background` 与 `--resume` 正交：`--background` 校验阶段感知双分支，读 `pipeline.json::phases.phase_1_5`——未 done 则强制要求 `--characters`（跳过 `confirm_with_user` 第一个 character 选择 input；end_stage prompt 兜底由 `confirm_with_user` 内 EOFError → `preset_end_stage = None` = 全跑 = 合法 daemon 行为，**不强制 `--end-stage`**，决策 #56 修订）；已 done 则强制要求 `--resume` 或 `--characters` 二选一（避免 daemon 撞 run_full 内 `'Resume from existing progress?'` 的 stdin 死锁）。两分支共同保证 daemon 路径上**没有任何**可触发 traceback 的 stdin prompt——所有 stdin 站点（character 选择 input + end_stage 选择 input + run_full `Resume from existing progress?` input）走 `try/except EOFError` 兜底 + 安全 default（character 选择 = `recommended_ids`、end_stage = None=全跑、resume = Y）。`--end-stage` argparse `type` 是 `_nonneg_int` 自定义函数，负数在 argparse 阶段直接 reject（exit 2 + 友好错误信息），避免 `--end-stage -1` 通过 `args.end_stage is None` 检查后让 `run_extraction_loop(max_stages=-1)` 在 line 1853 `tracker.completed >= max_stages` 立即 True 造成无声逻辑错误。Plumbing → `automation/persona_extraction/cli.py`（无条件走 run_full + 加 `_load_pipeline_status` helper + 阶段感知双分支 background 校验，phase_1_5 not done 单约束 `--characters` + `_nonneg_int` argparse type）+ `automation/persona_extraction/orchestrator.py::run_full(auto_resume: bool = False)` + `confirm_with_user` 内两 input 加 `try/except EOFError`（end_stage 兜底 = None = 全跑，对齐 prompt 文案 + flag "omit = all" 设计——决策 #56） + `automation/persona_extraction/_smoke_cli_resume_background_validation.py`（场景：phase_1_5 done/pending × {--resume, --characters, --end-stage, 都无} 的 background 校验真值表 + scenario I 验证 `--end-stage -1` argparse reject）。

52. **Phase 1 三 lane 并行 + 字段裁剪 + light_novel stage_plan 跳过 LLM。** 旧设计单次 `claude -p` 串行产出三件分析产物，schema gate 失败时整 lane 重跑且共享一个 `[phase1].exit_validation_max_retry` 池——实证 537 章 monolithic 单 LLM 调用 26min 仍未落盘，wall time 是后续 phase 启动前的硬瓶颈。新设计把 phase 1 内部拆成独立 lane：(1) **monolithic 模式 = 3 lane 并行**（foundation / stage_plan / candidate_characters，每 lane 独立 prompt template + 独立裁剪 chunks 输入 + 独立 schema gate）；**light_novel 模式 = 2 lane 并行**（foundation + candidate_characters）+ orchestrator 程序化 `_build_light_novel_stage_plan()` 直接落盘（zero LLM call，stage_plan lane 整体跳过 LLM）。(2) **字段裁剪**：每 lane 只接收自己需要的 chunk 字段，预先 project 后写到 `works/{work_id}/analysis/.phase1_lane_inputs/{lane}/chunk_NNN.json` 并 `.gitignore` 屏蔽——foundation lane = **仅** chunk-level 二级字段（`chunk_arc_summary` / `chunk_world_rules` / `chunk_power_levels` / `chunk_factions` **含 `members_present`**——决策 #54 修订段，foundation lane 写 `key_figures` raw 名直接来自 chunk_factions[].members_present[] 跨 chunk 合并去重 / `chunk_regions`），**`summaries` 整段删除**（全书设定不依赖逐章锚点）；stage_plan lane = `chunk_arc_summary` + `chunk_regions` + per-summary `chapter` + `summary`（**`characters_present` / `emotional_tone` / `identity_notes` 删除**——拐点合并依据是 `chunk_arc_summary` chunk 弧光 + `summary` 事件描述，与身份 / 角色 / 情绪粒度正交，裁掉减 token + 减 LLM thinking 长尾；`key_events` 已从 chunk schema 整体删除，见 #53）；candidate_characters lane = per-summary `chapter` + `summary` + `characters_present` + `identity_notes` + `chunk_factions[].{name,members_present}`（**新增 `summary`**——跨 chunk 身份合并需要事件上下文判断隐含身份链，光看 `identity_notes` 短句不够）。(3) **foundation lane 落盘路径** = `works/{work_id}/world/foundation/foundation.json`（与 phase 2 后续补齐的 `key_figures` 同文件；phase 2 `fixed_relationships.json` 同目录），**不再走 `works/{work_id}/analysis/world_overview.json`** 路径——decision #54 把 foundation 前移到 phase 1 直接产，phase 2 不再二次综合 foundation。(4) **per-lane retry = schema gate + correction_feedback（per-lane 独立预算）**：每 lane 完成抽取后落盘文件即跑 jsonschema gate（含 stage_plan lane 的 8–15 章 limit 检查由 schema `chapter_count.minimum=8 / maximum=15` 直接硬挡，决策 #27i schema-gate-as-retry-trigger 注入 prior_error；代码层 `_check_stage_plan_limits` 作 belt-and-suspenders 二次兜底）；首条违规作为 `prior_error` 注入下一次重试 prompt（与 phase 0 chunk-level / phase 4 chapter-level prior_error 注入同形态）。`[phase1].exit_validation_max_retry` 语义改为 per-lane 独立预算（不再共享池）。**不集成 `repair_agent.run`**——phase 1 输出是 chunk-level 派生的全书分析，不是 stage-anchored 源文抽取，repair_agent 的 SourceContext + T2 source_patch 假设 stage scoped chapter range 可读，对 phase 1 不成立。(5) **失败语义** = lane 隔离：单 lane fail 不影响其他 lane 已落盘产物，`--resume` 时 `reconcile_with_disk` 检测到 schema-valid 产物即跳过对应 lane 重跑（与 phase 0 chunk-level skip / phase 3 lane-level skip 同形态）。(6) **prompt template 三件套替换 `analysis.md`**：`analysis_foundation.md` / `analysis_stage_plan.md`（含 #27m 步骤 2.1/2.2/2.3 反锚定自检三子步） / `analysis_candidate_characters.md`（含步骤 1.5 跨 chunk 身份合并）；旧 `analysis.md` + `analysis_world_overview.md` 删除，no legacy fallback。(7) **tmpdir 清理**：run_analysis 在 `try/finally` 内 cleanup `.phase1_lane_inputs/`（成功 / 失败 / SIGTERM 均清）。Plumbing → `automation/prompt_templates/analysis_{foundation,stage_plan,candidate_characters}.md`、`automation/persona_extraction/prompt_builder.py`（`build_foundation_prompt` / `build_stage_plan_prompt` / `build_candidate_characters_prompt` + 三个 `_project_chunk_for_*` 内部裁剪函数 + `prepare_phase1_lane_inputs`）、`automation/persona_extraction/orchestrator.py::run_analysis`（fan-out 重写 + foundation lane 输出到 `world/foundation/`）、`automation/config.toml [phase1]` + `automation/persona_extraction/config.py::Phase1Config`（增 `lane_concurrency`，注释更新 `exit_validation_max_retry` per-lane 语义）、`.gitignore`（`works/*/analysis/.phase1_lane_inputs/`）。

53. **Analysis schema 收紧 v2 + Phase 1.5 推荐规则化。** 2026-05-08 跑完一次端到端 phase 0 + 1 + 1.5 + phase 2 部分（被 SIGTERM 中止），看实际产物决定收紧三组 analysis schema。(1) **chunk schema** — 删 `summaries.items.key_events`（经 #52 三 lane 投影后无消费方，Phase 2 baseline 也不读，是死字段）；`summaries.items.summary` 100-150 → 150-200 CJK chars（需要装下事件 + 设定上下文，原范围在实际产出里频繁触底）。决策 #27m 内描述同步修订（key_events 段删除、summary 长度更新）。(2) **candidate_characters schema** — 删 `candidates.items.recommended` boolean（LLM 自报推荐拍脑袋打 boolean，不可靠）；删 `candidates.items.aliases.items.first_appearance` 字符串（如"约第 0042 章"，无下游消费且不可程序检索）。Phase 1.5 默认勾选改为基于 `importance == "主角"` 程序判定（用户仍可手选追加 / 取消），`recommended` 字段在 candidate 级消失但 `RECOMMENDED` 标签字符串保留——展示逻辑改读 `importance`。(3) **foundation schema（原 world_overview schema，决策 #54 改名 + 前移到 phase 1 落 `world/foundation/foundation.json`）** — `world_structure.major_regions.items` 由 `string` 升 `{name (≤15), description (≤30)}` 对象（对齐 `chunk_regions.items` 形态，phase 1 foundation lane 直接读 chunk 综合，不再 mid-step 拼对象）；`power_system.levels.items` 同上对齐 `chunk_power_levels.items`；`core_rules.maxItems` 20→30（N chunk × ≤5 条原始规则去重后 30 比 20 合理），`items.maxLength` 100→150（保留字符串数组形态，强制 LLM 重新整理而非照搬 chunk 行）。Plumbing → `schemas/analysis/{chapter_summary_chunk,candidate_characters}.schema.json` + `schemas/world/foundation.schema.json`（决策 #54 把 `world_overview.schema.json` 内容合并入 foundation schema，删 analysis 副本）、`automation/prompt_templates/{summarization,analysis_foundation,analysis_stage_plan,analysis_candidate_characters,baseline_production}.md`、`automation/persona_extraction/{prompt_builder,orchestrator}.py`、`docs/architecture/{schema_reference,extraction_workflow}.md`、`ai_context/{architecture,decisions}.md`（修订 #27m 描述 + 本条新增）。

54. **Foundation 前移 phase 1 + phase 2 仅补 `key_figures` + target_baseline 准入门槛收紧（dialogue/action 交互）。** 2026-05-09 端到端跑完 phase 2 后比对 [analysis/world_overview.json](works/<work_id>/analysis/world_overview.json) vs [world/foundation/foundation.json](works/<work_id>/world/foundation/foundation.json)，发现两份 95% 字段重叠（`work_id` / `genre` / `tone` / `world_structure` / `power_system` / `world_lines` 几乎 1:1 拷贝）；真增量只有 `core_rules` 升 object[] 含 `impact` + `major_factions.key_figures[]` 两项。同步发现 target_baseline 15 条全 `核心 / 重要` tier，含末章才出生且无 dialogue / action 的双胞胎角色——baseline prompt 当前"宁可多列、不可漏列、被点名提及即纳入"导致前 12 stage × 2 角色 × 3 结构 = 72 条纯空 entry 噪声。改造三件合一：(1) **foundation 前移 phase 1**：原 phase 1 `world_overview` lane → 改名 `foundation` lane，输出路径 `works/{work_id}/analysis/world_overview.json` → `works/{work_id}/world/foundation/foundation.json`。`schemas/analysis/world_overview.schema.json` 删除，内容**逐字搬到** `schemas/world/foundation.schema.json` 替换旧 foundation schema（旧 foundation 字段 / bound 形态废弃，新 foundation = 旧 world_overview 形态）；`$id` / `title` / `description` 改写为 foundation 语义，**字段 / bound 一字不改**（含 `core_rules` 保持 `string[] ≤30 条 / 每条 ≤150 字` 形态——user 决策 1 明确不改 core_rules 结构）。`major_factions.items` 新增 `key_figures[]` optional 字段（items: string maxLength 30 / maxItems 10 / 注释说明双阶段语义），**phase 1 lane 写 raw 名**（chunk_factions[].members_present[] 跨 chunk 合并去重直接写入，化名 / 真名 / 称呼任一）。`analysis_world_overview.md` → 改名 `analysis_foundation.md`。(2) **phase 2 缩水到 LLM "替换" 工作**（决策 #54 修订段，2026-05-11 user 反馈 phase 1 不应丢信息——chunk_factions.members_present 已有 raw 名）：删 `baseline_production.md`「产出 1：世界 Foundation」整段（≈100 行）；新增「产出 1：替换 foundation.major_factions[].key_figures 内 raw 名为 character_id」段：单次 LLM call 整合到 build_baseline_prompt（与 fixed_relationships / identity / target_baseline / manifest 同一次调用），输入 phase 1 落盘 foundation（含 raw 名 key_figures）+ `analysis/candidate_characters.json`（含 character_id + aliases） + 已确认目标清单；LLM 对 key_figures 每个 raw 名 lookup candidates[*].aliases，能匹配的换为对应 character_id，**匹配不上保留 raw 名**（不报错、不删除）；schema 不抓 character_id 合法性，key_figures 最终是 character_id + 未合并 raw 名混合。phase 2 保留产出：`fixed_relationships.json` + per-character `identity.json` + `target_baseline.json` + `manifest.json` 四件 + foundation key_figures 替换。失败处理：phase 2 现行兜底形态——单次 `run_with_retry` → `validate_baseline` schema gate → length-bound tolerance gate (#48) → fail 则 `sys.exit(1)`，**不接入 repair_agent**（B-2 拆出来作单独 todo `T-PHASE2-REPAIR-AGENT`，工程量 ≈ phase 3 接入当年的工作量，与本次重构正交）。(3) **target_baseline 准入门槛收紧**：删 prompt 中「宁可多列、不可漏列、被点名提及即纳入」原则；改为 **准入门槛 = 本角色与目标角色在 chapter_summaries 摘要描述中被反映为有过 dialogue / action 交互**（如"X 对 Y 说……" / "X 救/打/教 Y" / "X 与 Y 联手……"等动作或对话描述）；血亲不再默认核心 tier——按准入门槛 + 实际剧情驱动力分级。tier 4 档 (核心 / 重要 / 次要 / 普通) 不动，准入门槛与 tier 分级正交。Phase 3 stage_snapshot 三结构双向 set-equal 约束（#13）不动——准入门槛只影响 baseline 收录范围，对 phase 3 keys == baseline 的执行不变。**显式不做**：不动 [target_baseline.schema.json](schemas/character/target_baseline.schema.json) 与 [targets_cap.schema.json](schemas/character/targets_cap.schema.json)（schema 不变，仅 prompt 加严）；不引入 `_validation_tolerance_applied` 类元数据；不本次接入 repair_agent 到 phase 2（拆出来作 `T-PHASE2-REPAIR-AGENT`）；本 /go 不执行 `git reset` 重跑 phase 2 数据迁移——user 自决何时操作。Plumbing → `schemas/world/foundation.schema.json`（重写）+ `schemas/analysis/world_overview.schema.json`（删除）、`automation/prompt_templates/analysis_foundation.md`（改名 + 内容更新）+ `automation/prompt_templates/baseline_production.md`（删 foundation 段 + 加 key_figures 补齐段 + target_baseline 加严）、`automation/persona_extraction/prompt_builder.py`（`build_world_overview_prompt` → `build_foundation_prompt`、`_project_chunk_for_world_overview` → `_project_chunk_for_foundation`、新增 `build_factions_keyfigures_prompt`、lane 名常量 `world_overview` → `foundation`）、`automation/persona_extraction/orchestrator.py`（`run_analysis` foundation lane 输出路径改 + `run_baseline_production` 新增 key_figures 补齐 LLM call）、`schemas/README.md` + `automation/README.md`（schema 索引 + lane 列表更新）、`ai_context/{architecture,decisions,conventions}.md`（本条 + #25 / #40 disambiguation + #48 措辞修正 + #27m + #52 + #53 同步）、`docs/architecture/{schema_reference,extraction_workflow}.md` + `docs/requirements.md` §9 / §11、`docs/todo_list.md`（新立 `T-PHASE2-REPAIR-AGENT`）。

55. **char_snapshot lane 拆 3 sub-lane 并行 + 程序 merge + lifecycle 2
    sub-lane 重抽。** 2026-05-12 起 phase 3 单 stage 的 `char_snapshot` lane
    内部拆 3 个并行 sub-lane（`char_expression` / `char_decision` /
    `char_cognition`）压 wall-time。字段归属表（同源给 prompt + merge 用，
    定义在 `automation/persona_extraction/snapshot_merge.py::FIELD_ALLOCATION`）：
    `char_expression` = `voice_state` / `active_aliases` / `current_mood` /
    `failure_modes.tone_traps`；`char_decision` = `behavior_state` /
    `boundary_state` / `emotional_baseline` / `current_personality` /
    `current_status` / `stage_delta.{status_changes, mood_shift,
    personality_changes}`；`char_cognition` = `knowledge_scope` /
    `misunderstandings` / `concealments` / `relationships` /
    `relationship_state_summary` / `stage_events` / `character_arc` /
    `snapshot_summary` / `stage_delta.{trigger_events, relationship_changes,
    voice_shift}` / `failure_modes.{common_failures, relationship_traps,
    knowledge_leaks}`；程序注入 = `schema_version` / `work_id` /
    `character_id` / `stage_id` / `stage_title` / `timeline_anchor` /
    `chapter_scope`. **Merge hard gate**：(1) 每 partial 顶层字段集合 ==
    分配；(2) `failure_modes` 4 子键互斥 across 2 sub-lane + 全 4 子键覆盖；
    (3) `stage_delta` 6 子键互斥 across 2 sub-lane + 全 6 子键覆盖（S001
    允许两 sub-lane 都不写 `stage_delta` 顶层 key）；(4) 三方 keys（
    `voice_state.target_voice_map` / `behavior_state.target_behavior_map` /
    `relationships`）keys 集合相互相等且 == `target_baseline.targets[].target_character_id`
    — 复用 `automation/repair_agent/checkers/targets_keys_eq_baseline.py`
    做 merge 前置预检；(5) **(D) drop entry 不被误判**：merge 仅查字段集合
    互斥 + 全覆盖，**不查** partial entry 数 ≥ prev（per #11f / #13）。
    **Lane 级 resume 粒度仍是 `snapshot:{char_id}`**——sub-lane 拆分对
    `StageEntry.lane_states` 不可见；任一 sub-lane 或 merge 失败即整 lane
    重跑，PENDING / ERROR 状态下的 `.partial/{stage_id}_*.json` 由
    `progress.reconcile_with_disk` 一律删，不复用。**Repair lifecycle 2 T3
    重抽**：file-level lifecycle 1 末端 T3 触发后，若开关开 + 文件是
    `characters/<cid>/canon/stage_snapshots/<sid>.json` → T3 fixer 走 3
    sub-lane 并行重新 extract + merge 路径（每 sub-lane prompt 注入
    `prior_attempt_context` resolved+remaining ≤600 char 摘要 + 错误信息），
    替代默认 `FileRegenFixer` 全文 regen；lifecycle 计数（`max_lifecycles_per_file = 2`）
    与 `T3_EXHAUSTED` 终止语义不变（lifecycle +1 仅在 T3 真正触发并 reset 进入
    下一轮时计入，rate-limit pause 重跑不消耗 lifecycle 槽 — R1）。
    **Rate-limit / hard-stop**：sub-lane 走现有 `run_with_retry` 继承
    `RateLimitController` pause / resume；hard-stop 时 sub-lane sub-executor
    `shutdown(wait=False, cancel_futures=True)` 并立即 raise，磁盘 partial
    保留供下次 `--resume` 启动前的 `_clear_snapshot_partials` 兜底清理覆盖
    （R2 — 不在 hard-stop 路径删 partial，避免 sleep 中的同伴 future 被
    隐式 `with` 退出阻塞数小时；R3 — 启动前清理仍是单源真理）。**Outer pool
    全并发**：phase 3 主 ThreadPoolExecutor `n_workers = max(1, len(lanes_to_run))`，
    外层 lane (`world` / `snapshot:*` / `support:*`) 全并发提交；sub-lane fan-out
    仅在 `snapshot:*` lane 内部展开 3 inner LLM 调用，`world` / `support:*` 无
    fan-out。2 角色场景峰值 = 1 world + 2×3 snapshot sub-lane + 2 support = **9**
    LLM 并发；sub-lane 关闭时降为 1 + 2 + 2 = **5**——均 ≤ `[phase3].concurrency=10`
    cap（`automation/persona_extraction/config.py`）。原 H1 "÷3 与 inner 相消"
    算法把 `world` / `support` 错按 sub-lane 折扣，外层无故缩到 1 等效串行，
    单 stage 时长由理论 max(world, snapshot, support) ~15 min 拉到 ~60 min，
    已撤回。**Toml 开关 +
    CLI 双向 flag**：`[phase3].char_snapshot_sub_lanes`（缺省 `true`）+
    `--char-snapshot-sub-lanes` / `--no-char-snapshot-sub-lanes`；
    light_novel 模式单 stage 字符数小，3 sub-lane 启动开销可能 > 抽取
    耗时收益，**不引入** mode-aware 默认值，由用户按 work 手切。
    **Fallback** `false` → 单 lane 等价 `lane_scope=ALL`，phase 3 现状不变
    （baseline 锚点 + #11f 四态 + #13 keys == baseline 校验均为 phase 3
    通用现状，已落地，本决策不引入新强制规则；仅在 prompt_builder
    校准 char_snapshot read list 把 `target_baseline.json` 纳入——todo body
    误以为该文件已在 read list 里，实际此前没有，作为同源校准随本次落盘）。
    **`.partial/` 路径**：`works/{wid}/characters/{cid}/canon/stage_snapshots/.partial/`
    被 `.gitignore` 屏蔽。Plumbing → `automation/persona_extraction/{snapshot_merge,
    prompt_builder,orchestrator,progress,config,cli,lane_output}.py`、
    `automation/prompt_templates/character_snapshot_extraction.md`（加
    `{lane_scope}` / `{lane_field_whitelist}` 占位，不动 §核心规则 #2 与
    §maxItems 裁剪段，保持 sub-lane / 单 lane 全 inherits）、
    `automation/repair_agent/{coordinator.py,fixers/file_regen.py}`（
    `FileRegenFixer` 加可选 `sub_lane_regen` 回调，`coordinator.run` 新增
    kwarg 透传到 `_build_fixers`）、`automation/config.toml`、`.gitignore`、
    `docs/architecture/extraction_workflow.md` §6.2、`docs/requirements.md` §9.3、
    `automation/README.md` Phase 3 段、`ai_context/{architecture,decisions,conventions}.md`、
    `docs/todo_list_archived.md`。

56. **Pipeline-resume alignment 三处修复 — `pipeline.json` schema_version
    启动、phase 2 recovery 阻 phase 3 committed 产物、`--end-stage` daemon
    路径"empty = 全跑"语义贯通。** 2026-05-12 codex `gpt-5` 复审报告（
    `logs/review_reports/2026-05-12_113619_gpt-5_pipeline-resume-alignment-audit.md`）
    指出 3 个 H/M finding，全部确认真实。
    (1) **`PipelineProgress.load()` 误把当前 `phase_2` 当 legacy remap**：
    `_LEGACY_PHASE_KEY_MAP` 把 `phase_2 → phase_1_5` 原本是为兼容旧 progress
    文件（老命名 `phase_2 = 用户确认` / `phase_2_5 = baseline`）；当前命名
    `phase_1_5 = 用户确认` / `phase_2 = baseline` 后，当前文件被 `load()`
    无差别 remap，`phase_2=done` 经"DONE wins"守卫跳过、未在 dict 内立项，
    `__post_init__` 再补 `phase_2 = pending` → 续跑 baseline 完成状态丢失，
    放大 phase 2 recovery 触发面。修复 = `save()` 写 `schema_version: 2`
    顶层字段；`load()` 优先 `schema_version >= 2` 整体跳 legacy remap；缺
    `schema_version` 字段时退到 shape-based 兜底（raw_phases 含 `phase_1_5`
    或 `phase_3_5` 任一即视为 current shape）。**两层守卫并行**：version
    优先、shape-based 兜底——单层 version 短期对存量未写 version 的当前
    文件不安全，shape-based 短期止血 + version 长期权威。`_LEGACY_PHASE_KEY_MAP`
    保留以兼容 `migrate_legacy_progress` 的真 legacy 路径。
    (2) **Phase 2 validation-triggered recovery 不阻已有 phase 3 committed
    产物**：`run_extraction_loop` existing baseline validation 失败时直调
    `run_baseline_production` + `commit_stage("Phase 2 baseline (validation-
    triggered recovery)")` 重写 `target_baseline.json`；`run_baseline_production`
    docstring 已明写 baseline 改写后 phase 3 stage_snapshot 必须配套清空（#13
    双向 set-equal 约束），但本函数声明"不自动清理"——所以调用点必须前置
    guard。修复 = 新增 `_phase3_committed_artifacts_present()` helper（读
    `phase3_stages.json` 任一 stage state == `COMMITTED` 或扫磁盘
    `world/stage_snapshots/*.json` + `characters/*/canon/stage_snapshots/*.json`
    非空即返回 True），插入到两条路径前：(a) validation-triggered recovery
    分支；(b) `--start-phase 2` `force_baseline` 分支。**Daemon vs 前台
    双模交互**：daemon (`--background`，stdin=`/dev/null`) → 打印清理清单
    + `sys.exit(1)`；前台 → 同清理清单 + `input("Continue and overwrite
    phase 3 artifacts? [y/N]: ")` 非 y 即退出。**默认 hard stop**，不实现
    `--reset-phase3-after-baseline-change` 自动清理 flag——破坏性动作走显式
    人工执行（撞 hard stop 后用户手动跑清理命令再重启或切前台走 `[y/N]`）。
    (3) **`--end-stage` daemon 路径"empty = 全跑"语义贯通**：(3a)
    `confirm_with_user` 内 `Extract up to stage N` prompt 文案写 `"0 or
    empty = all"`，但代码 `int(raw) if raw else 0` 把 empty 折成 0（baseline
    only）——文案 / 代码矛盾。daemon stdin=DEVNULL EOFError 走 raw="" 路径，
    被悄悄折成 baseline-only。(3b) `--background` validator 因(3a)折坏才
    硬性要求 `--end-stage`——本来 `argparse default=None` + `run_extraction_loop
    max_stages=None` 已是合法"no limit"语义（决策 #51）。修复 = `preset_end_stage
    = int(raw) if raw else None`（empty → None = 全跑，对齐 prompt 文案 +
    flag "omit = all" + `run_extraction_loop` None 语义）+ prompt 文案改
    `"Extract up to stage N (total {N}; empty = all (no limit), 0 = baseline
    only): "` + 删除 cli.py phase_1_5 未 done 时对 `--end-stage` 必填的
    硬挡（仅保留 `--characters` 必填，决策 #51 daemon prompt 防 deadlock
    口径相应放宽：empty 走"安全 default = 全跑"是合法 daemon 行为）。
    `_smoke_cli_resume_background_validation.py` C / D 翻转为 accept；G / H
    显式传 `--end-stage` 仍 accept；I (`--end-stage -1` argparse reject) 不动。
    **决策 #51 措辞同步**：双约束 `--characters AND --end-stage` 改为单约束
    `--characters`，end_stage prompt 兜底从"daemon validator 强制提供"
    改为"EOFError → None = 全跑"。**显式不做**：不动 `_LEGACY_PHASE_KEY_MAP`
    内容（仍保留 `phase_2 → phase_1_5` / `phase_2_5 → phase_2`）；不动
    `migrate_legacy_progress` 的 `extraction_progress.json` 路径；不实现
    `--reset-phase3-after-baseline-change` flag（破坏性动作走人工执行更稳）；
    不动 light_novel `chapter_count=1` schema 例外（决策 #27m 现状保留，
    外部 validator 消费方未出现 → todo `T-LIGHTNOVEL-SCHEMA-ONEOF`）。Plumbing →
    `automation/persona_extraction/progress.py`（`PipelineProgress.save/load`
    + `_LEGACY_REMAP_GUARD` 内部辅助）、`automation/persona_extraction/orchestrator.py`
    （`_phase3_committed_artifacts_present` helper + `run_extraction_loop`
    validation-triggered & force_baseline 两调用点前置 guard + `confirm_with_user`
    line 2125 兜底改 None + line 2116-2117 prompt 文案改写）、
    `automation/persona_extraction/cli.py`（删 phase_1_5 未 done 时 `--end-stage`
    必填硬挡 + 长注释同步）、
    `automation/persona_extraction/_smoke_cli_resume_background_validation.py`
    （C / D 翻转）、`automation/README.md` + `docs/architecture/extraction_workflow.md`
    + `ai_context/architecture.md`（四处 `--background` 文案同步）、
    `ai_context/decisions.md`（本条 + #51 措辞同步）、`docs/todo_list.md`
    （登记 `T-LIGHTNOVEL-SCHEMA-ONEOF`）。

## Repository

41. No novels / databases / indexes / large artifacts / real user packages in git.
42. `works/*/analysis/` + `works/*/indexes/` tracked as canonical; `works/*/retrieval/` local-only.
43. `logs/change_logs/` + `logs/review_reports/` write-mostly — do not proactively read.
44. `prompts/` = manual scenarios only (ingest / review / supplement / cold start). Extraction prompts in `automation/prompt_templates/`; runtime rules in `simulation/prompt_templates/`. Self-contained modules.
