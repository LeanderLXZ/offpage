# target_behavior_map 新增 & target_voice_map 详细度强化

**时间**：2026-04-08
**触发**：用户审查阶段01产出后发现 target_voice_map 内容太少、缺少
target_behavior_map

## 变更内容

### 1. Schema 变更

`schemas/stage_snapshot.schema.json`：

- `behavior_state` 新增 `target_behavior_map` 字段，与 `voice_state` 中的
  `target_voice_map` 平行结构。每个条目包含：
  - `target_type`（具体角色名或角色类型）
  - `behavior_shift`（行为模式整体描述）
  - `typical_actions`（典型行为列表）
  - `action_examples[]`（原文行为示例，要求至少 3-5 条）
- `target_voice_map` 描述更新：强调每个 target 至少 3-5 条 dialogue_examples，
  重要角色用具体名称而非泛化类型
- 两个 map 均标注"运行时按用户角色过滤加载"

### 2. 需求文档更新

`docs/requirements.md`：

- §9 快照完整性检查清单：补充 target_behavior_map 要求，细化 target_voice_map
  描述（每 target 至少 3-5 条对话示例）
- 缺陷示例：新增 target_voice_map 内容过少和 target_behavior_map 缺失的后果
- §12.3 stage_snapshot 内容：补充 target_behavior_map，新增运行时过滤加载说明

### 3. 架构文档更新

- `docs/architecture/schema_reference.md`：更新 voice_state 和 behavior_state
  的 section 说明
- `docs/architecture/extraction_workflow.md`：验证清单新增两项检查

### 4. 加载策略更新

`simulation/retrieval/load_strategy.md`：Tier 0 stage snapshot 加载说明中
新增 filtered loading 规则——target_voice_map 和 target_behavior_map 按用户
角色过滤加载（canon 角色精确匹配，OC 角色按关系类型匹配）

### 5. 抽取 Prompt 更新

`automation/prompt_templates/coordinated_extraction.md`：

- 核心规则中补充 target_behavior_map 和 target_voice_map 缺失的扮演缺陷说明
- 新增专门的"target_voice_map 和 target_behavior_map 详细度要求"章节，
  包含详细的正反面示例
- 风格一致性要求新增两项检查
- 稀释保护退化信号新增两项

`automation/prompt_templates/semantic_review.md`：

- 风格与详细度一致性检查新增 target_voice_map/target_behavior_map
- 信息充分性检查更新
- 输出格式 STYLE_CONSISTENCY 新增两项

### 6. AI Context 更新

- `ai_context/architecture.md`：Self-Contained Stage Snapshots 段落补充
  filtered loading 说明
- `ai_context/requirements.md`：§7 信息分层加载补充过滤说明
- `ai_context/decisions.md`：新增决策 #16（target maps 结构、示例要求、
  加载过滤策略），后续编号 +1

### 7. 未变更

- `automation/persona_extraction/validator.py`：无需修改。behavior_state
  存在性检查不变，schema 校验走 jsonschema（target_behavior_map 是 optional）
- `schemas/behavior_rules.schema.json`（baseline）：不加入 target_behavior_map，
  baseline 是简略锚点
- `docs/architecture/data_model.md`：目录/文件级描述，不涉及 schema 内部字段

## 设计理由

- 面对不同对象时的语气和行为差异是角色真实感的关键维度
- 同一情绪面对不同对象，说话方式和行为完全不同——这种差异必须被结构化捕捉
- 运行时按用户角色过滤加载，避免详细的 target maps 浪费 prompt 预算
- token 预算分析显示：filtered loading 后 target maps 扩充仅增加 ~4K tokens，
  远非瓶颈（真正瓶颈是 memory_timeline 历史累积，待后续处理）
