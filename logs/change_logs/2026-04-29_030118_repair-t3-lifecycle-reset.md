# repair-t3-lifecycle-reset

- **Started**: 2026-04-29 03:01:18 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

`/todo` 拉出 `T-REPAIR-T3-LIFECYCLE-RESET`（🔴 High / ✅ Ready / Medium / 依赖无）。代码 grep 验证仍为旧机制：

- `automation/repair_agent/protocol.py:65` `t3_max_per_file = 1`
- `automation/config.toml:102` `t3_max_per_file = 1`
- `automation/repair_agent/coordinator.py` 仍 `T3_CORRUPTED` 路径（L18 / L246 / L365 / L599 / L839）
- 计划新名 `max_lifecycles_per_file` / `_run_one_lifecycle` / `prior_attempt_context` / `T3_EXHAUSTED` 全部 0 命中

todo 条目 `discussion 已收敛 / 待决策项=0`，可直接 /go 落地。

## 结论与决策

**新语义**：单文件最多走 2 个完整 lifecycle。

- **第 1 轮 lifecycle**：T0/T1/T2 跑完仍残留 → 触发 T3。**T3 prompt 携带 `prior_attempt_context`**（已修+未修两类 issue 摘要，~200 token），LLM 重生成。T3 跑完后**不做 Post-T3 scoped 检查**，**不走第 1 轮 L3 gate / Phase C**，状态机完整重置 → 进入第 2 轮
- **第 2 轮 lifecycle**：全新 Phase A→B→C，**禁用 T3**。Phase A 重扫的 issue 走 T0/T1/T2（同第 1 轮 retry 上限）。任何升到 T3 的 issue 立即 `T3_EXHAUSTED` 退出
- **第 2 轮 T3 分支**：先跑 Pre-T3 triage（triage 可全 accept），triage 后仍残留才 `T3_EXHAUSTED`
- **Triage cap**：两轮独立各 5 条（`notes_per_file` 内存计数器跨轮重置）；磁盘 `extraction_notes/{stage_id}.jsonl` append-only 累积；第 2 轮 lifecycle 启动前从磁盘读已 accept 的 fingerprint 集合，Phase A blocking 中过滤掉这些 fingerprint 避免同 issue 在 jsonl 写两条
- **状态机重置**：tracker / accepted_notes 局部 / notes_per_file / l3_file_set / gate state / prev_report 全新；磁盘文件保留（第 1 轮 T3 写出的内容是第 2 轮的输入）
- **RepairRecorder**：JSONL 跨轮保留同一份；事件加 `cycle=0/1` 字段（用 0-based 索引；report/log 文本里说 "lifecycle 1/2"）
- **删除 `T3_CORRUPTED`**：移除该状态、`t3_corrupted` 局部变量、Post-T3 scoped check、`FAIL_T3_CORRUPTED` 终止路径、`_build_report` 的 `t3_corrupted` 分支
- **新终止 `T3_EXHAUSTED`**：仅在第 2 轮升 T3 且 Pre-T3 triage 后仍残留时触发；最终 RepairResult.passed=False
- **`accepted_notes` final**：跨轮累计。第 1 轮 pre-T3 triage 接受的条目已写盘 + 加入 final list；第 2 轮接受的条目同样累积。RepairResult.accepted_notes 是两轮并集
- **rate_limit / `--resume` 兼容**：rate_limit 由 LLM call 层处理，repair_agent 不感知；硬停 exit 2 + `--resume` 触发 lane 重跑，`max_lifecycles_per_file` 预算跟着 lane 重置（lane-level resume 的固有行为）

## 计划动作清单

### Code

1. **`automation/repair_agent/protocol.py`**
   - `RetryPolicy.t3_max_per_file: int = 1` → 删除
   - 新增 `RepairConfig.max_lifecycles_per_file: int = 2`（独立字段，不在 RetryPolicy 内；命名上 lifecycle 是协调层概念）
2. **`automation/persona_extraction/config.py:77`**
   - `RepairAgentConfig.t3_max_per_file: int = 1` → `max_lifecycles_per_file: int = 2`
