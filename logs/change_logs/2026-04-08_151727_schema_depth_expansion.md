# Schema 深度扩展：核心创伤、执念/目标拆分、人物关系弧线、角色整体弧线

**日期**: 2026-04-08
**范围**: schemas, docs, ai_context, automation prompt templates, validator

## 变更内容

### 1. identity.schema.json — 新增 `core_wounds` 和 `key_relationships`

- `core_wounds`：跨全故事的根源性心理创伤（wound、origin、behavioral_impact、source_type）
- `key_relationships`：核心人物关系弧线（target、initial_relationship、relationship_arc、turning_points、source_type）
- 运行时加载（identity.json 是不变层，始终加载）

### 2. behavior_rules.schema.json — `core_drives` 拆分为 `core_goals` + `obsessions`

- `core_goals`：理性目标（可权衡调整优先级）
- `obsessions`：执念（非理性心结，与创伤或强烈情感相关）
- 旧 `core_drives` 字段向后兼容保留，新提取使用拆分字段

### 3. stage_snapshot.schema.json — 三处变更

- `behavior_state`：新增 `core_goals` + `obsessions`，旧 `core_drives` 保留
- `emotional_baseline`：新增 `active_goals` + `active_obsessions`，旧 `active_desires` 保留
- 新增 `character_arc`：角色从阶段 1 到当前的整体弧线概览（arc_summary、arc_stages、current_position）

### 4. 文档同步更新

- `docs/requirements.md`：快照完整性检查清单、baseline 产出说明
- `docs/architecture/schema_reference.md`：identity、behavior_rules、stage_snapshot 描述
- `docs/architecture/system_overview.md`：快照内容列表
- `docs/architecture/data_model.md`：角色包文件列表
- `ai_context/architecture.md`、`decisions.md`、`requirements.md`、`current_status.md`
- `simulation/contracts/baseline_merge.md`、`simulation/retrieval/load_strategy.md`

### 5. 提取模板更新

- `automation/prompt_templates/baseline_production.md`：identity 产出加入 core_wounds、key_relationships
- `automation/prompt_templates/coordinated_extraction.md`：快照检查清单、字段命名表、退化信号

### 6. validator.py 更新

- 新增 identity.json 深度检查（core_wounds、key_relationships 缺失警告）
- 新增 legacy 字段迁移提示（core_drives → core_goals + obsessions）
- 新增 character_arc 缺失检查（阶段 2+ 必须包含）
- 新增 behavior_rules.json 的 goals/obsessions 拆分检查

## 向后兼容性

- 所有旧字段保留，新字段均为 optional
- 现有数据通过 validator 无 error（仅 warning 提示迁移）
- 新提取将使用拆分字段

## 已验证

- 三个 schema 文件 JSON 语法正确
- validator 对现有阶段 01-03 数据运行通过（0 errors）
- grep 全库确认无遗留的旧引用（docs 层面）
