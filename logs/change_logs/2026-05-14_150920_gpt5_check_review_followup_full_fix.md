# gpt5_check_review_followup_full_fix

- **Started**: 2026-05-14 15:09:20 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

/check-review codex（gpt-5 报告 `logs/review_reports/2026-05-14_004356_gpt-5_full-review-alignment-audit.md`）逐条复核后，user 指令"把建议修的都修复了，建议留 todo 的都跳过，建议跳过的也跳过"。本轮一次性落地 4 H + 7 M + 4 L + 3 OQ 的全部"建议修"项；2 条"已失效 / 跳过"项（M6 原 claim、OQ4）+ 1 条"建议留 todo"（OQ3）不做。

## 结论与决策

**做（21 项）**：H1 / H2 / H3 / H4 / M1 / M2 / M3 / M4 / M5 / M6-handoff（报告外补充）/ M7 / M8 / L1 / L2 / L3 / L4 / OQ1 / OQ2 / OQ5

**不做（3 项）**：
- M6 原 claim（已失效——conventions.md:114 已 exempt `docs/todo_list_archived.md`）
- OQ3（建议留 todo，转 `T-PROMPT-SCHEMA-INJECT`）
- OQ4（已失效）

**关键设计决策**：
1. **OQ1 拍板**：foundation.schema.json 加 `genre / tone / world_structure / power_system / major_factions / world_lines / core_rules` 到 `required`。理由：Phase 1 foundation lane 是 runtime Tier 0 单一来源，`{"work_id":"demo"}` 通过会让 Phase 1 lane skip + Phase 2 gate 静默放行。代价：main 上 `works/` 只 README，无历史 foundation 受影响。
2. **OQ2 拍板**：`major_factions[].key_figures` 加入 items `required`，允许 `[]`。理由：给 Phase 2 替换 LLM 稳定的"key 存在"前提。
3. **OQ5 拍板**：取消 Phase 2 LLM 写空 stage_catalog 步骤；Phase 3 第一个 stage 的 `post_processing.upsert_stage_catalog` 已自动 init。需先验 `mkdir parents=True` 已在位（已确认 post_processing.py 调 `_atomic_write_json` 走 mkdir parents）。
4. **H1 方案**：单行 `entry["memory_importance"]` → `entry.get("memory_importance", "significant")` + 删错误注释。fallback 与 `_infer_importance` 默认值一致。
5. **H2 方案**：`PidLock.acquire()` 改 `os.open(O_CREAT|O_EXCL)`；EEXIST → stale 判定 + unlink 重试一次。调用方 `is_held()` + `acquire()` 双 pre-check 保留（用于打印对方 PID 给用户）。
6. **H3 方案**：`_chunk_passes_full_check` 改 `count != expected` + 抽 `summaries[].chapter` set 与期望 chapter range set 严等；签名加 `(start_ch, end_ch)` 入参。3 个调用点同步。
7. **M2 方案**：`_merge_jsonl_slice` 加 `current_stage_keys: set` 第四参数；`RepairFileEntry` dataclass 加 `current_stage_keys` 字段；`_jsonl_stage_entry` 注入。`write_file_entry` 透传。
8. **M3 方案**：`run_baseline_production:2264` 移除 mark_done；`run():3713-3717` 改 `if sha is None: sys.exit(1)`；recovery 路径 `:2534-2542 / :2557-2561` 同形态。
9. **M8 方案**：`analysis/conflicts/` 选 **local**（无 writer + 与 evidence/ 同性质）；`.gitignore` 加 + `works/README.md` 标"本地未 tracked"。

## 计划动作清单

### Schema 改动（H4 + OQ1 + OQ2 + L3）

- `schemas/world/foundation.schema.json`:7 → `required` 加 7 个核心字段（OQ1）
- `schemas/world/foundation.schema.json`:84（items required）→ 加 `key_figures`（OQ2）
- `schemas/world/foundation.schema.json`:81（major_factions description）→ 对齐双阶段语义
- `schemas/analysis/chapter_summary_chunk.schema.json`:57, :65, :87, :119 → "Phase 2 综合" → "Phase 1 foundation lane 综合"（L3）

