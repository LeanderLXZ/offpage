# Phase 1 出口验证：Batch Plan 章节数检查与自动拆分

日期：2026-04-09

## 问题

Phase 1 全书分析产出的 `source_batch_plan.json` 中，LLM 频繁违反
"最大 15 章"的硬约束。实测首次运行产出 24 batch，其中 20 个超限
（最多 51 章），后续 agent 自行修正为 46 batch 但不可靠。

## 变更

### 1. Prompt 加强（`automation/prompt_templates/analysis.md`）

- 将"最小 5 章，最大 15 章"升级为带警告标记的硬性约束
- 明确禁止以"保持剧情完整性"为由创建超限 batch
- 新增自检要求：完成 batch plan 后逐一检查 chapter_count

### 2. 程序化兜底（`automation/persona_extraction/orchestrator.py`）

新增 `_validate_and_split_batch_plan()` 函数，在 Phase 1 完成后自动执行：

- 扫描所有 batch，标记超限（>15 章）的 batch
- 按 target 10 章均分拆分，确保子 batch 不小于 5 章
- 子 batch stage_id 追加后缀（2 个：上/下，3 个：上/中/下，4+：a/b/c/d...）
- batch_id 重新编号保持连续
- 重写 `source_batch_plan.json`
- 0 token 开销

### 3. 文档更新

- `docs/requirements.md`：§11.4.2 Phase 1 出口验证增加章节数检查；§11.9 新增程序化兜底规则
- `docs/architecture/extraction_workflow.md`：Phase 1 新增出口验证说明
- `ai_context/architecture.md`、`ai_context/requirements.md`：同步更新
