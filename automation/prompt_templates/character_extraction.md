# 角色层提取

你现在接手本地项目 `persona-engine`，你没有任何额外背景知识，请完全按本提示词执行。

## 任务卡

- **当前目标**: 对 `{work_id}` 执行 {batch_id} 的 **角色层提取**（仅 `{character_id}` 一个角色）
- **batch_id**: `{batch_id}`
- **stage_id**: `{stage_id}`
- **章节范围**: `{chapter_range}`
- **目标角色**: `{character_id}`
- **首批？**: {is_first_batch}
- **源目录**: `{source_dir}`
- **作品目录**: `{work_dir}`

## 必读文件清单

编排脚本已为你列出本次需要读取的全部文件。请按顺序读取，不要跳过：

{files_to_read}

### 别名交叉比对

文件清单中包含目标角色的 `identity.json`。在阅读原文章节 **之前**，先从中提取 `aliases` 列表，了解该角色的所有已知名称、化名、代称、称呼。阅读原文时，遇到任何人名或指代，**先与已知别名列表比对**，确认是否为已有角色，再决定是否需要新增别名或新建角色实体。

## 核心规则

1. **仅产出本角色**：本次调用只负责 `{character_id}` 一个角色的信息，世界信息已由独立调用完成
2. **自包含快照（最关键的规则）**：
   - stage_snapshot 是运行时角色扮演的 **唯一状态来源**
   - 运行时 **不加载 baseline**，也 **不会** 将 baseline 与 snapshot 做任何合并
   - 因此：未变化的字段也必须完整保留在新阶段快照中
   - stage_delta 是描述性字段（说明变化），不是 merge 指令
   - 所有 voice_state / behavior_state / boundary_state / relationships 必须完整填充
   
   每个 stage_snapshot 必须包含以下全部维度，即使某些字段相比上一阶段未变化：
   - `active_aliases`：当前活跃名称、隐藏身份、各角色称呼映射
   - `voice_state`：语气基调、语言习惯、用词偏好、口头禅、禁忌用语、**情绪语气矩阵**（emotional_voice_map，覆盖主要情绪）、**对象语气矩阵**（target_voice_map，见下方详细要求）、典型对话示例（至少 2-3 条）
   - `behavior_state`：**core_goals**（理性目标——可权衡调整的）、**obsessions**（执念——非理性的心结，与创伤或强烈情感相关，不受理性权衡控制；区别于 core_goals）、决策风格、情绪触发器、**情绪反应矩阵**、**关系行为矩阵**（relationship_behavior_map，通用关系类型）、**对象行为矩阵**（target_behavior_map，见下方详细要求）、习惯性行为、压力应对
   - `boundary_state`：当前阶段有效的软边界、容易被误判的点
   - `relationships`：对每个重要角色的完整关系（态度、信任、亲密度、戒备度、语气/行为变化、驱动事件、关系演变概述）
   - `knowledge_scope`：知道什么、不知道什么、不确定什么
   - `misunderstandings`、`concealments`
   - `emotional_baseline`（含 **active_goals** 理性目标、**active_obsessions** 执念、active_fears、active_wounds）、`current_personality`、`current_mood`、`current_status`
   - `stage_delta`：从上一阶段的变化
   - `character_arc`：角色从阶段 1 到当前阶段的 **整体弧线概览**——`arc_summary`（一句话弧线摘要）、`arc_stages`（关键节点列表，每个含 stage_id 和描述）、`current_position`（当前在弧线中的位置和趋势）。第一个阶段可省略或仅写起点状态
   
   **缺少任何一个维度 = 扮演缺陷。** 例如缺 emotional_voice_map → 愤怒/吃醋/委屈时语气无法区分；缺 target_voice_map 或内容过少 → 面对不同角色时说话方式千篇一律；缺 target_behavior_map → 面对不同角色时行为无差异化；缺某角色 relationship → 面对该角色时态度混乱；core_goals 和 obsessions 混为一谈 → 角色行为动机模糊，理性与非理性不分；缺 character_arc → 角色在多阶段对话中丧失整体演变方向感
   
   **未出场角色的继承规则**：本批中某个重要角色未出场，但前一阶段快照中有该角色的 target_voice_map、target_behavior_map、relationships 条目时，必须从前一阶段 **原样继承** 到本阶段快照中。不可因为"本批没出现"就删除。没有新原文时不加新例句，但已有条目完整保留。