### Prompt 改动（H4 + OQ5）

- `extraction/persona_extraction/prompts/baseline_production.md`:9 → 改写为 line 42 同款"Phase 1 写 raw 名 / Phase 2 替换"（H4）
- `extraction/persona_extraction/prompts/baseline_production.md`:13 + step 5 段（约 253-256 / 279 / 292）→ 删 stage_catalog 初始化步骤（OQ5）

### Code 改动（H1 + H2 + H3 + M1 + M2 + M3 + L4）

- `extraction/persona_extraction/phases/post_processing.py`:223 + 215-219 注释（H1）
- `extraction/persona_extraction/core/process_guard.py`:90-108 PidLock.acquire 改原子（H2）
- `extraction/persona_extraction/orchestrator.py`:635-659 _chunk_passes_full_check 严等校验 + 3 调用点同步（H3）
- `extraction/ingestion/validator.py`:175 段后加 chapter txt 存在性 loop（M1）
- `extraction/repair/field_patch.py`:57-85 + RepairFileEntry dataclass + orchestrator.py:1394-1429 注入（M2）
- `extraction/persona_extraction/orchestrator.py`:2264 / 2534-2542 / 2557-2561 / 3713-3717 mark_done 时序（M3）
- `extraction/validation/gates/phase2_baseline.py`:3-4 docstring 改实际校验集（L4）

### Docs / ai_context 改动（M4 + M5 + M6-handoff + M7 + M8 + L1 + L2）

- `docs/requirements.md`:2117 → Phase 2 validation row 重写（M4）
- `docs/requirements.md`:773 → "(~25ch)" → "（默认 20 章 / chunk）"（L2）
- `docs/requirements.md`:3342 → "（Phase 2）" → "（Phase 1 foundation lane）"（L2）
- `docs/requirements.md`:1005 → `.partial_prev` 加 `{char_id}`（L1）
- `ai_context/skills_config.md`:30 → `works/*/analysis/logs/` → `works/*/analysis/progress/extraction_logs/`（M5）
- `ai_context/handoff.md`:77-78 → exempt 列表扩到 conventions.md:114 全集（M6-handoff）
- `ai_context/architecture.md`:158 → `.partial_prev` 加 `{char_id}`（L1）
- `ai_context/decisions.md`:455 → `.partial_prev` 加 `{char_id}`（L1）
- `ai_context/conventions.md`:51 → analysis_foundation.md 描述修正（H4）
- `simulation/retrieval/load_strategy.md`:94-97 → 加 future / not produced yet 注释（M7）
- `works/README.md`:213 → conflicts/ 标"本地"（M8）
- `.gitignore` → 加 `works/*/analysis/conflicts/`（M8）

### Decisions 新条目

- `ai_context/decisions.md` 加新决策条目记 OQ1+OQ2+OQ5（foundation tightening + key_figures required + Phase 2 stage_catalog responsibility removal）

## 验证标准

