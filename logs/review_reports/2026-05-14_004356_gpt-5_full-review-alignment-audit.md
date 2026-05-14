**Review 模型**：Codex (GPT-5)（`gpt-5`）

# /full-review — Full Repository Alignment Audit

Date: 2026-05-14 00:43:56 America/New_York

Scope followed the `full-review` skill contract: `ai_context/`, `docs/requirements.md`,
`docs/architecture/`, `schemas/`, `prompts/`, `extraction/`, `simulation/`,
`works/`, `users/_template/`, `README`-class files, and `.gitignore`.
`ai_context/skills_config.md` was present and all required review sections
resolved to existing paths.

## Findings

### High

**H1** `extraction/persona_extraction/phases/post_processing.py:215` — Pre-repair post-processing can crash on schema-invalid `memory_timeline` entries.

`schemas/character/memory_timeline_entry.schema.json:8` requires `memory_importance`, but `_timeline_to_digest()` dereferences `entry["memory_importance"]` at `post_processing.py:223`. The orchestrator runs stage post-processing before the repair gate (`orchestrator.py:2959` → `3007`). A parseable but schema-invalid memory timeline can therefore raise `KeyError` before the repair lifecycle can validate and fix the file.

Impact: stage extraction can wedge in `POST_PROCESSING`/exception territory instead of entering the intended repair path for a normal schema violation.

Evidence:
- `schemas/character/memory_timeline_entry.schema.json:8`
- `extraction/persona_extraction/phases/post_processing.py:215`
- `extraction/persona_extraction/phases/post_processing.py:223`
- `extraction/persona_extraction/orchestrator.py:2959`
- `extraction/persona_extraction/orchestrator.py:3007`

**H2** `extraction/persona_extraction/core/process_guard.py:90` — PID lock acquisition is non-atomic.

`PidLock.acquire()` does `is_held()` and then writes the PID file with `write_text()` (`process_guard.py:90` / `99`). The main extraction path and Phase 4 also call `is_held()` before `acquire()` (`orchestrator.py:611`, `scene_archive.py:721`). Two near-simultaneous starts can both observe no lock and then overwrite the same lock file.

Impact: concurrent processes for the same work can write progress files, generated artifacts, and commits concurrently. Rate-limit pause files use `fcntl.flock`, but PID locks do not.

Evidence:
- `extraction/persona_extraction/core/process_guard.py:90`
- `extraction/persona_extraction/core/process_guard.py:99`
- `extraction/persona_extraction/orchestrator.py:611`
- `extraction/persona_extraction/phases/scene_archive.py:721`
- `extraction/persona_extraction/core/rate_limit.py:748` (contrast: uses `flock`)

**H3** `extraction/persona_extraction/orchestrator.py:635` — Phase 0 chunk completion accepts over-complete or wrong chapter coverage.

The docstring says `_chunk_passes_full_check()` enforces `len(summaries) == expected`, and workflow docs repeat the exact-count gate. The implementation only rejects `count < expected` at `orchestrator.py:657`; extra summaries pass. The schema only validates each `chapter` as `^C[0-9]{4}$`, not uniqueness or membership in the chunk range.

Impact: duplicate, extra, or out-of-range summaries can pass Phase 0 and feed Phase 1 foundation/stage/candidate lanes, while a real chapter may be missing.

Evidence:
- `extraction/persona_extraction/orchestrator.py:635`
- `extraction/persona_extraction/orchestrator.py:656`
- `docs/architecture/extraction_workflow.md:59`
- `schemas/analysis/chapter_summary_chunk.schema.json:140`
- `schemas/analysis/chapter_summary_chunk.schema.json:154`

**H4** `schemas/world/foundation.schema.json:7` — Foundation validation is too weak for the pipeline claims, and the `key_figures` contract is split-brain.

