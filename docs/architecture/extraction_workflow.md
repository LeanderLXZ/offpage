# 端到端提取工作流

## 概述

本文档描述从原始小说到可运行角色包的完整提取流程。提取是增量的——
按阶段推进，每个阶段对应一个剧情阶段，阶段 N 累积阶段 1..N 的全部内容。

## 流程总览

```
1. 作品入库
2. 章节归纳（Phase 0，按 chunk 并行）
3. 全书分析（Phase 1：身份合并 → 世界观 → 阶段规划 → 候选角色）
4. 活跃角色确认（Phase 2，用户参与）
5. Baseline 产出（Phase 2.5，全书视野）
6. 1+2N 分层阶段提取（Phase 3，world + char_snapshot×N + char_support×N 并行）
7. 跨阶段一致性检查（Phase 3.5）
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
- 输出：`works/{work_id}/analysis/chapter_summaries/`

### 3. 全书分析（Phase 1）

基于所有章节摘要（不读原文），按顺序执行：

a. **跨 chunk 角色身份合并**：不同 chunk 中以不同名称出现的同一角色统一为
   单一候选条目
b. **世界观概览**：题材类型、力量体系、主要势力、地理结构、大世界线划分、
   核心设定规则。输出：`works/{work_id}/analysis/world_overview.json`
c. **源文件阶段规划**：按自然剧情边界切分（默认目标 10 章，最小 5 章，
   最大 15 章），剧情边界准确性优先于均匀。
   输出：`works/{work_id}/analysis/stage_plan.json`
d. **候选角色识别**：基于身份合并后的角色出场信息。
   输出：`works/{work_id}/analysis/candidate_characters.json`

阶段规划是分析阶段**最核心的产出**——每个 stage 边界直接成为系统的 stage 边界，
世界快照、角色快照、记忆时间线、运行时阶段选择全部建立在此切分之上。

**出口验证（硬性门控）**：Phase 1 完成后程序化检查所有 stage 的 `chapter_count`
是否在 5-15 范围内。违规 stage 会触发 Phase 1 重跑——删除
`stage_plan.json`，带修正反馈重新调用 LLM 产出更精准的切分（最多重试
2 次）。若重试耗尽仍有违规，流程终止（`sys.exit(1)`）。

### 4. 活跃角色确认（Phase 2）

- **用户参与**：用户从候选中选择要建包的目标角色
- 确认后进入 baseline 产出和 1+2N 分层提取模式

### 5. Baseline 产出（Phase 2.5）

基于全书摘要上下文和确认的角色，产出：

- `world/foundation/foundation.json` — 世界基础设定初稿
- `characters/{character_id}/canon/identity.json` — 角色身份初稿
- `characters/{character_id}/manifest.json` — 角色 manifest
- `characters/{character_id}/canon/voice_rules.json` — 基线语言风格骨架
- `characters/{character_id}/canon/behavior_rules.json` — 基线行为模式骨架
- `characters/{character_id}/canon/boundaries.json` — 角色底线禁忌骨架
- `characters/{character_id}/canon/failure_modes.json` — 角色易崩模式骨架

这些 baseline 记录**跨阶段稳定的角色基底**，作为后续 stage 的修正与补充
锚点。阶段性变化由 stage_snapshot 覆盖。

**出口验证**：Phase 2.5 完成后运行 `validate_baseline()`，校验所有
baseline 文件的 schema 合规性。identity/manifest/foundation 为必须
（error），voice_rules/behavior_rules/boundaries/failure_modes 为建议
（warning）。验证失败阻断 Phase 3。

### 6. 1+2N 并行阶段提取

每个阶段采用 1+2N 并行架构：世界提取（1 次调用）+ 各角色快照提取（N 次调用）+ 各角色支持层提取（N 次调用），**同一 stage 内全并行执行**，无先后依赖。

- **char_snapshot** 进程：产出 `stage_snapshots/{stage_id}.json`，接收前一阶段快照作为 delta/风格参照
- **char_support** 进程：产出 `memory_timeline/{stage_id}.json` + baseline 修正，**不接收**前一阶段快照

每次调用只传最近一个相关产物（不传全部历史），减少输入规模。提取超时 3600s。

#### 6.1 世界信息提取（1 次调用）

每阶段产出或更新（LLM 产出）：

- `world/stage_snapshots/{stage_id}.json` — 当前阶段的世界快照
- `world/foundation/` — 如有修正

**对应提示词**：`automation/prompt_templates/world_extraction.md`

#### 6.2 角色快照提取（N 次并行调用，char_snapshot lane）

每阶段产出：

- `characters/{character_id}/canon/stage_snapshots/{stage_id}.json` —
  **自包含快照**，包含该阶段的完整 voice_state、behavior_state、
  boundary_state、relationships、personality、mood、knowledge

**对应提示词**：`automation/prompt_templates/character_snapshot_extraction.md`

#### 6.3 角色支持层提取（N 次并行调用，char_support lane）

每阶段产出或更新：

**Baseline 文件**（每个 stage 都可修正和补充，不限 stage 1）：

- `characters/{character_id}/canon/identity.json`
- `characters/{character_id}/canon/voice_rules.json`
- `characters/{character_id}/canon/behavior_rules.json`
- `characters/{character_id}/canon/boundaries.json`
- `characters/{character_id}/canon/failure_modes.json`

**阶段文件**（LLM 产出）：

- `characters/{character_id}/canon/memory_timeline/{stage_id}.json` —
  该阶段的角色记忆条目

**对应提示词**：`automation/prompt_templates/character_support_extraction.md`

**程序化维护**（0 token，提取后由 `post_processing.py` 自动生成）：

- `characters/{character_id}/canon/memory_digest.jsonl` —
  从 memory_timeline 自动聚合；每条 `summary` 由对应 entry 的
  `digest_summary` **1:1 复制**（遵循 memory_digest_entry.schema.json）
- `characters/{character_id}/canon/stage_catalog.json` — 从 snapshot 元数据自动维护
- `world/stage_catalog.json` — 从世界 snapshot 元数据自动维护（仅 bootstrap 阶段选择，运行时不加载）
- `world/world_event_digest.jsonl` — 从世界 snapshot `stage_events` 自动累积
  （ID 格式 `E-S###-##`，`summary` 即 `stage_events` 原文 1:1 复制，
  importance 按关键词推断）。世界/角色层边界的判定在落笔时完成
  （LLM 写入 `stage_events` 时自控 + repair agent 语义检查层可检测泄漏），
  digest 本身不做过滤。

