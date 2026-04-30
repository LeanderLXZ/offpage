# skills_step_progress_reporting

- **Started**: 2026-04-30 00:19:44 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

用户要求所有 skills：(a) 加 Step 0 / Step 1 / Step 2 ... 步骤标号；
(b) skill 运行过程中每个 step 都打印当前进度让用户看到。

## 结论与决策

按"不过度工程"原则，最小动作：

- 已有数字编号的 skill（`## 0.` / `## 1.` / `### 1.` 等）→ 统一改成
  `## Step N: 标题` 格式（h2 + 「Step」前缀，规避 markdown 渲染时
  歧义）
- 已经分得很细但属定义型而非执行序列的小节（如 full-review 的
  「目标 / 工作方式 / 重点检查项 / 输出格式」）保留原样，仅 `## 0.
  Load skills config` 改为 `## Step 0: Load skills config`
- 每份 skill 顶部加 1 段「Progress reporting」规则：进入 step 时
  打印一行 `[<skill>] Step N: <标题>`，最后一步结束打印
  `[<skill>] done`
- plan.md 没有执行序列（只是"只讨论模式锁"）→ 顶部加 1 行进入
  / 退出信号即可，不强加 step 编号
- 镜像约束：`.claude/commands/*.md`（canonical）+ `.agents/skills/*/SKILL.md`
  正文必须逐字一致（仅 SKILL.md 多 YAML frontmatter）；todo 别名同
  步 4 文件

## 计划动作清单

每对文件（`.claude/commands/<skill>.md` + `.agents/skills/<skill>/SKILL.md`）
做相同改动：

- file: `check-review` → 顶部加 Progress reporting 段；`## 0.` → `## Step 0:` 等
- file: `commit` → 顶部加 Progress reporting；`## 0./1./.../5.` → `## Step 0/1/.../5:`
- file: `full-review` → 顶部加 Progress reporting；仅 `## 0.` → `## Step 0:`，其它定义型小节不动
- file: `go` → 顶部加 Progress reporting；`## 0./.../10.` → `## Step 0/.../10:`
- file: `monitor` → 顶部加 Progress reporting；`## 0./.../5.` → `## Step 0/.../5:`
- file: `post-check` → 顶部加 Progress reporting；`## 0./1./1.5/2./.../7.` → `## Step 0/1/1.5/2/.../7:`
- file: `plan` → 顶部加 Progress signal（一句进入 + 一句退出）；不强加 step
- file: `todo-add` → 顶部加 Progress reporting；`### 1./.../7.` → `## Step 1/.../7:`（h3 提升到 h2）
- file: `todo-list` (+ alias `todo`) → 顶部加 Progress reporting；`### 1./.../4.` → `## Step 1/.../4:`

## 验证标准

- [ ] grep `^## Step ` 在每个 .claude/commands/ 文件 → ≥ 1 命中
  （除 plan.md 例外）
- [ ] grep `Progress reporting\|Progress signal` 在每个 .claude/commands/
  文件 → 1 命中
- [ ] grep `^## [0-9]+\.` 在 .claude/commands/ → 0 命中（确认旧编号
  全部转换为 `## Step N:`）
- [ ] `.claude/commands/<x>.md` 与 `.agents/skills/<x>/SKILL.md`
  正文 diff（去 frontmatter 后）= 0
- [ ] `.claude/commands/todo.md` 与 `.claude/commands/todo-list.md` diff = 0；
  `.agents/skills/todo/SKILL.md` 与 `.agents/skills/todo-list/SKILL.md`
  去 frontmatter 后 diff = 0

## 执行偏差

- 2026-04-30 EDT：本轮用户重新下指令时**显式收窄范围到 4 个 skill**：`/go` `/post-check` `/commit` `/todo-add`。原计划里的 `check-review` `full-review` `monitor` `plan` `todo-list` 本轮**不动**，等用户后续单独要求再处理。理由：
  - 用户原话只列了这 4 个 skill；
  - 跨文件引用都是文本里的 "Step N" 字样，不依赖小节标题样式，收窄不会破坏一致性；
  - 已未改的 skill 仍维持 `## N.` 标题，文本里出现的 "Step N" 引用是描述性而非结构性，不会因此失效。
