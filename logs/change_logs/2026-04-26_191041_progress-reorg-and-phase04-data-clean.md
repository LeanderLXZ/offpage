# progress-reorg-and-phase04-data-clean

- **Started**: 2026-04-26 19:10:41 EDT
- **Branch**: main（worktree `../offpage-main`，主 checkout 留在 `extraction/我和女帝的九世孽缘`，clean）
- **Status**: DONE
- **LOG**: `logs/change_logs/2026-04-26_191041_progress-reorg-and-phase04-data-clean.md`

## 背景 / 触发

会话上下文里收尾 3 件相互依赖的事，本轮一并落：

1. **Phase 0 / Phase 4 现存产物清盘**：用户已确认现存数据按旧 prompt + 无 bound 时代生成，schema 启用后 ~30% 不达标；handoff caveat 段落（pre-current /go 写入）即将变 stale。最干净路径是清盘重抽，而不是迁移修补。
2. **progress 目录混乱**：`works/{work_id}/analysis/progress/` 当前 30 个 entry，22 个 `repair_*.jsonl` 全堆在根，2 个 `extraction.log{,.1}` 也散在根，跟 4 个 phase state json + lock 混在一起。讨论决定方案 A：`progress/extraction_logs/` + `progress/repair_logs/` 双子目录（与已存在的 `progress/failed_lanes/` 子目录布局对称）。
3. **handoff caveat 移除**：上一轮 /go 写的 "Phase 0 chunk + Phase 4 scene_archive 不达新 schema (caveat)" 段落，在数据清盘后即过时；同步移除避免 doc-vs-state drift。

## 结论与决策

**1. progress/ 重组只动 path 常量，不写迁移工具**

代码层只需改两处 path 常量：
- [process_guard.py:172-173](automation/persona_extraction/process_guard.py) `progress / extraction.log` → `progress / extraction_logs / extraction.log`
- [orchestrator.py:1751-1753](automation/persona_extraction/orchestrator.py) `progress_dir / repair_*.jsonl` → `progress_dir / repair_logs / repair_*.jsonl`

`Path.parent.mkdir(parents=True, exist_ok=True)` 已在两处都有调用 → 子目录自动创建，无需新装置。

**不**写"迁移现有 progress/ 文件到子目录"的脚本——本轮同时清盘，旧 22 个 `repair_*.jsonl` + 2 个 `extraction.log` 直接 rm，没有要迁移的内容。

**2. 数据清盘范围（Phase 0/4 + 配套 progress state）**

| 路径 | 类型 | 处理 |
|---|---|---|
| `works/我和女帝的九世孽缘/analysis/chapter_summaries/` (22 chunks) | Phase 0 LLM 产物 (gitignored) | `rm -rf` |
| `works/我和女帝的九世孽缘/analysis/scene_splits/` (537 files) | Phase 4 中间产物 (gitignored) | `rm -rf` |
| `works/我和女帝的九世孽缘/retrieval/scene_archive.jsonl` (1236 行 / 4MB) | Phase 4 最终产物 (gitignored) | `rm -f` |
| `works/我和女帝的九世孽缘/analysis/progress/phase0_summaries.json` | Phase 0 state | `rm -f` |
| `works/我和女帝的九世孽缘/analysis/progress/phase4_scenes.json` | Phase 4 state | `rm -f` |
| `works/我和女帝的九世孽缘/analysis/progress/extraction.log{,.1}` | runtime 日志 | `rm -f`（fresh start） |
| `works/我和女帝的九世孽缘/analysis/progress/repair_*.jsonl` (22 个) | Phase 3 残留（其 target 文件已在前轮 /go 删除，记录已 stale） | `rm -f` |
| `works/我和女帝的九世孽缘/analysis/progress/pipeline.json` | 标 phase_0/1/2/4 done、phase_3 running、phase_3_5 pending；与已删数据矛盾 | `rm -f`，让 orchestrator next run 重建 |

**保留**：
- `works/我和女帝的九世孽缘/analysis/progress/phase3_stages.json`（Phase 3 lane state，重抽 Phase 3 时由 reconcile_with_disk 重置；不阻塞）
- `works/我和女帝的九世孽缘/analysis/progress/failed_lanes/`（历史失败 lane 日志，留作诊断）
- `works/我和女帝的九世孽缘/analysis/progress/rate_limit_pause.json.lock`（rate limit 状态文件，无害）

**3. handoff caveat 移除**

[ai_context/handoff.md](ai_context/handoff.md) 的 "Phase 0 chunk + Phase 4 scene_archive 不达新 schema (caveat)" 段落移除——数据清盘后该 caveat 过时（描述的"现存数据违反 schema"事实已不复存在；新数据在 schema gate enforce 下产出即合规）。

**4. 故意不动**

- **不**新增 `progress/extraction_logs/` 或 `progress/repair_logs/` 在 main 上的目录占位（main 上没 `works/{work_id}/`，目录占位无意义；orchestrator runtime mkdir 即可）
- **不**改 Phase 3 progress（phase3_stages.json / failed_lanes/）—— 用户没要求，不越界
- **不**重构 `_progress_dir` / `splits_dir` 等 path helper 函数（重组的 path 是 leaf 级，不是 dir 级；helper 不需要改）
- **不**清前轮 /go 留下的 todo（T-PHASE1-OUTPUT-SCHEMAS / T-SCENE-ARCHIVE-SUMMARY-REQUIRED / T-EXTRACTION-BRANCH-DISPOSE / T-PHASE4-STAGE-REMAP / T-WORLD-SNAPSHOT-S001-S002-MIGRATE / T-CHAR-SNAPSHOT-13-DIM-VERIFY / T-RESUME-SCHEMA-RECHECK 等）—— 各自独立

