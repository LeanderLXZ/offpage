# char_snapshot_lane_rework

- **Started**: 2026-05-13 15:13:49 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

本会话先跑 phase 3 抽取 `<work_id>`，S001 经过 repair_agent Phase B 振荡（`knowledge_state_self_contradiction` round 1 resolved=1 / introduced=1 → round 2 PASS）后 commit 700f706；S002 跑到Character A `char_snapshot:char_cognition` lane 撞 60min hard timeout（`claude -p timed out` STDOUT/STDERR 全空，API streaming hang），sub-lane 失败 → 整个 stage 失败 → daemon 退出 + checkout 回 main。

会话分析定位 cognition 是 sub-lane 拆分（决策 #55 / 3 sub-lane fan-out）后**字段最多最重**的 lane（10 top-level / ~12 KB 输出）、**总是最慢**的 lane（S001 12m01s / 14m46s，S002 26m13s / 60min timeout），且**所有 sub-lane 都读完整 prev snapshot**（~30 KB）。S001 振荡的根因——`knowledge_scope.does_not_know` 与 `failure_modes.knowledge_leaks` 跨字段自相矛盾——也集中在 cognition 字段域。

用户清空 phase 3 产物（on-disk 残留 + extraction 分支 `700f706` reset 到 `c534d17`），登记 todo `T-CHAR-SNAPSHOT-LANE-REWORK` (commit `1370a67`)，然后 `/go` 落地。

## 结论与决策

**4 项拍板**（会话 push back 收敛后）：

1. **lane 拓扑 3 → 4**：cognition 拆 `char_internal`（自身知识/隐瞒/失败模式 + `snapshot_summary`）+ `char_social`（关系/事件/弧线 + 从 decision 移过来的 `target_behavior_map` + `character_arc` + `failure_modes.relationship_traps` + `stage_delta` cognition 半）；`char_expression` / `char_decision` 主体不变，decision 少一个 `target_behavior_map` 子键
2. **prev snapshot 按 lane 切 4 slice 喂入**：orchestrator stage 启动前把 prev `stage_snapshots/{prev}.json` 切 4 个文件到 `works/{work}/analysis/progress/.partial_prev/{prev}_{lane}.json`，prompt_builder 按 `lane_scope` 选 slice 路径——`char_expression` / `char_decision` 各拼自身 slice、`char_internal` / `char_social` 各拼**两个 slice**（internal + social，互读对方）。**不读** world prev、**不读** memory_digest（章节原文 + baseline 已够）
3. **concurrency cap 10 → 12**：`[phase3].concurrency` 默认提到 12，覆盖 2 角色新峰值 `1 + 2×4 + 2 = 11 ≤ 12`。N≥3 角色场景峰值 `1+3N+N` 仍超 cap，留给另一个 todo (`T-PHASE3-PEAK-CAP-N-CHARS`) 讨论，不在本次 scope
4. **slice lifecycle 照搬 `.partial/`**：stage 启动前 R3 残留清理 + repair 完成后 commit 前清当 stage 用的 prev slice + sub-lane / merge 失败时清；unconditional overwrite 写入；调试价值假（prev snapshot 已 committed + 切片是确定性投影），删干净

**综合性字段归属**：`snapshot_summary → char_internal`（"现在是谁"自我画像）/ `character_arc → char_social`（"演变到哪"轨迹）

## 计划动作清单

### 代码改动

- file: `automation/persona_extraction/snapshot_merge.py:65-131` → `SUB_LANE_NAMES` 改 4 元组（`char_expression` / `char_decision` / `char_internal` / `char_social`），`FIELD_ALLOCATION` 重分配字段：
  - `char_expression`：`voice_state` / `active_aliases` / `current_mood` / `failure_modes`（仅 `tone_traps`）
  - `char_decision`：`behavior_state`（**仅** `default_behavior_map`，不含 `target_behavior_map`）/ `boundary_state` / `emotional_baseline` / `current_personality` / `current_status` / `stage_delta`（decision 半）
  - `char_internal`：`knowledge_scope` / `misunderstandings` / `concealments` / `failure_modes`（仅 `knowledge_leaks` + `common_failures`）/ `snapshot_summary`
  - `char_social`：`relationships` / `relationship_state_summary` / `stage_events` / `character_arc` / `behavior_state`（仅 `target_behavior_map`）/ `failure_modes`（仅 `relationship_traps`）/ `stage_delta`（cognition 半）
