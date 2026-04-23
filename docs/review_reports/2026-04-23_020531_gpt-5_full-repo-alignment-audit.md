**Review 模型**：Codex（`gpt-5`）

# Full Repo Alignment Audit

## Findings

### High

#### H1. Repairing current-stage slices of accumulated JSONL can truncate prior-stage digest entries

`ExtractionOrchestrator._build_repair_file_entries()` filters accumulated `.jsonl` files down to entries matching the current stage, but keeps the original accumulated file path:

- `automation/persona_extraction/orchestrator.py:486-522`

The repair stack writes the patched in-memory list back to that same path:

- `automation/repair_agent/field_patch.py:44-49`
- `automation/repair_agent/fixers/local_patch.py:83-88`

Impact: if `memory_digest.jsonl` or `world_event_digest.jsonl` current-stage entries are repaired, previous committed stage entries can be overwritten by the filtered current-stage subset. This would silently damage runtime retrieval indexes and then be included by the normal stage commit path.

#### H2. Post-processing runs before repair, so repair can make derived digests/catalogs stale

Phase 3 generates `memory_digest.jsonl`, `world_event_digest.jsonl`, and stage catalogs before the repair agent runs:

- `automation/persona_extraction/orchestrator.py:1569-1584`
- `automation/persona_extraction/orchestrator.py:1617-1624`

The stage is then committed after repair:

- `automation/persona_extraction/orchestrator.py:1790-1796`

But Phase 3.5 only checks memory ID presence and world event counts, not `memory_digest.summary == memory_timeline.digest_summary` or `world_event_digest.summary == world stage_events[i]`:

- `automation/persona_extraction/consistency_checker.py:415-448`
- `automation/persona_extraction/consistency_checker.py:590-654`

Impact: if repair changes `digest_summary`, `stage_events`, or catalog source fields, runtime-facing derived files can remain stale while still passing the documented 1:1 correspondence expectations.

#### H3. Snapshot schemas do not enforce the core self-contained snapshot contract

The character snapshot prompt requires all runtime dimensions to be present, including `active_aliases`, `voice_state`, `behavior_state`, `boundary_state`, `relationships`, `knowledge_scope`, `stage_events`, `stage_delta`, and `character_arc`:

- `automation/prompt_templates/character_snapshot_extraction.md:35-48`

The schema reference also states snapshots must be self-contained:

- `docs/architecture/schema_reference.md:200-214`

But the character snapshot schema only requires metadata plus `snapshot_summary`:

- `schemas/character/stage_snapshot.schema.json:8-15`

The world requirements similarly list stage events, current state, relationship shifts, character status changes, location/map changes, and evidence refs as expected world snapshot content:

- `docs/requirements.md:75-97`

But the world snapshot schema only requires metadata plus `snapshot_summary`:

- `schemas/world/world_stage_snapshot.schema.json:7-13`

Impact: L1 schema validation can pass roleplay-useless snapshots. The system currently depends on prompts and later structural/semantic checks to enforce the most important runtime contract, despite docs repeatedly presenting schema gates as hard protection.

#### H4. Phase 3.5 output is written after the final stage commit and is not committed before squash/final checkout

Per-stage commits happen inside `_process_stage()`:

- `automation/persona_extraction/orchestrator.py:1790-1796`

After all stages are committed, the orchestrator runs Phase 3.5, saves `consistency_report.json`, immediately offers squash merge, and then runs Phase 4:

- `automation/persona_extraction/orchestrator.py:1240-1248`
- `automation/persona_extraction/orchestrator.py:1820-1837`
- `automation/persona_extraction/orchestrator.py:1866-1904`

There is no commit for `works/{work_id}/analysis/consistency_report.json`, even though `ai_context/current_status.md` says that file is tracked:

- `ai_context/current_status.md:160-164`

Additionally, Phase 3.5 loaders can write L1 JSON repairs while checking:

- `automation/persona_extraction/consistency_checker.py:153-170`
- `automation/persona_extraction/json_repair.py:224-228`
- `automation/persona_extraction/json_repair.py:299-300`

Impact: if the user skips squash merge, the uncommitted report/repairs make `checkout_master()` refuse to return to `master` under the extraction scope. If squash proceeds, uncommitted/untracked Phase 3.5 outputs are not part of the extraction branch commit being squashed, so the final master commit can omit the documented report.

### Medium

#### M1. Runtime startup memory contract conflicts on whether all historical `memory_timeline` files load

Current architecture says startup loads only the recent two memory stages in full and uses `memory_digest.jsonl`/FTS5 for distant history:

- `ai_context/requirements.md:96-98`
- `simulation/retrieval/load_strategy.md:38-45`

But `simulation/contracts/baseline_merge.md` still says `memory_timeline/{stage_id}.json × stages 1..N` is Tier 0 startup:

- `simulation/contracts/baseline_merge.md:30-37`

Impact: runtime implementation could accidentally load every historical memory file at startup, breaking the token-budget and tiered-retrieval design.

