# TODO 清单 <!-- holo:heading -->

<!-- holo:section start -->
---
<!-- holo:section end -->

## Index (auto-generated; do not hand-edit) <!-- holo:heading -->

<!-- holo:section start -->
> 本段是下方三个子表的缓存，由编辑某条目正文的人在正文段
> 进行任何 add / edit / segment-move / completion / abandonment
> 之后**立即**刷新。刷新规则参见 `## File guide → Index maintenance`。
> `/todo` skill（若使用）不解析正文 —— 它只读这份 Index，所以
> 本段必须与正文保持同步；这里漂移意味着 `/todo` 会给出错误答案。
<!-- holo:section end -->

### 🟢 In Progress (0)

_(none)_

### 🟡 Next (4)

| ID | Brief | Importance | Ready | Scope | Updated | Deps |
|---|---|---|---|---|---|---|
| `T-GATE-SCOPED-RECHECK` | 修完一个字段后系统会把整份文件重审一遍，每次挑出不同的毛病，于是修一个冒一个、白跑五轮才放弃，还攒出本不该有的待修债。改成只复检改过的地方——全文审一次就够了。 | 🔴 High | ⏸ Blocked | 🔴 Large·Arch | 2026-07-17 EDT | 等 effort 分档（#65）的基线对比 stage 跑完（单变量） |
| `T-REPAIR-TIMEOUT-CONFIG` | 修复环节还有三处超时值硬写在代码里、不读配置。上次就是这种硬编码让整个配置层静默失效、改了没反应。顺带清理一个名字叫 phase3 但实际只服务 phase4 的参数。 | 🟢 Med-Low | 💬 Discuss first | 🔴 Large·Arch | 2026-07-17 EDT | 无 |
| `T-SMOKE-TRIAGE-BROKEN` | 一个自动化测试在主干上一直是坏的（至少从包重构那次起）。要先弄清是测试过期了还是它测的功能真坏了——如果是后者，生产里可能一直在静默出错。 | 🟢 Med-Low | ✅ Ready | 🟡 Medium | 2026-07-17 EDT | 无 |
| `T-LIGHTNOVEL-SCHEMA-ONEOF` | stage_plan 里"一个 stage 包几章"这个数字，普通模式是 8-15、轻小说模式是 1。schema 现在只允许 ≥5，所以轻小说产物自己跑 schema 校验过不了——但实际没有外部校验它，所以是个已知缺陷不致命。 | 🟢 Med-Low | ⏸ Blocked | 🔴 Large·Arch | 2026-05-12 EDT | 等首个外部 artifact validator 消费方出现 |

### ⚪ Discussing (8)

| ID | Brief | Open decisions | Updated | Blocked by |
|---|---|---|---|---|
| `T-PHASE35-DEFERRED-FIX` | 决策 #60 落地了"记录不停机"——repair 修不平的 L3 语义残留写进 deferred_repairs 台账、stage 照常继续。本 todo 是那个"跑完全部 stage 后读台账逐条 field-level 精准修 + 复验"的收尾 pass（Part B），不重跑整个 stage。等真实台账数据积累后据此设计 fixer 形态。 | 4 | 2026-07-15 EDT | deferred_repairs 台账在真实运行中积累出样本 |
| `T-SEMANTIC-FULLFILE-COST` | 语义审校每次把整个文件读一遍，超过 5 万字符的部分直接丢掉不审——大文件的尾部从来没被检查过，而且这不是理论风险，每个 stage 都在发生。检查还吃掉了修复环节 92% 的开销：改一个字段却要通读全书。 | 4 | 2026-07-17 EDT | T-EFFORT-TIER-TUNING + T-GATE-SCOPED-RECHECK 的实测数据 |
| `T-SEMANTIC-UNPARSEABLE` | 审校跑完了但返回的内容不是合法格式，3 个 stage 里出现 2 次。这跟超时是两回事，加时间救不了。它还和真实内容问题混在同一个待修账本里，下游没法区分处理。 | 4 | 2026-07-17 EDT | 无（诊断可立即启动） |
| `T-REPAIR-EVENT-DRIVEN` | Phase 3 一抽完一个文件就立刻去修复、跟下一文件的抽取并行——理论最快。但实测算过只比当前方案省 4 分钟/stage，要为这点收益引入双线程池 + 撞限额风险，性价比太低。先做简单版（E1），等真实跑数据出来再决定要不要做这个。 | 0 | — | T-REPAIR-PARALLEL 先落地 |
| `T-PROMPT-SCHEMA-INJECT` | 项目约定"长度上限这种数字只在 schema 写一份"，但少数 prompt 和 doc 里仍有手写的数字（"150-200 字"之类）。万一 schema 改了，这些地方就会偷偷不一致。要么写代码让 prompt 自动从 schema 读，要么修约定明说"prompt 允许例外"。 | 3 | — | 无（路径决策即可启动） |
| `T-PHASE5-RETRIEVAL` | 好几份架构文档都在说"每部作品下应该有个 indexes/ 目录"，但实际没有任何阶段在生成它——目录在磁盘上压根不存在。打算加一个 Phase 5 专门做检索类产物（词典、关键词、向量索引、RAG 数据等）。等 phase 3 跑完 + 检索层设计定稿再启动。 | 5 | — | Phase 3 全量完成 + retrieval 层设计定稿 |
| `T-RETRY` | LLM 调用失败时的重试策略能更聪明些。现在不到 5 秒就失败的会重试，但人物抽取正常要跑 10-20 分钟，5 秒太短了——那种短时失败几乎都是启动错、不是真活干完才挂。打算扩到 60 秒，再按失败类型分流要不要重试。改动小，两个数值要拍板。 | 2 | — | 无（T-LOG 已完成） |
| `T-USER-AUX-SCHEMAS` | users/ 目录下有几个辅助 JSON 文件（session 索引、归档引用之类）没绑 schema，字段长啥样全靠模板猜。simulation 运行时一旦写起来要消费这些文件，到时候字段可能已经漂得不像样。等 simulation 选完 loader 设计再补 schema。 | 2 | — | simulation runtime loader 选型 / 设计定稿 |

**Total**: 12 — 🟢 In Progress 0 ｜ 🟡 Next 4 ｜ ⚪ Discussing 8

<!-- holo:section start -->
---
<!-- holo:section end -->

## File guide <!-- holo:heading -->

<!-- holo:section start -->
### 用途

记录**已计划但尚未完成**的具体工程任务。
与兄弟文件区分：

