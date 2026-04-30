# phase2_baseline_post_check_fixes

- **Started**: 2026-04-29 21:52:06 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

`/post-check` 复查 `2026-04-29_205423_phase2_target_baseline.md` 得到
REVIEWED-FAIL：identity → identity + target_baseline 的措辞同步在 8 处
文件遗漏，Cross-File Alignment 表点名的 `schemas/README.md` +
`docs/architecture/schema_reference.md` 完全没改。本轮 /go 目标：闭合
该 post-check 报告里列出的 Missed Updates，**不扩到** Residual Risks
里属于 BASELINE-DEPRECATE 范围的 validator.py 模块 docstring。

## 结论与决策

直接按 /post-check 报告的 Missed Updates 列表逐项修：
- ai_context/conventions.md / architecture.md / decisions.md #11a
  → identity 唯一恒定 → identity + target_baseline 都是 character-level
  恒定文件
- docs/requirements.md 三处（ASCII 流程图 / 输入裁剪段 / 目录结构图）
  → 同步 target_baseline
- docs/architecture/schema_reference.md → 加 target_baseline 章节
  + 计数 5→6 + 启动加载表加 target_baseline 行 + 「无独立 baseline 文件
  需要合并」改写
- schemas/README.md → character/ 行 schemas 列表加 target_baseline
- automation/prompt_templates/baseline_production.md → 末尾 checklist
  补 target_baseline

不动：
- automation/persona_extraction/validator.py 模块 docstring（属
  BASELINE-DEPRECATE post-check 已识别的 4 件套残余范围，不扩）
- 不引入新概念 / 不改 schema / 不动代码逻辑（纯 doc 对齐）

## 计划动作清单

- file: `ai_context/conventions.md` line 80 → identity「**only**
  character-level constant baseline」改为「identity + target_baseline
  是 character-level 恒定文件」
- file: `ai_context/architecture.md` line 90 → 「`identity.json` is the
  only character-level constant」改为含 target_baseline 的并列说法
