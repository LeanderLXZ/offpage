# repair-semantic-timeout-decouple

- **Started**: 2026-07-16 14:13:42 EDT
- **Branch**: main
- **Type**: GO
- **Status**: DONE

## Background / Trigger

Phase 3 重跑期间（runtime 监控），S001 的 repair 收尾出现两条 lane 撞
`[phase3].review_timeout_s = 600s` 硬超时被杀，撞线 lane 的
`semantic_unavailable` 经决策 #60 的 record-and-continue 通道写入
`deferred_repairs/S001.jsonl` 并让 stage 正常提交 —— 即 stage 以「L3 语义
审校从未跑出结论」的状态落盘，而非「已知有瑕疵」。

对全部 4 份历史 extraction log 做耗时统计（n=104 条 repair lane）：

| 指标 | 值 |
|---|---|
| p50 | 93s |
| p95 | 519s |
| 未删失最大 | 598s |
| 撞 600s 上限 | 3 / 104 = 2.9% |

按 repair 调用类型拆分（n=104）：

| 调用类型 | n | p50 | max |
|---|---|---|---|
| T1 local_patch 修复 | 34 | 14s | 411s |
| T2 source_patch 修复 | 2 | 28s | 28s |
| L3 语义检查 (Phase A) | 38 | 152s | 600（删失）|
| L3 gate 复检 | 24 | 185s | 600（删失）|
| L3 兜底复检 (Phase C) | 1 | 600（删失）| 600 |

结论：决策 #62 的定点修复已生效（修复侧 p50 = 14s，比提取 lane p50 ≈ 800s
快 ~50×）；撞墙的是**检查侧**（L3 语义审校），不是修复侧。

根因是参数耦合：`review_timeout_s` 同时服务三类形态差异极大的调用 ——
repair 的 L3 语义审校（读整份 50k 字符 stage_snapshot）、phase 3 reviewer
短链、phase 4 reviewer（`scene_archive.py:429`）。600s 这个值来自
`d79dc7f`（2026-04-20，「常量改读 config」，即该值比该 commit 更早），当时
注释「审校 prompt 输入更小、输出更确定」对 reviewer 短链成立；此后 repair
L3 语义审校在同一参数下接入，负载形态变化而数值未随动。

同结构先例：决策 #47 —— phase 0 chunk summarize 曾借用
`phase3.review_timeout_s`，全部 10 chunk 撞 600s，修法是解耦出
`[phase0].summarize_timeout_s = 1800`。#47 只解耦了 phase 0，repair 留在
原地共用，本轮撞墙的正是当时未解耦的那一半。

## Conclusion and decisions

**决策**：为 repair 的 L3 语义审校新增独立超时参数
`[repair].semantic_timeout_s = 1200`，与 `[phase3].review_timeout_s` 解耦。

**取值 1200 而非 1800 的理由**：#47 的**结构教训（解耦）**适用，但其
**取值逻辑（3 × 典型 wall）不适用** —— #47 的形态是「全员偏慢」（典型 wall
≥ 600s，故 3× = 1800）；本处形态是「p50 快（152s）+ 长尾」，照搬 3× 得
456s，反而比现值更小。长尾分布的取值依据应是「慢」与「卡死」的分界：

- 1200 = 未删失最大观测（598s）的 2.0×、p50 的 8×
- 跑满 8× p50 仍未返回的调用大概率是卡死而非仍在算；从 1200 等到 1800
  主要买到「卡死多占 10 分钟槽位」而非「多救回几条」
- 代价不对称：取低了有决策 #60 的 defer → Phase 3.5 兜底（便宜）；取高了
  在 `repair_concurrency = 10` 下直接加到每个受影响 stage 的 wall time
  （53 stage 累积可观）
- 附带收益：现有数据在 600s 处**右删失**，真实尾部未知。1200 兼作测量 ——
  若重跑无 lane 撞 1200，即首次取得未删失尾部，之后可有据收紧

**不做**：
- 不动 `[phase3].review_timeout_s = 600`（phase 3 / phase 4 reviewer 短链
  无撞线证据，调大等于松掉它们的超时保护 —— 正是 #47 批评的耦合）
