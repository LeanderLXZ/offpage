# 修复 schema source_type 枚举 + 批次重试逻辑

## 变更

### 1. stage_snapshot.schema.json — source_notes.source_type 补充 canon

- `schemas/stage_snapshot.schema.json`
- 原来 source_notes 的 source_type 只允许 `["inference", "ambiguous"]`
- LLM 提取时产出 `"canon"` 导致 programmatic validation 失败
- 修复：对齐 memory_timeline_entry 等其他 schema，改为 `["canon", "inference", "ambiguous"]`

### 2. 批次重试逻辑修复

- `automation/persona_extraction/progress.py` — `next_pending_batch()`
- `automation/persona_extraction/orchestrator.py` — `_process_batch()`

**Bug 1**: `next_pending_batch()` 先遍历所有 pending 再遍历 failed，导致 batch_001 失败后跳到 batch_002。批次有顺序依赖（batch N+1 依赖 batch N 的产出），跳过会导致后续 batch 缺少前一阶段参照。

**Bug 2**: ERROR 状态的 batch 不被 `next_pending_batch()` 匹配，也没有在 `_process_batch` 中处理恢复，导致 ERROR batch 被永久跳过。

**修复**：
- `next_pending_batch()` 改为按 batch 顺序扫描，遇到第一个未 committed 的 batch 就返回；stuck 则返回 None 阻塞管线
- `_process_batch()` 增加 ERROR → rollback + PENDING 的恢复路径

## 提交

- `8287501` 修复 source_notes.source_type 枚举：补充 canon 选项
- `13d9831` 修复批次重试逻辑：顺序阻塞 + ERROR 状态重试