3. **`automation/config.toml:100-102`**
   - 段落注释 + 字段名同步：`t3_max_per_file = 1` → `max_lifecycles_per_file = 2`
4. **`automation/persona_extraction/orchestrator.py:1794-1807`**
   - `_repair_cfg()` 把 `t3_max_per_file=ra_cfg.t3_max_per_file` 改为 `max_lifecycles_per_file=ra_cfg.max_lifecycles_per_file`（提到 RepairConfig 顶层）
5. **`automation/repair_agent/coordinator.py`** （核心重构）
   - 模块 docstring 改写：移除 `T3_CORRUPTED` 段落，加 lifecycle 描述
   - 抽 `_run_one_lifecycle(cycle, *, files, config, source_context, pipeline, retriever, fixers, tracker, triager, notes_writer, accepted_notes, notes_per_file, recorder, t3_disabled, prior_attempt_context, importance_map) -> tuple[terminated_by, lifecycle_state]` 包住 Phase A→B→C
     - terminated_by 取值：`"PASS"` / `"FAIL"` / `"T3_TRIGGERED"`（第 1 轮）/ `"T3_EXHAUSTED"`（第 2 轮）
     - lifecycle_state 包含 final_issues / final_blocking / had_semantic / l3_gate_results / round_count / resolved_summary / remaining_summary（后两者用于喂第 2 轮 prior_attempt_context）
   - 外层 `run()` 改造：
     - 实例化 notes_writer 一次（跨轮共享，序列号续接）
     - 实例化 recorder 一次（已经是外部传入；只是把 cycle 字段加进 emit）
     - 累计 `accepted_notes_total: list[SourceNote] = []`
     - For `cycle in range(config.max_lifecycles_per_file)`:
       * 每轮重新建 fresh tracker / fresh notes_per_file / fresh local accepted_notes / fresh l3_file_set / fresh prev_report
       * cycle==1 时：从磁盘 `extraction_notes/{stage_id}.jsonl` 读已 accept fingerprint 集合 → Phase A blocking 中过滤
       * 调 `_run_one_lifecycle(cycle=cycle, t3_disabled=(cycle>=1), prior_attempt_context=...)`
       * accepted_notes_total 累加本轮 accepted
       * cycle==0 且 terminated_by="T3_TRIGGERED" → 准备 prior_attempt_context（resolved_summary + remaining_summary 总长 ~200 token），continue
       * 否则（PASS / FAIL / T3_EXHAUSTED 或 cycle==1 自然结束）→ break
     - 最终构造 RepairResult；`_build_report` 不再有 t3_corrupted 分支
   - `_run_fixer_with_escalation` 改造：
     - 删 `t3_corrupted` 局部、删 Post-T3 scoped L0–L2 check 块（L588-604）、删 `t3_self_report` 中专为 corruption 路径的处理（保留 self_report dict 用于 post-gate triage）
     - 函数签名加 `t3_disabled: bool, prior_attempt_context: dict | None`、返回值改成 `tuple[set[str], dict[str, TriageVerdict], str]` —— 第 3 项是 lifecycle-level signal：`""` / `"T3_TRIGGERED"` / `"T3_EXHAUSTED"`
     - tier==3 分支：
       - 若 `t3_disabled`：跑 Pre-T3 triage；residual 空 → 正常 break；否则返回 `terminated="T3_EXHAUSTED"` 立即出
       - 否则：原有 Pre-T3 triage 流程；residual 非空且 t3_cap 内可执行 → 调 fixer.fix(prior_attempt_context=…)；T3 调用完成（无论 resolved 多少）即返回 `terminated="T3_TRIGGERED"`，让外层 lifecycle 收尾、下一轮重启
     - 删除 `t3_cap = config.retry_policy.t3_max_per_file` + 相关过滤（lifecycle 数即上限，不再需要 per-issue T3 计数）
     - tracker.record_tier_use_on_file / tracker.tier_uses_on_file 仍保留（其他 tier 也在用），只是不被 t3_max_per_file gate 读
   - 外层 lifecycle 收到 `T3_TRIGGERED` 后：
     - 不跑当前轮的 scoped recheck、不跑当前轮 L3 gate、不进 Phase C
     - 立即返回，把 lifecycle_state 中 resolved_summary / remaining_summary 从 tracker.history + current_issues 现场提取
