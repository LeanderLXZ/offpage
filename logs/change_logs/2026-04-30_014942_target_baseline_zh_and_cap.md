# target_baseline_zh_and_cap

- **Started**: 2026-04-30 01:49:42 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

用户在 `/plan` 模式下提出三项决议（多轮收敛后定型）：

1. `target_baseline.relationship_type` 从英文 17-enum 改为**中文 + 柔性 string**：列 14 候选（覆盖亲密度 × 立场 × 特殊纽带），允许必要时使用列表外更精确中文短词，并在 `description` 字段说明差异；schema 不再 enum 硬卡。
2. 同 schema 的 `tier` 把「路人」改为「普通」——避免与 `relationship_type` 候选「路人」撞名（type=人际关系性质，tier=本角色视角的重要度梯度，两维正交）。
3. `target_baseline.targets` 加 `maxItems = 15` 上限；下游 `stage_snapshot.{target_voice_map, target_behavior_map, relationships}` 通过 **`schemas/_shared/targets_cap.schema.json` $ref 共享继承（方案 B）**，单源化、未来调整数字只改一处。同时把 `character_snapshot_extraction.md` 等 prompt 里复述 maxItems 的硬数字删掉，改成"按 schema cap" / "按 baseline 实际数量"的 schema-pointer 表述（贴合 #27b 单源原则）。

附带识别已有漏洞：consistency_checker / repair_agent **未真正实现** stage_snapshot 三 map keys ⊆ baseline.targets[].target_character_id 的 cross-file ⊆ 硬校验，docstring/文档承诺与代码不符——本次仅登记 todo_list，不在主任务内修。

## 结论与决策

- ① relationship_type 改 `type: "string"`，14 候选（至亲 / 恋人 / 挚友 / 师长 / 弟子 / 朋友 / 同僚 / 主人 / 下属 / 宠物 / 武器 / 对手 / 敌人 / 路人）写进 description + fallback 段；不留 enum
- ② tier 枚举改为 `核心 / 重要 / 次要 / 普通`
- ③ 新建 `schemas/_shared/targets_cap.schema.json`（单值 `maxItems: 15`），target_baseline.targets + stage_snapshot 三 map 全部用 `allOf + $ref` 引用；validator.py 跑一次 smoke 确认 $ref 跨文件解析能 work
- ④ prompt 模板里复述具体数字的处删数字、改 schema-pointer
- ⑤ ai_context（decisions / conventions / requirements）+ docs（schema_reference / data_model / extraction_workflow / requirements / todo_list）下游全部对齐
- ⑥ 已有 work_id 已生成的 target_baseline.json 中英文 `relationship_type` 值需要手工迁移（或重跑 phase 2 baseline）—— 本次不跑迁移，仅在 POST log 标注后续动作；登 todo_list
- ⑦ ⊆ cross-file 校验缺失漏洞登 todo_list 单独跟进，本次不修

## 计划动作清单

### Schema 层
- file: `schemas/_shared/targets_cap.schema.json` → **新建**，单值 `{$id, $schema, maxItems: 15}`
- file: `schemas/character/target_baseline.schema.json` →
  - `relationship_type` 字段：删 17 项 `enum`，改 `type: "string"`，description 改写 14 候选 + fallback 段
  - `tier` enum: `路人` → `普通`，description 同步
  - `targets` 数组：加 `allOf: [{$ref: "../_shared/targets_cap.schema.json"}]`
- file: `schemas/character/stage_snapshot.schema.json` →
  - `target_voice_map`（line 312 附近）：删 `maxItems: 10` 行，加 `allOf: [{$ref: "../_shared/targets_cap.schema.json"}]`
  - `target_behavior_map`（line 436 附近）：同上
  - `relationships`（line 693 附近）：同上
  - 注：本字段说明文字（≤10 条 等）顺手清掉数字、改 schema-pointer 描述
