# 自动化分析阶段 — Foundation Lane

你现在接手本地项目 Offpage，你没有任何额外背景知识。本次任务**仅产出一件文件**：`foundation.json`，即作品 `{work_id}` 的世界基础设定 baseline——决策 #54 把 foundation 前移到 phase 1 直接产；`major_factions[].key_figures` 字段**本 lane 写 raw 名**（chunk_factions[].members_present[] 跨 chunk 合并去重），phase 2 baseline LLM 后续把能匹配身份的 raw 名替换为 character_id。

## 作品信息

- work_id: `{work_id}`
- 书名: `{title}`
- 语言: `{language}`
- 总章节数: `{chapter_count}`
- 作品目录: `{work_dir}`

## 输入：裁剪后的章节摘要（lane 专用）

裁剪后的 chunk JSON 文件已经准备好，存放在：

`{lane_inputs_dir}`

每个文件是一个 chunk 的归纳结果（JSON），**已经按 foundation lane 的需求做了字段裁剪**——**只保留 chunk-level 二级字段**（`summaries[]` 整段已删除，全书设定不依赖逐章锚点）：

- `work_id` / `chunk_index` / `chapters`（chunk 元信息——`chapters` 是 `C####-C####` 范围串，可用于 `world_lines.chapter_range` 推理）
- `chunk_arc_summary`（≤200 字本 chunk 整体剧情弧）
- `chunk_world_rules[]`（≤5 条 × `{{rule, description, observed_impact}}`；本 chunk 揭示的世界规则；observed_impact 可能是具体影响或 fallback "未在本 chunk 直接观察"）
- `chunk_power_levels[]`（≤20 条 × `{{name, description}}`；本 chunk 出现的力量体系等级）
- `chunk_factions[]`（≤20 条 × `{{name, description, members_present}}`；势力名 + 简介 + **关键人物 raw 名列表**——`members_present` 是 chunk-LLM 视野下的角色 raw 名，化名 / 真名 / 称呼任一）
- `chunk_regions[]`（≤20 条 × `{{name, description}}`；本 chunk 出现的地理区域）

chunk 输入 schema 契约 → `schemas/analysis/chapter_summary_chunk.schema.json`（注意：lane 输入只是子集；输出 schema 见下方）。

## 执行步骤

### 步骤 1：读取所有裁剪后的 chunk

读取 `{lane_inputs_dir}` 下所有 `chunk_*.json`，按 `chunk_index` 顺序构建全书的世界观信号脉络。重点：

- `chunk_arc_summary` 串起来 = 作品的"大世界线"骨架
- `chunk_regions` 跨 chunk 出现的地理区域聚合 → `foundation.world_structure.major_regions`
- `chunk_power_levels` 跨 chunk 同名等级合并 → `foundation.power_system.levels`
- `chunk_factions` 跨 chunk 同名势力合并 → `foundation.major_factions`：
  - `name` + `description` 跨 chunk 综合
  - `key_figures` 用 `chunk_factions[].members_present[]` 跨 chunk 合并去重（raw 名直接写，不做身份合并；身份合并由 phase 2 baseline LLM 负责）
- `chunk_world_rules` 跨 chunk 同名规则合并 → `foundation.core_rules`
- `chunk_arc_summary` 的弧线推进 + `chapters` 范围切分 → `foundation.world_lines[].{{name, chapter_range, core_conflict, setting_features}}`（`chapter_range` 来源是 chunk 元信息的 `chapters` 字段，非每章 summary）

### 步骤 2：综合产出 foundation

字段映射：

- `chunk_world_rules → core_rules[]`（**字符串数组**，maxItems 30 / 每条 ≤150 字。**重新整理**——把多 chunk 的同一规则合并为完整描述，含规则名 + 机制 + 影响一句话写出；不要照搬 chunk 行的 `rule` / `description` / `observed_impact` 三字段拼接）
- `chunk_power_levels → power_system.levels[]`（**对象数组**，每项 `{name (≤15 字), description (≤30 字)}`，对齐 chunk_power_levels.items 形态。综合多 chunk 同一等级名，合并 description）
- `chunk_factions → major_factions[]`（每项 `{name (≤30 字), description (≤100 字), key_figures[]}`）：
  - `name` / `description` 综合多 chunk 同一势力合并
  - `key_figures[]`（≤10 项，每项 ≤30 字）：把所有 `chunk_factions[同势力].members_present[]` 跨 chunk 合并去重后**直接作为字符串**写入。不做身份合并（不要把"X 真名是 Y"等推断合并），不要换成 character_id（candidate_characters 身份合并由另一 lane 并行处理，本 lane 看不到结果）——raw 名（化名 / 真名 / 称呼）有什么写什么。Phase 2 baseline LLM 后续会把能匹配 candidate_characters.aliases 的 raw 名替换为 character_id，匹配不上的保留 raw 名（你不需要操心）
- `chunk_regions → world_structure.major_regions[]`（**对象数组**，每项 `{name (≤15 字), description (≤30 字)}`，对齐 chunk_regions.items 形态。综合多 chunk 同一地名，合并 description）
- `chunk_arc_summary → world_lines[].core_conflict`（多 chunk 弧线串成大世界线核心冲突）
- `world_structure.summary` / `power_system.summary` / `world_lines[].setting_features` 由你综合 `chunk_regions` / `chunk_power_levels` / `chunk_factions` / `chunk_world_rules` 的信号写出（无 chunk 直供字段，需要综合判断）
- `genre` / `tone` 由所有 chunk_arc_summary 的整体语调判断

### 步骤 3：落盘 + 自检

输出文件：`{work_dir}/world/foundation/foundation.json`（**注意路径** — 决策 #54 把 foundation 前移到 phase 1，落盘路径在 `world/foundation/foundation.json`，与 phase 2 baseline 后续补齐的 `fixed_relationships.json` 同目录）

schema 契约 → `schemas/world/foundation.schema.json`，长度上下限以 schema 为准。

JSON 结构：

```json
{{
  "work_id": "{work_id}",
  "genre": "...",
  "tone": "...",
  "world_structure": {{
    "summary": "...",
    "major_regions": [
      {{ "name": "...", "description": "..." }}
    ]
  }},
  "power_system": {{
    "summary": "...",
    "levels": [
      {{ "name": "...", "description": "..." }}
    ]
  }},
  "major_factions": [
    {{
      "name": "...",
      "description": "...",
      "key_figures": ["raw_name_1", "raw_name_2"]
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

落盘后自检 schema（结构 / bound / enum / pattern）能否通过；若你写的某字段超出长度 / 数量上限，先在生成阶段裁剪到合规再写盘——schema gate 会在落盘后再次校验，违规会回到本 lane 重试。**key_figures 触顶 10 项时**：按 chunk 出现频次裁剪——同一势力跨多 chunk 多次出现的 raw 名优先保留；单 chunk 一次出现的次序靠后弃。

## 规则

- 中文作品的 work_id、字段值使用中文
- 产出文件必须是格式良好的 JSON
- 你**只**负责 foundation，不要尝试产出 stage_plan / candidate_characters（它们由其他 lane 并行处理）
- **必须写 `major_factions[].key_figures` 字段**：用 chunk_factions[].members_present[] 跨 chunk 合并去重产出 raw 名列表（化名 / 真名 / 称呼有什么写什么，不做身份合并）。phase 2 baseline LLM 后续替换能匹配身份的 raw 名为 character_id
- 不要修改 `{lane_inputs_dir}` 下的输入文件
- 不要读取 `sources/` 下的原始章节正文——本 lane 输入仅基于 chunks 摘要
{retry_note}
