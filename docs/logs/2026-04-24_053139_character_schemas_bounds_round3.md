# character_schemas_bounds_round3

- **Started**: 2026-04-24 05:31:39 EDT
- **Branch**: master (via worktree ../persona-engine-master；主 checkout 停留 extraction/我和女帝的九世孽缘 dirty 不动)
- **Status**: PRE

## 背景 / 触发

延续 `phase_schemas_bounds_cleanup`（2026-04-23_203404）+
`phase_schemas_bounds_followups`（2026-04-24_021238）的字段级上下限收口
系列。本轮用户会话给出新一批指标清单，焦点是 `stage_snapshot` 全身 +
`voice_rules.dialogue_examples` + `behavior_rules` 的 `relationship_behavior_map`
重命名与若干窄化。目标仍是「bounds only in schema；TOML / prompt template
不存第二份」。

主 checkout 当前 dirty（voice_rules.schema.json 已有一笔 typical_expressions
5→10 的未提交改动，语义与本轮指标相符但未合入 master）。按 /go 契约：
主 checkout 原封不动，所有改动落在 `../persona-engine-master` worktree
的 master 上；Step 9 时 extraction 分支因 dirty 会被记入 todo_list 推迟
merge。

## 结论与决策

### stage_snapshot.schema.json

- 字段收口按用户清单逐一落地。特别注意：
  - `timeline_anchor` 加 `maxLength:50` + required
  - `snapshot_summary` 加 `minLength:100 / maxLength:200`
  - `active_aliases` 下：`active_names` item（及 object.name / context）
    补上限；`hidden_identities` item + reason 补上限；`known_as` 映射
    `propertyNames` + 内层数组 + item 加上限
  - `current_status / current_personality / current_mood` 已有 maxItems:10，
    补 item `maxLength:50`
  - `emotional_baseline.dominant_traits` item `maxLength:15` + `maxItems:10`
  - `emotional_baseline.active_goals/obsessions/fears/wounds` 各 `maxItems:10`，
    item `maxLength:50`
  - `voice_state.tone_summary` `maxLength:100`
  - `voice_state.speech_patterns / vocabulary_preferences` 各 `maxItems:15 / item:50`
  - `voice_state.signature_phrases` `maxItems:30 / item:10`
  - `voice_state.taboo_patterns` `maxItems:15 / item:30`
  - `voice_state.dialogue_examples`：`maxItems:10`；item 追加 `quote:30`、
    `context:50`；**删除 `evidence_ref` 属性**
  - `voice_state.emotional_voice_map`：`maxItems:15`；item.voice_shift 已有
    50，本轮保持；`typical_expressions` 改为 `maxItems:10 / item:15`；
    `dialogue_examples` 与上同样改：`maxItems:10`, quote:30, context:50,
    **删除 evidence_ref**
  - `voice_state.target_voice_map`：`maxItems:10`；item.target_type 加
    `maxLength:15`；voice_shift 加 `maxLength:50`；`typical_expressions`
    改为 `maxItems:10 / item:15`；`dialogue_examples` 改为 `maxItems:10`,
    quote:30, context:50, **删除 evidence_ref**
  - `behavior_state.core_goals/obsessions` 各 `maxItems:10 / item:50`
  - `behavior_state.decision_making_style` `minLength:50 / maxLength:200`
  - `behavior_state.emotional_triggers` `maxItems:15`；trigger:50；reaction:100
  - `behavior_state.emotional_reaction_map`：`maxItems:15`；
    `emotion:10`；`internal_response:50`；`typical_actions` `maxItems:5 / item:50`；
    `recovery_pattern:50`
  - `behavior_state.target_behavior_map`：`maxItems:10`；item.target_type
    `maxLength:15`；`behavior_shift:100`；`typical_actions` `maxItems:5 / item:50`；
    `action_examples` `maxItems:5`、action:50、context:100，**删除 evidence_ref**
  - `behavior_state.habitual_behaviors` `maxItems:15 / item:50`
  - `behavior_state.stress_response.*` 三字段 `maxLength:50`
  - `boundary_state.soft_boundaries`：`maxItems:15`；rule/exception_condition/stage_note
    各 `maxLength:50`
  - **`boundary_state.hard_boundaries` 新增**：`maxItems:15`，与
    `boundaries.schema.json` 的 hard_boundaries item 形状一致（rule:50 + reason:50，
    required=["rule"]）。用户 brief 原文镜像 boundaries.schema 里的描述。
  - `boundary_state.common_misconceptions` `maxItems:15`；misconception:50；reality:100
  - `relationship_state_summary` `maxLength:100`
  - `relationships`：已有 maxItems:10；
    - `target_label` `maxLength:30`
    - `summary` `maxLength:50`
    - `attitude` `maxLength:50`
    - `voice_shift` `maxLength:50`
    - `behavior_shift` `maxLength:50`
    - `driving_events` `maxItems:10 / item:50`
    - `target_known_status` `maxLength:50`
    - `relationship_history_summary` 现有 `maxLength:300` → 收紧到 `maxLength:100`
      （用户新指标）
  - `misunderstandings`：本轮用户给 `maxItems:15`；content:50；truth:50；cause:50
  - `concealments`：本轮用户给 `maxItems:15`；content:50；reason:50
  - `stage_delta.trigger_events` `maxItems:10 / item:50`
  - `stage_delta.personality_changes` `maxItems:10`；change:50；influenced_by:30
  - `stage_delta.relationship_changes` `maxItems:10`；change:50；driving_event:50
  - `stage_delta.mood_shift` `maxLength:100`
  - `stage_delta.voice_shift` `maxLength:100`
  - **`character_arc` 由 object 改为单一 string `maxLength:200`**
    （需要同步删除 arc_summary/arc_stages/current_position object 结构）
  - **`memory_refs` 顶层字段删除**
  - **`evidence_refs` 顶层字段删除**（含 `required` 里移除）

