# phase_schemas_bounds_cleanup

- **Started**: 2026-04-23 20:34:04 EDT
- **Branch**: extraction/<work_id>（编辑阶段）→ master（提交阶段）
- **Status**: PRE

## 背景 / 触发

延续 `character_schema_bounds_cleanup` / `identity_voice_rules_bounds_cleanup`
系列：把各 phase 产出的字段级上下限收口到 JSON schema 一处，保持「bounds only
in schema; TOML 不存第二份；prompt template 里描述性字数要求作为 LLM 指引保留
但不是权威」这条约束。本轮由用户在会话中给出具体指标清单，覆盖 digest 层
（world_event_digest / memory_digest）、foundation、fixed_relationships、
stage_catalog（world + character）以及 memory_timeline。顺带完成两项结构性收
口：character 侧 stage_catalog schema 从 `schemas/work/` 迁到
`schemas/character/`；memory_timeline 删除 `scene_refs` 场景回溯字段。

## 结论与决策

1. **digest 层 time/location 统一为 ≤15 字短时间地点锚**，与
   stage_catalog.stage_title、stage_snapshot.timeline_anchor 的短字段家族对齐。
   digest 条目由 post_processing 从 snapshot 派生，`required` 生效意味着上游
   snapshot 必须给出 `timeline_anchor` + `location` 才能通过 digest 校验 —
   这是刻意的硬门控。
2. **foundation** 作为 Phase 2.5 的静态基底，逐字段加上中文语境下合理的
   maxLength / maxItems；`additionalProperties: true` 继续保留，不做破坏性收
   紧，仅对用户列出的字段设门控。
3. **fixed_relationships** 去掉 `source_type` + `evidence_refs`，与其他 baseline
   schema 保持一致（章节锚点统一走 stage_snapshot/evidence_refs；
   fixed_relationships 是结构性纽带，不需要逐条章节追溯）。
4. **stage_catalog** 删除 `order`：`stage_id` 本身（`S###`）即天然有序，
   `order` 是冗余字段；upsert 时改为按 `stage_id` 字典序排序。
5. **character stage_catalog schema 位置**：由 `schemas/work/stage_catalog.schema.json`
   迁到 `schemas/character/stage_catalog.schema.json`。该 schema 仅被角色目录使用，
   放在 `work/` 下属于历史归类错误。同时删除 `stages[].*_summary` 七个兜底字
   段 —— 这些字段从未被 LLM 填、post_processing 侧 `_CHAR_CATALOG_SUMMARY_FIELDS`
   也是空列表，属于历史遗留。
6. **memory_timeline** `scene_refs` 删除：memory_timeline 已通过 `event_description`
   + `digest_summary` 自足，`scene_archive` 追溯链并非运行时要求；
   `knowledge_gained` 收紧为 `maxItems:10 / item maxLength:50`（之前是 5 条无
   item 上限）；`time` / `location` 补 `maxLength:15` + `required`，与 digest
   对齐。
7. **`automation/config.toml` 不新增任何字段级 bound**（保持「bound 只在 schema」
   这条硬规则）；prompt template 里的字数描述仅作为 LLM 引导，不是权威。

## 计划动作清单

### 1 Schema 变更

- `schemas/world/world_event_digest_entry.schema.json`
  - `time` / `location` 添加 `maxLength: 15`
  - `required` 追加 `time` / `location`
- `schemas/character/memory_digest_entry.schema.json`
  - `time` / `location` 添加 `maxLength: 15`
  - `required` 追加 `time` / `location`
- `schemas/world/foundation.schema.json`
  - `tone` `maxLength: 100`
  - `world_structure.summary` `maxLength: 200`
  - `world_structure.major_regions` `maxItems: 20`；item `description` `maxLength: 50`
  - `power_system.summary` `maxLength: 200`
  - `power_system.levels` `maxItems: 15`；item `description` `maxLength: 50`
  - `core_rules` `maxItems: 20`；item `description` / `impact` 各 `maxLength: 50`
  - `world_lines` `maxItems: 20`；item `core_conflict` / `setting_features` 各 `maxLength: 50`
  - `major_factions` `maxItems: 20`；item `description` `maxLength: 50`；`key_figures` `maxItems: 10`
