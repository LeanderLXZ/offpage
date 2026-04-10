# 架构重构：5 项变更

日期：2026-04-10
分支：master

## 变更概述

本次变更包含 5 项架构调整，统一处理世界级固定关系、世界事件时间线、
stage_catalog 瘦身、快照内联引用清理、以及运行时加载策略对齐。

## 变更清单

### 1. 新增 fixed_relationships.json

- 新增 `schemas/fixed_relationships.schema.json`
- 世界级固定关系（血缘、宗族、师徒、势力从属）独立记录在
  `world/foundation/fixed_relationships.json`
- Phase 2.5 产出骨架，后续批次可修正
- 运行时 Tier 0 加载
- `baseline_production.md` 新增产出模板
- orchestrator / validator 新增存在性检查（warn 级别）
- prompt_builder 新增 schema 引用

### 2. stage_catalog 瘦身与降级

- 移除 `key_events`、`current_world_summary` 字段（世界 catalog）
- `short_summary` 重命名为 `summary`
- stage_catalog 降级为 bootstrap 阶段选择器，运行时不加载
- schema 文件同步更新（world_stage_catalog + stage_catalog）

### 3. 新增 world_event_digest.jsonl

- 新增 `schemas/world_event_digest_entry.schema.json`
- `post_processing.py` 新增 `generate_world_event_digest()` 函数
  - 从世界 stage_snapshot `key_events` 程序化生成
  - event_id 格式：`WE-{stage_short}-{seq}`
  - upsert 语义（按 stage_id 去重）
- `run_batch_post_processing()` 流程中新增调用
- 运行时 stage 1..N 过滤加载（N = 用户选定阶段）

### 4. 世界快照移除内联章节引用

- `world_stage_snapshot.schema.json` 更新：body 字段不需要逐条标注 `[NNNN]`
- `world_extraction.md` 提取规则同步
- `evidence_refs` 章节号列表仍保留

### 5. 运行时加载策略对齐

- `memory_digest.jsonl`：从"全量加载"改为"stage 1..N 过滤加载"
- `world_event_digest.jsonl`：新增 Tier 0 加载项
- `fixed_relationships.json`：新增 Tier 0 加载项
- `stage_catalog.json`：从 Tier 0 移除（仅 bootstrap 使用）
- 防止知识泄漏：digest 仅加载到用户选定阶段，不暴露未来阶段

## 涉及文件

**新增 schema**：
- `schemas/fixed_relationships.schema.json`
- `schemas/world_event_digest_entry.schema.json`

**修改 schema**：
- `schemas/world_stage_catalog.schema.json`
- `schemas/stage_catalog.schema.json`
- `schemas/world_stage_snapshot.schema.json`

**代码**：
- `automation/persona_extraction/post_processing.py`
- `automation/persona_extraction/prompt_builder.py`
- `automation/persona_extraction/orchestrator.py`
- `automation/persona_extraction/validator.py`

**提取提示词**：
- `automation/prompt_templates/baseline_production.md`
- `automation/prompt_templates/world_extraction.md`
- `automation/prompt_templates/coordinated_extraction.md`
- `automation/prompt_templates/character_extraction.md`

**需求与架构文档**：
- `docs/requirements.md`
- `docs/architecture/system_overview.md`
- `docs/architecture/data_model.md`
- `docs/architecture/extraction_workflow.md`
- `docs/architecture/schema_reference.md`

**运行时文档**：
- `simulation/flows/startup_load.md`
- `simulation/retrieval/load_strategy.md`
- `simulation/retrieval/index_and_rag.md`
- `simulation/README.md`

**AI 上下文**：
- `ai_context/architecture.md`
- `ai_context/decisions.md`

**README**：
- `works/README.md`
- `automation/README.md`

## 后续事项

- 在 extraction 分支上重新运行 Phase 2.5 以生成 fixed_relationships.json
- Phase 3 batch 002-005 待继续
- Phase 4 剩余 4 章（0380, 0455, 0467, 0502）可重试
