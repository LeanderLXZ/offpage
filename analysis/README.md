# Analysis

This directory stores extraction-side incremental outputs and supporting
evidence.

Planned layout:

```text
analysis/
  incremental/
  evidence/
```

Recommended use:

- top-level `analysis/` is best treated as pipeline scratch space, experiments,
  and transitional extraction storage
- persistent simulation-needed work analysis should move toward:
  - `works/{work_id}/analysis/`
  - `works/{work_id}/analysis/evidence/`
- the first persistent analysis file has already been moved into:
  - `works/wo-he-nvdi-de-jiushi-nieyuan/analysis/incremental/`
- user conversation history, user-role drift, and user-specific events should
  not be stored here