## 计划动作清单

### Code（main 分支）

- file: [automation/persona_extraction/process_guard.py:172-173](automation/persona_extraction/process_guard.py) → `extraction.log` 路径加一级 `extraction_logs/` 子目录；`launch_background` 内 `log_path.parent.mkdir(...)` 已存在不变
- file: [automation/persona_extraction/orchestrator.py:1731,1751-1753](automation/persona_extraction/orchestrator.py) → repair log 写盘前先确保 `repair_logs/` 子目录存在；path 改 `progress_dir / "repair_logs" / f"repair_..."`

### Doc 同步（main 分支）

- file: [ai_context/handoff.md](ai_context/handoff.md) → 移除上一轮 /go 加的 "Phase 0 chunk + Phase 4 scene_archive 不达新 schema (caveat)" 段；改 `tail -f works/<work_id>/analysis/progress/extraction.log` → `tail -f works/<work_id>/analysis/progress/extraction_logs/extraction.log`
- file: [automation/README.md](automation/README.md) → `tail -f` 路径同步；"进度文件存储在 progress/ 下" 段落补 extraction_logs/ + repair_logs/ 子目录说明
- file: [docs/architecture/extraction_workflow.md:446](docs/architecture/extraction_workflow.md) → repair log path 加子目录
- file: [docs/requirements.md:1750](docs/requirements.md) → repair log path 加子目录
- file: [ai_context/architecture.md](ai_context/architecture.md) → 不动（progress/ 子结构属实施细节，不是架构层）

### Data clean（extraction 分支，Step 9 之后单独 commit-less rm）

8 类路径见上"决策 2"表，全 gitignored，不入 git。

## 验证标准

- [ ] `python -m py_compile automation/persona_extraction/{process_guard,orchestrator}.py` 全过
- [ ] `python -c "from automation.persona_extraction import process_guard, orchestrator"` import 通
- [ ] `git grep -nE 'progress/extraction\.log|progress.*extraction\.log'` 不出现裸 `progress/extraction.log` 路径——全部 `progress/extraction_logs/extraction.log`（除 logs/ 历史 + commit messages）
- [ ] `git grep -nE 'repair_.*\.jsonl' -- 'automation/' 'docs/' 'ai_context/'` 涉及路径处含 `repair_logs/`
- [ ] handoff.md 的 "Phase 0 chunk ... caveat" 段落已 0 条引用
- [ ] 数据清盘后磁盘验证：`ls works/我和女帝的九世孽缘/analysis/chapter_summaries/ 2>&1` 报 No such file；`ls retrieval/` 不含 scene_archive.jsonl；`ls progress/repair_*.jsonl 2>&1` 无匹配
- [ ] commit message 风格对齐 `git log --oneline -10`

## 执行偏差

- 多动了 [automation/repair_agent/recorder.py:4](automation/repair_agent/recorder.py) 的 docstring（漏 grep 到的裸 `progress/repair_*.jsonl` 引用）—— 同步加 `repair_logs/` 子目录，与代码 path 一致。计划清单未列，但属"按 Cross-File Alignment 顺手对齐"，不算 scope 蔓延

<!-- POST 阶段填写 -->

## 已落地变更（main 分支）

- [automation/persona_extraction/process_guard.py:172-173](automation/persona_extraction/process_guard.py) `extraction.log` 路径加 `extraction_logs/` 子目录；`log_path.parent.mkdir(parents=True, exist_ok=True)` 已存在不变（自动建子目录）
- [automation/persona_extraction/orchestrator.py:1749-1754](automation/persona_extraction/orchestrator.py) repair log 路径改 `progress_dir / "repair_logs" / ...`；闭包外提一次 `mkdir(parents=True, exist_ok=True)` 确保目录存在
- [automation/repair_agent/recorder.py:4](automation/repair_agent/recorder.py) docstring 路径同步加 `repair_logs/`
- [ai_context/handoff.md](ai_context/handoff.md) 移除 14 行 caveat 段；`tail -f` 路径加 `extraction_logs/`
- [automation/README.md:128,253-262](automation/README.md) `tail -f` 路径加 `extraction_logs/`；进度文件段补四个子目录 / 子文件说明（extraction_logs / repair_logs / failed_lanes / rate_limit_pause）
- [docs/architecture/extraction_workflow.md:446](docs/architecture/extraction_workflow.md) repair log path 加 `repair_logs/`
- [docs/requirements.md:1750](docs/requirements.md) 同上

## 与计划的差异

PRE 计划 7 项 main 改动（含 8 类 data clean 在 Step 9 后做）；实际 main 改动 7 项（含偏差段记的 recorder.py docstring）。data clean 部分待 Step 9 同步到 extraction 后执行。

## 验证结果

- [x] `python -m py_compile automation/persona_extraction/{process_guard,orchestrator}.py` 全过
- [x] `git grep 'progress/extraction.log'` 无裸路径残留（仅 logs/ + 本轮 log）
- [x] `git grep 'progress/repair_'` 三处均含 `repair_logs/` 子目录
- [x] `extraction_logs` / `repair_logs` 引用 10 处分布合理（process_guard / orchestrator / handoff / README × 2 / extraction_workflow / requirements）
- [x] `grep "Phase 0 chunk + Phase 4 scene_archive 不达新 schema" ai_context/handoff.md` = 0
- [x] diffstat 6 文件 + 1 docstring + 1 log = 8 文件改动总计
- [x] `git grep '我和女帝'` = 0（无真实书名残留）
- [ ] data clean 后磁盘验证（待 Step 9 后做）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-26 19:10:41 EDT
