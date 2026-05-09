# stage_plan_schema_min_8_direct_gate

- **Started**: 2026-05-09 01:21:58 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

紧接 commit `5235e25` (M1+M2 in-depth 防御) + `6e4e9ec` (extraction 分支 commit phase 1 产物清理 main 工作目录)。用户审视 `schemas/analysis/stage_plan.schema.json` 后提问"为什么 schema 里的 chapter_count 不规定 8-15？validation check 不就看不到吗？"——直击当前妥协点。

**当前妥协**（决策 #27m / #52 描述）：schema `chapter_count.minimum=1` / `maximum=15`，文字描述说"minimum=1 是为 light_novel 1:1 派生让出空间，monolithic 8-15 hard 由 orchestrator `_check_stage_plan_limits` 强制"。但这违反决策 #27b "Bounds-only-in-schema" 单一真源原则——下限 8 在代码层兜底而非 schema 层。

**实际代码路径检查**（grep `_stage_plan_validator` + `_check_stage_plan_limits` 全 module）：
- monolithic 模式：`run_analysis` 把 stage_plan lane 加进 `lanes` 列表（orchestrator.py:1212-1216 `if not is_light_novel:`），LLM 输出经 `_lane_passes_skip` line 1227 schema validate（**当前不挡 < 8** 因 minimum=1）+ 后续代码层 `_check_stage_plan_limits` 兜底
- light_novel 模式：stage_plan lane **整体不在 lanes 列表里**（line 1212 条件不满足），由 `_build_light_novel_stage_plan` (line 1264) 程序派生后 `_write_json` 直接落盘——**任何路径都不走 schema validate**

**核心发现**：light_novel 派生路径**事实上不被 schema validate 检查**——既不在 lanes 也无主动 validate 调用。所以 schema `minimum=1` 这个"为 light_novel 让出空间"的妥协实际**没有受益方**：light_novel 不走这条路，monolithic 又被妥协迫使靠代码兜底。

## 结论与决策

**方案 A**：schema `chapter_count.minimum: 1 → 8`（maximum=15 不动）。light_novel 派生路径无影响（不走 schema gate）；monolithic LLM 输出由 schema gate 直接挡 < 8，复用决策 #27i schema-gate-as-retry-trigger 自动注入 prior_error 到下次 `build_stage_plan_prompt` retry——更标准的反馈环。

**保留**：orchestrator.py `_check_stage_plan_limits` 函数 + `_lane_passes_skip` 内对 stage_plan 的二次检查（line 1230-1234）+ retry path 的二次检查（line 1339-1342）—— 作 **belt-and-suspenders zero-cost 兜底**（schema gate 是首层硬挡，代码层二次确认）。函数签名 `min_stage_size: int = 8` 上一轮已对齐。**不删代码层兜底**理由：(a) 多层防御原则与决策 #27i 思路一致（schema gate 失败时代码层仍能给出友好诊断 print）；(b) light_novel 派生 + 程序写入路径若未来加入 schema validate 时，代码层兜底仍能在那条路径起作用；(c) zero cost。

**Trade-off 接受**：light_novel 派生的 stage_plan.json (chapter_count=1) 在新 schema 下 **schema-invalid**——若未来某外部工具（IDE / lint / /full-review 产物完整性扫描扩展到 works/<work_id>/analysis/）拿 stage_plan.schema 验证 light_novel 产物会误报。当前没有这种调用点（grep 确认），可接受；若未来出现，再升级到方案 B（schema 顶层加 `structure_mode` 字段 + `if/then/else` dispatch 两 profile）。该 trade-off 在 decisions.md #27m 描述里显式记录。

**不修**：
- 方案 B（if/then/else dispatch）—— 工作量大（schema 重构 + LLM prompt 加 structure_mode 字段教学 + `_build_light_novel_stage_plan` 写入 + 4 件 docs 同步），当前 trade-off 没有触发，过度工程。
- light_novel 派生路径不加 schema validate —— 程序产出可信，无 LLM-edge 不确定性，加 validate 是冗余。

