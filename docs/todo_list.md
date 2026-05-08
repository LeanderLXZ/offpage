# TODO List（待办任务清单）

---

## Index (auto-generated; do not hand-edit)

> 本段是三张子表的渲染缓存，由维护本文件的人（包括 Claude）在**每次对正文条目增 / 改 / 移段 / 完成 / 废弃后**顺手刷新——具体规则见下方"## File guide → Index maintenance"。`/todo` skill 不解析正文，只读这一段，所以这里的内容必须与正文同步；不同步会让 `/todo` 给出错误结论。

### 🟢 In Progress (5)

| ID | Title | Start time | Updated | Status |
|---|---|---|---|---|
| `T-BASELINE-DEPRECATE` | 废弃 voice_rules / behavior_rules / boundaries / failure_modes 4 件套，identity 重定位为模拟时加载 | 2026-04-29 14:42 EDT | — | 代码完成、runtime 验证待跑 |
| `T-PHASE2-TARGET-BASELINE` | phase 2 产出 per-character target_baseline，作为 phase 3 全模式的 target keys 锚点 | 2026-04-29 20:54 EDT | — | 代码完成、runtime 验证待跑（与 BASELINE-DEPRECATE 同形态，可同批跑） |
| `T-INGEST-STRUCTURE-MODE` | Phase 0/1 双模式（monolithic / light_novel）调度 | 2026-05-01 07:04 EDT | 2026-05-01 | schema/code/prompt/ai_context/docs 完成 + post-check 两轮残留缺口（stage_title 软截断改用启动时动态读取 schema cap + progress.py reconcile C 前缀兼容 + cosmetic 全过）已修；end-to-end runtime 验证待跑（需 light_novel fixture 与 monolithic 既有 fixture 双向回归） |
| `T-PHASE0-CHUNK-SCHEMA-EXPAND` | chapter_summary_chunk schema 二级字段扩展（命中 world_overview / foundation 不可信字段） | 2026-05-04 14:50 EDT | 2026-05-08 | schema/prompt/ai_context/docs 完成 + 静态 gate 全过（jsonschema metaschema OK；样本 chunk 1 valid + 10 negative case 全过；orchestrator + validator import 通过；grep 无 chapter.location 残留）；runtime 验证待跑（与 T-BASELINE-DEPRECATE / T-PHASE2-TARGET-BASELINE / T-INGEST-STRUCTURE-MODE 同批跑）。**注**：本任务的 per-summary 字段计划（key_events 保留 + summary 100-150）已由 T-ANALYSIS-SCHEMA-TIGHTEN 进一步收紧（key_events 删 + summary 150-200） |
| `T-ANALYSIS-SCHEMA-TIGHTEN` | 收紧 phase 0 chunk + phase 1 candidate / world_overview schema 字段（chunk 删 `key_events` + `summary` 100-150→150-200；candidate 删 `recommended` + `aliases.first_appearance` + Phase 1.5 默认勾选改基于 `importance==主角`；world_overview `major_regions` / `levels` item 升对象 + `core_rules` 20→30 / 100→150） | 2026-05-08 10:26 EDT | 2026-05-08 11:06 EDT | schema/prompt/code/ai_context/docs 完成 + 静态 gate 全过（3 件 schema metaschema OK；正样本 + 多 negative case 全过；orchestrator + prompt_builder + validator + scene_archive import 通过；grep 无 key_events / first_appearance / recommended 残留主动引用）；e2e 验证待跑（清掉现有 untracked `works/<work_id>/` 后从 phase 0 全新跑——schema gate 不报红 + phase 0/1/1.5/2 全过为标准） |

### 🟡 Next (2)

| ID | Brief | Importance | Ready | Scope | Updated | Deps |
|---|---|---|---|---|---|---|
| `T-PLUGIN-README` | 2026-04-28 把 skills 项目专属内容抽到 `ai_context/skills_config.md`，但新项目装 plugin 时不知道每节怎么填 / 缺失行为 / 模板。需写 `.agents/skills/README.md` 作为 setup 单一入口。 | 🟢 Med-Low | ✅ Ready | 🟢 Small | — | 无 |
| `T-CHAR-SNAPSHOT-SUB-LANES` | character stage_snapshot 拆 3 sub-lane（char_expression / char_decision / char_cognition）并行 + repair lifecycle，单/三 lane 都吃 phase 2 target_baseline + 三态规则，三方 keys == baseline by-construction（合并 phase 3 全模式 keys 约束改造）。 | 🟢 High | ⏸ Blocked | 🔴 Large·Arch | 2026-05-02 | T-PHASE2-TARGET-BASELINE + T-BASELINE-DEPRECATE |

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
**Total**: 15 — 🟢 In Progress 5 ｜ 🟡 Next 2 ｜ ⚪ Discussing 8

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

### [T-BASELINE-DEPRECATE] 废弃 voice_rules / behavior_rules / boundaries / failure_modes 4 件套，identity 重定位为模拟时加载