- 不动 `extraction_timeout_s` / `summarize_timeout_s` /
  `json_repair_l2_timeout_s` / `max_turns` / 熔断 / 限流（全景排查：均无
  触发记录）
- 不动 `_SEMANTIC_MAX_CHARS = 50000` 截断（独立的架构问题，另开 todo）
- 不动 `char_support` 的 3600s 余量（最慢 2127s = 1.7× 余量，形态可疑但
  n=4，样本不足，记为观察项）

## Planned action list

- file: `extraction/persona_extraction/core/config.py` → `RepairConfig`
  新增 `semantic_timeout_s: int = 1200`
- file: `extraction/config.toml` → `[repair]` 段新增
  `semantic_timeout_s = 1200` + 中文注释（取值依据 + 与
  `review_timeout_s` 的分工）
- file: `extraction/persona_extraction/orchestrator.py:3286` →
  `default_timeout` 由 `get_config().phase3.review_timeout_s` 切到
  `get_config().repair.semantic_timeout_s`
- file: `extraction/README.md` → 配置分段表 `[repair]` 行补
  `semantic_timeout_s`
- file: `ai_context/decisions.md` + `docs/decisions.md` → 新增决策条目
  （L3 语义审校超时解耦 + 1200 取值依据 + 与 #47 的关系）
- file: `docs/architecture/extraction_workflow.md` → 子进程硬超时描述补
  repair L3 语义审校 1200s
- file: `docs/requirements.md` → 同段 + 配置分节表同步
- file: `ai_context/handoff.md` → §Current State / §Next Steps 更新

## Validation criteria

- [ ] `tomllib` 静态解析 `extraction/config.toml` 通过
- [ ] `load_config()` 返回的 `RepairConfig.semantic_timeout_s == 1200`
- [ ] `orchestrator.py` 模块 import 无 error
- [ ] `grep "phase3.review_timeout_s"` 仅剩 2 个合法用点
      （`orchestrator.py:2108` phase 3 reviewer 短链 /
      `scene_archive.py:429` phase 4 reviewer），repair 用点已切走
- [ ] repair 的 `_llm_call` 实际取到 1200（构造 config 后断言
      `default_timeout` 取值路径）
- [ ] `config.local.toml` 覆盖链对新键仍生效（CLI > local > toml > 默认）
- [ ] 文档 grep 残留 = 0：不存在「repair ... 600s」等过期表述

## Execution deviations

**偏差 1 — PRE 对 `orchestrator.py:2108` 的定性有误（事实更正）。**
PRE 称 2108 是「phase 3 reviewer 短链」。实际读码：2108 位于
`# --- repair plumbing (shared by every lane) ---` 段内，
`lane_name="repair[phase2]"` —— 它是 **phase 2 的 per-lane repair**
（决策 #59 缩水版：`run_semantic=False` / `l3_gate_enabled=False` /
`t2_max=0`，即只有 T0/T1，不含 L3 语义层）。

由此得出一个 PRE 未预见的事实：本轮改动落地后，`[phase3].review_timeout_s`
仅剩 2 个引用点，且**都不属于 phase 3**；其中**只有一个是真实消费者**
（此结论经 Step 5 Surface 复审更正，见下）——
- `scene_archive.py:429` → phase 4 scene split：**唯一真实消费者**
  （`timeout_seconds=cfg.phase3.review_timeout_s` 直接传值）
- `orchestrator.py:2108` → phase 2 per-lane repair 的 `default_review_timeout`：
  **同属死代码**。#59 缩水版关掉 `run_semantic` / `l3_gate` / `triage` 且
  `t2_max=0`，phase 2 repair 唯一可达的 LLM 调用是 T1 `local_patch.py:106`，
  而它显式传 `timeout=600` ⇒ 该 default 从不被消费（与 3286 同构）

即一个名为 `[phase3]` 的参数实际只服务 phase 4。参数名与归属已完全脱离
实际服务对象，属本轮意图之外的命名 / 归属问题，不在本轮修（避免范围
蔓延），转 Step 5 suggest-list 交用户定夺。

**决策（沿用 PRE 的证据原则）**：两个用点均维持 600s 不动 ——
- phase 2 repair：只跑 T0/T1，实测 T1 p50=14s / max=411s，600s 余量充足，
  无撞线证据
