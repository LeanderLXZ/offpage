# Schema 参考文档

本文档是 `schemas/` 目录下所有 JSON Schema 的功能说明与用途索引。
**Schema 文件本身是权威定义**——所有 `maxLength` / `minLength` /
`maxItems` / `required` 等字段级数值以 `schemas/<path>/<name>.schema.json`
为准，本文档不再复述具体数字，仅提供字段用途 / 运行时契约 / 跨字段
不变量的描述。如需具体上下限，直接打开对应 schema 文件。

`schemas/` 按语义分层组织为子目录：

| 子目录 | 作用 | 文件数 |
|--------|------|--------|
| `schemas/work/` | 作品入库、目录、阶段目录、per-work 加载配置 | 6 |
| `schemas/world/` | 世界基础设定、阶段快照、事件、固定关系、目录页 | 6 |
| `schemas/character/` | 角色 baseline + 阶段快照 + 记忆 | 9 |
| `schemas/user/` | 用户根画像、绑定、长期档案、关系核心、钉选记忆条目 | 5 |
| `schemas/runtime/` | Context / Session / 请求载荷 / 场景归档条目 | 5 |
| `schemas/shared/` | 跨域共享（extraction_notes 等） | 1 |

## Work 层（`schemas/work/`）

### work/work_manifest.schema.json

**用途**：source package manifest。
**位置**：`sources/works/{work_id}/manifest.json`
**关键字段**：work_id, title, language, source_types, ingestion_status, paths
**生成时机**：`prompts/ingestion/原始资料规范化.md` 执行规范化时产出。

---

### work/works_manifest.schema.json

**用途**：canon 作品包 manifest（作品包目录页）。
**位置**：`works/{work_id}/manifest.json`
**关键字段**：work_id, title, language, source_package_ref, paths, chapter_count, stage_count, character_count, stage_ids, character_ids
**生成时机**：Phase 1.5 用户确认完成时由 `automation.persona_extraction.manifests.write_works_manifest` 程序化写出；不走 LLM。

---

### work/book_metadata.schema.json

**用途**：书籍元数据（作者、原始格式、封面、identifier 等 EPUB/来源级信息）。
**位置**：`sources/works/{work_id}/metadata/book_metadata.json`
**关键字段**：work_id, title, language, source_format, chapter_count
**生成时机**：规范化阶段产出。

---

### work/chapter_index.schema.json

**用途**：章节索引（顶层 JSON 数组）。
**位置**：`sources/works/{work_id}/metadata/chapter_index.json`
**关键字段**：每条含 sequence（严格连续递增）、chapter_id、title、normalized_path
**生成时机**：规范化阶段产出；后续 Phase 0/1/3/4 的 chapter 引用都以 chapter_id 为锚。

---

### work/load_profiles.schema.json

**用途**：Per-work 运行时加载配置，作为 sparse override 覆盖 simulation 启动器默认值。文件不存在时 loader 使用内置默认。
**位置**：`works/{work_id}/indexes/load_profiles.json`
**关键字段**：`scene_fulltext_window`（默认 10）、`startup_packets[]`、`on_demand_buckets[]`、`retrieval_notes`、`fidelity_escalation{}`。
**形态**：`additionalProperties: true`，字段集随 simulation 层演进；schema 提供最小契约。

---

## World 层（`schemas/world/`）

### world/world_manifest.schema.json

**用途**：世界包 manifest（世界包目录页）。
**位置**：`works/{work_id}/world/manifest.json`
**关键字段**：work_id, world_id, paths, stage_ids
**生成时机**：Phase 2 baseline 产出后由 `automation.persona_extraction.manifests.write_world_manifest` 程序化写出；不走 LLM。

---

### world/world_stage_catalog.schema.json

**用途**：世界阶段目录，列出作品的所有可选阶段。仅用于 bootstrap 阶段选择，运行时不加载。
**位置**：`works/{work_id}/world/stage_catalog.json`
**关键字段**：stages[].stage_id（`S###`，既是主键也是排序键）, stages[].stage_title, stages[].summary, stages[].snapshot_path

---

### world/world_stage_snapshot.schema.json

