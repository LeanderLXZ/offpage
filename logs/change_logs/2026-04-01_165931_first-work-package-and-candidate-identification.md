# First Work Package And Candidate Identification

## Summary

- Confirmed the first real source work package is present under:
  - `sources/works/wo-he-nvdi-de-jiushi-nieyuan/`
- Confirmed the work package is normalized from a local `epub` and currently
  contains `537` normalized chapter files.
- Added the first-pass candidate-character identification artifact:
  - `works/wo-he-nvdi-de-jiushi-nieyuan/analysis/incremental/candidate_characters_initial.md`
- Updated `ai_context/` so future AI sessions no longer start from the outdated
  assumption that no real novel corpus has been imported yet.

## Why This Was Needed

- The repository state had moved beyond the original architecture-only
  baseline.
- The earlier AI handoff files still described the project as having no real
  corpus and no real source onboarding.
- A resumable local artifact was needed so candidate-character identification
  would not live only in transient chat context.

## Identification Scope

The new candidate-character file was intentionally kept lightweight.

It used:

- work-package metadata
- chapter-title scan
- lightweight mention statistics across normalized chapters
- small targeted chapter reads

It did not use:

- a full-novel read
- long raw-text copying
- large evidence dumps

## High-Level Result

Current leading candidate roles include:

- `王枫`
- `姜寒汐`
- `萧浩`
- `楚妍儿`
- `冷凝月`
- `苏婉`
- `许青枫`
- `柳青瑶`
- `楚沫兮`
- `秦羽溪`

`哈弟` was noted separately as an important non-human recurring companion.

## Next Recommended Step

- Let the user choose one or two target characters from the current candidate
  list.
- Begin incremental batch extraction rather than whole-book role construction.
- Keep the fixed 7-part per-batch structure and preserve evidence traceability.