- `schemas/world/fixed_relationships.schema.json`
  - item `description` `maxLength: 100`
  - 删除 item `source_type` / `evidence_refs` 两个 property
- `schemas/world/world_stage_catalog.schema.json`
  - 删除 `stages[].order`（property + required）
- `schemas/character/stage_catalog.schema.json`（**新建 = 从 work/ 迁入**）
  - 复制 `schemas/work/stage_catalog.schema.json`，`$id` 改为
    `persona-engine/character/stage_catalog.schema.json`
  - 删除 `stages[].order`（property + required）
  - 删除 `stages[].experience_summary` / `relationship_summary` /
    `personality_summary` / `current_status_summary` / `current_mood_summary` /
    `voice_shift_summary` / `knowledge_boundary_summary` 七个 property
- `schemas/work/stage_catalog.schema.json` **删除**
- `schemas/character/memory_timeline_entry.schema.json`
  - `time` `maxLength: 15`、`location` `maxLength: 15`
  - `required` 追加 `time` / `location`
  - `knowledge_gained` `maxItems: 10`，item `maxLength: 50`
  - 删除 `scene_refs`

### 2 代码侧连带

- `automation/persona_extraction/post_processing.py`
  - `upsert_stage_catalog()`：new_entry 不再写 `order`；排序改按 `stage_id`；
    schema_name 在 character 分支改为 `character/stage_catalog.schema.json`；
    删除 `_CHAR_CATALOG_SUMMARY_FIELDS` 相关死代码 + loop；
    参数 `order: int` 删除；日志里 `order` 字面量移除
  - 调用方 `run_stage_post_processing`（行 495/536/614）同步去 `stage_order`
    透传
- `automation/persona_extraction/prompt_builder.py`（行 169-170）schema 列表
  更新为 `character/stage_catalog.schema.json`
- `automation/persona_extraction/orchestrator.py`（行 584）schema 路径更新
- `automation/persona_extraction/consistency_checker.py`（行 367-412）：删除
  `memory_timeline scene_refs` 覆盖检查整段；上下文调整

### 3 Prompt template 同步

- `automation/prompt_templates/baseline_production.md`（行 226）
  `schemas/work/stage_catalog.schema.json` → `schemas/character/stage_catalog.schema.json`
- `automation/prompt_templates/character_support_extraction.md`（行 31）
  删除 "memory_timeline 每条的 scene_refs ..." 这一行
- prompt template 内对 digest `time`/`location` 若无描述，补最小一行引导

### 4 文档同步

- `docs/requirements.md`：
  - §11.4 / §11.x 关于 stage_catalog 的映射表和字段列表更新（删 `order` +
    character *_summary + 迁路径）
  - memory_timeline 段落删除 `scene_refs`，对应 JSON 示例同步清理
  - fixed_relationships 段落删除 `source_type` / `evidence_refs`
  - foundation 段落补上限描述（若原本没有）
- `docs/architecture/schema_reference.md`：
  - `### work/stage_catalog.schema.json` 段落搬到 character 节，标题改名
  - memory_timeline `scene_refs` 字段描述删除
  - fixed_relationships `source_type` / `evidence_refs` 删除
- `docs/architecture/data_model.md`：无直接字段列表，仅需确认引用路径
- `simulation/retrieval/index_and_rag.md`：memory_timeline FTS5 表里
  `scene_refs TEXT` 列删除（及索引语句相关片段）；memory_timeline 字段清单
  删 `scene_refs`

### 5 ai_context 同步

- `ai_context/architecture.md`（行 98）memory_timeline 描述去掉 `scene_refs`
- `ai_context/conventions.md`（行 83）Baseline removed fields 表：
  - `memory_timeline` 不再持有 `scene_refs`（仅保留 digest 派生）
  - `fixed_relationships` 不再持有 `source_type` / `evidence_refs`
  - stage_catalog 不再持有 `order` / character 侧 `*_summary`
  - stage_catalog schema 位置条目迁到 `schemas/character/`
