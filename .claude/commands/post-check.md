# /post-check — /go 之后的针对性复审

对**本次修改**做一次聚焦复审，双轨并进：**轨 1 — 原始需求落实情况**（对账 PRE log 的计划动作清单 + 验证标准）、**轨 2 — 影响扩散 / 计划外副作用**（向计划之外的文件扩散找冲突 / bug / 歧义 / 不一致）。**可并行用 sub-agent 扫描审计**。

这不是全仓 review（那是 `/full-review`），只针对这次 `/go` 触及的细节。`$ARGUMENTS` 存在则作为本轮 log 文件 slug 精确匹配；否则取 `logs/change_logs/` 按 filename 时间戳最新的一份作为 intent 基线。

## Progress reporting

下方流程分为 `## Step 0:` ~ `## Step 7:`（含子 step `## Step 1.5:`）。

**进入 Step 0 之前**：调用 **<进度工具>** 把 Step 0 / Step 1 / Step 1.5 / Step 2 ~ Step 7 全部预登记（每个 step 一条，`content` 用 `Step N: <子段标题>`，`status` 全为 `pending`）。这是硬性要求，**不调 <进度工具> 不许往下走**。

每进入一个 step：调 **<进度工具>** 把当前 step 改 `in_progress`（同一次调用里把上一个 step 标 `completed`），然后做实际工作。**step 跨越时不要漏调**。进度由 <进度工具> 的 UI 直接显示，**对话里不再打 `[/post-check] Step N: ...` 之类的进度行**。

跳过某 step：调 **<进度工具>** 把对应条目直接标 `completed`，并在对话里打一行 `Step N 跳过（理由：…）`——"理由"是 UI 缺失的信息，保留这一行；不要静默略过。

最后一步完成：调 **<进度工具>** 把最后一条标 `completed`。

**<进度工具> 解析**：Claude → `TodoWrite`（界面显示为 "Update Todos"）；Codex → `update_plan`。语义对齐：预登记 + 切状态 + 标完成。

## Step 0: Load skills config

`Read` `ai_context/skills_config.md`。

- 文件不存在 / 某节标题缺失 → fail loudly：打印缺失项 + 提示按 plugin 模板补全，停手
- 某节内容 `(none)` 或留空 → 跳过该节相关步骤（视为本项目无此项）
- 某节列了具体路径但路径不存在 → fail loudly：提示该节漂移到不存在路径，停手等用户修

后续步骤出现 "skills_config.md `## XX`" 时引用本配置。本 skill 用到：
`## Example artifact directories`（轨 2 产物结构线）、
`## Sensitive content placeholder rules`（轨 2 残留检查）、
`## Protected branch prefixes`（Step 5 commit 分支提示）、
`## Data contract directories`（Step 3 规范线数据契约扫描；含 JSON Schema / proto / OpenAPI / Pydantic / SQL DDL 等）。

## Step 1: 界定本次改动范围

- `git log --oneline -n 10` + `git status` 判断 `/go` 产出的 commit 区间（一般是最近 1–N 个）；改动若未提交则用 working tree 快照
- `git diff <base>..HEAD --stat`（或 `git diff --stat`）列出本次触及的文件清单，作为"必须复核"的文件集
- 明确打印："本次复审范围：commits {X..Y}（或 working tree），N 个文件"

## Step 1.5: 加载 intent 基线（强制）

- `$ARGUMENTS` 传 slug → 精确匹配 `logs/change_logs/*_{slug}.md`；否则取 `logs/change_logs/` 按 filename 时间戳最新的一份
- 读 PRE 段：**背景 / 触发**、**结论与决策**、**计划动作清单**、**验证标准**、**执行偏差**
- 打印："intent 基线：`logs/change_logs/{...}.md`" + PRE 段结构化摘要
- log 缺失或无 PRE 段 → 打印"⚠️ intent 基线缺失，轨 1 跳过，只跑轨 2"并继续

## Step 2: Cross-File Alignment 对照