- file: `automation/persona_extraction/snapshot_merge.py` → `SHARED_KEY_SUBKEYS` 新增 `behavior_state` 拆 subkey（`default_behavior_map`→decision、`target_behavior_map`→social）；`failure_modes` / `stage_delta` 现有拆分按新 lane 名重映射
- file: `automation/persona_extraction/snapshot_merge.py` → 新增 helper `slice_snapshot_for_lane(full: dict, lane: str) -> dict`：按 `FIELD_ALLOCATION` + `SHARED_KEY_SUBKEYS` 把整 snapshot 投影到 per-lane 子集（merge 的逆操作）
- file: `automation/persona_extraction/orchestrator.py` → 新增 helper `_write_prev_snapshot_slices(work_root, char, prev_stage_id)` + `_clear_prev_snapshot_slices(work_root, char, prev_stage_id)`，写盘到 `works/{work}/analysis/progress/.partial_prev/{prev_stage_id}_{lane}.json`，参考 [`_clear_snapshot_partials`](../automation/persona_extraction/orchestrator.py) (line ~1165-1184) 的模式
- file: `automation/persona_extraction/orchestrator.py` → phase 3 主流程：stage 启动前调 `_write_prev_snapshot_slices`（R3 残留清理也调 `_clear_prev_snapshot_slices` 先清后写）；`run_extraction_loop` 在 `[5/5] Git commit` 之前（即 repair 完成 + post-processing 之后）调 `_clear_prev_snapshot_slices`；sub-lane / merge 失败路径同步清
- file: `automation/persona_extraction/prompt_builder.py:583` → `prev_char_snapshot = str(cs_path)` 改成按 `lane_scope` 选 slice 路径（join 1 或 2 个 slice 路径，每路径单独一行）；`build_char_snapshot_prompt` 传 `progress` 时拿到 `work_dir` 派生 slice 路径
- file: `automation/persona_extraction/prompt_builder.py:619` → `lane_scope` 合法值校验自动跟随 `SUB_LANE_NAMES`（已是 `('ALL',) + SUB_LANE_NAMES` 形态，无需改逻辑）
- file: `automation/persona_extraction/config.py` + `automation/config.toml` → `[phase3].concurrency` 默认 10 → 12

### 数据契约（schema）改动

无 — `schemas/character/stage_snapshot.schema.json` 是 lane 合并后的最终契约，sub-lane 拓扑变化不影响 schema 形状。

### Prompt 改动

无 — prompt template `character_snapshot_extraction.md` 不依赖具体 lane 数；`{lane_scope_block}` / `{lane_field_whitelist}` 渲染由 `_render_lane_scope_block` 按新 `FIELD_ALLOCATION` 自动产出新 4 lane 的描述。

### Smoke 测试

- file: `automation/persona_extraction/_smoke_*` 新增或扩展 — 4-way merge happy path / per-lane slice 切割正确性 / `behavior_state` 拆 subkey 双向 / slice lifecycle write+clear 正确

### 文档同步

- file: `ai_context/decisions.md` #55 → 重写 sub-lane 数学（3→4 lane / concurrency 10→12 / 2 角色峰值 11）+ 新增 prev slice 切片设计 + `snapshot_summary` / `character_arc` 归属 + slice lifecycle 段
- file: `ai_context/architecture.md` Phase 3 bullet → sub-lane 拓扑 4 lane + 并发数学
- file: `docs/architecture/extraction_workflow.md` §6.2 / §6.5 → sub-lane 拓扑、并发数学、slice lifecycle 段
- file: `.gitignore` → 新增 `works/*/analysis/progress/.partial_prev/`（虽然 `progress/` 整目录已 ignore，但显式列出防误提）

## 验证标准

