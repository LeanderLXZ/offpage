# active_aliases_name_caps

- **Started**: 2026-04-24 06:22:24 EDT
- **Branch**: master (via worktree ../persona-engine-master；主 checkout 停留 extraction/我和女帝的九世孽缘 dirty 不动)
- **Status**: PRE

## 背景 / 触发

`/after-check` 复查 `character_schemas_bounds_round3`（2026-04-24_053139）
后，用户在 Open Question 2 决策：为 `active_aliases.active_names.name`
与 `active_aliases.hidden_identities.name` 补 `maxLength:10`，覆盖上一
轮遗漏的名字字符串上限。

## 结论与决策

- `schemas/character/stage_snapshot.schema.json`：
  - `active_aliases.active_names.items.oneOf[1].properties.name.maxLength = 10`
  - 字符串形 `active_aliases.active_names.items.oneOf[0].maxLength = 10`
    （与 object 形的 name 上限对齐；保持两种 item 形式等价）
  - `active_aliases.hidden_identities.items.properties.name.maxLength = 10`

其他字段不动。

## 计划动作清单

- file: `schemas/character/stage_snapshot.schema.json` → active_aliases 两处 name 及一处字符串 item 加 `maxLength:10`

## 验证标准

- [ ] 32 份 schema 全部 `Draft202012Validator.check_schema` 通过
- [ ] `python -c "from automation.persona_extraction import post_processing, orchestrator, prompt_builder, consistency_checker, validator"` import OK
- [ ] 断言：active_names oneOf[0] maxLength=10；oneOf[1].name.maxLength=10；hidden_identities.name.maxLength=10
- [ ] Smoke test：name 长度 11 → 校验 fail；长度 10 → pass

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

- `schemas/character/stage_snapshot.schema.json`
  - `active_aliases.active_names.items.oneOf[0]`（字符串形）加 `maxLength:10`
  - `active_aliases.active_names.items.oneOf[1].properties.name` 加 `maxLength:10`
  - `active_aliases.hidden_identities.items.properties.name` 加 `maxLength:10`
- `docs/architecture/schema_reference.md:272` — active_aliases 关键 section 行追加"每个 name ≤ 10 字"
- `ai_context/decisions.md` 27f — 扩写 active_names / hidden_identities 内部上限（name ≤10、context/reason ≤50）

## 与计划的差异

无。PRE 计划动作三处字段加 `maxLength:10` 全部落地；顺带同步 schema_reference / decisions.md 两处 docs。

## 验证结果

- [x] 32 份 schema `Draft202012Validator.check_schema` 通过
- [x] `post_processing / orchestrator / prompt_builder / consistency_checker / validator` import OK
- [x] 结构断言：active_names oneOf[0] maxLength=10；oneOf[1].name maxLength=10；hidden_identities.name maxLength=10
- [x] Smoke test：10 字 pass；11 字在字符串形 / object.name / hidden_identities.name 三处全部 REJECTED
- [x] 全仓库 grep `active_names` / `hidden_identities` 未发现除 schema + consistency_checker + docs 以外的引用点
- [x] CLAUDE.md / AGENTS.md 镜像：未触入口文件，N/A

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 06:24:07 EDT
