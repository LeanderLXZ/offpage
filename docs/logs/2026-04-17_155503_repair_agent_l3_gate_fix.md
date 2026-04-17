# Repair Agent — Phase B L3 Gate + T3 Per-File Global Cap

**日期**：2026-04-17 (America/New_York 时区)
**分支**：master（worktree 在 `/tmp/persona-engine-repair-l3gate`）
**目标**：修复 repair agent 的语义层修复反馈漏洞；引入 T3 全局每文件上限

---

## 背景：Stage 02 失败根因

Stage 02 在 Phase 3 提取后走 repair agent，最终 FAIL 停机。从
`extraction.log` 观察到的序列：

```
Phase A 语义审校 → 3 个 L3 error
Phase B 修复循环：
  T1 ×3 尝试 → 未解决 → 升级 T2
  T2 ×3 尝试 → 未解决 → 升级 T3
  T3 ×1 整文件重写（8m33s）→ claim "resolved all 3"
  → Round 1 结束：resolved=3, persisting=0
  → Phase B 退出
Phase C 最终语义复核 → 发现 **同样的 3 个语义 error 仍然存在**
→ 判 FAIL
```

**根因**：Phase B 的 scoped recheck 只跑 L0–L2（`max_layer=2`），不复跑
L3。T3（以及 T1/T2）返回 `FixResult` 把所有尝试过的 fingerprint 加进
`resolved_fingerprints`，Phase B 以此认定 "问题已修"，实际语义层 LLM
一看并没有修。Phase C 只能读结果不能再触发修复，所以一旦到这里就
注定 FAIL。

**影响范围**：任何 T1/T2/T3 "谎报语义修复成功" 的场景都会让 Phase B
假性收敛，消耗 LLM 预算走一遍 T3 却最终 FAIL。

---

## 设计：L3 gate 内嵌 Phase B + T3 全局每文件上限

### 核心思想

修复时机前移——在 Phase B 的每一轮末、L0–L2 scoped recheck 之后，**对
"本轮被修改过 + Phase A 有过语义问题" 的文件跑一次 L3**，把 gate 返回
的新 issue 回灌进下一轮 issue 队列。这样 T3 的谎报在下一轮就会被修复
循环重新处理，而不是拖到 Phase C 才发现。

### 两条止损线

1. **T3 全局每文件上限 `t3_max_per_file=1`**：整个 repair 流程中，一个
   文件最多触发一次 T3（跨所有轮次，不是每轮一次）。用尽后该文件若
   gate 还报错也不再升 T3——因为整文件 LLM 重写又贵又容易把其他字段
   改坏，二次重写基本不会带来收益。
2. **L3 gate 反复**：连续两轮 gate 返回的 blocking 指纹集合完全相同
   → 语义层不收敛（修复动作没有改变 LLM 审校结果），直接 break 进入
   Phase C 出报告。

### Phase C 简化

有了 Phase B 的 gate，Phase C 不再需要独立触发 L3：
- **有 gate 跑过**：直接复用最后一次 gate 的结果（0 新增 LLM）
- **Phase A 有语义问题但 gate 从没跑过**（例如修复循环在还没改到 L3
  文件时就退出了）：兜底跑一次 L3

---

## 代码变更

### `automation/repair_agent/protocol.py`
```python
@dataclass
class RetryPolicy:
    t0_max: int = 1
    t1_max: int = 3
    t2_max: int = 3
    t3_max: int = 1
    t3_max_per_file: int = 1   # NEW — global cap per file
    max_total_rounds: int = 5

@dataclass
class RepairConfig:
    max_rounds: int = 5
    block_on: Literal["error", "all"] = "error"
    run_semantic: bool = True
    l3_gate_enabled: bool = True   # NEW
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
```

### `automation/repair_agent/checkers/__init__.py`
新增 `run_layer(files, layer, **kwargs)`——只跑指定层、绕过"前层有 error
就跳过"的保护，给 Phase B L3 gate 用。

### `automation/repair_agent/tracker.py`
- `_tier_uses_per_file: dict[str, dict[int, int]]` +
  `record_tier_use_on_file(file, tier)` / `tier_uses_on_file(file, tier)`
  → 支持 T3 全局每文件上限执行。
- `_l3_gate_history: list[set[str]]` + `record_l3_gate(fps)` /
  `is_l3_gate_reemerge()` → 检测两轮 gate 返回的 blocking fingerprint
  集合是否相同（且非空）。

