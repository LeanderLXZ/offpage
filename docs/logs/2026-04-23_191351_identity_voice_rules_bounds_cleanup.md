# identity_voice_rules_bounds_cleanup

- **Started**: 2026-04-23 19:13:51 EDT
- **Branch**: master
- **Status**: DONE

## 背景 / 触发

接续 2026-04-23 17:04:52 的 `character_schema_bounds_cleanup`：
上一轮把 `memory_timeline` / `behavior_rules` / `boundaries` /
`failure_modes` 四份 schema 的字段级上下限收口到 JSON schema、并删除
`evidence_refs`。本轮继续把剩下两份角色 baseline schema
（`identity` / `voice_rules`）以及 `behavior_rules` 的一处遗漏条目统一收紧，
让 LLM 输出的字段长度 / 条目数由 schema 硬门控，避免 TOML 或 prompt
第二份副本漂移。

用户明确要求 TOML 里不要重复这些上下限（已验过 `automation/config.toml`，
无相关键，无改动）。

## 结论与决策

### `schemas/character/behavior_rules.schema.json`

- `emotional_reaction_map`: `maxItems` 10 → 15。

（其余字段已于 2026-04-23 17:04:52 批次收紧，本轮不动。）

### `schemas/character/identity.schema.json`

- `aliases.source`: 加 `maxLength: 100`
- `birth_origin`: 加 `maxLength: 100`
- `appearance_summary`: 加 `maxLength: 100`
- `background_summary`: 加 `maxLength: 200`
- `initial_social_position`: 加 `maxLength: 100`
- `distinguishing_features`: 加 `maxItems: 20`, items `maxLength: 100`
- `core_wounds`: 加 `maxItems: 15`;
  items 中 `wound maxLength: 50` / `origin maxLength: 100` /
  `behavioral_impact maxLength: 100`;
  **删除 `source_type` 字段**
- `key_relationships`: 加 `maxItems: 10`;
  items 中 `initial_relationship maxLength: 50` /
  `relationship_arc maxLength: 100`;
  `turning_points` 加 `maxItems: 15`, items `maxLength: 50`;
  **删除 `source_type` 字段**
- **删除顶层 `evidence_refs` 字段**

### `schemas/character/voice_rules.schema.json`

- `baseline_tone`: 加 `maxLength: 100`
- `speech_patterns`: 加 `maxItems: 15`, items `maxLength: 50`
- `vocabulary_preferences`: 加 `maxItems: 15`, items `maxLength: 50`
- `signature_phrases`: 加 `maxItems: 30`, items `maxLength: 10`
- `emotional_voice_map`: 加 `maxItems: 15`;
  items 中 `voice_shift maxLength: 50`;
  `typical_expressions` 改 `maxItems: 5` (原 15), items `maxLength: 15`
- `target_voice_map`: 加 `maxItems: 10`;
  items 中 `voice_shift maxLength: 50`;
  `typical_expressions` 改 `maxItems: 5` (原 15), items `maxLength: 15`
- `taboo_patterns`: 加 `maxItems: 15`, items `maxLength: 30`
- **删除顶层 `evidence_refs` 字段**

### 连带影响

- `docs/architecture/schema_reference.md` — identity 小节里
  `core_wounds` / `key_relationships` 的描述含 `source_type`，
  同步删除。
- `docs/architecture/data_model.md` — 第 286 行
  "identity.json 以字段白名单加载（剥离 `evidence_refs` 等大字段）"
  改为不再提 evidence_refs（该字段已从 identity 删除）。
- `docs/requirements.md` — 第 641/643 行提到
  "identity 中 aliases[].evidence_refs" 的表述与当前 schema 已脱节
  （当前 aliases 无 evidence_refs，仅顶层有），本轮顶层也删除后，
  该段需整体澄清。
- `automation/prompt_templates/baseline_production.md` — 第 145 行
  "对于不确定的字段，标注在 evidence_refs 中说明…" 以及
  `fixed_relationships` 示例外的 identity 示例若有 evidence_refs
  须删掉。fixed_relationships 示例保留 evidence_refs（该 schema 未动）。
- `automation/persona_extraction/consistency_checker.py` — 未涉及
  identity / voice_rules 的 evidence_refs 校验，无需改动（已确认）。
- TOML：`automation/config.toml` 已无相关键，不改。
- `ai_context/conventions.md` — Cross-File Alignment 表及长度上下限
  条目需把 identity / voice_rules 补齐进"schema 单一来源"列表。
- `ai_context/decisions.md` — 追加一条说明"identity / voice_rules
  字段级上下限收口至 schema；evidence_refs / source_type 字段删除"。

## 计划动作清单

- file: `schemas/character/behavior_rules.schema.json` →
  `emotional_reaction_map maxItems` 10 → 15
- file: `schemas/character/identity.schema.json` → 按决策补
  `maxLength` / `maxItems`；删 `core_wounds[].source_type` /
  `key_relationships[].source_type`；删顶层 `evidence_refs`
- file: `schemas/character/voice_rules.schema.json` → 按决策补
  `maxLength` / `maxItems`；`typical_expressions` 条数上限降到 5；
  删顶层 `evidence_refs`
- file: `docs/architecture/schema_reference.md` → identity 小节删
  `source_type` 说明
- file: `docs/architecture/data_model.md` → 更新 identity 字段白名单
  表述
- file: `docs/requirements.md` → 641/643 行 identity evidence_refs
  表述澄清
- file: `automation/prompt_templates/baseline_production.md` →
  删 identity 语境下的 `evidence_refs` 说明；fixed_relationships
  示例保留