**用途**：世界阶段快照，描述某个阶段下的世界状态。
**位置**：`works/{work_id}/world/stage_snapshots/{stage_id}.json`
**关键字段**：
- `timeline_anchor` / `location_anchor` — 阶段级时间 / 地点锚点（≤15 字短语），required；post_processing 复制到 `world_event_digest.time` / `location`
- `snapshot_summary` — 阶段的世界状态概述
- `foundation_corrections` — 对基础设定的修正
- `stage_events` — 本阶段事件（**唯一事件清单**，每条一句话；**仅收录世界公共层事件**，角色私事/内心决定应写入该角色 memory_timeline；既是快照内容又是 `world_event_digest.jsonl` 的直接来源，1:1 复制）
- `current_world_state` — 当前阶段的世界总体状态
- `relationship_shifts` — 关注的人物关系转变
- `location_changes`, `map_changes` — 地理变化
- `unresolved_questions` — 本阶段遗留的开放问题（可选）

**自包含契约（schema 硬门控）**：`required` 除元信息外还包含
`timeline_anchor` / `location_anchor` / `snapshot_summary` /
`foundation_corrections` / `stage_events` / `current_world_state` /
`relationship_shifts` / `location_changes` / `map_changes`。L1 schema
层即强制所有自包含维度存在（允许空数组，但不允许缺字段），让 schema
gate 承担 self-contained 契约而非仅依赖 prompt + L2/L3。

---

### world/fixed_relationships.schema.json

**用途**：世界级固定关系网络（血缘、宗族、师徒、势力从属等不随阶段变化的结构性关系）。
**位置**：`works/{work_id}/world/foundation/fixed_relationships.json`
**关键字段**：relationships[].relationship_id, relationships[].type, relationships[].parties, relationships[].description
**生命周期**：Phase 2 产出骨架，后续阶段可修正。运行时 Tier 0 加载。

---

### world/foundation.schema.json

**用途**：世界基础设定（genre / tone / world_structure / power_system / core_rules / world_lines / major_factions）。不含 stage-scoped 信息，作为运行时 Tier 0 的静态背景加载。
**位置**：`works/{work_id}/world/foundation/foundation.json`
**生命周期**：Phase 2 基线产出；后续阶段可通过 world_stage_snapshot.foundation_corrections 增量修正。
**形态**：`additionalProperties: true`（顶层与子对象），容纳 per-work 扩展字段；`required` 仅 `work_id`。字段级上下限以 schema 为准。

---

### world/world_event_digest_entry.schema.json

**用途**：世界事件压缩摘要条目——从世界 stage_snapshot `stage_events` 程序化生成的精简索引。
**位置**：`works/{work_id}/world/world_event_digest.jsonl`
**格式**：JSONL，每行一条事件摘要。
**运行时**：启动时 stage 1..N 过滤加载（loader 从 `event_id` 的 `S###` 前缀解析阶段号，不依赖单独的 `stage_id` 字段）。

**关键字段**：
- `event_id` — 格式 `E-S{stage:03d}-{seq:02d}`（例：`E-S003-02`）；阶段号编码在 ID 中
- `summary` — 事件精简摘要（1:1 复制自世界快照 `stage_events`）
- `importance` — 5 级重要度（`trivial` / `minor` / `significant` / `critical` / `defining`）
- `time` — 故事内时间（required，来自 snapshot `timeline_anchor`）
- `location` — 事件地点（required，来自 snapshot `location_anchor`）
- `involved_characters` — 涉及的角色（可选）

---

## Character 层（`schemas/character/`）

### character/character_manifest.schema.json

**用途**：角色包 manifest（角色包目录页）。
**位置**：`works/{work_id}/characters/{character_id}/manifest.json`
**关键字段**：schema_version, character_id, work_id, canonical_name, aliases（扁平字符串数组）, paths, source_scope
**生成时机**：Phase 2 baseline 由 LLM 按 `baseline_production.md` 产出。

---

### character/identity.schema.json

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

**核心创伤**：`core_wounds` 字段记录跨全故事始终影响角色行为的根源性
心理创伤，每条含 `wound` / `origin`（成因）/ `behavioral_impact`（行为
影响）。不同于 stage_snapshot 中的 `active_wounds`（随阶段演变），
core_wounds 记录最底层的创伤根源。