- phase 4 scene split：phase 4 从未运行，零样本，无依据调整

**偏差 2 — PRE 的核心接线假设是错的；只改 `orchestrator.py:3286` 是
100% no-op（Step 3 验证捕获）。**

PRE（及此前全部分析）假定 L3 语义审校的 600s 来自
`[phase3].review_timeout_s`。实际读码：`repair/` 内**全部 4 个**
`_llm_call` 调用点都传**硬编码** timeout，无一读 config ——

| 调用点 | 硬编码值 | 用途 |
|---|---|---|
| `checkers/semantic.py:138` | **600** | L3 语义检查（Phase A + gate 复检）|
| `fixers/local_patch.py:106` | 600 | T1 定点修复 |
| `fixers/source_patch.py:122` | 600 | T2 原文修复 |
| `triage.py:370` | 300 | triage |

因 `_llm_call` 内是 `timeout or default_timeout`，而 `timeout` 永远非
None，故 `orchestrator.py:3286` 的 `default_timeout` 是**死代码**。真正
管着语义审校的一直是 `semantic.py:138` 的硬编码 600，`review_timeout_s`
从未参与。

**诊断仍然成立**（L3 审校撞 600s 墙、n=104 的耗时分布、右删失全部为真），
**但修复位置改变**：追加改动
`extraction/repair/checkers/semantic.py:138` —— 去掉显式 `timeout=600`，
改为 `self._llm_call(prompt)`，把预算交回注入方（orchestrator，config 的
所有者）。`repair/` 保持 config-agnostic（框架靠注入 callable，刻意不依赖
`persona_extraction.core.config`），符合 `conventions.md §Single Source of
Truth`：值的权威位置是 `config.toml`。

前置校验：两个注入点（`orchestrator.py:2110` / `:3288`）与 smoke 测试
stub（`_smoke_l3_gate.py:51/71/121`）的签名均为 `timeout` 带默认值，省略
传参安全。

**副作用（正向）**：因只有 `semantic.py` 放弃显式传值，
`semantic_timeout_s` 恰好只管 L3 语义审校（Phase A + gate 复检，两者共用
`_review_file`），字段名与实际覆盖范围精确吻合 —— 原「偏差 2（名称覆盖
范围偏宽）」随之消失。T1/T2/triage 维持各自硬编码值，行为不变（实测 T1
p50=14s / max=411s，无撞线证据，符合本轮「无证据不调参」原则）。

**遗留**：T1/T2/triage 的超时仍硬编码、脱离 config，属同一类结构问题但
不在本轮意图内 → 转 Step 5 suggest-list。

**偏差 3 — Step 4 未改 `ai_context/handoff.md`（PRE 计划要改）。**
本轮是配置级 hot-fix，未改变项目阶段 / 已有 / 当前 gap / 生效规则，也未改变
§下一步 的方向层路线图（"端到端跑通首个作品的提取管线"仍为高优先级）。
handoff §当前状态 明确界定「单任务进度归 `docs/todo_list.md`，不在这里」，
写入超时参数属噪音。改为按 #47 先例归档到
`docs/todo_list_archived.md ## Completed`（hot-fix 未上正向队列，跳过
In Progress 直接归档）。

**偏差 5 — Step 3 的 V7 验证项开得过窄，漏检（Step 5 Surface 复审捕获）。**
V7 原 grep 只查 `review_timeout_s` 标识符，漏掉散文式表述，致
`extraction/README.md` §子进程超时 的「Repair agent LLM 调用：600 秒
（10 分钟）超时」残留未被发现 —— 它与同一文件 §配置分段 新写的口径直接
矛盾。已用 `repair.{0,25}600|审校.{0,20}600` 等宽 pattern 重跑并修正。
教训：验证「grep 残留 = 0」时，pattern 必须覆盖散文表述而非仅标识符。

