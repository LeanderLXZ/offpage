# pipeline_resume_alignment_fixes

- **Started**: 2026-05-12 12:12:25 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

`/check-review codex` 复核 codex (`gpt-5`) `pipeline-resume-alignment-audit`
报告（`logs/review_reports/2026-05-12_113619_gpt-5_pipeline-resume-alignment-audit.md`）。
5 条 finding（H1 / H2 / M1 / L1 / L2）逐条对照当前 HEAD 代码 / 文档，
全部确认为真实。原报告 M1 在用户追问 `--end-stage` 语义后被升级为
**M1'(A+B)**：根因是 `confirm_with_user` 内 EOFError 兜底把 empty 折成
0（baseline only），与 prompt 文案 "empty = all" + `--end-stage` flag
"omit = all" 设计同时矛盾，迫使 `--background` validator 过度保守强制
`--end-stage` 必填。

OQ1–OQ4 用户未逐条回应、说"开始修复吧"，按 system 指示 "make the
reasonable call and continue" 走推荐方案：

- **OQ1**：shape-based 短期 guard + 写入 `schema_version: 2` 字段（不
  在本轮做完整 version-only 迁移）
- **OQ2**：H2 默认 hard stop；`--reset-phase3-after-baseline-change`
  flag 留二期不实现
- **OQ3**：light_novel `chapter_count=1` schema 例外保留现状（不动）
- **OQ4**：H2 guard 同时覆盖 validation-triggered recovery 与
  `--start-phase 2 force_baseline` 路径；daemon (`--background`) 一律
  hard stop，前台（无 `--background`）打印警告 + 交互确认 `[y/N]`

## 结论与决策

### H1 — `PipelineProgress.load()` 误把当前 `phase_2` 当 legacy remap

