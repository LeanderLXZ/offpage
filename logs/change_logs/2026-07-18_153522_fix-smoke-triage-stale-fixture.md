# fix-smoke-triage-stale-fixture

- **Started**: 2026-07-18 15:35:22 EDT
- **Branch**: main
- **Type**: GO
- **Status**: PRE

## Background / Trigger

`docs/todo_list.md` 词条 `T-SMOKE-TRIAGE-BROKEN`：
`python -m extraction.repair.tests._smoke_triage` 在 HEAD 上长期失败
（`scenario_a_pre_t3_accept` → `AssertionError: expected at least one
accepted note`，输出 `notes=0 / triage calls=0`）。已用 `git stash` 对照
证实与近期改动无关。词条要求先判定是「测试过期」还是「triage 代码真坏」——
后者意味着 `source_inherent` 接受路径在生产里一直静默失效。

## Conclusion and decisions

**判定：测试 fixture 过期，triage 代码正常，生产无静默破损。**

根因（现场证据，见下）：`_write_work_layout` 把被测文件放在
`characters/A001/canon/stage_snapshots/S001.json`，但不写同级
`target_baseline.json`。L2 的 `TargetsKeysEqBaselineChecker`（D4 校验，
在这个 fixture 写成之后才加入 pipeline）因此报
`targets_baseline_missing`（`json_path="$"`、`category=cross_file`、
severity=error）。两个后果叠加：

1. `CheckerPipeline` 对带低层 error 的文件按设计跳过 L3 —— 打桩的 semantic
   issue 根本没被生成（`state["semantic"] == 0`），triage 无输入，
   `triage calls=0`；
2. 该 issue 是 root-anchored（`json_path == "$"`）→ `route_tiers` 返回
   `NO_FIX_TIER`(-1) → `fixers.get(-1) is None` → 整个 tier group 被跳过，
   Phase B 无补丁、无 residual triage，直接 FAIL。

生产影响：无。`targets_baseline_missing` 是 fail-closed 的 blocking error，
真实提取里 `target_baseline.json` 由 phase 2 落盘，该分支不会触发；也不存在
「被静默吞掉的 `source_inherent` 接受」。

已用一次性脚本验证：给 fixture 补 `target_baseline.json` + snapshot 三结构
后，scenario A 端到端通过（`passed=True notes=1 triage=1 regen=0`，
`SN-S001-01 / semantic / author_contradiction`）。

因此本轮只改测试，不动 `triage.py` / `coordinator.py` 等生产代码。
同时按词条授权，清掉场景里残留的 T3 痕迹（决策 #62 已删除 T3 与
`file_regen.py`）：场景名 `scenario_a_pre_t3_accept`、stub 的
`regeneration tool` 分支与 `regen` 计数断言。

## Planned action list

- file: `extraction/repair/tests/_smoke_triage.py`
  → `_write_work_layout`：补写 `canon/target_baseline.json`，snapshot 携带
    D4 三结构（`voice_state.target_voice_map` /
    `behavior_state.target_behavior_map` / `relationships`），并参数化
    snapshot + baseline targets，使 scenario F 复用同一 fixture（消除 F 内
    ~35 行重复的目录 / stage_plan / SourceContext 搭建）
- file: `extraction/repair/tests/_smoke_triage.py`
  → 场景 A 更名为 `scenario_a_triage_accept`；删除 A / F 中 T3
    （`regeneration tool` stub 分支 + `regen` 计数断言）残留；模块 docstring
    与场景 docstring 同步对齐 #62 后的三层就地修复形态
- file: `docs/todo_list.md` + `docs/todo_list_archived.md`
  → 词条 `T-SMOKE-TRIAGE-BROKEN` 完成后归档 + 刷新顶部 Index

## Validation criteria

- [ ] `python -m extraction.repair.tests._smoke_triage` 全部 5 个场景通过，exit 0
- [ ] `python -m extraction.repair.tests._smoke_l3_gate` 不回归（仍与改前同状态）
- [ ] `python -c "import extraction.repair.tests._smoke_triage"` import 无错
- [ ] `grep -rn "pre_t3\|scenario_a_pre_t3_accept\|regeneration tool" extraction/` 残留 = 0
- [ ] `git diff --name-only` 只含 `extraction/repair/tests/_smoke_triage.py`
      + `docs/todo_list*.md` + 本日志文件（生产代码零改动）

## Execution deviations

- Step 5 就地修 1 处：模块 docstring 里 ``` ``target_baseline\n.json`` ``` 的双反引号
  被换行截断，改写为不跨行。
- 计划外发现（未落地，已在 Step 5 列为"建议注册到 todo_list"）：
  `extraction/repair/tests/` 没有聚合入口，两个 smoke 不被任何流程调用 ——
  这正是本 bug 存活约 3 个月的机制。

<!-- POST phase fills in -->

## Landed changes

`_smoke_triage.py` 的 fixture 改写为 D4-complete 角色包，scenario F 复用同一
fixture（消除 ~35 行重复搭建），并清掉决策 #62 已删除的 T3 残留。生产代码零改动；
`T-SMOKE-TRIAGE-BROKEN` 归档。

## Diff from plan

none —— 三条计划动作全部落地，无增删。

## Validation results

- [x] `python -m extraction.repair.tests._smoke_triage` —— 5 个场景全过，exit 0
      （`[A] passed=True notes=1 triage calls=1` / `[F] passed=True notes=1
      triage_calls=0`）
- [x] `python -m extraction.repair.tests._smoke_l3_gate` —— 7 个场景不回归，仍全过
- [x] `python -c "import extraction.repair.tests._smoke_triage"` —— 无错
- [x] `_smoke_triage` 内 T3 残留 grep = 0（`_smoke_l3_gate` 中的 `regen` 提及是
      "T3 已不存在"的现行断言，非残留，不动）
- [x] `git status` 仅含 `extraction/repair/tests/_smoke_triage.py` +
      `docs/todo_list{,_archived}.md` + 本日志

## Completed

- **Status**: DONE
- **Finished**: 2026-07-18 15:41:23 EDT
