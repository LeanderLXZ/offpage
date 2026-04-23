# character_schema_bounds_cleanup

- **Started**: 2026-04-23 17:04:52 EDT
- **Branch**: master
- **Status**: DONE

## 背景 / 触发

用户提出两个诉求：

1. 把 `automation/config.toml` 里所有"schema 字段上下限（长度 / 数量）"
   配置删除——schema 字段的 bound 应当只在 JSON schema 里声明，不再在
   TOML 里维护第二份副本。
2. 在四份 character 子 schema 里补齐 / 调整具体字段的
   `minLength` / `maxLength` / `maxItems` 约束，并删除 `evidence_ref(s)`
   字段（只针对这四份 schema，identity / stage_snapshot / voice_rules /
   world / fixed_relationships 的 evidence 字段不动）。

本次改动是在 character extraction 还未进入第一批提取之前做的 schema 收紧，
目的是让 LLM 输出的字段长度和条目数量直接由 schema 硬门控，避免 TOML 和
schema 两处漂移。

## 结论与决策

### 删除 TOML 中的 schema-bound 项

- 只有一处：`relationship_history_summary_max_chars = 300`
  （`[repair_agent]` 段）及对应注释段。
- 同步删除 `automation/persona_extraction/config.py` 里
  `ExtractionConfig.relationship_history_summary_max_chars` 字段、
  `automation/persona_extraction/orchestrator.py` 里把该字段传给
  coordinator 的链路、`automation/repair_agent/coordinator.py` 里相关
  形参。`checkers/structural.py` 里保留 `= 300` 默认值（该文件内部既做
  "空串 warning"也做"超长 error"，保留 warning 能力；300 这个硬值和
  schema 对齐）。

### schema 字段约束（要在这次改的）

四个 character schema：

- `schemas/character/memory_timeline_entry.schema.json`
  - `subjective_experience`: `minLength: 100, maxLength: 200`
  - `knowledge_gained`: `maxItems: 5`
  - `misunderstanding`: **由对象改为 array**, `maxItems: 5`，
    items 里 `content maxLength: 50`, `truth maxLength: 50`
  - `concealment`: **由对象改为 array**, `maxItems: 5`，items 里
    `content maxLength: 50`, `reason maxLength: 50`, `target` 保留原样
  - `emotional_impact`: `maxLength: 50`（字符串字段）
  - `relationship_impact` items 的 `change`: `maxLength: 100`
  - 删除 `evidence_refs` 字段

- `schemas/character/behavior_rules.schema.json`
  - `core_goals`: `maxItems: 10`, items `maxLength: 50`
  - `obsessions`: `maxItems: 10`, items `maxLength: 50`
  - `decision_making_style`: `minLength: 50, maxLength: 200`
  - `emotional_triggers`: `maxItems: 15`, `trigger maxLength: 50`,
    `reaction maxLength: 100`
  - `emotional_reaction_map`: `maxItems: 10`,
    `internal_response maxLength: 50`,
    `external_behavior maxLength: 50`,
    `typical_actions` items `maxLength: 50`,
    `recovery_pattern maxLength: 50`
  - `relationship_behavior_map`: `maxItems: 10`,
    `default_stance maxLength: 50`, `boundaries maxLength: 50`,
    `escalation_pattern maxLength: 50`
  - `habitual_behaviors`: `maxItems: 15`, items `maxLength: 50`
  - `stress_response`: `coping_style maxLength: 50`,
    `breaking_point maxLength: 50`,
    `post_crisis_behavior maxLength: 50`
  - 删除 `evidence_refs` 字段

- `schemas/character/boundaries.schema.json`
  - `hard_boundaries`: `maxItems: 15`, `rule maxLength: 50`,
    `reason maxLength: 50`, 删除 item 级 `evidence_ref`
  - `soft_boundaries`: `maxItems: 15`, `rule maxLength: 50`,
    `exception_condition maxLength: 50`, 删除 item 级 `evidence_ref`
  - `common_misconceptions`: `maxItems: 15`,
    `misconception maxLength: 50`, `reality maxLength: 100`
  - 删除顶层 `evidence_refs` 字段

- `schemas/character/failure_modes.schema.json`
  - `common_failures`: `maxItems: 15`, `description maxLength: 50`,
    `why_it_happens maxLength: 50`, `correct_behavior maxLength: 100`,
    `common_triggers maxItems: 10`
  - `tone_traps`: `maxItems: 10`, `trap maxLength: 50`,
    `correction maxLength: 100`
  - `relationship_traps`: `maxItems: 10`, `trap maxLength: 50`,
    `correction maxLength: 100`
  - `knowledge_leaks`: `maxItems: 15`, `leak_risk maxLength: 50`,
    `correct_knowledge_state maxLength: 100`
  - 删除顶层 `evidence_refs` 字段

### 连带影响

- `automation/persona_extraction/consistency_checker.py` 里
  `_check_evidence_refs_coverage()` 对 memory_timeline 条目的
  evidence_refs 校验需要删除（schema 里该字段已被移除）。stage_snapshot
  / world snapshot 的同类校验保留。
