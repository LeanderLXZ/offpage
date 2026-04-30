# /go — 方案落盘

按上文讨论执行；某步本次 N/A 就明说"跳过 Step X"。`$ARGUMENTS` 存在即本次改动焦点。

## Progress reporting

下方流程分为 `## Step 0:` ~ `## Step 10:`。

**进入 Step 0 之前**：调用 **<进度工具>** 把 Step 0 ~ Step 10 全部预登记（每个 step 一条，`content` 用 `Step N: <子段标题>`，`status` 全为 `pending`）。这是硬性要求，**不调 <进度工具> 不许往下走**。

每进入一个 step：调 **<进度工具>** 把当前 step 改 `in_progress`（同一次调用里把上一个 step 标 `completed`），然后做实际工作。**step 跨越时不要漏调**。进度由 <进度工具> 的 UI 直接显示，**对话里不再打 `[/go] Step N: ...` 之类的进度行**。

跳过某 step：调 **<进度工具>** 把对应条目直接标 `completed`，并在对话里打一行 `Step N 跳过（理由：…）`——"理由"是 UI 缺失的信息，保留这一行；不要静默略过。

最后一步完成：调 **<进度工具>** 把最后一条标 `completed`。

**子任务（可选，按需启用）**：当某个 step 内部工作复杂、明显由多个独立小任务组成（如 Step 4 同批改 schema / prompt / code / config 多块）时，进入该 step 时可在 <进度工具> 里把 `Step N: <title>` **展开**为若干条 `Step Na: <子标题>` / `Step Nb: …` / `Step Nc: …`（用字母序，同次调用替换原 `Step N` 条目），按子任务推进切 `in_progress` / `completed`。**只展开当前正在做的 step 的子任务**——其他 step 保持单条 `Step M: <title>` 折叠形态，不展开。当前 step 的子任务全部 `completed` 后，**进入下一 step 时把这些子任务折回成一条** `Step N: <title>` `status=completed`，再展开下一 step（如有需要）。这样 UI 里始终是"当前 step 细粒度 + 其他 step 折叠粗粒度"。

简单 step 不必启用——直接按 `Step N: <title>` 切状态即可。子任务编号用同一字母序，**不要嵌套二层**（不要 `4a-1` / `4a-2`）。

**<进度工具> 解析**：Claude → `TodoWrite`（界面显示为 "Update Todos"）；Codex → `update_plan`。语义对齐：预登记 + 切状态 + 标完成（含子任务展开 / 折回）。

## Step 0: Load skills config

`Read` `ai_context/skills_config.md`。

- 文件不存在 / 某节标题缺失 → fail loudly：打印缺失项 + 提示按 plugin 模板补全，停手
- 某节内容 `(none)` 或留空 → 跳过该节相关步骤（视为本项目无此项）
- 某节列了具体路径但路径不存在 → fail loudly：提示该节漂移到不存在路径，停手等用户修

后续步骤出现 "skills_config.md `## XX`" 时引用本配置。本 skill 用到：
`## Main branch policy`（Step 1 / Step 10 工作流硬规则）、
`## Background processes`（Step 1 自动锁定 / Step 10 同步判断）、
`## Protected branch prefixes`（Step 10 同步判断）、
`## Do-not-commit paths`（Step 9）、
`## Timezone`（Step 2 / Step 8 时间戳）、
`## Sensitive content placeholder rules`（Step 3 / Step 7）。

## Step 1: 环境 & 自动锁定工作位置
按 skills_config.md `## Main branch policy` 锁定主分支名与变更同步方向。`/go` 的 git 交互契约：**Step 1 到 Step 10 中途一次都不问**，只在全部完成后按需问一次是否切回主分支。

- `git branch --show-current` / `git status --short` / 按 skills_config.md `## Background processes` 探测（pgrep 模式 + 进程产物路径；该节留空则跳过进程检测）——采信息，**不问**用户
- 按下表自动选工作位置，**不询问**：

下表中的 `<MAIN>` = skills_config.md `## Main branch policy` 的"Main branch"字段。

| 当前状态 | 自动动作 | 工作位置 |
|---|---|---|
| 已在 `<MAIN>` 且工作区 clean | 原地编辑 | 主 checkout |
| 其它（非 `<MAIN>` / dirty / 有运行进程） | `git worktree add ../<repo>-<MAIN> <MAIN>`；后续编辑、Step 2 PRE log、Step 9 commit 全部走这个 worktree | `../<repo>-<MAIN>` worktree |