- `ai_context/decisions.md`：追加新的决策条目（编号接在 27c 之后），记录
  本轮字段收口 + 位置迁移 + scene_refs 移除 的 rationale

## 验证标准

- [ ] 所有修改后的 schema 文件 `python -m jsonschema` 自解析无错
- [ ] `grep -r "source_type" schemas/ automation/ ai_context/ docs/requirements.md docs/architecture/` 只剩 work_manifest `source_types` 复数字段
- [ ] `grep -r "scene_refs" schemas/ automation/ ai_context/ docs/requirements.md docs/architecture/ simulation/` 为 0
- [ ] `grep -rn "schemas/work/stage_catalog" .` 在仓库内为 0；`schemas/work/stage_catalog.schema.json` 已删除
- [ ] `grep -rn '"order"' schemas/world/world_stage_catalog.schema.json schemas/character/stage_catalog.schema.json` 为 0
- [ ] `python -c "from automation.persona_extraction import post_processing"` import 通过
- [ ] `python -c "from automation.persona_extraction import orchestrator, prompt_builder, consistency_checker"` import 通过
- [ ] CLAUDE.md 的「Sync with AGENTS.md」镜像约束成立（本轮如触到入口文件需同步；如未触到，此项为 N/A）
- [ ] 全仓库 grep 无 "已废弃 / legacy / 原为 / 旧" 等字样被新引入

## 执行偏差

### 偏差 1（2026-04-23 21:00 EDT）：world_stage_snapshot 新增 `location_anchor`

**触发**：Step 6 full-review agent 发现，将 `world_event_digest.location` 设为
required 后，post_processing 没有数据源可填（world_stage_snapshot 没有
stage-level location 字段），会导致每次 digest 生成时验证失败。

**决策**：在 `schemas/world/world_stage_snapshot.schema.json` 新增
`location_anchor: string, maxLength: 15`，并加入 `required`。与既有
`timeline_anchor` 形成对称设计（阶段级锚点）。同步：
- 把 `timeline_anchor` 也加到 `required`（本来就是 digest.time 必填的隐式前提）
- `timeline_anchor` 补 `maxLength: 15`（之前无上限，digest.time 有 15 上限
  会截断矛盾）
- `post_processing.generate_world_event_digest` 读 `location_anchor`，写入
  digest.location；time 也改为无条件写入（required 意味着即便空串也要有键）
- `automation/prompt_templates/world_extraction.md` 核心规则 #6 明确两字段
  的填法
- `docs/requirements.md` §11.3a world_event_digest 映射表补 `location_anchor`
  一行
- `docs/architecture/schema_reference.md` world_stage_snapshot 段落列出两
  字段并补入自包含契约
- `ai_context/decisions.md` 27d 条目扩写为数据源说明

**为什么不改 `stage_events` 成 object[]**：那是更大的 schema 重构，涉及
所有现存 world snapshot 数据。阶段级锚点方案对现有数据结构侵入最小，
符合 user 原始指令（只调整上下限 / 删字段，不重塑现有结构）。

### 偏差 2（2026-04-23 21:05 EDT）：baseline_production.md fixed_relationships 示例去 evidence_refs

**触发**：full-review agent 指出示例 JSON 里还保留 `"evidence_refs": []`，
但 schema `additionalProperties: false` 会让 LLM 按示例生成的产出直接
被判失败。

**决策**：同文件 prompt 示例删除 `evidence_refs` 字段，`description`
描述追加 "(≤100 字)" 提示。

<!-- POST 阶段填写 -->

## 已落地变更

### Schema

