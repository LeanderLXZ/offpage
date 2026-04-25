# 2026-04-23 05:31:16 — world stage_events maxItems 15 → 30

## 背景

2026-04-23 05:02 的 H4 跟进把 world `stage_events` maxItems 设为 15，与
character 侧对齐（"character / world 同限"）。但世界公共层事件可枚举性
显著高于单角色本阶段事件：一个阶段内典型会包含多势力变迁 + 地形/资源
变化 + 规则揭示 + 若干跨角色公共事件，按保守编码条目常超 15。为避免
把这些合并成粗粒度模糊摘要（破坏 50–80 字/条硬门控的"精确摘要"初衷），
放宽 world 侧到 30。character 侧维持 15（角色本阶段关键事件通常更集中）。

## 改动

- `schemas/world/world_stage_snapshot.schema.json`
  `stage_events.maxItems` 15 → 30
- `docs/requirements.md`
  - §2.3.4 世界阶段快照：`stage_events`，≤ 15 条 → ≤ 30 条
  - "字段条数上限汇总" 表：原单行 `stage_events | 15` 拆为两行
    `stage_events（character） | 15` 与 `stage_events（world） | 30`
- `docs/architecture/schema_reference.md`
  world_stage_snapshot.stage_events 描述 `≤ 15 条` → `≤ 30 条`

character 侧无改动（schema / prompt / 描述仍为 15）。
`ai_context/` 相关文件未声明条数上限，无需同步。

## 校验

- schema self-validation：`Draft202012Validator.check_schema` 通过，
  `stage_events.maxItems == 30`
- extraction 分支 S001 world snapshot（12 条 stage_events）按新 schema
  校验：0 errors