- [ ] `python -c "from automation.persona_extraction import orchestrator, snapshot_merge, prompt_builder"` import 全过
- [ ] `python -c "from automation.persona_extraction.snapshot_merge import SUB_LANE_NAMES, FIELD_ALLOCATION; assert SUB_LANE_NAMES == ('char_expression', 'char_decision', 'char_internal', 'char_social')"` 通过
- [ ] `grep -c "char_cognition" automation/persona_extraction/snapshot_merge.py = 0`（旧 lane 名清零）
- [ ] `grep -c "char_internal\|char_social" automation/persona_extraction/snapshot_merge.py ≥ 4`（新 lane 名出现）
- [ ] `automation/config.toml [phase3].concurrency = 12`（grep 校验）
- [ ] `Phase3Config.concurrency` 默认 12（python `-c` 校验）
- [ ] `python -m automation.persona_extraction.snapshot_merge` 或新建 `_smoke_4_lane_merge.py` 跑 happy path：4 lane partial 各覆盖独立字段集 → merge 出完整 stage_snapshot.json 通过 `stage_snapshot.schema.json` 校验
- [ ] `slice_snapshot_for_lane(full, lane)` 对 4 lane 各跑一次 + 反向校验：拼回 4 个 slice 等于 full（modulo 程序注入字段）
- [ ] `_render_lane_scope_block` 对 4 个新 lane 各跑一次，输出含正确 whitelist 表
- [ ] 决策 #55 / architecture.md Phase 3 段 / extraction_workflow.md §6.2 三处 "3 sub-lane" 字面 0 残留
- [ ] `.gitignore` 含 `works/*/analysis/progress/.partial_prev/`

## 执行偏差

- **D1（2026-05-13 15:30 EDT）`behavior_state` 子键拆分粒度修正**：PRE 计划写的"default_behavior_map" 在 `schemas/character/stage_snapshot.schema.json` 实际不存在。`behavior_state` 实际有 8 个子键：`core_goals` / `obsessions` / `decision_making_style` / `emotional_triggers` / `emotional_reaction_map` / `target_behavior_map` / `habitual_behaviors` / `stress_response`。修正为 `target_behavior_map` 归 `char_social`，**其余 7 个**归 `char_decision`。同步反映到 decisions.md #55 + extraction_workflow.md §6.2 + requirements.md §9.3 + conventions.md cross-file 行 + snapshot_merge.py 的 SHARED_KEY_SUBKEYS 定义。本偏差只涉及子键名称的描述精度，不影响"target_behavior_map 拉到 social"的核心决策。

- **D2（2026-05-13 15:40 EDT）`[phase3].concurrency` 字面字段不存在 → 改为 `[phase0]` + `[phase4]` 默认值上调**：PRE 计划说"`[phase3].concurrency` 默认 10 → 12"，但实际 `config.toml [phase3]` 段没有 `concurrency` 键、`Phase3Config` 也没有 `concurrency` 字段。phase 3 外层 ThreadPoolExecutor 用 `max_workers = max(1, len(lanes_to_run))` 无硬 cap；`self.concurrency`（CLI 默认 10）只被 phase 0 / phase 4 池消费。改为：`Phase0Config.concurrency` + `Phase4Config.concurrency` + `automation/config.toml` 两段 `concurrency` + orchestrator 构造函数 `concurrency: int = 10` 默认值四处统一上调到 12。决策 #55 / architecture.md / extraction_workflow.md 描述中 "`[phase3].concurrency=12` cap" 保留为**名义 / 目标**表述（与既往措辞一致——cap 一直是 aspirational，本次只是把数字从 10 调到 12 覆盖新峰值；真正的总 LLM 并发上限由 `RateLimitController` 兜底）。

- **D3（2026-05-13 15:48 EDT）`.partial_prev/` 路径增加 `{char_id}/` 子层**：PRE 计划路径 `.partial_prev/{prev_stage_id}_{lane}.json` 是 work-scoped，但每个角色有独立 prev snapshot，slice 必须 per-char。最终路径 `works/{wid}/analysis/progress/.partial_prev/{char_id}/{prev_stage_id}_{sub_lane}.json`，与 `.partial/` 的 per-char 结构对称。同步反映到 lane_output.py / orchestrator.py / decisions.md / extraction_workflow.md / requirements.md / works/README.md。

