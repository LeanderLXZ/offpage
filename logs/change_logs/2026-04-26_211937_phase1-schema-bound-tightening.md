# phase1-schema-bound-tightening

- **Started**: 2026-04-26 21:19:37 EDT
- **Branch**: main（worktree `../offpage-main`，主 checkout 留在 `extraction/我和女帝的九世孽缘`，clean）
- **Status**: DONE
- **LOG**: `logs/change_logs/2026-04-26_211937_phase1-schema-bound-tightening.md`

## 背景 / 触发

用户复审上一轮 /go (`2438620`) 落的 Phase 1 三件套 schema 的 bound 选取，给出收紧建议：原 schema bound 偏宽（部分按"先有 schema 再调"的思路设默认值），现在按用户实际 domain 知识收紧。同时移除 `key_events_expected` 字段（用户判断该字段冗余 / 不必要）。

## 结论与决策

按用户精确数值落 schema，**不引入新字段、不重抽数据**（数据已清盘，下次重抽自然合规）。

### world_overview 收紧

| 字段 | old | new |
|---|---|---|
| `tone` | maxLength 30 | maxLength 49 (`<50`) |
| `world_structure.summary` | maxLength 200 | minLength 100, maxLength 200 |
| `power_system.summary` | maxLength 200 | minLength 100, maxLength 200 |
| `power_system.levels` maxItems | 30 | 19 (`<20`) |
| `world_structure.major_regions` maxItems | 20 | 29 (`<30`) |
| `world_structure.major_regions[]` maxLength | 30 | 29 (`<30`) |
| `major_factions` maxItems | 30 | 19 (`<20`) |
| `major_factions[].description` maxLength | 200 | 99 (`<100`) |
| `world_lines` maxItems | 50 | 19 (`<20`) |
| `world_lines[].core_conflict` maxLength | 200 | 99 (`<100`) |
| `world_lines[].setting_features` maxLength | 200 | 99 (`<100`) |

### stage_plan 收紧 + 字段移除

| 字段 | 操作 |
|---|---|
| `stage_title` | maxLength 30 → 14 (`<15`) |
| `key_events_expected` | **移除**（schema 删字段定义 + required 列表去除；prompt 三处引用同步去除） |

### candidate_characters 收紧

| 字段 | old | new |
|---|---|---|
| `candidates` maxItems | 100 | 29 (`<30`) |
| `description` maxLength | 200 | minLength 100, maxLength 200 |

### bound 解析约定（与既有 5 份 schema 一致）

- `length 100-200` → `minLength: 100, maxLength: 200`（双边 inclusive）
- `length <N` → `maxLength: N-1`（strict less）
- `# of Items <N` → `maxItems: N-1`（strict less）

## 计划动作清单

### Schema（main 分支）

- [schemas/analysis/world_overview.schema.json](schemas/analysis/world_overview.schema.json) → 11 处 bound 调整
- [schemas/analysis/stage_plan.schema.json](schemas/analysis/stage_plan.schema.json) → stage_title maxLength 14；删 `key_events_expected` 整段（properties + required）
- [schemas/analysis/candidate_characters.schema.json](schemas/analysis/candidate_characters.schema.json) → candidates maxItems 29；description 加 minLength 100

### Prompt（main 分支）

- [automation/prompt_templates/analysis.md:114](automation/prompt_templates/analysis.md) stage 条目字段表删 `key_events_expected`
- [automation/prompt_templates/analysis.md:138](automation/prompt_templates/analysis.md) JSON 模板删 `key_events_expected: ["..."]` 行

### Doc（main 分支）

- [docs/architecture/schema_reference.md:58](docs/architecture/schema_reference.md) stage_plan 关键字段段移除 `key_events_expected[]`

### 故意不动

- 不改 `chapter_count` 5-15 bound（用户没要求调）
- 不改 `aliases[]` enum / `frequency` / `importance` enum（用户没要求调）
- 不改 ai_context/architecture.md / extraction_workflow.md / decisions.md 中关于 Phase 1 schema gate 的描述（路径不变，bound 数字以 schema 为权威，doc 不复述具体数字）
- 不改 orchestrator.run_analysis 代码（schema 文件路径不变，validator lru_cache 自动加载新版 schema）
- 不动 todo_list（无新 todo / 无完成项）

