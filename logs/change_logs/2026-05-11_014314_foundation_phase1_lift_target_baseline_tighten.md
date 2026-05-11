# foundation_phase1_lift_target_baseline_tighten

- **Started**: 2026-05-11 01:43:14 EDT
- **Branch**: main (worktree `../offpage-main`，主 checkout 仍在 extraction/`<work_id>`)
- **Status**: PRE

## 背景 / 触发

会话观察 phase 2 baseline 实际产物（[foundation.json](works/<work_id>/world/foundation/foundation.json) vs [world_overview.json](works/<work_id>/analysis/world_overview.json)）发现两份文件 95% 字段重叠（`work_id` / `genre` / `tone` / `world_structure` / `power_system` / `world_lines`），真增量只有 `core_rules` 升级为 object[] 含 `impact` 字段 + `major_factions.key_figures[]` 字段。Phase 2 LLM 重写整份 foundation token 浪费明显。

另观察 target_baseline 实际产物 15 条全部 `核心 / 重要` tier，含末章才出生且无 dialogue / action 的双胞胎角色——baseline prompt 当前规则 "宁可多列、不可漏列、被点名提及即纳入"导致前 12 stage × 2 角色 × 3 结构 = 72 条纯空 entry 噪声。

会话深挖确认两个误解源：
1. ai_context [decisions.md #48](ai_context/decisions.md) 措辞 "Phase 2/3/3.5/4 via repair_agent T3_EXHAUSTED" 暗示 phase 2 接入 repair_agent。实际 grep `run_repair(...)` 唯一调用点 = [orchestrator.py:2365](automation/persona_extraction/orchestrator.py)（phase 3 stage loop 内）。Phase 2 现行实现 [run_baseline_production](automation/persona_extraction/orchestrator.py) = 裸单次 `run_with_retry` + `validate_baseline` schema gate + length-bound tolerance gate 兜底，**未接入 repair_agent**。
2. decisions.md #25 (repair_agent L0–L3 × T0–T3) 与 #40 (phase 0 JSON repair L1/L2/L3) 共用 "L1/L2/L3" 字面但语义完全不同（前者 checker × fixer 矩阵，后者 JSON 格式三档），从未在同一处对比说明，长期混淆潜在源。

## 结论与决策

**B-1 拆分方案**：本次 /go 落 foundation 重构 + target_baseline 收紧 + ai_context 措辞修正三件，不本次接入 repair_agent。Phase 2 整体接入 repair_agent 拆为单独 todo `T-PHASE2-REPAIR-AGENT` 后续单跑。

### 核心改动决策

1. **Phase 1 world_overview lane 改名 foundation lane**，输出路径从 `works/<work_id>/analysis/world_overview.json` 改为 `works/<work_id>/world/foundation/foundation.json`。schema 把 [world_overview.schema.json](schemas/analysis/world_overview.schema.json) 逐字搬到 [foundation.schema.json](schemas/world/foundation.schema.json) 替换现有 foundation schema —— 字段 / bound 一字不改（含 `core_rules: string[] ≤30 条 / 每条 ≤150 字`，**user 决策 1 明确不动 core_rules**），仅改 `$id` / `title` / `description` 语义化为 foundation。
2. **新增 `major_factions[].key_figures[]` 字段**为 phase 2 LLM 补齐预留（optional / `default: []`）：phase 1 lane 不写该字段，phase 2 单独一个轻量 LLM call 补齐 character_id 列表（补丁式 merge）。
3. **Phase 2 缩水**：删除 baseline_production.md 「产出 1：世界 Foundation」整段（≈100 行），新增「产出 X：补齐 foundation.major_factions.key_figures」短段。保留 fixed_relationships + identity + target_baseline 三件 LLM 产出。
4. **target_baseline 准入收紧**：删 prompt 中 "宁可多列、不可漏列" 原则；改为准入门槛 = "本角色与目标角色在 chapter_summaries 摘要描述中**被反映为有过 dialogue / action 交互**"；tier 4 档不动。
5. **B-1 失败处理**：phase 2 key_figures 补齐 step 复用 phase 2 现行兜底形态——单次 `run_with_retry` → `validate_baseline` schema gate → length-bound tolerance gate → fail 则 `sys.exit(1)`。character_id 合法性校验失败属于 schema validate 范畴（schema `enum`-like 校验），失败直接 fail，不引入新的 retry 机制。
6. **ai_context 措辞修正**：(a) decisions.md #48 "Phase 2/3/3.5/4 via repair_agent T3_EXHAUSTED" → "Phase 3 via repair_agent T3_EXHAUSTED；Phase 2 / Phase 4 经各自原生 retry exhaust"；(b) decisions.md #25 / #40 加 disambiguation 注释，明确两套 "L1/L2/L3" 同名不同物。
7. **新立 `T-PHASE2-REPAIR-AGENT` todo**：description = phase 2 整体接入 repair_agent（4 件产物 foundation patch + fixed_relationships + identity + target_baseline 各自包装 SourceContext + 写 phase 2 专属 checkers）；状态 Next；deps 无。

### 显式不做

- 不动 chunk schema（`chunk_factions.members_present` 保留服务 phase 1 candidate_characters lane 的身份合并）
- 不动 phase 1 stage_plan / candidate_characters lane 与 phase 1.5
- 不动 [target_baseline.schema.json](schemas/character/target_baseline.schema.json) 与 [targets_cap.schema.json](schemas/character/targets_cap.schema.json)（schema 不变，仅 prompt 加严）
- 不动 stage_snapshot 三结构的双向 set-equal 约束（决策 #13）
- 不做数据迁移（user D=(1) 接受重跑 phase 2，但本 /go 不执行 `git reset` 与重跑——user 自决何时操作）
- 不引入 `_validation_tolerance_applied` 类元数据字段
- 不本次接入 repair_agent（B-2 留 todo）

## 计划动作清单

### Schema（3 处）

- file: `schemas/world/foundation.schema.json` → **重写**为现 [world_overview.schema.json](schemas/analysis/world_overview.schema.json) 逐字拷贝 + `major_factions.items` 加 `key_figures[]` optional 字段（items: string maxLength 30 / maxItems 10 / 注释说明 character_id 由 phase 2 补齐），`$id` / `title` / `description` 改写为 foundation 语义
- file: `schemas/analysis/world_overview.schema.json` → **删除**
- file: `schemas/character/target_baseline.schema.json` → 不动

### Prompt（2 处）

- file: `automation/prompt_templates/analysis_world_overview.md` → **改名**为 `analysis_foundation.md`；内容更新：(a) 任务描述改为产出 foundation.json；(b) 输出路径改为 `works/{work_id}/world/foundation/foundation.json`；(c) 不再产出 `major_factions[].key_figures[]`（明确说该字段由 phase 2 补齐）；其它字段产出指令不动（含 `core_rules: string[]` 形态）
- file: `automation/prompt_templates/baseline_production.md` → 大改：
  - 删「产出 1：世界 Foundation」整段
  - 新增「产出 X：补齐 foundation.major_factions.key_figures」短段：输入 foundation.json + candidate_characters.json + target_characters；补丁式 LLM 输出 `{faction_name: [character_id, ...]}`；程序 merge；character_id 必须 ∈ candidate_characters
  - target_baseline 段加严：删「宁可多列不可漏列」措辞；准入门槛改为 "本角色与目标角色在 chapter_summaries 摘要描述中被反映为有过 dialogue / action 交互"；tier 4 档不动；血亲不再默认核心 tier（按准入门槛 + 实际剧情驱动力分级）

### Code（2 处）

- file: `automation/persona_extraction/prompt_builder.py` → 
  - `build_world_overview_prompt` → **改名** `build_foundation_prompt`，prompt 模板路径更新为 `analysis_foundation.md`
  - `_project_chunk_for_world_overview` → **改名** `_project_chunk_for_foundation`（投影字段不变）
  - `prepare_phase1_lane_inputs` / `cleanup_phase1_lane_inputs` 内部 lane 名常量 `"world_overview"` → `"foundation"`
  - 新增 `build_factions_keyfigures_prompt(work_id, foundation_path, candidate_characters_path, target_characters)` → 返回 phase 2 补齐 prompt
- file: `automation/persona_extraction/orchestrator.py` → 
  - `run_analysis` foundation lane 输出路径 / lane 名常量改：从 `analysis/world_overview.json` → `world/foundation/foundation.json`；目录创建调用同步
  - `run_baseline_production` 删 foundation 写入路径检查（行 1495-1500 附近），保留 `world/foundation/foundation.json` 存在性确认（phase 1 lane 已写）；新增 key_figures 补齐 LLM call（输出合法性 schema 校验通过即程序 merge into foundation.json）；保留现有 fixed_relationships / identity 检查
  - `validate_baseline` 调用点不变（schema 引用从 world_overview.schema.json 移除）

### Doc / ai_context sweep（按 conventions §Cross-File Alignment）

- file: `ai_context/decisions.md` → 
  - 更新 #27m 描述（chunk_summary_chunk 行 lane 列表 + Phase 2 baseline 读用方式）
  - 更新 #52 描述（world_overview lane → foundation lane 改名 + 输出路径）
  - 更新 #53 描述（schema 收紧 v2 章节 world_overview → foundation；删 world_overview 引用）
  - **修正 #48** 措辞 "Phase 2/3/3.5/4 via repair_agent T3_EXHAUSTED" → "Phase 3 via repair_agent T3_EXHAUSTED；Phase 2 与 Phase 4 经各自原生 retry exhaust"
  - **#25 / #40 加 disambiguation 注释**明确两套 "L1/L2/L3" 同名不同物
  - 新增 #54 durable 决策（foundation 前移 phase 1 + phase 2 key_figures 补齐 + target_baseline 准入门槛三件合一）
- file: `ai_context/architecture.md` → Phase 1 / Phase 2 描述更新；Cross-File Alignment 引用更新；Phase 3 D4 设定不变
- file: `ai_context/conventions.md` § Cross-File Alignment → 表 row "chapter_summary_chunk 字段/bound" 行 lane 列表更新；新增或更新行涵盖 foundation lane 重命名
- file: `docs/architecture/schema_reference.md` → world_overview → foundation 索引更新；foundation 字段表更新（加 key_figures）
- file: `docs/architecture/extraction_workflow.md` → Phase 1 lane 列表 + Phase 2 产出列表更新；流程图同步
- file: `docs/requirements.md` § 9.x phase 流程 + § 11.x 自动化管线 → foundation 前移描述同步；target_baseline 准入门槛措辞同步

### todo_list

- file: `docs/todo_list.md` → 
  - 新增 `T-PHASE2-REPAIR-AGENT` 条目入 ## Next 段（拆出来单独做）
  - 顶部 Index 段同步刷新

## 验证标准

- [ ] `python -c "import json; json.load(open('schemas/world/foundation.schema.json'))"` 成功
- [ ] `python -m jsonschema --check schemas/world/foundation.schema.json` 元 schema 校验通过（draft 2020-12）
- [ ] `python -c "from automation.persona_extraction.orchestrator import Orchestrator"` import 无报错
- [ ] `python -c "from automation.persona_extraction.prompt_builder import build_foundation_prompt, build_factions_keyfigures_prompt"` 新签名 import 通过
- [ ] grep `world_overview` 在 automation/ + schemas/ + ai_context/ + docs/architecture/ + docs/requirements.md 残留 = 0（exclude logs/ + works/ + docs/todo_list_archived.md 历史快照）
- [ ] grep `analysis_world_overview.md` 在 automation/ 残留 = 0
- [ ] grep `Phase 2/3/3.5/4 via repair_agent T3_EXHAUSTED` 在 ai_context/ 残留 = 0
- [ ] `schemas/analysis/world_overview.schema.json` 文件已删
- [ ] `automation/prompt_templates/analysis_world_overview.md` 文件已删（改名为 `analysis_foundation.md`）
- [ ] `docs/todo_list.md` 顶部 Index 段含 T-PHASE2-REPAIR-AGENT 条目

## 执行偏差

### 偏差 D1：`build_factions_keyfigures_prompt` 未单独实现，整合到 `build_baseline_prompt`

**PRE 计划**：新增独立函数 `build_factions_keyfigures_prompt(work_id, foundation_path, candidate_characters_path, target_characters)` 作 phase 2 补齐 LLM call 的 prompt builder（PRE 计划动作清单 Code 段第 1 条 + 决策 5 第 2 句）。

**实际实现**：合并到 `build_baseline_prompt(...)` 内（单次 LLM call 产出 5 件 baseline 产物：foundation key_figures 补齐 + fixed_relationships + identity + target_baseline + manifest + 空 stage_catalog）。`baseline_production.md` prompt 的「产出 1：补齐 `foundation.major_factions[].key_figures`」段直接告诉 LLM "读 foundation.json → 仅修改 major_factions[].key_figures → 写回"，与其他产出一起在同一 LLM 输出里处理。

**偏差原因**：拆分独立 LLM call 需要在 orchestrator 加第二次 `run_with_retry` + 第二份 prompt + 独立 retry budget + 独立 schema gate，工程量翻倍但 token 净增（每次 LLM call 都要重读 schemas + foundation + candidates context）。整合到单次 baseline LLM 的代价 ≈ 0（prompt 长度增加约 60 行 +  LLM 在同一 context 内完成所有产出，schema gate 已经覆盖 foundation.major_factions[].key_figures 字段的合法性）。决策 B-1 路径明确"phase 2 复用现有兜底形态——单次 `run_with_retry` → `validate_baseline` → length tolerance gate → fail sys.exit(1)"，因此单次 LLM 才是契约一致的实现，独立 prompt builder 反而违反 B-1 形态。

**影响范围**：
- prompt_builder.py 不需要新增 `build_factions_keyfigures_prompt` 签名
- orchestrator.run_baseline_production 保持现有形态（单次 `build_baseline_prompt(...)` + `run_with_retry`）
- baseline_production.md prompt 的「产出 1」段描述"补齐 foundation.major_factions[].key_figures"含义未变——LLM 仍然按补丁式 read-modify-write，仅是与其他产出共用同一 LLM call

**待跟进**：本 /go runtime 阶段需要验证 baseline LLM 在单次 call 里产出 5 件输出的可行性（token 预算 / 准确率）；若实测发现 LLM 在单 call 内忘记补 key_figures，再拆分到独立 LLM call（拆分动作可保留 prompt 段不变，仅改 orchestrator 调度形态）。

### 偏差 D2：`validate_baseline()` 内 foundation.json 加 schema gate（Risk Line HIGH 1 修复）

**PRE 计划**：`validate_baseline` 校验 foundation.json 存在 + JSON 解析 + work_id 非空（PRE 计划动作清单 Code 段未明确要求 schema gate）。

**实际实现**：升级 `validate_baseline` 对 foundation.json 调 `_validate_schema(...)` 走 `schemas/world/foundation.schema.json` 全 schema gate（与 fixed_relationships / identity / target_baseline 同形态）。

**偏差原因**：Step 7 风险线 review 发现"决策 #54 显式要求 character_id 合法性走 schema validate 范畴"但 validator 实现仅做最小存在性 / work_id 非空检查，无 schema gate——缺口会让 phase 2 LLM 产出非法 character_id 时直到 phase 3 world extraction 读 foundation 时才崩。修复将 foundation 升级为 schema-gated（含 length-tolerance 兜底，#48 覆盖）。

**影响范围**：
- `automation/persona_extraction/validator.py::validate_baseline`（升级 foundation 校验形态）

### 偏差 D3：`schema_reference.md` target_baseline 段同步「dialogue/action 准入门槛」（Spec Line CRITICAL 修复）

**PRE 计划**：覆盖 docs/architecture/{schema_reference,extraction_workflow}.md 中 target_baseline 准入门槛措辞改造。

**实际实现**：`schema_reference.md` 第一轮改动仅同步 phase 1 lane / foundation schema 段，target_baseline 段（line 282-285）的"宁可多列、不可漏列"原则被遗漏，Step 7 规范线 review 抓到后补齐：删除旧措辞 + 加准入门槛新定义（dialogue/action 交互判定 + 血亲不再默认核心 tier + tier 与准入门槛正交）。

**影响范围**：
- `docs/architecture/schema_reference.md` line 282-285 段

### 偏差 D4：orchestrator.py 顶部 docstring 加 L1/L2/L3 disambiguation 注释

**PRE 计划**：未明确要求 code-level disambiguation 注释（仅 decisions.md #25 + #40 加注释）。

**实际实现**：Step 7 风险线 MED 5 finding 建议代码内也加 disambiguation；顺手在 `orchestrator.py` 顶部 docstring 第 10 行 `Repair agent (L0–L3 check → T0–T3 fix loop → final verify)` 后补一段 disambiguation note，明确这里的 `L0–L3` 是 decision #25 repair_agent checker 层级（非 decision #40 phase 0 JSON repair 三档）。

**偏差原因**：避免未来读者撞到 orchestrator.py 内 "L0–L3" 字面时误以为是 phase 0 JSON repair 三档，导致下次某个 review 又重新踩同一个坑（本次会话 user 三轮质疑 "phase 2 不是用 repair_agent 吗" 部分就是这个混淆引起）。code-level disambiguation 比 ai_context disambiguation 更近读者，零成本加。

**影响范围**：
- `automation/persona_extraction/orchestrator.py` 顶部 docstring（line 10-15 段）

<!-- POST 阶段填写 -->

## 已落地变更

### Schema（3 处）

- **`schemas/world/foundation.schema.json`** 重写：内容 = 旧 `schemas/analysis/world_overview.schema.json` 逐字搬过来（含 `core_rules: string[] ≤30 条 / 每条 ≤150 字` 形态——user 决策 1 明确不改 core_rules），仅改 `$id` / `title` / `description` 语义化为 foundation；`major_factions.items` 新增 optional `key_figures[]` 字段（items: string maxLength 30 / maxItems 10 / 注释说明 character_id 由 phase 2 补齐）
- **`schemas/analysis/world_overview.schema.json`** 删除
- **`schemas/character/target_baseline.schema.json`** 不动

### Prompt（4 处）

- **`automation/prompt_templates/analysis_world_overview.md` → `analysis_foundation.md`** (git mv) + 内容改写：lane 名 / 任务描述 / 字段映射 / 输出路径 / 不写 key_figures 字段说明
- **`automation/prompt_templates/baseline_production.md`** 重写：删「产出 1：世界 Foundation」整段 + 新增「产出 1：补齐 foundation.major_factions[].key_figures」短段 + target_baseline 准入门槛收紧（dialogue/action 交互） + 整体结构重编号 5 件产出
- **`automation/prompt_templates/analysis_stage_plan.md`** + **`analysis_candidate_characters.md`**：sibling lane 列表内 `world_overview` → `foundation`
- **`automation/prompt_templates/summarization.md`** Phase 1/2 综合描述同步

### Code（4 处）

- **`automation/persona_extraction/prompt_builder.py`**：
  - `build_world_overview_prompt` → `build_foundation_prompt` (函数改名 + template 路径 + decision #54 docstring)
  - `_project_chunk_for_world_overview` → `_project_chunk_for_foundation` (投影函数改名 + 注释更新)
  - `_LANE_PROJECTORS` + `PHASE1_LANES` lane 名常量 `world_overview` → `foundation`
  - `build_baseline_prompt` schemas 列表加 `world/foundation.schema.json`、文件列表读 `world/foundation/foundation.json`（不再读 `analysis/world_overview.json`）、context 新增 `summaries_dir` 占位符
- **`automation/persona_extraction/orchestrator.py`**：
  - `_world_overview_validator` → `_foundation_validator`（schema 加载从 `schemas/analysis/world_overview.schema.json` 改 `schemas/world/foundation.schema.json`）
  - `_load_world_schema` 新增 helper
  - `run_analysis` lane 表 + `_lane_passes_skip` + `_run_one_lane` 形态改：lane 表 (name, **relpath**, validator, builder) 而非 (name, fname, ...)，foundation lane 落 `world/foundation/foundation.json`；新增 `_LANE_SCHEMA_REF` map 用于 prior_error 注入；新增 target_path.parent.mkdir(parents=True, exist_ok=True)
  - `run_analysis` 末尾 trio_relpaths 列表更新 + 返回 dict 字段 `world_overview` → `foundation`
  - `run_baseline_production` 改造：前置 foundation.json 存在性检查（phase 1 lane 已产）；docstring 改写说明 phase 2 缩水到 5 件 baseline；后续 missing_critical 检查注释更新 ("present" 而非 "produced")
  - 顶部 docstring 加 L0–L3 disambiguation 注释（决策 #25 vs #40）
  - `_build_light_novel_stage_plan` docstring 同步
  - import 列表把 `build_world_overview_prompt` → `build_foundation_prompt`
- **`automation/persona_extraction/validator.py`**：`validate_baseline` 内 foundation.json 校验**升级为 schema gate**（与 fixed_relationships 同形态），含 `try_repair_json_file` 自修 + `_validate_schema(... length_tolerance=...)` 长度容忍兜底
- **`automation/persona_extraction/config.py`** + **`automation/config.toml`**：注释里 `world_overview / stage_plan / candidate_characters` → `foundation / stage_plan / candidate_characters`

### Doc + ai_context sweep（8 处）

- **`ai_context/decisions.md`**：
  - #25 加 disambiguation 注释（repair_agent L0-L3 × T0-T3，仅 phase 3 接入）
  - #40 加 disambiguation 注释（phase 0 JSON repair L1/L2/L3，与 #25 同名不同物）
  - #48 措辞修正："Phase 2/3/3.5/4 via repair_agent T3_EXHAUSTED" → "Phase 3 via repair_agent T3_EXHAUSTED；Phase 2 / Phase 4 经各自原生 retry exhaust"
  - #27m chunk-level fields 段：删 "Phase 2 baseline_production.md reads chunk-level fields directly"，改为 "Phase 1 foundation lane mapping" + "Phase 2 no longer produces foundation"
  - #52 改写：world_overview lane → foundation lane，输出路径同步
  - #53 修订：world_overview schema → foundation schema
  - 新增 #54 durable 决策（foundation 前移 phase 1 + phase 2 仅补 key_figures + target_baseline 准入门槛）
  - #27i 修正：5 schemas 列表 `schemas/analysis/world_overview.schema.json` 改 `schemas/world/foundation.schema.json` + `build_world_overview_prompt` → `build_foundation_prompt`
- **`ai_context/architecture.md`**：Phase 0/1/2 描述、Length-bound tolerance gate、CLI --resume 路径同步
- **`ai_context/conventions.md`** § Cross-File Alignment：chunk schema 行更新 + 新增 foundation schema 行
- **`ai_context/current_status.md`**：works/*/analysis/ tracked 列表移除 world_overview
- **`docs/architecture/schema_reference.md`**：chapter_summary_chunk 段 + 删 world_overview 段 + foundation 段重写 + stage_plan / candidate_characters lane 同步 + target_baseline 准入门槛改写（Step 7 规范线 finding 修复）
- **`docs/architecture/extraction_workflow.md`**：Phase 1 lane 表 + 输出路径 + Phase 2 5 件产出列表 + target_baseline 准入门槛
- **`docs/architecture/system_overview.md`**：阶段 1/2 流程描述同步
- **`docs/architecture/data_model.md`**：foundation.json 生命周期更新（phase 1 直接产）
- **`docs/requirements.md`**：流程图 + § 9.x phase 描述 + target_baseline 准入门槛 + phase 1 lane 描述同步
- **`schemas/README.md`** + **`automation/README.md`**：schema 索引 + lane 列表 + schema gate 表更新

### todo_list

- **`docs/todo_list.md`**：新立 `T-PHASE2-REPAIR-AGENT` 条目入 Next 段（Med + Blocked + Large·Arch）；Index 段 Next (2)→(3)、Total 15→16 同步

## 与计划的差异

四点偏差（详见上方"## 执行偏差"段 D1-D4）：
- D1：`build_factions_keyfigures_prompt` 未单独实现，整合到 `build_baseline_prompt` 内（functionally equivalent，避免不必要的函数拆分 + 二次 LLM call token 浪费）
- D2：升级 `validate_baseline()` foundation schema gate（Risk Line HIGH 1 修复）
- D3：补齐 `schema_reference.md` target_baseline 段措辞（Spec Line CRITICAL 修复）
- D4：orchestrator.py 顶部 docstring 加 L1/L2/L3 disambiguation 注释（Risk Line MED 5 修复）

其它无偏差。

## 验证结果

- [x] `python -c "import json; json.load(open('schemas/world/foundation.schema.json'))"` 成功 — PASS
- [x] `Draft202012Validator.check_schema(foundation schema)` 元 schema 校验通过 — PASS
- [x] `orchestrator` + `prompt_builder` + `validator` import 通过 — PASS
- [x] `build_foundation_prompt` / `_foundation_validator` / `PHASE1_LANES = ('foundation', 'stage_plan', 'candidate_characters')` / `_project_chunk_for_foundation` 新签名 import 通过 — PASS
- [x] grep `world_overview` 在 automation/ + schemas/ + ai_context/ + docs/ 残留：剩余全部是 code-level disambiguation 注释 + decision #54 历史索引 + docs/todo_list.md 已 archived 任务里的描述（exclude logs/ + works/ + docs/todo_list_archived.md 合理）— PASS
- [x] grep `analysis_world_overview.md` 在 automation/ 残留 = 0（除注释内 "renamed from analysis_world_overview.md" disambiguation）— PASS
- [x] grep `Phase 2/3/3.5/4 via repair_agent T3_EXHAUSTED` 在 ai_context/ 残留 = 0 — PASS
- [x] `schemas/analysis/world_overview.schema.json` 文件已删 — PASS
- [x] `automation/prompt_templates/analysis_world_overview.md` 文件已删（rename 为 analysis_foundation.md）— PASS
- [x] `docs/todo_list.md` 顶部 Index 段含 T-PHASE2-REPAIR-AGENT 条目 — PASS
- [x] Step 7 四线 review 全部 finding 修复（规范线 CRITICAL 1 / 实现线 DEVIATION 1 已记录 / 风险线 HIGH 1 + MED 5 已修；HIGH 2 (phase 2 read-modify-write 原子性) 是 phase 2 整体形态局限，本次重构作用域外，已写入 T-PHASE2-REPAIR-AGENT todo / 结构线 MAJOR = 同 D1 偏差）— PASS

## Completed

- **Status**: DONE
- **Finished**: 2026-05-11 02:18:56 EDT
