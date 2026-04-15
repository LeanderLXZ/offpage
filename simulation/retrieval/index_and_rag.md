# 索引与运行时检索

## 三层记忆架构

| 层 | 名称 | 定位 | 视角 | 存储级别 |
|----|------|------|------|----------|
| 第一层 | stage_snapshot | 角色当前阶段的聚合状态 | 角色主观（聚合） | 角色级 |
| 第二层 | memory_timeline | 角色从头到现在的经历过程 | 角色第一人称主观（逐事件） | 角色级 |
| 第三层 | scene_archive | 小说原文按场景切分的档案 | 客观原文 | 作品级 |

三者的关系：
- stage_snapshot 是**结论**（"我现在信任他"）
- memory_timeline 是**过程**（"那次他替我挡剑之后我开始动摇"）
- scene_archive 是**原始证据**（完整的原文对话和叙述）

不设独立的对话语料库。

## 数据结构

### scene_archive（原文场景档案）

**条目结构**：

```json
{
  "scene_id": "SC-S{stage:03d}-{seq:02d}",
  "stage_id": "{stage_id}",
  "chapter": "{chapter_identifier}",
  "time": "故事内时间",
  "location": "场景发生地点",
  "characters_present": ["{character_id}", "..."],
  "summary": "客观第三人称事件梗概",
  "full_text": "完整场景原文（无字数限制）"
}
```

切分规则：以自然场景边界切分，一个场景不跨章节边界。`stage_id` 由章节号
查 `stage_plan.json` 得出（stage_plan 是唯一真源；scene_archive
每次合并均按 stage_plan 重建）。`scene_id` 将阶段号编码在前缀中
（`SC-S003-07` 表示阶段 3 的第 7 个场景）。

### memory_timeline（角色主观记忆线）

每条条目是角色第一人称主观视角的归纳（不是原文复制），包含
`memory_id`（`M-S###-##`）、`time`、`location`、`event_description`
（150–200 字客观描述，schema 硬门控）、`digest_summary`（30–50 字独立
撰写的精简摘要，schema 硬门控；是 memory_digest 的 1:1 来源）、
`subjective_experience`（不限长度）、`emotional_impact`、
`memory_importance`、`scene_refs` 等字段。

详见 `schemas/memory_timeline_entry.schema.json`。

### 专有名词表

提取阶段自动产出，每个作品一份。存储在
`works/{work_id}/indexes/vocab_dict.txt`，jieba 自定义词典格式。

包含：

- 人名（含别名、称呼）
- 地名（宗门、城市、秘境等）
- 功法 / 物品 / 阵法名
- 事件关键词（大比、渡劫、结丹等）

运行时启动时加载到内存，用于每轮 jieba 分词后的关键词匹配。

## 两级检索漏斗

### 第一级：jieba + 名词表 + FTS5（默认，<20ms）

每轮对话都执行，延迟可忽略：

1. **jieba 分词**：对用户输入 + 当前情境关键词进行中文分词
2. **名词表匹配**：只保留命中专有名词表的词，其余丢弃
3. **FTS5 查询**：用命中词查询 SQLite FTS5 索引，BM25 排序取 top-K
   条 summary，加 metadata 过滤（`stage_id`、`characters_present`、
   `memory_importance`）

无命中时不检索——直接用已加载的上下文生成回复。

FTS5 返回的候选摘要直接塞进主 LLM 调用的 prompt。**不额外调用 LLM**，
由 LLM 在生成回复时自行判断哪条有用。

### 第二级：Embedding 语义检索（兜底，200-300ms）

使用 LLM tool use 机制，仅在第一级不足时触发：

- 引擎为 LLM 定义 `search_memory` 工具
- LLM 判断候选不足时主动调用，传入语义化 query
- 引擎执行 embedding 近似搜索（对 summary 的向量）
- 结果传回 LLM，第二次生成回复

Embedding 对象是 **summary 字段**，不是 full_text：
- full_text 可能几千字，超出 embedding 模型输入上限
- summary 信息密度高，向量表征更精准
- 命中 summary 后，需要原文时再拉 full_text

绝大多数轮次在第一级结束（一次 LLM 调用）。第二级极少触发。

### 角色过滤

模拟角色 A 时：

- 加载 / 检索：`characters_present` 包含角色 A 的场景
- 加载 / 检索：角色 A 的 memory_timeline
- 不加载：其他角色的 memory_timeline 和角色 A 不在场的场景

## 角色主动联想

角色不是被动回答问题的助手。引擎每轮不只分析用户输入，还从当前
context state 提取情境关键词，扩大 FTS5 候选范围：

```python
# 引擎每轮的关键词提取（伪代码）
keywords = jieba_extract(user_input, vocab_dict)
keywords += jieba_extract(context.current_location, vocab_dict)
keywords += jieba_extract(context.recent_events, vocab_dict)
keywords = list(set(keywords))
```

情境关键词来源：
- 当前对话场景地点
- 近期发生的事件
- 角色当前情绪状态
- 对话对象