- file: `ai_context/conventions.md` → Cross-File Alignment 表 +
  长度上下限条目补充 identity / voice_rules
- file: `ai_context/decisions.md` → 追加"identity / voice_rules
  字段级约束收口 + evidence_refs / source_type 删除"决策

## 验证标准

- [ ] `python -c "import jsonschema, json; [jsonschema.Draft202012Validator.check_schema(json.load(open(p))) for p in ['schemas/character/behavior_rules.schema.json','schemas/character/identity.schema.json','schemas/character/voice_rules.schema.json']]"` 成功
- [ ] `grep -n 'evidence_refs' schemas/character/identity.schema.json schemas/character/voice_rules.schema.json` 输出为空
- [ ] `grep -n 'source_type' schemas/character/identity.schema.json` 输出为空
- [ ] import smoke: `python -c "from automation.persona_extraction import orchestrator, consistency_checker, validator"`
- [ ] 构造 instance sample 验证 `key_relationships` / `core_wounds` 超限会被拒
- [ ] 全库 grep 检查：docs / ai_context / prompt 里不再把 identity /
      voice_rules 的 evidence_refs / identity 的 source_type 当必填或示例

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

- `schemas/character/behavior_rules.schema.json` —
  `emotional_reaction_map.maxItems` 10 → 15，描述同步到"最多 15 条"。
- `schemas/character/identity.schema.json` —
  `aliases[].source` 加 `maxLength:100`；
  `birth_origin` / `appearance_summary` / `initial_social_position` 加
  `maxLength:100`；`background_summary` 加 `maxLength:200`；
  `distinguishing_features` 加 `maxItems:20`, items `maxLength:100`；
  `core_wounds` 加 `maxItems:15`, items
  `wound maxLength:50 / origin maxLength:100 /
  behavioral_impact maxLength:100`；**删除 `core_wounds[].source_type`**；
  `key_relationships` 加 `maxItems:10`, items
  `initial_relationship maxLength:50 / relationship_arc maxLength:100`，
  `turning_points` 加 `maxItems:15`, items `maxLength:50`；
  **删除 `key_relationships[].source_type`**；
  **删除顶层 `evidence_refs`**。
- `schemas/character/voice_rules.schema.json` —
  `baseline_tone` 加 `maxLength:100`；`speech_patterns` /
  `vocabulary_preferences` 加 `maxItems:15`, items `maxLength:50`；
  `signature_phrases` 加 `maxItems:30`, items `maxLength:10`；
  `emotional_voice_map` 加 `maxItems:15`, items
  `voice_shift maxLength:50`；`typical_expressions.maxItems` 15 → 5，
  items `maxLength:15`；`target_voice_map` 加 `maxItems:10`，
  同结构；`taboo_patterns` 加 `maxItems:15`, items `maxLength:30`；
  **删除顶层 `evidence_refs`**。
  （`dialogue_examples[].evidence_ref` 单数、按条台词级的章节引用保留。）
- `docs/architecture/schema_reference.md` — identity / voice_rules /
  behavior_rules 三节补齐字段上下限清单，删除 `source_type` 表述。
- `docs/architecture/data_model.md:286` — identity 加载描述从
  "字段白名单剥离 evidence_refs" 改为"全量加载，字段上下限由 schema
  硬门控"。
- `docs/requirements.md` §7.1 — identity 不变层描述同步更新，删除
  `aliases[].evidence_refs` loader 白名单相关表述。
- `simulation/retrieval/load_strategy.md` — identity 加载描述同步
  更新（英文）。
- `automation/prompt_templates/baseline_production.md` — 去掉
  "对于不确定的字段标注在 evidence_refs 中说明" 的提示；
  `fixed_relationships` 示例保留 evidence_refs（该 schema 未动）。
- `ai_context/conventions.md` §Data Separation — Length / Count
  spot examples 合并 identity / voice_rules 的新上限，追加一条
  "baseline 无 evidence_refs / source_type；chapter 锚点在
  stage_snapshot / world_stage_snapshot；memory_timeline 用
  scene_refs" 的补注。
- `ai_context/decisions.md` — 新增条目 27c 记录 baseline schemas
  不再持有 `evidence_refs` / `source_type` 的决策 + 原因。

## 与计划的差异

无新增 / 删除项。PRE 列表 9 个文件全部落地。`automation/config.toml`
事前复核无相关键，确认不改，与计划一致。

## 验证结果

- [x] `python -c "import jsonschema, json; [...Draft202012Validator.check_schema(...) for p in [behavior_rules, identity, voice_rules]]"` — 三份 schema 全部通过。
- [x] 构造 instance 样本 — `key_relationships.relationship_arc` 超 100 字、`distinguishing_features` 超 20 条、identity 顶层 `evidence_refs`（additionalProperties:false）都被正确拒绝；最小合法 instance 通过。
- [x] `grep evidence_refs schemas/character/{identity,voice_rules}.schema.json` — 输出为空（仅 voice_rules 内 `dialogue_examples[].evidence_ref` 单数按计划保留）。
- [x] `grep source_type schemas/character/identity.schema.json` — 输出为空。
- [x] Import smoke — `automation.persona_extraction.orchestrator` / `consistency_checker` / `validator` + `automation.repair_agent.coordinator` 正常 import。
- [x] 全库 grep（Explore 子 agent 协查）— docs / ai_context / prompt / 非 log TOML 均无残留，`source_types`（work_manifest 的源格式标签）为同名不同概念，与本次无关。

## Completed

- **Status**: DONE
- **Finished**: 2026-04-23 19:30:00 EDT
