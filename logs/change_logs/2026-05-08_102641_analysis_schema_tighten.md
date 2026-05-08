# analysis_schema_tighten

- **Started**: 2026-05-08 10:26:41 EDT
- **Branch**: main (worktree at ../offpage-main, detached HEAD @ 3e36ecd)
- **Status**: PRE

## 背景 / 触发

2026-05-08 03:54-04:30 EDT 跑 work_id=`<work_id>` phase 0/1/1.5 + phase 2 部分（被 SIGTERM 中止），看实际 phase 1 三 lane 产物（world_overview.json / candidate_characters.json / stage_plan.json）后讨论收紧三组 analysis schema：

- chunk per-summary `key_events`：经 #52 lane 拆分后，三个 phase 1 lane 都不投这字段（prompt_builder.py 当前只在注释里提）+ Phase 2 baseline 也不读，是死字段。同时 `summary` 100-150 字范围装不下事件 + 设定二者，需要扩到 150-200。
- candidate `recommended`：是 LLM 自报推荐意愿（拍脑袋打 boolean），不可靠；改为 phase 1.5 基于 `importance == "主角"` 程序推荐（用户仍可手选追加）。
- candidate `aliases.first_appearance`：字符串描述（"约第 0042 章"），既不参与下游也不能用于程序检索，是冗余。
- world_overview `major_regions` / `power_system.levels`：当前是字符串数组，与 chunk_regions / chunk_power_levels 的 `{name, description}` 对象形态不对齐。
- world_overview `core_rules`：maxItems 20 对应 N chunk × ≤5 条原始规则去重合并到 30 比较合理；同时 maxLength 100→150 强制 LLM 重新整理而不是照搬 chunk 行。

todo: T-ANALYSIS-SCHEMA-TIGHTEN（已登记到 docs/todo_list.md `## Next` 段，本次 commit 一并归档移到 archived `## Completed`）。

## 结论与决策

按上一轮 plan 模式拍板的方案落地。具体澄清两点：

- Q1（recommended 删除范围）：删候选层的 `recommended` boolean。Phase 1.5 改为基于 `importance == "主角"` 程序判定默认勾选，不勾选其他 importance 等级的 candidate（用户仍可手选追加）。
- Q2（core_rules.items 形态）：保留字符串数组，只 `maxItems` 20→30 + `items.maxLength` 100→150。强制 LLM 重新整理而非照搬 chunk 行。

落盘策略：A 路径——清掉现有 untracked `works/<work_id>/` 后从 phase 0 全新跑 e2e（属于本 PR 的下一步运行验证；不在本 commit 内执行）。

## 计划动作清单

**Schema（3 件）**

- file: `schemas/analysis/chapter_summary_chunk.schema.json` →
  - `summaries.items.required` 删 `key_events`
  - 删 `summaries.items.properties.key_events`
  - `summaries.items.properties.summary.minLength` 100→150；`maxLength` 150→200
- file: `schemas/analysis/candidate_characters.schema.json` →
  - `candidates.items.required` 删 `recommended`
  - 删 `candidates.items.properties.recommended`
  - `aliases.items.required` 删 `first_appearance`
  - 删 `aliases.items.properties.first_appearance`
- file: `schemas/analysis/world_overview.schema.json` →
  - `world_structure.major_regions.items` 由 string 改 `{name (≤15), description (≤30)}` 对象（对齐 `chunk_regions.items`）；name 必填
  - `power_system.levels.items` 同上对齐 `chunk_power_levels.items`；name 必填
  - `core_rules.maxItems` 20→30；`core_rules.items.maxLength` 100→150（保留字符串数组形态）

**Prompt template（5 件）**

- file: `automation/prompt_templates/summarization.md` →
  - 删 `key_events` 教学（per-chapter 字段说明 + 示例 JSON 中的 `key_events` 字段）
  - 把 `summary` 长度教学从 100-150 改 150-200
- file: `automation/prompt_templates/analysis_world_overview.md` →
  - 输入契约文字与新 chunk 字段集对齐（无 `key_events`，summary 字段不投）
  - 输出 `major_regions` / `power_system.levels` 升对象 + `core_rules` 30/150 教学