LLM 看到稍宽的候选池后，自主决定是否在回复中自然提起某段记忆。
不额外调用 LLM，不增加延迟。

示例：

```
当前地点 = "天剑宗·演武场"
jieba 匹配 "演武场" → FTS5 命中记忆：
  "小时候第一次在演武场被师兄打哭"
角色在回复中自然带出：
  "说到演武场……我小时候第一次来这里，被师兄打得鼻青脸肿。"
```

## 完整检索流程

```
用户输入 + 当前情境
    │
    ▼
jieba 分词 + 名词表匹配（<10ms）
    │
    ├─ 命中 → FTS5 查询 top-K summary（<10ms）
    │         │
    │         ▼
    │     候选摘要塞入主 LLM 调用 prompt
    │     LLM 自行判断：
    │       ├─ 候选够用 → 直接生成回复（一次调用）
    │       └─ 候选不足 → 调用 search_memory 工具
    │                      → embedding 检索 → 结果传回
    │                      → 生成回复（两次调用）
    │
    └─ 未命中 → 不额外检索，直接生成回复
               （stage_snapshot + 近期记忆 + memory_digest 仍在上下文中）
```

## 运行时加载集成

### 启动加载

**memory_timeline**：
- 近期 2 个阶段（N + N-1）全量加载
- `memory_digest.jsonl` stage 1..N 过滤加载（压缩索引，~60-80 tokens/条）
- 其余条目通过 FTS5 按需检索

**scene_archive**：
- 最近 `scene_fulltext_window` 条 full_text（默认 10，可通过
  `load_profiles.json` 覆盖）
- **摘要不在启动期加载**——仅存在于 FTS5 索引，按需检索命中

**专有名词表**：
- 启动时加载 `works/{work_id}/indexes/vocab_dict.txt` 到内存

### 对话中按需（Tier 1 集成）

大多数轮次不触发深度检索。FTS5 每轮都跑（<20ms），但仅在有命中时
才将候选注入 prompt。embedding 检索极少触发。

scene_archive 的 `full_text` 也可作为 Tier 3 原文验证来源。

## 技术选型

- **中文分词**：`jieba`（加载作品级自定义词典）
- **全文检索**：`sqlite FTS5`（BM25 排序，**默认主力方案**）
- **Embedding**（可选兜底）：`bge-large-zh-v1.5`（本地，~1.3GB 显存）
- **数据库**：单个 SQLite 文件，FTS5 索引 + 可选 embedding BLOB 列
- **不使用**独立向量数据库（chromadb、faiss 等）

## 数据库 Schema

```sql
-- 场景档案表
CREATE TABLE scene_archive (
    scene_id TEXT PRIMARY KEY,  -- SC-S{stage:03d}-{seq:02d}
    stage_id TEXT NOT NULL,
    chapter TEXT,
    time TEXT,                  -- 故事内时间
    location TEXT,
    characters_present TEXT,  -- JSON array
    summary TEXT NOT NULL,
    full_text TEXT NOT NULL,
    summary_embedding BLOB   -- 可选，embedding 向量
);

-- 场景 FTS5 索引
CREATE VIRTUAL TABLE scene_fts USING fts5(
    summary, full_text,
    content='scene_archive',
    content_rowid='rowid'
);

-- 记忆时间线表（检索副本）
CREATE TABLE memory_timeline (
    memory_id TEXT PRIMARY KEY,  -- M-S{stage:03d}-{seq:02d}
    character_id TEXT NOT NULL,
    stage_id TEXT NOT NULL,      -- redundant with memory_id prefix; kept for SQL filtering
    time TEXT,                   -- 故事内时间
    location TEXT,
    event_description TEXT,      -- 150–200 chars 客观描述
    digest_summary TEXT,         -- 30–50 chars 精简摘要（memory_digest 的来源）
    subjective_experience TEXT,
    memory_importance TEXT,      -- 5 levels: trivial/minor/significant/critical/defining
    scene_refs TEXT,           -- JSON array
    summary_embedding BLOB    -- 可选，embedding 向量
);

-- 记忆 FTS5 索引
CREATE VIRTUAL TABLE memory_fts USING fts5(
    event_description, digest_summary, subjective_experience,
    content='memory_timeline',
    content_rowid='rowid'
);
```

## 存储布局

```
works/{work_id}/
  ├── retrieval/
  │   ├── scene_archive.jsonl     # 原文场景档案（Phase 4 产出，.gitignore）
  │   └── fts.sqlite              # 运行时检索数据库（启动时构建）
  ├── characters/{character_id}/canon/
  │   └── memory_timeline/        # 角色主观记忆（JSON 数组，提交 git）
  └── indexes/
      ├── scene_index.jsonl       # 轻量场景索引（可提交 git）
      └── vocab_dict.txt          # 专有名词表（可提交 git）
```

JSONL 是提取产出格式（git 友好）。SQLite 是运行时检索格式，
启动时从 JSONL 导入构建，本地生成不提交 git。

## 权威来源

完整需求见 `docs/requirements.md` §12。
