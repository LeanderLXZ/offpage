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

### 🟡 Next (1)

| ID | Brief | Importance | Ready | Scope | Updated | Deps |
|---|---|---|---|---|---|---|
| `T-LIGHTNOVEL-SCHEMA-ONEOF` | stage_plan 里"一个 stage 包几章"这个数字，普通模式是 8-15、轻小说模式是 1。schema 现在只允许 ≥5，所以轻小说产物自己跑 schema 校验过不了——但实际没有外部校验它，所以是个已知缺陷不致命。 | 🟢 Med-Low | ⏸ Blocked | 🔴 Large·Arch | 2026-05-12 EDT | 等首个外部 artifact validator 消费方出现 |

### ⚪ Discussing (6)

| ID | Brief | Open decisions | Updated | Blocked by |
|---|---|---|---|---|
| `T-SEMANTIC-FULLFILE-COST` | 语义审校每次把整个文件读一遍，是 repair 里最重的一类调用。截断问题已解决（决策 #70）；成本问题原先卡在测不出来，现在尺子已装好（决策 #71 给账本加了调用类型标签），只差跑一次提取产出带标签的账本。紧迫性已降——scoped gate 落地后 repair 从 38min 降到 8min。 | 3 | 2026-07-20 EDT | 一次带 call_type 标签的真实提取跑 |
| `T-REPAIR-EVENT-DRIVEN` | Phase 3 一抽完一个文件就立刻去修复、跟下一文件的抽取并行——理论最快。但实测算过只比当前方案省 4 分钟/stage，要为这点收益引入双线程池 + 撞限额风险，性价比太低。先做简单版（E1），等真实跑数据出来再决定要不要做这个。 | 0 | — | T-REPAIR-PARALLEL 先落地 |
| `T-PROMPT-SCHEMA-INJECT` | 项目约定"长度上限这种数字只在 schema 写一份"，但少数 prompt 和 doc 里仍有手写的数字（"150-200 字"之类）。万一 schema 改了，这些地方就会偷偷不一致。要么写代码让 prompt 自动从 schema 读，要么修约定明说"prompt 允许例外"。 | 3 | — | 无（路径决策即可启动） |
| `T-PHASE5-RETRIEVAL` | 好几份架构文档都在说"每部作品下应该有个 indexes/ 目录"，但实际没有任何阶段在生成它——目录在磁盘上压根不存在。打算加一个 Phase 5 专门做检索类产物（词典、关键词、向量索引、RAG 数据等）。等 phase 3 跑完 + 检索层设计定稿再启动。 | 5 | — | Phase 3 全量完成 + retrieval 层设计定稿 |
| `T-RETRY` | LLM 调用失败时的重试策略能更聪明些。现在不到 5 秒就失败的会重试，但人物抽取正常要跑 10-20 分钟，5 秒太短了——那种短时失败几乎都是启动错、不是真活干完才挂。打算扩到 60 秒，再按失败类型分流要不要重试。改动小，两个数值要拍板。 | 2 | — | 无（T-LOG 已完成） |
| `T-USER-AUX-SCHEMAS` | users/ 目录下有几个辅助 JSON 文件（session 索引、归档引用之类）没绑 schema，字段长啥样全靠模板猜。simulation 运行时一旦写起来要消费这些文件，到时候字段可能已经漂得不像样。等 simulation 选完 loader 设计再补 schema。 | 2 | — | simulation runtime loader 选型 / 设计定稿 |

**Total**: 7 — 🟢 In Progress 0 ｜ 🟡 Next 1 ｜ ⚪ Discussing 6

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



## Discussing (Undecided) <!-- holo:heading -->

<!-- holo:section start -->
<!-- Tasks with open decisions / external deps / unsettled design.
     Don't start; converge the decision first.
     Format: see "What to record" + "Open decisions" section mandatory. -->
<!-- holo:section end -->

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

### [T-SEMANTIC-FULLFILE-COST] Phase A 全文语义审校的成本

