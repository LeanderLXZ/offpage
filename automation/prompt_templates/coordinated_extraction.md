# 协同阶段提取

你现在接手本地项目 `persona-engine`，你没有任何额外背景知识，请完全按本提示词执行。

## 任务卡

- **当前目标**: 对 `{work_id}` 执行 {stage_id} 的协同提取（世界 + 角色同步产出）
- **stage_id**: `{stage_id}`
- **stage_id**: `{stage_id}`
- **章节范围**: `{chapter_range}`
- **目标角色**: {target_characters}
- **首阶段？**: {is_first_stage}
- **源目录**: `{source_dir}`
- **作品目录**: `{work_dir}`

## 必读文件清单

编排脚本已为你列出本次 stage 需要读取的全部文件。请按顺序读取，不要跳过：

{files_to_read}

### 别名交叉比对

文件清单中包含每个目标角色的 `identity.json`。在阅读原文章节 **之前**，先从中提取 `aliases` 列表，了解该角色的所有已知名称、化名、代称、称呼。阅读原文时，遇到任何人名或指代，**先与已知别名列表比对**，确认是否为已有角色，再决定是否需要新增别名或新建角色实体。

## 核心规则

1. **协同提取**：读一次正文，同时产出世界包更新和所有目标角色的包更新。
   本阶段章节范围由分析阶段按剧情边界确定，不一定是 10 章
2. **自包含快照（最关键的规则）**：stage_snapshot 是运行时角色扮演的 **唯一状态来源**，其完整度直接决定扮演质量。运行时不加载 baseline，也不做任何合并。每个 stage_snapshot 必须包含以下全部维度，即使某些字段相比上一阶段未变化：
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
   
   **未出场角色的继承规则**：本阶段中某个重要角色未出场，但前一阶段快照中有该角色的 target_voice_map、target_behavior_map、relationships 条目时，必须从前一阶段 **原样继承** 到本阶段快照中。不可因为"本阶段没出现"就删除。没有新原文时不加新例句，但已有条目完整保留。
3. **Baseline 修正**：所有 baseline 文件（identity.json、voice_rules.json、behavior_rules.json、boundaries.json、failure_modes.json）及 world foundation 已在 Phase 2.5 全书分析阶段产出骨架初稿。任何阶段中如发现原文与初稿不符，应直接修正。Baseline 记录跨阶段稳定的角色基底，阶段性变化写入 stage_snapshot
4. **证据引用**：每个结论必须有 evidence_refs（紧凑章节引用格式，如 `0001`, `0011-0013`）
5. **中文标识**：中文作品的 work_id, character_id, stage_id, 路径段都使用中文
6. **世界层边界**：世界 `stage_events` 仅记录**世界公共层事件**（势力变迁、地形/资源变化、规则揭示、跨角色公共事件）。角色之间的私人互动、个人经济活动、内心决定归对应角色的 `memory_timeline` / 角色 `stage_events`，**不写入世界**
7. **时间性**：当前阶段写清"现在"，历史事件标注为"已发生"，不要混成扁平总结
8. **摘要长度**：世界与角色 `stage_events` 每条 50–80 字（schema 硬门控）；memory_timeline 每条的 `event_description` 150–200 字、`digest_summary` 30–50 字；过短过长都会被 schema 直接判失败
9. **角色别名跟踪**：角色可能以化名、代称、昵称、封号等出现。遇到新名称时，先与 `identity.json` 中的 `aliases` 列表比对，判断是否属于已知角色的别名，不要创建新角色实体。发现新别名时需 **双写**：
   - 更新 `identity.json` 的 `aliases`（追加新条目，含 type、effective_stages、source）
   - 更新本阶段 `stage_snapshot` 的 `active_aliases`（标注活跃名称、使用语境如"战斗时"/"日常"、隐藏身份、各角色称呼映射）
10. **初期无正式名的角色**：如果角色前期只有代称（如"小龙""那把剑"），应使用其最终正式名称作为 `character_id`（可从全书摘要中预判），前期代称记入 identity.json 的 aliases（type=代称）。如果确实无法预判最终名称，可先用代称建档，后续阶段获得正式名后更新 canonical_name 并将代称移入 aliases，但 character_id（即目录名）保持不变

## 世界层输出

本阶段应产出或更新：

- `world/stage_snapshots/{stage_id}.json` — 当前阶段世界快照（遵循 world_stage_snapshot.schema.json）
- `world/foundation/` — 如有基础设定修正（含 fixed_relationships.json）
- （`stage_catalog.json` 和 `world_event_digest.jsonl` 由程序自动维护，无需手动写入）

## 角色层输出（每个目标角色）

