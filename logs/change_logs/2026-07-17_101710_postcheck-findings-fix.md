# postcheck-findings-fix

- **Started**: 2026-07-17 10:17:10 EDT
- **Branch**: main
- **Type**: GO
- **Status**: PRE

## Background / Trigger

上游链条：`T-EFFORT-TIER-TUNING /go`（commit `2a7d68f`）→ `/post-check`
（复审回写 commit `80e0698`，status **REVIEWED-PARTIAL**）→ `/fix` 分诊
（Auto 模式，路径 `/go`）→ 本轮。

`/post-check` 双轨审计结论：Track 1 达成 17/17 计划项 + 9/9 验证项（提速
实测按 PRE 声明延后到挂机跑）；Track 2 出 High=0 / Medium=7 / Low=5 / OQ=2。
**所有 finding 都不是代码行为缺陷**——`2a7d68f` 的接线本身正确（三个 shard
独立核对通过）。问题集中在**描述代码的文字**：6 处失准，其中 4 处是
`2a7d68f` 亲手引入的。

`/fix` 分诊结果（用户 2026-07-17 拍板）：

- **fix（7）**：M1 / M2 / M5 / M6 / M7 / L1 / L2
- **OQ1 = Adopt 候选 A**：Phase C fallback L3 传 `effort="medium"`
  —— **这同时解决 M3**（两者同一件事；M3 原推荐 todo，经 OQ1 采纳进入本轮）
- **OQ2 = Adopt 候选 A**：删除 config / dataclass 注释里的沿革句
  —— 与 M6 同一处置，不重复计
- **dropped（Auto 模式丢弃，未登记 todo）**：M4 / L3 / L4 / L5

**一条贯穿性观察（来自 `/post-check`）**：`2a7d68f` 的 PRE 把验收判据设成
**字面量 grep**（`1200` / `claude-opus-4-7`），对**语义等价物**结构性失明
—— M1 的旧值以中文口径「20 分钟」存在（= 1200s），M5 的失效条件以概念而非
字面量存在。本轮验证判据须避免重蹈。

## Conclusion and decisions

`/fix` 交接的 anti-over-engineering 契约**逐字生效**：

> Anti-over-engineering reminder: post-review fixes — minimal patches only.
> No opportunistic refactor / "while I'm here" cleanup / new abstractions /
> new tests / new flags. If a 3-line edit solves it, do not extract helpers.
> Reviewers picked these findings precisely because they are worth fixing on
> their own — do not bundle adjacent rewrites unless the reviewer flagged them.

即：本轮只做 8 处定点修复（7 finding + OQ1），**一律最小补丁**，不顺手重构、
不加抽象、不加测试、不加 flag。唯一允许的"扩散"是 OQ1 带来的决策 #65 二分法
→ 三分法的 lockstep 同步（那是 reviewer 明确点出的连带项）。

**唯一有行为改变的一条是 OQ1**（`coordinator.py:522` 加 `effort="medium"`），
其余 7 条全是注释 / 文档 / 索引的文字修正。

## Planned action list

- file: `extraction/config.toml`（**M1 + M6/OQ2 + L1 + L2**，四条同文件）
  → M1：`:194` 删「白占 20 分钟」（旧值 1200s 残影；新值 900s = 15 分钟）；
    M6/OQ2：`:191-192` 删「旧 600s 天花板」沿革句，只留「900 = 实测未删失
    尾部 743s 的 1.2×」；L1：`:51-53` 「高 effort 档」→「更高的 effort 档
    （`xhigh` / `max`）」（`high` 本身就是高档，与括号里"effort=high 不撞墙"
    自相矛盾）；L2：`:55` 裸 `decisions.md #49 / #65` → 带路径
    `ai_context/decisions.md #49 / #65`
- file: `extraction/persona_extraction/core/config.py`（**M1 + M6/OQ2**）
  → `:134` 删 "stalling one for 20 minutes"；`:129-131` 删 "the old 600s
    ceiling" 沿革句
