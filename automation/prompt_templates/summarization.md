# 章节归纳（Chunk {chunk_index}/{total_chunks}）

你现在接手本地项目 Offpage，你没有任何额外背景知识。

## 目标

对作品 `{work_id}` 的章节 {start_chapter}–{end_chapter} 进行归纳，产出每章的结构化摘要 + chunk-level 二级聚合字段。

## 作品信息

- work_id: `{work_id}`
- 书名: `{title}`
- 语言: `{language}`
- 本 chunk 章节范围: {start_chapter}–{end_chapter}（共 {chunk_chapter_count} 章）
- 源目录: `{source_dir}`

## 执行步骤

### 步骤 1：读取所有章节

读取以下章节文件的全部内容：

{chapter_file_list}

读完所有章节后再开始写归纳，确保对整个 chunk 的剧情脉络 + 出现过的世界规则 / 力量体系 / 势力 / 区域有完整认知。

### 步骤 2：逐章归纳（per-summary）

对每一章产出一条结构化摘要，**所有字段均 required**。schema 契约 → `schemas/analysis/chapter_summary_chunk.schema.json`，长度上下限以 schema 为准、本说明只描述用途。**bound 是硬上限不是配额**——能写清的不要为凑长度注水。

- `chapter`: 章节标识，与 `chapter_index.json` 的 `chapter_id` 一致（C 前缀 + 4 位零填充，如 `"C0001"`）
- `title`: 章节标题（从原文提取；原文无明确标题时为空字符串）
- `summary`: 3-5 句话概括本章核心剧情（事件描述 + 关键剧情节点）。长度 150-200 字。Phase 1 monolithic stage_plan 边界判定的主要文本信号——既要把推动剧情的关键事件写进去（不要为凑长度水），也要把场景 / 节奏 / 转折交代清楚。**设定 / 世界规则 / 力量体系 / 势力 / 区域信号写到 chunk-level 二级字段（步骤 3），不要塞进 summary**
- `characters_present`: 本章有实质互动的角色列表（不计背景群演）
- `emotional_tone`: 本章主要情绪基调（≤ 20 字，例如"紧张" / "温馨" / "搞笑" / "悲伤"）
- `identity_notes`: 本章中的角色身份相关线索（化名建立、真名揭示、封号赋予等），≤ 50 字。无此类事件时为空字符串

### 步骤 3：chunk-level 二级聚合字段

读完整个 chunk 后，从全 chunk 视野填以下五个 chunk-level 字段。它们承载世界规则 / 力量体系 / 势力 / 区域 / 剧情弧信号——Phase 1 综合多 chunk 产 `world_overview`，Phase 2 综合多 chunk 产 `foundation`。**没有这些字段下游 LLM 只能凭 genre 套模板**。

- `chunk_arc_summary`（**required**）：本 chunk 整体剧情弧的概述（≤200 字）。例如"主角进入<location_a>遭遇<faction_b>截杀，逃亡过程中习得<power_level_c>，最终与<character_d>缔结契约离开<location_a>"。Phase 1 综合多 chunk 弧线产出 `world_lines.core_conflict`
- `chunk_world_rules[]`（最多 5 条）：本 chunk 揭示的世界规则（修炼 / 转世 / 天道 / 契约 / 因果等结构性规则）。每条：
  - `rule`（≤50 字，**required**）：规则名 + 一句概括（如"转世规则：每千年一次大轮回，记忆自动封存"）
  - `description`（≤50 字）：规则的具体机制描述。本 chunk 无更详细解释 → 写空字符串
  - `observed_impact`（≤50 字）：本 chunk 观察到的对剧情 / 角色的影响。**禁止静默留空**——本 chunk 未直接观察到触发时，必须显式填 `"未在本 chunk 直接观察"` 或同义短语；空字符串会被下游误读为"无影响"。本字段是 Phase 2 综合 `foundation.core_rules.impact` 的局部锚点
