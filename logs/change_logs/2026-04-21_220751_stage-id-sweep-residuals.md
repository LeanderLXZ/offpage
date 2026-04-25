# 二轮扫描：stage_id 英文化后残留的 schema / docs 小漏

## 背景

`/go` 和 `/after-check` 两轮落地后再做一次全仓扫描，聚焦非 log / 非
review_report 范围里仍保留旧约定的 stage_id 相关点。扫描结果大部分是
一致的 `{stage_id}` 通用占位符（符合新约定，代入值就是 `S###`），
以及 `docs/logs/` / `docs/review_reports/` 历史快照（按约定不动）。
本次补齐下面两处真正有漏网问题的：

## 改动清单

### `docs/requirements.md` §12.4.2 memory_timeline 条目示例

L2742 `"stage_id": "所属阶段"` 改为 `"stage_id": "S{stage:03d}"`，
与上一行 `"memory_id": "M-S{stage:03d}-{seq:02d}"` 的占位格式风格对齐，
清楚表达 stage_id 必须匹配紧凑英文代号 `S###`。

### `schemas/character/stage_snapshot.schema.json`

两处 stage 引用字段缺 pattern 约束：

- `misunderstandings[].resolved_at_stage`
- `concealments[].revealed_at_stage`

两者语义都是"在哪个阶段被解开/揭露"，value 本质是 stage_id 或空串。
schema 原先只写 `type: string`，改动后允许任意字符串混进来。本次
加上 `pattern: "^(S[0-9]{3})?$"`（允许空串或 `S###`），同时在
description 里点明"紧凑英文代号 S###"。

## 验证

- `Draft202012Validator.check_schema` 对 stage_snapshot schema PASS
- 正则自测：`^(S[0-9]{3})?$` 接受 `""` / `"S001"`，拒绝 `"阶段01"` /
  `"S01"`
- 磁盘上 `works/**/stage_snapshots/*.json` 目前为空（Phase 2.5
  rollback 状态），无需迁移

## 不动的区域

- `docs/logs/` + `docs/review_reports/`：历史快照，按约定保留原文
- `works/<work_id>/characters/<character_a>/canon/failure_modes.json`
  中 `evidence_refs` 里散文字符串 `FM-JHX-04S003追踪：...`：这是 /go
  批量转换时 `阶段03` → `S003` 直接替换的结果，语义仍然清晰，保留
- 所有 `{stage_id}.json` 形式的路径片段占位符：语义无偏移（代入值
  本来就是 `S###`），已由 `docs/architecture/data_model.md` §321
  统一约束过，不再重写

## 独立 commit

走 `/go` 流程、独立一次 commit、独立 log。
