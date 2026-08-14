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
6. Sentinel 纪律（参见 CLAUDE.md §plugin 管理段）：sentinel `<!-- holo:section start/end -->` 内的内容是 plugin canonical，`/holo:update` 会覆写；项目专属新增内容写在 sentinel 之外的 gap 里。
-->
<!-- holo:section end -->

# 需求 —— 压缩索引 <!-- holo:heading -->

<!-- holo:section start -->
项目需求的压缩摘要，供快速跟进。

**权威来源**：`docs/requirements.md`（长篇正文，可能用
项目工作语言撰写）。下面的每一段用几行做摘要，并
指向那里对应的段以查阅全文。

本文件存在的目的是让会话起点无需加载长篇需求文档。
当需求发生变化时，两个文件须同步更新；该配对是
`conventions.md` §Cross-File Alignment 的其中一行。
<!-- holo:section end -->

## 格式 <!-- holo:heading -->

<!-- holo:section start -->
每条 entry 是一个编号块 —— 粗体引出语 + 2–5 行摘要（依 MAINTENANCE
规则 5）+ `→ docs/requirements.md §N` 指针；更长的细节推到指针目标。

**编号 —— 镜像 `docs/requirements.md`：**

- 条目 `N.` ≡ `docs/requirements.md §N`（1:1）。
- 只有当 `docs/requirements.md §N` 本身发生变化时，才新增 / 删除 /
  重写本文件的条目（lockstep）；不要在本文件凭空新增独立条目。
- 该 lockstep 对在 `conventions.md §Cross-File Alignment` 中登记
  （以 "Requirement statement added/changed in `docs/requirements.md`
  §N" 为 key 的那一行）。
<!-- holo:section end -->

## 段 <!-- holo:heading -->

## §1 总体目标

长期存续的小说角色扮演。深度的行为 / 记忆 /
关系一致性，而非表面语气模仿。任意角色、
基于阶段的状态、多终端。

## §2 阶段模型

按自然剧情边界切分（默认 10 章 / 最小 8 / 最大 15，作品 config 可调）；
阶段 N 累积覆盖 1..N，当前所选阶段 = "现在"。世界 / 角色 / 记忆共享
`stage_id`（`S###`）+ `stage_title`（供 bootstrap 阶段选择）。跨阶段
回忆用行为细节而非事件摘要。
→ `docs/requirements.md` §2。

## §3 三个深度扮演目标

1. 结构化角色数据（identity 含 `core_wounds` +
   `key_relationships` 作为角色级常量；每阶段 snapshot
   含 personality、triggers、goals vs obsessions、relationships、
   voice、boundaries、failure modes、`character_arc`）。
2. 角色视角记忆（主观，而非剧情摘要）。
3. 按情绪 / 对象 / 情境保持稳定的 voice + 行为。
- → `docs/requirements.md` §3。

### §3.1 身份 / 名称追踪

在稳定的 `character_id` 下做多名称追踪（别名类型：真名 /
别名 / 称谓 / 称呼 / 尊号 / 道号 —— 覆盖阶段范围
与出处）。分析阶段的**跨 chunk 身份
合并**是强制项。
→ `docs/requirements.md` §三「角色标识与名称跟踪」 + `schemas/character/identity.schema.json`。

## §4 运行时加载

六大类：基础身份 / 性格内核 / 说话风格 /
记忆 / 行为规则 / 禁止偏离。另有认知冲突
与历史回忆规则。完整公式 → `architecture.md` §运行时加载公式 +
`simulation/retrieval/load_strategy.md`。
→ `docs/requirements.md` §4。

## §5 用户流程

新建：作品 → 角色 → 阶段 → 自设角色 → 用户包 → 上下文；已有：加载账户 →
选择 / 创建上下文。设定一次性锁定（变更需新包或显式迁移）。关闭 / 合并 =
选择性长期提升；已合并的 context = 不可变的账户历史。逐轮 journaling
供崩溃恢复。
→ `docs/requirements.md` §5。

## §6 数据分离

客观 vs 主观；正典 vs 推断；角色正典 vs 用户
数据；知识边界；阶段边界；多作品命名空间；
内容语言一致性。硬性 schema 门控见 `conventions.md`
§Data Separation。
→ `docs/requirements.md` §6。

## §7 信息分层

五层：不可变层（identity + target_baseline，phase 2 角色级常量）/ 自包含
阶段快照（内联 voice / behavior / boundary / failure_modes）/ 历史记忆
（timeline + digests + FTS5）/ 会话内可变（逐轮）/ 跨会话（long_term_profile
+ relationship_core，仅合并）。加载：启动核心 → 结构化按需 → 对话记录 → 原文验证。
→ `docs/requirements.md` §7 + `architecture.md` §运行时加载公式。

## §8 源文本摄入

格式 TXT / EPUB / MOBI / HTML / 用户摘录。流水线：raw →
归一化 → 章节切分（补零）→ 元数据。源包 =
输入层，下游绝不修改，排除在 git 之外。中文
作品 → 中文 `work_id`。
→ `docs/requirements.md` §8 + `extraction/ingestion/`。

## §9 提取流程 —— Phase 0–4

Phase 0 章节摘要（并行 chunk，chunk 级字段与消费矩阵见 `docs/architecture/schema_reference.md`）
→ Phase 1 三 lane 全局分析（light_novel 2 lane + 程序化 stage_plan，决策 #52）→ Phase 1.5
角色确认 → Phase 2 baseline（2+2N lane fan-out + per-lane repair 缩水版，决策 #54/#59）→ Phase 3 协同阶段提取（文件级 repair）
→ Phase 3.5 最终关卡（六段：程序全扫 → 结清台账债 → 跨阶段连贯审校 → 定点修 → 重投影 → 复扫门判，决策 #72；每文件两次机会、未结清回写台账、仍失败记 `given_up` 降 warning 放行，决策 #74）→ Phase 4
场景归档 → 包校验；每阶段 snapshot 自包含（含未变字段）。
→ `docs/requirements.md` §9。

## §10 输出质量保护

§10.1 运行时抗稀释 —— 锚定重注入、滚动会话状态、深度校准 checkpoint
（`simulation/prompt_templates/` 实现）。§10.2 提取跨阶段质量 —— 每阶段
全新上下文（无会话内稀释），由 prompt_builder schema 注入、validator +
语义复审、Phase 3.5 一致性检查保护。
→ `docs/requirements.md` §10。

## §11 自动化提取流水线

Orchestrator（`extraction/persona_extraction/`）按 §9 驱动 Phase 0→1→1.5→2→3（阶段循环）→3.5→4（独立）；Claude / Codex CLI 后端。
Repair agent → `extraction/repair/` + §11.4；Token 上限自动暂停 → §11.13 + `extraction/persona_extraction/core/rate_limit.py`。
细节 → `architecture.md` §自动化抽取流水线 + `extraction/README.md` + `docs/architecture/extraction_workflow.md`。
→ `docs/requirements.md` §11。

## §12 记忆系统与检索

三层记忆：`stage_snapshot`（聚合状态）/ `memory_timeline`（主观过程）/
`scene_archive`（场景切分原文，Phase 4）。两级检索漏斗：Level 1 默认 <20ms
—— jieba + 作品词表 + FTS5 → LLM 判相关性；Level 2 兜底 —— `search_memory`
工具 → embedding。技术栈 `jieba` + `sqlite FTS5` + 可选 `bge-large-zh-v1.5`，单一 SQLite。
→ `docs/requirements.md` §12 + `simulation/retrieval/index_and_rag.md`。
