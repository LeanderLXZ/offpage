# repair_defer_unresolved_semantic

- **Started**: 2026-07-15 10:17:32 EDT
- **Branch**: main
- **Type**: GO
- **Status**: PRE

## Background / Trigger

Phase 3 首次端到端运行时，S002 的 repair 在某角色快照里查出 3 个真实语义
自相矛盾（knowledge_scope 同一事实既 known 又 uncertain；current_status 与
relationships 对同一物件的来源打架）。这些是 L3 语义层问题，field-level 的
T1/T2 自动修复搞不定（跨字段一致性），T3 在 lifecycle 2 又被禁用；加上 L3
semantic reviewer 本身非确定性（每轮 flag 数 2→4→3 跳动），修复循环追不平，
stage 最终判 ERROR、整条 Phase 3 停在 S002。

用户诉求：repair 检测/修复逻辑**不变**，但把「修不动 → 停机」改为「修不动
→ 记录 + 继续」，全部 stage 跑完后再由一个 Phase 3.5 收尾工具逐条精准修
（不重跑整个 stage）。收尾修复工具（Part B）本轮**不做**，登记为 todo。

## Conclusion and decisions

- 只改「repair 终局未决 → stage ERROR」这一个接缝（orchestrator Phase 3
  `_process_stage` Step 4 出口，约 line 3609-3642）。
- **只延后 `category=="semantic"` 的残留 error**；只要残留里含 json_syntax /
  schema / structural / cross_file，或有 worker exception（issues 为空但
  passed=False），仍走原 hard ERROR 路径——那些会让下游 stage 读不了。
- 延后时：把未决语义 issue 写进 durable 台账
  `works/{work_id}/analysis/deferred_repairs/{stage_id}.jsonl`（随 stage
  commit 一起提交，Phase 3.5 收尾工具日后消费），打 WARNING，Step 4 打印
  `DEFER`，然后**穿透到原 PASS 路径**（post-repair PP rerun → PASSED → commit）。
- 开关：`[repair].defer_unresolved_semantic`。代码默认 **False**（保留原
  停机语义，opt-in）；config.toml 本项目设 **true** 开启。
- 判据「哪些可延后」抽成纯函数放新模块，便于 smoke。

## Planned action list

- file: extraction/persona_extraction/lifecycle/deferred_repair_log.py（新增）
  → `deferrable_semantic_issues(failed_entries)` 纯判据 +
    `write_deferred_repairs(work_root, stage_id, issues)` jsonl 台账写出
- file: extraction/persona_extraction/orchestrator.py
  → Step 4 repair 出口接缝：all_pass / defer / hard-ERROR 三分支重构
- file: extraction/persona_extraction/core/config.py
  → `RepairConfig`（或对应节）加 `defer_unresolved_semantic: bool = False`
- file: extraction/config.toml
  → `[repair]` 加 `defer_unresolved_semantic = true` + 注释
- file: docs/architecture/extraction_workflow.md + extraction/README.md
  → repair 段补「未决语义延后 + deferred_repairs 台账」说明
- file: ai_context/decisions.md + docs/decisions.md → 新决策条目
- file: docs/todo_list.md → 登记 Part B（Phase 3.5 收尾精准修复工具）

## Validation criteria

- [ ] import 无错：orchestrator / config / 新模块
- [ ] smoke：`deferrable_semantic_issues` 对「全 semantic error」返回该列表；
      对「含 structural / cross_file」返回 None；对「issues 为空」返回 None
- [ ] smoke：`write_deferred_repairs` 写出的 jsonl 每行含
      stage_id/file/json_path/category/severity/rule/message 且可解析
- [ ] config 加载：`get_config().repair.defer_unresolved_semantic` 读到 true
- [ ] grep：orchestrator Step 4 出口无残留旧「无条件 ERROR」路径漏改

## Execution deviations

- Step 4 对齐时顺带同步 `ai_context/architecture.md`（Phase 3 流程串补
  deferred 分支一句），不在初始 Planned action list 内——属 Cross-File
  Alignment 同步，非新设计。详见 POST §Diff from plan。

<!-- POST phase fills in -->

## Landed changes

repair 终局门控加「未决语义 record-and-continue」：新增
`lifecycle/deferred_repair_log.py`（`deferrable_semantic_issues` 判据 +
`write_deferred_repairs` 台账），orchestrator Phase 3 Step 4 出口重构成
PASS / DEFER / hard-ERROR 三分支，config 加 `[repair].defer_unresolved_semantic`
（代码默认 false，config.toml 本项目 true）。文档全链同步 + 决策 #60 +
Part B（Phase 3.5 收尾修复 pass）登记为 `T-PHASE35-DEFERRED-FIX`。

## Diff from plan

- 计划外新增：`ai_context/architecture.md` Phase 3 流程串补一句 deferred
  分支（Cross-File Alignment 顺带同步，非新设计）。
- 其余与 Planned action list 一致。

## Validation results

- [x] import 无错：orchestrator / config / 新模块 / cli 全 import ok
- [x] smoke 判据：全 semantic→返回列表；含 structural/cross_file/schema→None；
      空 issues→None；semantic warning（无 error）→None
- [x] smoke 台账：jsonl 每行 7 字段齐全可解析
- [x] config 加载：`defer_unresolved_semantic == True`（config.toml 生效）
- [x] grep 接缝：PASS / DEFER / hard-ERROR 三分支完整，无旧无条件 ERROR 残留
- [x] 回归：`_smoke_l3_gate` / `_smoke_stage_plan` 通过；`_smoke_triage`
      失败是 HEAD 既坏（commit 5d9ef6f 明注），与本改动正交
- [x] 红线：本次改动文件无真实角色/书名（PRE log 一处「Character B」已改占位符）

## Completed

- **Status**: DONE
- **Finished**: 2026-07-15 10:31:17 EDT
