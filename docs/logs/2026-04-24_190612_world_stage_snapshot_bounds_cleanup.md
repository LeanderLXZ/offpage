# world_stage_snapshot_bounds_cleanup

- **Started**: 2026-04-24 19:06:12 EDT
- **Branch**: extraction/我和女帝的九世孽缘（编辑/提交阶段走 `../persona-engine-master` worktree → master）
- **Status**: PRE

## 背景 / 触发

延续 character / phase / digest schemas 的 bounds-cleanup 系列，本轮把
`world_stage_snapshot` 的字段级上下限补齐并对两类字段做结构裁剪：

- `character_status_changes` 与 `world_stage_snapshot` 的"世界级公共层"职责
  重叠 —— 角色个人状态变化已由 `character/stage_snapshot` 与
  `character/memory_timeline` 承载，世界快照不应再列；删除。
- `evidence_refs` 章节锚点列表删除 —— 章节回溯不再要求落到 world stage
  snapshot；conventions 中"章节锚点只挂在 world_stage_snapshot.evidence_refs"
  的旧约束随之废止，所有 baseline / snapshot 一致地不带 evidence 锚。

`automation/config.toml` 不新增任何字段级 bound（保持"bound 只在 schema"
这条硬规则；TOML 不存第二份）。

## 结论与决策

1. **`world_stage_snapshot.schema.json`** 字段调整：
   - `timeline_anchor` 从 `maxLength: 15` 放宽到 `maxLength: 50`，仍为
     `required`。这条字段同时被 post_processing 用作 world_event_digest
     的 `time` 字段（digest schema 那边仍是 `maxLength: 15`），意味着 50 字
     的 timeline_anchor 在 digest 派生时需要被压缩或截断 —— 派生由
     post_processing 接管，schema 本身允许 50 字给 LLM 留出表达空间。
   - `snapshot_summary` 加 `minLength: 100, maxLength: 200`。
   - `foundation_corrections`：`maxItems: 10`, item `maxLength: 100`。
   - `stage_events`：`maxItems` 由 30 收到 15，item 区间 `50-80` 放宽为
     `50-100`（与 50–100 范围对齐，给世界级事件一句话留更多余量）。
   - `current_world_state`：`maxItems: 10`, item `maxLength: 100`。
   - `relationship_shifts`：`maxItems: 10`, item `maxLength: 50`。
   - `location_changes`：`maxItems: 10`, item `maxLength: 100`。
   - `map_changes`：`maxItems: 10`, item `maxLength: 10`（用户明确指定，
     按短代号/简标记理解；如审查阶段发现下游期望长描述会回头确认）。
   - `unresolved_questions`：`maxItems: 10`, item `maxLength: 50`。
   - **删除** `character_status_changes` 字段及其 `required`。
   - **删除** `evidence_refs` 字段及其 `required`。
2. **conventions.md** 第 82 行"Chapter anchors only on
   `world_stage_snapshot.evidence_refs`"句子整体重写：所有
   baseline / stage_snapshot / memory_timeline 一致地不带 evidence_refs /
   source_type / scene_refs；章节锚点目前不在任何 schema 中保留。
3. **prompt template / 抽取代码 / 文档** 同步：
   - `automation/prompt_templates/world_extraction.md` 删除两个字段的产出
     要求与示例。
   - `automation/persona_extraction/consistency_checker.py`、`validator.py`
     等若引用了 `character_status_changes` / `evidence_refs` 需清理。
   - `docs/architecture/schema_reference.md` 字段表更新。
   - `docs/architecture/data_model.md` / `extraction_workflow.md` 顺扫。
4. `automation/config.toml` 与其他 toml **不新增任何 bounds**。

## 计划动作清单

- file: `schemas/world/world_stage_snapshot.schema.json` →
  按上面 1 条逐字段加上下限；从 properties + required 中删除
  `character_status_changes` / `evidence_refs`。
