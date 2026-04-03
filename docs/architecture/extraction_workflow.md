# 端到端提取工作流

## 概述

本文档描述从原始小说到可运行角色包的完整提取流程。提取是增量的——
按批次推进，每个批次对应一个剧情阶段，阶段 N 累积阶段 1..N 的全部内容。

## 流程总览

```
1. 作品入库
2. 全书总体分析
3. 源文件分批规划
4. 候选角色识别
5. 活跃角色确认（用户参与）
6. 协同批次提取（世界 + 角色）
7. 针对性补充提取
8. 包验证与发布
```

## 阶段详解

### 1. 作品入库

- 将原始小说放入 `sources/works/{work_id}/`
- 归一化章节：`sources/works/{work_id}/normalized/`
- 创建元数据：`sources/works/{work_id}/metadata/book_metadata.json`
  和 `chapter_index.json`
- 创建作品 manifest：`works/{work_id}/manifest.json`

**对应提示词**：无（手动或脚本）

### 2. 全书总体分析

- 读取章节索引和元数据，产出全书分析摘要
- 评估体量，建议分批策略

**对应提示词**：`prompts/analysis/全书总体分析.md`

### 3. 源文件分批规划

- 制定 batch plan：每批默认 10 章，可按作品 config 调整
- 尽量按自然剧情边界切分
- 输出：`works/{work_id}/analysis/incremental/source_batch_plan.md`

**对应提示词**：`prompts/analysis/源文件分批规划.md`

### 4. 候选角色识别

- 基于前几批章节，识别可建包的候选角色
- 输出：`works/{work_id}/analysis/incremental/candidate_characters_initial.md`

**对应提示词**：`prompts/analysis/候选角色识别.md`

### 5. 活跃角色确认

- **用户参与**：用户从候选中选择要建包的目标角色
- 确认后，后续批次进入协同提取模式

### 6. 协同批次提取

每个批次 N 同时产出世界包更新和角色包更新。

#### 6.1 世界信息提取

每批产出或更新：

- `world/stage_catalog.json` — 追加新阶段条目
- `world/stage_snapshots/{stage_id}.json` — 当前阶段的世界快照
- `world/foundation/` — 如有修正
- `world/social/stage_relationships/{stage_id}.json` — 动态关系
- 按需：events、locations、factions、maps

**对应提示词**：`prompts/analysis/世界信息抽取.md`

#### 6.2 角色信息提取

每批产出或更新：

**Baseline 文件**（batch 1 时创建，后续仅在必要时修订）：

- `characters/{character_id}/canon/identity.json`
- `characters/{character_id}/canon/voice_rules.json`
- `characters/{character_id}/canon/behavior_rules.json`
- `characters/{character_id}/canon/boundaries.json`
- `characters/{character_id}/canon/failure_modes.json`

**阶段文件**（每批产出）：

- `characters/{character_id}/canon/stage_catalog.json` — 追加新阶段条目
- `characters/{character_id}/canon/stage_snapshots/{stage_id}.json` —
  **自包含快照**，包含该阶段的完整 voice_state、behavior_state、
  boundary_state、relationships、personality、mood、knowledge
- `characters/{character_id}/canon/memory_timeline/{stage_id}.jsonl` —
  该阶段的角色记忆条目

**自包含快照的生成规则**：

- 阶段 1 快照 ≈ baseline 内容 + 阶段特有字段（事件、心情、关系等）
- 阶段 N 快照以 baseline + 前一阶段快照为参照，产出完整的当前阶段状态
- **未变化的内容也必须包含在快照中**——快照是自包含的，运行时不依赖 baseline
- `stage_delta` 记录从上一阶段的变化（信息性，便于理解演变弧线）

**信息来源标注**：

- 记忆条目的 `source_type` 字段标注 canon / inference / ambiguous
- 快照的 `source_notes` 数组记录推断和多义性解读
- 当 source_type 为 inference 或 ambiguous 时，必须附带说明

**对应提示词**：`prompts/analysis/角色信息抽取.md`

### 7. 针对性补充提取

当协同批次完成后，如果角色包仍有明显缺口（如某些章节与该角色高度相关
但批次提取时未充分覆盖），可执行针对性补充：

- 仅读取与缺口相关的章节
- 补充到对应阶段的快照和记忆文件中
- 不创建新阶段，只丰富已有阶段

### 8. 包验证与发布

验证清单：

- [ ] 每个阶段快照是否自包含（voice_state、behavior_state、boundary_state
  齐全）
- [ ] 每个阶段快照的 relationships 是否完整（对每个重要角色都有条目）
- [ ] memory_timeline 是否每个阶段都有文件
- [ ] stage_catalog 的阶段数 = stage_snapshots 目录下的文件数
- [ ] evidence_refs 是否有效引用
- [ ] source_notes 中的推断是否合理
- [ ] 世界快照是否与角色快照的阶段对齐

## Baseline 文件的角色

Baseline 文件在提取流程中有两个用途：

1. **阶段 1 的起点**：batch 1 提取时先填充 baseline，然后据此生成阶段 1
   的自包含快照
2. **后续批次的参照锚点**：提取者用 baseline 来判断"相比初始状态，
   当前阶段有什么变化"，帮助准确描述 stage_delta

**Baseline 不在运行时加载**——运行时只加载 identity.json、failure_modes.json、
hard_boundaries 和所选阶段的自包含快照。

## 批次间的增量规则

- 每个批次可以修订任何已有资产（不仅限于当前阶段）
- 如果本批原文推翻了之前的结论，应更新 baseline 和受影响的阶段快照
- 矛盾和修订必须在 source_notes 中显式记录
- 进度追踪：`works/{work_id}/analysis/incremental/extraction_status.md`