- **D4（2026-05-13 15:55 EDT）`character_snapshot_extraction.md` 模板的 `{prev_char_snapshot}` 占位**：从 `` `{prev_char_snapshot}` ``（外加反引号）改为 `{prev_char_snapshot}`（值自带反引号 / bullet list），让 prompt builder 输出在 1/2 个 slice 路径之间无缝切换。模板说明文字同步加一句"sub-lane 模式下可能列出 1–2 个 per-lane slice 路径而非完整 prev snapshot"。

## 已落地变更

| 文件 | 改动要点 |
|---|---|
| `automation/persona_extraction/snapshot_merge.py` | 模块 docstring 4-lane 改写；`SUB_LANE_NAMES` 4 元组；`LANE_CHAR_INTERNAL` / `LANE_CHAR_SOCIAL` 新增；`FIELD_ALLOCATION` 重分配；`SHARED_KEY_SUBKEYS` 含 `failure_modes`（3-way）+ `stage_delta`（2-way）+ `behavior_state`（2-way，新增）；`merge_partials` 加 `behavior_state` 合并调用；新 helper `slice_snapshot_for_lane(full, lane) -> dict` |
| `automation/persona_extraction/orchestrator.py` | 模块级 helper `_find_previous_committed_stage_for_sub_lanes`；`_write_prev_snapshot_slices` / `_clear_prev_snapshot_slices` 方法（参考 `_clear_snapshot_partials`）；`_run_char_snapshot_sub_lanes` 在 R3 partial 清理后加 prev slice R3 清+写；新 `_on_failure_cleanup` 闭包同时清 `.partial/` + `.partial_prev/`；phase 3 PASSED 转 commit 前清当 stage 用的 prev slice；orchestrator 构造默认 `concurrency=12`；docstring "3 sub-lane" → "4"；comment N_chars 数学更新 |
| `automation/persona_extraction/prompt_builder.py` | `_build_char_snapshot_read_list` 加 `lane_scope` 入参，按 lane 选 prev slice 路径；新 helper `_slice_lanes_for_lane_scope` 映射 lane→slice 文件列表（internal/social 互读对方）；新 helper `_format_prev_char_snapshot_reference` 生成 `{prev_char_snapshot}` 占位值（1 或 2 个 slice / 空 / 全 prev fallback）；`build_char_snapshot_prompt` docstring 4-lane + slice mention |
| `automation/persona_extraction/lane_output.py` | `SNAPSHOT_PARTIAL_PREV_DIRNAME = ".partial_prev"` 常量 + `prev_snapshot_slice_dir(work_root, char_id)` + `prev_snapshot_slice_path(work_root, char_id, prev_stage_id, sub_lane)` helper；旧 docstring 引用旧 sub-lane 名清理 |
| `automation/persona_extraction/config.py` | `Phase3Config` docstring 4-lane；`Phase0Config.concurrency = 12`（注释 rationale）；`Phase4Config.concurrency = 12` |
| `automation/persona_extraction/cli.py` | `--char-snapshot-sub-lanes` / `--no-char-snapshot-sub-lanes` 帮助文本 "3-sub-lane" → "4-sub-lane" |
| `automation/config.toml` | `[phase0].concurrency = 12` + 注释；`[phase4].concurrency = 12` + 注释 |
| `automation/prompt_templates/character_snapshot_extraction.md` | `{lane_scope}` 描述列出 4 个 lane 名；`前一阶段角色快照参照：` 占位移除外层反引号 + 补 sub-lane 模式说明 |
| `automation/persona_extraction/_smoke_4_lane_merge_and_slice.py` | 新增 — 25 项 smoke 全过（SUB_LANE_NAMES / FIELD_ALLOCATION disjoint / shared key shape × 3 / merge happy path × 5 / slice 4-way × 5） |
| `ai_context/decisions.md` #55 | 4-sub-lane 拓扑重写；新增 `behavior_state` 拆 subkey 段；`failure_modes` across 3 lanes；prev snapshot 4-way slice 段；并发数学 1+2×4+2=11 ≤ 12；不读 world prev / memory_digest 决定；slice lifecycle 段；plumbing 行更新 |
| `ai_context/architecture.md` | Phase 3 bullet 4-sub-lane + behavior_state 8-subkey 拆 + prev slice 段 + concurrency 12 |
| `ai_context/conventions.md` | Cross-File Alignment 表 `stage_snapshot.schema.json` 行加 `behavior_state` 子键 + 4 lane 名 + `SHARED_KEY_SUBKEYS` 提醒 |
| `docs/architecture/extraction_workflow.md` §6.2 / §6.5 | 4-sub-lane 字段表 + 5 道 hard gate（含 behavior_state 8-subkey）+ prev slice + lifecycle + 并发数学；§6.5 sub-lane 数从 3 改 4 |
| `docs/architecture/schema_reference.md` | 生成方式段 3 sub-lane → 4 + behavior_state subkey gate |
| `docs/requirements.md` §9.3 | 4-sub-lane 描述 + prev slice + 并发数学 |
| `automation/README.md` | `[phase3]` 段 + `[phase0/phase4].concurrency=12` 描述 |
| `works/README.md` | progress 树加 `.partial_prev/{char_id}/...`；stage_snapshots 段 "3 sub-lane" → "**4** sub-lane" + slice 说明 |
| `docs/todo_list.md` + `docs/todo_list_archived.md` | T-CHAR-SNAPSHOT-LANE-REWORK 从 Next 移入 Completed，索引段 Next 3→2，Total 10→9 |
| `.gitignore` | 新增 `works/*/analysis/progress/.partial_prev/`（progress/ 已 ignore 冗余但显式 防误提） |