- `chunk_power_levels[]`（最多 20 条）：本 chunk 出现的力量体系等级 / 阶段名。每条：
  - `name`（≤15 字，**required**）：等级名（如"练气"、"筑基"、"金丹"）
  - `description`（≤30 字）：等级简要描述。本 chunk 无解释 → 写空字符串
- `chunk_factions[]`（最多 20 条）：本 chunk 出现的势力 / 组织 / 阵营 / 国家 / 门派。每条：
  - `name`（≤15 字，**required**）：势力名
  - `description`（≤50 字）：势力简要描述。本 chunk 无解释 → 写空字符串
  - `members_present[]`（最多 20 条 × ≤10 字）：本 chunk 中归属此势力的角色名列表。**raw 角色名**——化名 / 真名 / 称呼任一形式，**不要尝试做身份合并**（跨 chunk 身份合并是 Phase 1.5 的事）。无明确归属角色 → 写空数组
- `chunk_regions[]`（最多 20 条）：本 chunk 出现的地理 / 空间区域 / 地名。每条：
  - `name`（≤15 字，**required**）：区域 / 地名（中文长地名常见 6-10 字，如"北方苦寒之地"、"西北边境蛮荒部族联盟"）
  - `description`（≤30 字）：区域简要描述。本 chunk 无解释 → 写空字符串

**字段空值规则**：

- `chunk_arc_summary` 永远必须填（每 chunk 必有整体剧情弧）
- 其余 4 个 array 字段（`chunk_world_rules` / `chunk_power_levels` / `chunk_factions` / `chunk_regions`）允许空数组——本 chunk 无相关信号时不要硬凑
- sub-field `description` 允许空字符串——本 chunk 有解释 → 必须填；无解释 → 写空字符串。**空有意义，不是默认偷懒**
- `chunk_world_rules[].observed_impact` **不允许空字符串**——必须显式标注（具体影响 / 或 fallback "未在本 chunk 直接观察"），让 Phase 2 区分"无影响"和"未观察到"

### 步骤 4：写入输出文件

将结果写入：`{output_path}`

JSON 结构（不要添加 schema 之外的字段；**严格遵循 `additionalProperties: false`**）：

```json
{{
  "work_id": "{work_id}",
  "chunk_index": {chunk_index},
  "chapters": "{start_chapter}-{end_chapter}",
  "chunk_arc_summary": "...",
  "chunk_world_rules": [
    {{ "rule": "...", "description": "...", "observed_impact": "未在本 chunk 直接观察" }}
  ],
  "chunk_power_levels": [
    {{ "name": "...", "description": "" }}
  ],
  "chunk_factions": [
    {{ "name": "...", "description": "...", "members_present": ["...", "..."] }}
  ],
  "chunk_regions": [
    {{ "name": "...", "description": "" }}
  ],
  "summaries": [
    {{
      "chapter": "C0001",
      "title": "...",
      "summary": "...",
      "characters_present": ["...", "..."],
      "emotional_tone": "...",
      "identity_notes": ""
    }}
  ]
}}
```

## 规则

- 中文作品使用中文产出内容
- 摘要要简洁但信息量充分，重点在于 **剧情事件**，不是文学分析
- `summary` 必须把本章的关键事件 + 场景 + 节奏 / 转折一并写进去（不留独立 key_events 字段了），跳过日常水文
- `characters_present` 只记录有实质互动的角色，不记背景群演。**注意角色可能以化名、代称、昵称等出现**——如果你能判断某个名称实际上是已知角色的别名，在 `characters_present` 中使用其最常用的名称，并在 `identity_notes` 中注明化名关系（如"角色A以XX身份潜入"）；**chunk_factions[].members_present 内不做合并**，按 raw 角色名记
- 你只负责归纳，不要开始提取世界或角色信息（chunk-level 二级字段是给下游 Phase 1/2 用的素材，不是世界 / 角色提取）
- 读取所有章节后再开始写摘要，确保对整个 chunk 的剧情脉络有完整认知
{retry_note}