6. **`automation/repair_agent/fixers/file_regen.py`**
   - `FileRegenFixer.fix()` 签名加 `prior_attempt_context: dict | None = None`（在 attempt_num/max_attempts 后）
   - `_build_prompt` 签名同步加 `prior_attempt_context`，存在则在 `--- ISSUES TO FIX ---` 段下方加一段 `--- PRIOR ATTEMPT CONTEXT (lifecycle 1) ---` 注入：列已修指纹（resolved）+ 未修指纹（remaining）+ 简短 message 摘要；总字符数硬截断到 ~600 char（≈ 200 token 中文）
7. **`automation/repair_agent/notes_writer.py`**
   - 加 `load_existing_fingerprints(file_path: str, stage_id: str) -> set[str]` 方法：从磁盘 `extraction_notes/{stage_id}.jsonl` 读出 `issue_fingerprint` 集合；用于 lifecycle 2 启动前过滤 Phase A
8. **`automation/repair_agent/tracker.py`**
   - 不动（每轮 fresh 实例化即重置）
9. **`automation/repair_agent/recorder.py`**
   - 不动；改 emit 调用方传入 `cycle=` 即可

### Smoke harness

10. 更新 `automation/repair_agent/_smoke_l3_gate.py`：原本测 T3 per-file cap，现在改测：
    - (a) 单 lifecycle 内 PASS（短路）
    - (b) 第 1 轮 T3 触发 → 第 2 轮 PASS
    - (c) 第 1 轮 T3 触发 → 第 2 轮 T1/T2 修不好升 T3 → `T3_EXHAUSTED`
    - (d) 第 1 轮 pre-T3 triage 全 accept → 不进 T3 → 第 1 轮 PASS

### Docs

11. **`automation/config.toml:100-102`** 段注释从"单文件 T3 全局上限"改为"单文件最多走的 lifecycle 数"；`triage` 段注释保持
12. **`ai_context/decisions.md` #25 / #25a**
    - #25 末尾："T3 globally capped `t3_max_per_file=1`" → "Per file at most `max_lifecycles_per_file=2` complete check→fix→verify lifecycles; lifecycle-1 T3 triggers a state-machine reset into lifecycle-2; lifecycle-2 disables T3."
    - #25a 末尾："Post-T3 scoped L0–L2 check aborts with `T3_CORRUPTED` (no triage)." → 删除整句；改为说明 "T3 输出直接进入 lifecycle-2，不再做 corruption 即时门"
13. **`docs/requirements.md` §11.4.4 / §11.4.5 / §11.4.6**
    - §11.4.4 RetryPolicy 代码块同步：删 `t3_max_per_file`；RepairConfig 增 `max_lifecycles_per_file`；段后说明改为 lifecycle 概念
    - §11.4.5 流程图 "阶段 B 第 3 步"（T3 corruption 检查）→ 改为 "T3 跑完不做即时检查；本轮 lifecycle 收尾、状态机重置进入第 2 轮 lifecycle"；新增对 `prior_attempt_context` 注入的说明
    - §11.4.6 安全阀 "T3 corrupted 止损" 整段 → 删除；"T3 全局配额" 改为 "Lifecycle 上限"；新增 `T3_EXHAUSTED` 描述
14. **`docs/architecture/extraction_workflow.md`**
    - L416 / L422 流程图注释 + L466 retry 描述 + L497-499 `T3_CORRUPTED` 段：同口径同步

### Todo

15. **`docs/todo_list.md`**
    - 把 `T-REPAIR-T3-LIFECYCLE-RESET` 整条移到 `docs/todo_list_archived.md` `## Completed`
    - Index Next 4 → 3、Total 10 → 9（删该行）
16. **`docs/todo_list_archived.md`**
    - `## Completed` 顶部追加瘦身条目（完整完成；含 1 行摘要 + 链向本 log）

## 验证标准

