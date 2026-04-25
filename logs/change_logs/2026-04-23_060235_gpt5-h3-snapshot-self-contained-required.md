# 2026-04-23 06:02 — gpt-5 audit H3：快照 schema 强制自包含契约

## 背景

gpt-5 H3：character / world stage_snapshot schema 的 `required` 只到
`snapshot_summary`。自包含契约（all runtime dimensions must be present）
之前只由 prompt + L2 structural + L3 semantic 兜底，L1 schema gate 对
"只有元信息 + snapshot_summary" 的残缺快照会放行。与 `schema_reference.md`
"这是运行时加载角色状态的核心文件，自包含" 的定位不一致。

## 改动

### character schema（`schemas/character/stage_snapshot.schema.json`）

`required` 追加自包含维度：`active_aliases`, `current_personality`,
`current_mood`, `knowledge_scope`, `voice_state`, `behavior_state`,
`boundary_state`, `relationships`, `stage_events`, `character_arc`,
`evidence_refs`。

`stage_delta` **不强制**——stage 1 无上一阶段参考，schema 层必须容忍
缺失。prompt 和 L2 仍会在 stage≥2 的情况下要求出现。

### world schema（`schemas/world/world_stage_snapshot.schema.json`）

`required` 追加：`foundation_corrections`, `stage_events`,
`current_world_state`, `relationship_shifts`, `character_status_changes`,
`location_changes`, `map_changes`, `evidence_refs`——即 §2.3.4
"每个世界阶段快照应包含" 列出的 8 个字段。允许空数组，只强制字段存在。

## 验证

- `Draft202012Validator.check_schema` 两个 schema 都通过
- extraction 分支 S001：
  - `<character_a>` 角色快照 → PASS
  - `<character_b>` 角色快照 → PASS
  - 世界快照 → PASS
- 即：现有实例数据与新门控兼容，不会 break S001 已提交内容；S002 ERROR
  待 `--resume` 重跑时将用新 schema 严格校验

## 跨文件对齐

- `docs/architecture/schema_reference.md`：
  - world_stage_snapshot 条目末尾追加"自包含契约（schema 硬门控）"段
  - character/stage_snapshot 条目末尾追加同名段

## 未做 / 推迟

- prompt template / `docs/requirements.md` §2.3.4 措辞未改——原文已列出
  所有自包含字段，这次仅升门控层级；若后续要显式声明"schema 强制"可
  单独补一句
- `snapshot_summary` / `chapter_scope` / `timeline_anchor` 等字段 maxItems /
  minLength 微调不在本次范围

## 受影响文件清单

```
docs/architecture/schema_reference.md
schemas/character/stage_snapshot.schema.json
schemas/world/world_stage_snapshot.schema.json
```
