# phase1-schema-triplet-and-doc-fixes

- **Started**: 2026-04-26 19:53:54 EDT
- **Branch**: main（worktree `../offpage-main`，主 checkout 留在 `extraction/我和女帝的九世孽缘`，clean）
- **Status**: DONE
- **LOG**: `logs/change_logs/2026-04-26_195354_phase1-schema-triplet-and-doc-fixes.md`

## 背景 / 触发

合并三件事（POST-CHECK 收尾 + Phase 1 schema 三件套）：

1. **Phase 1 schema 三件套**（todo `T-PHASE1-OUTPUT-SCHEMAS`）：Phase 1 (`automation/prompt_templates/analysis.md`) 一次 LLM 调用产出 3 个 JSON 文件 (world_overview / stage_plan / candidate_characters)，全部进 git 且喂给 Phase 2/3/4 全部下游，但**当前 schemas/ 下无对应 schema**，破坏 #27b "Bounds-only-in-schema" 全局原则。
2. **POST-CHECK Medium #1**：`ai_context/decisions.md` 加 #27i ADR 记录 "schema-gate-as-retry-trigger" 模式（与 #27b 配对，覆盖 Phase 0 / Phase 1 / Phase 4 三处现已落地的 enforcement）。
3. **POST-CHECK Medium #2**：`automation/README.md` 补 Phase 0/4 schema gate + retry 机制说明（现 README 仅描述 repair_agent 的 jsonschema check）。

## 结论与决策

**1. Phase 1 走与 Phase 0/4 一致的 schema-gate-as-retry-trigger 模式**

`run_analysis` 已有 retry loop（`MAX_ANALYSIS_RETRIES = cfg.phase1.exit_validation_max_retry`，目前用于 stage chapter_count 5-15 限制违反时重试）。schema gate 接入直接复用此 retry：
- 在 3 个文件 `_load_json` 后跑 jsonschema 校验
- schema 失败的文件 + stage limit violating stage 合并成 correction_feedback
- 删除 schema 失败文件（让 LLM 重生），保留 valid 文件
- 重试上限统一走 `MAX_ANALYSIS_RETRIES`
- 现有 `_check_stage_plan_limits` 不删除（schema 也卡 chapter_count 5-15，但代码层 belt-and-suspenders 不冲突）

**Phase 1 不引入新的 retry_note 模板槽**——`build_analysis_prompt(correction_feedback=...)` 已是 code-append 机制（_render_template 后追加 "## ⚠️ 修正要求" 块），与 Phase 0/4 的 `{retry_note}` 模板槽路径不同但功能等价；保持现状不重构（YAGNI），只复用 correction_feedback。

**2. Schema bound 选取**

| schema | 关键 bound | 理由 |
|---|---|---|
| world_overview | `additionalProperties: true` 顶层 | per-work 可扩展，对齐 #27 world foundation 同款 |
| world_overview | summary 200 / 名字段 30 / 列表条目 100-200 | 不是用户严格指定，按现有 Phase 2 类似字段量级取 |
| stage_plan | `additionalProperties: false` | 结构稳定，硬收敛 |
| stage_plan | `stage_id: ^S\d{3}$` / `chapters: ^\d{4}-\d{4}$` | 与 ID 家族 + chapter 命名约定对齐 |
| stage_plan | `chapter_count: 5-15` | 与 prompt 自检 + 现 `_check_stage_plan_limits` 一致 |
| stage_plan | `stages: maxItems 200` | 49 stage 实测，留余量给大作品 |
| candidate_characters | `additionalProperties: false` | 同上 |
| candidate_characters | `aliases[].type: enum` | 10 项中文枚举，prompt 第 151-153 行明确列出 |
| candidate_characters | `frequency: ["高","中","低"]` enum | prompt 列举 |
| candidate_characters | `importance: ["主角","重要配角","次要配角"]` enum | prompt 列举 |
| candidate_characters | `recommended: boolean` | **prompt 文本"是/否/待定"与 JSON 模板 `true` 不一致；按 JSON 模板取 boolean，prompt 文本同步修正** |

**3. analysis.md prompt 修正**

- line 157 `建议是否建包（是/否/待定）` → 改为 `建议是否建包（boolean: true 或 false；不确定时取 false）`，让 prompt 文本与 JSON 模板 + schema 三方对齐
- 三个 JSON 模板段加 schema 链接说明（如 summarization.md 步骤 2 的 schema 契约引导文字同款）

**4. ai_context/decisions.md #27i 新条目**

