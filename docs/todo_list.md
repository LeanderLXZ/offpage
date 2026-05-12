# TODO List（待办任务清单）

---

## Index (auto-generated; do not hand-edit)

> 本段是三张子表的渲染缓存，由维护本文件的人（包括 Claude）在**每次对正文条目增 / 改 / 移段 / 完成 / 废弃后**顺手刷新——具体规则见下方"## File guide → Index maintenance"。`/todo` skill 不解析正文，只读这一段，所以这里的内容必须与正文同步；不同步会让 `/todo` 给出错误结论。

### 🟢 In Progress (1)

| ID | Title | Start time | Updated | Status |
|---|---|---|---|---|
| `T-INGEST-STRUCTURE-MODE` | Phase 0/1 双模式（monolithic / light_novel）调度 | 2026-05-01 07:04 EDT | 2026-05-01 | schema/code/prompt/ai_context/docs 完成 + post-check 两轮残留缺口（stage_title 软截断改用启动时动态读取 schema cap + progress.py reconcile C 前缀兼容 + cosmetic 全过）已修；end-to-end runtime 验证待跑（需 light_novel fixture 与 monolithic 既有 fixture 双向回归） |

### 🟡 Next (3)

| ID | Brief | Importance | Ready | Scope | Updated | Deps |
|---|---|---|---|---|---|---|
| `T-PHASE2-REPAIR-AGENT` | phase 2 baseline production 整体接入 repair_agent lifecycle（4 件产物 foundation key_figures patch + fixed_relationships + identity + target_baseline 各自包装 SourceContext + 写 phase 2 专属 checkers）。当前 phase 2 仅"裸单次 LLM + tolerance gate"为遗留缺陷（决策 #54 拆出），decision #25 + decision #48 措辞修正后已明确 repair_agent 仅在 phase 3。 | 🟡 Med | ⏸ Blocked | 🔴 Large·Arch | 2026-05-11 EDT | 无（与本次 foundation 重构正交） |
| `T-PLUGIN-README` | 2026-04-28 把 skills 项目专属内容抽到 `ai_context/skills_config.md`，但新项目装 plugin 时不知道每节怎么填 / 缺失行为 / 模板。需写 `.agents/skills/README.md` 作为 setup 单一入口。 | 🟢 Med-Low | ✅ Ready | 🟢 Small | — | 无 |
| `T-CHAR-SNAPSHOT-SUB-LANES` | character stage_snapshot 拆 3 sub-lane（char_expression / char_decision / char_cognition）并行 + file-level repair lifecycle；sub-lane partial 程序 merge 后复用现有 `targets_keys_eq_baseline.py` 做早期预检。prev_snapshot 处理对齐决策 #11f 四态 + #13 set-equal 硬约束（已是 phase 3 现状，本 todo 不重述）。 | 🟢 High | ✅ Ready | 🔴 Large·Arch | 2026-05-12 | 无（依赖物均已就位） |

### ⚪ Discussing (8)

