# Baseline 产出（全书分析后）

你现在接手本地项目 Offpage，你没有任何额外背景知识，请完全按本提示词执行。

## 任务

基于全书分析阶段的产出（世界观概览、候选角色列表、章节摘要），为作品
`{work_id}` 产出 **世界 foundation baseline**（含固定关系网络）和
**角色 identity baseline**。

identity 与 target_baseline 都是 character-level 恒定文件——identity 记录
角色基础事实（aliases / core_wounds / key_relationships 等），target_baseline
记录该角色与其它角色之间的全部 target 关系（全书视野，phase 3 只读不写）。
两者 phase 2 一次产出后永不变化；运行时与当前 stage_snapshot 配套加载。
voice / behavior / boundary / failure_modes 不在 Phase 2 产出——由 Phase 3
char_snapshot lane 在每个 stage_snapshot 中直接生成（S001 从原文 + identity
推演基线种子，S002+ 从前一 stage_snapshot 演变）。

## 作品信息

- work_id: `{work_id}`
- 书名: `{title}`
- 语言: `{language}`
- 目标角色: {target_characters}
- 作品目录: `{work_dir}`
- schemas 目录: `{schemas_dir}`

## 必读文件

请按顺序读取以下文件：

{files_to_read}

## 产出 1：世界 Foundation

基于世界观概览和全书摘要，产出以下世界基础文件。这些文件记录的是 **全书
范围内不随阶段变化的基础设定**，阶段性变化由后续提取阶段的 stage_snapshot
记录。

创建目录结构 `{work_dir}/world/foundation/`，产出：

### foundation.json

世界基础设定文件：

```json
{{
  "work_id": "{work_id}",
  "genre": "...",
  "tone": "...",
  "world_structure": {{
    "summary": "世界的整体结构描述",
    "major_regions": [
      {{
        "name": "区域名",
        "description": "简要描述"
      }}
    ]
  }},
  "power_system": {{
    "summary": "力量体系概述",
    "levels": [
      {{
        "name": "等级名",
        "description": "简要描述"
      }}
    ]
  }},
  "core_rules": [
    {{
      "rule": "规则名",
      "description": "规则描述",
      "impact": "对剧情的影响"
    }}
  ],
  "world_lines": [
    {{
      "name": "篇章名",
      "chapter_range": "起止章节",
      "core_conflict": "核心冲突",
      "setting_features": "环境特征"
    }}
  ],
  "major_factions": [
    {{
      "name": "势力名",
      "description": "简要描述",
      "key_figures": ["相关角色名"]
    }}
  ]
}}
```

### fixed_relationships.json

世界级固定关系网络（不随阶段变化的结构性纽带）：

位置：`{work_dir}/world/foundation/fixed_relationships.json`

必须遵循 `schemas/world/fixed_relationships.schema.json`。

记录血缘、师承、门派归属等跨阶段不变的关系纽带。这些关系是世界视角的客观
事实，不同于角色 identity.json 中的主观关系感知。

```json
{{
  "schema_version": "1.0",
  "work_id": "{work_id}",
  "relationships": [
    {{
      "relationship_id": "FR-001",
      "type": "血缘/师承/门派归属/...",
      "parties": ["角色A", "角色B"],
      "description": "关系描述（≤100 字）"
    }}
  ]
}}
```

初稿基于全书摘要推断，后续 stage 读到原文后修正和补充。

## 产出 2：角色 Identity Baseline

为每个目标角色产出 `identity.json` 和 `manifest.json`。

目标角色列表：{target_characters_list}

### identity.json

位置：`{work_dir}/characters/{{char_id}}/canon/identity.json`

必须遵循 `schemas/character/identity.schema.json`。

重点字段：
- `canonical_name`：角色最终/最通用的正式名称
- `aliases`：结构化别名数组（从身份合并结果直接转化），每条含 name、type（本名/化名/代称/称呼/昵称/绰号/封号/道号/武器名/其他）、effective_stages（可先留空，提取时填充）、source、used_by
- `gender`、`species`、`birth_origin`、`appearance_summary`、`background_summary`、`initial_social_position`、`affiliations`、`distinguishing_features`
- `core_wounds`：角色的核心创伤——跨全故事始终影响角色行为和心理的根源性伤痛。每条含：
  - `wound`：创伤内容
  - `origin`：创伤的来源/成因
  - `behavioral_impact`：对行为的长期影响
- `key_relationships`：角色的核心人物关系（仅记录对角色有重大影响的关系）。每条含：
  - `target`：关系对象
  - `initial_relationship`：故事开始时的关系状态
  - `relationship_arc`：全局演变弧线概述（如"仇人→被迫共处→产生真情→结为伴侣"）
  - `turning_points`：关键转折点列表

注意：这些信息基于全书摘要产出，是初稿。后续 stage 提取读到原文后会修正。
对于不确定的字段直接留空或省略，不要强行填写以示"推断"。
core_wounds 和 key_relationships 基于全书摘要可以产出较准确的初稿——全书
视野有利于识别贯穿故事的创伤和关系弧线。

### manifest.json

位置：`{work_dir}/characters/{{char_id}}/manifest.json`

必须遵循 `schemas/character/character_manifest.schema.json`。

- `character_id`：与目录名一致
- `canonical_name`：与 identity.json 一致
- `aliases`：从 identity.json 的结构化 aliases 中提取名称的扁平字符串数组
- `paths`：填入正确的相对路径。**注意**：
  - `stage_snapshot_root` 必须指向 `characters/{{char_id}}/canon/stage_snapshots`（不是 `canon/stages`）
  - `target_baseline_path` 必须指向 `characters/{{char_id}}/canon/target_baseline.json`（即下方"产出 3"所产文件）

