---
log_id: 2026-05-04_145024_phase0_chunk_schema_expand
task_id: T-PHASE0-CHUNK-SCHEMA-EXPAND
---

# phase0_chunk_schema_expand

- **Started**: 2026-05-04 14:50:24 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

phase 1 [world_overview.json](../../schemas/analysis/world_overview.schema.json) 与 phase 2 [foundation.json](../../schemas/world/foundation.schema.json) 多字段被 chunk schema 信息密度不足约束，实际质量分层：

- ✅ genre / tone / world_lines.{name,chapter_range} — chunk 字段直接可信
- 🟡 world_structure.summary / major_regions / world_lines.core_conflict — 半可信
- 🟠 power_system.summary / major_factions.description / world_lines.setting_features — chunk 信号稀疏，LLM 多按 genre 推断
- 🔴 power_system.levels / core_rules / core_rules.impact — chunk 完全无信息源，LLM 凭 genre 套常见模板（仙侠 → 练气筑基金丹元婴）

根因：现 [chapter_summary_chunk.schema.json](../../schemas/analysis/chapter_summary_chunk.schema.json) 只有 per-章字段，且 prompt 明令"事件描述而非文学评论"——所有"设定 / 体系 / 规则"信号被主动过滤。foundation 是 world_overview 的"结构化精化版"，信息源相同，可信度同分层。

## 结论与决策

讨论后定方案 (a) + (b)：

- **(a) 精简 per-章冗余字段**：仅删 `location`，`summary` 50-100 → 100-150 字承载更详细事件；保留 `key_events` ≤5×≤50 字（phase 1 monolithic 模式 stage_plan 边界判定的离散信号，删除会让 LLM 只能从 summary 自然语言读 5-15 章 stage 边界，chunk_arc_summary 25 章一弧粒度太粗无法替代）
- **(b) 加 5 chunk-level 二级字段**承载世界规则 / 力量体系 / 势力 / 区域 / 弧线信号

14 个原不可信字段实质改善：9 升 ✅（chunk 直供）+ 4 升 🟡（chunk 提供具体信号、phase 1/2 LLM 综合写）+ 1 信号源更具体（world_structure.summary 仍 🟡 但底层从 chunk_regions / chunk_power_levels / chunk_factions 综合，非凭 genre 拼）。

显式不加：

- `chunk_fixed_relationships[]` — chunk-level 视野（25 章）无法判断"贯穿全书不变"，会把大量 stage-acquired 关系误判为 fixed → 污染 [foundation/fixed_relationships.json](../../schemas/world/fixed_relationships.schema.json) + 连带污染 phase 3 character stage_snapshot.relationships 的 fixed_relationship 例外路径。fixed_relationships 全书判定权留 phase 2 baseline_production
- `chunk_setting_features` — 杂物收纳字段，与 chunk_world_rules / chunk_power_levels / chunk_factions / chunk_regions 职责重叠风险，LLM 大概率把内容重复写一遍让 4 个专门字段留空。world_structure.summary / world_lines.setting_features 由 phase 1 LLM 综合 4 个 chunk-level 字段写出

## 计划动作清单

### Schema 改造（[schemas/analysis/chapter_summary_chunk.schema.json](../../schemas/analysis/chapter_summary_chunk.schema.json)）

顶层 properties 加 5 个 chunk-level 二级字段：

- `chunk_arc_summary`: string ≤200（本 chunk 整体剧情弧描述；required）
- `chunk_world_rules[]`: array maxItems 5 × items `{rule: string ≤50, description: string ≤50, observed_impact: string ≤50}`，items `additionalProperties: false` + `required: [rule]`，description / observed_impact optional
- `chunk_power_levels[]`: array maxItems 20 × items `{name: string ≤15, description: string ≤30}`，items `additionalProperties: false` + `required: [name]`，description optional
- `chunk_factions[]`: array maxItems 20 × items `{name: string ≤15, description: string ≤50, members_present: array maxItems 20 × items string maxLength 10}`，items `additionalProperties: false` + `required: [name]`，description ≤50 对齐 foundation.major_factions.description ≤50 减少 phase 2 综合时截断
- `chunk_regions[]`: array maxItems 20 × items `{name: string ≤15, description: string ≤30}`，items `additionalProperties: false` + `required: [name]`

