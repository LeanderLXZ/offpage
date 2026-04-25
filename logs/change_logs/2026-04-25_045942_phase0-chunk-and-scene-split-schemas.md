# phase0-chunk-and-scene-split-schemas

- **Started**: 2026-04-25 04:59:42 EDT
- **Branch**: main（worktree `../offpage-main`，主 checkout 留在 `extraction/我和女帝的九世孽缘`，clean）
- **Status**: DONE
- **LOG**: `logs/change_logs/2026-04-25_045942_phase0-chunk-and-scene-split-schemas.md`

## 背景 / 触发

- 上一轮验证发现 **Phase 0 chunk** 没有正式 schema（前面 23 个 schema 里无 chunk / chapter_summary / key_events 关键字），结构契约只在 prompt `automation/prompt_templates/summarization.md` 里，破坏了 `decisions.md` #27b "Bounds-only-in-schema" 全局原则。Phase 4 的 **scene_split**（per-chapter LLM 中间产物）同样缺 schema。
- 用户给出明确的字段集 + bound：
  - **chunk per-summary entry**：required = `chapter` / `title` / `summary` / `key_events` / `characters_present` / `location` / `emotional_tone` / `identity_notes`；`potential_boundary` 与 `boundary_hint` 移除；summary 50–100 / key_events ≤5 项 + 每项 <50 / location <20 / emotional_tone <20 / identity_notes <50
  - **scene_split per-scene entry**：required = `scene_start_line` / `scene_end_line` / `time` / `location` / `characters_present` / `summary`；time <20 / location <20 / summary 50–100

## 结论与决策

**1. Schema 是 future contract，不强制迁移现有数据**

实测现有数据对新 bound 违反率：

| 字段 | 违反 | 备注 |
|---|---|---|
| chunk summary 50–100 | 144/537 (27%) | min 38, max 155 |
| chunk key_events ≤5 项 | 167/537 (31%) | max 9 |
| chunk identity_notes <50 | 28/537 | max 91 |
| chunk location <20 | 10/537 | max 24 |
| chunk 含 `potential_boundary`/`boundary_hint` | 537/537 | additionalProperties: false 拒 |
| scene_archive summary 50–100 | 354/1236 (29%) | max 196 |
| scene_archive location <20 | 28/1236 | max 31 |

→ bound 按用户精确值定 schema。现有 phase 0 chunk + phase 4 scene_archive 已知不达 schema，明示在 ai_context/handoff，等下次重抽收敛。chunk 是 phase 1 的输入，建议 phase 1 重抽前先重抽 phase 0；scene_archive 可继续按程序 remap 用，等 summary 风格调整时整轮重抽。

**2. cross-file alignment 必然牵连**

| 改动 | 原因 |
|---|---|
| `schemas/runtime/scene_archive_entry.schema.json` summary 加 minLength=50/maxLength=100 + description 改"50–100 字" | scene_archive.summary 是 scene_split.summary 1:1 程序拷贝（已溯源），契约必须一致；现 description 写"30–50 字"是历史误差 |
| `automation/prompt_templates/summarization.md` 删 `potential_boundary`/`boundary_hint` 描述 + JSON 模板字段 + 规则段；按新 bound 限定每字段长度 | LLM 必须按新 schema 产出 |
| `automation/prompt_templates/scene_split.md` 加 time/location/summary bound 描述 | 同上 |
| `automation/prompt_templates/analysis.md` 删除 `potential_boundary` 引用 | chunk 不再含此字段；Phase 1 stage 边界推断改为基于 summary + key_events + location 转换 + emotional_tone 突变 + identity_notes（prompt 早就说"不要机械以它为唯一依据"） |
| `schemas/README.md` 加 `analysis/` 子目录索引 | 全局索引必须收新 schema |
| `docs/architecture/schema_reference.md` 加 Analysis 层段 + 同步 scene_archive_entry summary 描述 | conventions Cross-File Alignment 表第一行 |

**3. 故意不动**

- **不**改 `scene_archive_entry.schema.json` 的 required（summary 当前 optional；让 required 是合理但超 scope）→ 登记 todo
- **不**迁移现有数据
- **不**为 phase 1 输出（world_overview / stage_plan / candidate_characters）加 schema → 超 scope，登记 todo

## 计划动作清单

- file: `schemas/analysis/chapter_summary_chunk.schema.json` (新建) → 顶层 chunk wrapper（required: work_id / chunk_index / chapters / summaries）+ 内嵌 ChapterSummary（required 8 字段 + 全 bound + additionalProperties: false）
- file: `schemas/analysis/scene_split.schema.json` (新建) → root array of SceneSplit（required 6 字段 + 3 个长度 bound + additionalProperties: false + maxItems: 5）
- file: `schemas/runtime/scene_archive_entry.schema.json` → summary 加 minLength=50 / maxLength=100；description 改"50–100 字"
- file: `schemas/README.md` → 加 `analysis/` 子目录段
- file: `docs/architecture/schema_reference.md` → 加 Analysis 层段 + scene_archive_entry summary 契约说明
- file: `automation/prompt_templates/summarization.md` → 删 potential_boundary / boundary_hint；加 bound 说明；JSON 模板同步
- file: `automation/prompt_templates/scene_split.md` → 加 time/location/summary bound 说明
- file: `automation/prompt_templates/analysis.md` → 删除 potential_boundary 三处引用，改用其他字段
- file: `ai_context/handoff.md` → 加段说明现存 phase 0 chunk + phase 4 scene_archive 未达新 schema bound（已知 caveat）
- file: `docs/todo_list.md` → 加 2 条 todo：T-PHASE1-OUTPUT-SCHEMAS、T-SCENE-ARCHIVE-SUMMARY-REQUIRED

