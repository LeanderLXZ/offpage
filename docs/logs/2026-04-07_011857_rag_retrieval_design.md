# RAG 检索系统设计

**时间**: 2026-04-07
**类型**: 架构设计

## 变更内容

设计并文档化了 RAG 检索系统的完整方案。

### 核心设计决策

1. **双库架构**：原文场景库（scene_chunks，作品级）+ 记忆检索库
   （memory_index，角色级），职责分离，不重叠
2. **不设独立对话语料库**：对话保留在场景 `full_text` 中，避免数据重叠和
   逐句标注的高昂提取成本
3. **场景切分规则**：以自然场景为单位，一个场景不跨章节边界，`stage_id`
   由章节号查 batch plan 得出
4. **三层检索漏斗**：metadata 过滤 → FTS5 lexical 召回 → semantic rerank
5. **启动时优先场景池**：当前 stage 全量 + 前一 stage 尾部，首轮检索
   5-8 条代表性场景作为 few-shot 样本
6. **角色过滤**：模拟角色 A 时只加载 A 在场的场景和 A 的记忆
7. **技术选型**：bge-large-zh-v1.5（本地）、chromadb/faiss、sqlite FTS5

### 场景条目结构

六字段：`chunk_id`、`stage_id`、`chapter`、`characters_present`、
`summary`、`full_text`

### 存储布局

- `sources/works/{work_id}/rag/` — 大文件，不提交 git
- `works/{work_id}/indexes/scene_index.jsonl` — 轻量索引，可提交

## 修改的文件

- `docs/requirements.md` — 新增 §12 RAG 检索系统
- `simulation/retrieval/index_and_rag.md` — 全面重写为双库设计
- `simulation/retrieval/load_strategy.md` — 新增 Tier 0 RAG Extension、
  更新 Tier 1 和 Tier 3 的 RAG 集成
- `docs/architecture/data_model.md` — 更新源作品包的 rag/ 目录说明、
  更新按需加载项
- `ai_context/architecture.md` — 新增 RAG Retrieval System 节
- `ai_context/decisions.md` — 新增 §33-38 RAG 相关决策
- `ai_context/current_status.md` — 新增 RAG 设计状态、更新 gaps 列表
- `ai_context/requirements.md` — 新增 §12 压缩引用
