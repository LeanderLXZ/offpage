# Phase 2.5 Baseline Skeleton + world/social/ Removal + Phase 4 Retry Fix

Date: 2026-04-10

## Changes

### 1. Phase 2.5 Baseline Skeleton Production

Phase 2.5 now produces skeleton drafts of all character baseline files
(previously only identity.json and manifest.json):

- `voice_rules.json` — baseline language style
- `behavior_rules.json` — baseline behavior patterns
- `boundaries.json` — character boundaries and hard limits
- `failure_modes.json` — character failure modes

All marked `source_type: inference`. Subsequent batches refine with raw text
evidence (upgrading to canon). These files record **cross-stage stable character
foundations** — inherent style, behavior, boundaries — not stage-specific changes.

**Files changed:**
- `automation/prompt_templates/baseline_production.md` — added 4 file sections
- `automation/persona_extraction/prompt_builder.py` — added 4 schemas to file list
- `automation/persona_extraction/orchestrator.py` — added existence checks (warn)
- `automation/persona_extraction/validator.py` — added schema validation (warning level)
- `automation/prompt_templates/character_extraction.md` — updated rule 3 and output section
- `automation/prompt_templates/coordinated_extraction.md` — same updates (legacy)

### 2. Remove world/social/ Directory Layer

`world/social/` (fixed_relationships + stage_relationships) removed as redundant:
- Fixed relationships already in `identity.json` → `key_relationships`
- Stage relationships already in `world_stage_snapshot` → `relationship_shifts`
- No schema existed for social/ files

**Files changed:**
- `automation/prompt_templates/world_extraction.md` — removed social reference
- `automation/prompt_templates/coordinated_extraction.md` — same
- `docs/architecture/data_model.md` — replaced social section with note
- `docs/architecture/extraction_workflow.md` — removed social from output list
- `simulation/flows/startup_load.md` — removed from load sequence
- `simulation/retrieval/load_strategy.md` — removed from Tier 0 and Tier 1
- `simulation/contracts/baseline_merge.md` — updated accordingly
- `simulation/README.md` — removed from startup list
- `works/README.md` — removed directory tree entry and description
- `ai_context/architecture.md` — removed from world description and load formula

### 3. Phase 4 Retry Bug Fix

Two bugs fixed in scene archive retry:

**Bug A: reset_failed() cleared retry_count on every --resume**
- `retry_count` was reset to 0, preventing escalation to ERROR state
- Chapters failed → resume → reset to 0 → fail again → infinite loop
- Fix: `reset_failed()` now preserves `retry_count`

**Bug B: No error feedback on retry**
- Prompt had no information about prior failure, LLM produced same error
- Fix: `build_scene_split_prompt()` accepts `prior_error` kwarg
- `_process_chapter()` passes `entry.error_message` when `retry_count > 0`
- `scene_split.md` template gains `{retry_note}` placeholder

**Files changed:**
- `automation/persona_extraction/scene_archive.py` — reset_failed + _process_chapter
- `automation/persona_extraction/prompt_builder.py` — prior_error parameter
- `automation/prompt_templates/scene_split.md` — retry_note placeholder

### 4. Documentation Updates

- `docs/requirements.md` — all three changes reflected in §9.2, §9.4, §9.6, §11.4.2, §11.5, §11.11, flow diagrams
- `ai_context/decisions.md` — decision 13 updated
- `docs/architecture/extraction_workflow.md` — Phase 2.5 and baseline sections
- `simulation/contracts/baseline_merge.md` — extraction workflow section

## Review Checklist

- [x] No remaining `world/social/` references (except historical logs)
- [x] No remaining "首批新建" references for baseline files
- [x] `retry_count` not cleared in `reset_failed()`
- [x] `{retry_note}` wired through template → builder → caller
- [x] All imports pass
- [x] `reset_failed()` preserves retry_count (verified programmatically)
