---
name: push
description: 把指定本地分支 push 到对应 remote。$ARGUMENTS = 分支名（不传 → 默认 `main`）。流程：解析分支 → 校验存在 → 确认追踪状态与领先/落后情况 → 干净 push（fast-forward only，不允许 --force / --no-verify）。用户说"push 一下"、"推一下 main"、"/push"、"/push library" 时触发。
---

# /push — 把分支 push 到 remote

把指定本地分支推到它的 remote。**不做 commit、不做 merge、不做 rebase**——这只是个干净的 push。

## Progress reporting

下方流程分为 `## Step 0:` ~ `## Step 3:`（前置一段 `## $ARGUMENTS 解析` 是参数解析，不算正式 step）。

**进入 Step 0 之前**：调用 **<进度工具>** 把 Step 0 ~ Step 3 全部预登记（每个 step 一条，`content` 用 `Step N: <子段标题>`，`status` 全为 `pending`；`$ARGUMENTS` 解析不计入）。这是硬性要求，**不调 <进度工具> 不许往下走**。

每进入一个 step：调 **<进度工具>** 把当前 step 改 `in_progress`（同一次调用里把上一个 step 标 `completed`），然后做实际工作。**step 跨越时不要漏调**。进度由 <进度工具> 的 UI 直接显示，**对话里不再打 `[/push] Step N: ...` 之类的进度行**。

跳过某 step：调 **<进度工具>** 把对应条目直接标 `completed`，并在对话里打一行 `Step N 跳过（理由：…）`——"理由"是 UI 缺失的信息，保留这一行；不要静默略过。

最后一步完成：调 **<进度工具>** 把最后一条标 `completed`。

**<进度工具> 解析**：Claude → `TodoWrite`（界面显示为 "Update Todos"）；Codex → `update_plan`。语义对齐：预登记 + 切状态 + 标完成。

## `$ARGUMENTS` 解析

- `$ARGUMENTS` 为空 → 目标分支 = `main`
- 否则 → 目标分支 = `$ARGUMENTS` 去掉首尾空白后的字符串（只取首个 token；多余 token 报错停手，让用户重新表达）

## Step 1: 校验目标分支

- `git rev-parse --verify <target>` 确认本地分支存在；不存在 → 停手报告
- `git config --get branch.<target>.remote` + `branch.<target>.merge` 取追踪 remote / 远端分支名
  - 没有追踪 → 停手问用户：是否要 `git push -u origin <target>` 建追踪？得到肯定回复才继续
- 当前 HEAD 不必切到目标分支；用 `git push <remote> <target>:<remote-branch>` 即可（无需 checkout）

## Step 2: 推前盘点

- `git fetch <remote> <remote-branch>` 拉最新远端引用
- 算 ahead / behind：`git rev-list --left-right --count <target>...<remote>/<remote-branch>`
  - ahead=0, behind=0 → 已同步，跳过 Step 3，打印"无需 push"收尾
  - ahead>0, behind=0 → 可 fast-forward，进 Step 3
  - behind>0（无论 ahead 多少）→ 远端有本地没有的 commit，**停手报告**，让用户决定（pull / rebase / 放弃）；**不自动 force push**
- 顺手列出 ahead 的 commit（`git log --oneline <remote>/<remote-branch>..<target>`），让用户在 push 前过一眼

## Step 3: Push

- 执行 `git push <remote> <target>:<remote-branch>`（不传 `--force` / `--force-with-lease` / `--no-verify`）
- push 成功 → 再 `git rev-list --left-right --count <target>...<remote>/<remote-branch>` 复核 0/0，打印结果
- push 失败（hook 拦截、权限、网络等）→ 打印错误原文，停手让用户处理；**不重试 / 不绕过**

## 约束

- 只 push 一个分支（`$ARGUMENTS` 指定的或默认 `main`）；不批量 push
- 不 `--force` / `--force-with-lease` / `--no-verify` / `--no-gpg-sign`，除非用户在本轮明确授权
- 不动 working tree、不 commit、不 merge、不 rebase、不 checkout
- 远端落后于本地之外的任何状态（behind>0 / 无追踪 / push 失败）→ 停手问，不绕过
- 不替用户 push 到非追踪 remote / 非追踪分支

---

**镜像约束**：本文件和 `.claude/commands/push.md` 正文保持同步——任一侧修改必须在同 commit 内镜像到另一侧。本文件额外带 YAML frontmatter（`name` / `description`），正文（从一级标题 `# /push` 起往下）与 `.claude/commands/push.md` **逐字一致**。
