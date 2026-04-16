# 抽取阶段全 lane 化（Extraction-Side Lane-Attributed Retry）

**日期**：2026-04-16
**范围**：Phase 3 提取流水线 — 把"初次提取 1+N 并行"和"cascade 重抽
helper"两条遗留路径也纳入 lane 独立重试模型

## 起因

上一轮 Gate Cascade（见 `2026-04-16_012709_gate_lane_retry_cascade.md`）
让审校失败和门控失败统一走 lane 配额，但提取流水线里还残留两条**遗留**
的"任一 lane 出错 → 全 stage rollback"路径，是 35515e5 那次重构没清理
干净的角落：

1. `_process_stage` Step 2（初次 1+N 并行 extraction）：任意一条 lane
   的 LLM 调用失败 → `rollback_to_head` + 转 ERROR + 消耗 stage
   `max_retries`。
2. `_re_extract_and_post_process` 闭包：cascade 内部 lane 重抽时如果
   LLM 自身报错 → 全 stage rollback + 转 FAILED + 清空 `lane_retries`。

两者都让一条 lane 的瞬时 LLM 错误（API 5xx、rate limit）作废整个 stage
的进度，违背了 §11.4b "lane-first, full rollback last" 的设计意图。

## 变更

### 1. `automation/persona_extraction/orchestrator.py` — Step 2

把"一次性 1+N 提交 → 任一失败就全 rollback"改成 **per-lane 重试循环**：

```python
pending: list[tuple[str, str]] = [("world", "world")]
pending.extend(("character", c) for c in pipeline.target_characters)
while pending:
    failed_lanes = parallel_submit(pending)
    if not failed_lanes:
        break
    next_pending, exhausted = [], []
    for lt, lid, err in failed_lanes:
        lk = lane_key(lt, lid)
        if stage.lane_retries.get(lk, 0) < stage.lane_max_retries:
            stage.lane_retries[lk] += 1
            rollback_lane_files(...)        # 仅清该 lane 的部分产物
            next_pending.append((lt, lid))
        else:
            exhausted.append((lt, lid, err))
    if exhausted:
        rollback_to_head(...)               # 全 stage rollback 兜底
        stage.transition(StageState.ERROR)
        return
    pending = next_pending
```

要点：
- 已成功 lane 的产物**不再**被 `rollback_to_head` 误伤。
- 失败 lane 与 review/gate 共享同一个 `stage.lane_retries` 配额。
- `error_message` 只记录真正 exhausted 的 lane（不是本轮所有失败 lane）
  ——审计时发现的初版 bug，已修。

### 2. `automation/persona_extraction/orchestrator.py` — `_re_extract_and_post_process`

把"任一 lane LLM 错 → 全 rollback + return False"改成"打 warn + return
None"：

```python
if errors:
    print(f"    [WARN] {len(errors)} lane(s) failed to "
          f"re-extract — leaving outer loop to cascade")
    return
_rerun_post_processing()
```

后果链路：
- 失败 lane 的快照已经被调用前的 `rollback_lane_files` 清掉了。
- post_processing 这轮跳过（避免在缺 snapshot 状态下产生伪 catalog/digest）。
- 外层 `while True:` 循环回到顶部，重新跑 review + gate。
- gate 会针对该 lane 抛 `category=snapshot_missing` 的 `GateIssue`，
  自然走 cascade 的 Tier 2 lane 重抽路径，再消耗一格 `lane_retries`。
- 该 lane 配额耗尽时，cascade 的 `gate_exhausted` 分支才升级到全
  rollback。

两处 caller 的 `if not _re_extract_and_post_process(...): return` 死代码
也一并删除。

### 3. 文档对齐

- `docs/requirements.md` §11.4b：新增 **失败处理 A0**（初次提取 LLM 报错），
  并把"重提取本身 LLM 报错 → 直接全 stage rollback"改成"仅清该 lane +
  下一轮 cascade 兜底"。
- `docs/architecture/extraction_workflow.md`：流程图把 1+N 提取节点展开
  成 `[全部成功] / [部分 lane 失败] / [失败 lane 配额耗尽]` 三个分支；
  关键设计决策段补"extraction/review/gate 三处共享配额"。
- `automation/README.md`：失败分级清单加"初次提取 lane LLM 报错"和
  "lane 重提取自身 LLM 报错"两条路径。
- `ai_context/{architecture,current_status,decisions,requirements}.md`：
  全部更新成"三路径共享 `lane_retries` 配额"的描述；`decisions.md` 新增
  25c.1 条目专门描述 Step 2 lane-attributed 模型。
- `automation/persona_extraction/progress.py`：`lane_retries` 字段注释
  从"两路径共享"改成"三路径共享 (initial extraction / review / gate)"。

## 测试

新增 `/tmp/test_extraction_lane_retry.py`，5 项断言（无 LLM、无 git、
纯算法逻辑复现）：

- T1：Step 2 部分失败时，只重跑失败 lane，已成功 lane 产物保留。
- T2：Step 2 lane 配额耗尽 → 触发全 rollback 回调（共 3 次尝试 = round 1
  + 2 次 retry）。
- T3：Step 2 world 单独失败时，只消耗 world 的配额，character lane 不
  受影响。
- T4：`_re_extract_and_post_process` 部分 LLM 错时不再触发全 rollback。
- T5：`_re_extract_and_post_process` 全部成功时返回干净结果。

回归：原有 `/tmp/test_phase3_lane_retry.py` (4 项) + `/tmp/test_gate_cascade.py`
(6 项) 全部仍通过，共 15 项断言全绿。

## 设计取舍

- **为什么不在 Step 2 全失败时也走 cascade**？
  Step 2 是 stage 启动后第一次产生数据；如果整个 1+N 全失败、又没耗尽
  配额，下一轮 retry 仍然在 Step 2 内重抽。直到配额耗尽才把 stage 推
  到 ERROR 由 stage-level retry 介入。这与 cascade 把 gate 失败留在
  外层循环的语义一致：lane 内部能解决就别升级。

- **为什么 `_re_extract_and_post_process` 出错时跳过 `_rerun_post_processing`**？
  在缺 snapshot 的状态下跑 post_processing 会产生不完整的 catalog/digest。
  下一轮 cascade 的 Tier 2 lane 重抽完成后会再次触发 post_processing，
  幂等 upsert 会修正，所以这里跳过更安全也更简单。

- **error_message 只记 exhausted 的原因**：
  exhausted 的 lane 是真正"我已经放弃"的；retriable lane 在本轮提交了
  retry，未来仍可能成功。把 retriable 的错误也写进 `error_message`
  会让 stage-level retry 的人误以为所有列出的 lane 都已永久失败。

- **配额上限不变**：`lane_max_retries=2`、`max_retries=2`。一条 lane
  在整个 stage 生命周期里最多 3 次提取尝试（初次 + 2 retry），无论这
  3 次发生在 Step 2、cascade 还是混合场景。

## 影响

- 无 schema 变更、无 prompt 变更、无 git 流程变更、无 progress 文件
  字段变更（`lane_retries` 仍是 `{lane_key: count}`）。
- 进度日志多出 `[RETRY] Extraction round N for K lane(s): [...]` 与
  `[FAIL] Extraction lane retry exhausted for ...` 两类提示。
- 共同效果：把"瞬时 API 故障让全 stage 重跑 N+1 次 LLM"的浪费降到
  "瞬时 API 故障只让一条 lane 重抽 1 次"。

## 后续

无 follow-up TODO；首份真实素材跑 Phase 3 后观察 Step 2 retry 触发
频次，若极少触发可考虑把 round-2/3 的并发度调成 1（节省冷启动）。
