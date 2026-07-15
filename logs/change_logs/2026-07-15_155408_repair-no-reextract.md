# repair-no-reextract

- **Started**: 2026-07-15 15:54:08 EDT
- **Branch**: main（worktree ../offpage-main，隔离自 extraction/<work_id>）
- **Type**: GO
- **Status**: PRE

## Background / Trigger

决策 #61（派生文件不进 repair）落地后重跑 phase 3，S001 在 repair 阶段
**死循环 1.5h 不收敛**：`Character B voice_state.target_voice_map[*].dialogue_examples`
的 `min_examples`（coverage_shortage）与 L3 语义 issue 形成打地鼠——T2 fixer
凑对白满足 min_examples → 凑的内容触发语义矛盾 → 语义 fixer 删掉 → min_examples
又不足。期间还触发一次 T3 全文重生烧 ~20min。coverage_shortage 的 0-token
接受快路被"先凑够再说"的顺序绕过，从未干净触发。

用户已把根治写成 todo `T-REPAIR-NO-REEXTRACT`（docs/todo_list.md）：repair
去掉 T3「全文重跑」（全 phase）+ 定点修复治本，按"修复需要什么"分层路由 +
每 tier 封顶 + defer，不合并 T1/T2、不碰 cache/API。用户拍板：A+B+C 一次做完。

## Conclusion and decisions

三步一次落地（A→B→C）。已定两个开放决策：
- **#2 薄内容**：`min_examples` count∈[1,threshold) 且源无干净增量 → 直接走
  coverage_shortage 0-token 接受（记 SourceNote），**不进 fixer padding**。砍掉
  打地鼠源头（联动决策 #61 的"门在跟现实打架就改门"哲学）。
- **#1 非语义修不掉**：schema/结构级 error 连 T1 都修不掉也一律 defer（扩展
  `deferred_repair_log` 的 DEFERRABLE_CATEGORY），承担 Phase 3.5 可能 error、
  人工兜底（用户已接受该风险）。

## Planned action list

Step A（止 spin + 厚 T0 + 叶子锚点）：
- file: `extraction/repair/fixers/local_patch.py` → apply patch 后立即对该字段跑
  L0–L2 复验，过了才算 resolved（现 apply 即算）；L3 留轮末 gate。
- file: `extraction/repair/fixers/programmatic.py` → 厚 T0：补 additionalProperties
  删多余键；required-缺失不再补空串致 minLength spin。
- file: `extraction/repair/checkers/{semantic,schema,structural}.py` → json_path 锚到
  叶子字段而非大容器，消灭巨型 patch。

Step B（删 T3）：
- file: `extraction/repair/coordinator.py` → build_fixers 去 tier 3；删 T3 分支；
  外层 lifecycle 塌成单轮（删 max_lifecycles_per_file/T3_TRIGGERED/T3_EXHAUSTED/
  prior_attempt_context/existing_accepted_fps + _TERMINAL_TYPES 的 T3_*）。
- file: `extraction/repair/fixers/file_regen.py` → 整文件删除。
- file: `extraction/persona_extraction/orchestrator.py` → 删 _build_sub_lane_regen_callback
  + 接线 + Phase 2 _lane_regen。
- file: `config.toml` → 去 [repair].max_lifecycles_per_file。

Step C（按 rule 路由 + 封顶）：
- file: `extraction/repair/protocol.py` → START_TIER + _issue_max_tier 按 rule 分流
  （机械 起始T0 封顶T1；判断类 T1；语义/需源 起始T2 封顶T2）；每 tier ≤2 次。
- file: `extraction/repair/fixers/local_patch.py` → 同文件多 issue 批量单次 patch；
  related context 从 attempt≥1 提前到 attempt 0。
- file: `extraction/persona_extraction/lifecycle/deferred_repair_log.py` → 扩展
  DEFERRABLE_CATEGORY（决策 #1）。

## Validation criteria

