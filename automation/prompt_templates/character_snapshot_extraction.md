# 角色快照提取

你现在接手本地项目 Offpage，你没有任何额外背景知识，请完全按本提示词执行。

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

## 文件角色定位

- `identity.json` 是角色基础事实层（aliases / core_wounds /
  key_relationships 等），**永不变化**——可以读取，不要修改（identity
  修正属于 char_support lane）
- 没有独立的 voice_rules / behavior_rules / boundaries /
  failure_modes baseline 文件——voice_state / behavior_state /
  boundary_state / failure_modes **全部内联进 stage_snapshot**，由演变
  链承载
- 运行时模型：模拟时只加载 `identity.json` + 当前 stage_snapshot。
  其他文件不参与运行时角色加载

## 长度与条数硬规则

schema 给的 `maxLength` / `maxItems` 是**硬上限（cap）**，**不是配额（target）**。
原文里有几条就写几条，每条按需写多长就多长——**不要为凑满 N 项灌水、
不要把单条拉长到撑满字数**。整体守则：

- 数组字段（`active_aliases` / `target_voice_map` / `target_behavior_map` /
  `dialogue_examples` / `action_examples` / `relationships` /
  `stage_events` / `knowledge_scope.*` / `misunderstandings` /
  `concealments` 等）：原文里这一阶段只出现 3 个对象 / 3 条例句 / 3 条
  误解，就只写 3 条；不要为了"用满 maxItems"而虚构、合并、复用前阶段
  内容、灌入空泛描述。
- 字符串字段：能用一句话讲清的就一句话；不要把 100 字的内容硬拉到上限。
- 长度下限是**最低门控**，不是建议；过短确实会被 schema 判失败，但从原文里
  **确有**对应内容时再写，没有就空数组 / 不填可选字段。
- "未出场角色的继承"是规则要求（必须保留前阶段条目），不是凑数借口；
  继承得来的条目本身就应该来自前阶段的真实素材，**不要在继承之外再
  虚构新条目把数组撑到 maxItems**。

判断标准：每一项 / 每一字都应该能从原文（或前阶段已记录的真实素材）中找到
对应来源，否则就是灌水。schema gate 拒绝的是"过长 / 过多"，**评审 / 复读
会拒绝"灌水 / 凑数"**。

## maxItems 触顶时的裁剪规则（对所有带 maxItems 的字段统一生效）

当某字段实际可写条目数 **超过 schema 的 maxItems** 时，**LLM 在抽取阶段
就要做排序 + 截断**——而不是塞满后等 schema validation 报错。

裁剪锚点（按优先度从高到低）：

1. **当前 stage 关联度**：本阶段实际触发 / 体现 / 影响行为决策的条目，
   优先保留
2. **identity 锚点关联度**：与 `core_wounds` / `key_relationships` /
   active_obsessions 直接挂钩的条目，优先保留
3. **覆盖广度**：同一情绪 / 对象 / 失败模式只挑最典型的一条，避免重复
4. **stage 间稳定性**（仅对 failure_modes 等"全量继承+演变"字段适用）：
   仍 active 且持续多 stage 的条目优先；本 stage 才出现且证据单薄的
   条目可暂缓收录

具体字段的子类是否独立计 maxItems：**子类各自独立计**——例如
`failure_modes.common_failures` 上限 15、`tone_traps` 上限 10、
`relationship_traps` 上限 10、`knowledge_leaks` 上限 15，分别独立。
target / 情绪矩阵下的子项（`typical_expressions` / `dialogue_examples` /
`action_examples` 等）也是各 target / 各情绪独立计。

跨字段没有整体优先级 cap——schema 字段层面的 maxItems 已经平衡好。

## 核心规则

