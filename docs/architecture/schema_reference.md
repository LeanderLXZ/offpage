# Schema 参考文档

本文档是 `schemas/` 目录下所有 JSON Schema 的功能说明与用途索引。
Schema 文件本身是权威定义，本文档仅提供快速导航。

## 作品级 Schema

### work_manifest.schema.json

**用途**：作品入库 manifest。
**位置**：`sources/works/{work_id}/manifest.json`
**关键字段**：work_id, title, language, source_types, ingestion_status

---

### world_stage_catalog.schema.json

**用途**：世界阶段目录，列出作品的所有可选阶段。仅用于 bootstrap 阶段选择，运行时不加载。
**位置**：`works/{work_id}/world/stage_catalog.json`
**关键字段**：stages[].stage_id, stages[].title, stages[].summary

---

### world_stage_snapshot.schema.json

**用途**：世界阶段快照，描述某个阶段下的世界状态。
**位置**：`works/{work_id}/world/stage_snapshots/{stage_id}.json`
**关键字段**：
- `snapshot_summary` — 阶段的世界状态概述
- `foundation_corrections` — 对基础设定的修正
- `stage_events` — 本阶段事件（**唯一事件清单**，每条 **50–80 字**一句话，schema 硬门控；**仅收录世界公共层事件**，角色私事/内心决定应写入该角色 memory_timeline；既是快照内容又是 `world_event_digest.jsonl` 的直接来源，1:1 复制）
- `current_world_state` — 当前阶段的世界总体状态
- `relationship_shifts` — 关注的人物关系转变
- `character_status_changes` — 人物状态变化（生死、等级等）
- `location_changes`, `map_changes` — 地理变化
- `evidence_refs` — 章节号列表

---

### fixed_relationships.schema.json

**用途**：世界级固定关系网络（血缘、宗族、师徒、势力从属等不随阶段变化的结构性关系）。
**位置**：`works/{work_id}/world/foundation/fixed_relationships.json`
**关键字段**：relationships[].relationship_id, relationships[].type, relationships[].parties, relationships[].description
**生命周期**：Phase 2.5 产出骨架，后续阶段可修正。运行时 Tier 0 加载。

---

### world_event_digest_entry.schema.json

**用途**：世界事件压缩摘要条目——从世界 stage_snapshot `stage_events` 程序化生成的精简索引。
**位置**：`works/{work_id}/world/world_event_digest.jsonl`
**格式**：JSONL，每行一条事件摘要。
**运行时**：启动时 stage 1..N 过滤加载（loader 从 `event_id` 的 `S###` 前缀解析阶段号，不依赖单独的 `stage_id` 字段）。

**关键字段**：
- `event_id` — 格式 `E-S{stage:03d}-{seq:02d}`（例：`E-S003-02`）；阶段号编码在 ID 中
- `summary` — 事件精简摘要（**50–80 字**，1:1 复制自世界快照 `stage_events`）
- `importance` — 5 级重要度（`trivial` / `minor` / `significant` / `critical` / `defining`）
- `time` — 故事内时间（可选）
- `location` — 事件地点（可选）
- `involved_characters` — 涉及的角色（可选）

---

## 角色级 Schema

### character_manifest.schema.json

**用途**：角色包 manifest。
**位置**：`works/{work_id}/characters/{character_id}/manifest.json`

---

### identity.schema.json

**用途**：角色基线身份信息（不变层）。
**位置**：`characters/{character_id}/canon/identity.json`
**运行时**：始终加载。

**别名系统**：`aliases` 字段为结构化对象数组，每条记录包含：
- `name` — 名称文本
- `type` — 类型（本名/化名/代称/称呼/封号/道号/武器名/其他）
- `effective_stages` — 生效阶段范围（null=全阶段）
- `source` — 来源说明
- `used_by` — 使用该称呼的角色列表（仅对称呼类型有意义）

`character_manifest.json` 的 `aliases` 保持扁平字符串数组用于快速查找。

**核心创伤**：`core_wounds` 字段记录跨全故事始终影响角色行为的根源性心理
创伤，每条含 `wound`、`origin`（成因）、`behavioral_impact`（行为影响）、
`source_type`。不同于 stage_snapshot 中的 `active_wounds`（随阶段演变），
core_wounds 记录最底层的创伤根源。

**核心人物关系**：`key_relationships` 字段记录对角色有重大影响的跨全故事
关系概览，每条含 `target`、`initial_relationship`、`relationship_arc`
（全局演变弧线）、`turning_points`、`source_type`。不同于 stage_snapshot
中的 `relationships`（记录某一阶段的关系状态），key_relationships 提供
关系的全局演变轨迹。

---

### voice_rules.schema.json

**用途**：角色语言风格的提取锚点（baseline）。
**位置**：`characters/{character_id}/canon/voice_rules.json`
**运行时**：**不加载**。运行时使用 stage_snapshot 中的 `voice_state`。

---

### behavior_rules.schema.json

