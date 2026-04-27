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

对每一章产出一条结构化摘要，**所有字段均 required**。schema 契约 → `schemas/analysis/chapter_summary_chunk.schema.json`，长度上下限以 schema 为准、本说明只描述用途。**bound 是硬上限不是配额**——能 30 字写清的 summary 不要为凑 50 字注水；能列 3 条的 key_events 不要为凑 5 条添碎事。

- `chapter`: 章节编号（4 位零填充，如 `"0001"`）
- `title`: 章节标题（从原文提取；原文无明确标题时为空字符串）
- `summary`: 1-3 句话概括本章核心剧情（事件描述，不是文学评论）。长度 50-100 字
- `key_events`: 本章推动剧情的关键事件列表，**最多 5 条**，每条 ≤ 50 字，跳过日常水文
- `characters_present`: 本章有实质互动的角色列表（不计背景群演）
- `location`: 本章主要场景 / 地点（≤ 20 字）
- `emotional_tone`: 本章主要情绪基调（≤ 20 字，例如"紧张" / "温馨" / "搞笑" / "悲伤"）
- `identity_notes`: 本章中的角色身份相关线索（化名建立、真名揭示、封号赋予等），≤ 50 字。无此类事件时为空字符串

### 步骤 3：写入输出文件

将结果写入：`{output_path}`

JSON 结构（不要添加 schema 之外的字段）：

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
      "identity_notes": ""
    }}
  ]
}}
```

## 规则

- 中文作品使用中文产出内容
- 摘要要简洁但信息量充分，重点在于 **剧情事件**，不是文学分析
- `key_events` 只记录推动剧情的事件，跳过日常水文
- `characters_present` 只记录有实质互动的角色，不记背景群演。**注意角色可能以化名、代称、昵称等出现**——如果你能判断某个名称实际上是已知角色的别名，在 `characters_present` 中使用其最常用的名称，并在 `key_events` 中注明化名关系（如"角色A以XX身份潜入"）
- 你只负责归纳，不要开始提取世界或角色信息
- 读取所有章节后再开始写摘要，确保对整个 chunk 的剧情脉络有完整认知
{retry_note}
