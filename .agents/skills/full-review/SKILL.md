---
name: full-review
description: 全仓库对齐审计 — 扫 ai_context/docs/schema/prompt/代码/样例产物，找跨文件不一致、legacy 残留、文档与实现漂移、状态机/门控缺口、bug 与隐患，输出按严重度排序的 findings 并归档到 logs/review_reports/。用户说"全库 review"、"对齐审计"、"full-review"、"跑一轮 review" 时触发。只审计，不改代码。
---

# /full-review — 全仓库对齐审计

对整个 Offpage 仓库做一次"规范对齐 + 实现风险"的全量 review。`$ARGUMENTS` 存在则作为本轮重点或额外关注点。

## 目标

先阅读 `ai_context/` 和 `docs/` 来 follow 当前项目真相，再 review 整个仓库，判断：
1. 文档、ai_context、schema、prompt、实现是否对齐
2. 是否存在冲突、歧义、过时描述、未落地承诺
3. 是否存在 bug、行为风险、状态机 / 流程门控问题、数据一致性风险
4. 架构设计和实现上是否有明显问题、隐患、脆弱点
5. 是否存在"文档说 A，代码做 B，样例数据又是 C"的情况
6. 是否存在 legacy 逻辑、半迁移状态、死代码、失效校验、空跑检查
7. 是否存在当前已提交样例 / 产物与仓库宣称状态不一致的问题

## 工作方式

- 先读 `ai_context/`，把它当作默认 handoff 入口
- 再读 `docs/requirements.md` 和 `docs/architecture/`
- 不要默认去读 `logs/change_logs/`，除非已发现冲突、必须追溯历史决策
- 然后扫描整个仓库，包括但不限于：
  - `automation/`
  - `simulation/`
  - `schemas/`
  - `prompts/`
  - `works/`
  - `users/`
  - `README.md`
  - `.gitignore`
- 如果能力支持并行，并行跑至少三条审计线：
  1. 规范线：`ai_context/`、`docs/`、`schemas/`、`prompts/`
  2. 实现线：`automation/`、`simulation/`、脚本 / 状态机 / 校验 / 重试 / 回滚逻辑
  3. 样例产物线：`works/`、`users/_template/`、已提交的 progress / artifact 是否与规范一致

## 重点检查项

- `ai_context` 与 `docs` 是否一致
- `docs/requirements.md` 与 `docs/architecture/*` 是否一致
- `schemas` 是否覆盖文档承诺的核心数据结构
- prompt 模板是否仍引用过时字段、旧流程、已废弃文件
- orchestrator / validator / consistency checker / post-processing 是否真的兑现文档中的门控与校验承诺
- Phase / 状态机 / 恢复 / 回滚 / 重试 / commit gate 是否有缺口
- 是否有"文档宣称会阻断，但代码实际不会阻断"的问题
- 是否有字段名漂移、schema 字段与代码字段不一致的问题
- 是否有程序化检查实际上失效、漏检、空检的问题
- `.gitignore`、本地产物、已跟踪文件之间是否矛盾
- 当前 `works/` 下已提交样例是否与 `ai_context/current_status.md`、README、docs 描述一致
- 是否有对外宣称"已完成 / 已验证"的内容，其实仓库现状并不支持

## 审计要求

- 这是 review，**不是改代码**；除"结果归档（必做）"那份新建的 review report 必须 commit 之外，不要修改、commit 或推送任何其他文件
- 优先找"高价值问题"，不是泛泛而谈
- 不要只给总结，先给 findings
- findings 按严重性排序：High / Medium / Low
- 每条 finding 尽量给出：
  - 结论
  - 为什么这是问题
  - 影响范围
  - 证据文件和具体行号
- 如果是"推断"而不是"直接证据"，明确标注"这是推断"
- 如果没有发现问题，也要明确说"未发现明确问题"，并列出残余风险和未覆盖区域
- 不要为了凑数而列低价值意见
- 不要把"未来可优化"混成 bug；把 bug / 冲突 / 风险 / 架构隐患分清楚

## 输出格式

1. `Findings`
   - 按严重性排序
   - 每条都带文件路径和行号
2. `Open Questions / Ambiguities`
   - 列出仓库内部无法唯一判断、需要产品 / 架构决策澄清的点
3. `Alignment Summary`
   - 简短总结哪些层是对齐的，哪些层最不对齐
4. `Residual Risks`
   - 即使当前没确认成 bug，也值得警惕的地方

## 结果归档（必做）

Review 结束后，把本轮完整 findings（含 False Positives、Open Questions、
Alignment Summary、Residual Risks、建议落地顺序）写到：

```
logs/review_reports/{YYYY-MM-DD_HHMMSS}_{model}_{slug}.md
```

- **时间戳**：用 `TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'` 取
- **`{model}`**：执行本轮 review 的模型 slug，小写、用 `-` 连接。例：
  `opus-4-7`、`sonnet-4-6`、`haiku-4-5`、`gpt-5`、`codex`。禁用空格、
  下划线、厂商前缀（不要写 `claude-opus-4-7`，直接 `opus-4-7` 即可）
- **`{slug}`**：英文或拼音短名描述本轮主题（如
  `t-token-watch_review_findings`、`post-phase3_audit`）
- **文件开头**必须有一行 `**Review 模型**：<完整模型名>（`<model-id>`）`，
  与文件名中的 `{model}` 对应，便于后续搜索 / 区分不同模型的判断差异
- 一次 review 一个文件，不追加、不覆盖旧文件
- `logs/review_reports/` 仅存 review 结果快照；与 `logs/change_logs/`（历史决策
  记录）、`docs/todo_list.md`（待办）职责互不重叠

写完后**立即 commit 这一份 review report 文件**——不要留作脏工作区，否则下一轮 `/go` 的 Step 0 自动锁定逻辑会把这份残留误判为"dirty 工作区"而强制走 worktree 路径。

- commit 在**当前分支**即可（`/full-review` 通常在用户当前所在分支跑，无需切换）
- 仅 `git add` 这一份 review report 文件——不要顺手把其他无关 dirty 文件带进 commit
- commit message 风格：`log(review_reports): /full-review {slug} ({model})`
- 不 push，不切分支；commit 后即结束本轮 review

## 额外要求

- 如果发现"文档之间互相冲突"，明确指出哪个应视为更高优先级真相
- 如果发现"ai_context 已过时"，明确指出它会如何误导后续 AI
- 如果发现"样例数据 / 进度文件与当前叙述不一致"，把它作为正式 finding
- 如果发现"检查器 / 一致性工具本身有盲区"，把它作为高优先级问题处理
- 尽量覆盖全仓库，但把重点放在真实会影响后续开发、提取质量、运行时正确性的地方

---

**镜像约束**：本文件和 `.claude/commands/full-review.md` 正文保持同步——任一侧修改必须在同 commit 内镜像到另一侧。本文件额外带 YAML frontmatter（`name` / `description`），正文（从一级标题 `# /full-review` 起往下）与 `.claude/commands/full-review.md` **逐字一致**。