`foundation.schema.json` only requires `work_id`; a minimal `{"work_id": "demo"}` passes jsonschema. `run_analysis()` skips a lane when schema validation has no errors (`orchestrator.py:1850` / `1855`), and Phase 2 validation only checks schema plus a non-empty `work_id` (`phase2_baseline.py:142` / `152`). Separately, active instructions disagree on `major_factions[].key_figures`: Phase 1 foundation prompt says it writes raw names (`analysis_foundation.md:3` and `:53`), but `baseline_production.md:9` says Phase 1 does not write the field, while `baseline_production.md:42` assumes raw names already exist. `ai_context/conventions.md:51` repeats the stale "except key_figures" contract.

Impact: incomplete Tier 0 world data or missing faction-to-character bindings can pass/re-skip without retry. This can weaken runtime world context and character binding.

Evidence:
- `schemas/world/foundation.schema.json:7`
- `schemas/world/foundation.schema.json:84`
- `schemas/world/foundation.schema.json:89`
- `extraction/persona_extraction/orchestrator.py:1850`
- `extraction/validation/gates/phase2_baseline.py:142`
- `extraction/persona_extraction/prompts/analysis_foundation.md:3`
- `extraction/persona_extraction/prompts/baseline_production.md:9`
- `extraction/persona_extraction/prompts/baseline_production.md:42`
- `ai_context/conventions.md:51`

### Medium

**M1** `extraction/ingestion/validator.py:94` — Source validation does not verify chapter text files.

The ingestion validator checks required metadata files, schema shape, `chapter_count`, sequence continuity, and `structure_mode` profile alignment, but it does not verify that `chapter_index[].normalized_path` exists or matches the extraction path convention. The schema treats `normalized_path` as a string only. Phase 0 prompt building assumes `sources/works/{work_id}/chapters/C####.txt`, and later read-list builders silently omit missing chapter files.

Impact: a source package can pass the pre-Phase-0 gate while extraction references nonexistent or misnamed chapter text.

Evidence:
- `extraction/ingestion/validator.py:94`
- `extraction/ingestion/validator.py:145`
- `extraction/ingestion/validator.py:175`
- `schemas/work/chapter_index.schema.json:38`
- `extraction/persona_extraction/prompt_builder.py:74`
- `extraction/persona_extraction/prompt_builder.py:818`

**M2** `extraction/repair/field_patch.py:57` — Repair JSONL slice merge cannot delete stale current-stage entries.

The repair path loads a current-stage JSONL slice while retaining the full accumulated JSONL (`orchestrator.py:1394`). `_merge_jsonl_slice()` replaces entries by key and appends new keys, but every full-list entry not referenced by the patched slice is passed through unchanged (`field_patch.py:60` / `65` / `80`). If a repair removes an invalid duplicate/current-stage entry from the slice, write-back preserves the stale entry from the full list.

Impact: digest JSONL files can remain polluted after repair; validation or retrieval may continue seeing an entry the repair output intentionally removed.

Evidence:
- `extraction/persona_extraction/orchestrator.py:1394`
- `extraction/repair/field_patch.py:57`
- `extraction/repair/field_patch.py:65`
- `extraction/repair/field_patch.py:80`
- `extraction/repair/field_patch.py:101`

**M3** `extraction/persona_extraction/orchestrator.py:2251` — Phase 2 progress is marked done before the baseline commit is known to have succeeded.

`run_baseline_production()` marks `phase_2` done before returning. In the fresh flow, `commit_stage()` runs afterward (`orchestrator.py:3689`) and only prints if a SHA exists; the code continues into Phase 3 even when `commit_stage()` returns `None`. `commit_stage()` returns `None` for empty status or commit failure.

Impact: baseline artifacts can be considered phase-complete while dirty/uncommitted, causing resume/preflight friction and breaking the extraction branch's "passing stage committed" contract for Phase 2.

Evidence:
- `extraction/persona_extraction/orchestrator.py:2251`
- `extraction/persona_extraction/orchestrator.py:3689`
- `extraction/persona_extraction/core/git_utils.py:228`
- `extraction/persona_extraction/core/git_utils.py:237`

**M4** `docs/requirements.md:2108` — Requirements still overclaim repair-agent coverage outside Phase 3.

The requirements table says every phase completes via the repair agent and specifically lists Phase 2 as `repair(files=[identity, manifest, foundation, ...])`. Durable decisions and code say repair is currently only wired into Phase 3; Phase 2 is a single LLM call followed by schema/tolerance validation, with a separate todo for future Phase 2 repair integration.

