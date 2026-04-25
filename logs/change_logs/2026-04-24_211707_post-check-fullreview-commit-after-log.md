# post-check-fullreview-commit-after-log

- **Started**: 2026-04-24 21:17:07 EDT
- **Branch**: master（worktree `../persona-engine-master`，原仓 dirty 并停留在 `extraction/<work_id>`，包含上一次 /post-check 未提交的 log 回写）
- **Status**: PRE

## 背景 / 触发

用户反馈：`/post-check` 与 `/full-review` 两条 skill 在执行过程中都会写 log
文件（前者追加 log 摘要、后者新建 review report），但当前 SKILL 文档明确说
"不提交"。结果是 skill 跑完后留下脏工作区，污染下一轮 `/go` 的 Step 0
自动锁定逻辑（`/go` 检测到 dirty → 强制走 worktree 路径），形成"上一轮的 log
回写在干扰下一轮的开发"的副作用。

本会话上一次 `/post-check` 也复现了这个问题：
`logs/change_logs/2026-04-24_204846_drop-digest-catalog-length-item-bounds.md`
被追加了 `<!-- /post-check 填写 -->` 段，但从未 commit。这正是用户指出"要不然
会制造脏目录"的现实证据。

## 结论与决策

**新增规则**：`/post-check` 与 `/full-review` 写完 log / report 后必须**立即
commit**该写入的文件，且仅 stage 这一份文件，不携带其他 dirty 文件。

镜像 4 份文件需要同步修改（每对各 2 份）：

- `/post-check`：
  - `.claude/commands/post-check.md`
  - `.agents/skills/post-check/SKILL.md`（多 frontmatter，正文保持逐字一致）
- `/full-review`：
  - `.claude/commands/full-review.md`
  - `.agents/skills/full-review/SKILL.md`（多 frontmatter，正文保持逐字一致）

具体落点：

- `/post-check` Step 5：在 log 摘要 markdown 模板之后追加"立即 commit"段
- `/post-check` "约束"节：把 "不提交" 字样改为 "唯一允许的 commit 是 Step 5
  那份 log 摘要"
- `/full-review` "结果归档（必做）"节：在 review report 写入后追加"立即
  commit" 段
- `/full-review` "审计要求" 节：把 "不要修改文件" 改为 "除结果归档那份
  review report 之外不要修改 / 提交其他文件"

commit 的归属选择：log / review report 文件随该 skill 当下运行的分支走
（通常 extraction 分支），**不强制走 master worktree**。理由：

- 这两类文件本身是事后总结性质，不属于"代码 / schema / prompt / ai_context"
  这类需要先进 master 的 durable 真理
- /post-check 的 log 已经由 /go 的 worktree 路径在 master 上首次创建并
  merge 进 extraction，回写阶段附加的内容随 extraction 走没有信息倒挂
- review report 由 /full-review 全新创建，归 review 当时的快照分支即可

参照已有先例：commit `3b22e80 log(world_stage_snapshot_bounds_cleanup):
/post-check 复查结论回写 REVIEWED-FAIL`。

## 计划动作清单

- file: `.claude/commands/post-check.md` → Step 5 末尾追加 commit 段；约束节改"不提交"为"只 commit log 摘要"
- file: `.agents/skills/post-check/SKILL.md` → 同上正文同步（frontmatter 不动）
- file: `.claude/commands/full-review.md` → 结果归档节末尾追加 commit 段；审计要求节改"不要修改文件"为"除 review report 之外不要修改/提交"
- file: `.agents/skills/full-review/SKILL.md` → 同上正文同步（frontmatter 不动）
- 主 checkout 的 extraction 分支侧：commit 残留的 `logs/change_logs/2026-04-24_204846_*.md` /post-check 回写（commit message 例：`log(drop-digest-catalog-length-item-bounds): /post-check 复查结论回写 REVIEWED-PASS`）

## 验证标准

- [ ] `diff` 比对 `.claude/commands/post-check.md` 与 `.agents/skills/post-check/SKILL.md`，去除 frontmatter 后正文逐字一致
- [ ] 同上比对 `/full-review` 两份镜像
- [ ] master 提交完成后工作区 clean
- [ ] extraction 提交残留 log 后工作区只剩 `2026-04-24_201937_relocate-logs-to-root.md`（与本次无关，用户预先存在的 dirty 文件）
- [ ] master → extraction merge 无冲突

## 执行偏差

无。PRE 计划清单逐条落实。

<!-- POST 阶段填写 -->

## 已落地变更

`/post-check` 镜像（2 份）：

- `.claude/commands/post-check.md` Step 5 末尾追加 6 行 commit 段（commit 在当前分支、仅 stage log 文件、message 风格 `log({slug}): /post-check 复查结论回写 REVIEWED-...`）
- 同文件"约束"节："**只读 + 单写例外**：...不提交；唯一的写操作是 Step 5 追加 log 摘要" → "**只读 + 单写单 commit 例外**：...唯一允许的写 + commit 是 Step 5 那份 log 摘要回写——其他 dirty 文件一律不动、不提交"
- `.agents/skills/post-check/SKILL.md` 同步上述 2 处（frontmatter 不动）

`/full-review` 镜像（2 份）：

- `.claude/commands/full-review.md` "审计要求" 首条："不要修改文件" → "除「结果归档（必做）」那份新建的 review report 必须 commit 之外，不要修改、commit 或推送任何其他文件"
- 同文件"结果归档（必做）"末尾追加 5 行 commit 段（commit 在当前分支、仅 stage review report、message 风格 `log(review_reports): /full-review {slug} ({model})`）
- `.agents/skills/full-review/SKILL.md` 同步上述 2 处

未在 worktree 内处理：主 checkout（extraction 分支）残留的 `logs/change_logs/2026-04-24_204846_*.md` 上一轮 /post-check 回写——按本次新规则它本应在 /post-check Step 5 末就 commit；现在会在 Step 8 worktree commit 完成、worktree 移除后，于 extraction 主 checkout 上单独补一个 `log(...): /post-check 复查结论回写 REVIEWED-PASS` commit，与新规则首次落地的姿态一致。

## 与计划的差异

无。

## 验证结果

- [x] `diff` `.claude/commands/post-check.md` ↔ `.agents/skills/post-check/SKILL.md`：除既有镜像约束行（设计差异，互相引用）外正文逐字一致；与 master HEAD 的 baseline diff 模式相同
- [x] 同上 `/full-review` 两份镜像；唯一额外差异是 `.claude/commands/full-review.md` 末尾 `\ No newline at end of file`，**HEAD 时已存在**，不是本次引入
- [ ] master 提交 + worktree 移除（待 Step 8）
- [ ] extraction 残留 log 单独 commit（待 Step 8）
- [ ] master → extraction merge（待 Step 9）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 21:21:13 EDT