注：`knowledge_scope` / `stage_events` / `chapter_scope` 用户本轮未点名，
保持上轮状态不动（已 bound）。

### voice_rules.schema.json

用户清单仅给了一条：`voice_state dialogue_examples`。voice_rules 里
dialogue_examples 实际出现在 3 处（top-level、`emotional_voice_map` 内、
`target_voice_map` 内），考虑到：
- stage_snapshot 的对应 3 处都统一了上限（#of terms<10, quote<30,
  context<50, 删 evidence_ref）
- voice_rules 是 stage_snapshot.voice_state 的 baseline 参照锚点，两处
  dialogue_examples 结构本应平行

→ 本轮对 voice_rules **所有三处 dialogue_examples** 做同款收口：
  `maxItems:10`；item.quote `maxLength:30`；item.context `maxLength:50`；
  **删除 item.evidence_ref property**。若用户后续 /after-check 认为只改
  top-level，改回来代价小；反向（漏改）会留结构不一致。

### behavior_rules.schema.json

- `emotional_reaction_map.items.emotion` 加 `maxLength:10`
- `emotional_reaction_map.items.typical_actions` 加 `maxItems:5`（item 上限
  已是 50，保留）
- **`relationship_behavior_map` 改名为 `target_behavior_map`**
- 内部 `relationship_type` 改名为 `target_type`，加 `maxLength:15`
- 其余字段（default_stance / boundaries / escalation_pattern）保持不动

### 刻意不动

- `stage_snapshot.active_aliases.primary_name` / `character_id`
  / `work_id` 等字符串用户未点名
- `voice_rules` 里除 dialogue_examples 之外的字段（上一轮已收口）
- `behavior_rules` 的 default_stance / boundaries / escalation_pattern
  在 `relationship_behavior_map` item 内，本轮用户只要求重命名外壳 +
  `target_type` 收口，内部其余字段保持原 50 字上限

### 代码 / prompt / 文档连带

- `automation/persona_extraction/` 下若有引用
  `character_arc.arc_summary/arc_stages/current_position`、
  `memory_refs`、`stage_snapshot.evidence_refs`、`relationship_behavior_map`、
  `relationship_type` 的位置，需同步
