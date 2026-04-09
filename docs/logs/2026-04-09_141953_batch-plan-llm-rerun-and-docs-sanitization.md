# Batch Plan LLM 重跑修正 + 文档脱敏

日期：2026-04-09

## 变更内容

### 1. Batch plan 超限处理：从程序化拆分改为 LLM 重跑修正

**动机**：Phase 1 batch plan 出口验证发现超过 15 章的 batch 时，原方案
采用程序化自动均分拆分。用户认为这是一次性操作，精准性优先于效率，
要求改为重新调用 LLM 生成更精准的 batch plan。

**实现**：
- `orchestrator.py`：删除 `_validate_and_split_batch_plan()` 和
  `_generate_split_suffixes()`，替换为纯检查函数 `_check_batch_plan_limits()`
- `orchestrator.py`：`run_analysis()` 新增重试循环（`MAX_ANALYSIS_RETRIES = 2`），
  超限时删除 plan 文件，构建修正反馈，重新调用 LLM
- `prompt_builder.py`：`build_analysis_prompt()` 新增 `correction_feedback` 参数，
  非空时追加 `## ⚠️ 修正要求` 段落到 prompt 末尾
- `analysis.md`：强化 batch 约束提示（⚠️ 硬性约束 + 自检要求）

### 2. 文档脱敏：移除所有具体作品/角色/剧情引用

**动机**：用户要求 docs、需求文档、readme、prompt 模板中不出现当前测试
作品的书名、角色名、章节名、剧情细节。即使是示例也应使用通用占位符。

**涉及文件**：
- `docs/requirements.md` — 多处示例通用化
- `ai_context/` 下 6 个文件 — 移除具体 work_id、角色名、批次信息
- `automation/README.md` — work_id 占位符化
- `automation/prompt_templates/analysis.md` — 示例通用化
- `automation/prompt_templates/summarization.md` — 示例通用化
- `automation/prompt_templates/coordinated_extraction.md` — 示例通用化
- `simulation/contracts/runtime_packets.md` — 示例通用化
- `simulation/prompt_templates/历史回忆处理规则.md` — 对话示例通用化
- `prompts/runtime/历史回忆处理规则.md` — 对话示例通用化
- `prompts/analysis/全流程提取编排.md` — 示例通用化
- `automation/persona_extraction/consistency_checker.py` — 注释通用化
- `automation/persona_extraction/validator.py` — 注释通用化
- `docs/architecture/extraction_workflow.md` — 描述更新

**豁免**：`docs/logs/` 下的历史日志保持原样，不做脱敏。

## 验证

- 全库 grep 确认仅 `docs/logs/` 中残留具体引用
- `python -c "from automation.persona_extraction import ..."` 全模块导入通过
