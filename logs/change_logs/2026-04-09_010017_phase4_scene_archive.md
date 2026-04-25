# Phase 4 场景切分实现

**时间**: 2026-04-09 01:00 ET
**变更类型**: 新功能实现 + 架构更新 + 路径迁移

## 变更内容

### 新增文件

- `automation/persona_extraction/scene_archive.py` — Phase 4 完整实现：
  逐章并行 LLM 调用做场景边界标注，程序提取 full_text，程序化校验，
  进度追踪，断点恢复，合并输出
- `automation/prompt_templates/scene_split.md` — 场景切分 prompt 模板

### 修改文件

- `automation/persona_extraction/cli.py` — 新增 `--start-phase` (0-4)、
  `--concurrency` (默认 10) 参数；Phase 4 独立执行路径
- `automation/persona_extraction/orchestrator.py` — 集成 Phase 4 调用
  （Phase 3.5 完成后自动触发）；新增 start_phase/concurrency 参数
- `automation/persona_extraction/prompt_builder.py` — 新增
  `build_scene_split_prompt()` 函数
- `.gitignore` — 新增 `works/*/rag/` 排除规则

### 路径迁移

scene_archive 存储位置从 `sources/works/{work_id}/rag/` 迁移到
`works/{work_id}/rag/`。原因：`sources/` 定位为原始输入层，不应存放
提取产出。以下文件中的路径引用已同步更新：

- `docs/requirements.md` (§12.5, §12.9)
- `docs/architecture/data_model.md`
- `docs/architecture/extraction_workflow.md`
- `ai_context/architecture.md`
- `ai_context/decisions.md`
- `ai_context/requirements.md`
- `simulation/README.md`
- `simulation/retrieval/index_and_rag.md`

### scene_id 格式变更

从 `scene_{zero_padded_number}` 改为 `scene_{chapter}_{seq}`
（如 `scene_0015_003`），支持并行处理时各章独立编号。
已更新 `simulation/retrieval/index_and_rag.md` 和 `docs/requirements.md`。

## 设计决策

1. Phase 4 与 Phase 3 完全独立，前置条件仅为 source_batch_plan.json
2. LLM 不输出 full_text，只标注行号，程序从原文提取（省 token + 零出错）
3. 仅程序化校验，不做语义审校（场景切分任务结构化程度高）
4. 中间产物在 `works/{work_id}/analysis/incremental/scene_archive/`
