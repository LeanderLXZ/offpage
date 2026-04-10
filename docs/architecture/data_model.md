# 数据模型

## 顶层目录树

```text
persona-engine/
  ai_context/
  automation/
  docs/
  interfaces/
  prompts/
  schemas/
  simulation/
  sources/
  users/
  works/
```

## 作品作用域规则

每部小说应被视为一个独立的命名空间，以 `work_id` 作为标识。

至少以下层级应以 `work_id` 为作用域：

- 原始语料库
- 规范化作品包
- 作品级分析输出
- 世界观包
- 角色包
- 作品级用户关系数据
- 持久化的用户级运行时产物

## 内容语言规则

`sources/works/{work_id}/manifest.json` 中声明的 `language` 应作为作品级生成材料的默认内容语言。

该默认值应适用于：

- 作品标题和显示名称
- 世界观包的文本内容
- 角色包的文本内容
- 作品级用户/关系文本内容
- 作品级分析摘要，除非特定的 AI 接口层另有说明
- `work_id` 本身（当所选作品为中文时）
- 作品级实体名称和标识符值

结构化字段名可保留英文：

- JSON 键名
- schema 属性名
- 仓库级结构路径约定

但作品级规范数据中的标识符值不必为英文。
对于中文作品，地点、事件、阵营、阶段及其他作品级实体应优先使用原始中文标签，而非仅用拼音作为 id。

同样的规则适用于 `works/{work_id}/` 下生成的作品级路径片段。如果规范标识符为中文，则派生的文件夹或文件名片段默认也应使用中文。

如果 `work_id` 本身为中文，则 `sources/works/` 和 `works/` 下的根目录应使用相同的中文路径片段。

## 原始作品包

每部小说应存放于：

```text
sources/works/{work_id}/
```

推荐内容：

- `manifest.json`
- `raw/`
- `normalized/`
- `chapters/`
- `scenes/`
- `chunks/`
- `metadata/`
- ~~`rag/`~~ — 已移除，运行时检索数据现位于 `works/{work_id}/retrieval/`

### 原始包构建规范

一个合格的原始作品包应通过以下步骤构建：

1. **创建包目录**，路径为 `sources/works/{work_id}/`。
   - 对于中文作品，`{work_id}` 应使用原始中文标题。

2. **将原始源文件放入** `raw/`。
   - 支持的格式：`epub`、`txt`、网页抓取的 HTML 或用户提供的摘录。
   - 保持原始文件不做修改。

3. **在包根目录创建 `manifest.json`**，至少包含：
   - `work_id` — 必须与目录名一致
   - `title` — 源语言的显示标题
   - `language` — ISO 639-1 代码（如 `"zh"`、`"en"`）
   - `source_types` — 源格式标签数组（如 `["epub"]`）
   - `ingestion_status` — 取值为 `"pending"`、`"active"` 或 `"complete"` 之一

4. **将文本标准化**至 `normalized/`。
   - 去除格式伪影、修复编码问题，生成适合章节切分的干净纯文本内容。

5. **按章节拆分**至 `chapters/`。
   - 每章一个文件，命名为 `{chapter_number}.txt`，使用零填充编号（如 `0001.txt`、`0002.txt`）。
   - 每个文件应包含一章的完整文本。

6. **在 `metadata/` 下创建元数据**。
   - `book_metadata.json` — 标题、作者、章节数、来源信息。
   - `chapter_index.json` — 章节有序列表，包含标题和文件路径。

7. **（可选）** 当源文本章节内有明确的场景分隔时，在 `scenes/` 下按场景拆分。

8. **（可选）** 在 `chunks/` 下创建面向检索的分块，供后续 RAG 或 embedding 工作流使用。

9. **（可选）** 检索资产由 Phase 4 产出至 `works/{work_id}/retrieval/`：

   ```
   works/{work_id}/retrieval/
     ├── scene_archive.jsonl       # 按场景切分的原文档案（Phase 4 产出，.gitignore）
     └── fts.sqlite                # 运行时检索数据库（启动时从 JSONL 导入）
                                   #   - scene_archive 表 + FTS5 索引
                                   #   - memory_timeline 表 + FTS5 索引
                                   #   - 可选：summary_embedding BLOB 列
   ```

   场景切分规则：以场景为自然单位（非固定 token），一个场景不跨章节边界。
   `scene_id` 格式：`scene_{chapter}_{seq}`（如 `scene_0015_003`）。
   每个场景条目包含 `scene_id`、`stage_id`、`chapter`、`time_in_story`、
   `location`、`characters_present`、`summary`、`full_text` 八个字段。

   运行时检索使用两级漏斗：jieba 分词 + 专有名词表 + FTS5（默认）→
   embedding 语义检索（LLM tool use 兜底）。单个 SQLite 文件，
   不使用独立向量数据库。

   详见 `docs/requirements.md` §12 和 `simulation/retrieval/index_and_rag.md`。