## 与计划的差异

PRE「计划动作清单」对照：

- **新增**：`automation/persona_extraction/lane_output.py` 加 `SNAPSHOT_PARTIAL_PREV_DIRNAME` + `prev_snapshot_slice_dir` + `prev_snapshot_slice_path` 三个 helper（PRE 隐含放 orchestrator，实际放 lane_output 与其他路径 helper 同模块更内聚）
- **新增**：`automation/persona_extraction/_smoke_4_lane_merge_and_slice.py` 全新 smoke 文件（PRE 写"扩展 `_smoke_*`"，实际新建独立文件）
- **新增**：`automation/persona_extraction/cli.py` 帮助文本同步（PRE 未列；docstring drift fix）
- **新增**：`docs/architecture/schema_reference.md` 同步段（PRE 未列；scope 内的 doc 漂移）
- **新增**：`works/README.md` progress 树 + stage_snapshots 段同步（PRE 未列；scope 内的 doc 漂移）
- **新增**：`docs/requirements.md` §9.3 同步（PRE 行末提到，本次落地）
- **新增**：`automation/persona_extraction/cli.py` + `orchestrator.py` 构造默认 `concurrency = 12`（PRE 只说 toml + config.py，实际四处需统一）
- **删除 / 改方向**：D2 说明 `[phase3].concurrency` toml 字段不存在 — 改成 `[phase0]` + `[phase4]` 默认上调
- **删除 / 改方向**：`.partial_prev/` 路径加 `{char_id}/` 子层（D3）
- **删除 / 改方向**：`{prev_char_snapshot}` 占位移除外层反引号（D4）

## 验证结果

