# targets_keys_eq_baseline

- **Started**: 2026-04-30 03:46:14 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

T-CONSISTENCY-TARGETS-SUBSET 在多处文档/docstring（[target_baseline.schema.json:5](../../schemas/character/target_baseline.schema.json#L5)、[validator.py:264](../../automation/persona_extraction/validator.py#L264)、[consistency_checker.py:11-15](../../automation/persona_extraction/consistency_checker.py#L11-L15)、`ai_context/decisions.md` #13、[extraction_workflow.md:113-118](../../docs/architecture/extraction_workflow.md#L113-L118)、`docs/requirements.md` §9.2）声明了一条 cross-file 硬约束，但代码层从未实现。2026-04-30 给 baseline 加 `maxItems = 15` + 裁剪规则后该硬约束更关键（裁剪策略要求 stage_snapshot 不能写 baseline 没列的角色，但只靠 prompt 软约束）。

2026-04-30 后续讨论拍板四项升级：

1. 语义升级为**双向 ==**（不再单向 ⊆）；三态由"内容是否填充"承载，不由"key 是否出现"承载
2. snapshot 三结构 keying 统一切到 `target_character_id`（当前 `target_voice_map` / `target_behavior_map` 按 `target_type` keying）
3. 校验位置从 phase 3.5 末端搬到 **phase 3 单 stage validate** 层，越界走 file-level repair lifecycle (L1/L2/L3)
4. `targets_cap.schema.json` 从 `schemas/_shared/` 回滚到 `schemas/character/`（共享面太窄）

## 结论与决策

**校验语义**

- `set(stage_snapshot 三结构 keys) == set(baseline.targets[].target_character_id)` — 双向相等，多/少都 hard fail
- 三结构：`voice_state.target_voice_map` / `behavior_state.target_behavior_map` / 顶层 `relationships`
- 三态由内容承载：
  - 已登场（cumulative） → key 在，字段正常填
  - 已见过 + 此 stage 未登场 → key 在，继承 prev
  - 从未登场 → key 在，字段为空
  - **fixed_relationship 例外**：从未登场也可预填 relationships 那条目的关系字段

**fixed_relationship 严控定义**

`fixed = 全书从开始到结束都未改变的关系`。任何在故事中才建立 / 改变 / 解除的关系（含但不限于：故事中才结成的师承、加入门派、收养、结义、结婚 / 离婚、决裂、归化）都不是 fixed，按普通 `relationships` 在 stage_snapshot 中按 stage 演进。关系类型（血缘 / 师承 / 门派归属）只是常见示例，**判定核心是"是否在本作时间线内变化"**。

**校验位置**

phase 3 单 stage validate 层（与 schema validate 同层），越界走 file-level repair lifecycle:
- L1 = json_repair
- L2 = repair_agent (cross-file `targets_keys_eq_baseline` checker)
- L3 = re-extract

phase 3.5 `consistency_checker.py` 不再承担此规则。

**targets_cap 路径**

回滚到 `schemas/character/targets_cap.schema.json`，target_baseline.schema.json 的 `$ref` 同步更新。

## 计划动作清单

### A. Schema 改 keying

- file: `schemas/character/stage_snapshot.schema.json` → `voice_state.target_voice_map` 与 `behavior_state.target_behavior_map` 的 entry required 字段从 `target_type` 切到 `target_character_id`，map 的 key 也用 `target_character_id`。`target_type` 字段保留作 sibling 元数据（标注 target 角色定位/类型）。三结构（含 `relationships`）的 description 加 `keys == baseline.targets` + 三态规则说明。

### B. fixed_relationship 严控（baseline 生成侧）

- file: `automation/prompt_templates/baseline_production.md` § "fixed_relationships.json" → 改写定义段，强调"全书贯穿不变的关系"，列举反例（故事中才建立 / 改变 / 解除的关系一律不算）
- file: `schemas/world/fixed_relationships.schema.json` → root description / type description 同步更新

### C. snapshot prompt 三态规则

- file: `automation/prompt_templates/character_snapshot_extraction.md` → 显式三态规则 + keys 必须等于 baseline.targets 全集 + 从未登场字段空 + fixed_relationship 例外说明

### D. Validator 位置 + repair lifecycle

- file: `automation/persona_extraction/validator.py` → 新增 `_check_targets_keys_eq_baseline(stage_snapshot, baseline)` 函数，在 phase 3 单 stage validate 流程里调用（与 schema validate 同层），越界返回结构化错误供 repair lifecycle 使用
- file: `automation/repair_agent/checkers/` → 新增 `targets_keys_eq_baseline.py` cross-file checker，被 L2 repair_agent 调用
- file: `automation/persona_extraction/consistency_checker.py` → 移除模块 docstring 中 D4 占位 TODO（line 10-15），module 不再承担此规则

### E. targets_cap 路径回滚

- `git mv schemas/_shared/targets_cap.schema.json schemas/character/targets_cap.schema.json`
- file: `schemas/character/target_baseline.schema.json` → `$ref` 路径同步
- file: `schemas/_shared/README.md` → 删该项
- file: `schemas/character/README.md` → 加该项

### F. 文档对齐

- file: `ai_context/decisions.md` #13 → 把"phase 3.5 cross-file hard fail"措辞改成"phase 3 单 stage validate + file-level repair lifecycle"；纳入 keys == 双向相等语义
- file: `docs/architecture/extraction_workflow.md` line 113-118 周围 → 同步
- file: `docs/requirements.md` §9.2 → 同步
- file: `ai_context/requirements.md` → 如有相关段同步
- file: `docs/todo_list.md` / `docs/todo_list_archived.md` → 把 T-CONSISTENCY-TARGETS-SUBSET 移到 archived ## Completed（瘦身），刷新顶部索引

## 验证标准

- [ ] `python -c "import json, jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('schemas/character/stage_snapshot.schema.json')))"` 通过
- [ ] `python -c "import json, jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('schemas/character/targets_cap.schema.json')))"` 通过（新路径）
- [ ] `python -c "import json, jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('schemas/character/target_baseline.schema.json')))"` 通过（新 $ref 路径解析正常）
- [ ] `python -c "from automation.persona_extraction.validator import _check_targets_keys_eq_baseline"` import 无报错
- [ ] `python -c "from automation.repair_agent.checkers import targets_keys_eq_baseline"` import 无报错（新模块）
- [ ] `git ls-files schemas/_shared/targets_cap.schema.json` 输出空（文件已不在）
- [ ] `git ls-files schemas/character/targets_cap.schema.json` 输出非空（文件已落 character/）
- [ ] `grep -rn "schemas/_shared/targets_cap" schemas/ automation/ docs/ ai_context/` 输出空（无残留 ref）
- [ ] `grep -n "phase 3.5.*hard fail\|phase 3.5.*cross-file" docs/ ai_context/ automation/ schemas/` 残留 ≤ 现有引用本规则的最低限（理论应为 0；非本规则的 phase 3.5 提及不算残留）
- [ ] consistency_checker.py 模块 docstring 移除 D4 占位 TODO 后 import 仍正常
- [ ] phase 3.5 consistency_checker 已有的非 D4 检查（`_check_target_map_counts` 等）行为不变，可在不写新 work 的前提下读源码确认

## 执行偏差

- **PRE 计划 E.5 单独写一份 `_targets_cap_moveback.md` change_log → 取消**：
  路径回滚的动机和 diff 已完整在本 log 里覆盖，再单独开一份会造成同
  事件双 log。决定折叠到本 log。
- **新校验入口选 (B) 路径推断而非 (A) API 注入**：原计划在 `validator.py`
  里加 `_check_targets_keys_eq_baseline` + 在 `coordinator.py` 加
  `target_baseline_per_char` 注入参数；执行时改成把规则做成独立的
  `repair_agent/checkers/targets_keys_eq_baseline.py` (L2 layer)，让
  checker 通过 `path → ../target_baseline.json` 自己解析 baseline。
  好处：不动 `coordinator.run` / `validate_only` 的公共 API，无新增
  注入参数；坏处：依赖 character stage_snapshot 的目录结构约定（已
  在 `_is_character_stage_snapshot` / `_baseline_path_for` 里独立封装，
  破坏即报错）。`validator.py` 维持原有职责（baseline 出口校验），
  没有再加重复的 `_check_targets_keys_eq_baseline` 函数。

## 已落地变更

**Schema (5 件)**

- `schemas/character/targets_cap.schema.json` ← 从 `schemas/_shared/`
  `git mv` 过来；`$id` 改为 `offpage/character/targets_cap.schema.json`；
  description 改写：character 域内部共享 + cross-file 双向相等约束。
  `schemas/_shared/` 目录已 `rmdir`（git 不再追踪）
- `schemas/character/target_baseline.schema.json` `$ref` 路径
  `../_shared/targets_cap.schema.json` → `targets_cap.schema.json`；
  根 description / `targets` description 改写为双向 == 语义
- `schemas/character/stage_snapshot.schema.json`:
  - `voice_state.target_voice_map` items required `target_type` →
    `target_character_id`，新增 `target_character_id` 字段（`minLength: 1`）；
    `target_type` 留作 sibling 元数据；description 改 == + 三态
  - `behavior_state.target_behavior_map` 同上
  - 顶层 `relationships` items required 加 `target_character_id`；
    description 改 == + 三态 + fixed_relationship 例外（须自始即有）
  - 三处 `$ref` 都更新为 sibling `targets_cap.schema.json`
- `schemas/world/fixed_relationships.schema.json` 根 description 与
  `relationships.items.type.description` 改写为"全书贯穿不变"严格定义
  + 反例清单（故事中才建立 / 改变 / 解除的师承 / 门派 / 收养 / 结义
  / 婚姻 / 决裂 / 归化等都不算）
- `schemas/character/character_manifest.schema.json` `target_baseline_path`
  description 同步：`⊆` → `==` 双向相等

**代码 (5 件)**

- `automation/repair_agent/checkers/targets_keys_eq_baseline.py` 新文件：
  L2 cross-file checker，按 `characters/{cid}/canon/stage_snapshots/{sid}.json`
  路径自动解析同目录的 `target_baseline.json`，比对三结构 keys 与
  baseline 的双向相等；missing / extra / missing_structure /
  baseline_missing 四种 issue rule
- `automation/repair_agent/coordinator.py` `_build_pipeline` 注册新 checker
- `automation/repair_agent/checkers/structural.py` `_check_target_map`：
  优先读 `target_character_id`（`target_type` 作 fallback），跳过空
  `examples`（避免对从未登场 entry 触发 false positive 的 min_examples
  warning，因为 keys == baseline 约束要求空 entry 占位）
- `automation/persona_extraction/consistency_checker.py`：
  - 模块 docstring 移除 D4 占位 TODO，改写为"D4 由 phase 3 单 stage
    validate 层执行"
  - `_check_target_map_counts` 内 voice/behavior 两段：`target_type`
    → `target_character_id` (fallback)；空 examples 跳过
- `automation/persona_extraction/validator.py`:
  - line 264 注释从 `⊆` 改为"set-equal cross-file at the phase 3
    single-stage validate layer by repair_agent's
    TargetsKeysEqBaselineChecker"
  - `importance_for_target` docstring 改写说明 character_id keying
- `automation/persona_extraction/schema_loader.py` 顶部 docstring 改写：
  cross-domain shares vs single-domain shares 的放置规则 +
  sibling-form ref 兼容
- `automation/repair_agent/_smoke_triage.py` scenario_f
  `target_type` → `target_character_id`

**Prompt (2 件)**

- `automation/prompt_templates/character_snapshot_extraction.md`:
  - relationships 字段说明：`schemas/_shared/` → `schemas/character/`，
    "key 必须 ⊆ baseline" → 引用下方 D4
  - **D4 段重写**：双向相等 + 三态由内容承载（已登场/已见过未登场/从
    未登场）+ fixed_relationship 例外（须自始即有；非自始即有的师承
    / 门派 / 收养等都不算 fixed）+ 越界处置改为 stage_delta 自由文本
    说明（同前）
  - target_voice_map / target_behavior_map "详细度要求" 段加：从未
    登场的 baseline target entry 必须存在（占位）但字段为空
  - "字段命名严格对照"：内层 keying 字段说明从 `target_type` 改为
    `target_character_id`，`target_type` 作 sibling 元数据
  - (A) 未出场角色继承规则：明确"已见过 vs 从未登场"分流
- `automation/prompt_templates/baseline_production.md`:
  - fixed_relationships.json 段 **重写**：判定核心是"是否在本作时间线
    内贯穿不变"；类型只是示例（血缘 / 自始即有的师承 / 自始即有的门派
    归属 / 长辈晚辈）；反例清单（故事中才建立 / 改变 / 解除的关系都不
    属于此处）
  - target_baseline.json `tier` 普通注释 + 硬约束段：`⊆` → 双向 ==
    （多/少都 fail）；路径 `_shared/` → `character/`

**文档 (8 件)**

- `docs/requirements.md` line 895 / 914-928 / 1391 / 3240 — 路径 +
  `⊆` → 双向 == 语义改写 + 三态 + fixed_relationship 例外 + phase 3
  单 stage validate / file-level repair lifecycle
- `docs/architecture/extraction_workflow.md` line ~110-122 + 396-409 —
  路径 + `⊆` → 双向 == + 三态 + fixed exception + repair lifecycle
- `docs/architecture/data_model.md` line 317 — 同步
- `docs/architecture/schema_reference.md` line 258 + 491 — 同步
- `ai_context/decisions.md` #13 + #27b — #13 改写为双向相等 + 三态 +
  fixed exception + phase 3 single-stage validate layer + file-level
  repair lifecycle；#27b 改写共享片段放置规则（cross-domain →
  `_shared/`，single-domain → 该域目录），example 从
  `_shared/targets_cap` → `character/targets_cap`
- `ai_context/architecture.md` Phase 2 / Phase 3.5 段同步：路径 +
  `⊆` → 双向 == + repair lifecycle + phase 3.5 D4 不再承担
- `ai_context/conventions.md` Data Separation 段同步双向 == + 三态 +
  fixed exception；Bounds-only-in-schema 段同步单 / 跨域 share 规则
- `ai_context/requirements.md` §7 Information Layering — 路径 +
  `⊆` → set-equal + repair lifecycle
- `schemas/README.md` 表格：character 行加 `targets_cap`；新增
  `_shared/` 行标 `(none)`；`_shared/` vs `shared/` 区分段重写；
  新增 schema 归类规则段
- `docs/todo_list.md`:
  - 索引：T-CONSISTENCY-TARGETS-SUBSET 行删除（移到 archived）；
    Next 总数 4 → 3；Total 12 → 11
  - 正文：T-CONSISTENCY-TARGETS-SUBSET 整条删除
  - 其他 todo 条目（T-PHASE2-TARGET-BASELINE / T-CHAR-SNAPSHOT-SUB-LANES
    等）的 `⊆` 表述统一改 `==`
- `docs/todo_list_archived.md` ## Completed 段顶端新增
  T-CONSISTENCY-TARGETS-SUBSET 瘦身条目（标题 + 1 行摘要 + log 链接）

## 与计划的差异

- E.5 单独 change_log 取消（理由见上方"执行偏差"）
- 校验入口实现路径选 (B)（理由见上方"执行偏差"）；`validator.py`
  没新增 `_check_targets_keys_eq_baseline`，仅同步注释
- T-CHAR-SNAPSHOT-SUB-LANES / T-PHASE2-TARGET-BASELINE 等"邻居" todo
  条目的 `⊆` 文字一并刷成 `==`（PRE 没显式列出，属于 Cross-File
  Alignment 顺手活——发现即修原则）

## 验证结果

- [x] `python -c "import json, jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('schemas/character/stage_snapshot.schema.json')))"` 通过
- [x] `targets_cap` 新路径 schema 校验通过
- [x] `target_baseline` schema 通过 + `$ref` 解析 `targets_cap` 正常（schema_loader inline 测试 maxItems=15 已落入）
- [x] `from automation.repair_agent.checkers.targets_keys_eq_baseline import TargetsKeysEqBaselineChecker` import 无报错
- [x] `_build_pipeline` 注册新 checker（L2 层 ['StructuralChecker', 'TargetsKeysEqBaselineChecker']）
- [x] 端到端：合成 baseline `{B001, C001}` + snapshot 三结构有 missing C001 / extra X001 → checker 同时报 missing + extra
- [x] `git ls-files schemas/_shared/targets_cap.schema.json` 输出空（旧路径不再追踪），`schemas/character/targets_cap.schema.json` 已追踪
- [x] `grep -rn "schemas/_shared/targets_cap"` 残留：仅出现在解释 `_shared/` 规则的 docstring（`schema_loader.py` / `decisions.md` / `conventions.md`）和新 `targets_cap.schema.json` 自身的"故置于 schemas/character/ 而非 schemas/_shared/" 解释里——非陈旧 ref
- [x] `grep -rn "⊆"` 在 schemas/ automation/ ai_context/ docs/（排除 todo_list_archived 与 logs/change_logs）残留为 0
- [x] `consistency_checker.py` 模块 docstring D4 占位 TODO 已移除，import 仍正常
- [x] phase 3.5 `_check_target_map_counts` 现在跳过空 examples（不会因从未登场的占位 entry 触发 min_examples warning），其他 `_check_*`（alias / memory_id / 等）行为不变（源码 diff 仅触及 voice/behavior 两块）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-30 04:07:58 EDT
