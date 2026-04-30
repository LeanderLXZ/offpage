# Abandon T-CHAR-SNAPSHOT-TARGET-LIST

**Time**: 2026-04-29 203800 EDT
**Action**: 废弃，从 `docs/todo_list.md` ## Discussing 移到
`docs/todo_list_archived.md` ## Abandoned

## 废弃原因

**被 T-PHASE2-TARGET-BASELINE 方案吞掉。**

原 todo 围绕"sub-lane 主方案 step 0 用什么策略生成 target_char_list"展开
（决策项 1：program-only / llm-light / hybrid 三选一；决策项 2：fallback
模式是否也跑 step 0）。讨论过程中提出更优替代方案：在 phase 2 全书视野
一次性产 per-character `target_baseline.json`（含 tier + relationship_type），
后续 phase 3 各 stage 严格 ⊆ baseline 写 target keys，三方一致 by-construction。

新方案使原 todo 的两个决策项都不再需要：

- **决策项 1（生成策略）→ 整个删除**：sub-lane / 单 lane 都直接读
  phase 2 baseline，无需 stage 内算 active list。原 step 0 串行卡口
  消失（program-only / llm-light / hybrid 三选一已无意义）
- **决策项 2（fallback 是否跑 step 0）→ 整个删除**：单 lane 也吃同一份
  baseline + 同三态规则 prompt，三方 keys ⊆ baseline 校验在两种模式
  下口径一致，no special-case

## 替代任务

新方案落地拆为两条新 todo（在同一会话登记）：

1. **`T-PHASE2-TARGET-BASELINE`**（已登记到 ## Next）— phase 2 加产出
   per-character target_baseline.json，含新 schema + manifest 字段 +
   validate_baseline 校验
2. **`T-CHAR-SNAPSHOT-SUB-LANES`**（已更新）— 吸收原
   T-PHASE3-TARGET-CONSTRAINT 范围；step 0 / `target_char_list.py` 整个
   删除；改动清单同步精简；依赖加 T-PHASE2-TARGET-BASELINE 硬前置

## 关联

- T-PHASE2-TARGET-BASELINE 详见 `docs/todo_list.md` ## Next
- T-CHAR-SNAPSHOT-SUB-LANES 详见 `docs/todo_list.md` ## Next（已更新版）
- 新方案的 D1-D4 决策细节会在 T-PHASE2-TARGET-BASELINE / SUB-LANES 落地
  时同步进 `ai_context/decisions.md`