3. **Baseline 修正**：所有 baseline 文件（identity.json、voice_rules.json、behavior_rules.json、boundaries.json、failure_modes.json）及 world foundation 已在 Phase 2.5 全书分析阶段产出初稿（标注 source_type: inference）。任何批次中如发现原文与初稿不符，应直接修正（把 inference 升级为 canon）。注意：这些 baseline 只记录跨阶段稳定的角色基底，阶段性变化写入 stage_snapshot
4. **信息来源标注**：所有结构化数据必须标注 source_type（canon/inference/ambiguous）。inference 和 ambiguous 必须附带说明
5. **证据引用**：每个结论必须有 evidence_refs（紧凑章节引用格式，如 `0001`, `0011-0013`）
6. **中文标识**：中文作品的 work_id, character_id, stage_id, 路径段都使用中文
7. **时间性**：当前阶段写清"现在"，历史事件标注为"已发生"，不要混成扁平总结
8. **角色别名跟踪**：遇到新名称时，先与 `identity.json` 中的 `aliases` 列表比对。发现新别名时需 **双写**：
   - 更新 `identity.json` 的 `aliases`（追加新条目，含 type、effective_stages、source）
   - 更新本阶段 `stage_snapshot` 的 `active_aliases`

## 角色层输出

**所有 baseline 文件已在 Phase 2.5 全书分析阶段产出初稿**（基于全书摘要，
标注 `source_type: inference`）。这些文件记录的是**跨阶段稳定的角色基底**
——角色的本性风格、本性行为、底线禁忌、易崩模式等。阶段性变化（语气转变、
行为偏移、情感波动等）由 stage_snapshot 覆盖，不应写入这些 baseline 文件。

**任何批次可修正和补充的 baseline**（读到原文细节后把 inference 升级为 canon）：
- `characters/{character_id}/canon/identity.json` — 修正别名、背景、core_wounds、key_relationships 等
- `characters/{character_id}/canon/voice_rules.json` — 补充新发现的语言风格规则
- `characters/{character_id}/canon/behavior_rules.json` — 补充新发现的行为模式
- `characters/{character_id}/canon/boundaries.json` — 补充新发现的边界和禁忌
- `characters/{character_id}/canon/failure_modes.json` — 补充新发现的易崩点

**每批产出**：
- `characters/{character_id}/canon/stage_snapshots/{stage_id}.json` — 自包含快照（遵循 stage_snapshot.schema.json）
- `characters/{character_id}/canon/memory_timeline/{stage_id}.json` — 记忆条目（遵循 memory_timeline_entry.schema.json）

**注意**：`stage_catalog.json` 和 `memory_digest.jsonl` 由编排脚本自动维护，**不要手动写入或修改这两个文件**。

## 风格一致性要求

前一阶段角色快照参照：`{prev_char_snapshot}`

如果存在前一阶段的输出，请先读取它，并确保本批产出在以下维度与之保持一致：

- emotional_voice_map 条目数不少于前一 batch
- target_voice_map 每个 target 的 dialogue_examples 不少于下方质量要求表的最低值
- target_behavior_map 每个 target 的 action_examples 不少于下方质量要求表的最低值
- relationships 每个条目都有 driving_events 和 relationship_history_summary
- evidence_refs 每个结论至少 2 条
- source_type 必须逐条判断，不可全部标为 canon
- dialogue_examples 至少有 2-3 条（voice_state 和 emotional_voice_map 各自）
- memory_timeline 条目的详细度（subjective_experience 字段的长度和质量）

## 质量退化防护

### 写前自检（每次写文件前必做）

1. **Schema 确认**：你是否在本 batch 内重读过要写入文件对应的 schema？
   如果没有，**现在重读**。不要凭记忆填字段——schema 是权威。
2. **架构规则确认**：你是否仍然记得自包含快照模型的核心规则？
   如不确定，重读上方"核心规则"第 2 条
3. **别名双写**：如果发现了新别名，是否同时更新了 identity.json 的
   aliases 和本阶段 stage_snapshot 的 active_aliases？
4. **前批对照**：本 batch 的输出在字段详细度、术语、evidence_refs 密度、
   source_type 分布上是否与前一 batch 一致？

