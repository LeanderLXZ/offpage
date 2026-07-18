# gate-scope-doc-accuracy

- **Started**: 2026-07-18 04:20:16 EDT
- **Branch**: main
- **Type**: GO
- **Status**: PRE

## Background / Trigger

`/post-check`（对 commit `e67abb5` / 决策 #66）复审出的 **M1（Medium）**，经 `/fix`
逐条 triage 后用户选 fix，交由本轮落地。

来源 review：`logs/change_logs/2026-07-17_112727_gate-scoped-recheck.md`
（Type: GO，Status: REVIEWED-PARTIAL）。

M1 内容：决策 #66 落地时，首版 scope 只含「本轮改过的 json_path」；复审发现该
形态会让本轮未修好、又不在改动 path 上的语义 error 被 round-diff 误判 resolved
→ 假 PASS，遂在 `/go` Step 5 就地修复为 per-file 的
「触碰 path ∪ 本轮携带的未修语义 issue path」（`_gate_scope`）。**但修复之后没有
回头改文档**——6 处落盘文档仍写 touched-only，与代码和自己的 commit message 相互
矛盾。

危害：未来读者据 touched-only 理解，可能把 carried 分支当冗余删掉，重新引入刚被
堵住的假 PASS；且文档中「introduced 只出现在改过的 path 上」的推论也建立在已失准
的 touched-only 前提上。

## Conclusion and decisions

**纯文字修正，不改任何运行时行为。** 把 gate scope 的描述统一为
「per-file scope = 本轮改过的 json_path **∪ 本轮携带的未修语义 issue path**」，
并在 `docs/decisions.md` #66 归档补一句 carried 的**理由**（防 round-diff 把未修
issue 误判 resolved），使该决策档案自身携带这条复审驱动的关键修复。

顺带把两处代码 docstring 的同一处欠准对齐（注释，不改行为）。

**边界**：
- 不动 gate 逻辑。未触碰文件的假 PASS 已单独登记为
  `T-GATE-UNMODIFIED-FILE-CARRY`（`docs/todo_list.md` Next），不在本轮。
- 不动 `docs/decisions.md` #62 等历史归档条目（历史语境正确保留）。
- 不做顺手重构 / 不加抽象 / 不加测试。

## Planned action list

- file: `docs/decisions.md` #66（标题 + 正文约 :1106 / :1116）→ scope 描述改为
  touched ∪ carried；补 carried 的理由（优先级最高，归档是耐久记录）
- file: `ai_context/decisions.md` #66 索引条目（约 :299）→ 同步
- file: `docs/requirements.md` §11.4.5 三阶段流程 step 4（约 :1845）→ 同步
- file: `docs/requirements.md` L3 gate 触发条件与范围（约 :1909）→ 同步
- file: `docs/architecture/extraction_workflow.md` Phase B gate 段（约 :799）→ 同步
- file: `ai_context/architecture.md` Phase 3 句（约 :134）→ 同步
- file: `extraction/repair/coordinator.py` → 模块 docstring / gate 块注释里
  touched-only 的表述对齐（`_gate_scope` 自身 docstring 已正确，核对即可）
- file: `extraction/repair/tracker.py` `is_regression` docstring（约 :60-62）→ 同步

## Validation criteria

- [ ] `python -c "import extraction.repair.coordinator, extraction.repair.tracker"` 无 error
  （docstring 编辑可能破坏引号 / 语法，必须验）
- [ ] `python -m extraction.repair.tests._smoke_l3_gate` 6 场景 A–F 全过（确认纯注释
  改动未触碰行为）
- [ ] grep 残留 = 0：全仓（排除 `logs/`、`docs/todo_list*.md` 的历史/问题陈述语境）
  不再有把 gate scope 描述成「只复检本轮改过的 json_path」的**现行设计**表述
- [ ] 8 处计划锚点逐一确认已改（无漏项）

## Execution deviations

- **计划 8 个锚点，实际 9 个**：Step 3 的 grep 验证标准抓出计划外的第 9 处同类
  欠准——`extraction/repair/checkers/__init__.py:115`
  （`run_semantic_scoped` docstring 写「re-checks ONLY the json_paths a fix
  touched this round」）。属 M1 同一 finding 的同类表述，非范围外扩，就地补齐。
- `extraction/repair/coordinator.py` 计划内但**实际无需改动**：其模块 docstring
  与 gate 块注释在上一轮（#66 的复审就地修复）已同步为
  「touched + still-open semantic」，核对后确认准确。
- **Step 5 复审又抓出 2 处同类残留（第 10、11 处）**：
  `extraction/repair/checkers/semantic.py:43`（`_path_in_scope` docstring
  「scopes a re-check to the json_paths a fix actually touched this round」）与
  `:138`（`check_scoped` docstring「restricted to ``paths`` — the json_paths a
  fix actually touched this round」）。**根因是我的 grep 模式太窄**——只覆盖
  `only the json_paths`，漏了 `restricted to ...` / `scopes a re-check to ...`
  两种句式，导致 Step 3 的「残留 = 0」是假阴性。已就地补齐并**加宽 grep 模式**
  重跑，现 en/zh 双向残留均为 0。
- **Step 5 复审两处准确性补强（就地修）**：(1) `tracker.py` 模块 docstring 的
  「`introduced` 只出现在本轮被复检的 path 上」补上例外——`$` 锚的后端失败类
  issue 永不被 scope 过滤，可从 scope 外冒出，其含义是「复检没跑通」而非回归；
  (2) `docs/requirements.md`「没被改动的文件 gate 不会重复跑（节省 LLM 调用）」
  补上代价说明并指向 `T-GATE-UNMODIFIED-FILE-CARRY`——原文把一个已确认的假 PASS
  洞写成纯成本优化，有再次误导的风险。

<!-- POST phase fills in -->

## Landed changes

M1 落地：把 gate scope 的描述从 touched-only 统一订正为「per-file = 本轮改过的
json_path ∪ 本轮携带的未修语义 issue path」，共 11 处锚点（6 处文档 + 5 处代码
docstring/注释），并在决策 #66 归档补上 carried 那一半的**理由**（防 round-diff
把未修 issue 误判 resolved = 假 PASS），使该档案自身携带这条复审驱动的关键修复。
零可执行行变更。

## Diff from plan

- 计划 8 处锚点 → 实际 11 处：Step 3 的 grep 抓出第 9 处
  （`checkers/__init__.py`），Step 5 复审抓出第 10、11 处（`semantic.py:43` /
  `:138`）。三处均为 M1 同一 finding 的同类表述，非范围外扩。
- 计划内 `coordinator.py` 实际无需改动（上一轮已同步，核对确认）。
- 计划外的两处准确性补强（tracker 的 `$` 后端失败例外、requirements 的
  `T-GATE-UNMODIFIED-FILE-CARRY` 代价说明），均为一句话就地修，见 deviations。
- **验证标准本身被修正**：原 grep 模式过窄导致 Step 3 出现假阴性，已加宽后重跑。

## Validation results

- [x] `import extraction.repair.{coordinator,tracker,checkers,checkers.semantic}` — IMPORT OK
- [x] `_smoke_l3_gate` 6 场景 A–F 全过（确认纯注释改动未触碰行为）
- [x] grep 残留 = 0 —— **加宽后**的模式（覆盖 `only the json_paths` /
  `restricted to ...` / `scopes a re-check to ...` / 中文三种句式）en/zh 双向均为 0
- [x] 锚点无漏项：11/11（计划 8 + grep 1 + 复审 2）

## Completed

- **Status**: DONE
- **Finished**: 2026-07-18 04:29:31 EDT
