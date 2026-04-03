# 协同批次提取

你现在接手本地项目 `persona-engine`，你没有任何额外背景知识，请完全按本提示词执行。

## 任务卡

- **当前目标**: 对 `{work_id}` 执行 {batch_id} 的协同提取（世界 + 角色同步产出）
- **batch_id**: `{batch_id}`
- **stage_id**: `{stage_id}`
- **章节范围**: `{chapter_range}`
- **目标角色**: {target_characters}
- **首批？**: {is_first_batch}
- **源目录**: `{source_dir}`
- **作品目录**: `{work_dir}`

## 必读文件清单

编排脚本已为你列出本次 batch 需要读取的全部文件。请按顺序读取，不要跳过：

{files_to_read}

## 核心规则

1. **协同提取**：读一次正文，同时产出世界包更新和所有目标角色的包更新。
   本批章节范围由分析阶段按剧情边界确定，不一定是 10 章
2. **自包含快照**：每个 stage_snapshot 必须自包含——包含完整的 voice_state, behavior_state, boundary_state, relationships，即使某些字段相比上一阶段未变化也必须包含
3. **Baseline 角色**：首批创建 baseline 文件（identity.json, voice_rules.json 等），后续批次仅在必要时修订。Baseline 是提取锚点，不在运行时加载
4. **信息来源标注**：所有结构化数据必须标注 source_type（canon/inference/ambiguous）。inference 和 ambiguous 必须附带说明
5. **证据引用**：每个结论必须有 evidence_refs（紧凑章节引用格式，如 `0001`, `0011-0013`）
6. **中文标识**：中文作品的 work_id, character_id, stage_id, 路径段都使用中文
7. **世界层边界**：世界层只记录大事件和主要角色，小事件和小角色归角色层
8. **时间性**：当前阶段写清"现在"，历史事件标注为"已发生"，不要混成扁平总结

## 世界层输出

本批应产出或更新：

- `world/stage_catalog.json` — 追加本阶段条目
- `world/stage_snapshots/{stage_id}.json` — 当前阶段世界快照（遵循 world_stage_snapshot.schema.json）
- `world/foundation/` — 如有基础设定修正
- `world/social/stage_relationships/{stage_id}.json` — 动态关系
- 按需：events, locations, factions, cast

## 角色层输出（每个目标角色）

目标角色列表：{target_characters_list}

每个角色本批应产出或更新：

**首批额外创建 baseline**（如果 {is_first_batch}）：
- `characters/{{char_id}}/canon/identity.json`
- `characters/{{char_id}}/canon/voice_rules.json`
- `characters/{{char_id}}/canon/behavior_rules.json`
- `characters/{{char_id}}/canon/boundaries.json`
- `characters/{{char_id}}/canon/failure_modes.json`

**每批产出**：
- `characters/{{char_id}}/canon/stage_catalog.json` — 追加本阶段条目
- `characters/{{char_id}}/canon/stage_snapshots/{stage_id}.json` — 自包含快照（遵循 stage_snapshot.schema.json）
- `characters/{{char_id}}/canon/memory_timeline/{stage_id}.jsonl` — 记忆条目（遵循 memory_timeline_entry.schema.json）

## 风格一致性要求

前一阶段世界快照参照：`{prev_world_snapshot}`
前一阶段角色快照参照：{prev_char_snapshots_json}

如果存在前一阶段的输出，请先读取它，并确保本批产出在以下维度与之保持一致：

- emotional_voice_map 条目数不少于前一 batch
- relationships 每个条目都有 driving_events 和 relationship_history_summary
- evidence_refs 每个结论至少 2 条
- source_type 必须逐条判断，不可全部标为 canon
- dialogue_examples 至少有 2-3 条（voice_state 和 emotional_voice_map 各自）
- memory_timeline 条目的详细度（subjective_experience 字段的长度和质量）

## 稀释保护

1. 写文件前，重读对应 schema
2. 如果开始出现以下退化信号，停下来重读 schema 和前一 batch 输出：
   - 字段填充变粗糙
   - evidence_refs 越来越少
   - source_type 全标 canon
   - dialogue_examples 减少
   - relationships 缺少 driving_events
3. 不要把用户互动数据写回 canon
4. 不要把大量小事件堆进世界层
5. 不要把历史事件误写成当前状态

## 本批输出清单

完成后，请确认已产出以下内容：

1. 世界快照 + stage_catalog 更新
2. 每个目标角色的 stage_snapshot + memory_timeline + stage_catalog 更新
3. 所有文件都通过 schema 校验
4. evidence_refs 非空
5. source_type 已标注
{retry_note}
