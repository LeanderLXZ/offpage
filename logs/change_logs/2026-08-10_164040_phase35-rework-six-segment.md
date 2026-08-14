# phase35-rework-six-segment

- **Started**: 2026-08-10 16:40:40 EDT
- **Branch**: main
- **Type**: GO
- **Status**: DONE

## Background / Trigger

T-PHASE35-DEFERRED-FIX。2026-08-02/03 两轮提取跑完全部 53 stage 后，对
Phase 3.5 现状做了实测（53 stage × 2 角色，0.26s）：

- 9 项检查里唯一报出东西的 `_check_alias_consistency` 产 40 条 warning，
  **全部误报** —— `identity.aliases` 收专有称号、`active_names` 收关系性
  称呼，两个集合语义不同，要求后者 ⊆ 前者的前提不成立。
- `deferred_repairs` 台账 38 条债（17 length / 5 type / 16 semantic，跨
  27 个文件）**一条都不在 Phase 3.5 的检查面上**；且全仓 grep 确认台账
  **零消费方**（只有 `write_deferred_repairs` 写入方）。
- 多处 `if snapshot is None: continue` 静默跳过 —— "检查通过" 与 "根本
  没检查" 在报告里无法区分。

**Step 0 排查（本轮新增证据，推翻先前假设）**：逐条比对台账 length 债与
`repair_logs/*.jsonl`，17 条 length 债中 **16 条是 repair 自己制造的**：
T2 为修语义而重写散文字段（如 `$.character_arc`）→ 改写后超 `maxLength`
→ 轮内 scoped recheck 捕获为新指纹 → `introduced=1` → 回归安全阀
（`coordinator.py:567`）立即 break → Phase C 复扫仍报 → 判 FAIL 入台账。
T0 从未见过它们。典型样本 `repair_S035_stage_snapshots_S035.json_ac34bb5c`：
`phase_a_result blocking=4`（全 semantic）→ `round_result resolved=0,
persisting=4, introduced=1` → `complete FAIL issues_remaining=1`。

## Conclusion and decisions

Phase 3.5 从"只 check 不修的跨 stage 校验器"重做为**stage 文件的最后
关卡**：跨 stage 全面检查 + 遗留债定点修复，六段串行、段内并行。

**定位与职责**：Phase 3.5 吞掉 deferred_repairs 台账（决策 #60 的 Part B
并入），成为"债必须还清才能进 Phase 4"的门。

**不重复做同一件事**：Phase A（`check_full`）已逐文件全文语义审校过一遍，
本关**绝不重跑全量全文审校**；补的是全管线唯一空白 —— 跨 stage 连贯
视角（arc 断裂 / 境界倒退 / 关系数值跳变 / 知识倒流）。唯一例外是
`semantic_unparseable` 的文件（该文件 Phase A 实际从未读成，属补课）。

**全部定点修复**：所有修复走 `json_path` field patch；T3 全文重生成在
决策 #62 已删除，`$` 根锚点永不升 LLM 层 —— 文件重生成这条路在代码里
不存在，无需额外防。

**根因修复纳入本轮**（原计划"另立修复项"，改为在本轮修）：length 债的
制造机是共享的 repair 轮循环 —— Phase 3.5 自己的修复循环复用同一份
`repair.run()`，不修就会每跑一次制造一批新债。在债的制造机上建门 =
建在沙上，故纳入。修法最小：轮内 scoped recheck 新增的**纯长度类**问题
不触发回归安全阀（它们下一轮起步 T0 可确定性修复），且被计入该轮
`introduced` 的长度类问题先交 T0 就地修一次。

**effort 分档沿用现有 3 键，不新增配置**：冷读（跨 stage 审校 + 补课
`check_full`）不传 effort、吃 `[llm].effort`（xhigh）；修复与复验传
`[repair].recheck_effort`（medium）。

**并行**：段内并行、段间串行。轨道 C 必须在债修完之后跑 —— 台账债恰好
落在 C 要投影的字段上（`character_arc` / `stage_delta` / `current_status`
/ `relationships[].summary` / 境界链），并行会让 C 读到脏状态；且 C 放在
修复之后才能顺带终审 B 的语义补丁是否引入跨 stage 断裂。

**六段**：
1. 程序全扫 + 机械修（0 token）：全量 jsonschema + 跨文件结构/派生检查
   （删 alias check）+ 台账 schema 债就地复验自动销账
2. semantic 债定点修复（T2，medium）+ `semantic_unparseable` 文件补课
3. 跨 stage 连贯审校（每角色 + world 各 1 次冷读，并行）
4. 审校发现 → 同一套定点修复循环（修前程序存在性确认，防幻觉锚点）
5. PP 重投影（受影响 stage 重跑 `run_stage_post_processing`，幂等 0 token）
   —— 缺此步 #32/#33 的派生 1:1 检查必假 FAIL
6. 程序复扫 + 门判 + 报告（coverage 账本）

**门判**：`passed = error_count == 0 AND skipped_files == 0`。静默跳过
变显式失败。