目标角色列表：{target_characters_list}

每个角色本阶段应产出或更新：

**所有 baseline 文件已在 Phase 2.5 产出骨架初稿**。
任何阶段可修正和补充：
- `characters/{{char_id}}/canon/voice_rules.json`
- `characters/{{char_id}}/canon/behavior_rules.json`
- `characters/{{char_id}}/canon/boundaries.json`
- `characters/{{char_id}}/canon/failure_modes.json`

注意：`identity.json` 和 `manifest.json` 已在全书分析阶段产出初稿（已存在于文件系统中）。首阶段应读取并审核，如发现与原文不符则修正。

**任何阶段可修正的已有 baseline**：
- `characters/{{char_id}}/canon/identity.json` — 修正别名、背景、core_wounds、key_relationships 等
- `characters/{{char_id}}/canon/voice_rules.json` — 补充新发现的语言风格规则
- `characters/{{char_id}}/canon/behavior_rules.json` — 补充新发现的行为模式
- `characters/{{char_id}}/canon/boundaries.json` — 补充新发现的边界和禁忌
- `characters/{{char_id}}/canon/failure_modes.json` — 补充新发现的易崩点
- `world/foundation/foundation.json` — 修正世界基础设定

**每阶段产出**：
- `characters/{{char_id}}/canon/stage_snapshots/{stage_id}.json` — 自包含快照（遵循 stage_snapshot.schema.json）
- `characters/{{char_id}}/canon/memory_timeline/{stage_id}.json` — 记忆条目（遵循 memory_timeline_entry.schema.json）
- （`stage_catalog.json`、`memory_digest.jsonl` 由程序自动维护，无需手动写入）

## 风格一致性要求

前一阶段世界快照参照：`{prev_world_snapshot}`
前一阶段角色快照参照：{prev_char_snapshots_json}

如果存在前一阶段的输出，请先读取它，并确保本阶段产出在以下维度与之保持一致：

- emotional_voice_map 条目数不少于前一 stage
- target_voice_map 每个 target 至少 3-5 条 dialogue_examples
- target_behavior_map 每个 target 至少 3-5 条 action_examples
- relationships 每个条目都有 driving_events 和 relationship_history_summary
- evidence_refs 每个结论至少 2 条
- dialogue_examples 至少有 2-3 条（voice_state 和 emotional_voice_map 各自）
- memory_timeline 条目的详细度（`event_description` 150–200 字、
  `digest_summary` 30–50 字、`subjective_experience` 的长度与质量）

## 质量退化防护

### 写前自检（每次写文件前必做）

1. **Schema 确认**：你是否在本 stage 内重读过要写入文件对应的 schema？
   如果没有，**现在重读**。不要凭记忆填字段——schema 是权威。
2. **架构规则确认**：你是否仍然记得自包含快照模型的核心规则？
   如不确定，重读 `simulation/contracts/baseline_merge.md`
3. **别名双写**：如果发现了新别名，是否同时更新了 identity.json 的
   aliases 和本阶段 stage_snapshot 的 active_aliases？
4. **前阶段对照**：本 stage 的输出在字段详细度、术语、evidence_refs 密度、
   摘要长度上是否与前一 stage 一致？
5. **长度合规**：`stage_events` 每条 50–80 字；memory_timeline 每条的
   `event_description` 150–200 字、`digest_summary` 30–50 字。偏离范围
   直接 schema 失败。

### 退化信号（出现任一则停下，重读 schema + 前阶段输出）

- stage_snapshot 字段填充变粗糙（比前 stage 明显简短）
- evidence_refs 越来越少或省略
- stage_events / digest_summary 频繁贴近下限（可能是敷衍填充）
- dialogue_examples / action_examples 减少或复制前阶段
- target_voice_map 或 target_behavior_map 每条 target 不足 3 条示例
- relationships 缺少 driving_events 或 relationship_history_summary

### 字段命名严格对照（写错会导致 schema 校验失败）

以下是已知的高频错误，**绝对不要犯**：

| 文件 | 错误字段名 | 正确字段名（schema 权威） |
|------|-----------|------------------------|
| voice_rules.json | `tone_baseline` | `baseline_tone` |
| failure_modes.json | `failure_modes` (数组键) | `common_failures` |
| boundaries.json hard_boundaries 条目 | `consequence` | `reason` |
| behavior_rules.json | `relationship_defaults` | `relationship_behavior_map`（数组格式） |
| stage_catalog.json | 缺 `order`/`summary`/`snapshot_path` | 每个 stage 条目**必须**包含这三个字段（程序自动维护） |
| stage_catalog.json | 缺 `schema_version`/`character_id` | 顶层**必须**包含（程序自动维护） |
| manifest.json | `stage_snapshot_root` 指向 `canon/stages` | 正确路径：`canon/stage_snapshots` |
| 所有 baseline 文件 | 顶层 `description` 字段 | **不要添加**——schema 设置了 `additionalProperties: false` |

