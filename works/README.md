# 作品包

这个目录是按作品划分、由原文支撑的基础设定包的首选存放位置。

推荐结构：

```text
works/{work_id}/
  manifest.json
  world/
  characters/
  analysis/
  indexes/
```

如果作品进入增量抽取阶段，推荐进一步细化为：

```text
works/{work_id}/analysis/incremental/
  extraction_status.md
  source_batch_plan.md
  world_batch_progress.md
  world_batch_*.md
  character_batch_progress/{character_id}.md
```

设计规则：

- `sources/works/{work_id}/` 存放源文本与标准化正文
- `works/{work_id}/` 存放该作品的基础 canon 包
- repo 级运行时 engine 设计与未来实现放在 `simulation/`
- 与作品相关的分析产物统一放在 `works/{work_id}/analysis/`，不再单独维护仓库顶层 `analysis/`
- 用户侧状态应存放在 `users/{user_id}/`
- 对中文作品，`work_id` 本身可以直接使用中文，`works/` 下生成的根目录应与之保持一致
- 对中文作品，`works/{work_id}/` 以下的作品级 canon 默认应保留中文名称和中文标识值，而不是转成拼音
- 对中文作品，`works/{work_id}/` 以下由这些标识派生出来的文件夹名也应保持中文

各子目录的推荐含义：

- `world/`
  - 世界基础设定、历史、大事件、状态、地点、势力、地图
  - 以及作品级角色索引、按阶段存储的关系视图
- `characters/`
  - 详细角色包
- `analysis/`
  - 与该作品相关、且由原文支撑的分析产物与证据
  - 其中 `analysis/incremental/` 适合放：
    - 当前提取总状态
    - source / world / character 的批次规划
    - 自动连续模式的进度文件
    - 每批交接摘要
- `indexes/`
  - 角色、地点、事件、关系等跨目录查询索引
  - 也承接该作品给 simulation engine 用的按需加载与检索提示

重要边界：

- `world/` 可以为了索引和检索方便，包含简短的角色摘要与按阶段存储的关系视图
- `world/` 里的关系文件建议按阶段存储，例如：
  - `world/social/stage_relationships/{stage_id}.json`
- 运行时默认只加载当前所选 `stage_id` 对应的关系文件
- `world/` 应记录作品级共享大事件，而不是那些更适合放进角色包的小场景、小桥段
- `world/` 中的 cast 视图应聚焦主角团和高频配角，不默认收录一次性龙套
- 当前 `world/` 结构不包含单独的：
  - `mysteries/`
  - `knowledge/character_event_awareness/`
- 角色的详细心理、记忆、语气、行为和阶段信息仍应保留在 `characters/` 下
- 用户对话不得改写作品级世界事实或大事件记录
- 用户侧角色漂移、关系变化和对话历史应归入 `users/{user_id}/`

增量抽取建议：

- 如果 `works/{work_id}/analysis/incremental/extraction_status.md` 存在，
  后续 agent 应优先读取它，再决定继续哪个 batch，而不是默认从头开始。
- 每次 world / character / batch planning 有实质进度变化时，应优先更新
  `works/{work_id}/analysis/incremental/` 下最近的一层进度文件。
- 这类 work-local 进度推进默认不需要同步改 `ai_context/` 或
  `docs/logs/`，除非连带改变了仓库级规则或架构。

证据引用建议：

- work-scoped JSON 中如果证据只来自当前作品章节，`evidence_refs`
  默认应使用紧凑章节引用，例如：
  - `0001`
  - `0004`
  - `0011-0013`
- 不要默认把完整章节路径重复写进每个 JSON。
- 只有当证据指向：
  - 作品外文件
  - 非章节文件
  - 或者路径本身具有区分意义
  时，才优先写完整路径。
