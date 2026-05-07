# phase1_parallel_lanes

- **Started**: 2026-05-07 13:26:08 EDT
- **Branch**: main (worktree at ../offpage-main; original checkout extraction/<work_id> stays untouched)
- **Status**: PRE

## 背景 / 触发

Phase 1 现行 `automation/persona_extraction/orchestrator.py:1168 run_analysis` 走单次 `build_analysis_prompt` → 单 claude lane → 一次 LLM 推理产出 world_overview / stage_plan / candidate_characters 三件，schema gate per-file retry 共享 `[phase1].exit_validation_max_retry` 预算。

本会话端到端 runtime 验证（与 T-INGEST-STRUCTURE-MODE / T-PHASE0-CHUNK-SCHEMA-EXPAND / T-BASELINE-DEPRECATE / T-PHASE2-TARGET-BASELINE 同批）实测 phase 1 单 LLM 调用 26min 仍未落盘任何产物，被用户主动 SIGTERM 打断（`works/<work_id>/analysis/progress/extraction_logs/extraction.log` 09:13:21 启动 → 09:40:34 graceful exit）。

读 `automation/prompt_templates/analysis.md` 字段血缘表确认三个产出之间没有硬数据依赖：world_overview 仅吃 chunk-level 二级字段 + 章号；stage_plan 吃 per-summary 全字段 + chunk_arc_summary / chunk_regions；candidate_characters 吃 per-summary 的 characters_present / identity_notes / chapter + chunk_factions.members_present。三件可并行；唯一交叉是 chunk_arc_summary 被 world_overview + stage_plan 双用。

附带发现 `orchestrator.py:1218-1223`：light_novel 模式下 LLM 产出的 stage_plan 立即被 `_build_light_novel_stage_plan()` 程序化派生覆盖——LLM 调用是浪费。本次拆分顺手把 light_novel 模式下 stage_plan lane 的 LLM 调用整体跳过。

`docs/todo_list.md` 已通过 /todo-add 登记 `T-PHASE1-PARALLEL-LANES`（Next 段 + Index 段同步刷新；状态见 git diff），本 /go 即为该任务的实施 + 收尾。

## 结论与决策

A 方案 + 6 项决策：

1. **三独立 prompt template**：`analysis_world_overview.md` / `analysis_stage_plan.md` / `analysis_candidate_characters.md`；现行 `analysis.md` 删除（no legacy fallback）
2. **字段裁剪**（保留较宽，给 LLM 留判断空间）：
   - world_overview lane：work_id / chunk_index / chapters / chunk_arc_summary / chunk_world_rules / chunk_power_levels / chunk_factions（去 members_present）/ chunk_regions / summaries[].chapter
   - stage_plan lane：work_id / chunk_index / chapters / chunk_arc_summary / chunk_regions / summaries[].{chapter, summary, key_events, characters_present, emotional_tone, identity_notes}
   - candidate_characters lane：work_id / chunk_index / chapters / summaries[].{chapter, characters_present, identity_notes} / chunk_factions[].{name, members_present}
3. **tmpdir 喂入**（参考 `analysis/scene_splits/` 既有约定，无 dot 前缀，gitignored）：裁剪后 chunks 写到 `works/{work_id}/analysis/.phase1_lane_inputs/{lane}/chunk_NNN.json`，run_analysis 结束清理；`.gitignore` 追加 `works/*/analysis/.phase1_lane_inputs/`
4. **per-lane retry 复用 phase 2/3 同一份 validate-repair 通道**（repair_agent.run）；预算 per-lane 独立（每 lane 各享 `[phase1].exit_validation_max_retry`，不再共享池）
5. **失败语义**：单 lane 失败不影响其他 lane 已落盘产物保留；`--resume` 时 `reconcile_with_disk` 检测到产物存在 + schema valid 跳过对应 lane
6. **light_novel 优化**：light_novel 模式下 stage_plan lane 整体跳过 LLM，走程序化 `_build_light_novel_stage_plan()`；只剩 world_overview + candidate_characters 两 lane 并行

## 计划动作清单

prompt template 新增 / 删除：
- file: `automation/prompt_templates/analysis_world_overview.md` → 取自现行 analysis.md 步骤 1 + 1.8（裁剪后 chunks 字段说明 + world_overview 产出契约）
- file: `automation/prompt_templates/analysis_stage_plan.md` → 取自现行步骤 1 + 步骤 2 三子步反锚定自检（裁剪后 per-summary 字段说明 + stage_plan 产出契约）
- file: `automation/prompt_templates/analysis_candidate_characters.md` → 取自现行步骤 1 + 步骤 1.5 跨 chunk 身份合并 + 步骤 3（candidate_characters 产出契约）
- file: `automation/prompt_templates/analysis.md` → 删除

