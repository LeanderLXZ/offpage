# 自动化分析阶段

你现在接手本地项目 `persona-engine`，你没有任何额外背景知识。

## 目标

对作品 `{work_id}` 执行三项分析任务并产出结构化结果：

1. **全书总体分析** — 评估体量，判断题材和整体结构
2. **源文件分批规划** — 按自然剧情边界制定 batch plan
3. **候选角色识别** — 识别可建包的候选角色

## 作品信息

- work_id: `{work_id}`
- 书名: `{title}`
- 语言: `{language}`
- 总章节数: `{chapter_count}`
- 源目录: `{source_dir}`
- 作品目录: `{work_dir}`

## 执行步骤

### 步骤 1：最小结构读取

读取以下文件建立项目认知：

1. `README.md`
2. `works/README.md`
3. `schemas/README.md`
4. `docs/architecture/data_model.md`（仅在不确定 world/ 和 characters/ 分工时）

### 步骤 2：全书总体分析

读取元数据和章节索引：
- `{source_dir}/manifest.json`
- `{source_dir}/metadata/book_metadata.json`
- `{source_dir}/metadata/chapter_index.json`

产出简要分析摘要，包括：
- 题材类型
- 大致体量评估
- 推荐的分批策略

### 步骤 3：源文件分批规划（本阶段最核心的产出）

**为什么这一步至关重要：** 你划定的每个 batch 边界会直接成为整个系统的 stage 边界。世界快照、角色快照、记忆时间线、运行时阶段选择——全部建立在这个切分之上。切分不合理会导致角色人格转变生硬、世界事件时间线断裂、用户选择某阶段时体验不连贯。请投入足够精力确认剧情节点。

制定详细的 batch plan。要求：

- 默认每批 10 章，但必须优先贴近自然剧情边界——剧情边界的准确性比章节数量均匀更重要
- 最小批次 5 章，最大批次 20 章
- 每个 batch 条目包含：batch_id, stage_id, chapters, chapter_count, boundary_reason, key_events_expected
- 为 stage_id 取一个有意义的中文名称（如"阶段1_南林初遇"），不要只用编号
- `boundary_reason` 必须说明为什么在此处切分（例如"主角离开某地""重大事件结束""新势力登场"），不能只写"满 10 章"

为了确定剧情边界，你可以：
- 先读取章节索引中的章节标题
- 选择性抽读关键章节的开头和结尾来确认剧情节点
- 不需要通读全部章节

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

### 步骤 4：候选角色识别

基于前 2-3 批章节的抽读，识别可建包的候选角色。

为每个候选角色提供：
- character_id（中文名）
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
      "character_id": "角色名",
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
- 不要通读全部章节，只做必要的抽读
- 产出文件都应是格式良好的 JSON
- 你只负责分析，不要开始提取世界或角色信息