**台账自愈**：Phase 3.5 不信任台账陈述 —— schema 类就地复验（修好自动
销账），semantic 类靠 resolution 追加记录（append-only、逐条即时落盘，
中途崩溃重跑天然幂等）。

**不做**（防过度工程）：不重跑 Phase A 全量；不新建修复框架（复用
`repair.run()`）；不做事件驱动双线程池；不给轨道 C 做多轮迭代；不动
程序部分性能（0.26s 已达标）。

## Planned action list

- file: `extraction/repair/coordinator.py` → 轮内长度类 `introduced` 不
  触发回归阀 + 先交 T0 就地修（length 债制造机的根因修复）
- file: `extraction/repair/fixers/programmatic.py` → T0 新增 index-keyed
  dict → array 转换（5 条 `schema_type` 债的固定形态）
- file: `extraction/persona_extraction/lifecycle/deferred_repair_log.py` →
  新增 resolution 追加读写（append-only，逐条即时落盘）
- file: `extraction/validation/gates/phase3_5_consistency.py` → 三层重构
  （L1 结构 / L2 派生 / L3 台账复验）+ coverage 账本 + 删
  `_check_alias_consistency`
- file: `extraction/persona_extraction/phases/cross_stage_projection.py`
  （新增）→ 跨 stage 瘦投影拼接器
- file: `extraction/persona_extraction/prompts/cross_stage_review.md`
  （新增）→ 跨 stage 连贯审校 prompt
- file: `extraction/persona_extraction/orchestrator.py` →
  `_run_consistency_check` 扩为六段驱动 + PP 重投影 + commit 扩面
- file: `docs/architecture/extraction_workflow.md` → §Phase 3.5 契约重写
- file: `docs/requirements.md` → §11.10 Phase 3.5 产物提交契约更新
- file: `ai_context/architecture.md` → §自动化抽取流水线 Phase 3.5 段更新
- file: `ai_context/decisions.md` + `docs/decisions.md` → 新决策 #72
- file: `docs/todo_list.md` + `docs/todo_list_archived.md` →
  T-PHASE35-DEFERRED-FIX 归档 + Index 刷新

## Validation criteria

- [ ] `python -c "import extraction.persona_extraction.orchestrator"` 无报错
- [ ] `python -c "import extraction.validation.gates.phase3_5_consistency"` 无报错
- [ ] `python -c "import extraction.repair"` 无报错
- [ ] 新增模块 `cross_stage_projection` 可 import 且瘦投影在真实数据上跑通
      （53 stage × 2 角色 + world），打印文档字符数
- [ ] `phase3_5_consistency` 在真实数据上跑通：alias 误报归零、coverage
      账本有 checked/skipped/hit 三个计数、L3 层能读出台账 38 条债
- [ ] T0 index-keyed dict → array 单元级验证（构造 `{"0": ..., "1": ...}`
      → 得到有序 array）
- [ ] 长度类 `introduced` 不再触发回归阀：构造/复核 tracker 判定逻辑
- [ ] repair 既有 smoke 通过（`extraction/repair/tests/_smoke_*.py`）
- [ ] grep 残留：`_check_alias_consistency` / `alias_consistency` 在
      `extraction/` `docs/` `ai_context/` 中 0 处 live 引用
- [ ] 敏感内容：新增 prompt / 文档 / 代码注释中无真实书名 / 角色名

## Execution deviations

1. **新增 `[phase3_5]` 配置段**（`extraction/config.toml` +
   `core/config.py::Phase35Config`）—— 计划未列。审校窗口尺寸是真实的
   运行期可调量，按决策 #45「单源 TOML」应当入配置而非硬编码常量；只装
   `review_window_chars` / `review_window_overlap_stages` 两个键，不装
   推理档位（effort 仍由现有 3 键穷尽，符合计划的"不新增 effort 键"）。

2. **`repair.run()` 新增 `seed_issues` 参数** —— 计划的动作清单只写了
   coordinator 的长度类修复，未写这条。但计划结论段明确要求"复用
   `repair.run()` 做定点修、不新建修复框架"，而原 `run()` 必然先跑 Phase A
   发现扫描 = 把每个文件重新全文读一遍，与"不重复做同一件事"直接冲突。
   seed 入口是满足该结论的最小改动：只跳过发现，其后 tier 路由 / scoped
   复验 / L3 gate / 安全阀全部不变。

3. **`extraction/README.md` + `docs/architecture/system_overview.md`
   一并更新** —— 前者是模块 README（Phase 3.5 段与目录树描述已失真），
   后者在复审 Surface 维度扫出旧描述残留（"可选 LLM 裁定"）。同批修掉
   `docs/requirements.md` 三处 ASCII 流程图里的"9 项程序化检查 / 可选 LLM
   裁定"。

4. **`ai_context/{conventions,handoff,requirements}.md` 一并更新** ——
   conventions 增一行 Cross-File Alignment（`DEFERRABLE_CATEGORIES` ⇄
   `REVALIDATABLE_CATEGORIES`：两侧常量名不同，grep 查不到对方）；
   handoff 更新当前 gap；requirements 索引补 Phase 3.5 于 §9 流程串。

