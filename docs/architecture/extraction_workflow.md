# 端到端提取工作流

## 概述

本文档描述从原始小说到可运行角色包的完整提取流程。提取是增量的——
按批次推进，每个批次对应一个剧情阶段，阶段 N 累积阶段 1..N 的全部内容。

## 流程总览

```
1. 作品入库
2. 章节归纳（Phase 0，按 chunk 并行）
3. 全书分析（Phase 1：身份合并 → 世界观 → 分批规划 → 候选角色）
4. 活跃角色确认（Phase 2，用户参与）
5. Baseline 产出（Phase 2.5，全书视野）
6. 1+N 分层批次提取（Phase 3，世界 → 角色并行 + memory_timeline）
7. 跨批次一致性检查（Phase 3.5）
8. 场景切分（Phase 4，scene_archive，独立阶段）
9. 针对性补充提取
10. 包验证与发布
```

## 阶段详解

### 1. 作品入库

- 将原始小说放入 `sources/works/{work_id}/`
- 归一化章节：`sources/works/{work_id}/normalized/`
- 创建元数据：`sources/works/{work_id}/metadata/book_metadata.json`
  和 `chapter_index.json`
- 创建作品 manifest：`works/{work_id}/manifest.json`

**对应提示词**：无（手动或脚本）

### 2. 章节归纳（Phase 0）

- 将全书按分组（chunk，约 20-25 章/组）归纳
- 多 chunk 并行处理（`--concurrency` 控制，默认 10）
- 产出每章的结构化摘要（事件、出场角色、地点、情绪基调、身份变化线索、
  候选阶段边界标记）
- JSON 修复：L1 程序化 → L2 LLM（600s）→ L3 全量重跑（最多 1 次）
- 完成门控：全部 chunk 成功后才进入 Phase 1，有缺失则阻断并退出
- 输出：`works/{work_id}/analysis/incremental/chapter_summaries/`

### 3. 全书分析（Phase 1）

基于所有章节摘要（不读原文），按顺序执行：

a. **跨 chunk 角色身份合并**：不同 chunk 中以不同名称出现的同一角色统一为
   单一候选条目
b. **世界观概览**：题材类型、力量体系、主要势力、地理结构、大世界线划分、
   核心设定规则。输出：`works/{work_id}/analysis/incremental/world_overview.json`
c. **源文件分批规划**：按自然剧情边界切分（默认目标 10 章，最小 5 章，
   最大 15 章），剧情边界准确性优先于均匀。
   输出：`works/{work_id}/analysis/incremental/source_batch_plan.json`
d. **候选角色识别**：基于身份合并后的角色出场信息。
   输出：`works/{work_id}/analysis/incremental/candidate_characters.json`

分批规划是分析阶段**最核心的产出**——每个 batch 边界直接成为系统的 stage 边界，
世界快照、角色快照、记忆时间线、运行时阶段选择全部建立在此切分之上。

**出口验证（硬性门控）**：Phase 1 完成后程序化检查所有 batch 的 `chapter_count`
是否在 5-15 范围内。违规 batch 会触发 Phase 1 重跑——删除
`source_batch_plan.json`，带修正反馈重新调用 LLM 产出更精准的切分（最多重试
2 次）。若重试耗尽仍有违规，流程终止（`sys.exit(1)`）。

### 4. 活跃角色确认（Phase 2）

- **用户参与**：用户从候选中选择要建包的目标角色
- 确认后进入 baseline 产出和 1+N 分层提取模式

### 5. Baseline 产出（Phase 2.5）

基于全书摘要上下文和确认的角色，产出：

- `world/foundation/foundation.json` — 世界基础设定初稿
- `characters/{character_id}/canon/identity.json` — 角色身份初稿
- `characters/{character_id}/manifest.json` — 角色 manifest

这些是初稿——后续批次读到原文细节时可修正。全书视野使这些 baseline
比仅靠 batch 1 产出更准确。voice_rules、behavior_rules、boundaries
等需要原文细节的文件留到 Phase 3 batch 1 创建。

**出口验证**：Phase 2.5 完成后运行 `validate_baseline()`，校验
identity.json / manifest.json / foundation.json 的 schema 合规性和
required 字段非空。验证失败阻断 Phase 3。

### 6. 1+N 分层批次提取

每个批次 N 采用 1+N 分层架构：先提取世界信息（1 次调用），再并行提取各角色信息（N 次调用）。每次调用只传最近一个 stage_snapshot 和 memory_timeline（不传全部历史），减少输入规模。提取超时 3600s。

#### 6.1 世界信息提取（Phase A，1 次调用）

每批产出或更新（LLM 产出）：

- `world/stage_snapshots/{stage_id}.json` — 当前阶段的世界快照
- `world/foundation/` — 如有修正
- `world/social/stage_relationships/{stage_id}.json` — 动态关系
- 按需：events、locations、factions、maps

**对应提示词**：`automation/prompt_templates/world_extraction.md`

