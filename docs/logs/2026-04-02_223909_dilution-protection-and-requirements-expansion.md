# Dilution Protection & Requirements Expansion

Date: 2026-04-02

## Summary

Added dilution protection mechanisms for both runtime roleplay and extraction
workflows. Expanded requirements document with multiple missing sections.
Cleaned up ai_context files for conciseness and correct reading order.

## Changes

### Requirements (docs/requirements.md)

- Added §八 作品入库与规范化 (source ingestion: formats, normalization, package
  boundaries, work manifest)
- Added §九 提取流程 (extraction workflow: principles, 8-step pipeline,
  coordinated mode, self-contained snapshots, source labeling, output files)
- Added §十 稀释保护 (dilution protection: 10.1 runtime, 10.2 extraction)
- Expanded §2.3 world info into 4 subsections (foundation, entity tracking,
  relationships, stage snapshots)
- Added runtime behavior rules to §四
- Added context state tracking, crash recovery, conversation archive to §五
- Added multi-work namespace and content language consistency to §六
- Rewrote §七 as 5-layer + 4-tier loading model
- Removed "（不限于女主）" from §一
- Renumbered old §八/§九 to accommodate new sections

### ai_context/ updates

- `requirements.md` — rewritten as ~100 line concise English index (§1-§10)
- `project_background.md` — trimmed from ~112 to ~35 lines, removed
  duplication with requirements.md
- `instructions.md` — added 5-rule dilution protection section
- `README.md` + `instructions.md` — swapped reading order so
  project_background.md comes before requirements.md

### Extraction prompt updates

- `prompts/shared/批次执行检查清单.md` — restructured with new sections C
  (schema/architecture re-read), D (cross-batch consistency), E (drift signals)
- `prompts/analysis/直接提取一本书信息_引导式.md` — added schema protection items
- `prompts/analysis/角色信息抽取.md` — added schema protection items
- `prompts/analysis/世界信息抽取.md` — added schema protection items
- `prompts/analysis/批次修订与冲突合并.md` — added schema re-read items

### Runtime prompt updates

- `prompts/runtime/会话稀释保护检查清单.md` — restructured into 3 parts:
  character anchor (≤300 chars), rolling session state (5-8 turns), deep
  calibration (15-20 turns)
- `simulation/contracts/runtime_packets.md` — added character_anchor and
  rolling_session_state to Turn Packet

### Other

- `.gitignore` — added `.history/`
