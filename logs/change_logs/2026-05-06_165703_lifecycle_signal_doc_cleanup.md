# lifecycle_signal_doc_cleanup

- **Started**: 2026-05-06 16:57:03 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

清扫两条上轮 /post-check 留下的小尾巴：

1. **`automation/repair_agent/coordinator.py:358`** inline 注释
   `lifecycle_signal = ""  # "" | "T3_TRIGGERED" | "T3_EXHAUSTED"`
   漏列上轮 T-LENGTH-TOLERANCE-GATE (#48) 引入的新值
   `LENGTH_TOLERANCE_PASS`（在 line 778 / 409 实际使用）。
2. **`automation/repair_agent/coordinator.py:684-687`** `_run_fixer_with_escalation`
   的 docstring 描述 `lifecycle_signal` 可能值时同样漏 `LENGTH_TOLERANCE_PASS`。
3. **`works/<work_id>/analysis/progress/phase0_summaries.json`**
   中 chunk_008 是会话早些时候手工 hot-fix 把 state failed→done，但
   没有同步设置 `recovery_attempted=True`。审计语义不严：从字段看
   像"未经过 sweep"，实际是"手工 sweep 等价物"（前台 effort=high
   diag 跑完 14 min 写出 schema valid 的 chunk_008.json）。补字段
   让 resume 时 sweep 跳过它的语义更明确。

两条都不在前几次 /go intent 范围内（#1/#2 是 T-LENGTH-TOLERANCE-GATE
落地后 /post-check 的 Low finding；#3 是 chunk_008 hot-fix 决策时的
补强），打包一次清理。

## 结论与决策

- coordinator.py:358 inline comment 加 `LENGTH_TOLERANCE_PASS`
- coordinator.py:684 docstring 描述 lifecycle_signal 可能值的列表加
  一行 `LENGTH_TOLERANCE_PASS` 说明（lifecycle 2 length-bound tolerance
  accepted residual）
- works/<work_id>/analysis/progress/phase0_summaries.json
  chunk_008 加 `"recovery_attempted": true` 字段（works/ 在 .gitignore
  内，不入 commit；纯本地状态修复）

显式不做的事：

- 不动 coordinator.py 的实际状态机逻辑（_TERMINAL_TYPES 常量没
  LENGTH_TOLERANCE_PASS 是有意的——它是个 lifecycle_signal 中间值，
  最终被 _run_one_lifecycle 解释为 `terminated_by="PASS"`，所以
  _TERMINAL_TYPES 对应的是终态而不是 signal，无需加）
- 不动 progress.py / config.py / orchestrator.py / llm_backend.py
  等其它文件，本次纯文档级修补 + 1 处本地状态文件
- 不创建新 todo entry（两条都是清理性质，无 spec 变更，不值得
  todo 空间）

## 计划动作清单

- file: `automation/repair_agent/coordinator.py:358` →
  inline 注释枚举值列表加 `LENGTH_TOLERANCE_PASS`
- file: `automation/repair_agent/coordinator.py:684-687` →
  `_run_fixer_with_escalation` docstring `lifecycle_signal` 段加
  `LENGTH_TOLERANCE_PASS` 说明（与 line 706+ 的实际 set 处对应）
- file: `works/<work_id>/analysis/progress/phase0_summaries.json`
  → chunk_008 加 `"recovery_attempted": true`（gitignored，不入 commit；
  本地状态修复）
- file: `logs/change_logs/2026-05-06_165703_lifecycle_signal_doc_cleanup.md`
  → 本 log 文件本身（PRE 段已落，POST + commit 在 Step 8/9）

## 验证标准

- [ ] `grep -n "LENGTH_TOLERANCE_PASS" automation/repair_agent/coordinator.py`
      命中 ≥ 4 行（line 358 inline comment + line 684 docstring + line 409
      `if` 分支 + line 778 `lifecycle_signal = "..."`）
- [ ] `python -m automation.repair_agent._smoke_l3_gate` 4 场景
      （A/B/C/D）全过（无回归）
- [ ] `python -c "from automation.repair_agent import coordinator"` 不抛
- [ ] `python3 -c "import json; d=json.load(open('works/<work_id>/analysis/progress/phase0_summaries.json')); assert d['chunks']['chunk_008']['recovery_attempted'] is True"` 不抛

## 执行偏差

无（计划清单 1:1 落地）。Step 3 / Step 6 / Step 7 跳过的理由已在 step
切换时打印；本质：纯注释/docstring 修复 + 1 处本地 gitignored 状态
文件，无跨文档对齐 / todo 移段 / 上下游连带。

<!-- POST 阶段填写 -->

## 已落地变更

- `automation/repair_agent/coordinator.py:358` — inline 注释枚举值
  列表加 `LENGTH_TOLERANCE_PASS`：
  `# "" | "T3_TRIGGERED" | "T3_EXHAUSTED" | "LENGTH_TOLERANCE_PASS"`
- `automation/repair_agent/coordinator.py:684-693` —
  `_run_fixer_with_escalation` docstring `lifecycle_signal` 段加 5 行
  描述 `LENGTH_TOLERANCE_PASS` 的语义（lifecycle 2 即将 T3_EXHAUSTED
  时所有残留 issue 是纯 minLength/maxLength 类经 relaxed 验证通过，
  caller 视为 PASS 终态；引用 decision #48）
- `works/<work_id>/analysis/progress/phase0_summaries.json`
  → chunk_008 加 `"recovery_attempted": true` + 刷新 `last_updated`
  时间戳；works/ 在 .gitignore 内不入 commit（本地状态修复，让前
  期手工 hot-fix 的 chunk 在 resume 时 sweep 跳过的语义更清晰）

## 与计划的差异

无。

## 验证结果

- [x] `grep -n "LENGTH_TOLERANCE_PASS" automation/repair_agent/coordinator.py`
      命中 4 行：358 (inline) / 409 (if 分支) / 688 (新加 docstring) /
      783 (signal set 处) — 文档与实际使用全对齐
- [x] `python -m automation.repair_agent._smoke_l3_gate` 4 场景
      (A/B/C/D) 全过 — 无回归
- [x] `python -m automation.persona_extraction._smoke_recovery_sweep`
      4 场景 (A/B/C/D) 全过 — recovery sweep 路径无回归
- [x] `python -c "from automation.repair_agent import coordinator"`
      不抛 — import OK
- [x] `chunks['chunk_008']['recovery_attempted'] is True` — assert 通过

## Completed

- **Status**: DONE
- **Finished**: 2026-05-06 17:00:00 EDT
