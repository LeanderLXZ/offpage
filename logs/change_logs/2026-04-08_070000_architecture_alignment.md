# 架构文档全面对齐

**日期**: 2026-04-08
**变更范围**: 架构文档、ai_context、schema_reference

## 背景

Phase 3.5 新增后，对全部架构文档做系统性对齐检查，发现 13 处过时/缺失/不一致。

## 修复内容

### extraction_workflow.md
- §2-5 重写：旧的手动步骤（全书总体分析/源文件分批规划/候选角色识别）
  对齐为 Phase 0（章节归纳）+ Phase 1（全书分析四子步骤）
- 新增 §5 Baseline 产出（Phase 2.5）独立小节
- 候选角色输出路径从 `candidate_characters_initial.md` 修正为
  `candidate_characters.json`

### system_overview.md
- "自动化提取流程（五阶段）"移除错误的"五"标签（实际 7 个编号 0-6）
- 运行时加载公式重写：明确 baseline 不加载，补充三层记忆系统加载策略
  （memory_timeline 近期 2 阶段 + memory_digest 全量 + scene_archive 摘要
  + vocab_dict）

### data_model.md
- 顶层目录树补 `automation/`
- 角色包推荐内容：移除从未产出的 `canon/bible.md` 和 `canon/relationships.json`，
  补充 `canon/memory_digest.jsonl`，标注各文件运行时加载状态
- 世界包 `foundation/` 路径：从三个独立文件改为实际产出的统一
  `foundation/foundation.json`

### schema_reference.md
- 补充 `memory_digest_entry.schema.json` 完整文档（8 个字段说明）

### ai_context/
- current_status.md：补 Phase 3.5 + resume auto-reset 说明；
  scene_archive "after Phase 3" → "after Phase 3.5"
- next_steps.md：batch 数 36 → 40
- handoff.md：补 Phase 3.5 自动运行和 resume auto-reset 说明

## 同会话其他提交

- `325490e` — Phase 3.5 跨批次一致性检查（文档 + 代码 + 编排集成）
- `e055b52` — 修复 Phase 3.5 调用参数不匹配 + stage_delta 首阶段豁免
- `6a7854d` — resume 自动重置 blocked batch + §11.2 automation 控制流总图
