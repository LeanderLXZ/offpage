# Phase 3 长度硬门控 + 世界/角色边界过滤重构

## 背景

提取管线原先对 memory_timeline / stage_events / digest 字段只有软长度要求
（描述里写"≤N 字"，但 schema 没有 minLength/maxLength）。结果：

- LLM 产出的 event_description 常常一句话带过或膨胀到几百字
- memory_digest.summary 是 event_description 的机器截断，质量不稳定
- world stage_events 里偶尔混入只有角色私人知道的内心活动
- `source_type: canon/inference/ambiguous` 标注在实践中几乎永远填
  "inference"，既不承担判别义务，也吃 prompt 预算

本次重构统一解决三件事：

1. 所有长度要求升级为 schema 硬门控（minLength/maxLength）
2. memory_timeline 拆成 objective `event_description` (150–200 字) +
   indexable `digest_summary` (30–50 字) 两个独立字段；digest 层 1:1 复制
3. world stage_events 过滤前移到提取与世界审校阶段（不让私人内心进公共层）
4. 彻底删除 `source_type` 字段（identity.json / fixed_relationships.json
   除外——不在本次重构范围）

## 改动范围

### Schema（硬门控真源）

- `schemas/memory_timeline_entry.schema.json` — 新增 `digest_summary`
  (minLength 30 / maxLength 50)；`event_description` 150–200 字；删
  `event_summary` 与 `source_type`
- `schemas/memory_digest_entry.schema.json` — `summary` 30–50 字
- `schemas/world_event_digest_entry.schema.json` — `summary` 50–80 字
- `schemas/stage_snapshot.schema.json` / `world_stage_snapshot.schema.json`
  — `stage_events[].summary` 50–80 字

### 提取与审校 prompt

- `automation/prompt_templates/world_extraction.md` — world stage_events 过
  滤规则；长度硬门控说明；移除 source_type
- `automation/prompt_templates/character_extraction.md` — 同上 + timeline
  双字段说明
- `automation/prompt_templates/coordinated_extraction.md` — 同步
- `automation/prompt_templates/semantic_review_world.md` — 审校读取各角色
  memory_timeline，检出私人内容泄漏到 world stage_events
- `automation/prompt_templates/semantic_review_character.md` — timeline 两
  字段一致性与长度
- `automation/prompt_templates/semantic_review.md` — 兜底模板对齐
- `automation/prompt_templates/baseline_production.md` — 移除 source_type
- `prompts/review/手动补抽与修复.md` — 硬门控规则；删 source_type 修复类型

### Python 管线

- `automation/persona_extraction/validator.py` — 依赖 schema 硬门控，移除
  自带长度/source_type 判断
- `automation/persona_extraction/post_processing.py` — memory_digest 与
  world_event_digest 都改为 1:1 机械复制上游 summary/digest_summary
- `automation/persona_extraction/consistency_checker.py` — 9 项检查 → 8 项
  （source_type 分布检查删除）

### 文档对齐

- `ai_context/{architecture,conventions,requirements,decisions,current_status}.md`
- `docs/architecture/{data_model,extraction_workflow,schema_reference}.md`
- `docs/requirements.md`（§11.10 表格重排，流程图 9→8）
- `automation/README.md`、`works/README.md`
- `simulation/retrieval/{index_and_rag,load_strategy}.md` — FTS5 索引字段切到
  event_description + digest_summary；Tier 0 digest 说明更新
- `simulation/contracts/baseline_merge.md` — 删 source_type 提升路径

## 验证

- Grep 全仓未见游离的 `event_summary` / `source_notes` / `≤50字` / `≤80字` 表述
- Phase 3.5 检查条数统一为 8 项（requirements.md 表格、automation/README、
  ai_context/architecture、current_status、extraction_workflow）
- post_processing 文档字符串标注 1:1 mechanical copy，与实现一致

## 未触及

- `schemas/identity.schema.json` / `schemas/fixed_relationships.schema.json`
  仍保留 `source_type`（显式声明在本次范围外）
- 历史 works 数据未回填——schema 硬门控只影响新 Phase 3 运行
