# abandon T-PHASE35-IMPORTANCE-AWARE

- **Started**: 2026-04-30 04:55:22 EDT
- **Branch**: main
- **Status**: ABANDONED

## 废弃原因

T-CONSISTENCY-TARGETS-SUBSET（commit `620be09` + `9a8acc4`）落地后，原 T-PHASE35-IMPORTANCE-AWARE 改动清单的核心痛点已被其他工作覆盖或失去触发基础：

1. **核心痛点已修**：改动清单 1 提到 `_check_target_map_counts` 对 tier=次要/普通 / 从未登场角色的 over-error 场景，在 T-CONSISTENCY-TARGETS-SUBSET commit `620be09` 的 [consistency_checker.py](../automation/persona_extraction/consistency_checker.py) 改动里已加"空 examples 跳过"守卫——同形态问题已解决（虽然走的是 D4 state 锚点而不是 importance 锚点，但效果等价）。

2. **剩余 7 个 `_check_*` 的 over-error 风险被 D4 == 改造稀释**：D4 升级为双向相等后，从未登场的 tier=次要/普通 角色被强制占位为空字段 entry。schema 把 4 个核心字段（`target_character_id` / `target_label` / `summary` / `attitude`）标 required（schema validate 已挡）；其余可选字段（driving_events / relationship_history_summary 等）schema 不强制——`_check_field_completeness` / `_check_relationship_continuity` 等 phase 3.5 检查，对 schema 已挡的字段不需要重复，对 schema 未挡的字段则 tier-aware 收紧只是"提防过激报警"层面的优化，不是阻塞性 bug。

3. **过早优化风险**：T-PHASE2-TARGET-BASELINE / T-BASELINE-DEPRECATE 的 runtime 验证还没跑，phase 3.5 在新 D4 == + tier 占位 entry 形态下的实际 over-error 频率没有数据；现在做 importance-aware 收紧是凭直觉调，可能调错方向（如收紧后又对 tier=核心 漏检）。

4. **触发源已弱化**：原触发链是 2026-04-27 opus-4-7 review L-3 finding——但当时还在旧 keying 形态（target_type 二分），新 keying 后那条 finding 的具体场景重新评估的话，可能不再适用。

## 后续如有需要

待 T-PHASE2-TARGET-BASELINE / T-BASELINE-DEPRECATE runtime 验证跑过，若 phase 3.5 实测确实在 D4 state 3 占位 entry 上产生大量 over-error，再以"D4-state + importance 双锚点"重新立项即可（不沿用本 ID）。

## 关联

- 已完成的等价工作：[2026-04-30_034614_targets_keys_eq_baseline.md](2026-04-30_034614_targets_keys_eq_baseline.md)（`_check_target_map_counts` 加空 examples 跳过守卫部分）