- `automation/prompt_templates/` 相关 prompt 的字段清单需对齐（character_support_extraction.md 为主）
- `docs/requirements.md` / `docs/architecture/schema_reference.md` 字段表需同步
- `ai_context/conventions.md` Data Separation 内列示例（stage_snapshot `evidence_refs` 的说法本轮反转，要更新）
- `ai_context/decisions.md` 追加本轮收口决策

## 计划动作清单

### 1 Schema

- file: `schemas/character/stage_snapshot.schema.json` → 按上「结论与决策」stage_snapshot 段逐字段改
- file: `schemas/character/voice_rules.schema.json` → 3 处 dialogue_examples 统一改（maxItems:10, quote:30, context:50, 删 evidence_ref）
- file: `schemas/character/behavior_rules.schema.json` → emotional_reaction_map.emotion maxLength:10 + typical_actions maxItems:5；`relationship_behavior_map` → `target_behavior_map`；内部 `relationship_type` → `target_type` + maxLength:15

### 2 代码

- file: `automation/persona_extraction/post_processing.py` → grep `relationship_behavior_map`、`relationship_type`、`character_arc.arc_`、`memory_refs`、`evidence_refs`（stage_snapshot 侧）；发现点同步
- file: `automation/persona_extraction/consistency_checker.py` → 同上 grep
- file: `automation/persona_extraction/validator.py` → 同上 grep
- file: `automation/persona_extraction/prompt_builder.py` → 同上 grep
- file: `automation/persona_extraction/orchestrator.py` → 同上 grep

### 3 Prompt templates

- file: `automation/prompt_templates/character_support_extraction.md` → stage_snapshot 字段清单按新 schema 同步（character_arc 变 string、去 memory_refs/evidence_refs、target_behavior_map 名字、dialogue_examples 去 evidence_ref 等）
- file: `automation/prompt_templates/baseline_production.md` → voice_rules / behavior_rules 相关字段同步（dialogue_examples 去 evidence_ref；behavior_rules 的 target_behavior_map / target_type 改名）
- file: `automation/prompt_templates/world_extraction.md` → 扫一下是否引用（应无，保留确认）

### 4 文档

- file: `docs/requirements.md` → stage_snapshot / voice_rules / behavior_rules 字段映射表 + JSON 示例同步
- file: `docs/architecture/schema_reference.md` → 三份 schema 段落同步
- file: `docs/architecture/data_model.md` → 如有 character_arc / memory_refs / evidence_refs / relationship_behavior_map 出现则同步

### 5 ai_context

- file: `ai_context/conventions.md` Data Separation 段 → 收口清单扩写（stage_snapshot 本轮改动点、character_arc 降级、baseline removed 条目确认 stage_snapshot 侧也去 `memory_refs` / `evidence_refs`）——等等，`evidence_refs` 原本上轮的决策是"保留在 stage_snapshot"，本轮用户反转删除，需要显式更新
- file: `ai_context/decisions.md` → 追加 27f / 27g 条目：stage_snapshot 全身收口 + character_arc 降级 + stage_snapshot evidence_refs/memory_refs 取消
- file: `ai_context/handoff.md` → 再补一条 advisory：现有 extraction 产物里如果 character_arc 是 object / 有 memory_refs / 有 evidence_refs / 有 relationship_behavior_map 会在新 schema 下 INVALID
- file: `ai_context/architecture.md` → 如有相关字段描述则同步

### 6 其他

- file: `schemas/README.md` → 若有 stage_snapshot 字段级说明或 relationship_behavior_map 名字出现，同步
- file: `docs/todo_list.md` → 若上一轮 /after-check 留下本轮相关条目（stage_snapshot 收口/character_arc）则清除

## 验证标准