**自包含快照的生成规则**：

- 阶段 1 快照 ≈ baseline 内容 + 阶段特有字段（事件、心情、关系等）
- 阶段 N 快照以 baseline + 前一阶段快照 + 前一阶段 memory_timeline 为参照，产出完整的当前阶段状态
- **未变化的内容也必须包含在快照中**——快照是自包含的，运行时不依赖 baseline
- `stage_delta` 记录从上一阶段的变化（信息性，便于理解演变弧线）

**长度硬门控**：

- 世界 / 角色 `stage_events`：每条 50–80 字（schema minLength/maxLength）
- memory_timeline `event_description`：150–200 字（schema 硬门控）
- memory_timeline `digest_summary`：30–50 字（schema 硬门控，独立撰写，
  非 `event_description` 机械截断，直接作为 memory_digest 的来源）

**对应提示词**：`automation/prompt_templates/character_extraction.md`（每个角色独立调用）

### 7. 跨阶段一致性检查（Phase 3.5）

Phase 3 全部 stage 提交后、进入 Phase 4 之前，运行跨阶段一致性检查。

**程序化检查**（零 token 开销）：

1. alias 一致性 — stage_snapshot active_aliases vs identity.json aliases
2. 快照字段完整性 — 13 个必填维度是否齐全
3. 关系连续性 — 相邻 stage 间 attitude/trust/intimacy 变化是否有 driving_events
4. evidence_refs 覆盖率 — 空 evidence_refs 比例
5. memory_digest 对应 — memory_digest.jsonl ↔ memory_timeline 一一对应
6. target_map 样本数 — importance-based 阈值（主角≥5, 重要配角≥3, 其他≥1）
7. stage_id 对齐 — 世界/角色 catalog 与 snapshot 目录对齐
8. world_event_digest 对应 — digest 条目数 ↔ world snapshot `stage_events` 逐阶段对应