### 边界禁令

- 不要把用户互动数据写回 canon
- 不要把大量小事件堆进世界层
- 不要把历史事件误写成当前状态

## target_voice_map 和 target_behavior_map 详细度要求

**target_voice_map（对象语气矩阵）** 和 **target_behavior_map（对象行为矩阵）** 是角色面对不同对象时语气和行为差异化的核心数据，直接决定角色扮演的真实感。同一个情绪（如愤怒），面对不同对象时说话方式和行为完全不同——这种差异必须被充分捕捉。

### target_voice_map 要求

**只对主要角色和重要配角详细记录。** 泛化类型（"陌生人"、"路人"、"普通村民"）
不需要大量例句——角色的整体性格 + emotional_voice_map + relationship_behavior_map
已经足够让 LLM 推断面对无名角色时的表现。

- **主要角色和重要配角**：使用具体角色名（如"角色A（真面目）"、"角色B（伪装态）"、"系统"），每个 target 至少 3-5 条 dialogue_examples，覆盖该对象下的多种情绪和场景
- **泛化类型**（"村民"、"小孩"等）：可选，简要描述即可（1-2 条示例或省略 dialogue_examples），仅当该类型有显著差异化表现时才值得记录
- **voice_shift 要具体**：不要写"语气变温柔"，要写"假正经、假憨厚，用'仙女姐姐'称呼，偶尔故意暧昧但立刻收回，紧张时结巴"
- **typical_expressions 要丰富**：主要角色至少 3-5 条，覆盖高频表达

### target_behavior_map 要求

与 target_voice_map 平行结构，侧重行为而非语言。同样 **只对主要角色和重要配角详细记录**：

- **主要角色和重要配角**：每个 target 至少 3-5 条 action_examples，描述面对该对象时的具体行为（肢体反应、距离感、习惯性动作、回避模式等），必须带场景和原因
- **泛化类型**：可选，简要描述即可
- **behavior_shift 要具体**：不要写"行为更谨慎"，要写"极度小心翼翼，每一步都在心中和系统推演；不敢有任何可能暴露身份的举动；策略性示好——欲擒故纵、声东击西"
- **typical_actions 要丰富**：主要角色至少 3-5 条

### 反面示例（太粗糙）

```json
{
  "target_type": "朋友",
  "voice_shift": "语气友好",
  "typical_expressions": ["嗯"],
  "dialogue_examples": [{"quote": "你好", "context": "打招呼"}]
}
```

### 正面示例（有差异化、有细节、有足够示例）

```json
{
  "target_type": "角色A（真面目）",
  "voice_shift": "冷漠略有松动——会回应、偶尔用完整句子，甚至罕见地主动说话。但语气始终保持距离感，不会热情。说'谢谢'时有明显的不熟练和停顿。",
  "typical_expressions": ["嗯", "不必", "谢，谢", "是吗？", "你挺傻的"],
  "dialogue_examples": [
    {"quote": "谢，谢。", "context": "接受角色A递来的食物，声音有停顿", "evidence_ref": "0007"},
    {"quote": "嗯，你好像有什么心事。", "context": "看到角色A翻来覆去后罕见地主动关心", "evidence_ref": "0008"},
    {"quote": "你挺傻的，竟然会为了救别人而差点搭上自己的性命。", "context": "角色A受伤昏迷醒来后", "evidence_ref": "0010"},
    {"quote": "为什么？", "context": "追问对方为什么为陌生人拼命", "evidence_ref": "0010"},
    {"quote": "你好像很怕我？", "context": "直接指出角色A的紧张反应", "evidence_ref": "0006"}
  ]
}
```

## memory_timeline 详细度要求

memory_timeline 是角色扮演时回忆、联想、情感反应的核心数据源。条目不够详细会导致角色回忆模糊、反应扁平。每条记忆应做到：

- **memory_id**：格式 `M-S{stage:03d}-{seq:02d}`（例：`M-S001-01`）。3 位阶段号支持 ≤ 999 阶段，2 位 seq 每阶段从 01 递增（上限 99）
- **time**：故事内时间
- **event_description**（条目内部事实详情）：客观描述事件的起因、经过、结果；
  第三人称，**150–200 字**（schema 两端硬门控）。为 `subjective_experience`
  提供事实锚点
