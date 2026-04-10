# 进度管理架构重构 + 目录扁平化

## 变更概述

重构提取流水线的进度管理架构和目录结构，解决三个问题：

1. `analysis/incremental/` 中间层冗余
2. 进度管理仅覆盖 Phase 3，缺少 Phase 0 和全局流水线追踪
3. `rag/`、`scene_archive/` 命名不准确

## A. 目录扁平化：`analysis/incremental/` → `analysis/`

去除 `incremental/` 中间层，所有分析产物直接存放在 `analysis/` 下：

```
analysis/
  world_overview.json
  source_batch_plan.json
  candidate_characters.json
  consistency_report.json
  chapter_summaries/         # Phase 0 产出
  scene_splits/              # Phase 4 中间产物（原 scene_archive/splits/）
  progress/                  # 新建，进度管理目录
    pipeline.json
    phase0_summaries.json
    phase3_batches.json
    phase4_scenes.json
    extraction.log
  evidence/
  conflicts/
```

## B. 新进度管理架构

- `PipelineProgress`（pipeline.json）：全局流水线进度，记录各 phase 完成状态
- `Phase0Progress`（phase0_summaries.json）：Phase 0 各 chunk 状态（pending/done/failed），
  支持文件存在双重检测
- `Phase3Progress`（phase3_batches.json）：原 `ExtractionProgress` 拆分，batch 状态机
- Phase 4 进度从 `scene_archive/progress.json` 迁移到 `progress/phase4_scenes.json`
- `migrate_legacy_progress()`：老格式 `extraction_progress.json` → 新格式自动迁移

## C. `scene_archive/` → `scene_splits/`

Phase 4 中间产物目录更名：
- 旧：`analysis/incremental/scene_archive/splits/`
- 新：`analysis/scene_splits/`
- progress 文件迁入 `analysis/progress/phase4_scenes.json`

## D. `rag/` → `retrieval/`

运行时检索数据目录更名，反映其实际用途不限于 RAG：
- 旧：`works/{work_id}/rag/`
- 新：`works/{work_id}/retrieval/`

## E. `--start-phase` 参数生效

- `start_phase` 参数在 orchestrator 构造函数中正确传递并使用
- `--start-phase 2.5` 强制重跑 baseline（即使 pipeline 已标记完成）

## F. `--end-batch` 语义修正

- `None`（未指定）= 运行全部 batch
- `0` = 仅运行 baseline（Phase 2.5），不进入 Phase 3 batch 循环
- 正整数 N = 运行 N 个 batch

## G. `baseline_done` 增强

- 除检查 foundation.json 和 identity.json 外，新增 fixed_relationships.json 检查

## 修改文件

### 核心代码
- `automation/persona_extraction/progress.py` — 完全重写
- `automation/persona_extraction/orchestrator.py` — 重构进度管理调用
- `automation/persona_extraction/prompt_builder.py` — 更新路径、修复 `_find_previous_committed_batch` 参数传递
- `automation/persona_extraction/scene_archive.py` — 更新路径
- `automation/persona_extraction/process_guard.py` — 更新路径
- `automation/persona_extraction/git_utils.py` — 更新 rollback 排除列表
- `automation/persona_extraction/cli.py` — 更新进度加载逻辑
- `automation/persona_extraction/consistency_checker.py` — 更新路径
- `automation/persona_extraction/review_lanes.py` — 更新类型注解

### 文档
- `docs/requirements.md` — 全面更新
- `ai_context/` — 全部 6 个文件更新路径引用
- `docs/architecture/extraction_workflow.md` — 更新路径和进度管理描述
- `docs/architecture/system_overview.md` — 更新路径
- `docs/architecture/data_model.md` — 更新路径
- `automation/README.md` — 更新路径和进度文件描述
- `works/README.md` — 更新目录结构和描述
- `simulation/README.md` — 更新路径
- `simulation/retrieval/index_and_rag.md` — 更新路径
- `prompts/shared/最小结构读取入口.md` — 更新路径

### 配置
- `.gitignore` — 更新排除规则
- `automation/prompt_templates/analysis.md` — 更新路径
