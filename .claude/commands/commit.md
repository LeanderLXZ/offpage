# /commit — 快速确认并提交当前改动

对当前 working tree 做一次轻量校验，确认改动有效、分支正确、追踪状态无误后 commit；完成后询问是否把改动 forward / merge 到其他分支。**不做全仓 review、不动 ai_context / docs 对齐**（那是 `/go` 的事）。

## Progress reporting

下方流程分为 `## Step 0:` ~ `## Step 5:`（前置一段 `## $ARGUMENTS 解析` 是参数解析，不算正式 step）。

**进入 Step 0 之前**：调用 **<进度工具>** 把 Step 0 ~ Step 5 全部预登记（每个 step 一条，`content` 用 `Step N: <子段标题>`，`status` 全为 `pending`；`$ARGUMENTS` 解析不计入）。这是硬性要求，**不调 <进度工具> 不许往下走**。

每进入一个 step：调 **<进度工具>** 把当前 step 改 `in_progress`（同一次调用里把上一个 step 标 `completed`），然后做实际工作。**step 跨越时不要漏调**。进度由 <进度工具> 的 UI 直接显示，**对话里不再打 `[/commit] Step N: ...` 之类的进度行**。

跳过某 step：调 **<进度工具>** 把对应条目直接标 `completed`，并在对话里打一行 `Step N 跳过（理由：…）`——"理由"是 UI 缺失的信息，保留这一行；不要静默略过。

最后一步完成：调 **<进度工具>** 把最后一条标 `completed`。

**<进度工具> 解析**：Claude → `TodoWrite`（界面显示为 "Update Todos"）；Codex → `update_plan`。语义对齐：预登记 + 切状态 + 标完成。

## `$ARGUMENTS` 解析

`$ARGUMENTS` 同时承担两个角色，按以下规则解析：

1. **sync 触发词**（不区分大小写）：`同步` / `sync` / `auto-sync` / `--sync`。
   出现任意一个（作为独立词或单独 token）→ 进入 **auto-sync 模式**：跳过
   Step 5 的询问，直接把本次 commit forward 到所有未同步、当前没有运行
   进程、且非 dirty 的本地分支
2. **其余文本**：作为 commit message 的提示 / 主题（参见 Step 4）

解析时把 sync 触发词从原始 `$ARGUMENTS` 中**剥离**，剩余部分才是消息提示。
都没有时（`$ARGUMENTS` 为空）→ 普通模式 + 由 diff 自动归纳消息。

## Step 0: Load skills config

`Read` `ai_context/skills_config.md`。

- 文件不存在 / 某节标题缺失 → fail loudly：打印缺失项 + 提示按 plugin 模板补全，停手
- 某节内容 `(none)` 或留空 → 跳过该节相关步骤（视为本项目无此项）
- 某节列了具体路径但路径不存在 → fail loudly：提示该节漂移到不存在路径，停手等用户修

后续步骤出现 "skills_config.md `## XX`" 时引用本配置。本 skill 用到：
`## Do-not-commit paths`（Step 3）、`## Background processes`（Step 5
forward 进程检测）、`## Protected branch prefixes`（Step 5 区分长跑分支）。

## Step 1: 改动有效性

- `git status` + `git diff --stat` 看 working tree 与 index
- 若完全没有改动：打印"无改动"并停手
- 扫改动列表，判断是否值得独立 commit（不是空白 / 误保存 / 临时 debug 打印）；有可疑 → 先问用户

## Step 2: 分支正确性

- `git branch --show-current` 打印当前分支
- 按 skills_config.md `## Main branch policy` 判断当前分支与改动性质是否匹配（一般规则：可作为真相基线的变更——代码 / schema / prompt / docs / ai_context / skill ——应落在主分支；功能实验 / 长跑任务在对应 feature 分支）
- 当前分支与改动性质不匹配 → 先停手报告，等用户决定（切分支、worktree、或坚持当前分支）

