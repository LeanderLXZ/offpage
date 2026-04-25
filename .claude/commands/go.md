# /go — 方案落盘

按上文讨论执行；某步本次 N/A 就明说"跳过 Step X"。`$ARGUMENTS` 存在即本次改动焦点。

## 0. 环境 & 自动锁定工作位置
项目硬规则：代码 / schema / prompt / docs / ai_context / skill 变更**先进 main**，其他分支通过 `git merge main` 前向同步。`/go` 的 git 交互契约：**Step 0 到 Step 9 中途一次都不问**，只在全部完成后按需问一次是否切回 main。

- `git branch --show-current` / `git status --short` / `pgrep -af persona_extraction` / 看 `works/*/analysis/progress/*.pid`——采信息，**不问**用户
- 按下表自动选工作位置，**不询问**：

| 当前状态 | 自动动作 | 工作位置 |
|---|---|---|
| 已在 main 且工作区 clean | 原地编辑 | 主 checkout |
| 其它（非 main / dirty / 有运行进程） | `git worktree add ../<repo>-main main`；后续编辑、Step 1 PRE log、Step 8 commit 全部走这个 worktree | `../<repo>-main` worktree |

- 选定后打印一行策略声明：`策略：main 原地` 或 `策略：../<repo>-main worktree 隔离`。主 checkout 在 worktree 路径下**全程不被动**（运行中的进程、dirty 工作区都原样保留）
- `git merge` 冲突、`git worktree` 操作失败等异常才停下来让用户决定，不走询问路径

## 1. PRE log 登记（先登记再动手）
**任何代码 / schema / prompt / docs / ai_context / skill 改动之前**，先创建本次改动的 log 文件并写入 PRE 段。这是 `/post-check` 的 intent 基线来源，强制。

- 文件名：`logs/change_logs/{YYYY-MM-DD}_{HHMMSS}_{slug}.md`。HHMMSS 强制，`TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'` 获取；slug 语义化英文短名
- 回显路径给用户（一行 `LOG: logs/change_logs/...md`），便于后续 `/post-check` 显式引用

PRE 段必须包含：

```markdown
# {slug}

- **Started**: {YYYY-MM-DD HH:MM:SS EDT}
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

写完 PRE 段**再进入 Step 2**。中途发现偏离计划 → 在 log 里追加 `## 执行偏差` 段落记新决定，**不默默改**。

## 2. 需求文档 `docs/requirements.md`
更新相关节，含流程图 / 示例。**新增流程图 / 示例仅当现有内容无法覆盖新逻辑时**，避免冗余。**不出现真实书名 / 角色 / 剧情**，用通用占位符；描述只写当前设计，不写"旧 / legacy / 已废弃 / 原为"。同步 `ai_context/requirements.md` + `decisions.md`。

## 3. 核心实现
按讨论改 schema、prompt template、架构代码、配置。对照 `ai_context/conventions.md` 的 Cross-File Alignment 表列出连带文件。

## 4. 轻量测试（仅有代码 / schema 变更时）
Import 检查 + 关键函数 smoke test；schema 改动跑 `jsonschema` 校验。有错立即修。

## 5. 文档对齐
同步 `ai_context/`（仅 durable truth）、`docs/architecture/`、相关 README。再查 `docs/todo_list.md`：新任务登记、已完成条目**清除**、状态变化更新。

## 6. 全库 review
并行扫描（可派 Agent）所有可能涉及的文件：需求、schema、代码、README、architecture、ai_context、prompts、目录结构。检查项：**残留旧逻辑、歧义、跨文件不一致、冲突、遗漏更新、bug、风险**；顺查有无混入真实书名或 legacy 字样。**发现即修**；太大则登记到 `docs/todo_list.md`。

> **进入本步之前，自己先重读 Step 1 创建的 PRE log**——经过前几步的编辑上下文，已经离"原始 intent"有距离；以 PRE 的"结论与决策 / 计划动作清单 / 验证标准"重新校准，再开始扫描。
>
> **派出的每个 sub agent 也必须先重读同一份 PRE log**：把 `LOG:` 路径塞进它的 prompt，并**明示要求它开工前先读完该 log 的 PRE 段**再做事。sub agent 是独立 context，不强制它读 PRE 就只会按 prompt 里的 brief 空转，容易脱离本次 intent。

## 7. POST log 更新（收尾前必填）
更新 **Step 1 创建的同一份 log**，追加 POST 段：

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
- **Finished**: {timestamp}
```

不要新建 log 文件；就地更新 PRE 段那份。

## 8. Git commit + 清理 worktree
Step 0 已经把工作位置锁在 main（主 checkout 或 worktree），**不再询问**切 main。

- `git status` 只剩本次改动；扫禁提路径（`sources/` 原文、数据库、embeddings、caches、真实 user packages）
- message 风格对齐 `git log --oneline -10`；按逻辑单元分 commit
- 提交后 `git status` 确认干净
- **若 Step 0 走了 worktree 路径**：commit 完成后立刻回到主 checkout（无需离开主 checkout 的原分支）并 `git worktree remove --force ../<repo>-main`；commit 已落到 main ref，worktree 目录删除不丢数据

## 9. 同步其他分支 + 末尾单次询问
`git branch --format='%(refname:short)'` 列出所有本地分支；对每个非 main 分支判断是否已含本次 main 改动（`git merge-base --is-ancestor main <branch>` → 0 即已同步）。未同步的分支逐个处理，**中途不询问**：

- 若分支有正在运行的进程（如 `extraction/*`）或未完成工作 → 记录到 `docs/todo_list.md` 推迟，不强推
- 否则 merge 进去：
  - 若该分支 = 当前主 checkout 所在分支（走 worktree 路径时常见 = 原分支）→ 直接 `git merge main`，无需 checkout
  - 否则 → `git checkout <branch> && git merge main`
  - `git checkout` 因 dirty / 冲突失败 → 记录到 `docs/todo_list.md` 跳过
  - `git merge` 冲突 → 停手，让用户决定（流程中唯一允许停下来问用户的情况）

全部遍历完成后打印同步状态表：每个分支（已同步 / 已合并 / 推迟原因）+ 当前 HEAD 所在分支。

**此时——也只有此时——询问用户一次**：
- 若当前 HEAD == main → 无询问，直接结束
- 若当前 HEAD != main → 问一次："所有分支已同步，当前停在 `<branch>`，是否 `git checkout main`？"。同意则切；用户说停留则留在当前分支

---

**镜像约束**：本文件和 `.agents/skills/go/SKILL.md` 正文保持同步——任一侧修改必须在同 commit 内镜像到另一侧。`.agents/skills/go/SKILL.md` 额外带 YAML frontmatter（`name` / `description`），正文（从一级标题 `# /go` 起往下）与本文件**逐字一致**。
