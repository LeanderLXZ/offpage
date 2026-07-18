# repair-timeout-config

- **Started**: 2026-07-18 07:09:24 EDT
- **Branch**: main
- **Type**: GO
- **Status**: PRE

## Background / Trigger

用户指定 todo `T-REPAIR-TIMEOUT-CONFIG` 走 `/go`。

决策 #64 把 L3 语义审校超时解耦到 `[repair].semantic_timeout_s`，并去掉
`checkers/semantic.py` 里 shadow 掉 config 的硬编码。但同类问题在 `repair/`
内另外三处仍然存在——全都传字面量、都不读 config：

| 调用点 | 硬编码值 | 用途 |
|---|---|---|
| `fixers/local_patch.py:106` | 600 | T1 定点修复 |
| `fixers/source_patch.py:122` | 600 | T2 原文修复 |
| `triage.py:370` | 300 | triage |

这违反 `ai_context/conventions.md §Single Source of Truth`（运行时常量的权威
位置是 config 文件）。#64 的教训：硬编码会 shadow 掉 config，让整个配置层静默
失效——那次 `orchestrator` 的 `default_timeout` 因此成了死代码。

附带的命名问题：#64 落地后 `[phase3].review_timeout_s` 只剩 2 个引用点，且都
不属于 phase 3——`phases/scene_archive.py:429`（phase 4 scene split，唯一真实
消费者）与 `orchestrator.py:2108`（phase 2 per-lane repair 的
`default_review_timeout`，死代码：#59 缩水版下 phase 2 唯一可达的 LLM 调用是
T1 `local_patch`，而它显式传 600）。

## Conclusion and decisions

**归属模型 = 统一显式传（用户在 Step 0 拍板）。** 四个 repair LLM 调用点
（semantic / T1 / T2 / triage）全部从 `RepairConfig` 读各自的 timeout 并显式
传给 `_llm_call`；`orchestrator` 两个 `_llm_call` 包装器里的 `default_timeout`
/ `default_review_timeout` 兜底一并删除。

理据：
- 与决策 #65（effort 由调用点自己传，方案 A）**完全同构** ——
  同一函数上的 `timeout` 与 `effort` 走同一套哲学，消解 todo 里担心的
  "两个参数两套哲学"。
- `repair/` 仍然 config.toml-agnostic：它不读 toml，只消费注入方填好的
  `RepairConfig`（与既有 `max_rounds` / `accept_cap_per_file` / `retry_policy`
  形态一致）。
- 四种调用的预算本就不同（900 / 600 / 600 / 300）。让它们共享一个注入方
  default 会抹掉这个差异；给 `_llm_call` 加 kind 分派则是把策略搬进包装器，
  比直接传值更绕。
- 一个机制而非两个：不会长期并存"有的传、有的吃 default"。

这是对 #64 **机制**的 supersede（值 900 不变，#64 的解耦结论不变）。

**`review_timeout_s` 归属清理**：`[phase3].review_timeout_s` → 移段重命名为
`[phase4].scene_split_timeout_s`（唯一真实消费者是 phase 4 scene split）；
`orchestrator.py:2108` 的死代码 `default_review_timeout` 随统一模型删除。

**不做的事**：不动任何数值本身（900 / 600 / 600 / 300 / phase 4 的 600 原样
搬过去）；不给 phase 2 repair 接 L3（#59 缩水版是有意设计）。**行为不变**，
纯 refactor。

## Planned action list

- file: `extraction/repair/protocol.py::RepairConfig` → 新增
  `semantic_timeout_s=900` / `t1_timeout_s=600` / `t2_timeout_s=600` /
  `triage_timeout_s=300` 四字段
- file: `extraction/repair/checkers/semantic.py` → ctor 收 `timeout_s`；
  `_review_file` 显式传 `timeout=`；订正 llm_call 契约 docstring
- file: `extraction/repair/fixers/local_patch.py` → ctor 收 `timeout_s`，
  去掉字面量 600
- file: `extraction/repair/fixers/source_patch.py` → 同上
- file: `extraction/repair/triage.py` → ctor 收 `timeout_s`，去掉字面量 300
- file: `extraction/repair/coordinator.py` → `_build_pipeline` /
  `_build_fixers` / `Triager` 构造点接 `RepairConfig` 并透传四个 timeout
  （`validate_only` 路径给默认 `RepairConfig()`）
- file: `extraction/persona_extraction/core/config.py::RepairAgentConfig` →
  新增 `t1_timeout_s` / `t2_timeout_s` / `triage_timeout_s`
- file: `extraction/config.toml [repair]` → 三个同名键 + 中文注释
- file: `extraction/persona_extraction/core/config.py` →
  `Phase3Config.review_timeout_s` 删除；`Phase4Config.scene_split_timeout_s`
  新增
- file: `extraction/config.toml` → `[phase3].review_timeout_s` 移到
  `[phase4].scene_split_timeout_s`
- file: `extraction/persona_extraction/phases/scene_archive.py:429` → 跟随
  重命名
