# Codex 审计修复——H-4 / H-5 / H-6 + 文档对齐 M-1 / M-2 / M-3

## 背景

上一轮 codex 审计输出 6 High + 3 Medium 条目。本次按 requirements.md
§3 的权威地位与 §11.5 的"repair 失败保留产物"条款，逐项核验并修复。

## 变更清单

### H-4a — chapters_dir 路径对齐 manifest 单一真源

- 文件：`automation/persona_extraction/orchestrator.py`
- 将 `chapters_dir` 从旧路径改为
  `sources/works/{work_id}/chapters`，与 `sources/works/{work_id}/manifest.json`
  的声明一致。

### H-4b — stage plan chapters 字符串解析

- 文件：`automation/repair_agent/context_retriever.py`
- `_get_stage_chapters` 重写：
  - 主路径用正则 `^(\d+)\s*-\s*(\d+)$` 解析 `"NNNN-NNNN"` 字符串；
  - 兼容 `[start, end]` 列表形态作为兜底。
- 动机：stage_plan 目前统一使用字符串形式，原代码仅接受列表形态导致
  T2/T3 source-grounded 修复永远拿不到章节范围。

### H-5a — smart-skip 收紧到 1+2N 全产物

- 文件：`automation/persona_extraction/orchestrator.py`
- `_extraction_output_exists`：除 world snapshot + 每个角色 stage_snapshot
  外，**新增** `memory_timeline/{stage_id}.json` 存在性校验。任一 lane
  缺失则 smart-skip 判负，触发完整 1+2N 重跑。
- 动机：旧逻辑允许 support lane 缺失仍走 skip，与 1+2N 拆分契约冲突。

### H-5b — world stage_catalog 纳入 repair 上下文

- 文件：`automation/persona_extraction/orchestrator.py::_collect_stage_files`
- 在 `world_event_digest` 之后追加 `world/stage_catalog.json` 块，使
  repair agent 的 L0/L1 checker 能看到世界级目录。

### H-5c — post-processing 错误阻断 REVIEWING

- 文件：`automation/persona_extraction/post_processing.py`、
  `automation/persona_extraction/orchestrator.py`
- 签名由 `-> list[str]` 改为 `-> tuple[list[str], list[str]]`，拆分
  errors / warnings：
  - **errors**：world/char snapshot 缺失或不可解析；memory_timeline 缺失
    → 阻断 REVIEWING，状态 FAILED → ERROR。
  - **warnings**：内部 digest / catalog 产物异常 → 只记录不阻断。
- 调用点相应更新，注释标注 §11.5。

### H-6 — repair FAIL 保留产物、不回滚 HEAD

- 文件：`automation/persona_extraction/orchestrator.py`
- 删除 repair-FAIL 分支的 `rollback_to_head(...)` 调用，遵循
  requirements.md §11.5：repair 失败 → stage ERROR，产物保留在磁盘上供
  `--resume` 审视；不做自动回滚重提取。
- **保留**另外两处 rollback：
  - 启动自愈中 "interrupted EXTRACTING" 分支；
  - 抽取阶段 "all lanes failed" 分支。
  两者需要通过回滚清理部分产物，否则下一次 smart-skip 会被欺骗。

### M-1 — manifest 路径单一真源

- 统一为 `sources/works/{work_id}/manifest.json`。
- 涉及：
  - `docs/architecture/schema_reference.md`
  - `docs/architecture/extraction_workflow.md`
  - `simulation/README.md`
  - `simulation/flows/startup_load.md`
  - `prompts/shared/最小结构读取入口.md`

### M-2 — current_status.md 刷新

- `ai_context/current_status.md`：
  - 项目阶段改为 "Phase 2.5 complete; Phase 3 pending — no stages
    committed yet; Phase 4 scene archive independently done"。
  - 首个工作包状态同步更新。
  - Smart resume 描述扩展为显式说明 1+2N 全产物收紧。

### M-3 — 删除历史遗留 character_extraction.md

- 删除：`automation/prompt_templates/character_extraction.md`
- 同步清理：
  - `automation/persona_extraction/prompt_builder.py` 中 LEGACY 注释块
  - `docs/architecture/extraction_workflow.md` 中对旧文件的引用，改为
    指向 `character_snapshot_extraction.md` + `character_support_extraction.md`
  - `docs/requirements.md` 中相同引用

## 验证

- `python -c "from automation.persona_extraction.orchestrator import
  ExtractionOrchestrator; from automation.persona_extraction.post_processing
  import run_stage_post_processing; from automation.repair_agent
  .context_retriever import ContextRetriever"` 通过。
- 全仓回归审计：由 Explore 子代理平行扫描遗留引用、跨文件不一致、
  漏改项；补齐了 `current_status.md` 的两处 drift。

## 两项自主决策记录

1. **H-6 选择保留产物** 而非回滚：依据 requirements.md §3 自我声明的
   权威地位 + §11.5 明文"不触发回滚重提取——产物保留在磁盘上"。
2. **M-1 单一 manifest** 置于 `sources/works/{work_id}/`：依据
   requirements.md §8.4 对 sources 目录的权威声明。
