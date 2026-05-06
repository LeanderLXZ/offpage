# length_tolerance_gate

- **Started**: 2026-05-06 12:10:47 EDT
- **Branch**: main (worktree at ../offpage-main，源会话所在分支
  `extraction/<work_id>`)
- **Status**: PRE

## 背景 / 触发

`<work_id>` Phase 0 重跑（前置 log
`logs/change_logs/2026-05-04_154622_phase0_summarize_timeout_bump.md`）20/22
chunks 通过、2 chunk 终端失败：

- `chunk_011` (C0251-C0275)：`max_turns=51` 用尽，残留 `chunk_011.json`
  里 25 个 per-summary 中 15 个长度 97-99（schema bound 100-150 的
  minLength），LLM 在 schema 边界 ±1-3 字处反复抖动 50 turns 未收敛。
  根因 = schema 100 字下限对中文密集内容过严，加 max_turns 治标不治本。
- `chunk_008` (C0176-C0200)：1800s wall-clock timeout ×2。章节字符
  分布完全正常（6326-7015，全书 mean 2285），无异常长章。怀疑 agent
  loop 卡死或某次 tool call hang。

decision #27i（schema-gate-as-retry-trigger）已让 L1+L2+L3 严格修复跑全；
但抖动在 schema 边界毛刺处时这条路径会反复无效消耗 turn / wall。需要
在 strict 修复全跑完后加一个"length 边界 ±10% 容差兜底"出口。

todo 条目 `T-LENGTH-TOLERANCE-GATE` 已落
`docs/todo_list.md ## Next` 段（commit `08242d6`），本次 /go 落地全部
改动清单。

## 结论与决策

**B 方案：strict L1+L2+L3 全跑完后兜底**：

1. **Helper（追加在 `automation/persona_extraction/validator.py` 末尾）**
   - `relaxed_schema_for_length(schema, tolerance=0.10)`：深拷贝 schema，
     递归调 `minLength` 乘 `(1-tol)` ↓floor、`maxLength` 乘 `(1+tol)` ↑ceil；
     其它约束（required / type / enum / pattern / minimum / maximum /
     minItems / maxItems）原样保留。
   - `validate_with_length_tolerance(instance, schema, tolerance=0.10)
     -> tuple[bool, list[ValidationIssue]]`：先 strict 验证 → pass 直接
     `(True, [])`；strict fail → 检查违规列表，**仅当全为
     minLength/maxLength 类**才用 `relaxed_schema_for_length` 再验一次；
     relaxed pass → `(True, [])`，relaxed fail / 夹杂其它约束违规 →
     `(False, original_errors)`，**不放宽**。

2. **5 处 LLM 终点接入 tolerance**：
   - Phase 0：`orchestrator._summarize_chunk` line ~540-567 区域，L3 retry
     仍 fail 后调 tolerance；pass → 接受；fail → 标 failed
   - Phase 1：`orchestrator.run_analysis` line ~1047 `cfg.phase1
     .exit_validation_max_retry` 耗尽分支（world_overview / stage_plan /
     candidate_characters 三 schema 各自兜底）
   - Phase 2：`orchestrator.run_baseline_production` line 1215+ 调
     `validate_baseline` 后判失败的分支接 tolerance
   - Phase 3 / 3.5 / 4 经 repair_agent 路径：`automation/repair_agent/
     coordinator.py` 在 lifecycle 2 决定 T3_EXHAUSTED 之前的 L3 gate：
     当剩余 issues 仅为 `category == schema_validation` + 错误描述命中
     `minLength`/`maxLength` 关键词时调 tolerance；pass → 改判 PASS；
     fail → 仍 T3_EXHAUSTED。**仅修改终态判定分支**，不动 lifecycle
     1 / 2 / T3 cap / fixer 升级。
   - Phase 4：`scene_archive._handle_validation_failure` line ~343
     `entry.retry_count > entry.max_retries` 路径

   **不接 tolerance**：`post_processing.py` 三处程序化产物
   （memory_digest / world_event_digest / stage_catalog）——非 LLM 生成，
   length 边界毛刺概率为零；接反而掩盖代码 bug。

3. **max_turns 50 → 80 全局**：
   - `automation/persona_extraction/config.py:Phase3Config.max_turns`
     50 → 80
   - `automation/config.toml [phase3] max_turns` 50 → 80 + 注释更新