- [ ] `python -c "from automation.repair_agent import coordinator, protocol; from automation.repair_agent.fixers.file_regen import FileRegenFixer; from automation.persona_extraction.orchestrator import _llm_call" 2>&1 | grep -i error` 返回空（import 无报错；具体路径按 module 实际接口调）
- [ ] `python -m automation.repair_agent._smoke_l3_gate` 主要场景全过
- [ ] `grep -rn 't3_max_per_file\|T3_CORRUPTED\|t3_corrupted' automation/ docs/ ai_context/ --include='*.py' --include='*.md' --include='*.toml'` 命中均在 `logs/change_logs/` 之外为 0（其它命中只剩本次 log + archived todo log 的历史叙述）
- [ ] `grep -rn 'max_lifecycles_per_file\|T3_EXHAUSTED\|prior_attempt_context\|_run_one_lifecycle' automation/repair_agent/ automation/persona_extraction/ automation/config.toml` 均出现在预期文件
- [ ] `docs/todo_list.md` 正文已无 T-REPAIR-T3-LIFECYCLE-RESET；Index Next 3 / Total 9
- [ ] `docs/todo_list_archived.md` ## Completed 顶部已加该条瘦身记录

## 执行偏差

- 计划项 #10 列了 4 个 smoke 场景（含 "(d) pre-T3 triage 全 accept → 不进 T3 → 第 1 轮 PASS"），实际 `_smoke_l3_gate.py` 只更新到 A/B/C 三个；triage 全 accept 路径已被 `_smoke_triage.py` 的 scenario A 覆盖（pre-T3 accepted, T3 regen calls=0），重复测试无价值，省略。
- 计划项 #15 把 `T-CHAR-SNAPSHOT-T3-REGEN-PATH` 内仍引用 `T-REPAIR-T3-LIFECYCLE-RESET 已定型方案` 的 prose 行（todo_list.md L20 brief / L238 / L282）保留不动——这些引用描述设计假设而非实现状态，被指方案现在已落地，引用语义仍准确。

<!-- POST 阶段填写 -->

## 已落地变更

- `automation/repair_agent/protocol.py`
  - `RetryPolicy.t3_max_per_file` 删除
  - `RepairConfig.max_lifecycles_per_file: int = 2` 新增
  - `accept_cap_per_file` 注释改为 per-lifecycle 语义
- `automation/persona_extraction/config.py:77`
  - `RepairAgentConfig.t3_max_per_file: int = 1` → `max_lifecycles_per_file: int = 2`
- `automation/config.toml:100-102`
  - 字段名 + 段注释同步
- `automation/persona_extraction/orchestrator.py:1794-1808`
  - `_repair_cfg()` 改读 `max_lifecycles_per_file`，提到 RepairConfig 顶层
- `automation/repair_agent/coordinator.py` （核心重构）
  - 模块 docstring 重写：移除 `T3_CORRUPTED` 段；加 lifecycle 描述
  - 引入 `_LifecycleOutcome` dataclass + `_run_one_lifecycle()` 包住 Phase A→B→C
  - `run()` 改为外层 lifecycle 循环：跨轮共享 notes_writer / recorder；每轮 fresh tracker / accepted_notes / notes_per_file；lifecycle 2 启动前从磁盘读已 accept fingerprint 过滤；recorder emit 加 `cycle` 字段
  - `_run_fixer_with_escalation` 改造：返回值第 3 项是 `lifecycle_signal: str`（""/"T3_TRIGGERED"/"T3_EXHAUSTED"）；删 `t3_corrupted` 局部 + Post-T3 scoped check + `t3_cap` 过滤；T3 完成立即 `T3_TRIGGERED` 返回；t3_disabled 路径返回 `T3_EXHAUSTED`
  - `_build_signal_outcome` 把 tracker history + remaining 转 prior_attempt_context 输入
  - `_build_report` 删 `t3_corrupted` 分支；新加 `T3_EXHAUSTED` 分支
- `automation/repair_agent/fixers/file_regen.py`
  - `FileRegenFixer.fix()` 加 `prior_attempt_context: dict | None = None` 参数
  - `_format_prior_attempt_context()` 渲染 resolved+remaining 摘要，硬截断 600 字符（≈200 token 中文）
- `automation/repair_agent/notes_writer.py`
  - 新增 `load_existing_fingerprints(file_path, stage_id) -> set[str]`