**偏差 4 — Step 4 追加修正 #47 的一处事实错误（PRE 未预见）。**
#47 原文称「`phase3.review_timeout_s` 保持 600s，服务它真正对应的 phase 3
reviewer 短链」。经本轮读码证实该短链不存在。#47 的核心（phase 0 解耦）
成立，不构成 supersede，故按 gap-fix 就地修正该句（`docs/decisions.md`
#47），并补一句指向 #64 的边界说明。`ai_context/decisions.md` 的 #47 索引
条目不含该错误表述，无需改动。

**修正记录（Step 5 Surface 复审捕获）**：本偏差的首版修正把该句改为
「服务 phase 2 per-lane repair 与 phase 4 scene split」—— **这个新表述同样
是错的**，且错因与本轮判定 3286 是死代码的推理完全同构（见偏差 2）：phase 2
的 `default_review_timeout` 从不被消费。准确口径 = **唯一真实消费者是
phase 4 scene split**（`scene_archive.py:429` 直接传值）。已再次修正 #47、
#64 边界段与偏差 1 的清单。教训：本轮识破了「显式传参 shadow 掉 default」
这一模式并据此定位根因，却未把同一推理应用到同一函数族的另一个注入点。

<!-- POST phase fills in -->

## Landed changes

L3 语义审校超时解耦到 `[repair].semantic_timeout_s = 1200`，并移除
`repair/checkers/semantic.py` 中 shadow 掉 config 的硬编码 `timeout=600`
（后者才是真正的根因 —— 没有它整个改动是 no-op）。预算改由注入方
（orchestrator，config 的所有者）持有，`repair/` 保持 config-agnostic。
决策 #64；#47 就地修正一处事实错误。T1/T2/triage 与
`[phase3].review_timeout_s` 按「无证据不调参」维持原状。

## Diff from plan

对照 PRE `## Planned action list`：

- **新增**（PRE 未预见，见偏差 2）：`extraction/repair/checkers/semantic.py`
  —— 去掉硬编码 `timeout=600` + `__init__` docstring 契约修正（Step 5 Code
  复审）。这是本轮唯一让改动真正生效的一处。
- **新增**（偏差 4）：`docs/decisions.md` #47 就地 gap-fix（两次修正，见偏差 4
  的修正记录）。
- **新增**（循 #47 先例）：`docs/todo_list_archived.md ## Completed` 归档条目
  T-REPAIR-SEMANTIC-TIMEOUT（hot-fix 未上正向队列）。
- **移除**（偏差 3）：`ai_context/handoff.md` 未改 —— 配置级 hot-fix 未改变
  项目阶段 / gap / 方向层路线图。
- **修改**：`extraction/README.md` 除 §配置分段 外，追加 §子进程超时 的过期
  表述修正（偏差 5，Step 5 Surface 复审捕获）。

## Validation results

- [x] `tomllib` 静态解析 `extraction/config.toml` — PASS
- [x] `load_config().repair.semantic_timeout_s == 1200` — PASS
      （`phase3.review_timeout_s` 仍为 600）
- [x] `orchestrator.py` 模块 import 无 error — PASS
- [x] `grep phase3.review_timeout_s` 仅剩 2 个引用点 — PASS
      （`scene_archive.py:429` 真实消费 / `orchestrator.py:2108` 死代码）
- [x] repair `_llm_call` 实际取到 1200 — PASS
- [x] **V5b（Step 3 追加）** `SemanticChecker` 实跑观测到的 timeout = 1200 —
      PASS。**本项是捕获 no-op 的唯一验证**：V1–V4 全绿却掩盖了改动完全
      无效，因它们只验到 config 层、未驱动真实调用路径。
- [x] `config.local.toml` 覆盖链对新键生效 — PASS（777 覆盖成功、还原回
      1200、无残留文件；兄弟键 `repair_concurrency` 不受影响）
- [x] 文档 grep 残留 = 0 — PASS（首轮因 pattern 过窄漏检，见偏差 5；已用宽
      pattern 重跑并修正）

smoke：`_smoke_l3_gate` PASS · `_smoke_4_lane_merge_and_slice` PASS ·
`_smoke_triage` **FAIL —— 既有破损**（已用 `git stash` 对照证实 HEAD 上以
完全相同的断言失败，与本轮正交；`5d9ef6f` 亦记录过）。

## Completed

- **Status**: DONE
- **Finished**: 2026-07-16 14:31:54 EDT
