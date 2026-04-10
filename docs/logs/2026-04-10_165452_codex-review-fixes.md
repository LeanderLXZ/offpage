# Codex Review Fixes

Date: 2026-04-10

## Summary

Fixed 5 code bugs and 1 stale-docs issue found by Codex cross-review,
plus clarified 2 open questions in requirements.md. Added 9th consistency
check (world_event_digest correspondence) and aligned all docs.

## 7 Changes

1. **Phase 3.5 error must block Phase 4** (code): `_run_consistency_check()`
   now returns `bool`. Phase 4 (scene archive) only runs when consistency
   check passes. `--start-phase 4` can bypass this gate for standalone runs.

2. **Relationship continuity field names** (code): `_check_relationship_continuity`
   in `consistency_checker.py` corrected from `target`/`target_id`/`trust_level`/
   `intimacy_level` to schema-correct `target_character_id`/`target_label`/
   `trust`/`intimacy`. Also fixed integer 0 comparison (`is not None` instead
   of truthiness check).

3. **Post-targeted-fix re-validation gate** (code): `review_lanes.py` now
   checks `re_report.passed` after targeted fix before proceeding to semantic
   re-review. Previously the re-validation result was computed but not gated on.

4. **world_event_digest best-effort fields** (code): `generate_world_event_digest`
   now accepts `character_names` parameter and populates `involved_characters`
   via substring matching of known character names against event text. The caller
   resolves canonical names + aliases from `identity.json`.

5. **world_event_digest consistency check** (code): New
   `_check_world_event_digest` in `consistency_checker.py` verifies digest
   entry count matches world snapshot `key_events` count per stage. Total
   consistency checks: 8 → 9.

6. **Stale batch_001 claims removed** (docs): `current_status.md` and
   `handoff.md` no longer reference specific batch numbers. Pipeline status
   described generically ("extraction underway", "iterative testing").

7. **Phase 2.5 / Phase 4 clarifications** (docs): requirements.md Phase exit
   validation table now distinguishes critical files (error, blocks Phase 3)
   from skeleton files (warning, non-blocking). Phase 3.5 → Phase 4 blocking
   documented explicitly. "完全独立" → "数据独立" throughout to distinguish
   data independence from execution gating.

## Files Modified

**Code**:
- `automation/persona_extraction/orchestrator.py` — `_run_consistency_check`
  returns bool; Phase 4 gated on result
- `automation/persona_extraction/consistency_checker.py` — relationship field
  names fixed; added `_check_world_event_digest`; total checks 8 → 9
- `automation/persona_extraction/review_lanes.py` — `re_report.passed` gate
  after targeted fix
- `automation/persona_extraction/post_processing.py` — `character_names` param
  for `generate_world_event_digest`; caller resolves names from identity.json

**Documentation**:
- `docs/requirements.md` — Phase 2.5 validation severity split (error vs
  warning); Phase 3.5 blocking note; consistency check table #6 split into
  #6 + #9; "完全独立" → "数据独立"; check count 8 → 9
- `docs/architecture/extraction_workflow.md` — consistency check list +9;
  Phase 4 "数据独立" + blocking note
- `ai_context/architecture.md` — check count 8 → 9
- `ai_context/current_status.md` — removed stale batch_001 claims; check
  count 8 → 9
- `ai_context/handoff.md` — removed batch_001 reference
- `automation/README.md` — check count 8 → 9; Phase 4 "数据独立"
