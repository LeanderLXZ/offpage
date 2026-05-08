# post_check_m1_m2_phase15_input_defense_and_neg_end_stage

- **Started**: 2026-05-08 16:20:23 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

紧接上一轮 commit `2fbc481` (`stage_min_8_chapters_and_phase15_end_stage_fix`) + log 回写 commit `9dd7d81` (`/post-check REVIEWED-PARTIAL`)。/post-check 4 sub-agent 双轨审计输出 4 项 M finding，用户拍板修 M1 + M2：

- **M1**：`automation/persona_extraction/orchestrator.py:1607,1636` `confirm_with_user` 两个 `input()` 缺 EOFError 防护——上一轮只补了 line 2833 的 `Resume from existing progress?` prompt（commit body 声明的"防止 daemon stdin EOFError"主旨），同函数内的 character 选择 + end_stage 选择两个 input 形成防御不对称。CLI 守门人 (cli.py:234-246) 已挡 daemon 路径，但 in-depth 防御不对称属代码 quality 缺口（与决策 #51 主旨"daemon 路径上**没有任何**可触发的 stdin prompt"一致性应贯穿 confirm_with_user 函数本身，不能完全依赖外层守门）。

- **M2**：`automation/persona_extraction/cli.py:106-109` `--end-stage` argparse 仅 `type=int` 无范围下限——`-1` 通过 None vs not-None 检查，进 `run_extraction_loop(max_stages=-1)` → orchestrator.py:1853 `tracker.completed >= max_stages` 第一个 stage 完成即 stop（无声逻辑错误）。pre-existing 边界，但本次新增 `--end-stage` 强制路径让此漏点暴露面更大（更多用户路径会经过此 arg）。

`/post-check` Recommendations 给的修法都是"一行修"。

## 结论与决策

**M1 修法**：在 `confirm_with_user` 内 line 1607（character 选择 input）和 line 1636（end_stage 选择 input）外各包一层 `try/except EOFError`，fallback 到 `raw = ""`（沿用既有"empty → 默认值"的下游逻辑——character 选 recommended_ids，end_stage 取 0=baseline only）。这与 line 2833 的防御形态一致（`try: ... except EOFError: 给默认 fallback`）。注释说明"daemon 路径由 cli.py 双约束守门，本 try/except 是 in-depth 防御"。

**M2 修法**：在 cli.py 增加 `_nonneg_int` 自定义 argparse type 函数（或 inline 通过 `type=` 给 lambda），让 argparse 直接 reject 负数，而不是绕过 None 检查后让 run_extraction_loop 行为漂移。具体做法：在 cli.py 顶层加：

```python
def _nonneg_int(s: str) -> int:
    v = int(s)
    if v < 0:
        raise argparse.ArgumentTypeError(
            f"--end-stage must be >= 0 (got {v}; 0 = baseline only, "
            f"positive = stage count)")
    return v
```

并把 `parser.add_argument("--end-stage", type=int, ...)` 改成 `type=_nonneg_int`。这样负数在 argparse 阶段就被挡住，错误信息友好，避免无声逻辑错误。

**不修**（按 /post-check Recommendations 拍板）：
- M3（小型 work ≤7 章 兼容性 early sanity check 缺失） → 留 todo（架构 + 文档双层改造，独立 plan）
- M4（决策 #51 措辞优化） → 跳过（commit 已落不可 amend）
- L1/L2/L3 → 按 Recommendations 跳过 / 留 todo

## 计划动作清单

- file: `automation/persona_extraction/orchestrator.py:1607-1610` → 把 `raw = input("Enter character IDs to extract...")` 包进 `try/except EOFError: raw = ""` + 注释说明 in-depth 防御
- file: `automation/persona_extraction/orchestrator.py:1636-1640` → 把 `raw = input(f"Extract up to stage N...")` 包进 `try/except EOFError: raw = ""` + 注释说明（fallback 到 empty 后沿用既有 `int(raw) if raw else 0` 逻辑取 0=baseline only；但 baseline only 在 daemon 路径不该是默认——若 daemon 真撞这里说明 CLI 守门有漏点，记 warn 日志即可，不强行改默认行为）
- file: `automation/persona_extraction/cli.py:1-25` 顶部加 `_nonneg_int` argparse type 函数（含 docstring 说明 0/正/负的语义）
- file: `automation/persona_extraction/cli.py:106-109` `--end-stage` 的 `type=int` → `type=_nonneg_int`
- file: `automation/persona_extraction/_smoke_cli_resume_background_validation.py` → 加场景 I（`--end-stage -1` argparse 阶段被挡，exit code 2 = argparse error）+ docstring 说明
- file: `ai_context/decisions.md` #51 → 在末尾追加一句 confirm_with_user 内 input() 已加 in-depth EOFError 防护 + cli.py 加 `_nonneg_int` 防负数 `--end-stage` 的备注，让决策描述与代码现状一致

不动：docs/ 层（M1/M2 是代码级 in-depth 防御 + arg 边界，与 docs 描述无矛盾，不需要再写一段需求 / 架构）；ai_context/architecture.md（同理）；ai_context/requirements.md / current_status.md / handoff.md / next_steps.md（不影响 durable 状态）。

## 验证标准