per-章字段精简（summaries[] items 内）：

- 删 `location`（chunk_regions[] 完全覆盖）
- `summary` bound：50-100 → 100-150
- 保留 `chapter` / `title` / `summary` / `key_events`（≤5×≤50）/ `characters_present` / `emotional_tone` / `identity_notes`

required 列表更新：

- chunk-level 顶层 required 加 `chunk_arc_summary`（每 chunk 必有）
- 4 个 array 字段（chunk_world_rules / chunk_power_levels / chunk_factions / chunk_regions）非 required（本 chunk 无相关信号则空数组）
- per-章 required 删 `location`，保留 `key_events`

### Prompt 同步（必同步否则 LLM 不知道新字段语义）

- [automation/prompt_templates/summarization.md](../../automation/prompt_templates/summarization.md) — 加 chunk-level 字段填写指引：
  - chunk_arc_summary：本 chunk 整体剧情弧（≤200 字，required）
  - chunk_world_rules[]：本 chunk 揭示的世界规则（maxItems 5）；observed_impact 强引导"宁可写'未在本 chunk 直接观察'也不要静默留空"——避免下游 foundation.core_rules.impact 改善失效；description 允许空但鼓励填
  - chunk_power_levels / chunk_factions / chunk_regions：本 chunk 出现的体系 / 势力 / 地名清单 + 简要说明，sub-field description "如本 chunk 有解释 → 必须填；无解释 → 写空字符串"明示
  - per-章 summary 100-150 字仍以"事件描述"为主，保留 key_events 离散信号约束（chunk-level 字段是设定信号正轨）
- [automation/prompt_templates/analysis.md](../../automation/prompt_templates/analysis.md) — phase 1 prompt 步骤 1（"读取所有摘要"）更新：明确 chunk-level 二级字段存在 + 字段映射（chunk_world_rules → core_rules / chunk_power_levels → power_system.levels / chunk_factions → major_factions / chunk_regions → world_structure.major_regions / chunk_arc_summary → world_lines.core_conflict）；location 信号源改成 chunk_regions[]；world_structure.summary / world_lines.setting_features 由 LLM 综合多 chunk 字段写出
- [automation/prompt_templates/baseline_production.md](../../automation/prompt_templates/baseline_production.md) — phase 2 prompt 重写"产出 1：世界 Foundation"段的 LLM 思考链（不只加"信息源说明"几句话）：从"基于全书摘要推断 foundation"改为"读 chunk-level 直供字段（chunk_world_rules / chunk_power_levels / chunk_factions / chunk_regions）→ 综合多 chunks → 写 foundation"；chunk_world_rules.observed_impact 给 core_rules.impact 提供局部锚点

### ai_context / docs 同步

- [ai_context/architecture.md](../../ai_context/architecture.md) Phase 0 描述加 chunk-level 二级字段说明
- [ai_context/data_model.md](../../ai_context/data_model.md) chapter_summary_chunk 描述更新
- [ai_context/decisions.md](../../ai_context/decisions.md) 新增决策：chunk schema 加 chunk-level 设定信号字段 + 不加 chunk_fixed_relationships 的理由 + 不加 chunk_setting_features 的理由
- [ai_context/conventions.md](../../ai_context/conventions.md) Cross-File Alignment 表加 chapter_summary_chunk → summarization.md / analysis.md / baseline_production.md 的同步关系
- [docs/architecture/extraction_workflow.md](../../docs/architecture/extraction_workflow.md) Phase 0 章节同步
- [docs/architecture/schema_reference.md](../../docs/architecture/schema_reference.md) chapter_summary_chunk 描述

### 代码侧

- 已 grep 确认 [orchestrator.py](../../automation/persona_extraction/orchestrator.py) / [validator.py](../../automation/persona_extraction/validator.py) 无代码直接读 chapter.location（仅 consistency_checker.py 自身的 issue.location 同名假阳性）—— 删 location 字段无代码侧 break

## 验证标准

静态校验（前置 gate）：

