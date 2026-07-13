# Baseline lane：角色 identity + manifest

你现在接手本地项目 Offpage，你没有任何额外背景知识，请完全按本提示词执行。

## 任务

基于全书分析阶段的产出，为作品 `{work_id}` 的**单个角色** `{char_id}` 产出两件 character-level 恒定文件：

1. `{work_dir}/characters/{char_id}/canon/identity.json`
2. `{work_dir}/characters/{char_id}/manifest.json`

identity 记录角色基础事实（aliases / core_wounds / key_relationships 等），
phase 2 一次产出后永不变化；运行时与当前 stage_snapshot 配套加载。
voice / behavior / boundary / failure_modes 不在本 lane 产出——由 Phase 3
char_snapshot lane 在每个 stage_snapshot 中直接生成。

## 作品信息

- work_id: `{work_id}`
- 书名: `{title}`
- 语言: `{language}`
- 本 lane 角色: `{char_id}`
- 作品目录: `{work_dir}`
- schemas 目录: `{schemas_dir}`

## 必读文件

请按顺序读取以下文件：

{files_to_read}

全书摘要在 `{lane_inputs_dir}/` 下（`chunk_*.json`，已按本 lane 需要裁剪字段：每章 `chapter` + `summary` + `characters_present` + `identity_notes`）。

## identity.json

位置：`{work_dir}/characters/{char_id}/canon/identity.json`

必须遵循 `schemas/character/identity.schema.json`。

重点字段：
- `canonical_name`：角色最终/最通用的正式名称
- `aliases`：结构化别名数组（从 candidate_characters 中本角色的身份合并结果直接转化），每条含 name、type（本名/化名/代称/称呼/昵称/绰号/封号/道号/武器名/其他）、effective_stages（可先留空，提取时填充）、source、used_by
- `gender`、`species`、`birth_origin`、`appearance_summary`、`background_summary`、`initial_social_position`、`affiliations`、`distinguishing_features`——`affiliations` 的势力名与 `world/foundation/foundation.json` 的 `major_factions[].name` 对齐
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

## manifest.json

位置：`{work_dir}/characters/{char_id}/manifest.json`

必须遵循 `schemas/character/character_manifest.schema.json`。

- `character_id`：与目录名一致（= `{char_id}`）
- `canonical_name`：与 identity.json 一致
- `aliases`：从 identity.json 的结构化 aliases 中提取名称的扁平字符串数组
- `paths`：填入正确的相对路径。**注意**：
  - `stage_snapshot_root` 必须指向 `characters/{char_id}/canon/stage_snapshots`（不是 `canon/stages`）
  - `target_baseline_path` 必须指向 `characters/{char_id}/canon/target_baseline.json`（该文件由并行的 target_baseline lane 产出，此刻可能尚不存在——路径照填，不要因此留空）

## 规则

- 中文作品的 character_id 直接使用中文角色名
- 所有产出文件必须是格式良好的 JSON
- 创建目录结构时确保所有中间目录存在
- 这是基于摘要的初稿——宁可保守少写，不可编造细节
- 如果某个字段在摘要中完全无法判断，留空或省略，不要猜测
- **`maxLength` / `maxItems` 是上限不是配额**：schema 给的字段长度 / 条数
  上限只是硬门控，不是要写到的目标。摘要里能支撑 3 条就写 3 条，能写
  50 字就写 50 字，不要为了凑到 maxItems 或 maxLength 而虚构、扩写、灌水
- **只写本 lane 的两件输出文件**——不要创建或修改任何其他文件
  （foundation / fixed_relationships / target_baseline 由并行 lane 产出；
  stage_catalog / digest 由后续 phase 程序化维护）
{retry_note}