### 原始包边界

- 原始包应仅包含原始及标准化的源材料。
- 分析、抽取和规范化输出应归入 `works/{work_id}/`，而非 `sources/`。
- 原始包默认应通过 `.gitignore` 排除在 git 之外。如有需要，仅 `manifest.json` 可被纳入版本控制。
- 原始包是输入层，不应被下游抽取或运行时流程修改。

## 规范化作品包

一部作品的持久化、源文本驱动的规范数据应存放于：

```text
works/{work_id}/
```

推荐内容：

- `manifest.json`
- `world/`
- `characters/`
- `analysis/`
- `indexes/`

## 模拟引擎目录

仓库级运行时引擎契约及未来实现应存放于：

```text
simulation/
```

推荐内容：

- `README.md`
- `contracts/`
- `flows/`
- `retrieval/`

重要边界：

- `simulation/` 描述运行时编排逻辑
- `works/{work_id}/` 存储规范化的作品事实
- `users/{user_id}/` 存储可变的用户状态
- 作品级加载和检索提示仍应归入 `works/{work_id}/indexes/`

## 世界观包

每部作品应在以下路径拥有一个规范的世界观包：

```text
works/{work_id}/world/
```

推荐内容：

- `manifest.json`
- `stage_catalog.json`
- `stage_snapshots/{stage_id}.json`
- `foundation/foundation.json` — Phase 2.5 产出的统一基础设定
  （未来可拆分为 setting.json、cosmology.json、power_system.json 等）
- `foundation/fixed_relationships.json` — 世界级固定关系网络
  （Phase 2.5 骨架，后续批次可修正）
- `history/timeline.json`
- `events/{event_id}.json`
- `state/world_state_snapshots/{state_id}.json`
- `locations/{location_id}/identity.json`
- `locations/{location_id}/state_snapshots/{state_id}.json`
- `factions/{faction_id}.json`
- `maps/region_graph.json`
- `maps/map_notes.md`
- `cast/character_index.json`
- `cast/character_summaries.json`
世界观包预期会随着后续文本扩展或修正先前认知而逐步增长和修订。

后续批次提取可修正 `foundation.json` 的内容。当作品需要更细粒度的
世界基础设定时，可拆分为独立文件。

stage 子树是运行时加载所用的作品级时间线锚点。它应描述用户在对话开始时可选择的作品阶段。这些 stage 记录应总结该阶段的当前世界状态，而更早的发展则作为历史事件保留可用。

这些规范修订应仅由源文本证据驱动。用户对话、运行时分支和关系漂移不应改写规范的世界事实或事件记录。

`cast/` 子树是作品级视图，用于索引和检索的便利。详细的角色规范数据仍应存放于 `characters/` 下。

`events/` 子树应聚焦于重大的作品级共享事件，而非属于角色层记忆或分析的细碎场景。

`cast/` 子树应聚焦于主要角色和高频出场的配角。一次性出场的小角色默认不需要提升至世界观包中。

世界观包默认不应为角色对事件的特定理解或误解复制一个独立的 `knowledge/` 层。这类更细粒度的记忆和认知记录应保留在 `characters/` 下。

未解问题默认也不需要专门的 `mysteries/` 子树。除非用户明确要求，这些不确定性应保留在：

- `analysis/` 下的批次报告中
- 修订注记中
- 或不确定性直接相关的 stage / event 文件中

关系信息不设独立的 `world/social/` 目录。世界级固定关系（血缘、宗族、
师徒、势力从属）记录在 `world/foundation/fixed_relationships.json`；
角色侧核心关系弧线记录在 `characters/{char_id}/canon/identity.json`
的 `key_relationships` 中；阶段性关系变化记录在
`world/stage_snapshots/{stage_id}.json` 的 `relationship_shifts` 字段中。

## 运行时加载层级

推荐的启动必需世界观加载项：

- `world/manifest.json`
- 选中的 `world/stage_snapshots/{stage_id}.json`
- `world/foundation/foundation.json` + `fixed_relationships.json`
- `world/world_event_digest.jsonl`（stage 1..N 过滤加载）

如果存在，`works/{work_id}/indexes/load_profiles.json` 应为该作品细化默认的启动数据包。

启动时还应：
- 加载 stage 1..N 中与选定角色相关的 scene_archive summary
- 加载当前阶段前后 N 个（默认 5）与选定角色相关的 scene_archive full_text
- 加载近期 2 个阶段（N + N-1）的 memory_timeline 全量
- 加载 `memory_digest.jsonl`（stage 1..N 过滤加载）
详见 `simulation/retrieval/load_strategy.md` 和 `docs/requirements.md` §12。