**核心人物关系**：`key_relationships` 字段记录对角色有重大影响的跨全
故事关系概览，每条含 `target` / `initial_relationship` /
`relationship_arc`（全局演变弧线）/ `turning_points`。不同于
stage_snapshot 中的 `relationships`（记录某一阶段的关系状态），
key_relationships 提供关系的全局演变轨迹。

---

### character/voice_rules.schema.json

**用途**：角色语言风格的提取锚点（baseline）。
**位置**：`characters/{character_id}/canon/voice_rules.json`
**运行时**：**不加载**。运行时使用 stage_snapshot 中的 `voice_state`。

**关键字段**：`baseline_tone` / `speech_patterns` /
`vocabulary_preferences` / `signature_phrases` / `taboo_patterns` /
`emotional_voice_map` / `target_voice_map` / `dialogue_examples`（顶层
+ `emotional_voice_map` + `target_voice_map` 三处对齐结构，均无
`evidence_ref`）。

---

### character/behavior_rules.schema.json

**用途**：角色行为规则的提取锚点（baseline）。
**位置**：`characters/{character_id}/canon/behavior_rules.json`
**运行时**：**不加载**。运行时使用 stage_snapshot 中的 `behavior_state`。

**目标与执念分离**：`core_goals`（理性目标，可权衡调整）与
`obsessions`（非理性心结，不受权衡控制）是两个独立字段。stage_snapshot
中的 `behavior_state` 同样维护 `core_goals` / `obsessions`，
`emotional_baseline` 维护 `active_goals` / `active_obsessions`。

**关键字段**：`core_goals` / `obsessions` / `decision_making_style` /
`emotional_triggers` / `emotional_reaction_map` / `target_behavior_map`
（与 stage 侧同名）/ `habitual_behaviors` / `stress_response`。

---

### character/boundaries.schema.json

**用途**：角色行为边界（硬边界 + 软边界）的提取锚点。
**位置**：`characters/{character_id}/canon/boundaries.json`
**运行时**：hard_boundaries 始终加载；soft_boundaries 由 stage_snapshot 的 `boundary_state` 提供。

---

### character/failure_modes.schema.json

**用途**：AI 扮演该角色时容易犯的错误清单。
**位置**：`characters/{character_id}/canon/failure_modes.json`
**运行时**：始终加载。

---

### character/stage_snapshot.schema.json

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
| `timeline_anchor` | 本阶段时间锚点短描述（required） |
| `snapshot_summary` | 阶段一段式摘要（required） |
| `active_aliases` | 本阶段活跃名称（primary_name / active_names / hidden_identities / known_as 称呼映射） |
| `voice_state` | 语气基调、语言习惯、用词偏好、口头禅、禁忌用语、情绪语气矩阵（emotional_voice_map）、对象语气矩阵（target_voice_map，按具体角色区分，每 target 至少 3-5 条对话示例）、典型对话示例（dialogue_examples 无 evidence_ref） |
| `behavior_state` | **core_goals**（理性目标）、**obsessions**（执念）、决策风格、情绪触发器、情绪反应矩阵（emotional_reaction_map）、对象行为矩阵（target_behavior_map，与 target_voice_map 平行对齐，每 target 至少 3-5 条行为示例；action_examples 无 evidence_ref）、习惯性行为、压力应对 |
| `boundary_state` | `hard_boundaries` / `soft_boundaries` / `common_misconceptions` |
| `relationships` | 对每个重要角色的完整关系状态（态度、信任、亲密度、语气变化、行为变化、驱动事件、`relationship_history_summary`） |
| `misunderstandings` | 角色持有的误解（content / truth / cause） |
| `concealments` | 角色主动隐瞒的事情（content / reason） |
| `stage_delta` | 从上一阶段的变化摘要（信息性） |
| `character_arc` | 角色从阶段 1 到当前的整体弧线概述（单一字符串） |
| `stage_events` | 本阶段发生的事件（每条一句话，不累积历史） |

