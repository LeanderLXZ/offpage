# 端到端提取工作流

## 概述

本文档描述从原始小说到可运行角色包的完整提取流程。提取是增量的——
按阶段推进，每个阶段对应一个剧情阶段，阶段 N 累积阶段 1..N 的全部内容。

## 流程总览

```
1. 作品入库
2. 章节归纳（Phase 0，按 chunk 并行）
3. 全书分析（Phase 1：身份合并 → 世界观 → 阶段规划 → 候选角色）
4. 活跃角色确认（Phase 1.5，用户参与）
5. Baseline 产出（Phase 2，全书视野）
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
- 创建元数据（三份均为 schema 硬门控）：
  - `sources/works/{work_id}/manifest.json`
    （schema：`schemas/work/work_manifest.schema.json`）
  - `sources/works/{work_id}/metadata/book_metadata.json`
    （schema：`schemas/work/book_metadata.schema.json`）
  - `sources/works/{work_id}/metadata/chapter_index.json`
    （schema：`schemas/work/chapter_index.schema.json`）
- 交付前 gate：运行 `python -m automation.ingestion.validator <work_id>`，
  任一文件不过 schema 必须回修，才可进入 Phase 0。

**对应提示词**：`prompts/ingestion/原始资料规范化.md`

### 2. 章节归纳（Phase 0）

- 将全书按分组（chunk，约 20-25 章/组）归纳
- 多 chunk 并行处理（`--concurrency` 控制，默认 10）
- 产出每章的结构化摘要（事件、出场角色、地点、情绪基调、身份变化线索）
- JSON 修复：L1 程序化 → L2 LLM（600s）→ L3 全量重跑（最多 1 次）
- **Schema gate**：每个 chunk 落盘后跑 jsonschema (`schemas/analysis/chapter_summary_chunk.schema.json`) 校验，
  字段 bound + `additionalProperties:false` 违反归入同一 fail 类型（具体数字以 schema 为准）；失败路由到 L3 全量重跑，
  把上次错误（schema 失败首条 / JSON 解析失败 desc）作为 `prior_error` 注入新 prompt 的 `{retry_note}` 段
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

**出口验证（硬性门控）**：Phase 1 完成后跑两层校验，**共享同一 retry 预算**
（`[phase1].exit_validation_max_retry`，默认 2 次）：

1. **jsonschema 校验**：三件套各自跑 `Draft202012Validator.iter_errors`
   （`schemas/analysis/{world_overview,stage_plan,candidate_characters}.schema.json`），
   覆盖结构 / bound / enum / pattern。
2. **stage `chapter_count` 5-15 限制**（`_check_stage_plan_limits`，与 schema
   `chapter_count: minimum 5, maximum 15` 同义；belt-and-suspenders）。

任一层失败 → 把首条 schema 错误 + stage 限制违规明细合并进
`correction_feedback`（按 `build_analysis_prompt(correction_feedback=...)`
追加到 prompt 的"⚠️ 修正要求"段），删除失败的文件让 LLM 重生（通过校验的
文件保留），重新跑 Phase 1。若重试耗尽仍 fail，流程终止（`sys.exit(1)`）。

### 4. 活跃角色确认（Phase 1.5）

- **用户参与**：用户从候选中选择要建包的目标角色
- 确认完成后 orchestrator 程序化写出
  `works/{work_id}/manifest.json`（schema：
  `schemas/work/works_manifest.schema.json`；写入器：
  `automation.persona_extraction.manifests.write_works_manifest`）
- 进入 baseline 产出和 1+2N 分层提取模式

### 5. Baseline 产出（Phase 2）

基于全书摘要上下文和确认的角色，产出：

- `world/foundation/foundation.json` — 世界基础设定初稿
- `world/foundation/fixed_relationships.json` — 世界级固定关系骨架
- `characters/{character_id}/canon/identity.json` — 角色身份初稿
  （角色级唯一恒定文件）
- `characters/{character_id}/manifest.json` — 角色包 manifest

identity 是 character-level 唯一恒定文件，记录角色基础事实
（aliases / core_wounds / key_relationships 等），作为后续 stage 的
修正锚点。voice / behavior / boundary / failure_modes 不在 Phase 2
产出——由 Phase 3 char_snapshot lane 在每个 stage_snapshot 中直接
生成（S001 从原文 + identity 推演基线种子，S002+ 从前一 stage_snapshot
演变）。

Phase 2 baseline 完成后，orchestrator 程序化写出
`works/{work_id}/world/manifest.json`（schema：
`schemas/world/world_manifest.schema.json`；写入器：
`automation.persona_extraction.manifests.write_world_manifest`）。

**出口验证**：Phase 2 完成后运行 `validate_baseline()`，校验所有
baseline 文件的 schema 合规性。works manifest / world manifest /
identity / 角色 manifest / foundation / fixed_relationships 全部为
必须（error）。验证失败阻断 Phase 3。

### 6. 1+2N 并行阶段提取

每个阶段采用 1+2N 并行架构：世界提取（1 次调用）+ 各角色快照提取（N 次调用）+ 各角色支持层提取（N 次调用），**同一 stage 内全并行执行**，无先后依赖。

- **char_snapshot** 进程：产出 `stage_snapshots/{stage_id}.json`（含本阶段全量 voice / behavior / boundary / failure_modes 字段），接收 identity + 前一阶段快照作为 delta/风格参照
- **char_support** 进程：产出 `memory_timeline/{stage_id}.json` + identity 修正（按需），**不接收**前一阶段快照

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
  boundary_state、failure_modes、relationships、personality、mood、knowledge

**对应提示词**：`automation/prompt_templates/character_snapshot_extraction.md`

#### 6.3 角色支持层提取（N 次并行调用，char_support lane）

每阶段产出或更新：

**identity 修正**（每个 stage 都可修正补充，不限 stage 1）：

- `characters/{character_id}/canon/identity.json`

**阶段文件**（LLM 产出）：

- `characters/{character_id}/canon/memory_timeline/{stage_id}.json` —
  该阶段的角色记忆条目

**对应提示词**：`automation/prompt_templates/character_support_extraction.md`

**程序化维护**（0 token，提取后由 `post_processing.py` 自动生成）：

- `characters/{character_id}/canon/memory_digest.jsonl` —
  从 memory_timeline 自动聚合；每条 `summary` 由对应 entry 的
  `digest_summary` **1:1 复制**（遵循 character/memory_digest_entry.schema.json）
- `characters/{character_id}/canon/stage_catalog.json` — 从 snapshot 元数据自动维护
- `world/stage_catalog.json` — 从世界 snapshot 元数据自动维护（仅 bootstrap 阶段选择，运行时不加载）
- `world/world_event_digest.jsonl` — 从世界 snapshot `stage_events` 自动累积
  （ID 格式 `E-S###-##`，`summary` 即 `stage_events` 原文 1:1 复制，
  importance 按关键词推断）。世界/角色层边界的判定在落笔时完成
  （LLM 写入 `stage_events` 时自控 + repair agent 语义检查层可检测泄漏），
  digest 本身不做过滤。