- [ ] Python AST：`python -c "import ast; [ast.parse(open(p).read()) for p in ['extraction/persona_extraction/phases/post_processing.py', 'extraction/persona_extraction/core/process_guard.py', 'extraction/persona_extraction/orchestrator.py', 'extraction/ingestion/validator.py', 'extraction/repair/field_patch.py', 'extraction/validation/gates/phase2_baseline.py']]"` 无报错
- [ ] Python import smoke：`python -c "from extraction.persona_extraction.core.process_guard import PidLock; from extraction.persona_extraction.phases.post_processing import _timeline_to_digest; from extraction.persona_extraction.orchestrator import PersonaExtractor; from extraction.ingestion.validator import validate_source_package; from extraction.repair.field_patch import _merge_jsonl_slice; from extraction.validation.gates.phase2_baseline import validate_baseline"` 无报错
- [ ] JSON Schema metaschema：`python -c "import json, jsonschema; [jsonschema.Draft202012Validator.check_schema(json.load(open(p))) for p in ['schemas/world/foundation.schema.json', 'schemas/analysis/chapter_summary_chunk.schema.json']]"` 无报错
- [ ] grep 残留：`grep -rn "Phase 2 综合.*foundation" schemas/` = 0
- [ ] grep 残留：`grep -rn "works/\*/analysis/logs/" ai_context/` = 0
- [ ] grep 残留：`grep -rn ".partial_prev/{prev[_]\?stage_id}_{lane}.json" ai_context/ docs/requirements.md` = 0（应被 `{char_id}/{prev_stage_id}_{lane}.json` 替换）
- [ ] grep 残留：`grep -n "phase 1 foundation lane 不写该字段" extraction/persona_extraction/prompts/baseline_production.md` = 0（line 9 旧版应消失）
- [ ] grep 残留：`grep -n "skeleton voice/behavior/boundary" extraction/validation/gates/phase2_baseline.py` = 0
- [ ] grep 残留：`grep -n "空数组占位\|世界与角色 stage_catalog 初始化\|空的 stage_catalog" extraction/persona_extraction/prompts/baseline_production.md` = 0（OQ5）
- [ ] foundation schema 自检：`{"work_id": "demo"}` 不再通过；含 7 核心字段 + 每 faction 含 key_figures(=[]) 的最小有效样例通过
- [ ] _chunk_passes_full_check 行为：count != expected → False；count == expected 但 chapter set 错位 → False；set 完全一致 → True
- [ ] `_merge_jsonl_slice` 行为：current_stage_keys 内的 full 条目被丢弃，slice 完全接管
- [ ] PidLock.acquire 原子性：模拟 EEXIST + stale 情况

## 执行偏差

Step 7 review 发现 5 处 PRE log 漏列的 ripple，发现即修（属"一行能修的小问题"扫尾）：

1. `schemas/analysis/chapter_summary_chunk.schema.json:101` "Phase 2 综合截断" → "Phase 1 foundation lane 综合截断"（L3 narrow-regex 漏网）
2. `extraction/persona_extraction/prompt_builder.py:397-401` `build_baseline_prompt` docstring "5 件 + 空 stage_catalog" → "4 件 + stage_catalog 由 phase 3 post_processing 落盘"（OQ5 ripple）
3. `extraction/persona_extraction/prompts/summarization.md:46` "Phase 2 综合 foundation.core_rules.impact" → "Phase 1 foundation lane 综合 foundation.core_rules"（L3 ripple）
4. `extraction/persona_extraction/orchestrator.py:2176-2185` `run_baseline_production` docstring "5 件 + 空 stage_catalog" → "4 件 + stage_catalog 由 phase 3 post_processing 落盘"（OQ5 ripple）
5. `docs/requirements.md:1348-1352` 流程图 Phase 2 框内 "+ 空 stage_catalog" → 删除（OQ5 ripple）

`docs/architecture/data_model.md:294-303` 加 future-design 注释（M7 ripple——Cross-File "Loading strategy" 表行牵连），让 future loader 不被 stale 路径误导。

`docs/architecture/schema_reference.md:181-184` foundation entry 加 `key_figures` items.required + 顶层 8 项 required 收紧说明（OQ1+OQ2 ripple）。

`ai_context/decisions.md` 内 #58 narrative 中描述 "Phase 2 不再让 LLM 写空 stage_catalog" 的 3 处保留——是决策本身的措辞，非 stale。

M3 risk review 论证：commit_stage 返回 None 在 baseline rerun 路径上 = 空 status 或 commit 失败，无论哪种都不应该让 Phase 3 起跑。fatal exit 是 fail-loudly 行为，与 Phase 3 "passing stage committed" contract 一致。已在内嵌注释明确点出该选择。

## 已落地变更

### Schema（4 文件）

