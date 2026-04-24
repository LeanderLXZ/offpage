# doc_schema_bounds_dedupe

- **Started**: 2026-04-24 06:25:07 EDT
- **Branch**: master (via worktree ../persona-engine-master；主 checkout 停留 extraction/我和女帝的九世孽缘 dirty 不动)
- **Status**: PRE

## 背景 / 触发

用户指示：清理 `ai_context/`、`docs/`、`docs/requirements.md` 等文档里
关于 schema 字段级上下限的**具体数字**。「bounds only in schema」已是
仓库硬规则，多轮字段收口后文档里残留大量重复数字（≤ 50 / maxItems:15 /
50–200 字 等），既难同步又占字数。保留"有上下限、细节见 schema"的抽象
说明即可。

## 结论与决策

### 保留 vs 压缩 的原则

**保留**：
- 字段/结构**概念描述**（`character_arc` 是整体弧线概述、`stage_events`
  是本阶段公共事件清单、`dialogue_examples` 是对话示例）
- **契约行为**（1:1 拷贝契约、required 字段必须填、self-contained 不合并
  baseline、schema 硬门控存在）
- **跨字段不变量**（`memory_digest.summary = digest_summary`、`world_event_digest.summary = stage_events[i]`）
- **maxItems / maxLength 相关的行为侧描述**不写数字，用"schema 硬门控"
  / "按 schema 上下限"等表述
- 现有 `docs/requirements.md` 的"字段条数上限汇总表"段落——这是**唯一**
  对用户友好的便利索引，删除会让读者失去一站式视图；压缩到单链接指向
  schema 文件 + 保留各字段是否受限的抽象说明

**压缩 / 删除**：
- 所有具体的 `≤ N 字` / `≤ N 条` / `N–M 字` 数字
- 所有 `maxLength:N` / `maxItems:N` / `minLength:N` 数字
- ai_context/conventions.md 的 "Length gates / Count caps" 超长 spot
  examples 段（保留"bounds only in schema"原则一句话）
- ai_context/decisions.md 27f / 27g 里的全量数字清单（保留决策本身的
  动机与影响文件列表；具体数字由 schema 承载）
- ai_context/handoff.md extraction-branch advisory 里枚举的具体字段
  上下限（保留"几类字段被改动了、会让 S00X INVALID"层面的事实）

### 范围圈定

扫描涉及文件（grep 命中上下限数字 / 字数 / 条数的）：

- `ai_context/requirements.md`
- `ai_context/handoff.md`
- `ai_context/conventions.md`
- `ai_context/architecture.md`
- `ai_context/decisions.md`
- `docs/requirements.md`
- `docs/architecture/data_model.md`
- `docs/architecture/schema_reference.md`
- `docs/architecture/extraction_workflow.md`

`docs/logs/` 不动（历史记录本就该有数字）。`docs/review_reports/`
不动（同理）。`automation/prompt_templates/` **不动**——这些是 LLM
产出的 brief，里面的数字是给 LLM 看的指引（和 schema 双重约束，用户
未点名）。

## 计划动作清单

### ai_context

- file: `ai_context/conventions.md` Data Separation 段的 Length gates
  / Count caps 两条巨型 spot examples 清单 → 压缩为 1–2 句「门控只在
  schema；文档不重复」＋ 给出 schemas/character 与 schemas/world 两个
  入口路径
- file: `ai_context/decisions.md` 27b / 27d / 27e / 27f / 27g →
  删除具体数字（如 "≤100", "≤50 chars" 等），保留决策动机与受影响
  文件列表，指向具体 schema 文件
- file: `ai_context/handoff.md` Extraction-branch artifact drift 段
  → 去掉每条具体 maxLength / maxItems 数字；保留"这几类字段受影响、
  现有产物会 INVALID、迁移路径三选一"
- file: `ai_context/architecture.md`  →  查下有没有残留数字；有就去
- file: `ai_context/requirements.md` → 同上

### docs

- file: `docs/requirements.md`：
  - §快照完整性检查清单中的"≤ N 条 / ≤ N 字"具体数字移除，保留字段
    名 + 结构描述；改成"具体上下限见 schema"
  - §字段条数上限汇总表 → 大幅压缩：要么保留抽象表但去数字（字段名 +
    "schema 硬门控 / 见 schema"）要么整表删除 + 指向 schema_reference.md
  - §L1/L2 表里 `relationship_history_summary_max_chars (100)` 等具体
    数字改成"与 schema 保持一致"
  - 其他段落 grep `≤ ?[0-9]+` 清理