4. **chunk_size default 25 → 20**：
   - `automation/persona_extraction/cli.py:81-86` argparse `default=25` →
     `default=20`，help 文案同步
   - `automation/persona_extraction/orchestrator.py:361` `chunk_size:
     int = 25` → `20`

5. **文档同步**：
   - `automation/README.md` example 25 → 20
   - `docs/requirements.md` / `docs/architecture/extraction_workflow.md`
     凡含 "25 章" / "chunk_size = 25" / "default: 25" 同步到 20
   - `ai_context/decisions.md` 加 #48 durable 决策（length-bound
     tolerance B 方案 ±10%；触发；覆盖；不带 metadata；max_turns
     80 + chunk_size 20 顺势）
   - `automation/repair_agent/_smoke_l3_gate.py` 加场景 D：
     `L1 length-only fail → lifecycle 2 tolerance PASS`

显式不做的事：

- 不写 tolerance metadata（`_validation_tolerance_applied`）—— trade-off
  是未来回看产物无法识别严格 vs 兜底，但简化下游消费方逻辑
- 不动 `post_processing.py` 程序化产物的 schema 验证（保持严格）
- 不动 lifecycle 1/2/T3 cap / fixer 升级 / Issue 类型枚举
- chunk_008 timeout 根因排查不在本轮（先靠 chunk_size 20 / max_turns
  80 减小复杂度，看是否仍复现）

## 计划动作清单

- file: `automation/persona_extraction/validator.py` → 末尾追加
  `relaxed_schema_for_length` + `validate_with_length_tolerance` 两个函数
- file: `automation/persona_extraction/orchestrator.py` →
  - line ~540-567 _summarize_chunk L3 失败路径接 tolerance
  - line ~1047 run_analysis exit_validation 耗尽路径接 tolerance（3 schema）
  - line ~1215+ run_baseline_production validate_baseline 失败路径接 tolerance
  - line 361 `chunk_size: int = 25` → `20`
- file: `automation/persona_extraction/scene_archive.py` →
  `_handle_validation_failure` 接 tolerance
- file: `automation/repair_agent/coordinator.py` → T3_EXHAUSTED 终态前
  接 tolerance（仅 length-only issues 时改判 PASS）
- file: `automation/persona_extraction/cli.py` → `--chunk-size default=25`
  → `default=20`，help 文案同步
- file: `automation/persona_extraction/config.py` → `Phase3Config
  .max_turns: int = 50` → `80`
- file: `automation/config.toml` → `[phase3] max_turns = 50` → `80`，
  注释加密集中文小说 chunk 经验
- file: `automation/repair_agent/_smoke_l3_gate.py` → 加 scenario D
  （L1 length-only fail → lifecycle 2 tolerance PASS）
- file: `automation/README.md` → chunk_size example 25 → 20
- file: `docs/requirements.md` → 凡含 "25 章" / "chunk_size = 25" /
  "default: 25" 同步到 20；max_turns 50 → 80 同步
- file: `docs/architecture/extraction_workflow.md` → 同上
- file: `ai_context/decisions.md` → 加 #48 length-bound tolerance B
  方案 durable 决策

## 验证标准

- [ ] **validator.py 3 个 unit case** 通过：
  1. strict pass → `(True, [])`
  2. 仅 minLength 差 ≤10%（如 schema minLength=100，给 90 字）→ `(True, [])`
  3. minLength 差 11%（如给 89 字）/ 或夹杂 enum 不匹配 → `(False, errors)`
- [ ] `python -c "from automation.persona_extraction.config import
      load_config; c = load_config(); assert c.phase3.max_turns == 80"` 不抛
- [ ] `python -m automation.persona_extraction --help` 显示
      `(default: 20)`
- [ ] argparse 默认值 = 20（不传 --chunk-size 时 orchestrator.chunk_size
      = 20）
- [ ] `python automation/repair_agent/_smoke_l3_gate.py` 4 场景全过
      （A/B/C 不动 + 新加 D）
- [ ] orchestrator + scene_archive + post_processing +
      repair_agent.coordinator 全部 import 通过
- [ ] `grep -RnE "chunk_size = 25|default: 25|默认.*25.*章|25 章 per chunk"`
      在 docs / ai_context / automation/ 残留为 0
- [ ] `grep -RnE "max_turns = 50|max-turns 50"` 在 docs / ai_context /
      automation/ 残留为 0（commit message / log 文件除外）
- [ ] config.toml 静态可解析（`tomllib.load` 不抛），phase3.max_turns
      = 80

runtime 验证（重跑 phase 0）由后续会话/loop 处理，不在本 commit 内。