- file: `automation/persona_extraction/validator.py` → 必要时给 `_validate_schema` 加 `RefResolver` 支持跨文件 $ref；先跑 smoke 看是否需要

### Prompt 层
- file: `automation/prompt_templates/baseline_production.md` → 同步 14 候选 + fallback 段；`tier` 改普通；删英文枚举对照
- file: `automation/prompt_templates/character_snapshot_extraction.md` →
  - line 118-120 等"≤ 10 个对象 / ≤ 15 条"硬数字清空，改 schema-pointer
  - 整文 grep `≤ \d` 残留扫一遍

### docs 层（公开权威）
- file: `docs/architecture/schema_reference.md` → 252 行附近的 `relationship_type` / `tier` 说明全改
- file: `docs/architecture/data_model.md` → 317 行附近 `target_baseline` 描述同步
- file: `docs/architecture/extraction_workflow.md` → 108 / 393 行附近同步 tier + relationship_type 描述
- file: `docs/requirements.md` → 896 行附近 phase 2 描述同步
- file: `docs/todo_list.md` → 355 行附近的 enum 描述同步；新增两条 todo（迁移现有 target_baseline 中英文值；补 ⊆ cross-file 校验漏洞）；刷新 Index

### ai_context 层
- file: `ai_context/decisions.md` → #13 tier enum + relationship_type 描述更新；#11 / #11d 间接受影响处复查
- file: `ai_context/conventions.md` → §Data Separation tier enum 同步（line 80 附近）
- file: `ai_context/requirements.md` / `architecture.md` → 间接 baseline 描述同步（如有）

## 验证标准

- [ ] `python -c "import jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('schemas/character/target_baseline.schema.json')))"` 通过
- [ ] `python -c "from automation.persona_extraction import validator"` import 无报错
- [ ] 用一份合法 stage_snapshot 实例（取 S001 或 S002）跑 jsonschema 校验通过 —— 验证 $ref 跨文件解析
- [ ] 用一份"15 个 target"和"16 个 target"的 mock baseline 数据跑校验，前者通过、后者 maxItems fail —— 验证 cap 生效
- [ ] `grep -RnE '路人.*=.*极弱|极弱.*=.*路人' docs/ ai_context/ automation/` 无残留 tier=路人 描述
- [ ] `grep -RnE 'close_kin|close_friend|nemesis|passerby|acquaintance' schemas/ docs/ automation/ ai_context/` 无残留英文 enum 项
- [ ] `grep -RnE '≤ ?10 个对象|≤ ?15 个对象' automation/prompt_templates/` 等于 0
- [ ] todo_list.md Index 段已刷新，新增 2 条与已完成条目分段正确

## 执行偏差

- **新增**：`automation/persona_extraction/schema_loader.py` 单文件，提供 `load_schema(path)` 在加载时递归 inline 化相对路径 `$ref`。原计划只在 validator.py 加 RefResolver / Registry，但 grep 后发现 `repair_agent/checkers/schema.py:51` 用的是 Draft7Validator，referencing-based registry 不能直接套；为兼顾两条路径（Draft7 + Draft202012）+ 不动外部依赖，改成 load-time inline 方案——`FileEntry.schema` 永远是自包含 dict，任何 draft 都能直接吃。validator.py + orchestrator.py 两处 `_load_schema` 都改成调 schema_loader 的 `load_schema`。这是相对 PRE 计划的小幅扩展，但同样符合 #27b "single source"（数字仍只在 `_shared/targets_cap.schema.json` 一处）。已更新 ai_context/decisions.md #27b 描述这条 inlining 路径。

- **未做**：character_snapshot_extraction.md 的 5 处 #27b 硬数字残留（`character_arc ≤ 200 字` / `timeline_anchor ≤ 50 字` / `snapshot_summary 100–200 字` / `stage_events ≤ 15 条 / 50–80 字` / `relationship_history_summary ≤ 100 字`）—— 这些字段不在本任务变更的 schema 范围内（target_baseline + stage_snapshot 三 map + 共享 cap），属于预先存在的 #27b 违规。Step 7 sub-agent 报告 → 本任务保留不动，避免 scope creep。后续可单开 todo 一次扫干净所有 prompt 模板里的硬数字。