### `automation/repair_agent/coordinator.py`
- Phase A 后额外计算 `l3_file_set = {file: 有过 L3 issue}`
- Phase B 每轮：
  1. 先运行 T0/T1/T2/T3 升级链；
  2. `_run_fixer_with_escalation` 返回 `set[file_path]` 本轮被改过的
     文件（之前返回 `bool`）；
  3. 到 tier 3 时，先按 `tracker.tier_uses_on_file(file, 3)` 过滤掉已经
     用尽 T3 配额的文件；T3 成功写入后为涉及文件 `record_tier_use_on_file`；
  4. L0–L2 scoped recheck；
  5. 若 `l3_file_set & modified_files_this_round` 非空 → `pipeline.run_layer(..., layer=3)`
     对这个子集跑 L3 gate；
  6. `tracker.record_l3_gate(blocking_fps)`；
  7. gate 发现的 blocking issue 与 L0–L2 recheck blocking 合并，成为下一轮的
     `current_issues`；
  8. 追加一条新安全阀：`tracker.is_l3_gate_reemerge()` → break。
- Phase C：不再无条件调 L3，优先复用最后一次 gate 的 blocking 集合；
  只有 `had_semantic=True` 且 `gate_ever_ran=False` 时才兜底跑一次 L3。

### `automation/repair_agent/_smoke_l3_gate.py`（新文件）
最小功能测试：stub LLM 模拟 T1/T2 不会产生 patch、L3 审校一直报同一个
error。验证：
1. 总 semantic 调用 ≥ 2（Phase A + 至少一次 gate）
2. T3 最多 1 次（全局上限）
3. 最终 `passed=False`

运行：`python -m automation.repair_agent._smoke_l3_gate`

---

## 文档对齐

- `docs/requirements.md` §11.4.4：T3 行增加 "全局每文件最多触发 1 次"；
  `RetryPolicy` dataclass 增加 `t3_max_per_file: int = 1` 并补文字说明。
- `docs/requirements.md` §11.4.5：重写三阶段流程——新增 Phase B L3 gate
  描述、gate 触发条件、失败后升级链、修正 LLM 预算公式（Phase A: N 次；
  Phase B: 最多 M × R 次；Phase C: 0 次新增，有兜底）。
- `docs/requirements.md` §11.4.6：在安全阀里增加 "L3 gate 反复" 和
  "T3 全局配额" 两条。
- `docs/architecture/extraction_workflow.md`：同步修复流程图 + 文字说明。
- `ai_context/architecture.md`、`ai_context/requirements.md`、
  `ai_context/decisions.md`、`ai_context/current_status.md`：
  各补短说明，指向 requirements.md 的权威章节。
- `automation/README.md`：更新 T3 行说明（加全局上限）、三阶段文字。

---

## 兼容性

- `RepairConfig` 和 `RetryPolicy` 新增字段都有默认值 → 现有调用方
  （`orchestrator.py:1437` 等）无需改动即享受新行为。
- `CheckerPipeline.run_scoped()` 和 `run()` 签名不变；新增
  `run_layer()` 向下兼容。
- `_run_fixer_with_escalation` 从 `bool` 改为返回 `set[str]`——是私有
  辅助函数（单下划线前缀、仅被 `run()` 调用），单点调用已同步更新。

---

## 未来讨论（本次不做）

用户先前提出的 `source_discrepancies` / `auto_accepted_with_note` 概念
在本次修复中**未实现**——先把 "Phase B 假性收敛" 这个客观漏洞补上，
再讨论该不该给 repair agent 一个"接受带标记"的出口。相关决策记录
留待下一次会话。

---

## 合并路径

- 本次变更在 worktree `/tmp/persona-engine-repair-l3gate`（基于 `master` HEAD
  `1e29331`）完成。
- master 提交后，需要合并到 extraction 分支
  `extraction/我和女帝的九世孽缘` 才能让中断的 Stage 02 重跑时拿到
  新行为。**主仓工作区现有 14 个脏文件（Stage 02 产物）**，merge 时
  需要先 stash 或借助工作流检查点保护。
- 合并建议：`git checkout extraction/...` → `git stash` →
  `git merge master` → `git stash pop` → 解决冲突（若有，多半无冲突
  因为本次只动 automation/repair_agent 和文档）→ 再 `--resume`。