- `ai_context/handoff.md §Next Steps` —— 架构方向与高层路线图
  （按优先级的 2 列表格）。
- `ai_context/handoff.md §Current State` —— 当前项目状态快照
  （按方面的 2 列表格）。
- `logs/change_logs/` —— 历史（带时间戳，append-only）。
- `docs/architecture/` —— 正式架构文档。
- `docs/todo_list_archived.md` —— 已完成 / 已废弃任务的精简归档
  （完整细节存于 git 历史 + change logs）。

本文件是**工程层**的队列：文件路径、行号、
change manifest、验证步骤。

### 任务流转

```
Discussing ──(decided)──▶ Next ──(start)──▶ In Progress ──(commit done)──▶ archived ## Completed
                                                                            ▲
any node ─────────────────(abandoned)──────────────────────────── archived ## Abandoned
```

段位语义：

- **In Progress**（单槽）—— 已开始但尚未提交的任务。
  **同一时刻只有一条** —— 这样在工作被打断（ctrl-c / 暂停 /
  会话切换）时，下一个 AI 会话能直接看到"当前在做什么"，
  无需解析 git status 或进度文件。
- **Next** —— 依赖与设计均已就绪、随时可以开始的任务。
  按用户优先级排序 —— 第一条就是下一个要开始的。
- **Discussing** —— 仍有待决策项 / 外部依赖 / 设计未定的任务。
  不要开始；先把决策收敛掉。

### 记录什么

✓ 文件 / 函数级别的具体改动任务。
✓ 每条目必须包含：**Context**（动机 + 当前状态 +
  trigger）、**Change manifest**（文件路径 + 行号；在 `Discussing`
  中可以是部分的）、**Done criteria**、**Deps**。
✓ 视情况：**Open decisions**（在 `Discussing` 中必填）、
  **Estimate**、**Why not landed yet**、**Out of scope**。
✓ **Requirements**（可选；位置在 **Context** 与 **Change manifest**
  之间）：用户要做什么 / 要达成什么效果。纯文字段，无特殊格式规则。
  本会话收敛了值得保留的用户需求时填。
✓ **Solution details**（可选；位置在 **Requirements** 与
  **Change manifest** 之间）：最终落定的方案是什么、由哪些部分组成。
  **只装最终落定版** —— 不写废弃方案、不写否决备选、不写讨论历史。
  纯文字段，无特殊格式规则。本会话收敛了值得保留的具体方案时填。
✓ 在 `Discussing` 条目中，列出未解决的选项及其权衡。

### 不记录什么

✗ 架构方向 / 高层路线图 → `ai_context/handoff.md §Next Steps`（2 列表格）。
✗ 已完成 / 已废弃任务 → 移到 `docs/todo_list_archived.md`（精简）。
✗ 临时调试笔记 / 思考过程中的分析 → 放到对话或 plan 里，
  不要持久化。
✗ 运行时状态 / 进度 → 写到运行时进度产物里
  （参见 `ai_context/skills_config.md` §Background processes）。

### 如何更新条目

**所有段位通用**：每个 `### [T-XXX]` 块都必须有
**Updated** 时间戳（`YYYY-MM-DD HH:MM` + 时区，遵循
`ai_context/skills_config.md` §Timezone）。创建时设置；
任何正文字段被修改或条目在段位间移动时刷新。
**只刷新 Index 缓存不算** —— 该字段标记的是"正文实际变更的时间"。

**添加新任务**：放入合适的段位（Next 或
Discussing）。新条目必须包含 "What to record" 中的字段，
加上 `**Updated**`。**不要直接加进 "In Progress"** ——
该段位只有任务实际开始时才填入。

**任务开始（移入 In Progress）**：
1. 把整条目从 "Next" 移到 "In Progress"。
2. 添加 `**Start time**`（同样的时间戳格式）和 **Current state**
   （in-progress / awaiting decision / paused）。
3. 刷新 `**Updated**` = start time。
4. **单槽** —— 如果 "In Progress" 已被占用，
   先完成或显式 pause-back 那条任务。
5. 刷新 Index（参见 "Index maintenance"）。

**任务完成（已 commit + 已验证）**：
1. 把条目移到 `docs/todo_list_archived.md` `## Completed`
   （精简条目：标题 + completion form + 一行总结 + log 链接）；
   从本文件删除。
2. 如果该任务产生了持久结论 / 新的架构
   决策 / 可复用洞见，写一份
   `logs/change_logs/YYYY-MM-DD_HHMMSS_slug.md`。
3. 如果完成会改变 `ai_context/` 中的持久事实（`handoff.md` 的
   Current State / Next Steps 表，或 `decisions.md`），相应更新。
4. 刷新 Index。

**任务废弃**：写一份 `logs/change_logs/` 条目说明原因，然后
把条目移到 `docs/todo_list_archived.md` `## Abandoned`（同样的
精简格式）。刷新 Index。

**讨论落地**：当一条 `Discussing` 条目得出结论时：
- **完整决策** —— 把条目移到 `Next`，补齐缺失的
  字段（Change manifest / Done criteria / Deps）。刷新 Index。
- **部分决策** —— 把已决策的子任务拆成独立的
  `Next` 条目；未决的余下部分留在 `Discussing` 中，
  context 已更新。刷新 Index。
- **结论使现有 `Next` / `In Progress` 任务失效**
  —— 当作 "任务废弃" 处理。

### Index maintenance

文件顶部的 `## Index (auto-generated; do not hand-edit)` 段
缓存了三个子表。**在正文进行任何 add / edit /
segment-move / completion / abandonment 之后刷新。** `/todo`
skill 只读这一段。

**触发**刷新 —— 以下任一：

- 添加新条目。
- 编辑现有条目的标题、context 摘要、deps、open
  decisions、change-manifest 文件数、schema/architecture/multi-phase
  涉及范围、或 `**Updated**`。
- 段位移动：Discussing → Next、Next → In Progress、In Progress →
  archived、any → archived（废弃）。
- `In Progress` 条目内的 "Current state" 变更。

**列定义**：

**In Progress**

| Column | Source |
|---|---|
| ID | 反引号包起来的 T-XXX slug |
| Title | 方括号之后的人类可读短语 |
| Start time | 条目的 `**Start time**` 字段，完整时间戳 |
| Updated | 条目的 `**Updated**` 字段，仅日期（不含 HH:MM）；缺失 → `—` |
| Status | 条目的 `**Current state**` 值 |

**Next**

