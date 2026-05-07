# stage_plan_anchor_debias

- **Started**: 2026-05-07 08:06:19 EDT
- **Branch**: extraction/<work_id> → main (worktree at ../offpage-main)
- **Status**: PRE

## 背景 / 触发

resume 跑 `phase 1 → 1.5 → 2 (baseline)`，phase 1 LLM call (07:21–07:38)
产出 `works/<work_id>/analysis/stage_plan.json` 时被 SIGTERM 中断
前已落盘 `world_overview.json` (07:31) + `stage_plan.json` (07:35)。

stage_plan 异常：537 章被切成 53 个 stage，**前 38 个全是恰好 10 章**
（C0001-C0010 / C0011-C0020 / …），剩余 S039/S040/S053 是 13/12/12
（537 不能被 10 整除剩到尾段）。`boundary_reason` 字段是真实剧情
节点描述，但 stage 边界明显是先按 10 章切、后挑剧情节点写理由——
不是按剧情节点切。

根因（[automation/prompt_templates/analysis.md](automation/prompt_templates/analysis.md)
原 §步骤 2 + JSON 示例 + 字段名共 3 重 "10 章" 锚点）：

1. 第 131 行 "默认每阶段 10 章" 直接给 LLM 锚定值
2. JSON 示例 `"chapters": "C0001-C0010"` + `"chapter_count": 10`
3. schema 字段 `default_stage_size: 10` 字段名 + 值同时锚定

## 结论与决策

讨论结果（用户拍板「重写 prompt + 方案 c」）：

- **Prompt 重写**：[analysis.md](automation/prompt_templates/analysis.md)
  §步骤 2 改成 **三子步程序式流程**——2.1 全局剧情拐点扫描（强制
  先列拐点列表）→ 2.2 候选拐点分组成 stage（章数 5-15 hard）→
  2.3 反锚定自检（≥3 连等章数视为机械等分必须重审 + boundary_reason
  必须对应 2.1 拐点章号）。JSON 示例改为非整数倍（8 章 + 13 章
  混合），打破 "10 是甜区" 暗示。
