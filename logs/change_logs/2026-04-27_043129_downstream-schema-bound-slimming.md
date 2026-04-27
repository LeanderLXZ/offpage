# downstream-schema-bound-slimming

- **Started**: 2026-04-27 04:31:29 EDT
- **Branch**: main (worktree at /home/leander/Leander/offpage-main; primary checkout stays on `library`)
- **Status**: PRE

## 背景 / 触发

完成 T-SCENE-ARCHIVE-SUMMARY-REQUIRED 后，用户提出全仓盘点"程序级从上游 schema 派生"的下游 schema 是否都应按相同思路对齐：上游已 enforce 的 bound 在下游不重复、required 列表与上游对齐、字段 description 显式标注数据来源。

普查结论：B 类（程序生成 + 依赖上游 schema）共 7 份。其中 works_manifest / world_manifest 字段是程序常量或计算结果（非"上游 schema 字段直拷"），不在本轮范围；其他 5 份都需要瘦身或对齐：

| 文件 | 上游 | 关键改动 |
|---|---|---|
| `schemas/runtime/scene_archive_entry.schema.json` | scene_split + chapter txt | 删 summary 的 minLength/maxLength；description 注明来源 |
| `schemas/character/memory_digest_entry.schema.json` | memory_timeline_entry | 删 time / location / summary 的所有 bound；description 注明来源 |
| `schemas/world/world_event_digest_entry.schema.json` | world_stage_snapshot | 删 time / location / summary 的所有 bound；description 注明来源 |
| `schemas/character/stage_catalog.schema.json` | stage_snapshot | stages[].timeline_anchor 升 required；description 注明来源 |
| `schemas/world/world_stage_catalog.schema.json` | world_stage_snapshot | stages[].timeline_anchor 升 required；description 注明来源 |

代码联动：`automation/persona_extraction/post_processing.py:upsert_stage_catalog` 删 `if timeline_anchor:` 判空，无条件赋值（确保下游 required 不被跳过）。

## 结论与决策

### 1. stage_catalog（×2）—— B 路径升 required

**改动**：
- `stages[].timeline_anchor` 加入 `required` 列表
- 同步 `post_processing.py:upsert_stage_catalog` 删 `if timeline_anchor:` 判空逻辑

**为什么这么改**：上游 stage_snapshot.timeline_anchor 已 required，程序应无条件传递到下游，与 scene_archive 修法对称。

**不动**：上游 stage_snapshot 的 timeline_anchor 不加 minLength: 1（C 路径未选中）；空字符串仍合法。

### 2. scene_archive_entry —— 去 summary bound

