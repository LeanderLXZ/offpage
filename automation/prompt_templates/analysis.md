# 自动化分析阶段

你现在接手本地项目 Offpage，你没有任何额外背景知识。

## 目标

基于已经完成的章节摘要，对作品 `{work_id}` 执行以下分析任务并产出结构化结果：

1. **跨 chunk 角色身份合并** — 统一不同 chunk 中同一角色的不同名称
2. **世界观概览** — 分析世界观基础信息，产出世界观概览文件
3. **源文件阶段规划** — 按自然剧情边界制定 stage plan（每个 stage 对应一个剧情阶段）
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

每个文件是一个 chunk 的归纳结果（JSON），包含两层信息：

**per-summary 层**（每章一条）：`chapter` / `title` / `summary`（100-150 字事件描述）/ `key_events`（≤5×≤50 字关键事件）/ `characters_present` / `emotional_tone` / `identity_notes`。

**chunk-level 二级字段层**（每 chunk 聚合一份，本 chunk 视野下的设定信号）：
- `chunk_arc_summary`（≤200 字本 chunk 整体剧情弧，required）
- `chunk_world_rules[]`（≤5 条 × `{{rule, description, observed_impact}}`；本 chunk 揭示的世界规则；observed_impact 可能是具体影响或 fallback "未在本 chunk 直接观察"）
- `chunk_power_levels[]`（≤20 条 × `{{name, description}}`；本 chunk 出现的力量体系等级）
- `chunk_factions[]`（≤20 条 × `{{name, description, members_present}}`；势力名 + 本 chunk 归属的 raw 角色名清单——化名 / 真名 / 称呼任一形式，**身份合并由步骤 1.5 完成**）
- `chunk_regions[]`（≤20 条 × `{{name, description}}`；本 chunk 出现的地理区域）

schema 契约 → `schemas/analysis/chapter_summary_chunk.schema.json`。

## 执行步骤

### 步骤 1：读取所有摘要

读取 `{summaries_dir}` 下的所有 JSON 文件，按 chunk 顺序建立全书剧情脉络的完整认知。

per-summary 层重点关注：
- 每章的 `summary` 和 `key_events` — 了解剧情走向 + stage 边界离散信号
- `emotional_tone` 突变 — 候选阶段边界信号
- `characters_present` — 角色出场频率
- `identity_notes` — 角色身份变化线索（获得新名称、揭示真实身份、化名等）

chunk-level 二级字段层是步骤 1.8（世界观概览）的**直接信号源**，按下方字段映射使用：
- `chunk_world_rules[]` → `world_overview.core_rules[]`（综合多 chunk 的同一规则、合并描述；observed_impact 给 Phase 2 `foundation.core_rules.impact` 提供局部锚点）
- `chunk_power_levels[]` → `world_overview.power_system.levels[]`（综合多 chunk 同一等级名 / 阶段名，去重）
- `chunk_factions[]` → `world_overview.major_factions[]`（综合多 chunk 同一势力，合并描述；members_present 在步骤 1.5 身份合并后再映射到 character_id，**步骤 1.8 不需要**）
- `chunk_regions[]` → `world_overview.world_structure.major_regions[]`（综合多 chunk 同一地名）；步骤 2 stage_plan 的区域转换信号也来自本字段
- `chunk_arc_summary` → `world_overview.world_lines.core_conflict`（多 chunk 弧线串成大世界线核心冲突）
- `world_overview.world_structure.summary` / `world_lines.setting_features` 由你综合 `chunk_regions` / `chunk_power_levels` / `chunk_factions` / `chunk_world_rules` 的信号写出（无 chunk 直供字段，需要综合判断）

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

输出文件：`{work_dir}/analysis/world_overview.json`
schema 契约 → `schemas/analysis/world_overview.schema.json`，长度上下限以 schema 为准。

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

### 步骤 2：源文件阶段规划（本阶段最核心的产出）

**为什么这一步至关重要：** 你划定的每个 stage 边界会直接成为整个系统的 stage 边界。世界快照、角色快照、记忆时间线、运行时阶段选择——全部建立在这个切分之上。切分不合理会导致角色人格转变生硬、世界事件时间线断裂、用户选择某阶段时体验不连贯。请投入足够精力确认剧情节点。

**核心原则：拐点先行，章数后定。** 不要先决定"每段多少章"再去找剧情边界，必须从全书剧情拐点反推 stage 边界——以下三子步**严格按顺序**执行，**不要跳步、不要倒推**：

#### 步骤 2.1：全局剧情拐点扫描（必须先于 2.2 完成）

通览所有 chunk 的 `chunk_arc_summary` / `key_events` / `emotional_tone` / `chunk_regions` / `identity_notes` / per-summary `summary`，列出全书所有**剧情拐点候选**（plot inflection points）。每个拐点写一行，包含：

- 章号（如 `C0037`）
- 拐点类型（**枚举**：场景转换 / 弧线切换 / 主要角色登场退场 / 关键身份揭示 / 时间跳跃 / 阵营变动 / 情感转折 / 重大伤亡）
- 一句话事件描述