**开始时间**：2026-04-29 14:42 EDT

**当前状态**：代码完成、runtime 验证待跑（schema / 代码 / prompt / docs / 迁移脚本均已落地，jsonschema + import 静态验证通过；下一步需在 extraction 分支跑迁移脚本 `--apply` + 重抽 1-2 stage 验证 stage_snapshot.failure_modes 产出 + 命中 maxItems 时裁剪生效）

**上下文**

现行 character/canon/ 下 6 个 baseline 文件中（schema 详见 schemas/character/）：
- **voice_rules.json / behavior_rules.json / boundaries.json**：顶层
  字段与 stage_snapshot 字段几乎一一对应（target_voice_map / core_goals
  / hard_boundaries 等），是结构性冗余。运行时不加载（[character_snapshot_extraction.md:52-55](../automation/prompt_templates/character_snapshot_extraction.md) 明文）
- **failure_modes.json**：角色级诊断手册（common_failures /
  knowledge_leaks / tone_traps / relationship_traps）。本质同样是
  "演变会发生但被强行做成恒定层"——某些 mode 在 stage 间会消除 / 新增
- **identity.json**：角色基础事实（aliases / canonical_name / gender /
  species / appearance / background / core_wounds 等），永不变化，
  不与 stage_snapshot 字段重合
- **character_manifest.json**：元数据（paths / created_at / role_labels），
  与 prompt 内容生成无关

讨论后定方案：

1. **废弃 4 件套**（voice_rules / behavior_rules / boundaries /
   failure_modes）：内容归入 stage_snapshot 演变链；S001 是基线种子
   （从原文 + identity 推演），S002+ 从 prev 演变
2. **identity 重定位** 为 character-level 恒定文件 + 未来 simulation
   runtime 加载（"最 common、永不变、模拟时加载"原则）
3. **manifest** 从 char_snapshot prompt 的 files_to_read 移除（元数据，
   对内容生成零价值）
4. **stage_snapshot 加 failure_modes 字段**（每 stage 全量；schema 直接
   搬用原 failure_modes 文件 schema：4 子类 common_failures /
   knowledge_leaks / tone_traps / relationship_traps，子类上下限完全
   照旧）。模拟时只读当前 stage 即可，无需向前 trace 多个文件
5. **stage_delta 不动**：保留现行自由文本方案，不升级结构化（避免一次
   改动撞两个 schema 决策）；voice_state / behavior_state /
   boundary_state 等字段维持现行 full-state（每 stage 完整重抽，无变化
   也照抄）
6. **prompt 加 maxItems-aware 裁剪规则**（统一规则，对所有带 maxItems
   上限的字段生效，不限于新增的 failure_modes 4 子类）：触发上限时由
   LLM 在抽取阶段就按"最重要、最符合当前 stage 需要"先排序后截断，
   而非交给 schema validation 报错

**时机优势**：simulation runtime 尚未实装（[T-SIMULATION-MODE-MARKER]
仍在 Discussing），当前没有任何运行时代码依赖 4 件套——废弃决策不破坏
任何已运行的东西，是边际成本最低的时刻。

**改动清单**

新增 / schema 改动：
- `schemas/character/stage_snapshot.schema.json` 加 `failure_modes`
  对象字段（4 子类 common_failures / knowledge_leaks / tone_traps /
  relationship_traps；子类上下限直接照搬现行
  `schemas/character/failure_modes.schema.json`）
- 数据迁移脚本（一次性，新增）：扫描 `works/*/characters/*/canon/`，
  把现有 voice_rules / behavior_rules / boundaries 内容合并进 S001
  stage_snapshot 种子；现有 failure_modes 内容并入 S001
  stage_snapshot.failure_modes；废弃文件移到
  `works/*/characters/*/.archive/baseline_{ts}/`；在 `logs/change_logs/`
  写迁移日志

废弃 / 删除：
- `schemas/character/voice_rules.schema.json` /
  `behavior_rules.schema.json` / `boundaries.schema.json` /
  `failure_modes.schema.json` 删除

