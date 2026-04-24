# go_git_flow_redesign

- **Started**: 2026-04-24 03:54:10 EDT
- **Branch**: master worktree（`/home/leander/Leander/persona-engine-master`），主 checkout 仍在 `extraction/<work_id>`
- **Status**: PRE

## 背景 / 触发

连续几轮 `/go` 后用户发现现行 git 交互分布在 Step 8（commit 时）+
Step 9（每个非-master 分支合并后），每次都得答一次"是否 `git checkout
master`"，累计 N+1 次询问；加上 Step 0 的硬规则（代码 / schema /
prompt / docs / ai_context 变更**先进 master**）在措辞里没显式说明切
master 的时机，导致"编辑先在原分支做、commit 前才切"——流程与原则
不对称，体验也啰嗦。

用户拍板的新 git 流程（原话）：

> 进入 master worktree 修改、在 master 提交 commit（并移除完成的
> worktree），将改动合并/forward 到其他分支，确认已经提交 commit
> 并且各个分支同步，在此之前都不用询问，一切已经完成后，最后再询问
> 用户是否切回 master

翻译成契约：**中途零询问，末尾单次询问**。worktree 从"逃生门"升
格为"默认隔离器"，只要当前不在 master（或当前分支脏 / 有进程），
自动开 worktree，而不问用户。

## 结论与决策

1. **Step 0 自动选路径**：基于 `git branch --show-current` +
   working tree 状态 + `pgrep -af persona_extraction` 自动选两档之一：
   - 已在 master 且 clean → 原地编辑
   - 其它 → `git worktree add ../<repo>-master master`，全程在
     worktree 里工作
   - 路径选定后打印一行策略声明；**不询问用户**
2. **Step 8 直接提交 + 清理 worktree**：commit 就地进 master ref；
   若走了 worktree 路径，commit 完成后自动 `git worktree remove --force`
   清理，回到主 checkout（它仍在原分支，未被动过）；**不询问用户**。
   删掉现行 "若当前不在 master 先询问是否 `git checkout master`" 这句
3. **Step 9 同步遍历 + 末尾单次询问**：遍历非-master 分支做 merge，
   中途不问；`git merge` 冲突或 `git checkout` 失败（dirty 等）→
   登记到 `docs/todo_list.md` / 停手等用户决定（merge 冲突是唯一允许
   在流程中停下来要用户决策的情况）。全部遍历完、同步状态表打印完
   之后，**仅当当前 HEAD != master 时问一次**："当前停在 `<branch>`，
   是否 `git checkout master`？"
4. **worktree 命名**：固定 `../<repo>-master`（当前目录名加
   `-master` 后缀）。简单够用；重跑前检测并清理残留
5. **worktree 清理失败兜底**：`git worktree remove --force`，因为
   commit 已完成，worktree 里不应再有未提交内容
6. **镜像约束**：`.claude/commands/go.md` 与 `.agents/skills/go/SKILL.md`
   正文逐字一致；本次同 commit 内镜像

## 计划动作清单

- file: `.claude/commands/go.md`
  - Step 0 重写：加入"自动选工作位置（master 原地 / master worktree）"
    决策表，删掉"明确说出策略"的模糊要求改为显式策略声明
  - Step 8 重写：删掉"若当前不在 master 先询问是否 `git checkout
    master`"；若走 worktree 路径，commit 完成后自动 `git worktree
    remove --force`；**中途零询问**
  - Step 9 重写：遍历非-master 分支做 merge，**中途不逐分支询问**；
    全部同步完打印状态表；**仅当当前 HEAD != master 时**在末尾问
    一次是否切 master
- file: `.agents/skills/go/SKILL.md`
  - 正文逐字镜像上面三处改动；frontmatter 的 `description` 未变
- file: `ai_context/conventions.md` §Git
  - "Code / schema / prompt / docs / `ai_context/` commits go to
    `master` first; extraction branch syncs via `git merge master`."
    的表述保留，补一句"`/go` uses a master worktree when not already
    on master; `/go` never asks between Steps 1–Step 9, only at the
    very end decides whether to switch back to master"
- file: `ai_context/decisions.md`
  - 新增一条（编号接在现有最大后），记录本次 `/go` git 流程收敛的
    rationale：中途零询问、worktree 默认化、末尾单次询问

## 验证标准

- [ ] `diff <(sed -n '/^# \/go/,$p' .claude/commands/go.md) <(sed -n '/^# \/go/,$p' .agents/skills/go/SKILL.md)` 仅剩镜像约束自引用行一行 diff
- [ ] `grep -n "先询问用户是否 git checkout master\|先询问用户是否 \`git checkout master\`" .claude/commands/go.md .agents/skills/go/SKILL.md` 仅剩 0 次（旧语句完全清除）
- [ ] `grep -n "worktree" .claude/commands/go.md` 至少出现在 Step 0 的自动选路径段落、Step 8 的清理段落
- [ ] Step 9 末尾的询问文本只出现一次（非逐分支问）
- [ ] `ai_context/conventions.md` §Git 段落补充了 `/go` 流程说明
- [ ] `ai_context/decisions.md` 追加一条新编号条目
- [ ] 两份 SKILL 文件的 YAML frontmatter（name / description）未被改动
- [ ] **Dogfood 验证**：本次 `/go` 自己按新流程跑 —— Step 0 自动开
      worktree、Step 8 自动清理、Step 9 末尾仅一次问

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

- `.claude/commands/go.md`
  - Step 0 重写为"环境 & 自动锁定工作位置"：头部声明"Step 0 到 Step 9 中途一次都不问"；用决策表自动区分"master 原地"vs "master worktree 隔离"；策略声明改为显式两选一打印
  - Step 8 重写为"Git commit + 清理 worktree"：删除现行"若当前不在 master 先询问是否 `git checkout master`"整句；走 worktree 路径时 commit 完成后自动 `git worktree remove --force ../<repo>-master`
  - Step 9 重写为"同步其他分支 + 末尾单次询问"：**遍历过程中绝不询问**；全部同步完后打印状态表；**仅当当前 HEAD != master 时**在末尾问一次是否切 master
- `.agents/skills/go/SKILL.md` — Step 0 / 8 / 9 逐字镜像上面三处；frontmatter（name / description）未改动
- `ai_context/conventions.md` §Git — 在既有 6 条之后补第 7 条：明确 `/go` 的 git contract（worktree 默认化 + 中途零询问 + 末尾单次决策）
- `ai_context/decisions.md` §Repository — 新增第 47 条决策，记录 `/go` git 流程从 "N+1 次询问" 收敛到 "末尾单次询问" 的 rationale + 变更定位
- `docs/logs/2026-04-24_035410_go_git_flow_redesign.md` — 本轮 PRE/POST log

### Dogfood 验证（本轮 /go 自己就按新流程跑）

- Step 0：当前在 `extraction/<work_id>`（非 master） → 自动 `git worktree add /home/leander/Leander/persona-engine-master master`（打印策略：`../persona-engine-master worktree 隔离`）
- Step 1-7：全部在 worktree 内完成，主 checkout 的 extraction 分支不被动
- Step 8（进行中）：在 worktree 内 commit 后 `git worktree remove --force` 自动清理
- Step 9：主 checkout 仍在 extraction；直接 `git merge master` 前向同步；末尾询问是否切 master

## 与计划的差异

无。四份目标文件按计划落地，措辞一致，镜像约束仅剩自引用行 diff。

## 验证结果

- [x] `diff <(sed -n '/^# \/go/,$p' ...)` 仅剩镜像约束自引用行一行 diff — 输出确认
- [x] `grep -n "先询问用户是否"` 两份文件均 0 次 — 清除干净
- [x] `grep -n "worktree"` 在 Step 0（决策表 + 策略行 + 异常说明）+ Step 8（清理条目）+ Step 9（同步说明）共 6 处出现
- [x] Step 9 末尾询问文本（"是否 `git checkout master`"）全文件出现 1 次，不再逐分支询问
- [x] `ai_context/conventions.md` §Git 新增 `/go git contract` 一行 — 行 94
- [x] `ai_context/decisions.md` 新增条目第 47（行 133）
- [x] 两份 SKILL 文件 YAML frontmatter 保持原样
- [x] **Dogfood 成功**：本轮 /go 真的在 master worktree 里跑完了 Step 1-7

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 04:02:00 EDT