```
27i. **schema-gate-as-retry-trigger pattern.** L1 jsonschema 校验作为
     LLM 输出失败重试的另一类 trigger（与"JSON 解析失败"并列）；失败首条
     注入 retry prompt（Phase 0/4 通过 `{retry_note}` 占位 + `prior_error`
     参数；Phase 1 通过 `correction_feedback` 代码追加）。schemas 路径
     `schemas/analysis/{chapter_summary_chunk,scene_split,world_overview,
     stage_plan,candidate_characters}.schema.json`。装置 →
     `automation/persona_extraction/{orchestrator.py:_summarize_chunk + 
     run_analysis, scene_archive.py:validate_scene_split}`。
```

**5. 故意不动**

- **不**改 `_check_stage_plan_limits`（与 schema chapter_count 重复，但 belt-and-suspenders；defer）
- **不**重构 `build_analysis_prompt` 走 `{retry_note}` 模板槽（与 Phase 0/4 路径不同但功能等价；YAGNI）
- **不**给 Phase 2 / Phase 3 / Phase 3.5 加 schema gate（Phase 2 由 Phase 3 char_support 通路接住；Phase 3 已有 repair_agent；Phase 3.5 是程序级一致性检查不是 LLM 输出）
- **不**清 todo_list 其他条目（仅删 T-PHASE1-OUTPUT-SCHEMAS）

## 计划动作清单

### Schema（main 分支）

- file: `schemas/analysis/world_overview.schema.json` (新建)
- file: `schemas/analysis/stage_plan.schema.json` (新建)
- file: `schemas/analysis/candidate_characters.schema.json` (新建)

### Code（main 分支）

- file: [automation/persona_extraction/orchestrator.py](automation/persona_extraction/orchestrator.py) → 加 3 个 module-level lru_cache validator helper（`_world_overview_validator` / `_stage_plan_validator` / `_candidate_characters_validator`）；`run_analysis` 加 schema 校验段（在现有 stage limit 检查之前），失败合并到 `correction_feedback`，复用现有 retry 机制

### Prompt（main 分支）

- file: [automation/prompt_templates/analysis.md](automation/prompt_templates/analysis.md) → 三个 JSON 模板段附 schema 链接；line 157 `recommended` 字段说明 `(是/否/待定)` 改 `(boolean)`；步骤 2/3 `recommended: 是` 等示例改 `recommended: true/false`

### Doc（main 分支）

- file: [schemas/README.md](schemas/README.md) → analysis 行典型成员加 3 项；文件数 2 → 5
- file: [docs/architecture/schema_reference.md](docs/architecture/schema_reference.md) → Analysis 层段加 3 个新 schema 描述；子目录表 "2" → "5"
- file: [docs/architecture/extraction_workflow.md](docs/architecture/extraction_workflow.md) → Phase 1 段加 schema gate 说明（与 Phase 0/4 同款）
- file: [ai_context/architecture.md](ai_context/architecture.md) → Phase 1 描述加 schema gate（`schemas/analysis/{world_overview,stage_plan,candidate_characters}.schema.json`）
- file: [ai_context/decisions.md](ai_context/decisions.md) → 加 #27i ADR
- file: [automation/README.md](automation/README.md) → Phase 0/4 schema gate + retry 机制段（POST-CHECK Medium #2）
- file: [docs/todo_list.md](docs/todo_list.md) → 删除 T-PHASE1-OUTPUT-SCHEMAS 整条（已落实），按 todo_list 文件说明的"任务完成 → 立即从本文件删除整条"规则

## 验证标准

- [ ] 3 个新 schema 跑 `Draft202012Validator.check_schema` 自身合法
- [ ] 跑 mock data：构造 valid + invalid 各 1 份，分别验证 0 errors / 非 0 errors
- [ ] `python -m py_compile automation/persona_extraction/orchestrator.py` 通
- [ ] `python -c "from automation.persona_extraction.orchestrator import _world_overview_validator, _stage_plan_validator, _candidate_characters_validator"` import 通
- [ ] `git grep -nE 'schemas/analysis/' -- ':!logs/'` 含 5 个 schema 引用全到位（chunk + scene_split 旧 2 + world_overview/stage_plan/candidate_characters 新 3）
- [ ] schemas/README.md 子目录表 analysis 文件数 = 5；schema_reference.md 同
- [ ] `git grep -nE 'recommended.*[(（].*是[/／].*否' automation/prompt_templates/analysis.md` 0 命中（旧"是/否/待定"已替换）
- [ ] `git grep -nE '\bT-PHASE1-OUTPUT-SCHEMAS\b'` 仅 logs/ 残留（todo 已删）
- [ ] decisions.md 新增 #27i 段落含 "schema-gate-as-retry-trigger" 关键字
- [ ] automation/README.md 含 Phase 0/4 schema gate 段落
- [ ] 文档不出现真实书名 / 角色名（`git grep '我和女帝' -- ':!logs/' ':!.git*'` = 0）
- [ ] commit message 风格对齐 `git log --oneline -10`

