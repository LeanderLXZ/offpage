# TODO List（待办任务清单）

---

## Index (auto-generated; do not hand-edit)

> 本段是三张子表的渲染缓存，由维护本文件的人（包括 Claude）在**每次对正文条目增 / 改 / 移段 / 完成 / 废弃后**顺手刷新——具体规则见下方"## File guide → Index maintenance"。`/todo` skill 不解析正文，只读这一段，所以这里的内容必须与正文同步；不同步会让 `/todo` 给出错误结论。

### 🟢 In Progress (0)

| ID | Title | Start time | Status |
|---|---|---|---|
| _(none)_ | | | |

### 🟡 Next (4)

| ID | Brief | Importance | Ready | Scope | Deps |
|---|---|---|---|---|---|
| `T-PHASE35-IMPORTANCE-AWARE` | [consistency_checker.py:96-117](../automation/persona_extraction/consistency_checker.py#L96-L117) 已构造 importance_map 但只 _check_target_map_counts 用上；其他 8 个 _check_* 一刀切，对次要配角的 field_completeness / relationship_continuity 过度报错。decisions.md #15 已定 bound 因 importance 而异。 | 🟢 Med-Low | 💬 Discuss first | 🟡 Medium | 无（触发自 2026-04-27 opus-4-7 review L-3） |
| `T-REPAIR-T3-LIFECYCLE-RESET` | T3 触发后开新 repair lifecycle，单文件最多 2 个 lifecycle。第一轮 T3 prompt 带 prior_attempt_context（已修+未修摘要 ~200 token），跑完直接进第二轮（不做 Post-T3 check / 不走第一轮 L3 gate）。第二轮全新 Phase A→B→C，禁用 T3，升 T3 即 T3_EXHAUSTED。Triage 两轮独立 cap=5。 | 🔴 High | ✅ Ready | 🟡 Medium | 无 |
| `T-CHAR-SNAPSHOT-T3-REGEN-PATH` | char_snapshot T3 重生成走 3 sub-lane 并行 + 程序汇总（β 路径），保持「单一生成路径」原则。T-REPAIR-T3-LIFECYCLE-RESET 已定型 → T3 单文件最多 1 次 → β 的 token 成本上限 = ×3，可接受。 | 🟡 Medium | 💬 Discuss first | 🟡 Medium | char_snapshot 3 sub-lane 并行方案本身要先落地（未单独立条） |
| `T-PLUGIN-README` | 2026-04-28 把 skills 项目专属内容抽到 `ai_context/skills_config.md`，但新项目装 plugin 时不知道每节怎么填 / 缺失行为 / 模板。需写 `.agents/skills/README.md` 作为 setup 单一入口。 | 🟢 Med-Low | ✅ Ready | 🟢 Small | 无 |

### ⚪ Discussing (6)

| ID | Brief | Open decisions | Blocked by |
|---|---|---|---|
| `T-REPAIR-EVENT-DRIVEN` | E2 方案：每 lane 完成立刻触发 repair，与后续 lane extract 重叠。2026-04-22 测算只比 E1 省 4min/stage（49 stage 共 ~3h），双线程池 + peak 9 并发撞 rate limit 复杂度跳一档，暂不做。等 E1 真实耗时数据出来再重评。 | 0 | T-REPAIR-PARALLEL 先落地 |
| `T-CODEX-STDIN` | ClaudeBackend 已改 stdin 临时文件绕过 argv 128KiB 上限；CodexBackend.run 仍走 positional argv，切 `--backend codex` 时大 prompt 会复现 Argument list too long。已加注释未改代码——本机无 codex CLI 实测。 | 2 | 有 codex CLI 的机器 / 订阅 |
| `T-SIMULATION-MODE-MARKER` | CLAUDE.md / AGENTS.md 已预留 `[simulation_runtime_mode]` worker-mode short-circuit；extraction 侧已注入 `[extraction_worker_mode]`，simulation 侧零 Python 尚无注入点。 | 2 | simulation runtime 首次实装 |
| `T-PHASE5-RETRIEVAL` | 多处 canonical docs 宣称 `works/*/indexes/` 是 committed 产物（current_status / decisions / data_model / system_overview 都在说），但目前没有 Phase 承担生成职责。计划新增 Phase 5 统一承接 vocab_dict / 关键词 / FTS5 / RAG 等。 | 5 | Phase 3 全量完成 + retrieval 层设计定稿 |
| `T-RETRY` | T-LOG 已能解析 subtype / num_turns / cost，但 retry 决策本身还没用上 subtype 分流；短时阈值仍 5s（[config.toml:130](../automation/config.toml#L130)）偏小，char_snapshot 正常 10-20m，<60s 失败几乎一定是 launch / 连接错。需扩大阈值到 60s（候选 120s）+ 长时 exit 按 subtype 分流。 | 2 | 无（T-LOG 已完成） |
| `T-USER-AUX-SCHEMAS` | users/ 下若干辅助文件无 schema 绑定（session_index.json / archive_refs.json），2026-04-20 codex audit R3 指出 runtime 真正落地前最容易继续漂移。 | 2 | simulation runtime loader 选型 / 设计定稿 |

**Total**: 10 — 🟢 In Progress 0 ｜ 🟡 Next 4 ｜ ⚪ Discussing 6

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

### [T-REPAIR-T3-LIFECYCLE-RESET] T3 触发后开新 repair lifecycle，单文件最多 2 个 lifecycle

**上下文**

现状（[ai_context/decisions.md](../ai_context/decisions.md) #25 / #25a +
[automation/repair_agent/coordinator.py](../automation/repair_agent/coordinator.py)）：
repair_agent 内 `t3_max_per_file=1`；T3 完成后只跑 Post-T3 scoped L0–L2
门禁，不通过判 `T3_CORRUPTED` 终止；**没有「T3 后重跑完整 lifecycle」
的机会**。

期望语义：

- 一个文件最多走 **2 个完整 lifecycle**
- 第一轮 lifecycle：T0/T1/T2 跑完仍残留 → 触发 T3。**T3 prompt 带
  `prior_attempt_context`**（含本轮 T0–T2 已修 + 未修两类 issue 摘要，
  ~200 token），LLM 整文件重生成。T3 跑完后**不做 Post-T3 scoped
  check**，**不走第一轮 L3 gate / Phase C**，状态机完整重置 → 进入
  第二轮
- 第二轮 lifecycle：全新一轮 Phase A→B→C，**禁用 T3**。Phase A 重扫
  发现的 issue 走 T0/T1/T2（默认 retry 上限，跟第一轮一样）。任何
  issue 升到 T3 → 立即 `T3_EXHAUSTED` 退出
- 第二轮 T3 分支顺序：**Pre-T3 triage 优先**（triage 把残留 accept 掉
  则不触发终止），triage 后仍残留才走 `T3_EXHAUSTED`
- Triage 两轮都启用，`accept_cap_per_file=5` 内存独立各 5 条；磁盘
  `extraction_notes/{stage_id}.jsonl` append-only 累积
- 第二轮启动前**读已有 SourceNote fingerprint** 过滤掉，避免同一 issue
  在 jsonl 写两条记录
- 状态机完整重置（tracker / accepted_notes / notes_per_file /
  l3_file_set / gate state 全新）；磁盘文件内容保留（第一轮 T3 写出的
  内容是第二轮的输入）
- `RepairRecorder` JSONL 跨轮保留，事件加 `cycle=0/1` 字段；每次 lane
  run 独立 JSONL（沿用现有行为）
- 删除 `T3_CORRUPTED` 状态（新机制下不再产生）；保留 `T3_EXHAUSTED`
  作为新的终止状态
- 与现有 rate_limit / retry 机制**完全兼容**：rate_limit 在 LLM call
  层处理，repair_agent 不感知；硬停 exit 2 + `--resume` 后 lane 重跑，
  T3 预算跟着 lane 重置（lane-level resume 的固有行为）

**改动清单**

1. [automation/repair_agent/protocol.py:65](../automation/repair_agent/protocol.py#L65)
   `t3_max_per_file` 重命名为 **`max_lifecycles_per_file`**（默认 2），
   语义从「T3 调用次数 cap」改为「一个文件最多走的 lifecycle 数」
2. [automation/repair_agent/coordinator.py](../automation/repair_agent/coordinator.py)
   `run()` 函数体抽成 `_run_one_lifecycle(cycle: int) -> RepairResult`；
   外层 `run()` 加 `for cycle in range(max_lifecycles_per_file)` 循环；
   第二轮（cycle==1）的 `_run_fixer_with_escalation` 在 `tier == 3`
   分支顶部：先跑 Pre-T3 triage，残留为空 break；仍有残留 → 立即
   `T3_EXHAUSTED` 返回（不调 LLM）
3. [automation/repair_agent/coordinator.py:271-298](../automation/repair_agent/coordinator.py#L271-L298)
   第一轮 T3 跑完后**不走 L3 gate / Phase C**：T3 触发记号设上后，
   `_run_one_lifecycle` 立即返回 `terminated_by="T3_TRIGGERED"` 信号；
   外层进入第二轮
4. [automation/repair_agent/coordinator.py:584-604](../automation/repair_agent/coordinator.py#L584-L604)
   删除 `Post-T3 scoped L0–L2 check` + `T3_CORRUPTED` 路径
5. [automation/repair_agent/fixers/file_regen.py](../automation/repair_agent/fixers/file_regen.py)
   `FileRegenFixer.fix()` 新增 `prior_attempt_context: dict | None`
   参数；prompt builder 注入「已修 issue 列表 + 未修 issue 列表」精简
   摘要（~200 token 上限）。数据来源：tracker.history（resolved
   attempts）+ remaining issues
6. [automation/repair_agent/coordinator.py](../automation/repair_agent/coordinator.py)
   第二轮 lifecycle 启动前从磁盘 `extraction_notes/{stage_id}.jsonl`
   读取已 accept 的 fingerprint 集合，第二轮 Phase A 之后立即过滤
7. [automation/config.toml:102](../automation/config.toml#L102)
   `t3_max_per_file = 1` → `max_lifecycles_per_file = 2`，更新注释
8. [ai_context/decisions.md](../ai_context/decisions.md) #25 / #25a
   描述同步（描述当前设计，无 legacy 字样）
9. [docs/requirements.md](../docs/requirements.md) §11.4 同步
10. 单测：覆盖路径——单 lifecycle 通过 / 第一轮 T3 触发 → 第二轮 PASS
    / 第一轮 T3 触发 → 第二轮 T1-T2 修不好升 T3 → `T3_EXHAUSTED` /
    第一轮 triage round 1 全 accept → 不进 T3 → 第一轮 PASS

**待决策项**

无（discussion 已收敛）

**完成标准**

- 单文件最多触发 2 个 lifecycle；第二轮 T3 = `T3_EXHAUSTED` 立即退出
- 第一轮 T3 prompt 含 `prior_attempt_context`（已修 + 未修摘要）
- Triage 两轮独立各 5 条 cap;磁盘 jsonl 同 fingerprint 不重复写
- `T3_CORRUPTED` 路径删除；`T3_EXHAUSTED` 取代之
- 与 rate_limit / `--resume` 机制兼容（无需新工程）
- 单测三条主要路径全过
- decisions.md / requirements.md / config.toml 同步
- 本 todo 条目移到 archived

**预估**：M（1–1.5 天）

**依赖**：无

---

### [T-CHAR-SNAPSHOT-T3-REGEN-PATH] char_snapshot T3 重生成走 sub-lane（β 路径）

**上下文**

character `stage_snapshot` 拆 3 sub-lane 并行的方案下（L1 voice +
relationships + aliases / L2 behavior + boundary + 解读字段 / L3
knowledge + misunderstandings + concealments；程序汇总；schema
validation + repair_agent），当 repair_agent 走到 T3 全文件 LLM regen
时，必须保持「**单一生成路径**」原则——T3 也走 3 sub-lane 并行 +
程序汇总，而不是单文件 prompt regen。避免「首次走 sub-lane、修复走
全文件」的双轨 prompt 维护负担。

代价是 T3 一次性 token ×3。结合 T-REPAIR-T3-LIFECYCLE-RESET 已定型方案
（单文件最多 2 个 lifecycle，第二轮禁用 T3），T3 在一个文件 lifecycle
里**最多触发 1 次** → β 路径的 token 成本上限 = 第一轮 T3 一次 ×3，
可接受。

**改动清单**

1. [automation/repair_agent/fixers/file_regen.py](../automation/repair_agent/fixers/file_regen.py)
   T3 fixer 对 character `stage_snapshot` 文件特殊化：识别文件类型，
   不直接调单文件 LLM regen，而是回到 stage 调度层重新进入 sub-lane
   流程
2. stage 调度层（[automation/persona_extraction/orchestrator.py](../automation/persona_extraction/orchestrator.py)）
   暴露「重跑 char_snapshot sub-lane 并行 + 程序汇总」入口供 T3
   fixer 复用
3. [automation/persona_extraction/post_processing.py](../automation/persona_extraction/post_processing.py)
   或新模块负责 sub-lane partial JSON → 完整 stage_snapshot 的程序汇总
4. T3 触发时为 sub-lane 并行单独设缓速 / 单 lane token cap（避免一次
   把 rate limit 打穿）
5. [ai_context/decisions.md](../ai_context/decisions.md) #25 补充
   「char_snapshot T3 走 sub-lane 路径」例外条款
6. [docs/architecture/extraction_workflow.md](../docs/architecture/extraction_workflow.md)
   Phase 3 描述更新

**待决策项**

1. β 的工程位置：sub-lane 编排逻辑放进 repair_agent 的 fixer 层，
   还是把 T3 抽出 fixer 由 stage 调度层重新进入 sub-lane 流程？
   （倾向后者，避免 fixer 变重）
2. 其他文件类型（world_stage_snapshot / memory_timeline / catalog 等）
   是否也走类似 sub-lane 拆分？本条仅覆盖 char_snapshot

**完成标准**

- char_snapshot T3 路径与首次提取共享同一份 sub-lane prompt + 汇总代码
- 单文件 prompt regen 路径在 char_snapshot 上不再被使用
- decisions.md / extraction_workflow.md 同步
- 本 todo 条目移到 archived

**预估**：M（1–2 天，含 sub-lane 并行方案本身的落地与对接）

**依赖**：

- char_snapshot 3 sub-lane 并行方案本身要先落地（目前未单独立条；
  本条可与之合并为一个 epic）
- T-REPAIR-T3-LIFECYCLE-RESET 方案已定型（无阻塞）

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
