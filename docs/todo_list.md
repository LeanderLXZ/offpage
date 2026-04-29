# TODO List（待办任务清单）

---

## Index (auto-generated; do not hand-edit)

> 本段是三张子表的渲染缓存，由维护本文件的人（包括 Claude）在**每次对正文条目增 / 改 / 移段 / 完成 / 废弃后**顺手刷新——具体规则见下方"## File guide → Index maintenance"。`/todo` skill 不解析正文，只读这一段，所以这里的内容必须与正文同步；不同步会让 `/todo` 给出错误结论。

### 🟢 In Progress (0)

| ID | Title | Start time | Status |
|---|---|---|---|
| _(none)_ | | | |

### 🟡 Next (5)

| ID | Brief | Importance | Ready | Scope | Deps |
|---|---|---|---|---|---|
| `T-PHASE35-IMPORTANCE-AWARE` | [consistency_checker.py:96-117](../automation/persona_extraction/consistency_checker.py#L96-L117) 已构造 importance_map 但只 _check_target_map_counts 用上；其他 8 个 _check_* 一刀切，对次要配角的 field_completeness / relationship_continuity 过度报错。decisions.md #15 已定 bound 因 importance 而异。 | 🟢 Med-Low | 💬 Discuss first | 🟡 Medium | 无（触发自 2026-04-27 opus-4-7 review L-3） |
| `T-PLUGIN-README` | 2026-04-28 把 skills 项目专属内容抽到 `ai_context/skills_config.md`，但新项目装 plugin 时不知道每节怎么填 / 缺失行为 / 模板。需写 `.agents/skills/README.md` 作为 setup 单一入口。 | 🟢 Med-Low | ✅ Ready | 🟢 Small | 无 |
| `T-CHAR-SNAPSHOT-SUB-LANES` | character stage_snapshot 拆 3 sub-lane（char_expression / char_decision / char_cognition）并行抽取 + 程序合并 + repair lifecycle（rate-limit / 掉线兼容 R1/R2/R3）；schema / world / char_support / 其他 phase 不动；toml `[phase3].char_snapshot_sub_lanes`（默认 true）+ CLI 双向 flag；fallback `--no-char-snapshot-sub-lanes` 等价现行单 lane；prompt 共用单文件 + lane_scope 占位 | 🟢 High | ✅ Ready | 🟡 Medium | 无（target list 策略另议，program-only 占位起步） |
| `T-BASELINE-DEPRECATE` | 废弃 4 件套：voice_rules / behavior_rules / boundaries / failure_modes（内容并入 stage_snapshot 演变链）；identity 重定位为 character-level 恒定 + 模拟时加载；manifest 从 char_snapshot read list 移除；stage_snapshot 加 failure_modes 字段（每 stage 全量、原 schema 上下限照搬）；prompt 加 maxItems-aware 裁剪规则。simulation runtime 未实装是改动最便宜窗口。 | 🔴 High | ✅ Ready | 🔴 Large·Arch | 与 T-CHAR-SNAPSHOT-PER-STAGE 部分解耦（仅 prompt 文件改动重叠）；建议先于 T-CHAR-SNAPSHOT-SUB-LANES |
| `T-CHAR-SNAPSHOT-PER-STAGE` | 废弃 baseline 后 stage_snapshot 成唯一权威，prompt 加 prev_stage 四态规则（A 继承 / B 重写 / C 无变化 / D 删除）+ per-stage 推演原则；stage_delta 升级为结构化字段（changed/removed/added），schema 同步改动。3 子段 vs 4 子段未定。 | 🟢 Med-Low | 💬 Discuss first | 🟡 Medium | 与 T-BASELINE-DEPRECATE 配套（schema 同步改动）；建议合并 commit |

### ⚪ Discussing (7)

| ID | Brief | Open decisions | Blocked by |
|---|---|---|---|
| `T-REPAIR-EVENT-DRIVEN` | E2 方案：每 lane 完成立刻触发 repair，与后续 lane extract 重叠。2026-04-22 测算只比 E1 省 4min/stage（49 stage 共 ~3h），双线程池 + peak 9 并发撞 rate limit 复杂度跳一档，暂不做。等 E1 真实耗时数据出来再重评。 | 0 | T-REPAIR-PARALLEL 先落地 |
| `T-CODEX-STDIN` | ClaudeBackend 已改 stdin 临时文件绕过 argv 128KiB 上限；CodexBackend.run 仍走 positional argv，切 `--backend codex` 时大 prompt 会复现 Argument list too long。已加注释未改代码——本机无 codex CLI 实测。 | 2 | 有 codex CLI 的机器 / 订阅 |
| `T-SIMULATION-MODE-MARKER` | CLAUDE.md / AGENTS.md 已预留 `[simulation_runtime_mode]` worker-mode short-circuit；extraction 侧已注入 `[extraction_worker_mode]`，simulation 侧零 Python 尚无注入点。 | 2 | simulation runtime 首次实装 |
| `T-PHASE5-RETRIEVAL` | 多处 canonical docs 宣称 `works/*/indexes/` 是 committed 产物（current_status / decisions / data_model / system_overview 都在说），但目前没有 Phase 承担生成职责。计划新增 Phase 5 统一承接 vocab_dict / 关键词 / FTS5 / RAG 等。 | 5 | Phase 3 全量完成 + retrieval 层设计定稿 |
| `T-RETRY` | T-LOG 已能解析 subtype / num_turns / cost，但 retry 决策本身还没用上 subtype 分流；短时阈值仍 5s（[config.toml:130](../automation/config.toml#L130)）偏小，char_snapshot 正常 10-20m，<60s 失败几乎一定是 launch / 连接错。需扩大阈值到 60s（候选 120s）+ 长时 exit 按 subtype 分流。 | 2 | 无（T-LOG 已完成） |
| `T-USER-AUX-SCHEMAS` | users/ 下若干辅助文件无 schema 绑定（session_index.json / archive_refs.json），2026-04-20 codex audit R3 指出 runtime 真正落地前最容易继续漂移。 | 2 | simulation runtime loader 选型 / 设计定稿 |
| `T-CHAR-SNAPSHOT-TARGET-LIST` | target_char_list 生成策略（program / llm-light / hybrid，主方案先 program-only 占位）+ fallback 模式（`--no-char-snapshot-sub-lanes`）下单 lane 是否真能保证三方 target 一致；先 0 token 验证 S001/S002 历史输出 | 3 | 0 token 验证可立刻；策略调整待主方案跑通 1–2 stage |

**Total**: 12 — 🟢 In Progress 0 ｜ 🟡 Next 5 ｜ ⚪ Discussing 7

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

**添加任务**：放进合适的分节（Next / Discussing）。新任务必须有上方"What to record"列出的字段。**不要直接添加到"In Progress"**——那个段位仅由 `/go` 启动动作填入。

**任务进入执行（/go 启动）**：
1. 把整条从 "Next" 移到 "In Progress"
2. 在条目里追加 `**开始时间**`（YYYY-MM-DD HH:MM 时区缩写——按 skills_config.md `## Timezone`）和 `**当前状态**`（进行中 / 等用户决策 / 暂停）字段
3. **In Progress 段位单槽**——若已有占用，先把当前那条 commit 完成或显式暂停回退到 "Next" 再启动新任务
4. 同步刷新索引段（见 "Index maintenance"）

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
- 修改现有条目的：标题、上下文摘要、依赖、待决策项、改动清单文件数、是否触及 schema / 架构 / 多 phase
- 任务移段：Discussing → Next、Next → In Progress、In Progress → archived、任意 → archived（abandoned）
- 任务在 "In Progress" 段内的"当前状态"变化（进行中 / 等用户决策 / 暂停）

**三张子表的列定义**：

**In Progress**

| 列 | 取值 |
|---|---|
| ID | 反引号包裹的 T-XXX slug |
| Title | 方括号后的中文短语 |
| Start time | 条目里的 `**开始时间**` 字段，YYYY-MM-DD HH:MM 时区缩写 |
| Status | 条目里的 `**当前状态**` 字段：进行中 / 等用户决策 / 暂停 |

**Next**

| 列 | 取值 |
|---|---|
| ID | 反引号包裹的 T-XXX slug |
| Brief | 上下文段首句 + 1-2 句关键背景，**总长 ≤ 150 字**；去掉 markdown 链接的反引号让表格不破，但保留 `[text](url)` 形式 |
| Importance | 🔴 High / 🟢 Med-Low / 🟡 Medium（推断规则见下） |
| Ready | ✅ Ready / 💬 Discuss first / ⏸ Blocked（推断规则见下） |
| Scope | 🟢 Small / 🟡 Medium / 🔴 Large·Arch / —（推断规则见下） |
| Deps | 条目"**依赖**"段首句 |

**Discussing**

| 列 | 取值 |
|---|---|
| ID | 反引号包裹的 T-XXX slug |
| Brief | 同上，≤ 150 字 |
| Open decisions | 数 `**待决策项**` 段下的列表条目数；缺该段 → 0 |
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

_(empty — `/go` will move an entry here from "Next" when starting. Single slot.)_

---

## Next

### [T-PHASE35-IMPORTANCE-AWARE] Phase 3.5 一致性检查按 importance 调门槛

**上下文**

[automation/persona_extraction/consistency_checker.py:96-117](../automation/persona_extraction/consistency_checker.py#L96-L117) 读 `candidate_characters.json` 构造 `importance_map`，但当前只 `_check_target_map_counts` 消费它。其他 8 个 `_check_*`（含 `_check_field_completeness` / `_check_relationship_continuity` 等）对所有角色一刀切。

`ai_context/decisions.md` #15 明确 "main / important chars (≥3–5 examples); generic types brief or omitted"——bound 本就因 importance 而异。一致性检查不区分 importance，会对次要配角过度报错（field_completeness 把可选字段也按主角标准查）或对主角过宽。

**改动清单**

1. [automation/persona_extraction/consistency_checker.py:271](../automation/persona_extraction/consistency_checker.py#L271) `_check_field_completeness` 签名加 `importance_map: dict[str, str]`；调用点 [consistency_checker.py:111](../automation/persona_extraction/consistency_checker.py#L111) 透传
2. 内部按 importance（主角 / 重要配角 / 次要配角）调整必填字段集合或严重度（次要配角 → warning，主角 / 重要配角 → error）
3. 视情况对 `_check_relationship_continuity` 也做同样处理（次要配角的关系不连续可能是合理的低存在感）
4. 不动 `_check_alias_consistency` / `_check_memory_id_correspondence` 等（这些都是格式正确性，与重要度无关）

**待决策项**

1. 次要配角的 missing field 走 warning 还是直接跳过？
2. 是否扩展到 `_check_relationship_continuity`？

**完成标准**

- `_check_field_completeness` 对次要配角不再产生过激 error
- consistency_report 在多重要度场景下符合预期
- 本 todo 条目移到 archived

**预估**：S（30 分钟 - 1 小时）

**依赖**：无；触发自 2026-04-27 opus-4-7 review L-3 finding。

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

### [T-CHAR-SNAPSHOT-SUB-LANES] character stage_snapshot 拆 3 sub-lane 并行抽取

**上下文**

Phase 3 单 stage 的 char_snapshot lane 是当前 wall-time 最长的瓶颈
（粗估 T，49 stage 累加显著）。讨论后定方案：把单个 char_snapshot lane
拆成 3 个并行 sub-lane（按字段聚类），每 sub-lane 输入完整源材料 +
上阶段 snapshot + character baseline 全套（identity / voice_rules /
behavior_rules / boundaries / failure_modes / manifest）+ 程序预算的
active target 列表（**不**包含上阶段 memory_timeline——状态聚合不需要
事件流水）；3 份 partial JSON 由程序合并成完整 stage_snapshot.json，
再走 repair_agent 整文件 repair（最多 2 life-cycle，T3 触发时改为
3 sub-lane 并行重抽 → re-merge → re-validate）。schema 不动、世界 lane
和 char_support lane 不动、其他 phase 不动。

**字段归属表**

| sub-lane | 字段 |
|---|---|
| `char_expression` | `voice_state` / `active_aliases` / `current_mood` |
| `char_decision` | `behavior_state` / `boundary_state` / `emotional_baseline` / `current_personality` / `current_status` |
| `char_cognition` | `knowledge_scope` / `misunderstandings` / `concealments` / `relationships` / `stage_events` / `stage_delta` / `character_arc` / `snapshot_summary` |
| 程序注入 | `character_id` / `stage_id` / `timeline_anchor` / `chapter_scope` / `extracted_at` |

**流程**

```
sub_lanes = true:
  Step 0: 程序生成 target_char_list → .partial/{stage_id}_target_char_list.json
  Step 1: 3 sub-lane 并行 extract → .partial/{stage_id}_{lane}.json
  Step 2: 程序 merge → canon/stage_snapshots/{stage_id}.json，
          清理 lane partial（保留 target_char_list partial 给 T3 复用）
  Step 3: repair_agent（最多 2 life-cycle）；T3 触发 → 3 sub-lane 并行重抽 →
          re-merge → re-validate；target_char_list 复用 step 0 产物，
          每 sub-lane prompt 注入修复历史 + 错误信息
  Step 4: 清理 target_char_list partial

sub_lanes = false（fallback 到现行行为）：
  跳过 Step 0 / 2 / sub-lane T3；走单 lane char_snapshot + 单调用 T3
```

**改动清单**

新增：
- `automation/persona_extraction/target_char_list.py` — Step 0 实现，
  函数签名 `compute_target_char_list(stage_id, work_id, character_id) -> list[str]`；
  策略待 T-CHAR-SNAPSHOT-TARGET-LIST 决议，先放 program-only 占位
  （扫上阶段 snapshot.target_voice_map keys + memory_timeline character mention）；
  上限直接读 `schemas/character/stage_snapshot.schema.json` 的
  `target_voice_map.maxItems`（bounds-only-in-schema）
- `automation/persona_extraction/snapshot_merge.py`（或并入 `post_processing.py`）
  — Step 2 merge：按字段归属表拼接 + 校验 target 三方一致 / 字段不重叠
  / 必填齐 / 注入结构性字段

修改：
- `automation/prompt_templates/character_snapshot_extraction.md` — **保留
  单一文件（不拆 3 份）**。加 `{lane_scope}` 占位（取值 `ALL` /
  `char_expression` / `char_decision` / `char_cognition`）+
  `{target_char_list}` 占位；prompt 头部按 lane_scope 注入"本次仅写以下
  字段"约束。字段归属表移到代码（同一来源给 sub-lane 调度 + merge 用，
  避免 prompt 与 merge 字段集合漂移），fallback 模式 `lane_scope=ALL`
  等价现行单 lane
- `automation/persona_extraction/orchestrator.py` — sub-lane 调度
  + hard-stop 时 `executor.shutdown(cancel_futures=True)` + .partial 清理；
  分支 `if config.phase3.char_snapshot_sub_lanes` 包住 Step 0/2/T3-sub-lane 路径，
  否则走现行单 lane
- `automation/persona_extraction/repair_agent/` T3 dispatcher — sub-lane 开启
  时改为 3 并行重抽 + 注入修复历史 + 错误信息；T3 内 rate-limit pause
  重跑**不**消耗 `t3_max_per_file` 槽
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
  拆分 + 流程图
- `automation/README.md` — Phase 3 说明 + toml 配置文档
- `ai_context/architecture.md` § Automated Extraction Pipeline — 一句话补充
- `ai_context/decisions.md` — 新增决策：sub-lane 拆分 + target_char_list 复用
- `docs/requirements.md` §11 — 同步描述

**rate-limit / 掉线兼容（推荐方案）**

- 每 sub-lane 调用走 `run_with_retry`，自然继承现行 `RateLimitController`
  pause / resume 机制（决策 46）
- 显式处理 3 点：
  - **R1 T3 内 rate-limit 不消耗 t3 槽**：t3 计数器只在「LLM 真正成功
    调用且产出仍失败」时 +1，rate-limit pause 重跑不计数
  - **R2 hard-stop 时 cancel 同胞 sub-lane**：A 抛 `RateLimitHardStop`
    → orchestrator catch → `executor.shutdown(cancel_futures=True)` +
    删除已写 .partial → exit 2
  - **R3 .partial 残留清理**：disk reconcile 启动时扫 .partial，PENDING/ERROR
    lane 的 partial 一律删（不尝试复用），整 lane 重跑

**完成标准**

- toml `[phase3].char_snapshot_sub_lanes = true` + CLI 双向 flag 生效
- sub_lanes=true 跑通：Step 0/1/2/3/4 完整，merge 后 schema 校验通过
- sub_lanes=false 跑通：行为跟现行单 lane 完全等价（回归测试）
- 3 sub-lane partial 字段集合互斥 + 全覆盖 schema required（merge 函数兜底校验）
- target_char_list 三方一致（A.target_voice_map keys ==
  B.target_behavior_map keys ⊆ C.relationships keys，merge 时校验）
- T3 触发时 3 sub-lane 并行重抽 + 注入修复历史，re-merge 后 re-validate
- rate-limit 兼容：R1/R2/R3 在测试场景下行为符合上述描述
- disk reconcile 启动时正确清理孤儿 .partial
- 文档（architecture / extraction_workflow / README / ai_context / requirements）同步

**预估**

- 中量改动（新增 2 模块 + 修改 ~10 文件 + 拆 1 prompt）
- 实施 ~1–2 个工作日；首次跑 1 stage 验证 + 对比单 lane 输出质量

**依赖**

- 无硬依赖。target_char_list 实现策略可先用 program-only 占位，由
  T-CHAR-SNAPSHOT-TARGET-LIST 后续决议替换
- 跟 T-CHAR-SNAPSHOT-TARGET-LIST 并行讨论：fallback 模式是否也跑 step 0
- **建议先执行 T-BASELINE-DEPRECATE**：若先做废弃，sub-lane 输入清单
  自动简化为 `identity + 上阶段 snapshot + 章节 + target_char_list`
  （三件套已删 / manifest 已移除 / failure_modes 是 character-level
  不进 prompt）；若后做，sub-lane 实现需按本任务上下文段的 6 件套读取

**暂不做的事**

- 不拆分 sub-lane 输入（每 sub-lane 仍拿完整源 + 上阶段 snapshot，
  token 总量约 ×3，订阅模式可承受）
- 不拆 schema（character / stage_snapshot 结构不动）
- 不动 world lane / char_support lane / 其他 phase
- 当前 work package 切到新模型的时序问题不在本任务内（按用户原则
  「不过度工程，整 lane 重跑」处理）

---

### [T-BASELINE-DEPRECATE] 废弃 voice_rules / behavior_rules / boundaries / failure_modes 4 件套，identity 重定位为模拟时加载

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
- 与 T-CHAR-SNAPSHOT-PER-STAGE 部分解耦：本 todo 不再触动 stage_delta
  结构；PER-STAGE 仅在 character_snapshot_extraction.md prompt 文件上
  有改动重叠，可选择合并 commit 或分开
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

### [T-CHAR-SNAPSHOT-PER-STAGE] character_snapshot prompt 强化 per-stage 真实性 + prev_stage 四态使用规则 + stage_delta 结构化

**上下文**

终极目标是 stage_snapshot 反映**本阶段实际状态**，而不是笼统的"全阶段
概括"。但现行 [character_snapshot_extraction.md](../automation/prompt_templates/character_snapshot_extraction.md)
只有 stage_events 强制 per-stage（第 67 行明文"仅本阶段"）；voice_state /
behavior_state / boundary_state / target_voice_map / target_behavior_map /
relationships / knowledge_scope 的 per-stage 性靠隐含语义，无显式约束。
prev_stage 使用规则只覆盖 (A)「未出场原样继承」（第 75 行），缺
(B)「出场且变化」、(C)「出场且无变化」、(D)「主动删除 / 裁剪」三种
情况的处理叙述。后果：LLM 处理 target / emotion / relationship 在
阶段间变化的场景时无显式指引，默认偷懒整体继承；stage_delta 容易被
写成"无明显变化"敷衍过 schema。character_arc 是累积型设计（第 69 行
"从阶段 1 到当前阶段的整体弧线"），不在 per-stage 化范围。

T-BASELINE-DEPRECATE 一旦落地，stage_snapshot 成为角色状态的**唯一
权威**——演变链必须可审计：不能无效叠加（每 stage 把 prev 整体 copy
+ 加几条），也不能静默删除（重要 target 长期未出场被误判删除），还要
可追溯（裁剪了什么、为什么）。stage_delta 从描述性自由文本升级为
结构化字段，是配套 schema 改动。

**改动清单**

- `automation/prompt_templates/character_snapshot_extraction.md` 在
  「核心规则」加新条目：

  ```
  X. **prev_stage_snapshot 四态使用规则**：

     (A) 本阶段未出场（target / 角色 / emotion）→ **原样继承** prev 条目
        （现行第 75 行规则保留）；不允许"长期未出场所以删除"
     (B) 本阶段出场且状态有变化 → 以本阶段原文为准**重写**该条目；prev
        仅作对照；变化点列入 stage_delta.changed
     (C) 本阶段出场且状态无变化 → 保留 prev 内容；未在 stage_delta 中
        显式列出的字段视为 unchanged（无需逐项列举）
     (D) 主动删除 / 裁剪 → 在 stage_delta.removed 写明：哪条、为什么删
        （仅当：① 该项已在原文 / 前阶段被显式 resolved/revealed；
                ② schema maxItems 触发硬裁剪——按现行第 64 行裁剪策略）

  Y. **per-stage 推演原则**：除 character_arc（累积型）和 (A) 类继承外，
     所有字段值必须基于本阶段原文 + prev_snapshot **推演得出**，不可
     静默照搬 prev_snapshot；schema 通过不等于推演到位。
  ```

- `schemas/character/stage_snapshot.schema.json` stage_delta 字段从
  描述性字符串升级为结构化对象：
  ```
  stage_delta: {
    changed: array<{ field, prev, current, reason }>  // (B) 类
    removed: array<{ field, item, reason }>           // (D) 类
    added:   array<{ field, item }>                   // 新增项
  }
  ```
- `character_snapshot_extraction.md` 第 68 行 stage_delta 字段说明
  同步更新为结构化版本

**待决策项**

- stage_delta 是否需要 unchanged 子段（4 子段方案）：
  - **选项 1（推荐）**：3 子段（changed / removed / added），未列入字段
    默认 unchanged；增量小、LLM 推断负担轻；缺点是依赖 LLM 自觉对照
  - 选项 2：4 子段（+ unchanged audit 文字段），强制 LLM 在前三段全空
    时写一段"对照了哪些字段"叙述；审计强、增量略涨

**完成标准**

- prompt 四态规则（A/B/C/D）+ per-stage 推演原则
- stage_snapshot.schema.json stage_delta 字段结构化（待决策项定后
  定最终子段数）
- 跑 1-2 stage 后人工抽查：
  - stage_delta.changed / removed / added 不出现"无明显变化"敷衍
  - target / emotion / relationship 在阶段间的演变能在 stage_delta
    被明确捕捉

**依赖**

- 与 T-BASELINE-DEPRECATE 配套（同一次 schema 改动 / prompt 修订）；
  建议合并 commit
- 与 T-CHAR-SNAPSHOT-SUB-LANES 共同 prompt 头部，无冲突

**暂不做的事**

- 不改 character_arc（其设计就是累积型，不该 per-stage 化）
- 不动 char_support / world / 其他 phase

---

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

### [T-CHAR-SNAPSHOT-TARGET-LIST] target_char_list 生成策略 + fallback 模式是否需要

**上下文**

T-CHAR-SNAPSHOT-SUB-LANES 主方案的 Step 0 由
`compute_target_char_list()` 扫源 + 上阶段产物，输出本阶段 active
target 列表，注入 3 sub-lane prompt 强约束三方一致（A.target_voice_map
/ B.target_behavior_map / C.relationships keys 对齐）。函数签名定下来
即可解锁主方案，但**生成策略**和 **fallback 模式行为**两个具体问题
需要决议。

**待决策项 1：生成策略**

1.1 选用哪个？
   - **A. program-only（0 token）**：上阶段 snapshot.target_voice_map
     keys ∪ 本阶段 memory_timeline 中（jieba + candidate_characters
     角色清单）匹配出的 character mention，按出现频次排序取 top N
   - **B. llm-light（~5% sub-lane token）**：精简 prompt = candidate_characters
     角色清单 + 本阶段 memory_timeline 全文 + 上阶段 active target
     列表，让 LLM 输出 active target 列表 JSON 数组。优点：识别化名 /
     别号 / 第三方称呼
   - **C. hybrid**：先 A 跑，结果若覆盖率不足（如低于上阶段一半 target
     数）降级到 B
1.2 默认起步用哪个？（推荐 program-only，留 hybrid 作未来升级路径）
1.3 策略不做成 toml 配置项（用户已明确去掉 `target_budget_strategy`
   字段）；代码硬选一个，未来切换直接换函数体不动调用方

**待决策项 2：fallback 模式（`--no-char-snapshot-sub-lanes`）是否也需要 target_char_list**

2.1 单 lane 模式下，LLM 在同一 context 内同时写 voice_map / behavior_map
   / relationships，**理论上** target 集合天然对齐。但**实际是否真的
   一致**需验证：抓 S001 / S002 的历史输出，0 token 比对三方 target keys
   - 验证命令：
     `jq '.voice_state.target_voice_map | keys' / '.behavior_state.target_behavior_map | keys' / '.relationships[] | .target'`
2.2 若验证发现单 lane 也存在不一致：
   - 选项 X：fallback 模式额外跑 Step 0 + 注入 prompt
   - 选项 Y：在 prompt 头加一段「以上阶段 snapshot 的 target_voice_map
     keys 为基准」的 0-token 约束（无需新模块）
2.3 若验证发现单 lane 一致性 OK：
   - 保留当前推荐（`--no-char-snapshot-sub-lanes` 完全等价于现行行为，
     跳过 Step 0）

**完成标准**

- 决策项 1：选定一个生成策略，落到 `target_char_list.py` 的实现
- 决策项 2：先做 0 token 验证（S001 / S002 历史输出），据此决定 fallback
  模式行为
- 主方案 T-CHAR-SNAPSHOT-SUB-LANES 跑通 1–2 stage 后，对比目标列表
  vs 实际 LLM 写入的 target 集合，验证策略覆盖率 ≥ 95%
- 两个决议均追加到 `ai_context/decisions.md`

**依赖**

- 决策项 1 不阻塞 T-CHAR-SNAPSHOT-SUB-LANES（主方案先用 program-only
  占位起步）
- 决策项 2 的 0 token 验证可立刻做（S001 / S002 已 commit）；结论会
  反向影响主方案的 fallback 分支实现，但不阻塞主路径（sub_lanes=true）
- 实际策略调整可参考主方案首次跑通后的 1–2 stage 输出

---
