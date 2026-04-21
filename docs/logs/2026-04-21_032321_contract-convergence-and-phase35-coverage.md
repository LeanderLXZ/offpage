# 契约收敛与 Phase 3.5 覆盖补齐

按 2026-04-21 01:00:57 codex full-repo alignment audit + `/check-review` 复核
落实 5 条 finding（F1 High / F2 High / F3 Medium / F4 Medium / F5 Low），
一次 commit 收齐。

## 改了什么 / 为什么

### F1 — `relationship_core` / `pinned_memories` canonical storage 定为 sidecar JSONL

schema + template 原来把 `pinned_memories` 以内联 array 写在 `manifest.json`，
但 `users/README.md` / `simulation/flows/startup_load.md` /
`simulation/retrieval/load_strategy.md` / 模板目录实际存在的
`pinned_memories.jsonl` 都指向独立 append-only 流。两套契约冲突会让
后续 runtime loader / writer 任选一边都"对"但互不兼容。

选定方案 B（append-only JSONL）：与 `ai_context/decisions.md §20`
merge is append-first 语义对齐；merge 追加写入更利于崩溃恢复；避免
每次钉选都全文件重写 manifest。

落地：

- `schemas/user/relationship_core.schema.json` 删除 `pinned_memories`
  inline array 字段（原 66–98 行）
- 新建 `schemas/user/pinned_memory_entry.schema.json`：规范 jsonl
  单条格式（memory_id / summary / source_context_ids? / importance? /
  permanence_reason? / pinned_at?）
- `users/_template/relationship_core/manifest.json` 移除
  `"pinned_memories": []` 字段；`pinned_memories.jsonl` 空文件保留
- `docs/architecture/schema_reference.md` 新增 entry schema 条目，
  更新 `schemas/user/` 条目计数 4 → 5，修订 relationship_core 用途
  说明（单对象 manifest + sidecar JSONL 的分工）
- `ai_context/decisions.md` 新增 §22a 记录此存储契约

### F2 — Phase 3.5 `evidence_refs` 覆盖率扩展到 world stage snapshot

`automation/persona_extraction/consistency_checker.py` 的
`_check_evidence_refs_coverage` 原本只遍历字符 snapshot 和
`memory_timeline`，没有检查 `works/{work_id}/world/stage_snapshots/*.json`
的 `evidence_refs`。`schemas/world/world_stage_snapshot.schema.json` 明确
定义了该字段，需求 / 架构文档也承诺"快照和记忆条目"的覆盖率。

落地：函数体起始处新增 world 段遍历，空值 emit
`ConsistencyIssue("warning", "evidence_refs", f"world/{stage_id}", ...)`。
函数签名不变；其他 checker 不影响。

### F3 — `docs/requirements.md:1265` `repairing` → `reviewing`

`progress.py` / `automation/README.md` 早已是 `post_processing → reviewing`；
需求文档状态机图还留着不存在的 `repairing` 状态名，会误导后续运维 / AI
把它当持久化状态名。单行替换。

### F4 — `docs/architecture/data_model.md` 把 append-only 流统一为 `.jsonl`

`docs/architecture/data_model.md` 把 transcript / turn_journal /
turn_summaries / memory_updates / key_moments / archive_index /
pinned_memories / history/timeline 写成 `.json`，但 `users/README.md` /
`simulation/flows/` / `simulation/retrieval/` / 模板都已改为 `.jsonl`。
`ai_context/handoff.md` 把 data_model.md 列为权威 "Architecture detail"，
所以 data_model.md 必须对齐。

落地：逐行把上述 append-only 文件扩展名改为 `.jsonl`；单对象文件
（`manifest.json` / `profile.json` / `role_binding.json` /
`long_term_profile.json` / `context_summary.json` /
`session_index.json` / `character_state.json` /
`archive_refs.json`）保持 `.json`。全库复查 `docs/architecture/`
除报告文件外无残留旧扩展名。

### F5 — 删除重复日志

`docs/logs/` 下同时跟踪
`2026-04-03_stage_boundary_alignment_and_prompt_rewrite.md`
（无 HHMMSS）与
`2026-04-03_020841_stage_boundary_alignment_and_prompt_rewrite.md`
（合规），`diff -q` 显示内容完全相同。`git rm` 无 HHMMSS 版。

## 涉及文件

- `schemas/user/relationship_core.schema.json`
- `schemas/user/pinned_memory_entry.schema.json`（新建）
- `users/_template/relationship_core/manifest.json`
- `automation/persona_extraction/consistency_checker.py`
- `docs/requirements.md`
- `docs/architecture/data_model.md`
- `docs/architecture/schema_reference.md`
- `ai_context/decisions.md`
- `docs/todo_list.md`（删除已落地的 T-USER-DATA-FORMAT 条；T-USER-AUX-SCHEMAS 清除 `pinned_memories.jsonl per-line schema` 子项并解除对 T-USER-DATA-FORMAT 的依赖）
- `docs/logs/2026-04-03_stage_boundary_alignment_and_prompt_rewrite.md`（删除）

## 跨文件对齐（对照 `ai_context/conventions.md` Cross-File Alignment 表）

- `schemas/**` 改动 → 同步 `docs/architecture/schema_reference.md`
  （计数 + 新条目 + relationship_core 用途说明）；`schemas/README.md`
  无细粒度字段说明，无需改
- `docs/requirements.md` 改动 → `ai_context/requirements.md` 无
  `repairing` 引用，无需同步
- Loading strategy 文件名 → `users/README.md` /
  `simulation/flows/startup_load.md` /
  `simulation/retrieval/load_strategy.md` 已是 `.jsonl`，本次对齐
  的是 `docs/architecture/data_model.md`
- Durable decision → `ai_context/decisions.md §22a / §22b`

## 验证

- `python -c "from automation.persona_extraction import consistency_checker"`
  通过
- 两份 schema 通过 `jsonschema.Draft202012Validator.check_schema`
- 更新后的 template manifest 通过 `jsonschema.validate` 新 schema
- 全库 grep `repairing` 仅命中报告历史文档
- 全库 grep append-only 文件名 `.json\b`（transcript/turn_journal/
  turn_summaries/memory_updates/key_moments/archive_index/
  pinned_memories）在 `docs/architecture/` 和 `ai_context/` 无残留
- 全库 grep `pinned_memories` 无内联 array 形态残留