- `schemas/world/world_event_digest_entry.schema.json` — `time` / `location` 加 `maxLength:15` + required
- `schemas/character/memory_digest_entry.schema.json` — 同上
- `schemas/character/memory_timeline_entry.schema.json` — `time` / `location` 加 `maxLength:15` + required；`knowledge_gained` 改 `maxItems:10` + item `maxLength:50`；删 `scene_refs`
- `schemas/world/foundation.schema.json` — tone ≤100、world_structure/power_system `summary` ≤200、各 item 数组 / 字段上限按 PRE 计划逐字段落地
- `schemas/world/fixed_relationships.schema.json` — `description` `maxLength:100`；删 `source_type` + `evidence_refs`
- `schemas/world/world_stage_catalog.schema.json` — 删 `stages[].order`（property + required），注释更新为按 `stage_id` 字典序排序
- `schemas/character/stage_catalog.schema.json`（新建）— 从 work/ 迁入，`$id` 改为 character 命名空间；删 `order` + 七个 `*_summary` 字段
- `schemas/work/stage_catalog.schema.json` — `git rm`
- `schemas/world/world_stage_snapshot.schema.json` — 偏差 1：新增 `timeline_anchor` / `location_anchor` `maxLength:15` + required（供 world_event_digest 取值）

### 代码

- `automation/persona_extraction/post_processing.py`
  - `upsert_stage_catalog()` 签名去 `order` 参数；new_entry 不再写 `order`；排序改按 `stage_id`；character 分支 schema 路径切到 `character/stage_catalog.schema.json`；删 `_CHAR_CATALOG_SUMMARY_FIELDS` 死码与 loop
  - `run_stage_post_processing()` 签名去 `stage_order`
  - `generate_world_event_digest()` 读 `snapshot.location_anchor`，与 `timeline_anchor` 一起无条件写入 digest 条目的 `location` / `time`
  - `_timeline_to_digest` docstring 更新（time/location 改为 required）
- `automation/persona_extraction/orchestrator.py`
  - 两处 `run_stage_post_processing()` 调用去 `stage_order=`
  - L584 `work/stage_catalog.schema.json` → `character/stage_catalog.schema.json`
- `automation/persona_extraction/prompt_builder.py` — L170 同上切路径
- `automation/persona_extraction/consistency_checker.py` — `_check_evidence_refs_coverage` 删除 memory_timeline `scene_refs` 覆盖分支

### Prompt templates

- `automation/prompt_templates/baseline_production.md`
  - fixed_relationships 示例去 `evidence_refs`，补 "(≤100 字)"
  - `schemas/work/stage_catalog.schema.json` → `schemas/character/stage_catalog.schema.json`
  - 后续追加 stage 条目的字段清单去 `order`
- `automation/prompt_templates/character_support_extraction.md`
  - 删"场景回溯"一条（scene_refs 填写指引）
  - memory_timeline 字段清单补 `time / location ≤15 字`，`knowledge_gained` 改为 "最多 10 条，每条 ≤ 50 字"
- `automation/prompt_templates/world_extraction.md`
  - 核心规则 #6 新增 `timeline_anchor` / `location_anchor` 填法说明

### 文档

- `docs/requirements.md`
  - §11.3a world_event_digest 映射表补 `location_anchor → location`；写入规则补 time/location required 说明
  - memory_digest 映射表 time/location 标注 `≤15 字 required`
  - stage_catalog 映射表去 `order`；补 character / world schema 路径；排序改按 `stage_id` 字典序；character 段落显式说明不再有 `*_summary`
  - memory_timeline §12.4.2 JSON 示例去 `scene_refs`、`knowledge_gained` 改描述；追加 time/location ≤15 说明
  - §12.2 / §12.4 / §12.5 流程图 + 文字的三处 `scene_refs` 反查链路删除
- `docs/architecture/schema_reference.md`
  - 删 `work/stage_catalog.schema.json` 段落；Character 节新增 `character/stage_catalog.schema.json` 段落
  - world_stage_snapshot 段落列出 `timeline_anchor` / `location_anchor` 并加入自包含契约清单
  - world_stage_catalog 段落更新关键字段（去 order）
  - fixed_relationships 段落 description 补 ≤100
  - foundation 段落追加字段级上下限清单
  - world_event_digest_entry 段落 time/location 标注 required ≤15
  - memory_timeline_entry 段落删 `scene_refs`，time/location/knowledge_gained 描述更新
  - memory_digest_entry 段落 time/location 描述更新
- `docs/architecture/data_model.md` — character 章节 `canon/stage_catalog.json` 后补 schema 路径

### ai_context