| Column | Source |
|---|---|
| ID | 反引号包起来的 T-XXX slug |
| Brief | Context 的第一句 + 1–2 行关键背景。**总长度 ≤ 150 字符。** 去掉 markdown 链接反引号以便表格渲染，但保留 `[text](url)` 形式。 |
| Importance | 🔴 High / 🟡 Medium / 🟢 Med-Low（规则见下） |
| Ready | ✅ Ready / 💬 Discuss first / ⏸ Blocked（规则见下） |
| Scope | 🟢 Small / 🟡 Medium / 🔴 Large·Arch / —（规则见下） |
| Updated | 条目的 `**Updated**` 字段，仅日期 |
| Deps | 条目 `**Deps**` 字段的第一句 |

**Discussing**

| Column | Source |
|---|---|
| ID | 反引号包起来的 T-XXX slug |
| Brief | 同 Next，≤ 150 字符 |
| Open decisions | `**Open decisions**` 下 bullet 项的数量；缺该段 → 0 |
| Updated | 条目的 `**Updated**` 字段，仅日期 |
| Blocked by | `**Deps**` 的第一句 |

**推断规则**（确定性 —— 不要自由发挥）：

**Importance**（仅 Next）

| Level | Trigger |
|---|---|
| 🔴 High | 用户已标记为高优先级 OR 阻塞其他任务 |
| 🟡 Medium | 既未标 High 也未标 Med-Low 的默认 |
| 🟢 Med-Low | Deps 被阻塞 OR open decisions ≥ 2 OR 用户未标过优先级 |

**Ready**

| Tag | Trigger |
|---|---|
| ✅ Ready | Deps 已就绪 AND open decisions = 0 |
| 💬 Discuss first | Open decisions ≥ 1 |
| ⏸ Blocked | Deps 中含具体阻塞项（外部 CLI、未实现模块、待发生事件） |

优先级：⏸ > 💬 > ✅。

**Scope**

| Size | Trigger |
|---|---|
| 🟢 Small | Change manifest ≤ 2 个文件 AND 无 schema / interface 改动 |
| 🟡 Medium | Change manifest 3–6 个文件 OR 模块内多函数 refactor；无架构层改动 |
| 🔴 Large·Arch | Change manifest ≥ 7 个文件 OR 触及：新 phase / schema field / 核心 interface / 跨模块协议 / 新依赖 |
| — | 缺 change manifest（在未拆解的 `Discussing` 条目中常见） |

**Brief 写作规则**：用大白话写 —— 这件事解决什么
问题、为什么值得做。**避免代号 / 函数名 /
schema 路径 / 行号 / 决策编号 / 行话**，除非
它们本身就是问题。总长度 ≤ 150 字符；超出时砍掉
细节，直到只剩 "what + why"。

**Summary line**：三个表之后，打印一行：
`Total: N — 🟢 In Progress a ｜ 🟡 Next b ｜ ⚪ Discussing c`。

### 何时阅读

- 用户问待办 / 接下来做啥 → `/todo` skill（只读
  Index）。
- 开始任何改动之前，**读一次**避免
  重复规划。
- 在讨论某个可能已在此跟踪的话题时。
- **默认不加载** —— 不属于 `ai_context/`
  会话启动阅读顺序。

---
<!-- holo:section end -->

## In Progress <!-- holo:heading -->

<!-- holo:section start -->
<!-- Single-slot. Filled only when a task is actually started.
     Format: see "How to update entries → Task starts". -->
<!-- holo:section end -->

## Next <!-- holo:heading -->

<!-- holo:section start -->
<!-- Ordered by user priority. First entry is the next to start.
     Format: see "What to record". -->
<!-- holo:section end -->

### [T-LIGHTNOVEL-SCHEMA-ONEOF] light_novel `chapter_count=1` schema 正式契约化

**开始时间**：2026-05-12 EDT（决策 #56 复审时确认推迟）

**当前状态**：Discussing（无外部消费方，决策 #27n 现状保留；本 todo 是预备工作，等首个外部 validator 出现时启动）

**上下文**

decision #27n 把 `stage_plan.chapter_count=1` 在 schema 下 schema-invalid 标记为已知 trade-off：light_novel 模式 orchestrator 程序化 1:1 派生不走 schema validate，事实上没有外部消费方校验该产物。codex `gpt-5` 2026-05-12 复审报告 OQ3 指出：如果未来出现外部 artifact validator 独立校验 `stage_plan.json`，这会重新变成契约问题。

**改动清单（设计）**

- file: `schemas/analysis/stage_plan.schema.json`：改 `stages.items.chapter_count` 为 `oneOf`，按结构模式分支
  - monolithic: `minimum=8, maximum=15`
  - light_novel: `minimum=1, maximum=1`
- file: `extraction/persona_extraction/_build_light_novel_stage_plan`：产物加 `structure_mode` 字段供 schema dispatch（或在外层 manifest 索引）
- file: `extraction/validation/gates/phase2_baseline.py`：派生产物现在走 schema validate
- file: `docs/architecture/schema_reference.md` + decision #27n + #56：trade-off 文案改写为已契约化

**完成标准**

- monolithic / light_novel 两路产物 schema validate 都过
- 增加 fixture 测试：light_novel 产物 schema 校验过；monolithic 含 chapter_count=1 的非法产物校验失败

**依赖**

- 等首个外部 artifact validator 消费方出现（如独立离线校验工具 / 第三方对接），否则推动力不足

**暂不做的事**

- 决策 #56 复审 OQ3 用户拍板"留 todo"——本轮不动 schema

---

### [T-GATE-SCOPED-RECHECK] L3 gate 复检改定点：全文审校一次，之后只复检改过的地方

**上下文**

2026-07-16 挂机跑 S003 时逐行拆 repair 循环，发现一个**正确性缺陷**（不只是
慢）：**每轮末的 L3 gate 把整份 50k 字符文件重读一遍复检，导致打地鼠循环**。

单个 round 的实测拆分（`Character A/canon/stage_snapshots/S003.json`）：

```
Fix round 1 — 2 issues
  T2 定点修复 #1  →  18s
  T2 定点修复 #2  →  16s
  L3 gate 全文复检 → 4m36s          ← 8 倍不对称
Round 1 result: resolved=2, persisting=0, introduced=1
```

而 `introduced` 的定义是**指纹集合差**（`repair/tracker.py:30`）：

```python
introduced = [curr_fps[fp] for fp in curr_fps if fp not in prev_fps]
```

**任何"上轮没有、这轮有"的 issue 都算 introduced，不管是不是修复造成的。**
全文复检每轮重读整份文件，LLM 审校本身不确定，每次挑出的毛病天然不同 →
新指纹 → 算 introduced → 循环继续。实测某文件连续四轮：