| ID | Brief | Open decisions | Updated | Blocked by |
|---|---|---|---|---|
| `T-REPAIR-EVENT-DRIVEN` | E2 方案：每 lane 完成立刻触发 repair，与后续 lane extract 重叠。2026-04-22 测算只比 E1 省 4min/stage（49 stage 共 ~3h），双线程池 + peak 9 并发撞 rate limit 复杂度跳一档，暂不做。等 E1 真实耗时数据出来再重评。 | 0 | — | T-REPAIR-PARALLEL 先落地 |
| `T-CODEX-STDIN` | ClaudeBackend 已改 stdin 临时文件绕过 argv 128KiB 上限；CodexBackend.run 仍走 positional argv，切 `--backend codex` 时大 prompt 会复现 Argument list too long。已加注释未改代码——本机无 codex CLI 实测。 | 2 | — | 有 codex CLI 的机器 / 订阅 |
| `T-CODEX-RATE-LIMIT` | ClaudeBackend 已通过 `_classify_rate_limit`（含 429）把 stderr 映射为 `rate_limit:`；CodexBackend.run 非零退出仍直接返回 `exit N`，撞限额走普通 retry，不进 pause-controller。本机无 codex CLI 实测。 | 2 | — | 有 codex CLI 的机器 / 订阅 |
| `T-PROMPT-SCHEMA-INJECT` | conventions.md 要求 bounds 只在 schema 写一次，但 prompt template + schema_reference.md 部分段落仍复述具体数字。需选定路径：A 自动从 schema 注入 prompt bound 段；B 修订 conventions 加 prompt 例外条款。 | 3 | — | 无（路径决策即可启动） |
| `T-SIMULATION-MODE-MARKER` | CLAUDE.md / AGENTS.md 已预留 `[simulation_runtime_mode]` worker-mode short-circuit；extraction 侧已注入 `[extraction_worker_mode]`，simulation 侧零 Python 尚无注入点。 | 2 | — | simulation runtime 首次实装 |
| `T-PHASE5-RETRIEVAL` | 多处 canonical docs 宣称 `works/*/indexes/` 是 committed 产物（current_status / decisions / data_model / system_overview 都在说），但目前没有 Phase 承担生成职责。计划新增 Phase 5 统一承接 vocab_dict / 关键词 / FTS5 / RAG 等。 | 5 | — | Phase 3 全量完成 + retrieval 层设计定稿 |
| `T-RETRY` | T-LOG 已能解析 subtype / num_turns / cost，但 retry 决策本身还没用上 subtype 分流；短时阈值仍 5s（[config.toml:130](../automation/config.toml#L130)）偏小，char_snapshot 正常 10-20m，<60s 失败几乎一定是 launch / 连接错。需扩大阈值到 60s（候选 120s）+ 长时 exit 按 subtype 分流。 | 2 | — | 无（T-LOG 已完成） |
| `T-USER-AUX-SCHEMAS` | users/ 下若干辅助文件无 schema 绑定（session_index.json / archive_refs.json），2026-04-20 codex audit R3 指出 runtime 真正落地前最容易继续漂移。 | 2 | — | simulation runtime loader 选型 / 设计定稿 |
**Total**: 12 — 🟢 In Progress 1 ｜ 🟡 Next 3 ｜ ⚪ Discussing 8

---

## File guide

### Purpose

记录**计划完成但尚未完成**的具体工程任务。区别于：
- `ai_context/next_steps.md`：**架构方向**和高层 roadmap（用英文）
- `ai_context/current_status.md`：**当前项目状态快照**
- `logs/change_logs/`：**历史记录**（时间戳，只追加不修改）
- `docs/architecture/`：**正式架构文档**
- `docs/todo_list_archived.md`：**Completed / Abandoned** 任务的瘦身归档（瘦身条目，原文细节去 git history / change_logs）

本文件是**工程级**的待办队列，含文件路径、行号、改动清单、验证步骤。

### Task flow

```
Discussing ──(decided)──▶ Next ──(/go starts)──▶ In Progress ──(commit done)──▶ archived ## Completed
                                                                                ▲
any node ─────────────────(abandoned)──────────────────────────────── archived ## Abandoned
```

三个段落的语义：

- **In Progress**（单槽位）：`/go` 已启动、尚未 commit 完成的任务。同时**只能 1 条**——目的是中途 ctrl-c / 用户暂停 / 切换会话时，能立刻从这里看到"正在做什么"，不用翻 git status / progress 文件
- **Next**：依赖与设计已基本就绪、随时可以 `/go` 启动的任务队列。条目按用户优先级排序，第一条就是下一个该启动的
- **Discussing**：有未决策项 / 有外部依赖 / 方案未拍板的任务；不要 `/go` 启动它们，先收敛决策

### What to record

✓ 具体到文件 / 函数级的改动任务
✓ 每条任务必须包含：**上下文**（动机 + 现状 + 触发链）、**改动清单**（含文件路径和行号；Discussing 段可暂缺）、**完成标准**、**依赖**
✓ 视情况补：**待决策项**（Discussing 段必有）、**预估**、**未落地原因**、**暂不做的事**
✓ Discussing 段尚未定案的方案及其权衡

### What NOT to record

✗ 架构方向 / 高层 roadmap → 写进 `ai_context/next_steps.md`
✗ Completed / Abandoned 任务 → 移到 `docs/todo_list_archived.md`（瘦身），不留在本文件
✗ 临时调试笔记 / 中间思考 → 对话上下文或 plan，不持久化
✗ 当前运行状态 / 进度 → 写进运行时进度产物（按 skills_config.md `## Background processes` 的进程产物路径）

### How to update entries

**所有段位条目共同字段**：每条 `### [T-XXX]` 块都必须含 `**更新时间**`
（YYYY-MM-DD HH:MM 时区缩写——按 skills_config.md `## Timezone`）。CREATE 时
初始化 = 创建时刻；正文任意字段被改 / 跨段移动时刷新 = 改动时刻。**纯索引
刷新本身不刷该字段**——索引是缓存，正文没动就是没动。该字段是 `/recent-activity`
判定"何时讨论 / 改过该 task"的唯一锚点。

**添加任务**：放进合适的分节（Next / Discussing）。新任务必须有上方"What to record"
列出的字段 + `**更新时间**`。**不要直接添加到"In Progress"**——那个段位仅由 `/go`
启动动作填入。

**任务进入执行（/go 启动）**：
1. 把整条从 "Next" 移到 "In Progress"
2. 在条目里追加 `**开始时间**`（YYYY-MM-DD HH:MM 时区缩写——按 skills_config.md `## Timezone`）和 `**当前状态**`（进行中 / 等用户决策 / 暂停）字段
3. 刷新 `**更新时间**` = 启动时刻
4. **In Progress 段位单槽**——若已有占用，先把当前那条 commit 完成或显式暂停回退到 "Next" 再启动新任务
5. 同步刷新索引段（见 "Index maintenance"）

**任务完成（commit 完成 + 验证通过）**：
1. 把整条**移到** `docs/todo_list_archived.md` 的 `## Completed` 段，按归档格式瘦身（标题 + 完成形式 + 1 行摘要 + log 链接），原条目从本文件删除
2. 若该任务产生了值得沉淀的结论 / 新架构决策 / 可复用经验，写一条 `logs/change_logs/{YYYY-MM-DD}_{HHMMSS}_{slug}.md`
3. 若完成涉及 `ai_context/` 的持久事实变化（current_status / decisions / next_steps 等），同步更新
4. **从 "Next" 首条提升一条到 "In Progress"**——只在用户立刻 `/go` 下一条时做；非紧凑流程则保持 "In Progress" 为空，等下次 `/go` 启动时再移
5. 同步刷新索引段

**任务废弃**：写一条 `logs/change_logs/` 记录废弃原因后，把整条**移到** `docs/todo_list_archived.md` 的 `## Abandoned` 段（同样瘦身：标题 + 废弃原因 + log 链接）。同步刷新索引段。

**讨论转落地**：Discussing 章节产生结论时，无论整体定案还是阶段性结论，都要立即把结果反映到对应章节——
- **整体定案**：把条目从 "Discussing" 整条移到 "Next"，补全成完整任务（上下文 / 改动清单 / 完成标准 / 依赖）。同步刷新索引段
- **部分定案**：把已定案的子任务单独拆出迁移到 "Next"（作为独立任务条目），未定案部分继续留在 "Discussing" 并更新上下文说明已拆分出去的部分。同步刷新索引段
- **结论颠覆原假设**：若讨论结果反而证明某已在 "Next / In Progress" 的任务不再必要，按"任务废弃"流程处理

### Index maintenance

文件顶部 `## Index (auto-generated; do not hand-edit)` 段是三张子表的缓存。**每次对正文条目增 / 改 / 移段 / 完成 / 废弃**后必须刷新这一段；`/todo` skill 不解析正文，只读这一段。

**触发时机**：以下任一发生时刷新：

- 添加新任务条目
- 修改现有条目的：标题、上下文摘要、依赖、待决策项、改动清单文件数、是否触及 schema / 架构 / 多 phase、`**更新时间**`
- 任务移段：Discussing → Next、Next → In Progress、In Progress → archived、任意 → archived（abandoned）
- 任务在 "In Progress" 段内的"当前状态"变化（进行中 / 等用户决策 / 暂停）

**三张子表的列定义**：

**In Progress**

| 列 | 取值 |
|---|---|
| ID | 反引号包裹的 T-XXX slug |
| Title | 方括号后的中文短语 |
| Start time | 条目里的 `**开始时间**` 字段，YYYY-MM-DD HH:MM 时区缩写 |
| Updated | 条目里的 `**更新时间**` 字段，YYYY-MM-DD（仅日期，省 HH:MM）；缺字段 → "—" |
| Status | 条目里的 `**当前状态**` 字段：进行中 / 等用户决策 / 暂停 |

**Next**

| 列 | 取值 |
|---|---|
| ID | 反引号包裹的 T-XXX slug |
| Brief | 上下文段首句 + 1-2 句关键背景，**总长 ≤ 150 字**；去掉 markdown 链接的反引号让表格不破，但保留 `[text](url)` 形式 |
| Importance | 🔴 High / 🟢 Med-Low / 🟡 Medium（推断规则见下） |
| Ready | ✅ Ready / 💬 Discuss first / ⏸ Blocked（推断规则见下） |
| Scope | 🟢 Small / 🟡 Medium / 🔴 Large·Arch / —（推断规则见下） |
| Updated | 条目里的 `**更新时间**` 字段，YYYY-MM-DD；缺字段 → "—" |
| Deps | 条目"**依赖**"段首句 |

**Discussing**

| 列 | 取值 |
|---|---|
| ID | 反引号包裹的 T-XXX slug |
| Brief | 同上，≤ 150 字 |
| Open decisions | 数 `**待决策项**` 段下的列表条目数；缺该段 → 0 |
| Updated | 条目里的 `**更新时间**` 字段，YYYY-MM-DD；缺字段 → "—" |
| Blocked by | "**依赖**"段首句 |

**字段推断规则**（确定性，不要灵活发挥）：

**Importance**（仅用于 "Next" 段；In Progress 段不显示，Discussing 段不显示）

| 等级 | 触发条件 |
|---|---|
| 🔴 High | 段落 = Next 且 用户曾标注高优先 / 阻塞其他任务 |
| 🟢 Med-Low | 段落 = Next 且（依赖 blocked 或 待决策项 ≥ 2 或 用户未明确高优先） |

**Ready**

| 标签 | 触发条件 |
|---|---|
| ✅ Ready | 依赖 ready 且 待决策项 = 0 |
| 💬 Discuss first | 待决策项 ≥ 1 |
| ⏸ Blocked | 依赖中含具体阻塞名（外部 CLI、未实装模块、未发生事件 等） |

优先级：⏸ > 💬 > ✅。同时满足"待决策 ≥ 1"和"被阻塞"时取 ⏸。

**Scope**

| 规模 | 触发条件 |
|---|---|
| 🟢 Small | 改动清单 ≤ 2 文件 且 不动 schema / 不动接口 / 单点修复 |
| 🟡 Medium | 改动清单 3–6 文件 或 涉及多函数协作 / 单模块内重构；不触发架构层调整 |
| 🔴 Large·Arch | 改动清单 ≥ 7 文件 或 触及任一：新增 Phase / 改 schema 字段 / 改核心接口 / 跨模块协议变更 / 引入新依赖 / 影响多 work 流程 |
| — | 缺「改动清单」段（多见于 "Discussing" 未拆解的条目）；备注"未拆解，规模待评估" |

**简介撰写要求**：首句必含核心信息；再补 1–2 句关键背景（痛点 / 关键文件 / 实测数据 / 触发原因之一），让用户不点开正文也知道这是个什么事、为什么值得做。**总长 ≤ 150 字**——超过宁可砍背景也要保住首句。

**汇总行**：三张表后打印一行：`Total: N — 🟢 In Progress a ｜ 🟡 Next b ｜ ⚪ Discussing c`。

### When to read

- 用户问及待办 / 即将做什么 / 接下来该做什么 → `/todo` skill（只读索引段）
- 开始任意改动前 **先查一次**，避免重复规划
- 讨论到可能已登记的话题时
- **默认不主动读取**（不进入 session 启动的 `ai_context/` 读取序列）

---

## In Progress

### [T-INGEST-STRUCTURE-MODE] Phase 0/1 双模式（monolithic / light_novel）调度

**开始时间**：2026-05-01 07:04 EDT

**更新时间**：2026-05-01 14:29 EDT

**当前状态**：schema/code/prompt/ai_context/docs 完成、smoke 全过；
post-check 第 1 轮残留缺口（stage_title.maxLength 50→80 + 代码层软截断兜底；
progress.py `_expected_chapter_count` 兼容 `C####-C####`；automation/README
加 dual-mode 指针；todo_list Index 大小写对齐）已修；post-check 第 2 轮
残留缺口（orchestrator `_STAGE_TITLE_MAX = 80` 硬编码违反 §27b 单源原则
→ 改用启动时从 `stage_plan.schema.json` 读取 maxLength；流程级 docs 加
软截断 safeguard 注；todo_list 累计 50→80）已修；end-to-end runtime 验证
待跑（需 light_novel fixture 与 monolithic 既有 fixture 双向回归）

**上下文**

phase 0/1 流程原本仅为单卷非结构化作品（典型中文网络小说）设计：phase 0
按 token-budget 启发式切 batch、phase 1 自主发现 stage 边界。多卷结构化
轻小说的天然结构（卷 → 印刷章 → sub-section）这套流程没有利用，且
`1 stage = 1 sub-section` 的粒度需求与启发式不匹配。

方向：phase 0/1 支持双模式，由 source manifest `structure_mode` 字段调度——

- **monolithic**：维持现有 token-budget 启发式 + 自动 stage 发现
- **light_novel**：1 phase 0 chunk = 1 phase 1 stage = 1 sub-section
  （normalization 后的 1 个 C-id）；stage_plan 直接 1:1 从 chapter_index
  派生，不跑 boundary discovery

phase 2+ 不分叉，统一消费 stage_plan，volume / 印刷章语义靠 chapter_index
里 profile-B 字段携带，character / world schema 不动。

**已落地（schema/code/prompt/ai_context/docs，2026-05-01）**

- schema：`schemas/work/chapter_index.schema.json` items 改 `oneOf` 双
  profile（monolithic 禁 6 字段、light_novel 必填 4 + 可选 2）；
  `schemas/work/work_manifest.schema.json` + `schemas/work/works_manifest.schema.json`
  加 `structure_mode` enum（默认 `monolithic`）；`schemas/analysis/stage_plan.schema.json`
  放宽容纳 light_novel（`chapter_count.minimum` 5→1、`stages.maxItems`
  200→1000、`stage_title.maxLength` 14→80；`chapters.pattern` 保持
  `^C[0-9]{4}-C[0-9]{4}$` 不变，light_novel 走 degenerate 单章区间）
- code：`automation/ingestion/validator.py` 跨文件断言 `structure_mode` ⇔
  chapter_index profile；`automation/persona_extraction/manifests.py` 加
  `read_structure_mode()` + `write_works_manifest` 拷字段；
  `automation/persona_extraction/orchestrator.py` 加
  `_build_light_novel_stage_plan()` 输出 `chapters = f"{chapter_id}-{chapter_id}"`
  degenerate 单章区间，phase 0 / phase 1 入口分支调度，phase 1 STAGE_MIN/MAX
  校验在 light_novel 下绕过；phase 2/3/4 既有 `chapters` 解析器
  （`prompt_builder._parse_chapter_range`、`scene_archive`、
  `repair_agent.context_retriever`、`post_processing._parse_chapter_scope`）
  零改动
- prompt：`prompts/ingestion/原始资料规范化.md` 补 `structure_mode` 填写
  指引 + light_novel 三层 seq 字段说明 + title 派生公式；2026-05-01 14:29
  update：把 task 步骤 2 改成"判定 `structure_mode`"流程——先输出 monolithic
  / light_novel 判定 + 依据 + 置信度，≥ 0.8 直接进 / < 0.8 停手等用户拍板，
  任意识别信号"不确定" → 置信度上限 0.7（必走人工确认）；manifest 段
  `structure_mode` 子项的旧"判定要点" bullet 删除（迁到 step 2 单源）
- ai_context：`decisions.md` 加 27j/27k/27l + 更新 10a；`conventions.md`
  Cross-File Alignment 加 `structure_mode` 行；`architecture.md` Phase 0/1
  描述加双模式
- docs：`docs/architecture/{schema_reference,extraction_workflow}.md`、
  `docs/requirements.md` §8.4 / §9.2 同步双模式说明
- smoke：chapter_index oneOf（monolithic + 字段误用拒绝、light_novel +
  缺字段拒绝）4 case；validator 跨文件断言（pass + fail 双向）4 case；
  `_build_light_novel_stage_plan` 12-sub-section fixture 通过 stage_plan
  schema；`write_works_manifest` 拷 `structure_mode` + `read_structure_mode`
  prefer works → source 全过

**待跑（runtime 验证）**

- 拿一份完整规范化的多卷 light_novel fixture 跑一遍 phase 0 + phase 1：
  phase 0 chunk 数 == chapter_index 长度；phase 1 stage 数 == chapter_index
  长度；stage_plan 顺序、stage_id、stage_title 正确
- 既有 monolithic fixture dry-run 一遍 phase 0/1，与历史结果一致——确认
  默认路径不退化

**暂不做的事**

- normalization-时 LLM 形态判断的 prompt 设计 / 落地（独立后续 todo）
- 第三种 mode（western_epub / webnovel_serialized 等）— 不预设 schema 扩
  展点，等真有 fixture 再说
- chunking_strategy / stage_strategy 解耦的 feature-flag 重构 — 现 2 个
  mode 用 if/else 够用
- light_novel 模式 phase 0/1 LLM call 合并优化 — take 这份冗余成本
- 上/下卷合并、短篇集粒度细化 — 由 normalization 阶段控制 volume_id
  （同卷给同 id）；不在 phase 0/1 处理

---

## Next

### [T-PHASE2-REPAIR-AGENT] phase 2 baseline production 整体接入 repair_agent lifecycle

**开始时间**：2026-05-11 EDT（决策 #54 落地时拆出）

**当前状态**：Blocked（设计未拍板）。本任务从决策 #54 的 foundation 重构 /go 中拆出来作单独 todo，工程量大、与 foundation 重构正交。

**上下文**

会话深挖发现 phase 2 baseline production 当前形态 = "**裸单次 LLM + jsonschema gate + length-bound tolerance gate**"，不经 repair_agent lifecycle（[orchestrator.py:run_baseline_production](../automation/persona_extraction/orchestrator.py)）。代码注释自己承认："Phase 2 has no LLM-level retry budget here ... this is the terminal gate."

repair_agent 实际接入点 grep 全仓库**只有 1 处** = `orchestrator.py` 内 phase 3 stage loop 的 `_repair_one(f)` 调用（per-file 并行 lifecycle，每 stage 1+2N files 各自独立跑 L0-L3 × T0-T3 checker/fixer 矩阵）。phase 0 / 1 / 1.5 / 2 / 3.5 / 4 都没接 repair_agent。

历史误解源头：
1. [decisions.md #48](../ai_context/decisions.md) 原措辞 "Phase 2/3/3.5/4 via repair_agent T3_EXHAUSTED"——把 phase 2/3.5/4 的兜底也写成"经由 repair_agent"，但实际只有 phase 3 走 repair_agent。已在 foundation 重构 /go 同批修正。
2. commit `e644886 phase1_parallel_lanes` 归档条目 paper trail："原计划集成 `repair_agent.run` 走 L1/L2/L3 + T0/T1/T2/T3 lifecycle，盘点后发现 phase 2 实际不调 repair_agent + phase 1 输出非 stage-anchored，改用更轻的 `prior_error` 注入式 retry"——当时做 phase 1 lane 改造时也误以为 phase 2 接了 repair_agent，盘点后才发现没接。

**改动清单**

设计未拍板，待启动时定。预期改动量 ≈ phase 3 接入当年的工作量：

新增：
- `automation/repair_agent/checkers/phase2_*.py`（专属 checkers，预估 4-5 个）：
  - `foundation_factions_legal`：foundation.major_factions[].key_figures character_id 合法性（必须 ∈ candidate_characters 已合并身份集）
  - `fixed_relationships_legal`：parties[] character_id 必须 ∈ 已确认目标 ∪ candidate_characters
  - `identity_required_fields`：identity.json 含 character_id / canonical_name / aliases 等必填
  - `target_baseline_admission_rule`：targets[] 准入门槛（dialogue/action 交互判定，可能需 LLM）
  - `target_baseline_keys_set`：targets[].target_character_id 集合校验
- `automation/persona_extraction/orchestrator.py` `run_baseline_production`：包装 SourceContext + 调 `run_repair(...)`，per-file 并行 + lifecycle dispatch
- baseline 产物 per-file 拆分：4 件产物（foundation patch / fixed_relationships / identity / target_baseline）各自独立 file-level repair entry

修改：
- `automation/repair_agent/coordinator.py`：可能需要扩 fixer T0-T3 适配 phase 2 产物形态
- `ai_context/decisions.md` #25：repair_agent 接入点扩到 phase 2
- `ai_context/decisions.md` #48：length tolerance gate 接入点同步更新

**完成标准**

- phase 2 baseline production 4 件产物 + foundation.key_figures 补齐都走 repair_agent file-level lifecycle，与 phase 3 同形态
- 现有 phase 2 测试通过（含 length-tolerance gate 兜底）
- ai_context 措辞 disambiguation 完成（不再把 phase 2/4 描述成"经 repair_agent"）
- 端到端跑一个 work：phase 2 任意环节产物 schema 违规 → repair_agent 自动修复（无需 user 重跑）

**依赖**：无技术依赖（与 foundation 重构正交，可独立启动）；设计前置：先盘点 phase 2 4 件产物的常见违规模式 + 决定 checker / fixer 切分粒度

**暂不做的事**

- 不在 foundation 重构 /go（2026-05-11）一并做——拆出来作独立 todo，避免 PR/log 爆炸
- 不动 phase 3 现有 repair_agent 接入（已稳定运行多个 stage）

---

### [T-PLUGIN-README] 写 .agents/skills 的 plugin README

**上下文**

2026-04-28 把 6 个 skill（commit/go/full-review/post-check/monitor/check-review）
里的项目专属 hardcode 抽到 `ai_context/skills_config.md`，新项目接 plugin
只需复制 `.agents/skills/` + `.claude/commands/` + 在 ai_context 下填一份
`skills_config.md` 即可跑。但目前 plugin 装上去后，新项目不知道去哪读
"每节怎么填 / 缺失行为 / 模板"——这些信息散落在 skills_config.md 注释
和各 skill 的 0a 段里，没有单一入口文档。

**改动清单**

- file: `.agents/skills/README.md`（新增）→ 列出 plugin 装上去后的 setup 流程：
  1) 在目标项目 `ai_context/` 下创建 `skills_config.md` + 9 节模板
  2) 每节字段语义、可空值约定、缺失行为
  3) 每节由哪些 skill 用、怎么用
  4) Cross-File Alignment 提醒
