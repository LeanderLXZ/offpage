# 2026-04-01 17:40:47 - Work Package Filesystem Restructure

## Summary

The repository layout was actually migrated on disk, not only in docs.

## Changes

- Created the first real simulation package root:
  - `works/wo-he-nvdi-de-jiushi-nieyuan/`
- Added the initial subtree scaffold:
  - `world/`
  - `characters/`
  - `users/`
  - `analysis/`
  - `runtime/`
  - `indexes/`
- Moved the persistent candidate-character analysis file into:
  - `works/wo-he-nvdi-de-jiushi-nieyuan/analysis/incremental/candidate_characters_initial.md`
- Narrowed top-level `users/` to the optional global-profile role:
  - `users/profiles/`

## Intent

This makes the work-scoped simulation package visible in the actual repo tree
and reduces confusion from older top-level scaffolds like `characters/`,
`worlds/`, `runtime/`, and `sessions/`.