prompt_builder 改造：
- file: `automation/persona_extraction/prompt_builder.py` → 删除 `build_analysis_prompt`（行 110-157）；新增 `build_world_overview_prompt` / `build_stage_plan_prompt` / `build_candidate_characters_prompt`；新增 `_project_chunk_for_world_overview` / `_project_chunk_for_stage_plan` / `_project_chunk_for_candidates` 三个内部裁剪函数；新增 `prepare_phase1_lane_inputs(project_root, work_id, lane)` 把裁剪后 chunks 落到 tmpdir

orchestrator 改造：
- file: `automation/persona_extraction/orchestrator.py` → `run_analysis`（行 1168-1330+）改为 fan-out：
  - monolithic：3 lane 并行（concurrent.futures.ThreadPoolExecutor，对齐 phase 3 lane 并发原语）
  - light_novel：2 lane（world_overview + candidate_characters）+ 程序化 `_build_light_novel_stage_plan()` 直接落盘
  - 每 lane 单独：prepare tmpdir → run agent → schema gate → repair_agent.run validate-repair（使用 `[phase1].exit_validation_max_retry` per-lane 独立预算）
  - 失败 lane 不影响其他 lane 产物
  - `try/finally` 清理 tmpdir
- file: `automation/persona_extraction/orchestrator.py` → 删除 import `build_analysis_prompt`（行 68），替换为三个新 build_* 入口

config 调整：
- file: `automation/config.toml [phase1]` → `exit_validation_max_retry` 注释更新为 per-lane 语义；增 `lane_concurrency = 3`（默认 = lane 数）
- file: `automation/persona_extraction/config.py` → 新增 `phase1.lane_concurrency` 字段（如有 dataclass）

gitignore：
- file: `.gitignore` → 追加 `works/*/analysis/.phase1_lane_inputs/`

ai_context / docs 同步：
- file: `ai_context/architecture.md` § Automated Extraction Pipeline → phase 1 描述更新（单 LLM → 3 lane fan-out）
- file: `ai_context/decisions.md` → 新增决策（27p 或下一序号：phase 1 lane 并行 + 字段裁剪 + light_novel stage_plan 跳过 LLM）
- file: `docs/architecture/extraction_workflow.md` § Phase 1 → 流程图 + 描述更新
- file: `automation/README.md` § Phase 1 → 双模式 fan-out 段落更新

todo_list 收尾（Step 6）：
- file: `docs/todo_list.md` → 把 `T-PHASE1-PARALLEL-LANES` 整条从 Next 移除；Index 子表 Next (3) → Next (2)，Total 15 — Next 3 → 14 — Next 2
- file: `docs/todo_list_archived.md` → ## Completed 段追加瘦身条目（标题 + 完成形式 + 1 行摘要 + 本次 log 链接）

## 验证标准

- [ ] `python -c "from automation.persona_extraction.prompt_builder import build_world_overview_prompt, build_stage_plan_prompt, build_candidate_characters_prompt"` 无报错
- [ ] `python -c "from automation.persona_extraction.orchestrator import StagedExtractionOrchestrator"` 无报错（全模块 import 通过）
- [ ] `python -c "import json, jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('schemas/analysis/world_overview.schema.json')))"` + 同样校验 stage_plan / candidate_characters / chapter_summary_chunk schema metaschema 通过（schemas 本次未改但 phase 1 输出仍走这几个 schema gate）
- [ ] 三个 _project_chunk_for_* 函数 smoke：用现有 chunk_001.json 跑一次，检查输出字段集与本 log 决策点 2 列出的字段集匹配（多余 / 缺失字段都算失败）
- [ ] 全仓 `grep -rn "build_analysis_prompt"` 残留 = 0（除本 log 自身和 ai_context/decisions.md 的合法历史引用）
- [ ] 全仓 `grep -rn "analysis\.md\b"` 仅剩本 log + 历史决策正文里的引用，不含 prompt template 残留 / orchestrator 引用
- [ ] orchestrator.run_analysis fan-out 路径：monolithic 走 3 lane；light_novel 走 2 lane + programmatic stage_plan（unit-level inspection；端到端 runtime 验证留给下次 resume）
- [ ] tmpdir 路径在 `.gitignore` 命中：`git check-ignore works/test/analysis/.phase1_lane_inputs/world_overview/chunk_001.json` 退出码 0

## 执行偏差