## 产出 3：角色 Target Baseline

为每个目标角色产出 `target_baseline.json`——全书视野下该角色与其它
角色之间的全部 target 关系列表（character-level 恒定文件，与 identity /
fixed_relationships 同源思路：phase 2 一次拍，phase 3 各 stage 只读不写）。

### target_baseline.json

位置：`{work_dir}/characters/{{char_id}}/canon/target_baseline.json`

必须遵循 `schemas/character/target_baseline.schema.json`。

字段：

- `character_id`：本 baseline 描述的角色 ID（与 identity.character_id /
  目录名 / manifest.character_id 三者一致）
- `targets[]`：每条对应一个对方角色。每条含：
  - `target_character_id`：对方角色的 identity.character_id（**统一用
    identity ID，不要用 canonical_name 或 aliases**——规避化名 / 隐藏身份
    导致的歧义）
  - `relationship_type`：关系类型枚举（覆盖亲密度 × 立场两维），常用值：
    `close_kin` 至亲血亲 / `lover` 恋人配偶 / `close_friend` 挚友 /
    `mentor` 师长引路人 / `disciple` 弟子 / `friend` 朋友 / `ally` 盟友 /
    `colleague` 同僚 / `subordinate` 下属 / `superior` 上司 /
    `acquaintance` 泛交 / `stranger` 陌生人 / `rival` 竞争对手（非敌对）/
    `enemy` 敌人 / `nemesis` 宿敌 / `passerby` 路人微弱关联 / `other`
    其他（罕用，需在 description 说明）
  - `tier`：重要程度（站在本角色视角看对方的相对重要性）：
    - `核心` = 亲密圈 / 关键宿敌（驱动主要剧情线）
    - `重要` = 对角色行为有显著影响
    - `次要` = 偶有交互
    - `路人` = 极弱关联但仍纳入 baseline（确保 phase 3 keys ⊆ baseline
      不会因路人被 LLM 写入而 fail）
  - `description`：≤100 字关系描述

**该 baseline 是 phase 3 的硬锚点**：phase 3 stage_snapshot 中
`target_voice_map` / `target_behavior_map` / `relationships` 的 keys 必须
严格 ⊆ `targets[].target_character_id`。这是硬约束（cross-file hard
fail），phase 2 一旦漏判某 target，phase 3 不会自动补救——需要人工编辑
baseline 后重抽该 stage。所以 phase 2 产出时**宁可多列、不可漏列**——
任何在全书摘要里出现过、与本角色有过互动 / 涉及关系演变 / 即使只是
路人但被点名提及的角色，都应纳入。

`tier` 与 `relationship_type` 的关系：tier 描述本角色视角下的"重要度
梯度"，relationship_type 描述"关系性质"。两者正交，不要把 tier 信息
强行塞进 relationship_type。例如同样是 `friend`，对主角而言可能是 `核心`
（青梅竹马）或 `次要`（点头之交）。

## 产出 4：世界与角色 Stage Catalog 初始化

为世界包和每个目标角色创建空的 stage_catalog.json，后续提取时逐阶段追加。

- `{work_dir}/world/stage_catalog.json`（遵循 `schemas/world/world_stage_catalog.schema.json`）
- `{work_dir}/characters/{{char_id}}/canon/stage_catalog.json`（遵循 `schemas/character/stage_catalog.schema.json`）

世界 catalog 初始内容：

```json
{{
  "schema_version": "1.0",
  "work_id": "{work_id}",
  "stages": []
}}
```

角色 catalog 初始内容：

```json
{{
  "schema_version": "1.0",
  "character_id": "{{char_id}}",
  "work_id": "{work_id}",
  "stages": []
}}
```

**注意**：后续提取追加 stage 条目时，每条**必须**包含 `stage_id`（紧凑英文代号 S###，排序键）、`stage_title`（短标题）、`summary`（一句话摘要）、`snapshot_path`（快照相对路径）。stage_catalog 仅用于 bootstrap 阶段选择，运行时不加载。

## 不在 baseline 阶段产出的文件

以下文件由 `post_processing.py` 在每阶段提取完成后程序化维护（0 token），
baseline 阶段**不需要**创建任何占位文件：

- `{work_dir}/world/world_event_digest.jsonl` — 从世界 stage_snapshot 的
  `stage_events` 生成；首阶段提取后首次创建，后续阶段 upsert。
- `{work_dir}/characters/{{char_id}}/canon/memory_digest.jsonl` — 从角色
  memory_timeline 生成；同样由首阶段 post-processing 首次创建。

baseline 阶段只需完成上文列出的 foundation / fixed_relationships /
identity / manifest / 空 stage_catalog。

## 规则

- 中文作品的 work_id、character_id、路径段、内容使用中文；`stage_id` 使用紧凑英文代号 `S###`（如 `S001`），`stage_title` 使用中文短标题
- 中文作品的 character_id 直接使用中文角色名
- 所有产出文件必须是格式良好的 JSON
- 创建目录结构时确保所有中间目录存在
- 这是基于摘要的初稿——宁可保守少写，不可编造细节
- 如果某个字段在摘要中完全无法判断，留空或省略，不要猜测
- **`maxLength` / `maxItems` 是上限不是配额**：schema 给的字段长度 / 条数
  上限只是硬门控，不是要写到的目标。摘要里能支撑 3 条就写 3 条，能写
  50 字就写 50 字，不要为了凑到 maxItems 或 maxLength 而虚构、扩写、
  灌水