## 计划动作清单

- file: `schemas/analysis/stage_plan.schema.json` line 52-54 → `chapter_count.minimum: 1 → 8`
- file: `schemas/analysis/stage_plan.schema.json` line 5（顶部 description） + line 54（chapter_count description） → 文字同步：去掉"为 light_novel 让出空间"的措辞，改为说明"schema chapter_count: minimum=8 / maximum=15 双向硬挡 LLM 输出（monolithic 路径）；light_novel 派生路径事实上不走 schema validate（程序产出可信，chapter_count=1 schema-invalid 是已知 trade-off，记录在 decisions.md #27m）"
- file: `automation/prompt_templates/analysis_stage_plan.md` line 52 + 71 → 文字精化：从"`schema chapter_count.maximum=15 强制上限 + orchestrator _check_stage_plan_limits 强制下限 8`"改为"`schema chapter_count.minimum=8 + maximum=15 双向硬挡 + orchestrator _check_stage_plan_limits 代码层 belt-and-suspenders 兜底`"，反映新单一真源
- file: `ai_context/decisions.md` #27m 第二条（line 308-310）→ "schema chapter_count.maximum=15 强制上限 + ..." 文字同步成"schema chapter_count: minimum=8 / maximum=15 双向硬挡 (monolithic LLM 输出路径) + 代码层兜底；light_novel 派生不走 schema validate, chapter_count=1 schema-invalid 是已知 trade-off"
- file: `ai_context/decisions.md` #52 stage_plan lane 段（"8–15 章 limit 检查，monolithic 模式由 `_check_stage_plan_limits` 在 schema 之后兜底执行下限 8"）→ "8–15 章 limit 检查由 schema 直接硬挡（monolithic 模式 LLM 输出路径走 schema-gate-as-retry-trigger 注入 prior_error，决策 #27i），代码层 `_check_stage_plan_limits` 作 belt-and-suspenders 二次兜底"
- file: `docs/architecture/schema_reference.md` line 68 → 同步描述
- file: `docs/architecture/extraction_workflow.md`（如有相关锚点）→ 同步
- file: `automation/persona_extraction/_smoke_cli_resume_background_validation.py` 不动（与本次改动无关）
- 新增 schema gate 反向 smoke：`automation/persona_extraction/_smoke_stage_plan_schema_min8.py`（独立小 smoke，验证 chapter_count=5 直接 schema-fail + chapter_count=8/15 通过 + chapter_count=16 fail）

不动：code 层 `_check_stage_plan_limits`（function 签名 default 上一轮已 5→8，本次保留作兜底）；light_novel 派生路径；CLI；config.toml / config.py（min_chapter_count=8 已对齐）。

## 验证标准

- [ ] schema metaschema 通过：`jsonschema.Draft202012Validator.check_schema(stage_plan.schema.json)` 无错误
- [ ] 新增 smoke `_smoke_stage_plan_schema_min8.py` 全过：(a) chapter_count=5 → validator 报 minimum=8 错；(b) chapter_count=8 / 15 → 无错；(c) chapter_count=16 → validator 报 maximum=15 错；(d) chapter_count=1 → validator 报 minimum=8 错（确认 light_novel 派生产物如果跑 schema 会 fail，作为已知 trade-off 文档证据）
- [ ] 既有 smoke 全过：`_smoke_cli_resume_background_validation.py` 9/9 + import OK（`from automation.persona_extraction import orchestrator, cli, config`）
- [ ] 文字残留 grep：`schema chapter_count.minimum=1 是为 light_novel 让出空间` / `schema 不再硬挡 5 下限` / `schema 不挡 minimum=8` 等旧措辞在 `automation/ schemas/ ai_context/ docs/ prompts/`（除 `logs/change_logs/`）残留 = 0

## 执行偏差

无（PRE 计划清单全部 1:1 落地；Step 7 review 发现 1 处一行修在 conventions.md:49 Cross-File Alignment 表 structure_mode row 描述）。