- [ ] 32 份 schema 全部 `Draft202012Validator.check_schema` 通过
- [ ] `python -c "from automation.persona_extraction import post_processing, orchestrator, prompt_builder, consistency_checker, validator"` import OK
- [ ] `grep -rn "relationship_behavior_map\|relationship_type" schemas/ automation/ docs/ ai_context/ simulation/` 零匹配（除 docs/logs 历史）
- [ ] `grep -rn "character_arc" schemas/character/stage_snapshot.schema.json` 为 string 类型描述，不再出现 `arc_summary / arc_stages / current_position`
- [ ] `grep -rn "memory_refs" schemas/character/stage_snapshot.schema.json` 零匹配
- [ ] `grep -rn "\"evidence_refs\"" schemas/character/stage_snapshot.schema.json` 零匹配
- [ ] `grep -rn "evidence_ref" schemas/character/voice_rules.schema.json` 零匹配（删除后的 dialogue_examples item 无此 property）
- [ ] `grep -rn "evidence_ref" schemas/character/stage_snapshot.schema.json` 零匹配
- [ ] stage_snapshot 的 `boundary_state.hard_boundaries` 存在且 item required `["rule"]`，rule maxLength 50
- [ ] Smoke test：构造一个合法 stage_snapshot 最小实例 → schema 校验 pass；构造一个超限（relationship_history_summary 200 字）→ 校验 fail
- [ ] 全仓库未引入 "已废弃 / legacy / 原为 / 旧" 字样
- [ ] CLAUDE.md / AGENTS.md 镜像：本轮未触入口文件，N/A

## 执行偏差

### 偏差 1：voice_rules 三处 dialogue_examples 全部应用

用户清单里 `voice_rules` 仅给出一条（`voice_state dialogue_examples`），
但 voice_rules schema 实际有 3 处 `dialogue_examples`（top-level、
`emotional_voice_map` 内、`target_voice_map` 内）。stage_snapshot 侧
3 处已统一收口；若 voice_rules 只改 top-level，baseline ↔ stage 结构
不对称，并留下 `evidence_ref` 残留属性漏洞。决策：三处统一应用同套
bounds（maxItems:10、quote:30、context:50、删 evidence_ref）。若用户
/after-check 判断只需改 top-level，反向修补代价小；漏改代价大。

### 偏差 2：handoff.md advisory 扩写

原计划只在 handoff 追加角色 stage_snapshot 四条 break points。执行中
发现 voice_rules 的 dialogue_examples 去 evidence_ref、behavior_rules
的 relationship_behavior_map → target_behavior_map 同样会让现存产物
在新 schema 下失败，补齐全部三类改动到 Extraction-branch advisory。

### 偏差 3：StructuralChecker 常量更新（连带）

`relationship_history_summary` 上限从 300 → 100 变化同时要求
`automation/repair_agent/checkers/structural.py:36` 的默认值参数从
`300` 改为 `100`，与 schema 保持一致——这是决策 27b 内写明的契约。
PRE 计划动作清单漏列 repair_agent 子目录，执行时识别后补入。

<!-- POST 阶段填写 -->

## 已落地变更

### Schema