**自包含快照的生成规则**：

- 阶段 1 快照：基于本阶段原文 + identity 直接推演基线状态全字段（voice_state / behavior_state / boundary_state / failure_modes 等），不再依赖 4 件套 baseline
- 阶段 N 快照以 identity + 前一阶段快照为参照，产出完整的当前阶段状态
- **未变化的内容也必须包含在快照中**——快照是自包含的；运行时与 identity 配套加载即可
- `stage_delta` 记录从上一阶段的变化（自由文本），必须捕捉 (B) 关键变化 + (D) 消除原因，禁止"无明显变化"敷衍
- **prev_stage 处理规则**：(A) 未出场继承 / (B) 出场且变化 重写 / (C) 出场且无变化 保留 / (D) resolved-revealed-消除 + per-stage 推演原则的权威定义见 `automation/prompt_templates/character_snapshot_extraction.md` §核心规则 #2

**长度硬门控**：所有字段级长度限制由对应 schema 的 `minLength` /
`maxLength` 承担——`stage_events` 每条一句话、`event_description` 需有
完整因果链、`digest_summary` 是独立撰写的精简检索摘要（非
`event_description` 的机械截断，直接作为 memory_digest 来源）。具体
数值以 schema 文件为准。

**对应提示词**：步骤 6 按 1+2N 拆分为 `character_snapshot_extraction.md`
（角色快照）与 `character_support_extraction.md`（memory_timeline + identity
校正）两个独立提示词，各角色并行调用。详见上文步骤 6a / 6b。

