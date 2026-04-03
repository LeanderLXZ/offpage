# Default Stage Batch Size To 10

## Summary

Raised the repository-wide default extraction batch size for stage-oriented
source reading from `5` chapters to `10` chapters.

## What Changed

- updated the first real work manifests to make
  `extraction.default_batch_size = 10` explicit
- kept the existing default stage mapping behavior explicit:
  - `batch_to_stage = true`
  - `stage_is_cumulative = true`
- updated the work-manifest schema description so the documented recommended
  default is now `10`
- updated the world extraction, character extraction, and source batch planning
  prompts so fresh agents inherit the new default
- updated `ai_context/` and architecture docs so handoff memory and roadmap
  text now match the new default

## Files Updated

- `sources/works/我和女帝的九世孽缘/manifest.json`
- `works/我和女帝的九世孽缘/manifest.json`
- `schemas/work_manifest.schema.json`
- `prompts/analysis/世界信息抽取.md`
- `prompts/analysis/角色信息抽取.md`
- `prompts/analysis/源文件分批规划.md`
- `docs/architecture/data_model.md`
- `ai_context/current_status.md`
- `ai_context/decisions.md`
- `ai_context/next_steps.md`
- `ai_context/handoff.md`

## Notes

- This only changes the default. Work-specific manifests may still override the
  batch size later if a source needs smaller or larger windows.
- This is a historical log entry under `docs/logs/`.