**LLM 裁定**（可选）：仅在有标记项时调用独立 agent 进行语义裁定。

**产出**：`works/{work_id}/analysis/consistency_report.json`

有 error 级别问题时阻断 Phase 4，需人工处理后继续。

### 8. 场景切分（Phase 4）

Phase 4 与 Phase 3 数据独立——前置条件仅为 `stage_plan.json` 存在
（Phase 1 产物，提供 chapter → stage_id 映射）。常规流程中 Phase 3.5 error 阻断
Phase 4（见 §11.4.2）；`--start-phase 4` 可跳过此门控独立运行。Phase 4 使用独立
`.scene_archive.lock`，其中间目录 `analysis/scene_splits/`
为本地忽略产物，Phase 3 的 repo-wide rollback 不会清掉它们。

**调用粒度**：每章一次 `claude -p`。LLM 输出场景边界标注（起止行号 +
元数据），不输出 full_text。程序根据行号从原文提取 full_text。

**并行**：多章并行处理（`--concurrency`，默认 10）。

**质量保障**：仅程序化校验（行号有效、不重叠、覆盖全章、alias 匹配），
不做语义审校。失败（LLM/解析/校验）同次运行内自动重试（≤2 次），
超限进 ERROR 状态；`--resume` 时 ERROR 重置且 retry_count 清零。

产出：
- `works/{work_id}/retrieval/scene_archive.jsonl`（.gitignore，文件过大）
- 中间文件：`works/{work_id}/analysis/scene_splits/`（每章一个 JSON，.gitignore）
- 进度：`works/{work_id}/analysis/progress/phase4_scenes.json`
- 锁：`works/{work_id}/analysis/.scene_archive.lock`
- 每次启动通过 `reconcile_with_disk()` 与磁盘对账：passed 缺文件
  → 回退 pending；PENDING/中间态有半成品 → 清掉

`scene_id` 格式：`SC-S{stage:03d}-{seq:02d}`（如 `SC-S003-07`）。
阶段号由章节号通过 `stage_plan.json` 查得；seq 为该阶段内从 01
起递增的顺序号（上限 99）。

每条场景条目包含：
- `scene_id` — `SC-S{stage:03d}-{seq:02d}` 格式
- `stage_id` — 由章节号查 stage plan 得出（程序化；stage_plan 是唯一真源）
- `chapter` — 所属章节
- `time` — 故事内时间
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

当阶段提取完成后，如果角色包仍有明显缺口（如某些章节与该角色高度相关
但阶段提取时未充分覆盖），可执行针对性补充：

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
- [ ] memory_timeline 条目是否包含 `memory_id`（`M-S###-##`）、`time`、`location`；`event_description` 是否 150–200 字、`digest_summary` 是否 30–50 字（均为 schema 硬门控）
- [ ] memory_digest.jsonl 是否与 memory_timeline 条目一一对应（summary = digest_summary 1:1 复制）
- [ ] stage_catalog 的阶段数 = stage_snapshots 目录下的文件数
- [ ] evidence_refs 是否有效引用
- [ ] 世界快照是否与角色快照的阶段对齐
- [ ] scene_archive 是否覆盖全部章节
- [ ] scene_archive 的 `characters_present` 是否使用已确认的 character_id

## Baseline 文件的角色

Baseline 文件记录**跨阶段稳定的角色基底**（本性风格、本性行为、底线禁忌、
易崩模式等），在提取流程中有两个用途：

1. **提取参照锚点**：Phase 2.5 产出全书视野骨架，后续 stage 据此修正和补充
2. **跨阶段稳定参照**：提取者用 baseline 判断"角色的本性是什么"，阶段性
   变化写入 stage_snapshot，不写入 baseline

**运行时加载**：identity.json、failure_modes.json、hard_boundaries + 所选
阶段的自包含快照。voice_rules.json 和 behavior_rules.json 不在运行时加载
（voice 和 behavior 状态在 stage_snapshot 中自包含）。

## 阶段间的增量规则

