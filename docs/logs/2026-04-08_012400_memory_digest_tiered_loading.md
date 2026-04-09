# memory_digest.jsonl 与分层记忆加载

**日期**: 2026-04-08
**范围**: 记忆加载策略优化

## 背景

旧策略：启动时加载当前 stage 全量 + 全历史 critical/defining 条目。
在阶段数 30+ 时，历史 critical/defining 条目可能累积 ~66K tokens，
加上其他启动数据接近 200K token 上限。

## 变更

### 新三层记忆加载策略

1. **近期记忆**：近期 2 个阶段（N + N-1）全量加载
2. **远期感知**：`memory_digest.jsonl` 全量加载（压缩索引，~60-80 tokens/条）
3. **按需检索**：FTS5 按需检索 memory_timeline 详情

### 新增文件

- `schemas/memory_digest_entry.schema.json` — digest 条目 schema
- 每角色产出 `characters/{char_id}/canon/memory_digest.jsonl`

### memory_digest 字段

- `memory_id`, `stage_id`, `event_summary`（压缩版）, `memory_importance`
- 可选：`time_in_story`, `location`, `emotional_tags`, `involved_targets`

### Token 预算改善

- 旧策略 Stage 40 启动：~141K tokens（其中历史记忆 ~66K）
- 新策略 Stage 40 启动：~101K tokens（其中 digest ~26K）
- 节省 ~40K tokens，远离 200K 上限

## 修改文件

### 架构与需求
- `docs/requirements.md` — §7.1, §12.4 加载策略替换, §12.4.4 新增 digest 规范
- `docs/architecture/schema_reference.md` — memory_timeline 加载描述 + 表格
- `docs/architecture/extraction_workflow.md` — 每批产出增加 digest, 验证清单
- `docs/architecture/data_model.md` — 启动加载描述
- `simulation/retrieval/load_strategy.md` — Tier 0/1 描述
- `simulation/retrieval/index_and_rag.md` — 启动加载集成
- `simulation/flows/startup_load.md` — 加载顺序和规则

### 自动化
- `automation/prompt_templates/coordinated_extraction.md` — digest 生成规则
- `automation/prompt_templates/semantic_review.md` — digest 审校检查
- `automation/persona_extraction/validator.py` — digest 校验逻辑
- `automation/persona_extraction/prompt_builder.py` — digest schema 加入读取列表

### AI 上下文
- `ai_context/architecture.md` — 加载公式和三层记忆
- `ai_context/requirements.md` — §7, §12
- `ai_context/decisions.md` — #32

### 运行时
- `prompts/runtime/记忆检索规则.md` — 数据依赖更新

### Schema
- `schemas/memory_digest_entry.schema.json`（新增）
- `schemas/README.md` — 索引更新
