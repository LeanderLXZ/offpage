# 1+2N 分层提取架构（角色提取拆分 + 流程简化）

**日期**：2026-04-16
**范围**：Phase 3 提取流水线 — 角色提取拆分为 snapshot/support 双通道 + 重试/审校流程简化

## 起因

原 1+N 架构中，每个角色的提取由单个 LLM 调用同时产出 `stage_snapshot` 和
`memory_timeline`。这导致：

- 单次调用输出范围过大，prompt 与上下文膨胀
- snapshot 和 support 材料互相干扰，审校和重试粒度粗
- cross-entity 审校增加无效 token 消耗且缺乏明确收益
- stage 级重试代价过高（N+1 次 LLM 全量重跑）

## 变更

### 1. 角色提取拆分：1+N → 1+2N

每个 stage 从 1+N（1 world + N character）改为 1+2N（1 world + N char_snapshot +
N char_support）并行：

- **char_snapshot**：只产出 `stage_snapshots/{stage_id}.json`。读取 baseline 和
  前一个 stage_snapshot，不读 memory_timeline
- **char_support**：只产出 `memory_timeline/{stage_id}.json` + baseline 修正。
  读取 baseline 和前一个 memory_timeline，不读 stage_snapshot

Lane key 格式：`"world"` / `"char_snapshot:{char_id}"` / `"char_support:{char_id}"`

### 2. targeted_fix 重试次数：1 → 2

`max_fix_attempts` 从 1 增加到 2。每次重试累积之前的 findings 反馈给 LLM。

### 3. 移除 cross-entity 审校

- world reviewer 不再读角色 memory_timeline
- character reviewer 不再读 world snapshot
- 每条 lane 的审校只读取自己的产出

### 4. lane_max_retries：2 → 1

每条 lane 最多重提取 1 次。

### 5. 移除 stage 级重试

- 删除 `RETRYING` 状态、`retry_count`、`max_retries`
- lane 耗尽后 stage 直接 → ERROR（终态）
- `--resume` 将 ERROR → PENDING 重新开始

### 6. lane re-extract 后仅审校受影响 lane

使用 `lane_filter` 参数，只对重新提取的 lane 运行审校；已通过的 lane 保留结果。

## 涉及文件

### 核心代码

- `automation/persona_extraction/orchestrator.py` — 1+2N 提取闭包、状态机简化、
  review_filter 机制
- `automation/persona_extraction/prompt_builder.py` — `build_char_snapshot_prompt` /
  `build_char_support_prompt` + 独立 read list；reviewer/fix prompt 适配新 lane_type
- `automation/persona_extraction/review_lanes.py` — autofix 拆分 char_snapshot /
  char_support；lane_key 和 rollback 适配
- `automation/persona_extraction/validator.py` — char_snapshot / char_support
  分别校验
- `automation/persona_extraction/progress.py` — 移除 StageEntry.retry_count、
  RETRYING 状态

### Prompt 模板

- `automation/prompt_templates/character_snapshot_extraction.md` — 新建
- `automation/prompt_templates/character_support_extraction.md` — 新建
- `automation/prompt_templates/semantic_review_char_snapshot.md` — 新建
- `automation/prompt_templates/semantic_review_char_support.md` — 新建

### 文档

- `ai_context/architecture.md` — Phase 3 章节重写
- `ai_context/current_status.md` — 提取描述更新
- `ai_context/requirements.md` — §11 更新
- `ai_context/decisions.md` — Decision 13 更新
- `automation/README.md` — 1+2N、lane 类型、重试策略
- `docs/architecture/extraction_workflow.md` — §6 拆分、流程图、设计决策
- `docs/architecture/system_overview.md` — 阶段 3 描述
- `docs/requirements.md` — Phase 3 流程全面更新
