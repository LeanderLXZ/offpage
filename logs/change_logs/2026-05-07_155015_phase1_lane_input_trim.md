# phase1_lane_input_trim

- **Started**: 2026-05-07 15:50:15 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

实测 phase 1 monolithic 537 章 work，3 lane 并行 wall time 仍偏长（world_overview 6m15s 落盘，stage_plan / candidate_characters 跑过 20min 仍未落盘，无 schema fail 也无 retry——纯 LLM thinking 长尾）。复盘发现各 lane 的 chunk 输入字段裁剪过宽，给了 LLM 与 lane 任务无关的字段，导致 token 量虚高 + LLM 反复"读完再判断哪些有用"耗 thinking budget：

- **world_overview lane** 不需要逐章 `summaries[].chapter` 字段（LLM 写的是全书设定，不依赖章号锚点；chunk-level 二级字段 `chunk_world_rules / chunk_power_levels / chunk_factions / chunk_regions / chunk_arc_summary` 已足够）
- **stage_plan lane** 拐点合并依据是 `chunk_arc_summary`（chunk-level）+ per-summary `summary` 的事件描述；`key_events`（5×50 字活动列表）+ `characters_present` + `emotional_tone` + `identity_notes` 都是身份 / 角色 / 情绪粒度，与"按章序合并相邻拐点"任务正交
- **candidate_characters lane** 当前给了 `chapter` + `characters_present` + `identity_notes` + `chunk_factions[].{name,members_present}`，但缺 per-summary `summary`——LLM 跨 chunk 合并身份时需要事件上下文判断"Character A = <character>化身"这类隐含身份链，光看 `identity_notes` 短句不够

## 结论与决策

**Phase 1 lane 字段裁剪三处调整**（仅改裁剪，不改 lane 拆分 / 重试 / schema gate 等结构）：

| Lane | 当前 | 调整后 |
|---|---|---|
| world_overview | chunk-level 5 字段 + `summaries[].chapter` | chunk-level 5 字段（**删 `summaries` 整段**） |
| stage_plan | chunk_arc_summary + chunk_regions + per-summary 6 字段 | chunk_arc_summary + chunk_regions + per-summary `chapter` + `summary`（**删 key_events / characters_present / emotional_tone / identity_notes**） |
| candidate_characters | chunk_factions[].{name,members_present} + per-summary 3 字段（chapter / characters_present / identity_notes） | chunk_factions[].{name,members_present} + per-summary 4 字段（**加 `summary`**） |

裁剪原则保持不变：每 lane 只接收任务相关字段，token surface 与 lane scope 成正比（decision #52 既定方向）。

## 计划动作清单

- file: `automation/persona_extraction/prompt_builder.py:144-213` → 改 `_project_chunk_for_world_overview` / `_project_chunk_for_stage_plan` / `_project_chunk_for_candidates` 三个 projector
- file: `automation/prompt_templates/analysis_world_overview.md` → 删除 LLM 读 `summaries[]` 的指引
- file: `automation/prompt_templates/analysis_stage_plan.md` → per-summary 字段引用从 6 个缩到 2 个（chapter + summary）；步骤 2.1 / 2.2 / 2.3 措辞跟随调整（拐点候选只能从 `summary` + `chunk_arc_summary` 提取）
- file: `automation/prompt_templates/analysis_candidate_characters.md` → 步骤 1.5（跨 chunk 身份合并）补 `summary` 引用
- file: `ai_context/decisions.md` #52 → 更新三 lane 字段裁剪描述（精确到哪些字段保留 / 删除）
- file: `ai_context/architecture.md` `## Automated Extraction Pipeline` → Phase 1 段三 lane 字段裁剪描述同步
- file: `docs/architecture/extraction_workflow.md` → Phase 1 lane 字段裁剪段同步（按 conventions cross-file 表"Extraction workflow"行）

## 验证标准

