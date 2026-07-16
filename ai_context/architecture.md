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

# 架构快照 <!-- holo:heading -->

<!-- holo:section start -->
系统架构的压缩摘要，供快速跟进。

**权威来源**：详细架构文档存放于
`docs/architecture/`。本文件每一段都指向对应的
细节文档。

本文件存在的目的是让会话起点无需加载每一份架构文档。
当架构发生变化时，两层须同步更新 —— 该配对是
`conventions.md` §Cross-File Alignment 的其中一行。
<!-- holo:section end -->

权威来源：
`docs/architecture/system_overview.md`、`data_model.md`、
`schema_reference.md`、`extraction_workflow.md`、
`extraction/README.md`、`extraction/repair/`。

## 顶层结构 <!-- holo:heading -->

- `sources/` —— 原始小说输入 + 规范化的来源包
- `works/` —— 以原文为据的 canonical 包（world / characters / analysis / indexes）
- `users/` —— 按 `user_id` 分组的用户侧可变状态
- `simulation/` —— 运行时引擎的生命周期、检索、服务契约
- `prompts/` —— 仅手动使用（摄取 / 复审 / 补充 / 冷启动）
- `schemas/` —— 持久化 + 运行时请求 schema
- `interfaces/` —— 未来的终端适配器
- `extraction/` —— 抽取编排器（Python）
- `docs/architecture/` —— 正式架构文档（含 schema reference）
- `logs/` —— 变更日志 / 评审报告 / 文件快照（change_logs / review_reports / file_snapshots）
- `ai_context/` —— 本压缩交接

## 系统分层 <!-- holo:heading -->

1. **来源** —— 原始文本、规范化章节、元数据
2. **抽取** —— `works/{work_id}/analysis/`（progress、evidence、conflicts）
3. **世界** —— `works/{work_id}/world/`（foundation、stages、events、locations、factions、cast）
4. **角色** —— `works/{work_id}/characters/{character_id}/`（identity、memory、voice、behavior、boundaries、stage snapshots）
5. **用户** —— `users/{user_id}/`（锁定绑定、长期档案、关系核心、上下文、会话）
6. **模拟引擎** —— 启动、加载、检索、回写、关闭 / 合并
7. **界面** —— 终端适配器（未来）

## 关键边界 <!-- holo:heading -->

- 作品域 canon 数据在 `works/` 下；用户可变数据在 `users/` 下。
- 用户对话永不改写权威的世界 / 角色数据。
- 一个 `user_id` = 一个锁定的「作品-目标角色-对手角色」绑定。
- 中文作品使用中文标识符与路径段。
- JSON 字段名可保持英文；内容文本 = 作品语言。

## 运行时加载公式

启动一次性加载（按序）：世界 foundation（`foundation.json` + `fixed_relationships.json`）+ 选定世界阶段快照 → 角色常量层（`identity.json` + `target_baseline.json`）+ 自包含阶段快照（内联 `failure_modes` / voice / behavior / boundary state）→ `memory_timeline` 最近 2 阶段全量 + `memory_digest.jsonl` / `world_event_digest.jsonl` 按阶段 1..N 过滤 → `scene_archive` 最近 `scene_fulltext_window` 条 `full_text`（默认 10；summary 仅走 FTS5）→ 词表 → jieba → 用户角色绑定 + 长期档案 + 关系核心 → 当前 context manifest + `character_state.json` → 最近会话摘要。
按需加载：events / locations / factions / history、完整对话转写、archive 记录、原始章节、FTS5 / embedding 检索。
完整分层模型 → `simulation/retrieval/load_strategy.md` + `docs/architecture/system_overview.md` §运行时加载公式。

## 阶段模型

- 阶段（抽取）= 阶段（运行时），按 `stage_id` 1:1 对应。
- `stage_catalog.json` = 启动阶段选择器（运行时不加载）。
- `world_event_digest.jsonl` = 启动时加载，按 1..N 过滤。
- 阶段 N 累积覆盖 1..N；最新阶段 = 活跃的当下。
- 用户在初始设置时选定阶段；同时作用于目标角色 + 有原著依据的用户角色。

## 上下文生命周期

`ephemeral` → `persistent` → `merged`。实时角色扮演期间会话状态
持续更新；`long_term_profile` + `relationship_core` 仅在关闭时
显式合并后更新。合并是追加优先的（永不做破坏性覆盖）。

