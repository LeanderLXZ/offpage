# complete T-INGEST-STRUCTURE-MODE

- **Started**: 2026-07-13 05:47 EDT
- **Branch**: main
- **Status**: COMPLETED（用户判定收尾）

## 收尾说明

T-INGEST-STRUCTURE-MODE（phase 0/1 双模式 monolithic / light_novel 调度）
自 2026-05-01 起在 In Progress 单槽停留，全部工程项早已落地：

- schema / code / prompt / ai_context / docs 全量改动 + smoke 全过
  （落地明细见 [2026-05-01_070414_phase01_ingest_structure_mode.md](2026-05-01_070414_phase01_ingest_structure_mode.md)）
- post-check 两轮残留缺口已修（stage_title 软截断改为启动时动态读取
  schema cap、progress.py reconcile `C` 前缀兼容、cosmetic 项；见
  [2026-05-01_090952_post_check_followup_ingest_structure_mode.md](2026-05-01_090952_post_check_followup_ingest_structure_mode.md)
  + [2026-05-01_100857_post_check_followup_dynamic_bound.md](2026-05-01_100857_post_check_followup_dynamic_bound.md)）
- normalization 判定流程置信度门槛补丁（见
  [2026-05-01_142902_ingest_structure_mode_confidence_gate.md](2026-05-01_142902_ingest_structure_mode_confidence_gate.md)）

唯一未做项 = end-to-end runtime 双向回归验证（light_novel fixture 跑
phase 0/1 + monolithic 既有 fixture dry-run 确认默认路径不退化）。

**用户 2026-07-13 拍板**：该验证不需要单独跟踪——下次真实跑 pipeline
时自然覆盖双模式路径，若出问题再立项。按**完整完成**归档，不留尾巴
todo。

## 影响

- `docs/todo_list.md` In Progress 单槽腾出（1 → 0），后续任务
  （如 T-PHASE2-REPAIR-AGENT）可启动。
- 无 ai_context 持久事实变更——双模式设计与决策（#27j/k/l 等）在
  5 月落地时已同步。