**进展**（2026-07-18）：原条目的两半里，**质量缺口那半已解决**——L3 审校的输入
截断已删除，Phase A 现在无条件通读整份文件，且刻意不做成配置项（决策 #70，
`logs/change_logs/2026-07-18_215402_semantic-no-truncation.md`）。**剩余 = 成本
那半**，但其原有支撑数据经核账不成立，见下。

**上下文**

Phase A 是整条 repair 链路中**唯一一次**全文语义审校：T1 / T2 修复与 Phase B
gate 复检都只处理 Phase A 报出的问题。它把整份 `stage_snapshot`（实测约 59KB）
送给 LLM 通读，单次 wall 可达数百秒，是 repair 里最重的一类调用。问题是：这个
"最重"到底占多少，目前**测不出来**。

**成本口径（已按账本订正）**

口径以账本为准（`logs/runs/<work_id>_2026-07-16_144353.jsonl`，3-stage 跑）：

| 口径 | 账本实测 |
|---|---|
| 全跑总成本（3 stage） | $157.86 |
| repair 部分 | **69 次调用 / $46.23 / 占 29.3%** |
| repair output tokens | 951k |
| repair cache_read / cache_creation | 2.15M / 2.14M（prompt caching 生效） |

**上表的测量局限（限于 2026-07-16 那份账本）**：当时的 lane 标签只有
`repair[S00N]`、不携带调用类型，因此"检查（Phase A + gate 复检）vs 修复
（T1 + T2）"的开销比**无法从上表数据得出** —— 任何声称该比值的结论都不能拿
这份账本验证。此限制自决策 #71 起解除：新账本每行带 `call_type`，可直接分组
（见待决项 1，已完成）。**下次跑任意 stage 即产出第一份可分组的账本。**

**边界**：Phase B gate 复检的 prompt 输入仍是整份 JSON（scope 过滤发生在返回值
上），**已决定不改**——理由与收益上限见决策 #70。本条不重开该议题。

**待决策项**

1. ~~**先补测量**：账本加调用类型标签~~ —— **已完成（2026-07-20，决策 #71）**。
   实现与本条原设想不同：**没有**把类型拼进 `lane` 后缀，而是加了独立的
   `call_type` 字段（闭集 `check_full` / `check_scoped` / `fix_t1` / `fix_t2` /
   `triage`，非 repair 调用写 `null`），`summarize()` 聚合键扩展为
   `(phase, lane_type, call_type)`。独立字段比 lane 后缀好在：不破坏既有
   `lane` 解析、`_lane_type()` 的折叠逻辑不用改、旧账本文件读出来 `call_type`
   缺失即 `None`（向后兼容，无需迁移）。
   → logs/change_logs/2026-07-20_140928_ledger-call-type-label.md
2. **Phase A 要不要降 effort**：目前不传 effort、吃 `[llm].effort`（xhigh）；
   gate / T1 / T2 / triage 已由 `[repair].recheck_effort` 降到 medium（决策 #65）。
   Phase A 是"找问题"不是"创作"——medium 够不够？需要 xhigh 的基线数据才好判断
3. **要不要按 importance 分级审校**：`validation/shared/importance.py` 已有
   `importance_for_target`——低 importance 的 target 相关字段是否可以跳过 L3？
   风险：实测残留多为跨字段一致性问题（`cross_field_consistency` /
   `voice_ownership`），按 target 切字段未必等比例降成本，却会在跨字段问题上开洞
4. **值不值得**：本质是"审校覆盖率 vs 成本"的取舍，需要用户拍板，不是技术问题。
   但在待决项 1 落地前，讨论缺少事实基础

**未落地原因**

- 尺子已装好（待决项 1，决策 #71），但**还没有带标签的真实账本** —— 本轮只改了
  记账代码，没有跑提取。下次跑任意一个 stage 就会产出第一份可直接分组的账本，
  届时 2/3/4 才有事实基础
- 紧迫性已下降：#65/#66/#67 落地后 S004 实测 repair 墙钟从基线 27/31/38min 降到
  **8m04s**，检查的绝对开销小了很多。本条现在更接近"想清楚再说"而非"赶紧修"

**依赖**：一次带 `call_type` 标签的真实提取跑（跑任意 stage 即可产出）

**更新时间**：2026-07-20 14:09 EDT