读 `ai_context/conventions.md` 的 Cross-File Alignment 表；对照本次触及的每个维度（需求 / schema / prompt / code / 架构 / ai_context / README / 目录结构），列出**本应一起被改**的文件集合。这份集合同时喂给轨 1（对账 Missed Updates）和轨 2（扩散起点）。

该表不存在时：跳过本步的对账输入，轨 1 仅用 PRE 计划清单 + 实际 diff 对账（Missed Updates 退化为"PRE 列了但没改"的子集），轨 2 扩散起点仅用本次 diff 触及文件 + 上下游引用。

## Step 3: 并行 sub-agent 双轨审计线

> **轨 vs. 线**：**轨**是审计视角（轨 1 对账 / 轨 2 扩散，共 2 条），**线**是扫描分工（按文件域切片派 sub-agent，共 4 条）。两者正交——每条线都同时跑两条轨。

改动面小就单线跑；跨模块或跨层时并行派 sub-agent，四条线各自同时承担双轨：

1. **规范线**：`docs/requirements.md` / `docs/architecture/` / `ai_context/` / skills_config.md `## Data contract directories` 列出的目录（`(none)` 时跳过该节扫描）/ `prompts/` —— 描述 vs. 本次改动是否一致，有无残留旧描述 / 旧字段 / 旧流程
2. **实现线**：本次改过的代码 + 其上下游（调用方 / 被调用方 / 导入方）—— 字段名 / 参数 / 返回值 / 状态机 / 门控 / 异常路径是否连贯，import 是否还能跑
3. **风险线**：本次改过的代码 + 受其牵连的相关代码（调用方 / 被调用方 / 共享状态 / 共享数据流）—— 边界条件、空值 / None、异常路径、并发、重试 / 回滚、错误处理是否藏 bug；新行为是否引入数据丢失 / 安全口子 / 性能回退；状态机 / 门控 / 不变量是否有漏覆盖分支。**与实现线区分**：实现线问"还连得上吗"（签名 / import / 上下游一致性），风险线问"做的事对吗"（语义正确性 + 失败模式）；产出归到 Step 4 的「bug / 行为风险」与 Step 6 报告的同名小节
4. **产物与结构线**：本次是否影响 skills_config.md `## Example artifact directories` 列出的目录里的样例、相关 README 展示、目录结构；若改了目录或文件名，追查所有引用点。该节 `(none)` / 留空时跳过本线

> **派出的每个 sub agent 都必须先重读 intent 基线 PRE log**：把 Step 1.5 读到的 log 路径塞进它的 prompt，并**明示要求它开工前先读完 PRE 的"结论与决策 / 计划动作清单 / 验证标准 / 执行偏差"**，再按本条线的范围扫描。sub agent 是独立 context，不强制它读 PRE 就只会按 prompt 里的 brief 空转，容易脱离本次 intent；对账与扩散判断都必须扎根在 PRE log 上。

每条线产出：**轨 1 对账结果**（PRE 计划项 × 实际改动的核对）+ **轨 2 发现**（计划外文件的问题，带文件 + 行号、直接证据 vs. 推断）。

## Step 4: 重点检查项（只针对本次改动）

