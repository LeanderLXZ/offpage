# post-check-rootcause-and-go-verify-upfront

- **Started**: 2026-04-29 04:40:02 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

会话讨论：参考 https://code.claude.com/docs/en/best-practices 全文 vs 已有 skill 集对照后，绝大多数已覆盖；只挑 1 条主推 + 1 条微调（不再多塞防止信号稀释）：

1. **主推**：`/post-check` Step 4 加「root cause vs symptoms」检查项——doc 强调"Address root causes, not symptoms"，我们 CLAUDE.md 项目级已有相关全局条款但 post-check 没有专门事后核查。
2. **微调**：`/go` Step 4 顶部加一句"先确认 PRE log 验证标准 ≥ 1 条具体可执行"——doc 强调 verification criteria up front，我们已有验证标准段但偶尔顺序错位（先改代码再补验证）。

用户 /go 落地 1+2 全部。

## 结论与决策

只动 2 个 skill 各加 1 条措辞，不重构结构、不改其他 step。

**`/post-check` Step 4** — 在「bug / 行为风险」之后、「README / 目录结构」之前插入：

> - **root cause vs symptoms**：本次若是 bug fix / error 修复，核对改动是攻击根因还是只压制了表象（例如吞 exception、降 assert、try/except 不分类、绕过校验）。表象修复 → 列入 Residual Risks

**`/go` Step 4** — 第一行后追加一句（不替换原有内容）：

> 按讨论改 schema、prompt template、架构代码、配置。**先确认 PRE log「验证标准」段已有 ≥ 1 条具体可执行项**（如 `import 无报错` / `grep 残留 = 0` / `smoke X 全过`；非"做对了就行"这类含糊）；含糊 → 立刻补具体的再继续。对照 `ai_context/conventions.md` 的 Cross-File Alignment 表列出连带文件（该表不存在则跳过本项，仅按本次改动直觉判断）。

镜像约束：每个 skill 都 4 份镜像本质 2 份正文（`.claude/commands/X.md` + `.agents/skills/X/SKILL.md`），共改 4 个文件。

## 计划动作清单

- file: `.claude/commands/post-check.md` Step 4 — 在「bug / 行为风险」与「README / 目录结构」之间插入 root-cause bullet
- file: `.agents/skills/post-check/SKILL.md` — 同位置同措辞镜像
- file: `.claude/commands/go.md` Step 4 — 首句后追加"先确认 PRE log「验证标准」段已有 ≥ 1 条具体可执行项..."一句
- file: `.agents/skills/go/SKILL.md` — 同位置同措辞镜像

## 验证标准

- [ ] `/post-check` 两份镜像正文逐字一致：`diff <(awk '/^# \/post-check/,0' .claude/commands/post-check.md) <(awk '/^# \/post-check/,0' .agents/skills/post-check/SKILL.md)` 返回空
- [ ] `/go` 两份镜像正文逐字一致：`diff <(awk '/^# \/go/,0' .claude/commands/go.md) <(awk '/^# \/go/,0' .agents/skills/go/SKILL.md)` 返回空
- [ ] post-check Step 4 列表从 11 项变为 12 项（grep `^- \*\*` 在两份各 12）
- [ ] post-check 两份各含 "root cause vs symptoms" 关键词 1 次
- [ ] go Step 4 两份各含 "先确认 PRE log「验证标准」段已有 ≥ 1 条具体可执行项" 1 次
- [ ] 其它步骤未被改动（diff `git diff --stat` 仅这 4 个 skill 文件 + 本 log）

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

- `.claude/commands/post-check.md` Step 4 — 在「bug / 行为风险」与「README / 目录结构」之间插入 root-cause 子条目；列表 11 → 12 项
- `.agents/skills/post-check/SKILL.md` — 同位置同措辞镜像
- `.claude/commands/go.md` Step 4 — 首句末尾插入"**先确认 PRE log「验证标准」段已有 ≥ 1 条具体可执行项**...含糊 → 立刻补具体的再继续"
- `.agents/skills/go/SKILL.md` — 同位置同措辞镜像

## 与计划的差异

无

## 验证结果

- [x] /post-check 两份镜像逐字一致 — diff 返回空
- [x] /go 两份镜像逐字一致 — diff 返回空
- [x] post-check Step 4 列表 11 → 12 项 — `awk '/^## 4\./,/^## 5\./' | grep -c '^- \*\*'` = 12 in both mirrors
- [x] post-check 两份各含 "root cause vs symptoms" 1 次
- [x] go 两份各含 "先确认 PRE log「验证标准」段已有" 1 次
- [x] `git diff --stat` 仅这 4 个 skill 文件 + 本 log（4 files changed, 4 insertions(+), 2 deletions(-)）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-29 04:41:49 EDT