- prompt templates 里涉及 memory_timeline / behavior_rules / boundaries
  / failure_modes 的 evidence_refs 说明更新；character_snapshot_extraction
  只写 stage_snapshot 顶层 evidence_refs 即可，character_support_extraction
  / baseline_production 等提到上述四 schema evidence_refs 的地方删除。
- `docs/requirements.md` 里 memory_timeline 条目结构示例更新
  （misunderstanding / concealment 改成数组、去掉 evidence_refs 字段）。
- `docs/architecture/schema_reference.md` 有 `misunderstanding`
  字段说明和 evidence_refs 段落，同步更新。
- `ai_context/requirements.md` 若有具体字段布局映射需同步。
- `docs/architecture/data_model.md` 对 identity.json 字段白名单
  （剥离 evidence_refs）表述保留。

## 计划动作清单

- file: `automation/config.toml` → 删除 `[repair_agent]` 段里
  `relationship_history_summary_max_chars` 及其注释段
- file: `automation/persona_extraction/config.py` → 删除
  `ExtractionConfig.relationship_history_summary_max_chars` 字段
- file: `automation/persona_extraction/orchestrator.py` →
  去掉把该字段传给 coordinator 的参数
- file: `automation/repair_agent/coordinator.py` → 去掉
  `relationship_history_summary_max_chars` 形参 + 转发
- file: `automation/repair_agent/checkers/structural.py` → 保留
  `= 300` 默认值；无改动（兜底）
- file: `schemas/character/memory_timeline_entry.schema.json` →
  按决策更新字段；misunderstanding / concealment 改 array；删
  evidence_refs
- file: `schemas/character/behavior_rules.schema.json` →
  按决策补 maxItems / min-max length；删 evidence_refs
- file: `schemas/character/boundaries.schema.json` → 按决策补约束；
  删 item 级 evidence_ref 和顶层 evidence_refs
- file: `schemas/character/failure_modes.schema.json` → 按决策补约束；
  删顶层 evidence_refs
- file: `automation/persona_extraction/consistency_checker.py` →
  删掉对 memory_timeline `evidence_refs` 的空值警告分支
- file: `automation/prompt_templates/character_snapshot_extraction.md`
  → evidence_refs 叙述仍适用 stage_snapshot，不改
- file: `automation/prompt_templates/character_support_extraction.md`
  → misunderstanding / concealment 是数组、evidence_refs 从
  memory_timeline 删除
- file: `automation/prompt_templates/baseline_production.md` →
  若涉及 behavior_rules / boundaries / failure_modes evidence_refs 的
  示例或说明，同步删除
- file: `docs/requirements.md` → memory_timeline 条目结构示例更新
- file: `docs/architecture/schema_reference.md` → misunderstanding /
  evidence_refs 叙述更新
- file: `ai_context/requirements.md` → 仅在有具体字段映射时更新
- file: `ai_context/decisions.md` → 记一条"character schema bounds
  全部收口到 JSON schema"的决策

## 验证标准

- [ ] `python -c "import jsonschema; import json; [jsonschema.Draft202012Validator.check_schema(json.load(open(p))) for p in ['schemas/character/memory_timeline_entry.schema.json','schemas/character/behavior_rules.schema.json','schemas/character/boundaries.schema.json','schemas/character/failure_modes.schema.json']]"` 成功
- [ ] `python -c "from automation.persona_extraction.config import load_config; print(load_config())"` 不报错
- [ ] `grep -n "relationship_history_summary_max_chars" automation/config.toml automation/persona_extraction/config.py automation/persona_extraction/orchestrator.py automation/repair_agent/coordinator.py` 只在 structural.py 默认值里剩 1 处
- [ ] `grep -n "evidence_refs" schemas/character/memory_timeline_entry.schema.json schemas/character/behavior_rules.schema.json schemas/character/boundaries.schema.json schemas/character/failure_modes.schema.json` 全部为空
- [ ] import smoke: `python -c "from automation.persona_extraction import orchestrator, consistency_checker; from automation.repair_agent import coordinator"`
- [ ] 全库 grep 检查：docs / ai_context / prompt templates 里不再把这四 schema 的 evidence_refs 作为必填或示例出现

## 执行偏差

无。schema_reference.md 里 behavior_rules / boundaries / failure_modes
三节本来就不列字段级约束表，按 PRE 计划只更新 memory_timeline 这一节
即可——事前低估了"每份 schema 都要改 schema_reference"的必要性，实际
核对后确认无改动空间。

<!-- POST 阶段填写 -->

## 已落地变更

- `automation/config.toml` — 删除 `relationship_history_summary_max_chars`
  配置项 + 注释段。
- `automation/persona_extraction/config.py` — 从 `RepairAgentConfig`
  dataclass 里移除 `relationship_history_summary_max_chars` 字段 + 注释。
- `automation/persona_extraction/orchestrator.py` — Phase B 调用
  `run_repair(...)` 时不再传 `relationship_history_summary_max_chars`。
- `automation/repair_agent/coordinator.py` — `_build_pipeline` /
  `validate_only` / `run` 三个入口函数签名中全部移除该形参；内部
  `StructuralChecker()` 构造不再传此参数（保留内部 `= 300` 默认）。
