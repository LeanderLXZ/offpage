# run_extraction_loop_no_force_baseline_on_end_stage_0

- **Started**: 2026-05-09 15:02:49 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

紧接 commit `a62e4a3` (schema chapter_count.minimum=8 直接硬挡) + 端到端 daemon 跑（PID 938208 → 退出 11:59:52 EDT）。runtime 实测发现 logic bug：

`run_extraction_loop` (orchestrator.py:1729-1738) 把"`max_stages == 0`"和"`--start-phase == 2`"两个不同语义混用同一个 `force_baseline` 布尔触发，导致 `--end-stage 0` 路径在 fresh-start 已经跑完 baseline + commit 后**重复跑一次冗余 baseline**：

事件链：
1. fresh-start path (line 2908) `run_baseline_production` 跑完 19m24s（PID 938726）+ Validation PASSED + line 1558 `mark_done("phase_2")` + save → pipeline.json `phase_2: done`
2. line 2911 `commit_stage(... "Phase 0-2 baseline")` → commit `2b1d4d5`
3. line 2917 进入 `run_extraction_loop(max_stages=0)`
4. **line 1729 `if max_stages == 0: force_baseline = True`** ← bug 根源
5. **line 1737 `pipeline.set_phase("phase_2", PHASE_RUNNING)` + save** ← 强制覆盖刚 mark 的 done
6. line 1760 `if not pipeline.is_done("phase_2")` = True (因被覆盖) → 进入 baseline-recovery if 体
7. line 1769 `if (... and not force_baseline)` → `not force_baseline = False` → 整个 condition False → **不走 "files present, validating" 跳过路径**
8. line 1812 else → `[WARN] Baseline not completed. Running Phase 2...` + 第二次 `run_baseline_production`
9. 第二次 baseline 7m24s（PID 939350，比第一次快——LLM cache + 已熟悉 prompt）+ commit `06ece59 "Phase 2 baseline (recovery)"`
10. line 1822 `[STOP] --end-stage 0` 退出

**两个语义混淆**：
- `--start-phase 2`：用户**明确要求**重跑 baseline（force 合理）
- `--end-stage 0`：用户要求"baseline only 然后停"（不该 force 重跑已 validated 的 baseline）

把这俩语义塞进同一个 `force_baseline` 布尔 → bug。

**实际后果**（不 critical 但有成本）：每次 `--end-stage 0` 跑都浪费一次冗余 baseline LLM call（~7-19min wall）+ 一个冗余 commit。不卡死、不损坏数据、不阻塞流程退出。

## 结论与决策

**修法（一行修）**：去掉 `max_stages == 0` 触发 `force_baseline=True` 的分支，让 `force_baseline` 仅在 `--start-phase 2` 路径生效。

orchestrator.py:1728-1733 改为：

```python
# Force baseline only when --start-phase 2 is explicitly requested.
# --end-stage 0 ("baseline only, stop") is handled by line 1822 [STOP]
# below — it should NOT force-rerun an already-validated baseline that
# fresh-start path's run_baseline_production just produced + committed.
force_baseline = self.start_phase == "2"
```

修复后行为矩阵：
- `--end-stage 0` + phase_2 已 done（fresh-start 跑完 / resume 命中）：`force_baseline=False` → line 1736 if 跳过 `set_phase(running)` → line 1760 `not is_done("phase_2")` = False → 整个 if 体跳过 → 直接进 line 1822 `[STOP]` 退出。**单次 baseline 就退出**。
- `--end-stage 0` + phase_2 pending（partial 状态 / 缺文件）：`force_baseline=False` → line 1760 `not is_done("phase_2")` = True → 进 if 体 → line 1769 检查 `foundation/identity/fixed_rel` 文件存在 + `not force_baseline = True` → 走 "files present, validating" 路径，validate pass 则 mark_done + skip；validate fail 则 line 1801 重跑（合理）。
- `--start-phase 2`：`force_baseline=True`（不变）→ 行为与现状完全一致。

