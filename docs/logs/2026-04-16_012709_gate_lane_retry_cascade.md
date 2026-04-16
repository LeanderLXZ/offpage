# 提交门控级联恢复（Gate Cascade for Lane-Independent Recovery）

**日期**：2026-04-16
**范围**：Phase 3 提取流水线 — 提交门控失败处理与 lane 独立重试的统一

## 起因

Phase 3 之前的失败处理在审校通道（review lanes）层面已经做到 lane 独立重试，
但提交门控（commit gate）一旦报错只有一条出路：**直接全 stage rollback + 整阶段重试**。
门控的检查项其实多数都能落到具体某条 lane 的产物上：

- `world/stage_snapshots/{stage}.json` 或 `characters/{cid}/canon/stage_snapshots/{stage}.json` 缺失或 `stage_id` 错位
- 程序化维护的 `stage_catalog.json` / `memory_digest.jsonl` 没有当前 stage 条目

这两类问题里：

- **catalog/digest 缺失** 完全可以靠 `post_processing` 的幂等 upsert 0-token 重新生成；
- **snapshot 缺失/错位** 才真正需要重新调 LLM 重抽该 lane。

让门控在 PASS 之前先执行同一套"lane 独立重试 → 全量回滚为最后手段"的级联，
能省下大量不必要的全 stage rerun（=N+1 次 LLM 调用 + 一轮再审校）。

## 变更

### 1. `automation/persona_extraction/review_lanes.py`

新增 `GateIssue` dataclass，将 gate 输出从 `list[str]` 升级为可路由的结构化对象：

```python
@dataclass
class GateIssue:
    message: str
    severity: str             # "error" | "warning"
    lane_type: str = ""       # "world" | "character" | ""
    lane_id: str = ""         # "world" | char_id | ""
    category: str = ""        # snapshot_missing / snapshot_stage_id /
                              # snapshot_parse / catalog_missing /
                              # digest_missing / lane_review /
                              # reference_warning
```

新增免费可恢复类目集合：

```python
POST_PROCESSING_RECOVERABLE: frozenset[str] = frozenset({
    "catalog_missing",
    "digest_missing",
})
```

`run_commit_gate` 返回值改为 `tuple[bool, list[GateIssue]]`，内部所有检查
（lane review 失败、snapshot 缺失、snapshot stage_id 错位、snapshot JSON
解析失败、catalog 缺条目、digest 为空/缺条目、跨实体引用警告）都附带
`lane_type` / `lane_id` / `category` 标签。`stage_id` 解析失败这种没有
明确归属的结构性错误保留 `lane_type=""`，让上层走全量回滚。

`_validate_catalog_has_stage` / `_validate_digest_has_stage` 改为接受
`label`、`lane_type`、`lane_id` 关键字参数并产出 `GateIssue`。

### 2. `automation/persona_extraction/orchestrator.py`

- 引入 `POST_PROCESSING_RECOVERABLE` 与 `GateIssue`。
- `_process_stage` 的 REVIEWING 块改成**外层 review+gate 循环**：
  1. 内层并行审校 lane 重试（语义沿用原状）→ 全部 PASS 后跳出内层。
  2. 外层运行 commit gate。
     - **gate PASS** → 跳出外层。
     - **有无归属问题（unattributed structural）** → 立刻全 stage rollback + FAILED + return。
     - **全部问题 ∈ POST_PROCESSING_RECOVERABLE** → 调用 `_rerun_post_processing()`（免费）→ 重新过门控；再失败时按下面的 lane 路径继续。
     - **按 lane 分组**剩余问题，配额来自 `stage.lane_retries`（与审校失败共享）：
       - 任一 lane 配额耗尽 → 全 stage rollback + FAILED + return。
       - 否则对每条 lane 自增计数 → `rollback_lane_files` 仅清该 lane 的快照/timeline → 在并行线程池里重抽这些 lane → `_rerun_post_processing()`。
     - 回到外层 while 顶部，重新跑全部 review lane + gate（满足"任何一条 lane 改动会让别的 lane 已 PASS 的判定失效"这一耦合）。
- `stage.lane_retries = {}` 的清零**从内层成功后移到外层 PASS 之后**。
  这样 review/gate 共享同一份配额，避免同 stage 内反复消耗。
