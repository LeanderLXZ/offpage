# check_review_followup_cancel_futures_and_doc_alignment

- **Started**: 2026-05-14 00:44:11 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

上一轮 `/full-review` 产出 [2026-05-13_230056_opus-4-7_full-review-findings.md](../review_reports/2026-05-13_230056_opus-4-7_full-review-findings.md)（H1 + 9 M + 6 L + 4 OQ）。`/check-review` 复核全部 finding 真实，逐条产出方案草稿与 4 个 OQ。user 指令："把建议修的全修了；建议留 todo 的跳过；建议跳过的跳过。同时判断是否过度工程——过度工程则跳过 / 取最小可行修复。"

## 结论与决策

按 `/check-review` 建议清单分类执行（OQ 全部按推荐候选 a）：

**修**（11 条）：
- **H1**（5 站点 cancel_futures 缺失）— OQ4 候选 b 实施：per-site 就地补，**不抽 helper**（5 站点 × 3 行，helper 1 层抽象不值；reference pattern at orchestrator.py:732-737 / 1004-1011 已是 per-site 形态，沿用即可）。判断：抽 helper 是过度工程，**跳过 helper 路径，取 per-site 最小可行**。
- **M1**：[schemas/README.md:12](../../schemas/README.md#L12) `3 sub-lane` → `4 sub-lane`。
- **M2**（OQ1 候选 a）：[character_snapshot_extraction.md:102,104,139,177](../../extraction/persona_extraction/prompts/character_snapshot_extraction.md) + [extraction_workflow.md:405](../../docs/architecture/extraction_workflow.md#L405) 5 处 "stage_delta 自由文本" 措辞改为"stage_delta 是 6-key 结构化对象，子字段内容是叙述性 text"。**不另起 6 subkey 枚举表**——schema 已通过 prompt 内 `{stage_snapshot_schema_inline}` 占位符自动 inline，再枚举一遍是重复，**判断为过度工程跳过**。
- **M3**（OQ3 候选 a）：[ai_context/conventions.md:51](../../ai_context/conventions.md#L51) + [ai_context/decisions.md:393](../../ai_context/decisions.md#L393) 两处删 `build_factions_keyfigures_prompt`，措辞回归 `build_baseline_prompt` 单调用现状。
- **M4**：[ai_context/requirements.md §9](../../ai_context/requirements.md#L101-L109) 一段重写为 Phase 0/1/1.5/2/3/4 形态，删 "world overview" 旧术语。
- **M5**（OQ1 候选 a 联动）：[ai_context/decisions.md:56-57](../../ai_context/decisions.md#L56-L57) 11d 改为结构化对象描述；[ai_context/decisions.md:80](../../ai_context/decisions.md#L80) 11f 同步措辞 + forward-ref。
- **M6**（OQ2 候选 a）：[ai_context/conventions.md:114](../../ai_context/conventions.md#L114) Exempt 行加 `docs/todo_list_archived.md`。
- **M7**：[file_regen.py:120,152](../../extraction/repair/fixers/file_regen.py) 两处 `3-sub-lane` → `4-sub-lane`。
- **M8**：[cli.py:128](../../extraction/persona_extraction/cli.py#L128) help 加一句 "Phase 4 standalone treats 0/omit both as all chapters."
- **L1**：[foundation.schema.json:5](../../schemas/world/foundation.schema.json#L5) + [schemas/README.md:9](../../schemas/README.md#L9) 删 "原 ... 已删除" provenance 句。
- **L2**：[schema_reference.md:13](../../docs/architecture/schema_reference.md#L13) wording 收紧——Phase 1 入 git 部分明确为 stage_plan + candidate_characters 两件。

**跳过**（6 条 — 按 user "留 todo / 跳过" 全部不做本轮）：
- **M9**（建议留 todo）：reconcile_with_disk `.partial_prev/` 平行 sweep 仅磁盘 GC，不影响正确性 → 跳过。
- **L3**（建议跳过）：recovery sweep 行为正确，纯文档锦上添花 → 跳过。
- **L4**（建议留 todo）：forward-compat trap，触发点是 v3 schema_version 出现之后 → 跳过。
- **L5**（建议留 todo）：commit_stage 多失败模式坍缩，运维 QoL，需改函数签名 → 跳过。
- **L6**（建议留 todo）：relationship_core/manifest.json 模板风格，schema 已 pass → 跳过。

## 计划动作清单

### Code (H1 — 5 站点 cancel_futures per-site 修)
1. [extraction/persona_extraction/orchestrator.py:1654-1660](../../extraction/persona_extraction/orchestrator.py#L1654-L1660) Phase 0 chunk pool → `except RateLimitHardStop:` 段先加 `executor.shutdown(wait=False, cancel_futures=True)` 再 raise。
2. [extraction/persona_extraction/orchestrator.py:2059-2072](../../extraction/persona_extraction/orchestrator.py#L2059-L2072) Phase 1 lane pool → 给 `fut.result()` 包 `try/except RateLimitHardStop: pool.shutdown(wait=False, cancel_futures=True); raise`。
3. [extraction/persona_extraction/orchestrator.py:2913-2939](../../extraction/persona_extraction/orchestrator.py#L2913-L2939) Phase 3 outer lane pool → 给 `future.result()` 包同上 try/except。
4. [extraction/persona_extraction/orchestrator.py:3143-3150](../../extraction/persona_extraction/orchestrator.py#L3143-L3150) repair per-file pool → 现 `except RateLimitHardStop:` 段加 `pool.shutdown(wait=False, cancel_futures=True)` 再 raise。
5. [extraction/persona_extraction/phases/scene_archive.py:970-975](../../extraction/persona_extraction/phases/scene_archive.py#L970-L975) Phase 4 chapter pool → 现 `except RateLimitHardStop:` 段加 `executor.shutdown(wait=False, cancel_futures=True)` 再 raise。

### Code (M7 file_regen 注释)
6. [extraction/repair/fixers/file_regen.py:120,152](../../extraction/repair/fixers/file_regen.py) `3-sub-lane` → `4-sub-lane`。

### Code (M8 cli help)
7. [extraction/persona_extraction/cli.py:128-129](../../extraction/persona_extraction/cli.py#L128-L129) help 文字补一句 phase 4 standalone 例外。

### Schema (L1 description + L2 wording)
8. [schemas/world/foundation.schema.json:5](../../schemas/world/foundation.schema.json#L5) description 删 "原 schemas/analysis/world_overview.schema.json 已删除，内容合并入本 schema；" 一段。
9. [schemas/README.md:9](../../schemas/README.md#L9) `analysis/` row "典型成员" 删 provenance 注脚。
10. [schemas/README.md:12](../../schemas/README.md#L12) `3 sub-lane` → `4 sub-lane (char_expression / char_decision / char_internal / char_social)`。
11. [docs/architecture/schema_reference.md:13](../../docs/architecture/schema_reference.md#L13) "Phase 1 三件套入 git" → 明确为 `stage_plan + candidate_characters` 两件 + foundation 在 world/ 域。

### Prompt / Docs (M2 stage_delta 措辞)
12. [extraction/persona_extraction/prompts/character_snapshot_extraction.md:102,104,139,177](../../extraction/persona_extraction/prompts/character_snapshot_extraction.md) 4 处 "stage_delta 自由文本" / "自由文本" 改为结构化对象 + 叙述性子字段措辞。
13. [docs/architecture/extraction_workflow.md:405](../../docs/architecture/extraction_workflow.md#L405) 同上一句改写。

### Docs (M4 §9 重写)
14. [ai_context/requirements.md:101-109](../../ai_context/requirements.md#L101-L109) §9 重写为 Phase 0/1/1.5/2/3/4 形态。

### ai_context (M3 + M5 + M6 + Cross-File Alignment)
15. [ai_context/conventions.md:51](../../ai_context/conventions.md#L51) Cross-File Alignment row → 删 `+ build_factions_keyfigures_prompt`。
16. [ai_context/conventions.md:114](../../ai_context/conventions.md#L114) Exempt 行加 `docs/todo_list_archived.md`。
17. [ai_context/decisions.md:56-57](../../ai_context/decisions.md#L56-L57) #11d 措辞改为结构化对象。
18. [ai_context/decisions.md:80](../../ai_context/decisions.md#L80) #11f "free-text per #11d" 同步改写 + forward-ref to #55。
19. [ai_context/decisions.md:393](../../ai_context/decisions.md#L393) #54 Plumbing 删 `build_factions_keyfigures_prompt`。

## 验证标准

- [ ] H1：`python -c "import ast; ast.parse(open('extraction/persona_extraction/orchestrator.py').read()); ast.parse(open('extraction/persona_extraction/phases/scene_archive.py').read())"` 通过；5 站点各 `grep -n "executor.shutdown(wait=False, cancel_futures=True)\|pool.shutdown(wait=False, cancel_futures=True)"` 命中含 sub-executor / recovery sweep 在内共 ≥ 7 次（5 新 + 2 原）。
- [ ] H1：5 站点都在 `except RateLimitHardStop` 段先 shutdown 再 raise（grep 验证 except 段附近 cancel_futures）。
- [ ] M1 / M7：`grep -rn "3 sub-lane\|3-sub-lane" schemas/ extraction/ docs/ ai_context/` 残留 = 0（除 logs/ 历史归档）。
- [ ] M2 / M5：`grep -rn "stage_delta 自由文本\|stage_delta.*free-text\|stage_delta.*stays free" extraction/persona_extraction/prompts/ docs/ ai_context/` 命中 = 0。
- [ ] M3：`grep -rn "build_factions_keyfigures" ai_context/` 命中 = 0；conventions.md 关键行 grep `build_baseline_prompt` 仍有命中。
- [ ] M4：`grep -n "world overview\|world_overview" ai_context/requirements.md` 命中 = 0。
- [ ] M6：`grep -n "docs/todo_list_archived" ai_context/conventions.md` 命中 ≥ 1（Exempt 行）。
- [ ] M8：`grep -n "Phase 4 standalone" extraction/persona_extraction/cli.py` 命中 ≥ 1。
- [ ] L1：`grep -n "已删除" schemas/world/foundation.schema.json schemas/README.md` 命中 = 0。
- [ ] L2：`grep -n "Phase 1 三件套入 git" docs/architecture/schema_reference.md` 命中 = 0。
- [ ] Import smoke：`python -c "from extraction.persona_extraction import orchestrator; from extraction.persona_extraction.phases import scene_archive; from extraction.repair.fixers import file_regen; from extraction.persona_extraction import cli"` 全过。
- [ ] JSON schema valid：`python -c "import json, jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('schemas/world/foundation.schema.json')))"` 通过。

## 执行偏差

### 偏差 D1：M7 同根残留扩到 file_regen.py 模块 docstring + coordinator.py kwarg docstring

**PRE 计划**：M7 仅列 [file_regen.py:120,152](../../extraction/repair/fixers/file_regen.py) 两行 inline comment 改 `3-sub-lane` → `4-sub-lane`。

**实际发现**：执行后 grep `3-sub-lane` 残留 4 处——除 PRE 列出的 2 处，还有 [file_regen.py:10](../../extraction/repair/fixers/file_regen.py#L10)（模块顶 docstring）+ [coordinator.py:187](../../extraction/repair/coordinator.py#L187)（`sub_lane_regen` kwarg docstring）描述当前行为为 `3-sub-lane`，与 PRE 列的 inline comment 同根（都是 #55 收尾遗漏）。

**实际动作**：两处 docstring 一并改为 `4-sub-lane`。`coordinator.py:188` 同时把 `legacy single-LLM full-file regen` 的 "legacy" 前缀去掉（顺手对齐 `conventions.md` §Generic Placeholders 第 4 条"no history narration"——不引入新 finding，是 M7 同根 wording）。其他 `3 sub-lane` 残留（[config.toml:34,102](../../extraction/config.toml) / [core/config.py:41](../../extraction/persona_extraction/core/config.py#L41) / [orchestrator.py:2883](../../extraction/persona_extraction/orchestrator.py#L2883) / [extraction_workflow.md:268,356](../../docs/architecture/extraction_workflow.md) / [decisions.md:434,497](../../ai_context/decisions.md) / [requirements.md:1018](../../docs/requirements.md#L1018)）是"原 3 sub-lane 时代 → 现 4 sub-lane"的并发 cap 调参 rationale 比较，属于决策日志 / 配置注释的鉴权 provenance，不是 current-state 错误描述——**留原样不动**，避免本轮 scope 外扩；scope leak 风险点已确认。

### 偏差 D2：M3 ai_context residue 收紧到 grep=0

**PRE 计划**：[ai_context/decisions.md:393 (#54 Plumbing)](../../ai_context/decisions.md#L393) 删 `build_factions_keyfigures_prompt` 一处提及。

**实际动作**：替换 #54 Plumbing 文本时初稿留了"不再拆独立 `build_factions_keyfigures_prompt`"否定式表述（仍 grep 命中）。考虑到 PRE 验证标准 `grep -rn build_factions_keyfigures ai_context/ 命中 = 0` 是 grep=0 的硬契约，把后半句改成纯 current-state 描述（"phase 2 key_figures 替换段整合到 build_baseline_prompt 单次 LLM call 内"），grep 真 = 0；决策 #54 上半节的"修订段 2026-05-11 落地形态"括号保留语义信号。

## 已落地变更

### Code (5 cancel_futures site + 2 docstring + 1 cli help)
- [extraction/persona_extraction/orchestrator.py:1659-1664](../../extraction/persona_extraction/orchestrator.py#L1659-L1664)（Phase 0 chunk pool）`except RateLimitHardStop` 段先 `executor.shutdown(wait=False, cancel_futures=True)` 再 raise + 注释引 decision #55 R2 pattern。
- [extraction/persona_extraction/orchestrator.py:2071-2077](../../extraction/persona_extraction/orchestrator.py#L2071-L2077)（Phase 1 lane pool）给 `fut.result()` 包 `try/except RateLimitHardStop: pool.shutdown(wait=False, cancel_futures=True); raise`。
- [extraction/persona_extraction/orchestrator.py:2940-2947](../../extraction/persona_extraction/orchestrator.py#L2940-L2947)（Phase 3 outer lane pool）给 `future.result()` 包同上 try/except。
- [extraction/persona_extraction/orchestrator.py:3166-3172](../../extraction/persona_extraction/orchestrator.py#L3166-L3172)（repair per-file pool）现 `except RateLimitHardStop` 段加 `pool.shutdown(wait=False, cancel_futures=True)` 再 raise。
- [extraction/persona_extraction/phases/scene_archive.py:972-977](../../extraction/persona_extraction/phases/scene_archive.py#L972-L977)（Phase 4 chapter pool）现 `except RateLimitHardStop` 段加 `executor.shutdown(wait=False, cancel_futures=True)` 再 raise。
- [extraction/repair/fixers/file_regen.py:10,120,152](../../extraction/repair/fixers/file_regen.py) 3 处 `3-sub-lane` → `4-sub-lane`（PRE 列 2 处 + 偏差 D1 模块 docstring 1 处）。
- [extraction/repair/coordinator.py:187-188](../../extraction/repair/coordinator.py#L187-L188) `sub_lane_regen` kwarg docstring `3-sub-lane` → `4-sub-lane` + 删 "legacy" 前缀（偏差 D1）。
- [extraction/persona_extraction/cli.py:128-130](../../extraction/persona_extraction/cli.py#L128-L130) `--end-stage` help 文字补 "Phase 4 standalone treats 0 / omit both as all chapters."

### Schema (1 description trim)
- [schemas/world/foundation.schema.json:5](../../schemas/world/foundation.schema.json#L5) description 删 "原 schemas/analysis/world_overview.schema.json 已删除，内容合并入本 schema" 一段；改写为 current-state 描述（"`build_baseline_prompt` 单次 LLM call 内补齐 key_figures"），field/bound 一字不动。

### Schema docs (2 row wording)
- [schemas/README.md:9](../../schemas/README.md#L9) `analysis/` row 删 "原 world_overview 已删除" provenance 注脚。
- [schemas/README.md:12](../../schemas/README.md#L12) `character/` row `3 sub-lane partial` → `4 sub-lane partial` + 枚举四个 sub-lane 名（`char_expression` / `char_decision` / `char_internal` / `char_social`）。

### Prompt (4 处 stage_delta 措辞)
- [extraction/persona_extraction/prompts/character_snapshot_extraction.md:102,104,139,177](../../extraction/persona_extraction/prompts/character_snapshot_extraction.md) 4 处 "stage_delta 自由文本" / "自由文本" → "stage_delta 对应 sub-field 的叙述性 text"；line 139 额外补一句"顶层是 6-key 结构化对象"枚举 6 个 subkey 名，schema 真值仍由 inline schema 占位符承担。

### Architecture docs
- [docs/architecture/extraction_workflow.md:405](../../docs/architecture/extraction_workflow.md#L405) `stage_delta` 行同步措辞改为结构化对象 + 叙述性 sub-field。
- [docs/architecture/schema_reference.md:13](../../docs/architecture/schema_reference.md#L13) `schemas/analysis/` row 明确为 `stage_plan + candidate_characters` 两件 + foundation 在 `schemas/world/`。

### ai_context durable
- [ai_context/requirements.md:101-115](../../ai_context/requirements.md#L101-L115) §9 一段重写为 Phase 0 / 1 (3 lane mono / 2 lane light_novel + 程序 stage_plan) / 1.5 / 2 / 3 / 4 形态，删 "world overview" 旧术语。
- [ai_context/conventions.md:51](../../ai_context/conventions.md#L51) Cross-File Alignment foundation row 删 `+ build_factions_keyfigures_prompt`，改写为 `build_baseline_prompt` 五件合一 current-state 描述。
- [ai_context/conventions.md:114-115](../../ai_context/conventions.md#L114-L115) Exempt 行加 `docs/todo_list_archived.md`。
- [ai_context/decisions.md:56-61](../../ai_context/decisions.md#L56-L61) #11d "stage_delta stays free-text" → "顶层 6-key structured object + 子字段叙述性 text" 措辞 + ref to #55。
- [ai_context/decisions.md:81-83](../../ai_context/decisions.md#L81-L83) #11f "stays free-text (per #11d)" 同步 + ref to #55。
- [ai_context/decisions.md:396](../../ai_context/decisions.md#L396) #54 Plumbing `prompt_builder.py` 段删 `build_factions_keyfigures_prompt`，改写为 `build_baseline_prompt` 五件合一 current-state（偏差 D2 收紧后 grep=0）。

## 与计划的差异

- **D1**：M7 实际改动从 PRE 列的 2 处扩到 4 处（模块 docstring + kwarg docstring 同根）+ coordinator.py:188 "legacy" 前缀顺手去（同根）。其他 `3 sub-lane` 残留是 cap 调参 rationale provenance，故意不动。
- **D2**：#54 Plumbing 改写文案的后半句二次收紧（grep=0 硬契约）。
- 其余动作与 PRE 计划清单 1:1 一致。

## 验证结果

- [x] H1：`python -c "import ast; ..."` AST OK；`grep -n "cancel_futures=True" extraction/persona_extraction/orchestrator.py extraction/persona_extraction/phases/scene_archive.py` 命中 7 行（reference 2 行 + 本次新增 5 行——orchestrator.py 行 736 / 1011 / 1663 / 2077 / 2947 / 3172 + scene_archive.py:977；scene_archive 共 1 行；orchestrator 共 6 行；总 7）。
- [x] H1：5 站点 `except RateLimitHardStop` 段附近确认 shutdown 调用——visual diff inspection 已确认每段 raise 前一行是 shutdown(cancel_futures=True)。
- [x] M1 / M7：`grep -rn "3 sub-lane\|3-sub-lane" extraction/repair/` 命中 = 0（PRE + 偏差 D1 同根残留全清）；canonical 层（schemas/ extraction/persona_extraction/prompts/ docs/architecture/）current-state 描述命中 = 0；其余 `3 sub-lane` 残留是 cap 调参 provenance（config.toml / core/config.py / orchestrator.py inline / extraction_workflow.md / decisions.md / requirements.md），故意保留。
- [x] M2 / M5：`grep -rn "stage_delta 自由文本\|stage_delta.*free-text\|stage_delta.*stays free" extraction/persona_extraction/prompts/ docs/ ai_context/` 命中 = 0。
- [x] M3：`grep -rn "build_factions_keyfigures" ai_context/ schemas/ extraction/ docs/` 命中 = 0（偏差 D2 收紧后）。
- [x] M4：`grep -in "world overview\|world_overview" ai_context/requirements.md docs/requirements.md ai_context/architecture.md ai_context/decisions.md` 命中 = 0。
- [x] M6：`grep -n "docs/todo_list_archived" ai_context/conventions.md` 命中 2（line 65 + line 115 Exempt 行）。
- [x] M8：`grep -n "Phase 4 standalone" extraction/persona_extraction/cli.py` 命中 line 129 help 字段 + 既有 229 段头注释，共 2。
- [x] L1：`grep -n "已删除" schemas/world/foundation.schema.json schemas/README.md` 命中 = 0。
- [x] L2：`grep -n "Phase 1 三件套入 git" docs/architecture/schema_reference.md` 命中 = 0。
- [x] Import smoke：`python -c "from extraction.persona_extraction import orchestrator, cli; from extraction.persona_extraction.phases import scene_archive; from extraction.repair.fixers import file_regen; from extraction.repair import coordinator"` 全过。
- [x] JSON schema valid：`python -c "import json, jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('schemas/world/foundation.schema.json')))"` 通过。

## Completed

- **Status**: DONE
- **Finished**: 2026-05-14 01:05:58 EDT

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：19 / 19 项计划动作全部落实 + 12 / 12 项验证标准全过；偏差 D1 / D2 已在 POST 段记录
- Missed updates: 2 条（M2 同根残留扩展——PRE 漏盖 docs/architecture/extraction_workflow.md:301 + docs/requirements.md:1081）

### 轨 2 — 影响扩散
- Findings: High=0 / Medium=2 / Low=1
- Open Questions: 1 条（decision log #27i provenance 是否同步收紧）

## 复查时状态
- **Reviewed**: 2026-05-14 09:55:22 EDT
- **Status**: REVIEWED-PARTIAL
  - 轨 1 落实率 100% + 验证 100%；轨 2 有 2 条 M（M2 同根扩散），无 H
- **Conversation ref**: 同会话内 /post-check 输出