- **跨文件不一致**：同一字段 / 概念在 schema / 代码 / 文档 / prompt 里命名与定义是否一致
- **歧义**：需求 / 架构描述里对新行为是否存在两种读法
- **冲突**："文档说 A，代码做 B，样例又是 C" 是否出现
- **残留旧逻辑 / legacy 措辞**：有无描述旧流程的段落、被替换的字段、失效的 import、死分支；顺查本次触及的 docs / prompts / ai_context 有没有违反 skills_config.md `## Sensitive content placeholder rules` 的真实内容，或 `旧 / legacy / 已废弃 / 原为` 字样
- **悬挂引用 / 过度删除**：本次 diff 若删除了符号 / 文件 / 段落，grep 仓库剩余位置是否还有引用方未更新；这是「残留旧逻辑」的反向——旧目标已没，旧引用还在
- **change_log / docs 内链断链**：本次 log 或修改过的 docs 里引用 `decisions.md #25` / `[xxx](path)` / `详见 logs/change_logs/.../X.md` 等，核对编号未漂移、相对路径存在、anchor 锚点真实
- **todo_list 漂移**：本次改动若实质完成了某 todo 条目（PRE log「完成标准」段含「本 todo 条目移到 archived」、或 diff 等价于某条 Next/Discussing 条目的「改动清单」），核对 `docs/todo_list.md` 该条目是否已整条移到 `docs/todo_list_archived.md` `## Completed` + Index 段是否同步刷新。漏移 → 列入 Missed Updates
- **bug / 行为风险**：新代码在边界条件、空值、异常路径下会不会崩；状态机 / 门控 / 重试 / 回滚是否有漏口
- **README / 目录结构**：新增 / 删除 / 改名的文件是否同步到相关 README 与目录说明
- **ai_context 漂移**：本次的 durable 决策是否已落 `ai_context/decisions.md` / `current_status.md` / `next_steps.md`；handoff 是否需要更新
- **commit message vs diff 匹配度**：commit body 描述 vs `git diff --stat` 实际改动 是否互相覆盖——body 列了 N 处但 diff 只动 M 处，或 diff 改了文件 body 没提

> Step 3 / Step 4 跑完后，把双轨结论（计划项落实状态、Findings 列表、Missed Updates、Open Questions、Residual Risks）**先 hold 在脑里 / 笔记里**，不要立刻打印。Step 5 用结构化摘要回写 log + commit；Step 6 才把完整报告打印到对话——这样完整报告就是 `/post-check` 输出的最后一段，用户看完就能直接拍板，不需要往回翻屏。

## Step 5: 回写 log（摘要版）+ commit

把双轨结论的**结构化摘要**追加到 **intent 基线那份 log 文件**（Step 1.5 读的那份），**不重复贴完整 Findings 全文**（全文留给 Step 6 在对话里展开，避免 log 文件爆炸）：

```markdown
<!-- /post-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：{M/N 项计划 + K/L 项验证}
- Missed updates: {X} 条（详见对话）

### 轨 2 — 影响扩散
- Findings: High={h} / Medium={m} / Low={l}
- Open Questions: {q} 条（详见对话）

## 复查时状态
- **Reviewed**: {timestamp}
- **Status**: REVIEWED-PASS | REVIEWED-FAIL | REVIEWED-PARTIAL
  - PASS = 轨 1 全落实 且 轨 2 无 High/Medium
  - PARTIAL = 轨 1 有缺口 或 轨 2 有 Medium，无 High
  - FAIL = 轨 1 大面积未落实 或 轨 2 有 High
- **Conversation ref**: 同会话内 /post-check 输出
```

log 缺失时：打印"⚠️ 无 log 可回写，复查结论仅在对话中保留"，并**直接进入 Step 6**（无 commit 可做）。

回写完成后**立即 commit 这一份 log 文件**——不要留作脏工作区，否则下一轮 `/go` 的 Step 1 自动锁定逻辑会把这份残留误判为"dirty 工作区"而强制走 worktree 路径，形成"上轮 log 回写在干扰下一轮开发"的副作用。

- commit 在**当前分支**即可（`/post-check` 通常运行于主分支或 skills_config.md `## Protected branch prefixes` 列出的长跑分支，无需切换）
- 仅 `git add` 这一份 log 文件——不要顺手把其他无关 dirty 文件带进 commit
- commit message 风格对齐既有先例：`log({slug}): /post-check 复查结论回写 REVIEWED-PASS|PARTIAL|FAIL`
- 不 push，不切分支；commit 后立刻进入 Step 6

log 缺失（无回写）时跳过 commit。

## Step 6: 对话输出完整双轨报告

**这是用户决策的主要界面，所有 Findings / Missed Updates / Open Questions 完整打印到对话**，不省略、不只放摘要。**这是 `/post-check` 在对话里的最后一段实质内容**——放在 log 回写之后，用户看完报告就能直接拍板，不需要往回翻屏。

