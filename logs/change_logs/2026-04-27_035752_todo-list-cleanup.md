# todo-list-cleanup

- **Started**: 2026-04-27 03:57:52 EDT
- **Branch**: extraction/我和女帝的九世孽缘
- **Status**: PRE+POST（簿记小改，PRE / POST 合写）

## 背景 / 触发

用户 review todo_list 现状后，给出处置指示：

- T-WORLD-SNAPSHOT-S001-S002-MIGRATE 废弃：已清产物，extraction 全部重新开始
- T-PHASE4-STAGE-REMAP 废弃：同上，scene_archive.jsonl 已清，无需 remap
- T-SCENE-ARCHIVE-SUMMARY-REQUIRED 仍未落地，但即将讨论 → 提升到「立即执行」（30 分钟工作量、无依赖）
- T-CHAR-SNAPSHOT-13-DIM-VERIFY 漂移确认：docs 说 13，schema 实测 17 必填，需修
- T-RETRY 前置 T-LOG 已完成，但本身两条决策（短时阈值扩大 / 长时 exit 按 subtype 分流）未落地
- T-PHASE35-IMPORTANCE-AWARE 保留
- 讨论中 4 条依赖外部条件未变，原状保留

## 落地变更

1. `docs/todo_list.md`
   - 删 `T-WORLD-SNAPSHOT-S001-S002-MIGRATE`（立即执行段）
   - 删 `T-PHASE4-STAGE-REMAP`（下一步段）
   - `T-SCENE-ARCHIVE-SUMMARY-REQUIRED` 从下一步提升到立即执行（按"任务完成 → 提升首条"规则）
   - `T-CHAR-SNAPSHOT-13-DIM-VERIFY` 上下文更新：实测 17 必填（不是怀疑漂移；明确数字 + 列出实际 required 列表）
   - `T-RETRY` 上下文更新：T-LOG 已完成、subtype 已可解析；本任务剩余两条具体落地点（短时阈值 + subtype 分流），从"待决策"降级到"待落地"

## 废弃原因记录（per "任务废弃" 规则）

- **T-WORLD-SNAPSHOT-S001-S002-MIGRATE**：S001 / S002 旧产物已被用户清除，extraction 分支将从零重抽，新产物天然按当前 schema 生成，无迁移需求。
- **T-PHASE4-STAGE-REMAP**：同因，旧 scene_archive.jsonl 不存在；未来若 stage_plan 重抽，直接 `--start-phase 4` 全量跑即可（用户已接受全量重跑代价）。重启该任务的触发条件 = 出现"已落产 scene_archive 但 stage_plan 想改"的真实用例。

## Status

DONE — 仅簿记改动，无代码 / schema / prompt 变更。