- file: `automation/prompt_templates/analysis_stage_plan.md` →
  - 输入契约：per-summary 仅含 `chapter` + `summary`（无 `key_events`，本就不投）
- file: `automation/prompt_templates/analysis_candidate_characters.md` →
  - 删 `aliases.first_appearance` 字段教学
  - 删 `recommended` 字段教学
  - 输入契约：per-summary 含 `chapter` + `summary` + `characters_present` + `identity_notes`（无 `key_events`）
- file: `automation/prompt_templates/baseline_production.md` →
  - 输入契约描述同步：不读 `key_events`

**Code（2 件）**

- file: `automation/persona_extraction/prompt_builder.py` →
  - 注释里描述 `key_events` 的两处（约 line 122 / line 166）随 schema 删除一并清理
  - 自身 projector 当前已不投 `key_events`，无代码逻辑改动
- file: `automation/persona_extraction/orchestrator.py` →
  - line 1586 附近：`recommended` 字段消失后，Phase 1.5 默认勾选改为基于 `importance == "主角"` 程序判定
  - `RECOMMENDED` 标签的渲染逻辑改基于 importance

**Docs（2 件）**

- file: `docs/architecture/schema_reference.md` →
  - chunk schema 表：删 `key_events` 行；改 `summary` 长度
  - candidate schema 表：删 `recommended` / `aliases.first_appearance` 行
  - world_overview schema 表：改 `major_regions` / `levels` 形态；改 `core_rules` bound
- file: `docs/architecture/extraction_workflow.md` →
  - Phase 0 / Phase 1 / Phase 1.5 流程描述与新 schema 对齐
  - Phase 1.5 推荐逻辑改基于规则的描述

**ai_context（2 件）**

- file: `ai_context/architecture.md` →
  - Phase 0 / Phase 1 描述更新：chunk per-summary 字段集变化（删 `key_events`，summary 100-150→150-200）
  - Phase 1.5 推荐逻辑改基于规则的描述
- file: `ai_context/decisions.md` →
  - 修订 #27m（chunk-level secondary fields 段落）：删 `key_events` 描述、改 `summary` 长度
  - 修订 #52（Phase 1 三 lane）：删 `key_events` 在 lane 投影描述里的提及
  - 新增 decision 条目（顺位）：本次三组 schema 收紧 + Phase 1.5 推荐规则化

## 验证标准

- [ ] 三个 schema 文件 jsonschema metaschema 校验通过（`python -c "import json; from jsonschema import Draft202012Validator; ..."` 三次）
- [ ] `python -c "from automation.persona_extraction import orchestrator, prompt_builder, validator"` import 无报错
- [ ] grep 全仓库（除 `logs/` `works/` `users/` `docs/todo_list_archived.md`）无 `key_events` 残留引用
- [ ] grep 全仓库（除 `logs/` `works/` `users/` `docs/todo_list_archived.md`）无 `first_appearance` 残留引用
- [ ] grep 全仓库（除 `logs/` `works/` `users/` `docs/todo_list_archived.md`）无 candidate 层 `recommended` boolean 字段残留引用（注意区分上下文：`RECOMMENDED` 标签字符串保留，但其判定逻辑改为基于 importance）
- [ ] 新 schema 对一个最小合法样本 + 一个 negative case 各跑一次（手写 inline，确认 gate 行为符合预期）
- [ ] Cross-File Alignment 表（conventions.md）所列 chunk schema 行的 9 个下游文件全部已动

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

**Schema (3)**
- `schemas/analysis/chapter_summary_chunk.schema.json` — `summaries.items.required` 删 `key_events`；删 `properties.key_events`；`summary.minLength` 100→150 / `maxLength` 150→200；`description` 改"3-5 句话 150-200 字 + 关键剧情节点"；`characters_present.description` 改"化名 / 代称在 identity_notes 注明"
- `schemas/analysis/candidate_characters.schema.json` — `candidates.items.required` 删 `recommended`；删 `properties.recommended`；`aliases.items.required` 删 `first_appearance`；删 `aliases.items.properties.first_appearance`；`importance.description` 加"Phase 1.5 默认勾选 = importance == 主角"
- `schemas/analysis/world_overview.schema.json` — `world_structure.major_regions.items` 由 string 升 `{name (≤15), description (≤30), additionalProperties: false, required: [name]}` 对象（对齐 `chunk_regions.items`）；`power_system.levels.items` 同上对齐 `chunk_power_levels.items`；`core_rules.maxItems` 20→30；`core_rules.items.maxLength` 100→150；三处 `description` 同步刷新

