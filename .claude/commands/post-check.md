# /post-check — /go 之后的针对性复审

对**本次修改**做一次聚焦复审，双轨并进：**轨 1 — 原始需求落实情况**（对账 PRE log 的计划动作清单 + 验证标准）、**轨 2 — 影响扩散 / 计划外副作用**（向计划之外的文件扩散找冲突 / bug / 歧义 / 不一致）。**可并行用 sub-agent 扫描审计**。

这不是全仓 review（那是 `/full-review`），只针对这次 `/go` 触及的细节。`$ARGUMENTS` 存在则作为本轮 log 文件 slug 精确匹配；否则取 `docs/logs/` 按 filename 时间戳最新的一份作为 intent 基线。

## 0. 界定本次改动范围

- `git log --oneline -n 10` + `git status` 判断 `/go` 产出的 commit 区间（一般是最近 1–N 个）；改动若未提交则用 working tree 快照
- `git diff <base>..HEAD --stat`（或 `git diff --stat`）列出本次触及的文件清单，作为"必须复核"的文件集
- 明确打印："本次复审范围：commits {X..Y}（或 working tree），N 个文件"

## 0.5 加载 intent 基线（强制）

- `$ARGUMENTS` 传 slug → 精确匹配 `docs/logs/*_{slug}.md`；否则取 `docs/logs/` 按 filename 时间戳最新的一份
- 读 PRE 段：**背景 / 触发**、**结论与决策**、**计划动作清单**、**验证标准**、**执行偏差**
- 打印："intent 基线：`docs/logs/{...}.md`" + PRE 段结构化摘要
- log 缺失或无 PRE 段 → 打印"⚠️ intent 基线缺失，轨 1 跳过，只跑轨 2"并继续

## 1. Cross-File Alignment 对照

读 `ai_context/conventions.md` 的 Cross-File Alignment 表；对照本次触及的每个维度（需求 / schema / prompt / code / 架构 / ai_context / README / 目录结构），列出**本应一起被改**的文件集合。这份集合同时喂给轨 1（对账 Missed Updates）和轨 2（扩散起点）。

## 2. 并行 sub-agent 双轨审计线

改动面小就单线跑；跨模块或跨层时并行派 sub-agent，三条线各自同时承担双轨：

1. **规范线**：`docs/requirements.md` / `docs/architecture/` / `ai_context/` / `schemas/` / `prompts/` —— 描述 vs. 本次改动是否一致，有无残留旧描述 / 旧字段 / 旧流程
2. **实现线**：本次改过的代码 + 其上下游（调用方 / 被调用方 / 导入方）—— 字段名 / 参数 / 返回值 / 状态机 / 门控 / 异常路径是否连贯，import 是否还能跑
3. **产物与结构线**：本次是否影响 `works/` / `users/_template/` 的样例、相关 README 展示、目录结构；若改了目录或文件名，追查所有引用点

> **派出的每个 sub agent 都必须先重读 intent 基线 PRE log**：把 Step 0.5 读到的 log 路径塞进它的 prompt，并**明示要求它开工前先读完 PRE 的"结论与决策 / 计划动作清单 / 验证标准 / 执行偏差"**，再按本条线的范围扫描。sub agent 是独立 context，不强制它读 PRE 就只会按 prompt 里的 brief 空转，容易脱离本次 intent；对账与扩散判断都必须扎根在 PRE log 上。

每条线产出：**轨 1 对账结果**（PRE 计划项 × 实际改动的核对）+ **轨 2 发现**（计划外文件的问题，带文件 + 行号、直接证据 vs. 推断）。

## 3. 重点检查项（只针对本次改动）

- **跨文件不一致**：同一字段 / 概念在 schema / 代码 / 文档 / prompt 里命名与定义是否一致
- **歧义**：需求 / 架构描述里对新行为是否存在两种读法
- **冲突**："文档说 A，代码做 B，样例又是 C" 是否出现
- **残留旧逻辑 / legacy 措辞**：有无描述旧流程的段落、被替换的字段、失效的 import、死分支；顺查本次触及的 docs / prompts / ai_context 有没有混入真实书名 / 角色 / 剧情 或 `旧 / legacy / 已废弃 / 原为` 字样
- **bug / 行为风险**：新代码在边界条件、空值、异常路径下会不会崩；状态机 / 门控 / 重试 / 回滚是否有漏口
- **README / 目录结构**：新增 / 删除 / 改名的文件是否同步到相关 README 与目录说明
- **ai_context 漂移**：本次的 durable 决策是否已落 `ai_context/decisions.md` / `current_status.md` / `next_steps.md`；handoff 是否需要更新

## 4. 对话输出完整双轨报告

**这是用户决策的主要界面，所有 Findings / Missed Updates / Open Questions 完整打印到对话**，不省略、不只放摘要。Markdown 模板：

```markdown
## Scope
- commits {X..Y}（或 working tree），N 个文件
- intent 基线：`docs/logs/{...}.md`（或"缺失"）

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

## 5. 回写 log（摘要版）

把双轨结论的**结构化摘要**追加到 **intent 基线那份 log 文件**（Step 0.5 读的那份），**不重复贴完整 Findings 全文**（全文在对话里，避免 log 文件爆炸）：

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

log 缺失时：打印"⚠️ 无 log 可回写，复查结论仅在对话中保留"。

## 6. 等待确认

对话输出 + log 摘要回写完成后**停手**。不要进入 `/go`、不要改代码、不要改 schema / prompt / docs / ai_context、不要 commit；等用户基于对话里的完整报告逐条拍板，通常交由下一轮 `/go` 执行补改。

## 约束

- 这是针对**本次修改**的复审，不是全仓 review；超出本次改动范围的疑点 → 登记到 `Residual Risks` 或 `Open Questions`，不在本轮追
- **只读 + 单写例外**：不改代码、不改 docs、不改 schema / prompt / ai_context、不提交；**唯一的写操作是 Step 5 追加 log 摘要**
- 每条 finding 必须落到文件 + 行号；直接证据与推断分开标注
- 不要因为 `/go` Step 6 已经 review 过就走过场 —— 此轮用新的眼睛再看一遍，重点抓 `/go` 漏掉的连带文件和歧义
- 轨 1 和轨 2 都要跑（除非 intent 基线缺失跳过轨 1）；不能只做其中一条

---

**镜像约束**：本文件和 `.agents/skills/post-check/SKILL.md` 正文保持同步——任一侧修改必须在同 commit 内镜像到另一侧。`.agents/skills/post-check/SKILL.md` 额外带 YAML frontmatter（`name` / `description`），正文（从一级标题 `# /post-check` 起往下）与本文件**逐字一致**。