#### 6.4 Lane 级失败诊断

任一 lane 调用失败时（含超时、exit≠0、token_limit、rate_limit），
自动在 `works/{work_id}/analysis/progress/failed_lanes/` 写入单独日志：

- 文件名：`{stage_id}__{lane_type}_{lane_id}__{pid}.log`
- 内容：lane 元数据 + `duration` + `returncode` + 从 CLI JSON 解析到的
  `subtype` / `num_turns` / `total_cost_usd` + 完整 stdout + stderr
- 每次重试都写一份（按 pid 去重），便于重试序列复盘
- `run_with_retry` 通过 `on_failure` 回调把每次失败的 `LLMResult`
  交回编排层落盘
- prompt 本身不入盘（可由 git 状态 + stage_id 复现；日志只记 CLI 输出）
- 目录随 `progress/` 一并被 `.gitignore`

PID 打印 / heartbeat 行统一带 `[{lane_name}]` 标签
（`[world]` / `[char_snapshot:<id>]` / `[char_support:<id>]`），
日志 tail 时不需反推 PID 与 lane 的对应关系。

**Heartbeat 输出策略**：`claude -p` / `codex` 子进程的 30s 心跳行只在
`sys.stderr.isatty()` 时打到终端 stderr，避免 `--background` 模式下
持续污染 `extraction.log`。同时保留最后 20 条心跳样本到内存环形
buffer；子进程 timeout / 非零退出时 `logger.warning` 一次性 flush 到
log，失败诊断所需的内存 / elapsed 曲线不丢失。间隔仍由
`[runtime].heartbeat_interval_s` 控制（默认 30s）。

#### 6.5 Lane 级 resume

`StageEntry.lane_states: dict[str, str]` 追踪每个 lane 的完成状态：
键为 `world` / `snapshot:{char_id}` / `support:{char_id}`，值为
`"complete"` 或键缺失（= 未开始/未完成）。

**完成判据**（两者同时成立，在主线程 `as_completed` 循环中判定）：

1. `run_with_retry` 返回 `success=True`
2. 该 lane 的产物文件通过 `verify_lane_output`（存在 + JSON 可解析）

任一条件不满足，结果被降级为失败，lane 不写 complete 标记。

**失败保留契约**：任一 lane 失败 → stage 迁移 ERROR，已完成 lane 的产物
与 `lane_states` 条目全部保留在磁盘上，**不触发** `rollback_to_head`。
外部擦盘安全网有两条分支，都复用 `_extraction_output_exists`（逐 lane 校验
1+2N 产物存在且 JSON 可解析）：

- **REVIEWING** 在恢复时若检测到产物缺失：`clear_lane_states` 后重走
  PENDING——磁盘已无产物，无需回滚。
- **PASSED** 在恢复时若检测到产物缺失：直接转 FAILED → ERROR（
  `error_message="stage products missing after gate PASS — refusing to
  commit deletions"`），拒绝把 `git add -A works/` 带入的删除一起提交；
  操作者恢复文件后再 `--resume`。

**`--resume` 行为**：

1. `run_extraction_loop` 把 ERROR/FAILED stage 的 state 重置到 PENDING；
   `error_message` 与 `last_reviewer_feedback` 清空，`lane_states` **保留**
2. `_process_stage` 进入 PENDING 时先做磁盘对账——任何 `lane_states` 标
   complete 但文件丢失/不可解析的条目立即 reset
3. 若对账后仍有 complete 标记（`is_partial_resume=True`），preflight 的
   `ignore_patterns` 扩展 `expected_lane_dirty_paths`——覆盖 1+2N 每 lane
   的产物路径 + 每角色的 identity.json
4. `missing_lanes(target_characters)` 给出待跑列表，`ThreadPoolExecutor`
   只提交这些 lane
5. 待跑列表中每个 `support:{c}` 在子进程启动前调用
   `reset_paths(project_root, baseline_paths(work_root, c))`，把
   identity.json 恢复到 HEAD，抹掉上一次半写入的残留
6. 主线程 `as_completed` 循环：lane 成功 → `mark_lane_complete` +
   立即 `phase3.save`；失败累计到 `extraction_errors`
7. 循环结束后若 `all_lanes_complete == False` → stage → ERROR，
   `lane_states` 保留，下一次 `--resume` 继续步骤 1

