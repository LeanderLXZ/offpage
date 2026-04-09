# 三层记忆系统与 scene_archive 设计

**时间**: 2026-04-07
**类型**: 架构设计（重大修订）

## 概述

从初版的双库 RAG 设计（scene_chunks + memory_index）重新设计为三层记忆系统。
这次修订是经过多轮讨论后的定稿，替代了同日早些时候的初版 RAG 设计
（见 `2026-04-07_011857_rag_retrieval_design.md`）。

## 核心设计决策

### 三层记忆架构

1. **stage_snapshot**（第一层）：角色当前阶段的聚合状态结论，启动只加载
   当前 stage。已有 schema 无需改动。
2. **memory_timeline**（第二层）：角色第一人称主观视角的归纳记忆（不是原文），
   篇幅由事件复杂度决定无硬性限制。新增 `time_in_story`、`location`、
   `scene_refs` 字段。启动加载当前 stage 全量 + 历史 critical/defining，
   其余 RAG 按需。
3. **scene_archive**（第三层）：小说原文按自然场景切分的档案。八字段
   （新增 `time_in_story`、`location`）。作品级资产。启动加载 stage 1..N
   的 summary + 当前阶段附近 N 个 full_text。

### 名称变更

- `scene_chunks` → `scene_archive`（避免与 data_model 中已有的 `chunks/`
  混淆）

### 双库 RAG

scene_archive + memory_timeline 均需向量检索。三层漏斗：metadata 过滤 →
FTS5 lexical → semantic rerank。引擎每轮自动分析语义决定是否检索。

### Phase 4（独立提取阶段）

scene_archive 在 Phase 4 产出（Phase 3 之后），与 Phase 3 分离避免
单次调用任务过重影响质量。各 batch 间无依赖，可并行。

### memory_timeline 保留

讨论中考虑过去除 memory_timeline（被 stage_snapshot + scene_archive 覆盖），
最终决定保留。原因：memory_timeline 提供了"角色怎么走到这一步的"这一中间
粒度层，stage_snapshot 只有聚合结论，scene_archive 太重无法全量加载。

### 对话语境驱动检索

检索不仅在用户显式问"你记得..."时触发，而是引擎每轮自动分析用户输入
语义来决定是否需要检索。

## 修改的文件

### 需求和架构文档
- `docs/requirements.md` — 重写 §12（三层记忆 + RAG），更新 §7.1 和 §9.2
- `docs/architecture/data_model.md` — 更新 rag/ 目录和加载策略
- `docs/architecture/system_overview.md` — 新增 Phase 4
- `docs/architecture/extraction_workflow.md` — 新增 Phase 4 章节，更新流程
- `docs/architecture/schema_reference.md` — 更新 memory_timeline 文档

### 运行时设计
- `simulation/retrieval/index_and_rag.md` — 全面重写为三层 + 双库 RAG
- `simulation/retrieval/load_strategy.md` — 全面重写加载策略
- `simulation/README.md` — 更新 RAG 章节
- `simulation/flows/startup_load.md` — 全面重写启动加载流程

### AI 上下文
- `ai_context/architecture.md` — 全面重写（三层记忆、RAG、Phase 4）
- `ai_context/decisions.md` — 重写 §33-40（替代初版 §33-38）
- `ai_context/requirements.md` — 重写 §7 和 §12 压缩引用
- `ai_context/current_status.md` — 更新 RAG 设计状态
- `ai_context/handoff.md` — 新增 Phase 4
- `ai_context/next_steps.md` — 新增 Phase 4

### Schema
- `schemas/memory_timeline_entry.schema.json` — 新增 `time_in_story`、
  `location`、`scene_refs` 字段

### 自动化
- `automation/README.md` — 新增 Phase 4 说明
