# revert-post-check-rootcause

- **Started**: 2026-04-29 05:12:07 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

会话里"反过度工程自审"的结论：上一轮 commit
[7ee7a60](../../) 同时落了 2 项 Karpathy CLAUDE.md 借鉴

1. `/post-check` Step 4 加 **root cause vs symptoms**
2. `/go` Step 4 加 **verification-up-front**

复盘后判定：

- (1) 与项目级 CLAUDE.md「identify root causes…」全局条款语义重叠；sub-agent 实操判不出来（依赖语义理解，不是结构规则）；列表已 12 条达到"塞不下"临界 → **稀释成本 > 边际收益，撤**
- (2) 不是新增规则，是把已有结构（PRE log「验证标准」段）推到落地；含糊验证标准的代价是 `/post-check` 整轮失效，回报明显 → **保留**

用户「回滚吧，然后加入你真正觉得有必要加入的东西」——本轮就是只动 `/post-check`，把 root-cause 那条撤掉；`/go` Step 4 不动。

git history 选择：手工 edit 撤一条而不是 git revert 全 commit + new commit。理由：原 7ee7a60 改了 4 文件 + log，full revert 会带回 `/go` Step 4，再加新 commit 会留 3 条 commit 噪音；手工 edit 1 条 + 1 个 log → 单 commit 干净。

## 结论与决策

只在 2 份 `/post-check` 镜像里删除上一轮加的「root cause vs symptoms」那条 bullet（位置：Step 4 列表「bug / 行为风险」与「README / 目录结构」之间）。

不动：
- `.claude/commands/go.md` Step 4「先确认 PRE log「验证标准」段已有 ≥ 1 条具体可执行项」——保留
- `.agents/skills/go/SKILL.md` Step 4 同——保留
- 项目级 CLAUDE.md（已有 root-cause 全局条款，无需补）

## 计划动作清单

- file: `.claude/commands/post-check.md` — 删除「- **root cause vs symptoms**: ...」整行
- file: `.agents/skills/post-check/SKILL.md` — 同行同步删除
- 同 commit 提交本 log

## 验证标准

- [ ] `/post-check` 两份镜像逐字一致：`diff <(awk '/^# \/post-check/,0' .claude/commands/post-check.md) <(awk '/^# \/post-check/,0' .agents/skills/post-check/SKILL.md)` 返回空
- [ ] post-check Step 4 列表 12 → 11 项：`awk '/^## 4\./,/^## 5\./' | grep -c '^- \*\*'` = 11 in both mirrors
- [ ] post-check 两份「root cause vs symptoms」关键词 0 命中
- [ ] `/go` 两份镜像未受本次影响：仍含「先确认 PRE log「验证标准」段已有」1 次
- [ ] git diff --stat 仅 `.claude/commands/post-check.md` + `.agents/skills/post-check/SKILL.md` + 本 log（3 文件）

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

- `.claude/commands/post-check.md` Step 4 — 删除「- **root cause vs symptoms**: ...」整行；列表 12 → 11 项
- `.agents/skills/post-check/SKILL.md` — 同行同步删除

`/go` 两份镜像未受本次影响（保留上一轮的 verification-up-front 句）。

## 与计划的差异

无

## 验证结果

- [x] /post-check 两份镜像逐字一致 — diff 返回空
- [x] post-check Step 4 列表 12 → 11 项 — 两份各 11 bullet
- [x] post-check 两份「root cause vs symptoms」0 命中 — grep 已验
- [x] /go 两份「先确认 PRE log「验证标准」段已有」仍各 1 次 — 未受影响
- [x] git diff --stat 仅 2 个 skill 文件（2 deletions）+ 本 log

## Completed

- **Status**: DONE
- **Finished**: 2026-04-29 05:14:01 EDT