**用途**：角色行为规则的提取锚点（baseline）。
**位置**：`characters/{character_id}/canon/behavior_rules.json`
**运行时**：**不加载**。运行时使用 stage_snapshot 中的 `behavior_state`。

**目标与执念分离**：`core_goals`（理性目标，可权衡调整）与
`obsessions`（非理性心结，不受权衡控制）是两个独立字段。stage_snapshot
中的 `behavior_state` 同样维护 `core_goals` / `obsessions`，
`emotional_baseline` 维护 `active_goals` / `active_obsessions`。

---

### boundaries.schema.json

**用途**：角色行为边界（硬边界 + 软边界）的提取锚点。
**位置**：`characters/{character_id}/canon/boundaries.json`
**运行时**：hard_boundaries 始终加载；soft_boundaries 由 stage_snapshot 的 `boundary_state` 提供。

---

### failure_modes.schema.json

**用途**：AI 扮演该角色时容易犯的错误清单。
**位置**：`characters/{character_id}/canon/failure_modes.json`
**运行时**：始终加载。

---

### stage_catalog.schema.json

**用途**：角色阶段目录，与世界 stage_catalog 对应。
**位置**：`characters/{character_id}/canon/stage_catalog.json`
**关键字段**：stages[].stage_id（必须与世界的 stage_id 一致）

---

### stage_snapshot.schema.json

**用途**：角色阶段快照——**自包含**的完整角色状态。
**位置**：`characters/{character_id}/canon/stage_snapshots/{stage_id}.json`
**运行时**：这是运行时加载角色状态的核心文件。

**核心原则**：
- 每个快照必须自包含，包含完整的状态（即使与上一阶段无变化）
- 运行时直接加载，不需要与 baseline 合并
- Baseline 文件是提取锚点，不在运行时加载
- `target_voice_map` 和 `target_behavior_map` 按用户扮演角色**过滤加载**
  （只加载匹配条目）；如果当前快照缺少匹配条目，引擎向前扫描最近包含
  该条目的快照（fallback，纯代码 I/O，不产生额外 LLM 调用）
- 只对主要角色和重要配角详细记录（每 target 至少 3-5 条示例）；
  泛化类型（陌生人、路人）简要描述即可

**关键 section**：

| Section | 说明 |
|---------|------|
| `active_aliases` | 本阶段活跃名称（primary_name、active_names、hidden_identities、known_as 称呼映射） |
| `voice_state` | 语气基调、语言习惯、用词偏好、口头禅、禁忌用语、情绪语气矩阵（emotional_voice_map，≤ 10）、**对象语气矩阵**（target_voice_map，≤ 5，按具体角色区分，每 target 至少 3-5 条对话示例）、典型对话示例（≤ 5） |
| `behavior_state` | **core_goals**（理性目标）、**obsessions**（执念）、决策风格、情绪触发器、情绪反应矩阵（emotional_reaction_map，≤ 10）、**对象行为矩阵**（target_behavior_map，≤ 5，与 target_voice_map 平行且对齐，按具体角色区分，每 target 至少 3-5 条行为示例）、习惯性行为、压力应对 |
| `boundary_state` | 当前阶段有效的软边界、容易被误判的点 |
| `relationships` | 对每个重要角色的完整关系状态（态度、信任、亲密度、语气变化、行为变化、驱动事件、关系演变概述） |
| `misunderstandings` | 角色持有的误解（主观认知 vs 客观事实） |
| `concealments` | 角色主动隐瞒的事情 |
| `stage_delta` | 从上一阶段的变化摘要（信息性） |
| `character_arc` | 角色从阶段 1 到当前的整体弧线概览（arc_summary、arc_stages 关键节点、current_position） |
| `stage_events` | 本阶段发生的事件（每条 50–80 字，schema 硬门控；不累积历史） |

---

### memory_timeline_entry.schema.json

**用途**：角色记忆条目——角色第一人称主观视角的归纳记忆（不是原文复制）。
**位置**：`characters/{character_id}/canon/memory_timeline/{stage_id}.json`
**格式**：JSON 数组，每个元素为一条记忆。
**运行时**：启动加载近期 2 个阶段（N + N-1）全文；远期阶段通过
`memory_digest.jsonl` 摘要感知，详情通过 FTS5 按需检索。

**关键字段**：
- `memory_id` — 格式 `M-S{stage:03d}-{seq:02d}`（例：`M-S003-02`）
- `time` — 故事内时间（可选）
- `location` — 事件发生地点
- `event_description` — 客观事件描述（**150–200 字**，schema 硬门控）
- `digest_summary` — 用于 memory_digest 的精简摘要（**30–50 字**，schema 硬门控；独立撰写，聚焦可检索关键词，**不是** `event_description` 的机械截断）
- `subjective_experience` — 角色对事件的主观体验（第一人称视角，核心字段，不限长度）
- `emotional_impact` — 情感影响
- `misunderstanding` — 是否产生了误解
- `concealment` — 是否选择隐瞒
- `memory_importance` — 重要程度（trivial ~ defining）
- `scene_refs` — 关联的 scene_archive scene_id（追溯到原文）