- file: `ai_context/decisions.md`（**M1 + M5**，另加 OQ1 的 #65 同步）
  → M1：`:293`（#64 索引行）删「白占 20 分钟」；M5：`:252`（#49 索引行）
    触发条件去掉钉死的 `opus-4-7 effort=max`
- file: `extraction/repair/checkers/semantic.py`（**M2**）
  → `:78` docstring 散文句「omits `effort` on the Phase A full pass」→
    「passes `effort=None`」（签名行本身正确，只改这句）
- file: `docs/todo_list.md`（**M7**）
  → `:416` / `:498` 正文段悬空前置引用改为指向真实剩余阻塞（挂机实跑基线
    对比）；`:25` T-GATE-SCOPED-RECHECK 的 Deps 保持 Blocked 但理由改为
    「等基线对比 stage 跑完」；`:26` T-REPAIR-TIMEOUT-CONFIG 的 Deps → 无，
    但 `:472`/`:498` 的「effort 归属模型影响 timeout 归属」约束**仍有效**，
    改述为「已定的方案 A（决策 #65）」而非删除；`:35` 不动
- file: `docs/architecture/extraction_workflow.md`（**L1**）
  → `:72-74` 同 L1 的「高 effort 档」句
- file: `extraction/repair/coordinator.py`（**OQ1**）
  → `:522` `pipeline.run_layer(fallback_files, layer=3)` 加 `effort="medium"`
- file: `ai_context/decisions.md` + `docs/decisions.md`（**OQ1 连带**）
  → #65 的二分法（gate=medium / Phase A=默认）扩成三分：补 Phase C
    fallback L3 = medium 及其理由

## Validation criteria

- [ ] import smoke：`cli` / `orchestrator` / `repair.*` 全部 import 无 error
- [ ] `load_config().repair.semantic_timeout_s == 900`（确认注释改动未碰值）
- [ ] `_smoke_l3_gate` 全过
- [ ] `_smoke_4_lane_merge_and_slice` 全过
- [ ] `coordinator.py` 的**三个** L3 入口在代码层可确认：Phase A 不传
      effort / L3 gate 传 medium / Phase C fallback 传 medium
- [ ] **语义等价残留 grep（非字面量）**：全仓「20 分钟」/「20 minutes」在
      `semantic_timeout_s` 语境下 = 0；「旧 600s」/「old 600s」在
      `extraction/` 代码注释内 = 0（`docs/decisions.md` 归档豁免）
- [ ] `ai_context/decisions.md` 内 `opus-4-7` = 0（`docs/decisions.md` 归档
      豁免、`logs/` 豁免）
- [ ] 裸 `decisions.md #` 指针（不带 `ai_context/` 或 `docs/` 前缀）在
      `extraction/config.toml` 内 = 0
- [ ] `docs/todo_list.md` 正文无「必须在 T-EFFORT-TIER-TUNING 之后」类悬空
      前置；Index 与正文一致、计数自洽（Next 4 / Discussing 8 / Total 12）
- [ ] 决策对 lockstep：#65 两边同步扩成三分，编号无漂移

## Execution deviations

1. **改 M1 时自己又犯了一次 L2**：替换「白占 20 分钟」那句时顺手写了新的裸
   指针「完整取值推导见 `decisions.md #64`」—— 而 L2 修的正是裸指针歧义。
   当场发现并纠正为 `docs/decisions.md #64`（完整推导在归档，指向正确）。
   无残留，但说明「裸 `decisions.md #N`」是个反复踩的坑，不是一次性笔误。
2. **`config.toml:41`（`summarize_timeout_s` 取值依据）一并脱敏**：原文
   「高 effort 档下单 chunk wall 经验值常 ≥ 600s」在 L1 的判据下同样自相
   矛盾（`high` 本身就是高档），且该句的档位限定对 1800s 这个取值并无信息
   量——直接删掉限定词，改为「单 chunk wall 经验值常 ≥ 600s」。属 L1 同类
   句的第三个副本，计划清单只列了两处（`config.toml:51-53` +
   `extraction_workflow.md:72-74`）。
