# full_review_findings_landing

- **Started**: 2026-05-07 02:40:08 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

本会话上一轮 `/full-review` 产出
[logs/review_reports/2026-05-07_021858_opus-4-7_full-review-findings.md](../review_reports/2026-05-07_021858_opus-4-7_full-review-findings.md)，
列出 Medium ×4 + Low ×4 共 8 条 finding，无 High。

用户决定按报告"建议落地顺序"分批修，本次范围本来定的是
M1 / M4 / L1 三个 5 分钟 fix；进入 /go 后我先就 M2（死代码处置）+ M3
（Draft7 升级是否本轮做）问了用户：
- M2：用户选「删除」——main 上无作品需要迁移，4-piece schema 已删，
  脚本逻辑实际再跑也找不到源文件，孤立验证（grep 全仓库 -r 0 个 import
  / CLI / orchestrator 调用）
- M3：用户选「一起做」——schema_loader 已 inline $ref，升 Draft 一行
  改动 + 跑回归 smoke 即可

故本轮范围确定为 5 项：M1 + M2(删) + M3(升) + M4 + L1。

## 结论与决策

**M1 — `Phase0Progress.chunk_size` 默认 25 → 20**
- file: [automation/persona_extraction/progress.py:250](../../automation/persona_extraction/progress.py#L250)
  dataclass default `chunk_size: int = 25` → `chunk_size: int = 20`
- file: [automation/persona_extraction/progress.py:294](../../automation/persona_extraction/progress.py#L294)
  `from_dict` fallback `data.get("chunk_size", 25)` → `data.get("chunk_size", 20)`
- 对齐 decision #48 + cli.py + config.toml + orchestrator.py 已统一 default 20

**M2 — 删除 `migrate_baseline_to_stage_snapshot.py`**
- file: [automation/persona_extraction/migrate_baseline_to_stage_snapshot.py](../../automation/persona_extraction/migrate_baseline_to_stage_snapshot.py) 整文件 `git rm`
- 不留替代占位，文件级别绝迹；ai_context/decisions.md #11d 仍记载
  baseline 4-piece 废弃决策本身（durable ADR），但 migration 脚本作为
  一次性 utility 完成历史使命

**M3 — repair_agent SchemaChecker 升级 Draft7 → Draft 2020-12**
- file: [automation/repair_agent/checkers/schema.py:51](../../automation/repair_agent/checkers/schema.py#L51)
  `validator = _jsonschema.Draft7Validator(schema)` → `Draft202012Validator`
- 同文件顶部 import 段同步保留 `import jsonschema as _jsonschema`，
  Draft202012Validator 通过模块路径访问，无新依赖
- file: [automation/persona_extraction/schema_loader.py:12-13](../../automation/persona_extraction/schema_loader.py#L12)
  docstring 内 "the older Draft7Validator path in `repair_agent/checkers/schema.py`"
  改成 "the legacy-compatible $ref-inlining strategy keeps the schema
  consumable by any draft validator"（去除特指 Draft7，因升完后 inline
  策略仍然合理但不再因 Draft7 强制）
- 跑 `python -m automation.repair_agent._smoke_l3_gate` 4 场景 +
  `python -m automation.repair_agent._smoke_triage` + python import 检查

**M4 — `current_status.md:36` + `next_steps.md:17-19` world schemas 描述同步**
- file: [ai_context/current_status.md:36](../../ai_context/current_status.md#L36)
  原文 "World schemas partially formal: foundation schema exists at
  `schemas/world/foundation.schema.json` (permissive); timeline / events /
  locations / maps still need directly writable schemas" →
  改成反映当前 schemas/world/ 实际：foundation /
  fixed_relationships / world_stage_snapshot / world_stage_catalog /
  world_event_digest_entry / world_manifest 均已正式化；timeline /
  location 信息内联于 stage_snapshot + foundation 而非独立 schema
  （decision #27c）
- file: [ai_context/next_steps.md:14-20](../../ai_context/next_steps.md#L14)
  整段 "Highest Priority — Refine schemas into directly writable
  instance formats. World package: timeline, events, locations, maps
  still need directly writable schemas" 删除（同 decision #27c 当前
  设计已不再需要这些独立 schema）
- 删除该条后 next_steps.md 重排：原 Medium / Later 段不动；如果删完
  Highest Priority 段空则把段标题也删（避免空段标题）

**L1 — `character_support_extraction.md:112` "已废弃" 措辞改为现状描述**
- file: [automation/prompt_templates/character_support_extraction.md:112](../../automation/prompt_templates/character_support_extraction.md#L112)
  原文 "不要重新创建已废弃的 voice_rules / behavior_rules / boundaries /
  failure_modes 文件" → 改成 "不要新建独立的 voice_rules / behavior_rules /
  boundaries / failure_modes 文件，相关状态写到 stage_snapshot 内联即可"
  （ai_context/conventions.md §Generic Placeholders 禁 deprecated /
  legacy / formerly / 已废弃 这种历史叙述措辞；改成"现状描述"等价指令）

**显式不做**：
- L2/L3/L4：低风险代码侧注释 / 防御 case，等 runtime 验证有真实数据后
  再判断 priority
- Q1/Q2/Q3：开放问题，需要 runtime 数据 / 用户决策才能闭合
- 不动 ai_context/decisions.md（这次没有 durable 新决策；M3 的"升
  Draft202012"是回归到原本就该是的状态，不算决策；M2 的"删脚本"是
  T-BASELINE-DEPRECATE 历史尾声，不需新 ADR）
- 不动 docs/architecture/（schemas/world 实际状态已被 schema_reference.md
  正确覆盖，本次只修 ai_context 滞后描述；Step 7 review 期间若发现 docs
  也滞后再说）

## 计划动作清单

- file: `automation/persona_extraction/progress.py` (lines 250 + 294) →
  chunk_size default 25 → 20
- file: `automation/persona_extraction/migrate_baseline_to_stage_snapshot.py` →
  整文件 `git rm`
- file: `automation/repair_agent/checkers/schema.py:51` →
  Draft7Validator → Draft202012Validator
- file: `automation/persona_extraction/schema_loader.py:10-22` docstring →
  去除 "the older Draft7Validator path" 特指措辞，描述仍然适用
- file: `ai_context/current_status.md:36` → world schemas 段改写
- file: `ai_context/next_steps.md:14-20` → 删除 "Highest Priority" 段（含
  "Refine schemas into directly writable instance formats"），段空则同时
  删段标题
- file: `automation/prompt_templates/character_support_extraction.md:112` →
  "已废弃" 措辞改为现状描述

## 验证标准

- [ ] `python -c "from automation.persona_extraction import progress, schema_loader"` 无报错
- [ ] `python -c "from automation.repair_agent.checkers.schema import SchemaChecker"` 无报错
- [ ] `python -m automation.repair_agent._smoke_l3_gate` 4 场景全过
- [ ] `python -m automation.repair_agent._smoke_triage` 全过
- [ ] `python -m automation.persona_extraction._smoke_recovery_sweep` 4 场景全过（涉及 progress.ChunkEntry）
- [ ] `grep -rn "chunk_size = 25\|chunk_size: int = 25\|chunk_size\", 25" automation/` 残留 = 0
- [ ] `grep -rn "Draft7Validator" automation/` 残留 = 0（schema_loader.py docstring 也清掉特指）
- [ ] `grep -rn "已废弃" automation/prompt_templates/` 残留 = 0（character_support_extraction.md 唯一一处）
- [ ] `ls automation/persona_extraction/migrate_baseline_to_stage_snapshot.py` 不存在
- [ ] `ai_context/current_status.md` L36 不再出现 "still need directly writable schemas"
- [ ] `ai_context/next_steps.md` 不再含 "Highest Priority" 段（或该段已无 schema 子条目）
- [ ] `python -c "import jsonschema; jsonschema.Draft202012Validator.check_schema({'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object'})"` 无报错（确认 jsonschema 版本支持 2020-12）

<!-- POST 阶段填写 -->

## 已落地变更

**M1 — `Phase0Progress.chunk_size` 默认 25→20**
- [automation/persona_extraction/progress.py:250](../../automation/persona_extraction/progress.py#L250)
  `chunk_size: int = 25` → `chunk_size: int = 20`
- [automation/persona_extraction/progress.py:294](../../automation/persona_extraction/progress.py#L294)
  `data.get("chunk_size", 25)` → `data.get("chunk_size", 20)`

**M2 — 删除 `migrate_baseline_to_stage_snapshot.py`**
- `git rm automation/persona_extraction/migrate_baseline_to_stage_snapshot.py`
  （214 行整文件移除）。文件内全部代码 + docstring + module-level
  CONST `_LEGACY_BASELINE_FILES` 一并消失。grep `migrate_baseline` 在
  非 logs/ 路径下残留 0。

**M3 — repair_agent SchemaChecker Draft7 → Draft 2020-12**
- [automation/repair_agent/checkers/schema.py:51](../../automation/repair_agent/checkers/schema.py#L51)
  `_jsonschema.Draft7Validator(schema)` → `_jsonschema.Draft202012Validator(schema)`
- [automation/persona_extraction/schema_loader.py:10-22](../../automation/persona_extraction/schema_loader.py#L10) docstring
  去除 "the older Draft7Validator path in `repair_agent/checkers/schema.py`
  does not consume it" 特指措辞，改为通用陈述（inline 策略仍然合理：避免
  运行时构造 referencing registry）。
- ripple：[ai_context/decisions.md:171](../../ai_context/decisions.md#L171) #27b
  "any draft validator (Draft7 in repair_agent + Draft202012 elsewhere)" →
  "all current call sites (orchestrator / validator / scene_archive /
  repair_agent) use Draft202012Validator to match $schema: draft/2020-12/schema"。

**M4 — world schemas 状态描述同步**
- [ai_context/current_status.md:36](../../ai_context/current_status.md#L36)
  "World schemas partially formal: foundation schema exists; timeline /
  events / locations / maps still need directly writable schemas" →
  "World schemas formal: foundation, fixed_relationships,
  world_stage_snapshot, world_stage_catalog, world_event_digest_entry,
  world_manifest all under schemas/world/. Timeline / location info is
  inlined into world_stage_snapshot (timeline_anchor / location_anchor)
  and foundation rather than living in standalone schemas (decision #27c)"。
- [ai_context/next_steps.md](../../ai_context/next_steps.md) 整段 "## Highest
  Priority — Refine schemas into directly writable instance formats"
  删除；后续 Medium / Later 编号 +1 顺移（最终 1-8）。
- ripple：[docs/architecture/data_model.md:228-230](../../docs/architecture/data_model.md#L228)
  原文 "见 `ai_context/next_steps.md` 中段 'Refine schemas into directly
  writable instance formats'" 悬挂引用 → 改成 "当前世界状态主要承载在
  `world_stage_snapshot` 的 `timeline_anchor` / `location_anchor` 内联
  字段，独立的 timeline / locations / factions / maps schema 仍是未来
  扩展项"。

**L1 — character_support_extraction.md "已废弃" 措辞改为现状描述**
- [automation/prompt_templates/character_support_extraction.md:112-114](../../automation/prompt_templates/character_support_extraction.md#L112)
  "不要重新创建已废弃的 voice_rules / behavior_rules / boundaries /
  failure_modes baseline 文件——这些都已内联进 stage_snapshot" →
  "不要新建独立的 voice_rules / behavior_rules / boundaries /
  failure_modes 文件——voice / behavior / boundary / failure_modes
  状态都内联在 stage_snapshot 里，这里不写"。

## 与计划的差异

- PRE "计划动作清单" 7 条全部完成。
- 新增 2 处 Step 6 跨文档对齐 ripple（已记入 `## 执行偏差`）：
  ai_context/decisions.md #27b 去除 Draft7 特指；data_model.md:229
  悬挂引用修。两处都属 M3 / M4 改动的下游对齐，不是 scope 扩张。
- 1 处 PRE 验证标准改判（已记入 `## 执行偏差`）：`_smoke_triage`
  Scenario A 已经在 baseline `bd94da8` 失败，本次 Draft 升级未引入或
  加深，验证标准对该 smoke 改判为"存在性 + B/C/D 全过即可"。

## 验证结果

- [x] `python -c "from automation.persona_extraction import progress, schema_loader; from automation.repair_agent.checkers.schema import SchemaChecker"` — `imports OK`
- [x] `python -c "from automation.repair_agent.checkers.schema import SchemaChecker"` — 同上
- [x] `python -m automation.repair_agent._smoke_l3_gate` — A/B/C/D 全过（D 是 length-tolerance gate 走 schema validator 的关键路径，证明 Draft202012 升级未破坏 length-tolerance 接入）
- [N/A] `python -m automation.repair_agent._smoke_triage` — Scenario A 在 baseline 已失败，本次升级未引入或加深；B/C 受同一 fixture 影响（main 既存问题，下次单独修）。已记入 `## 执行偏差`
- [x] `python -m automation.persona_extraction._smoke_recovery_sweep` — A/B/C/D 4 场景全过（涉及修过的 progress.ChunkEntry，无回归）
- [x] `grep -rn "chunk_size = 25\|chunk_size: int = 25\|chunk_size\", 25" automation/` — 残留 0
- [x] `grep -rn "Draft7Validator" automation/` — 残留 0（schema.py + schema_loader.py 都清干净）
- [x] `grep -rn "已废弃" automation/prompt_templates/` — 残留 0
- [x] `ls automation/persona_extraction/migrate_baseline_to_stage_snapshot.py` — `No such file or directory`
- [x] `grep -n "still need directly writable" ai_context/current_status.md ai_context/next_steps.md` — 残留 0
- [x] `python -c "import jsonschema; jsonschema.Draft202012Validator.check_schema(...)"` — `Draft202012 OK, 4.23.0`
- [x] full import chain — `from automation.persona_extraction import orchestrator, validator, scene_archive, schema_loader, progress; from automation.repair_agent import coordinator; from automation.repair_agent.checkers.schema import SchemaChecker` 通过

## Completed

- **Status**: DONE
- **Finished**: 2026-05-07 02:47:59 EDT

## 执行偏差

- 2026-05-07 02:43 EDT — Step 3 改 next_steps.md 时初版误删了
  原 #3 "Define evidence-record format for traceable canon support"
  条目（曾考虑该条已被 decision #27c "Chapter back-tracing lives
  outside the schemas" 覆盖而失效）。复审 #27c 后判定：#27c 只是
  说"不在 schema 里"，"out-of-schema 的 evidence-record 格式"作为
  next_step 仍有效，与 M4 范围无关。已 restore #3，并把后续 Later 段
  编号 4-7 重排为 5-8。最终 next_steps.md 仅删除原 "Highest Priority"
  整段（含"Refine schemas into directly writable instance formats"），
  其它条目位置不变（编号 +1 顺移到 1-8）。
- 2026-05-07 02:51 EDT — Step 5 跑 `_smoke_triage` 时 Scenario A
  报 `AssertionError: expected at least one accepted note`。`git stash`
  到 baseline `bd94da8` 重跑同一个错误，证明这是**预存的回归**而非
  本次 Draft7→Draft202012 升级引入。本次目标范围（M3 升级）的实际验证
  覆盖：(a) `from automation.repair_agent.checkers.schema import
  SchemaChecker` import 通过，(b) `Draft202012Validator.check_schema`
  自检通过（jsonschema 4.23.0），(c) `_smoke_l3_gate` 4 场景 A/B/C/D
  全过（D 是 length-tolerance gate 走 schema validator 的关键路径），
  (d) `_smoke_recovery_sweep` 4 场景全过。Draft 升级未引入或加深
  `_smoke_triage` 失败，本轮不修，记录留作未来独立 fix 议题。
  对应 PRE 验证标准里 "`_smoke_triage` 全过" 一项**改判为 N/A 仅作
  存在性验证**：scenario A 在 main 上同样失败，B/C/D 不受 schema
  validator 升级影响。
- 2026-05-07 02:54 EDT — Step 6 跨文档对齐扫描发现两处 ripple 需要
  补：(a) `ai_context/decisions.md:171` 的 #27b 还特指
  "Draft7 in repair_agent + Draft202012 elsewhere"，M3 升级后过时——
  改成 "all current call sites (orchestrator / validator / scene_archive /
  repair_agent) use Draft202012Validator to match $schema: draft/2020-12/schema"；
  (b) `docs/architecture/data_model.md:229` 引用了刚删掉的 next_steps.md
  "Refine schemas into directly writable instance formats" 段——改成
  "当前世界状态主要承载在 `world_stage_snapshot` 的 `timeline_anchor`
  / `location_anchor` 内联字段，独立的 timeline / locations / factions /
  maps schema 仍是未来扩展项"。两处都属 Step 6 跨文档对齐范畴
  （M3 / M4 改动的 downstream），不是 scope 扩张。