## 验证标准

- [ ] 3 个 schema 跑 `Draft202012Validator.check_schema` 全 OK
- [ ] mock data：构造一个 valid 样本（按新 bound）+ 一个 invalid 样本（每 schema 各一处违反），分别返 0 errors / 非 0 errors
- [ ] `git grep key_events_expected` 在 schemas/ + automation/ + docs/ 范围内 = 0；仅 logs/ 历史保留
- [ ] `python -c "from automation.persona_extraction.orchestrator import _world_overview_validator, _stage_plan_validator, _candidate_characters_validator; [v() for v in [_world_overview_validator,_stage_plan_validator,_candidate_characters_validator]]"` 通（schema 加载无错）
- [ ] commit message 风格对齐 `git log --oneline -10`

## 执行偏差

无（计划清单全落实；5 文件 modified + 1 新 log）

<!-- POST 阶段填写 -->

## 已落地变更

- [schemas/analysis/world_overview.schema.json](schemas/analysis/world_overview.schema.json)：11 处 bound 收紧（tone 49 / world_structure.summary 100-200 / power_system.summary 100-200 / power_system.levels maxItems 19 / major_regions maxItems 29 + items 29 / major_factions maxItems 19 / major_factions.description 99 / world_lines maxItems 19 / world_lines.core_conflict 99 / world_lines.setting_features 99）
- [schemas/analysis/stage_plan.schema.json](schemas/analysis/stage_plan.schema.json)：stage_title maxLength 14；删除 `key_events_expected` 字段定义 + required 列表去除该项
- [schemas/analysis/candidate_characters.schema.json](schemas/analysis/candidate_characters.schema.json)：candidates maxItems 29；description minLength 100 + maxLength 200
- [automation/prompt_templates/analysis.md:114,138](automation/prompt_templates/analysis.md)：stage 字段表 + JSON 模板移除 `key_events_expected`
- [docs/architecture/schema_reference.md:58](docs/architecture/schema_reference.md)：stage_plan 关键字段段移除 `key_events_expected[]`

## 与计划的差异

无

## 验证结果

- [x] 3 个 schema `Draft202012Validator.check_schema` 全 OK
- [x] mock data 10 项全过：valid 样本 0 errors；invalid 样本各精准捕获 1+ 违反
  - world_overview summary 50 字 → "is too short"
  - world_overview world_lines 20 项 → array too big
  - stage_plan stage_title 16 字 → "is too long"
  - stage_plan 含 `key_events_expected` → "Additional properties are not allowed" （additionalProperties:false 配合字段移除自动拒绝）
  - candidate_characters description 5 字 → "is too short"
  - candidate_characters candidates 30 项 → array too big
- [x] `git grep key_events_expected -- ':!logs/'` = 0
- [x] 13 处新 bound 数字 grep 验证全到位（49 / 100 / 19 / 29 / 14 / 99）
- [x] `git grep '我和女帝' -- ':!logs/' ':!.git*'` = 0

## Completed

- **Status**: DONE
- **Finished**: 2026-04-26 21:19:37 EDT

<!-- /post-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：5/5 计划项 + 5/5 验证标准 = 100%
- Missed updates: 0 条

### 轨 2 — 影响扩散
- Findings: High=0 / Medium=0 / Low=1
- Low：analysis.md prompt 主文未显式告知新增 minLength 100 bound（仅在文件链接处提"以 schema 为准"），可能浪费一次 L3 retry token；建议下轮 prompt 改动时一并加"长度 100-200 字"括注，与 chunk schema prompt 风格统一
- Open Questions: 1 条（详见对话）

## 复查时状态
- **Reviewed**: 2026-04-26 22:35 EDT
- **Status**: REVIEWED-PASS
  - 理由：轨 1 全落实，轨 2 仅 1 条 Low（prompt token 效率优化），无 High / Medium
- **Conversation ref**: 同会话内 /post-check 输出
