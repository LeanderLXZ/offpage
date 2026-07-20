# ledger-call-type-label

- **Started**: 2026-07-20 14:09:28 EDT
- **Branch**: main
- **Type**: GO
- **Status**: DONE

## Background / Trigger

`T-SEMANTIC-FULLFILE-COST` 卡在**测不出来**：它想回答「语义审校（找问题）在 repair
里花的钱值不值」，但 run ledger（`logs/runs/*.jsonl`）只记 `lane`，repair 的全部
调用都是 `lane=repair`，**不区分「检查」与「修复」**。

该 todo 引用的原始结论「检查吃掉 repair 92% token，修复只占 8%」是 2026-07-16
**靠日志上下文猜出来的** —— 看到调用前有 `Retrieved N chapters` 就当修复、看到
`L3 gate` 就当检查。这种猜法当时能用；决策 #66 把 gate 改成 scoped 之后调用形态
变了，同样的猜法复现不出原数字。**没有尺子，就无法判断优化值不值得。**

用户 2026-07-20 拍板：先加标签。

## Conclusion and decisions

**标签由调用点显式给出**，不在事后从日志推断——只有 `repair/` 自己知道这次调用
是检查还是修复。沿用两个既有形态：决策 #49 的 `effort` per-call kwarg（同一条
`run_with_retry` 透传链）、决策 #68 的「调用点显式传出、注入方不留兜底 default」
（避免 #64 式的 config 被静默 shadow）。

**取值集合（定死 5 个，写进 `run_metrics.record` 的 docstring）**：

| 值 | 产生点 | 含义 |
|---|---|---|
| `check_full` | `SemanticChecker.check` | Phase A 全量语义检查（冷读整份文件）|
| `check_scoped` | `SemanticChecker.check_scoped` | L3 gate 定点复检（决策 #66）|
| `fix_t1` | `LocalPatchFixer` | T1 局部 patch |
| `fix_t2` | `SourcePatchFixer` | T2 原文 patch |
| `triage` | `Triager` | 源文差异 triage |

**未打标签的调用（提取 lane / phase 0 summarize / phase 1-2 lane 等）写 `null`**
——它们本来就能靠 `lane` 区分（`world` / `char_snapshot` / `char_support`），不是
repair 调用，无需二级分类。**不给它们编造标签**。

**关键设计点**：`_review_file` 被 `check` 与 `check_scoped` **共用**，是一个调用点
服务两种类型。让两个 public 方法各自在内部定死自己的 `call_type` 传给
`_review_file`，而**不是**让 coordinator 传进来——「这是全量检查还是定点复检」
是方法身份自带的信息，不该让调用方重复声明。副作用：`coordinator.py` 不进改动集。

**不做**：不动任何超时 / effort 值；不改 repair 行为；不给提取侧调用编标签；
不基于新标签做任何优化决策（本轮只装尺子，不量也不改）。

## Planned action list

- file: `extraction/persona_extraction/core/run_metrics.py` →
  `Recorder.record()` + 模块级 `record()` 增加 `call_type: str | None = None`
  参数，写入 jsonl 行的 `call_type` 字段；docstring 写死 5 个取值；
  `summarize()` 的聚合键从 `(phase, lane_type)` 扩展为
  `(phase, lane_type, call_type)`，表格加一列
- file: `extraction/persona_extraction/core/llm_backend.py` →
  `run_with_retry()` 增加 `call_type: str | None = None` kwarg，透传给
  `_record_run_metrics(lane_name, result, call_type)`
- file: `extraction/persona_extraction/orchestrator.py` → 两处 `_llm_call`
  闭包（`:2112` phase2 / `:3299` phase3）增加 `call_type: str | None = None`
  参数并透传给 `run_with_retry`
- file: `extraction/repair/checkers/semantic.py` → `_review_file` 增加
  `call_type` 参数并传给 `self._llm_call`；`check` 传 `"check_full"`、
  `check_scoped` 传 `"check_scoped"`
- file: `extraction/repair/fixers/local_patch.py` → `_llm_call` 调用点传
  `call_type="fix_t1"`
- file: `extraction/repair/fixers/source_patch.py` → 同上传 `"fix_t2"`
- file: `extraction/repair/triage.py` → 同上传 `"triage"`

## Validation criteria

- [ ] 全部 7 个文件 import 无 error
- [ ] `run_metrics.record()` 在传入 `call_type` 时把它写进 jsonl 行；不传时写
      `null`（构造 Recorder 实跑一次，读回落盘的行断言）
- [ ] **端到端穿透**：构造一个 fake `llm_call` 注入 `SemanticChecker` /
      `LocalPatchFixer` / `SourcePatchFixer` / `Triager`，断言各自传出的
      `call_type` 恰为 `check_full` / `check_scoped` / `fix_t1` / `fix_t2` /
      `triage`（**这是本轮最关键的一项**——#64 的教训是只验 config 层会漏掉
      调用点 shadow，必须驱动真实调用路径）
- [ ] `run_with_retry` 的签名新增 kwarg 后，既有调用点（不传 `call_type` 的）
      仍能正常调用（默认值生效，无 TypeError）
- [ ] `summarize()` 在混合 `call_type` 的行上能正常打表，不抛异常
- [ ] smoke: `_smoke_l3_gate` + `_smoke_triage` + `_smoke_4_lane_merge_and_slice`
      全过