`phase3_stages.json` 通过 temp file + `os.replace` 原子写，保证 SIGKILL
打断写盘时不会留下残缺 JSON。最坏场景：丢掉最后一次 `mark_lane_complete`
的落盘 → resume 时该 lane 被重跑一次（幂等）。

### 7. 跨阶段一致性检查（Phase 3.5）

Phase 3 全部 stage 提交后、进入 Phase 4 之前，运行跨阶段一致性检查。

**程序化检查**（零 token 开销）：

1. alias 一致性 — stage_snapshot active_aliases vs identity.json aliases
2. 快照字段完整性 — 必填维度是否齐全（以 `schemas/character/stage_snapshot.schema.json` 的 `required` 列表为准）
3. 关系连续性 — 相邻 stage 间 attitude/trust/intimacy 变化是否有 driving_events
4. memory_digest 对应 — memory_digest.jsonl ↔ memory_timeline 一一对应
5. memory_digest 摘要一致 — `memory_digest.summary` 与对应 `digest_summary` 文本完全相等（1:1 拷贝契约）
6. target_map 样本数 — importance-based 阈值（主角≥5, 重要配角≥3, 其他≥1）
7. stage_id 对齐 — 世界/角色 catalog 与 snapshot 目录对齐
8. world_event_digest 对应 — digest 条目数 ↔ world snapshot `stage_events` 逐阶段对应
9. world_event_digest 摘要一致 — `world_event_digest.summary` 与对应 `stage_events[i]` 文本完全相等（1:1 拷贝契约，i 由 `event_id` 的 seq 推得）

**LLM 裁定**（可选）：仅在有标记项时调用独立 agent 进行语义裁定。

**产出**：`works/{work_id}/analysis/consistency_report.json`

有 error 级别问题时阻断 Phase 4，需人工处理后继续。

**提交契约**：编排器在 `save_report` 之后、`_offer_squash_merge` 之前
在 extraction 分支上 commit `consistency_report.json`
（`phase3.5: consistency_report S###..S###`），不分 pass/fail。未提交的
报告会以 dirty 状态挡住 `checkout_main`，也会被 squash-merge 漏掉。
同理，一致性检查器加载 JSON/JSONL 源文件必须**只读**——不再顺带触发
L1 JSON 修复写盘（修复是 repair_agent 的职责，Phase 3.5 不越权改写已
COMMITTED 的产物）。

### 8. 场景切分（Phase 4）

Phase 4 与 Phase 3 数据独立——前置条件仅为 `stage_plan.json` 存在
（Phase 1 产物，提供 chapter → stage_id 映射）。**Phase 4 可与 Phase 3
并行、先行或后行完成，无时序依赖**；`pipeline.json` 中 phase_4 先于
phase_3 完成是允许状态。常规流程中 Phase 3.5 error 阻断
Phase 4（见 §11.4.2）；`--start-phase 4` 可跳过此门控独立运行。Phase 4 使用独立
`.scene_archive.lock`，其中间目录 `analysis/scene_splits/`
为本地忽略产物。

**调用粒度**：每章一次 `claude -p`。LLM 输出场景边界标注（起止行号 +
元数据），不输出 full_text。程序根据行号从原文提取 full_text。

**并行**：多章并行处理（`--concurrency`，默认 10）。

**质量保障**：程序化校验（行号有效、不重叠、覆盖全章、alias 匹配）
**+ jsonschema gate**（`schemas/analysis/scene_split.schema.json`；
字段 bound + `additionalProperties:false` 由 schema 权威定义），
schema 失败和手写 fail 一起进 errors list；不做语义审校。
失败（LLM/解析/校验/schema）同次运行内自动重试（≤2 次），重试时
LLM 通过 `prior_error` 看到上次 errors 拼接（`build_scene_split_prompt(prior_error=...)`）；
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
- [ ] memory_timeline 条目是否包含 `memory_id`（`M-S###-##`）、`time`、`location`；`event_description` / `digest_summary` 长度是否通过 schema 硬门控
- [ ] memory_digest.jsonl 是否与 memory_timeline 条目一一对应（summary = digest_summary 1:1 复制）
- [ ] stage_catalog 的阶段数 = stage_snapshots 目录下的文件数
- [ ] 世界快照是否与角色快照的阶段对齐
- [ ] scene_archive 是否覆盖全部章节
- [ ] scene_archive 的 `characters_present` 是否使用已确认的 character_id

