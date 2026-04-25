# prompts/ 清理与模块封闭性重构

**日期**: 2026-04-08
**变更范围**: prompts/, simulation/prompt_templates/ (new), automation/, ai_context/, docs/

## 背景

prompts/ 目录是手动提取时代的产物，automation/ 建成后大部分文件已被替代。
此外 automation 代码依赖 prompts/shared/ 文件，simulation 文档引用
prompts/runtime/ 文件，违反了模块封闭性原则。

## 设计决策

1. **automation 和 simulation 各自封闭** — 不依赖外部 prompts/ 目录
2. **prompts/ 仅保留手动场景** — ingest、终审、补抽修复、冷启动
3. **运行时 LLM 行为规则归属 simulation** — 迁入 simulation/prompt_templates/
4. **不需要公共 skills/tools 目录** — 跨模块共享面窄，schemas/ 已是独立目录

## 具体变更

### automation 封闭性修复
- `prompt_builder.py`: 移除对 `prompts/shared/批次执行检查清单.md` 的引用
- `coordinated_extraction.md`: "质量退化防护"段扩充为写前自检 + 退化信号 +
  边界禁令三部分，吸收原检查清单的有用内容

### simulation/prompt_templates/ (新建)
- 从 prompts/runtime/ 迁入 4 个 LLM 行为规则文件：
  - 历史回忆处理规则.md
  - 认知冲突处理规则.md
  - 记忆检索规则.md
  - 会话防稀释检查清单.md（原名"会话稀释保护检查清单"，对齐术语）
- simulation/contracts/runtime_packets.md: 引用更新
- simulation/retrieval/load_strategy.md: 引用更新

### prompts/ 清理（删除 16 个文件）
- analysis/ 全部 7 个（已被 automation/prompt_templates/ 替代）
- shared/ 3 个：批次执行检查清单、批次交接模板、自动批处理进度模板
  （已被 automation 代码化）
- runtime/ 3 个：用户入口与上下文装载、users状态回写、写回前防污染检查清单
  （simulation/flows/ 已覆盖设计，实现时由 simulation 代码构建）

### prompts/ 保留（4 个 + README）
- ingestion/原始资料规范化.md — 手动 ingest
- review/数据包审校.md — 终审
- review/手动补抽与修复.md — **新建**，用于 automation 完成后的局部修复
- shared/最小结构读取入口.md — 新 agent 冷启动

### 文档对齐
- docs/architecture/extraction_workflow.md: 提示词引用从 prompts/analysis/
  更新为 automation/prompt_templates/
- ai_context/architecture.md: prompts/ 描述更新、runtime prompt 引用迁移
- ai_context/conventions.md: Runtime prompts 路径更新
- ai_context/decisions.md: 44-45 条重写（模块封闭性）
- ai_context/handoff.md: 移除已删除的手动提取入口，替换为补抽/终审入口

### 术语统一
- 保留的 prompts/ 文件中"稀释保护机制"改为"防漂移机制"
  （手动场景的单 agent 长会话确实有注意力漂移，但用词不再与 §10 混淆）