- [ ] [chapter_summary_chunk.schema.json](../../schemas/analysis/chapter_summary_chunk.schema.json) 落地新结构（chunk-level 5 字段 + per-章删 location 扩 summary 100-150 + 保留 key_events），jsonschema metaschema 校验通过
- [ ] 手写 1 个 sample chunk JSON 文件能通过新 schema：含 chunk_arc_summary + 一个非空 chunk_world_rules + 一个非空 chunk_factions 子字段；验证 required + sub-fields 结构 + observed_impact 兜底字符串"未在本 chunk 直接观察"能通过 + sub-object additionalProperties: false 拒收 spurious 字段 + sub-object required 拒收无 name/rule 的空对象 entry
- [ ] `python -c "import automation.persona_extraction.orchestrator; import automation.persona_extraction.validator"` 通过（确认无 import break）
- [ ] grep 全库无残留 `chapter.location` / chunk schema 旧字段引用

文档对齐：

- [ ] ai_context/architecture.md / data_model.md / decisions.md / conventions.md 同步完成
- [ ] docs/architecture/extraction_workflow.md / schema_reference.md 同步完成
- [ ] 不引入 chunk_fixed_relationships / chunk_setting_features（两个决议显式排除）

Runtime 验证（本次 /go 不跑书；落到 Step 6 todo_list 后续 runtime 验证条目；本次只确保静态 gate 通过）。

## 执行偏差

- **PRE 计划动作清单提到 `ai_context/data_model.md` 同步**——该文件不存在
  （todo 条目原文笔误）。`docs/architecture/data_model.md` 是工程级 data
  model 文档，未提 chunk schema 字段层细节，本次也无需更新（chunk schema
  描述现集中在 `docs/architecture/schema_reference.md` 单一权威）。已在
  `## 已落地变更` 中说明为"跳过：文件不存在"。

<!-- POST 阶段填写 -->

## 已落地变更

- **schema** [`schemas/analysis/chapter_summary_chunk.schema.json`](../../schemas/analysis/chapter_summary_chunk.schema.json)：
  顶层 properties 加 5 chunk-level 二级字段
  （`chunk_arc_summary` ≤200 required；`chunk_world_rules[]` maxItems 5 ×
  `{rule≤50,description≤50,observed_impact≤50}`、`chunk_power_levels[]`
  maxItems 20 × `{name≤15,description≤30}`、`chunk_factions[]` maxItems 20
  × `{name≤15,description≤50,members_present[≤20×items≤10]}`、
  `chunk_regions[]` maxItems 20 × `{name≤15,description≤30}`；items 全
  `additionalProperties:false` + `required:[name|rule]`）；顶层 required
  加 `chunk_arc_summary`；per-summary required 删 `location`、`summary`
  bound 50-100 → 100-150；title 字段描述微调（chunk-level 二级聚合）
- **prompt** [`automation/prompt_templates/summarization.md`](../../automation/prompt_templates/summarization.md)：
  全文重写为 4 步骤结构（读章节 → per-summary → chunk-level → 写文件），
  补 chunk-level 字段语义 + observed_impact 强引导 + sub-field description
  空值规则 + 完整 JSON 输出结构
- **prompt** [`automation/prompt_templates/analysis.md`](../../automation/prompt_templates/analysis.md)：
  步骤 1 读取摘要段加 chunk-level 字段两层信息说明 + chunk-level → world_overview
  字段映射表；步骤 2 stage_plan 边界判断信号源由 per-summary `location`
  替换为 `chunk_regions` / `chunk_arc_summary`
- **prompt** [`automation/prompt_templates/baseline_production.md`](../../automation/prompt_templates/baseline_production.md)：
  产出 1 段加新增"思考链：从 chunk-level 二级字段综合产 foundation"
  小节 + 9 行字段映射表 + 3 条关键约束（不凭 genre 套模板 / impact 是综合
  判断不是直接拷贝 / 空信号 = 空字段）；fixed_relationships 注脚加
  members_present 经 phase 1.5 身份合并后用法说明
- **ai_context** [`ai_context/architecture.md`](../../ai_context/architecture.md)：
  Phase 0 段加 chunk-level 二级字段说明 + 字段名 + sub-object 结构约束
- **ai_context** [`ai_context/decisions.md`](../../ai_context/decisions.md)：
  新增决策 27m，含字段定义 / 字段映射 / 显式排除 chunk_fixed_relationships
  + chunk_setting_features 的理由 / members_present 不直接映射到 character_id
  的理由
- **ai_context** [`ai_context/conventions.md`](../../ai_context/conventions.md)：
  Cross-File Alignment 表加 `chapter_summary_chunk.schema.json` 行
  （3 prompt 同步 + ai_context/docs 牵动关系）