**Prompt templates (4 件触动)**
- `automation/prompt_templates/summarization.md` — 删 `key_events` 教学（per-章字段说明 + JSON 示例 + 规则段 3 处）；`summary` 长度教学 100-150 → 150-200 + "3-5 句话 + 关键剧情节点"；规则段把"key_events 中注明化名"改成"identity_notes 中注明"
- `automation/prompt_templates/analysis_world_overview.md` — 字段映射表：`major_regions` / `levels` 升对象（含 ≤15 / ≤30 bound）+ `core_rules` 30 条 / ≤150 字符串教学 + "强制重新整理 vs 照搬 chunk 行" 反偷懒说明；JSON 示例同步对象形态
- `automation/prompt_templates/analysis_stage_plan.md` — per-summary 字段集 100-150 → 150-200；裁剪原则段落改为"`characters_present` / `emotional_tone` / `identity_notes` 删除"（key_events 已从 chunk schema 整体删除）
- `automation/prompt_templates/analysis_candidate_characters.md` — per-summary 字段集 100-150 → 150-200；删 `aliases.first_appearance` / `recommended` 字段教学；改"不需要再判断是否建议建包" + JSON 示例同步
- `automation/prompt_templates/baseline_production.md` — 经检查无 `key_events` / `recommended` / `first_appearance` 提及，本次未改动（field mapping 表本就基于 chunk-level 字段，与 per-summary 无关）

**Code (2)**
- `automation/persona_extraction/prompt_builder.py:118-124,165-172` — module-level 注释段：stage_plan lane 描述改"per-summary chapter + summary only ... 150-200 CJK-char summary 承载 turning-point 信号"；candidate lane 描述对齐 #52 实际投影；`_project_chunk_for_stage_plan` docstring 改"key_events 已从 chunk schema 删除（决策 #53）"。projector 函数本身无代码变更（本就不投 key_events）
- `automation/persona_extraction/orchestrator.py:1582-1614` — `confirm_with_user` Phase 1.5：新增 `recommended_ids: list[str]` 程序计算（基于 `c.get("importance") == "主角"`）；`RECOMMENDED` 标签从 `c.get("recommended")` 改为 importance 判断；新增"Default selection (importance=主角): X, Y" + "(Press Enter to accept default, or type IDs to override / extend.)" 提示行；空输入 fallback 到 `recommended_ids`（preset_characters 路径不变）；空 selected → sys.exit(1) 行为不变

**Docs (4)**
- `docs/architecture/schema_reference.md` — chunk per-summary 字段表删 `key_events` / 改 `summary` 长度；消费方说明改"`summary` 150-200 字承载，原 `key_events` 已删除"；world_overview 关键字段表 `major_regions` / `levels` 形态升级 + `core_rules` bound 更新；candidate 关键字段表删 `recommended` / `aliases.first_appearance` 行 + 加"Phase 1.5 默认勾选基于 importance"
- `docs/architecture/extraction_workflow.md` — Phase 1.5 段加"默认勾选 = importance==主角 程序判定"段；裁剪原则段落删 `key_events` 提及
- `ai_context/architecture.md:154-156` — Phase 0 chunk 字段集删 `key_events` + 加 `summary` 150-200；Phase 1 lane 投影字段集删 `key_events`；Phase 1.5 加"Default-recommended set = candidates with importance==主角"段
- `ai_context/decisions.md` — 修订 #27m（key_events 段落改"removed"，`summary` 长度更新 100-150 → 150-200）；修订 #52（lane 投影删 `key_events` 提及）；新增 #53（本次三组 schema 收紧 + Phase 1.5 推荐规则化总条目，含三块改动 + 完整 plumbing 列表）