- **Schema 字段删除（方案 c）**：彻底删除 `default_stage_size` 字段。
  全仓 grep 确认：消费侧只有 [orchestrator.py:1545](automation/persona_extraction/orchestrator.py#L1545)
  / [orchestrator.py:2700](automation/persona_extraction/orchestrator.py#L2700)
  把字段值传给 `Phase3Progress(stage_size=...)`，而 [Phase3Progress.stage_size](automation/persona_extraction/progress.py#L558)
  是 **dead metadata**（只 serialize / deserialize，无任何决策逻辑读取）。
  [work_manifest.schema.json:93](schemas/work/work_manifest.schema.json#L93)
  的 `extraction.default_stage_size` 完全孤立（无 Python 代码读 manifest
  的 extraction 块）。三处均可安全删除，单一真源 = stage_plan.schema.json
  的 `chapter_count: minimum 1, maximum 15`（其中 monolithic 5-15 由
  orchestrator `_check_stage_plan_limits` 强制下限）。
- **不扩范围**：work_manifest 的 `stage_is_cumulative` 同样疑似 dead，
  本次不动；下次 review 单独处理。

## 计划动作清单

Schema 改动：
- file: [schemas/analysis/stage_plan.schema.json](schemas/analysis/stage_plan.schema.json) → 从 `required` 移除 `default_stage_size`；删除 properties.default_stage_size 整块；调整顶部 description（去掉默认值锚点提示）
- file: [schemas/work/work_manifest.schema.json](schemas/work/work_manifest.schema.json) → 删除 `extraction.default_stage_size` 字段（保留 `stage_is_cumulative` 不动）

Prompt 改动：
- file: [automation/prompt_templates/analysis.md](automation/prompt_templates/analysis.md) → §步骤 2 整段重写为三子步流程（2.1 拐点扫描 / 2.2 分组 / 2.3 反锚定自检）；JSON 示例改为 `chapters: "C0001-C0008" / chapter_count: 8` + `chapters: "C0009-C0021" / chapter_count: 13` 混合非整数倍；删除示例里的 `"default_stage_size": 10`；§规则 收紧 `boundary_reason` 描述

Code 改动：
- file: [automation/persona_extraction/orchestrator.py](automation/persona_extraction/orchestrator.py) → 删除 1545 行 `stage_size = stage_plan.get(...)`；删除 1164 行 light_novel 路径的 `"default_stage_size": 1,`；删除 2700-2701 行 rebuild 路径的字段读取；`Phase3Progress(...)` 调用去掉 `stage_size=` 实参
- file: [automation/persona_extraction/progress.py](automation/persona_extraction/progress.py) → 删除 558 行 `stage_size: int = 10` 字段；删除 639 行 save 字典里的 `"stage_size"`；删除 656 / 847 行 load 路径的 `stage_size=data.get(...)`

Docs 改动：
- file: [docs/architecture/schema_reference.md](docs/architecture/schema_reference.md) → 第 66 行的 stage_plan 关键字段列表去掉 `default_stage_size`
- file: [ai_context/decisions.md](ai_context/decisions.md) → 新增决策条目（stage_plan 切分语义：prompt 反锚定 + 字段去除）

## 验证标准

- [ ] `python -c "from automation.persona_extraction import progress, orchestrator"` 无 ImportError / NameError
- [ ] `python -c "import json,jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('schemas/analysis/stage_plan.schema.json')))"` 通过
- [ ] `python -c "import json,jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('schemas/work/work_manifest.schema.json')))"` 通过
- [ ] 全仓 grep `default_stage_size` 在 logs/ + sources/ + works/ + users/ 之外残留为 0
- [ ] 全仓 grep `"默认每阶段 10 章"` 残留为 0
- [ ] prompt 示例不再出现 `"chapters": "C0001-C0010"` + `"chapter_count": 10` 同行组合（确保示例改为非整数倍）
- [ ] `Phase3Progress` 的字段总数减 1（`stage_size` 移除）

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

Schema：
- [schemas/analysis/stage_plan.schema.json](schemas/analysis/stage_plan.schema.json) — `required` 移除 `default_stage_size`；`properties.default_stage_size` 整块删除；`boundary_reason.description` 收紧（明确要求命名拐点类型 + 关键事件，禁止"满 N 章"或泛泛剧情概括）
- [schemas/work/work_manifest.schema.json](schemas/work/work_manifest.schema.json) — `extraction.default_stage_size` 字段块删除（保留 `stage_is_cumulative`）

Prompt：
- [automation/prompt_templates/analysis.md](automation/prompt_templates/analysis.md) — §步骤 2 整段重写为三子步流程：2.1 全局剧情拐点扫描（强制先于 2.2，列章号 + 8 类拐点枚举 + 一句话事件，作为推理过程产出）→ 2.2 候选拐点分组成 stage（章数 5-15 hard，拐点优先级表，章数取舍原则）→ 2.3 反锚定自检（≥3 连等章数视为机械等分必须重审 + boundary_reason 必须指回 2.1 拐点 + 章数硬范围）。删除"默认每阶段 10 章"。JSON 示例改为 8 章 + 13 章 + 11 章混合非整数倍，并加注释"故意用非整数倍数字，避免暗示某个章数是甜区"；删除示例里的 `"default_stage_size": 10`

Code：
- [automation/persona_extraction/orchestrator.py:1163](automation/persona_extraction/orchestrator.py#L1163) — `_build_light_novel_stage_plan` 返回 dict 删除 `"default_stage_size": 1`
- [automation/persona_extraction/orchestrator.py:1543](automation/persona_extraction/orchestrator.py#L1543) — 删除 `stage_size = stage_plan.get("default_stage_size", 10)`；同位 `Phase3Progress()` 调用去掉 `stage_size=stage_size` 实参
- [automation/persona_extraction/orchestrator.py:2694](automation/persona_extraction/orchestrator.py#L2694) — rebuild 路径的 `Phase3Progress()` 去掉 `stage_size=stage_plan_data.get("default_stage_size", 10)`
- [automation/persona_extraction/progress.py:557](automation/persona_extraction/progress.py#L557) — `Phase3Progress` dataclass 删除 `stage_size: int = 10` 字段
- [automation/persona_extraction/progress.py:637](automation/persona_extraction/progress.py#L637) — `save` 序列化字典删除 `"stage_size": self.stage_size`
- [automation/persona_extraction/progress.py:653](automation/persona_extraction/progress.py#L653) — `load` 反序列化删除 `stage_size=data.get("stage_size", 10)`
- [automation/persona_extraction/progress.py:842](automation/persona_extraction/progress.py#L842) — legacy migrate 路径的 `Phase3Progress()` 去掉 `stage_size=data.get("stage_size", 10)`

Docs：
- [docs/architecture/schema_reference.md:66](docs/architecture/schema_reference.md#L66) — stage_plan 关键字段列表去掉 `default_stage_size`
- [ai_context/decisions.md:301](ai_context/decisions.md#L301) — 新增决策 27m（stage_plan 切分语义：拐点先行 + 字段下线）

## 与计划的差异

无。计划清单 = 实际改动清单 1:1 对应。

## 验证结果

- [x] `python -c "from automation.persona_extraction import progress, orchestrator"` 无 ImportError / NameError — OK，`progress, orchestrator imports` 正常
- [x] `jsonschema.Draft202012Validator.check_schema(stage_plan.schema.json)` 通过 — OK
- [x] `jsonschema.Draft202012Validator.check_schema(work_manifest.schema.json)` 通过 — OK
- [x] 全仓 grep `default_stage_size` 在 logs/ + sources/ + works/ + users/ 之外残留 — 仅 ai_context/decisions.md 3 行（27m 决策正文里描述"旧字段已删除"，合法引用）
- [x] 全仓 grep `"默认每阶段 10 章"` / `每阶段 10 章` 残留 — 0 命中
- [x] prompt 示例不再出现 `"chapters": "C0001-C0010"` + `"chapter_count": 10` 同行组合 — 0 命中
- [x] `Phase3Progress` 字段总数减 1 — 验证 `dataclasses.fields()` = `['work_id', 'stages', 'last_updated']`
- [x] 旧 stage_plan.json（含 `default_stage_size: 10`）现被 schema `additionalProperties: false` 拒绝 — 验证 `Additional properties are not allowed ('default_stage_size' was unexpected)`
- [x] 新 stage_plan.json（无 `default_stage_size`，章数非整数倍混合）通过 schema 校验

## Completed

- **Status**: DONE
- **Finished**: 2026-05-07 08:17:42 EDT

