# post_check_followup_dynamic_bound

- **Started**: 2026-05-01 10:08:57 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

前一轮 `/post-check` 复审 `post_check_followup_ingest_structure_mode` 给出
REVIEWED-PARTIAL，1 Medium + 2 Low：

- **[M]** `automation/persona_extraction/orchestrator.py:937 _STAGE_TITLE_MAX = 80`
  硬编码 schema bound，违反 `decisions.md §27b`（Bounds-only-in-schema）。§27b
  仅 grandfather 一条 `StructuralChecker.relationship_history_summary_max_chars`
  fallback；新加的 `_STAGE_TITLE_MAX` 是第二条未登记的 fallback。schema 端 80
  改动后代码不会自动同步——schema 收紧时复发无穷重试 FATAL，schema 放宽时静默
  丢失截断信息。
- **[L]** `docs/todo_list.md:449` In Progress body 「已落地」段写
  `stage_title.maxLength 14→50`，本轮已 50→80，累计应为 14→80
- **[L]** `docs/architecture/extraction_workflow.md:71` +
  `ai_context/architecture.md:155` 描述 light_novel `stage_title =
  chapter_index[i].title` 直接赋值，未提及代码层软截断兜底

用户：「修复 M」 → 同时把 2 个 L 一并修，免得多轮往返。

## 结论与决策

### M 修法（推荐项 1：动态读取 schema）

orchestrator 启动时从 `schemas/analysis/stage_plan.schema.json` 解析
`stages.items.properties.stage_title.maxLength`，取代硬编码 `80`：

- 复用既有 `_load_analysis_schema("stage_plan.schema.json")` 路径——schema 已
  在 `_stage_plan_validator()` 启动时通过 `schema_loader.load_schema` 加载
- 加 `@_lru_cache(maxsize=1)` 模块级 helper `_stage_title_max_length()`，从
  loaded schema dict 抽取 maxLength 整数，做防御性 fallback（schema 路径意外
  缺失则降回 80 + 打 warning，确保不阻断流水线）
- `_build_light_novel_stage_plan` 调用 `_stage_title_max_length()` 替代类常量
  `_STAGE_TITLE_MAX`；类常量删除
- 这样 schema 是真单源——bump 80→N 后代码自动跟进

### L1 修法

`docs/todo_list.md:449` 文字 `14→50` → `14→80`（累计反映）。

### L2 修法

`docs/architecture/extraction_workflow.md:71`：light_novel `stage_title`
描述末加注「（超 schema cap 由 orchestrator 软截断 + `…` 兜底）」。
`ai_context/architecture.md:155`：同步加同样注。

## 计划动作清单

Code：

- file: `automation/persona_extraction/orchestrator.py`
  - 加 module-level helper `_stage_title_max_length()`，`@_lru_cache(maxsize=1)`，
    从 `_stage_plan_validator()` 已加载的 schema 中读 `stages.items.properties.
    stage_title.maxLength`；缺失则 fallback 到一个常量 `_STAGE_TITLE_FALLBACK_MAX
    = 80` + `print("[WARN] ...")`
  - `ExtractionOrchestrator._STAGE_TITLE_MAX` 类常量删除；`_build_light_novel_stage_plan`
    调用 `_stage_title_max_length()` 拿 cap

Docs：

- file: `docs/todo_list.md:449` —— `14→50` → `14→80`
- file: `docs/architecture/extraction_workflow.md` light_novel stage_title 描述
  加软截断注
- file: `ai_context/architecture.md` Phase 1 描述加软截断注

ai_context：

- file: `ai_context/decisions.md::§27l` —— 把 "schema cap (currently 80)"
  改为 "schema cap (read at orchestrator startup from
  `stage_plan.schema.json`)"，反映动态读取
- 不动 §27b 例外列表（避免新增 fallback；动态读取后**没有**第二条 fallback
  需要登记）

## 验证标准