<!-- POST 阶段填写 -->

## 已落地变更

### Schema 层

- **新增** `schemas/_shared/targets_cap.schema.json`：`{$id: offpage/_shared/targets_cap.schema.json, $schema: draft 2020-12, maxItems: 15}` —— 单源约束，下游 4 处 $ref 共享继承
- `schemas/character/target_baseline.schema.json`：
  - `targets`（line 27-34）：加 `allOf: [{$ref: "../_shared/targets_cap.schema.json"}]`
  - `relationship_type`（line 47-51）：删 17 项 `enum`，改 `type: "string"` + `minLength: 1`，description 列 14 候选 + fallback 段
  - `tier`（line 53-57）：enum 从 `[核心, 重要, 次要, 路人]` 改为 `[核心, 重要, 次要, 普通]`，description 解释「普通」与 relationship_type 「路人」正交
- `schemas/character/stage_snapshot.schema.json`：
  - `voice_state.target_voice_map`（line ~310-314）：删 `maxItems: 10`，加 `allOf + $ref`
  - `behavior_state.target_behavior_map`（line ~436-440）：删 `maxItems: 10`，加 `allOf + $ref`
  - `relationships`（line ~693-697）：删 `maxItems: 10`，加 `allOf + $ref`

### 代码层

- **新增** `automation/persona_extraction/schema_loader.py`：`load_schema(path)` + `_inline_refs(node, base_dir)`，递归 inline 相对路径 `$ref`，支持 LRU 缓存
- `automation/persona_extraction/validator.py`：
  - 顶部 import `from .schema_loader import load_schema`
  - `_validate_schema` 用 `load_schema(schema_path)` 替代 `_load_json` 直接读取（line 314 起）
- `automation/persona_extraction/orchestrator.py`：
  - `_load_analysis_schema`（line 77-82）改用 `schema_loader.load_schema`
  - `_build_repair_files` 内部 `_load_schema`（line 536-545）改用 `schema_loader.load_schema`

### Prompt 层

- `automation/prompt_templates/baseline_production.md`：
  - `relationship_type` 段（line 186-216）：14 候选 + fallback 详细说明 + tier 普通 + 双维度正交说明
  - 触顶裁剪规则（line 222-227）：按 tier 优先级，普通先弃；与 cross-file ⊆ 校验配套
- `automation/prompt_templates/character_snapshot_extraction.md`（line 116-130）：
  - target_voice_map / target_behavior_map / relationships / knowledge_scope / failure_modes / misunderstandings / concealments / emotional_baseline / current_personality / current_mood / current_status / stage_events / active_aliases 等字段的硬数字删掉，改"以 schema 为准"
  - relationships 字段额外加共享 cap + ⊆ 约束指引

### 文档层

- `docs/requirements.md` line 893-921：tier 新枚举、relationship_type 14 候选 + fallback、targets cap 共享 $ref、tier 触顶裁剪规则
- `docs/architecture/schema_reference.md` line 250-264：tier `普通` + 14 候选柔性 string + 共享 $ref + tier 优先级裁剪
- `docs/architecture/data_model.md` line 317：tier 新枚举 + 共享 $ref 描述
- `docs/architecture/extraction_workflow.md` line 105-118 + 386-394：tier 新枚举 + 14 候选 + 共享 $ref
- `docs/todo_list.md`：
  - line 355-360：T-PHASE2-TARGET-BASELINE 描述同步 14 候选 + 普通 tier
  - 新增 2 条 Next 任务 `T-CONSISTENCY-TARGETS-SUBSET`（补 ⊆ cross-file 校验代码漏洞）+ `T-MIGRATE-TARGET-BASELINE-ZH`（迁移已 commit 的英文 enum baseline）
  - Index 段刷新：Next 3→5、Total 11→13