- `schemas/character/stage_snapshot.schema.json`（整表重写）
  - required：加 `timeline_anchor`；去 `evidence_refs`
  - timeline_anchor：加 `maxLength:50`
  - snapshot_summary：加 `minLength:100 / maxLength:200`
  - active_aliases.active_names：`maxItems:5`；object name 内 context `maxLength:50`
  - active_aliases.hidden_identities：`maxItems:5`；reason `maxLength:50`
  - active_aliases.known_as：`maxProperties:10`
  - current_status / current_personality / current_mood：已有 maxItems:10，补 item `maxLength:50`
  - emotional_baseline.dominant_traits：`maxItems:10`、item `maxLength:15`
  - emotional_baseline.active_goals / active_obsessions / active_fears / active_wounds：各 `maxItems:10`、item `maxLength:50`
  - voice_state.tone_summary：`maxLength:100`
  - voice_state.speech_patterns / vocabulary_preferences：`maxItems:15`、item `maxLength:50`
  - voice_state.signature_phrases：`maxItems:30`、item `maxLength:10`
  - voice_state.taboo_patterns：`maxItems:15`、item `maxLength:30`
  - voice_state.dialogue_examples：`maxItems:10`；item quote `maxLength:30`、context `maxLength:50`；删 `evidence_ref`；required 改 ["quote","context"]
  - voice_state.emotional_voice_map：`maxItems:15`；emotion `maxLength:10`；voice_shift `maxLength:50`；typical_expressions `maxItems:10 / item:15`；dialogue_examples `maxItems:10 / quote:30 / context:50 / 删 evidence_ref`
  - voice_state.target_voice_map：`maxItems:10`；target_type `maxLength:15`；voice_shift `maxLength:50`；typical_expressions `maxItems:10 / item:15`；dialogue_examples `maxItems:10 / quote:30 / context:50 / 删 evidence_ref`
  - behavior_state.core_goals / obsessions：`maxItems:10 / item:50`
  - behavior_state.decision_making_style：`minLength:50 / maxLength:200`
  - behavior_state.emotional_triggers：`maxItems:15`；trigger `maxLength:50`；reaction `maxLength:100`
  - behavior_state.emotional_reaction_map：`maxItems:15`；emotion `maxLength:10`；internal_response `maxLength:50`；typical_actions `maxItems:5 / item:50`；recovery_pattern `maxLength:50`；external_behavior `maxLength:50`
  - behavior_state.target_behavior_map：`maxItems:10`；target_type `maxLength:15`；behavior_shift `maxLength:100`；typical_actions `maxItems:5 / item:50`；action_examples `maxItems:5`、action `maxLength:50`、context `maxLength:100`；删 evidence_ref；action_examples item required 改 ["action","context"]
  - behavior_state.habitual_behaviors：`maxItems:15 / item:50`
  - behavior_state.stress_response.coping_style / breaking_point / post_crisis_behavior：各 `maxLength:50`
  - boundary_state.hard_boundaries：**新增** `maxItems:15`、item required ["rule"]、rule `maxLength:50`、reason `maxLength:50`（与 boundaries.schema.json hard_boundaries 同形）
  - boundary_state.soft_boundaries：`maxItems:15`；rule/exception_condition/stage_note 各 `maxLength:50`
  - boundary_state.common_misconceptions：`maxItems:15`；misconception `maxLength:50`；reality `maxLength:100`
  - relationship_state_summary：`maxLength:100`
  - relationships.items：target_label `maxLength:30`；summary/attitude/voice_shift/behavior_shift/target_known_status 各 `maxLength:50`；driving_events `maxItems:10 / item:50`；relationship_history_summary `maxLength:100`（原 300 → 100）
  - misunderstandings：`maxItems:15`（原 20）；content/truth/cause 各 `maxLength:50`
  - concealments：`maxItems:15`（原 20）；content/reason 各 `maxLength:50`
  - stage_delta.trigger_events：`maxItems:10 / item:50`
  - stage_delta.personality_changes：`maxItems:10`；change `maxLength:50`；influenced_by `maxLength:30`
  - stage_delta.relationship_changes：`maxItems:10`；change `maxLength:50`；driving_event `maxLength:50`
  - stage_delta.mood_shift / voice_shift：各 `maxLength:100`
  - character_arc：object → **string**，`maxLength:200`（删除 arc_summary / arc_stages / current_position 子对象）
  - 顶层 `memory_refs`：**删除**
  - 顶层 `evidence_refs`：**删除**（同步从 required 移除）

- `schemas/character/voice_rules.schema.json`（3 处 dialogue_examples 统一改）
  - top-level dialogue_examples：`maxItems:10`；quote `maxLength:30`；context `maxLength:50`；**删 evidence_ref**
  - emotional_voice_map.items.typical_expressions：`maxItems:5 → 10`
  - emotional_voice_map.items.dialogue_examples：`maxItems:10`；quote `maxLength:30`；context `maxLength:50`；**删 evidence_ref**
  - target_voice_map.items.typical_expressions：`maxItems:5 → 10`
  - target_voice_map.items.dialogue_examples：`maxItems:10`；quote `maxLength:30`；context `maxLength:50`；**删 evidence_ref**

- `schemas/character/behavior_rules.schema.json`
  - emotional_reaction_map.items.emotion：加 `maxLength:10`
  - emotional_reaction_map.items.typical_actions：加 `maxItems:5`
  - `relationship_behavior_map` → `target_behavior_map`（rename）
  - 内部 `relationship_type` → `target_type`，加 `maxLength:15`

### 代码

- `automation/persona_extraction/consistency_checker.py`
  - `_check_evidence_refs_coverage`：删除 character stage_snapshot `evidence_refs` 覆盖分支（仅保留 world 侧）；docstring 同步