## 自包含阶段快照

每个 `stage_snapshots/{stage_id}.json` 携带完整角色状态（voice / behavior / boundary / `failure_modes` / relationships / personality / mood / knowledge / `character_arc`）——运行时加载单个快照即可，无需 baseline 合并。
`identity.json` + `target_baseline.json` 是角色级常量（Phase 2 产物，Phase 3 起不可变），与快照一同加载；`target_baseline` 锚定 phase 3 快照的 target 键集合（跨文档硬失败；见 #13）。voice / behavior / boundary / failure_modes **无独立 baseline 文件**——状态由快照演化链承载（S001 从原文 + identity 派生种子；S002+ 从上一快照演化）。
`target_voice_map` / `target_behavior_map` 以 `target_character_id` 为键、详略随 tier（核心 / 重要 ≥3–5 例，次要 / 普通 / 未出场按 D4 状态 3 从简 / 为空），按用户角色过滤：canon → 精确匹配；OC → 经 role_binding 按条目 `target_type` 回退。无匹配时向前回扫先前快照（纯代码 I/O）。
详情 → `docs/architecture/data_model.md` §角色包 + `simulation/retrieval/load_strategy.md` Tier 0。

## 三层记忆

1. **stage_snapshot** —— 每阶段聚合状态（「我现在信任他」）；运行时仅加载当前阶段。
2. **memory_timeline** —— 每事件主观过程（`memory_id` = `M-S###-##`，必填简短 `time` / `location` 锚点；字段精确边界 → `schemas/character/memory_timeline_entry.schema.json`）；按阶段存放于 `canon/memory_timeline/{stage_id}.json`。启动最近 2 阶段全量，较远经 `memory_digest.jsonl` + FTS5 / embedding 按需加载。
3. **scene_archive** —— 按场景切分的原文（`scene_id` = `SC-S###-##`，作品级）；仅加载最近 `scene_fulltext_window` 条 `full_text`，summary 仅走 FTS5。
关系演化：快照 `relationships` 记录对各 target 的态度 / 信任 / 亲密 / 戒备 / 语言与行为变化 / 驱动事件 / 感知地位 / 1..N 历史；`stage_delta.*_changes` 携带归因。
字段详情 → `docs/architecture/schema_reference.md` + `docs/architecture/data_model.md` §角色包。

## 历史回忆与认知冲突

- 历史回忆由启动时加载的 `memory_timeline` + `relationship_history_summary` 提供。过往快照按需加载。
- 认知冲突由运行时 prompt 规则处理，而非预写数据。
- → `simulation/prompt_templates/历史回忆处理规则.md`、`认知冲突处理规则.md`。

## 角色扮演逻辑链

`memory + relationship → psychological reaction → behavior decision → language realization`

而不是：`surface tone imitation → generic reply`。

## 记忆检索

两个库（`scene_archive` + `memory_timeline`），两级漏斗：Level 1（默认，<20ms）= jieba + 词表 + FTS5 top-K summary；Level 2（罕见，200–300ms）= LLM `search_memory` 工具 → summary 向量 embedding 检索。每轮主动做上下文状态关键词联想。
技术选型：`jieba` + `sqlite FTS5` 为主 + `bge-large-zh-v1.5` 可选；单一 SQLite，无独立向量库。
→ `docs/requirements.md` §12 + `simulation/retrieval/index_and_rag.md`。

## Git 分支模型

三分支，`main` 是唯一推远端的分支：`main` = 仅框架（`works/` 仅 tracked README；用户侧脚手架 = `users/_template/`）；`extraction/{work_id}` = 单作品进行中抽取（仅本地）；`library` = 完成抽取的归档（仅本地，squash-merge 目标，经 `[git].squash_merge_target` 可配）。
空闲 = `main`。编排器在 Phase 0（第一次 LLM 调用）之前 checkout 抽取分支，全部五个 phase 都在其上运行，无例外；任何退出路径经 `run_full`（fresh-start 外层）/ `run_extraction_loop`（resume 内层）的 `try/finally: checkout_main(...)` 回 `main`。`checkout_main` / `preflight_check` 接受 `scope_paths=["works/{work_id}/"]`——仅 scope 内脏文件阻断。
框架提交（代码 / schema / prompt / 文档 / `ai_context/`）先进 `main` 再 `git merge main` 到其他分支；抽取数据提交只属于抽取分支。所有 stage `COMMITTED` 后 `_offer_squash_merge` 交互式 squash-merge 到 `library`（永不进 `main`），随后交互式询问（`[y/N]` 默认 N，即使 `auto_squash_merge=true` 也询问）删除源分支 + `git gc --prune=now`。`library` 周期性 `git merge main` 吸收框架更新，永不回流。
异常防护：holo 插件 SessionStart hook（`scripts/session_branch_check.sh`，经插件 hooks.json 注册）会话启动打印分支横幅，永不阻断启动。
详情 → `docs/architecture/extraction_workflow.md` §自动化编排（分支纪律段）+ `docs/decisions.md` #26。