## Step 3: 追踪状态

- 扫禁提路径：按 skills_config.md `## Do-not-commit paths` 列表 +（`.gitignore` + `ai_context/conventions.md`）兜底
- `git ls-files --others --exclude-standard` 看未跟踪文件，判断是否应该一并加入 / 加入 .gitignore / 留着
- 大文件（>1MB）或二进制单独列出，请用户确认是否入库
- 任一项可疑 → 停手问用户，不要擅自 `git add -A`

## Step 4: Commit

- 按逻辑单元分 commit（若单次改动跨多个独立主题）；一次别塞太多
- message 风格对照 `git log --oneline -10`，保持仓库惯例（中英文 / prefix / 动词时态）
- 解析后剩余的 `$ARGUMENTS` 文本（已剥离 sync 触发词）存在则以此为主题扩写；否则根据 diff 归纳
- 执行 `git add <具体文件>` + `git commit`（**不用 `git add -A` / `git add .`**，避免误入敏感文件）
- commit 后 `git status` 确认干净

## Step 5: Forward / Merge

- `git branch --format='%(refname:short)'` 列出所有本地分支
- 对每个非当前分支，用 `git merge-base --is-ancestor <当前分支> <branch>` 判断是否已含本次 commit；并按 skills_config.md `## Background processes` 探测该分支是否有运行中进程（pgrep 模式 + 进程产物路径）/ 是否 dirty（`git -C <path> status` 等价手段）。`## Background processes` 留空时视为"无进程"
- 输出一个简表：`{branch} | 已同步 / 未同步 | 状态（有进程 / 干净 / dirty）`

**普通模式**（默认）：

- **问用户**：是否需要把本次 commit forward / merge 到未同步的分支？列出候选分支，等回答；不要擅自切分支合并
- 用户指定要同步的分支后：`git checkout <branch> && git merge <原分支>`；冲突先停手，让用户决定；合并完回原分支

**auto-sync 模式**（`$ARGUMENTS` 含 sync 触发词）：

- **跳过询问**，直接把本次 commit 同步到所有满足以下全部条件的分支：
  - 未同步（`git merge-base --is-ancestor` 返回非 0）
  - 没有运行中进程（按 skills_config.md `## Background processes` 检测；`## Protected branch prefixes` 列出的分支额外谨慎判断）
  - 工作树干净
- 对每个候选分支：`git checkout <branch> && git merge <原分支>`；合并完成后继续下一个；末尾回到原分支
- 跳过的分支（有进程 / dirty / 合并冲突）→ 各自打一行说明，**不停手问**，继续处理后续分支
- 合并冲突仍是唯一允许停手的情况——冲突分支需要用户人工介入，但其他干净分支应已先合完

打印同步结果表：每个非当前分支（已同步 / 已合并 / 跳过原因 / 冲突待处理）+ 当前 HEAD 所在分支。

## 约束

- 只提交本次 working tree 改动；不做 ai_context / docs / README 对齐（那是 `/go` 范围）
- 不 `git push`、不 `--force`、不 `--amend`（除非用户明确要求）
- 不 `git add -A`；逐文件加
- 发现可疑（禁提路径、巨型 diff、分支不对、有未解决冲突）→ 停手问，不绕过
- forward / merge 在普通模式下必须经用户确认；**auto-sync 模式**（`$ARGUMENTS` 含 `同步` / `sync` / `auto-sync` / `--sync`）才允许跳过询问直接同步，仍跳过有进程 / dirty / 冲突的分支
- auto-sync 仅作用于本地分支；**永不 push**

---

**镜像约束**：本文件和 `.claude/commands/commit.md` 正文保持同步——任一侧修改必须在同 commit 内镜像到另一侧。本文件额外带 YAML frontmatter（`name` / `description`），正文（从一级标题 `# /commit` 起往下）与 `.claude/commands/commit.md` **逐字一致**。