推荐的按需世界观加载项：

- `world/events/{event_id}.json`
- `world/history/timeline.json`
- `world/locations/{location_id}/...`
- `world/factions/{faction_id}.json`
- FTS5 / embedding scene_archive 检索（按 `characters_present`、`stage_id`、
  `time_in_story`、`location` 过滤）
- FTS5 / embedding memory_timeline 检索（启动时未加载的低重要度记忆）
- 用于验证的章节原文或分块级证据

## 角色包

每个目标角色应存放于：

```text
works/{work_id}/characters/{character_id}/
```

对于中文作品，`{character_id}` 目录片段应直接使用规范的中文标识符，而非拼音重写。

推荐内容：

- `manifest.json`
- `canon/identity.json` — 含 core_wounds（核心创伤）、key_relationships（核心人物关系弧线）
- `canon/voice_rules.json` — 提取锚点，不在运行时加载
- `canon/behavior_rules.json` — 提取锚点，不在运行时加载；core_drives 已拆分为 core_goals + obsessions
- `canon/boundaries.json` — 提取锚点（hard_boundaries 运行时加载）
- `canon/failure_modes.json`
- `canon/stage_catalog.json`
- `canon/stage_snapshots/{stage_id}.json` — **自包含**，运行时核心
- `canon/memory_timeline/{stage_id}.json`
- `canon/memory_digest.jsonl` — 压缩摘要索引，stage 1..N 过滤加载

对于中文作品，`{stage_id}` 路径片段也应直接使用规范的中文 stage 标识符。

角色包可比世界观包保存更丰富的事件细节，包括记忆权重、情感解读以及与扮演相关的角色视角。

推荐语义：

- 首先从世界观包中选择作品级 `stage_id`
- 角色包将同一 `stage_id` 投射为角色特定的状态
- stage `N` 是对之前各 stage 的累积，但所选 snapshot 应将最新 stage 呈现为当前活跃状态，而非将所有历史扁平化为一个无时间感的总结

## 用户包

用户状态应以用户为根组织：

```text
users/{user_id}/
```

推荐内容：

- `profile.json`
- `conversation_library/manifest.json`
- `conversation_library/archive_refs.json`
- `conversation_library/archive_index.json`
- `conversation_library/archives/{archive_id}/manifest.json`
- `conversation_library/archives/{archive_id}/context_summary.json`
- `conversation_library/archives/{archive_id}/session_index.json`
- `conversation_library/archives/{archive_id}/key_moments.json`
- `role_binding.json`
- `long_term_profile.json`
- `relationship_core/manifest.json`
- `relationship_core/pinned_memories.json`
- `contexts/{context_id}/manifest.json`
- `contexts/{context_id}/character_state.json`
- `contexts/{context_id}/relationship_state.json`
- `contexts/{context_id}/shared_memory.json`
- `contexts/{context_id}/session_index.json`

`role_binding.json` 的首版专用 schema 已存在于：

- `schemas/role_binding.schema.json`

重要边界：

- 规范的基础世界观和角色数据应保留在 `works/{work_id}/` 下
- 用户特定的漂移、关系状态和历史记录应保留在 `users/{user_id}/` 下
- 根目录的 `users/{user_id}/profile.json` 应保持为全局用户档案，而非某一作品-角色分支的情感或关系漂移的堆砌
- 锁定绑定的长期档案变更应写入 `long_term_profile.json`
- 用户包应引用规范的角色包，而非复制它
- 一个 `user_id` 应代表一个锁定的 作品-目标角色-对戏身份 绑定
- `role_binding.json` 应能存储主要目标角色、stage 绑定、当前用户侧角色模式，以及引导设置是否已锁定
- 如果用户侧角色也是规范角色，用户包还应持久化该侧选定的 `character_id`
- 如果用户侧角色有规范数据支撑，默认应继承当前选定的作品 stage，除非存在明确的分支覆盖
- 运行时请求对象和用户级 manifest 应在文件内容中显式携带 `work_id`，而非仅通过目录路径隐含
- session 和 context 状态可在实时角色扮演过程中持续更新
- 只有被保留、提升或合并的内容才应流入 `relationship_core`
- 长期档案和 relationship_core 的更新应仅在关闭时的明确合并确认后，或通过明确的合并操作触发
- 完整对话历史可本地持久化至 `sessions/{session_id}/transcript.json`
- 每个活跃 session 还应保持一个仅追加的 `turn_journal.json` 或等效备份日志用于恢复
- 启动时默认应加载摘要层的用户状态，而非完整的对话历史
- `users/` 下的真实用户包应保持本地存储，默认通过 git 排除
- 合并后的 context 可将完整对话记录提升至账户级 `conversation_library/`

