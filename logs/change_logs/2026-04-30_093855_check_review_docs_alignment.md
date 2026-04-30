# check_review_docs_alignment

- **Started**: 2026-04-30 09:38:55 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

`/check-review claude` 复核了 `logs/review_reports/2026-04-30_052217_opus-4-7_full-review-findings.md`（Claude Opus 4.7 的 /full-review 报告）。复核结论：

- H1 真实（works/README.md 仍把 4-piece deprecated baseline 当现行结构）
- M1 真实（`schemas/_shared/` 被三处文档引用但磁盘上不存在）
- M2 真实（`schemas/work/` 表标 6 实测 5；`schemas/character/` 表标 6 实测 7—— targets_cap 按既有口径不计入独立 schema）
- L1 真实（current_status.md §Rules In Effect 缺 main vs extraction/library 分支语境限定）
- L2 误判（仓库根 README.md 实存且内容合理，**驳回**）

报告外补充：repo-wide grep `voice_rules\|behavior_rules\|boundaries\.json\|failure_modes\.json` 仅 `works/README.md` 一处 stale 引用，其余命中点均为合法的"反向叙述 / 弃用声明 / 迁移脚本目标"语境，修完 H1 即彻底切断 stale 血流。

## 结论与决策

用户拍板：

1. **M1**：`_shared/` 视为已废弃目录——**全部移除**相关说明（不走"按需创建"占位路线，直接从 schemas/README.md 表格 + 解释段、conventions.md、decisions.md 删除）
2. **M2**：character 计数取 7（按 schemas/README.md 既有"$ref 片段不计入独立 schema"口径，与 schema_reference.md 既有 character 节专节数严格匹配）
3. **H1**：works/README.md 改 47-50 目录树 + 130-154 五段子文件描述；含独立 `target_baseline.json` 段（character-level 恒定文件）
4. **L1**：在 current_status.md §Rules In Effect 加一行 main vs extraction/library 限定
5. **驳回 L2**；其余 deferred / Residual Risks 项不在本轮处理

## 计划动作清单

按两个逻辑 commit 提交：

**Commit 1（works/README.md 跟上 4-piece deprecation）**

- file: `works/README.md` → 47-50 目录树删 4 件套；canon/ 下补 `target_baseline.json`；130-154 五段子文件描述重写为：
  - 保留 `identity.json` 段（含 core_wounds / key_relationships）
  - 新增 `target_baseline.json` 段（character-level 恒定，targets / tier / relationship_type / description）
  - 增强 `stage_snapshots/{stage_id}.json` 段：voice_state / behavior_state / boundary_state / failure_modes 内联子结构 + 4 子类
  - § 设计规则末尾补一行说明 voice/behavior/boundary/failure_modes 内联结构与 character-level 恒定文件清单
  - bound 数字不抄到 README（遵守 conventions §27b）

**Commit 2（schemas 文档 + ai_context 跟上 _shared/ 移除 + 计数修正 + 分支语境限定）**

- file: `schemas/README.md` → 删表格中 `_shared/` 行；删 line 18-21 "`_shared/` 与 `shared/` 的区分" 解释段；改 line 25-27 "新增 schema 文件归类" 列表中"跨域片段 → 放 `_shared/`"措辞为"跨域片段 → 放对应共享位置（语义上 cross-domain，但当前无此类需求）"或直接精简
- file: `ai_context/conventions.md:82` → 删除 "cross-domain shares live under `schemas/_shared/`" 短语；保留"single-domain shares live in that domain's directory"措辞
- file: `ai_context/decisions.md:169` → 同步删除 `_shared/` 引用
- file: `docs/architecture/schema_reference.md:14, :16` → `work/` 6→5；`character/` 6→7
- file: `ai_context/current_status.md:64` 之前 → 插入一行 main vs extraction/library 分支限定
- file: `docs/todo_list.md` → 登记本次 review 复核与落地（如已有合适分段则增条目，否则按本次实际改动写一行；同步刷新 Index 段）

## 验证标准

- [ ] `grep -rn "voice_rules\|behavior_rules\|boundaries\.json\|failure_modes\.json" works/README.md` 命中数 = 0
- [ ] `ls schemas/_shared/` 仍报 "No such file or directory"，且 `grep -rn "_shared/" schemas/ ai_context/ docs/` 命中数 = 0（除 `logs/review_reports/` / `logs/change_logs/` 历史档案外）
- [ ] `docs/architecture/schema_reference.md` 头表 `work/` = 5、`character/` = 7
- [ ] `docs/architecture/schema_reference.md` 头表"文件数"列与 `ls schemas/{analysis,work,world,character,user,runtime,shared}/` 实际计数（按 schemas/README.md `$ref 片段不计独立 schema` 口径）一致
- [ ] `ai_context/current_status.md` §Rules In Effect 含一行 main vs extraction/library 分支语境限定
- [ ] `python3 -c "import json; [json.load(open(f)) for f in __import__('glob').glob('schemas/**/*.schema.json', recursive=True)]"` 通过（确保未误碰 schema 文件）
- [ ] `docs/todo_list.md` Index 段刷新后与正文条目顺序、标题一致

## 执行偏差