5. **复审自查修掉两个结清回路缺陷**（实现当轮引入，未进入提交）：
   - `ConsistencyIssue` 原先不带 `rule`，resolution 与台账的
     `issue_key`（`file::json_path::rule`）**永远匹配不上** —— semantic 债
     写了 resolution 也不会被认，门将永久 FAIL。改为显式携带 `rule`，
     并删掉三处 `message.split(":")` 的脆弱推导。
   - L3 原先对**所有**类别先查 resolution 再判定，会让一条 schema 债的
     resolution 永久屏蔽它（即使该字段后来重新写坏）。改为：可复验类别
     只认文件复验结果（文件即真相），resolution 只对不可复验类别生效；
     写入侧同步只为 semantic 债写 resolution。
   - 附带：L3 issue 的 `category` 由通用 `deferred_debt` 改为携带**原始
     类别**——否则 seed 给 repair 时 schema 债会被当 semantic 路由到 T2
     （载章节原文），既慢又错。

6. **未做**：`schemas/analysis/consistency_report.schema.json` ——
   计划里标注为"若存在需同步；否则新建"。核查后该 schema 不存在，且
   报告是本地诊断产物、无外部消费方（与 `T-LIGHTNOVEL-SCHEMA-ONEOF` 同
   性质），本轮不新建以免立无人消费的契约。

<!-- POST phase fills in -->

## Landed changes

Phase 3.5 从"只 check 不修的跨 stage 校验器"重做为 stage 文件的最终关卡：
三层检查（L1 结构 / L2 派生 1:1 / L3 台账结清）+ 六段流程（程序全扫 →
结清台账债 → 跨阶段连贯审校 → 定点修 → 重投影 → 复扫门判）+ coverage
账本门判；顺带定位并根治了 length 债的制造机（决策 #72 / #73）。
文件级明细见本次 commit diff。

## Diff from plan

见上方 §Execution deviations 六条。要点：新增 `[phase3_5]` 配置段与
`repair.run(seed_issues=)` 入口（均为满足计划结论所必需）；额外同步了
`extraction/README.md` / `system_overview.md` / 三处 requirements ASCII 图
的旧描述；复审自查修掉两个当轮引入的结清回路缺陷；未新建
`consistency_report.schema.json`（无消费方）。

## Validation results

- [x] `import extraction.persona_extraction.orchestrator` — 无报错
- [x] `import extraction.validation.gates.phase3_5_consistency` — 无报错
- [x] `import extraction.repair` — 无报错
- [x] `cross_stage_projection` 可 import 且真实数据跑通 —— 53 stage × 2 角色
      + world；角色投影 410,270 / 381,753 字符、world 65,854；按 120k 切窗
      得 4 + 4 + 1 = **9 次审校调用**，窗间重叠 1 stage
- [x] `phase3_5_consistency` 真实数据跑通 —— 0.28s；**alias 误报 40 → 0**；
      coverage 账本 10 个 check 全部产出 checked/hit/skipped；L3 读出全部
      **38 条债**（22 schema + 16 semantic）
- [x] T0 index-keyed dict → array —— `{"0":a,"1":b,"2":c}` → `[a,b,c]`；
      偏移键 / 非数字键 / 非 dict 均正确拒绝
- [x] 长度类 `introduced` 不再触发回归阀 —— 三条门控实测：自造超限被 T0
      扫掉（180→48 字符，句读边界收口）、预存在的不动、未碰路径的不动
- [x] repair 既有 smoke 全过 —— `_smoke_triage` + `_smoke_l3_gate`
      场景 A–H
- [x] grep 残留 —— `alias_consistency` 在 extraction/docs/ai_context 中
      0 live 引用；"9 项程序化检查 / 可选 LLM 裁定" 0 残留
- [x] 敏感内容 —— 全部改动与新增文件中真实书名 / 角色名命中数 0
- [x] 额外（复审补充）：结清回路端到端 —— schema 债凭复验自愈、semantic
      债凭 resolution 结清、resolution 不庇护重新写坏的 schema 债
- [x] 额外（复审补充）：pyflakes 干净（仅剩 2 处既有问题，已用 HEAD 版本
      核实非本轮引入）

**未验证（需真实运行）**：段 2/3/4 的 LLM 环节从未端到端跑过——本轮只验证
了程序段与全部接缝。首次真实运行预期因 38 条历史债判 FAIL，属设计内。

## Completed

- **Status**: DONE
- **Finished**: 2026-08-10 17:12:34 EDT

<!-- /post-check writes -->

## Review conclusion (full report in conversation)

### Track 1 — requirement fulfillment
- Fulfillment rate: 12/12 计划文件项 + 10/10 验证标准
- Missed updates: 1 项（见对话：extraction/README.md 目录树未列新模块）

### Track 2 — impact spread
- Findings: High=1 / Medium=3 / Low=2
- Open Questions: 1 项（见对话）

## Review state
- **Reviewed**: 2026-08-14 12:03:30 EDT
- **Status**: REVIEWED-FAIL
  - H1：L3 revalidator 抛异常后，同文件其余债被静默判为已结清（假 PASS）
- **Conversation ref**: /post-check output in this session