修改：
- `automation/persona_extraction/prompt_builder.py`
  `_build_char_snapshot_read_list`（[行 436-480](../automation/persona_extraction/prompt_builder.py#L436-L480)）：
  移除 voice_rules / behavior_rules / boundaries / failure_modes /
  manifest（5 文件）；保留 identity / 上阶段 snapshot / schema / 章节
- `automation/prompt_templates/character_snapshot_extraction.md`
  - 加「baseline 文件的角色定位」段：identity 是角色基础事实层
    （权威），4 件套已废弃不读取
  - 第 50-57 行「自包含快照」修订：明确 stage_snapshot 是角色状态唯一
    权威；模拟时**会加载** identity（character-level 恒定文件），但
    **不**加载已废弃的 4 件套
  - is_first_stage = true 分支：S001 必须基于本阶段原文 + identity
    直接推演出基线状态全字段（voice_state / behavior_state /
    boundary_state / failure_modes 等），不再依赖 baseline 4 件套
  - 新增 `failure_modes` 字段说明（每 stage 全量；4 子类上下限同原
    failure_modes schema）
  - 新增「maxItems 裁剪规则」段（**对所有带 maxItems 字段统一生效**，
    含 failure_modes 4 子类、target_voice_map / target_behavior_map /
    relationships 等）：触发上限时 LLM 在抽取阶段按"最重要、最符合
    当前 stage 需要"先排序后截断；判定锚点的细化（"最重要"基准 /
    子类是否独立计上限 / 跨字段是否有整体优先级）写 prompt 时与具体
    字段一起敲定
- phase 1/2 prompt 模板（待 grep 确定具体文件）：删除产出 4 件套指令；
  identity 仍然产出
- `ai_context/architecture.md` § Character canon：更新文件清单
- `ai_context/decisions.md`：新增决策（废弃 4 件套 + failure_modes 并入
  stage_snapshot full-state + identity 重定位 + maxItems 裁剪统一规则）
- `ai_context/data_model.md`（如有）：更新角色 canon 数据模型
- `ai_context/current_status.md`：状态变更说明
- `docs/architecture/extraction_workflow.md`：phase 1/2/3 产出更新
- `docs/requirements.md`：同步 character canon 描述

**完成标准**

- 4 件套 schema 文件删除，stage_snapshot.schema.json 加 failure_modes
- 至少一个现有 work 完成迁移：原 4 件套内容合入 S001 stage_snapshot；
  废弃文件保留在 .archive/
- phase 1/2 不再产出 4 件套（跑一次验证）
- phase 3 char_snapshot read list 不再含 4 件套 / manifest（跑 1-2 stage
  验证 stage_snapshot.failure_modes 字段产出正确 + 命中 maxItems 时
  裁剪生效）
- ai_context / docs 同步更新

**预估**

- 较大改动（schema 增删 + phase 1/2/3 prompt + 迁移脚本 + 多处
  ai_context / docs 更新）
- 实施 ~2-3 个工作日；首次跑 1-2 stage 验证 + 现有 work 迁移

**依赖**

- 无硬依赖
- T-CHAR-SNAPSHOT-PER-STAGE 已完成并归档（prompt 三态规则在
  character_snapshot_extraction.md 内，stage_delta 维持自由文本与
  本 todo 的拍板一致）
- 建议先于 T-CHAR-SNAPSHOT-SUB-LANES 执行（sub-lane 输入清单将在此
  todo 落地后简化）

**暂不做的事**

- 不改 simulation runtime 加载机制（runtime 尚未实装；本 todo 仅完成
  数据侧准备，加载机制随 [T-SIMULATION-MODE-MARKER] 实装时配套实施）
- 不改 character_arc 字段（其设计仍为累积型）
- 不改 stage_delta 结构（保留现行自由文本，避免一次改动撞两个 schema
  决策）
- 不动 char_support / world / 其他 phase

---

### [T-PHASE2-TARGET-BASELINE] phase 2 产出 per-character target_baseline，作为 phase 3 全模式的 target keys 锚点

**开始时间**：2026-04-29 20:54 EDT

**当前状态**：代码完成、runtime 验证待跑（schema / 代码 / prompt / docs 全部落地，jsonschema + import + validate_baseline 静态验证通过；下一步需在 extraction 分支跑一遍 phase 2 验证 LLM 实际产出 target_baseline.json schema 合规 + 与 BASELINE-DEPRECATE 同批跑 runtime）

**上下文**

当前 phase 3 char_snapshot 由 LLM 在 stage-local 视角自主决定
target_voice_map / target_behavior_map / relationships 的 keys。三个痛点：

1. stage-local 视角看不到全书关系网络，可能漏判跨章节的隐性重要关系
   （反派只前/后期出场但贯穿主线等）
2. 单 lane 模式下三方 keys 名义上由同一 LLM 写入应一致，实际是否真的
   对齐尚未 0 token 验证（被替代的 T-CHAR-SNAPSHOT-TARGET-LIST 决策项 2
   提的疑点）
3. T-CHAR-SNAPSHOT-SUB-LANES 拆 3 lane 后三方 keys 必须 == 同一基线才能
   合并（双向相等约束，三态由内容承载），否则需每 stage 额外算 active
   target list（原 step 0 LLM 调用，占串行卡口）

新方案：phase 2 全书视野一次性拍每角色 `target_baseline.json`，列全书所有
重要 target（含 tier + 关系类型），后续 phase 3 各 stage 严格 == baseline
写 keys。三方一致 by-construction，跟 identity / fixed_relationships 同源
思路（结构性 + 跨 stage 不变 → phase 2 一次拍，后续 stage 只读不写）。

**改动清单**

新增：
- `schemas/character/target_baseline.schema.json` — 字段：`schema_version`
  / `work_id` / `character_id` / `targets[]`，每条 target =
  `target_character_id`（用 identity.id，规避化名 / 隐藏身份歧义）+
  `relationship_type`（中文短词，柔性 string 非 enum；14 候选：至亲 /
  恋人 / 挚友 / 师长 / 弟子 / 朋友 / 同僚 / 主人 / 下属 / 宠物 / 武器 /
  对手 / 敌人 / 路人；候选无法准确描述时允许使用列表外更精确中文短词，
  需在 description 字段说明差异）+ `tier`（核心 / 重要 / 次要 / 普通）+
  `description`（≤100 字）；`targets` 数组容量上限通过
  `schemas/character/targets_cap.schema.json` $ref 共享继承（下游
  stage_snapshot 三 map 通过同一份 $ref 单源同步）

修改：
- `automation/prompt_templates/baseline_production.md` — 新增「产出 3：
  角色 Target Baseline」章节；manifest.json 段加 `target_baseline_path`
  填写指引
- `automation/persona_extraction/prompt_builder.py`
  `build_baseline_prompt` — schemas 读列表加
  `character/target_baseline.schema.json`
- `schemas/character/character_manifest.schema.json` — `paths` 对象加
  `target_baseline_path` 字段
- `automation/persona_extraction/validator.py` `validate_baseline()` —
  加 target_baseline.json 校验：必须存在 + schema 合规 + character_id
  与目录名一致；缺失 / 违规 → error
- `ai_context/decisions.md` #13 — 改写为含 target_baseline 产出 + D4 硬
  约束（phase 3 keys == baseline，违规 hard fail）+ baseline 在 phase 3
  全程只读不写
- `ai_context/architecture.md` § Automated Extraction Pipeline — Phase 2
  行补充 target_baseline 产出
- `ai_context/requirements.md` § §7 Information Layering — immutable 层
  补 target_baseline
- `docs/architecture/extraction_workflow.md` § 5 Baseline 产出（Phase 2）
  — 加 target_baseline 描述 + immutable 约束 + 出口验证补充
- `docs/requirements.md` § 角色层 baseline — 加 target_baseline 条目 +
  immutable 约束 + phase 2 宁可多列不可漏列原则

**完成标准**

- target_baseline.schema.json 落地 + jsonschema 校验通过 ✓ done
- character_manifest 含 target_baseline_path ✓ done
- validate_baseline() 把 target_baseline 列为必须文件，缺失 / 违规阻断
  phase 3 ✓ done（smoke 验证通过：missing → error / mismatch → error /
  schema 违规 → error）
- ai_context / docs 同步更新 ✓ done
- phase 2 跑通至少一个 work：每个 candidate character 产出
  target_baseline.json，schema 合规 ⏳ 待 runtime（与 BASELINE-DEPRECATE
  可同批跑）

**预估**

- 中量改动（新增 1 schema + phase 2 prompt 改造 + 几处 ai_context / docs
  更新）
- 代码实施已完成；首次跑 1 个 work 验证待用户在 extraction 分支触发

**依赖**

- T-BASELINE-DEPRECATE 已落地（runtime 验证通过后归档）
- 无其他硬依赖
- 是 T-CHAR-SNAPSHOT-SUB-LANES 的硬前置（sub-lane 三方 keys == baseline
  的锚点）

---

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

### [T-PHASE0-CHUNK-SCHEMA-EXPAND] chapter_summary_chunk schema 二级字段扩展（命中 world_overview / foundation 不可信字段）

**开始时间**：2026-05-04 14:50 EDT

**更新时间**：2026-05-04 14:50 EDT

**当前状态**：schema/prompt/ai_context/docs 完成 + 静态 gate 全过
（jsonschema metaschema OK；样本 chunk 1 个 valid + 10 个 negative case
全过，含 spurious sub-key / 缺 name|rule entry / observed_impact 兜底
字符串接受 / 删除的 location 复现拒绝 / summary < 100 与 > 150 双向拒绝
/ chunk_world_rules > 5 拒绝；orchestrator + validator import 通过；
全库 grep 无 chapter.location 残留代码）；runtime 验证待跑（与
T-BASELINE-DEPRECATE / T-PHASE2-TARGET-BASELINE / T-INGEST-STRUCTURE-MODE
同批跑——本 todo 完成后 baseline 不再被 chunk 信息密度限制，是 phase 2
runtime 验证质量改善的前置）

**上下文**

Phase 1 [world_overview.json](../schemas/analysis/world_overview.schema.json) 与 phase 2 [foundation.json](../schemas/world/foundation.schema.json) 多字段被 chunk schema 信息密度不足约束，实际质量分层：

- ✅ genre / tone / world_lines.{name,chapter_range} — chunk 字段直接可信
- 🟡 world_structure.summary / major_regions / world_lines.core_conflict — 半可信
- 🟠 power_system.summary / major_factions.description / world_lines.setting_features —
  chunk 信号稀疏，LLM 多按 genre 推断
- 🔴 power_system.levels / core_rules / core_rules.impact — chunk 完全无信息源，
  LLM 凭 genre 套常见模板（仙侠 → 练气筑基金丹元婴）

根因：旧 [chapter_summary_chunk.schema.json](../schemas/analysis/chapter_summary_chunk.schema.json)
只有 per-章字段，且 prompt 明令"事件描述而非文学评论"——所有"设定 / 体系 /
规则"信号被主动过滤。chunk-level 没有二级合成字段，phase 1 LLM 拿到的是
~22 chunks × 25 章扁平堆，无法挖出力量体系 / 世界规则细节。foundation 是
world_overview 的"结构化精化版"——信息源相同，可信度同分层。

**已落地（schema/prompt/ai_context/docs，2026-05-04）**

- schema：[`schemas/analysis/chapter_summary_chunk.schema.json`](../schemas/analysis/chapter_summary_chunk.schema.json)
  顶层加 5 chunk-level 二级字段（`chunk_arc_summary` ≤200 required；
  `chunk_world_rules` maxItems 5 × `{rule≤50, description≤50, observed_impact≤50}`、
  `chunk_power_levels` maxItems 20 × `{name≤15, description≤30}`、
  `chunk_factions` maxItems 20 × `{name≤15, description≤50, members_present ≤20×items≤10}`、
  `chunk_regions` maxItems 20 × `{name≤15, description≤30}`；items 全标
  `additionalProperties:false` + `required:[name|rule]`）；per-章删
  `location`、`summary` 50-100→100-150、保留 `key_events` ≤5×≤50 作为
  monolithic stage_plan 边界判定离散信号
- prompt：[`automation/prompt_templates/summarization.md`](../automation/prompt_templates/summarization.md)
  改 4 步骤结构（读章节 → per-summary → chunk-level → 写文件），
  `observed_impact` 强引导"宁可写未在本 chunk 直接观察也不要静默留空"，
  sub-field description "有解释必填 / 无解释写空字符串"明示；
  Phase 1 三 lane 模板（[analysis_world_overview.md](../automation/prompt_templates/analysis_world_overview.md)
  / [analysis_stage_plan.md](../automation/prompt_templates/analysis_stage_plan.md)
  / [analysis_candidate_characters.md](../automation/prompt_templates/analysis_candidate_characters.md)，
  决策 #52 拆出）各加 chunk-level 字段说明 + 字段 → world_overview 映射表，
  stage 边界信号源由 per-summary location 替换为 chunk_regions / chunk_arc_summary；
  [`automation/prompt_templates/baseline_production.md`](../automation/prompt_templates/baseline_production.md)
  产出 1 思考链重写——加 chunk-level → foundation 映射表 + "不要凭 genre
  套模板" / "core_rules.impact 是综合判断不是直接拷贝" 关键约束；fixed_relationships
  注脚加"chunk_factions.members_present 经 phase 1.5 身份合并后可作势力归属信号"
- ai_context：[`decisions.md`](../ai_context/decisions.md) 加 27m
  （chunk-level 二级字段决策 + 显式不加 chunk_fixed_relationships /
  chunk_setting_features 理由）；[`architecture.md`](../ai_context/architecture.md)
  Phase 0 段加 chunk-level 字段说明；[`conventions.md`](../ai_context/conventions.md)
  Cross-File Alignment 加 `chapter_summary_chunk.schema.json` → 三 prompt 同步行
- docs：[`docs/architecture/schema_reference.md`](architecture/schema_reference.md)
  chapter_summary_chunk 章节重写关键字段表 + 消费方映射；
  [`docs/architecture/extraction_workflow.md`](architecture/extraction_workflow.md)
  Phase 0 通用流程加 chunk-level 二级聚合字段说明
- smoke：jsonschema metaschema 校验通过；手写 sample chunk JSON 1 valid +
  10 negative case 全过；orchestrator + validator import 通过；
  grep 全库无 `chapter.location` / 旧 chunk 字段残留

**待跑（runtime 验证）**

- summarization.md 跑 1-2 chunk 验证 LLM 实际能正确填 chunk-level 字段，
  特别 `chunk_world_rules.observed_impact` 是真填具体事件还是 fallback
  写"未在本 chunk 直接观察"——两者都接受，但**不能静默留空**
- analysis_world_overview.md 跑 1 个 work 验证 world_overview 质量改善：
  power_system.levels 不再 LLM 套模板（应反映原文真实力量体系）；
  core_rules 不再空泛规则；world_structure.summary 虽仍 🟡 但应反映
  原文真实区域结构（不是仙侠默认拼装）
- baseline_production.md 跑 1 个 work 验证 foundation 改善：
  core_rules.impact 字段不再 LLM 编（应反映本作真实"对剧情/角色的
  影响"，源自 chunk_world_rules.observed_impact 的多 chunks 综合）

**暂不做的事**

- 不加 `chunk_fixed_relationships[]`——chunk-level 视野无法判定"贯穿
  全书"，会污染 phase 2 fixed_relationships.json + phase 3
  character_snapshot.relationships 的 fixed_relationship 例外。
  fixed_relationships 全书判定留 phase 2 baseline_production 全书视野
- 不加 `chunk_setting_features`——杂物收纳字段，与其他 4 chunk-level
  字段职责重叠；world_structure.summary / world_lines.setting_features
  让 phase 1 LLM 综合 4 个专门字段写出
- per-chapter `location` 不拆 `region` + `scene`（chunk_regions[] 已直接
  覆盖 region 维度，不必再 per-章细化）
- per-chapter `summary` 不扩到 200-300（保留 100-150；扩太长会鼓励 LLM
  把设定信息塞进 summary——chunk-level 字段才是设定信号正轨）
- per-chapter `key_events` 不删（≤5×≤50 字保留——phase 1 monolithic 模式
  stage_plan 边界判定靠它做离散事件信号）
- foundation.core_rules.impact 不要求"完全可信"——chunk_world_rules[].observed_impact
  是局部锚点（每 chunk 局部观察 / fallback "未观察"标注），phase 2 LLM
  综合多 chunks 判定"对剧情/角色的整体影响"仍需推断（从 🔴 升到 🟡，
  本 todo 不追求升到 ✅）
- 不单独加 chunk-level "key_figures of faction" 字段（已由
  chunk_factions[].members_present 间接覆盖）

---

### [T-ANALYSIS-SCHEMA-TIGHTEN] 收紧 phase 0 chunk + phase 1 candidate / world_overview schema 字段

**开始时间**：2026-05-08 10:26 EDT

**更新时间**：2026-05-08 11:06 EDT

**当前状态**：schema/prompt/code/ai_context/docs 完成 + 静态 gate 全过
（3 件 schema metaschema OK；正样本 + 多个 negative case 全过——chunk
拒 key_events / summary 长度双向边界、candidate 拒 first_appearance /
recommended、world_overview 拒 string major_regions/levels item +
core_rules > 30 + items > 150；orchestrator + prompt_builder + validator +
scene_archive import 通过；grep 全仓库无 key_events / first_appearance /
recommended 残留主动引用）；e2e 验证待跑（清掉现有 untracked
`works/<work_id>/` 后从 phase 0 全新跑——schema gate 不报红 + phase 0/1/
1.5/2 全过为标准）

**上下文**

2026-05-08 03:54-04:30 EDT 跑 work_id=`<work_id>` phase 0/1/1.5 + phase 2
部分（被 SIGTERM 中止）后，看到实际产物决定收紧三组 schema：

- chunk per-summary `key_events`：经 #52 lane 拆分后，三个 phase 1 lane
  都不投这字段（[prompt_builder.py:122,166](../automation/persona_extraction/prompt_builder.py)
  当前只在注释里提）+ Phase 2 baseline 也不读，是死字段；同时 `summary`
  100-150 字范围装不下事件 + 设定二者，需要扩到 150-200。
- candidate `recommended`：是 LLM 自报推荐意愿（拍脑袋打 boolean），不
  可靠；改为 phase 1.5 基于 `importance == 主角` 程序推荐（用户仍可手
  选追加）。
- candidate `aliases.first_appearance`：字符串描述（"约第 0042 章"），
  既不参与下游也不能用于程序检索，是冗余。
- world_overview `major_regions` / `power_system.levels`：当前是字符串
  数组，与 chunk_regions / chunk_power_levels 的 `{name, description}`
  对象形态不对齐，Phase 2 baseline 时需要再拼对象，是 churn。
- world_overview `core_rules`：maxItems 20 对应 N chunk × ≤5 条原始规则
  去重合并到 30 比较合理；同时 maxLength 100→150 强制 LLM 重新整理而
  不是照搬 chunk 行。

**改动清单**

1. [chapter_summary_chunk.schema.json](../schemas/analysis/chapter_summary_chunk.schema.json)
   — `summaries.items.required` 删 `key_events`；删 `properties.key_events`；
   `properties.summary.minLength` 100→150，`maxLength` 150→200；
   `characters_present.description` 改"化名 / 代称在 identity_notes 注明"
2. [candidate_characters.schema.json](../schemas/analysis/candidate_characters.schema.json)
   — `candidates.items.required` 删 `recommended`；删 `properties.recommended`；
   `aliases.items.required` 删 `first_appearance`；删
   `aliases.items.properties.first_appearance`；
   `importance.description` 加"Phase 1.5 默认勾选 = importance == 主角"
3. [world_overview.schema.json](../schemas/analysis/world_overview.schema.json)
   — `world_structure.major_regions.items` 由 string 改 `{name (≤15),
   description (≤30)}` 对象（对齐 `chunk_regions.items`）；
   `power_system.levels.items` 同上对齐 `chunk_power_levels.items`；
   `core_rules.maxItems` 20→30；`core_rules.items.maxLength` 100→150
   （保留字符串数组形态）
4. [summarization.md](../automation/prompt_templates/summarization.md)
   — 删 key_events 教学（per-章字段 + JSON 示例 + 规则段落 3 处）+ 把
   summary 长度教学从 100-150 改 150-200 + 教 LLM 把关键事件写进 summary
5. [analysis_world_overview.md](../automation/prompt_templates/analysis_world_overview.md)
   — 字段映射表：`major_regions` / `levels` 升对象 + `core_rules` 30 条
   字符串教学；JSON 示例同步
6. [analysis_stage_plan.md](../automation/prompt_templates/analysis_stage_plan.md)
   — per-summary 字段集 100-150 → 150-200；裁剪原则段落删 `key_events`
   提及（chunk schema 已删）
7. [analysis_candidate_characters.md](../automation/prompt_templates/analysis_candidate_characters.md)
   — 删 `aliases.first_appearance` / `recommended` 字段教学；改"不需要再
   判断是否建议建包" + JSON 示例同步
8. [prompt_builder.py:118-124,165-172](../automation/persona_extraction/prompt_builder.py)
   — module-level 注释 + `_project_chunk_for_stage_plan` docstring：
   key_events 描述改为"已从 chunk schema 删除（决策 #53）"；
   prompt_builder 自身 projector 本就不投 key_events 无代码改动
9. [orchestrator.py:1582-1612](../automation/persona_extraction/orchestrator.py)
   — `confirm_with_user` Phase 1.5：`RECOMMENDED` 标签从 `c.get("recommended")`
   改为 `c.get("importance") == "主角"`；新增 `recommended_ids` 程序计算
   + 默认勾选行 `(Press Enter to accept default, or type IDs to override)`
   + 空输入回退到 `recommended_ids`（preset_characters 路径不变）
10. [schema_reference.md](architecture/schema_reference.md)
    + [extraction_workflow.md](architecture/extraction_workflow.md)
    — chunk per-summary 字段表删 key_events / 改 summary 长度；
    candidate 关键字段表删 recommended + first_appearance；
    world_overview 关键字段表 major_regions / levels 形态升级 + core_rules
    bound；Phase 1.5 默认勾选规则化描述
11. [architecture.md](../ai_context/architecture.md) Phase 0 chunk 字段
    集 + Phase 1 lane 投影（删 key_events）+ Phase 1.5 默认规则化；
    [decisions.md](../ai_context/decisions.md) 修订 #27m（key_events 段删
    + summary 长度更新）+ 修订 #52（lane 投影 key_events 提及修订）+
    新增 #53（本次三组 schema 收紧 + Phase 1.5 推荐规则化总条目）

**完成标准**

- 三个 schema 文件改完，Draft202012 metaschema 校验通过 ✅
- 9 个下游文件文字 / 代码同步 ✅
- Phase 1.5 推荐逻辑改为基于规则（程序判定 `importance == "主角"`）✅
- grep 全仓库无 `key_events` / `first_appearance` / `recommended` 残留
  主动引用（除 logs / works / users / archived）✅
- 现有 `works/<work_id>/` 整 untracked 目录清掉，从 phase 0 全新跑 e2e
  验证 schema gate 不报红 → phase 0 + phase 1 + phase 1.5 + phase 2 全过
  ⏳（待跑）

**依赖**

无（schema 改动属 framework 层；不阻塞其他 In Progress 任务，可立即
启动）

**预估**

schema + prompt + ai_context + docs 改动 ~30 min（**已完成**）；e2e 重跑
phase 0（~1.5h wall）+ phase 1（~30min）+ phase 1.5 + phase 2（~10-20min）
≈ 2.5h（不含可能的 retry / debug）

---

## Next

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

### [T-CHAR-SNAPSHOT-SUB-LANES] character stage_snapshot 拆 3 sub-lane 并行抽取 + phase 3 全模式 target keys 约束

**更新时间**：2026-05-02 18:18 EDT

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

**target keys 约束（合并自原 T-PHASE3-TARGET-CONSTRAINT，对单 lane / 三
lane 模式均生效）**：每 sub-lane / 单 lane 主抽取读 phase 2 产出的
`target_baseline.json` 为锚点，prompt 内嵌三态规则让 LLM 自行判断本 stage
active 子集——

- a) baseline 列了但本 stage + prev 都未登场 → keys 不出现（空缺）
- b) 已登场 → 以 prev 的 target_voice_map / target_behavior_map /
  relationships 为基线，按本 stage 原文必要时增删 / 更新对应字段