- `automation/repair_agent/checkers/structural.py:36`
  - `relationship_history_summary_max_chars` 默认值 `300 → 100`

### Prompt templates

- `automation/prompt_templates/character_snapshot_extraction.md`
  - 字段清单全面同步：target_voice_map/target_behavior_map ≤ 10、emotional_voice_map/emotional_reaction_map ≤ 15、dialogue_examples ≤ 10、misunderstandings/concealments ≤ 15、hard_boundaries 新维度、typical_expressions ≤ 10
  - character_arc 改写为单一字符串 ≤ 200 字
  - 加入 timeline_anchor ≤ 50 字 + snapshot_summary 100–200 字必填条目
  - 删除 evidence_refs 相关规则（原第 3 条核心规则、风格一致性要求中该行、退化信号中该行、本阶段输出清单中该行）
  - 字段命名错误表 relationship_behavior_map 行改写为"baseline 与 stage 快照同名"
  - relationship_history_summary 描述从 300 字 → 100 字
- `automation/prompt_templates/baseline_production.md`
  - behavior_rules 骨架清单 `relationship_behavior_map` → `target_behavior_map`

### 文档

- `docs/architecture/schema_reference.md`
  - voice_rules 字段上下限段：typical_expressions 5 → 10；补 dialogue_examples 三处统一上下限 + 无 evidence_ref 说明
  - behavior_rules 字段上下限段：补 emotion ≤ 10、typical_actions ≤ 5、target_behavior_map ≤ 10 + target_type ≤ 15 说明
  - stage_snapshot 关键 section 表整表重写：新增 timeline_anchor / snapshot_summary 行；matrix 容量全部更新；boundary_state 列出 hard/soft/common_misconceptions；relationships 更新 100；misunderstandings/concealments 改 15；character_arc 改单一字符串
  - 自包含契约：required 改 timeline_anchor/snapshot_summary 入列、evidence_refs 去除；加注 memory_refs/evidence_refs 均移除

- `docs/architecture/extraction_workflow.md`
  - 一致性检查项 #4 + 最终 checklist 双处 evidence_refs 覆盖率：角色 stage_snapshot 已脱离，只剩世界侧

- `simulation/contracts/baseline_merge.md:59`
  - character_arc 描述从 "object (arc_summary, key nodes, current_position)" → "single string ≤ 200 chars"

- `docs/requirements.md`
  - §快照完整性检查清单：target_voice_map/target_behavior_map ≤ 10、emotional_voice_map/emotional_reaction_map ≤ 15、dialogue_examples ≤ 10、misunderstandings/concealments ≤ 15、hard_boundaries/soft_boundaries/common_misconceptions 各 15；character_arc 改单一字符串；timeline_anchor / snapshot_summary 条目加入
  - §字段条数上限汇总表：对应行全部更新，新增 boundary_state 三数组行
  - §L1/L2 表：L2 `relationship_history_summary_max_chars` 描述里 300 → 100
  - §程序化检查项 #4：evidence_refs 覆盖率描述更新（仅世界侧）
  - §退化信号：去 evidence_refs 项（两处）
  - §2.7 附近 stage_events evidence_refs 叙述：只保留世界层

### ai_context

- `ai_context/conventions.md` Data Separation 段
  - 长度门控示例：补 timeline_anchor ≤ 50、snapshot_summary 100–200、character_arc string ≤ 200、relationship_history_summary 300 → 100
  - 计数门控示例：补 target_behavior_map ≤ 10、stage dialogue_examples ≤ 10、target_voice_map/target_behavior_map stage ≤ 10、emotional_voice_map/emotional_reaction_map stage ≤ 15、misunderstandings/concealments stage ≤ 15、boundary_state.* ≤ 15
  - 已移除字段条目：character stage_snapshot 去 evidence_refs / memory_refs；dialogue_examples/action_examples 去 evidence_ref；behavior_rules 重命名两项

- `ai_context/decisions.md`
  - 27b 里 StructuralChecker 常量 300 → 100
  - 新增 27f（stage_snapshot 全身 bounds）+ 27g（structural prunes：character_arc 降级 + memory_refs/evidence_refs 移除 + evidence_ref 属性统一删 + behavior_rules rename）