- file: `ai_context/skills_config.md`（offpage 实例）→ 顶部加一行链接
  "字段语义 / 模板 / 缺失行为详见 .agents/skills/README.md"

**完成标准**

- README 存在，9 节字段全覆盖，含每节"完整填值 / `(none)` / 缺失"
  三态在各 skill 中的具体行为表
- 拿一个新项目模拟接入：跟着 README 填 skills_config.md → 跑 `/commit`
  / `/full-review` 都能正常降级或运行

**依赖**：无（skills_config.md 已落地、6 skill 改造已完成）

---

---

### [T-CHAR-SNAPSHOT-SUB-LANES] character stage_snapshot 拆 3 sub-lane 并行抽取

**更新时间**：2026-05-12 EDT

**上下文**

Phase 3 单 stage 的 char_snapshot lane 是当前 wall-time 最长的瓶颈
（粗估 T，monolithic 模式 ≈ 49 stage 累加显著；light_novel 模式 stage 数
≈ chapter 数，单 stage 更小，sub-lane 启动开销可能 > 抽取耗时收益——
跑 light_novel 时由用户手动 `--no-char-snapshot-sub-lanes` 切换，不引入
mode-aware schema 默认值，详见"暂不做的事"）。讨论后定方案：把单个
char_snapshot lane 拆成 3 个并行 sub-lane（按字段聚类）；3 份 partial JSON
由程序合并成完整 stage_snapshot.json，再走 file-level repair_agent
（最多 2 lifecycle，per T-REPAIR-T3-LIFECYCLE-RESET：lifecycle 1 末端
T3 触发 → state reset → lifecycle 2 按 sub-lane 模式重新 extract →
re-merge → re-validate）。schema 不动、世界 lane 和 char_support lane
不动、其他 phase 不动。