Impact: future agents may assume Phase 2 has automatic repair/retry strength it does not have, leading to bad runbooks or missed implementation work.

Evidence:
- `docs/requirements.md:2108`
- `docs/requirements.md:2114`
- `ai_context/decisions.md:164`
- `extraction/persona_extraction/orchestrator.py:2232`
- `extraction/persona_extraction/orchestrator.py:3123`
- `docs/todo_list.md:14`

**M5** `ai_context/skills_config.md:29` — Skill config points background log consumers at the wrong log directory.

`skills_config.md` says process logs live at `works/*/analysis/logs/`, but the background launcher writes to `works/{work_id}/analysis/progress/extraction_logs/extraction.log`, and `extraction/README.md` documents the latter.

Impact: `/monitor` or other skill consumers can miss the actual extraction log directory.

Evidence:
- `ai_context/skills_config.md:29`
- `extraction/persona_extraction/core/process_guard.py:172`
- `extraction/README.md:141`

**M6** `docs/todo_list_archived.md:93` — Work-specific identifiers are committed in a docs file despite the placeholder policy.

`ai_context/handoff.md` and `ai_context/conventions.md` require docs, prompts, schemas, and `ai_context/` to stay work-agnostic; only `works/`, `sources/`, `logs/change_logs/`, `logs/review_reports/`, and git commit messages are explicitly exempt. `docs/todo_list_archived.md` contains real work and character identifiers in completed-task summaries.

Impact: the public/framework branch carries work-specific references outside the declared exemption set.

Evidence:
- `ai_context/handoff.md:74`
- `ai_context/handoff.md:76`
- `ai_context/conventions.md:109`
- `ai_context/conventions.md:114`
- `docs/todo_list_archived.md:93`
- `docs/todo_list_archived.md:98`
- `docs/todo_list_archived.md:103`

**M7** `simulation/retrieval/load_strategy.md:94` — Simulation retrieval design references world artifact paths not produced or manifest-described by extraction.

The retrieval design lists `world/events/`, `world/locations/`, `world/factions/`, and `world/history/timeline.jsonl` as structured expansion paths. Current world manifest schema and writer only expose foundation, fixed relationships, stage catalog, stage snapshots, and world event digest. Current status also says timeline/location info is currently inlined rather than standalone.

Impact: no executable runtime is broken yet, but a future loader following `load_strategy.md` would chase unproduced/unmanifested paths.

Evidence:
- `simulation/retrieval/load_strategy.md:94`
- `schemas/world/world_manifest.schema.json:31`
- `extraction/persona_extraction/lifecycle/manifests.py:167`
- `ai_context/current_status.md:15`
- `ai_context/current_status.md:36`

**M8** `works/README.md:213` — `analysis/conflicts/` is documented but has no clear tracked/local rule.

`works/README.md` and `docs/architecture/data_model.md` list `works/{work_id}/analysis/conflicts/`, while current status says only `stage_plan`, `candidate_characters`, and `consistency_report` are tracked under `analysis/`. `.gitignore` ignores progress/summaries/splits/evidence but not `conflicts/`, and no current code writer was found.

Impact: if a future writer creates `analysis/conflicts/`, it will surface as untracked with unclear handling.

Evidence:
- `works/README.md:213`
- `docs/architecture/data_model.md:488`
- `ai_context/current_status.md:45`
- `.gitignore:7`

### Low

**L1** `ai_context/architecture.md:158` — Compressed context describes `.partial_prev` as flat, while code writes per-character subdirectories.

`ai_context/architecture.md`, `ai_context/decisions.md`, and `docs/requirements.md` describe `.partial_prev/{prev_stage_id}_{lane}.json`. Code and `docs/architecture/extraction_workflow.md` use `.partial_prev/{char_id}/{prev_stage_id}_{lane}.json`.

Impact: future agents relying on compressed handoff docs may inspect or clean the wrong scratch path. Git safety is unaffected because `analysis/progress/` is ignored.

