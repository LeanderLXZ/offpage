# 提取架构重构：1+N 分层提取 + 输入裁剪 + 质量流程改进

日期：2026-04-09

## 背景

Phase 3 批次提取在 batch_003/004 出现反复超时（30min 硬超时）。排查发现两个根因：
1. `_build_read_list()` 使用 `rglob("*")` 将 canon/ 和 world/ 下**全部历史文件**传给 LLM，导致输入规模随批次线性增长
2. 单次调用同时处理世界 + 所有角色，任务过重，agent 行为随机性大

同时 targeted fix 后仅跑程序化校验（不重跑语义审校），以及 commit 后不清空 feedback/error 字段，存在流程缺陷。

## 变更内容

### 1. 提取调用拆分：单体 → 1+N 并行

- **Phase A**：世界提取（1 次 `claude -p` 调用）→ 生成 world stage_snapshot
- **Phase B**：角色提取（N 次 `claude -p` 并行，ThreadPoolExecutor）→ 各角色独立产出
- 角色调用依赖 Phase A 的 world_snapshot 作为事实参照
- 新增 prompt templates：`world_extraction.md`、`character_extraction.md`
- 旧 `coordinated_extraction.md` 保留用于 legacy（reviewer/targeted-fix 参照）

### 2. 输入裁剪：全量历史 → 最近一份

- `_build_world_read_list()`：只传 world foundation + 最近一个 world stage_snapshot + stage_catalog + 原文
- `_build_character_read_list()`：只传角色 baseline 文件 + 最近一个 stage_snapshot + 最近一个 memory_timeline + memory_digest + stage_catalog + world_snapshot + 原文
- 旧 `_build_read_list()` 保留为 legacy wrapper（合并 world + all characters）

### 3. Targeted fix 后重跑原检查层

- 新增 `fail_source` 字段（"programmatic" / "semantic"）记录失败来源
- fix 完成后根据 `fail_source` 决定重跑哪层检查
- 语义审校失败 → fix → 重跑语义审校
- 程序化校验失败 → fix → 重跑程序化校验

### 4. Commit 后清空 feedback/error 字段

- `last_reviewer_feedback`、`error_message`、`fail_source` 在 commit 成功后清空
- 避免下次 `--resume` 时看到已解决的错误信息

### 5. 超时调整

- 提取超时：1800s → 3600s（给 agent 足够 margin）
- 审校超时保持 600s 不变

### 6. 章节上限调整

- 最大批次：20 章 → 15 章
- 默认目标保持 10 章

## 受影响文件

核心代码：
- `automation/persona_extraction/prompt_builder.py` — 新增 `build_world_extraction_prompt()`、`build_character_extraction_prompt()`、`_build_world_read_list()`、`_build_character_read_list()`
- `automation/persona_extraction/orchestrator.py` — 1+N 提取流程、ThreadPoolExecutor 并行、targeted fix 重跑逻辑、commit 清空字段、超时 3600s
- `automation/persona_extraction/progress.py` — 新增 `fail_source` 字段
- `automation/persona_extraction/git_utils.py` — commit message 更新
- `automation/prompt_templates/world_extraction.md` — 新增
- `automation/prompt_templates/character_extraction.md` — 新增
- `automation/prompt_templates/analysis.md` — 批次上限 20→15

文档：
- `docs/requirements.md` — §9.3、§11 流程图、§11.3、§11.5、§11.9 全面更新
- `ai_context/requirements.md`、`ai_context/decisions.md`、`ai_context/current_status.md`
- `docs/architecture/extraction_workflow.md`、`docs/architecture/system_overview.md`
- `automation/README.md`、`works/README.md`
