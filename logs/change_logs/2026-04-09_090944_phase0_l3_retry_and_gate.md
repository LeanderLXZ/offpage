# Phase 0: L3 全量重跑 + 完成门控

**时间**: 2026-04-09 09:09 ET

## 问题背景

Phase 0 并行测试中 chunk_014（第 326-350 章）失败：
- LLM 产出的 JSON 格式损坏，L1 程序化修复失败
- L2 LLM 修复超时（硬编码 120s，chunk JSON 体量约 14000 chars）
- 无 L3 重跑机制，chunk 直接标记 FAIL 并删除
- Phase 0→Phase 1 无门控：`run_summarization()` 只打 WARN，Phase 1
  在缺失 chunk 的情况下继续运行

## 变更内容

### 1. L2 timeout 参数化（json_repair.py）

- `try_repair_json_file()` 新增 `repair_timeout` 关键字参数，默认 600s
- 原硬编码 120s 移除，所有调用方通过默认值获得 600s

### 2. L3 全量重跑（orchestrator.py）

- `_summarize_chunk()` 新增 `_is_l3_retry` 参数
- L1+L2 均失败后，删除损坏文件，递归调用自身重新归纳（最多 1 次）
- L3 仍失败则返回 FAIL（不再重试）

### 3. Phase 0 完成门控（orchestrator.py）

- `run_summarization()` 在并行处理完成后检查所有 chunk 文件
- 有缺失 chunk → 打印缺失列表 → `sys.exit(1)` 阻断 Phase 1
- 下次运行时断点恢复自动跳过已完成 chunk，只补跑缺失的

## 修改文件

### 核心代码
- `automation/persona_extraction/json_repair.py` — `repair_timeout` 参数
- `automation/persona_extraction/orchestrator.py` — L3 重跑 + 门控

### 文档
- `docs/requirements.md` — Phase 0 流程图更新 + 三级修复表更新
- `docs/architecture/extraction_workflow.md` — Phase 0 描述补充
- `ai_context/requirements.md` — §9 和 §11 更新
- `ai_context/architecture.md` — Phase 0 描述更新
- `ai_context/current_status.md` — 修复管线和 Phase 0 描述更新
- `automation/README.md` — 三级修复表和集成位置更新

## 设计说明

- L3 重跑比增大 L2 timeout 更可靠：L2 是修 JSON 格式，L3 是重新生成内容
- 门控放在 `run_summarization()` 内部而非主流程，保持主流程简洁
- `repair_timeout` 参数化允许不同场景使用不同超时（Phase 3 可传不同值）
- 递归深度限制为 1（`_is_l3_retry` 布尔值），无无限循环风险
