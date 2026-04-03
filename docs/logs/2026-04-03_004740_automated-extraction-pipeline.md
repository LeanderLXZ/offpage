# 自动化提取编排器

时间：2026-04-03
范围：新增 `automation/` 目录；更新需求、架构、ai_context

## 变更内容

### 新增：`automation/` — 自动化提取编排器

Python 包 `persona_extraction`，通过 CLI 调用（`claude -p` 或 `codex`）
驱动多批次的世界+角色协同提取。

核心模块：
- `cli.py` — CLI 入口 (`persona-extract` 命令)
- `orchestrator.py` — 主循环（分析 → 用户确认 → 提取循环）
- `llm_backend.py` — LLM 后端抽象（Claude CLI + Codex CLI）
- `progress.py` — 进度追踪和状态机
- `validator.py` — 程序化校验（JSON schema + 结构完整性，不花 token）
- `prompt_builder.py` — 上下文感知的 prompt 组装
- `git_utils.py` — Git 安全操作（preflight、commit、rollback）

Prompt 模板：
- `prompt_templates/analysis.md` — 分析阶段
- `prompt_templates/coordinated_extraction.md` — 协同提取
- `prompt_templates/semantic_review.md` — 语义审校

### 新增：`docs/architecture/schema_reference.md`

所有 JSON Schema 的功能说明、用途、位置、运行时加载规则的完整索引。
包含 Baseline vs Runtime 加载规则对照表。

### 更新：`docs/requirements.md`

新增 §十一（自动化提取编排），覆盖：
- 总体架构
- Pipeline 流程
- Agent 上下文模型
- 两层质量检查
- 失败处理
- Git 集成
- LLM 后端抽象
- Batch boundary 规则

### 更新：`docs/architecture/extraction_workflow.md`

新增"自动化编排"section，描述编排架构和关键设计决策。
进度追踪文件从 `.md` 改为 `.json` 格式。

### 更新：`ai_context/`

- `current_status.md` — 新增自动化编排器和 schema 文档的状态
- `architecture.md` — 新增 automation/ 目录和自动化 pipeline 描述
- `next_steps.md` — 最高优先级改为测试自动化 pipeline
- `handoff.md` — 新增 schema 文档和 automation 的导航指引
- `decisions.md` — 新增自动化提取的 5 条关键决策（#23-#27）
- `requirements.md` — 新增 §11 压缩引用

## 设计决策

1. 每个 batch 是独立的 `claude -p` 调用，批次间无共享内存
   - 优势：无稀释风险
   - 代价：编排脚本必须完整组装 prompt
2. 两层质量检查：程序化（免费）+ 语义（LLM）
3. Git commit 作为天然回滚点，提取在独立分支进行
4. 支持 Claude CLI 和 Codex CLI 两种后端
5. Batch boundary 应遵循自然剧情边界（min 5, max 20, default 10 章）

## 未完成

- 尚未端到端测试
- Prompt 模板可能需要根据实际输出质量调优
- Codex CLI 的具体 flag 可能需要更新