```
Round 1: resolved=2, persisting=0, introduced=1
Round 2: resolved=1, persisting=0, introduced=1
Round 3: resolved=1, persisting=0, introduced=1
Round 4: resolved=1, persisting=0, introduced=1
Fix round 5 — No patches applied — stopping   → FAIL
```

**修复根本没搞坏任何东西——是复检自己每轮换了个目标。**

**更糟：两个安全阀对这个模式全盲。**

- `is_regression()` = `len(introduced) > len(resolved)` → `1 > 1` = False
- `is_stalled()` = persisting 两轮相同 **且** `len(curr_fps) > 0` →
  persisting 恒为 0 → False

`resolved=1 / introduced=1 / persisting=0` 恰好从两阀中间穿过，**每次跑满
`total_round_limit=5` 然后判 FAIL**，攒出本不该有的 defer 债（S003 的 4 条
defer 里 `inconsistent_relationship_type` / `realm_label_contradiction` /
`missing_true_state_change` 高度疑似由此而来）。

**用户 2026-07-17 的判断**：「全文审查一次就够了，之后应该是修啥复审啥」。

**关键陷阱**：`repair/checkers/semantic.py:96` 已有 `check_scoped(files, paths)`
方法，docstring 明写 `"""Re-check only specific json_paths (for final
verification)."""`——**但全仓零调用方，是死代码**（gate 走的是 `check`，全文）。
而且**它现成的实现并不能解决问题**：

```python
file_issues = self._review_file(f.path, content, focus_paths=paths)
#                                        ^^^^^^^ 仍传全量 content
issues.extend(file_issues)   # ← 不过滤返回值
```

它只在 prompt 末尾加一句 `Focus review on these paths: ...`——**是软提示、不是
硬约束，且返回值不过滤**。LLM 完全可能照样报 focus 之外的问题，打地鼠继续。
**真正的根治必须在代码层过滤 gate 结果到本轮实际改过的 json_path。**

**要做什么**

让 gate 的职责回归「我这一刀改对了吗」，而不是「再审一遍全书」——Phase A
已经做过全文审计了。

**改动清单**

- file: `extraction/repair/coordinator.py:~415`（`if config.l3_gate_enabled
  and config.run_semantic and gate_targets` 那处）→ gate 改调
  `check_scoped(files, paths=<本轮改过的 json_path 集合>)`，不再走
  `run_layer → check`
- file: `extraction/repair/coordinator.py` → 收集"本轮实际改过的 json_path"
  （T0/T1/T2 各 fixer 的 `FixResult` 已带 patch 信息，需确认是否已暴露改过的
  path；若无则补）
- file: `extraction/repair/checkers/semantic.py:96 check_scoped` →
  **返回值按 `paths` 过滤**（程序保证，不指望 LLM 听 focus 提示）；同时
  评估 prompt 里 focus 段是否需要加严成硬约束
- file: `extraction/repair/tracker.py:47-58` → **scoped 之后 `introduced` /
  `is_regression` 的语义必须重想**。scoped gate 只看改过的 path，`introduced`
  的含义从"文件里冒出个新问题"变成"我这一刀改出了新问题"——那才是回归的真定义。
  `is_stalled` 的 `len(curr_fps) > 0` 守卫也要复核（persisting 恒 0 的场景）
- file: `extraction/repair/tests/_smoke_l3_gate.py` → 补 scoped gate 的场景：
  (a) 修复成功 → scoped 复检 0 issue → 早退不再跑满 5 轮；
  (b) 修复真的引入了新问题（改过的 path 上）→ 仍被 `introduced` 抓到
- file: `ai_context/decisions.md` + `docs/decisions.md` → 新增决策条目（gate
  职责边界 = 验证本刀，不是重新审计；放弃"修 A 是否搞坏 B"的跨 path 检测能力
  是有意取舍——Phase A 已覆盖，且现状那个能力实际报的是审校抖动不是真回归）
- file: `docs/requirements.md` §11.4 repair 三阶段描述 → gate 语义同步
- file: `docs/architecture/extraction_workflow.md` → 同步

**完成标准**

- 跑至少 1 个完整 stage，与基线对比 **round 数**（基线：S003 单文件最多 5 轮
  且撞 `total_round_limit`；期望降到 1–2 轮）
- 不再出现 `resolved=N, persisting=0, introduced=N` 的连续打平模式
- repair 墙钟下降（基线 S001 27min / S002 31min / S003 38min）
- **defer 债不增加**，且 defer 的 rule 分布里不再出现「每轮换一个目标」的痕迹
- `_smoke_l3_gate` 新增场景全过

**依赖**

- **必须等 effort 分档（决策 #65）的基线对比 stage 跑完再单独 `/go`**——单变量：
  effort 降档的提速幅度尚未实测，两条混在一起就分不清耗时变化的归因
- 与 T-SEMANTIC-FULLFILE-COST 相关但正交：本条改的是**每轮 gate 复检**；那条
  讨论的是 **Phase A 全量检查**读全文 + 50k 截断的问题。Phase A 保持全文是本条
  的前提（用户要的是「全文审查一次」）

**更新时间**：2026-07-17 06:51 EDT

---

### [T-REPAIR-TIMEOUT-CONFIG] repair 的超时值统一进 config + `review_timeout_s` 命名归属清理

**上下文**

决策 #64（2026-07-16）把 L3 语义审校的超时解耦到
`[repair].semantic_timeout_s` 并去掉 `checkers/semantic.py` 里 shadow 掉
config 的硬编码。但**同类问题在另外三处仍然存在**——`repair/` 内其余调用点
都还在传硬编码 timeout，全都不读 config：

| 调用点 | 硬编码值 | 用途 |
|---|---|---|
| `fixers/local_patch.py:106` | 600 | T1 定点修复 |
| `fixers/source_patch.py:122` | 600 | T2 原文修复 |
| `triage.py:370` | 300 | triage |

这违反 `ai_context/conventions.md §Single Source of Truth`（运行时常量的权威
位置是 config 文件）。#64 的教训是：**硬编码会 shadow 掉 config，让整个配置
层静默失效**——那次 `orchestrator` 的 `default_timeout` 因此成了死代码，改
config 完全不产生效果，直到 runtime 验证才发现。这三处是同一个雷。

**附带的命名问题**：#64 落地后 `[phase3].review_timeout_s = 600` 只剩 2 个
引用点，且**都不属于 phase 3**：

