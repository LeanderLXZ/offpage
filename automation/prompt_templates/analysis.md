# 自动化分析阶段

你现在接手本地项目 `persona-engine`，你没有任何额外背景知识。

## 目标

基于已经完成的章节摘要，对作品 `{work_id}` 执行以下分析任务并产出结构化结果：

1. **跨 chunk 角色身份合并** — 统一不同 chunk 中同一角色的不同名称
2. **世界观概览** — 分析世界观基础信息，产出世界观概览文件
3. **源文件分批规划** — 按自然剧情边界制定 batch plan（每个 batch 对应一个剧情阶段）
4. **候选角色识别** — 识别可建包的候选角色（基于合并后的身份信息）

## 作品信息

- work_id: `{work_id}`
- 书名: `{title}`
- 语言: `{language}`
- 总章节数: `{chapter_count}`
- 作品目录: `{work_dir}`

## 输入：章节摘要

章节摘要已经完成，存放在以下目录：

`{summaries_dir}`

每个文件是一个 chunk 的归纳结果（JSON），包含该 chunk 内每章的 summary、key_events、characters_present、potential_boundary 等字段。

## 执行步骤

### 步骤 1：读取所有摘要

读取 `{summaries_dir}` 下的所有 JSON 文件，按 chunk 顺序建立全书剧情脉络的完整认知。

重点关注：
- 每章的 `summary` 和 `key_events` — 了解剧情走向
- `potential_boundary` 标记为 true 的章节 — 候选阶段边界
- `characters_present` — 角色出场频率
- `identity_notes` — 角色身份变化线索（获得新名称、揭示真实身份、化名等）

### 步骤 1.5：跨 chunk 角色身份合并

**重要**：由于章节归纳是分 chunk 独立进行的，同一角色可能在不同 chunk 中以不同名称出现（例如前期的代称和后期的正式名）。在进入下一步之前，你必须：

1. 汇总所有 chunk 中出现的角色名称
2. 利用 `identity_notes`、角色特征一致性、叙事上下文等线索，识别出哪些不同名称实际上指向同一角色
3. 建立一个"名称 → 角色"的合并映射

合并判断依据：
- 相同叙事位置出现的角色特征一致
- `identity_notes` 中明确记录了身份揭示或名称变更
- 角色行为模式、能力、与其他角色的关系在前后一致
- 其他角色对其的反应/态度延续

不确定的合并应标注为推测。

### 步骤 1.8：世界观概览

基于所有章节摘要，分析作品的世界观基础信息，产出世界观概览文件。

概览应包含：
- **题材与基调**：作品的题材类型和整体基调
- **世界结构**：世界地理/空间结构、主要区域划分
- **力量体系**：修炼/能力体系的基本框架和等级划分（如有）
- **主要势力**：主要组织、阵营、国家/门派的基本格局
- **大世界线**：故事的大时代/篇章划分（如"天苍篇→仙界篇→蓝星篇"），每个大阶段的核心冲突和环境特征
- **核心设定规则**：影响剧情走向的关键世界规则（如转世机制、天道规则等）

输出文件：`{work_dir}/analysis/incremental/world_overview.json`

JSON 结构：

```json
{{
  "work_id": "{work_id}",
  "genre": "...",
  "tone": "...",
  "world_structure": {{
    "summary": "...",
    "major_regions": ["..."]
  }},
  "power_system": {{
    "summary": "...",
    "levels": ["..."]
  }},
  "major_factions": [
    {{
      "name": "...",
      "description": "..."
    }}
  ],
  "world_lines": [
    {{
      "name": "...",
      "chapter_range": "...",
      "core_conflict": "...",
      "setting_features": "..."
    }}
  ],
  "core_rules": ["..."]
}}
```

### 步骤 2：源文件分批规划（本阶段最核心的产出）

**为什么这一步至关重要：** 你划定的每个 batch 边界会直接成为整个系统的 stage 边界。世界快照、角色快照、记忆时间线、运行时阶段选择——全部建立在这个切分之上。切分不合理会导致角色人格转变生硬、世界事件时间线断裂、用户选择某阶段时体验不连贯。请投入足够精力确认剧情节点。

制定详细的 batch plan。要求：

- 默认每批 10 章，但必须优先贴近自然剧情边界——剧情边界的准确性比章节数量均匀更重要
- **⚠️ 硬性约束：最小批次 5 章，最大批次 15 章。任何超过 15 章的 batch 都是违规的。** 如果一个大故事弧跨度超过 15 章，必须在其中寻找次级剧情节点（如小高潮、场景转换、时间跳跃）将其拆分为多个 batch。绝不允许为了保持剧情完整性而创建超过 15 章的 batch
- 每个 batch 条目包含：batch_id, stage_id, chapters, chapter_count, boundary_reason, key_events_expected
- 为 stage_id 取一个有意义的中文名称（如"阶段1_南林初遇"），不要只用编号
- `boundary_reason` 必须说明为什么在此处切分（例如"主角离开某地""重大事件结束""新势力登场"），不能只写"满 10 章"
- 参考摘要中的 `potential_boundary` 标记，但不要机械地以它为唯一依据——你需要从全局剧情结构出发做最终判断
- **自检**：完成 batch plan 后，逐一检查每个 batch 的 `chapter_count`。如有任何一个 ≤4 或 ≥16，必须调整切分点直到全部 batch 满足 5-15 章约束

输出文件：`{work_dir}/analysis/incremental/source_batch_plan.json`

JSON 结构：

```json
{{
  "work_id": "{work_id}",
  "default_batch_size": 10,
  "total_chapters": {chapter_count},
  "batches": [
    {{
      "batch_id": "batch_001",
      "stage_id": "阶段1_...",
      "chapters": "0001-0010",
      "chapter_count": 10,
      "boundary_reason": "...",
      "key_events_expected": ["..."]
    }}
  ]
}}
```

### 步骤 3：候选角色识别

基于所有章节摘要中的 `characters_present` 和 `identity_notes` 信息，以及步骤 1.5 的身份合并结果，识别可建包的候选角色。

**关键要求**：同一角色的不同名称必须合并为一个候选条目。character_id 应选择该角色最通用或最终的正式名称。所有其他名称（代称、化名、昵称、封号等）记入 `aliases` 字段。

为每个候选角色提供：
- character_id（中文名，选择最终/最通用的名称）
- aliases（所有已知的其他名称列表，标注类型和首次出现的大致章节范围）。
  **type 必须使用以下枚举值之一**：本名 / 化名 / 代称 / 称呼 / 昵称 / 绰号 /
  封号 / 道号 / 武器名 / 其他。不要使用自由描述（如"易容伪装"→应为"化名"，
  "前世称号"→应为"封号"，"天道对其称呼"→应为"称呼"）
- 角色简介（2-3 句）
- 预估出场频率（高/中/低）
- 预估重要程度（主角/重要配角/次要配角）
- 建议是否建包（是/否/待定）

输出文件：`{work_dir}/analysis/incremental/candidate_characters.json`

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

- 中文作品使用中文标识和中文路径段
- 产出文件都应是格式良好的 JSON
- **同一角色的不同名称不得作为独立候选条目出现**——必须合并
- 如果不确定两个名称是否为同一角色，在 description 中标注推测并说明依据
- 你只负责分析，不要开始提取世界或角色信息
