# 章节归纳（Chunk {chunk_index}/{total_chunks}）

你现在接手本地项目 Offpage，你没有任何额外背景知识。

## 目标

对作品 `{work_id}` 的第 {start_chapter}–{end_chapter} 章进行归纳，产出每章的结构化摘要。

## 作品信息

- work_id: `{work_id}`
- 书名: `{title}`
- 语言: `{language}`
- 本 chunk 章节范围: 第 {start_chapter}–{end_chapter} 章（共 {chunk_chapter_count} 章）
- 源目录: `{source_dir}`

## 执行步骤

### 步骤 1：读取所有章节

读取以下章节文件的全部内容：

{chapter_file_list}

### 步骤 2：逐章归纳

对每一章产出一条结构化摘要，包含：

- `chapter`: 章节编号（如 "0001"）
- `title`: 章节标题（从文件内容中提取，如果没有则留空）
- `summary`: 1-3 句话概括本章核心剧情（不是文学评论，是事件描述）
- `key_events`: 本章关键事件列表（每条一句话）
- `characters_present`: 本章出场的重要角色列表
- `location`: 本章主要场景/地点
- `emotional_tone`: 本章主要情绪基调（如"紧张""温馨""搞笑""悲伤"等）
- `identity_notes`: 如果本章中出现角色身份相关的线索（角色获得新名称、揭示真实身份、开始使用化名、被赋予称号等），在此记录。例如："主角得知'角色A'的真名为'角色B'"、"角色C化名'XX'潜入敌营"。如无此类事件则留空字符串
- `potential_boundary`: 如果本章结尾或下章开头存在明显的剧情转折（如换地图、时间跳跃、重大事件结束、新势力登场），标记为 true 并在 `boundary_hint` 中简述原因；否则为 false

### 步骤 3：写入输出文件

将结果写入：`{output_path}`

JSON 结构：

```json
{{
  "work_id": "{work_id}",
  "chunk_index": {chunk_index},
  "chapters": "{start_chapter}-{end_chapter}",
  "summaries": [
    {{
      "chapter": "0001",
      "title": "...",
      "summary": "...",
      "key_events": ["...", "..."],
      "characters_present": ["...", "..."],
      "location": "...",
      "emotional_tone": "...",
      "identity_notes": "",
      "potential_boundary": false,
      "boundary_hint": ""
    }}
  ]
}}
```

## 规则

- 中文作品使用中文产出内容
- 摘要要简洁但信息量充分，重点在于 **剧情事件**，不是文学分析
- `key_events` 只记录推动剧情的事件，跳过日常水文
- `characters_present` 只记录有实质互动的角色，不记背景群演。**注意角色可能以化名、代称、昵称等出现**——如果你能判断某个名称实际上是已知角色的别名，在 `characters_present` 中使用其最常用的名称，并在 `key_events` 中注明化名关系（如"角色A以XX身份潜入"）
- `potential_boundary` 的判断要基于剧情结构（地点转移、时间跳跃、重大事件完结、新篇章开始），不是章节数量
- 你只负责归纳，不要开始提取世界或角色信息
- 读取所有章节后再开始写摘要，确保对整个 chunk 的剧情脉络有完整认知