- file: `extraction/persona_extraction/orchestrator.py` → phase 2 / phase 3
  两个 `_llm_call` 删 default 兜底；两个 `RepairConfig(...)` 构造点透传
  `ra_cfg` 的四个 timeout；删 `default_review_timeout` 死代码
- file: `ai_context/decisions.md` + `docs/decisions.md` → 新增 #68；订正
  #47 / #64 里关于 `review_timeout_s` 消费者与 `repair/` timeout 归属的边界
  描述
- file: `extraction/README.md` + `docs/requirements.md` +
  `docs/architecture/extraction_workflow.md` → 配置分节表同步
- file: `docs/todo_list.md` + `docs/todo_list_archived.md` → 条目归档 +
  Index 刷新

## Validation criteria

- [ ] `python -c "import extraction.persona_extraction.orchestrator"` 无错
- [ ] `python -c "from extraction.persona_extraction.core.config import load_config"`
      + `load_config()` 能读到 4 个新键，且 `config.local.toml` 覆盖链生效
- [ ] `grep -rE "timeout=[0-9]+" extraction/repair/` 命中 0（tests 除外）
- [ ] `grep -rn "review_timeout_s" extraction/` 命中 0
- [ ] `grep -rn "phase3.review_timeout_s" extraction docs ai_context` 无 live 引用
- [ ] repair smoke 套件全过（`_smoke_l3_gate` 等；`_smoke_triage` HEAD 即坏，
      属 `T-SMOKE-TRIAGE-BROKEN` 既有破损，不计本轮）
- [ ] 行为不变：四个调用点实际传出的 timeout 值 = 改动前的 900/600/600/300

## Execution deviations

- `coordinator.validate_only()` 计划外新增 `config` 参数。原因：它是公共 API
  且内部走 `_build_pipeline`，不加参数会让 `semantic_timeout_s` 在这条路径上
  不可达 —— 与本轮「不留不可达 config」的目标直接冲突。一行改动，已记入 #68 边界。
- `_llm_call` 的 `timeout` 从 `int | None = None` 改为必填 `int`（计划里只写了
  "删除 default"）。这是同一决策的必然结果：注入方不留兜底后，漏传必须是
  TypeError 而非静默 `None`。
- `[repair]` 的注释按四键分组重写（计划里只写"三个同名键 + 中文注释"）——
  原 `semantic_timeout_s` 的注释里有「T1/T2/triage 各自显式传 timeout，不受
  此值影响」这类现已过时的表述，不重写会留下错误描述。
- Step 4 漏改 `docs/architecture/extraction_workflow.md`（它在 Planned action
  list 内），由 Step 5 表层复审查出并补上 —— 该文件原写「T1/T2/triage 目前仍
  硬编码在 `extraction/repair/` 内」，正是本轮推翻的状态。

<!-- POST phase fills in -->

## Landed changes

`repair/` 四类 LLM 调用（L3 语义审校 / T1 / T2 / triage）的 timeout 全部改由
调用点从 `RepairConfig` 显式传出，注入方的兜底 default 删除；三处硬编码
（600 / 600 / 300）收进 `[repair]` 新键；`[phase3].review_timeout_s` 重命名
移段为 `[phase4].scene_split_timeout_s`，死代码 `default_review_timeout` 删除。
新增决策 #68。文件级明细见 commit diff。

## Diff from plan

- 计划外新增 3 处（均已记入 §Execution deviations）：`validate_only()` 加
  `config` 参数、`_llm_call` 的 `timeout` 改必填、`[repair]` 注释按四键重写。
- 计划内漏做 1 处后被复审补回：`docs/architecture/extraction_workflow.md`。
- 其余与 Planned action list 逐条对应。

## Validation results

- [x] orchestrator import 无错
- [x] `load_config()` 读到 4 个新键；`config.local.toml` 覆盖链对新键生效 ——
      复审另用 DEBUG 日志确认零条 `unknown key ... ignored` warn，排除了
      「warn-and-drop 后恰好回退到相同默认值」的假阳性
- [x] `grep -rE "timeout=[0-9]+" extraction/repair/` 命中 0
- [x] `grep -rn "review_timeout_s" extraction/` 命中 0
- [x] `phase3.review_timeout_s` 无 live 引用（残留仅在 `logs/` +
      `docs/todo_list_archived.md` + `docs/decisions.md` 历史豁免区）
- [x] smoke 7/8 —— `_smoke_l3_gate` 场景 A–G 全过；`_smoke_triage` 失败已用
      `git stash` 对照证实 HEAD 上以完全相同的断言失败（既有破损
      `T-SMOKE-TRIAGE-BROKEN`，本轮正交；失败是断言而非 TypeError，也排除了
      timeout 签名收紧的嫌疑）
- [x] 行为不变 —— 两个复审 agent 独立实例化验证四调用点实际传出
      900 / 600 / 600 / 300，phase 4 为 600，与改动前逐一相等

## Completed

- **Status**: DONE
- **Finished**: 2026-07-18 07:24:02 EDT