- `automation/repair_agent/tracker.py`
  - 注释更新（不再提 `t3_max_per_file` enforcement）
- `automation/repair_agent/_smoke_l3_gate.py`
  - 三场景重写：A 单 lifecycle PASS / B lifecycle 1 T3 → lifecycle 2 PASS / C 持续失败 → T3_EXHAUSTED
  - T1/T2 stub 改返回 malformed JSON 强制 escalation
- `automation/repair_agent/_smoke_triage.py`
  - 5 处 `t3_max_per_file=1` 移除（sed 批量）
  - scenario_c 期望改为 per-lifecycle cap × cycles（cap=2 × 2 lifecycles → ≤4）
- `ai_context/decisions.md` #25 / #25a 同步 lifecycle 概念
- `docs/requirements.md` §11.4.4 RetryPolicy 代码块 + §11.4.5 流程图 + §11.4.6 安全阀 + 末尾 per-file 描述同步
- `docs/architecture/extraction_workflow.md` Phase 3 流程图 + L3 gate 描述 + 「Lifecycle 重置」段（取代 T3_CORRUPTED 硬停）
- `automation/README.md` T3 描述 + accept_cap 描述 + Lifecycle 重置（取代 T3_CORRUPTED 段）
- `docs/todo_list.md` 删除 T-REPAIR-T3-LIFECYCLE-RESET 整条（正文 + Index 行）；Index Next 4→3，Total 10→9
- `docs/todo_list_archived.md` `## Completed` 顶部追加该条瘦身记录

## 与计划的差异

仅"执行偏差"段记录的两点（smoke (d) 略 + todo_list 内交叉引用保留）；其余照计划落地。

## 验证结果

- [x] `python3 -c "from automation.repair_agent ... import _run_one_lifecycle, _LifecycleOutcome ..."` 导入无报错
- [x] `python3 -m automation.repair_agent._smoke_l3_gate` — A/B/C 三场景全过；regen=1, T3_EXHAUSTED 出现在 C 的 report
- [x] `python3 -m automation.repair_agent._smoke_triage` — A/B/C/D/E/F 全过；C 在新 per-lifecycle cap × cycles 范围内（2×2=4 notes）；F coverage_shortage 路径未受影响
- [x] `grep -rn 't3_max_per_file\|T3_CORRUPTED\|t3_corrupted' automation/ docs/ ai_context/ --include='*.py' --include='*.md' --include='*.toml'` 命中均在 `logs/` 与 `todo_list_archived.md` 之外为 0
- [x] `grep -rn 'max_lifecycles_per_file\|T3_EXHAUSTED\|prior_attempt_context\|_run_one_lifecycle\|T3_TRIGGERED' automation/ docs/ ai_context/` 共 66 命中，全在预期文件
- [x] `docs/todo_list.md` 正文 / Index 已无 T-REPAIR-T3-LIFECYCLE-RESET；Index Next 3 / Total 9
- [x] `docs/todo_list_archived.md` ## Completed 顶部已加该条瘦身记录

## Completed

- **Status**: DONE
- **Finished**: 2026-04-29 03:35:10 EDT

<!-- /post-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：16/16 项计划 + 7/7 项验证全过
- Missed updates: 3 条（automation/README.md:32 / :66 + docs/requirements.md:2399 boilerplate 中沿用旧"T3 全局每文件最多 1 次 / T3 全局上限"措辞，未与新 lifecycle 语义同步；详见对话）

### 轨 2 — 影响扩散
- Findings: High=0 / Medium=2 / Low=5
- Open Questions: 0 条（所有 Medium 经手动复核均为"设计意图正确，仅命名/文档清晰度可改进"，无功能性 bug）

## 复查时状态
- **Reviewed**: 2026-04-29 03:47:32 EDT
- **Status**: REVIEWED-PARTIAL
  - 轨 1 主要 16 项落实但 3 条 boilerplate 未同步（Missed Updates）；轨 2 无 High，仅 Medium 设计澄清。下一轮 /go 可吸收 3 条 Missed Updates 即可转 PASS
- **Conversation ref**: 同会话内 /post-check 输出