- `phases/scene_archive.py:429` → **phase 4** scene split：**唯一真实消费者**
  （`timeout_seconds=cfg.phase3.review_timeout_s` 直接传值）
- `orchestrator.py:2108` → **phase 2** per-lane repair 的
  `default_review_timeout`：**同属死代码**——#59 缩水版关掉 `run_semantic` /
  `l3_gate` / `triage` 且 `t2_max=0`，phase 2 唯一可达的 LLM 调用是 T1
  `local_patch`，而它显式传 `timeout=600` ⇒ 该 default 从不被消费

即**一个名为 `[phase3]` 的参数实际只服务 phase 4**。#47 已经就地修正过一次
它的错误描述（原称"服务 phase 3 reviewer 短链"——该短链不存在）。

**要做什么**

把三处硬编码超时收进 config；顺带清理 `review_timeout_s` 的命名与归属。

**改动清单**

- file: `extraction/persona_extraction/core/config.py::RepairAgentConfig` →
  新增 `t1_timeout_s: int = 600` / `t2_timeout_s: int = 600` /
  `triage_timeout_s: int = 300`（与 `semantic_timeout_s` 并列）
- file: `extraction/config.toml` `[repair]` → 三个同名键 + 中文注释
- file: `extraction/repair/fixers/local_patch.py:106` /
  `fixers/source_patch.py:122` / `triage.py:370` → 去掉显式硬编码，改由注入方
  持有预算（与 #64 对 `semantic.py` 的处理形态一致：`repair/` 保持
  config-agnostic，`orchestrator` 的 `_llm_call` 按调用类型给默认值）。
  **注意**：这与已定的方案 A（effort 由调用点自己传，决策 #65）方向相反——
  落地前需先想清楚 timeout 和 effort 是否该用同一种归属模型，避免同一函数上
  两个参数两套哲学
- file: `extraction/persona_extraction/core/config.py::Phase3Config` +
  `extraction/config.toml [phase3]` → `review_timeout_s` 重命名 / 移段
  （候选：移到 `[phase4]` 作 `scene_split_timeout_s`，因为唯一消费者是
  phase 4 scene split）
- file: `extraction/persona_extraction/orchestrator.py:2108` → 删除死代码
  `default_review_timeout`（或在 phase 2 repair 接入 config 化的 timeout 后
  让它真正生效——二选一，需拍板）
- file: `extraction/persona_extraction/phases/scene_archive.py:429` → 跟随
  重命名
- file: `ai_context/decisions.md` + `docs/decisions.md` → #47 / #64 的边界
  描述同步（#64 现在写着「唯一真实消费者是 phase 4 scene split」，重命名后要改）
- file: `extraction/README.md` + `docs/requirements.md` +
  `docs/architecture/extraction_workflow.md` → 配置分节表同步

**完成标准**

- `grep -rE "timeout=[0-9]+" extraction/repair/` 命中 0（全部走 config 或注入方）
- `grep -rn "phase3.review_timeout_s" extraction/` 命中 0
- `load_config()` 能读到全部新键；`config.local.toml` 覆盖链对新键生效
- smoke 全过；**行为不变**（同样的值，只是来源从硬编码变成 config）

**依赖**

- 无前置。effort 的归属模型已定为方案 A（决策 #65），本条要么沿用同一模型、
  要么明确论证 timeout 为何该不同——见上方 change list 的「注意」
- 纯 refactor，无行为变化，可随时插队

**暂不做的事**

- 不动数值本身（`semantic_timeout_s` = 900 已由决策 #64 定案）
- 不给 phase 2 repair 接 L3（#59 缩水版是有意设计）

**更新时间**：2026-07-17 06:51 EDT

---

### [T-SMOKE-TRIAGE-BROKEN] `_smoke_triage` 在 HEAD 上即坏（既有破损）

**上下文**

`python -m extraction.repair.tests._smoke_triage` 在 HEAD 上失败：

```
File "extraction/repair/tests/_smoke_triage.py", line 157, in scenario_a_pre_t3_accept
  assert result.accepted_notes, "expected at least one accepted note"
AssertionError: expected at least one accepted note
[A] passed=False  notes=0  T3 regen calls=0  triage calls=0
```

**已用 `git stash` 对照证实与近期改动无关**——把 #64 的改动 stash 掉后，HEAD
上以**完全相同的断言**失败。commit `5d9ef6f`（extraction 包重构）的 message
里也记录过「smoke 6/7 全过（`_smoke_triage` HEAD 即坏，正交）」，说明它至少
从那时起就是坏的。

场景名 `scenario_a_pre_t3_accept` 里的 `pre_t3` 暗示它写于 T3 全文重跑还存在
的年代；决策 #62（`010fb03`，2026-07-15）已删除 T3 与 `file_regen.py`。输出里
`T3 regen calls=0` 也印证了——**这个测试很可能是在测一个已经不存在的路径**。

**要做什么**

先诊断是"测试过期"还是"triage 真坏了"，再决定修测试还是修代码。这个判断很
重要：如果是后者，那 triage 的 `source_inherent` 接受路径在生产里一直是坏的
而没人知道（`triage_enabled = true` 是本项目的现行配置）。

**改动清单**

- file: `extraction/repair/tests/_smoke_triage.py:157`（`scenario_a_pre_t3_accept`）
  → 起点：为什么 `accepted_notes` 是空的
- file: `extraction/repair/triage.py` → 被测对象，确认 `source_inherent`
  接受路径是否仍按契约工作（`triage_accept_cap_per_file = 5`）
- file: `extraction/repair/coordinator.py` → triage 的调用点与结果消费
- 判定后二选一：
  - **测试过期** → 重写场景对齐 #62 后的三层就地修复形态（删 T3 相关断言）
  - **代码坏了** → 修 `triage.py`，并复核生产里是否已经有被静默吞掉的
    `source_inherent` 接受（查 `works/*/characters/*/canon/extraction_notes/`
    有没有 SourceNote 落盘）

**完成标准**

- `python -m extraction.repair.tests._smoke_triage` 全过
- 如判定为"代码坏了"：给出生产影响面评估（有多少 stage 的 triage 接受被静默
  吞掉），并在 `ai_context/decisions.md` 记录

**依赖**

- 无（独立，可随时做）

**更新时间**：2026-07-17 06:51 EDT

---

## Discussing (Undecided) <!-- holo:heading -->

<!-- holo:section start -->
<!-- Tasks with open decisions / external deps / unsettled design.
     Don't start; converge the decision first.
     Format: see "What to record" + "Open decisions" section mandatory. -->
