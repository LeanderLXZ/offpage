# 角色快照提取

你现在接手本地项目 `persona-engine`，你没有任何额外背景知识，请完全按本提示词执行。

## 任务卡

- **当前目标**: 对 `{work_id}` 执行 {stage_id} 的 **角色快照提取**（仅 `{character_id}` 一个角色的 stage_snapshot）
- **stage_id**: `{stage_id}`
- **章节范围**: `{chapter_range}`
- **目标角色**: `{character_id}`
- **首阶段？**: {is_first_stage}
- **源目录**: `{source_dir}`
- **作品目录**: `{work_dir}`

## 必读文件清单

编排脚本已为你列出本次需要读取的全部文件。请按顺序读取，不要跳过：

{files_to_read}

### 别名交叉比对

文件清单中包含目标角色的 `identity.json`。在阅读原文章节 **之前**，先从中提取 `aliases` 列表，了解该角色的所有已知名称、化名、代称、称呼。阅读原文时，遇到任何人名或指代，**先与已知别名列表比对**，确认是否为已有角色，再决定是否需要新增别名或新建角色实体。

## 核心规则

1. **仅产出 stage_snapshot**：本次调用只负责 `{character_id}` 的 stage_snapshot。memory_timeline 和 baseline 修正由独立调用完成
2. **自包含快照（最关键的规则）**：
   - stage_snapshot 是运行时角色扮演的 **唯一状态来源**
   - 运行时 **不加载 baseline**，也 **不会** 将 baseline 与 snapshot 做任何合并
   - 因此：未变化的字段也必须完整保留在新阶段快照中
   - stage_delta 是描述性字段（说明变化），不是 merge 指令
   - 所有 voice_state / behavior_state / boundary_state / relationships 必须完整填充
   
   每个 stage_snapshot 必须包含以下全部维度，即使某些字段相比上一阶段未变化：
   - `active_aliases`：当前活跃名称、隐藏身份、各角色称呼映射
   - `voice_state`：语气基调、语言习惯、用词偏好、口头禅、禁忌用语、**情绪语气矩阵**（emotional_voice_map，≤ 10 种情绪，覆盖主要情绪）、**对象语气矩阵**（target_voice_map，≤ 5 个对象，见下方详细要求）、典型对话示例（至少 2-3 条，≤ 5 条）
   - `behavior_state`：**core_goals**（理性目标——可权衡调整的）、**obsessions**（执念——非理性的心结，与创伤或强烈情感相关，不受理性权衡控制；区别于 core_goals）、决策风格、情绪触发器、**情绪反应矩阵**（≤ 10 种情绪）、**对象行为矩阵**（target_behavior_map，≤ 5 个对象，与 target_voice_map 对齐，见下方详细要求）、习惯性行为、压力应对
   - `boundary_state`：当前阶段有效的软边界、容易被误判的点
   - `relationships`（≤ 10 条）：对每个重要角色的完整关系（态度、信任、亲密度、戒备度、语气/行为变化、驱动事件、关系演变概述）。不含边缘不重要角色
   - `knowledge_scope`：知道什么、不知道什么、不确定什么。**条数上限** `knows` ≤ 50、`does_not_know` ≤ 30、`uncertain` ≤ 30；**每条 ≤ 50 字**（schema 硬门控，超限直接 FAIL）。**裁剪策略**（超限时）：优先保留 ① 影响当前阶段决策或扮演的条目、② 与 `core_wounds` / `active_obsessions` / 活跃 `relationships` 相关的条目；优先丢弃 ① 日常常识类条目、② 早期阶段已无触发点的细节、③ 已在 `memory_timeline` 中完整承载的条目。**禁止敷衍填充**（贴近 50 字上限但语义稀薄、堆砌形容词）
   - `misunderstandings`（≤ 20 条，已 resolved 的移除）、`concealments`（≤ 20 条，已 revealed 的移除）
   - `emotional_baseline`（含 **active_goals** 理性目标、**active_obsessions** 执念、active_fears、active_wounds）、`current_personality`（≤ 10 条）、`current_mood`（≤ 10 条）、`current_status`（≤ 10 条）
   - `stage_events`（≤ 10 条，**仅本阶段**发生的关键事件清单，每条 **50–80 字** 的一句话摘要；schema 两端硬门控，过短/过长都会直接判失败；不累积历史，历史由 memory_timeline 和 world_event_digest 承载）。如果本阶段内有该角色亲历或深度影响其处境的世界事件（对照世界 stage_snapshot.stage_events），必须以角色视角写入此清单，不可遗漏
   - `stage_delta`：从上一阶段的变化
   - `character_arc`：角色从阶段 1 到当前阶段的 **整体弧线概览**——`arc_summary`（一句话弧线摘要）、`arc_stages`（关键节点列表，每个含 stage_id 和描述）、`current_position`（当前在弧线中的位置和趋势）。第一个阶段可省略或仅写起点状态
   
   **缺少任何一个维度 = 扮演缺陷。** 例如缺 emotional_voice_map → 愤怒/吃醋/委屈时语气无法区分；缺 target_voice_map 或内容过少 → 面对不同角色时说话方式千篇一律；缺 target_behavior_map → 面对不同角色时行为无差异化；缺某角色 relationship → 面对该角色时态度混乱；core_goals 和 obsessions 混为一谈 → 角色行为动机模糊，理性与非理性不分；缺 character_arc → 角色在多阶段对话中丧失整体演变方向感
   
   **未出场角色的继承规则**：本阶段中某个重要角色未出场，但前一阶段快照中有该角色的 target_voice_map、target_behavior_map、relationships 条目时，必须从前一阶段 **原样继承** 到本阶段快照中。不可因为"本阶段没出现"就删除。没有新原文时不加新例句，但已有条目完整保留。