- [ ] `python -c "from automation.persona_extraction import orchestrator, cli, config; print('OK')"` import 全过
- [ ] `python -c "from automation.persona_extraction.cli import _nonneg_int; assert _nonneg_int('0')==0 and _nonneg_int('5')==5; import argparse; e=None; \nimport contextlib; \nimport io; \n"` 或更直接：argparse smoke——构造 `--end-stage -1` 命令应在 argparse 阶段 exit 2 + stderr 含 ">= 0"
- [ ] grep `try:` / `except EOFError:` 在 orchestrator.py 内出现 ≥ 3 次（line 1607 / 1636 / 2833 三处），且每处 fallback 都是 `raw = ""` 或 `resume = ""`
- [ ] 既有 smoke `_smoke_cli_resume_background_validation.py` 8 场景仍 8/8 passed（M1 改动应不破坏 CLI 守门层为，M2 改动是 argparse type，与 cli.py 后段 background 校验路径正交）
- [ ] 新增 smoke 场景 I（`--end-stage -1` argparse reject）通过：argparse exit code 2 + stderr 含友好错误信息

## 执行偏差

- **/go Step 1 worktree 隔离绕过**：与上一轮 commit `2fbc481` 同款情况——main checkout 工作区有 2 个 untracked phase 1 产物（`works/<work_id>/analysis/{candidate_characters,world_overview}.json`，stage_plan.json 已上轮删除），按 /go 表格 dirty → worktree。但 `git worktree add ../offpage-main main` 因 main 已被主 checkout 占用而 fatal（与上一轮同因）。dirty 内容是 untracked work 产物（按 conventions.md `works/` 不入 git，与本次代码改动 0 交集），改原地编辑路径继续；本次改动文件在 `automation/persona_extraction/` + `ai_context/` 范围内，不会 stage 到 untracked 的 `works/*`。Step 9 commit 显式按文件路径 `git add` 杜绝误纳。

<!-- POST 阶段填写 -->

## 已落地变更

**M1 — `confirm_with_user` 内两个 input() 加 EOFError 防护（in-depth 对称防御）**：

- `automation/persona_extraction/orchestrator.py:1607-1617`：character 选择 input 包 `try/except EOFError: raw = ""`，5 行注释说明"daemon path with stdin=DEVNULL — cli.py background validator requires --characters preset on phase_1_5-pending path so we shouldn't reach here, but defend in depth"，empty fallback 走既有 `selected = typed if typed else recommended_ids` 默认（若无 recommended_ids 则 line 1619 sys.exit(1)）
- `automation/persona_extraction/orchestrator.py:1635-1650`：end_stage 选择 input 包 `try/except EOFError: raw = ""`，6 行注释说明同上，empty fallback 走 `int(raw) if raw else 0` 取 0（baseline only）；附 daemon operator 提示"re-run with --end-stage <N> for phase 3+"

**M2 — `--end-stage` argparse 加 `_nonneg_int` 自定义 type**：

- `automation/persona_extraction/cli.py:24-40`：新增 `_nonneg_int(s: str) -> int` 函数（含 8 行 docstring 说明负数风险——`args.end_stage is None` 检查只区分 None/not-None 不挡 -1，run_extraction_loop line 1853 `tracker.completed >= max_stages` 立即 True 造成无声逻辑错误）；`int()` 内部转换后若 < 0 raise `argparse.ArgumentTypeError` 含友好错误信息 `"--end-stage must be >= 0 (got {v}; 0 = baseline only, positive = stage count to extract)."`
- `automation/persona_extraction/cli.py:124-129`：`--end-stage` argparse 定义 `type=int` → `type=_nonneg_int`，help 文本附"Negative values rejected at argparse"

**Smoke 扩展**：

- `automation/persona_extraction/_smoke_cli_resume_background_validation.py`：场景从 8 (A-H) 扩到 9 (A-I)；新增 `_scenario_i` 验证 `--end-stage -1` argparse exit 2 + stderr 含 ">= 0"；docstring "Eight scenarios" → "Nine scenarios" + 加 (I) 段描述

**决策同步**：

- `ai_context/decisions.md` #51：在末尾追加 "**In-depth 防御**" 段，说明三个 stdin 站点全部 EOFError 防护 + `_nonneg_int` 防负数 `--end-stage` 的实现，引用本次 log；plumbing 段更新含三处新加防护点

## 与计划的差异

按 PRE 计划清单 1:1 落地，无新增 / 删除 / 走样。未触动 docs/ / ai_context/{architecture,requirements,current_status,handoff,next_steps}.md（PRE 已说明 M1/M2 是代码级 in-depth 防御 + arg 边界，与 docs 描述无矛盾）。

## 验证结果

- [x] **import OK**：`from automation.persona_extraction import orchestrator, cli, config; from automation.persona_extraction.cli import _nonneg_int` → 全过
- [x] **`_nonneg_int` 边界正确**：`_nonneg_int('0')==0`、`_nonneg_int('5')==5` accept；`_nonneg_int('-1')` raise `argparse.ArgumentTypeError("--end-stage must be >= 0 (got -1; 0 = baseline only, positive = stage count to extract).")`
- [x] **EOFError 防护数量 ≥ 3**：grep `except EOFError:` 在 orchestrator.py 命中 5 处（line 1610 character / 1647 end_stage / 2644 squash / 2676 dispose / 2851 resume；前两条 + 最后一条是 stdin prompt 防护，2644/2676 是已有 git 询问保护）
- [x] **smoke 9/9 passed**：A-H 既有 8 场景全过 + 新增 (I) `--end-stage -1` argparse reject 通过（exit 2 + stderr 含 ">= 0"）

## Completed

- **Status**: DONE
- **Finished**: 2026-05-08 16:25:08 EDT