## 自动化抽取流水线

编排器 `extraction/persona_extraction/`：每步 = 全新 `claude -p` / `codex` 调用（无共享会话，文件传上下文）；双模式由来源 manifest `structure_mode`（schema 必填）决定 `monolithic` / `light_novel`，Phase 2+ 不分支——`stage_plan` 是下游唯一契约。
- **Phase 0** chunk 摘要并行（3 级 JSON 修复 + schema 门控 + `effort='high'` 恢复扫尾，#49）→ **Phase 1** fan-out lane（monolithic 3 / light_novel 2 + 程序化 stage_plan；foundation lane 直产 `world/foundation/foundation.json`，#52/#54）→ **Phase 1.5** 用户确认角色 + 阶段（推荐 = `importance == "主角"`，#53）。
- **Phase 2** baseline 2+2N lane fan-out（lane A `key_figures` 替换先行串行，`fixed_relationships` + 每角色 `identity`+`manifest` / `target_baseline` 两 lane 并行，输入按 lane 投影裁剪；per-lane repair 缩水版——T0/T1 + 程序 checker，无 regen，终点 `validate_baseline` 安全阀，#59；phase 3 三 target 结构与 baseline 双向相等硬门控；重写有 phase 3 产物前置 guard，#56）→ **Phase 3** 逐 stage 1+2N 并行 + char_snapshot 4 sub-lane（`snapshot_merge.py`，#55）+ per-file repair（3 tier T0/T1/T2，按 rule 路由到 `(start,max)` + 每 tier 封顶 2 次，单遍无整文件 regen；`$` 根锚点 issue 永不升 LLM 层（钳到 T0；本就起步 LLM 层的 → `NO_FIX_TIER` 直接 defer）——根补丁交给 LLM = 全文重写，即被删的 T3；T1/T2 patch 后均即时 scoped 复验才算 resolved；L3 gate 覆盖本轮全部被改文件，#62）+ PP 重跑 + commit SHA 非空才 `COMMITTED`（`defer_unresolved_semantic` 开时未决可延后类别 semantic/schema/structural/cross_file + coverage_shortage 残留写 `deferred_repairs/` 台账后当 PASS 继续，逐文件判定，仅 json_syntax / worker 崩溃硬停机，#60）→ **Phase 3.5** 程序化一致性检查（error 阻断）→ **Phase 4** 场景归档（独立，仅需 `stage_plan.json`；`--start-phase 4`）。
- 关键设计：lane 级 resume + 启动磁盘 reconcile 自愈；`RateLimitController` token 限额自动暂停（`docs/requirements.md` §11.13）；长度容差门控最终安全阀（#48）；`--resume` phase 无关续跑 + `--background` 校验（#51/#56）；配置单源 `extraction/config.toml`（CLI > local > toml > 默认）；run 指标账本 `core/run_metrics.py`（`run_with_retry` 单点每调用落 `logs/runs/{work_id}_{ts}.jsonl` 时间/token/cost，`set_phase` 标注 phase，run 末聚合表；best-effort no-op）。
→ `extraction/README.md` + `docs/architecture/extraction_workflow.md`；schema → `docs/architecture/schema_reference.md`。

## 运行时 / 入口点 <!-- holo:heading -->

- 抽取入口：`python -m extraction.persona_extraction`
  （`extraction/persona_extraction/__main__.py` → `cli.py`；配置
  `extraction/config.toml`）。
- `simulation/` 无任何运行时代码 —— 全部为 .md 契约 / 流程 /
  检索策略文档（`contracts/` / `flows/` / `retrieval/` /
  `prompt_templates/`），运行时角色扮演引擎尚未实现。