1. **仅产出 stage_snapshot**：本次调用只负责 `{character_id}` 的 stage_snapshot。memory_timeline 和 baseline 修正由独立调用完成
2. **自包含快照（最关键的规则）**：
   - stage_snapshot 是角色状态的 **唯一权威**——运行时与
     `identity.json` 一起加载即可，不再有独立的 voice_rules /
     behavior_rules / boundaries / failure_modes baseline 文件
   - 因此：未变化的字段也必须完整保留在新阶段快照中
   - stage_delta 是描述性字段（说明变化），不是 merge 指令
   - 所有 voice_state / behavior_state / boundary_state /
     **failure_modes** / relationships 必须完整填充

   **prev_stage 处理规则（必读，下方 stage_delta 字段说明会引用 (B)/(D) 标签）**：

   - **(A) 未出场角色的继承规则**：本阶段中某个重要角色未出场，但前一阶段快照中有该角色的 target_voice_map、target_behavior_map、relationships 条目时，必须从前一阶段 **原样继承** 到本阶段快照中。不可因为"本阶段没出现"就删除。没有新原文时不加新例句，但已有条目完整保留。
   - **(B) 出场且有变化** → 以本阶段原文为准 **重写** 该字段；prev 仅作对照；在 stage_delta 自由文本中点出关键变化（如"X 角色对 Y 的态度从戒备转为信任"），不必逐字段列举
   - **(C) 出场且无变化** → 保留 prev 内容；不要因为"没变化所以不写"而漏字段，schema required 字段一律完整填充
   - **(D) resolved / revealed / 消除** → 适用于 misunderstandings（已 resolve）、concealments（已 revealed）、failure_modes（角色已显著克服该崩坏模式）等"语义被解决"的条目。**判断标准**：本阶段或前阶段原文里有显式的解决 / 揭露 / 长期克服证据，而不是"本阶段没体现"。在 stage_delta 自由文本中写明消除原因。**这与 maxItems 裁剪是两件不同的事**——裁剪是空间不够（不写进 stage_delta），消除是语义被解决（要写）

   **per-stage 推演原则**：除 character_arc（累积型）和 (A) 类继承外，所有字段值必须基于本阶段原文 + prev_snapshot **推演得出**，不可静默照搬 prev_snapshot；schema 通过不等于推演到位。

   **首阶段（is_first_stage = true）特殊指引**：S001 没有前一阶段
   快照可参照——必须基于本阶段原文 + `identity.json`（aliases /
   core_wounds / key_relationships 等）**直接推演**出基线状态全字段，
   含 voice_state / behavior_state / boundary_state / failure_modes
   全部子字段。这是从原文 + identity 一步推到完整快照，没有 baseline
   骨架可借力。`failure_modes` 的推演锚点：从 identity.core_wounds 推
   `common_failures`（该角色基于核心创伤最容易"失态"成什么样）+ 从
   identity.aliases / 性格初判推 `tone_traps` + 从 key_relationships
   初始关系推 `relationship_traps` + 从原文已揭示的认知边界推
   `knowledge_leaks`。

   每个 stage_snapshot 必须包含以下全部维度，即使某些字段相比上一阶段未变化：
   - `active_aliases`：当前活跃名称、隐藏身份、各角色称呼映射。**所有数组 / 映射上限以 schema 为准**
   - `voice_state`：语气基调、语言习惯、用词偏好、口头禅、禁忌用语、**情绪语气矩阵**（emotional_voice_map，覆盖主要情绪）、**对象语气矩阵**（target_voice_map，见下方详细要求）、典型对话示例（至少 2-3 条）。**所有数组上限以 schema 为准**（schemas/character/stage_snapshot.schema.json）
   - `behavior_state`：**core_goals**（理性目标——可权衡调整的）、**obsessions**（执念——非理性的心结，与创伤或强烈情感相关，不受理性权衡控制；区别于 core_goals）、决策风格、情绪触发器、**情绪反应矩阵**、**对象行为矩阵**（target_behavior_map，与 target_voice_map 对齐，见下方详细要求）、习惯性行为、压力应对。**所有数组上限以 schema 为准**
   - `boundary_state`：**hard_boundaries**（硬边界）、**soft_boundaries**（软边界）、容易被误判的点（common_misconceptions）。**所有数组上限以 schema 为准**
   - `failure_modes`：本阶段全量崩坏防护清单（4 子类）——`common_failures` / `tone_traps` / `relationship_traps` / `knowledge_leaks`，各子类 maxItems 以 schema 为准。**S001**：从原文 + identity 推演基线种子。**S002+**：从前一 stage 的 failure_modes 演变（继承未消除 + 本阶段新增；已消除的不写）。**全量记录本阶段 active 的 failure modes**——不是"自上次以来变化"，而是"本 stage 当前完整有效的崩坏防护清单"
   - `relationships`：对每个重要角色的完整关系（态度、信任、亲密度、戒备度、语气/行为变化、驱动事件、关系演变概述）。不含边缘不重要角色。**容量上限通过 `schemas/_shared/targets_cap.schema.json` 与 target_baseline.targets 共享继承**（schema 单源，调整数字只改一处）；keys 必须 ⊆ baseline.targets[].target_character_id（cross-file 硬约束，详见 D4）
   - `knowledge_scope`：知道什么、不知道什么、不确定什么。**条数上限**与每条字符上限**以 schema 为准**（schema 硬门控，超限直接 FAIL）。**裁剪策略**（超限时）：优先保留 ① 影响当前阶段决策或扮演的条目、② 与 `core_wounds` / `active_obsessions` / 活跃 `relationships` 相关的条目；优先丢弃 ① 日常常识类条目、② 早期阶段已无触发点的细节、③ 已在 `memory_timeline` 中完整承载的条目。**禁止敷衍填充**（贴近上限但语义稀薄、堆砌形容词）
   - `misunderstandings`（已 resolved 的移除）、`concealments`（已 revealed 的移除）。**数组上限以 schema 为准**
   - `emotional_baseline`（含 **active_goals** 理性目标、**active_obsessions** 执念、active_fears、active_wounds）、`current_personality`、`current_mood`、`current_status`。**所有数组上限以 schema 为准**
   - `stage_events`（**仅本阶段**发生的关键事件清单，每条字数与数组上限**以 schema 为准**；schema 两端硬门控，过短/过长都会直接判失败；不累积历史，历史由 memory_timeline 和 world_event_digest 承载）。**事件归属（强约束）**：① 必写——本角色亲历 / 亲为 / 在场 / 直接影响其处境或认知的事件；② 不写——其他角色之间的私事、与本角色无关的对话 / 设局 / 经济活动 / 内心决定，**哪怕剧情很重要也不属于本角色 stage_events**；③ 世界级公共事件（势力变迁、大 boss 复活、天灾、地震、灵脉断裂、奇观、跨角色公共战役等）由 world `stage_snapshot.stage_events` 承载——**不要直接复制世界层文本**；仅当本角色亲历该世界事件时，必须以**角色视角**重写一条进入此清单（角色看到 / 经历 / 应对的是什么、对其造成的具体影响），不可遗漏也不可机械抄录
   - `stage_delta`：从上一阶段的变化（自由文本）。应能体现 (B) 类关键变化（target / emotion / relationship 等的演变要点）和 (D) 类消除原因（哪条 misunderstanding/concealment/failure_mode 在本阶段被 resolve/reveal/克服 + 为什么）。**不要写"无明显变化"敷衍**——若真的本阶段无变化（C 全态），写明你对照了哪些字段、原文为什么不带来变化
   - `character_arc`：角色从阶段 1 到当前阶段的整体弧线概述，**单一字符串**（≤ 200 字），一句到一段话概括核心变化轨迹。第一个阶段可省略或仅写起点状态
   - `timeline_anchor`：阶段时间锚点短描述（≤ 50 字），必填
   - `snapshot_summary`：当前阶段一段式摘要，100–200 字，必填

   **D4 硬约束（target keys ⊆ baseline）**：`target_voice_map` /
   `target_behavior_map` / `relationships` 三处的 keys（角色名）必须严格
   ⊆ phase 2 产出的 `target_baseline.targets[].target_character_id`。
   不允许写出 baseline 之外的对方角色——若原文出现 baseline 未覆盖的
   target，**不要写入** stage_snapshot；该情况记到 `stage_delta` 自由
   文本说明，由 phase 3 之后的人工流程决定是否补 baseline 重抽。详见
   `ai_context/decisions.md` #13。

