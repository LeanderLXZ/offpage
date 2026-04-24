# skill_pre_log_reread_emphasis

- **Started**: 2026-04-24 02:20:54 EDT
- **Branch**: extraction/我和女帝的九世孽缘（编辑阶段）→ master（提交阶段）
- **Status**: PRE

## 背景 / 触发

用户在连续跑 `/go` + `/after-check` 两轮后，发现审查阶段里"重读 PRE
log"这条约束**执行得不对称**：

- `/go` Step 6（全库 review）当前只提"派 sub agent 时，**先让它重读
  PRE log**"——强调了 sub agent，没强调 Claude 自己。实际场景中
  Claude 进 Step 6 前已经累了几千 token 的编辑上下文，更需要显式重读
  PRE 的"结论与决策 / 计划动作清单 / 验证标准"对齐自检
- `/after-check` Step 2（并行 sub-agent 双轨审计线）当前没要求 sub
  agent 在开工前重读 PRE log——只在 Step 0.5 让 Claude 主进程加载
  intent 基线。sub agent 是独立 context，如果 prompt 里不塞 PRE log
  路径 + 明示重读，agent 会只读 prompt 自己写死的 brief，容易脱离
  本次 intent

本轮**不改 skill 语义，只改措辞让这条约束对称**：两处都明确说"Claude
自己 + sub agent 都必须重读 PRE log"。

## 结论与决策

1. `/go` Step 6：把现有"派 sub agent 时，先让它重读 PRE log"改为
   覆盖两端——"进入本步之前，**自己和派出的每个 sub agent 都必须重读
   Step 1 创建的 PRE log**"
2. `/after-check` Step 2：在并行 sub-agent 清单上方加一行强约束——
   "派出的**每个** sub agent 都必须在 prompt 里带上 Step 0.5 读到的
   intent 基线路径，并要求它开工前先读完该 log 的 PRE 段"
3. 镜像约束：`.claude/commands/{go,after-check}.md` 与
   `.agents/skills/{go,after-check}/SKILL.md` 正文**逐字一致**，本次
   同 commit 内镜像四份文件

## 计划动作清单

- file: `.claude/commands/go.md` → Step 6 措辞扩成"自己 + 每个 sub agent 都重读 PRE log"
- file: `.agents/skills/go/SKILL.md` → 同上镜像
- file: `.claude/commands/after-check.md` → Step 2 顶部加一行"每个 sub agent 都必须重读 intent 基线 PRE log"
- file: `.agents/skills/after-check/SKILL.md` → 同上镜像

## 验证标准

- [ ] `diff <(sed -n '/^# \/go/,$p' .claude/commands/go.md | grep -v "镜像约束") <(sed -n '/^# \/go/,$p' .agents/skills/go/SKILL.md | grep -v "镜像约束")` 为空
- [ ] `diff <(sed -n '/^# \/after-check/,$p' .claude/commands/after-check.md | grep -v "镜像约束") <(sed -n '/^# \/after-check/,$p' .agents/skills/after-check/SKILL.md | grep -v "镜像约束")` 为空
- [ ] `/go` Step 6 文本同时包含"自己"和"sub agent"且都指向"重读 PRE log"
- [ ] `/after-check` Step 2 文本明确写出"每个 sub agent 都必须...读 PRE"
- [ ] 两份 SKILL.md 的 YAML frontmatter（`name` / `description`）未被误改

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

- `.claude/commands/go.md` Step 6 — 原先只有一行引用块说"派 sub agent 时先让它重读 PRE log"，改写为两段引用块：
  - 第一段强制 Claude 自己在进入 Step 6 之前先重读 PRE log（理由：前几步的编辑上下文已经累积，需要重新对齐 intent）
  - 第二段保留并加强对 sub agent 的要求：把 `LOG:` 路径塞进 prompt + 明示要求 sub agent 开工前先读完 PRE 段
- `.agents/skills/go/SKILL.md` Step 6 — 逐字镜像上条
- `.claude/commands/after-check.md` Step 2 — 三条线清单之后、"每条线产出"之前新增一整段引用块：**派出的每个 sub agent 都必须先重读 intent 基线 PRE log**，明示要求读完 PRE 的四个小节（结论与决策 / 计划动作清单 / 验证标准 / 执行偏差）再扫描
- `.agents/skills/after-check/SKILL.md` Step 2 — 逐字镜像上条

## 与计划的差异

无。四份文件按计划落地，措辞一致。

## 验证结果

- [x] `/go` 两份文件正文 diff 仅剩**镜像约束自引用行**（路径自然反向，既有约定）
- [x] `/after-check` 两份文件正文 diff 仅剩**镜像约束自引用行**
- [x] `/go` Step 6 文本同时出现"自己"（首句）和 "sub agent"（第二段）且两句都落在"重读 PRE log"上
- [x] `/after-check` Step 2 文本出现"派出的**每个** sub agent 都必须先重读 intent 基线 PRE log"
- [x] 两份 SKILL.md 的 YAML frontmatter（`name` / `description`）未被改动
- [x] 仅四份目标文件被修改（`git diff --stat` 验证 4 files, +10/-2）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 02:28:00 EDT
