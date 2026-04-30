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

## Step 0: 加载 skills 配置

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
`## Sensitive content placeholder rules`（Step 3 / Step 7）、
`## Data contract directories`（Step 5 / Step 7 数据契约扫描；含 JSON Schema / proto / OpenAPI / Pydantic / SQL DDL 等）。

## Step 1: 锁定工作位置（环境探测 + worktree 隔离）
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
- [ ] {如 数据契约校验通过}
- [ ] {如 grep 残留为 0}
- ...

## 执行偏差
（执行中追加；无偏差则写"无"）
```

写完 PRE 段**再进入 Step 3**。中途发现偏离计划 → 在 log 里追加 `## 执行偏差` 段落记新决定，**不默默改**。

## Step 3: 把讨论结论落到文档（内容创作）

把会话里已拍板的方案翻译成文档语言。**这一步只做"写入"**——跨文档对齐校验留给 Step 6，全库 review 留给 Step 7；本步任何"某文件 A 写完发现文件 B 也得改"的连带感觉，**先记进 PRE log 的「执行偏差」段**，留给 Step 6 系统补齐，不要边写边四处串改。

按本次讨论触及的范围筛取（不要无脑全跑）：

- **`docs/requirements.md`**：相关节 / 流程图 / 示例。**新增流程图 / 示例仅当现有内容无法覆盖新逻辑时**，避免冗余
- **`docs/architecture/`**：本次拍板含结构性决策（新模块 / 新接口 / 新状态机 / 调用关系变化）时更新
- **`ai_context/requirements.md`**：与 `docs/requirements.md` 相关节同步
- **`ai_context/decisions.md`**：本次产生的 durable 决策立刻落条目，不要拖到 Step 6 / Step 8
- **`prompts/`**：讨论结论包含 prompt 行为契约 / 模板变化时更新
- **`README.md`**：仅当目录 / 入口 / 启动方式有变化

写作约束：

- **按 skills_config.md `## Sensitive content placeholder rules` 用占位符替换真实内容**（该节留空则跳过该项扫描）
- 描述只写当前设计，不写"旧 / legacy / 已废弃 / 原为"

## Step 4: 实现代码 / schema / prompt / 配置
按讨论改 schema、prompt template、架构代码、配置。**先确认 PRE log「验证标准」段已有 ≥ 1 条具体可执行项**（如 `import 无报错` / `grep 残留 = 0` / `smoke X 全过`；非"做对了就行"这类含糊）；含糊 → 立刻补具体的再继续。对照 `ai_context/conventions.md` 的 Cross-File Alignment 表列出连带文件（该表不存在则跳过本项，仅按本次改动直觉判断）。

## Step 5: Smoke 测试 + 数据契约校验（仅当代码 / 数据契约改动时）
Import 检查 + 关键函数 smoke test；如本次改动触及 skills_config.md `## Data contract directories` 列出的目录（schema / proto / openapi / pydantic / SQL DDL 等数据契约），按项目对应的校验工具跑一次（例：JSON Schema → `jsonschema` / `ajv`；OpenAPI → `openapi-spec-validator` / `redocly lint`；proto → `protoc --lint_out`；pydantic → 模型 import + `model_rebuild()`；SQL DDL → migration dry-run）。该节 `(none)` 时跳过本步契约校验。有错立即修。

## Step 6: 跨文档对齐 + todo_list 维护

到这里 Step 3 / 4 / 5 已分别把内容写进文档与代码。**本步只做"对齐校验 + 维护收尾"**，不做内容创作——若发现某项需要重新写一段需求 / 架构描述，回到 Step 3 重写而不是在本步硬塞。

**跨文档对齐**：

- 对照 `ai_context/conventions.md` 的 Cross-File Alignment 表（不存在则按 Step 3 / Step 4 实际触及的文件直觉判断），核对 schema / prompt / code / docs / ai_context / README 在以下维度是否一致：
  - 字段名 / 参数 / 返回值 / 状态值 / 错误码
  - 流程描述 / 状态机 / 门控时序
  - 术语 / 概念命名