## 执行偏差

- Step 7 review 期间发现 `orchestrator.py:1546` 的 baseline resume 路径
  仍走纯 strict `validate_baseline`，与 Phase 2 fresh extraction 出口
  不一致——一个 tolerance-accepted 的 baseline 在 resume 时会失败 strict
  re-validation 触发不必要的 Phase 2 重跑。原 PRE 计划清单未列此点；
  Step 7 inline 修：在 resume 路径加同形态的 tolerance 兜底。改动量
  小（~10 行），与本次 intent 同向，不算偏离。
- repair_agent coordinator 的 tolerance 路径设计上
  返回新的 `lifecycle_signal = "LENGTH_TOLERANCE_PASS"`，由
  `_run_one_lifecycle` 解释为 PASS 终态。原 PRE 计划只说"修改终态判定
  分支"，未明示新增 lifecycle_signal 字面量；落地时为了复用
  T3_TRIGGERED / T3_EXHAUSTED 同形态 outcome 构造，新增了一个 signal
  值，与原意一致非偏离。

<!-- POST 阶段填写 -->

## 已落地变更

### Helper（新增）
- `automation/persona_extraction/validator.py:464-526` — `relaxed_schema_for_length(schema, tolerance=0.10)` + `validate_with_length_tolerance(instance, schema, tolerance=0.10) → (bool, list[ValidationIssue])`，加 `_is_length_bound_error` 内部 helper（line 458），加 `import copy as _copy` + `import math as _math`（line 451-452）
- `automation/persona_extraction/validator.py:347-396` — `_validate_schema` 加 `length_tolerance: float = 0.0` kwarg，>0 时走 tolerance 分支
- `automation/persona_extraction/validator.py:133-145` — `validate_baseline` 加 `length_tolerance: float = 0.0` kwarg + docstring
- `automation/persona_extraction/validator.py:166/184/218/240/267/290` — 6 处 `_validate_schema` 调用全部 propagate `length_tolerance=length_tolerance`

### LLM 终点接 tolerance（5 处）
- `automation/persona_extraction/orchestrator.py:540-572` — `_summarize_chunk` L3 retry 仍 fail 后调 `validate_with_length_tolerance(data, _chunk_validator().schema)`：pass → 接受 chunk + 不删 output；fail → 维持原 fail
- `automation/persona_extraction/orchestrator.py:1191-1232` — `run_analysis` `exit_validation_max_retry` 耗尽 else 分支：仅 `not missing_files and not violating and bool(schema_failures)` 时按 fname 分别重验（world_overview/stage_plan/candidate_characters），全 pass → break 出 retry loop（accept Phase 1）；任一 fail → 维持 FATAL
- `automation/persona_extraction/orchestrator.py:1338-1357` — `run_baseline_production` 终末 `validate_baseline` 失败分支：调 `validate_baseline(..., length_tolerance=0.10)`：pass → 接受；fail → sys.exit(1)
- `automation/persona_extraction/orchestrator.py:1551-1580` — Phase 2 resume re-validate 路径同形态 tolerance 兜底（Step 7 inline 补的，PRE 未列）
- `automation/persona_extraction/scene_archive.py:247-262` — `validate_scene_split` 加 `length_tolerance: float = 0.0` 参数；`scene_archive.py:329-355` schema gate 段：tolerance>0 时只在 strict pass 时报告（即 length-bound only fail 不进 errors）；`scene_archive.py:418-429` `_process_chapter` 在 `entry.retry_count + 1 > entry.max_retries` 即将 ERROR 之前调 tolerance 重验，pass 则清空 errors 接受
- `automation/repair_agent/coordinator.py:706-758` — lifecycle 2 `t3_disabled=True` 即将 T3_EXHAUSTED 之前：检查 `remaining` 全为 `category=='schema' and rule in ('schema_minLength','schema_maxLength')`；若是，再对每个 affected file 调 `validate_with_length_tolerance(content, file.schema)`（list 类 jsonl 走 per-entry）；全 pass → 返回新 `lifecycle_signal = "LENGTH_TOLERANCE_PASS"`
- `automation/repair_agent/coordinator.py:399-417` — `_run_one_lifecycle` round loop 解释 `LENGTH_TOLERANCE_PASS`：直接构造 `_LifecycleOutcome(terminated_by="PASS", final_issues=[], final_blocking=[], ...)` 并返回，不进 Phase C strict re-check

