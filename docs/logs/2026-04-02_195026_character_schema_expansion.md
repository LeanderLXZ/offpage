# 角色包 Schema 扩充与深度扮演支持

**时间**: 2026-04-02  
**范围**: schemas/, works/README.md, 角色包架构

## 变更动机

对照三个深度角色扮演目标（系统化角色资料、角色视角记忆体系、稳定的语言与行为
模拟规则），评估后发现：

- 7 个角色基线文件中有 5 个没有 schema
- 语言和行为模拟规则几乎空白——没有按情绪/场景/对象分类的细粒度模型
- 记忆体系缺少"误解"和"隐瞒"两个关键维度
- 阶段快照只有点状状态，没有阶段间变化轨迹

## 变更内容

### 新增 Schema（6 个）

1. **`schemas/voice_rules.schema.json`** — 角色语言风格规则基线
   - 基础语气、语言习惯、用词偏好、标志性口头禅
   - `emotional_voice_map`: 按情绪状态分类的语言变化模式（暧昧、愤怒、委屈、
     嘴硬、关心、吃醋等），每种含 voice_shift + typical_expressions +
     dialogue_examples
   - `target_voice_map`: 按对象类型分类的说话差异（亲近者、陌生人、敌对者等）
   - `dialogue_examples`: 代表性台词示例（含出处和语境）
   - `taboo_patterns`: 语言禁忌

2. **`schemas/behavior_rules.schema.json`** — 角色行为规则基线
   - `core_drives`: 核心行为驱动力
   - `emotional_triggers`: 情绪触发点（触发条件 + 反应 + 强度）
   - `emotional_reaction_map`: 按情绪状态分类的完整反应模式（内心感受、外在
     表现、典型动作、恢复方式）
   - `relationship_behavior_map`: 按关系类型分类的行为差异
   - `stress_response`: 压力反应（应对方式、崩溃临界点、危机后行为）

3. **`schemas/memory_timeline_entry.schema.json`** — 角色记忆时间线条目
   - 客观事件 + 角色主观体验（可能与事实不同）
   - `misunderstanding`: 角色在该事件中产生的误解（含真相）
   - `concealment`: 角色因该事件而隐瞒的信息（含对象和原因）
   - `relationship_impact`: 该事件对角色关系的影响
   - `memory_importance`: trivial → defining 五级重要度

4. **`schemas/identity.schema.json`** — 角色基础身份
   - 不随阶段变化的底层属性：姓名、别名、性别、种族、出身、外貌、初始社会地位

5. **`schemas/boundaries.schema.json`** — 角色人设边界
   - `hard_boundaries`: 硬边界（含原因）
   - `soft_boundaries`: 软边界（含例外条件）
   - `common_misconceptions`: 常见误解（误解 + 实际情况）

6. **`schemas/failure_modes.schema.json`** — 角色崩坏预警
   - `common_failures`: 常见扮演错误（描述 + 原因 + 正确行为）
   - `tone_traps`: 语气陷阱
   - `relationship_traps`: 关系互动陷阱
   - `knowledge_leaks`: 知识泄漏风险（含相关阶段）

### 增强 Schema（1 个）

7. **`schemas/stage_snapshot.schema.json`** — 新增三个字段：
   - `misunderstandings`: 角色在该阶段持有的误解（含真相、原因、解开阶段）
   - `concealments`: 角色在该阶段主动隐瞒的信息（含对象、原因、揭露阶段）
   - `stage_delta`: 从上一阶段到当前阶段的关键变化摘要（触发事件、性格/关系/
     状态变化、情绪基调转变、口吻转变）

### 文档更新

8. **`works/README.md`** — characters/ 部分全面更新：
   - 每个文件的说明从一句话扩充为详细内容列表
   - 标注了对应的 schema 文件路径
   - stage_snapshots 新增误解、隐瞒、阶段间 delta 说明

## 设计思路

- **基线 + 阶段 override 模式**: voice_rules 和 behavior_rules 定义跨阶段的
  基线，stage_snapshot 中的 voice_overrides 和 behavior_overrides 在特定阶段
  覆盖或修正基线
- **记忆是角色视角的**: memory_timeline 的每条记忆包含客观事件和主观体验两层，
  明确区分"发生了什么"和"角色认为发生了什么"
- **误解和隐瞒是第一等公民**: 在 stage_snapshot 和 memory_timeline 中都有
  专属字段，不再隐藏在 knowledge_scope 里
- **变化轨迹而非只有快照**: stage_delta 记录阶段间的变化，补全了之前只有
  点状快照的不足

## 涉及文件

- `schemas/voice_rules.schema.json` (新增)
- `schemas/behavior_rules.schema.json` (新增)
- `schemas/memory_timeline_entry.schema.json` (新增)
- `schemas/identity.schema.json` (新增)
- `schemas/boundaries.schema.json` (新增)
- `schemas/failure_modes.schema.json` (新增)
- `schemas/stage_snapshot.schema.json` (增强)
- `works/README.md` (更新)