#### M2. Phase 4 `concurrency` config is not used as the CLI default

`automation/config.toml` defines `[phase4].concurrency`:

- `automation/config.toml:67-72`

But the CLI `--concurrency` default always uses `cfg.phase0.concurrency`, while the help text claims it comes from both phase0 and phase4:

- `automation/persona_extraction/cli.py:100-107`

That value is then passed into standalone Phase 4:

- `automation/persona_extraction/cli.py:153-163`

Impact: changing `[phase4].concurrency` has no effect unless the operator also passes `--concurrency`. This undermines the single-source TOML config contract for Phase 4 tuning.

#### M3. `ai_context/architecture.md` has stale config override precedence

Requirements and code agree on:

`CLI flag > config.local.toml > config.toml > dataclass defaults`

Evidence:

- `docs/requirements.md:2321-2330`
- `automation/persona_extraction/config.py:7-12`
- `automation/persona_extraction/config.py:228-238`
- `ai_context/decisions.md:280-284`

But `ai_context/architecture.md` still says:

`CLI flag > env > config.toml > config.local.toml`

Evidence:

- `ai_context/architecture.md:390-394`

Impact: because `ai_context/` is loaded first by future agents, this stale compressed-truth file can reintroduce a removed env layer or reverse local override semantics.

#### M4. `ai_context/current_status.md` is stale relative to local progress and extraction branch state

`ai_context/current_status.md` says Phase 3 was reset to a fresh start and all 49 stages are pending:

- `ai_context/current_status.md:5-8`
- `ai_context/current_status.md:30-34`

Current local progress shows `S001` committed and `S002` in error. The extraction branch also contains committed `S001` stage artifacts. This is a current-state drift rather than a code bug.

Impact: a future agent following `ai_context` may assume it should resume from a clean Phase 3 start, rather than handling an existing committed stage and an errored next stage.

#### M5. Formal world data model still lists unschematized world package files as required

`docs/architecture/data_model.md` lists additional world files such as `history/timeline.jsonl` as required:

- `docs/architecture/data_model.md:204-222`

But `ai_context/current_status.md` explicitly says world schemas for foundation, timeline, events, locations, maps, and state snapshots remain incomplete:

- `ai_context/current_status.md:150-152`

`docs/architecture/schema_reference.md` currently lists only five world schemas:

- `docs/architecture/schema_reference.md:8-13`

Impact: docs imply deliverables that extraction/runtime cannot yet schema-gate. Either those files should be marked planned, or schema coverage should be expanded before treating them as required.

## Open Questions / Ambiguities

- Should Phase 3.5 be a committed extraction-data milestone before squash merge, or should `consistency_report.json` be considered local-only despite `ai_context/current_status.md` saying it is tracked?
- Should schema L1 enforce the full self-contained snapshot contract, or is that intentionally delegated to L2/L3 repair checks? Current docs imply schema hard gates should carry more of this burden.
- Should `[phase0].concurrency` and `[phase4].concurrency` remain one CLI flag with phase-sensitive defaults, or should Phase 4 get a separate flag/default path?

## Alignment Summary

- Strongly aligned: stage ID convention (`S###`), config loader/code docs outside `ai_context/architecture.md`, branch return-to-master intent, and the high-level Phase 3 lane model.
- Most misaligned: Phase 3 derived-file lifecycle, Phase 3.5 finalization/commit semantics, schema strength vs prompt/runtime contract, and a few stale compressed-context statements.

## False Positives Checked

- Commit ordering for individual stages is correctly implemented: `commit_stage()` is attempted before `COMMITTED`, and no SHA transitions to `FAILED`.
- Branch return-to-master is wired through `finally`; the remaining concern is the uncommitted Phase 3.5 output making that best-effort checkout refuse to switch.
- Stage ID conventions appear consistently migrated to `S###` with sibling `stage_title`.
- Length gates for `stage_events`, `memory_timeline.event_description`, and `digest_summary` are present in schemas; the schema gap is missing required sections, not missing length constraints.

## Residual Risks

- The artifact audit subagent did not return a final message before timeout. A separate untracked report appeared at `docs/review_reports/2026-04-23_015308_opus-4-7_full-review-findings.md`; I left it untouched and did not fully integrate it into this report.
- I did not run the full automation test/smoke suite; findings are static-code/doc review findings.
- Prior review reports were not used as a primary source, per full-review read-scope guidance; unresolved older findings may still exist outside the issues above.

## Suggested Landing Order

1. Fix H1/H2 together: make JSONL repair patch accumulated files safely, and rerun post-processing after any repair that touches digest/catalog source files.
2. Fix H4: decide and implement the Phase 3.5 report commit/finalization contract.
3. Fix H3: either strengthen schemas or document that L2/L3, not schema, owns self-contained snapshot completeness.
4. Fix M1/M2/M3/M4: low-risk doc/config alignment that will prevent future agent drift.
5. Resolve M5 when expanding world schemas.