- 选定后打印一行策略声明：`策略：<MAIN> 原地` 或 `策略：../<repo>-<MAIN> worktree 隔离`。主 checkout 在 worktree 路径下**全程不被动**（运行中的进程、dirty 工作区都原样保留）
- `git merge` 冲突、`git worktree` 操作失败等异常才停下来让用户决定，不走询问路径

## Step 2: PRE log 登记（先登记再动手）
**任何代码 / schema / prompt / docs / ai_context / skill 改动之前**，先创建本次改动的 log 文件并写入 PRE 段。这是 `/post-check` 的 intent 基线来源，强制。

- 文件名：`logs/change_logs/{YYYY-MM-DD}_{HHMMSS}_{slug}.md`。HHMMSS 强制，按 skills_config.md `## Timezone` 的命令模板执行（该节缺失则 fallback 到 `date '+%Y-%m-%d_%H%M%S'` 系统时区）；slug 语义化英文短名
- 回显路径给用户（一行 `LOG: logs/change_logs/...md`），便于后续 `/post-check` 显式引用

PRE 段必须包含：

```markdown
# {slug}

- **Started**: {YYYY-MM-DD HH:MM:SS} {时区缩写：按 skills_config.md `## Timezone` 的设定}
- **Branch**: {/go 进入时的工作分支}
- **Status**: PRE

## 背景 / 触发
{会话上下文、用户原始需求、上游讨论链条摘要}

## 结论与决策
{/go 进来时已拍板的方案：选了哪个方向、改什么、不改什么}

## 计划动作清单
- file: {path} → {改动要点}
- ...

## 验证标准
- [ ] {如 Import 无报错}
- [ ] {如 jsonschema 通过}
- [ ] {如 grep 残留为 0}
- ...

## 执行偏差
（执行中追加；无偏差则写"无"）
```

写完 PRE 段**再进入 Step 3**。中途发现偏离计划 → 在 log 里追加 `## 执行偏差` 段落记新决定，**不默默改**。

## Step 3: 需求文档 `docs/requirements.md`
更新相关节，含流程图 / 示例。**新增流程图 / 示例仅当现有内容无法覆盖新逻辑时**，避免冗余。**按 skills_config.md `## Sensitive content placeholder rules` 用占位符替换真实内容**（该节留空则跳过该项扫描）；描述只写当前设计，不写"旧 / legacy / 已废弃 / 原为"。同步 `ai_context/requirements.md` + `decisions.md`。

## Step 4: 核心实现
按讨论改 schema、prompt template、架构代码、配置。**先确认 PRE log「验证标准」段已有 ≥ 1 条具体可执行项**（如 `import 无报错` / `grep 残留 = 0` / `smoke X 全过`；非"做对了就行"这类含糊）；含糊 → 立刻补具体的再继续。对照 `ai_context/conventions.md` 的 Cross-File Alignment 表列出连带文件（该表不存在则跳过本项，仅按本次改动直觉判断）。

## Step 5: 轻量测试（仅有代码 / schema 变更时）
Import 检查 + 关键函数 smoke test；schema 改动跑 `jsonschema` 校验。有错立即修。

## Step 6: 文档对齐
同步 `ai_context/`（仅 durable truth）、`docs/architecture/`、相关 README。再查 `docs/todo_list.md`：新任务登记到合适分段、本次涉及的已完成条目**整条移到 `docs/todo_list_archived.md`** 的 `## Completed` 段（瘦身：标题 + 完成形式 + 1 行摘要 + 本次 log 链接）、状态变化更新；任务移段 / 增改后**同步刷新顶部 `## Index` 段**（规则在 `docs/todo_list.md` 顶部"Index maintenance"小节）。`/todo` skill 只读索引，不刷新就会给出过期信息。

## Step 7: 全库 review
并行扫描（可派 Agent）所有可能涉及的文件：需求、schema、代码、README、architecture、ai_context、prompts、目录结构。检查项：**残留旧逻辑、歧义、跨文件不一致、冲突、遗漏更新、bug、风险**；顺查有无违反 skills_config.md `## Sensitive content placeholder rules` 的内容或 legacy 字样。**发现即修**；太大则登记到 `docs/todo_list.md`。

