# Smart Resume + 世界事件时间线重构

**日期**: 2026-04-10
**范围**: orchestrator 智能恢复、世界 stage_snapshot/stage_catalog 字段重构

## 变更概述

### 1. 智能 Resume（跳过已有产物）

**问题**: batch 因 error 被重置为 PENDING 后，即使提取产物已存在于磁盘，
resume 仍重新调用 LLM 提取，浪费 tokens。

**方案**: 在 git preflight 后、LLM 提取前，检测 world + 全部角色的
`stage_snapshots/{stage_id}.json` 是否存在。若存在则跳到 EXTRACTED 状态，
直接进入 post_processing。

**改动文件**:
- `automation/persona_extraction/orchestrator.py` — 新增
  `_extraction_output_exists()` 方法 + smart skip 分支

### 2. 世界 stage_snapshot 字段重构

**问题**: `historical_events` 是累积历史，随 batch 推进无限膨胀；
`evidence_refs` 含冗余详细描述。

**方案**:
- `historical_events` → `stage_events`（仅本阶段事件，详细）
  + `key_events`（重要事件 1 句话摘要，供 catalog 累积）
- `evidence_refs` 简化为章节号列表（如 `["0001", "0002"]`）
- event 内嵌引用改为 `[NNNN]`，去掉 `canon;` 前缀

**改动文件**:
- `schemas/world_stage_snapshot.schema.json`
- `schemas/world_stage_catalog.schema.json` — 新增 `key_events` 字段
- `automation/persona_extraction/post_processing.py` — 复制 `key_events` 到 catalog
- `automation/persona_extraction/validator.py` — 新增 `stage_events`/`key_events` 检查
- `automation/prompt_templates/world_extraction.md` — 更新字段名和规则
- `automation/prompt_templates/semantic_review_world.md` — 更新审校检查清单

### 3. 文档对齐

- `docs/requirements.md` — §2.3.4、§11.2 流程图、§11.3a post_processing
- `ai_context/architecture.md`、`ai_context/requirements.md`、
  `ai_context/decisions.md`（40f/40g/40h）、`ai_context/current_status.md`
- `docs/architecture/schema_reference.md`、`extraction_workflow.md`
- `automation/README.md`

## 向后兼容

- 现有 batch_001 的 world snapshot 使用旧字段名（`historical_events`），
  需重新提取。batch_001 当前状态为 pending，重跑时自动使用新 schema。
- 世界 stage_catalog 旧字段 `history_summary` 已从 schema 移除，
  新字段 `key_events` 由 post_processing 在提取后自动填充。

## 测试

- 模块 import 检查通过
- schema JSON 解析验证通过
- `upsert_stage_catalog` 单元测试：key_events 正确写入 catalog entry
- 跨文件一致性检查：无残留旧字段引用