### ai_context 层

- `ai_context/decisions.md`：
  - #13 完整改写，反映新 tier 枚举 + 柔性 string 14 候选 + fallback + 共享 $ref + 双维度正交
  - #27b 加 inlining 路径说明（schema_loader.py），明确这是单源仍然 single-source、不算重复
- `ai_context/conventions.md` line 82：bounds-only-in-schema 加 `$ref` 共享说明
- `ai_context/architecture.md` line 157：Phase 2 段同步新 tier 枚举 + 柔性 relationship_type + 共享 $ref
- `ai_context/requirements.md` line 78-83：immutable layer 加 targets_cap.schema.json 共享 $ref 说明

## 与计划的差异

- **新增文件 schema_loader.py**：原 PRE 计划只在 validator.py 加 RefResolver；改为独立 loader 模块以兼顾 Draft7（repair_agent）+ Draft202012 两路径，且不增依赖。已记到执行偏差段。
- **prompt 硬数字部分清理**：原计划"全文 grep 复述 maxItems 的硬数字逐个清理"；实际只清了与 target_baseline / stage_snapshot 三 map 相关字段（target_voice_map / target_behavior_map / relationships / knowledge_scope / failure_modes / 等同列表块的 active_aliases / misunderstandings / concealments / emotional_baseline / current_personality / current_mood / current_status / stage_events），其他 5 处（character_arc / timeline_anchor / snapshot_summary / relationship_history_summary）不在本次 scope 内，后续单开 todo 处理。
- **新增 todo 条目数**：原计划 2 条，实际落 2 条（T-CONSISTENCY-TARGETS-SUBSET、T-MIGRATE-TARGET-BASELINE-ZH），符合预期。

## 验证结果

- [x] `Draft202012Validator.check_schema(...)` 对 3 个 schema 文件全过
- [x] `from automation.persona_extraction import validator` import 无报错
- [x] 5-case 校验矩阵全过：15 targets OK、16 targets maxItems fail、custom relationship_type OK、旧 tier '路人' enum fail、stage_snapshot.target_voice_map=16 触发共享 cap maxItems fail（验证 $ref 跨文件解析路径 + Draft7 兼容）
- [x] grep 残留英文 enum：除 todo_list 迁移映射表（合理出现）外为 0
- [x] grep 残留 tier=路人 描述：仅 schema description / migration todo / baseline_production.md 正交说明（全合理）
- [x] todo_list.md Index 段已刷新（11 → 13，Next 3 → 5），新增 2 条任务
- [x] Step 7 sub-agent cross-file alignment audit 报告 5 类残留全 OK，唯一 finding 是预先存在的 prompt 硬数字（不在本任务 scope）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-30 02:03:51 EDT

<!-- /post-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：14/14 项计划文件改动 + 2/2 项新建文件 + 8/8 项验证标准
- Missed updates: 1 条 — `schemas/README.md` 未加 `_shared/` 子目录行（Cross-File Alignment 表第 41 行规定 `schemas/**/*.schema.json` 改动需同步 schemas/README.md）

### 轨 2 — 影响扩散
- Findings: High=0 / Medium=1（schemas/README.md 漏更新，与 `shared/` 命名近似有误读风险）/ Low=2（schema_loader._load_fragment lru_cache 进程内不 reload；character_snapshot_extraction.md 残留 5 处 #27b 硬数字 = 预先存在违规、本次确认不在 scope）
- Open Questions: 0 条

## 复查时状态
- **Reviewed**: 2026-04-30 02:08:33 EDT
- **Status**: REVIEWED-PARTIAL
  - 轨 1 大体落实，但有 1 项 Missed Update（schemas/README.md）；轨 2 1 个 Medium，无 High → PARTIAL
- **Conversation ref**: 同会话内 /post-check 输出
