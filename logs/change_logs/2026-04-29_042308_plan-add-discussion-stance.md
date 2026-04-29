# plan-add-discussion-stance

- **Started**: 2026-04-29 04:23:08 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

会话讨论：参考 Karpathy 风格 CLAUDE.md（forrestchang/andrej-karpathy-skills）的"Think Before Coding / Simplicity First"思路，给 `/plan` 加反过度工程 / 反过度思考的"讨论姿态"段。

筛过 Karpathy 4 节后只吸收 4 条与「讨论期」直接相关的：multiple interpretations / unclear → ask / simpler push back / explicit assumptions；不吸收「Surgical Changes」「Goal-Driven Execution」（实现期，不属 /plan）；不重复已在 CLAUDE.md 全局生效的「Don't add features beyond what was asked」类条款。

用户选 (b)：4 条 + 第 5 条「不清楚就停」。

## 结论与决策

在 `/plan` 现有「## 规则」段后追加新一节「## 讨论时的姿态」，5 条短规则。**只动这一节**——「## 规则」/ 顶部解释段 / 镜像约束段不动。

5 条措辞已在会话讨论里定型，本次 /go 直接落盘：

1. **范围收敛**：用户问范围 N → 答范围 N。若 N+1 顺手能解决再点一句，不主动扩到 N+2 / N+3。讨论阶段最常见的过度工程是堆"顺便"
2. **不预实现**：不写完整 pseudocode / 整段函数草案。需要示意时最多写 1-2 行签名或 1 个数据结构骨架
3. **简单优先 + 主动 push back**：发现"按用户提议做最简，X / Y 加进来反而复杂"时，主动说"建议不做 X" + 一句理由；不要默认接受用户的所有 framing
4. **显式标注不确定性**：哪些是已读到的事实（行号 / 引用）、哪些是猜的、哪些得 grep / Read 才能下判断——分开说，让用户能逐条挑战
5. **不清楚就停**：发现关键前提歧义 / 缺信息 → 直接问一句而不是硬猜；猜测推回多轮成本远高于一句澄清

## 计划动作清单

- file: `.claude/commands/plan.md` — 在「## 规则」段之后、「---」分隔线之前插入新节「## 讨论时的姿态」+ 5 条
- file: `.agents/skills/plan/SKILL.md` — 同位置同措辞镜像（YAML frontmatter 不动）

## 验证标准

- [ ] `diff <(awk '/^# \/plan/,0' .claude/commands/plan.md) <(awk '/^# \/plan/,0' .agents/skills/plan/SKILL.md)` 返回空（4 份镜像应是 2 份；本 skill 镜像是 2 份正文 = .claude/commands + .agents/skills）
- [ ] 两份镜像各含「## 讨论时的姿态」标题 1 次 + 5 条 bullet（`grep -c '^## 讨论时的姿态'` = 1，`awk '/^## 讨论时的姿态/,/^---$/' | grep -c '^- \*\*'` = 5）
- [ ] 「## 规则」段未被改动；镜像约束段未被改动；顶部解释段未被改动

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

- `.claude/commands/plan.md` — 在「## 规则」段最后一条 bullet 之后、`---` 镜像约束分隔线之前插入新节「## 讨论时的姿态」+ 5 条 bullet（范围收敛 / 不预实现 / 简单优先 + push back / 显式标注不确定性 / 不清楚就停）
- `.agents/skills/plan/SKILL.md` — 同位置同措辞镜像同步（YAML frontmatter 不动）

「## 规则」段、顶部解释段、镜像约束段未触及。

## 与计划的差异

无

## 验证结果

- [x] `diff <(awk '/^# \/plan/,0' .claude/commands/plan.md) <(awk '/^# \/plan/,0' .agents/skills/plan/SKILL.md)` 返回空 — "OK: 镜像逐字一致"
- [x] 两份镜像各含「## 讨论时的姿态」标题 1 次 + 5 条 bullet — grep 验证（heading=1, bullets=5 in both）
- [x] 「## 规则」段 / 镜像约束段 / 顶部解释段未被改动 — diff 复核

## Completed

- **Status**: DONE
- **Finished**: 2026-04-29 04:25:38 EDT
