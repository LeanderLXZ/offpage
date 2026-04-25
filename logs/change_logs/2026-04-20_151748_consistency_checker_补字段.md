# 2026-04-20 15:17:48 — consistency_checker 补 stage_events / character_arc

## 背景

opus-4-7 audit M1 指出：Phase 3.5 的 `_check_field_completeness`
宣称校验"每个快照包含所有必需维度"，实际 `required_fields` 只覆盖 12 个
字段，遗漏了 schema / prompt / 架构三方共识必填的 `stage_events` 与
`character_arc`。

- `schemas/stage_snapshot.schema.json` 顶层 `required` 不包含二者，
  所以 L1 schema check 也不会拦。
- `automation/prompt_templates/character_snapshot_extraction.md:44-46`
  把两者列为必填维度，缺失 = "扮演缺陷"。
- `docs/architecture/schema_reference.md:170,177` 把两者列为核心维度。

结果：完整缺失这两个字段的 snapshot 会被 Phase 3.5 误判为"通过"。

复核（/review-check）确认真实；首阶段 `character_arc` 的宽松性
（prompt 原文"第一个阶段可省略或仅写起点状态"）按与 `stage_delta`
一致的 `idx > 0` 分支处理。

## 改了什么

`automation/persona_extraction/consistency_checker.py`
`_check_field_completeness`：

- `required_fields` 追加 `"stage_events"`（每阶段都必填）。
- 原 `delta_field = "stage_delta"` 单字段变量改为
  `non_first_stage_fields = ("stage_delta", "character_arc")` 元组。
- 分支 `if idx > 0:` 由 `.append(delta_field)` 改为
  `.extend(non_first_stage_fields)`。

行为语义：

- 首阶段（idx == 0）：校验 13 字段（原 12 + `stage_events`），
  `stage_delta` / `character_arc` 不强制。
- 非首阶段（idx > 0）：校验 15 字段。

## 为什么 idx > 0 而非全强制

- prompt 模板 `character_snapshot_extraction.md:46` 明示首阶段可省略
  `character_arc`（"可省略或仅写起点状态"）。
- schema 顶层 `required` 也未列入。
- 与 `stage_delta` 的分支语义一致（stage 1 无前一阶段可 delta）。

## 校验

- `from automation.persona_extraction import consistency_checker` 成功。
- 对现有 `阶段01_<location_a>初遇`（两个角色：<character_a> / <character_b>）跑
  `_check_field_completeness`：0 completeness issue。
  两个 snapshot 均已包含 `stage_events`（list，9/10 条）与
  `character_arc`（dict）；首阶段 `stage_delta` 缺失被分支跳过，符合预期。

## 不做

- 不新增 "stage_events 条目长度/数量"校验（schema 已硬门控 50-80
  字 / maxItems 10）。
- 不动 prompt 或 schema（本次只补 checker 与 prompt / schema 的一致性）。
- 不动 sample 数据。