## Baseline 文件的角色

`identity.json` 是**唯一**的角色级 baseline 文件，记录跨阶段稳定的
角色基础事实（aliases / core_wounds / key_relationships 等）：

1. **提取参照锚点**：Phase 2 产出全书视野骨架，后续 stage 由
   char_support 据此修正和补充
2. **运行时加载**：与所选阶段的自包含 stage_snapshot 配套加载

voice / behavior / boundary / failure_modes 的状态由 stage_snapshot
演变链承载——每个 stage_snapshot 含本阶段全量字段，无独立 baseline
文件，运行时也无需合并。

## 阶段间的增量规则

- 每个阶段可以修订 identity（不仅限于当前阶段）；voice / behavior /
  boundary / failure_modes 的演变直接体现在每阶段新产出的
  stage_snapshot 中
- 如果本阶段原文推翻了之前的 identity 结论，char_support 直接更新
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
    │       ├── repair_agent per-file 并发 (ThreadPoolExecutor, 默认 10):
    │       │       └── 对每个待修文件独立跑 coordinator.run(files=[single]):
    │       │               ├── Lifecycle 1 (Phase A→B→C, T3 enabled)
    │       │               │       ├── Phase A: L0–L3 全量检查
    │       │               │       ├── Phase B: 修复循环 (T0→T1→T2→T3 逐层升级
    │       │               │       │       + 每轮末 L3 gate
    │       │               │       │       + 源文件问题 triage: pre-T3 & post-gate)
    │       │               │       │       T3 一旦触发 → 立即返回 (跳 L3 gate / Phase C)
    │       │               │       │       → 状态机重置 → lifecycle 2
    │       │               │       └── Phase C: 最终确认 (T3 未触发时, 复用最后一次 gate)
    │       │               └── Lifecycle 2 (T3 disabled, 仅在 lifecycle 1 触发 T3 后进入)
    │       │                       ├── Phase A: 重扫 (滤掉已 accept 的 fingerprint)
    │       │                       ├── Phase B: 同 lifecycle 1 但禁用 T3, 升 T3 即 T3_EXHAUSTED
    │       │                       └── Phase C: 同 lifecycle 1
    │       ├── 程序化后处理重跑 (digest/catalog, 0 token, idempotent)
    │       │       └── 在 transition(PASSED) 之前无条件重跑
    │       │           PASSED 语义 = repair 通过 ∧ PP 已同步
    │       │           SIGKILL 中断 → state 留 REVIEWING, --resume
    │       │             重入 Step 4 再跑 repair + PP (幂等)
    │       ├── [全部文件 PASS + PP 重跑成功] → transition(PASSED) → git commit
    │       └── [任一文件 FAIL 或 PP 重跑失败] → stage ERROR (--resume 重置 → PENDING)
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
- 每个 stage 都可修正和补充 identity（通过 char_support 提取）
- **Repair 按文件并发**：`orchestrator` 在每个 stage 的 Repair 步骤
  用 `ThreadPoolExecutor(max_workers=[repair_agent].repair_concurrency)`
  （默认 10）对每个待修文件独立调用 `coordinator.run(files=[single])`。
  coordinator 本就是纯 per-file 逻辑（跨文件一致性由 Phase 3.5 独立
  承担），per-file 并发是调用方式的改变，不动 coordinator 内部实现。
  Extract 池（1+2N）与 Repair 池**串联不共存**，峰值并发 = max(5, 10)。
  订阅 rate_limit 由 `RateLimitController` 进程单例统一管理。
- **Repair Agent 结构化事件日志**：每个待修文件独立打开一个
  `RepairRecorder`，写到
  `works/{work_id}/analysis/progress/repair_logs/repair_{stage_id}_{slug(file)}.jsonl`。
  `slug(file)` = 路径末两段 + 8 位 md5 摘要，避免中文路径 ASCII 折叠后
  冲突。coordinator 在每个 phase 起止、每条 blocking issue、每轮
  fix、L3 gate 结果、lifecycle 信号、最终结论处 append 一条 JSON 事件
  （含 fingerprint / file / json_path / rule / severity / message /
  start_tier / cycle 等字段；`cycle` 0/1 区分两个 lifecycle）。文件随
  `progress/` 一并 `.gitignore`；事后可
  用 `jq` 或脚本复盘"S001 里某个文件的第 3 个 issue 是什么 / 在哪个
  tier 被修"。
