---
name: commit
description: 快速确认并提交当前改动 — 校验 working tree 有效性、分支正确性、追踪状态（禁提路径/大文件/未跟踪文件），按逻辑单元分 commit，message 风格对齐仓库惯例；commit 后列出所有本地分支同步状态，询问是否 forward/merge 到其他分支（不擅自展开）。不做 ai_context/docs 对齐（那是 /go 范围），不 push / 不 force / 不 amend。用户说"commit 一下"、"提交当前改动"、"/commit" 时触发。
---

# /commit — 快速确认并提交当前改动

对当前 working tree 做一次轻量校验，确认改动有效、分支正确、追踪状态无误后 commit；完成后询问是否把改动 forward / merge 到其他分支。**不做全仓 review、不动 ai_context / docs 对齐**（那是 `/go` 的事）。`$ARGUMENTS` 存在则作为 commit message 的提示 / 主题。

## 0. 改动有效性

- `git status` + `git diff --stat` 看 working tree 与 index
- 若完全没有改动：打印"无改动"并停手
- 扫改动列表，判断是否值得独立 commit（不是空白 / 误保存 / 临时 debug 打印）；有可疑 → 先问用户

## 1. 分支正确性

- `git branch --show-current` 打印当前分支
- 按项目硬规则：代码 / schema / prompt / docs / ai_context 改动应在 master；功能实验 / 长跑进程在对应 feature 分支
- 当前分支与改动性质不匹配 → 先停手报告，等用户决定（切分支、worktree、或坚持当前分支）

## 2. 追踪状态

- 扫禁提路径：`sources/` 原文、数据库文件、`.sqlite*`、embeddings、caches、真实 user packages（对照 `.gitignore` + `ai_context/conventions.md`）
- `git ls-files --others --exclude-standard` 看未跟踪文件，判断是否应该一并加入 / 加入 .gitignore / 留着
- 大文件（>1MB）或二进制单独列出，请用户确认是否入库
- 任一项可疑 → 停手问用户，不要擅自 `git add -A`

## 3. Commit

- 按逻辑单元分 commit（若单次改动跨多个独立主题）；一次别塞太多
- message 风格对照 `git log --oneline -10`，保持仓库惯例（中英文 / prefix / 动词时态）
- `$ARGUMENTS` 存在则以此为主题扩写；否则根据 diff 归纳
- 执行 `git add <具体文件>` + `git commit`（**不用 `git add -A` / `git add .`**，避免误入敏感文件）
- commit 后 `git status` 确认干净

## 4. Forward / Merge 询问

- `git branch --format='%(refname:short)'` 列出所有本地分支
- 对每个非当前分支，用 `git merge-base --is-ancestor <当前分支> <branch>` 判断是否已含本次 commit
- 输出一个简表：`{branch} | 已同步 / 未同步 | 状态（有进程 / 干净）`
- **问用户**：是否需要把本次 commit forward / merge 到未同步的分支？列出候选分支，等回答；不要擅自切分支合并
- 用户指定要同步的分支后：`git checkout <branch> && git merge <原分支>`；冲突先停手，让用户决定；合并完回原分支

## 约束

- 只提交本次 working tree 改动；不做 ai_context / docs / README 对齐（那是 `/go` 范围）
- 不 `git push`、不 `--force`、不 `--amend`（除非用户明确要求）
- 不 `git add -A`；逐文件加
- 发现可疑（禁提路径、巨型 diff、分支不对、有未解决冲突）→ 停手问，不绕过
- forward / merge 必须经用户确认，不擅自展开

---

**镜像约束**：本文件和 `.claude/commands/commit.md` 正文保持同步——任一侧修改必须在同 commit 内镜像到另一侧。本文件额外带 YAML frontmatter（`name` / `description`），正文（从一级标题 `# /commit` 起往下）与 `.claude/commands/commit.md` **逐字一致**。
