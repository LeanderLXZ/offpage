# key_figures_semantic_phase1_raw_phase2_replace

- **Started**: 2026-05-11 05:05:27 EDT
- **Branch**: main (worktree `../offpage-main`，主 checkout 仍在 extraction/`<work_id>`)
- **Status**: PRE

## 背景 / 触发

上一轮 phase 1+2 重抽（commit `9ca104f`）按决策 #54 原始设计实施：phase 1 foundation lane **不写** `major_factions[].key_figures`，phase 2 baseline LLM 单独补齐为 character_id 列表。

user 端到端跑完后指出 2 个设计修正：
1. **Phase 1 foundation lane 应该写 key_figures**——但内容不是 character_id，而是 chunk-LLM 看到的 raw 名（化名 / 真名 / 称呼任一，跨 chunk 合并去重）。这样 phase 1 阶段不损失势力关键人物信息——chunk_factions[].members_present[] 内的 raw 名直接搬到 key_figures。
2. **Phase 2 baseline LLM 的工作改为"替换"**——读 phase 1 落盘 foundation.json + candidate_characters.json + 已确认目标清单，对每个 key_figures raw 名 lookup `candidates.aliases`：能匹配上对应 character_id 就**替换**为 character_id；匹配不上保留 raw 名（不报错、不删除）。

最终 key_figures 是 **character_id + 未合并 raw 名混合**，runtime 加载时 character_id 部分可绑定到角色包，raw 名部分作为字符串显示提示。

User 决策：phase 2 用 **A 方案 LLM 替换**（与现有 baseline_prompt 单次 call 一致；几乎零成本——LLM context 已含 foundation + candidate_characters；LLM 能处理 alias 没覆盖到的 fuzzy 匹配如"那位长老"等口语化）。

## 结论与决策

### 核心改动

1. **`schemas/world/foundation.schema.json`** `major_factions[].key_figures.items.description` 改写——明确 key_figures 是 character_id + raw 名混合：phase 1 foundation lane 写 raw 名（chunk_factions[].members_present[] 跨 chunk 合并去重，含化名 / 真名 / 称呼），phase 2 baseline LLM 替换能匹配 candidate_characters.aliases 的 raw 名为 character_id，匹配不上保留 raw 名。schema bound 不动（maxLength 30 / maxItems 10，chunk LLM 跨 chunk 去重后 ≤10 raw 名 / 势力是合理预期；中文化名 ≤30 字也合理）。

2. **`automation/prompt_templates/analysis_foundation.md`** 改"不要写 key_figures" → "用 `chunk_factions[].members_present[]` 跨 chunk 合并去重产出 key_figures（raw 名直接写，不做身份合并；身份合并交给 phase 2 baseline LLM）"。

3. **`automation/persona_extraction/prompt_builder.py`** `_project_chunk_for_foundation` 投影函数恢复 `chunk_factions[].members_present` 字段（上一轮重构去除了，现在 foundation lane 需要它产 key_figures，得恢复）。`_LANE_PROJECTORS` 注释更新。

4. **`automation/prompt_templates/baseline_production.md`** 「产出 1: 补齐 key_figures」整段改写为「产出 1: 替换 `foundation.major_factions[].key_figures` 内 raw 名为 character_id」语义：
   - 输入：phase 1 落盘 foundation.json（含 key_figures raw 名）+ candidate_characters.json（含 character_id + aliases，aliases 内每条 `{name, type}`）+ 已确认目标清单
   - 替换规则：对每个 raw 名遍历 `candidates[*].aliases[*].name`，命中则换该 candidate 的 character_id；未命中保留 raw 名不动
   - 不报错、不删除——LLM 不能匹配的 raw 名作为字符串保留，runtime 加载时按字符串显示
   - 与 fixed_relationships / identity / target_baseline / manifest / stage_catalog 同一次 LLM call 完成

5. **`automation/persona_extraction/validator.py`** validate_baseline 对 foundation 仍走 schema gate（无变化）——schema 已允许 key_figures 内任意字符串（无 enum 硬卡），混合内容合法。

### 显式不做

- 不修改 schema `key_figures` 的 maxItems / maxLength bound（runtime 验证后再调）
- 不引入程序化身份合并步骤（user 选 A LLM 替换）
- 不动 phase 1.5 流程 + decisions.md 内 #13 双向 set-equal 约束 + #27i schema-gate-as-retry-trigger
- 不本次接 phase 2 进 repair_agent（拆 T-PHASE2-REPAIR-AGENT todo）

### 任务 B：extraction 分支清空 phase 1+2 产物

新 phase 1 foundation lane 产出形态变（含 key_figures raw 名），旧 commit `9ca104f` 内 foundation.json 已落空 key_figures——user 重跑 phase 1 + phase 2 才能产新形态。任务 B 在 extraction 分支单独 commit。

