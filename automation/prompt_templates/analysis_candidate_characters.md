# 自动化分析阶段 — Candidate Characters Lane

你现在接手本地项目 Offpage，你没有任何额外背景知识。本次任务**仅产出一件文件**：`candidate_characters.json`，即作品 `{work_id}` 的可建包候选角色列表（基于跨 chunk 身份合并）。

## 作品信息

- work_id: `{work_id}`
- 书名: `{title}`
- 语言: `{language}`
- 总章节数: `{chapter_count}`
- 作品目录: `{work_dir}`

## 输入：裁剪后的章节摘要（lane 专用）

裁剪后的 chunk JSON 文件已经准备好，存放在：

`{lane_inputs_dir}`

每个文件是一个 chunk 的归纳结果（JSON），**已经按 candidate_characters lane 的需求做了字段裁剪**——只保留以下字段：

**per-summary 层（每章一条，角色出场 + 事件上下文 + 身份变化的主要信号）**：
- `chapter`（章号锚点，用于 aliases 的 `first_appearance` 推断）
- `summary`（100-150 字本章核心剧情概述——为身份合并提供事件上下文，例如"主角 A 被告知自己其实是势力 X 的转世"这类隐含身份链通常在 `summary` 里完整描述，光读 `identity_notes` 短句无法还原）
- `characters_present`（本章实质互动角色，最常用名形式）
- `identity_notes`（≤50 字本章身份相关线索：化名建立、真名揭示、封号赋予等）

**chunk-level 二级字段（势力归属辅助身份合并）**：
- `chunk_factions[]`（仅 `name` + `members_present`；势力名 + 本 chunk 归属此势力的 raw 角色名清单——化名 / 真名 / 称呼任一形式）

schema 契约 → `schemas/analysis/chapter_summary_chunk.schema.json`（注意：lane 输入只是子集；输出 schema 见下方）。

## 执行步骤

### 步骤 1：读取所有裁剪后的 chunk

读取 `{lane_inputs_dir}` 下所有 `chunk_*.json`，按 `chunk_index` 顺序汇总：

- 全书出现过的所有角色名（来自 `characters_present` + `identity_notes` + `chunk_factions[].members_present`）
- 每个名字的出现章号区间
- 身份变化线索（来自 `identity_notes` 短句 + `summary` 的事件上下文——后者覆盖隐含身份链，例如"昨日剑客原来是大长老转世"这类只在事件描述里完整出现的链路）

### 步骤 2：跨 chunk 角色身份合并

**重要**：由于章节归纳是分 chunk 独立进行的，同一角色可能在不同 chunk 中以不同名称出现（例如前期的代称和后期的正式名）。在产出候选角色之前，你必须：

1. 汇总所有 chunk 中出现的角色名称
2. 利用 `identity_notes`、角色特征一致性、叙事上下文等线索，识别出哪些不同名称实际上指向同一角色
3. 建立一个"名称 → 角色"的合并映射

合并判断依据：

- 相同叙事位置出现的角色特征一致
- `identity_notes` 中明确记录了身份揭示或名称变更
- `summary` 的事件上下文揭示的隐含身份链（如"角色 A 在某 chunk 被披露为另一势力的转世 / 化身 / 卧底"——这种链路通常只在 `summary` 中完整描述，`identity_notes` 短句不一定覆盖）
- 角色行为模式、能力、与其他角色的关系在前后一致
- 其他角色对其的反应 / 态度延续
- `chunk_factions[].members_present` 中归属同一势力且语境匹配

不确定的合并应在角色 `description` 中标注推测并说明依据。

### 步骤 3：候选角色识别

基于合并后的身份信息，识别可建包的候选角色。

**关键要求**：同一角色的不同名称必须合并为一个候选条目。`character_id` 应选择该角色最通用或最终的正式名称。所有其他名称（代称、化名、昵称、封号等）记入 `aliases` 字段。

为每个候选角色提供：

- `character_id`（中文名，选择最终 / 最通用的名称）
- `aliases`（所有已知的其他名称列表，标注类型和首次出现的大致章节范围）
  - **type 必须使用以下枚举值之一**：本名 / 化名 / 代称 / 称呼 / 昵称 / 绰号 / 封号 / 道号 / 武器名 / 其他。不要使用自由描述（如"易容伪装"→应为"化名"，"前世称号"→应为"封号"，"天道对其称呼"→应为"称呼"）
- `description`（角色简介，2-3 句）
- `frequency`（预估出场频率：高 / 中 / 低）
- `importance`（预估重要程度：主角 / 重要配角 / 次要配角）
- `recommended`（建议是否建包，boolean: true 或 false；不确定时取 false 让 Phase 1.5 用户最终决定）

### 步骤 4：落盘

输出文件：`{work_dir}/analysis/candidate_characters.json`
schema 契约 → `schemas/analysis/candidate_characters.schema.json`（aliases[].type / frequency / importance 三处 enum、recommended 为 boolean、长度上下限以 schema 为准）。

JSON 结构：

```json
{{
  "work_id": "{work_id}",
  "candidates": [
    {{
      "character_id": "角色正式名",
      "aliases": [
        {{
          "name": "别名",
          "type": "代称",
          "first_appearance": "约第XX章"
        }}
      ],
      "description": "简介",
      "frequency": "高",
      "importance": "主角",
      "recommended": true
    }}
  ]
}}
```

## 规则

- 中文作品的 character_id 使用中文
- 产出文件必须是格式良好的 JSON
- **同一角色的不同名称不得作为独立候选条目出现**——必须合并
- 如果不确定两个名称是否为同一角色，在 `description` 中标注推测并说明依据
- 你**只**负责 candidate_characters，不要尝试产出 world_overview / stage_plan（它们由其他 lane 并行处理）
- 不要修改 `{lane_inputs_dir}` 下的输入文件
- 不要读取 `sources/` 下的原始章节正文——本 lane 输入仅基于 chunks 摘要
{retry_note}