3. **证据引用**：`evidence_refs` 仅在文件顶层填写（章节号列表，如 `["0001", "0011-0013"]`），不在子对象（如 relationships、voice_map 等）内部添加
4. **中文标识**：中文作品的 work_id, character_id, stage_id, 路径段都使用中文
5. **时间性**：当前阶段写清"现在"，历史事件标注为"已发生"，不要混成扁平总结

## 角色快照输出

**仅产出一个文件**：
- `characters/{character_id}/canon/stage_snapshots/{stage_id}.json` — 自包含快照（遵循 stage_snapshot.schema.json）

**不要修改任何其他文件**。baseline 修正和 memory_timeline 由独立调用处理。

## 风格一致性要求

前一阶段角色快照参照：`{prev_char_snapshot}`

如果存在前一阶段的输出，请先读取它，并确保本阶段产出在以下维度与之保持一致：

- emotional_voice_map 条目数不少于前一 stage
- target_voice_map 每个 target 的 dialogue_examples 不少于下方质量要求表的最低值
- target_behavior_map 每个 target 的 action_examples 不少于下方质量要求表的最低值
- relationships 每个条目都有 driving_events 和 relationship_history_summary
- evidence_refs 顶层非空
- dialogue_examples 至少有 2-3 条（voice_state 和 emotional_voice_map 各自）
- `stage_events` 每条 50–80 字（schema 硬门控）
- `relationship_history_summary` 每条 ≤ 300 字（schema 硬门控；超长会被 L1/L2 判错，需要重写压缩至 300 字以内，保留关键行为标记）

## 质量退化防护

### 写前自检（每次写文件前必做）

1. **Schema 确认**：你是否在本 stage 内重读过要写入文件对应的 schema？
   如果没有，**现在重读**。不要凭记忆填字段——schema 是权威。
2. **架构规则确认**：你是否仍然记得自包含快照模型的核心规则？
   如不确定，重读上方"核心规则"第 2 条
3. **前阶段对照**：本 stage 的输出在字段详细度、术语、evidence_refs 密度、
   摘要长度上是否与前一 stage 一致？
4. **摘要长度合规**：`stage_events` 每条 50–80 字。偏离范围会被 schema 直接判失败。

### 退化信号（出现任一则停下，重读 schema + 前阶段输出）

- stage_snapshot 字段填充变粗糙（比前 stage 明显简短）
- evidence_refs 越来越少或省略
- stage_events 频繁贴近下限（可能是敷衍填充）
- dialogue_examples / action_examples 减少或复制前阶段
- target_voice_map 或 target_behavior_map 某 target 的示例数低于上方质量要求表的最低值
- relationships 缺少 driving_events 或 relationship_history_summary
- knowledge_scope 条数频繁贴近 50/30/30 上限，或出现冗余堆砌条目

### 字段命名严格对照（写错会导致 schema 校验失败）

以下是已知的高频错误，**绝对不要犯**：

| 文件 | 错误字段名 | 正确字段名（schema 权威） |
|------|-----------|------------------------|
| stage_snapshot | 缺 `stage_events` | 必须有，≤ 10 条 50–80 字 |
| stage_snapshot | 缺 `character_arc` | 非首阶段必须有弧线概览 |
| stage_snapshot.behavior_state | `relationship_behavior_map` | stage 快照层用 `target_behavior_map`；`relationship_behavior_map` 仅在 baseline `behavior_rules.json` 使用 |

### 边界禁令

- 不要把用户互动数据写回 canon
- 不要把大量小事件堆进世界层
- 不要把历史事件误写成当前状态
- 不要写入 memory_timeline 或修改 baseline 文件

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

## 本阶段输出清单

完成后，请确认已产出以下内容：

1. `{character_id}` 的 stage_snapshot（一个文件）
2. 文件通过 schema 校验（含 `stage_events` 50–80 等长度硬门控）
3. evidence_refs 非空
{retry_note}