- `ai_context/handoff.md`
  - Extraction-branch advisory 补三条 break points：character stage_snapshot 全身 / voice_rules dialogue_examples evidence_ref / behavior_rules rename

## 与计划的差异

- 偏差 1 / 2 / 3（详见上文「执行偏差」）
- PRE 计划列出的 `automation/persona_extraction/post_processing.py` / `orchestrator.py` / `prompt_builder.py` / `validator.py` 经 grep 未发现涉及本轮重命名字段的使用点（仅 consistency_checker 里一处；其余已在更早的 /go 轮次处理完毕）
- `ai_context/architecture.md` 里的 `character_arc` 引用无需改——L87 只提字段名，没展开形状

## 验证结果

- [x] 32 份 schema 全部通过 `Draft202012Validator.check_schema`
- [x] `python -c "from automation.persona_extraction import post_processing, orchestrator, prompt_builder, consistency_checker, validator"` import OK
- [x] `grep -rn "relationship_behavior_map|relationship_type"` 在 schemas / automation / docs / ai_context / simulation 中：仅剩 3 处刻意保留（ai_context/conventions.md 记录改名、ai_context/decisions.md 27g、ai_context/handoff.md advisory、prompt template 错误字段表教 LLM 别用旧名）——零功能性残留
- [x] `grep -rn "character_arc"` 在 schemas/character/stage_snapshot.schema.json 仅出现在 string 字段定义处（不再有 arc_summary / arc_stages / current_position）
- [x] `grep -rn "memory_refs"` 在 schemas/ + automation/ 零匹配
- [x] `grep -rn "evidence_refs"` 在 schemas/character/stage_snapshot.schema.json 零匹配
- [x] `grep -rn "evidence_ref"`（singular） 在 schemas/ + automation/ 零匹配（仅 ai_context + docs/architecture 描述段保留解释文字）
- [x] stage_snapshot.boundary_state.hard_boundaries 存在、item required ["rule"]、rule maxLength:50、reason maxLength:50，与 boundaries.schema.json hard_boundaries 同形
- [x] Smoke test（jsonschema 动态校验）：最小合法 stage_snapshot pass；character_arc 传 object reject；relationship_history_summary 150 字 reject；hard_boundaries 条目通过；顶层 evidence_refs / memory_refs reject；voice_rules dialogue_examples 带 evidence_ref reject；behavior_rules target_behavior_map 接受、relationship_behavior_map reject
- [x] 全仓库 diff 未引入 "已废弃 / legacy / 原为 / 旧 / deprecated" 字样
- [x] CLAUDE.md / AGENTS.md 镜像：本轮未触入口文件，N/A

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 05:57:24 EDT

<!-- /after-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：16/16 项计划动作 + 3/3 项偏差补丁 + 11/11 项可执行验证（CLAUDE/AGENTS 镜像 N/A）
- Missed updates: 无

### 轨 2 — 影响扩散
- Findings: High=0 / Medium=0 / Low=3
  - [L] `docs/requirements.md:2156` "13 个必填维度"枚举数字前轮遗留不准；本轮 required 实际含 timeline_anchor/snapshot_summary 17 项
  - [L] `schemas/character/stage_snapshot.schema.json` active_aliases.active_names 字符串形 + `name` 未加 maxLength（用户 brief 未指定、PRE 第 29 点提到但偏差未显式登记）
  - [L] ai_context/requirements.md + architecture.md 未标 character_arc 新形态；两处仅列举字段名不展开形状，可不改
- Open Questions: 3 条（详见对话）
  1. extraction 分支既有 S001/S002 产物迁移策略
  2. active_aliases 内部字符串是否补 maxLength
  3. StructuralChecker `relationship_history_summary_max_chars` 外部参数是否保留

## 复查时状态

- **Reviewed**: 2026-04-24 06:15:28 EDT
- **Status**: REVIEWED-PASS
  - 轨 1 全落实；轨 2 无 High/Medium，仅 3 条 Low
- **Conversation ref**: 同会话内 /after-check 输出