- **2026-05-07 ~13:35 EDT — per-lane retry 不集成 `repair_agent.run()`，改走 schema-gate + correction_feedback per-lane（与 phase 0 / phase 4 prior_error 注入同形态）**
  - 触发：Step 4a 实现前盘点 phase 2 + phase 3 实际代码路径时发现 `run_baseline_production`（phase 2）**不调** `run_repair`，仅走 `validate_baseline` + `validate_with_length_tolerance`；`run_repair` 在 orchestrator 里只被 phase 3 stage loop 调用一次（行 2249）。即 phase 2 / phase 3 实际不共享 validate-repair 代码（用户原始指引"验证逻辑相同、用的同样代码"在 phase 2 这边并不成立）。
  - 进一步评估：phase 1 输出（world_overview / stage_plan / candidate_characters）是 chunk-level 派生的全书分析文件，不是 stage-anchored 源文抽取。`repair_agent` 的 `SourceContext` 必填 `stage_id` + `T2 source_patch` 假设有 stage chapter range scoped 的章节文档可读——phase 1 lane 输入是全书 chunks 摘要，套用反而引入占位字段 + 失效 fixer 路径。
  - 决定：per-lane retry 用更轻的 schema gate + correction_feedback 模式（与 phase 0 chunk-level prior_error / phase 4 chapter-level prior_error 同形态，已证实对派生分析文件够用），保持 per-lane 独立预算 = `[phase1].exit_validation_max_retry`。其他 5 项决策（lane fan-out / 字段裁剪 / tmpdir / 失败语义 / light_novel skip）不变。
  - 落地：同步更新 `ai_context/decisions.md` #52 (3)、`ai_context/architecture.md` Phase 1 bullet、`docs/architecture/extraction_workflow.md` § Phase 1、`automation/README.md` § Phase 0 / Phase 1 双模式调度 + schema gate 表格里 phase 1 行的 retry 通路描述，把"走 `repair_agent.run(...)` L1/L2/L3 + T0/T1/T2/T3 lifecycle"统一改为"走 schema-gate + correction_feedback per-lane（与 phase 0 / phase 4 prior_error 注入同形态）"。

<!-- POST 阶段填写 -->

## 已落地变更

新增（4 件）：
- `automation/prompt_templates/analysis_world_overview.md` — Phase 1 world_overview lane prompt（chunk-level 二级字段映射 + JSON example + retry_note 占位）
- `automation/prompt_templates/analysis_stage_plan.md` — Phase 1 stage_plan lane prompt（步骤 1/2.1/2.2/2.3 反锚定自检 + JSON example + retry_note 占位；继承 #27m 拐点先行 + 章数硬范围 5-15 设计）
- `automation/prompt_templates/analysis_candidate_characters.md` — Phase 1 candidate_characters lane prompt（步骤 1.5 跨 chunk 身份合并 + 候选角色识别 + retry_note 占位）
- `logs/change_logs/2026-05-07_132608_phase1_parallel_lanes.md` — 本日志

删除（1 件）：
- `automation/prompt_templates/analysis.md`

修改（10 件）：
- `automation/persona_extraction/prompt_builder.py` — 删除 `build_analysis_prompt`（行 110-157），新增 `PHASE1_LANES` 常量 + `_phase1_lane_inputs_root` + `_project_chunk_for_world_overview` / `_project_chunk_for_stage_plan` / `_project_chunk_for_candidates` 三个内部裁剪函数 + `_LANE_PROJECTORS` 映射 + `prepare_phase1_lane_inputs` / `cleanup_phase1_lane_inputs` 两个 tmpdir helper + `_phase1_retry_note` / `_phase1_common_context` 两个内部辅助 + `build_world_overview_prompt` / `build_stage_plan_prompt` / `build_candidate_characters_prompt` 三个公共入口
- `automation/persona_extraction/orchestrator.py` — import 行 67-78 从 `build_analysis_prompt` 替换为三 builder + tmpdir helpers；`run_analysis`（行 1172-1402+）整体重写为 fan-out（lane skip-resume + try/finally cleanup + ThreadPoolExecutor 并发 + per-lane prior_error 注入 retry + length-tolerance gate fallback + light_novel 模式 stage_plan lane 跳过 LLM 走 `_build_light_novel_stage_plan` 程序化派生）
- `automation/persona_extraction/config.py` — `Phase1Config` 加注释说明 per-lane 独立预算 + 新增 `lane_concurrency: int = 3` 字段
- `automation/config.toml` — `[phase1]` 节注释重写 + 新增 `lane_concurrency = 3`
- `.gitignore` — 新增 `works/*/analysis/.phase1_lane_inputs/` 模式
- `ai_context/decisions.md` — 新增 #52 durable 决策（6 项分点）+ 更新 #27i 描述（phase 1 retry 通路）+ 更新 #27m 路径引用（`analysis.md §步骤 2` → `analysis_stage_plan.md §步骤 2`）+ 更新 #27l 路径引用（`{summarization,analysis,baseline_production}.md` → `{summarization,analysis_world_overview,baseline_production}.md`）
- `ai_context/architecture.md` — Phase 1 bullet 整段重写（fan-out 描述 + lane 列表 + 字段裁剪 + per-lane retry）+ "CLI `--resume` phase-agnostic resume" bullet 调整（per-lane product check）
- `ai_context/conventions.md` — Cross-File Alignment 表 chapter_summary_chunk 行更新消费方（analysis.md → 三 lane 模板 + prompt_builder projector 函数对齐）
- `docs/architecture/extraction_workflow.md` — § 3. Phase 1 段整体重写（lane 拆分 / 双模式 / 字段裁剪表 / per-lane retry）；含 Step 7 review 修复（"独立的 repair_agent validate-repair lifecycle" → "独立的 prior_error 注入式 retry"）
- `docs/architecture/schema_reference.md` — 4 处 phase 1 来源同步（chapter_summary_chunk 消费方 + world_overview / stage_plan / candidate_characters 各自的"生成时机"）
- `automation/README.md` — § Phase 0 / Phase 1 双模式调度段加 phase 1 fan-out 描述 + Phase 1 schema gate 表格 retry 通路描述更新 + 目录树同步（删 analysis.md，加 3 lane prompt + 列出全部 9 个 prompt template）
- `docs/todo_list_archived.md` — `## Completed` 段顶部追加 `[T-PHASE1-PARALLEL-LANES]` 完成条目（瘦身格式：标题 + 1 行摘要 + log 链接 + 偏差段引用）
- `docs/todo_list.md` — Step 7 修复：T-PHASE0-CHUNK-SCHEMA-EXPAND 段内 `analysis.md` 链接替换为三 lane 模板链接（lines 565-568 + 590）