Evidence:
- `ai_context/architecture.md:158`
- `ai_context/decisions.md:452`
- `docs/requirements.md:1005`
- `extraction/persona_extraction/lifecycle/lane_output.py:98`
- `extraction/persona_extraction/orchestrator.py:1238`
- `docs/architecture/extraction_workflow.md:308`

**L2** `docs/requirements.md:3339` — Requirement summaries retain stale phase/default labels.

The storage summary labels `foundation.json` as Phase 2 even though nearby requirements and architecture describe Phase 1 foundation output. The flow diagram still says Phase 0 chunks are roughly 25 chapters, while the detailed text and config use default 20.

Impact: low runtime risk, but it sends future agents to the wrong mental model.

Evidence:
- `docs/requirements.md:773`
- `docs/requirements.md:839`
- `docs/requirements.md:3339`
- `extraction/config.toml:38`

**L3** `schemas/analysis/chapter_summary_chunk.schema.json:57` — Chunk schema descriptions preserve old Phase 2 foundation wording.

The schema top description is current, but several field descriptions still say Phase 2 synthesizes foundation fields and line 87 describes a post-Phase-1.5 mapping path that conflicts with the current raw-name Phase 1 double-pipe.

Impact: schema descriptions are part of the data-contract surface read by agents and LLM prompt builders; stale prose can preserve the wrong flow despite valid field shapes.

Evidence:
- `schemas/analysis/chapter_summary_chunk.schema.json:5`
- `schemas/analysis/chapter_summary_chunk.schema.json:57`
- `schemas/analysis/chapter_summary_chunk.schema.json:65`
- `schemas/analysis/chapter_summary_chunk.schema.json:87`
- `schemas/analysis/chapter_summary_chunk.schema.json:119`

**L4** `extraction/validation/gates/phase2_baseline.py:3` — Active validator docstring still names removed baseline files.

The Phase 2 gate docstring says it checks "skeleton voice/behavior/boundary/failure-mode files", but those independent baseline files have been removed and the function checks manifests/foundation/fixed relationships/identity/target_baseline.

Impact: low runtime risk, but stale internal docs make the validation surface look broader/different than it is.

Evidence:
- `extraction/validation/gates/phase2_baseline.py:3`
- `extraction/validation/gates/phase2_baseline.py:82`
- `ai_context/architecture.md:91`

## Alignment Summary

Strongly aligned:
- Main branch artifact policy is mostly intact: tracked `works/` is only `works/README.md`, and tracked user data is limited to `users/README.md` plus `users/_template/`.
- Core extraction package paths now consistently use `extraction/` rather than the old top-level package in active code, excluding historical archive prose.
- Phase 1 lane split, Phase 3 sub-lane structure, Phase 2 overwrite guard, Phase 3 target-key equality, Phase 3 commit ordering, and Phase 4 scene validation are largely represented in code and current architecture docs.

Least aligned:
- Foundation/key-figures contracts are split across schema, active prompts, docs, and `ai_context`.
- Phase/repair guarantees in `docs/requirements.md` overstate current implementation strength.
- Some skill and runtime-design paths drift from actual generated paths.
- Archived todo prose now conflicts with the work-agnostic docs policy.

## Residual Risks

- Phase 2 still has no repair lifecycle; this is already tracked as `T-PHASE2-REPAIR-AGENT`.
- `light_novel` `stage_plan.chapter_count=1` is intentionally schema-invalid today; this is tracked as `T-LIGHTNOVEL-SCHEMA-ONEOF` and remains safe only while no external strict validator consumes that artifact.
- `simulation/` is design-only, so runtime path drift is not a live code defect yet, but it can become one when loader code starts.
- Local ignored `works/<work_id>/...` extraction residue exists on disk, but it is not tracked and did not affect git status.

## Open Questions / Ambiguities

**OQ1** Should `foundation.json` require its core fields (`genre`, `tone`, `world_structure`, `power_system`, `major_factions`, `world_lines`, `core_rules`) now that it is a Phase 1 LLM product and runtime Tier 0 input, or is a sparse extension-friendly schema intentional?

**OQ2** Should `major_factions[].key_figures` be required on every faction with an empty array allowed, or optional only when a faction has no observed figures? Current prompt says "must write", schema says optional.

