# Baseline lane：foundation key_figures 替换

你现在接手本地项目 Offpage，你没有任何额外背景知识，请完全按本提示词执行。

## 任务

替换 `{work_dir}/world/foundation/foundation.json` 的 `major_factions[].key_figures` 内 raw 名为 character_id。

phase 1 foundation lane 已经落盘 foundation.json，`major_factions[].key_figures` 字段含 phase 1 写入的 **raw 名**（chunk_factions[].members_present[] 跨 chunk 合并去重产出的化名 / 真名 / 称呼任一）。phase 1 阶段身份合并由 candidate_characters lane 并行处理，foundation lane 拿不到 character_id 终态，所以只能写 raw 名。本 lane 在身份合并完成后做"替换"工作：能匹配的 raw 名换为 character_id，匹配不上的保留 raw 名。

## 作品信息

- work_id: `{work_id}`
- 书名: `{title}`
- 语言: `{language}`
- 作品目录: `{work_dir}`
- schemas 目录: `{schemas_dir}`

## 必读文件

请按顺序读取以下文件：

{files_to_read}

## 读取契约

- 输入：`{work_dir}/world/foundation/foundation.json`（phase 1 foundation lane 已产，含 raw 名 key_figures）+ `{work_dir}/analysis/candidate_characters.json`（phase 1 candidate_characters lane 已产，含 `candidates[].character_id` + `candidates[].aliases[].name`，aliases 是身份合并的所有别名）
- 合法 character_id 集 = **`candidate_characters.candidates[].character_id` 全集**（非目标角色但合法的 candidate 也可作为势力 key_figures）

## 替换规则

读取 `foundation.json` 后，**仅修改 `major_factions[]` 数组的 `key_figures` 字段**——其他字段（`work_id` / `genre` / `tone` / `world_structure` / `power_system` / `core_rules` / `world_lines` / `major_factions[].name` / `major_factions[].description`）**一字不动**直接保留。

为每个 `major_factions[i].key_figures[]` 内每个 raw 名 `R`：

1. **匹配查找**：遍历 `candidate_characters.candidates[*]`，对每个 candidate `C`，检查 `R` 是否等于 `C.character_id` 或 `R` 是否出现在 `C.aliases[*].name` 列表里
   - 命中（exact match 或 alias name match）→ 把 `R` 替换为 `C.character_id`
   - 没命中（任何 candidate 的 character_id / aliases.name 都不等于 `R`）→ **保留 `R` 不动**（不报错、不删除）
2. **去重**：替换后若同一势力 key_figures 内出现重复 character_id（多个 raw 名映射到同一 character_id），保留一份去重
3. **不新增、不删除**：替换是 1-to-1 映射；不要因为 description 推断某 candidate 应该属于某势力而**额外**加 character_id；也不要因为某 raw 名"看起来不像主要角色"而删除——phase 1 lane 写入的就是 chunk-LLM 视野下的关键人物 raw 名，全部保留

## Fuzzy 匹配建议（LLM 优势区）

raw 名通常是化名 / 真名 / 称呼 / 称号；aliases 也含这些类型。优先 exact match；若没 exact match 但确信是同一人（如 raw 名 "李大爷" / alias name "李老" 都指向角色 X，对方有"长辈称谓"的称呼类型 alias），可视作匹配——但**必须谨慎**，宁可保留 raw 名不动也不要错配（错配会让 runtime 加载时绑错角色包）。

## 落盘

把修改后的整份 foundation 写回原路径 `{work_dir}/world/foundation/foundation.json`，覆盖原文件。schema 契约 → `schemas/world/foundation.schema.json`，bound 以 schema 为准。

## 失败处理

key_figures 内合法字符串混合（character_id + raw 名）— schema 不抓 character_id 合法性（无 enum 硬卡），任何字符串都合法。即使你完全没替换（所有 raw 名保留），schema 仍然 pass——但运行时绑定能力会受限（runtime 看到 raw 名只能字符串显示，不绑角色包）。**请尽力替换能匹配的项**。

## 规则

- 所有产出文件必须是格式良好的 JSON
- **只写本 lane 的输出文件** `world/foundation/foundation.json`——不要创建任何其他文件（fixed_relationships / identity / target_baseline 由并行 lane 产出；stage_catalog / digest 由后续 phase 程序化维护）
{retry_note}