- [ ] `grep -rn "call_type" extraction/` 的命中集合 = 计划的 7 个文件，无遗漏
      无多余

## Execution deviations

**偏差 1 — 追加改动两份 smoke 的 stub 签名（PRE 未预见，Step 3 验证捕获）。**

`_smoke_l3_gate` 与 `_smoke_triage` 在本轮改动后失败；用 `git stash` 对照证实
**HEAD 上两者均 PASS**，即由本轮引入，不是既有破损。

根因：两份 smoke 里共 8 个 `stub` 的签名是
`(prompt, timeout=600, effort=None) -> str`，**没有 `**kwargs` 兜底**。新增的
`call_type=` 关键字让它抛 `TypeError`，而该异常被 `semantic.py::_review_file`
的 `except Exception` 兜底吞掉、转成 `semantic_check_crashed` issue，所以表现
为断言失败而非崩溃 —— 排查时要留意这层遮蔽。

修法：给 8 个 stub 补 `**kwargs`（同文件内另有 3 个 stub 本就带 `**kwargs`，
未受影响）。这与当初新增 `effort` 参数时同类：**注入 callable 的契约扩展了，
测试替身要跟上**，不是 hack。

追加文件：
- `extraction/repair/tests/_smoke_l3_gate.py`（4 处 stub）
- `extraction/repair/tests/_smoke_triage.py`（4 处 stub）

实际改动集 = 计划 7 + 追加 2 = **9 个文件**。

**观察（不在本轮修）**：`_review_file` 的 `except Exception` 会把调用契约不匹配
这类**编程错误**和 LLM 侧的**运行时故障**一并转成 `semantic_check_crashed`
issue。fail-closed 的方向是对的（不静默 PASS），但它同时让签名不匹配这种本该
立刻炸出来的问题变得难排查。是否该把 `TypeError` 之类的编程错误单独放行，
转 Step 5 suggest-list。

<!-- POST phase fills in -->

## Landed changes

Run ledger 每行新增 `call_type` 字段，把 `lane=repair` 内部的调用按闭集 5 值再
分类；`summarize()` 聚合键相应扩展为 `(phase, lane_type, call_type)`。标签由
`extraction/repair/` 的调用点显式传出，经 `_llm_call` → `run_with_retry` →
`_record_run_metrics` 透传落盘。`T-SEMANTIC-FULLFILE-COST` 的测量阻塞解除 ——
下次跑任意 stage 即产出第一份可直接分组的账本。决策 #71。

## Diff from plan

对照 PRE `## Planned action list`（7 个文件）：

- **新增**（偏差 1）：`extraction/repair/tests/{_smoke_l3_gate,_smoke_triage}.py`
  —— 8 个 stub 补 `**kwargs`。不补则本轮改动直接打断这两份 smoke（已用
  `git stash` 对照证实 HEAD 上二者 PASS）。
- **新增**（Step 5 Code 复审）：`semantic.py::SemanticChecker.__init__` 的
  `llm_call` 契约 docstring 补 `call_type` —— 它是全仓唯一正式声明该注入契约
  的地方，不改则下一个照它写替身的人必然重踩同一个 `TypeError`。
- **新增**（Step 4 常规职责）：`docs/decisions.md` + `ai_context/decisions.md`
  #71、`docs/architecture/extraction_workflow.md` ledger 字段与聚合表描述、
  `ai_context/architecture.md` 一句话同步、`docs/todo_list.md` 条目更新。
- **修改**（Step 5 Surface 复审）：两份 decisions 的 #71 前补空行（与相邻条目
  排版一致）；`docs/todo_list.md` 的「测量局限」段消除自相矛盾 —— 该段原用
  现在时断言"账本不携带调用类型、需先补测量"，而同文件待决项 1 已标完成。

实际改动集 = 计划 7 + smoke 2 + 文档 5 = **14 个文件**（含本 log）。

## Validation results

- [x] 7 个文件 import 无 error — PASS（Step 5 后追加的 9 文件 `py_compile` 亦全过）
- [x] `record()` 传 `call_type` 时写入、不传时写 `null` — PASS，实读回落盘
      JSONL 断言 `['check_full', 'fix_t1', None]`
- [x] **端到端穿透四个调用点** — PASS。`SemanticChecker` 实跑得
      `check_full` / `check_scoped`；T1/T2/triage 源码断言 `fix_t1` / `fix_t2` /
      `triage`。Code 复审另行实测确认全仓 `_llm_call(` 发起调用恰 4 处、
      `_record_run_metrics` 恰 1 处，无遗漏
- [x] **（追加）** `run_with_retry` → `_record_run_metrics` 透传 — PASS，
      拦截观察到 `('repair[S9]','check_scoped')` / `('world', None)`
- [x] 既有调用点不传 `call_type` 无 TypeError — PASS，两处签名默认值均 `None`；
      Code 复审确认其余 11 个 `run_with_retry` 调用点不受影响
- [x] `summarize()` 混合 `call_type` 行不抛异常 — PASS，`None` 正确渲染为 `-`；
      Code 复审另行验证无 `call_type` 键的**旧行**亦不 KeyError（向后兼容）
- [x] smoke 三件全过 — PASS（修 stub 后）
- [x] `grep call_type` 命中 = 计划的 7 个文件 — PASS，无遗漏无多余

## Completed

- **Status**: DONE
- **Finished**: 2026-07-20 14:24:02 EDT