- 改 [progress.py:175-200](../../automation/persona_extraction/progress.py#L175-L200)
  `load()`：进入 remap 循环前，检测 raw_phases 是否含 current-shape
  signature（`phase_1_5` 或 `phase_3_5` 任一存在）→ 视为 current，
  整体跳过 legacy remap，原样读入
- `save()` 写入 `schema_version: 2` 顶层字段；`load()` 优先按
  `schema_version >= 2` 跳 remap，shape-based 退为 v0 兜底（兼容
  存量未写 `schema_version` 的当前文件）
- 不动 `_LEGACY_PHASE_KEY_MAP` 内容；不动 `migrate_legacy_progress`

### H2 — Phase 2 validation-triggered baseline 重跑不阻 Phase 3 committed 产物

- 改 [orchestrator.py:2273-2295](../../automation/persona_extraction/orchestrator.py#L2273-L2295)
  + force_baseline 路径（line 2211-2236 入口）：在调用
  `self.run_baseline_production(...)` 之前插入 guard
- guard 逻辑：
  1. 读 `phase3_stages.json`：若任一 stage state == `COMMITTED` → 视为
     已有 Phase 3 产物
  2. 兜底磁盘信号：扫 `works/{wid}/world/stage_snapshots/*.json` 与
     `works/{wid}/characters/*/canon/stage_snapshots/*.json`
  3. 任一为真 →
     - daemon (`--background`，stdin=DEVNULL) → 打印 docstring §1918-1923
       的清理清单 + 退出码 1
     - 前台 → 同样打印清理清单 + `input("Continue and overwrite? [y/N]: ")`
       非 y 即退出
- guard 覆盖：validation-triggered recovery + force_baseline 两条路径
- 不实现 `--reset-phase3-after-baseline-change` flag（用户拒/二期）

### M1'(A+B) — `--end-stage` 语义贯通

- **Bug A**: [orchestrator.py:2125](../../automation/persona_extraction/orchestrator.py#L2125)
  `preset_end_stage = int(raw) if raw else None`（empty → None = 全跑，
  对齐 prompt 文案 "empty = all" + flag "omit = all" 设计）
- **Bug A**: [orchestrator.py:2116-2117](../../automation/persona_extraction/orchestrator.py#L2116-L2117)
  prompt 文案改无歧义：`"Extract up to stage N (total {N}; empty = all
  (no limit), 0 = baseline only): "`
- **Bug B**: [cli.py:271-284](../../automation/persona_extraction/cli.py#L271-L284)
  删除 phase_1_5 未 done 时对 `--end-stage` 必填的硬挡（保留
  `--characters` 必填）
- **Bug B**: [cli.py:248-264](../../automation/persona_extraction/cli.py#L248-L264)
  长注释同步：daemon 路径 EOFError → preset=None → 全跑（决策 #51 daemon
  prompt 防 deadlock 改成"prompt 兜底安全 default = 全跑"）
- **Doc**: cli.py:159-164 `--background` help / `automation/README.md:145-151`
  / `docs/architecture/extraction_workflow.md:578-580` /
  `ai_context/architecture.md:172` 四处文案同步回 "phase_1_5 未 done →
  仅 `--characters` 必填；`--end-stage` 不传 = 全跑"
- **Test**:
  `automation/persona_extraction/_smoke_cli_resume_background_validation.py`
  C / D test case 翻转为 accept；G / H 保留 accept；I 不动

### L1 — `works/README.md` stage 最小章节数

- 改 [works/README.md:235](../../works/README.md#L235)：`最小 5 章` →
  `最小 8 章（monolithic 模式 schema 硬约束）；light_novel 模式由
  orchestrator 程序化派生 chapter_count=1，不走 schema validate`

### L2 — Phase 0 chunk size / summary length 注释漂移

- 改 [automation/config.toml:36-40](../../automation/config.toml#L36-L40) 注释：
  `25 章` → `20 章`；`100-150 字` → `150-200 字`；保留 1800s 数值（无
  证据说要重算），注释里写明按 20 章经验
- 改 [docs/architecture/system_overview.md:126](../../docs/architecture/system_overview.md#L126)：
  `约 25 章/组` → `约 20 章/组（CLI --chunk-size 默认；可调）`

## 计划动作清单

- **file**: `automation/persona_extraction/progress.py` → H1 load() shape
  guard + save() / load() 写读 `schema_version: 2`
- **file**: `automation/persona_extraction/orchestrator.py` → H2 guard 函数
  + 两条调用点；M1'A `preset_end_stage = int(raw) if raw else None` +
  prompt 文案
- **file**: `automation/persona_extraction/cli.py` → M1'B 删除 `--end-stage`
  必填 + 同步长注释 + 同步 `--background` help
- **file**: `automation/persona_extraction/_smoke_cli_resume_background_validation.py`
  → C / D test case 翻转
- **file**: `automation/README.md` → 同步 `--end-stage` 不再必填
- **file**: `docs/architecture/extraction_workflow.md` → 同步
- **file**: `ai_context/architecture.md` → 同步
- **file**: `works/README.md` → L1
- **file**: `automation/config.toml` → L2 注释
- **file**: `docs/architecture/system_overview.md` → L2 描述
- **file**: `ai_context/decisions.md` → 新决策条目（H2 guard 设计 +
  pipeline.json schema_version 启动）
- **file**: `docs/todo_list.md` → 登记 OQ3（light_novel schema 改造）
  + H2 二期 `--reset-phase3-after-baseline-change` flag

## 验证标准

- [ ] `python -c "from automation.persona_extraction.progress import PipelineProgress"`
  import 通过
- [ ] `python -c "from automation.persona_extraction.orchestrator import ExtractionOrchestrator"`
  import 通过
- [ ] `python -c "from automation.persona_extraction.cli import main"` import 通过
- [ ] H1 round-trip smoke：临时 `PipelineProgress(phases={phase_1_5: done,
  phase_2: done}).save()` → `load()` → 断言两 phase 都仍 `done`
- [ ] H1 legacy 兼容 smoke：构造无 `phase_1_5` / 含 `phase_2_5` 的旧
  shape pipeline.json → load → `phase_2_5` 正确 remap 为 `phase_2`、
  `phase_2` 正确 remap 为 `phase_1_5`
- [ ] M1'A smoke：直接 mock confirm_with_user 的 stdin → 模拟 daemon
  EOFError → `preset_end_stage is None`（不再 == 0）
- [ ] M1'B smoke：`_smoke_cli_resume_background_validation.py` C/D
  翻转后跑全套，全 pass
- [ ] grep 残留 = 0："最小 5 章" / "25 章/组" / "phase_1_5 not done →
  --characters and --end-stage" 在仓库中无残留
- [ ] H2 guard smoke：构造 `phase3_stages.json` 含 `state=committed` →
  调 guard → 返回 True（daemon 模式 sys.exit(1)）；空 phase3 → 返回
  False（pass through）

## 执行偏差

- PRE 阶段未列：`run_label` (orchestrator.py:2248) 在 preset_end_stage=0 时
  显示 "all" 而非 "baseline only" 是 pre-existing cosmetic bug，与本次
  `int → int | None` 改动相邻；Step 7 review 风险线 #5 提醒后顺手修复
  （`run_label` 三分支：None/0/positive）。
- PRE 阶段未列：`automation/config.toml:89` `max_turns` 注释仍写"Phase 0
  chunk 25 章"——本次 L2 只改了 line 36 同主题注释，Step 7 规范线发现 line 89
  漏修；顺手 25 → 20。
- PRE 阶段未列：`ai_context/architecture.md:155 / :172` +
  `docs/architecture/extraction_workflow.md:83` 三处 `"原 analysis/world_overview.json
  已废弃"` 违反 conventions.md §3 no-legacy 原则（pre-existing 漂移，决策 #54
  落地时未清理）；Step 7 规范线发现，三处一并改写为纯当前设计描述。
- Step 7 结构线建议补 `pipeline.json::schema_version` 字段表至 schema_reference.md
  / data_model.md / automation/README.md / works/README.md 4 处；评估后
  按 ai_context/conventions.md "Runtime 进度产物不入 durable 文档" 原则
  **不补**——决策 #56 已 mention schema_version 启动，progress.py 内部注释
  自述足够。不登记 todo。

## 已落地变更

- `automation/persona_extraction/progress.py` — `PipelineProgress.save()`
  写入 `schema_version: 2` 顶层字段；`load()` 增 `_looks_like_current_shape`
  helper 与 version-based / shape-based 双层 guard，跳过 legacy remap；
  `_LEGACY_PHASE_KEY_MAP` 保留（仍兼容 `migrate_legacy_progress` 真 legacy
  路径）。新增常量 `_SCHEMA_VERSION = 2`。
- `automation/persona_extraction/orchestrator.py` — 新增 module-level
  `_phase3_committed_artifacts_present` + `_guard_phase2_rewrite_against_phase3`
  helper（决策 #56 H2 guard）；插入两条调用点：(a) line 2273-2295 validation-
  triggered recovery；(b) line 2287-2295 baseline-missing path（含
  force_baseline）。`confirm_with_user` 内 `Extract up to stage N` prompt
  文案改写 + `preset_end_stage = int(raw) if raw else None`（决策 #56 M1'A）。
  `run_label` 三分支显示修正（None/0/positive）。
- `automation/persona_extraction/cli.py` — 删除 phase_1_5 未 done 时对
  `args.end_stage is None` 的硬挡 sys.exit；同步长注释 + `--background`
  help string；保留 `--characters` 单约束（决策 #56 M1'B）。
- `automation/persona_extraction/_smoke_cli_resume_background_validation.py`
  — C / D 两 case 期望从 reject 翻转为 accept，docstring 同步。9/9 全过。
- `automation/README.md` — `--background` 双分支文案同步 + `--end-stage`
  omit=all 语义。
- `automation/config.toml` — line 36 + line 89 `25 章` → `20 章`；line 36
  `100-150 字` → `150-200 字`（L2）。
- `docs/architecture/extraction_workflow.md` — `--background` 文案同步；
  baseline recovery 段补 H2 guard 描述；line 83 删 "原 analysis/world_overview.json
  已废弃" 改写。
- `docs/architecture/system_overview.md` — `约 25 章/组` → `约 20 章/组`
  + `CLI --chunk-size 默认；可调`（L2）。
- `works/README.md` — `最小 5 章` → `最小 8 章 ... light_novel chapter_count=1`（L1）。
- `ai_context/architecture.md` — line 155 / 172 删 "原 analysis/world_overview.json
  已废弃" + line 172 `--end-stage` 不传=全跑 + Phase 2 段加 H2 guard 描述。
- `ai_context/decisions.md` — 新增决策 #56（H1 + H2 + M1'A+B 三处复合修复
  全细节）+ 修订 #51 措辞（双约束 → 单约束 + end_stage prompt 兜底改为
  EOFError → None = 全跑）。
- `docs/todo_list.md` — 新增 Next 段两条：`T-PHASE2-RECOVERY-RESET-FLAG`
  （决策 #56 H2 二期 reset flag）+ `T-LIGHTNOVEL-SCHEMA-ONEOF`（OQ3
  light_novel schema oneOf 重构）；Index 段同步 11 → 13 / Next 2→3 /
  Discussing 8→9。

## 与计划的差异

- PRE 计划清单全部完成；额外修复 3 项（见"执行偏差"段）。
- 不实现 `--reset-phase3-after-baseline-change` flag（OQ2 用户选 hard stop
  默认 + 二期；已登记 `T-PHASE2-RECOVERY-RESET-FLAG`）。
- 不动 light_novel schema oneOf 重构（OQ3 用户选留 todo；已登记
  `T-LIGHTNOVEL-SCHEMA-ONEOF`）。
- 不补 `pipeline.json::schema_version` 字段表至 schema_reference / data_model
  / README 4 处（Step 7 结构线建议；按 conventions.md "Runtime 进度产物不入
  durable 文档" 原则拒绝）。

## 验证结果

- [x] `from automation.persona_extraction.progress import PipelineProgress`
  — `all imports OK`
- [x] `from automation.persona_extraction.orchestrator import
  ExtractionOrchestrator, _phase3_committed_artifacts_present,
  _guard_phase2_rewrite_against_phase3` — OK
- [x] `from automation.persona_extraction.cli import main` — OK
- [x] **H1 round-trip smoke**：`phase_1_5=done, phase_2=done` round-trip
  后两 phase 仍 `done`；`schema_version=2` 写到磁盘
- [x] **H1 legacy 兼容 smoke**：`phase_2/phase_2_5=done` legacy 文件
  load 正确 remap 为 `phase_1_5/phase_2=done`
- [x] **H1 schema_version priority smoke**：`schema_version=2` + `phase_2=done`
  不被 remap，`phase_1_5` 保持 pending
- [x] **M1'A smoke** (源码 verify)：orchestrator.py:2214 `int(raw) if raw
  else None`；orchestrator.py:2204 prompt 文案 `empty = all (no limit),
  0 = baseline only`
- [x] **M1'B + smoke test 翻转**：9/9 全过（A pass / B reject / C accept /
  D accept / E reject / F pass / G pass / H pass / I argparse reject）
- [x] **grep 残留 = 0**：`最小 5 章` / `约 25 章` / `100-150 字` /
  `phase_1_5 not done.*--characters and --end-stage` / `原.*analysis/world_overview.*已废弃`
  在仓库（除 logs/ + 决策记录自述）中无残留
- [x] **H2 guard smoke**：5 case 全过（empty project → False / committed
  stage → True / world snapshot file → True / character snapshot file →
  True / pending stages → False）
- [x] **schema metaschema**：34 schema 全 `check_schema()` 通过

## Completed

- **Status**: DONE
- **Finished**: 2026-05-12 12:58:56 EDT

<!-- /post-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：20/20 计划项 + 11/11 验证标准 全过 ✅
- Missed updates: 0 条

### 轨 2 — 影响扩散
- Findings: High=0 / Medium=2 / Low=1
- Open Questions: 1 条（详见对话）

## 复查时状态

- **Reviewed**: 2026-05-12 13:14:43 EDT
- **Status**: REVIEWED-PARTIAL
  - PASS = 轨 1 全落实 且 轨 2 无 High/Medium
  - 现状：轨 1 全落实但轨 2 有 2 Medium（同类 conventions §3 文案漂移）
- **Conversation ref**: 同会话内 /post-check 输出