3. **`docs/decisions.md` #65 的三分法段落改写幅度略大于「一行级」**：为了
   讲清 Phase C fallback 为何属「复读」而非「冷读」，补了它的触发条件
   （`had_semantic and run_semantic and not gate_ever_ran`）。这是 reviewer
   （OQ1）明确点出的连带项，不算顺手扩张，但比其余七条都长。
4. **未动 `docs/decisions.md` #65 的「两处连带（缺一即崩）」表述**——尽管
   `/post-check` 的 M4 已证伪它（宽 `except Exception` 会把 TypeError 吞成
   静默降级，不会崩）。M4 经用户 Auto 分诊丢弃，本轮按纪律不碰；已在 Step 5
   的 suggest-list 中提出。

<!-- POST phase fills in -->

## Landed changes

8 处定点修复全部落地（7 finding + OQ1）：唯一行为改动是 `coordinator.py`
Phase C fallback L3 加 `effort="medium"`（OQ1，同时解决 M3）；其余 7 条为
注释 / docstring / 文档索引的文字修正。决策 #65 两边同步扩成三分法（冷读 vs
复读）。文件级细节即 commit diff，不再枚举。

## Diff from plan

对照 PRE §Planned action list：

- **新增**（均见 §Execution deviations，非扩张）：`config.toml:41` 的
  `summarize_timeout_s` 取值依据脱敏（L1 同类句第三副本，计划只列两处）。
- **删除**：无。
- **修改**：`docs/decisions.md` #65 三分法段落改写幅度略大于「一行级」——
  为讲清 Phase C fallback 属「复读」补了其触发条件，属 OQ1 连带项。

## Validation results

- [x] import smoke —— `cli` / `orchestrator` / `repair.*` 无 error
- [x] `load_config().repair.semantic_timeout_s == 900`（注释改动未碰值；
      `summarize=1800` / `recovery_effort=high` 一并确认未变）
- [x] `_smoke_l3_gate` 全过
- [x] `_smoke_4_lane_merge_and_slice` 全过
- [x] 三个 L3 入口：Phase A 不传（`pipeline.run(...)`）/ L3 gate `medium`
      （`coordinator.py:426`）/ Phase C fallback `medium`（`:526`）—— 全仓
      layer=3 穷举确认无第四入口
- [x] 语义等价 grep：「20 分钟」/「20 minutes」/「旧 600s」/「old 600s」在
      `extraction/` + `ai_context/` 索引区 = 0（README「120 分钟」是
      `--max-runtime` 子串误命中，非本项）
- [x] `ai_context/decisions.md` 内 `opus-4-7` / `effort=max` = 0
- [x] 裸 `decisions.md #` 指针在 `config.toml` = 0（两处均带路径）
- [x] `docs/todo_list.md` 悬空前置 = 0；Index 12 条 ⇔ 正文 12 条，计数
      自洽（Next 4 / Discussing 8 / Total 12）
- [x] 决策对 lockstep：#65 两边三分法，基编号集合逐位一致

**复审**：因两个 sub-agent 均遇 API 529 中断，改为串行自查完成。Code 维度
零真缺陷（L3 入口穷举 + config 值未碰 + smoke 通过 + docstring 与代码
一致）；Surface 维度零缺陷（lockstep 干净、残留 = 0、无新增 legacy 措辞）。
一处 suggest-list（非本轮引入、非本轮 intent）：全仓另有 4 处裸
`decisions.md #N` 指针（`structural.py` / `targets_keys_eq_baseline.py` /
`_smoke_stage_plan_schema_min8.py`），属仓库级既有风格，建议并入未来
`/compress-ai-context` 批量清理，本轮不顺手做。

## Completed

- **Status**: DONE
- **Finished**: 2026-07-17 11:00:29 EDT