- **Repair Agent（统一检测+修复）**：独立模块 `automation/repair_agent/`，
  各 phase 通过统一接口调用。四层检查器（L0 JSON 语法 → L1 schema → L2 结构 → L3 语义）
  与四层修复器（T0 程序化 → T1 局部 LLM → T2 原文 LLM → T3 全文件重生成）**正交**——
  任何层的 issue 都可能需要任何 tier 的修复。修复从最低可用 tier 开始逐层升级，
  每个 tier 有独立重试次数（T0=1, T1=3, T2=3, T3=1）。T3 触发受 `max_lifecycles_per_file=2`
  约束：lifecycle 1 触发 T3 后状态机重置进入 lifecycle 2，lifecycle 2 禁用 T3，
  升 T3 即 `T3_EXHAUSTED`。Lifecycle 1 的 T3 prompt 携带 `prior_attempt_context`
  （已修+未修指纹摘要 ~200 token）。
  Phase B 每轮在 L0–L2 scoped recheck 后，对"本轮被修改 + Phase A 有过 L3 问题"的
  文件集合跑一次 **L3 gate**，把语义层的失败回灌进下一轮 issue 队列——关闭
  "T3 谎报语义已修但 Phase C 才发现" 的窗口。Phase C 优先复用最后一次 gate 的结果。
  字段级精确修补（json_path 定位），不整文件回滚。
  安全阀：回归保护（introduced ≥ resolved → 停机）、收敛检测（持续集不变 → 升级）、
  **L3 gate 反复**（连续两轮 gate 返回相同 blocking 集合 → 语义层不收敛 → 出 Phase C 报错）、
  Lifecycle 上限（默认 2，lifecycle 2 升 T3 即 T3_EXHAUSTED）、
  总轮次限制（每 lifecycle 默认 5 轮）
- **源文件问题 triage**（`triage_enabled`）：两条 accept_with_notes 通道，
  共用单文件上限 `accept_cap_per_file=5`。
  （A）**L3 `source_inherent`（LLM）**——某些 L3 残留不是提取错误，而是源小说
  本身的 bug（作者逻辑矛盾、typo、角色名/代称混用、世界规则冲突等）。在两个点
  做一次轻量级 LLM 判定：(1) pre-T3——若残留全是源文件自带问题，跳过 20 分钟
  的 T3 全文件重生成；(2) post-L3-gate——T3 跑完后的最后一次"接受与否"机会。
  反作弊完全程序化：每条接受判定必须引用 `chapter_number + line_range + 逐字
  quote`，程序用 `chapter_text.find(quote) >= 0` 校验；T2/T3 修复器自带
  "source_inherent" 自报通道，可直接把证据交给 triager 做 prior。
  （B）**L2 `coverage_shortage`（程序，0 token）**——L2 `min_examples` 规则
  判定字段条数不足 `importance_min_examples`（主角≥5 / 重要配角≥3 / 其他≥1）
  时，issue 降级为 `severity=warning + coverage_shortage=True`，路由
  `START_TIER=T2, MAX_TIER=T2`（跳过 T0/T1/T3）。T2 单次 source_patch 后仍不足
  → coordinator 程序构造 `SourceNote`（`discrepancy_type="coverage_shortage"`）
  直接收录，0 LLM 调用。原文素材不够就是不够——T0 无法凭空造例、T1 无原文易
  胡编、T3 整文件重写也无法让原文变长。quote 由程序选取该阶段首章的一段
  子串，仍走同一 `chapter_text.find(quote) >= 0` 校验。
  两条通道被接受的 issue 都写入 `{entity}/canon/extraction_notes/{stage_id}.jsonl`
  （世界级产物写到 `world/extraction_notes/`），附带 SHA-256 锚定以便将来原
  章节改动时自动标记 stale。stage 仍标记 COMMITTED，sidecar notes 作为审计
  痕迹和未来 fixer 的线索；**runtime 不消费这些 notes**（仅审计）。Phase 3.5
  一致性检查遇到 min_examples 不足时，若有匹配 json_path 的 coverage_shortage
  SourceNote 则视为已达标、不报 warning。
