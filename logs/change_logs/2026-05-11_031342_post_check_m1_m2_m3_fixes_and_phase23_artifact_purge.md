# post_check_m1_m2_m3_fixes_and_phase23_artifact_purge

- **Started**: 2026-05-11 03:13:42 EDT
- **Branch**: main (worktree `../offpage-main`，主 checkout 仍在 extraction/`<work_id>`)
- **Status**: PRE

## 背景 / 触发

上一轮 `/go` (commit `44ff4eb foundation_phase1_lift_target_baseline_tighten`) 落地 foundation 重构 + target_baseline 收紧 + ai_context 措辞修正三件合一。`/post-check` (commit `af000aa` REVIEWED-PARTIAL) 跑 4 sub-agent 并行扫描发现 5 个 Medium + 3 个 Low findings。user 选定按推荐**修复 M1 + M2 + M3** 三件 + **清空 extraction 分支下 phase 2 / phase 3 产物**（D=(1) 重跑路径正式执行）。

M4 / M5 / L1 / L2 / L3 + 3 个 Open Questions（OQ1-OQ3）均不在本 /go 作用域内（M5 spec authority 漂移可下一轮单独修；OQ 类问题归 `T-PHASE2-REPAIR-AGENT` todo 设计阶段）。

## 结论与决策

### 任务 A：修 M1 / M2 / M3 三件（main 端文档 / 代码改动）

