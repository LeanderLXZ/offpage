# Baseline 产出（全书分析后）

你现在接手本地项目 `persona-engine`，你没有任何额外背景知识，请完全按本提示词执行。

## 任务

基于全书分析阶段的产出（世界观概览、候选角色列表、章节摘要），为作品
`{work_id}` 产出 **世界 foundation baseline** 和 **角色 identity baseline**。

这些 baseline 是非阶段性的基础信息，后续逐 batch 提取时会作为参照并在
必要时修正。

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

## 产出 2：角色 Identity Baseline

为每个目标角色产出 `identity.json` 和 `manifest.json`。

目标角色列表：{target_characters_list}

### identity.json

位置：`{work_dir}/characters/{{char_id}}/canon/identity.json`

必须遵循 `schemas/identity.schema.json`。

重点字段：
- `canonical_name`：角色最终/最通用的正式名称
- `aliases`：结构化别名数组（从身份合并结果直接转化），每条含 name、type（本名/化名/代称/称呼/昵称/绰号/封号/道号/武器名/其他）、effective_stages（可先留空，提取时填充）、source、used_by
- `gender`、`species`、`birth_origin`、`appearance_summary`、`background_summary`、`initial_social_position`、`affiliations`、`distinguishing_features`
- `core_wounds`：角色的核心创伤——跨全故事始终影响角色行为和心理的根源性伤痛。每条含：
  - `wound`：创伤内容
  - `origin`：创伤的来源/成因
  - `behavioral_impact`：对行为的长期影响
  - `source_type`：canon/inference/ambiguous
- `key_relationships`：角色的核心人物关系（仅记录对角色有重大影响的关系）。每条含：
  - `target`：关系对象
  - `initial_relationship`：故事开始时的关系状态
  - `relationship_arc`：全局演变弧线概述（如"仇人→被迫共处→产生真情→结为伴侣"）
  - `turning_points`：关键转折点列表
  - `source_type`：canon/inference/ambiguous

注意：这些信息基于全书摘要产出，是初稿。后续 batch 提取读到原文后会修正。
对于不确定的字段，标注在 `evidence_refs` 中说明"基于摘要推断"。
core_wounds 和 key_relationships 基于全书摘要可以产出较准确的初稿——全书
视野有利于识别贯穿故事的创伤和关系弧线。

### manifest.json

位置：`{work_dir}/characters/{{char_id}}/manifest.json`

必须遵循 `schemas/character_manifest.schema.json`。

- `character_id`：与目录名一致
- `canonical_name`：与 identity.json 一致
- `aliases`：从 identity.json 的结构化 aliases 中提取名称的扁平字符串数组
- `build_status`：设为 `"extracting"`
- `paths`：填入正确的相对路径。**注意**：`stage_snapshot_root` 必须指向 `characters/{{char_id}}/canon/stage_snapshots`（不是 `canon/stages`）

## 产出 3：世界与角色 Stage Catalog 初始化

为世界包和每个目标角色创建空的 stage_catalog.json，后续提取时逐阶段追加。

- `{work_dir}/world/stage_catalog.json`（遵循 `schemas/world_stage_catalog.schema.json`）
- `{work_dir}/characters/{{char_id}}/canon/stage_catalog.json`（遵循 `schemas/stage_catalog.schema.json`）

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

**注意**：后续提取追加 stage 条目时，每条**必须**包含 `stage_id`、`order`（整数序号）、`title`、`short_summary`（一句话摘要）、`snapshot_path`（快照相对路径）。

## 规则

- 中文作品使用中文标识、中文路径段、中文内容
- 中文作品的 character_id 直接使用中文角色名
- 所有产出文件必须是格式良好的 JSON
- 创建目录结构时确保所有中间目录存在
- 这是基于摘要的初稿——宁可保守少写，不可编造细节
- 如果某个字段在摘要中完全无法判断，留空或省略，不要猜测