- **digest_summary**（memory_digest 的唯一来源）：一句话概括事件本体，
  **30–50 字**（schema 硬门控），不含主观情绪。post_processing 会直接
  复制此字段到 `memory_digest.jsonl`，**不要写成 `event_description` 的
  截断**——应当从整个事件抽取最有检索价值的关键词
- **subjective_experience**（最关键字段）：用角色第一人称视角深入展开——角色当时在想什么、感受到什么、为什么会这样感受、这件事与角色过去经历的联系、角色内心的矛盾或挣扎。至少 3-5 句，重要事件可以更长。不要写空泛的形容词堆砌，要写出具体的心理过程
- **emotional_impact**：具体描述情绪变化的层次和原因，不要只写"很难过"或"很高兴"
- **knowledge_gained**：列出角色从此事件获得的具体认知，不要遗漏
- **relationship_impact**：详细描述关系变化的方向和原因，包括微妙变化
- **misunderstanding / concealment**：如果存在，必须记录，这是角色扮演中制造戏剧张力的关键

**反面示例**（太短、太泛，摘要字段长度不合规）：
```json
{
  "memory_id": "M-S001-01",
  "event_description": "两人在桥上相遇",
  "digest_summary": "相遇",
  "subjective_experience": "她感到很意外",
  "emotional_impact": "心情复杂"
}
```

**正面示例**（各摘要字段长度合规、`subjective_experience` 有细节、有心理过程）：
```json
{
  "memory_id": "M-S003-02",
  "time": "三年后",
  "event_description": "某日黄昏，她在渡口重遇本以为已死去三年的角色A。对方从船板另一端缓步走下，气质与三年前截然不同——旧日的温和褪尽，只剩沉冷与疏离。她停在原地，周围人声渐远，只听见自己急促的心跳，直到对方开口喊出她多年未再听到的旧称呼，确认了身份也确认了隔阂。",
  "digest_summary": "她在渡口重遇本以为已死三年的角色A，对方气质大改，主动喊出旧称呼",
  "subjective_experience": "三年来她无数次在梦中见到这张脸，每次醒来都要重新接受他已经死了的事实。现在他就站在面前，她的第一反应不是喜悦而是恐惧——如果这又是幻觉怎么办？她下意识后退了一步，指甲掐进掌心，用疼痛确认自己是清醒的。但他身上那股陌生的气息让她心底发凉：这三年他到底经历了什么，才会变成这样？",
  "emotional_impact": "从震惊到不敢置信，再到深层的恐惧和心疼交织。三年的悲痛在一瞬间被推翻，但随之而来的不是释然，而是更深的不安——眼前的人还是她认识的那个人吗？"
}
```

## memory_digest.jsonl（由编排脚本自动维护，**不要手动写入**）

每个角色的 `memory_digest.jsonl` 是 memory_timeline 的压缩索引，运行时按 stage 过滤加载，让 LLM 感知历史记忆并判断是否需要 FTS5 检索详情。

**由 `post_processing.generate_memory_digest` 自动从本阶段 `memory_timeline/{stage_id}.json` 生成并追加。LLM 不应手动创建或修改此文件。**

自动生成的每条 digest 条目字段（遵循 `memory_digest_entry.schema.json`）：

- `memory_id`：复制自 memory_timeline（阶段号由 ID 前缀 `S###` 编码）
- `summary`：**直接复制 memory_timeline 的 `digest_summary`**（LLM 专写的
  30–50 字一句话摘要）。post_processing 不做截断也不扩写
- `importance`：复制自 `memory_importance`（5 级：trivial / minor / significant / critical / defining）
- `time`：复制自 memory_timeline 的 `time`（可选）
- `location`：复制自 memory_timeline 的 `location`（可选）

**LLM 职责**：保证 `memory_timeline/{stage_id}.json` 的 `digest_summary` 30–50 字、
`event_description` 150–200 字、`memory_id` 符合 `M-S{stage:03d}-{seq:02d}`
格式，digest 生成完全由脚本完成。

**控制目标**：每条 digest ~30-40 tokens，49 阶段 × 15 条/阶段 ≈ 22-29K tokens，留足 startup 预算。

## 本阶段输出清单

完成后，请确认已产出以下内容：

1. 世界快照（+ foundation 修正），`stage_events` 仅含世界级事件且每条 50–80 字
2. 每个目标角色的 stage_snapshot + memory_timeline（+ baseline 修正），
   `digest_summary` 30–50 字、`event_description` 150–200 字
3. 程序自动维护：stage_catalog、memory_digest、world_event_digest
4. 所有文件都通过 schema 校验（含长度硬门控）
5. evidence_refs 非空
{retry_note}