> **进入本步之前，自己先重读 Step 2 创建的 PRE log**——经过前几步的编辑上下文，已经离"原始 intent"有距离；以 PRE 的"结论与决策 / 计划动作清单 / 验证标准"重新校准，再开始扫描。
>
> **派出的每个 sub agent 也必须先重读同一份 PRE log**：把 `LOG:` 路径塞进它的 prompt，并**明示要求它开工前先读完该 log 的 PRE 段**再做事。sub agent 是独立 context，不强制它读 PRE 就只会按 prompt 里的 brief 空转，容易脱离本次 intent。

## Step 8: POST log 更新（收尾前必填）
更新 **Step 2 创建的同一份 log**，追加 POST 段：

```markdown
<!-- POST 阶段填写 -->

## 已落地变更
{实际改了哪些文件、每份改了什么，文件 + 行号或 diff 摘要}

## 与计划的差异
{对比 PRE 的"计划动作清单"，新增 / 删除 / 修改了什么；无则写"无"}

## 验证结果
- [x] {PRE 验证标准 1} — {输出摘要}
- [ ] {PRE 验证标准 2} — {失败原因}
- ...

## Completed
- **Status**: DONE | BLOCKED
- **Finished**: {timestamp，按 skills_config.md `## Timezone` 的命令模板取，与 PRE Started 同时区}
```

不要新建 log 文件；就地更新 PRE 段那份。

## Step 9: Git commit + 清理 worktree
Step 1 已经把工作位置锁在主分支（主 checkout 或 worktree），**不再询问**切主分支。

- `git status` 只剩本次改动；按 skills_config.md `## Do-not-commit paths` 列表 +（`.gitignore` + `ai_context/conventions.md`）兜底扫描
- message 风格对齐 `git log --oneline -10`；按逻辑单元分 commit
- 提交后 `git status` 确认干净
- **若 Step 1 走了 worktree 路径**：commit 完成后立刻回到主 checkout（无需离开主 checkout 的原分支）并 `git worktree remove --force ../<repo>-<MAIN>`（`<MAIN>` = skills_config.md `## Main branch policy` 主分支字段）；commit 已落到主分支 ref，worktree 目录删除不丢数据

## Step 10: 同步其他分支 + 末尾单次询问
`<MAIN>` = skills_config.md `## Main branch policy` 的"Main branch"字段。`git branch --format='%(refname:short)'` 列出所有本地分支；对每个非 `<MAIN>` 分支判断是否已含本次 `<MAIN>` 改动（`git merge-base --is-ancestor <MAIN> <branch>` → 0 即已同步）。未同步的分支逐个处理，**中途不询问**：

- 若分支匹配 skills_config.md `## Protected branch prefixes` 的前缀且按 `## Background processes` 检测有运行进程，或分支有未完成工作 → 记录到 `docs/todo_list.md` 推迟，不强推
- 否则 merge 进去：
  - 若该分支 = 当前主 checkout 所在分支（走 worktree 路径时常见 = 原分支）→ 直接 `git merge <MAIN>`，无需 checkout
  - 否则 → `git checkout <branch> && git merge <MAIN>`
  - `git checkout` 因 dirty / 冲突失败 → 记录到 `docs/todo_list.md` 跳过
  - `git merge` 冲突 → 停手，让用户决定（流程中唯一允许停下来问用户的情况）

全部遍历完成后打印同步状态表：每个分支（已同步 / 已合并 / 推迟原因）+ 当前 HEAD 所在分支。

**此时——也只有此时——询问用户一次**：
- 若当前 HEAD == `<MAIN>` → 无询问，直接结束
- 若当前 HEAD != `<MAIN>` → 问一次："所有分支已同步，当前停在 `<branch>`，是否 `git checkout <MAIN>`？"。同意则切；用户说停留则留在当前分支

---

**镜像约束**：本文件和 `.claude/commands/go.md` 正文保持同步——任一侧修改必须在同 commit 内镜像到另一侧。本文件额外带 YAML frontmatter（`name` / `description`），正文（从一级标题 `# /go` 起往下）与 `.claude/commands/go.md` **逐字一致**。
