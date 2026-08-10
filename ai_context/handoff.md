<!-- holo:section start -->
<!--
MAINTENANCE — 编辑本文件前请先阅读。
本文件是用于快速回到项目状态的索引，不是详细手册。
1. 写"是什么 / 去哪找"；链接到权威源（代码路径、docs/*.md、schema、logs）。
2. 优先删减而非新增；新增前先检查是否能并入已有条目。
3. 只描述当前设计 —— 不写"legacy / deprecated / formerly / renamed from"。
4. 不出现真实产品 / 客户 / 私有内容名称 —— 使用结构性占位符。
5. 精简要求：
   - 越短越好。每条都是总结，不是细节堆叠。
   - 精简的同时也要保证信息的准确性和有效性，不要为了精简而漏掉重要信息。
   - 目标每条 ≤ 5 行，更长的细节推到链接的来源里（docs/<topic>.md）。
   - 不要压缩或改动与当前编辑无关的内容。
6. 表格形式是永久的 —— 直接填 cell。若某 cell 内容溢出可读性，把细节推到链接的文档（`docs/<topic>.md`）并把 cell 摘要保持一行。
7. Sentinel 纪律（参见 CLAUDE.md §plugin 管理段）：sentinel `<!-- holo:section start/end -->` 内的内容是 plugin canonical，`/holo:update` 会覆写；项目专属新增内容写在 sentinel 之外的 gap 里。
-->
<!-- holo:section end -->

# 交接 <!-- holo:heading -->

<!-- holo:section start -->
会话起始读取顺序的最后一个文件。快照当前项目状态、下一步方向，
以及塑造每一次决策的用户偏好。替代旧的 `current_status.md` +
`next_steps.md` + `handoff.md` 三件套。
<!-- holo:section end -->

## 心智模型

架构已定，脚手架 + schema + 提取管线已完成。
尚无任何一个角色包端到端完成，尚无真实用户包，
尚无运行时代码。

## 快速上手

1. 按顺序阅读 `ai_context/`（见 `instructions.md`）。
2. 后续跟进时，从 `ai_context/` + 用户请求继续。
3. 细节 → `docs/architecture/system_overview.md`、`data_model.md`、
   `schema_reference.md`。
4. 运行时流程 → `simulation/README.md`、`simulation/flows/`、
   `simulation/retrieval/`、`simulation/prompt_templates/`。
5. 提取管线 → `extraction/README.md`。

## 运行提取

入口 `python -m extraction.persona_extraction "<work_id>" --resume`（后台加 `--background --max-runtime 360`）；产物在 `works/<work_id>/` + `sources/works/<work_id>/`，进度 / 日志在 `works/<work_id>/analysis/progress/`。
**Resume 门控**：对已有 `extraction/<work_id>` 分支 `--resume` 前，先读 `docs/todo_list.md` 顶部 Index（只看 In Progress + Next，跳过 Discussing），确认没有针对当前 schema 的迁移任务在途——否则 repair agent 的 L1 门控会在每个收紧之前生成的文件上触发。
完整 CLI、后台语义、PID 锁 + scoped git preflight、`jsonschema` HARD 依赖 → `extraction/README.md`；人工修复场景 → `prompts/review/*.md`。

## 当前状态 <!-- holo:heading -->

<!-- holo:section start -->
项目**当下**所在位置的实时快照。每当项目进入新阶段、里程碑落地、
或重大 gap 被关闭 / 打开时更新。易变但持久 —— 它为未来的 AI 会话
回答"仓库现在是什么状态"。单任务进度归 `docs/todo_list.md`，不在
这里。
<!-- holo:section end -->

| 方面 | 详情 |
|---|---|
| 项目阶段 | 架构脚手架完成；schema + 提取管线 + simulation 设计已落地，无运行时代码。作品级提取状态在 `works/{work_id}/analysis/progress/`，此处只跟框架级进度 |
| 已有 | 完整目录脚手架 + `docs/architecture/` 正式文档；角色 / 世界 / 用户 schema（索引 → `docs/architecture/schema_reference.md`）；simulation 仅设计（flows / contracts / retrieval / prompt templates）；`prompts/` 手动场景；提取编排器 `extraction/persona_extraction/`（→ `architecture.md` §自动化抽取流水线 + `extraction/README.md`）；`users/_template/` 用户包模板 |
| 当前 gap | Phase 3.5 最终关卡已实现但尚未在真实数据上跑过（首跑会因 38 条历史台账债判 FAIL，属预期——债须结清才进 Phase 4）；Phase 4 未跑；无完成的角色包；无真实用户包；无 simulation 服务实现；无终端适配器；无检索实现（设计已定，等提取产物）；无最终扮演 prompt |
| 生效规则 | 内容语言 = 作品语言；真实用户包仅本地；git 不入小说 / 数据库 / 索引 / 大产物（决策 #41）；`works/*` 跟踪细则 → `works/README.md`；`logs/` 以写为主不主动读；阶段按自然剧情边界（默认 10 章 / 8–15） |

## 下一步 <!-- holo:heading -->

<!-- holo:section start -->
按优先级分组的方向级路线图。这是**方向**层，不是任务层。文件 /
函数级工程任务归 `docs/todo_list.md`；当某个方向具体到能写出路径
和行号时，把它升级到 `docs/todo_list.md`。
<!-- holo:section end -->

| 优先级 | 条目 |
|---|---|
| 高 | 端到端跑通首个作品的提取管线（产出第一个完成的角色包） |
| 中 | 依 `simulation/contracts/` + `flows/` 写首版代码 stub；定义可溯源 canon 的 evidence 记录格式；定义终端适配器的请求 / 响应格式；定义用户上下文与会话索引（按需转录回忆） |
| 后续 | 实现统一角色服务接口；支持更丰富的阶段切分（含关系阶段切分）；扮演一致性自动评估；更完整的爬取与导入支持 |

## 用户在意的事 <!-- holo:heading -->

<!-- holo:section start -->
塑造每次决策的软偏好和品味规则，不是正式 requirements。这些是
新 AI 会话需要继承的"用户在意的事"。在对话中浮现新偏好时追加
bullet；不再适用的删掉。
<!-- holo:section end -->

- 深度扮演而非表面模仿 / AI 腔调；保留阶段差异 + 知识边界（不全知、不跨 context 泄漏）
- 正典与推断标注区分，不静默模糊；增量更新，绝不从头重来
- 追求流程 / 架构**越来越简单**，反对"越加越复杂"；根治优先于打补丁。派生数据只用代码 1:1 投影、不用 LLM 生成或修复；repair 只碰 primary（决策 #61）
- 内容语言 = 作品语言；不把原文粘贴进 logs / docs / 回答
- **不出现真实书名 / 角色 / 剧情名称**，用通用占位符（`Character A` / `<work_id>` / `S001`）；适用范围 + 豁免完整列表见 `conventions.md` §Generic Placeholders
- → `docs/requirements.md` §1 / §5 / §6 / §9.1 + `conventions.md` §Generic Placeholders

## 每个里程碑之后

1. 在 `logs/change_logs/` 写一条带 HHMMSS 时间戳的记录（schema /
   架构 / prompt / simulation / 目录变更为强制）。
2. 仅在内容持久时才更新本文件（§当前状态 / §下一步 表）。
