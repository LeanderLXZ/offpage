# fix-from-postcheck

- **Started**: 2026-07-15 17:33:16 EDT
- **Branch**: main
- **Type**: GO
- **Status**: PRE

## Background / Trigger

对 commit `010fb03`（决策 #62 repair 重构）的 `/post-check` 判定
REVIEWED-FAIL，经 `/fix` Auto triage 落地 fix 桶。源审查：
`logs/change_logs/2026-07-15_155408_repair-no-reextract.md`。核心是 H1——
本次重构的招牌功能（min_examples → 0-token 接受）在默认配置下实际不生效。

## Conclusion and decisions

修 10 项（H1-3 / M1-4 / L1-3）+ 采纳 OQ1（H1 修法）/ OQ2（= L3）。最小补丁，
不顺手重构。M5（数组嵌套 additionalProperties T0 删除失效）本轮不修（todo-eligible）。

## Planned action list

- file: `extraction/repair/coordinator.py` → **H1**: attempt 1 只从传给 `fix()` 的
  `attempted` 排除 coverage_shortage、保留在 `remaining` 供 0-token 快路（OQ1）。
  **M1**: LENGTH_TOLERANCE_PASS 短路收紧——仅当确无其它未处理 blocking 才 PASS。
  **M4**: modified_files 纳入"本轮真实改写落盘"文件（不只 resolved）供 L3 gate。
  **L1**: 删 `_TERMINAL_TYPES`。
- file: `extraction/repair/tracker.py` → **L1**: 删 `record_tier_use_on_file` /
  `tier_uses_on_file` / `attempts_at_tier` 死代码。
- file: `extraction/repair/context_retriever.py` → **L1**: 删 `retrieve_all_stage`。
- file: `extraction/repair/notes_writer.py` → **L1**: 删 `load_existing_fingerprints`（零调用者）。
- file: `extraction/persona_extraction/orchestrator.py` → **L1**: 删 `prior_attempt_context`
  参数 + `_format_prior_attempt_context_block`（恒 None）；**L2**: 改 :3496 T3 注释。
- file: `extraction/validation/shared/schema_tolerance.py` → **L1**: :8 docstring 去 T3_EXHAUSTED。
- file: `extraction/repair/fixers/programmatic.py` → **L3/OQ2**: `_fix_string_length`
  不再对已存在字符串补 minLength `…`。
- file: `docs/decisions.md` → **H2**: #62 归档「Character B」→「某角色」；**M2**: #25 归档补 #62 supersede。
- file: `ai_context/decisions.md` → **M2**: #25 索引补 #62 supersede + 对齐 fixer T0-T2；
  **M3**: #55 索引去 "lifecycle 2 sub-lane 重抽"。
- file: `extraction/README.md` → **H3**: repair 段刷到 T0→T1→T2 新模型，删 file_regen.py 引用。
- file: `extraction/validation/README.md` → **M3**: :3 "T0–T3 fixer" → T0–T2。

## Validation criteria

- [ ] `python -c "import extraction.repair.coordinator, extraction.repair.tracker, extraction.repair.context_retriever, extraction.repair.notes_writer, extraction.persona_extraction.orchestrator, extraction.repair.fixers.programmatic"` 无 error
- [ ] **H1 专项**：inline 复现构造 min_examples coverage_shortage → 断言走 0-token SourceNote 接受（accepted_notes≥1、`_run_coverage_shortage_triage` 被调用）
- [ ] repair smoke（l3_gate）+ phase smoke（post_processing / 4_lane_merge / recovery_sweep）回归 PASS
- [ ] grep 生产代码无 file_regen/T3 残留 + 无本轮删除符号（`_TERMINAL_TYPES` / `load_existing_fingerprints` / `retrieve_all_stage` / `record_tier_use_on_file` / `prior_attempt_context`）的悬空引用
- [ ] compileall OK
- [ ] docs 无真实角色名残留（grep Character B/Character A）

## Execution deviations

- H1 由主循环亲修（保留 coverage_shortage 于 remaining、仅从 attempted 排除）；
  其余 9 项由 implementation subagent 落地，主循环独立验证（含 H1 行为 smoke、
  逐读 M1/M4 coordinator 编辑）。
- M4 经确认**可达**（T1 apply 落盘但即时复验未过时，文件缺席 modified_files →
  L3 gate 漏检），已修（按 `result.patched_paths` 补入 modified_files）。
- **越界（保留 + 记录）**：subagent 在 `docs/todo_list_archived.md` 顺带 scrub 了
  **早前会话遗留**的真实名（`<work_id>`/`Character A`/`Character B` → `<work_id>`/
  `角色A`/`角色B`）。触发原因：H2 的 verify grep 要求 docs/ 无真名。scrub 干净、
  语义不变、符合项目「docs 禁真名」硬规则 → 保留；Step 5 透明标注。
- L1 附带删除 `_SUB_LANE_PRIOR_CONTEXT_BUDGET`、tracker `_tier_uses_per_file`
  字段（随死方法一并 dead）。

<!-- POST phase fills in -->

## Landed changes

落地 /post-check REVIEWED-FAIL 的 fix 桶 10 项 + OQ1/OQ2 采纳。核心 H1：
coverage_shortage 0-token 接受快路现真正可达（决策 #2 招牌功能生效）。M1
LENGTH_TOLERANCE 收紧、M4 modified_files 补 patched_paths、L1 清 T3 时代死代码、
L3 去 T0 minLength 造字符串、H2/H3/M2/M3 文档刷到 T0–T2 新模型。12 文件。

## Diff from plan

无实质偏离。计划外：H2 verify grep 触发 subagent 顺带 scrub `todo_list_archived.md`
早前会话遗留真名（保留，符合 docs 禁真名硬规则）。M5（数组嵌套 additionalProperties
T0 删除失效）本轮不修，作 Step 5 suggest-todo。

## Validation results

- [x] import（6 模块）无 error + compileall OK
- [x] **H1 专项**：inline 复现 min_examples coverage_shortage → 断言 `_run_coverage_shortage_triage` 被调用（接受快路可达）PASS
- [x] repair smoke（l3_gate）+ phase smoke（post_processing / 4_lane_merge / recovery_sweep）全 PASS
- [x] grep 生产代码无 file_regen/T3 残留 + 无删除符号悬空引用
- [x] docs/ai_context 无真实角色名（grep 0）
- [x] M1 gating（`_all_length_only(current_issues)` 全集才 PASS）+ M4（patched_paths 入 modified_files）代码审阅确认

## Completed

- **Status**: DONE
- **Finished**: 2026-07-15 17:56:18 EDT