**OQ3** Are exact numeric bounds in extraction prompts allowed despite `ai_context/conventions.md` saying bounds live only in schema? The repo already has `T-PROMPT-SCHEMA-INJECT`, so this may be an accepted temporary violation rather than a bug.

**OQ4** Should `docs/todo_list_archived.md` be added to the explicit "history is exempt" list, or should work-specific identifiers be scrubbed from archived todo summaries?

**OQ5** Should Phase 2 produce empty `stage_catalog.json` files, or should catalogs be purely programmatic Phase 3 post-processing artifacts? The prompt still asks Phase 2 LLM to create empty catalogs, but Phase 2 validation does not check them.

## False Positives Checked

- `users/_template/` placeholders are intentionally not schema-valid until substituted; `ai_context/skills_config.md:86` documents this.
- Local ignored `works/<work_id>/...` artifacts were not treated as branch leaks; `git ls-files works users/_template` confirms the intended tracked set.
- `light_novel` schema-invalid `chapter_count=1` is known and tracked; not counted as a new finding.
- `__pycache__` files under `extraction/` are ignored and not tracked.
- `AGENTS.md` and `CLAUDE.md` differ in reciprocal title/sync wording only after normalizing the entry title; not counted as a mirror violation in this review.

## Recommendations

- H1 — 修：make post-processing tolerate missing/invalid `memory_importance` by returning a warning/error instead of raising, or move schema validation before digest generation so repair can own the failure.
- H2 — 修：replace PID lock acquisition with atomic create/open (`O_CREAT|O_EXCL`) or a sibling `flock`, and collapse the double pre-check pattern into the atomic acquire path.
- H3 — 修：enforce exact chapter set equality for Phase 0 chunks: count, uniqueness, and expected `C####` range.
- H4 — 修：decide the real foundation/key_figures contract, then align schema required fields, prompts, `ai_context/conventions.md`, Phase 1 skip logic, and Phase 2 validation.
- M1 — 修：extend ingestion validation to verify `normalized_path` existence and/or the canonical `chapters/C####.txt` files used by prompt builders.
- M2 — 修：make JSONL slice write-back replace the whole current-stage slice, preserving only non-current-stage full entries.
- M3 — 修：only mark `phase_2` done after baseline commit succeeds, or make baseline commit failure fatal before Phase 3 starts.
- M4 — 修：update `docs/requirements.md` to match current Phase 2 schema/tolerance-only behavior, while leaving `T-PHASE2-REPAIR-AGENT` as future work.
- M5 — 修：update `ai_context/skills_config.md` process log path to `works/*/analysis/progress/extraction_logs/`.
- M6 — 修或明确豁免：either scrub work-specific identifiers from `docs/todo_list_archived.md`, or document that archived todo summaries are history-exempt.
- M7 — 留 todo：defer until simulation loader implementation, but mark those paths as future/unproduced in `simulation/retrieval/load_strategy.md`.
- M8 — 修：decide whether `analysis/conflicts/` is tracked or local, then update `.gitignore`, `current_status.md`, and structure docs.
- L1 — 修：refresh compressed `ai_context` / requirements `.partial_prev` paths to include `{char_id}`.
- L2 — 修：refresh stale Phase 0 default and foundation phase labels in `docs/requirements.md`.
- L3 — 修：update stale Phase 2 wording in chunk schema descriptions.
- L4 — 修：update the Phase 2 validator docstring to the current files it checks.
- OQ1 — 建议修：runtime Tier 0 should not accept a skeletal foundation unless there is an explicit sparse-mode design.
- OQ2 — 建议修：require the array key with empty array allowed; it gives Phase 2 a stable replacement surface without forcing invented figures.
- OQ3 — 建议留 todo：resolve through `T-PROMPT-SCHEMA-INJECT` rather than opportunistic edits.
- OQ4 — 建议修或豁免二选一：make the policy explicit so future reviewers do not keep rediscovering it.
- OQ5 — 建议修：remove Phase 2 empty-catalog LLM responsibility unless a validator and downstream reason are added.
