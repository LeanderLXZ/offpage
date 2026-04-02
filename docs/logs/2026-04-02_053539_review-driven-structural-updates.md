# Review-Driven Structural Updates

**Timestamp:** 2026-04-02 05:35 ET

## Summary

After a full codebase review against `ai_context/` requirements, the following
structural and documentation changes were made based on user feedback.

## Changes

### 1. `.gitignore` — Stopped Excluding Canonical Work Assets

- Removed exclusion rules for `works/*/analysis/incremental/` and
  `works/*/indexes/`.
- These are structured extraction outputs and retrieval indexes that belong in
  the canonical work package and should be tracked by git.

### 2. World Social Layer — Fixed vs. Dynamic Relationship Split

- Added `social/fixed_relationships/` alongside the existing
  `social/stage_relationships/`.
- Fixed relationships are immutable structural bonds that hold across all
  stages (e.g. parent-child, sibling, blood-relative ties).
- Dynamic (stage) relationships evolve over time (e.g. romantic involvement,
  alliances, rivalries).
- Runtime should load all fixed relationships at startup plus the selected
  stage's dynamic relationship file.
- Updated: `docs/architecture/data_model.md`, world manifest,
  `ai_context/architecture.md`, `ai_context/handoff.md`,
  `ai_context/decisions.md` (Decision #72).

### 3. Source Work Package Construction Specification

- Added a step-by-step construction guide to `docs/architecture/data_model.md`.
- This is not a formal JSON schema but a specification for how to build a
  well-formed source package (raw placement, normalization, chapter splitting,
  metadata creation).
- Recorded as Decision #73.

### 4. User Package Template

- Created `users/_template/` with placeholder files covering the full user
  directory structure: `profile.json`, `role_binding.json`,
  `long_term_profile.json`, `relationship_core/`, `contexts/`, `sessions/`,
  `conversation_library/`.
- Updated `.gitignore` to allow `users/_template/` through.
- Updated `users/README.md` to reference the template.

### 5. Prompts Naming Language Explanation

- Added a "naming language" section to `prompts/README.md` explaining that
  prompt files use Chinese for maintainer readability, while `ai_context/`
  uses English for AI handoff.

### 6. Logs Reading Restriction for AI Agents

- Added explicit instruction to `ai_context/instructions.md` that AI agents
  should not proactively read `docs/logs/`.
- Logs should only be read when the user explicitly asks, rollback is needed,
  or decision provenance must be verified.
- Recorded as Decision #74.

### 7. `ai_context/` Sync

- Updated `current_status.md` with a "Recent Additions" section.
- Added Decisions #72–#75 to `decisions.md`.
- Updated `handoff.md` with social split details, logs policy, user template
  reference, and git tracking notes.

## Decisions Added

- **#72:** World relationships split into fixed and dynamic categories.
- **#73:** Source packages use a documented specification, not a formal schema.
- **#74:** `docs/logs/` should not be proactively read by AI agents.
- **#75:** `works/*/analysis/incremental/` and `works/*/indexes/` are tracked
  by git.