#### 6.2 角色信息提取（Phase B，N 次并行调用）

每批产出或更新：

**Baseline 文件**（batch 1 时创建，后续仅在必要时修订）：

- `characters/{character_id}/canon/identity.json`
- `characters/{character_id}/canon/voice_rules.json`
- `characters/{character_id}/canon/behavior_rules.json`
- `characters/{character_id}/canon/boundaries.json`
- `characters/{character_id}/canon/failure_modes.json`

**阶段文件**（LLM 产出）：

- `characters/{character_id}/canon/stage_snapshots/{stage_id}.json` —
  **自包含快照**，包含该阶段的完整 voice_state、behavior_state、
  boundary_state、relationships、personality、mood、knowledge
- `characters/{character_id}/canon/memory_timeline/{stage_id}.json` —
  该阶段的角色记忆条目

**程序化维护**（0 token，提取后由 `post_processing.py` 自动生成）：

- `characters/{character_id}/canon/memory_digest.jsonl` —
  从 memory_timeline 自动提取压缩摘要（遵循 memory_digest_entry.schema.json）
- `characters/{character_id}/canon/stage_catalog.json` — 从 snapshot 元数据自动维护
- `world/stage_catalog.json` — 从世界 snapshot 元数据自动维护（含 key_events 累积时间线）

**自包含快照的生成规则**：

- 阶段 1 快照 ≈ baseline 内容 + 阶段特有字段（事件、心情、关系等）
- 阶段 N 快照以 baseline + 前一阶段快照为参照，产出完整的当前阶段状态
- **未变化的内容也必须包含在快照中**——快照是自包含的，运行时不依赖 baseline
- `stage_delta` 记录从上一阶段的变化（信息性，便于理解演变弧线）

**信息来源标注**：

- 记忆条目的 `source_type` 字段标注 canon / inference / ambiguous
- 快照的 `source_notes` 数组记录推断和多义性解读
- 当 source_type 为 inference 或 ambiguous 时，必须附带说明

**对应提示词**：`automation/prompt_templates/character_extraction.md`（每个角色独立调用）

### 7. 跨批次一致性检查（Phase 3.5）

Phase 3 全部 batch 提交后、进入 Phase 4 之前，运行跨批次一致性检查。

**程序化检查**（零 token 开销）：

1. alias 一致性 — stage_snapshot active_aliases vs identity.json aliases
2. 快照字段完整性 — 13 个必填维度是否齐全
3. 关系连续性 — 相邻 batch 间 attitude/trust 变化是否有 driving_events
4. source_type 分布 — 标记全 canon batch（可能偷懒标注）
5. evidence_refs 覆盖率 — 空 evidence_refs 比例
6. memory_digest 对应 — memory_digest.jsonl ↔ memory_timeline 一一对应
7. target_map 样本数 — importance-based 阈值（主角≥5, 重要配角≥3, 其他≥1）
8. stage_id 对齐 — 世界/角色 catalog 与 snapshot 目录对齐

**LLM 裁定**（可选）：仅在有标记项时调用独立 agent 进行语义裁定。

**产出**：`works/{work_id}/analysis/incremental/consistency_report.json`

有 error 级别问题时阻断 Phase 4，需人工处理后继续。

### 8. 场景切分（Phase 4）

Phase 4 与 Phase 3 完全独立——前置条件仅为 `source_batch_plan.json` 存在
（Phase 1 产物，提供 chapter → stage_id 映射）。Phase 4 使用独立
`.scene_archive.lock`，其中间目录 `analysis/incremental/scene_archive/`
为本地忽略产物，Phase 3 的 repo-wide rollback 不会清掉它们。

**调用粒度**：每章一次 `claude -p`。LLM 输出场景边界标注（起止行号 +
元数据），不输出 full_text。程序根据行号从原文提取 full_text。

**并行**：多章并行处理（`--concurrency`，默认 10）。

**质量保障**：仅程序化校验（行号有效、不重叠、覆盖全章、alias 匹配），
不做语义审校。校验失败重跑该章（≤2 次）。

产出：
- `works/{work_id}/rag/scene_archive.jsonl`（.gitignore，文件过大）
- 中间文件：`works/{work_id}/analysis/incremental/scene_archive/`
  （`.scene_archive.lock` + `progress.json` + `splits/`，均为本地忽略，
  不得被 git track）。resume 时校验 passed 章节的 split 文件是否存在，
  缺失则重置为 pending 重新生成

`scene_id` 格式：`scene_{chapter}_{seq}`（如 `scene_0015_003`）。

每条场景条目包含：
- `scene_id` — `scene_{chapter}_{seq}` 格式
- `stage_id` — 由章节号查 batch plan 得出（程序化）
- `chapter` — 所属章节
- `time_in_story` — 故事内时间
- `location` — 场景发生地点
- `characters_present` — 在场角色列表
- `summary` — 客观第三人称事件梗概
- `full_text` — 完整场景原文（程序从原文提取，非 LLM 产出）