- 发现某文件本应同步却没动 → **查漏补缺**式补上；改动量小（一两行同步）就地修，改动量大（要重写整段需求 / 架构描述）→ 回 Step 3 重做

**ai_context durable 维护**：

- `ai_context/current_status.md`：当前状态行是否需要更新
- `ai_context/next_steps.md`：本次产生的新方向 / 阻塞是否需要登记
- `ai_context/handoff.md`：是否需要给下一会话留一句话

**todo_list 维护**：

- `docs/todo_list.md`：本次完成的条目**整条移到 `docs/todo_list_archived.md`** 的 `## Completed` 段（瘦身：标题 + 完成形式 + 1 行摘要 + 本次 log 链接）；状态变化更新
- 任务移段 / 增改后**同步刷新顶部 `## Index` 段**（规则在 `docs/todo_list.md` 顶部"Index maintenance"小节）。`/todo` skill 只读索引，不刷新就会给出过期信息
- ⚠️ 仅维护"本次改动直接产生 / 完成"的条目；Step 7 review 期间发现的新问题**不在本步登记**，按 Step 7 的处理规则走

## Step 7: 全库多线 review（并行）

并行扫描全仓与本次改动相关 / 受牵连的文件，**至少四条线，可派 sub-agent 并行**；改动面小则单线串跑。

**四条线**（每条都先重读 PRE log 再扫描）：

1. **规范线**：`ai_context/` / `docs/` / skills_config.md `## Data contract directories` 列出的目录（`(none)` 时跳过该节扫描）/ `prompts/` —— 描述 vs. 本次改动是否一致，有无残留旧描述 / 旧字段 / 旧流程；顺查有无违反 skills_config.md `## Sensitive content placeholder rules` 的真实内容、`旧 / legacy / 已废弃 / 原为` 字样
2. **实现线**：本次改过的代码 + 其上下游（调用方 / 被调用方 / 导入方）—— 字段名 / 参数 / 返回值 / 状态机 / 门控 / 异常路径是否连贯，import 是否还能跑
3. **风险线**：本次改过的代码 + 受其牵连的相关代码（调用方 / 被调用方 / 共享状态 / 共享数据流）—— 边界条件、空值 / None、异常路径、并发、重试 / 回滚、错误处理是否藏 bug；新行为是否引入数据丢失 / 安全口子 / 性能回退；状态机 / 门控 / 不变量是否有漏覆盖分支。**与实现线区分**：实现线问"还连得上吗"（签名 / import 一致性），风险线问"做的事对吗"（语义正确性 + 失败模式）
4. **结构线**：README / 目录结构 / 已提交样例产物 / artifact 目录 是否与本次变化对齐；改了文件名 / 目录结构 → 追查所有引用点

**Findings 处理**（**重要**：本步发现的问题不要直接写进 `docs/todo_list.md`）：

- **一行能修的小问题**（错别字、漏占位符、漏一个 import、明显笔误、悬挂引用一处）→ **发现即修**，不留尾
- **大问题 / 跨范围 / 需要重新讨论 / 不在本次 intent 范围内的发现** → **不自己写进 `docs/todo_list.md`**；在对话里列一段「**建议登记到 todo_list**」清单，每条带：文件 + 行号、问题摘要、建议归到哪个分段。等用户拍板后由 `/todo-add` 或下一轮 `/go` 落条目——避免本次 intent 之外的发现污染 todo_list 历史

> **进入本步之前，自己先重读 Step 2 创建的 PRE log**——经过前几步的编辑上下文，已经离"原始 intent"有距离；以 PRE 的"结论与决策 / 计划动作清单 / 验证标准"重新校准，再开始扫描。
>
> **派出的每个 sub agent 也必须先重读同一份 PRE log**：把 `LOG:` 路径塞进它的 prompt，并**明示要求它开工前先读完该 log 的 PRE 段**再做事。sub agent 是独立 context，不强制它读 PRE 就只会按 prompt 里的 brief 空转，容易脱离本次 intent。

## Step 8: POST log 收尾
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