### Config 松绑
- `automation/persona_extraction/config.py:55` — `Phase3Config.max_turns: int = 50` → `80`
- `automation/config.toml:68-72` — `[phase3] max_turns` 50 → 80 + 注释加 "Phase 0 chunk 25 章 / chunk-level 5 字段聚合 + Phase 3 stage_snapshot schema 修订循环单 chunk 实测有时撞 50 上限触发 `error_max_turns`，故全局放到 80"
- `automation/persona_extraction/cli.py:81-86` — `--chunk-size default=25` → `default=20`，help `(default: 25)` → `(default: 20)`
- `automation/persona_extraction/orchestrator.py:361` — `chunk_size: int = 25` → `20`

### 文档同步
- `ai_context/decisions.md:339` — 加 #48 durable 决策（length-bound tolerance B 方案 ±10%；触发；覆盖；不带 metadata；max_turns 80 + chunk_size 20 顺势）
- `ai_context/decisions.md:338` — 修 #47 "25 chapters and produces 25× per-summary" → "`chunk_size` chapters (default 20) and produces N× per-summary"（保持当前默认描述）
- `ai_context/architecture.md:170` — Key Design 段加 "Length-bound tolerance gate" bullet
- `docs/architecture/extraction_workflow.md:548-554` — repair_agent 安全阀段加 length-bound tolerance 兜底说明
- `docs/requirements.md:839-841` — monolithic chunk "约 20-25 章一组" → "默认 20 章一组，由 `--chunk-size` 控制"
- `docs/requirements.md:1788-1792` — lifecycle 2 T3_EXHAUSTED 描述加 length-bound tolerance 兜底说明

### Smoke test
- `automation/repair_agent/_smoke_l3_gate.py:1-15` — 头部 docstring 三场景 → 四场景说明
- `automation/repair_agent/_smoke_l3_gate.py:142-201` — 加 `_scenario_d` (lifecycle 2 length-bound tolerance gate PASS)
- `automation/repair_agent/_smoke_l3_gate.py:213-216` — `main()` 加 scenario D 入口

### todo_list 维护
- `docs/todo_list.md` — 删除 Next 段 T-LENGTH-TOLERANCE-GATE 整块；Index Next 子表 3→2 行；汇总 15→14
- `docs/todo_list_archived.md:76-79` — `## Completed` 顶部插入 T-LENGTH-TOLERANCE-GATE 瘦身条目（标题 / 1 行摘要 / log 链接）

## 与计划的差异

- **新增**：`orchestrator.py:1546` baseline resume 路径加 tolerance 兜底（Step 7 inline 补，PRE 漏列；与本次 intent 同向）
- **新增**：`automation/repair_agent/coordinator.py` 增加 `LENGTH_TOLERANCE_PASS` lifecycle_signal 字面量（PRE 只说"修改 T3_EXHAUSTED 终态判定分支"未明示，落地时为复用现有 outcome 构造路径新增一个 signal 值；功能等价）
- **删除**：无
- **修改幅度小于预估**：PRE 估 ~150 行新增 + ~80 行修改；实际 helper 约 90 行 + 5 处 LLM 终点接入合计 ~120 行 + config/docs/smoke 约 80 行，合计与预估一致

## 验证结果

- [x] `validator.py` 5 个 unit case (PRE 列 3 个，落地扩到 5 个含 maxLength + relaxed_schema 不可变性) 全过
- [x] `load_config()` 返回 `phase3.max_turns == 80`
- [x] argparse `--chunk-size` 默认 20，`--help` 显示 `Chapters per summarization chunk (default: 20)`
- [x] 不传 `--chunk-size` 时 `ExtractionOrchestrator.__init__.chunk_size` default = 20
- [x] `automation/repair_agent/_smoke_l3_gate.py` 4 场景全过 (A PASS / B lifecycle reset PASS / C T3_EXHAUSTED / D tolerance PASS via decision #48)
- [x] orchestrator + scene_archive + post_processing + repair_agent.coordinator import 全过
- [x] `grep "chunk_size = 25" / "default: 25" / "max_turns = 50"` 在 docs / ai_context / automation/ 残留为 0（todo_list_archived / change_logs 内的历史描述除外）
- [x] config.toml 静态可解析 + phase3 块 `{'extraction_timeout_s': 3600, 'review_timeout_s': 600, 'max_turns': 80}`

runtime 验证（重跑<character> phase 0 27 chunks）由后续会话/loop 处理，不在本 commit 内。

## Completed

- **Status**: DONE
- **Finished**: 2026-05-06 12:35:01 EDT
