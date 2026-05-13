# phase3_outer_parallelism_restore

- **Started**: 2026-05-13 03:03:58 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

本会话先跑了 phase 3（end-stage 10）作为首次实战，单 stage S001 跑了 ~50 min 还没 commit。/monitor 期间发现日志/架构文档说 "(1 world + N snapshot + N support) parallel"，但实测**所有外层 lane 串行**，每次只 1 个 outer lane 在跑。

定位根因：commit 69146cc 的 H1 修复（"phase 3 主 ThreadPoolExecutor 启动前 `n_workers = max(1, len(lanes_to_run) // (3 if char_snapshot_sub_lanes else 1))`"）把外层 ThreadPool 的 `max_workers` 除以 3。意图是"与 inner sub-lane fan-out 相消，避免峰值 LLM 并发超出 ~8-10 cap"。

**算重了**：`sub_lane_factor=3` 仅对 `snapshot:` lane 成立——`world` / `support:` lane 没有 sub-lane fan-out，但 H1 把整个外层都按 ÷3 缩。

正确峰值（2 角色场景，与 [phase3].concurrency=10 cap 对照）：

| sub-lane 配置 | outer lane 数 | 内层 fan-out | 真实峰值 LLM |
|---|---|---|---|
| 开 (default) | 5 (1 world + 2 snapshot + 2 support) | snapshot×3, 其余×1 | 1 + 2×3 + 2 = **9** ≤ 10 ✓ |
| 关 | 5 | 全 1 | **5** ≤ 10 ✓ |

H1 把外层缩到 1，等效峰值砍到 3（sub-lane 开）/ 1（关），单 stage 时长从理论 ~15 min（关键路径 = max(world, snapshot, support)）拉到 ~60-65 min（全串）。**与 config.py 自述的 cap=10 严重不一致**，是 over-correction。

## 结论与决策

撤回 commit 69146cc 的 H1 outer 降量逻辑。phase 3 主 ThreadPool 外层全并发，sub-lane fan-out 开关保持不变。

- 改：[orchestrator.py:2745-2753](automation/persona_extraction/orchestrator.py#L2745-L2753) 删 `sub_lane_factor` 与 `// sub_lane_factor` 除法，`n_workers = max(1, len(lanes_to_run))`
- 删：H1 那段头注释（"When sub-lane fan-out is enabled, each ``snapshot:*`` lane spawns 3 inner sub-lane LLM calls; cap outer workers by that factor..."）
- 改：`ai_context/decisions.md` #55 末段 "Outer pool 并发降量" 一段——改写为"外层全并发，sub-lane 内层 fan-out 与外层独立计入 [phase3].concurrency=10 cap"，正确描述当前峰值数学
- 不动：sub-lane 开关本身、决策 #55 的 sub-lane fan-out 逻辑、[phase3].concurrency 配置、CLI flag
- 不动：架构文档 `ai_context/architecture.md:158` 与 `docs/architecture/extraction_workflow.md:16` 的 "1+2N parallel" 措辞——本来就描述意图，H1 是代码偏离了文档，本次修复恢复一致

## 计划动作清单

- file: `automation/persona_extraction/orchestrator.py` (line 2745-2753) → 删 `sub_lane_factor` + `// sub_lane_factor`，注释精简为一句话或删除，`n_workers = max(1, len(lanes_to_run))`
- file: `ai_context/decisions.md` (#55 line 436-440 附近) → 改写 "Outer pool 并发降量" 段为正确峰值描述（外层全并发 + 内层 sub-lane 独立 fan-out + 总峰值 ≤ [phase3].concurrency cap）

## 验证标准

- [ ] `python -c "from automation.persona_extraction import orchestrator"` import 无报错
- [ ] grep `sub_lane_factor` 在 orchestrator.py 残留 = 0
- [ ] grep `"Outer pool 并发降量"` 在 ai_context/decisions.md 残留 = 0
- [ ] `n_workers = max(1, len(lanes_to_run))` 出现在 orchestrator.py 恰好 1 次
- [ ] Python AST 检查：phase 3 ThreadPoolExecutor 初始化处 max_workers 表达式不再含除法
- [ ] decisions.md #55 新表述与 config.py [phase3].concurrency=10 cap 数学一致（2 角色 sub-lane 开 = 9，关 = 5）

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

- `automation/persona_extraction/orchestrator.py:2745-2753` → 删 `sub_lane_factor` 变量 + `// sub_lane_factor` 除法；H1 注释段精简为"Outer lanes ... all run in parallel. sub-lane fan-out only expands inside snapshot:* lanes"；`n_workers = max(1, len(lanes_to_run))`（diff -6/+4）
- `ai_context/decisions.md:436-440` 区域 → 决策 #55 末段 "Outer pool 并发降量" 改写为 "Outer pool 全并发"，给出 2 角色峰值数学（sub-lane 开 = 9，关 = 5，均 ≤ [phase3].concurrency=10 cap），并显式说明原 H1 算法把 world / support lane 错按 sub-lane 折扣的 over-correction 根因（diff -5/+9）

## 与计划的差异

- 无新增 / 无删除 / 无修改——按 PRE 计划动作清单逐项完成

## 验证结果

- [x] `python -c "from automation.persona_extraction import orchestrator"` — `orchestrator OK`
- [x] grep `sub_lane_factor` in orchestrator.py = **0**
- [x] grep `Outer pool 并发降量` in ai_context/decisions.md = **0**
- [x] `n_workers = max(1, len(lanes_to_run))` in orchestrator.py = **1 次**（line 2751）
- [x] AST 检查：ThreadPoolExecutor max_workers 表达式不含除法——line 2791 用裸 `n_workers`，其余 5 处 ThreadPoolExecutor 都是别的 pool（self.concurrency / SUB_LANE_NAMES / LANE_CONCURRENCY / repair_concurrency）
- [x] decisions.md #55 新表述与 config.py [phase3].concurrency=10 cap 数学一致（2 角色：sub-lane on=9, off=5）

## Step 7 review 期间额外发现（**不在本次 scope，建议另立 todo**）

**N ≥ 3 角色场景峰值会超 [phase3].concurrency=10 cap**：

| N | sub-lane on peak | sub-lane off peak |
|---|---|---|
| 2（本会话场景） | 9 ✓ | 5 ✓ |
| 3 | 13（超 30%） | 7 ✓ |
| 4 | 17（超 70%） | 9 ✓ |

`n_workers = len(lanes_to_run)` 不做 cap 协调；N=3+ 同 stage 启动峰值由 RateLimitController pause 兜底（功能正确但拖时长）。当前 2 角色场景无需修，待真有多角色 work 出现再讨论。建议 ID `T-PHASE3-PEAK-CAP-N-CHARS`，归到 ⚪ Discussing 段；待用户拍板由 /todo-add 落条目，本 /go **不自落 todo**（按 /go Step 7 规则）。

## Completed

- **Status**: DONE
- **Finished**: 2026-05-13 03:07:42 EDT
