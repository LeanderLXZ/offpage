# After-check M1 + L1 收尾

接 `2026-04-21_032321` 的契约收敛后做 `/after-check`，查出两条
遗漏：

- **M1（Medium）**：`schemas/README.md:12` 的 `user/` 行没跟着
  `schemas/user/pinned_memory_entry.schema.json` 的新增同步，成员列
  仍是 4 个；`ai_context/conventions.md` Cross-File Alignment 表明
  确点名 `schemas/README.md` 是 `schemas/**/*.schema.json` 的下游
- **L1（Low）**：`ai_context/decisions.md §22b` 开头写 "User-side
  append-only streams use `.jsonl`"，但枚举里含
  `world/history/timeline`，而这条实际在 `works/{work_id}/world/`
  下（world-side）。规则正确，仅作用域措辞有歧义

本轮一次收齐。

## 改了什么

### M1 — `schemas/README.md:12` 补 `pinned_memory_entry`

- 成员列：`user_profile / role_binding / long_term_profile /
  relationship_core` → 追加 `pinned_memory_entry`
- 描述：在"用户根画像、绑定、长期档案、关系核心"后追加"钉选记忆条目"
- 与 `docs/architecture/schema_reference.md:13`（计数 4 → 5 + 同款
  扩展描述）对齐

### L1 — `ai_context/decisions.md §22b` 首句改为系统级

原文开头 "User-side append-only streams use `.jsonl`" → 改为
"Append-only streams system-wide use `.jsonl`; single-object state
uses `.json`. Applies to both user-side (`users/{user_id}/...`) and
work/world-side (`works/{work_id}/world/...`) persistence."

规则内容不变；只是让作用域与枚举里真实出现的 `world/history/timeline`
自洽。

## 涉及文件

- `schemas/README.md`
- `ai_context/decisions.md`

## 跨文件对齐

- schema 索引层补齐后，`schemas/README.md` 与 `docs/architecture/
  schema_reference.md` 对 `schemas/user/` 成员的描述一致
- `decisions.md §22b` 文字与 `docs/architecture/data_model.md`
  的实际分布（world 侧 `history/timeline.jsonl` 在 L222 / L287，
  user 侧 append-only 在 L393–L454）不再冲突

## 验证

- `grep 'User-side append-only'` 全库无命中
- `sed -n '12p' schemas/README.md` 返回 5 个成员 + 新描述
- 无代码 / schema 结构变更，跳过 jsonschema / import smoke test