- **docs** [`docs/architecture/schema_reference.md`](../../docs/architecture/schema_reference.md)：
  chapter_summary_chunk 章节重写关键字段表（顶层 / chunk-level / per-summary
  三层）+ 消费方映射段
- **docs** [`docs/architecture/extraction_workflow.md`](../../docs/architecture/extraction_workflow.md)：
  Phase 0 通用流程加 chunk-level 二级聚合字段说明
- **docs** [`docs/todo_list.md`](../../docs/todo_list.md)：
  T-PHASE0-CHUNK-SCHEMA-EXPAND 从 `## Next` 移到 `## In Progress`，body
  改为 In Progress 形态（开始时间 / 更新时间 / 当前状态 / 已落地 / 待跑 /
  暂不做的事）；Index 更新（In Progress 3→4，Next 3→2，Total 14 不变）

## 与计划的差异

- PRE 计划写"ai_context/data_model.md"——该文件不存在；`docs/architecture/data_model.md`
  也不需要 chunk-level 字段描述（只承担工程级 data model，schema 字段
  细节集中在 schema_reference.md）。**跳过此项，不影响完成标准**
- PRE 未明确要求 `members_present` 是 raw 角色名而非 character_id 的语义
  注解写到 schema description 里——本次连同 prompt + decision 27m + 改动
  todo body 全部一致写明
- todo_list.md 同时移段 + 更新 Index，原计划只写到"todo_list 同步"
  （Index 维护是默认动作）

## 验证结果

- [x] schema 落地新结构 + jsonschema metaschema 校验通过 — `Draft202012Validator.check_schema` OK
- [x] 手写 sample chunk JSON 通过新 schema — 1 valid + 10 negative case 全过
  - valid sample 含 chunk_arc_summary + 非空 chunk_world_rules + 非空 chunk_factions
  - neg1-2 拒收 spurious sub-key（chunk_world_rules / chunk_factions item 内 unknown_field）
  - neg3-4 拒收无 name / rule 的空对象 entry
  - neg5 拒收 missing chunk_arc_summary（required）
  - neg6 拒收 per-summary location 复现（per-summary additionalProperties:false）
  - neg7-8 拒收 summary < 100 / > 150（minLength / maxLength）
  - neg9 拒收 spurious top-level field（顶层 additionalProperties:false）
  - neg10 拒收 chunk_world_rules > 5 items（maxItems）
  - pos2-3 接受 4 个 array 字段空数组 / 全省略（非 required）
  - pos4 接受 observed_impact 兜底字符串 "未在本 chunk 直接观察"
- [x] orchestrator + validator import 通过 — `python -c "import automation.persona_extraction.orchestrator; import automation.persona_extraction.validator"` OK
- [x] grep 全库无 chapter.location 残留 — `grep -rn "chapter.*\.location\|chunk\.location\|summary.*\.location"` 仅命中 memory_timeline.location / scene_archive.location 等非 chunk-summary 域；无代码读 per-summary location
- [x] ai_context/docs 同步完成 — architecture.md / decisions.md / conventions.md / schema_reference.md / extraction_workflow.md 全过
- [x] 不引入 chunk_fixed_relationships / chunk_setting_features — 显式排除 + decision 27m 记理由

## Review 发现

Step 7 多线 review，**仅 1 个非阻塞建议**（不在本次 intent 范围内，建议
登记到 todo_list）：

- **chunk_world_rules.observed_impact 空字符串 schema-prompt mismatch**：
  schema 接受空字符串（无 `minLength`），但 summarization.md 明令禁
  （"禁止静默留空"）。如 LLM 忽略 prompt 直接写 ""，schema gate 不会拦
  住。两条路径任选其一，不阻塞当前 /go：
  - A: schema 给 `chunk_world_rules.observed_impact` 加 `minLength: 1`
    （belt-and-suspenders，schema 层强制非空）
  - B: baseline_production.md 加一句 "若 observed_impact 为空字符串，
    按本 chunk 未观察处理"（兜底语义对齐）
  - 推荐 A：schema gate 在 phase 0 即时拦住，prior_error 注入 retry，
    避免污染下游

## Completed

- **Status**: DONE
- **Finished**: 2026-05-04 15:11:36 EDT
