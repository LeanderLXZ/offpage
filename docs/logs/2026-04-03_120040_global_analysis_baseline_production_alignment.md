# 2026-04-03 全书分析扩展、Baseline 产出阶段、全仓库对齐

## 变更概要

### 一、全书分析阶段扩展

**动机**：之前的全书分析只产出 batch plan + 候选角色。缺少世界观分析，
也没有利用全书视野产出 baseline。

**需求文档更新**（`docs/requirements.md` §9.2）：
- 重写端到端提取流程为七步：入库 → 章节归纳 → 全书分析 → 用户确认 →
  baseline 产出 → 协同批次提取 → 补充提取 → 包验证
- 全书分析阶段新增四个子步骤：身份合并 → 世界观概览 → 批次规划 → 角色识别
- 新增"世界观概览的内容要求"小节
- 新增"全书分析阶段的 Baseline 产出"小节
- 分析阶段候选角色要求加入别名、身份合并后统一

**新增需求**（`docs/requirements.md` §3 "分析阶段的身份合并"）：
- chunk 独立归纳时记录身份线索
- 全书分析阶段必须执行跨 chunk 身份合并
- 候选角色列表中同一角色不同名称必须合并为一个条目

### 二、新增 Phase 2.5 — Baseline 产出

**动机**：全书分析阶段拥有全书视野 + 身份合并结果，是产出非阶段性 baseline
信息的最佳时机。比 batch 1 只看前 10 章原文要准确得多。

**新增 prompt**：`automation/prompt_templates/baseline_production.md`
- 产出世界 foundation (`world/foundation/foundation.json`)
- 产出角色 identity.json + manifest.json（含完整结构化别名）
- 产出空的 stage_catalog.json 初始化

**代码变更**：
- `prompt_builder.py` — 新增 `build_baseline_prompt()`
- `orchestrator.py` — 新增 `run_baseline_production()` 方法，`run_full()` 中
  在 confirm 之后、extraction loop 之前调用

### 三、提取 Prompt 更新

- `coordinated_extraction.md` 规则 3 改为"Baseline 修正"：
  - identity.json 和 world foundation 已在 Phase 2.5 产出
  - 首批创建 voice_rules/behavior_rules/boundaries/failure_modes
  - 任何批次可修正任何已有 baseline（identity, voice, behavior, boundaries,
    failure_modes, world foundation）
- `analysis.md` 新增步骤 1.8（世界观概览）+ world_overview.json 产出
- `summarization.md` 新增 identity_notes 字段

### 四、全仓库文档对齐

以下文件已更新以反映新的五阶段 pipeline 和 baseline 产出时机：

- `ai_context/architecture.md` — 重写"Automated Extraction Pipeline"为五阶段
- `ai_context/decisions.md` — Decision 13 和 23 更新
- `ai_context/handoff.md` — pipeline 描述更新为五阶段
- `ai_context/next_steps.md` — 重写最高优先级任务描述
- `ai_context/requirements.md` — §9 重写为七步流程 + baseline 产出
- `docs/architecture/system_overview.md` — 分析层提取顺序改为五阶段
- `docs/architecture/data_model.md` — 世界观包注释加入 Phase 2.5 说明
- `docs/architecture/schema_reference.md` — identity aliases + active_aliases
- `simulation/contracts/baseline_merge.md` — extraction workflow 加入 Phase 2.5

## 涉及文件

新建：
- `automation/prompt_templates/baseline_production.md`
- `docs/logs/2026-04-03_120040_global_analysis_baseline_production_alignment.md`

修改：
- `docs/requirements.md`
- `ai_context/requirements.md`
- `ai_context/architecture.md`
- `ai_context/decisions.md`
- `ai_context/handoff.md`
- `ai_context/next_steps.md`
- `automation/prompt_templates/analysis.md`
- `automation/prompt_templates/summarization.md`
- `automation/prompt_templates/coordinated_extraction.md`
- `automation/persona_extraction/prompt_builder.py`
- `automation/persona_extraction/orchestrator.py`
- `docs/architecture/system_overview.md`
- `docs/architecture/data_model.md`
- `docs/architecture/schema_reference.md`
- `simulation/contracts/baseline_merge.md`
