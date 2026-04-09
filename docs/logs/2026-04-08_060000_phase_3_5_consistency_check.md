# Phase 3.5 跨批次一致性检查

**日期**: 2026-04-08
**变更范围**: 需求文档、架构文档、automation 代码、ai_context

## 变更内容

### 新增 Phase 3.5（跨批次一致性检查）

在 Phase 3（协同批次提取）全部 batch 提交后、Phase 4（场景切分）之前，
新增跨批次一致性检查阶段。

**8 项程序化检查**（零 token 开销）：
1. alias 一致性
2. 快照字段完整性（13 个必填维度）
3. 关系连续性（相邻 batch 间变化需有归因）
4. source_type 分布（标记全 canon batch）
5. evidence_refs 覆盖率
6. memory_digest 对应（与 memory_timeline 一一匹配）
7. target_map 样本数（每 target ≥ 3 examples）
8. stage_id 对齐（世界/角色 catalog 与 snapshot 目录）

可选 LLM 裁定仅在有标记项时触发。

### 更新的文件

- `docs/requirements.md` — 流程图、流程说明、新增 §11.10
- `docs/architecture/extraction_workflow.md` — 流程总览、新增 §7、编排架构图
- `docs/architecture/system_overview.md` — 新增阶段 3.5
- `automation/README.md` — 新增 Phase 3.5 段落、目录结构
- `automation/persona_extraction/consistency_checker.py` — 新文件，~490 行
- `automation/persona_extraction/orchestrator.py` — 导入、集成调用
- `ai_context/requirements.md` — §11 更新
- `ai_context/architecture.md` — pipeline phases 更新
- `ai_context/decisions.md` — 新增 decision 35，修复编号
- `ai_context/next_steps.md` — Phase 流程更新

### 设计决策

- 主要为程序化检查，零 token 开销
- error 级别阻断 Phase 4，warning 仅提示
- 在 orchestrator 的 all_committed() 后、squash_merge 前自动运行