**自包含契约（schema 硬门控）**：`required` 除元信息外还包含
`timeline_anchor` / `snapshot_summary` / `active_aliases` /
`current_personality` / `current_mood` / `knowledge_scope` /
`voice_state` / `behavior_state` / `boundary_state` / `relationships` /
`stage_events` / `character_arc`。L1 schema 层即强制所有自包含维度存在
（`stage_delta` 可省略，stage 1 没有上阶段参考）。由 schema gate
承担 self-contained 契约，而非仅靠 prompt + L2/L3 兜底。角色阶段快照
**不携带** 章节级回溯字段（`memory_refs` / `evidence_refs` /
`source_type` / `scene_refs` 全部不挂在快照层）；定位通过
`timeline_anchor` + `memory_timeline` 自身锚点完成。

---

### character/memory_timeline_entry.schema.json

**用途**：角色记忆条目——角色第一人称主观视角的归纳记忆（不是原文复制）。
**位置**：`characters/{character_id}/canon/memory_timeline/{stage_id}.json`
**格式**：JSON 数组，每个元素为一条记忆。
**运行时**：启动加载近期 2 个阶段（N + N-1）全文；远期阶段通过
`memory_digest.jsonl` 摘要感知，详情通过 FTS5 按需检索。

**关键字段**：
- `memory_id` — 格式 `M-S{stage:03d}-{seq:02d}`（例：`M-S003-02`）
- `time` / `location` — 故事内时间 / 地点，required
- `event_description` — 客观事件描述，下限硬门控避免空摘要
- `digest_summary` — 用于 memory_digest 的精简摘要；独立撰写，聚焦可检索关键词，**不是** `event_description` 的机械截断
- `subjective_experience` — 角色对事件的主观体验（第一人称视角，核心字段）
- `emotional_impact` — 情感影响
- `knowledge_gained` — 本事件带来的新认知
- `misunderstanding` — 是否产生了误解（数组，条目含 `content` / `truth`）
- `concealment` — 是否选择隐瞒（数组，条目含 `content` / `reason`）
- `relationship_impact` — 关系影响（数组，条目含 `target` / `change`）
- `memory_importance` — 重要程度（trivial ~ defining）

**归纳要求**：角色第一人称主观视角，是归纳不是原文复制。必须包含心理活动
和态度变化的因果。

---

### character/memory_digest_entry.schema.json

**用途**：记忆压缩摘要条目——从 memory_timeline 自动提取的精简索引。
**位置**：`characters/{character_id}/canon/memory_digest.jsonl`
**格式**：JSONL，每行一条压缩摘要。
**运行时**：启动时 stage 1..N 过滤加载（loader 从 `memory_id` 的 `S###` 前缀解析阶段号，不依赖单独的 `stage_id` 字段）；目标 ~30-40 tokens/条。

**关键字段**：
- `memory_id` — 格式 `M-S{stage:03d}-{seq:02d}`；与 memory_timeline 条目的 `memory_id` 一一对应
- `summary` — 事件精简摘要（1:1 复制自 memory_timeline 的 `digest_summary`）
- `importance` — 5 级重要度（`trivial` / `minor` / `significant` / `critical` / `defining`）
- `time` / `location` — 故事内时间 / 地点，required

---

### character/stage_catalog.schema.json

**用途**：角色阶段目录，与世界 stage_catalog 对称。仅用于 bootstrap 阶段选择，运行时不加载。
**位置**：`characters/{character_id}/canon/stage_catalog.json`
**关键字段**：stages[].stage_id（`S###`，与世界 stage_id 对齐，字典序即阶段顺序）、stages[].stage_title、stages[].summary、stages[].snapshot_path、stages[].timeline_anchor / chapter_scope（可选）

---

## User 层（`schemas/user/`）

### user/user_profile.schema.json

**用途**：用户根画像。
**位置**：`users/{user_id}/profile.json`

---

### user/role_binding.schema.json

**用途**：用户的锁定绑定（作品-目标角色-对戏身份）。
**位置**：`users/{user_id}/role_binding.json`

---

### user/long_term_profile.schema.json