**TODO 维护**
- `docs/todo_list.md` — T-ANALYSIS-SCHEMA-TIGHTEN 从 Next 移到 In Progress（state = "schema/prompt/code/ai_context/docs 完成 + 静态 gate 全过；e2e 验证待跑"）；T-PHASE0-CHUNK-SCHEMA-EXPAND 加注释行说明本任务进一步收紧；Index 段刷新（In Progress 4→5 / Next 3→2 / Total 15 不变）

## 与计划的差异

- **calculation: 触动文件数 = 14**（vs PRE 计划清单的 10）。多出 3 件 = `docs/todo_list.md`（todo 维护，PRE 没单列）+ `analysis_stage_plan.md`（PRE 在第 5 项中合并提及）+ `analysis_candidate_characters.md`（PRE 在第 5 项中合并提及）。`baseline_production.md` 实测无需改动（PRE 列了但实际无引用），减 1 件，所以净增 3 件、净改 14 件
- **calculation: Phase 1.5 默认勾选 UI 行为加强**（vs PRE 只提"程序判定"）：实际加了"Default selection: X, Y" 提示行 + "(Press Enter to accept default...)" + 空输入回退到 default 的 fallback 逻辑。这是对"用户仍可手选追加 / 取消"的具体落地。preset_characters 路径不变。
- **calculation: schema 同步刷新 description 字段**（vs PRE 只列 required / properties / bounds）：每个改动字段的 `description` 一并更新，确保 prompt 注入路径取到新描述

## 验证结果

- [x] 三个 schema 文件 jsonschema metaschema 校验通过 — Draft202012Validator.check_schema 三个 schema 全过
- [x] `python -c "from automation.persona_extraction import orchestrator, prompt_builder, validator, scene_archive"` import 无报错
- [x] grep 全仓库无 `key_events` 残留主动引用 — 仅命中 4 处 = 1 prompt 教学行（"不留独立 key_events 字段"明确说删除）+ 1 prompt_builder 注释（解释决策 #53）+ 4 处 docs/decisions/ai_context（描述删除）+ logs（历史）+ docs/todo_list.md（活跃任务条目本就描述任务）
- [x] grep 全仓库无 `first_appearance` 残留主动引用 — 仅命中决策 #53 描述 + schema_reference.md 描述删除 + todo_list 任务条目 + logs（历史）
- [x] grep 全仓库无 candidate 层 `recommended` boolean 残留引用 — 仅命中决策 #53 / extraction_workflow.md 描述删除 + todo_list / logs（历史）。`RECOMMENDED` 标签字符串保留但其判定逻辑已改为 importance
- [x] 新 schema 对最小合法样本 + 多个 negative case 各跑一次：positive 全过；negative 覆盖 chunk 拒 key_events / summary < 150 / summary > 200，candidate 拒 first_appearance / recommended，world_overview 拒 string major_regions / string levels item / core_rules > 30 / items > 150；boundary 测试 core_rules len 150 + maxItems 30 全过
- [x] Cross-File Alignment 表（conventions.md）所列 chunk schema 行的 9 个下游文件全部已动（schemas / 5 prompts (其中 baseline 经核实无需改) / prompt_builder / docs/architecture / ai_context；validator.py 经检查无相关引用）

## Completed

- **Status**: DONE
- **Finished**: 2026-05-08 11:37:41 EDT

<!-- /post-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：14/14 项计划（含 baseline_production.md "verified-no-change" 子项）+ 7/7 项验证
- Missed updates: 2 条（详见对话）—— PRE「执行偏差」段未登记 todo_list 状态变更（PRE line 17 说"归档"实际进 In Progress）；Index 段 T-PHASE0-CHUNK-SCHEMA-EXPAND 行 Updated 字段未随正文 2026-05-08 注释同步刷新

### 轨 2 — 影响扩散
- Findings: High=0 / Medium=4 / Low=2
- Open Questions: 3 条（详见对话）

## 复查时状态
- **Reviewed**: 2026-05-08 11:56:26 EDT
- **Status**: REVIEWED-PARTIAL
  - 轨 1 全落实，但 2 条 Missed updates（log + Index 字段刷新滞后）
  - 轨 2 4 条 Medium（无 High）：char_id 输入无校验 / In Progress 5-entry 单槽违规 / 无主角 case sys.exit 信息退化 / PRE 执行偏差漏登记
- **Conversation ref**: 同会话内 /post-check 输出