<!-- holo:section end -->

### [T-PHASE35-DEFERRED-FIX] Phase 3.5 收尾精准修复 pass（消费 deferred_repairs 台账）

**上下文**

决策 #60 落地了 record-and-continue：repair 修不平的 L3 语义残留不再停机，
写进 `works/{work_id}/analysis/deferred_repairs/{stage_id}.jsonl`（随 stage
commit），stage 照常继续。但**只记录、还没修**——本 todo 是那个"跑完全部
stage 后逐条精准修"的收尾 pass（决策 #60 显式登记的 Part B）。

**要做什么**

- 读取全部已 commit 的 `deferred_repairs/*.jsonl`（每行含
  file/json_path/category/severity/rule/message）。
- 对每条 issue 做 field-level 精准修（复用 `repair/field_patch.py` 的
  `apply_field_patch(json_path)` + `context_retriever` 取原文），修完复验
  （L3 gate），不重跑整个 stage。
- 修成的从台账移除；仍修不平的保留 + 标记，供人工兜底。
- 定位：跑在 Phase 3 全部 COMMITTED 之后（Phase 3.5 一致性检查前后待定），
  作为独立 pass / CLI 子命令。

**待决策项**

1. 触发形态：并入现有 Phase 3.5（`validation/gates/phase3_5_consistency.py`）
   还是独立 CLI 子命令 / `--start-phase` 变体？
2. fixer 预算：给比行内 repair 更强的预算吗（更多轮次 / 允许 T3 / 跨 stage
   全局上下文）——这正是延后的价值所在。
3. 修完的 stage 要不要重新 commit（amend 该 stage 的 commit 还是追一个
   `phase3.5-fix` commit）？下游 stage 已基于旧数据抽取，传播如何兜底
   （靠 Phase 3.5 一致性检查，还是要局部重抽受影响 stage）？
4. 台账"同类错反复出现"的聚合诊断——是否顺便产一个汇总，指导回改提取
   prompt？

**未落地原因**

- 先让真实台账数据积累（跑几个 work / 几十个 stage），据此判断残留语义错
  的真实分布与可 field-level 修复的比例，再定 fixer 形态；过早设计易脱靶。

**暂不做的事**

- 本轮（决策 #60）只做"记录 + 不停机"，不碰任何自动修复逻辑。

**依赖**：deferred_repairs 台账在真实运行中积累出样本

---

### [T-REPAIR-EVENT-DRIVEN] Repair 事件驱动 · extract→repair overlap（E2）

**上下文**

T-REPAIR-PARALLEL 的 E1 方案把 stage 总耗时从 69m 压到 ~32m（extract
22m + repair ~10m）。E2 方案进一步把每个 lane 完成后的文件立刻触发
repair，与后续 lane 的 extract 时间重叠，理论最优解。

**讨论结论（2026-04-22）**: **暂不做**，先做 E1。

**为什么暂不做**

- S001 实测 11 个文件里 **6 个是 post-processing 一次性生成的 digest /
  catalog**，都卡在 extract 全完（t=22m）之后才能进 repair 池
- E2 wall-clock 估 28m vs E1 32m，**只省 4min/stage**，49 stage 省 ~3h
- 代价：双 ThreadPoolExecutor（extract 池 + repair 池）+ 事件回调触发 +
  peak 并发 9 撞 rate limit 的管理。复杂度跳一档
- 要真正吃到 E2 红利，post-processing 也要改成 per-lane 触发
  （每 lane 完成就跑自己的 digest/catalog 更新），这是另一个重构
- 3h 收益 vs 重构成本，不划算

**何时重启讨论**

- E1 落地后跑若干 stage，观察真实 extract 与 repair 的耗时比
- 如果发现 extract 瓶颈 lane 远长于 repair（例如 extract 45m + repair 10m），
  overlap 收益会拉大，值得重评
- 或者 post-processing 因其他原因要改成 per-lane 触发时，顺带做 E2

**依赖**：T-REPAIR-PARALLEL 先落地

---

### [T-PROMPT-SCHEMA-INJECT] prompt 模板从 schema 自动注入具体 bound

**上下文**

`ai_context/conventions.md` §"Bounds only in schema" 要求所有
`maxLength` / `minLength` / `maxItems` 数值只在 schema 写一次。但
`extraction/persona_extraction/prompts/character_support_extraction.md` /
`character_snapshot_extraction.md`、`docs/architecture/extraction_workflow.md`
和 `docs/architecture/schema_reference.md` 的少量段落仍复述具体数字
（`150–200 字`、`30–50 字`、`≤15 字短语`、`最多 5 条` 等）。当前抽查
数值与 schema 一致，是 drift risk 而非 runtime bug——但每次 schema 改
bound 都要扫一遍 prompts。

**待决策项**

1. 严格对齐路径（A）：所有 prompt 改写为"见 schema"，schema_reference.md
   清理残留——prompt 需配套从 schema 自动生成具体 bound 段（运行时注入）。
   工程量：在 `prompt_builder.py` 增加 schema → bounds 段渲染。
2. 例外条款路径（B）：修订 conventions.md，允许 prompt template 复述
   schema bound，但 Cross-File Alignment 表已经把 prompts 列入 schema
   改动联动行——文档级承认 + 改 bound 时同 commit 镜像更新。
3. 选 A 时是否同时为 schema_reference.md 的具体值清理写一次性
   sweep（一次性脚本扫 grep）。

**改动清单（待路径选定后）**

- 路径 A：`extraction/persona_extraction/prompt_builder.py` 增加
  `render_schema_bounds(schema_path, fields=[...])` 渲染段；prompt
  template 把具体 bound 替换为 `{schema_bounds_for_X}` 占位符
- 路径 B：`ai_context/conventions.md` §"Bounds only in schema" 加例外
  条款（"prompt template 是允许例外，但 schema 改 bound 时同 commit
  镜像更新"）；schema_reference.md 残留的具体值仍清理为"见 schema"

**暂不做的事**

- 不双轨——选定路径前不动 prompt 数字

**依赖**：无（路径决策即可启动）

**未落地原因**

- 当前 schema bound 稳定，drift 风险尚未触发；优先级低于 H1–H4 体系问题

---

### [T-PHASE5-RETRIEVAL] 新增 Phase 5 生成 retrieval 产物

**上下文**

多处 canonical docs 宣称 `works/*/indexes/` 是 committed 产物
（`ai_context/requirements.md`、`ai_context/decisions.md` #38/#42、
`docs/architecture/data_model.md:160,475`、
`docs/architecture/system_overview.md:36,326`），但当前没有任何 Phase
承担生成职责——首作 `works/{work_id}/indexes/` 目录在磁盘上不存在。

