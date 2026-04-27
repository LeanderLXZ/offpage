# char-snapshot-required-fields-pointer

- **Started**: 2026-04-27 18:55:31 EDT
- **Branch**: main（worktree：`../offpage-main`）
- **Status**: PRE

## 背景 / 触发

`docs/architecture/extraction_workflow.md:277` 与 `docs/requirements.md:2139`
两处 docs 仍称角色 `stage_snapshot` 含"13 个必填维度"，且 requirements.md
括号内列举的字段名（`personality, mood, voice_state, behavior_state,
boundary_state, relationships, knowledge_scope, stage_delta` 等）与 schema
实际不符：

- 实际字段名是 `current_personality` / `current_mood`，不是 `personality` /
  `mood`
- `stage_delta` 在 schema 中**非** required（首阶段可省略，schema 描述明确）
- schema `required` 实测 **17 条**：`schema_version, work_id, character_id,
  stage_id, stage_title, timeline_anchor, snapshot_summary, active_aliases,
  current_personality, current_mood, knowledge_scope, voice_state,
  behavior_state, boundary_state, relationships, stage_events, character_arc`

来源：todo_list.md `T-CHAR-SNAPSHOT-13-DIM-VERIFY`。

## 结论与决策

采用**指针式表述**（去掉具体数字 / 字段名清单，改为"以
`schemas/character/stage_snapshot.schema.json` 的 required 列表为准"），
与 schema_reference.md "schema 是权威，不复述具体数字"原则一致；避免下次
schema required 增减时漂移。

## 计划动作清单

- file: `docs/architecture/extraction_workflow.md` 第 277 行
  → "13 个必填维度是否齐全" 改为指针式（schema required 为准）
- file: `docs/requirements.md` 第 2139 行
  → 表格"快照字段完整性"行说明改为指针式，去掉"13 个必填维度"和括号内字段示例
- file: `docs/todo_list.md`
  → 把 `T-CHAR-SNAPSHOT-13-DIM-VERIFY` 整条从"下一步"段删除，刷新顶部索引段
- file: `docs/todo_list_archived.md`
  → `## 已完成` 段添加瘦身条目（标题 + 完成形式 + 1 行摘要 + 本 log 链接）

## 验证标准

- [ ] `docs/architecture/extraction_workflow.md` 不再出现 "13 个必填维度"
- [ ] `docs/requirements.md` 不再出现 "13 个必填维度" 与括号内 schema 字段示例
- [ ] 全仓 grep "13 个必填" / "13 必填" 残留为 0
- [ ] `docs/todo_list.md` 顶部索引"下一步"行数 -1，汇总数同步
- [ ] `docs/todo_list_archived.md` `## 已完成` 段含本任务条目并指向本 log
- [ ] schema 文件未被修改（本次纯文档对齐）

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

- `docs/architecture/extraction_workflow.md:277` — 程序化检查项 #2
  "13 个必填维度是否齐全" → "必填维度是否齐全（以
  `schemas/character/stage_snapshot.schema.json` 的 `required` 列表为准）"。
- `docs/requirements.md:2139` — 表格"快照字段完整性"行说明改为指针式：
  "每个 stage_snapshot 的必填维度是否齐全；维度清单以 `schemas/character/
  stage_snapshot.schema.json` 的 `required` 列表为单一权威来源（schema 是
  权威，本文档不复述具体字段名 / 条数，避免漂移）"。括号内字段示例
  （personality / mood / stage_delta 等）一并删除。
- `docs/todo_list.md` — 删除 `T-CHAR-SNAPSHOT-13-DIM-VERIFY` 整条正文段；
  顶部索引"下一步"行数 2 → 1，汇总 8 → 7。
- `docs/todo_list_archived.md:74` — `## 已完成` 段顶部新增条目（改方案后
  完成形式：原候选"字面 17 条" → 实际"指针式"），含本 log 链接。

## 与计划的差异

无。

## 验证结果

- [x] `docs/architecture/extraction_workflow.md` 不再出现 "13 个必填维度" — `grep "13 个必填" docs/architecture/extraction_workflow.md` 无匹配
- [x] `docs/requirements.md` 不再出现 "13 个必填维度" 与括号内 schema 字段示例 — `grep "13 个必填" docs/requirements.md` 无匹配；该行括号内字段示例已删除
- [x] 全仓 `grep "13 个必填" / "13 必填"` 残留为 0（canonical docs 中）— 仅 `docs/todo_list_archived.md` 与 `logs/change_logs/` 历史 log 含字面引用，符合"历史只追加"约定
- [x] `docs/todo_list.md` 顶部索引"下一步"行数 -1，汇总数同步 — 索引"🟡 下一步（1 条）" + 汇总"共 7 条 — 🟢 0 ｜ 🟡 1 ｜ ⚪ 6"
- [x] `docs/todo_list_archived.md` `## 已完成` 段含本任务条目并指向本 log
- [x] schema 文件未被修改（本次纯文档对齐）— `git diff --stat schemas/` 无输出

## Completed

- **Status**: DONE
- **Finished**: 2026-04-27 19:17:45 EDT