- 同步收窄「计划动作清单」与「验证标准」：仅这 4 对文件（`.claude/commands/<x>.md` + `.agents/skills/<x>/SKILL.md`）参与 grep 检查；其余 skill 的 `## N.` 不视作残留。
- Step 7 review 顺手发现 `ai_context/decisions.md:188` entry 47 引用的 `/go` step 编号（"Steps 1–8" / "Step 9 merges main" / "→ Step 0 / 8 / 9"）与当前 11 步流程已偏离（worktree 实际持续到 Step 9，分支同步是 Step 10）。这是**本次改动之前就存在**的漂移、与 step 标号样式无关，**本次不顺手修**以保持 PR 范围聚焦；建议用户后续单独提出修正。

## 已落地变更

8 个文件每对升级为「顶部加 Progress reporting 段 + step 小节标题升格为 `## Step N:`」：

- `.claude/commands/go.md` + `.agents/skills/go/SKILL.md`：
  - 顶部新增 `## Progress reporting` 段（说明进入每个 step 时的进度行格式）
  - `## 0.` ~ `## 10.` → `## Step 0:` ~ `## Step 10:`（共 11 个标题）
  - 镜像 diff = 0
- `.claude/commands/post-check.md` + `.agents/skills/post-check/SKILL.md`：
  - 顶部 `## Progress reporting` 段
  - `## 0./1./1.5/2./3./4./5./6./7.` → `## Step 0:/1:/1.5:/2:/3:/4:/5:/6:/7:`（含子 step 1.5）
  - 镜像 diff = 0
- `.claude/commands/commit.md` + `.agents/skills/commit/SKILL.md`：
  - 顶部 `## Progress reporting` 段（注：参数解析段 `## $ARGUMENTS 解析` 不算 step）
  - `## 0.` ~ `## 5.` → `## Step 0:` ~ `## Step 5:`
  - 镜像 diff = 0
- `.claude/commands/todo-add.md` + `.agents/skills/todo-add/SKILL.md`：
  - 顶部 `## Progress reporting` 段（描述：`## Step 1:` ~ `## Step 7:`）
  - 删除空容器段 `## 步骤`，把 `### 1.` ~ `### 7.` 升 h3 → h2 的 `## Step 1:` ~ `## Step 7:`
  - 镜像 diff = 0

PRE log（本文件）追加「执行偏差」 + 「已落地变更」 + 「与计划的差异」 + 「验证结果」 + 「Completed」段。

## 与计划的差异

- 范围收窄：原 PRE 计划 8+ 个 skill，实际只动 4 个（详见执行偏差第一条）。
- 未变更项：未触及 `check-review` `full-review` `monitor` `plan` `todo-list`，未触及 `decisions.md` 中的旧 step 编号引用。

## 验证结果

- [x] grep `^## Step ` 在 4 个 commands 文件 + 4 个 SKILL 文件 → 各文件分别 6/7/9/11 命中（commit/todo-add/post-check/go），均 ≥ 1 ✅
- [x] grep `^## Progress reporting$` 在 4 个 commands + 4 个 SKILL → 每文件 1 命中 ✅
- [x] grep `^## [0-9]+\. ` 在 4 个 commands + 4 个 SKILL → 0 命中（旧编号已全部转换）✅
- [x] 4 对 `.claude/commands/<x>.md` ↔ `.agents/skills/<x>/SKILL.md` 去 frontmatter 后正文 diff = 0（4 对均 ✅）
- [x] 4 个 skill 内文本对自身 step 的引用（如 `Step 1.5` `Step 5` `Step 7`）均能在该 skill 的 `## Step N:` 标题中找到对应 ✅
- [x] 跨 skill 引用（如 post-check 引用 `/go Step 1` `/go Step 7`、ai_context/skills_config.md 引用 `/commit Step 5` `/go Step 1 / Step 10`、full-review/SKILL.md 引用 `/go Step 1`）目标 step 仍存在 ✅

## Completed

- **Status**: DONE
- **Finished**: 2026-04-30 00:43:50 EDT