## 执行偏差

无（计划清单全落实；7 任务领域 / 9 modified + 4 new = 13 文件）

<!-- POST 阶段填写 -->

## 已落地变更（main 分支）

### 新建 schema（3）

- [schemas/analysis/world_overview.schema.json](schemas/analysis/world_overview.schema.json)：`additionalProperties: true` 顶层；required 8 字段；world_structure / power_system 内嵌对象 required summary + array 字段；major_factions / world_lines / core_rules 全数组带 maxItems + items maxLength
- [schemas/analysis/stage_plan.schema.json](schemas/analysis/stage_plan.schema.json)：`additionalProperties: false`；stages[] maxItems 200，items required 6 字段；stage_id pattern `^S\d{3}$`、chapters pattern `^\d{4}-\d{4}$`、chapter_count integer 5-15 hard
- [schemas/analysis/candidate_characters.schema.json](schemas/analysis/candidate_characters.schema.json)：`additionalProperties: false`；candidates[] maxItems 100，items required 6 字段；aliases[].type 10 项中文 enum、frequency / importance 各自 enum、recommended boolean

### 代码（orchestrator.py）

- [orchestrator.py:75-104](automation/persona_extraction/orchestrator.py)：抽 `_load_analysis_schema(name)` helper，3 个 lru_cache validator getter 复用之
- [orchestrator.py:863-960](automation/persona_extraction/orchestrator.py) `run_analysis`：3 文件 load 后跑 jsonschema 校验 → 与 `_check_stage_plan_limits` 共同决定是否重试；失败时按文件粒度删除（valid 文件保留），feedback 合并 schema 失败首条 + stage 限制违规后注入 correction_feedback；共享原 `MAX_ANALYSIS_RETRIES` 预算

### Prompt（analysis.md）

- 三处 JSON 模板段附 schema 链接（line 71 / 121 / 161）
- line 157 `(是/否/待定)` → `(boolean: true 或 false；不确定时取 false 让 Phase 1.5 用户最终决定)` —— prompt 文本与 JSON 模板 + schema 三方对齐

### Doc 同步

- [schemas/README.md:9](schemas/README.md)：analysis 行典型成员加 3 项
- [docs/architecture/schema_reference.md](docs/architecture/schema_reference.md)：子目录表 analysis 文件数 2 → 5；§Analysis 层加 3 段 schema 描述
- [docs/architecture/extraction_workflow.md:71-78](docs/architecture/extraction_workflow.md)：Phase 1 出口验证段重写为"双层共享 retry 预算"
- [ai_context/architecture.md:156](ai_context/architecture.md)：Phase 1 描述加 schema gate + 共享 retry 预算
- [ai_context/decisions.md:92](ai_context/decisions.md) 加 #27i ADR：schema-gate-as-retry-trigger pattern
- [automation/README.md:351-364](automation/README.md)：新增"Phase 0 / Phase 1 / Phase 4 schema gate"段，列三 phase 的装置点 + retry 通路 + schema 路径
- [docs/todo_list.md](docs/todo_list.md)：删除 T-PHASE1-OUTPUT-SCHEMAS 整条（已落实）

## 与计划的差异

无

## 验证结果

- [x] 3 个新 schema `Draft202012Validator.check_schema` 全 OK
- [x] mock data：valid 样本 0 errors / invalid 样本（genre 31 字 / chapter_count 20 / recommended "是" / frequency "中等"）各捕获 1+ 错，错误消息可读
- [x] `python -m py_compile automation/persona_extraction/orchestrator.py` 通
- [x] 3 个 validator import + lru_cache same instance ✓
- [x] `git grep schemas/analysis/` = 29 处引用，5 schema 全到位
- [x] schemas/README.md `analysis/` 行 + schema_reference.md 子目录表 = 5（一致）
- [x] `git grep '是/否/待定' analysis.md` = 0
- [x] `git grep T-PHASE1-OUTPUT-SCHEMAS -- ':!logs/'` = 0（仅 logs/ 历史保留，正常）
- [x] decisions.md 含 #27i 段落，关键字 "schema-gate-as-retry-trigger" 命中
- [x] automation/README.md 含 Phase 0 / Phase 1 / Phase 4 schema gate 三表
- [x] `git grep '我和女帝'` = 0

## Completed

- **Status**: DONE
- **Finished**: 2026-04-26 19:53:54 EDT