- `ai_context/conventions.md` — Data Separation 小节三条分别扩写：长度门控示例加 digest/foundation/fixed_relationships；计数门控加 knowledge_gained / foundation arrays；新增 stage_catalog 位置条目；baseline removed 条目扩到 fixed_relationships 与 memory_timeline.scene_refs
- `ai_context/decisions.md` — 新增 27d / 27e 两条；27d 后来再扩写为包含 world_stage_snapshot 新 required 字段
- `ai_context/architecture.md` — Three-Layer Memory 第 2 项改写：去 scene_refs，time/location 加 ≤15 required 说明

### 其他

- `simulation/retrieval/index_and_rag.md` — memory_timeline 字段列表删 `scene_refs`；FTS5 DDL 的 `scene_refs TEXT` 列删除；time/location 注释补 ≤15

## 与计划的差异

- 偏差 1（计划外，review 发现后补）：world_stage_snapshot 新增 `timeline_anchor` + `location_anchor` 两个字段并加入 required；原计划未触及该 schema。理由详见「执行偏差」段。
- 偏差 2（计划内但位置意外）：PRE 计划里 prompt template 更新只提到 baseline_production 的 schema 路径行，未意识到同文件有 fixed_relationships 示例 JSON 也需要同步去 evidence_refs。

## 验证结果

- [x] 32 份 schema 全部通过 `Draft202012Validator.check_schema`
- [x] `grep -r "source_type"` 排除 logs / works / sources / source_types 复数后，只剩 ai_context/decisions.md + ai_context/conventions.md 两处有意义的记录行
- [x] `grep -r "scene_refs"` 排除 logs / works / sources 后，只剩 ai_context 的两条记录（描述"不再持有"）
- [x] `grep -rn "schemas/work/stage_catalog"` 仓库内除 decisions.md 的迁移记录外为 0；旧文件已 `git rm`
- [x] `grep -n '"order"'` 对两份 stage_catalog schema 均返回空
- [x] `python -c "from automation.persona_extraction import post_processing, orchestrator, prompt_builder, consistency_checker"` 全部 import OK
- [x] `upsert_stage_catalog` 签名已不含 `order`；`run_stage_post_processing` 签名已不含 `stage_order`
- [x] End-to-end 烟雾测试：合法 world_stage_snapshot（含两锚点）→ `generate_world_event_digest` → digest 条目含 time/location → schema 验证零 issue
- [x] 缺 `location_anchor` 的 snapshot 在 schema 校验就被拒（gated at snapshot level）
- [x] 全仓库未引入 "已废弃 / legacy / 原为 / 旧" 等字样
- [ ] CLAUDE.md / AGENTS.md 镜像约束：本轮未触及入口文件，N/A

## Completed

- **Status**: DONE
- **Finished**: 2026-04-23 21:15:00 EDT

<!-- /after-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：16/16 项计划 + 5/5 项可执行验证（CLAUDE/AGENTS 镜像 N/A）
- Missed updates: 1 条 —— `schemas/README.md:9,11` 未同步到 stage_catalog 从 work/ 迁到 character/

### 轨 2 — 影响扩散
- Findings: High = 1 / Medium = 1 / Low = 1
  - [H] schemas/README.md 目录表未同步
  - [M] ai_context/handoff.md 未提示 world_stage_snapshot 两个新 required 字段导致现有产物失效
  - [L] post_processing._timeline_to_digest 条件守卫 vs generate_world_event_digest 无条件写入，两处风格不一致
- Open Questions: 2 条
  1. 现有 extraction 分支 S001/S002 产物迁移策略（重跑 / 脚本 patch / 前向生效）
  2. memory_timeline time/location 是否补 minLength:1（堵"空串合法但 digest 拒绝"漏洞）

## 复查时状态

- **Reviewed**: 2026-04-23 21:35:00 EDT
- **Status**: REVIEWED-PARTIAL
  - 轨 1 大体全落实，仅 1 条 Cross-File Alignment 表里的 README 遗漏
  - 轨 2 1 High（README 同上）+ 1 Medium（handoff 提示缺失）+ 1 Low（技术债）
- **Conversation ref**: 同会话内 /after-check 输出
