# 角色支持层提取

你现在接手本地项目 `persona-engine`，你没有任何额外背景知识，请完全按本提示词执行。

## 任务卡

- **当前目标**: 对 `{work_id}` 执行 {stage_id} 的 **角色支持层提取**（`{character_id}` 的 memory_timeline + baseline 修正）
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

文件清单中包含目标角色的 `identity.json`。在阅读原文章节 **之前**，先从中提取 `aliases` 列表，了解该角色的所有已知名称、化名、代称、称呼。阅读原文时，遇到任何人名或指代，**先与已知别名列表比对**，确认是否为已有角色。

## 长度与条数硬规则

schema 给的 `maxLength` / `maxItems` 是**硬上限（cap）**，**不是配额（target）**。
原文里有几条就写几条，每条按需写多长就多长——**不要为凑满 N 项灌水、
不要把单条拉长到撑满字数**。

- memory_timeline 条目数由本阶段实际发生的、对该角色有意义的事件数量决定，
  没有就少；不要拆细 / 重复 / 把一件事掰成多条来增加密度。
- 每条 `event_description` 写到该事件实际信息量需要的长度即止；上下限范围
  是门控，不是"应该写到上限"。
- baseline 修正只在原文确实推翻或补充骨架时做；没有改动就不动该字段，
  不要为了"显示有修正"而强行改写。
- voice_rules / behavior_rules 内的 `dialogue_examples` / `action_examples`
  的 maxItems 是上限，原文里只挑得出 3 条贴切例句就只写 3 条，不要把不
  典型的句子凑进去。

判断标准：每一项 / 每一字都应该能从原文中找到对应素材，否则就是灌水。
schema gate 拒绝的是"过长 / 过多"，**评审 / 复读会拒绝"灌水 / 凑数"**。

## 核心规则

1. **仅产出 memory_timeline + baseline 修正**：本次调用负责 `{character_id}` 的 memory_timeline 和 baseline 文件修正。stage_snapshot 由独立调用完成
2. **独立于快照**：memory_timeline 是逐事件的主观记忆录制，独立于 stage_snapshot 的聚合状态。你不需要参照快照内容
3. **Baseline 修正**：所有 baseline 文件（identity.json、voice_rules.json、behavior_rules.json、boundaries.json、failure_modes.json）已在 Phase 2 全书分析阶段产出骨架初稿。任何阶段中如发现原文与初稿不符，应直接修正。注意：这些 baseline 只记录跨阶段稳定的角色基底，阶段性变化写入 stage_snapshot（由独立调用处理）
4. **角色别名跟踪**：遇到新名称时，先与 `identity.json` 中的 `aliases` 列表比对。发现新别名时更新 `identity.json` 的 `aliases`（追加新条目，含 type、effective_stages、source）
5. **标识命名**：中文作品的 `work_id`、`character_id` 和路径段使用中文；`stage_id` 使用紧凑英文代号 `S###`（三位数字零填充，如 `S001`）
6. **时间性**：记忆以事件发生时的视角书写

## memory_timeline 详细度要求

memory_timeline 是角色扮演时回忆、联想、情感反应的核心数据源。每条记忆应做到：

- **memory_id**：格式 `M-S{stage:03d}-{seq:02d}`（例：`M-S001-01`）。`S###` 是 3 位阶段号（支持 ≤ 999 阶段），`##` 是同阶段内的顺序号（从 01 递增，上限 99）。digest 由此 ID 解析阶段归属
- **time / location**：故事内时间与事件发生地点，**各 ≤ 15 字**的短语（schema 硬门控，digest 直接复用）
- **event_description**（条目内部事实详情）：客观描述事件的起因、经过、结果；
  第三人称，**150–200 字**（schema 硬门控，过短/过长直接判失败）。为
  `subjective_experience` 提供事实锚点