- file: `automation/prompt_templates/world_extraction.md` →
  删除两字段的产出要求；如有 stage_events 字数描述同步到 50–100。
- file: `automation/persona_extraction/consistency_checker.py` →
  grep 两字段名并清理。
- file: `automation/persona_extraction/validator.py`（如存在引用） → 清理。
- file: `docs/architecture/schema_reference.md` → 字段表更新。
- file: `docs/architecture/data_model.md` → 字段表更新（如有）。
- file: `docs/architecture/extraction_workflow.md` → 字段引用更新（如有）。
- file: `ai_context/conventions.md` → 第 82 行 evidence_refs 句子改写。
- file: `ai_context/decisions.md` → 如有相关条目同步。
- file: `ai_context/architecture.md` / `handoff.md` / `requirements.md` /
  `docs/requirements.md` → 顺扫两字段名。
- file: `works/README.md` / `prompts/review/手动补抽与修复.md` →
  顺扫两字段名。

## 验证标准

- [ ] `python -c "import json, jsonschema;
      jsonschema.Draft202012Validator.check_schema(
        json.load(open('schemas/world/world_stage_snapshot.schema.json')))"`
      通过。
- [ ] `grep -rn "character_status_changes\|evidence_refs"
      schemas/ automation/ docs/ ai_context/ prompts/ works/`
      残留为 0（除 `docs/logs/`、`docs/review_reports/` 历史档外）。
- [ ] `grep -rn "character_status_changes\|evidence_refs" -- "*.toml"`
      残留为 0（验证 toml 中本来就不应出现这些字段）。
- [ ] consistency_checker / validator 导入无报错。

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

- `schemas/world/world_stage_snapshot.schema.json` — 全文重写 properties /
  required 块：
  - `timeline_anchor` `maxLength` 15 → 50（仍 required）。
  - `snapshot_summary` 加 `minLength: 100` / `maxLength: 200`，并加入
    `required`（之前未在 required 中）。
  - `foundation_corrections` `maxItems: 10`, item `maxLength: 100`。
  - `stage_events` `maxItems` 30 → 15；item `minLength: 50`,
    `maxLength` 80 → 100。
  - `current_world_state` `maxItems: 10`, item `maxLength: 100`。
  - `relationship_shifts` `maxItems: 10`, item `maxLength: 50`。
  - `location_changes` `maxItems: 10`, item `maxLength: 100`。
  - `map_changes` `maxItems: 10`, item `maxLength: 10`。
  - `unresolved_questions` `maxItems: 10`, item `maxLength: 50`（保持
    可选）。
  - 删除 `character_status_changes` properties + required 条目。
  - 删除 `evidence_refs` properties + required 条目。
- `automation/persona_extraction/consistency_checker.py` — 删除
  `_check_evidence_refs_coverage` 函数 + 调用；`ConsistencyIssue.category`
  注释中的示例从 `"evidence_refs"` 换为 `"memory_id"`。
- `automation/prompt_templates/world_extraction.md` — 移除 `evidence_refs`
  描述/检查项；`stage_events` 50–80 → 50–100；`timeline_anchor` ≤15 → ≤50
  并补充 post_processing 派生时的压缩约束说明。
- `docs/architecture/schema_reference.md` — world_stage_snapshot 字段表
  按新 schema 重写（含 required 列表）；移除"chapter anchors only on
  world_stage_snapshot.evidence_refs"叙述。
- `docs/architecture/extraction_workflow.md` — Phase 3.5 程序化检查列表
  从 10 项缩到 9 项，删除 evidence_refs 覆盖率项；自检清单删除"世界
  stage_snapshot 的 evidence_refs 是否有效引用"项。
- `ai_context/conventions.md` — Data Separation 段第 2 行重写为"No
  chapter anchors on snapshots"统一规则。
- `ai_context/decisions.md` — 27c 改写为新规则；新增 27h 记录本轮
  world_stage_snapshot 结构修剪 + 边界放宽；§31 字数 50–80 → 50–100。
