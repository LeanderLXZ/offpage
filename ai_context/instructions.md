<!-- holo:section start -->
<!--
MAINTENANCE — 编辑本文件前请先阅读。
稳定的项目元规则。保持精简；仅在规则本身变化时更新。
Sentinel 纪律（参见 CLAUDE.md §plugin 管理段）：sentinel `<!-- holo:section start/end -->` 内的内容是 plugin canonical，`/holo:update` 会覆写；项目专属新增内容写在 sentinel 之外的 gap 里。
-->
<!-- holo:section end -->

<!--
项目补充维护规则：
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `Character A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# 给后续 AI 智能体的指引 <!-- holo:heading -->

## 入口点 <!-- holo:heading -->

<!-- holo:section start -->
`ai_context/` 是 handoff 入口。默认不要重读整段对话历史或大型产物
目录。只有当用户的任务明确需要时，才加载更重的层（logs、原始输入、
生成产物）。

读完 `ai_context/` 后，**停下来等待**下一条指令。读 `ai_context/`
是上下文加载，不是任务说明。只在用户显式请求时行动。
<!-- holo:section end -->

项目补充：默认也不要重读小说原文；除非用户要求，不要加载 `prompts/`。

## 阅读顺序 <!-- holo:heading -->

<!-- holo:section start -->
1. `instructions.md`（本文件）
2. `project_background.md`
3. `requirements.md`
4. `architecture.md`
5. `conventions.md`
6. `decisions.md`
7. `handoff.md`

Dilution self-check（何时重读哪个文件）写在 `CLAUDE.md` /
`AGENTS.md`。
<!-- holo:section end -->

项目实际阅读顺序：

1. `conventions.md`
2. `project_background.md`
3. `requirements.md`
4. `architecture.md`
5. `decisions.md`
6. `handoff.md`

## 阅读范围 <!-- holo:heading -->

<!-- holo:section start -->
默认先读什么 / 默认跳过什么 / 何时读得更深。

**默认优先级** —— 启动会话时优先读（`ai_context/` 永远最先读）。
随项目演进，把专属的"小而高信号"目录追加到下方 user-territory 列表。

**默认不读** —— 大型或以写为主的目录：`logs/change_logs/`（完整
历史）、`logs/review_reports/`（过往审计快照）、`logs/file_snapshots/`
（smart-merge 备份归档）、`docs/decisions.md`（决策完整条目 ——
会话开始只读索引 `ai_context/decisions.md`；仅当需要某条决策的
理据时才打开归档）。仅当任务明确要求时才加载。把项目专属的
跳过路径追加到下方 user-territory 列表。

**何时深入阅读** —— 用户明确要求；任务依赖来自更重源的特定证据；
`ai_context/` 中的压缩上下文不足以回答当前问题；某个冲突需要
provenance 校验。

**实用规则** —— 优先做定向读取：具体文件、最小摘录、先看摘要。
避免扫描整个大目录、加载全部会话历史、读取全部 logs，或将源内容
大段粘进回答。
<!-- holo:section end -->

项目专属默认优先级路径（例如顶层 `README.md`）：

- 顶层 `README.md`（项目定位 + 包家族 + 入口清单）
- `docs/architecture/`（正式架构文档，含 schema reference）

项目专属默认跳过路径：

- `sources/`（大型原始语料）
- `users/*/sessions/`（完整会话历史）
- `works/*/analysis/evidence/`（完整证据）
- 数据库 / 向量库 / 索引等大型生成产物
- `prompts/`（仅当任务与 prompt 相关或用户要求时读）

## 更新预期 <!-- holo:heading -->

<!-- holo:section start -->
仅在**仓库的持久事实**（长期惯例、架构、schema、决策）发生变更时
更新 `ai_context/`。短期运行时状态 / 单任务进度归 work-local 进度
文件或 TODO 列表，不归这里。
<!-- holo:section end -->

项目补充：持久事实还包括数据模型惯例与检索策略；运行时 / 提取进度归
work-local 或 user-local 进度文件，不归这里。

## 日志记录 <!-- holo:heading -->

<!-- holo:section start -->
`ai_context/` 之外的每次改动 → 按 `conventions.md` §Logging 的
契约在 `logs/change_logs/` 下落一条条目。负责 logging 格式的 skill
（`/go` / `/do` / `/post-check`，当本项目使用它们时）直接写文件 ——
不要在此处重复格式。
<!-- holo:section end -->

项目补充：日志条目为 `logs/change_logs/YYYY-MM-DD_HHMMSS_slug.md`
（HHMMSS 必填），分三个时间点写入：

- **PRE** —— `/go` Step 1，任何文件改动之前
- **POST** —— `/go` Step 7，commit 之前
- **REVIEW** —— `/post-check` Step 5

## TODO 清单 <!-- holo:heading -->

<!-- holo:section start -->
`docs/todo_list.md` —— 已规划但未完成任务的工作队列。按需读取，
**不**纳入会话起始的读取顺序。使用规则写在该文件自身的
`## File guide` 段。
<!-- holo:section end -->

项目补充：段位为 `## In Progress` / `## Next` / `## Discussing (Undecided)`。
文件顶部有一个 `## Index (auto-generated; do not hand-edit)` 段，
把全部词条缓存为三张子表；`/todo` skill 只读该段。已完成 / 已放弃
的任务移出到 `docs/todo_list_archived.md`（词条精简；细节在
`git log` + `logs/change_logs/`）。

## 项目焦点 <!-- holo:heading -->

决策逻辑、记忆逻辑与关系逻辑 —— 而非表层语气。分层隔离（客观情节 /
角色 canon / 记忆 / 口吻 / 行为 / 用户 / 运行时）。感知 stage。
canon 与推断分别标注。小说原文 = 最高权威。运行时 = 检索 + 编译，
而非单个巨型 prompt。
