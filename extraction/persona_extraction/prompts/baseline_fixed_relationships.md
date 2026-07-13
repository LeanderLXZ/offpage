# Baseline lane：世界级 fixed_relationships

你现在接手本地项目 Offpage，你没有任何额外背景知识，请完全按本提示词执行。

## 任务

基于全书分析阶段的产出，为作品 `{work_id}` 产出世界级固定关系网络 `{work_dir}/world/foundation/fixed_relationships.json`——**仅记录全书从开始到结束都未改变的结构性纽带**。

必须遵循 `schemas/world/fixed_relationships.schema.json`。

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

全书摘要在 `{lane_inputs_dir}/` 下（`chunk_*.json`，已按本 lane 需要裁剪字段：每章 `chapter` + `summary` + `characters_present`，以及 chunk 级 `chunk_factions[].{name, members_present}`）。

## 判定核心

是否在本作时间线内**贯穿不变**。关系类型只是常见示例：

- ✅ **属于 fixed**：血缘 / 自始即有的师承 / 自始即有的门派归属 / 长辈
  晚辈等贯穿始终的结构性关系。这些关系是世界视角的客观事实，不同于
  角色 identity.json 中的主观关系感知
- ❌ **不属于 fixed**（**任何在故事中才建立 / 改变 / 解除的关系都不是
  fixed**）：故事中才结成的师承、加入的门派、收养、结义、结婚 / 离婚、
  决裂、归化、敌对转盟友、盟友转敌对等。这些走 character/stage_snapshot
  的 `relationships`，按 stage 演进；写入此处会污染世界级骨架

```json
{
  "schema_version": "1.0",
  "work_id": "{work_id}",
  "relationships": [
    {
      "relationship_id": "FR-001",
      "type": "血缘 / 自始即有的师承 / 自始即有的门派归属 / 长辈晚辈 / ...",
      "parties": ["角色A", "角色B"],
      "description": "关系描述（≤100 字）"
    }
  ]
}
```

`parties` 内的角色优先使用 `candidate_characters.candidates[].character_id`（runtime 靠它绑定角色包）；确属固定关系但对方不在 candidate 集内时才写 raw 名。

初稿基于全书摘要 + chunk 级字段推断（`chunk_factions.members_present`
经身份合并后可作为势力归属信号；血缘 / 自始即有的师承等结构性
关系仍需结合摘要确认），后续 stage 读到原文后修正和补充（修正限于补漏、
订正描述等，不应把 stage-acquired 关系反向迁入此处）。

## 规则

- 中文作品的 character_id 直接使用中文角色名
- 所有产出文件必须是格式良好的 JSON
- 创建目录结构时确保所有中间目录存在
- 这是基于摘要的初稿——宁可保守少写，不可编造细节
- 如果某段关系在摘要中完全无法判断是否贯穿不变，不要写入
- **`maxLength` / `maxItems` 是上限不是配额**：schema 给的字段长度 / 条数
  上限只是硬门控，不是要写到的目标，不要为了凑数而虚构、扩写、灌水
- **只写本 lane 的输出文件** `world/foundation/fixed_relationships.json`——
  不要创建或修改任何其他文件（foundation / identity / target_baseline 由
  并行 lane 产出；stage_catalog / digest 由后续 phase 程序化维护）
{retry_note}
