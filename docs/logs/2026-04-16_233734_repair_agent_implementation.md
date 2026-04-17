# Repair Agent 实现：统一检测+修复系统替代旧审校通道架构

**日期**：2026-04-16
**范围**：Phase 3 提取流水线 — 完全重构 validation/fix 系统

## 背景

旧架构（并行审校通道 + 提交门控 + 修复瀑布 + lane 独立重试）过于复杂，且频繁
触发整 lane 回滚+重提取（每次 20+ 分钟）。核心问题：修复粒度太粗（整文件/整 lane），
无法对单个字段做精确修补。

## 变更内容

### 1. 新增 `automation/repair_agent/` 模块

独立的统一检测+修复系统，所有 phase 通过同一接口调用。

**四层检查器**（L0–L3，分层依赖，低层有 error 则跳过高层）：
- L0 `json_syntax` — 文件存在、UTF-8、JSON/JSONL 解析、非空
- L1 `schema` — jsonschema 校验（硬依赖）
- L2 `structural` — 业务规则（ID 格式、样本数阈值、长度门控、对齐检查）
- L3 `semantic` — LLM 语义审查（事实准确性、逻辑一致性、跨阶段连续性）

**四层修复器**（T0–T3，逐层升级，与检查器正交）：
- T0 `programmatic` — 0 token（正则修 JSON、类型转换、ID 格式、缺失字段）
- T1 `local_patch` — 字段级 LLM 修复（不读原文）
- T2 `source_patch` — 字段级 LLM 修复（通过 context_retriever 加载原文章节）
- T3 `file_regen` — 全文件 LLM 重生成（最后手段）

**三阶段运行**：
- Phase A：全量检查（L0–L3）
- Phase B：修复循环（按 `START_TIER[category]` 分组，T0→T1→T2→T3 逐层升级，每 tier 独立重试次数）
- Phase C：最终语义验证（仅 Phase A 有语义问题时触发）

**核心组件**：
- `protocol.py` — Issue, FileEntry, RepairConfig, RepairResult 等数据类
- `tracker.py` — fingerprint-based 跨轮次追踪 + 安全阀（回归/收敛检测）
- `field_patch.py` — json_path 字段级精确替换（保持 key 顺序）
- `context_retriever.py` — 两步定位：chapter_summaries 索引 → 加载原文章节
- `coordinator.py` — 三阶段编排入口（`run()`, `validate_only()`）

文件清单：
- `automation/repair_agent/__init__.py`
- `automation/repair_agent/protocol.py`
- `automation/repair_agent/coordinator.py`
- `automation/repair_agent/tracker.py`
- `automation/repair_agent/field_patch.py`
- `automation/repair_agent/context_retriever.py`
- `automation/repair_agent/checkers/__init__.py`
- `automation/repair_agent/checkers/json_syntax.py`
- `automation/repair_agent/checkers/schema.py`
- `automation/repair_agent/checkers/structural.py`
- `automation/repair_agent/checkers/semantic.py`
- `automation/repair_agent/fixers/__init__.py`
- `automation/repair_agent/fixers/programmatic.py`
- `automation/repair_agent/fixers/local_patch.py`
- `automation/repair_agent/fixers/source_patch.py`
- `automation/repair_agent/fixers/file_regen.py`

### 2. 修改 `automation/persona_extraction/orchestrator.py`

- 移除 `review_lanes`、`validate_lane`、`build_reviewer_prompt`、`build_targeted_fix_prompt` 的导入
- 移除 `_parse_verdict()`、`_is_fixable()` 函数（不再需要）
- 将 Step 4（原 ~360 行的审校通道+提交门控+lane 重试）替换为 ~70 行的 `repair_agent.run()` 调用
- 新增 `_collect_stage_files()` 方法，构建 RepairFileEntry 列表
- 步骤从 6 步减为 5 步（去掉独立的提交门控步骤）
- 保留 `try_repair_json_file`（Phase 0）和 `validate_baseline`（Phase 2.5）导入

### 3. 文档更新

- `docs/requirements.md` — §11.4 完全重写为 Repair Agent 架构
- `automation/README.md` — 架构图、目录结构、修复系统章节
- `docs/architecture/extraction_workflow.md` — Phase 3 流程图和设计决策
- `ai_context/architecture.md` — Phase 3 section
- `ai_context/requirements.md` — lane-attributed retry → repair agent
- `ai_context/current_status.md` — 同上
- `docs/architecture/schema_reference.md` — lane_retries 标注为遗留字段

## 保留的遗留文件

以下文件不再被导入使用，但保留在磁盘上（可后续清理）：
- `automation/persona_extraction/review_lanes.py` — 不再被任何文件导入
- `automation/persona_extraction/prompt_builder.py` 中的 `build_reviewer_prompt()`、`build_targeted_fix_prompt()`
- `automation/prompt_templates/semantic_review_*.md`、`targeted_fix.md`

## 测试

- 全部 16 个模块文件语法检查通过
- 全部模块 Python import 成功
- 基础功能测试通过：
  - 有效 JSON 文件 → 0 issues, pass
  - 尾部逗号 JSON → T0 自动修复 → pass
  - schema 缺失必填字段 → 正确报告 error
  - Issue fingerprint 生成正确
  - IssueTracker diff 正确区分 resolved/introduced/persisting
  - field_patch 正确替换嵌套路径值
  - ID 格式修复（M-S3-2 → M-S003-02）
  - 类型转换（string "42" → number 42）

## 设计决策记录

1. **检查器与修复器正交**：不是 L1→T1 的映射关系，而是任何层的 issue 都可能需要任何 tier 的修复
2. **修复从最低可用 tier 开始升级**：不预分配 fixability，而是逐层尝试
3. **语义 LLM 最多 2 次**：Phase A 初检 + Phase C 终验，修复循环内只用 0-token 的 L0–L2 复检
4. **字段级精确修补**：通过 json_path 定位单个字段替换，不整文件回滚
5. **context_retriever 使用原文**：chapter_summaries 太概括，evidence/ 不存在，只有原文可靠
