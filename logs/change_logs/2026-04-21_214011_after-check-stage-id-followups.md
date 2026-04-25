# /after-check 补齐：stage_id 英文化后的遗漏更新

## 背景

紧接 commit 1573506（stage_id 统一为 `S###` + 新增 `stage_title`）之后
的 `/after-check` 复审，发现 3 条 High + 4 条 Medium 的跨文件未对齐。
本次 `/go` 按 `/after-check` 推荐逐条修复。Residual Risks 按用户指示
跳过。

## 改动清单

### H1 — `schemas/README.md`

命名规则提醒区：把 `stage_id` 从"对中文作品…也可以直接使用中文"那
条里拆出来，单独一条写明"`stage_id` 始终使用 `S###`，与 `M-S###-##` /
`E-S###-##` / `SC-S###-##` / `SN-S###-##` 共享 stage 段，人类可读短
标题由 `stage_title`（≤15 字）承载"。

### H2 / M2 — `docs/architecture/schema_reference.md`

- L59（work/stage_catalog）关键字段补全为 `stage_id、order、stage_title、
  summary、snapshot_path`，与 schema `required` 对齐。
- L78（world/world_stage_catalog）关键字段 `stages[].title` 改为
  `stages[].stage_title`（≤15 字），反映 schema 字段改名。

### H3 — `docs/architecture/data_model.md`

L321 原句"对于中文作品，`{stage_id}` 路径片段也应直接使用规范的中文
stage 标识符"改为"`{stage_id}` 路径片段统一使用紧凑英文代号 `S###`"，
并注明 `stage_title` 仅出现在 catalog/plan 条目，不进入文件路径。

### M1 — orchestrator stage header 打印

`automation/persona_extraction/progress.py`

- `StageEntry` 新增 `stage_title: str = ""` 字段
- `to_dict` / `from_dict` 同步该字段；`from_dict` 对旧数据默认 `""`，
  保持向后兼容
- `Phase3Progress.expand_stages` 从 plan dict 读取 `stage_title`

三处 `StageEntry(...)` 构造全部追加 `stage_title=b.get("stage_title", "")`：

- `automation/persona_extraction/orchestrator.py:1024` — 首次创建 phase3 时
- `automation/persona_extraction/orchestrator.py:1928` — phase3 缺失时从
  stage_plan.json 重建
- `automation/persona_extraction/cli.py:244` — CLI 同样的 rebuild 路径

`automation/persona_extraction/orchestrator.py:178` print：
```python
title_suffix = f" — {stage.stage_title}" if stage.stage_title else ""
print(f"  [{n}/{self.total}] {stage.stage_id}{title_suffix}")
```
有 title 时打印 `S001 — 主角初登场`；没有时降级为 `S001`（兼容旧
phase3_stages.json 里 stage_title 缺字段）。

### M3 — `simulation/flows/bootstrap.md`

Step 3 "choose active `stage_id`" 加括号注释"user-facing picker shows
`stage_title`; the compact `S###` code is the stored value"，点明
stage 选择 UX 展示 stage_title，落库值是 stage_id。

### M4 — `ai_context/requirements.md`

§2 Stage Model 末尾补一条 `stage_id` = 紧凑英文代号 `S###` + `stage_title`
≤15 字的 naming 规则，对齐 `docs/requirements.md` §11.9。

## 验证

- `python -c "from automation.persona_extraction.progress import StageEntry, Phase3Progress; ..."`
  通过；`to_dict` / `from_dict` 往返正确；旧 dict（无 `stage_title`）
  `from_dict` 后默认 `""`。
- `automation.persona_extraction.orchestrator` / `cli` import 成功。
- `schemas/work/stage_catalog.schema.json` / `schemas/world/world_stage_catalog.schema.json`
  `Draft202012Validator.check_schema` PASS（本次文档改动没碰 schema
  文件本身，但顺手验一下 schema 仍合法）。
- 全仓 grep `stages[].title` / `stage_id.*直接使用中文` / `中文 stage
  标识符` / `{stage.stage_id} ({stage.stage_id})` 全部无命中。

## 不动的区域

- `schemas/**/*.schema.json`：pattern / 字段名本轮未再改（都在 1573506
  已完成）。
- 历史 log / review_reports：保留原 `阶段NN_<slug>` 字样。
- `post_processing.py:402` 的 `snapshot_data.get("stage_title", stage_id)`
  fallback：按用户指示归在 Residual Risks，本轮不动。
- 已写出的 phase3_stages.json 里旧条目 `stage_title` 保持空；orchestrator
  打印时会降级为只显示 `S###`，下次从 stage_plan 重建时自然回填。

## 独立 commit

本改动走 `/go` 流程、独立一次 commit、独立 log。
