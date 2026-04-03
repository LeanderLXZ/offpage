# Handoff

## Mental Model

Architecture agreed, scaffold created, implementation still missing. There is
one real work package but no finished character packages, no real user
packages, and no runtime code.

## Quick Start

1. Read all of `ai_context/` first.
2. On first follow-up, continue from `ai_context/` + the user request. Do not
   proactively route through `prompts/` unless the user asks.
3. For architecture details, read `docs/architecture/system_overview.md` and
   `docs/architecture/data_model.md`.
4. For runtime flow details, read `simulation/README.md` and relevant files
   under `simulation/flows/` and `simulation/retrieval/`.
5. For the current work, start from existing metadata and analysis, not raw
   chapters.

## Current Work Continuation Point

Work: `我和女帝的九世孽缘`

- Next batch: `batch_002`, cumulative scope 0011-0020
- Start from:
  - `works/我和女帝的九世孽缘/analysis/incremental/source_batch_plan.md`
  - `works/我和女帝的九世孽缘/analysis/incremental/world_batch_progress.md`
  - `works/我和女帝的九世孽缘/analysis/incremental/candidate_characters_initial.md`
  - `works/我和女帝的九世孽缘/world/stage_catalog.json`
  - Existing world package files
- Use targeted chapter reads only when needed. Do not reread the full novel.

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