- 每个阶段可以修订任何已有资产（不仅限于当前阶段）
- 如果本阶段原文推翻了之前的结论，应更新 baseline 和受影响的阶段快照
- 进度追踪：`works/{work_id}/analysis/progress/`（pipeline.json + phase3_stages.json）

## 自动化编排

手动提取流程可通过 `automation/` 目录下的编排脚本自动化。

详见 `automation/README.md` 和 `docs/requirements.md` §十一。

编排架构：

```
orchestrator (Python)
    │
    ├── 分析阶段 → claude -p (分析 prompt)
    │
    ├── 用户确认 → 交互式选择角色、确认阶段规划、设定提取范围
    │
    ├── 提取循环 → 每个 stage (1+2N 全并行):
    │       ├── git preflight
    │       ├── claude -p ×(1+2N) (world + char_snapshot×N + char_support×N, 3600s)
    │       ├── 程序化后处理 (digest/catalog, 0 token, idempotent upsert)
    │       ├── repair_agent.run() (统一检测+修复):
    │       │       ├── Phase A: L0–L3 全量检查
    │       │       ├── Phase B: 修复循环 (T0→T1→T2→T3 逐层升级)
    │       │       └── Phase C: 最终语义验证
    │       ├── [PASS] → git commit
    │       └── [FAIL] → stage ERROR (--resume 重置 → PENDING)
    │
    ├── 跨阶段一致性检查 (Phase 3.5):
    │       ├── 程序化检查 (Python, 0 token)
    │       └── 可选 LLM 裁定 (仅有标记项时)
    │
    └── 场景切分 → 每个 stage (可并行):
            └── claude -p (场景切分 prompt)
```

关键设计决策：

- 每个 stage 拆分为 1+2N 次独立 `claude -p` 调用（1 world + N char_snapshot + N char_support），**同一 stage 内全并行**，不共享 session 内存
- 阶段间上下文通过文件系统传递；char_snapshot 只传最近一个 snapshot；char_support 只传最近一个 memory_timeline（不传全部历史）
- 每个 stage 都可修正和补充 baseline（通过 char_support 提取）
- **Repair Agent（统一检测+修复）**：独立模块 `automation/repair_agent/`，
  各 phase 通过统一接口调用。四层检查器（L0 JSON 语法 → L1 schema → L2 结构 → L3 语义）
  与四层修复器（T0 程序化 → T1 局部 LLM → T2 原文 LLM → T3 全文件重生成）**正交**——
  任何层的 issue 都可能需要任何 tier 的修复。修复从最低可用 tier 开始逐层升级，
  每个 tier 有独立重试次数（T0=1, T1=3, T2=3, T3=1）。
  语义 LLM 最多调用 2 次（Phase A 初检 + Phase C 终验），修复循环内只用 0-token L0–L2 复检。
  字段级精确修补（json_path 定位），不整文件回滚。
  安全阀：回归保护（introduced ≥ resolved → 停机）、收敛检测（持续集不变 → 升级）、
  总轮次限制（默认 5 轮）
- 提取在独立 git 分支进行，每 stage 单独 commit（精确回滚）；全部完成后
  squash merge 回 main（干净历史），extraction 分支可删除
- 支持 Claude CLI 和 Codex CLI 两种后端

运行保障：

- PID 锁防止重复运行，启动时检查工作区干净
- `--background` 模式：后台运行，SSH 断开后存活，日志写入 `extraction.log`
- `--max-runtime` 总时间限制，到期后在 stage 间优雅停止
- 子进程硬超时（提取 3600s、repair agent LLM 调用 600s）
- Token/context limit 与 rate limit 区分：前者不重试（相同 prompt 必定再超限），
  后者递增退避重试
- Baseline 恢复：resume 时自动检测 Phase 2.5 产出完整性，缺失则补跑
- Progress 与 `--end-stage` 分离（同 Phase 4 模式）：progress 始终包含完整
  stage plan，`--end-stage` 仅控制运行时执行范围；入口防御性补全应对边缘情况
- 回滚范围覆盖全仓库（不仅限 `works/`），防止 LLM agent 在其他目录写入残留
- 每 30s 心跳显示 PID、内存占用、已用时间；分步耗时追踪和 ETA 预估
