# 两级检索漏斗与角色主动联想

**时间**: 2026-04-07
**类型**: 架构设计（检索策略修订）

## 概述

将前版的"三层漏斗 + 双库 RAG + 独立向量数据库"设计修订为更轻量的
两级检索漏斗。本次修订替代了同日较早的三层记忆与 scene_archive 设计中
关于检索策略的部分（见 `2026-04-07_035804_three_layer_memory_and_scene_archive.md`），
三层记忆架构本身不变。

## 核心设计决策

### 1. 两级检索漏斗

取代原来的"metadata 过滤 → FTS5 lexical → semantic rerank"三层漏斗：

- **第一级（默认，<20ms）**：jieba 分词 + 作品级专有名词表匹配 + FTS5 查询。
  每轮都跑，延迟可忽略。候选摘要直接塞进主 LLM 调用 prompt，
  LLM 自行判断相关性。无命中 = 不检索。
- **第二级（兜底，200-300ms）**：LLM 通过 tool use 调用 `search_memory`
  工具 → 引擎执行 embedding 近似搜索 → 结果传回 LLM 第二次生成回复。
  极少触发。

### 2. 去除独立向量数据库

不再使用 chromadb / faiss。改为单个 SQLite 文件统一存储：
- scene_archive 表 + FTS5 索引
- memory_timeline 表 + FTS5 索引
- 可选的 summary_embedding BLOB 列（第二级兜底用）

### 3. 专有名词表

新增 `works/{work_id}/indexes/vocab_dict.txt`，提取阶段自动产出，
jieba 自定义词典格式。包含人名、地名、功法名、事件关键词。
启动时加载到内存，用于每轮 jieba 分词后的关键词匹配。

### 4. 角色主动联想

引擎每轮不只分析用户输入，还从 context state 提取情境关键词
（当前地点、近期事件、当前情绪、对话对象），一并送入 jieba + FTS5。
LLM 自主决定是否在回复中自然提起某段记忆。不额外调用 LLM。

### 5. Embed summary 而非 full_text

第二级 embedding 检索的对象是 summary 字段，不是 full_text。
原因：full_text 可能超出 embedding 模型输入上限，且信息被稀释，
summary 信息密度更高。

### 6. JSONL → SQLite 导入

JSONL 是提取产出格式（git 友好），SQLite 是运行时检索格式。
启动时从 JSONL 导入构建 FTS5 索引，本地生成不提交 git。

## 修改的文件

### 需求文档
- `docs/requirements.md` — §12.6-12.10 全面重写（两级漏斗、角色主动联想、
  技术选型、存储布局、建设顺序）

### 运行时设计
- `simulation/retrieval/index_and_rag.md` — 全面重写（两级漏斗、角色主动联想、
  完整检索流程图、数据库 Schema、存储布局）
- `simulation/retrieval/load_strategy.md` — Context-Driven Retrieval 章节
  重写为两级漏斗 + 主动联想说明
- `simulation/flows/startup_load.md` — 新增 vocab dict 加载步骤和规则
- `simulation/README.md` — RAG Retrieval 章节重写为 Memory Retrieval

### 架构文档
- `docs/architecture/data_model.md` — rag/ 目录描述更新（去除向量数据库文件，
  改为单个 fts.sqlite），加载引用从 RAG 改为 FTS5/embedding
- `docs/architecture/schema_reference.md` — memory_timeline 加载规则从
  "RAG 按需"改为"FTS5/embedding 按需"

### AI 上下文
- `ai_context/architecture.md` — RAG Retrieval System → Memory Retrieval System，
  Runtime Load Formula 增加 vocab dict
- `ai_context/decisions.md` — §37 重写（两级漏斗），新增 §41（主动联想）、
  §42（专有名词表）
- `ai_context/requirements.md` — §12 重写
- `ai_context/current_status.md` — Memory System and RAG Design → Memory System
  and Retrieval Design，内容全面更新

### Runtime Prompt
- `prompts/runtime/记忆检索规则.md` — 新建，定义 search_memory 工具使用规则、
  主动联想指令、候选记忆使用方式
- `prompts/runtime/历史回忆处理规则.md` — 第一步增加 FTS5 候选记忆引用