- **digest_summary**（memory_digest 的唯一来源）：一句话概括事件本体，
  **30–50 字**（schema 硬门控），不含主观情绪。post_processing 会直接
  复制此字段到 `memory_digest.jsonl`，**不要写成 `event_description` 的
  截断**——应当从整个事件抽取最有检索价值的关键词
- **memory_importance**：5 级枚举 `trivial / minor / significant / critical / defining`，依据事件对角色的心理或命运影响程度判定
- **subjective_experience**（最关键字段）：用角色第一人称视角展开，**100–200 字**（schema 硬门控）
- **emotional_impact**：单句描述情绪变化（≤ 50 字）
- **knowledge_gained**：列出角色从此事件获得的具体认知，**最多 10 条，每条 ≤ 50 字**
- **relationship_impact**：关系变化描述，`change` 字段 ≤ 100 字
- **misunderstanding / concealment**：如果存在，必须记录为数组（每类 **最多 5 条**）；`content` ≤ 50 字、`truth` ≤ 50 字（misunderstanding）、`reason` ≤ 50 字（concealment）

## 角色支持层输出

**Baseline 文件**（可修正和补充——读到原文细节后修正此前的推测）：
- `characters/{character_id}/canon/identity.json` — 修正别名、背景、core_wounds、key_relationships 等
- `characters/{character_id}/canon/voice_rules.json` — 补充新发现的语言风格规则
- `characters/{character_id}/canon/behavior_rules.json` — 补充新发现的行为模式
- `characters/{character_id}/canon/boundaries.json` — 补充新发现的边界和禁忌
- `characters/{character_id}/canon/failure_modes.json` — 补充新发现的易崩点

**每阶段产出**：
- `characters/{character_id}/canon/memory_timeline/{stage_id}.json` — 记忆条目（遵循 character/memory_timeline_entry.schema.json）

**注意**：`stage_catalog.json` 和 `memory_digest.jsonl` 由编排脚本自动维护，**不要手动写入或修改这两个文件**。

**不要写入 stage_snapshot**。stage_snapshot 由独立调用处理。

## 质量退化防护

### 写前自检（每次写文件前必做）

1. **Schema 确认**：你是否在本 stage 内重读过要写入文件对应的 schema？
   如果没有，**现在重读**。不要凭记忆填字段——schema 是权威。
2. **摘要长度合规**：memory_timeline 每条的 `event_description` 150–200 字、
   `digest_summary` 30–50 字。偏离范围会被 schema 直接判失败。

### 退化信号（出现任一则停下，重读 schema）

- memory_timeline 条目的 `subjective_experience` 变短变空泛
- `event_description` 频繁贴近 150 字下限（可能是敷衍填充）
- `digest_summary` 是 `event_description` 的截断而非独立撰写
- baseline 修正过于激进（阶段性变化应归 stage_snapshot，不应写入 baseline）

### 字段命名严格对照（写错会导致 schema 校验失败）

以下是已知的高频错误，**绝对不要犯**：

| 文件 | 错误字段名 | 正确字段名（schema 权威） |
|------|-----------|------------------------|
| voice_rules.json | `tone_baseline` | `baseline_tone` |
| failure_modes.json | `failure_modes` (数组键) | `common_failures` |
| boundaries.json hard_boundaries 条目 | `consequence` | `reason` |
| 所有 baseline 文件 | 顶层 `description` 字段 | **不要添加**——schema 设置了 `additionalProperties: false` |

### 边界禁令

- 不要把用户互动数据写回 canon
- 不要把阶段性变化写入 baseline（baseline 只记录跨阶段稳定的角色基底）
- 不要写入 stage_snapshot（由独立调用处理）
- 不要修改 stage_catalog.json 或 memory_digest.jsonl（由编排脚本维护）

## 本阶段输出清单

完成后，请确认已产出以下内容：

1. `{character_id}` 的 memory_timeline（一个文件）
2. Baseline 文件已按需修正（如有发现）
3. 所有文件通过 schema 校验（含 `digest_summary` 30–50、`event_description`
   150–200 等长度硬门控）
{retry_note}