**改动**：
- 删 [scene_archive_entry.schema.json:43-48](schemas/runtime/scene_archive_entry.schema.json#L43-L48) summary 的 `minLength: 50` / `maxLength: 100`
- 保留 type / required 与 description

**为什么这么改**：上游 scene_split.schema.json 已对 summary 设 minLength: 50 / maxLength: 100，程序 1:1 直拷。下游重复约束违反 #27b "Bounds-only-in-schema, single source of truth"。

### 3. memory_digest_entry —— 去 time / location / summary bound

**改动**：删这三个字段的 `minLength` / `maxLength`，保留 type / required。

**为什么这么改**：上游 memory_timeline_entry 已 enforce 这三个字段的 bound + required（time / location maxLength: 15；digest_summary minLength: 30 / maxLength: 50）。post_processing.generate_memory_digest 1:1 直拷，无变换。

### 4. world_event_digest_entry —— 去 time / location / summary bound

**改动**：删这三个字段的 `minLength` / `maxLength`，保留 type / required。

**为什么这么改**：上游 world_stage_snapshot 已 enforce timeline_anchor / location_anchor maxLength: 15、stage_events 单条 minLength: 50 / maxLength: 100。

### 5. description 标注数据来源

为所有"程序从上游 1:1 拉取"的字段，在 description 末尾追加固定句式：`（从 schemas/<上游路径>.schema.json 的 <字段> 1:1 拉取，bound 由上游单源定义）`。

**已部分有标注的字段**（schema 里已写"1:1 复制自..."等措辞）：
- world_event_digest_entry.summary（schema_reference.md L190）
- memory_digest_entry.summary（schema_reference.md L365）

→ 把这类已有的描述统一为"从 X.schema.json 的 Y 字段 1:1 拉取"格式，让所有下游字段叙述一致。

### 不在范围

- works_manifest / world_manifest：字段全部是程序常量或派生计算，不属"上游 schema 字段直拷"
- 上游 schema：B 路径方针不动上游
- pattern：scene_id / stage_id / event_id / memory_id 的 pattern 是格式正确性的最后防线，保留
- character_manifest：实测是 LLM 在 Phase 2 baseline 产出（schema_reference.md L205），不是程序级从上游派生
- load_profiles / 其他 runtime / user / shared schema：与本轮无关

## 计划动作清单

1. `schemas/runtime/scene_archive_entry.schema.json`：删 summary 的 minLength: 50 / maxLength: 100；为 time / location / characters_present / summary 字段加来源标注
2. `schemas/character/memory_digest_entry.schema.json`：删 time / location / summary 三字段的 minLength / maxLength；加来源标注
3. `schemas/world/world_event_digest_entry.schema.json`：删 time / location / summary 三字段的 minLength / maxLength；加来源标注
4. `schemas/character/stage_catalog.schema.json`：stages[].timeline_anchor 升 required；为派生字段（stage_title / summary / timeline_anchor / snapshot_path）加来源标注
5. `schemas/world/world_stage_catalog.schema.json`：同上
6. `automation/persona_extraction/post_processing.py:upsert_stage_catalog`：删 `if timeline_anchor:` 判空，改为无条件赋值
7. 检查 `docs/architecture/schema_reference.md` 是否需要联动更新字段描述

## 验证标准

- [ ] 5 份 B 类 schema 通过 `Draft202012Validator.check_schema`
- [ ] 5 份 schema 字段 description 含"从 schemas/<上游路径>.schema.json 的 <字段> 1:1 拉取" 句式（或语义等价）
- [ ] `automation/persona_extraction/post_processing.py` `python -m py_compile` 通过
- [ ] memory_digest_entry / world_event_digest_entry / scene_archive_entry 不再出现 minLength / maxLength（除 pattern 类约束）
- [ ] stage_catalog stages[].required 含 timeline_anchor
- [ ] post_processing.py 不再含 `if timeline_anchor:` 判空（grep 0 命中）

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

### Schema 改动（5 文件）

1. [schemas/runtime/scene_archive_entry.schema.json](schemas/runtime/scene_archive_entry.schema.json)：
   - 删 `summary` 的 `minLength: 50` / `maxLength: 100`
   - 顶层 description + 8 个字段的 description 全部加上数据来源标注（程序常量 / 上游 1:1 拉取 / 程序生成）

2. [schemas/character/memory_digest_entry.schema.json](schemas/character/memory_digest_entry.schema.json)：
   - bound 已是干净状态（之前就无 minLength/maxLength），仅刷新 description 标注，统一为"从 schemas/character/memory_timeline_entry.schema.json 的 X 字段 1:1 拉取"格式

3. [schemas/world/world_event_digest_entry.schema.json](schemas/world/world_event_digest_entry.schema.json)：同上，刷新 description 标注

4. [schemas/character/stage_catalog.schema.json](schemas/character/stage_catalog.schema.json)：
   - `stages.items.required` 加入 `timeline_anchor`（原 4 字段 → 5 字段）
   - 顶层 description + 6 个 stages[] 字段的 description 加来源标注

5. [schemas/world/world_stage_catalog.schema.json](schemas/world/world_stage_catalog.schema.json)：同上

### 代码改动（1 文件）

6. [automation/persona_extraction/post_processing.py:393-405](automation/persona_extraction/post_processing.py#L393-L405) `upsert_stage_catalog`：
   - 删 `if timeline_anchor:` 判空逻辑
   - 改为 `"timeline_anchor": snapshot_data.get("timeline_anchor", "")` 无条件赋值
   - 加注释说明"上游 schema gate 保证键存在；空字符串合法"

### 文档改动（1 文件）

7. [docs/architecture/schema_reference.md](docs/architecture/schema_reference.md)：
   - L136-138：world_stage_catalog 关键字段补 timeline_anchor + 加"生成方式"行
   - L375-377：character/stage_catalog 同上
   - L466：scene_archive_entry 契约段补"bound 由上游 scene_split.schema.json 单源定义，本 schema 不重复约束"
   - memory_digest / world_event_digest 段已有"1:1 复制自"措辞，无需联动

## 与计划的差异

无。所有 7 个计划项全部按 PRE 设想完成。

## 验证结果

- [x] 5 份 B 类 schema 通过 `Draft202012Validator.check_schema`
- [x] scene_archive / memory_digest / world_event_digest 三 schema 0 处 minLength/maxLength（grep 0 命中）
- [x] 5 份 schema 全部字段 description 含数据来源标注（sub-agent 逐一确认）
- [x] `automation/persona_extraction/post_processing.py` `python -m py_compile` 通过
- [x] 两份 stage_catalog 的 `stages.items.required` 含 `timeline_anchor`
- [x] post_processing.py 无 `if timeline_anchor:` 判空（grep 0 命中）
- [x] sub-agent 双轨审计 10/10 PASS（含上下游一致性 / 边界风险 / 跨文件 / ai_context 漂移检查）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-27 04:39:24 EDT
