# timeline_anchor_revert_and_bounds_not_target

- **Started**: 2026-04-24 19:49:13 EDT
- **Branch**: extraction/我和女帝的九世孽缘 → master worktree (`../persona-engine-master`)
- **Status**: PRE

## 背景 / 触发

`/post-check` 对前一轮 `world_stage_snapshot_bounds_cleanup`
（commit 2b3553b）报出 REVIEWED-FAIL，2 个 High 级 finding 加 3 条
Open Question。用户拍板：

1. `timeline_anchor` 撤销 ≤15→≤50 的放宽，回到 ≤15。这条直接消解
   post_processing.py 裸拷贝问题（Open Q #1）—— 派生侧不需要再压缩。
2. `works/我和女帝的九世孽缘/world/stage_snapshots/S001.json` +
   `S002.json` 保持原样，不动（Open Q #2 关闭）。登记到
   `docs/todo_list.md` 作 Residual Risk，未来 Phase 3 重抽或一致性
   检查碰到再处理。
3. 加一条新规约：prompt 中告诉 LLM "schema 给的 maxLength /
   maxItems 是**硬上限**，不是建议；够用即可，不要为凑数硬拉长 /
   硬凑 item"。落地策略：方案 C（顶层一段总规则 + 关键易凑数字段
   就近补一句）+ 写进 `ai_context/conventions.md` 当长期规约。

Open Q #3（角色 stage_snapshot "13 必填维度" 是否漂移）登记
`docs/todo_list.md`，本轮不追。

## 结论与决策

### A. timeline_anchor 回滚 ≤15

- `schemas/world/world_stage_snapshot.schema.json` —
  `timeline_anchor.maxLength` 50 → 15。
- `automation/prompt_templates/world_extraction.md` 第 28 行附近 —
  ≤50 改回 ≤15；删除"由 post_processing 压缩"那句尾巴；恢复"短锚"
  语调。
- `docs/architecture/schema_reference.md` — `timeline_anchor` 描述
  同步回 ≤15 短锚。
- `ai_context/decisions.md` 27h —— 删除"`timeline_anchor` widened
  from ≤15 to ≤50"这一句。其余（character_status_changes /
  evidence_refs 删除、stage_events 50→100）保留。
- `ai_context/handoff.md` 中只描述 anchor required，未提具体 cap，
  无需改。
- `docs/logs/2026-04-24_190612_*.md` 是历史 log，不重写（conventions
  豁免规则）。

### B. S001 / S002 + "13 维度" 登记 docs/todo_list.md

- 新增条目"world stage_snapshot S001/S002 与新 schema 不兼容"，
  原因 = 含已删除字段 / S002 `timeline_anchor` 超 ≤15、数组 item
  超 maxLength；处理方式 = Phase 3 重抽时随手修正，本轮不动。
- 新增条目"角色 stage_snapshot '13 必填维度' 文档表述疑漂移"，
  下次触及 character_snapshot 时核对一次实际 required 列表。

### C. bounds-not-target 规约

- `ai_context/conventions.md` 在 "Bounds only in schema" 那条规则
  下面新增一条："Bounds are caps, not targets"——LLM 看到的字段
  上下限只是硬门控，不是配额。prompt 模板编写时必须用一句话明示
  这点。
- `automation/prompt_templates/world_extraction.md` —— "核心规则"
  段第一条之前/之后插入一节"长度与条数硬规则"，明确 maxLength /
  maxItems 是硬上限不是配额；同时在易凑数的几个数组字段
  （current_world_state / relationship_shifts /
  unresolved_questions / foundation_corrections / location_changes /
  map_changes / stage_events）的字段说明里就近补一句"按需写，
  不为凑 N 项灌水"。
- `automation/prompt_templates/character_snapshot_extraction.md` ——
  同样加顶层段 + 关键 maxItems 字段（active_aliases / stage_events
  / relationships / knowledge_scope.* / dialogue_examples /
  action_examples 等可凑数的）就近补提示。
- 其他 extraction prompt（baseline_production / character_support /
  scene_split / summarization / analysis）—— 顶层段都加，就近补只在
  字段已有 maxItems 描述的位置加，避免噪音。

## 计划动作清单

- file: `schemas/world/world_stage_snapshot.schema.json` —
  timeline_anchor.maxLength 50 → 15。
- file: `automation/prompt_templates/world_extraction.md` —
  恢复 timeline_anchor ≤15 短锚描述；新增"长度与条数硬规则"顶层段；
  关键数组字段就近补 "按需写" 提示。
- file: `automation/prompt_templates/character_snapshot_extraction.md`
  — 同样顶层段 + 关键字段就近提示。
- file: `automation/prompt_templates/baseline_production.md` /
  `character_support_extraction.md` /`scene_split.md` /
  `summarization.md` / `analysis.md` — 顶层段；就近提示按需补。
- file: `docs/architecture/schema_reference.md` — timeline_anchor
  描述回滚 ≤15。
- file: `ai_context/decisions.md` 27h — 删除 timeline_anchor
  放宽那句。
- file: `ai_context/conventions.md` — Data Separation 段后新增
  "Bounds are caps, not targets" 条目。
- file: `docs/todo_list.md` — 新增两条 Residual Risk 条目（S001/S002
  schema 不兼容 + 13 维度核对）。

## 验证标准

- [ ] `python3 -c "import json, jsonschema;
      jsonschema.Draft202012Validator.check_schema(
        json.load(open('schemas/world/world_stage_snapshot.schema.json')))"`
      通过；timeline_anchor 16 字被拒，15 字通过。
