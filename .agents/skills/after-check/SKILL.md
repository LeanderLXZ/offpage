---
name: after-check
description: /go 之后的针对性复审 — 只针对本次 /go 改动，确认需求/schema/代码/README/架构/ai_context/prompts/目录结构是否对齐，检查跨文件冲突、歧义、bug、风险、遗漏更新。可并行派 sub-agent 跑规范线/实现线/产物线。只读不写，输出不落盘、不改代码、不提交，等用户确认后再决定是否用 /go 补改。用户说"再确认一下这次改动"、"after-check"、"/go 完了复审一下" 时触发。
---

# /after-check — /go 之后的针对性复审

对**本次修改**做一次聚焦复审，再次确认需求文档、schema、代码、README、架构、ai_context、prompts、目录结构是否对齐这次改动；检查每个涉及的文件里存不存在冲突、歧义、bug、风险。**可并行用 sub-agent 扫描审计**。

这不是全仓 review（那是 `/full-review`），只针对这次 `/go` 触及的细节；也不是二次 finding 挖掘，不新增与本次改动无关的问题。`$ARGUMENTS` 存在则作为本轮聚焦方向或额外关注点。

## 0. 界定本次改动范围

- `git log --oneline -n 10` + `git status` 判断 `/go` 产出的 commit 区间（一般是最近 1–N 个）；改动若未提交则用 working tree 快照
- `git diff <base>..HEAD --stat`（或 `git diff --stat`）列出本次触及的文件清单，作为"必须复核"的文件集
- 明确打印："本次复审范围：commits {X..Y}（或 working tree），N 个文件"

## 1. 真相来源与连带文件对齐

读 `ai_context/conventions.md` 的 Cross-File Alignment 表；对照本次触及的每个维度（需求 / schema / prompt / code / 架构 / ai_context / README / 目录结构），列出**本应一起被改**的文件集合，与**实际改了**的对比，差集 = 疑似遗漏更新，单独登记。

## 2. 并行审计线（可派 sub-agent）

改动面小就单线跑；改动跨模块或跨层时并行派 sub-agent，至少三条线：

1. **规范线**：`docs/requirements.md` / `docs/architecture/` / `ai_context/` / `schemas/` / `prompts/` —— 描述 vs. 本次改动是否一致，有无残留旧描述 / 旧字段 / 旧流程
2. **实现线**：本次改过的代码 + 其上下游（调用方 / 被调用方 / 导入方）—— 字段名 / 参数 / 返回值 / 状态机 / 门控 / 异常路径是否连贯，import 是否还能跑
3. **产物与结构线**：本次是否影响 `works/` / `users/_template/` 的样例、相关 README 展示、目录结构；若改了目录或文件名，追查所有引用点

每条线产出：涉及文件清单、问题（带文件 + 行号）、直接证据 vs. 推断。

## 3. 重点检查项（只针对本次改动）

- **跨文件不一致**：同一字段 / 概念在 schema / 代码 / 文档 / prompt 里命名与定义是否一致
- **歧义**：需求 / 架构描述里对新行为是否存在两种读法
- **冲突**："文档说 A，代码做 B，样例又是 C" 是否出现
- **残留旧逻辑 / legacy 措辞**：有无描述旧流程的段落、被替换的字段、失效的 import、死分支；顺查本次触及的 docs / prompts / ai_context 有没有混入真实书名 / 角色 / 剧情 或 `旧 / legacy / 已废弃 / 原为` 字样
- **bug / 行为风险**：新代码在边界条件、空值、异常路径下会不会崩；状态机 / 门控 / 重试 / 回滚是否有漏口
- **README / 目录结构**：新增 / 删除 / 改名的文件是否同步到相关 README 与目录说明
- **ai_context 漂移**：本次的 durable 决策是否已落 `ai_context/decisions.md` / `current_status.md` / `next_steps.md`；handoff 是否需要更新

## 4. 输出格式

输出 markdown（**不改代码、不提交、不写 log、不落盘**）：

1. `Scope`：本次复审覆盖的 commit 范围 / 文件清单
2. `Findings`：按 High / Medium / Low 排序，每条带文件 + 行号、结论、证据、影响范围；推断标注"推断"
3. `Missed Updates`：Step 1 差集 —— 本应同步但没同步的文件
4. `Open Questions`：仓库内无法独自判断、需用户拍板的点
5. `Alignment Summary`：本次改动在各层（需求 / schema / 代码 / README / 架构 / ai_context / prompts / 目录）的对齐状况，哪层最不对齐
6. `Residual Risks`：未确认成 bug 但值得警惕的地方

## 5. 等待确认

输出后**停手**。不要进入 `/go`、不要改文件、不要写 log、不要 commit；等用户逐条确认后再决定是否补改（通常交由 `/go` 执行）。

## 约束

- 这是针对**本次修改**的复审，不是全仓 review；超出本次改动范围的疑点 → 登记到 `Residual Risks` 或 `Open Questions`，不在本轮追
- 只读不写：不改代码、不改文档、不落盘报告（归档是 `/full-review` 的事）
- 每条 finding 必须落到文件 + 行号；直接证据与推断分开标注
- 不要因为 `/go` Step 5 已经 review 过就走过场 —— 此轮用新的眼睛再看一遍，重点抓 `/go` 漏掉的连带文件和歧义

---

**镜像约束**：本文件和 `.claude/commands/after-check.md` 正文保持同步——任一侧修改必须在同 commit 内镜像到另一侧。本文件额外带 YAML frontmatter（`name` / `description`），正文（从一级标题 `# /after-check` 起往下）与 `.claude/commands/after-check.md` **逐字一致**。