清空清单：
- `works/<work_id>/world/foundation/foundation.json`（旧形态，key_figures 是 character_id-only 不含 raw 名）
- `works/<work_id>/world/foundation/fixed_relationships.json`（phase 2 产物）
- `works/<work_id>/world/manifest.json`
- `works/<work_id>/world/stage_catalog.json`
- `works/<work_id>/characters/{Character A,Character B}/{manifest.json + canon/{identity,target_baseline,stage_catalog}.json}`

保留：
- `works/<work_id>/manifest.json`（phase 1.5）
- `works/<work_id>/analysis/chapter_summaries/` + `stage_plan.json` + `candidate_characters.json` + `progress/{pipeline,phase0_summaries}.json`

注：phase 1 stage_plan + candidate_characters lane 产物 schema 不变，**可以保留不重跑**（重新跑 phase 1 时 `_lane_passes_skip` schema-valid 检测会自动跳过）。仅 foundation lane 重跑。

pipeline.json local 回滚 phase_1 done → pending（gitignored 不入 commit）；phase_2 已是 done 状态也回 pending（让 phase 2 重跑产新 baseline）。

## 计划动作清单

### 任务 A — schema / prompt / code（main 端）

- file: `schemas/world/foundation.schema.json` → `major_factions.items.key_figures.items.description` 改写：character_id + raw 名混合契约
- file: `automation/prompt_templates/analysis_foundation.md` → 改"不要写 key_figures" → "写 key_figures（raw 名）"段；改写「不要写 `major_factions[].key_figures` 字段」末段为"必须写 key_figures 用 chunk_factions[].members_present[] 跨 chunk 合并去重"
- file: `automation/persona_extraction/prompt_builder.py` → `_project_chunk_for_foundation` 恢复 chunk_factions[].members_present 字段透传；module 顶部注释 + 函数 docstring 同步
- file: `automation/prompt_templates/baseline_production.md` → 「产出 1」整段重写为"替换 raw 名 → character_id"语义；输入 / 规则 / fallback 全列
- file: `ai_context/decisions.md` → 修订 #54 第 (2) 项（phase 2 缩水）+ 新增 #54 末段说明 key_figures 双阶段语义；修订 #27m chunk-level fields 段（chunk_factions.members_present 喂给 foundation lane + candidate_characters lane 双 lane）
- file: `ai_context/architecture.md` → Phase 1 / Phase 2 描述同步双阶段语义
- file: `docs/architecture/schema_reference.md` → foundation `key_figures` 字段说明更新
- file: `docs/architecture/extraction_workflow.md` → Phase 1 foundation lane 输入投影 + Phase 2 替换流程同步
- file: `logs/change_logs/2026-05-11_050527_key_figures_semantic_phase1_raw_phase2_replace.md` → 本 log

### 任务 B — extraction 分支清空（commit 在 extraction 端）

worktree 退出 + 切回 extraction 后执行 `git rm` 13 个 tracked file + 改 pipeline.json local 状态回滚，单独 commit。

## 验证标准

### 任务 A
- [ ] `python -c "import json; json.load(open('schemas/world/foundation.schema.json'))"` 成功
- [ ] `python -m jsonschema --check schemas/world/foundation.schema.json` 元 schema 校验通过
- [ ] `python -c "from automation.persona_extraction.prompt_builder import _project_chunk_for_foundation; print(_project_chunk_for_foundation({'chunk_factions': [{'name': 'F', 'description': 'd', 'members_present': ['raw_a']}]}))"` 输出含 members_present
- [ ] `python -c "from automation.persona_extraction import orchestrator, validator, consistency_checker"` import 无报错
- [ ] grep `不要写 key_figures\|不要\s*写\s*major_factions\[\]\.key_figures` 在 `automation/prompt_templates/analysis_foundation.md` 残留 = 0
- [ ] grep `读 foundation.json → 仅修改 major_factions` 在 `automation/prompt_templates/baseline_production.md` 残留 = 0（旧 PRE-Plumbing "补齐"语义不应留）

### 任务 B
- [ ] `ls works/<work_id>/world/foundation/` 不存在
- [ ] `ls works/<work_id>/characters/*/canon/identity.json` 不存在
- [ ] `ls works/<work_id>/analysis/stage_plan.json` + `candidate_characters.json` 仍存在（保留）
- [ ] `git status` 干净（commit 后）

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

### 任务 A — schema / prompt / code / ai_context / docs（main 端，7 文件 + 1 log）