- 抽出三个本地闭包消除重复：`_rerun_post_processing`、
  `_re_extract_and_post_process`（兼容失败时自完成 rollback + return False
  的语义）、`_full_rollback_and_fail`。

### 3. 文档对齐

- `docs/requirements.md §11.4b 失败处理 B`：新增 lane-attributed gate 路由表，
  列明每个 category 的恢复路径。
- `docs/architecture/extraction_workflow.md`：流程图把"提交门控"展开成
  PASS / catalog-digest miss / snapshot-lane_review miss / 无法定位 四个分支；
  关键设计决策段补 Gate Cascade 说明。
- `automation/README.md`：失败分级清单加上 gate 路由细则。
- `ai_context/{architecture,current_status,decisions,requirements}.md`：
  同步更新 commit gate 行为与共享配额的描述。
- `automation/persona_extraction/progress.py`：`lane_retries` 字段注释
  说明它现在跨 review / gate 共享并在 gate PASS 之后才清零。

## 测试

新增 `/tmp/test_gate_cascade.py`（无副作用、不调用 LLM、不接触 git），
覆盖 6 项断言：

- `POST_PROCESSING_RECOVERABLE` 仅包含 `catalog_missing` / `digest_missing`，
  其他 category 不在其中（防止把需要 LLM 的问题错判成免费可恢复）。
- 完整 fixture 通过 gate（baseline 健全性）。
- 删掉世界 snapshot → 输出 `lane_type=world, category=snapshot_missing` 的
  `GateIssue`，且类目不在 PP_RECOVERABLE 中。
- 把某角色的 catalog 抹掉 → 该 lane 单独命中 `catalog_missing`，且全部
  错误都属于 PP_RECOVERABLE，触发免费恢复路径。
- lane review FAIL 通过 `lane_results` 进入 gate，输出
  `category=lane_review` + 对应 lane 归属。
- `GateIssue.lane_key_str` 的规范化（`character:甲`、`world`、空串）。

同步重跑了原先的 `/tmp/test_phase3_lane_retry.py`（rollback_lane_files
隔离 / run_parallel_review 单 lane FAIL / lane_filter 重放语义），所有 4
项仍通过。

## 设计取舍

- **为什么 PP rerun 只在"全部问题都 PP-recoverable"时触发？**
  混合场景（既有 PP 可修又有 snapshot 缺失）下，单跑 PP 不会修好 snapshot
  缺失项；与其先免费跑一次 PP 再去 lane 重抽，不如直接走 lane 重抽路径
  ——重抽完后 PP 也会自动跑一次，覆盖了同样的 PP 修复语义，且代码路径只有一条。
- **共享配额而不是新开 gate 配额**：gate 在 review 之后跑，二者改动的产物完全一样
  （快照、timeline → 派生 catalog/digest）。如果给 gate 单独配额，
  会出现"review 跑光配额还要再给 gate 三次机会"的不直观行为；
  共享后 `lane_max_retries=2` 是该 lane 在本 stage 内的总改动上限。
- **`lane_retries` 清零时机后移**：原先在"review 全 PASS"之后立刻清零，
  会让接下来的 gate 失败重新拿到满配额再进 review、再 PASS、再 gate ……
  形成 ping-pong。改到 gate PASS 之后才清，把整轮 review+gate 视作一个事务。
- **保留全量回滚兜底**：unattributed 类目（`stage_id` 解析失败这类）仍直接
  全量回滚 — 这类问题往往出在 Phase 1 的 `stage_plan.json` 或 progress
  状态本身，单 lane 重抽不会修好。

## 影响

- 配额上限不变（`lane_max_retries=2`、`max_retries=2`），但能在配额内
  消化更多类型的失败。
- 进度日志多出 `[GATE] [lane_key/category] message` 与可能的
  `Commit gate (round N)` / `PASS (after PP rerun)` / `FAIL — re-extracting K lane(s)` 提示。
- 进度文件结构未变更：`lane_retries` 仍是 `{lane_key: count}`，仅清零时机后移。
- 无 schema 变更、无 prompt 变更、无 git 流程变更。

## 后续

无 follow-up TODO；待第一份真实素材跑完 Phase 3 后观察 gate 路径触发频次，
若 `catalog_missing` / `digest_missing` 极少出现，可考虑把"先 PP 再 gate"
改成"先 gate 再 PP"以减小一次 gate 调用，但目前为可读性优先保持显式两步。