**prev_snapshot 处理（两个层面，sub-lane / 单 lane 模式均适用）**

phase 3 keys == baseline 硬约束 + prompt 各档 prev 处理规则**已由决策 #13
+ #11f + 现存 checker `automation/repair_agent/checkers/targets_keys_eq_baseline.py`
+ prompt 模板 §核心规则 #2 全量承载**——本 todo 不重述，只在此约束
sub-lane merge 阶段的边界感知：

**层面 1（per-target，三档）**：`target_voice_map` / `target_behavior_map` /
`relationships` 三个按 target 索引的字段——keys 必须与
`baseline.targets[].target_character_id` **双向 set-equal**（决策 #13 D4
硬约束）。三档由内容是否填充承载：

- 从未登场 → entry 必须存在 + 所有字段为空（fixed_relationship 例外可
  预填，见决策 #13）
- 见过但本 stage 未出场 → entry 存在 + 原样继承 prev
- 本 stage 出场 → entry 存在 + 内容按层面 2 四态推演

**层面 2（per-item，四态）**：每条 entry / 每个数组项的 prev → curr 演化
按决策 #11f 四态：

- (A) prev absent → 继承 verbatim
- (B) present + changed → 按本阶段原文重写 + stage_delta 写关键变化
- (C) present + unchanged → 保留 prev（required 字段仍要填，"无变化"
  不等于"跳过"）