- **Lifecycle 重置**：T3 跑完后**不做即时 corruption 检查**；T3 输出
  直接作为 lifecycle 2 的输入。Lifecycle 2 的 Phase A 会重扫所有 checker
  层（L0/L1/L2/L3）——若 T3 真把文件结构破坏了，L0/L1/L2 会在 lifecycle 2
  Phase A 立即报 error，仍走正常 fixer 链；若新 error 升到 T3 即
  `T3_EXHAUSTED`（lifecycle 2 禁用 T3）。这相当于 corruption 止损被合并
  进了 lifecycle 2 Phase A 的全量重扫，不再需要单独的 Post-T3 scoped 检查。
- 提取在独立 git 分支（`extraction/{work_id}`）进行，每 stage 单独 commit
  （精确回滚）；全部完成后 squash merge 到 `library` 分支（默认目标，可由
  `[git].squash_merge_target` 配置），**不回流 `main`**——`main` 只承载
  框架，作品 artefact 永久归档在本地 `library` 分支。**squash 成功后
  orchestrator 交互 offer（`[y/N]`，默认 N）跑 `git branch -D
  extraction/{work_id}` + `git gc --prune=now` 回收 blob**，否则历次 regen
  commit 仍可达、长期占盘；`library` squash 是唯一保留记录。分支删除是
  destructive 操作，即使 `[git].auto_squash_merge=true` 也仍交互询问，
  必须用户明确 `y` 才执行
- 分支纪律落实（见 `ai_context/architecture.md` §Git Branch Model）：
  - `run_extraction_loop` / `run_full` 把 `create_extraction_branch` +
    baseline rerun + Phase 3 循环整体包进 `try / finally:
    checkout_main(...)`，任何退出路径（DONE / BLOCKED / `--end-stage` /
    Ctrl+C / 异常 / `sys.exit`）工作树都回到 `main`
  - `checkout_main` / `preflight_check` 接受 `scope_paths` 参数，
    orchestrator 传入 `["works/{work_id}/"]`——scope 内有脏文件则拒绝
    切换 / 拒绝启动；scope 外的脏改动（编辑器临时状态等）静默容许，
    保留"半 stage 产物不跟到 `main`"的不变量
  - SessionStart Claude Code hook（`.claude/hooks/session_branch_check.sh`）
    新会话检测"非 main 分支 + 无 orchestrator 进程"的异常组合并提示
- 支持 Claude CLI 和 Codex CLI 两种后端

运行保障：

- PID 锁防止重复运行，启动时检查工作区干净
- `--background` 模式：后台运行，SSH 断开后存活，日志写入 `extraction.log`
- 启动时滚动 `extraction.log`：现有日志重命名为 `.1`，旧的 `.N` 依次后移，
  超过 `[logging].extraction_log_backup_count`（默认 3）的最旧一份被删除。
  保证每次启动都是干净日志，磁盘占用有上限。设为 0 关闭滚动
- `--max-runtime` 总时间限制，到期后在 stage 间优雅停止
- 子进程硬超时（提取 3600s、repair agent LLM 调用 600s；阈值由
  `automation/config.toml` 的 `[phase3]` 段控制）
- Token/context limit 与 rate limit 区分：前者不重试（相同 prompt 必定再超限），
  后者由 `RateLimitController` 暂停所有新请求直到 reset，再重发同一 prompt
  （**不消耗重试次数**，详见 `docs/requirements.md` §11.13）。订阅模式下
  reset 时间从 stderr 解析（PT/PST/PDT/ET/UTC 等时区识别）；解析失败时
  以最小 `claude -p "1" --max-turns 1` 探测限额是否解除。周限额等待 ≥
  `[rate_limit].weekly_max_wait_h`（默认 12h）则写
  `rate_limit_exit.log` 并以 exit code 2 停机
- Baseline 恢复：resume 时自动检测 Phase 2 产出完整性，缺失则补跑
- Progress 与 `--end-stage` 分离（同 Phase 4 模式）：progress 始终包含完整
  stage plan，`--end-stage` 仅控制运行时执行范围；入口防御性补全应对边缘情况
- 回滚范围覆盖全仓库（不仅限 `works/`），防止 LLM agent 在其他目录写入残留
- 每 30s 心跳显示 PID、内存占用、已用时间；分步耗时追踪和 ETA 预估