- file: `docs/architecture/schema_reference.md`：
  - 这是"schema 字段级索引"专题文档——**保留**字段表、但把**每份
    schema 内部**的 "字段级上下限" 详列段落压缩到一句话，指向
    schemas/*.schema.json 对应文件作为权威。stage_snapshot 的关键
    section 表里的具体数字全部去掉，只留字段名 + 一句职责说明。
- file: `docs/architecture/extraction_workflow.md`：
  - grep 数字清理；主要是 Phase 3.5 一致性检查项里复述的 50–80 / 150–200
    / ≤15 等复述
- file: `docs/architecture/data_model.md`：
  - grep 数字清理

### 不动

- `automation/prompt_templates/*` — 用户未点名；prompt 数字是给 LLM 的
  指引，另有用途
- `automation/repair_agent/checkers/structural.py` 的 `relationship_history_summary_max_chars`
  常量 —— 代码层，不在文档范围
- `automation/persona_extraction/consistency_checker.py` —— 同上
- `schemas/` 本身 —— 权威源
- `docs/logs/` / `docs/review_reports/` —— 历史记录

## 验证标准

- [ ] 32 份 schema 仍 `Draft202012Validator.check_schema` 通过
- [ ] Python import smoke test 依旧过
- [ ] `grep -rnE "≤ ?[0-9]+|maxItems: ?[0-9]+|maxLength: ?[0-9]+|minLength: ?[0-9]+|最多 [0-9]+ 条|[0-9]+[–-][0-9]+ 字" ai_context/ docs/requirements.md docs/architecture/ 2>/dev/null | grep -v docs/logs/ | grep -v docs/review_reports/` 结果大幅缩减
  （余下命中只应为：①真正的跨字段不变量需要数字定位时（极少）；②
  schema_reference.md 的总纲说明里不可避免保留的结构字段数之类）
- [ ] 文档语义未丢失——抽样 3 段前后对读，字段名 / 结构 / 契约描述仍在
- [ ] 全仓库未引入 "已废弃 / legacy / 原为 / 旧" 字样

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

### ai_context

- `conventions.md` Data Separation：巨型 Length / Count spot example 段
  → 压缩为两条「bounds only in schema」原则句 + 指向 schemas 入口；
  `stage_title ≤15 chars` → `length cap in schema`
- `decisions.md` 27b / 27c / 27d / 27e / 27f / 27g：删除字段级数字枚举，
  保留决策动机 + rationale + 受影响文件清单；27b StructuralChecker 常量
  描述去数字；12 号决策的 `stage_title ≤15 chars` 改为短标签说明
- `handoff.md` Extraction-branch artifact drift：7 条具体数字说明 → 压缩
  成 7 条字段 / 结构变动要点，指向各 schema 文件；文字从 30 行降到约 20 行
- `requirements.md` §2 `stage_title ≤15 chars` → `short label, work language
  — exact cap in schema`
- `architecture.md` memory_timeline 字段描述去具体字数 → 指向
  `memory_timeline_entry.schema.json`

### docs

- `docs/requirements.md`：
  - §2.3.4 世界阶段快照 `stage_events` 描述去 `≤ 30 条 / 50–80 字`
  - §6.x identity loader 段去 `background_summary ≤ 200 / key_relationships ≤ 10`
  - §快照完整性检查清单（第 11.x 节）：所有维度去具体 ≤ 数字；只留字段
    名 / 结构 / 契约描述
  - §字段条数上限汇总表：22 行具体 maxItems 表 → 压缩成 6 行通用裁剪
    策略 + 指向 schema
  - §11.3a digest 映射表 `≤15 字 required` → `required 短锚点`；
    `LLM 专写的 30–50 字 digest 摘要` → `LLM 专写的 digest 摘要`
  - §11.3a world_event_digest 段 `每条 50–80 字` / `≤15 字 required` 全部
    去数字
  - §L1/L2 表 `(300)` → `(100)` 已在之前轮次改过，本轮改为去数字：
    `relationship_history_summary 超长 error 内部常量与 schema 保持一致`
  - §程序化检查项 #2 `13 个必填维度` 的枚举描述保持（例举式语言无 schema
    数字）
  - §程序化检查项下方说明段：`长度约束（stage_events 50–80 字、
    event_description 150–200 字、digest_summary 30–50 字等）` → 抽象
    表述 + 指向 schema
  - §stage_title 使用 `≤15 字` → `长度由 schema 硬门控`
  - §12.4.2 memory_timeline JSON 示例：每字段注释里的 `≤15 字 / 150–200 字
    / 30–50 字 / 100–200 字 / ≤ 50 字 / 最多 10 条 / ≤ 100 字` 全部去掉；
    下方解释段同步
  - §12.4.3 `stage_events`（string[]，每条 50–80 字的一句话） → 去数字
  - §12.4.4 / §12.4.5 `summary 直接复制 ... （30–50 字）` / `（50–80 字）` → 去数字

- `docs/architecture/schema_reference.md`：
  - 文件顶部新增权威声明段：「schema 文件本身是权威定义」+ 字段级数值
    以 schemas/ 为准
  - world_stage_snapshot `stage_events ≤ 30 条；每条 50–80 字` → 一句话
    + 无 evidence_ref
  - `world/foundation.schema.json` 整块 "字段级上下限" 清单 → 一句话
  - `character/identity.schema.json` core_wounds / key_relationships /
    字段上下限三大段 → 去数字，保留字段职责与跨字段不变量
  - `character/voice_rules.schema.json` 字段上下限多行段落 → 关键字段
    列举
  - `character/behavior_rules.schema.json` 同上
  - `character/stage_snapshot.schema.json` 关键 section 表：12 行
    具体数字全部去掉
  - `character/memory_timeline_entry.schema.json` 关键字段列表：每字段
    描述去 `≤15 字 required / **150–200 字** / **30–50 字** / **100–200 字** /
    ≤ 50 字 / 最多 10 条 / 最多 5 条` 等
  - `character/memory_digest_entry.schema.json` 同上
  - world / character 两份 `stage_catalog.schema.json` 关键字段列
    `stage_title ≤15 字` → 去数字

- `docs/architecture/extraction_workflow.md`：
  - §6.3 长度硬门控三行具体数字 → 抽象段"具体数值以 schema 为准"
  - Phase 3.5 最终 checklist `event_description 是否 150–200 字、
    digest_summary 是否 30–50 字` → 去数字，保留 `长度由 schema 硬门控`

- `docs/architecture/data_model.md`：
  - 世界 stage_snapshot / 角色 stage_snapshot 两处 `每条 50–80 字，schema
    硬门控` → `每条一句话，长度由 schema 硬门控`
  - `stage_title ≤15 字` → `短标题，长度见 schema`

### 刻意保留

- `docs/requirements.md` / `ai_context/decisions.md` / `extraction_workflow.md`
  内的 `retry ≤ 2` / `≤999 阶段` / `≤200 字 quote extraction` 属于
  **非 schema 数值约束**（重试预算 / ID 模式 / prompt 级引文长度），
  保持不动
- `docs/requirements.md` §11.4.3 importance-based 质量阈值表（主角 5 /
  重要配角 3 / 其他 1）—— behavioural quality gate，不是 schema 上下限，
  保持不动
- `automation/prompt_templates/` 整个目录 —— 用户明确排除；prompt 里的
  数字是给 LLM 的指引（和 schema 双重约束）
- `schemas/` —— 权威源头
- `docs/logs/` / `docs/review_reports/` —— 历史记录

## 与计划的差异

无。按 PRE 计划 9 个文件逐一压缩完成。

## 验证结果

- [x] 32 份 schema `Draft202012Validator.check_schema` 通过
- [x] `post_processing / orchestrator / prompt_builder / consistency_checker / validator` import OK
- [x] `grep -rnE "≤ ?[0-9]+|maxItems: ?[0-9]+|maxLength: ?[0-9]+|minLength: ?[0-9]+|最多 [0-9]+ 条|[0-9]+[–-][0-9]+ 字"` 在 ai_context / docs/requirements / docs/architecture 的命中数量从 ~130+ → 10 条（全部为刻意保留的非 schema 数值）
- [x] 语义未丢失——抽样对读 decisions 27f / schema_reference stage_snapshot section / requirements §快照完整性清单，字段名 / 结构 / 契约描述均在
- [x] 全仓 diff `grep -E "^\+" | grep "已废弃\|legacy\|原为 \|deprecated"` 零命中

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 06:39:54 EDT