- `schemas/world/foundation.schema.json`：顶层 `required` 从 1 项 (`work_id`) 扩到 8 项（OQ1）；`major_factions.items.required` 加 `key_figures`（OQ2）；顶层 + items + key_figures 描述同步更新双阶段语义。
- `schemas/analysis/chapter_summary_chunk.schema.json`：5 处 "Phase 2 综合" → "Phase 1 foundation lane 综合"（L3 + Step 7 ripple）。

### Prompt（2 文件）

- `extraction/persona_extraction/prompts/baseline_production.md`：
  - 顶部 baseline 产物清单 5 件 → 4 件（删 stage_catalog 初始化条）
  - 行 9 "phase 1 foundation lane 不写该字段" → "phase 1 写 raw 名，phase 2 LLM 替换"（H4 fix）
  - 整段 "## 产出 5：世界与角色 Stage Catalog 初始化"（~30 行）删除（OQ5）
  - 末尾"baseline 阶段只需完成"列表移除 stage_catalog 提及，改为 "4 件"
  - "不在 baseline 阶段产出的文件" 段加 stage_catalog 由 phase 3 post_processing 落盘说明
- `extraction/persona_extraction/prompts/analysis_foundation.md`：line 110 "必须写 key_figures" 重申 "空数组合法（schema items.required，决策 #58）"
- `extraction/persona_extraction/prompts/summarization.md`：line 46 "Phase 2 综合" → "Phase 1 foundation lane 综合"（Step 7 ripple）

### Code（8 文件）

- `extraction/persona_extraction/phases/post_processing.py:215-227`：H1—`entry["memory_importance"]` → `entry.get("memory_importance", "significant")` + 注释修正（L1 gate 在 Step 4 repair 跑、非 Step 3 之前）
- `extraction/persona_extraction/core/process_guard.py:90-135`：H2—`PidLock.acquire` 改 `os.open(O_CREAT|O_EXCL)` + stale-retry once
- `extraction/persona_extraction/orchestrator.py`：
  - `:635-687` H3—`_chunk_passes_full_check` 加 `start_ch/end_ch` kwargs，count != expected + chapter set 严等
  - `:1610-1622 + 1745-1748` H3—3 个调用点同步传 chapter range
  - `:1423-1480` M2—`_jsonl_stage_entry` 注入 `current_stage_keys=frozenset(...)` 到 RepairFileEntry
  - `:2173-2188` Step 7 ripple—docstring 4 件 + stage_catalog 说明
  - `:2575-2602 + 3768-3792` M3—run_baseline_production:2264 移除 mark_done；3 个 commit_stage 调用点改 `if sha is None: sys.exit(1)` + 紧跟 mark_done
- `extraction/persona_extraction/lifecycle/progress.py:373-403`：H3 ripple—reconcile_with_disk 加 `_expected_chapter_range` helper + 传 chapter range 给 `_chunk_passes_full_check`
- `extraction/persona_extraction/prompt_builder.py:392-401`：Step 7 ripple—`build_baseline_prompt` docstring 4 件 + stage_catalog 说明
- `extraction/ingestion/validator.py:221-260`：M1—`validate_source_package` 加 chapter txt 存在性 loop（preflight 收紧）
- `extraction/repair/protocol.py:14-44`：M2—`FileEntry` dataclass 加 `current_stage_keys: frozenset[str] | None = None`
- `extraction/repair/field_patch.py:57-115`：M2—`_merge_jsonl_slice` 加 `current_stage_keys` 第四参数，新模式 drop full-list 内 current-stage 条目（让 repair 删除生效）；`write_file_entry` 透传
- `extraction/validation/gates/phase2_baseline.py:1-22`：L4—模块 docstring 更新为实际校验文件列表（删除 stale "skeleton voice/behavior/boundary" 段）

### Docs / ai_context（10 文件）

