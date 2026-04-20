---
name: go
description: 方案落盘 — 按上文讨论把 schema/代码/config/docs 改动按 8 步流程（环境隔离 → requirements → 实现 → 测试 → 文档对齐 → 全库 review → log → commit → 分支同步）推进到可交付状态。用户说"落地"、"执行方案"、"go"、"把刚才讨论的改下来" 时触发。
---

# /go — 方案落盘

按上文讨论执行；某步本次 N/A 就明说"跳过 Step X"。`$ARGUMENTS` 存在即本次改动焦点。

## 0. 环境 & 隔离
- `git branch --show-current`；项目硬规则：代码 / schema / prompt / docs / ai_context 变更**先进 master**，其他分支通过 `git merge master` 同步；大架构更改尤其要守。
- `pgrep -af persona_extraction` + 看 `works/*/analysis/progress/*.pid`；评估本次改动会不会让进程崩。
- 有冲突：`git worktree` 开 master 副本改；或推迟。
- 明确说出策略："在 master / worktree / 等进程结束"。

## 1. 需求文档 `docs/requirements.md`
更新相关节，含流程图 / 示例。**新增流程图 / 示例仅当现有内容无法覆盖新逻辑时**，避免冗余。**不出现真实书名 / 角色 / 剧情**，用通用占位符；描述只写当前设计，不写"旧 / legacy / 已废弃 / 原为"。同步 `ai_context/requirements.md` + `decisions.md`。

## 2. 核心实现
按讨论改 schema、prompt template、架构代码、配置。对照 `ai_context/conventions.md` 的 Cross-File Alignment 表列出连带文件。

## 3. 轻量测试（仅有代码 / schema 变更时）
Import 检查 + 关键函数 smoke test；schema 改动跑 `jsonschema` 校验。有错立即修。

## 4. 文档对齐
同步 `ai_context/`（仅 durable truth）、`docs/architecture/`、相关 README。再查 `docs/todo_list.md`：新任务登记、已完成条目**清除**、状态变化更新。

## 5. 全库 review
并行扫描（可派 Agent）所有可能涉及的文件：需求、schema、代码、README、architecture、ai_context、prompts、目录结构。检查项：**残留旧逻辑、歧义、跨文件不一致、冲突、遗漏更新、bug、风险**；顺查有无混入真实书名或 legacy 字样。**发现即修**；太大则登记到 `docs/todo_list.md`。

## 6. 写 log
`docs/logs/{YYYY-MM-DD}_{HHMMSS}_{slug}.md`。HHMMSS 强制，`TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'` 获取。内容：改了什么 / 哪些文件 / 为什么。

## 7. Git commit
`git status` 只剩本次改动；扫禁提路径（`sources/` 原文、数据库、embeddings、caches、真实 user packages）；message 风格对齐 `git log --oneline -10`；按逻辑单元分 commit；提交后 `git status` 确认干净，非 master 分支按 Step 0 策略回合。

## 8. 同步其他分支
`git branch --format='%(refname:short)'` 列出所有本地分支；对每个非 master 分支判断是否已含本次 master 改动（`git merge-base --is-ancestor master <branch>` → 0 即已同步）。未同步的分支：
- 若分支有正在运行的进程（如 `extraction/*`）或未完成工作：记录到 `docs/todo_list.md` 推迟同步，不强推
- 否则 `git checkout <branch> && git merge master`；冲突先停手，让用户决定；干净合并后 `git checkout master`
最后打印每个分支的同步状态（已同步 / 已合并 / 推迟原因）。

---

**镜像约束**：本文件和 `.claude/commands/go.md` 正文保持同步——任一侧修改必须在同 commit 内镜像到另一侧。本文件额外带 YAML frontmatter（`name` / `description`），正文（从一级标题 `# /go` 起往下）与 `.claude/commands/go.md` **逐字一致**。