**不修**（按 /post-check + 本会话讨论拍板）：
- 不删 `_check_stage_plan_limits` 代码层兜底（belt-and-suspenders 保留）
- 不改决策 #26a `try/finally: checkout_main(...)` 自动切回 main 的设计（这是 framework-level 设计，本次 scope 外）
- 不删历史 baseline-recovery commit `2b1d4d5` / `06ece59`（已落到 extraction 分支，Squash 时合并；本次只修代码逻辑避免下次再撞）

## 计划动作清单

- file: `automation/persona_extraction/orchestrator.py:1728-1733` → 删除 `max_stages == 0 → force_baseline = True` 分支，保留 `force_baseline = self.start_phase == "2"`；注释更新说明 `--end-stage 0` 由 line 1822 `[STOP]` 单独处理，不该 force-rerun 已 validated baseline
- 不动 schema / prompt / config / docs / ai_context（这是 code-level logic 修复，不影响外部契约）；决策 #26a 描述也不动（自动 checkout_main 行为不变）
- 不新增 smoke（既有 `_smoke_cli_resume_background_validation.py` 不覆盖此路径，写一个 `run_extraction_loop` 入口的单测需要 mock 大量上下文得不偿失；验证靠 import OK + 代码静态读 + 下次 e2e 跑观察）

## 验证标准

- [ ] `python -c "from automation.persona_extraction import orchestrator; print('OK')"` import 全过
- [ ] 静态 grep: orchestrator.py:1728-1740 范围内 `force_baseline` 仅由 `start_phase == "2"` 决定，无 `max_stages == 0 → True` 分支
- [ ] 既有 smoke 全过：`_smoke_cli_resume_background_validation.py` 9/9 + `_smoke_stage_plan_schema_min8.py` 5/5（验证修复不破坏既有 CLI 校验 + schema gate 路径）
- [ ] 文字逻辑 review（grep `force_baseline` 全 module）：所有引用站点（line 1731/1733/1736/1761/1770）语义连贯，`--start-phase 2` 路径行为不变

## 执行偏差

无（PRE 计划清单 1:1 落地：单 1 处 code 改动 + 6 行注释；Step 3 / Step 6 按 PRE 计划跳过——纯 code-level logic 修复无外部契约改动）。

<!-- POST 阶段填写 -->

## 已落地变更

- `automation/persona_extraction/orchestrator.py:1728-1737`：删除 `if max_stages is not None and max_stages == 0: force_baseline = True; else: force_baseline = self.start_phase == "2"` 的 if/else 分支，替换为单行 `force_baseline = self.start_phase == "2"`。新增 6 行 docstring-style 注释解释 trade-off：(a) `--end-stage 0` 由 line 1822 `[STOP]` 单独处理不该 force-rerun；(b) phase_2 真正 incomplete 的 resume 场景由 line 1760 `not is_done` 检查触发，force_baseline=False 时走 "files present, validating" 跳过路径。

## 与计划的差异

无。PRE 计划 1:1 落地。

## 验证结果

- [x] **import OK**: `from automation.persona_extraction import orchestrator` 通过
- [x] **静态 grep**: orchestrator.py:1737 `force_baseline = self.start_phase == "2"` 是唯一赋值；line 1740/1764/1774 引用站点全连贯（`if force_baseline: set_phase(running)` / `if not is_done or (force_baseline and not fixed_rel.exists())` / `if (... and not force_baseline)`）
- [x] **smoke `_smoke_cli_resume_background_validation.py` 9/9 passed**（A-I）
- [x] **smoke `_smoke_stage_plan_schema_min8.py` 5/5 passed**（A-E）
- [x] **路径覆盖 review**:
  - `--end-stage 0` + phase_2 已 done（fresh-start 跑完 / resume 命中）→ force_baseline=False → set_phase 不触发 → line 1764 `not is_done` = False → if 体跳过 → 直接 `[STOP]`。**修复目标场景，单次 baseline 即退出**。
  - `--end-stage 0` + phase_2 pending（partial / 缺文件）→ force_baseline=False → line 1764 `not is_done` = True → if 体进入 → line 1773 走 "files present, validating" 或 "重跑" 路径（合理）。
  - `--start-phase 2` + 任何 phase_2 状态 → force_baseline=True → 行为与现状完全一致。

## Completed

- **Status**: DONE
- **Finished**: 2026-05-09 15:05:30 EDT