- c) 曾登场但本 stage 未出现 → 直接继承 prev 内容，不动

stage_snapshot 三方 keys（target_voice_map / target_behavior_map /
relationships）必须 == baseline.targets[].target_character_id（D4 硬约束）；
违规由 consistency_checker 跨文件校验 hard fail，T3 用尽仍违规 → 错误
退出（不允许 stage 突破 baseline，即使 baseline 漏判也走人工编辑 baseline
+ stage 重抽）。

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

sub_lanes = false（fallback 模式，仍享 target keys 约束）：
  单 lane char_snapshot + file-level 2 lifecycle 标准流程；prompt 同样
  注入 target_baseline + 三态规则；产出仍走 keys == baseline 校验
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
  `{target_baseline}` 占位；prompt 头部按 lane_scope 注入"本次仅写以下
  字段"约束。新增「target keys 三态规则」段（D2 a/b/c）+「target keys
  必须 == baseline」硬约束段。**T-BASELINE-DEPRECATE 引入的「maxItems
  统一裁剪规则」段对所有 lane 全 inherits**（不按 lane_scope 过滤——该段
  是抽取期通用准则，与字段归属正交）。字段归属表移到代码（同一来源给
  sub-lane 调度 + merge 用，避免 prompt 与 merge 字段集合漂移），fallback
  模式 `lane_scope=ALL` 等价单 lane 但同样吃 baseline + 三态规则
