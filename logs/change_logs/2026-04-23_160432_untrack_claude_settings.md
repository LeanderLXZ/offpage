---
name: untrack_claude_settings
description: 把 .claude/settings.json 从 git 追踪中移除，改为本地配置
type: infra
---

# untrack_claude_settings

- **Started**: 2026-04-23 16:04:32 EDT
- **Branch**: extraction/<work_id>
- **Status**: PRE

## 背景 / 触发

用户在把 go.md skill 改动同步到 master 时发现 `.claude/settings.json`
里新追加的 `permissions.allow` 条目带了具体书名路径（如
`works/<work_id>/analysis/progress/extraction.log`），而且每
次 extraction 运行遇到新 awk 模式就会触发 Claude Code 的 permission
prompt 并追加 allow 条目。这类条目：

1. 本质是本地运行时配置，既不适合放进 git 历史，也不适合 merge 到
   master（master 上并不跑这个 work）
2. 带具体书名属 user feedback "no specific refs in docs" 的精神延伸
3. 频繁被改动会让 git status 长期有脏，干扰 /go 流程

用户当前指令：**"不追踪 .claude/settings.json 了 /go"**。

## 结论与决策

- 把 `.claude/settings.json` 从 git 追踪中移除（`git rm --cached`）
- 在 `.gitignore` 里加入 `.claude/settings.json`
- 保留 `.claude/settings.local.json`、`.claude/commands/`、`.claude/
  agents/`、`.claude/hooks/` 的追踪现状不变（本次不扩大范围）
- 本地文件内容**不动**，仍为工作配置继续生效
- 新增 1 条 commit：extraction 上先提交，再 cherry-pick 到 master（与
  上一轮 `b78ba9b` → `df964cd` 同模式）

## 计划动作清单

- file: `.gitignore` → 追加一行 `.claude/settings.json`（或在已有
  `.claude/` 相关段落下就近追加）
- file: `.claude/settings.json` → `git rm --cached -f`，解除追踪；
  working tree 文件保留
- file: `docs/logs/2026-04-23_160432_untrack_claude_settings.md` →
  本 log，PRE → POST
- git: extraction 上 1 个 commit，再 `git checkout master && git
  cherry-pick <sha>` 同步到 master

## 验证标准

- [ ] `git ls-files .claude/settings.json` 输出为空（未被追踪）
- [ ] `.claude/settings.json` 文件仍存在于 working tree
- [ ] `git check-ignore .claude/settings.json` 命中（被 ignore）
- [ ] 修改 `.claude/settings.json` 后 `git status` 干净（不显示为
  modified / untracked）
- [ ] master 和 extraction 两边 `git log -1 --name-only` 都包含本
  commit，且 diff 一致

<!-- POST 阶段填写 -->

## 已落地变更

- `.gitignore` 第 50 行新增 `.claude/settings.json`（放在 "Claude Code
  local config" 段落顶部，与 `settings.local.json` 并列）
- `.claude/settings.json` 从 git index 移除（`git rm --cached -f`）；
  本地 working tree 文件保留，hooks + permissions 继续生效
- `ai_context/next_steps.md:13-15`：scope 外脏改动例子从
  `.claude/settings.json` 改为"editor state / other local changes"
- `ai_context/architecture.md:192-198`：同上
- `docs/architecture/extraction_workflow.md:496-499`：同上
- `automation/README.md:188-193`：同上
- `docs/logs/2026-04-23_160432_untrack_claude_settings.md`：本 log

## 与计划的差异

- **新增**：Step 5 全库 grep 时发现 `automation/README.md` 也有同样
  过时例子（PRE 计划清单只列了 ai_context 两处 + docs/architecture
  一处），顺手一并修；Step 6 再 grep 一次确认除历史 log / review
  report 外无残留
- **偏差（已在 "执行偏差" 登记）**：`.claude/settings.json` 里除了
  permissions 还包含两个项目级 hooks（PreToolUse log 文件名校验 +
  SessionStart branch guard），移除追踪后新 clone / worktree 会丢失
  这两个 hook。仍按用户原意执行，副作用留给用户决策（选 A / B / C）

## 验证结果

- [x] `git ls-files .claude/settings.json` 输出为空 — 已验证（Step 6
  `git ls-files` 空输出）
- [x] `.claude/settings.json` 文件仍存在于 working tree — 已验证
  （`ls -la` 1623 bytes）
- [x] `git check-ignore .claude/settings.json` 命中 — 已验证
  （`.gitignore:50` 命中）
- [x] `git status` 中 settings.json 不再以 modified 形式出现 — 已验证
  （只剩 `deleted: .claude/settings.json` 这一条是本次 untrack 的
  commit 自身的 staged 变更；下次改动 settings.json 不会再脏）
- [ ] master 同步后两边 diff 一致 — 留给 Step 8 / Step 9 验证

## Completed

- **Status**: DONE
- **Finished**: 2026-04-23 16:07:07 EDT

## 执行偏差

**Step 5 发现的副作用（需用户确认下一步）**：`.claude/settings.json`
里不仅有 `permissions.allow`（本地化合理），还有两个**项目级** hooks：

1. `PreToolUse` — 校验 `docs/logs/*.md` 文件名格式为
   `YYYY-MM-DD_HHMMSS_slug.md`（项目硬规则来源）
2. `SessionStart` — 跑 `.claude/hooks/session_branch_check.sh`（branch
   guard，防止新会话带错分支）

这两个 hook 是**仓库共有规则**，不是用户本地偏好。移除追踪后：

- 本机 working tree 上 `settings.json` 仍在 → hooks 继续生效
- 新 clone / 新 worktree / 其他贡献者 → 无 settings.json，两个 hook
  都静默失效（PRE log 文件名规则失守、branch guard 失守）

**本次处理**：仍按用户明确指令执行（ignore 整个 settings.json），
此偏差作为后续决策项登记。可选后续路径：

- A. 维持现状：接受"单机规则，其他环境自行 bootstrap"的 trade-off
- B. 把 hooks 段抽到 `.claude/settings.committed.json`（仍追踪）并在
  README / CLAUDE.md 加一段 "本地 `settings.json` 需手工合并 hooks"
  —— 需要确认 Claude Code 是否支持多 settings 文件合并
- C. 反过来：只 ignore `.claude/settings.json`，把稳定的 hooks 配置
  放回 tracked `settings.json`，`permissions.allow` 本地化到
  `settings.local.json`（Claude Code 原生支持后者）—— 最接近"只本
  地化噪声部分"的设计意图

用户可在 POST 之后选择继续 (/go C) 或暂停接受当前状态。

**Step 5 附带**：`ai_context/next_steps.md:14`、`ai_context/architecture.md:195`、
`docs/architecture/extraction_workflow.md:498` 三处把 `.claude/settings.json`
作为"scope 外脏改动"的例子已过时（ignore 后它不会再脏），已就地改为
"editor state / 其他本地改动"之类通用描述。
