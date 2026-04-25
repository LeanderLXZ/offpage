# AI Context And Docs Cleanup

Timestamp: 2026-04-02 16:21 EDT

## Summary

Major cleanup of `ai_context/` to remove redundancy between files and with
`docs/architecture/`. Also patched `docs/architecture/` to reflect the newly
added `character_state.json`.

## What Changed

### ai_context/ — compressed (~2260 lines removed, ~330 lines added)

- **architecture.md**: reduced from ~732 to 81 lines. Now a compressed summary
  pointing to `docs/architecture/` for details. Removed full duplicates of
  layer descriptions, load formulas, stage models, and lifecycle rules.
- **current_status.md**: reduced from ~364 to 56 lines. Removed 50+ changelog-
  style "what has been completed" bullets. Now: stage, what exists, what's
  missing, active rules.
- **decisions.md**: reduced from ~465 lines (76 decisions) to 71 lines (26
  decisions). Merged redundant items, removed decisions already embodied in
  architecture docs.
- **handoff.md**: reduced from ~283 to 47 lines. Removed all content already
  present in other ai_context files.
- **instructions.md**: reduced from ~173 to 67 lines. Condensed update rules.
- **next_steps.md**: reduced from ~229 lines (29 items) to 44 lines (13
  items). Consolidated duplicates.
- **read_scope.md**: reduced from ~91 to 36 lines.

### docs/architecture/ — gap fixes

- **data_model.md**: added `character_state.json` to User Package contents
  list and startup-required user load list.
- **system_overview.md**: added `character_state.json` to simulation engine
  continuous writeback list.

## Motivation

ai_context files had grown to contain massive overlap with each other and with
docs/architecture/. The handoff layer should be compressed summaries, not full
duplicates. Additionally, the recently added context-level character state was
missing from docs/architecture/.