- file: `ai_context/decisions.md` line 41 (#11a) → 「**Only
  character-level constant file**」改为「character-level constant file
  alongside `target_baseline.json` (#13)」类措辞
- file: `docs/requirements.md` line ~1256 → Phase 2 ASCII 流程图节点
  追加 target_baseline.json + 删除「角色级唯一常量」措辞
- file: `docs/requirements.md` line ~1382 → 输入裁剪段同步 target_baseline
  也每 stage 传入 + 删除「角色级唯一常量」措辞
- file: `docs/requirements.md` line ~3230 → 目录结构 ASCII 图
  characters/{character_id}/canon/ 段加 target_baseline.json 条目 +
  identity.json 注释删除「唯一」
- file: `docs/architecture/schema_reference.md` → 5 处更新：
  - line 16 character/ schemas 计数 5→6
  - 在 identity.schema.json 章节后插入 `### character/target_baseline.schema.json` 段
  - line 246「运行时与 identity.json 配套加载即可，无独立 baseline 文件
    需要合并」改写
  - line 450 启动加载表加 target_baseline.json 行
  - line 451「与 identity 配套即可」改为「与 identity + target_baseline 配套」
- file: `schemas/README.md` line 12 → character/ 行 schemas 列表加
  `target_baseline`
- file: `automation/prompt_templates/baseline_production.md` line 254-255
  → 末尾「baseline 阶段只需完成上文列出的...」补 target_baseline

## 验证标准

- [ ] grep `唯一恒定|角色级唯一|唯一角色级|only character-level constant|the only character-level|Only character-level constant`
  在 ai_context/ docs/ schemas/ automation/ simulation/ 全部 0 命中
- [ ] grep `target_baseline` 在 docs/architecture/schema_reference.md
  ≥ 3 命中（章节标题 + 启动加载表 + 文中引用）
- [ ] grep `target_baseline` 在 schemas/README.md ≥ 1 命中
- [ ] python -c "import json; json.load(open('schemas/character/target_baseline.schema.json'))"
  仍能正常加载（未误改 schema 文件）
- [ ] git diff 仅触及 8 个 doc / md 文件，无代码 / schema 文件改动

## 执行偏差

无（按计划清单 1:1 执行；prompt_builder.py 的 char_snapshot /
char_support read list docstring 仍单独提 identity 没列 target_baseline，
但这是因为 phase 3 read list 还未把 target_baseline 加入——属
T-CHAR-SNAPSHOT-SUB-LANES 范围，本轮不扩。docstring 描述当前行为准确，
不是 stale）

<!-- POST 阶段填写 -->

## 已落地变更

修改（7 文件）：
- `ai_context/conventions.md` line 80 — Data Separation Hard Schema Gates
  identity「**only** character-level constant baseline」改为「identity +
  target_baseline are the character-level constant baselines」并补 D4
  硬约束一句
- `ai_context/architecture.md` line 90 — Self-Contained Stage Snapshots
  identity「only character-level constant」改为「identity +
  target_baseline are the character-level constants」+ 补 target_baseline
  锚点引用 #13
- `ai_context/decisions.md` #11a (line 41) — 「**Only character-level
  constant file**」改为「**Character-level constant file alongside
  `target_baseline.json` (#13)**」
- `docs/requirements.md` line 1255-1259 — Phase 2 ASCII 流程图节点改写：
  identity.json + target_baseline.json 并列「两件 character-level 恒定
  文件, 全书视野初稿」
- `docs/requirements.md` line 1383 — 输入裁剪原则段「identity.json（角色级
  唯一常量）每个 stage 都传入」改为「identity.json + target_baseline.json
  （两件 character-level 恒定文件）每个 stage 都传入」+ 区分 identity
  可被 char_support 修正、target_baseline 全程只读不写
- `docs/requirements.md` line 3231-3232 — works/{work_id}/ 目录结构图
  characters/{character_id}/canon/ 段插入 target_baseline.json 行；
  identity.json 行注释删除「唯一」措辞
- `docs/architecture/schema_reference.md` 5 处：line 16 character/ 计数
  5→6；identity.schema.json 章节后插入完整 `### character/target_baseline.schema.json`
  段（含字段 / D4 硬约束 / 生成时机三段）；stage_snapshot 段「运行时与
  identity.json 配套加载即可，无独立 baseline 文件需要合并」改为
  「identity.json + target_baseline.json 配套加载即可，无独立 voice /
  behavior / boundary baseline 文件需要合并」；启动加载表插入
  target_baseline.json 行 + identity 行下面紧跟；stage_snapshot 行
  「与 identity 配套即可」改为「与 identity + target_baseline 配套即可」
- `schemas/README.md` line 12 — character/ 行 schemas 列表 identity 后
  紧跟加 `target_baseline`
- `automation/prompt_templates/baseline_production.md` line 254-255 —
  末尾 checklist 「foundation / fixed_relationships / identity / manifest
  / 空 stage_catalog」改为「foundation / fixed_relationships / identity
  / target_baseline / manifest / 空 stage_catalog」

新增（1 文件）：
- `logs/change_logs/2026-04-29_215206_phase2_baseline_post_check_fixes.md`
  （本文件）

## 与计划的差异

无。计划 8 项 doc 文件全部触及；schemas/README.md + schema_reference.md
两张 Cross-File Alignment 点名表也都补齐。

## 验证结果

- [x] grep `唯一恒定|角色级唯一|唯一角色级|only character-level constant|the only character-level|Only character-level constant`
  在 ai_context/ docs/ schemas/ automation/ simulation/ → 0 命中
- [x] grep `target_baseline` 在 docs/architecture/schema_reference.md →
  5 命中（章节标题 + 启动加载表行 + stage_snapshot 段 + 章节内 3 处引用）
- [x] grep `target_baseline` 在 schemas/README.md → 1 命中（character/ 行）
- [x] python -c "import json; json.load(open('schemas/character/target_baseline.schema.json'))"
  → schema load OK
- [x] git diff 仅触及 7 个 doc / md 文件 + 1 新 log，无代码 / schema
  文件改动（PRE 计划写 8 个 doc，实际 docs/requirements.md 算 1 个文件
  内 3 处编辑，故 7 个 doc）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-29 21:57:55 EDT