## Session 包

每个分支 context 可拥有多个 session：

```text
users/{user_id}/contexts/{context_id}/sessions/{session_id}/
```

推荐内容：

- `manifest.json`
- `transcript.json`
- `turn_journal.json`
- `turn_summaries.json`
- `memory_updates.json`

推荐加载语义：

- `transcript.json` 可存储该 session 的完整对话历史
- `turn_summaries.json` 应作为启动和按需缩窄的摘要及路由层
- `memory_updates.json` 是详细的回写日志，通常应按需读取而非启动时加载
- `turn_journal.json` 应能在崩溃或响应中断后检测未完成的回合

## 对话归档包

合并后的长期对话记录应优先存放于：

```text
users/{user_id}/conversation_library/archives/{archive_id}/
```

推荐内容：

- `manifest.json`
- `context_summary.json`
- `session_index.json`
- `key_moments.json`
- `sessions/{session_id}/manifest.json`
- `sessions/{session_id}/transcript.json`
- `sessions/{session_id}/turn_summaries.json`
- `sessions/{session_id}/memory_updates.json`

推荐规则：

- 合并后的对话归档应为不可变的账户历史记录
- 源 context 在提升后应保留一个轻量的 `archive_ref` 或等效的溯源标记

## 用户运行时加载层级

推荐的启动必需用户加载项：

- `users/{user_id}/profile.json`
- `role_binding.json`
- `long_term_profile.json`
- `relationship_core/manifest.json`
- `relationship_core/pinned_memories.json`
- `contexts/{context_id}/manifest.json`
- `contexts/{context_id}/character_state.json`
- `contexts/{context_id}/relationship_state.json`
- `contexts/{context_id}/shared_memory.json`
- 最近的 `turn_summaries.json`
- `conversation_library/manifest.json`
- 当前绑定的 `archive_refs.json`

推荐的按需用户加载项：

- `contexts/{context_id}/session_index.json`
- 较早的 context 摘要
- 较早的 session 摘要
- `sessions/{session_id}/transcript.json`
- `sessions/{session_id}/memory_updates.json`
- `conversation_library/archive_index.json`
- `archives/{archive_id}/context_summary.json`
- `archives/{archive_id}/key_moments.json`
- `archives/{archive_id}/sessions/{session_id}/transcript.json`

推荐的生命周期补充：

- session 关闭时应记录由谁或什么触发了关闭
- session 关闭时应记录用户是否接受或拒绝了合并
- 关闭流程应支持退出关键词或等效的明确关闭意图

## 作品分析包

一部作品的持久化模拟相关分析应优先存放于：

```text
works/{work_id}/analysis/
```

推荐内容：

- `progress/` — 流水线进度文件
- `chapter_summaries/` — Phase 0 章节摘要
- `scene_splits/` — Phase 4 中间产物
- `evidence/`
- `conflicts/`

推荐规则：

- 源文本阅读数据包应以批次为作用域
- 批次按自然剧情边界切分（默认目标 `10` 章，最小 `5` 章，最大 `15` 章），可在作品 config 中调整
- 批次 `N` 是该抽取线第 `N` 个 stage 候选的默认来源
- 一个批次数据包可能为以下内容产生更新：
  - `world/`
  - 一个选定的角色包
  - 其他受影响的角色包
- 因此，后续的源文本证据可能会修订同一作品包中已写入的规范文件

## 作品索引包

跨领域的作品级查找视图应优先存放于：

```text
works/{work_id}/indexes/
```

推荐内容：

- `character_index.json`
- `location_index.json`
- `event_index.json`
- `relation_index.json`

## 服务契约输入

首版运行时契约由以下文件建模：

- `schemas/runtime_session_request.schema.json`

该请求模型应支持：

- 在 `work_id` 和 `character_id` 永久锁定之前，引导新的用户级绑定
- 在 context 恢复之前，加载已锁定的现有用户账户
- 选择作品
- 选择角色
- 为主要目标角色选择或列出可用的作品 stage
- 选择用户侧角色或对戏身份
- 对于有规范数据支撑的用户侧角色，默认继承相同的已选作品 stage
- 创建或恢复 context
- 传递用户 persona
- 在 `send_message` 过程中持续维护用户级 session/context 状态
- 通过明确的退出意图关闭 session
- 在 session 关闭后请求并记录合并确认
- 明确地将 context 内容提升或合并至长期用户状态
- 选择终端类型
- 显式携带 `work_id`，以确保请求和持久化的运行时 manifest 在多部作品间保持明确无歧义
