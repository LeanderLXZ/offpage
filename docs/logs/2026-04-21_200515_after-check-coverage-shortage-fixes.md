# 2026-04-21 20:05 EDT — coverage_shortage /after-check 回补

## 起因

`/after-check` 复审 `068fad4 / 993c281` 两个 commit（L2 coverage_shortage
程序化 accept_with_notes 通路）发现一处高危 bug、一处文档误引函数名、
一处 smoke 断言注释过期、一处 schema_reference 字段名对齐漂移，以及缺一条
coverage_shortage 端到端 smoke。H2（SourceNote.stage_id 格式预埋位）按用户
指示另行讨论，此轮不动。

## 改动概要

### H1 — Phase B recheck + Phase C 过滤已接受的 coverage_shortage 指纹

`automation/repair_agent/coordinator.py`：Phase B 每轮 scoped recheck（L0–L2）
与 Phase C 最终 `pipeline.run(... max_layer=2, run_semantic=False)`
都会重新发现已 accept 的 coverage_shortage issue —— 因为 SourceNote 是
sidecar，原 JSON 从未被修改。此前这些 warning 会被 `_filter_blocking`
再次判定为 blocking，让 stage 在成功接收的情况下仍然 FAIL。

修复：在两处 recheck 之后都减去 `{n.issue_fingerprint for n in
accepted_notes}` 之后再进入 `_filter_blocking`。`Issue.fingerprint =
f"{file}::{json_path}::{rule}"` 与结构检查器重新生成的 Issue 逐字一致，
过滤是确定性的。

### M1 — `build_coverage_shortage_note` → `build_coverage_shortage_verdict`

- `automation/repair_agent/protocol.py:190` `is_coverage_shortage` 文档段
- `automation/repair_agent/triage.py:216` `build_source_note` 文档段
- `docs/requirements.md:1823` §11.4.7 描述

实际函数已在 `068fad4` 之后改名为 `_verdict`（先构造
`TriageVerdict`，再经 `build_source_note` 转成 `SourceNote`），但三处
遗留文档仍引用旧名。

### L1 — scenario_d 文档段描述与新 schema 对齐

`automation/repair_agent/_smoke_triage.py:268-280`：旧注释说"schema 硬限
`issue_category=semantic`"。扩展 coverage_shortage 后 schema 枚举已经允许
`semantic | structural`，实际的"非语义类 issue 拒绝进 LLM triage" 由
`_run_triage_round` 顶部的 `category == "semantic"` 过滤保证。改写为
实际分层描述。

### Alignment — `docs/architecture/schema_reference.md`

SourceNote 关键字段列表里 `file_path` / `verbatim_quote` 是 commit `8e6a870`
之前的旧名；当前 schema 是 `file` / `source_evidence.quote`。同步纠正，
并把 chapter/line_range/quote 明确挂在 `source_evidence.*` 下。

### 新增 scenario_f — coverage_shortage 端到端 smoke

`_smoke_triage.py`：新场景驱动 coordinator 全流程，主角字段 1 条 example、
阈值 5。T2 stub 返回 `"not valid json"` 让 JSONDecodeError 分支 continue、
不写入 `[]` 抢跑。断言：

- `result.passed is True`（若 H1 回归 → FAIL）
- 1 条 SourceNote 写盘，`discrepancy_type="coverage_shortage"`、
  `issue_category="structural"`、`extraction_choice="keep_current_count"`
- triage LLM 调用 = 0（0-token 路径）
- T3 regen 调用 = 0（coverage_shortage 不升级到 T3）

## 未动

- H2 SourceNote.stage_id 预留格式：按用户指示另行讨论，本轮不动
- 代码 / schema / prompt / ai_context / docs 与本次 finding 无关的部分：
  不做顺带清理
- extraction 分支的 Phase 2.5 残留产物：保留（是上一轮 rollback 的结果）

## 校验

- `python -c "from automation.repair_agent import coordinator, triage,
  protocol, _smoke_triage, _smoke_l3_gate"`：imports OK
- `python -m automation.repair_agent._smoke_triage`：6/6 scenarios pass
  （含新 scenario_f）
- `python -m automation.repair_agent._smoke_l3_gate`：PASS（FAIL-as-expected
  预期路径）
- `jsonschema.Draft7Validator.check_schema(source_note.schema.json)`：valid

## 预期效果

- 凡是 L2 min_examples 在 T2 单次尝试后仍不达标的 stage，走完 0-token
  SourceNote 之后，Phase B 下一轮 recheck 与 Phase C 最终验证都不会再
  把该 fingerprint 视为 blocking，stage 能真正 PASS
- scenario_f 作为回归护栏，未来若有人改了 Phase C 验证逻辑但忘了维护
  过滤规则，smoke 会立刻失败