1. **M1**：[`works/README.md:52`](works/README.md#L52) 目录树 + [`:194`](works/README.md#L194) Phase 1 产物说明仍引用 `analysis/world_overview.json`。修法：surgical edit，把 line 52 (`analysis/` 目录树内) `world_overview.json` 删除（foundation 现在落 `world/foundation/foundation.json` 不在 analysis/ 下），把 line 194 的"`world_overview.json` — Phase 1 世界观概览"删除/改写为 phase 1 foundation lane 输出在 `world/foundation/foundation.json`。
2. **M2**：phase 3 stage_snapshot keys cascade 隐性后果——target_baseline 准入门槛收紧 → baseline.targets 缩水 → user 重跑 phase 2 必须**同时强制重跑所有 phase 3 stage** 才能恢复决策 #13 双向 set-equal 约束。修法：[`automation/persona_extraction/orchestrator.py::run_baseline_production`](automation/persona_extraction/orchestrator.py) docstring 加 warning 段；同时在 PRE log 的"数据迁移提醒"段（POST log 内）显式标注。
3. **M3**：D4 仅修了 `orchestrator.py:10-15` 顶部 docstring 的 L0–L3 disambiguation，但 [`validator.py:10`](automation/persona_extraction/validator.py#L10) + [`validator.py:413`](automation/persona_extraction/validator.py#L413) + [`consistency_checker.py:15`](automation/persona_extraction/consistency_checker.py#L15) 内仍有裸 `L0–L3` / `L1/L2/L3` 字面无 disambiguation。修法：三处加 D4 同形态 disambiguation note，引用 ai_context/decisions.md #25 + #40。

### 任务 B：清空 extraction 分支下 phase 2 / phase 3 产物（extraction 端 working tree 改动）

user D=(1) 决策正式执行：

- **phase 2 产物**（全清）：
  - `works/<work_id>/world/foundation/foundation.json`（旧 schema `core_rules: object[]` 形态，在新 foundation schema 下 31 errors）
  - `works/<work_id>/world/foundation/fixed_relationships.json`
  - `works/<work_id>/world/manifest.json`（phase 2 末 programmatic 写出）
  - `works/<work_id>/world/stage_catalog.json`（空骨架）
  - `works/<work_id>/characters/{Character A,Character B}/canon/{identity,target_baseline,stage_catalog}.json`
  - `works/<work_id>/characters/{Character A,Character B}/manifest.json`
- **phase 3 产物**（全清）：
  - `works/<work_id>/world/stage_snapshots/`（如有）
  - `works/<work_id>/world/world_event_digest.jsonl`（如有）
  - `works/<work_id>/characters/*/canon/stage_snapshots/`（如有）
  - `works/<work_id>/characters/*/canon/memory_timeline/`（如有）
  - `works/<work_id>/characters/*/canon/memory_digest.jsonl`（如有）
  - `works/<work_id>/characters/*/canon/extraction_notes/`（如有）
  - `works/<work_id>/analysis/progress/phase3_stages.json`（如有）
- **Phase 1 产物保留**（user 已确认 phase 1.5 targets + stage_plan）：
  - `works/<work_id>/analysis/chapter_summaries/` ← 保留（phase 0）
  - `works/<work_id>/analysis/stage_plan.json` ← 保留
  - `works/<work_id>/analysis/candidate_characters.json` ← 保留
  - `works/<work_id>/analysis/progress/{pipeline,phase0_summaries}.json` ← 保留（管线状态）
  - `works/<work_id>/manifest.json` ← 保留（phase 1.5 写）
- **Phase 1 旧 world_overview.json 单独处理**：
  - `works/<work_id>/analysis/world_overview.json` — 旧 phase 1 lane 产物，新 lane 改输出到 `world/foundation/foundation.json`。**删除**（不然下次 phase 1 跑会保留这份废文件，未来困扰）。

任务 B 不进 main 端 commit（works/ 不在 main 上），单独在 extraction 分支 commit。

### 显式不做

- 不修 M4（schema core_rules 锁定 comment）：决策 #54 + #1 已锁定，schema 内 comment 边际收益低
- 不修 M5（conventions / decisions plumbing 列表 D1 偏差未传播）：user 没列入本轮 /go，留待下一轮单独修
- 不动 L1（archived todo 历史描述）/ L2（phase 1 lane skip corrupt foundation）/ L3（phase 2 LLM token 预算实测）
- 不接 phase 2 进 repair_agent（拆出来作 `T-PHASE2-REPAIR-AGENT` todo，与本次正交）
- 不动 schema / prompt / 决策（本次纯文档 + 一行 docstring + working tree 清理）

## 计划动作清单

### 任务 A — M1/M2/M3 修复（main 端）

- file: `works/README.md` → M1：line 52 目录树内 `world_overview.json` 删除 + line 194 改写 phase 1 产物说明（指向 `world/foundation/foundation.json`）
- file: `automation/persona_extraction/orchestrator.py::run_baseline_production` → M2：docstring 加 phase 3 cascade warning 段，引用 decision #13 双向 set-equal 约束 + decision #54 target_baseline 准入门槛收紧 → 用户重跑 phase 2 时必须同时重抽所有 phase 3 stage
- file: `automation/persona_extraction/validator.py` → M3：line 10 (module docstring) + line 413 (Phase 0 L1+L2+L3 注释附近) 各加 D4 同形态 disambiguation note（引用 #25 vs #40）
- file: `automation/persona_extraction/consistency_checker.py` → M3：line 15 附近的 `L1/L2/L3` 字面加 disambiguation note
- file: `logs/change_logs/2026-05-11_031342_post_check_m1_m2_m3_fixes_and_phase23_artifact_purge.md` → 本 log

### 任务 B — 清空 phase 2/3 产物（extraction 端）

- worktree 切回主 checkout (`/home/leander/Leander/offpage` extraction/`<work_id>` 分支) 后执行 `rm -rf` + `git rm` + commit
- 在 extraction 分支单独 commit，message slug `purge_phase23_artifacts_for_foundation_rerun`

## 验证标准

### 任务 A
- [ ] `grep -n "world_overview.json" works/README.md` 残留 = 0
- [ ] `grep -c "decision #13\|双向 set-equal\|cascade" automation/persona_extraction/orchestrator.py` 中 `run_baseline_production` docstring 段含 phase 3 warning（≥1 处）
- [ ] `grep -c "see ai_context/decisions.md #25\|see decisions.md #40\|disambiguation" automation/persona_extraction/validator.py automation/persona_extraction/consistency_checker.py` 残留 ≥3 处（validator 2 + consistency_checker 1）
- [ ] `python -c "from automation.persona_extraction import orchestrator, validator, consistency_checker; print('OK')"` import 无报错

### 任务 B
- [ ] `ls works/<work_id>/world/foundation/` 不存在 / 为空
- [ ] `ls works/<work_id>/characters/*/canon/identity.json` 不存在
- [ ] `ls works/<work_id>/world/stage_snapshots/ works/<work_id>/characters/*/canon/stage_snapshots/` 不存在 / 为空
- [ ] `ls works/<work_id>/analysis/stage_plan.json works/<work_id>/analysis/candidate_characters.json works/<work_id>/analysis/chapter_summaries/` 仍存在（保留 phase 1 产物）
- [ ] `git -C /home/leander/Leander/offpage status` 干净（清空后 commit）

## 执行偏差

无。任务 A 与 PRE 计划完全对齐；任务 B 由 Step 10 末尾在 extraction 分支单独执行（另起一次 commit），不进 main 端 commit。

<!-- POST 阶段填写 -->

## 已落地变更

### 任务 A — M1/M2/M3 修复（main 端，4 文件 + 1 log）

- **`works/README.md`**（M1）：
  - line 51-55：`analysis/` 目录树里移除 `world_overview.json`（原 phase 1 产物路径已废弃）
  - line 192-196：phase 1 产物说明列表里删除 `world_overview.json` 行；在 `candidate_characters.json` 行末尾加 disambiguation 索引（"决策 #54：原 `world_overview.json` 路径已废弃；foundation 由 phase 1 foundation lane 直接落 `world/foundation/foundation.json`"）保留单条历史引用作未来 onboarding 索引
- **`automation/persona_extraction/orchestrator.py::run_baseline_production`**（M2）：docstring 加 11 行 "⚠️ **Phase 3 cascade warning (decision #54 + #13)**" 段，明确：
  - 重跑 phase 2 会改写 `target_baseline.json` → baseline.targets 集合可能缩水
  - 决策 #13 双向 set-equal 要求 phase 3 stage_snapshot 三结构 keys == baseline.targets 全集
  - 已落盘的 phase 3 stage_snapshot 与新 baseline 集合不一致时 cross-file validate 硬 fail
  - 必须配套清空所有 phase 3 产物：`world/stage_snapshots/` + `characters/*/canon/stage_snapshots/` + `memory_timeline/` + `memory_digest.jsonl` + `world_event_digest.jsonl` + `analysis/progress/phase3_stages.json`
  - 本函数不自动清理（破坏性动作）
- **`automation/persona_extraction/validator.py`**（M3）：
  - module docstring (line 1-12) 末追加 6 行 "**L1/L2/L3 disambiguation**" 段，明确 repair_agent L0–L3 (#25 checker hierarchy) vs phase 0 L1/L2/L3 (#40 JSON-format repair) 同字面不同物
  - length tolerance gate 段（line 409-431）注释重写：把 "Phase 0 L1+L2+L3" 加上 "decision #40" 标注；把 "repair_agent T3_EXHAUSTED" 加上 "Phase 3 only ... decision #25 + #48 disambiguation" 标注；强调 same字面 ``L1/L2/L3`` but different semantics across #25 and #40
- **`automation/persona_extraction/consistency_checker.py`**（M3）：module docstring (line 1-17) 内 "violations route into the file-level repair lifecycle (L1/L2/L3)" 字符串扩展，加 disambiguation 子句："here = repair_agent checker tiers, decision #25 — NOT phase 0's JSON-format L1/L2/L3 from decision #40; same字面, different semantics"

### 任务 B — 清空 phase 2/3 产物

任务 B 是 extraction 分支 working tree 改动，**不进 main 端 commit**。POST log 这一段已完成，Step 10 同步分支后切回 extraction 分支执行 `rm` + `git rm` + 单独 commit。详见 Step 10 部分。

## 与计划的差异

无。

## 验证结果

### 任务 A
- [x] `grep -n "world_overview.json" works/README.md` 残留 = 1（line 194 历史索引段，合理保留）— PASS
- [x] `grep` 中 `run_baseline_production` docstring 段含 phase 3 cascade warning 3 处 ("Phase 3 cascade" + "双向 set-equal" + "cross-file validate") — PASS
- [x] `grep "decision #25\|decision #40"` 在 validator.py + consistency_checker.py 残留 ≥3 处（validator 3 + consistency_checker 2）— PASS
- [x] `python -c "from automation.persona_extraction import orchestrator, validator, consistency_checker"` import 无报错 — PASS
- [x] 完整 import chain：`build_foundation_prompt` / `_foundation_validator` / `validate_baseline` / `validate_with_length_tolerance` / `consistency_checker` module 全部 import 通过 — PASS

### 任务 B
- 验证标准在 Step 10 执行后由 user 端 `ls` / `git status` 直接验证；POST log 这里仅记录任务 A 完成时点

## Completed

- **Status**: DONE（任务 A）+ Step 10 末尾执行任务 B
- **Finished**: 2026-05-11 03:18:25 EDT
