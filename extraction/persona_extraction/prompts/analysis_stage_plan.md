# 自动化分析阶段 — Stage Plan Lane

你现在接手本地项目 Offpage，你没有任何额外背景知识。本次任务**仅产出一件文件**：`stage_plan.json`，即作品 `{work_id}` 的源文件阶段规划。

**为什么这一步至关重要：** 你划定的每个 stage 边界会直接成为整个系统的 stage 边界。世界快照、角色快照、记忆时间线、运行时阶段选择——全部建立在这个切分之上。切分不合理会导致角色人格转变生硬、世界事件时间线断裂、用户选择某阶段时体验不连贯。请投入足够精力确认剧情节点。

## 作品信息

- work_id: `{work_id}`
- 书名: `{title}`
- 语言: `{language}`
- 总章节数: `{chapter_count}`
- 作品目录: `{work_dir}`

## 输入：裁剪后的章节摘要（lane 专用）

裁剪后的 chunk JSON 文件已经准备好，存放在：

`{lane_inputs_dir}`

每个文件是一个 chunk 的归纳结果（JSON），**已经按 stage_plan lane 的需求做了字段裁剪**——只保留以下字段：

**per-summary 层（每章一条，章序锚点 + 事件描述）**：
- `chapter` / `summary`（150-200 字本章核心剧情概述 + 关键剧情节点）

**chunk-level 二级字段（chunk 弧光 + 地理切换信号）**：
- `chunk_arc_summary`（≤200 字本 chunk 整体剧情弧——chunk 跨度内的剧情走向骨架）
- `chunk_regions[]`（≤20 条 × `{{name, description}}`；本 chunk 出现的地理区域，作为"场景转换"边界信号）

裁剪原则：拐点合并依据 = `chunk_arc_summary` chunk 弧光 + per-summary `summary` 事件描述（150-200 字承载事件 + 节奏 / 转折）+ `chunk_regions` 地理切换。`characters_present` / `emotional_tone` / `identity_notes` 是身份 / 角色 / 情绪粒度，与"按章序合并相邻拐点"任务正交，已删除。

schema 契约 → `schemas/analysis/chapter_summary_chunk.schema.json`（注意：lane 输入只是子集；输出 schema 见下方）。

## 执行步骤

**核心原则：拐点先行，章数后定。** 不要先决定"每段多少章"再去找剧情边界，必须从全书剧情拐点反推 stage 边界——以下三子步**严格按顺序**执行，**不要跳步、不要倒推**：

### 步骤 1：全局剧情拐点扫描（必须先于步骤 2 完成）

通览所有 chunk 的 `chunk_arc_summary` + per-summary `summary` + `chunk_regions`，从中读出全书所有**剧情拐点候选**（plot inflection points）——拐点信息都浓缩在 `summary` 的事件描述里（如"主角离开起始村落"、"盟友真实身份曝光"、"势力阵营变动"），由 `chunk_arc_summary` 提供 chunk 级宏观骨架辅助判断、`chunk_regions` 提供地理转场信号。每个拐点写一行，包含：

- 章号（如 `C0037`）
- 拐点类型（**枚举**：场景转换 / 弧线切换 / 主要角色登场退场 / 关键身份揭示 / 时间跳跃 / 阵营变动 / 情感转折 / 重大伤亡）
- 一句话事件描述

这份候选拐点列表是你的工作记录，**作为推理过程产出**（写在你的思考链 / agent 日志里，不需要进入最终 `stage_plan.json` 文件）；**完成本步候选列表后才允许进入步骤 2**。

### 步骤 2：候选拐点分组成 stage

沿章节顺序遍历步骤 1 列表，把相邻拐点合并成 stage：

- **章数硬范围 [8, 15] 闭区间**——schema `chapter_count.minimum=8` / `maximum=15` 双向硬挡（决策 #27i schema-gate-as-retry-trigger，违规作为 prior_error 注入下次 retry prompt）+ orchestrator `_check_stage_plan_limits` 代码层 belt-and-suspenders 二次兜底；任何 ≤7 或 ≥16 都是违规
- 拐点优先级（高 → 低）：场景转换 > 弧线切换 > 阵营变动 > 重大伤亡 > 关键身份揭示 > 主要角色登场退场 > 时间跳跃 > 情感转折
- 同优先级取舍：选能让前后两段都更接近"拐点驱动而非数量驱动"的落点；不要为了让章数靠近某个数字而硬挪边界
- 每个 stage 条目包含：`stage_id` / `stage_title` / `chapters` / `chapter_count` / `boundary_reason`
- `stage_id` 使用紧凑英文代号 `S###`（三位数字零填充，如 `S001`、`S049`），**不使用中文或其他格式**。这是整套 ID 家族（`M-S###-##` / `E-S###-##` / `SC-S###-##` / `SN-S###-##`）的共同 stage 段
- `stage_title` 是人类可读的中文短标题（如"<location_a>初遇"、"<location_b>下山"），作为 bootstrap 阶段选择时展示给用户的阶段名
- `boundary_reason` 必须直接对应步骤 1 列表里的某个具体拐点（命名拐点类型 + 关键事件），不能只写"满 N 章"或泛泛剧情概括

### 步骤 3：反锚定自检（完成步骤 2 后必跑，不允许跳过）

依次检查产出的 stage_plan：

1. **章数分布反锚定检查**：把所有 stage 的 `chapter_count` 列出来；若有 **≥3 个连续 stage 章数完全相等**（如连续 5 个 stage 都是 10 章），说明大概率落入了"按章数等分、再给每段挑剧情节点写理由"的偷懒模式——**回到步骤 1 重审拐点列表是否覆盖完整、回到步骤 2 重新切分**，直到该模式不再出现
2. **boundary_reason 实质检查**：每个 stage 的 `boundary_reason` 必须能指回步骤 1 列表里的某个具体拐点（章号 + 类型）；如果某个 boundary_reason 只是"叙事过渡"、"剧情推进"、"主角成长"这类泛泛描述，说明该 stage 边界不是从拐点反推出来的——回到步骤 2 重切
3. **章数硬范围检查**：任意 stage 的 `chapter_count` ≤7 或 ≥16 必须调整切分点直到全部 stage 落在 [8, 15] 闭区间

### 步骤 4：落盘

输出文件：`{work_dir}/analysis/stage_plan.json`
schema 契约 → `schemas/analysis/stage_plan.schema.json`（`chapter_count` 8-15 hard，schema `minimum=8` + `maximum=15` 双向硬挡 + orchestrator `_check_stage_plan_limits` 代码层兜底；`stage_id` `^S\d{{3}}$`、字段集合以 schema 为准）。

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

## 规则

- **`maxLength` / `maxItems` 是上限不是配额**：schema 给的 `stage_title` /
  `boundary_reason` 长度上限只是硬门控，不是要写到的目标。短标题能几个字说清
  就几个字，切分理由有多少依据就写多少——**不要为了撑满 maxLength 而堆砌
  修饰或复述剧情**。
- 中文作品的 work_id 使用中文；`stage_id` 使用紧凑英文代号 `S###`（如 `S001`），`stage_title` 使用中文短标题
- 产出文件必须是格式良好的 JSON
- 你**只**负责 stage_plan，不要尝试产出 foundation / candidate_characters（它们由其他 lane 并行处理）
- 不要修改 `{lane_inputs_dir}` 下的输入文件
- 不要读取 `sources/` 下的原始章节正文——本 lane 输入仅基于 chunks 摘要
{retry_note}