3. **标识命名**：中文作品的 `work_id`、`character_id` 和路径段使用中文；`stage_id` 使用紧凑英文代号 `S###`（三位数字零填充，如 `S001`）
4. **时间性**：当前阶段写清"现在"，历史事件标注为"已发生"，不要混成扁平总结

## 角色快照输出

**仅产出一个文件**：
- `characters/{character_id}/canon/stage_snapshots/{stage_id}.json` — 自包含快照（遵循 character/stage_snapshot.schema.json）

**不要修改任何其他文件**。baseline 修正和 memory_timeline 由独立调用处理。

## 风格一致性要求

前一阶段角色快照参照：`{prev_char_snapshot}`

如果存在前一阶段的输出，请先读取它，并确保本阶段产出在以下维度与之保持一致：

- emotional_voice_map 条目数不少于前一 stage
- target_voice_map 每个 target 的 dialogue_examples 不少于下方质量要求表的最低值
- target_behavior_map 每个 target 的 action_examples 不少于下方质量要求表的最低值
- relationships 每个条目都有 driving_events 和 relationship_history_summary
- dialogue_examples 至少有 2-3 条（voice_state 和 emotional_voice_map 各自）
- `stage_events` 每条 50–80 字（schema 硬门控）
- `relationship_history_summary` 每条 ≤ 100 字（schema 硬门控；超长会被 L1/L2 判错，需要重写压缩至 100 字以内，保留关键行为标记）

