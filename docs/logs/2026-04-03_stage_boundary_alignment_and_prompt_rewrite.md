# Stage Boundary Alignment & Prompt Rewrite

Date: 2026-04-03

## Summary

Two main changes:
1. Enforced story-boundary batch splitting alignment across all project layers
2. Rewrote the full-pipeline orchestration prompt

## Batch Boundary Alignment

Found and fixed 12+ misalignment points where old "fixed 10 chapters" language
conflicted with the "natural story boundary" design. After fixes, verified via
grep scan that all layers are consistent.

Key principle enforced everywhere:
- Batch splitting is the **most critical output** of the analysis phase
- Every batch boundary becomes a stage boundary for all downstream structures
- Story boundary accuracy > even chapter counts
- Default 10, min 5, max 20 (configurable)

### Files fixed for alignment

- `docs/requirements.md` — §2.1, §9.2, §11
- `ai_context/requirements.md`, `decisions.md`, `current_status.md`
- `docs/architecture/extraction_workflow.md`
- `prompts/analysis/` — 全书总体分析, 世界信息抽取, 角色信息抽取, 源文件分批规划
- `works/README.md`
- `automation/prompt_templates/coordinated_extraction.md`
- `automation/persona_extraction/orchestrator.py` — removed stale batch_size prompt
- `automation/persona_extraction/cli.py` — removed --batch-size flag

## Batch Splitting Significance

Added "为什么剧情切分至关重要" sections to analysis prompts and docs,
explaining that batch boundaries cascade into world snapshots, character
snapshots, memory timelines, runtime loading, and user experience coherence.

### Files updated

- `prompts/analysis/全书总体分析.md`
- `prompts/analysis/源文件分批规划.md`
- `automation/prompt_templates/analysis.md`
- `docs/architecture/extraction_workflow.md`
- `docs/requirements.md` §2.1
- `ai_context/requirements.md`

## Prompt Rewrite

Renamed `直接提取一本书信息_引导式.md` → `全流程提取编排.md` and rewrote:

- Added comparison table vs `automation/` pipeline (prompt-driven vs script-driven)
- Restructured into 7 clear sections with visual separators
- Added full batch splitting significance section in stage 2
- Added `boundary_reason` must explain why (not just "满 10 章")
- Removed redundant "阶段 6 进入运行时" (not extraction scope)
- Simplified initial interaction questions
- Aligned extraction output list with `coordinated_extraction.md` template
- Updated `prompts/README.md` reference

## Automated Extraction Pipeline (from earlier in session)

Added complete `automation/` directory with Python orchestrator, prompt
templates, and documentation. Added `docs/architecture/schema_reference.md`.
Updated all ai_context files, requirements, and architecture docs. See
`docs/logs/2026-04-03_004740_automated-extraction-pipeline.md` for details.