**归纳要求**：角色第一人称主观视角，是归纳不是原文复制。必须包含心理活动
和态度变化的因果。篇幅由事件复杂度决定，不设硬性字数限制。

---

### memory_digest_entry.schema.json

**用途**：记忆压缩摘要条目——从 memory_timeline 自动提取的精简索引。
**位置**：`characters/{character_id}/canon/memory_digest.jsonl`
**格式**：JSONL，每行一条压缩摘要。
**运行时**：启动时 stage 1..N 过滤加载（loader 从 `memory_id` 的 `S###` 前缀解析阶段号，不依赖单独的 `stage_id` 字段）；目标 ~30-40 tokens/条。

**关键字段**：
- `memory_id` — 格式 `M-S{stage:03d}-{seq:02d}`；与 memory_timeline 条目的 `memory_id` 一一对应
- `summary` — 事件精简摘要（**30–50 字**；1:1 复制自 memory_timeline 的 `digest_summary`）
- `importance` — 5 级重要度（`trivial` / `minor` / `significant` / `critical` / `defining`）
- `time` — 故事内时间（可选）
- `location` — 事件地点（可选）

---

## 用户级 Schema

### user_profile.schema.json

**用途**：用户根画像。
**位置**：`users/{user_id}/profile.json`

---

### role_binding.schema.json

**用途**：用户的锁定绑定（作品-目标角色-对戏身份）。
**位置**：`users/{user_id}/role_binding.json`

---

### long_term_profile.schema.json

**用途**：用户持有的针对某作品-角色对的长期自我档案。
**位置**：`users/{user_id}/long_term_profile.json`
**更新时机**：仅在会话关闭并确认合并后。

---

### relationship_core.schema.json

**用途**：长期关系核心（钉选记忆、关系状态）。
**位置**：`users/{user_id}/relationship_core/manifest.json`
**更新时机**：仅在会话关闭并确认合并后。

---

### context_manifest.schema.json

**用途**：Context 分支 manifest。
**位置**：`users/{user_id}/contexts/{context_id}/manifest.json`

---

### context_character_state.schema.json

**用途**：Context 内实时追踪的角色状态变化。
**位置**：`users/{user_id}/contexts/{context_id}/character_state.json`
**更新时机**：每轮对话实时更新。

---

### session_manifest.schema.json

**用途**：Session manifest。
**位置**：`users/{user_id}/contexts/{context_id}/sessions/{session_id}/manifest.json`

---

## 运行时 Schema

### runtime_session_request.schema.json

**用途**：运行时 session 请求载荷。
**使用者**：终端适配器 → 仿真引擎。

---

## Baseline vs Runtime 加载规则

| 文件 | 提取时 | 运行时 |
|------|--------|--------|
| identity.json | 首阶段创建，后续修订 | **加载** |
| failure_modes.json | 首阶段创建，后续修订 | **加载** |
| voice_rules.json | 提取锚点 | **不加载** |
| behavior_rules.json | 提取锚点 | **不加载** |
| boundaries.json | 提取锚点（hard_boundaries 加载） | hard_boundaries **加载** |
| stage_snapshot | 每阶段产出 | **加载**（核心） |
| memory_timeline | 每阶段产出 | 近期 2 阶段全量 + memory_digest 1..N 过滤 + FTS5 按需 |

---

## 进度跟踪状态（Python dataclass，非 JSON Schema）

以下结构存于 `automation/persona_extraction/progress.py`，不归属
`schemas/` 目录；序列化到磁盘时位于 `works/{work_id}/analysis/progress/`。
因其字段跨文档引用频繁，在此登记以便查询。

### StageEntry（Phase 3 阶段状态，序列化到 `phase3_stages.json`）

- `stage_id: str` — 阶段标识
- `chapters: str` + `chapter_count: int` — 章节范围 `"NNNN-NNNN"` 与总数
- `state: StageState` — 枚举：PENDING / EXTRACTING / EXTRACTED / POST_PROCESSING / REVIEWING / PASSED / FAILED / ERROR / COMMITTED
- `committed_sha: str` — git commit SHA（仅 COMMITTED 态非空）
- `error_message: str` — 最近一次错误摘要（含 `force_reset_to_pending` 的 reason）
- `fail_source: str` — 失败来源标签（`programmatic` / `semantic` / `external_delete`）。`external_delete` 由 PASSED 态 --resume 时发现 1+2N 产物被擦盘的安全网写入
- `last_reviewer_feedback: str` — 最近一次 repair agent 报告摘要，commit 成功后清空
- `last_updated: str` — ISO 时间戳，每次转换后更新

状态转换：由 `_TRANSITIONS` 白名单控制，不允许任意跳转。回到 PENDING 的
唯一合法路径是 `force_reset_to_pending(reason)`——disk reconcile 与
resume 自愈流程（EXTRACTING / REVIEWING 中断恢复、ERROR → PENDING 重
置）走此方法，必须携带原因，便于审计。

`from_dict` 对未识别的字段静默忽略（前向兼容），不会因为运行时版本差异
导致 progress 文件无法加载。

