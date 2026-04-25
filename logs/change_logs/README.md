# Change Logs

This directory is for timestamped historical records of meaningful project
changes.

Its purpose is:

- preserve why a change happened
- preserve important decisions that may later need provenance
- avoid forcing future AI sessions to reread full chat history

## What Belongs Here

- architecture milestones
- schema changes
- important workflow changes
- major extraction pipeline changes
- meaningful terminal or service integration changes

## What Does Not Belong Here

- raw novel text
- long chapter dumps
- full user conversation histories
- database exports
- vector indexes
- embeddings
- large generated artifacts
- copied runtime outputs

Logs should summarize changes, not archive bulk project data.

## Suggested Naming

Use timestamped filenames in local New York time, for example:

```text
2026-04-01_160500_initial-architecture-scaffold.md
```

## Practical Rule

If a log entry would require pasting large source text or binary-like data, do
not put that content here. Summarize it and point to the canonical source
location instead.

## Git Rule

Timestamped log entries under `logs/change_logs/` are git-tracked. They are
lightweight text summaries and should remain small enough to commit without
concern. Do not paste large source text, database dumps, or binary data into
log files.