- (D) **resolved / revealed / 克服 → drop entry + stage_delta 写消除原因**

**(D) 对 sub-lane merge 校验的影响**：`char_cognition` lane 承包的
`misunderstandings` / `concealments` / `failure_modes.{common_failures,
relationship_traps, knowledge_leaks}` 全都吃 (D) 语义——merge 时 "prev
有但 partial 没有某条 entry" 不一定是抽错，可能是 (D) 解决了。merge 校验
**只查字段集合互斥 + 全覆盖**（schema properties 全集），**不查 entry 数
是否 ≥ prev**——后者由 stage_delta 自由文本承载、由 phase 3.5
consistency_checker 跨文件审计兜底，不在 sub-lane merge 范围。

**字段归属表**

> 设计约束：`stage_snapshot.schema.json` 顶层 `additionalProperties: false`
> ——三 sub-lane partial 字段集合 ∪ 程序注入 必须**严格等于** schema
> properties 全集（不能多、不能少），merge 函数前置校验。

| sub-lane | 字段 |
|---|---|
| `char_expression` | `voice_state` / `active_aliases` / `current_mood` / `failure_modes.tone_traps` |
| `char_decision` | `behavior_state` / `boundary_state` / `emotional_baseline` / `current_personality` / `current_status` / `stage_delta.status_changes` / `stage_delta.mood_shift` / `stage_delta.personality_changes` |
| `char_cognition` | `knowledge_scope` / `misunderstandings` / `concealments` / `relationships` / `relationship_state_summary` / `stage_events` / `character_arc` / `snapshot_summary` / `stage_delta.trigger_events` / `stage_delta.relationship_changes` / `stage_delta.voice_shift` / `failure_modes.common_failures` / `failure_modes.relationship_traps` / `failure_modes.knowledge_leaks` |
| 程序注入 | `schema_version` / `work_id` / `character_id` / `stage_id` / `stage_title` / `timeline_anchor` / `chapter_scope` |

`stage_delta` 子键拆 char_decision / char_cognition 两 lane 的原因：
`status_changes` / `mood_shift` / `personality_changes` 与 char_decision 写
的 `current_status` / `current_mood` / `current_personality` 同源（避免
sub-lane 互不可见 → partial 不一致）；`trigger_events` / `relationship_changes`
/ `voice_shift` 与 char_cognition 的 relationships 联动。merge 函数把两
lane 的 stage_delta 子 object 合并，**子键互斥**（每子键只允许一个 lane
写）+ **6 子键全覆盖**（缺一即 partial 失败）。

`failure_modes` 4 子键分布到 **2 lane**（`tone_traps` → char_expression，
`common_failures` / `relationship_traps` / `knowledge_leaks` → char_cognition）：
merge 校验"4 子键互斥 across 2 lane + 4 子键齐"双约束（schema 上 4 子键
非 required，但运行时假设全有，所以 merge 层加 hard gate）。

**task balance 决策（2026-05-02）**：粗算各 lane 最大输出 char 数
（含 N=5 target；schema `maxItems × maxLength` 折算）—
char_expression ~22K / char_decision ~26K / char_cognition ~28.3K，
bottleneck 28.3K（理论加速比 ~2.3×）。比较：
- 4 子键拆 3 lane（tone→expr / common→dec / relationship+knowledge→cog）：
  bottleneck 33.6K（decision 重），merge 互斥需 across 3 lane，复杂度高
- 4 子键整块归 cog：bottleneck 29.8K，cog 单调用 output 风险最高，且
  tone_traps 离开 expression 牺牲"语气写崩↔语气写法"theme coupling
- **当前选 F**（tone 留 expr / 其余 3 子键归 cog）：bottleneck 最低 + 保
  tone↔voice 同源 + common_failures 离开 decision（schema description 写
  "AI 扮演该角色时最常见的错误模式"跨三方，挂 decision 凑数；reflective
  性质归 cognition 同源）

**流程**

```
sub_lanes = true:
  Step 1: 3 sub-lane 并行 extract → .partial/{stage_id}_{lane}.json
          每 sub-lane 输入：identity + 上阶段 snapshot + 章节原文 +
          phase 2 target_baseline.json + 本 lane 字段集合白名单
  Step 2: 程序 merge → canon/stage_snapshots/{stage_id}.json，
          清理 lane partial；merge 校验：字段集合互斥 + 全覆盖 schema
          required + failure_modes 4 子键互斥 across 2 lane（tone_traps
          仅 expr / 其余 3 子键仅 cog）+ stage_delta 6 子键互斥 across
          2 lane（dec / cog）+ 三方 keys 一致 + keys == baseline
  Step 3: file-level repair_agent（最多 2 lifecycle，per
          T-REPAIR-T3-LIFECYCLE-RESET）：
          - lifecycle 1：file-level L1/L2/L3 repair；末端若 T3 触发
            → state reset → lifecycle 2 启动
          - lifecycle 2：按 sub-lane 模式重新 extract（3 sub-lane 并行
            → re-merge → re-validate），lifecycle 2 默认禁用 T3，再升
            T3 即 T3_EXHAUSTED；每 sub-lane prompt 注入 prior_attempt_context
            （resolved+remaining 摘要 ≤600 char）+ 错误信息
          - fingerprint 过滤为 file-level（merge 后整文件 hash），
            sub-lane 间共享、不各自维护

sub_lanes = false（fallback 模式）：
  单 lane char_snapshot + file-level 2 lifecycle 标准流程——即 phase 3
  现状，本 todo 不改变 fallback 行为。baseline 锚点（已通过
  build_char_snapshot_prompt read list 注入）+ #11f 四态（已落地于 prompt
  §核心规则 #2）+ keys == baseline 校验（已落地于 checker
  targets_keys_eq_baseline.py）均为 phase 3 通用现状，不需 sub-lane 专门
  改造
```

**改动清单**

> 注：三方 keys == baseline 的跨文件校验**已存在**于
> `automation/repair_agent/checkers/targets_keys_eq_baseline.py`（L2
> checker，已在 `coordinator.py:86` 注册到 file-level repair pipeline）—
> 不需要重写到 `consistency_checker.py`；sub-lane merge 阶段 Step 2 复用
> 同一 checker 做早期预检即可。