切分规则：
- 以自然场景边界切分，不按固定字数
- 一个场景不跨章节边界
- 场景篇幅由原文自然决定

CLI：`--start-phase 4` 可独立运行 Phase 4

### 9. 针对性补充提取

当批次提取完成后，如果角色包仍有明显缺口（如某些章节与该角色高度相关
但批次提取时未充分覆盖），可执行针对性补充：

- 仅读取与缺口相关的章节
- 补充到对应阶段的快照和记忆文件中
- 不创建新阶段，只丰富已有阶段

### 10. 包验证与发布

验证清单：

- [ ] 每个阶段快照是否自包含（voice_state、behavior_state、boundary_state
  齐全）
- [ ] target_voice_map 每个 target 是否有至少 3-5 条 dialogue_examples
- [ ] target_behavior_map 每个 target 是否有至少 3-5 条 action_examples
- [ ] 每个阶段快照的 relationships 是否完整（对每个重要角色都有条目）
- [ ] memory_timeline 是否每个阶段都有文件
- [ ] memory_timeline 条目是否包含 `time_in_story` 和 `location`
- [ ] memory_digest.jsonl 是否与 memory_timeline 条目一一对应
- [ ] stage_catalog 的阶段数 = stage_snapshots 目录下的文件数
- [ ] evidence_refs 是否有效引用
- [ ] source_notes 中的推断是否合理
- [ ] 世界快照是否与角色快照的阶段对齐
- [ ] scene_archive 是否覆盖全部章节
- [ ] scene_archive 的 `characters_present` 是否使用已确认的 character_id

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
- 进度追踪：`works/{work_id}/analysis/incremental/extraction_progress.json`

## 自动化编排

手动提取流程可通过 `automation/` 目录下的编排脚本自动化。

详见 `automation/README.md` 和 `docs/requirements.md` §十一。

编排架构：

```
orchestrator (Python)
    │
    ├── 分析阶段 → claude -p (分析 prompt)
    │
    ├── 用户确认 → 交互式选择角色、确认批次规划、设定提取范围
    │
    ├── 提取循环 → 每个 batch (1+N):
    │       ├── git preflight
    │       ├── claude -p (世界提取, 3600s)
    │       ├── claude -p ×N (角色提取并行, 3600s)
    │       ├── 程序化后处理 (digest/catalog, 0 token)
    │       ├── 并行审校通道 (world + 各角色独立):
    │       │       ├── 程序化校验 (Python/jsonschema)
    │       │       ├── claude -p (语义审校, per-lane)
    │       │       └── [局部问题] → claude -p (定点修复) → 重跑检查
    │       ├── 提交门控 (程序化跨通道一致性, 0 token)
    │       ├── [全通过] → git commit
    │       └── [系统性问题] → rollback + 全量重试
    │
    ├── 跨批次一致性检查 (Phase 3.5):
    │       ├── 程序化检查 (Python, 0 token)
    │       └── 可选 LLM 裁定 (仅有标记项时)
    │
    └── 场景切分 → 每个 batch (可并行):
            └── claude -p (场景切分 prompt)
```

关键设计决策：

- 每个 batch 拆分为 1+N 次独立 `claude -p` 调用（世界 + N 角色），不共享 session 内存
- 批次间和调用间上下文通过文件系统传递；只传最近一个 snapshot/memory（不传全部历史）
- 三层质量检查：程序化校验（免费）+ 每通道语义审校（LLM，world + 各角色独立并行）+
  提交门控（程序化跨通道一致性，0 token）
- 失败分级：局部问题（≤5 个字段级错误）→ 通道内定点修复（~5% token 成本）；
  系统性问题（文件缺失/结构错误/理解偏差）→ 全量回滚重试
- 提取在独立 git 分支进行，每 batch 单独 commit（精确回滚）；全部完成后
  squash merge 回 main（干净历史），extraction 分支可删除
- 支持 Claude CLI 和 Codex CLI 两种后端

运行保障：

- PID 锁防止重复运行，启动时检查工作区干净
- `--background` 模式：后台运行，SSH 断开后存活，日志写入 `extraction.log`
- `--max-runtime` 总时间限制，到期后在 batch 间优雅停止
- 子进程硬超时（提取 3600s、审校 600s）+ 每 batch 最多重试 2 次
- Token/context limit 与 rate limit 区分：前者不重试（相同 prompt 必定再超限），
  后者递增退避重试
- Baseline 恢复：resume 时自动检测 Phase 2.5 产出完整性，缺失则补跑
- Progress 与 `--end-batch` 分离（同 Phase 4 模式）：progress 始终包含完整
  batch plan，`--end-batch` 仅控制运行时执行范围；入口防御性补全应对边缘情况
- 回滚范围覆盖全仓库（不仅限 `works/`），防止 LLM agent 在其他目录写入残留
- 每 30s 心跳显示 PID、内存占用、已用时间；分步耗时追踪和 ETA 预估