- `automation/repair_agent/checkers/structural.py` — 未改动，保留
  `= 300` 默认值作为 schema 值的程序化镜像。
- `schemas/character/memory_timeline_entry.schema.json` —
  `subjective_experience` 加 `minLength:100, maxLength:200`；
  `emotional_impact maxLength:50`；`knowledge_gained maxItems:5`；
  `misunderstanding` 由对象改成 `array` (`maxItems:5`)，items 里
  `content maxLength:50, truth maxLength:50`；`concealment` 同样改
  `array` (`maxItems:5`)，items 里 `content maxLength:50,
  reason maxLength:50`；`relationship_impact.change maxLength:100`；
  删除 `evidence_refs` 字段定义。
- `schemas/character/behavior_rules.schema.json` — 按 PRE 条目给
  `core_goals` / `obsessions` / `emotional_triggers` /
  `emotional_reaction_map` / `relationship_behavior_map` /
  `habitual_behaviors` / `stress_response.*` 等全部加上
  `maxItems` + `maxLength`；`decision_making_style` 加
  `minLength:50, maxLength:200`；删除 `evidence_refs` 字段。
- `schemas/character/boundaries.schema.json` — 三个数组字段
  （`hard_boundaries` / `soft_boundaries` / `common_misconceptions`）
  加 `maxItems:15`；items 里字符串字段加 `maxLength` 50 / 50 / 100
  对应；删除 items 级 `evidence_ref` + 顶层 `evidence_refs`。
- `schemas/character/failure_modes.schema.json` — `common_failures` /
  `tone_traps` / `relationship_traps` / `knowledge_leaks` 全部
  加 `maxItems` 和对应 `maxLength`；删除顶层 `evidence_refs`。
- `automation/persona_extraction/consistency_checker.py` —
  `_check_evidence_refs_coverage()` 移除对 memory_timeline
  `evidence_refs` 空值的 warning 分支，只保留 `scene_refs` 空值
  警告；docstring 同步更新。
- `automation/prompt_templates/character_support_extraction.md` —
  "证据引用" 条改成 "场景回溯 / scene_refs"；memory_timeline 详细度
  要求里 `subjective_experience` 改成 100–200 字硬门控、
  `emotional_impact ≤ 50 字`、`knowledge_gained` 最多 5 条、
  `misunderstanding / concealment` 明确写作数组且各字段有上限。
- `docs/requirements.md` — §12.4.2 memory_timeline 条目结构示例
  里 `misunderstanding` / `concealment` 改成数组、`subjective_experience`
  标 100–200、`emotional_impact ≤ 50 字`、`knowledge_gained` 最多 5 条、
  `relationship_impact.change ≤ 100 字`、去掉 `evidence_refs` 字段；
  附加一段说明两者允许多条；Phase 3.5 检查项 #4 更新表述。
- `docs/architecture/schema_reference.md` — memory_timeline_entry
  小节字段列表补齐 subjective_experience / emotional_impact /
  knowledge_gained / misunderstanding / concealment /
  relationship_impact 的新约束。
- `ai_context/conventions.md` — 长度上下限条块改写成
  "schema 单一来源"说法，把 memory_timeline / behavior_rules /
  boundaries / failure_modes 的新上限按条列示。
- `ai_context/decisions.md` — 新增 27b 条目记录"字段级约束
  只在 JSON schema 声明"的决策 + 来源指针。

## 与计划的差异

无新增 / 删除项；实际动手过程中全部 PRE 列表条目均已落地。
`baseline_production.md` 在 PRE 中标为"按需修订"，实际审计后发现
该模板里 evidence_refs 的两处出现均指向 identity.json /
fixed_relationships（这两份 schema 不动），所以保持原状。

## 验证结果

- [x] jsonschema Draft 2020-12 schema 校验 — 四份 schema 全部通过；
      附加一轮样本 instance 校验验证 `knowledge_gained > 5` 会被拒。
- [x] `python -c "from automation.persona_extraction.config import
      load_config; ..."` — Config 实例化成功；
      `RepairAgentConfig` 已不含 `relationship_history_summary_max_chars`。
- [x] `grep relationship_history_summary_max_chars` — 仓库内仅剩
      `automation/repair_agent/checkers/structural.py:36,39` 两处
      （构造函数形参 + self 字段，默认 300），与验收标准一致。
- [x] `grep evidence_ref schemas/character/{memory_timeline,
      behavior_rules,boundaries,failure_modes}.schema.json` — 输出为空。
- [x] Import smoke — `automation.persona_extraction.orchestrator` /
      `consistency_checker` / `automation.repair_agent.coordinator`
      全部能正常 import，并且新的 `StructuralChecker()` 默认
      `_rel_history_max_chars == 300`。
- [x] 全库 grep 审查（子 agent 配合）— 未发现 docs / ai_context /
      prompt 里把四份 schema 的 evidence_refs 当作必填字段或示例遗留。

## Completed

- **Status**: DONE
- **Finished**: 2026-04-23 17:20:00 EDT
