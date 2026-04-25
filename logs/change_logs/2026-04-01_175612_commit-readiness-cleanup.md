# 2026-04-01 17:56:12 - Commit Readiness Cleanup

## Summary

Performed a final consistency pass before commit.

## Changes

- Updated `.gitignore` to match the current architecture more closely:
  - ignore work-scoped evidence artifacts under `works/*/analysis/evidence/`
  - ignore work-scoped index bodies under `works/*/indexes/`
  - removed stale top-level `sessions/` and `runtime/` ignore rules
- Corrected `ai_context/decisions.md` so canonical work assets no longer imply
  work-local runtime or user-state ownership
- Clarified `ai_context/handoff.md` by separating:
  - canonical construction flow
  - user/runtime flow
- Removed one remaining "simulation-relevant" wording mismatch from the work
  package README