- [ ] schema 校验：所有 schema 通过 `jsonschema.check_schema`
- [ ] code smoke：`_stage_title_max_length()` 从 schema 读出 80（与 schema 实际
  值一致）
- [ ] code smoke：临时 monkey-patch schema maxLength=60，`_stage_title_max_length()`
  应读出 60（证明动态跟进，不再硬编码）。lru_cache 清理后再读
- [ ] code smoke：`_build_light_novel_stage_plan` 派生 100 字符 title 时，截断到
  schema cap（默认 80）+ `…`；派生 plan 仍通过 stage_plan schema
- [ ] orchestrator import 无报错
- [ ] grep 残留：`_STAGE_TITLE_MAX = 80`（硬编码字面量）= 0（除 fallback 常量
  外）
- [ ] grep 残留：本次 diff 不引入 legacy / 旧 / 已废弃 / 原为 / renamed from

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

Code（1 文件）：

- `automation/persona_extraction/orchestrator.py`
  - 新增 module-level `_STAGE_TITLE_FALLBACK_MAX = 80`（仅 fallback 用，
    schema 路径漂移时降级 + WARN，不参与日常路径）
  - 新增 `@_lru_cache(maxsize=1) _stage_title_max_length() -> int`，从
    `_stage_plan_validator().schema` 抽
    `properties.stages.items.properties.stage_title.maxLength`，做 isinstance(int) 与 cap > 1 防御
    校验；失败路径打 WARN + fallback；与 `_stage_plan_validator` 共用 lru_cache
    生命周期
  - `ExtractionOrchestrator._STAGE_TITLE_MAX = 80` 类常量删除
  - `_build_light_novel_stage_plan` 调用 `_stage_title_max_length()` 替代
    类常量，注释同步说明 §27b Bounds-only-in-schema 单源原则

Docs（2 文件）：

- `docs/todo_list.md` In Progress 当前状态字段更新（描述本轮第 2 轮残留修）；
  已落地段累计值 14→50 改为 14→80
- `docs/architecture/extraction_workflow.md` Phase 1 light_novel 段
  `stage_title` 描述末加软截断 safeguard 注

ai_context（2 文件）：

- `ai_context/decisions.md::§27l` "Code-side soft-truncation safeguard" 段把
  "schema cap (currently 80)" 改为 "schema cap (read dynamically at startup
  from `stage_plan.schema.json::stages.items.properties.stage_title.maxLength`
  via `_stage_title_max_length()`, preserving §27b single-source)"，反映动态
  读取
- `ai_context/architecture.md` Phase 1 light_novel 描述加软截断 safeguard 注

## 与计划的差异

无。1 项 M（dynamic schema cap）+ 2 项 L（todo_list 累计 + flow docs 软截断
注）按 PRE 计划清单逐条落地。

## 验证结果

- [x] schema 校验：所有 schema 通过 `jsonschema.check_schema`（smoke 6）
- [x] code smoke：`_stage_title_max_length()` 从 schema 读出 80（与 schema
  实际值一致）（smoke 1）
- [x] code smoke：monkey-patch schema maxLength=60 + cache_clear 后 →
  `_stage_title_max_length()` 读出 60；恢复后再读出 80（smoke 2+3，证明真动态
  跟进、不再硬编码）
- [x] code smoke：`_build_light_novel_stage_plan` 派生 100 字符 title 时截断到
  80 字符 + `…`；短 title 不变；派生 plan 通过 stage_plan schema（smoke 4+5）
- [x] orchestrator import 无报错（smoke 8 + 既有链）
- [x] grep 残留：`_STAGE_TITLE_MAX` 字面（除 `_STAGE_TITLE_FALLBACK_MAX`
  fallback 常量）= 0；`hasattr(ExtractionOrchestrator, "_STAGE_TITLE_MAX")` =
  False（smoke 7）
- [x] grep 残留：本次 diff 不引入 legacy / 旧 / 已废弃 / 原为 / renamed from
  （0 hits）

## Completed

- **Status**: DONE
- **Finished**: 2026-05-01 10:13:24 EDT