- [ ] `grep -rn "timeline_anchor.*≤\?50\|maxLength.*50.*timeline_anchor\|放宽到 50"
      schemas/ automation/ docs/ ai_context/ prompts/`
      残留为 0（除 docs/logs/ 历史记录）。
- [ ] 每个 extraction prompt template 都包含一句明示
      "maxLength / maxItems 是硬上限不是配额"或等价表述。
- [ ] `ai_context/conventions.md` 含 "Bounds are caps, not targets"
      新规则。
- [ ] `docs/todo_list.md` 含两条 Residual Risk 条目。
- [ ] consistency_checker / extraction 主代码导入无报错。

## 执行偏差

- `automation/prompt_templates/scene_split.md` / `summarization.md` /
  `analysis.md` 三份原计划要"顶层段都加"，实际**未加**：
  - `scene_split` 已有等价的 rule #6（"不要为了结构整齐或凑数而切分"），
    再加一节属重复，反而稀释。
  - `summarization` / `analysis` 整份 prompt 不暴露 `maxLength` /
    `maxItems` 数字，没有具体锚点；硬塞通用规则只增加噪音。
  这三份按"已有等价表述 / 无锚点"理由跳过，规则的本意（不为凑数灌水）
  在 `ai_context/conventions.md` 那条 "Bounds are caps, not targets"
  里已经覆盖。

<!-- POST 阶段填写 -->

## 已落地变更

- `schemas/world/world_stage_snapshot.schema.json` —
  `timeline_anchor.maxLength` 50 → 15；description 回滚到"≤15 字短语"。
- `automation/prompt_templates/world_extraction.md` —
  - 第 6 条核心规则恢复 `timeline_anchor` ≤15 短锚表述，删掉
    "由 post_processing 压缩"那句尾巴；
  - 第 7 条 `stage_events` 末补一句"maxItems 是上限不是配额"，提及
    `current_world_state` / `relationship_shifts` /
    `foundation_corrections` / `location_changes` / `map_changes` /
    `unresolved_questions` 都按需写；
  - 在 "## 核心规则" 之前新增 "## 长度与条数硬规则" 顶层段。
- `automation/prompt_templates/character_snapshot_extraction.md` —
  在 "## 核心规则" 之前新增 "## 长度与条数硬规则" 顶层段，覆盖
  `active_aliases` / `target_voice_map` / `target_behavior_map` /
  `dialogue_examples` / `action_examples` / `relationships` /
  `stage_events` / `knowledge_scope.*` / `misunderstandings` /
  `concealments` 等高 maxItems 字段；同时点明"未出场角色继承"是
  规则要求不是凑数借口。
- `automation/prompt_templates/character_support_extraction.md` —
  同样新增 "## 长度与条数硬规则" 顶层段，覆盖 memory_timeline /
  baseline 修正 / dialogue_examples / action_examples 等场景。
- `automation/prompt_templates/baseline_production.md` —
  在 `## 规则` 段末追加一条 "`maxLength` / `maxItems` 是上限不是
  配额" 项目符号，与已有的"宁可保守少写"规则并列。
- `docs/architecture/schema_reference.md` — world_stage_snapshot
  字段表 `timeline_anchor` / `location_anchor` 描述合并回 ≤15。
- `ai_context/decisions.md` 27h — 删除 "`timeline_anchor` widened
  from ≤15 to ≤50" 那句；其余（删字段、stage_events 50→100）保留。
- `ai_context/conventions.md` Data Separation 段 — 在"Bounds only
  in schema"下方新增 "Bounds are caps, not targets" 规则。
- `docs/todo_list.md` "下一步" 段新增两条：
  - `[T-WORLD-SNAPSHOT-S001-S002-MIGRATE]` 既有 S001/S002 世界快照
    与新 schema 不兼容，下次 Phase 3 推进时迁移。
  - `[T-CHAR-SNAPSHOT-13-DIM-VERIFY]` 文档侧"13 必填维度"表述与
    schema 实际匹配核对。
- `docs/logs/2026-04-24_190612_world_stage_snapshot_bounds_cleanup.md`
  补回前一轮的 `<!-- /post-check 填写 -->` 段（在 extraction 上已写过，
  搬到 master worktree 一起 commit）。

## 与计划的差异

PRE 计划清单提到要给 `scene_split.md` / `summarization.md` /
`analysis.md` 加顶层"长度与条数硬规则"段，实际跳过（理由见上方
"## 执行偏差"），改由 conventions.md 的全局规约统一覆盖。其余
全部按计划落地。

## 验证结果

- [x] `python3 -c "import json, jsonschema;
      jsonschema.Draft202012Validator.check_schema(...)"` 通过；
      world `timeline_anchor.maxLength == 15`；15 字 instance 通过、
      16 字被拒。
- [x] `grep -rn "timeline_anchor.*≤\?50\|widened from ≤15 to ≤50\|
      由 post_processing 压缩"` 在 schemas / automation / docs /
      ai_context / prompts 下残留为 0（除 docs/logs/ 历史档）；
      `character_snapshot_extraction.md` 中 ≤50 是**角色** schema
      的 timeline_anchor，与本次 world 改动无关。
- [x] 4 份 extraction prompt template 均含明示"maxLength / maxItems
      是硬上限不是配额"或等价表述。
- [x] `ai_context/conventions.md` 含 "Bounds are caps, not targets"
      新规则。
- [x] `docs/todo_list.md` 含两条 Residual Risk 条目。
- [x] `python3 -c "from automation.persona_extraction
      import consistency_checker"` 导入无报错。

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 20:08:54 EDT