- Step 7 review 时发现 `docs/todo_list.md:359` 在 In Progress 任务 `T-PHASE2-TARGET-BASELINE` 的"改动清单"中仍把 `targets_cap.schema.json` 写为 `schemas/_shared/`（实际实现已落到 `schemas/character/`）。本属 M1"_shared 全部移除"决议覆盖范围（虽属 In Progress 任务历史叙述，但仍出现在主 todo_list 而非 archived，会让读者误以为 `_shared/` 是当前合法路径），同步修订一行字面引用。
- 重写 `works/README.md` stage_snapshots 段时，把"对其他角色的关系状态与信任度"末尾追加"顶层 `relationships`；keys 与 `target_baseline.targets[].target_character_id` 双向相等"的限定，使其与 ai_context/decisions.md §13 的双向相等硬约束语义一致——属 H1 直接连带，未超范围。

<!-- POST 阶段填写 -->

## 已落地变更

- `works/README.md`（H1 主体，~30 行净增）
  - 47-50 目录树：删 `voice_rules.json` / `behavior_rules.json` / `boundaries.json` / `failure_modes.json`；canon/ 下补 `target_baseline.json`
  - 130-154 五段子文件描述：删 4 件套 5 段；新增 `target_baseline.json` 段（targets / tier / relationship_type 14 候选 / Phase 3 双向相等约束）
  - stage_snapshots 段：title 行改为"自包含"+"voice / behavior / boundary / failure_modes 全部内联"措辞；内容列表把"相对基线的 override"两行替换为 `voice_state` / `behavior_state` / `boundary_state` / `failure_modes` 4 行内联子结构描述（4 子类 `common_failures` / `tone_traps` / `relationship_traps` / `knowledge_leaks`）；末尾"对其他角色的关系状态与信任度"行加双向相等限定
  - § 设计规则：补一行说明 voice / behavior / boundary / failure_modes 内联结构 + character-level 恒定文件清单 = identity + target_baseline
- `schemas/README.md`（M1）
  - 表格删 `_shared/` 行
  - 删 line 18-21 "`_shared/` 与 `shared/` 的区分"整段
  - 重写 `shared/` 用法说明 + schema_loader $ref 注解为单段
  - "新增 schema 文件归类" 列表删除 `_shared/` 项；保留"片段 → 放该域目录"说法
- `ai_context/conventions.md:82`（M1） — `Bounds only in schema` 段删 `cross-domain shares live under schemas/_shared/` 短语，改为"placed in the directory of the domain that uses it"
- `ai_context/decisions.md:169`（M1） — §27b 同步删 `_shared/` 引用
- `schemas/character/targets_cap.schema.json:5`（M1） — description 删反向叙述"故置于 schemas/character/ 而非 schemas/_shared/"
- `automation/persona_extraction/schema_loader.py:1-9`（M1） — module docstring 删 `cross-domain sharing the fragment lives in schemas/_shared/`，改为"fragment lives in the directory of the domain that uses it"
- `docs/architecture/schema_reference.md:14, 16`（M2） — `work/` 6→5；`character/` 6→7（按"$ref 片段不计独立 schema"口径），character 行"典型成员"列附注 `(含 target_baseline + targets_cap 域内 $ref 片段)`
- `ai_context/current_status.md:64`（L1） — §Rules In Effect 在 `works/*` 跟踪规则前插一行限定 main = framework-only / 跟踪规则仅适用于 `extraction/{work_id}` 与 `library` 分支
- `docs/todo_list.md:359`（执行偏差补救） — `schemas/_shared/targets_cap.schema.json` → `schemas/character/targets_cap.schema.json`

## 与计划的差异

新增了 `docs/todo_list.md:359` 字面修订（PRE log 计划清单未列；属 M1"_shared 全部移除"决议直接覆盖范围内的字面 cleanup，已在 §执行偏差 段记录）。其余文件改动与计划清单一致。

## 验证结果

- [x] `grep -n "voice_rules\|behavior_rules\|boundaries\.json\|failure_modes\.json" works/README.md` — 0 命中 ✓
- [x] `ls schemas/_shared/` 仍报 "No such file or directory"；`grep -rn "_shared\b\|_shared/" schemas/ ai_context/ docs/ automation/ simulation/ prompts/ works/ README.md` — 命中 0（已剔除 logs/ 与 todo_list_archived.md 历史档案）✓
- [x] schema_reference.md 头表 `work/` = 5、`character/` = 7 ✓
- [x] 头表"文件数"列与磁盘一致：`analysis/`=5 / `work/`=5 / `world/`=6 / `character/`=7（"$ref 片段不计独立 schema"口径，注明 `target_baseline` + `targets_cap`）/ `user/`=5 / `runtime/`=5 / `shared/`=1 ✓
- [x] `ai_context/current_status.md` §Rules In Effect 含一行 main vs extraction/library 分支语境限定（line 64）✓
- [x] `python3 -c "import json; ..."` 全部 35 个 `schemas/**/*.schema.json` 解析通过；`automation.persona_extraction.schema_loader` import 干净 ✓
- [x] `docs/todo_list.md` Index 段无需刷新（本次仅修订 In Progress 任务体内一行字面引用，未改条目结构 / 标题 / ID / 状态）✓

## Completed

- **Status**: DONE
- **Finished**: 2026-04-30 09:49:47 EDT