计划：新增 **Phase 5**，专责生成 retrieval 相关产物，统一承接现在散落的
缺口。覆盖范围初定：

- `works/{work_id}/indexes/vocab_dict.txt`（jieba 自定义词典）
- 关键词 / 专名抽取结果
- 索引数据库（FTS5 / 其他）
- RAG 相关 embedding / chunking 产物
- 其它 retrieval 层启动所需的预计算产物

**待决策项**

1. Phase 5 的产物是 committed 还是 local-only？
   - 若 committed：需决定 `vocab_dict.txt` / 关键词表等是否落仓；
     体积上限？
   - 若 local-only：`.gitignore` 加 `works/*/indexes/`；删除 ai_context /
     docs 中"committed"叙述
2. Phase 5 入口：独立 CLI 子命令 vs. `--start-phase 5`？
3. 触发门控：是否要 Phase 3.5 passed 才能进 Phase 5？（类比 Phase 4
   的独立性）
4. 与运行时 retrieval 实现的边界：Phase 5 产 artifact，运行时消费——
   但 embedding 模型选型 / chunking 策略需先定好
5. 并行度：是否复用 Phase 4 的 per-chapter 并行模式？

**未落地原因**

- retrieval 层整体设计尚未动工（见 `ai_context/handoff.md` §当前状态
  gap：无检索实现）
- Phase 3 仍在进行（1/49 committed），且即将回滚重跑，Phase 5 要等
  Phase 3 真正完成有完整 stage_snapshots 作为源

**暂不做的事**

- 不改 ai_context / docs 里"committed indexes"的叙述（等 Phase 5
  落定后再批量同步，否则来回改噪声大）
- 不把 `works/*/indexes/` 加入 `.gitignore`（决策未定）
- 不要把 `vocab_dict.txt` 硬塞进 Phase 2 / Phase 3.5（B 方案已否决：
  两 Phase 本职不是 retrieval，硬塞会扭曲 Phase 边界）

**依赖**：Phase 3 全量完成 + retrieval 层设计定稿

---

### [T-RETRY] claude -p 失败的智能重试策略

**上下文**