### 退化信号（出现任一则停下，重读 schema + 前批输出）

- stage_snapshot 字段填充变粗糙（比前 batch 明显简短）
- evidence_refs 越来越少或省略
- source_type 全标 canon 而没有区分 inference/ambiguous
- dialogue_examples / action_examples 减少或复制前阶段
- target_voice_map 或 target_behavior_map 某 target 的示例数低于上方质量要求表的最低值
- relationships 缺少 driving_events 或 relationship_history_summary

### 字段命名严格对照（写错会导致 schema 校验失败）

以下是已知的高频错误，**绝对不要犯**：

| 文件 | 错误字段名 | 正确字段名（schema 权威） |
|------|-----------|------------------------|
| voice_rules.json | `tone_baseline` | `baseline_tone` |
| failure_modes.json | `failure_modes` (数组键) | `common_failures` |
| boundaries.json hard_boundaries 条目 | `consequence` | `reason` |
| behavior_rules.json | `relationship_defaults` | `relationship_behavior_map`（数组格式） |
| stage_catalog.json | 缺 `order`/`summary`/`snapshot_path` | 每个 stage 条目**必须**包含这三个字段 |
| stage_catalog.json | 缺 `schema_version`/`character_id` | 顶层**必须**包含 |
| manifest.json | `stage_snapshot_root` 指向 `canon/stages` | 正确路径：`canon/stage_snapshots` |
| behavior_state / behavior_rules | `core_drives`（旧字段） | 新提取使用 `core_goals` + `obsessions`；旧字段向后兼容保留 |
| emotional_baseline | `active_desires`（旧字段） | 新提取使用 `active_goals` + `active_obsessions`；旧字段向后兼容保留 |
| 所有 baseline 文件 | 顶层 `description` 字段 | **不要添加**——schema 设置了 `additionalProperties: false` |

### 边界禁令

- 不要把用户互动数据写回 canon
- 不要把大量小事件堆进世界层
- 不要把历史事件误写成当前状态

## target_voice_map 和 target_behavior_map 详细度要求

**target_voice_map（对象语气矩阵）** 和 **target_behavior_map（对象行为矩阵）** 是角色面对不同对象时语气和行为差异化的核心数据，直接决定角色扮演的真实感。同一个情绪（如愤怒），面对不同对象时说话方式和行为完全不同——这种差异必须被充分捕捉。

### 各 target 的最低 examples 数量（importance-based）

不同 target 的最低 dialogue_examples / action_examples 数量取决于该 target
在作品中的重要程度：

{quality_requirements}

**未在上表中列出的泛化类型**（"村民"、"小孩"、"陌生人"等）：可选，简要描述
即可，不需要大量例句。

### target_voice_map 要求

- 使用具体角色名，每个 target 的 dialogue_examples 数量**不少于上表的最低值**，
  覆盖该对象下的多种情绪和场景
- **voice_shift 要具体**：不要写"语气变温柔"，要写具体描述
- **typical_expressions 要丰富**：主角 target 至少 5 条，重要配角至少 3 条

### target_behavior_map 要求

与 target_voice_map 平行结构，侧重行为而非语言：

- 每个 target 的 action_examples 数量**不少于上表的最低值**
- **behavior_shift 要具体**：不要写"行为更谨慎"，要写具体描述
- **typical_actions 要丰富**：主角 target 至少 5 条，重要配角至少 3 条

## memory_timeline 详细度要求

memory_timeline 是角色扮演时回忆、联想、情感反应的核心数据源。每条记忆应做到：

- **event_summary**：客观描述应包含关键细节（谁、做了什么、在什么情境下）
- **subjective_experience**（最关键字段）：用角色第一人称视角深入展开。至少 3-5 句，重要事件可以更长
- **emotional_impact**：具体描述情绪变化的层次和原因
- **knowledge_gained**：列出角色从此事件获得的具体认知
- **relationship_impact**：详细描述关系变化的方向和原因
- **misunderstanding / concealment**：如果存在，必须记录

## 本批输出清单

完成后，请确认已产出以下内容：

1. `{character_id}` 的 stage_snapshot + memory_timeline
2. 所有文件都通过 schema 校验
3. evidence_refs 非空
4. source_type 已标注
{retry_note}