## 与计划的差异

主要差异已在「执行偏差」段记录：per-lane retry 由计划的 `repair_agent.run(...)` 改为 schema-gate + `prior_error` 注入（与 phase 0 / phase 4 同形态）。其他 5 项决策（lane fan-out / 字段裁剪 / tmpdir / 失败语义 / light_novel skip）按 PRE 计划实施，无新增偏差。

todo_list 维护：因 `T-PHASE1-PARALLEL-LANES` 在前一会话由 /todo-add 写入 extraction checkout 但未 commit，main worktree 视野下 todo_list.md 没有该条目；本次直接在 `todo_list_archived.md` 落 Completed 条目，main 上 `todo_list.md` 总数维持 14 不变（不需要先添加再移走）。

## 验证结果

- [x] `from automation.persona_extraction.prompt_builder import build_world_overview_prompt, build_stage_plan_prompt, build_candidate_characters_prompt` — OK，三 builder + 三 projector + PHASE1_LANES 常量全部可 import
- [x] `from automation.persona_extraction.orchestrator import ExtractionOrchestrator` — OK（注：原计划写错为 StagedExtractionOrchestrator，实际类名是 ExtractionOrchestrator，已更正）
- [x] jsonschema metaschema 校验：`world_overview` / `stage_plan` / `candidate_characters` / `chapter_summary_chunk` 4 个 schema 全过 `Draft202012Validator.check_schema`
- [x] 三 _project_chunk_for_* 函数 smoke：用合法 chunk sample（含全部 chunk-level 二级字段 + per-summary 全字段）跑一次，三 lane 输出字段集严格匹配本 log 决策点 2 列出的字段（multi-key set 等值断言；多余 / 缺失字段都立即 fail）
- [x] 全仓 `grep -rn 'build_analysis_prompt'` 残留 = 0（仅 ai_context/decisions.md #52 plumbing 段历史引用 + 本 log）
- [x] 全仓 `grep -rn 'analysis.md'` 残留：仅 ai_context/decisions.md 历史决策正文（合法）+ change_logs 旧 log（不动）+ logs/review_reports 历史报告元数据（不动）；docs/todo_list.md 已修复
- [x] orchestrator.run_analysis fan-out 路径：inspect.getsource 验证含 `world_overview` / `stage_plan` / `candidate_characters` 三 lane 名 + `is_light_novel` + `lane_concurrency` + `_build_light_novel_stage_plan` + `cleanup_phase1_lane_inputs` + `prepare_phase1_lane_inputs` + `ThreadPoolExecutor` + `prior_error` 全部到位
- [x] tmpdir gitignore 命中：`git check-ignore works/test/analysis/.phase1_lane_inputs/world_overview/chunk_001.json` exit 0，路径回显
- [x] Step 7 review 4 线（规范 / 实现 / 风险 / 结构）并行跑完，实现线 PASS、规范+结构线发现 2 处小修（extraction_workflow.md:78 的 repair_agent 残留 + todo_list.md 的 analysis.md 链接）已即刻修复；风险线 3 警告（light_novel↔monolithic mode 切换 stage_plan 残留 / prior_error "未生成" vs "json 坏" 诊断粒度 / per-lane retry 总 token 3× 消耗）属边界改进，不阻塞本次 intent，留作后续 todo

## Completed

- **Status**: DONE
- **Finished**: 2026-05-07 14:12:28 EDT