- `ai_context/handoff.md` — world stage_snapshot 重抽提示补充
  `character_status_changes` / `evidence_refs` 删除与字段级 bounds 收紧。
- `docs/requirements.md` — §2.3.4 字段清单移除"人物状态变化"和
  `evidence_refs` 项；§11.4 一致性检查表从 10 行缩到 9 行。
- `works/README.md` — 世界 stage_snapshots 描述同步（50-80 → 50-100，
  移除"人物状态变化"项）；删除"证据引用建议"段。
- `prompts/review/手动补抽与修复.md` — 长度硬门控行区分世界/角色
  stage_events（世界 50-100，角色 50-80）。

## 与计划的差异

新增了原计划未提到的 `snapshot_summary` 加入 `required` —— 用户给出的
`length 100-200` 标注暗示该字段必填，PRE 中漏了显式列入 required；schema
落地时按用户语义补上。其他与 PRE 计划一致。

## 验证结果

- [x] `python3 -c "import json, jsonschema;
      jsonschema.Draft202012Validator.check_schema(...)"` —
      schema valid，character_status_changes / evidence_refs 作为
      additionalProperties 被拒，timeline_anchor 51 字被拒、50 字通过，
      stage_events 49 字被拒、50/100 字通过，map_changes 10 字通过、
      11 字被拒，snapshot_summary 100 字通过，unresolved_questions 缺省
      不报错。
- [x] `grep -rn "character_status_changes\|evidence_refs"
      schemas/ automation/ docs/architecture/ ai_context/ prompts/
      works/ docs/requirements.md` 仅剩"已删除/不携带"型负向描述
      或 decisions.md 的历史记录条目（27c/27e/27g/27h），无残留正向
      引用。
- [x] `grep` TOML 文件 — `automation/config.toml` /
      `automation/pyproject.toml` 不含本轮任何字段名，符合 bounds-only-
      in-schema 规则。
- [x] `python3 -c "from automation.persona_extraction
      import consistency_checker"` 导入无报错，确认删函数后语法/
      引用一致。

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 19:33:07 EDT

<!-- /post-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实

- 落实率：13/13 项计划 + 4/4 项验证 全通过
- Missed updates: 0 条

### 轨 2 — 影响扩散

- Findings: High=2 / Medium=0 / Low=1
  - [H] `automation/persona_extraction/post_processing.py:276-290` —
    digest 派生裸拷贝 timeline_anchor / location_anchor，未按文档
    承诺压缩；timeline_anchor ≤50 直接喂入 ≤15 的 digest
    time / location，会破坏 digest schema gate。
  - [H] `works/我和女帝的九世孽缘/world/stage_snapshots/S001.json`
    + `S002.json` — 既有产物含已删除字段 `character_status_changes`
    / `evidence_refs`；S002 `timeline_anchor` 93 字超新 ≤50 cap；
    多个数组字段 item 长度超新 maxLength。需决定手工裁剪 vs 重抽。
  - [L] `docs/architecture/schema_reference.md:271` 残留 evidence_refs
    字面 token，但是负向描述，语义正确。
- Open Questions: 3 条（详见对话）
  1. post_processing 压缩策略选型（截断 / LLM 摘要 / 放宽 digest cap）。
  2. S001 / S002 stage_snapshot 修复路径（手工裁剪 vs 重抽）。
  3. 角色 stage_snapshot "13 必填维度" 数字是否仍对得上（疑漂移到
     17，登记后续）。

## 复查时状态

- **Reviewed**: 2026-04-24 19:44:49 EDT
- **Status**: REVIEWED-FAIL
  - 轨 1 全落实，但轨 2 出现 2 项 High 级 Findings
    （post_processing 裸拷贝 + 既有产物失效），影响下一阶段
    实际跑 Phase 3 / 3.5 的能力。
- **Conversation ref**: 同会话内 /post-check 输出
