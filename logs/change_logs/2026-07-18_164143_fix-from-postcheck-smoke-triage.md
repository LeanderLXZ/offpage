# fix-from-postcheck-smoke-triage

- **Started**: 2026-07-18 16:41:43 EDT
- **Branch**: main
- **Type**: DO
- **Status**: DONE

## Motivation

落地 `/post-check`（写回于
`logs/change_logs/2026-07-18_153522_fix-smoke-triage-stale-fixture.md`，
REVIEWED-FAIL）经 `/fix` Auto 模式筛出的 fix bucket：M1 / M2 / L1 / L3。
H1（scenario B/C/D 断言强度加固）按 Auto 模式设计被丢弃，本轮未处理。

## Change list

- file: `extraction/repair/tests/_smoke_triage.py`
  → **M1**：scenario F 的 target 由 `A001`（角色自身，phase 2 视为
    `target_self_reference` error）改为 `S002`，三处耦合字面量同改 ——
    `baseline_targets` / `target_voice_map[0].target_character_id` /
    `importance_map` 的键；并加注释说明三者必须同步（importance 键不匹配会
    把阈值静默降到 1、shortage 消失）
  → **M2**：F 的内联注释由 "the run's only structural shortage" 订正为
    "only coverage shortage"，并点明另有两条 relationships warning 不入
    blocking 集
  → **L1**：模块 docstring + `_write_work_layout` docstring 把过度声称的
    "D4-complete character package" 收敛为「满足
    `TargetsKeysEqBaselineChecker`」，并补一句区分两种缺失形态 ——
    缺 baseline 文件报 `targets_baseline_missing`（root-anchored、走
    `NO_FIX_TIER`）vs. 缺三结构报
    `targets_keys_eq_baseline_missing_structure`（锚在各自路径、不走）
- file: `extraction/repair/tests/__main__.py`（新建）
  → **L3**：聚合入口，`python -m extraction.repair.tests` 一次跑完两个 smoke
    模块。任一失败整体退出码 1；单个模块失败不中断后续模块（一个坏的 smoke
    不应遮住其余模块的状态）

## Verification summary

- `python -m extraction.repair.tests` —— 两个模块全过（`_smoke_triage` 5 场景
  + `_smoke_l3_gate` 7 场景），退出码 0
- 聚合入口的失败路径同样实测：注入抛 `AssertionError` 的假模块 → 退出码 1；
  注入返回非零 rc 的假模块 → 计入 failed 且后续模块继续执行。避免聚合入口
  本身成为「坏了也不会红」的假绿
- M1 改动后 F 仍恰好产出 1 条 coverage_shortage note（`[F] passed=True
  notes=1 triage_calls=0`），证明 importance 阈值未被静默降级

## Execution deviations

none —— 实际修改文件与 Step 1.1 声明的 2 个文件一致。
