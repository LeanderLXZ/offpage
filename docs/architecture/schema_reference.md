# Schema 参考文档

本文档是 `schemas/` 目录下所有 JSON Schema 的功能说明与用途索引。
Schema 文件本身是权威定义，本文档仅提供快速导航。

## 作品级 Schema

### work_manifest.schema.json

**用途**：作品入库 manifest。
**位置**：`works/{work_id}/manifest.json`
**关键字段**：work_id, title, language, source_types, ingestion_status

---

### world_stage_catalog.schema.json

**用途**：世界阶段目录，列出作品的所有可选阶段。
**位置**：`works/{work_id}/world/stage_catalog.json`
**关键字段**：stages[].stage_id, stages[].title, stages[].summary

---

### world_stage_snapshot.schema.json

**用途**：世界阶段快照，描述某个阶段下的世界状态。
**位置**：`works/{work_id}/world/stage_snapshots/{stage_id}.json`
**关键字段**：
- `snapshot_summary` — 阶段的世界状态概述
- `foundation_corrections` — 对基础设定的修正
- `historical_events` — 累积历史事件
- `current_world_state` — 当前阶段的世界总体状态
- `relationship_shifts` — 关注的人物关系转变
- `character_status_changes` — 人物状态变化（生死、等级等）
- `location_changes`, `map_changes` — 地理变化
- `evidence_refs` — 证据引用

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

**关键 section**：

| Section | 说明 |
|---------|------|
| `voice_state` | 完整的语气基调、语言习惯、用词偏好、口头禅、禁忌用语、情绪语气矩阵、对象语气矩阵、典型对话示例 |
| `behavior_state` | 核心驱动力、决策风格、情绪触发器、情绪反应矩阵、关系行为矩阵、习惯性行为、压力应对 |
| `boundary_state` | 当前阶段有效的软边界、容易被误判的点 |
| `relationships` | 对每个重要角色的完整关系状态（态度、信任、亲密度、语气变化、行为变化、驱动事件、关系演变概述） |
| `misunderstandings` | 角色持有的误解（主观认知 vs 客观事实） |
| `concealments` | 角色主动隐瞒的事情 |
| `stage_delta` | 从上一阶段的变化摘要（信息性） |
| `source_notes` | 推断和不确定性记录（field + source_type + note） |

---

### memory_timeline_entry.schema.json

**用途**：角色记忆条目——角色视角的主观记忆。
**位置**：`characters/{character_id}/canon/memory_timeline/{stage_id}.jsonl`
**格式**：JSONL，每行一条记忆。

**关键字段**：
- `event_summary` — 客观发生了什么
- `subjective_experience` — 角色认为发生了什么（可能与事实不同）
- `emotional_impact` — 情感影响
- `misunderstanding` — 是否产生了误解
- `concealment` — 是否选择隐瞒
- `source_type` — 信息来源（canon/inference/ambiguous）
- `memory_importance` — 重要程度（trivial ~ defining）

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
| identity.json | 首批创建，后续修订 | **加载** |
| failure_modes.json | 首批创建，后续修订 | **加载** |
| voice_rules.json | 提取锚点 | **不加载** |
| behavior_rules.json | 提取锚点 | **不加载** |
| boundaries.json | 提取锚点（hard_boundaries 加载） | hard_boundaries **加载** |
| stage_snapshot | 每批产出 | **加载**（核心） |
| memory_timeline | 每批产出 | 加载 1..N |