T-LOG 已落地：[llm_backend.py:565-680](../extraction/persona_extraction/core/llm_backend.py#L565-L680) `run_with_retry` 已能解析 subtype / num_turns / total_cost_usd 并附在 LLMResult 与错误消息上。但 retry 决策本身**还没用上 subtype 分流**，且短时阈值仍是 5s（[config.toml:130](../extraction/config.toml#L130) `fast_empty_failure_threshold_s = 5`）。

**现有机制**（截至 2026-04-27）

| 错误类型 | 识别 | 处理 | 状态 |
|---|---|---|---|
| `fast_empty_failure` | duration < 5s + stderr 空 + exit N | 按 backoff 序列重试（30s/60s/120s） | ✅ 已实现 |
| `rate_limit` / `usage_limit` | stderr 含 "rate limit" / "weekly" / "5-hour" / "too many requests" | 暂停所有新请求直到 reset，重发同一 prompt（不消耗 retry slot，§11.13） | ✅ 已实现 |
| `token_limit` | stderr 含 "context window" / "max_tokens" 等 | 不重试 | ✅ 已实现 |
| 通用长时 exit N | stderr 空 + duration 长 | 不重试（直接 return） | ⚠️ 当前未按 subtype 分流 |

**待落地（具体改动）**

1. **短时阈值扩大**：[config.toml:130](../extraction/config.toml#L130) `fast_empty_failure_threshold_s` 从 5s 扩大到 60s（候选 120s）。
   - 理由：char_snapshot 正常 10-20m，任何 <60s 失败几乎一定不是真正工作后失败，是 CLI launch / API 连接错误。
   - 风险极小（<60s 浪费），独立可先行
2. **长时 exit 按 subtype 分流**：[llm_backend.py `run_with_retry`](../extraction/persona_extraction/core/llm_backend.py) 在"非可重试错误"return 之前加一段判断：
   - `subtype == "error_max_turns"` → 不重试（同 prompt 必再次触达）
   - `subtype == "error_during_execution"` → 重试 1 次（瞬态可能性大）
   - 无 subtype / 解析失败 → 可选重试 1 次（默认开 / 可由 config 关）
3. **退避策略不动**：30s/60s/120s 已合理

**改动清单**

1. [extraction/config.toml:130](../extraction/config.toml#L130) 改 `fast_empty_failure_threshold_s = 60`（或 120，待拍板）
2. [extraction/persona_extraction/core/llm_backend.py `run_with_retry`](../extraction/persona_extraction/core/llm_backend.py) 加 subtype 分流分支
3. 新增 config 项 `[backoff].long_exit_retry_subtypes`（白名单）或对应布尔开关，默认 `["error_during_execution"]`
4. 单测覆盖三类 subtype 的决策路径
5. [docs/requirements.md §11.x](requirements.md) 重试策略小节同步

**待决策项**

1. 短时阈值定 60s 还是 120s？
2. 无 subtype 时默认重试 1 次，还是默认不重试？

**完成标准**

- 短时阈值落地
- subtype 分流生效（单测过 + 真实失败样本验证至少一类）
- 本 todo 条目移到 archived

**预估**：S（半天 - 1 天）

**依赖**：无（T-LOG 已完成）；可基于 `failed_lanes/` 日志样本辅助决策

---

### [T-USER-AUX-SCHEMAS] users/ 辅助文件缺 schema

**上下文**

2026-04-20 codex audit (residual R3) 指出 users/ 下若干辅助文件无 schema
绑定，在 runtime 真正落地前最容易继续自由漂移：

- `users/_template/contexts/{context_id}/session_index.json`
- `users/_template/conversation_library/archive_refs.json`

**待决策项**

1. 每个辅助文件是否都要独立 schema，还是由总目录层级 schema 一并约束？
2. schema 发布顺序：立即补齐，还是与 simulation runtime loader 设计
   同步发布？

**未落地原因**

- simulation 运行时尚未动工，实际消费路径未定；现阶段只有模板占位，
  字段边界可能随 loader 设计调整

**暂不做的事**

- 不提前补 schema，避免与后续 loader 字段收敛方案冲突

**依赖**：simulation runtime loader 选型 / 设计定稿

---

### [T-SEMANTIC-FULLFILE-COST] Phase A 全文语义审校：50k 截断 + 读全文的成本

**上下文**

L3 语义审校（`repair/checkers/semantic.py::_review_file`）把**整份文件**塞给
LLM 通读。两个后果，一个是质量缺口、一个是成本，**同源**：

**① 尾部从未被审校。** `semantic.py:121` 有个硬编码截断：

```python
_SEMANTIC_MAX_CHARS = 50000
if len(content_str) > _SEMANTIC_MAX_CHARS:
    logger.warning("Semantic review truncated %s: %d chars → %d chars "
                   "(tail dropped from review)", ...)
```

实测**正在持续触发**——2026-07-16 那轮 S003 的日志里
`Semantic review truncated .../canon/stage_snapshots/S00N.json` 反复出现
（`stage_snapshot` 实测 59KB）。即**大文件超出 50k 的部分从来没被审校过**，
而这不是理论风险，是每个 stage 都在发生。

**② 检查吃掉 repair 的绝大部分开销。** 2026-07-16 单 stage 的 repair 内部
按调用类型拆分（`logs/runs/*.jsonl`）：

| 类型 | n | p50 | 累计 out_tok | 成本 |
|---|---|---|---|---|
| T1 local_patch 修复 | 34 | **14s** | ~14k | ~$2.61 |
| T2 source_patch 修复 | 2 | **28s** | | |
| L3 语义检查 (Phase A) | 38 | 152s | ~172k | ~$6.24 |
| L3 gate 复检 | 24 | 185s | | |

**检查吃掉 repair 的 92% token，修复只占 8%。** 决策 #62 的定点修复完全生效
（改一个 `json_path` 只要 14 秒），但**检查的粒度和修复的粒度差了三个数量级**：
修复只碰一个字段，检查读整份 50k 字符。

全轮成本参照：3 个 stage = $157.86；按 $52.6/stage 外推 53 个 stage ≈ **$2,800**，
其中 repair 约 21%（$470），而 repair 的 92% 是检查（≈$430 花在"找问题"上）。

**注意边界**：本条讨论的是 **Phase A 全量检查**。**每轮 gate 复检**改定点是
另一条（T-GATE-SCOPED-RECHECK，用户已拍板方向：「全文审查一次就够了，之后修啥
复审啥」）——那条的前提正是 Phase A **保持全文**。所以本条不是"要不要全文"，
而是"全文这一次该怎么做得更好"。

**待决策项**

1. **截断怎么办**：`stage_snapshot` 实测 59KB > 50k，尾部恒定被丢。选项：
   (a) 调大 `_SEMANTIC_MAX_CHARS`（多少？context window 是 1M，50k 这个值的
   来历需要考古）；(b) 分块审校后合并 issue；(c) 按字段分组审校（与 #55 的
   sub-lane 字段归属表对齐）；(d) 接受现状但至少把它变成 config 而非硬编码
2. **Phase A 要不要也降 effort**：T-EFFORT-TIER-TUNING 只给 gate/T1/T2/triage
   降到 medium，Phase A 保持 backend 默认。它是"找问题"不是"创作"——medium
   够不够？需要先有 xhigh 的基线数据才好判断
3. **要不要按 importance 分级审校**：`validation/shared/importance.py` 已有
   `importance_for_target`——低 importance 的 target 相关字段是否可以跳过 L3？
4. **值不值得**：$430 找问题，最后 defer 了几条。这个投入产出比是否可接受，
   本质是用户对"审校覆盖率 vs 成本"的取舍——需要用户拍板，不是技术问题

**未落地原因**

- 需要 T-EFFORT-TIER-TUNING + T-GATE-SCOPED-RECHECK 的数据才好评估：如果那两条
  把 repair 从 32min 压到 15min，本条的紧迫性就下降；如果压不动，Phase A 就是
  下一个靶子
- 决策 1 的选项 (b)/(c) 是架构改动，成本远高于前两条 todo

**依赖**：T-EFFORT-TIER-TUNING + T-GATE-SCOPED-RECHECK 的实测数据

---

### [T-SEMANTIC-UNPARSEABLE] L3 审校返回非法 JSON（实测 3 个 stage 中 2 次）

**上下文**

`repair/checkers/semantic.py` 的审校返回值解析失败，日志：

```
[WARNING] extraction.repair.checkers.semantic: Invalid JSON in semantic
review for .../canon/stage_snapshots/S00N.json
```

2026-07-16 那轮 3 个 committed stage 里**出现 2 次**（S001 / S003 的
`deferred_repairs/*.jsonl` 各含 1 条 `rule: semantic_unparseable`），
出现率 ~33%。

**这与超时是不同的故障**：审校 LLM 跑完了、返回了内容，但内容不是合法 JSON。
决策 #64 放宽超时**救不了它**——那是输出格式问题，不是时间问题。

**性质要分清**：它经决策 #60 的 defer 通道写进账本、stage 照常提交，但它记录的
是「**审校从未跑出结论**」，而不是「已知有瑕疵」。同一个 defer 桶里混着两种
东西——S001 的 4 条里 1 条是 `semantic_unparseable`（审校故障）、3 条是
`cross_field_consistency` / `voice_ownership`（真实内容问题）。下游 Phase 3.5
（T-PHASE35-DEFERRED-FIX）消费账本时，这两类需要不同处理：前者应该**重跑审校**，
后者才是**逐条精准修**。

**待决策项**

1. **根因是什么**：prompt 让 LLM 输出 JSON 的方式不够硬？还是解析太严
   （比如 LLM 包了 markdown ```json 围栏、或前后加了说明文字）？需要抓一次
   原始返回值看。`_parse_response` 在 `semantic.py`，先读它怎么解析的
2. **要不要用结构化输出**：`claude` CLI 有 `--json-schema <schema>` flag
   （`claude --help` 可见）——能否用它硬约束审校返回值的形状？这可能是根治
3. **要不要重试**：现在是一次非法就 defer。重试一次的成本 vs 收益？
   （L3 检查 p50 152s，不便宜）
4. **defer 桶要不要分流**：`semantic_unparseable` 和真实内容问题混在一起，
   Phase 3.5 需要区分处理——是在写账本时就分开，还是让 3.5 按 `rule` 分流？
   （与 T-PHASE35-DEFERRED-FIX 的待决项 4 有关联）

**未落地原因**

- 根因未知，需要先抓一次原始返回值（决策 1）才能选方案
- 33% 是 3 个 stage 的样本，n 太小——可能是巧合，也可能更高。跑更多 stage 会
  自然攒出样本

**依赖**：无（诊断可立即启动）；但方案选择依赖决策 1 的结果