- [ ] `python -c "import extraction.repair.coordinator, extraction.repair.protocol, extraction.repair.fixers.local_patch, extraction.repair.fixers.programmatic"` 无 error
- [ ] grep 生产代码（排除 tests/logs/docs）无 `sub_lane_regen|lane_regen|file_regen|FileRegen` 调用
- [ ] `extraction/repair/fixers/file_regen.py` 已删除
- [ ] grep 确认 T1（local_patch attempt 0）不载 source
- [ ] `extraction/repair/tests/` 现有单测全过
- [ ] phase2 / phase3 相关 smoke 全过（stage_plan_min8 / 4_lane_merge / recovery_sweep / post_processing_replace_slice / l3_gate / cli_resume）
- [ ] compileall 通过

## Execution deviations

- 实现由 fresh-context engineering subagent 在 worktree 内完成（改动大、规格明确），
  主循环独立验证（import/grep/compileall/7 smoke + 逐段审 coordinator 状态机手术、
  routing、defer、immediate-re-verify 接线）。
- 计划外附带：新增 `field_patch.delete_field`（供 T0 删 additionalProperties 键）；
  一并移除 config 的 `t3_retry`（无消费者）；`structural.py` 已是叶子锚点故未改
  （容器锚点实为 schema additionalProperties，已改 schema.py）。
- `json_syntax` 有意排除出 DEFERRABLE_CATEGORIES（不可解析文件必须硬失败，不能提交）。
- 测试重写：`_smoke_l3_gate` 的 T3/lifecycle-2 场景改写为单轮无-T3 契约（保留真实断言：
  no-T3-in-report / patch_calls==0 / fact_mismatch）；`_smoke_triage` 去掉 T3 self-report
  场景。`_smoke_triage` 整体仍 FAIL —— 经 stash 隔离确认为 baseline 既有失败（fixture 缺
  target_baseline.json，与本次正交）。
- 遗留 stale 注释：`protocol.py` 数处 field 注释仍写 "pre-T3/post-T3"、"T2/T3 fixers"，
  `config.py`/`config.toml` phase2 注释提 "T3 = lane regen" —— Step 5 已清理
  （coordinator/protocol/triage/config 全部就地改）。
- Step 5 发现重构留下的 dead code（非本次范围，作 suggest-todo）：
  `notes_writer.load_existing_fingerprints`（零调用者）；orchestrator
  `_run_char_snapshot_sub_lanes` 的 `prior_attempt_context` 参数 +
  `_format_prior_attempt_context_block`（恒 None）；`schema_tolerance.py:8`
  docstring 提已删的 `T3_EXHAUSTED`。

<!-- POST phase fills in -->

## Landed changes

repair 子系统去掉 T3「全文重跑」+ 定点修复治本（A+B+C）：3 层就地修复
（T0→T1→T2，删 `file_regen.py`）、单轮 Phase A→B→C（塌 lifecycle 2）、按 rule
路由 `(start_tier,max_tier)` + 每 tier 封顶 2 次、T1 即时 L0–L2 复验止 spin +
同文件批量单 call、`coverage_shortage` 直接 0-token 接受不 padding、残留 defer
扩到 semantic/schema/structural/cross_file 四类。24 文件，净删 −662 行。

## Diff from plan

无方向偏离。计划外附带：新增 `field_patch.delete_field`（T0 删多余键用）；
一并去 `t3_retry`；改写 `_smoke_l3_gate` / `_smoke_triage` 至新契约。实现由
fresh-context subagent 完成，主循环独立验证 + 逐段审 coordinator 状态机。

## Validation results

- [x] import（coordinator/protocol/local_patch/programmatic/orchestrator/deferred_repair_log）无 error
- [x] grep 生产代码无 sub_lane_regen/lane_regen/file_regen/FileRegen 残留
- [x] `file_regen.py` 已删除
- [x] T1 不载 source（grep 确认）
- [x] 全悬空引用 sweep：无 T3_TRIGGERED/T3_EXHAUSTED/max_lifecycles/FileRegenFixer 生产/测试残留
- [x] repair + phase smoke：l3_gate / post_processing_replace_slice / 4_lane_merge / recovery_sweep / stage_plan_min8 / memory_digest_correspondence / cli_resume 全 PASS
- [x] compileall OK
- [ ] `_smoke_triage` — baseline 既有失败（stash 隔离确认），非本次引入，与本次正交

## Completed

- **Status**: DONE
- **Finished**: 2026-07-15 17:07:50 EDT