- `automation/persona_extraction/orchestrator.py` — sub-lane 调度
  （新建独立 ThreadPoolExecutor 与 repair pool 共用同一 `RateLimitController`
  信号源，hard-stop 任一池都触发 `executor.shutdown(cancel_futures=True)`）
  + .partial 清理；分支 `if config.phase3.char_snapshot_sub_lanes` 包住三
  lane 路径，否则走单 lane（两种模式都注入 baseline + 三态 prompt）。
  调用点 `prompt_builder.build_char_snapshot_prompt(..., lane_scope=...,
  target_baseline_path=...)` 增 2 入参
- `automation/persona_extraction/prompt_builder.py` —
  `build_char_snapshot_prompt` 增 `lane_scope`（`ALL` / `char_expression`
  / `char_decision` / `char_cognition`）+ `target_baseline_path` 入参，
  context dict 注入 `{lane_scope}` / `{lane_field_whitelist}` /
  `{target_baseline}` 三键
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
  拆分 + target_baseline 锚点 + 三态规则 + keys == baseline 硬约束（对
  全 phase 3 模式生效）
- `automation/README.md` — Phase 3 说明 + toml 配置文档
- `ai_context/architecture.md` § Automated Extraction Pipeline — 一句话补充
- `ai_context/decisions.md` — 新增决策：sub-lane 拆分 + target keys ==
  baseline by-construction + 三态规则
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
- sub_lanes=false 跑通：单 lane 仍注入 baseline + 三态规则，三方 keys ==
  baseline 校验生效（与三 lane 模式同口径）