- **`schemas/world/foundation.schema.json`** `major_factions.items.properties.key_figures.description` 重写：character_id + raw 名混合双阶段填充语义（phase 1 写 raw 名 / phase 2 LLM 替换；schema 不抓 character_id 合法性）。bound 不动（maxLength 30 / maxItems 10）
- **`automation/prompt_templates/analysis_foundation.md`** 大改：
  - 文件顶部 lead-in 改为"phase 1 lane 写 raw 名 / phase 2 LLM 替换 character_id"（旧 "本 lane 不写该字段" 删除）
  - 输入段 `chunk_factions[]` 加 `members_present` 字段说明（chunk-LLM 视野下的 raw 名）
  - 步骤 1 + 步骤 2 字段映射加 key_figures 产出指令（chunk_factions[].members_present[] 跨 chunk 合并去重直接写入，不做身份合并）
  - JSON 结构示例加 `"key_figures": ["raw_name_1", "raw_name_2"]`
  - 规则段 "不要写 key_figures" → "必须写 key_figures"，含触顶 10 项的裁剪规则
- **`automation/persona_extraction/prompt_builder.py`**:
  - module 顶部注释 (line 117-130) 改写：foundation lane chunk_factions **INCLUDING** members_present
  - `_project_chunk_for_foundation` 函数体改写：恢复透传 `members_present`（之前 strip 掉），docstring 同步双阶段语义
- **`automation/prompt_templates/baseline_production.md`** 「产出 1」整段重写为"替换"语义（≈40 行）：
  - 输入契约改：foundation.json 含 raw 名 key_figures + candidate_characters 含 character_id + aliases + 目标清单
  - 替换规则：对每个 raw 名 lookup `candidates[*].aliases[*].name`，命中换 character_id，未命中保留 raw 名；不报错 / 不删除 / 不新增
  - Fuzzy 匹配建议段（LLM 优势区——化名 / 真名 / 称呼 / 称号匹配；谨慎宁可保留也不要错配）
  - 失败处理：key_figures 字符串数组无 enum 硬卡，任何字符串合法 → schema 不抓 character_id 合法性
- **`ai_context/decisions.md`**:
  - #27m chunk-level fields 段（line 280-300）：foundation lane mapping 加 key_figures 双阶段说明；`members_present` 段从"intentionally not mapped 1:1"改为"double-pipe to key_figures"
  - #52 段 (line 384)：foundation lane chunk 输入字段裁剪段加 "**含 `members_present`**——决策 #54 修订段，foundation lane 写 `key_figures` raw 名直接来自 chunk_factions[].members_present[] 跨 chunk 合并去重"
  - #54 段 (line 388 附近)：(1) 段改"phase 1 lane 不写"为"phase 1 lane 写 raw 名"；(2) 段改"phase 2 缩水到只补 key_figures"为"phase 2 LLM 替换 raw 名 → character_id"，含 fallback 描述
- **`ai_context/architecture.md`** Phase 1 + Phase 2 描述段：key_figures 双阶段语义同步（phase 1 写 raw 名 / phase 2 LLM 替换）
- **`docs/architecture/schema_reference.md`** foundation 段：关键字段 + 生命周期 + 生成时机三段重写双阶段语义
- **`docs/architecture/extraction_workflow.md`** Phase 1 lane 段 + Phase 2 baseline 产出列表：`foundation lane 不写 key_figures` → `foundation lane 写 raw 名 key_figures`；phase 2 "补齐 key_figures" → "替换 key_figures raw 名 → character_id"

### 任务 B — extraction 分支清空 phase 1+2 产物

任务 B 在 Step 10 后切回 extraction 分支单独 commit。

## 与计划的差异

无。

## 验证结果

### 任务 A
- [x] `python -c "import json; json.load(open('schemas/world/foundation.schema.json'))"` 成功 — PASS
- [x] Draft202012Validator.check_schema(foundation schema) — PASS
- [x] `_project_chunk_for_foundation` 透传 `chunk_factions[].members_present` — PASS
- [x] full import chain (orchestrator + validator + consistency_checker + prompt_builder) — PASS
- [x] grep "phase 1 lane 不写 key_figures / 由 phase 2 补齐 / 补丁式 {faction_name: [character_id, ...]}" 残留 = 0 — PASS
- [x] baseline_production.md "raw 名 / 替换 / 保留" 关键词 ≥ 3 处 — PASS（12 处）
- [x] analysis_foundation.md "key_figures / members_present" 关键词 ≥ 2 处 — PASS（8 处）
- [x] orchestrator `build_baseline_prompt` 仍单次调用形态（不新增 build_factions_keyfigures_prompt）— PASS（2 import/call）

### 任务 B
- 任务 B 验证在 Step 10 执行后由 user 端 `ls` 直接验证

## Completed

- **Status**: DONE（任务 A）+ Step 10 执行任务 B
- **Finished**: 2026-05-11 05:13:23 EDT