新增：
- `automation/persona_extraction/snapshot_merge.py`（或并入
  `post_processing.py`）— Step 2 merge：按字段归属表拼接 + 校验字段
  集合互斥（含 stage_delta 6 子键互斥 across 2 lane + failure_modes 4
  子键互斥 across 2 lane：`tone_traps` 仅 char_expression 写、`common_failures`
  / `relationship_traps` / `knowledge_leaks` 仅 char_cognition 写）+
  字段集合 ∪ 程序注入 == schema properties 全集（schema
  `additionalProperties: false` 配套）+ stage_delta / failure_modes 子键
  全覆盖（缺一即 partial 失败）+ 复用
  `repair_agent/checkers/targets_keys_eq_baseline.py` 早期预检三方 keys
  == baseline + 注入结构性字段（`schema_version` / `work_id` /
  `character_id` / `stage_id` / `stage_title` / `timeline_anchor` /
  `chapter_scope`）+ merge 成功后写入 file-level fingerprint（整文件
  hash，供 lifecycle 2 启动时按 T-REPAIR-T3-LIFECYCLE-RESET 已 accept
  fingerprint 过滤复用——sub-lane 间共享、不各自维护）

修改：
- `automation/prompt_templates/character_snapshot_extraction.md` — **保留
  单一文件（不拆 3 份）**。加 `{lane_scope}` 占位（取值 `ALL` /
  `char_expression` / `char_decision` / `char_cognition`）+
  `{lane_field_whitelist}` 占位；prompt 头部按 lane_scope 注入"本次仅写
  以下字段"约束。**不动 §核心规则 #2 prev_snapshot 四态规则段**（决策 #11f
  + #13 已是 phase 3 通用准则，sub-lane / 单 lane 全 inherits）。**不动
  §maxItems 触顶时的裁剪规则段**（决策 #11e 通用准则，与字段归属正交）。
  字段归属表移到代码（同一来源给 sub-lane 调度 + merge 用，避免 prompt
  与 merge 字段集合漂移）；fallback 模式 `lane_scope=ALL` 等价单 lane
  即 phase 3 现状
- `automation/persona_extraction/orchestrator.py` — sub-lane 调度
  （新建独立 ThreadPoolExecutor 与 repair pool 共用同一 `RateLimitController`
  信号源，hard-stop 任一池都触发 `executor.shutdown(cancel_futures=True)`）
  + .partial 清理；分支 `if config.phase3.char_snapshot_sub_lanes` 包住三
  lane 路径，否则走单 lane（fallback 即 phase 3 现状，不需额外注入逻辑）。
  调用点 `prompt_builder.build_char_snapshot_prompt(..., lane_scope=...)`
  增 1 入参
