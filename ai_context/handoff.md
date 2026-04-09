# Handoff

## Mental Model

Architecture agreed, scaffold created, extraction in progress. There is
one real work package with batch_001 extracted, no finished character
packages yet, no real user packages, and no runtime code.

## Quick Start

1. Read all of `ai_context/` first.
2. On first follow-up, continue from `ai_context/` + the user request. Do not
   proactively route through `prompts/` unless the user asks.
3. For architecture details, read `docs/architecture/system_overview.md` and
   `docs/architecture/data_model.md`.
4. For schema documentation, read `docs/architecture/schema_reference.md`.
5. For runtime flow details, read `simulation/README.md` and relevant files
   under `simulation/flows/`, `simulation/retrieval/`, and
   `simulation/prompt_templates/`.
6. For the automated extraction pipeline, read `automation/README.md`.
7. For the current work, start from existing metadata and analysis, not raw
   chapters.

## Current Work Continuation Point

One Chinese web novel is onboarded and in progress. Check
`works/` and `sources/works/` for the actual work_id.

### How to continue extraction

```bash
# Resume in foreground
python -m automation.persona_extraction "<work_id>" --resume

# Resume in background (survives SSH disconnect), max 6 hours
python -m automation.persona_extraction "<work_id>" \
    --resume --background --max-runtime 360

# Follow log
tail -f works/<work_id>/analysis/incremental/extraction.log
```

Optional: `pip install jsonschema` for programmatic schema validation (the
tool works without it but skips schema checks).

The pipeline will check for a running instance (PID lock) and clean git
working tree before starting. See `automation/README.md` for full CLI
options and pipeline phase descriptions.

### Post-extraction manual repair

After automation completes, use `prompts/review/手动补抽与修复.md` for
targeted fixes (e.g. Phase 3.5 report items, missing relationships).
Use `prompts/review/数据包审校.md` for full package review.

## What The User Cares About

- Deep roleplay, not shallow mimicry or generic AI tone
- Preserve time-stage differences and knowledge boundaries
- Do not reduce analysis to ordinary literary summary
- Do not leak memory across contexts or write the character as omniscient
- Do not blur canon and inference without labeling
- Keep updating incrementally, do not restart from scratch
- Do not accidentally rewrite Chinese canon into English summaries
- Do not paste large raw text into logs, docs, or answers

## After Each Milestone

1. **Write a log entry under `docs/logs/`.** This is mandatory for any change
   to schemas, architecture, prompts, simulation docs, or directory structure.
   Do not skip this step.
2. Update `current_status.md`, `next_steps.md`, and this file.