- 3 sub-lane partial 字段集合 ∪ 程序注入 == schema properties 全集（merge
  前置校验，覆盖 schema 所有 required + 非 required 字段，无漂移）
- failure_modes 4 子键按字段归属表互斥分布到 char_expression（tone_traps）/
  char_cognition（其余 3 子键）+ 全 4 子键覆盖（hard gate，缺一即 partial
  失败），merge 后字段完整
- stage_delta 6 子键按字段归属表互斥分布到 char_decision / char_cognition +
  全 6 子键覆盖（hard gate，缺一即 partial 失败）
- 三方 keys（target_voice_map / target_behavior_map / relationships）==
  baseline.targets[].target_character_id 双向相等（多/少都 cross-file
  hard fail；三态由内容是否填充承载，从未登场 entry 字段空）— 复用现有
  `repair_agent/checkers/targets_keys_eq_baseline.py`
- prompt 模板的 maxItems 统一裁剪规则段对所有 lane 全 inherits（不按
  lane_scope 过滤），三 lane 主抽取均按"最重要 / 最符合当前 stage 需要"
  先排序后截断
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

- 中量改动（新增 1 模块 + 修改 ~10 文件 + prompt 改造，含 phase 3 全模式
  target keys 约束改造）
- 实施 ~1.5 个工作日；首次跑 1 stage 验证 sub_lanes=true 与
  sub_lanes=false 两套行为 + keys == baseline 校验