<!-- POST 阶段填写 -->

## 已落地变更

**核心改动（PRE 计划 1:1）**：

- `schemas/analysis/stage_plan.schema.json` line 5（顶部 description）+ line 52-54（`chapter_count`）:
  - `chapter_count.minimum: 1 → 8`（数值改动 = 本次核心）
  - 顶部 description + chapter_count.description 同步描述 schema 直接硬挡 + light_novel 派生路径 trade-off
- `automation/prompt_templates/analysis_stage_plan.md` line 52 + 71: 文字精化"schema `chapter_count.minimum=8` / `maximum=15` 双向硬挡 + 决策 #27i schema-gate-as-retry-trigger 注入 prior_error + 代码层 belt-and-suspenders 二次兜底"
- `ai_context/decisions.md` #27m line 308-315 + #52 stage_plan lane 段：描述同步反映 schema 单一真源
- `docs/architecture/schema_reference.md` line 66-68 + `docs/architecture/extraction_workflow.md` line 121: 同步描述

**新增 smoke**：
- `automation/persona_extraction/_smoke_stage_plan_schema_min8.py`（5 场景：A/B 边界 valid + C minimum=5 reject + D maximum=16 reject + E light_novel chapter_count=1 schema-invalid 作为已知 trade-off 文档证据）

**Step 7 review 一行修**：
- `ai_context/conventions.md` line 49 Cross-File Alignment 表 `structure_mode` row：去掉过时描述"`chapter_count.minimum`...loosened so light_novel 1:1 derivation passes"，改为"`chapter_count.minimum=8` / `maximum=15` directly hard-gates monolithic LLM output via decision #27i schema-gate-as-retry-trigger — light_novel derivation bypasses schema validate entirely, `chapter_count=1` derived products being schema-invalid is a known trade-off documented in decision #27m"

**不动**（按 PRE 决策）：
- `automation/persona_extraction/orchestrator.py` 代码层 `_check_stage_plan_limits` 函数 + 调用站点（保留作 belt-and-suspenders 兜底，zero cost）
- light_novel 派生路径 `_build_light_novel_stage_plan` + `_write_json` 直接落盘（不加 schema validate）
- `automation/config.toml` + `automation/persona_extraction/config.py`（min_chapter_count=8 已对齐）
- `automation/persona_extraction/cli.py`（与本次 schema 改动无关）
- 既有 smoke `_smoke_cli_resume_background_validation.py`（与本次正交）

## 与计划的差异

PRE 计划 1:1 落地。Step 7 引出 1 处 conventions.md:49 一行修（按 /go Step 7 规则发现即修，记入执行偏差段）。

## 验证结果

- [x] **schema metaschema 通过**：`jsonschema.Draft202012Validator.check_schema(stage_plan.schema.json)` → 无错
- [x] **新 smoke `_smoke_stage_plan_schema_min8.py` 5/5 全过**：
  - (A) chapter_count=8 valid ✅
  - (B) chapter_count=15 valid ✅
  - (C) chapter_count=5 invalid `5 is less than the minimum of 8` ✅
  - (D) chapter_count=16 invalid `16 is greater than the maximum of 15` ✅
  - (E) chapter_count=1 invalid `1 is less than the minimum of 8`（确认 light_novel 派生产物 schema-invalid trade-off）✅
- [x] **既有 smoke 全过**：CLI smoke 9/9 + import OK（`from automation.persona_extraction import orchestrator, cli, config`）
- [x] **文字残留 grep = 0**：`minimum.*1.*让出空间 / schema 不再硬挡 5 / schema 不挡 minimum=8 / schema chapter_count.minimum=1` 在 `automation/ schemas/ ai_context/ docs/ prompts/` 范围（除 `logs/change_logs/` 历史 log + `docs/todo_list.md` 历史归档段）残留 0

## Completed

- **Status**: DONE
- **Finished**: 2026-05-09 01:27:20 EDT
