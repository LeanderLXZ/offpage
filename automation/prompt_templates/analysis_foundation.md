# 自动化分析阶段 — Foundation Lane

你现在接手本地项目 Offpage，你没有任何额外背景知识。本次任务**仅产出一件文件**：`foundation.json`，即作品 `{work_id}` 的世界基础设定 baseline——决策 #54 把 foundation 前移到 phase 1 直接产，phase 2 baseline 仅负责单独 LLM call 补齐 `major_factions[].key_figures` 字段，**本 lane 不写该字段**。

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
- `chunk_factions[]`（≤20 条 × `{{name, description}}`；势力名 + 简介；**已剔除 `members_present`** 因 phase 1 foundation lane 不需要 raw 角色名映射——`key_figures` 由 phase 2 baseline 单独 LLM call 补齐）
- `chunk_regions[]`（≤20 条 × `{{name, description}}`；本 chunk 出现的地理区域）

chunk 输入 schema 契约 → `schemas/analysis/chapter_summary_chunk.schema.json`（注意：lane 输入只是子集；输出 schema 见下方）。

## 执行步骤

### 步骤 1：读取所有裁剪后的 chunk

读取 `{lane_inputs_dir}` 下所有 `chunk_*.json`，按 `chunk_index` 顺序构建全书的世界观信号脉络。重点：

- `chunk_arc_summary` 串起来 = 作品的"大世界线"骨架
- `chunk_regions` 跨 chunk 出现的地理区域聚合 → `foundation.world_structure.major_regions`
- `chunk_power_levels` 跨 chunk 同名等级合并 → `foundation.power_system.levels`
- `chunk_factions` 跨 chunk 同名势力合并 → `foundation.major_factions`（仅 `name` + `description` 两字段；`key_figures` 留给 phase 2 baseline 补齐）
- `chunk_world_rules` 跨 chunk 同名规则合并 → `foundation.core_rules`
- `chunk_arc_summary` 的弧线推进 + `chapters` 范围切分 → `foundation.world_lines[].{{name, chapter_range, core_conflict, setting_features}}`（`chapter_range` 来源是 chunk 元信息的 `chapters` 字段，非每章 summary）

### 步骤 2：综合产出 foundation

字段映射：

- `chunk_world_rules → core_rules[]`（**字符串数组**，maxItems 30 / 每条 ≤150 字。**重新整理**——把多 chunk 的同一规则合并为完整描述，含规则名 + 机制 + 影响一句话写出；不要照搬 chunk 行的 `rule` / `description` / `observed_impact` 三字段拼接）
- `chunk_power_levels → power_system.levels[]`（**对象数组**，每项 `{name (≤15 字), description (≤30 字)}`，对齐 chunk_power_levels.items 形态。综合多 chunk 同一等级名，合并 description）
- `chunk_factions → major_factions[]`（每项 `{name (≤30 字), description (≤100 字)}`，**不写 `key_figures` 字段**——该字段由 phase 2 baseline 单独 LLM call 在 phase 1.5 身份合并完成后填充）
- `chunk_regions → world_structure.major_regions[]`（**对象数组**，每项 `{name (≤15 字), description (≤30 字)}`，对齐 chunk_regions.items 形态。综合多 chunk 同一地名，合并 description）
- `chunk_arc_summary → world_lines[].core_conflict`（多 chunk 弧线串成大世界线核心冲突）
- `world_structure.summary` / `power_system.summary` / `world_lines[].setting_features` 由你综合 `chunk_regions` / `chunk_power_levels` / `chunk_factions` / `chunk_world_rules` 的信号写出（无 chunk 直供字段，需要综合判断）
- `genre` / `tone` 由所有 chunk_arc_summary 的整体语调判断

### 步骤 3：落盘 + 自检

输出文件：`{work_dir}/world/foundation/foundation.json`（**注意路径** — 决策 #54 把 foundation 前移到 phase 1，落盘路径从原 `analysis/world_overview.json` 改为 `world/foundation/foundation.json`，与 phase 2 baseline 后续补齐的 `fixed_relationships.json` 同目录）

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

落盘后自检 schema（结构 / bound / enum / pattern）能否通过；若你写的某字段超出长度 / 数量上限，先在生成阶段裁剪到合规再写盘——schema gate 会在落盘后再次校验，违规会回到本 lane 重试。

## 规则

- 中文作品的 work_id、字段值使用中文
- 产出文件必须是格式良好的 JSON
- 你**只**负责 foundation，不要尝试产出 stage_plan / candidate_characters（它们由其他 lane 并行处理）
- **不要**写 `major_factions[].key_figures` 字段——由 phase 2 baseline 补齐
- 不要修改 `{lane_inputs_dir}` 下的输入文件
- 不要读取 `sources/` 下的原始章节正文——本 lane 输入仅基于 chunks 摘要
{retry_note}