- `docs/requirements.md`：
  - `:773` chunk size "(~25ch)" → "(默认 20ch)"（L2）
  - `:1005` `.partial_prev` 加 `{char_id}/` 段（L1）
  - `:1348-1352` Phase 2 流程图框删 "空 stage_catalog"（OQ5 ripple）
  - `:2117` Phase 2 row 重写（schema + length-tolerance，无 repair）（M4）
  - `:3342` "foundation Phase 2" → "foundation Phase 1 foundation lane"（L2）
- `docs/architecture/schema_reference.md:181-184`：foundation entry 加 OQ1+OQ2 收紧说明（Step 7 ripple）
- `docs/architecture/data_model.md:294-303`：M7 ripple—world/events/locations/factions/timeline 加 future 注释
- `ai_context/architecture.md:158`：L1—`.partial_prev` 加 `{char_id}/`
- `ai_context/decisions.md`：
  - `:455` L1—`.partial_prev` 加 `{char_id}/`
  - 新增 #58 完整决策条目（OQ1+OQ2+OQ5 三件合一）
- `ai_context/conventions.md:51`：H4—Cross-File 表 analysis_foundation.md 描述"produces all fields except key_figures" → "produces all fields including key_figures with raw names"
- `ai_context/handoff.md:74-81`：M6-handoff—exempt 列表对齐 conventions.md:114-116 完整集
- `ai_context/skills_config.md:30`：M5—`works/*/analysis/logs/` → `works/*/analysis/progress/extraction_logs/`
- `works/README.md:213`：M8—conflicts/ 标 "本地，未 tracked"
- `simulation/retrieval/load_strategy.md:90-101`：M7—world/events/locations/factions/timeline 加 future-design block 注释
- `.gitignore`：M8—加 `works/*/analysis/conflicts/`

## 与计划的差异

- **PRE log 漏列 5 处 ripple，Step 7 review 抓出，发现即修**（见上述「执行偏差」段；属 /go skill Step 7 "一行能修的小问题发现即修" 范围）
- **PRE log 未列 `docs/architecture/schema_reference.md` + `docs/architecture/data_model.md` 编辑**，Step 6 Cross-File 表对照后补加（OQ1+OQ2 ripple + M7 ripple）
- **未在 PRE log 列 `extraction/persona_extraction/prompts/summarization.md` 编辑**，Step 7 grep 抓到补加
- 其他严格按 PRE 计划落地，无新增 / 删除项

## 验证结果

- [x] Python AST 8 个文件全过
- [x] Python import smoke 7 个模块全过
- [x] JSON Schema metaschema 2 个 schema 全过
- [x] grep 残留全清（"Phase 2 综合 foundation" / "works/*/analysis/logs/" / ".partial_prev/{prev[_]?stage_id}_{lane}.json" 扁平路径 / "phase 1 foundation lane 不写该字段" / "skeleton voice/behavior/boundary" / "空数组占位\|世界与角色 stage_catalog 初始化\|空的 stage_catalog" / "Phase 2 综合" 全仓 / "缩水到 5 件" / "空 stage_catalog" 全仓除 decisions.md #58 描述外）= 0
- [x] foundation schema 行为正确：`{"work_id":"demo"}` fail 7 个 required 字段；含 8 字段 + key_figures=[] 最小有效样例 pass；faction 缺 key_figures fail
- [x] `_chunk_passes_full_check` 行为正确：count != expected fail；count == expected 但 chapter set 错位 fail；valid set pass；duplicate 章 fail
- [x] `_merge_jsonl_slice` 行为正确：current_stage_keys 模式 drop full-list 内当前 stage 旧条目；legacy 模式保留旧 bug（向后兼容）
- [x] `PidLock.acquire` 行为正确：first acquire OK；second acquire blocked；stale lock recovered via O_EXCL + is_held 检测
- [x] `_timeline_to_digest` 行为正确：missing memory_importance fallback significant 无 KeyError；provided 值保留

## Completed

- **Status**: DONE
- **Finished**: 2026-05-14 15:35:34 EDT