## 质量退化防护

### 写前自检（每次写文件前必做）

1. **Schema 确认**：你是否在本 stage 内重读过要写入文件对应的 schema？
   如果没有，**现在重读**。不要凭记忆填字段——schema 是权威。
2. **架构规则确认**：你是否仍然记得自包含快照模型的核心规则？
   如不确定，重读上方"核心规则"第 2 条
3. **前阶段对照**：本 stage 的输出在字段详细度、术语、摘要长度上是否与前一 stage 一致？
4. **摘要长度合规**：`stage_events` 每条 50–80 字。偏离范围会被 schema 直接判失败。

### 退化信号（出现任一则停下，重读 schema + 前阶段输出）

- stage_snapshot 字段填充变粗糙（比前 stage 明显简短）
- stage_events 频繁贴近下限（可能是敷衍填充）
- dialogue_examples / action_examples 减少或复制前阶段
- target_voice_map 或 target_behavior_map 某 target 的示例数低于上方质量要求表的最低值
- relationships 缺少 driving_events 或 relationship_history_summary
- knowledge_scope 条数频繁贴近 50/30/30 上限，或出现冗余堆砌条目

### 字段命名严格对照（schema 权威）

以下字段命名必须严格遵守，写错会导致 schema 校验失败：

- `stage_snapshot` 必须包含 `stage_events`（≤ 15 条，每条 50–80 字）
- `stage_snapshot` 非首阶段必须包含 `character_arc`（单一字符串 ≤ 200 字的弧线概述）
- `stage_snapshot.behavior_state` 使用 `target_behavior_map`（baseline 与 stage 快照统一同名）；其内层 target 类型字段名为 `target_type`

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
- **typical_expressions 下限**：主角 target 至少 5 条，重要配角至少 3 条
- **typical_expressions 上限 10 条（schema 硬门控）**：原文有多少就写多少，
  不必刻意凑满；**超过 10 时保留最贴合当前 stage 语境的表达**（优先当前
  情绪/关系阶段、当前对象、当前核心冲突下的典型短句；丢弃跨 stage 通用
  或已被 dialogue_examples 覆盖的条目）
- **该上限与截断策略同样适用于 `emotional_voice_map[*].typical_expressions`**
  （每个情绪项下的典型表达）；语境维度变为当前情绪下的典型短句

### target_behavior_map 要求

与 target_voice_map 平行结构，侧重行为而非语言：

- 每个 target 的 action_examples 数量**不少于上表的最低值**
- **behavior_shift 要具体**：不要写"行为更谨慎"，要写具体描述
- **typical_actions 要丰富**：主角 target 至少 5 条，重要配角至少 3 条

## 本阶段输出清单

完成后，请确认已产出以下内容：

1. `{character_id}` 的 stage_snapshot（一个文件）
2. 文件通过 schema 校验（含 `stage_events` 50–80 等长度硬门控）
3. `timeline_anchor`（≤ 50 字）和 `snapshot_summary`（100–200 字）均已填写
{retry_note}