Markdown 模板：

```markdown
## Scope
- commits {X..Y}（或 working tree），N 个文件
- intent 基线：`logs/change_logs/{...}.md`（或"缺失"）

---

## 轨 1 — 原始需求落实情况（对账）

基于 PRE log 的"计划动作清单 + 验证标准"逐项核对：

| 计划项 | 状态 | 证据 |
|--------|------|------|
| {file A: 改动要点} | ✅ 已落实 | {diff 摘要 / 行号} |
| {file B: 改动要点} | ⚠️ 部分落实 | {缺了 X} |
| {file C: 改动要点} | ❌ 未落实 | {文件未触及} |
| {验证标准 1} | ✅ 通过 | {命令输出摘要} |
| {验证标准 2} | ❌ 失败 | {错误摘要} |

**Missed Updates**（对账差集 ∪ Cross-File Alignment 差集）：
- {file 路径 — 本应同步但没同步的理由}

intent 基线缺失时：**跳过本轨**并打印"无 PRE log，无法对账"。

---

## 轨 2 — 影响扩散 / 计划外副作用

用 intent 圈定的 scope 为起点，向**计划之外**的文件扩散：

### Findings
- **[H]** `{file:line}` — {冲突 / bug / 歧义描述} — 证据 / 推断
- **[M]** `{file:line}` — ...
- **[L]** `{file:line}` — ...

### Cross-file 冲突
- "文档说 A，代码做 B，样例又是 C"类发现

### 残留旧逻辑 / legacy 措辞
- {位置 + 行号}

### bug / 行为风险
- {边界、空值、异常路径、状态机漏口}

### README / 目录 / ai_context 漂移
- {漂移点}

---

## Open Questions
{仓库内无法独自判断、需用户拍板的点}

## Alignment Summary
本次改动在 需求 / schema / 代码 / README / 架构 / ai_context / prompts / 目录 各层的对齐状况；哪层最不对齐

## Residual Risks
{未确认成 bug 但值得警惕}
```

## Step 7: 等待确认

完整报告打印完成后**停手**。最多再补一句"等你拍板"或类似的极短语句作为结束语，**不要再写总结、不要再 commit、不要再列 next steps**——任何尾巴都会把双轨报告挤上去。不要进入 `/go`、不要改代码、不要改 schema / prompt / docs / ai_context；等用户基于对话里的完整报告逐条拍板，通常交由下一轮 `/go` 执行补改。

## 约束

- 这是针对**本次修改**的复审，不是全仓 review；超出本次改动范围的疑点 → 登记到 `Residual Risks` 或 `Open Questions`，不在本轮追
- **只读 + 单写单 commit 例外**：不改代码、不改 docs、不改 schema / prompt / ai_context；**唯一允许的写 + commit 是 Step 5 那份 log 摘要回写**——其他 dirty 文件一律不动、不提交
- 每条 finding 必须落到文件 + 行号；直接证据与推断分开标注
- 不要因为 `/go` Step 7 已经 review 过就走过场 —— 此轮用新的眼睛再看一遍，重点抓 `/go` 漏掉的连带文件和歧义
- 轨 1 和轨 2 都要跑（除非 intent 基线缺失跳过轨 1）；不能只做其中一条
- **输出顺序硬约束**：log 回写 + commit (Step 5) **先于** 对话报告输出 (Step 6)。完整双轨报告必须是 `/post-check` 在对话里的**最后一段实质内容**——Step 7 只放一行"等待确认"短语作收尾，不要在报告之后再跟一段总结 / commit 提示 / next steps，否则用户又得回滚屏幕

---

**镜像约束**：本文件和 `.agents/skills/post-check/SKILL.md` 正文保持同步——任一侧修改必须在同 commit 内镜像到另一侧。`.agents/skills/post-check/SKILL.md` 额外带 YAML frontmatter（`name` / `description`），正文（从一级标题 `# /post-check` 起往下）与本文件**逐字一致**。