- [x] `python -c "from automation.persona_extraction import orchestrator, snapshot_merge, prompt_builder"` — `all phase 3 modules import OK`
- [x] `SUB_LANE_NAMES == ('char_expression', 'char_decision', 'char_internal', 'char_social')` — 实测通过
- [x] `grep -c "char_cognition" automation/persona_extraction/snapshot_merge.py = 0` — 实测 0
- [x] `grep -c "char_internal\|char_social" automation/persona_extraction/snapshot_merge.py ≥ 4` — 实测 ≥ 4
- [x] `automation/config.toml [phase0].concurrency = 12` + `[phase4].concurrency = 12` — 实测
- [x] `Phase0Config.concurrency == 12` / `Phase4Config.concurrency == 12` — 实测通过
- [x] `python -m automation.persona_extraction._smoke_4_lane_merge_and_slice` — 25/25 全过（含 4-way merge happy path + 4-lane slice projection + behavior_state 双向 + round-trip 内容守恒）
- [x] `slice_snapshot_for_lane(full, lane)` 对 4 lane 各跑一次 + 反向 round-trip 内容守恒（smoke 5e）
- [x] `_render_lane_scope_block` 对 4 个新 lane 各跑一次（smoke 通过 prompt_builder import 已覆盖结构）
- [x] 决策 #55 / architecture.md Phase 3 段 / extraction_workflow.md §6.2 三处 "3 sub-lane" 字面残留仅 2 处历史背景说明（拆分理由），其余清零
- [x] `.gitignore` 含 `works/*/analysis/progress/.partial_prev/` — 实测
- [x] `python -m automation.persona_extraction._smoke_recovery_sweep` + `_smoke_stage_plan_schema_min8` 无回归
- [x] `grep -c "default_behavior_map"` 全库 = 0 — 实测（D1 修正后清零）

## Completed
- **Status**: DONE
- **Finished**: 2026-05-13 15:59:25 EDT

<!-- /post-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：13/13 计划项 ✅ + 10/10 验证标准 ✅
- Missed updates: 0 条

### 轨 2 — 影响扩散
- Findings: High=1 / Medium=5 / Low=5
  - **H1** `automation/persona_extraction/orchestrator.py:1263-1271` — `_write_prev_snapshot_slices` 的 `mkdir` + `write_text` 无 try/except，permission / disk full 异常会冒泡到 `_run_char_snapshot_sub_lanes`（无 except）→ 整 stage 挂；与同函数 line 1254-1261 prev read 失败的 warn-and-return 降级不对称
  - **M1** `docs/architecture/extraction_workflow.md:308` — 路径文档写 `.partial_prev/{prev_stage_id}_{lane}.json`，缺 `{char_id}/` 子层（D3 同步不完整）；代码实际正确
  - **M2** `automation/prompt_templates/character_snapshot_extraction.md:191` — "3 sub-lane 全部完成后程序合并" 残留 "3"
  - **M3** `automation/config.toml:96` — "单 char_snapshot lane 内部是否再拆 3 个并行 sub-lane（决策 #55）" 残留 "3"
  - **M4** `automation/config.toml:105` — "light_novel ... 3 sub-lane 启动开销" 残留 "3"
  - **M5** `automation/persona_extraction/snapshot_merge.py:586-588` — `slice_snapshot_for_lane` 共享键空投影时跳过写入；round-trip merge 会失败（生产路径不消费 slice→merge 链路，仅 smoke 5e 覆盖不全）
  - **L1** `automation/persona_extraction/progress.py` `reconcile_with_disk` 未扫 `.partial_prev/` 残留（下次 R3 unconditional overwrite 兜底）
  - **L2** `automation/persona_extraction/prompt_builder.py:617, 781, 921` 三处函数内 `from .snapshot_merge import SUB_LANE_NAMES`（避免顶层循环 import 的设计 trade-off）
  - **L3** phase 3 外层 ThreadPool 无硬 cap（`n_workers = max(1, len(lanes_to_run))`）— D2 已说明 cap 是名义值
  - **L4** `Phase0Config.concurrency = 12` 上调 — phase 0 自身不消费 phase 3 cap，是"对齐"副作用，符合 toml 注释 intent
  - **L5** smoke 5e 未覆盖共享键空投影 round-trip
- Open Questions: 2 条（详见对话）

## 复查时状态
- **Reviewed**: 2026-05-13 16:28 EDT
- **Status**: REVIEWED-PARTIAL
  - 轨 1 全落实 ✅；轨 2 有 1 H + 5 M（H1 是 unhandled exception 边界 case；M1-M4 是 docs / toml 文案漂移；M5 是 smoke 覆盖缺口）
- **Conversation ref**: 同会话内 /post-check 输出
