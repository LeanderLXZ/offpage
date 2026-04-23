---
name: go_ask_before_checkout_master
description: /go Step 8/9 切回 master 改为询问确认，而非自动 checkout
type: skill
---

# go_ask_before_checkout_master

- **Started**: 2026-04-23 16:59:34 EDT
- **Branch**: master
- **Status**: PRE

## 背景 / 触发

`/go` Step 8 末句和 Step 9 末行当前是**自动** checkout 回 master：

- Step 8: "提交后 `git status` 确认干净，非 master 分支按 Step 0
  策略回合"
- Step 9: "否则 `git checkout <branch> && git merge master`；…；
  干净合并后 `git checkout master`"

用户反馈：希望 AI 在完成 merge / commit 后**先问**是否要切回
master，而不是默认切过去。原因（推测）：用户可能想立即继续
extraction / 在 extraction 分支上做其他事，自动切 master 会打断
工作流。

## 结论与决策

- Step 8 末句：改为"提交后 `git status` 确认干净；若当前不在
  master，**询问用户**是否切回 master，不自动执行"
- Step 9 末行：改为"干净合并后**询问用户**是否 `git checkout
  master`；除非用户明确同意，否则停在合并完的分支上"
- 其余 Step 9 流程（列分支、判 ancestor、merge master、冲突停手）
  保持不变
- 保持镜像：`.claude/commands/go.md` + `.agents/skills/go/SKILL.md`
  同步修改
- `ai_context/conventions.md` §Git 的"Stay on `master` unless
  actively running extraction" 原则**不动** —— 那是仓库的稳态
  规则；本次改的只是 `/go` 的操作策略（不静默切，而是问）。默认
  稳态还是 master，但切换由用户决定

## 计划动作清单

- file: `.claude/commands/go.md` → Step 8 / Step 9 末尾文字修改
- file: `.agents/skills/go/SKILL.md` → 镜像同上（正文逐字一致）
- file: `docs/logs/2026-04-23_165934_go_ask_before_checkout_master.md`
  → 本 log

本次改动**不触及**：
- `ai_context/conventions.md` §Git（稳态原则仍是 master）
- `ai_context/architecture.md` §Git Branch Model（enforcement 机制：
  `try/finally: checkout_master(...)` + SessionStart hook 仍有效）
- `.claude/hooks/session_branch_check.sh` 行为

## 验证标准

- [ ] `.claude/commands/go.md` Step 8 末句 + Step 9 末行改为"询问"
  语义，无残留"自动 checkout" 字样
- [ ] `.agents/skills/go/SKILL.md` 镜像一致（`diff` 两份文件正文
  应只差 YAML frontmatter）
- [ ] `ai_context/conventions.md` §Git 未被改动
- [ ] master commit 后 extraction merge 干净
- [ ] **本 /go 本次自己就按新规则执行** —— Step 9 结束时问用户
  是否切回 master，而不是默认切

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

- `.claude/commands/go.md:90` — Step 8 末句"非 master 分支按 Step 0
  策略回合" → "若当前不在 master，**先询问用户是否 `git checkout
  master`**，得到明确同意再切；用户说不切就停在当前分支"
- `.claude/commands/go.md:95` — Step 9 "干净合并后 `git checkout
  master`" → "干净合并后**先询问用户是否 `git checkout master`**，
  得到明确同意再切；默认停在合并完的分支上"；Step 9 末句追加
  "并说明当前 HEAD 停在哪个分支"
- `.agents/skills/go/SKILL.md:95 / :100` — 镜像同上
- `docs/logs/2026-04-23_165934_go_ask_before_checkout_master.md` — 本 log

`diff` 验证两份文件正文只差自引用的"镜像约束"一行（符合现状）。

## 与计划的差异

无。

## 验证结果

- [x] Step 8 末句 + Step 9 末行改为"询问"语义，无残留自动 checkout — 已验证
- [x] SKILL.md 镜像一致（正文逐字，只差镜像约束自引用行）— 已验证
- [x] `ai_context/conventions.md` §Git 未被改动 — 已验证（本次 `git status` 只含 go.md + SKILL.md + log）
- [ ] master commit 后 extraction merge 干净 — 待 Step 8 / Step 9
- [ ] 本 /go 自己按新规则执行：Step 9 合并完不自动切回 master，而是问用户 — 待 Step 9

## Completed

- **Status**: DONE
- **Finished**: 2026-04-23 17:01:50 EDT
