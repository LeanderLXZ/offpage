# 2026-04-23 06:26 — /after-check 跟进：PP 重跑前移到 PASSED 之前 + 主流程图措辞修正

## 背景

`/after-check` 对 gpt-5 批次的复审（5 个 commit）发现两处跟进项：

- **[High] crash-window**：`bcd1e4b` 引入的 post-repair PP 重跑**位于
  `stage.transition(PASSED)` 之后**。若 SIGKILL 落在该窗口内，state 被
  写成 PASSED 但 PP 未同步；`--resume` 的 PASSED-resume 分支（
  `orchestrator.py:1401-1424`）直接跳到 Step 5 `commit_stage`，把**未
  同步的** `memory_digest` / `world_event_digest` 提进 extraction 分支。
  正好抵消了 H1+H2 引入 PP 重跑的意图
- **[Medium] 措辞歧义**：`docs/requirements.md` 主流程图第 ④' 行写
  "若 repair 改写了 digest_summary / stage_events，幂等重跑"——读法是
  条件性；同文件 §11.4.5 正文写"无条件再调用一次"。两处冲突

## H1 — PP 重跑前移

### `automation/persona_extraction/orchestrator.py`

原序：
```
if all_pass:
    stage.transition(PASSED)     # crash window 开始
    phase3.save(...)
    # PP 重跑                    # crash window 结束
    ...
```

改后：
```
if all_pass:
    # PP 重跑（state 仍 REVIEWING）
    ...
    if pp2_errors:
        transition REVIEWING → FAILED → ERROR, return
    stage.transition(PASSED)     # 此处状态不变量：repair ∧ PP 都已同步
    phase3.save(...)
```

SIGKILL 落在 PP 重跑途中：state 留 REVIEWING → resume 重入 Step 4 的
`if stage.state == REVIEWING:`，repair 幂等快速通过 + PP 重跑一次。
PASSED-resume 分支再也看不到半同步状态。

`error_message` 前缀从裸 `pp_errors` 改为 `"post-repair PP: " + ...`，
诊断时可与首次 PP 失败区分。

### 状态机

`REVIEWING → FAILED` 已在 `progress.py:341` 允许；`FAILED → ERROR`
已在 `progress.py:344` 允许。不需改转移表。

## M2 — 主流程图措辞改为无条件

### `docs/requirements.md` §11 ASCII 主流程图

原：`若 repair 改写了 digest_summary / stage_events，幂等重跑 post-processing`
改：`无条件幂等重跑 post-processing (0 token)，在 transition(PASSED)
之前执行，刷新 memory_digest / world_event_digest / stage_catalog`

### `docs/requirements.md` §11.4.5 正文

新增"顺序约束"段，明确：PP 重跑**必须在 `transition(PASSED)` 之前**；
`PASSED` 语义严格强化为 "repair 通过 ∧ PP 已同步"；封住 crash window
的推导 + `--resume` 行为；失败路径的 `error_message` 前缀约定。

## 跨文件对齐

- `ai_context/architecture.md` Phase 3 第 4 步描述改写，强调 "before
  the `transition(PASSED)`"、PASSED 状态不变量、crash 语义、
  `REVIEWING → FAILED → ERROR` 迁移链
- `docs/architecture/extraction_workflow.md` Phase 3 ASCII 流程把 PP
  重跑节点前置、在 [PASS + PP 重跑成功] 分支显式 transition(PASSED)

## 验证

- `python -c 'from automation.persona_extraction import orchestrator'`
  + 源码行序断言：`run_stage_post_processing` 出现在 `transition(
  StageState.PASSED)` 之前（pp_idx=526 < pass_idx=548）
- 状态机断言：`REVIEWING → FAILED` 与 `FAILED → ERROR` 转移都在
  `_TRANSITIONS` 中
- 全库 grep "若 repair 改写" / "若.*digest_summary.*幂等" → 无残留

## 受影响文件清单

```
ai_context/architecture.md
automation/persona_extraction/orchestrator.py
docs/architecture/extraction_workflow.md
docs/requirements.md
```