- 排期基于 monolithic 底数；light_novel 模式排期与开关行为不再"按 mode
  重评"——保持单 toml bool + CLI 双向 flag，跑 light_novel 时由用户
  `--no-char-snapshot-sub-lanes` 切换（详见"暂不做的事"）

**依赖**

- **硬前置 1**：T-PHASE2-TARGET-BASELINE（baseline 是三方 keys 锚点；无
  baseline 则 D4 硬约束无依据可校验）
- **硬前置 2**：T-BASELINE-DEPRECATE（字段归属表把 `failure_modes` 4 子键
  分到 char_expression / char_cognition，依赖 failure_modes 已在
  `stage_snapshot.schema` 内——schema 已合并满足，但需 runtime 验证
  failure_modes 实际产出 + maxItems 裁剪生效后才动 sub-lane prompt；同时
  本 todo 改动清单要求 prompt "maxItems 统一裁剪规则段对所有 lane 全
  inherits"，依赖该规则段先在 BASELINE-DEPRECATE 落地）
- **启动门槛 = phase 2 + BASELINE-DEPRECATE 双方都跑过 runtime 验证**——
  在真书上验证 baseline 实际产出 shape + failure_modes 实际产出 + maxItems
  裁剪行为之前不要开 sub-lane prompt 改造，避免上游字段语义后续微调
  → sub-lane prompt 全部回炉
- 无其他硬依赖

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
