# 2026-04-03 角色别名跟踪系统 + 章节归纳阶段

## 变更概要

本次包含两组独立但相关的变更：

### 一、角色标识与名称跟踪

**动机**：角色在小说中可能以多个名称出现（化名、代称、昵称、封号、武器名
等），且名称可能随剧情变化。需要结构化跟踪以确保数据归属正确。

**需求文档更新**（`docs/requirements.md`）：
- 新增 §3 "角色标识与名称跟踪"章节
- 覆盖五类场景：伪装/失忆化名、后期获名、名称变更、双名并行、关系称呼
- 定义通用要求：稳定 character_id + 结构化别名列表

**Schema 变更**：

1. `schemas/identity.schema.json`
   - `aliases` 从简单字符串数组改为结构化对象数组
   - 每条记录含：name, type (本名/化名/代称/称呼/封号/道号/武器名/其他),
     effective_stages, source, used_by

2. `schemas/stage_snapshot.schema.json`
   - 新增 `active_aliases` 字段
   - 含：primary_name, active_names, hidden_identities, known_as（角色称呼映射）

3. `schemas/character_manifest.schema.json`
   - `aliases` 保持扁平字符串数组，加说明指向 identity.json 获取完整信息

**Prompt 变更**：
- `automation/prompt_templates/coordinated_extraction.md` — 新增规则 9（别名跟踪）
- `automation/prompt_templates/summarization.md` — characters_present 规则更新

**文档变更**：
- `docs/architecture/schema_reference.md` — identity 和 stage_snapshot 条目更新
- `ai_context/requirements.md` — 新增 §3.1 压缩摘要

### 二、章节归纳阶段（Phase 0）

**动机**：原 Phase 1 让单次 LLM 调用分析 537 章全书，导致超时。改为分 chunk
归纳 → 全局分析的两步架构。

**概念区分**：
- **Chunk**：Phase 0 的处理分组（~25 章），纯处理粒度，无剧情含义
- **Batch / Stage**：Phase 1 分析出的剧情阶段边界，batch N = stage N

**代码变更**：
- `automation/prompt_templates/summarization.md` — 新建，chunk 归纳 prompt
- `automation/prompt_templates/analysis.md` — 重写，从摘要分析而非读原文
- `automation/persona_extraction/prompt_builder.py` — 新增 `build_summarization_prompt()`
- `automation/persona_extraction/orchestrator.py` — 新增 `run_summarization()` (Phase 0),
  构造函数加 `chunk_size` 参数，`run_full()` 先跑 Phase 0 再跑 Phase 1
- `automation/persona_extraction/cli.py` — 新增 `--chunk-size` 参数（默认 25）

**Bug 修复**：
- `automation/persona_extraction/progress.py` — `pending → error` 加入合法状态转换
- `automation/persona_extraction/orchestrator.py` — 分析阶段超时从 600s 改为 1800s

## 涉及文件

- `docs/requirements.md`
- `ai_context/requirements.md`
- `schemas/identity.schema.json`
- `schemas/stage_snapshot.schema.json`
- `schemas/character_manifest.schema.json`
- `docs/architecture/schema_reference.md`
- `automation/prompt_templates/summarization.md` (new)
- `automation/prompt_templates/analysis.md`
- `automation/prompt_templates/coordinated_extraction.md`
- `automation/persona_extraction/prompt_builder.py`
- `automation/persona_extraction/orchestrator.py`
- `automation/persona_extraction/cli.py`
- `automation/persona_extraction/progress.py`
