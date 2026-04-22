# Handoff

## Mental Model

Architecture agreed, scaffold created, extraction in progress. One real
work package under stage extraction. No finished character packages, no
real user packages, no runtime code.

## Quick Start

1. Read all of `ai_context/` (order in `instructions.md`).
2. On follow-up, continue from `ai_context/` + user request. Don't route
   through `prompts/` unless asked.
3. Architecture detail → `docs/architecture/system_overview.md`,
   `data_model.md`, `schema_reference.md`.
4. Runtime flow → `simulation/README.md`, `simulation/flows/`,
   `simulation/retrieval/`, `simulation/prompt_templates/`.
5. Extraction pipeline → `automation/README.md`.
6. Current work → start from existing metadata / analysis, not raw
   chapters.

## Current Work Continuation

One Chinese web novel is onboarded and in progress. Actual `work_id`
lives under `works/` and `sources/works/`.

### Resume extraction

```bash
# Foreground
python -m automation.persona_extraction "<work_id>" --resume

# Background (survives SSH disconnect), 6h cap
python -m automation.persona_extraction "<work_id>" \
    --resume --background --max-runtime 360

# Follow log
tail -f works/<work_id>/analysis/progress/extraction.log
```

`jsonschema` is a HARD dep in `automation/pyproject.toml` — validator
raises ImportError without it.

Pipeline checks PID lock and clean git tree before starting. See
`automation/README.md` for full CLI.

### Post-extraction manual repair

`prompts/review/手动补抽与修复.md` for targeted fixes;
`prompts/review/数据包审校.md` for full package review.

## What The User Cares About

- Deep roleplay, not shallow mimicry or generic AI tone
- Preserve stage differences and knowledge boundaries
- Don't reduce analysis to ordinary literary summary
- Don't leak memory across contexts or write the character as
  omniscient
- Don't blur canon and inference without labeling
- Incremental updates, never restart from scratch
- Don't rewrite Chinese canon into English summaries
- Don't paste large raw text into logs, docs, or answers
- Don't put specific book names, character names, chapter names, or
  plot details in docs, requirements, README, prompt templates,
  schemas, or `ai_context/` — use generic placeholders ("角色A",
  "<work_id>", `S001` for `stage_id`). Only `works/`, `sources/`, and
  `docs/logs/` may contain work-specific references.

## After Each Milestone

1. Write a log entry under `docs/logs/` with HHMMSS timestamp
   (mandatory for schema / architecture / prompt / simulation /
   directory changes).
2. Update `current_status.md`, `next_steps.md`, and this file.