- [ ] `python -c "from automation.persona_extraction.prompt_builder import _project_chunk_for_world_overview, _project_chunk_for_stage_plan, _project_chunk_for_candidates"` import 无报错
- [ ] 三个 projector 在 mock chunk 上输出符合裁剪后契约：world_overview 输出无 `summaries` key；stage_plan 输出 `summaries[].keys() ⊆ {chapter, summary}`；candidate_characters 输出 `summaries[].keys() ⊇ {chapter, summary, characters_present, identity_notes}`
- [ ] grep `key_events\|emotional_tone` 在 `analysis_stage_plan.md` 中残留 = 0
- [ ] grep `summaries\[\]` 在 `analysis_world_overview.md` 中残留 = 0（除"删除 / 不再读"等说明性引用）
- [ ] grep `summary` 在 `analysis_candidate_characters.md` 跨 chunk 合并段中出现 ≥ 1
- [ ] decision #52 / architecture.md / extraction_workflow.md 里 phase 1 字段裁剪描述与 prompt_builder.py 实际行为一致

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

- `automation/persona_extraction/prompt_builder.py:144-208` — 三个 projector 重写：
  - `_project_chunk_for_world_overview`：删除 `summaries` 整段（chunk-level 5 字段保留 + faction members_present 仍剥离）
  - `_project_chunk_for_stage_plan`：per-summary 从 6 字段缩到 2 字段（`chapter` + `summary`）
  - `_project_chunk_for_candidates`：per-summary 加 `summary`（共 4 字段）
- `automation/prompt_templates/analysis_world_overview.md:19-31, 44` — 输入字段说明删 summaries 行；步骤 1 `chapter_range` 推理依据从 `summaries[].chapter` 改为 chunk 元信息 `chapters` 范围串
- `automation/prompt_templates/analysis_stage_plan.md:21-32, 42` — 输入字段说明 per-summary 缩到 2 字段；步骤 1 拐点扫描依据从 7 个字段改为 3 个（`chunk_arc_summary` + `summary` + `chunk_regions`）
- `automation/prompt_templates/analysis_candidate_characters.md:19-30, 37-40, 49-56` — 输入字段说明 per-summary 加 `summary` 行；步骤 1 身份变化线索来源加 `summary`；步骤 2 合并判断依据加"`summary` 的事件上下文揭示的隐含身份链"
- `ai_context/decisions.md` #52 (2) — 三 lane 字段裁剪条目重写，明确每 lane 保留 / 删除字段
- `ai_context/architecture.md` Phase 1 段 — `narrow field projection per lane (...)` 子句重写
- `docs/architecture/extraction_workflow.md:101-115` — 三 lane 字段裁剪表 + 裁剪原则段落重写（含 placeholder `Character A / Character B`）

## 与计划的差异

无 — PRE 计划动作清单全部按计划落地，未追加 / 未删除任何文件改动。

## 验证结果

- [x] `python -c "from automation.persona_extraction.prompt_builder import _project_chunk_for_world_overview, _project_chunk_for_stage_plan, _project_chunk_for_candidates"` import 无报错 — 通过（smoke test 同时验证）
- [x] mock chunk 输入下三个 projector 输出符合契约：
  - world_overview top keys 不含 `summaries` ✅
  - stage_plan `summaries[0].keys() == {chapter, summary}` ✅
  - candidate_characters `summaries[0].keys() == {chapter, summary, characters_present, identity_notes}` + faction `members_present` 保留 ✅
- [x] grep `key_events|emotional_tone` 在 `analysis_stage_plan.md` 仅命中 line 30 的"已删除"说明性引用，无功能性引用残留
- [x] grep `summaries\[\]|summaries\b` 在 `analysis_world_overview.md` 仅命中 line 19 的"已删除"说明性引用
- [x] grep `summary` 在 `analysis_candidate_characters.md` 跨 chunk 合并相关段命中 3 处（字段说明 / 步骤 1 身份线索 / 步骤 2 合并依据），≥ 1
- [x] decision #52 / architecture.md / extraction_workflow.md 三处对三 lane 字段裁剪的描述与 prompt_builder.py 实际行为一致

## Completed

- **Status**: DONE
- **Finished**: 2026-05-07 15:56:56 EDT
