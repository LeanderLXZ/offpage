# 世界层提取

你现在接手本地项目 `persona-engine`，你没有任何额外背景知识，请完全按本提示词执行。

## 任务卡

- **当前目标**: 对 `{work_id}` 执行 {batch_id} 的 **世界层提取**（仅世界信息，不含角色）
- **batch_id**: `{batch_id}`
- **stage_id**: `{stage_id}`
- **章节范围**: `{chapter_range}`
- **目标角色（参考）**: {target_characters}
- **首批？**: {is_first_batch}
- **源目录**: `{source_dir}`
- **作品目录**: `{work_dir}`

## 必读文件清单

编排脚本已为你列出本次需要读取的全部文件。请按顺序读取，不要跳过：

{files_to_read}

## 核心规则

1. **仅产出世界层**：本次调用只负责世界信息，角色信息由后续独立调用处理
2. **世界层边界**：世界层只记录影响世界状态的大事件和主要角色参与的公共事件，小事件和个人视角归角色层
3. **信息来源标注**：所有结构化数据必须标注 source_type（canon/inference/ambiguous）。inference 和 ambiguous 必须附带说明
4. **证据引用**：`evidence_refs` 字段为本阶段涉及的章节号列表（如 `["0001", "0002"]`）。正文字段（stage_events、current_world_state 等）**不需要**逐条标注 `[NNNN]`
5. **中文标识**：中文作品的 work_id, stage_id, 路径段都使用中文
6. **时间性**：当前阶段写清"现在"，不要混成扁平总结
7. **仅本阶段事件**：`stage_events` 只记录本 batch 章节范围内发生的事件，不重复前序阶段已记录的内容。**每条为 ≤ 80 字的 1 句话摘要**（既是快照中的事件清单，也是 `world_event_digest.jsonl` 的直接来源——不再单独维护 `key_events` 字段）。跨阶段时间线由 `world_event_digest.jsonl` 程序化累积

## 世界层输出

本批应产出或更新：

- `world/stage_snapshots/{stage_id}.json` — 当前阶段世界快照（遵循 world_stage_snapshot.schema.json）
- `world/foundation/` — 如有基础设定修正

**注意**：`world/stage_catalog.json` 由编排脚本自动维护，**不要手动写入或修改此文件**。

## 风格一致性要求

前一阶段世界快照参照：`{prev_world_snapshot}`

如果存在前一阶段的输出，请先读取它，并确保本批产出在以下维度与之保持一致：

- `stage_events` 条目的粒度（≤ 80 字的 1 句话摘要）
- `current_world_state` 的描述风格
- 每条事件内嵌 `[NNNN]` 章节引用
- source_type 已标注

## 质量退化防护

### 写前自检（每次写文件前必做）

1. **Schema 确认**：你是否在本 batch 内重读过要写入文件对应的 schema？
   如果没有，**现在重读**。不要凭记忆填字段——schema 是权威。
2. **前批对照**：本 batch 的输出在字段详细度、术语、`stage_events`
   粒度、source_type 分布上是否与前一 batch 一致？

### 边界禁令

- 不要把角色个人互动细节写入世界层（如"某角色给另一角色穿衣"是角色层事件）
- 不要把个人经济活动写入世界层（如个人消费记录）
- 不要把角色内部心理事件写入世界层

## 本批输出清单

完成后，请确认已产出以下内容：

1. 世界快照 `world/stage_snapshots/{stage_id}.json`
2. 基础设定修正（如有）
4. 所有文件都通过 schema 校验
5. evidence_refs 为章节号列表（如 `["0001", "0002"]`），非空
6. source_type 已标注
7. `stage_events` 仅包含本阶段事件，每条为 ≤ 80 字的 1 句话摘要（digest 直接复用）
{retry_note}