- `automation/persona_extraction/prompt_builder.py` —
  `build_char_snapshot_prompt` 增 `lane_scope` 入参（`ALL` / `char_expression`
  / `char_decision` / `char_cognition`），context dict 注入 `{lane_scope}` /
  `{lane_field_whitelist}` 两键。**`target_baseline` 已通过
  `_build_char_snapshot_read_list` 写入 read list（[prompt_builder.py:540-541](automation/persona_extraction/prompt_builder.py#L540-L541)，phase 3 现状）**，不需新加 path 入参
- `automation/repair_agent/coordinator.py` 或对应 lifecycle dispatcher
  （**实际路径在 `automation/repair_agent/`，非 `persona_extraction/repair_agent/`**）
  — sub-lane 开启时 lifecycle 2 启动改走 3 sub-lane 并行重新 extract（替代
  现行单 lane 重抽）+ 每 sub-lane prompt 注入 prior_attempt_context（resolved
  + remaining 摘要 ≤600 char）+ 错误信息；lifecycle 计数（`max_lifecycles_per_file
  = 2`）的 +1 时机仅在「T3 真正触发并 reset 进入下一轮」，rate-limit pause
  重跑**不**消耗 lifecycle 槽（R1）
- `automation/persona_extraction/progress.py` — disk reconcile 扩展识别
  `.partial/{stage_id}_{lane}.json` 命名（不只是 `<stage>/<lane>` 现有
  约定），PENDING/ERROR lane 的 partial 一律删
- `automation/persona_extraction/config.py` + `automation/config.toml` +
  `automation/config.toml.example` — 新增
  ```toml
  [phase3]
  char_snapshot_sub_lanes = true
  ```
- `automation/persona_extraction/cli.py` — `--char-snapshot-sub-lanes`
  / `--no-char-snapshot-sub-lanes` 双向 flag
- `.gitignore` — `works/*/characters/*/canon/stage_snapshots/.partial/`
- `docs/architecture/extraction_workflow.md` § Phase 3 — 描述 sub-lane
  拆分（3 sub-lane 并行 → merge → file-level repair_agent）；
  prev_snapshot 四态 + keys == baseline 已在 schema_reference / 决策 #11f
  + #13 描述，不在此重述
- `automation/README.md` — Phase 3 说明 + toml 配置文档
- `ai_context/architecture.md` § Automated Extraction Pipeline — 一句话
  补充 sub-lane 拆分
- `ai_context/decisions.md` — 新增决策：char_snapshot sub-lane 拆分（字段
  归属表 + merge 校验 + file-level repair lifecycle 2 重抽走 sub-lane 模式）
- `docs/requirements.md` §11 — 同步描述

**rate-limit / 掉线兼容（推荐方案）**

- 每 sub-lane 调用走 `run_with_retry`，自然继承现行 `RateLimitController`
  pause / resume 机制（决策 46）
- 显式处理 3 点：
  - **R1 lifecycle 内 rate-limit pause 不消耗 lifecycle 槽**（per
    T-REPAIR-T3-LIFECYCLE-RESET 已废弃 `t3_max_per_file` 计数器，
    改用 `max_lifecycles_per_file = 2`）：lifecycle 计数只在「T3 真正
    触发并 reset 进入下一轮」时 +1，rate-limit pause 重跑不计数
  - **R2 hard-stop 时 cancel 同胞 sub-lane**：A 抛 `RateLimitHardStop`
    → orchestrator catch → `executor.shutdown(cancel_futures=True)` +
    删除已写 .partial → exit 2
  - **R3 .partial 残留清理**：disk reconcile 启动时扫 .partial，PENDING/ERROR
    lane 的 partial 一律删（不尝试复用），整 lane 重跑

**完成标准**

- toml `[phase3].char_snapshot_sub_lanes = true` + CLI 双向 flag 生效
- sub_lanes=true 跑通：Step 1/2/3 完整，merge 后 schema 校验通过
  （`additionalProperties: false` 不报漂移字段）
- sub_lanes=false 跑通：单 lane 走 phase 3 现状路径（baseline + #11f 四态
  + keys == baseline 校验均为 phase 3 通用行为，已落地，不在本 todo 验收
  范围；仅需确认 `lane_scope=ALL` 不破坏现有行为）
- 3 sub-lane partial 字段集合 ∪ 程序注入 == schema properties 全集（merge
  前置校验，覆盖 schema 所有 required + 非 required 字段，无漂移）
- failure_modes 4 子键按字段归属表互斥分布到 char_expression（tone_traps）/
  char_cognition（其余 3 子键）+ 全 4 子键覆盖（hard gate，缺一即 partial
  失败），merge 后字段完整
- stage_delta 6 子键按字段归属表互斥分布到 char_decision / char_cognition +
  全 6 子键覆盖（hard gate，缺一即 partial 失败）
- sub-lane merge 阶段调用现有 `repair_agent/checkers/targets_keys_eq_baseline.py`
  做早期预检（三方 keys == baseline 校验本身已是 phase 3 现状，本条仅验
  merge pre-flight 调用点接入正确——预检失败应在 merge 写盘前阻断，避免
  漂移产物落到 file-level repair 才被发现）
- (D) resolved/revealed/克服 entry drop 不被 merge 误判：merge 校验**不查**
  partial entry 数 ≥ prev（仅查字段集合互斥 + 全覆盖），entry 数变化由
  stage_delta 自由文本承载、phase 3.5 consistency_checker 跨文件审计兜底
- lifecycle 1 末端 T3 触发 → state reset → lifecycle 2 启动时按 sub-lane
  模式重新 extract（3 sub-lane 并行），re-merge 后 re-validate；lifecycle 2
  默认禁用 T3，再升 T3 即 T3_EXHAUSTED
- file-level fingerprint：merge 成功后写入整文件 hash；lifecycle 2 启动
  前按已 accept fingerprint 过滤（sub-lane 间共享，不各自维护）
- rate-limit 兼容：R1/R2/R3 在测试场景下行为符合上述描述（含 sub-lane
  pool 与 repair pool 共享 RateLimitController 信号源，任一 hard-stop
  双池齐落；R1 已对齐 lifecycle 槽语义）
- disk reconcile 启动时正确清理孤儿 `.partial/{stage_id}_{lane}.json`
- 文档（architecture / extraction_workflow / README / ai_context / requirements）同步

**预估**

- 中量改动（新增 1 模块 + 修改 ~10 文件 + prompt 加 lane_scope 占位）；
  原"phase 3 全模式 target keys 约束改造"半边已被前置工作消化（决策 #13
  + checker 落地），本 todo scope 较 2026-05-02 版本缩水 ~25%
- 实施 ~1 个工作日；首次跑 1 stage 验证 sub_lanes=true（merge + lifecycle
  + R1/R2/R3）与 sub_lanes=false（lane_scope=ALL 不破坏现有 phase 3 行为）
  两套路径
- 排期基于 monolithic 底数；light_novel 模式排期与开关行为不再"按 mode
  重评"——保持单 toml bool + CLI 双向 flag，跑 light_novel 时由用户
  `--no-char-snapshot-sub-lanes` 切换（详见"暂不做的事"）

**依赖**

- **决策依赖（全部已落地）**：
  - **#13** phase 3 keys == baseline by-construction（set-equal hard fail）
    — checker `automation/repair_agent/checkers/targets_keys_eq_baseline.py`
    已注册到 [coordinator.py:86](automation/repair_agent/coordinator.py#L86)，
    本 todo 仅在 sub-lane merge 阶段复用其做早期预检
  - **#11d** 4 件套废弃 + `failure_modes` 4 子类内联 stage_snapshot 顶层
    — 本轮 phase 3 S001 实测产出形态正确（详见 logs/change_logs/
    2026-05-11_135437_baseline_deprecate_archive.md）
  - **#11e** maxItems-aware truncation rule — 已落地于 prompt §maxItems
    触顶时的裁剪规则；sub-lane prompt 不动该段，直接 inherits
  - **#11f** prev_snapshot 四态 A/B/C/D — 已落地于 prompt §核心规则 #2；
    sub-lane prompt 不动该段，merge 校验需感知 (D) drop 语义（见上方
    "(D) 对 sub-lane merge 校验的影响"）
  - **#25 / #48** repair_agent lifecycle 1/2 + T3_EXHAUSTED（仅 phase 3）
    — 已落地于 `automation/repair_agent/coordinator.py`
  - **#54** target_baseline 准入门槛收紧（dialogue/action 交互）— 已落地；
    baseline cardinality 缩小对本 todo 是正向影响（sub-lane 输入 token
    随之缩小）
- **任务依赖（全部已完成）**：T-PHASE2-TARGET-BASELINE / T-BASELINE-DEPRECATE
  均于 2026-05-11 完成
- 全部依赖已就位 — 本 todo 可启动

**暂不做的事**

- 不拆分 sub-lane 输入（每 sub-lane 仍拿完整源 + 上阶段 snapshot +
  baseline，token 总量约 ×3，订阅模式可承受）
- 不拆 schema（character / stage_snapshot 结构不动）
- 不动 world lane / char_support lane / 其他 phase
- 不允许 stage 突破 baseline（即使 baseline 漏判某 target，也由人工
  编辑 baseline + stage 重抽处理，不引入 escape hatch）
- 当前 work package 切到新模型的时序问题不在本任务内（按用户原则
  「不过度工程，整 lane 重跑」处理）
- **不引入 mode-aware sub_lanes 默认开关**——`structure_mode` 是 work 级
  manifest 属性（per T-INGEST-STRUCTURE-MODE），不复制到 phase 3 toml /
  代码内做分支；保持 toml 单 bool + CLI 双向 flag 设计，light_novel 跑
  时由用户手动 `--no-char-snapshot-sub-lanes` 切换（单 stage 字符数小，
  3 sub-lane 启动开销可能 > 抽取耗时收益）。phase 3 extraction 不需要
  知道 mode


## Discussing (Undecided)

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

### [T-CODEX-STDIN] CodexBackend prompt 走 stdin 临时文件

**上下文**

`ClaudeBackend` 已在
`automation/persona_extraction/llm_backend.py::ClaudeBackend.run` 把 prompt
改走唯一临时文件 + stdin，绕过 Linux `MAX_ARG_STRLEN ≈ 128 KiB` 的 argv
上限。`CodexBackend.run` 仍用 `cmd = ["codex", "--quiet", "--full-auto",
prompt]`（同文件 L378 附近），大 prompt（尤其 T3 全文件 regen）会在
切到 `--backend codex` 时复现 `[Errno 7] Argument list too long`。

当前已加注释标注风险，未改代码——本机未安装 codex CLI 无法实测其 stdin
接口（是否自动读 stdin / 是否要 `-` / 是否要 `--prompt -`）。

**待决策项**

1. codex CLI 的 stdin 契约到底是哪种形式？三种候选：
   - `echo 'hi' | codex --quiet --full-auto`（自动读 stdin）
   - `codex --quiet --full-auto -`（显式 `-`）
   - `codex --quiet --full-auto --prompt -`（`--prompt` flag + `-`）
2. 是否仍坚持与 ClaudeBackend 对称？也可以走 `--input-file /tmp/xxx` 这类
   文件传递（若 codex 支持），避免 stdin 管道在并发下意外关闭的风险

**改动清单（待契约确认后落地）**

1. `automation/persona_extraction/llm_backend.py::CodexBackend.run` 复用
   `_prompt_tempfile` + stdin 文件句柄的写法，移除 cmd 中的 positional
   prompt
2. 删掉 `CodexBackend.run` 开头那段 "NOTE: codex CLI still receives the
   prompt via argv ..." 注释
3. 小 prompt smoke：`create_backend('codex', ...).run('ping')`

**暂不做的事**

- 不在没有 codex CLI 的机器上盲改——三种候选形式有两种会 silent hang，
  必须实测
- 不把 argv 传递路径保留为 fallback——要么切 stdin 要么不切，保留两路
  只会让并发下的错误更难定位

**依赖**：有 codex CLI 的机器 / 订阅

**未落地原因**

- 当前所有 extraction 默认走 `--backend claude`，codex 分支未被激活使用；
  问题是潜在风险而非阻塞

---

### [T-CODEX-RATE-LIMIT] CodexBackend 错误分类对齐 rate-limit / 429 / 5h_window

**上下文**

`automation/persona_extraction/llm_backend.py::ClaudeBackend.run` 已经
通过 `_classify_rate_limit`（涵盖 `rate limit` / `rate_limit` /
`too many requests` / `429`）把 stderr 命中映射为 `error="rate_limit: ..."`，
进入 `run_with_retry` 的 pause-controller 分支。`CodexBackend.run` 在
`returncode != 0` 时直接返回 `error=f"exit {N}: {stderr}"`，**没有过
`_classify_rate_limit`**——意味着 codex 端撞限额会走普通失败 / retry，
不会写共享 pause file，多 worker 并发更容易消耗 retry budget 或产生 ERROR。

`docs/requirements.md` §11.13.4 明确 `429` / `rate limit` 是通用 retry
关键词，跨 backend 应一致；本机当前默认 `--backend claude`，问题潜在但未
触发。

**待决策项**

1. CodexBackend 的 stdout / stderr 分别承载哪些限额信号？
   （Anthropic claude CLI 把限额放 stderr；codex CLI 行为本机不可实测）
2. 是否同时把 `5h_window` / `weekly` 等 Claude 专用关键词也通过同一函数对齐
   codex 端，还是 codex 端只走通用 `_classify_rate_limit`

**改动清单（待 codex CLI 实测后落地）**

1. `automation/persona_extraction/llm_backend.py::CodexBackend.run`
   `returncode != 0` 分支：先 `_classify_rate_limit(stderr)` /
   `_classify_rate_limit(stdout)`，命中则返回 `error=f"rate_limit: ..."`
2. （可选）把 `from .rate_limit import classify_error` 引入并用统一函数
   做 `5h_window` / `weekly` 二级分类
3. smoke：在有 codex CLI 的环境跑撞限额场景，确认 `RateLimitController`
   能进入 pause

**暂不做的事**

- 不在没有 codex CLI 的机器上盲改 stderr 关键词假设——不同 CLI 措辞差异大
- 不把 Claude 端的 `_RATE_LIMIT_SIGNALS` 列表硬编进 codex 端——保留 codex
  端独立的 stderr 解析空间

**依赖**：有 codex CLI 的机器 / 订阅；本条与 T-CODEX-STDIN 同环境，可同批跑

**未落地原因**

- 默认 backend 是 claude；codex 分支未激活使用

---

### [T-PROMPT-SCHEMA-INJECT] prompt 模板从 schema 自动注入具体 bound

**上下文**

`ai_context/conventions.md` §"Bounds only in schema" 要求所有
`maxLength` / `minLength` / `maxItems` 数值只在 schema 写一次。但
`automation/prompt_templates/character_support_extraction.md` /
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

- 路径 A：`automation/persona_extraction/prompt_builder.py` 增加
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

### [T-SIMULATION-MODE-MARKER] simulation 运行时注入 worker-mode marker

**上下文**

`CLAUDE.md` / `AGENTS.md` 顶部的 Worker-Mode Short-Circuit 已预留
`[simulation_runtime_mode]` 标记：当 system prompt 包含该字符串时，
worker 跳过 `ai_context/` 加载与所有自检，只按 user prompt 执行。

extraction 侧已在 [automation/persona_extraction/llm_backend.py](../automation/persona_extraction/llm_backend.py)
注入对应 `[extraction_worker_mode]`。simulation 侧预留了入口但尚无代码：
`simulation/` 当前只有 contracts / flows / prompt_templates / retrieval /
README.md，零 Python。

**待决策项**

1. simulation runtime 的 LLM backend 选型（是否复用 `ClaudeBackend` 类，
   还是独立 backend）
2. marker 注入点：每轮 user→character 对话的 LLM 调用、retrieval
   辅助调用、`search_memory` tool 的内部 LLM 调用，全部都需注入还是
   按调用类型区分

**完成标准**

- simulation runtime 首个实装的 LLM 调用处，命令行参数追加
  `--append-system-prompt "[simulation_runtime_mode]"`（或等价机制）
- 本 todo 条目移到 archived

**未落地原因**

- simulation runtime 尚未开始实装；无注入点

**依赖**：simulation runtime 首次实装

---

### [T-PHASE5-RETRIEVAL] 新增 Phase 5 生成 retrieval 产物

**上下文**

多处 canonical docs 宣称 `works/*/indexes/` 是 committed 产物
（`ai_context/current_status.md:157`、`ai_context/requirements.md:229`、
`ai_context/decisions.md:174,225`、`docs/architecture/data_model.md:160,475`、
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

- retrieval 层整体设计尚未动工（见 `ai_context/current_status.md` Current
  Gaps：No retrieval implementation）
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

T-LOG 已落地：[llm_backend.py:565-680](../automation/persona_extraction/llm_backend.py#L565-L680) `run_with_retry` 已能解析 subtype / num_turns / total_cost_usd 并附在 LLMResult 与错误消息上。但 retry 决策本身**还没用上 subtype 分流**，且短时阈值仍是 5s（[config.toml:130](../automation/config.toml#L130) `fast_empty_failure_threshold_s = 5`）。

**现有机制**（截至 2026-04-27）

| 错误类型 | 识别 | 处理 | 状态 |
|---|---|---|---|
| `fast_empty_failure` | duration < 5s + stderr 空 + exit N | 按 backoff 序列重试（30s/60s/120s） | ✅ 已实现 |
| `rate_limit` / `usage_limit` | stderr 含 "rate limit" / "weekly" / "5-hour" / "too many requests" | 暂停所有新请求直到 reset，重发同一 prompt（不消耗 retry slot，§11.13） | ✅ 已实现 |
| `token_limit` | stderr 含 "context window" / "max_tokens" 等 | 不重试 | ✅ 已实现 |
| 通用长时 exit N | stderr 空 + duration 长 | 不重试（直接 return） | ⚠️ 当前未按 subtype 分流 |

**待落地（具体改动）**

1. **短时阈值扩大**：[config.toml:130](../automation/config.toml#L130) `fast_empty_failure_threshold_s` 从 5s 扩大到 60s（候选 120s）。
   - 理由：char_snapshot 正常 10-20m，任何 <60s 失败几乎一定不是真正工作后失败，是 CLI launch / API 连接错误。
   - 风险极小（<60s 浪费），独立可先行
2. **长时 exit 按 subtype 分流**：[llm_backend.py `run_with_retry`](../automation/persona_extraction/llm_backend.py) 在"非可重试错误"return 之前加一段判断：
   - `subtype == "error_max_turns"` → 不重试（同 prompt 必再次触达）
   - `subtype == "error_during_execution"` → 重试 1 次（瞬态可能性大）
   - 无 subtype / 解析失败 → 可选重试 1 次（默认开 / 可由 config 关）
3. **退避策略不动**：30s/60s/120s 已合理

**改动清单**

1. [automation/config.toml:130](../automation/config.toml#L130) 改 `fast_empty_failure_threshold_s = 60`（或 120，待拍板）
2. [automation/persona_extraction/llm_backend.py `run_with_retry`](../automation/persona_extraction/llm_backend.py) 加 subtype 分流分支
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
