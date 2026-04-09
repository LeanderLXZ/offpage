# Progress 与 --end-batch 分离（Phase 4 模式对齐）

日期：2026-04-09

## 问题

`--end-batch N` 首次运行时，`confirm_with_user` 将 batch plan 截断为前 N 个
写入 progress。这导致 progress 同时承担"目标定义"和"状态记录"两个职责。
后续 resume 扩大范围时需要额外补全逻辑，且初版补全放在 `run_full()` 中，
CLI 的 `--resume` 路径（直接调 `run_extraction_loop`）会绕过。

## 修复

对齐 Phase 4 的设计模式：progress 始终包含完整数据，运行参数只控制执行范围。

### orchestrator.py — `confirm_with_user`

- 去掉 `batches_data = batches_data[:end_batch]` 截断
- progress 始终写入完整 batch plan
- `--end-batch` 仅传递给 `run_extraction_loop` 的 `max_batches` 参数

### orchestrator.py — `_ensure_batches_from_plan`

- 保留在 `run_extraction_loop` 入口作为防御性补全
- 应对 batch plan 更新或手动编辑 progress 等边缘情况

### progress.py

- `expand_batches()` 不变，仍作为底层补全工具

### 文档

- `docs/requirements.md` §11.5: "Progress 与 --end-batch 分离"
- `ai_context/current_status.md`, `docs/architecture/extraction_workflow.md`,
  `automation/README.md`: 同步更新

## 受影响文件

- `automation/persona_extraction/orchestrator.py`
- `docs/requirements.md`
- `ai_context/current_status.md`
- `docs/architecture/extraction_workflow.md`
- `automation/README.md`