这份候选拐点列表是你的工作记录，**作为推理过程产出**（写在你的思考链 / agent 日志里，不需要进入最终 `stage_plan.json` 文件）；**完成 2.1 候选列表后才允许进入 2.2**。

#### 步骤 2.2：候选拐点分组成 stage

沿章节顺序遍历 2.1 列表，把相邻拐点合并成 stage：

- **章数硬范围 [5, 15] 闭区间**——schema `chapter_count.minimum/maximum` + orchestrator `_check_stage_plan_limits` 双重强制；任何 ≤4 或 ≥16 都是违规
- 拐点优先级（高 → 低）：场景转换 > 弧线切换 > 阵营变动 > 重大伤亡 > 关键身份揭示 > 主要角色登场退场 > 时间跳跃 > 情感转折
- 同优先级取舍：选能让前后两段都更接近"拐点驱动而非数量驱动"的落点；不要为了让章数靠近某个数字而硬挪边界
- 每个 stage 条目包含：`stage_id` / `stage_title` / `chapters` / `chapter_count` / `boundary_reason`
- `stage_id` 使用紧凑英文代号 `S###`（三位数字零填充，如 `S001`、`S049`），**不使用中文或其他格式**。这是整套 ID 家族（`M-S###-##` / `E-S###-##` / `SC-S###-##` / `SN-S###-##`）的共同 stage 段
- `stage_title` 是人类可读的中文短标题（如"<location_a>初遇"、"<location_b>下山"），作为 bootstrap 阶段选择时展示给用户的阶段名
- `boundary_reason` 必须直接对应 2.1 列表里的某个具体拐点（命名拐点类型 + 关键事件），不能只写"满 N 章"或泛泛剧情概括

#### 步骤 2.3：反锚定自检（完成 2.2 后必跑，不允许跳过）

依次检查产出的 stage_plan：

1. **章数分布反锚定检查**：把所有 stage 的 `chapter_count` 列出来；若有 **≥3 个连续 stage 章数完全相等**（如连续 5 个 stage 都是 10 章），说明大概率落入了"按章数等分、再给每段挑剧情节点写理由"的偷懒模式——**回到 2.1 重审拐点列表是否覆盖完整、回到 2.2 重新切分**，直到该模式不再出现
2. **boundary_reason 实质检查**：每个 stage 的 `boundary_reason` 必须能指回 2.1 列表里的某个具体拐点（章号 + 类型）；如果某个 boundary_reason 只是"叙事过渡"、"剧情推进"、"主角成长"这类泛泛描述，说明该 stage 边界不是从拐点反推出来的——回到 2.2 重切
3. **章数硬范围检查**：任意 stage 的 `chapter_count` ≤4 或 ≥16 必须调整切分点直到全部 stage 落在 [5, 15] 闭区间

输出文件：`{work_dir}/analysis/stage_plan.json`
schema 契约 → `schemas/analysis/stage_plan.schema.json`（`chapter_count` 5-15 hard、`stage_id` `^S\d{3}$`、字段集合以 schema 为准）。

JSON 结构（**注意：示例中的 `chapter_count` 故意用非整数倍数字，避免暗示某个章数是"甜区"**）：

```json
{{
  "work_id": "{work_id}",
  "total_chapters": {chapter_count},
  "stages": [
    {{
      "stage_id": "S001",
      "stage_title": "主角初登场",
      "chapters": "C0001-C0008",
      "chapter_count": 8,
      "boundary_reason": "场景转换：主角离开起始村落赴下一城"
    }},
    {{
      "stage_id": "S002",
      "stage_title": "城中遭遇",
      "chapters": "C0009-C0021",
      "chapter_count": 13,
      "boundary_reason": "弧线切换：主线从入城任务转为势力对抗"
    }},
    {{
      "stage_id": "S003",
      "stage_title": "结义与远行",
      "chapters": "C0022-C0032",
      "chapter_count": 11,
      "boundary_reason": "关键身份揭示：盟友真实身份曝光迫使主角离城"
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
- 建议是否建包（boolean: true 或 false；不确定时取 false 让 Phase 1.5 用户最终决定）

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

- 中文作品的 work_id、character_id、路径段使用中文；`stage_id` 使用紧凑英文代号 `S###`（如 `S001`），`stage_title` 使用中文短标题
- 产出文件都应是格式良好的 JSON
- **同一角色的不同名称不得作为独立候选条目出现**——必须合并
- 如果不确定两个名称是否为同一角色，在 description 中标注推测并说明依据
- 你只负责分析，不要开始提取世界或角色信息

## 不需要你产出的文件

- `works/{work_id}/manifest.json`（作品包清单）——Phase 1.5 用户确认角色与
  阶段范围后，由 orchestrator 程序化写出，schema 为
  `schemas/work/works_manifest.schema.json`；你只需保证 `stage_plan.json`
  与 `candidate_characters.json` 正确即可，不要手动创建 `manifest.json`。
