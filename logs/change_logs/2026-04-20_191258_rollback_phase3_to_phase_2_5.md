# 回滚 Phase 3 → Phase 2.5 结束状态（第二次）

## 动机

准备对照 `schemas/` 六目录重排后的新 schema 重新校核 Phase 0/1/2/2.5/4
产物；为避免 Phase 3 已有产物（阶段01 committed + 阶段02/03 WIP）混入校
核与后续重抽，整仓回到 Phase 2.5 结束状态。代码 / schema / 架构不动。

## 改动（master）

### 删除（git rm）

- `works/<work_id>/world/stage_snapshots/阶段01_<location_a>初遇.json`
- `works/<work_id>/characters/<character_a>/canon/stage_snapshots/阶段01_<location_a>初遇.json`
- `works/<work_id>/characters/<character_a>/canon/memory_timeline/阶段01_<location_a>初遇.json`
- `works/<work_id>/characters/<character_b>/canon/stage_snapshots/阶段01_<location_a>初遇.json`
- `works/<work_id>/characters/<character_b>/canon/memory_timeline/阶段01_<location_a>初遇.json`

### Truncate 到 0 字节（文件保留）

- `works/<work_id>/world/world_event_digest.jsonl`
- `works/<work_id>/characters/<character_a>/canon/memory_digest.jsonl`
- `works/<work_id>/characters/<character_b>/canon/memory_digest.jsonl`

### 清空 stages 数组

- `works/<work_id>/world/stage_catalog.json` → `"stages": []`
- `works/<work_id>/characters/<character_a>/canon/stage_catalog.json`
  → `"stages": []`
- `works/<work_id>/characters/<character_b>/canon/stage_catalog.json`
  → `"stages": []`

### 进度文件（.gitignore 本地文件）

- `works/<work_id>/analysis/progress/phase3_stages.json`：10 个
  stage 全部 `state=pending`；清空 `committed_sha` / `last_updated` /
  `error_message` / `fail_source` / `last_reviewer_feedback` /
  `lane_states`。
- `works/<work_id>/analysis/progress/pipeline.json`：已经是
  `phase_3=pending` / `phase_3_5=pending` / `phase_4=done`，不动。

## 保留

- 代码 / schema（六目录）/ `ai_context/` / `automation/` / `simulation/`
  / `prompts/` / `docs/` 全部不动
- Phase 0 产物：`analysis/chapter_summaries/` + `phase0_summaries.json`
- Phase 1 产物：`analysis/world_overview.json` + `stage_plan.json` +
  `candidate_characters.json`
- Phase 2.5 产物：world `foundation/foundation.json` +
  `fixed_relationships.json`；两个角色的 `manifest.json` +
  `identity.json` + 四份 skeleton baseline (`voice_rules.json` /
  `behavior_rules.json` / `boundaries.json` / `failure_modes.json`)
- Phase 4 产物：`retrieval/scene_archive.jsonl`（本地）+
  `analysis/scene_splits/`（本地）
- `extraction.log`（append-only）

## Extraction 分支

- `extraction/<work_id>` fast-forward / 对齐到 master 的回滚
  commit
- `git stash drop stash@{0}`（阶段03 WIP）

## 后续

1. 对照 `schemas/{character,world,work,shared}/` 逐一核对 Phase 0/1/2/2.5/4
   保留产物是否符合当前 schema。
2. 不一致点汇总后再讨论 — 本次不动任何代码 / schema / 产物。
3. 校核通过后：`python -m automation.persona_extraction "<work_id>"
   --resume` 从阶段01 起重跑 Phase 3。

## 影响范围

- 代码 / 架构：零改动
- 数据：Phase 3 全部产物清空
- `ai_context/`：不动（`current_status.md` 关于 Phase 3 in progress 的
  描述会在 Phase 3 真正重新起跑后再更新口径）
