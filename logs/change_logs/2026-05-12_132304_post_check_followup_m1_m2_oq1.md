# post_check_followup_m1_m2_oq1

- **Started**: 2026-05-12 13:23:04 EDT
- **Branch**: main
- **Status**: PRE → POST（合并；本轮 ≤10 行编辑，PRE/POST 不分离写）

## 背景 / 触发

上一轮 `/post-check`（log: `2026-05-12_121225_pipeline_resume_alignment_fixes.md`，
REVIEWED-PARTIAL）报出 2 项 Medium + 1 项 Open Question，用户拍板"修复
M1 / M2 / OQ1"。本轮即落地这三项小修补，单 commit 收口。

## 结论与决策

- **M1**：`automation/README.md:394` 与本次 `/go` Step 7 已修的 3 处（
  `ai_context/architecture.md:155 + :172` + `docs/architecture/extraction_workflow.md:83`）
  逐字同源 "原 `analysis/world_overview.json` 路径已废弃"，违反
  `ai_context/conventions.md` §3 no-legacy。改写为"foundation 由 phase 1
  直接产到 world 域"纯当前设计描述。
- **M2**：`docs/architecture/schema_reference.md:182` "原
  `analysis/world_overview.schema.json` 已删除" 同类违反；改写为"schema
  归位 `schemas/world/` 域"。
- **OQ1**：`orchestrator.py:2214` `preset_end_stage = int(raw) if raw
  else None` 缺 ValueError 兜底（pre-existing）。前台用户输入 "abc" 会
  traceback。daemon 路径走 EOFError → `raw=""` → falsy → None 不触发。
  本轮加 try/except ValueError + 一行 `[WARN]` print + fallback 到 None
  = all stages，避免 fat-finger crash。

## 计划动作清单

- file: `automation/README.md:394` → 删 "原 ... 已废弃" 改写
- file: `docs/architecture/schema_reference.md:182` → 删 "原 ... 已删除" 改写
- file: `automation/persona_extraction/orchestrator.py:2202-2214` →
  `int(raw)` 套 try/except ValueError + [WARN] print

## 验证标准

- [x] `from automation.persona_extraction.orchestrator import
  ExtractionOrchestrator` import 过
- [x] `grep "原.*world_overview\|world_overview.*已废弃\|world_overview.*已删除"`
  排除 logs/ + decisions.md 决策叙事 → 0 残留
- [x] ValueError 兜底逻辑模拟验证：empty → None / "0" → 0 / "5" → 5 /
  "abc" → fallback to None（[WARN] 一行 print）

## 执行偏差

无。

## 已落地变更

- `automation/README.md:394` — 删 "原 `analysis/world_overview.json` 路径
  已废弃"；改写为 "foundation 由 phase 1 直接产到 world 域，phase 2 仅补
  `major_factions[].key_figures`"
- `docs/architecture/schema_reference.md:182` — 删 "原
  `analysis/world_overview.schema.json` 已删除，内容合并入 foundation
  schema"；改写为 "schema 归位 `schemas/world/` 域"
- `automation/persona_extraction/orchestrator.py:2202-2222` — 把
  `preset_end_stage = int(raw) if raw else None` 套进新增的 `try:` 块，
  `except ValueError:` 时 print `[WARN] '<raw>' is not a number —
  defaulting to all stages (no limit).` + `preset_end_stage = None`

## 与计划的差异

无。

## 验证结果

- [x] orchestrator.py import — `orchestrator import OK`
- [x] grep 残留扫描 — 0（除 logs/ + ai_context/decisions.md 决策叙事自述）
- [x] ValueError 兜底语义 4 case：empty → None / "0" → 0 / "5" → 5 /
  "abc" → ('FALLBACK', None)

## Completed

- **Status**: DONE
- **Finished**: 2026-05-12 13:23:04 EDT
