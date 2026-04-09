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

Work: `我和女帝的九世孽缘`

Source package intact at `sources/works/我和女帝的九世孽缘/` (537 chapters).
Phase 0 (summarization), Phase 1 (analysis), Phase 2 (confirmation), and
Phase 2.5 (baselines) are complete. Phase 3 in progress: batch_001 committed, batch_002-040 pending.
40 batches total, target characters: 姜寒汐, 王枫.
Extraction runs on branch `extraction/我和女帝的九世孽缘`.
Phase 3.5 (cross-batch consistency check) will run automatically after
all batches commit. Resume auto-resets blocked batches.

### How to continue extraction

```bash
cd automation

# Resume in foreground
python -m persona_extraction "我和女帝的九世孽缘" -r .. --resume

# Resume in background (survives SSH disconnect), max 6 hours
python -m persona_extraction "我和女帝的九世孽缘" -r .. \
    --resume --background --max-runtime 360

# Follow log
tail -f ../works/我和女帝的九世孽缘/analysis/incremental/extraction.log
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