## 验证标准

- [ ] 两个新 schema 跑 `python3 -c 'import json,jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open("...")))'` 自身合法
- [ ] 现存 22 个 chunk 跑新 chunk schema：预期 100% 违反（含 potential_boundary）—— 与决策 1 一致
- [ ] scene_archive_entry 修订后：现存 1236 行违反计数 ≈ 29%
- [ ] `git grep -nE 'potential_boundary|boundary_hint'` 在 prompt / docs / schemas 范围内 = 0
- [ ] `schemas/README.md` 索引和 `docs/architecture/schema_reference.md` 索引同步
- [ ] prompt bound 文字与 schema bound 数字一致
- [ ] commit message 风格对齐 `git log --oneline -10`

## 执行偏差

- 上一轮 /go（同 scope）被 user interrupt + worktree 自动 revert，PRE log 重写为新 timestamp `2026-04-25_045942`，原 PRE log `2026-04-25_042738` 未落盘
- 无其他偏差

<!-- POST 阶段填写 -->

## 已落地变更

- [schemas/analysis/chapter_summary_chunk.schema.json](schemas/analysis/chapter_summary_chunk.schema.json)（新建）：顶层 wrapper required = work_id/chunk_index/chapters/summaries；ChapterSummary required 8 字段 + summary 50-100 / key_events maxItems 5 + items maxLength 49 / location maxLength 19 / emotional_tone maxLength 19 / identity_notes maxLength 49 / chapter pattern `^\d{4}$`；additionalProperties: false（拒 potential_boundary/boundary_hint）
- [schemas/analysis/scene_split.schema.json](schemas/analysis/scene_split.schema.json)（新建）：root array minItems 1 / maxItems 5；SceneSplit required 6 字段 + summary 50-100 / time maxLength 19 / location maxLength 19；additionalProperties: false
- [schemas/runtime/scene_archive_entry.schema.json:43-47](schemas/runtime/scene_archive_entry.schema.json) summary 加 minLength 50 / maxLength 100；description 改"50-100 字"并写明 1:1 程序直拷契约
- [schemas/README.md:9](schemas/README.md) 表格加 `analysis/` 行
- [docs/architecture/schema_reference.md:13](docs/architecture/schema_reference.md) 子目录表加 `schemas/analysis/`；§Analysis 层段新增（chapter_summary_chunk + scene_split）；runtime/scene_archive_entry 段加"契约"行说明 1:1 直拷 + 可程序 remap
- [automation/prompt_templates/summarization.md](automation/prompt_templates/summarization.md) 步骤 2 字段表重写带 bound 描述 + "硬上限不是配额"提醒；删除 potential_boundary 字段说明 + JSON 模板 + 规则段
- [automation/prompt_templates/scene_split.md](automation/prompt_templates/scene_split.md) 元数据要求段加 schema 链接 + 三字段 bound + "硬上限不是配额"提醒
- [automation/prompt_templates/analysis.md](automation/prompt_templates/analysis.md) 三处 potential_boundary 引用替换：line 28 字段表改用 location/emotional_tone/identity_notes；line 38 候选边界信号改为 location 转换 / emotional_tone 突变；line 117 stage 边界判据改为综合多字段
- [ai_context/handoff.md](ai_context/handoff.md) 加段"Phase 0 chunk + Phase 4 scene_archive 不达新 schema (caveat)"，明示已知偏差 + 重抽收敛路径
- [docs/todo_list.md](docs/todo_list.md) "下一步"段加两条 todo：T-PHASE1-OUTPUT-SCHEMAS（world_overview/stage_plan/candidate_characters 缺 schema）、T-SCENE-ARCHIVE-SUMMARY-REQUIRED（summary 应 required）；插在最前

## 与计划的差异

无（PRE 计划 10 个文件改动 = 实际 10 个：2 新建 schema + 1 schema 修订 + README + schema_reference + 3 prompt + handoff + todo_list）

## 验证结果

- [x] 三个 schema 跑 `Draft202012Validator.check_schema` 全 OK
- [x] 现存 22 个 chunk 跑新 schema = 22/22 fail（首条 fail 原因即"Additional properties not allowed: potential_boundary/boundary_hint"）—— 与决策 1 完全一致
- [x] 现存 1236 行 scene_archive 跑修订后 scene_archive_entry = 354/1236 fail (28.6%)，分类 308 maxLength + 46 minLength —— 与 PRE 28.6% 实测预期一致
- [x] `git grep potential_boundary|boundary_hint -- ':!logs/'` 仅 ai_context/handoff.md 一处保留（caveat 段落正当引用，非残留）
- [x] schemas/README.md `analysis/` 行 vs schema_reference.md 的 schemas/analysis/ 子目录段同步
- [x] prompt bound 文字（"50-100 字" / "<20" / "<50" / "最多 5 条"）与 schema 数字一致
- [x] 文档无真实书名 / 角色 / 地名残留（`git grep '我和女帝'` = 0）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-25 04:59:42 EDT
