# 2026-04-20 codex audit follow-up — H1 / M2 / M3 / M5 / R1 / R2

## 背景

`docs/review_reports/2026-04-20_142956_codex_repo-alignment-audit.md` 出来后
先跑 `/review-check codex` 做真实性复核。确认 H1 / M2 / M3 / M5 / R1 / R2
均是真实 finding，按用户裁决：

- H1、M2、M3、M5、R1、R2：本轮修。
- M4（users/ inline vs. sidecar）：simulation 端未落地 → 登记
  `[T-USER-DATA-FORMAT]` 推迟。
- R3（users/ 辅助文件 schema）：阻塞于 M4 → 登记 `[T-USER-AUX-SCHEMAS]`。

用户额外裁定两条关键细节：

- M2 tie-break：子串匹配多命中时，**最重要优先 → 次选最长 `character_id`**。
- R1：同时加"最多 300 字硬门控 + L2 存在性 warning"，配置值要进 toml。

## 改了什么

### H1 — 外部擦盘安全网覆盖 PASSED 分支

原先只有 REVIEWING → PENDING 这条恢复路径检查 `_extraction_output_exists`；
PASSED 态 --resume 直接跳到 `git add -A works/` + commit，**外部删文件会被
当成合法变更一起 stage**，poison extraction 分支。

改动：`automation/persona_extraction/orchestrator.py` PASSED 分支
（~L1341）在进入 git commit 前先跑 `_extraction_output_exists`；
缺失时走 `PASSED → FAILED → ERROR`，`error_message` 明示 "refusing to commit
deletions"，`fail_source="external_delete"`，操作者恢复后再 --resume。

同步：REVIEWING 分支（~L1574）原本用"目录存在"判据，现也改成
`_extraction_output_exists` 的全文件校验，统一口径。

### M2 / R1 — validator 抽共享 helper + 结构检查加关系摘要

新抽两个公共函数 `automation/persona_extraction/validator.py`:

- `importance_for_target(target, importance_map) -> str`：子串匹配
  （`character_id in target`），多命中按 `(rank, len(char_id))` 取最大。
- `importance_min_examples(importance) -> int`：主角→5、重要→3、其他→1。

原 `_importance_threshold`（repair_agent/structural）+ 原
`_min_examples_for_target`（consistency_checker）都改 delegate 过去，单一
真相。

`StructuralChecker` 构造器增加 `relationship_history_summary_max_chars=300`：

- 缺失/空串 → `relationship_history_summary_non_empty` warning。
- 长度 > max → `relationship_history_summary_max_length` error（阻塞
  COMMITTED）。

`RepairConfig` / `RepairAgentConfig` / coordinator `run()` / `validate_only()`
/ `_build_pipeline()` 全链路透传 `relationship_history_summary_max_chars`；
`orchestrator.run_repair(...)` 读 `ra_cfg.relationship_history_summary_max_chars`
注入。

### M5 — baseline prompt 补两份 stage_catalog schema

`automation/persona_extraction/prompt_builder.py` baseline 必读 schema 列表
补 `world_stage_catalog.schema.json` 和 `stage_catalog.schema.json`——否则
LLM 产出的空 catalog 结构形同瞎猜。

### M3 — README 状态机对齐 progress.py docstring

`automation/README.md` 原状态机图失配：漏标 `post_processing` 节点和
`passed → failed → error` 边。现逐字同步 `progress.py` 顶部 docstring。

### R2 — consistency_checker 加 scene_refs 空值 warning

`automation/persona_extraction/consistency_checker.py::_check_evidence_refs_coverage`
对 memory_timeline 每条 entry 除 `evidence_refs` 外同步检查 `scene_refs`；
空集发 warning（`category="scene_refs"`），不阻塞提交但 runtime recall
会因此走退化路径。

## 涉及文件

### 代码 / schema / 配置

- `automation/persona_extraction/orchestrator.py`（H1 两处 +
  run_repair 传参）
- `automation/persona_extraction/validator.py`（新 helper）
- `automation/persona_extraction/consistency_checker.py`（delegate +
  scene_refs warn）
- `automation/persona_extraction/prompt_builder.py`（M5 schema 注入）
- `automation/persona_extraction/config.py`（`RepairAgentConfig` 增字段）
- `automation/persona_extraction/progress.py`（`fail_source` 枚举注释扩展）
- `automation/repair_agent/checkers/structural.py`（引入 helper +
  relationship_history_summary 校验）
- `automation/repair_agent/coordinator.py`（透传参数）
- `automation/config.toml`（新增 `relationship_history_summary_max_chars`）
- `schemas/stage_snapshot.schema.json`（`maxLength: 300`）

### 文档 / prompt

- `automation/README.md`（状态机对齐）
- `automation/prompt_templates/character_snapshot_extraction.md`（摘要
  长度提示）
- `ai_context/conventions.md`（Length rules 表加一行）
- `docs/architecture/schema_reference.md`（relationships 行 + fail_source
  枚举 + relationship_history_summary L2 兜底）
- `docs/architecture/extraction_workflow.md`（失败保留契约覆盖 PASSED
  分支）
- `docs/requirements.md`（§11.4 L2 列表补 relationship_history_summary +
  新增 "target_type 与 character_id 的匹配规则" 子节）
- `docs/todo_list.md`（登记 `[T-USER-DATA-FORMAT]` 与
  `[T-USER-AUX-SCHEMAS]`）

## 为什么这么做

- H1 是 data-integrity 级的隐患（poison extraction 分支），成本极低
  （只是多一次本地文件校验）。用户确认"改动后不会增加 LLM 占用"——确实
  只是 `Path.exists()` + `json.loads()`。
- M2 / R1 放一组 commit：共享 helper 必须先落，才能让两处调用方
  （structural + consistency_checker）同步切换；不拆就不会串味。
  tie-break 规则解决 `张三` / `张三丰` 这类真实二义性，避免高 importance
  角色被低阈值误判。
- R1 双重防御（schema + L2）与仓库其他字段（`stage_events` / `knowledge_scope`）
  一致；配置化便于未来调优。
- M5 缺 schema 属于系统性疏漏，补两行即可；留白成本远低于调查的时间。
- M3 纯文档失配；READMEs 是 onboarding 第一手材料，不能骗人。
- R2 是运行时体验防退化，warning-only 不扰动 COMMITTED。

## 验证

- Schema：`jsonschema.Draft202012Validator.check_schema` pass；
  `works/.../stage_snapshots/阶段01*.json` 现状仍合规。
- Python imports：`validator` / `structural` / `coordinator` /
  `orchestrator` / `config` 全链路可导入无错。
- 功能 smoke：`importance_for_target` 对 `主角A（某阶段）`
  / `张三` / `张三丰` 三类场景命中预期；`importance_min_examples` 三档
  数值正确。
- 全库扫描：进一步发现 `progress.py` 与 `schema_reference.md` 的
  `fail_source` 枚举注释残留，现已补 `external_delete`。