**用途**：用户持有的针对某作品-角色对的长期自我档案。
**位置**：`users/{user_id}/long_term_profile.json`
**更新时机**：仅在会话关闭并确认合并后。

---

### user/relationship_core.schema.json

**用途**：长期关系核心 manifest（关系状态、关系演变引用、互相约定、
个性化语气 / 行为迁移等单对象摘要）。钉选记忆作为独立 append-only
流记录在 sidecar JSONL 中，见下一条 schema。
**位置**：`users/{user_id}/relationship_core/manifest.json`
**更新时机**：仅在会话关闭并确认合并后。

---

### user/pinned_memory_entry.schema.json

**用途**：长期关系层被用户明确保留 / 提升的钉选记忆条目。
**位置**：`users/{user_id}/relationship_core/pinned_memories.jsonl`
**格式**：JSONL，每行一条钉选记忆；append-only。
**运行时**：随 `relationship_core/manifest.json` 一同在启动阶段加载
（按 `simulation/flows/startup_load.md` 与
`simulation/retrieval/load_strategy.md`）。
**关键字段**：user_memory_id, summary, source_context_ids?, importance?,
permanence_reason?, pinned_at?
**更新时机**：仅在会话关闭并确认合并后追加写入，不覆盖不删除。

---

## Runtime 层（`schemas/runtime/`）

### runtime/context_manifest.schema.json

**用途**：Context 分支 manifest。
**位置**：`users/{user_id}/contexts/{context_id}/manifest.json`

---

### runtime/context_character_state.schema.json

**用途**：Context 内实时追踪的角色状态变化。
**位置**：`users/{user_id}/contexts/{context_id}/character_state.json`
**更新时机**：每轮对话实时更新。

---

### runtime/session_manifest.schema.json

**用途**：Session manifest。
**位置**：`users/{user_id}/contexts/{context_id}/sessions/{session_id}/manifest.json`

---

### runtime/runtime_session_request.schema.json

**用途**：运行时 session 请求载荷。
**使用者**：终端适配器 → 仿真引擎。

---

### runtime/scene_archive_entry.schema.json

**用途**：`scene_archive.jsonl` 单条记录——Phase 4 `scene_split` 按行号切出的场景。作为 FTS5 检索与 `full_text` 取回的基本单元。
**位置**：`works/{work_id}/retrieval/scene_archive.jsonl`（本地生成，不入 git）
**关键字段**：`scene_id`（`SC-S###-##`）/ `stage_id`（`S###`）/ `chapter` / `time` / `location` / `characters_present[]` / `summary` / `full_text`
**运行时**：最近 `scene_fulltext_window` 条在 Tier 0 直接加载 `full_text`，其余由 FTS5 on-demand 取回；`summary` 不单独进入 Tier 0。

---

## Shared 层（`schemas/shared/`）

### shared/source_note.schema.json

**用途**：Repair agent accept_with_notes 通道持久化的 SourceNote 条目，两个来源共用：(1) L3 语义 issue 被 LLM triage 判定为源文件自带（作者矛盾、笔误、代词混淆等）；(2) L2 structural `min_examples` 被判定为 `coverage_shortage`（原文素材不足，T2 source_patch 单次尝试后仍不足）。均带 chapter + line_range + verbatim quote 证据锚定；coverage_shortage 的 quote 由程序从阶段首章选取（0 token）。
**位置**：
- 角色级：`works/{work_id}/characters/{character_id}/canon/extraction_notes/{stage_id}.jsonl`
- 世界级：`works/{work_id}/world/extraction_notes/{stage_id}.jsonl`

**格式**：JSONL，每行一条 SourceNote。

**关键字段**：
- `note_id` — 唯一 ID
- `stage_id` — 归属阶段
- `file` — 触发问题的目标文件相对路径
- `json_path` — 触发问题的字段 json_path
- `discrepancy_type` — 枚举（见 `automation/repair_agent/protocol.py DISCREPANCY_TYPES`）
- `source_evidence.chapter_number`、`source_evidence.line_range`、`source_evidence.quote` — 原文证据锚定
- `source_evidence.quote_sha256`、`source_evidence.chapter_sha256` — 内容 hash（用于 staleness 检测）

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
