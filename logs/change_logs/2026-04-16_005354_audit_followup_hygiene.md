# Audit follow-up：审计剩余 hygiene / 文档对齐

## 背景

上一批提交 (`35515e5` + `5f5232e`) 完成 lane 独立重试 + 世界 reviewer
越界检测 bug 修复后，并行审计还列出 3 个 minor / hygiene 项，当时判定
为"可选"未处理。用户要求补齐。

## 改动范围

### `docs/architecture/schema_reference.md`

- 新增末尾章节"进度跟踪状态（Python dataclass，非 JSON Schema）"，
  登记 `StageEntry` 全字段（含新加的 `lane_retries` / `lane_max_retries`）
  并注明向后兼容默认值
- 该 schema_reference 文档原本只收录 `schemas/` 目录下 JSON Schema；
  此次以明确分段标注保留其原有语义，同时满足"跨文档引用查询"的需求

### `docs/architecture/extraction_workflow.md`

- 阶段流程图的 `[lane FAIL]` 分支补一行指向 `requirements.md §11.4b`
  详细描述的引用

### `automation/persona_extraction/orchestrator.py`

- Step 5 commit gate FAIL 路径（`:1450`）：显式 `stage.lane_retries = {}`
- Step 6 git commit 空 SHA FAIL 路径（`:1474`）：显式
  `stage.lane_retries = {}`
- 两处逻辑上冗余（Step 4 成功出口已在 `:1429` 清空），但 defensive
  clarity 更好——任何走到 FAILED 的路径都显式归零，避免未来重构移动
  Step 4 清空点时留下隐性依赖

## 验证

- `python -c "from persona_extraction import orchestrator,
  prompt_builder, progress, review_lanes"` 全部导入成功

## 未采纳的"双保存"审计意见

原审计报告提出 `orchestrator.py:1426-1430` 存在"if 内 save + if 外
save"的双保存。复核后确认为误读——四行（print / `lane_retries = {}`
/ `phase3.save()`）均在同一 `if stage.lane_retries:` 块内，缩进一致，
无冗余保存。无改动。
