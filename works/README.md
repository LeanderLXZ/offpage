# 作品包

这个目录是按作品划分、由原文支撑的基础设定包的首选存放位置。

## 推荐目录结构

```text
works/{work_id}/
  manifest.json
  README.md

  world/
    manifest.json
    stage_catalog.json
    world_event_digest.jsonl
    stage_snapshots/{stage_id}.json
    foundation/
      foundation.json
      fixed_relationships.json
      setting.json
      cosmology.json
      power_system.json
    history/
      timeline.json
    events/
      {event_id}.json
    state/
      world_state_snapshots/{state_id}.json
    locations/
      {location_id}/
        identity.json
        state_snapshots/{state_id}.json
    factions/
      {faction_id}.json
    maps/
      region_graph.json
      map_notes.md
    cast/
      character_index.json
      character_summaries.json
  characters/
    {character_id}/
      manifest.json
      canon/
        identity.json
        memory_timeline/{stage_id}.json
        voice_rules.json
        behavior_rules.json
        boundaries.json
        failure_modes.json
        stage_catalog.json
        stage_snapshots/{stage_id}.json

  analysis/
    world_overview.json
    stage_plan.json
    candidate_characters.json
    consistency_report.json
    progress/
      pipeline.json
      phase0_summaries.json
      phase3_stages.json
      phase4_scenes.json
      extraction.log
    chapter_summaries/
    scene_splits/
    evidence/
    conflicts/

  indexes/
    load_profiles.json
    character_index.json
    location_index.json
    event_index.json
    relation_index.json
```

## 各子目录说明

### world/

世界基础设定包，包含：

- `stage_catalog.json` — 剧情阶段目录，每个阶段包含一句话总结
  （`summary`）供用户选择（仅 bootstrap 阶段选择，运行时不加载）
- `world_event_digest.jsonl` — 世界事件压缩摘要时间线（程序化维护）
- `stage_snapshots/` — 每个阶段的世界状态快照，内容涵盖：
  - 对基础设定的修正与补充
  - 仅本阶段发生的事件 `stage_events`（每条 50–80 字，schema 硬门控；
    仅收录世界公共层事件，角色私事/内心决定应写入该角色 memory_timeline。
    作为 `world_event_digest.jsonl` 的直接来源，1:1 复制；跨阶段时间线由
    digest 聚合，不在快照里累积）
  - 当前世界状态
  - 人物关系转变
  - 人物状态变化（生死、恋爱、等级等随时间变化的状态）
  - 地理与地图变化
  - 悬而未决的谜题
- `foundation/` — 稳定的世界规则（设定、宇宙观、力量体系）及固定关系网络
- `history/` — 历史时间线
- `events/` — 作品级共享大事件（不含角色侧小场景）
- `state/` — 动态世界状态快照
- `locations/` — 地点身份与状态
- `factions/` — 势力与机构
- `maps/` — 地图结构与地理推测
- `cast/` — 作品级角色索引与简要摘要（聚焦主角团和高频配角）
关系信息不设独立目录：世界级固定关系记录在
`world/foundation/fixed_relationships.json`；角色侧核心关系弧线记录在
`characters/{char_id}/canon/identity.json` 的 `key_relationships` 中；
阶段性关系变化记录在 `world/stage_snapshots/` 的 `relationship_shifts` 字段中。

### characters/

详细角色包，每个角色一个子目录，包含：

- `identity.json` — 基础身份信息（不随阶段变化的底层属性：姓名、别名、
  性别、种族、出身、外貌、初始社会地位）；此外还承载 `core_wounds`
  （根源性心理创伤）与 `key_relationships`（跨作品关系弧）。schema:
  `schemas/identity.schema.json`
- `memory_timeline/{stage_id}.json` — 角色视角的记忆时间线，按阶段拆分（JSON
  数组，每个元素为一条记忆）。加载阶段 N 时只需读取阶段 1..N 的文件。内容涵盖：
  - 客观事件与角色的主观体验（可能与事实不同）
  - 情感影响与获得的新认知
  - 角色在该事件中产生的误解（如有）
  - 角色因该事件而隐瞒的信息（如有）
  - 该事件对角色关系的影响
  - 记忆重要程度（trivial → defining）
  - schema: `schemas/memory_timeline_entry.schema.json`
- `voice_rules.json` — 语言风格规则（基线），内容涵盖：
  - 基础语气、语言习惯、用词偏好、标志性口头禅
  - 代表性台词示例（含出处和语境）
  - 按情绪状态分类的语言变化（暧昧、愤怒、委屈、嘴硬、关心、吃醋等）
  - 按对象类型分类的说话差异（亲近者、陌生人、敌对者等）
  - 语言禁忌
  - schema: `schemas/voice_rules.schema.json`
- `behavior_rules.json` — 行为规则（基线），内容涵盖：
  - 核心行为驱动力与决策风格
  - 情绪触发点（什么事情引发强烈反应及反应模式）
  - 按情绪状态分类的完整反应模式（内心感受、外在表现、典型动作、恢复方式）
  - 按关系类型分类的行为差异（默认态度、底线、升级/恶化模式）
  - 习惯性行为与压力反应（应对方式、崩溃临界点、危机后行为）
  - schema: `schemas/behavior_rules.schema.json`
- `boundaries.json` — 人设边界，内容涵盖：
  - 硬边界：任何情况下都不会做的事（含原因）
  - 软边界：强烈抗拒但极端条件下可能打破的事（含例外条件）
  - 常见误解：人们容易搞错的关于角色的认知
  - schema: `schemas/boundaries.schema.json`
- `failure_modes.json` — 崩坏预警（给 AI 运行时的防护指南），内容涵盖：
  - 常见扮演错误（错误描述、产生原因、正确行为）
  - 语气陷阱
  - 关系互动陷阱
  - 知识泄漏风险（角色不该知道但 AI 容易泄漏的信息）
  - schema: `schemas/failure_modes.schema.json`
- `stage_catalog.json` — 角色阶段目录，每个阶段包含一句话总结
  （`summary`）供用户选择（仅 bootstrap 阶段选择，运行时不加载）
- `stage_snapshots/` — 角色在每个阶段的投影快照，内容涵盖：
  - 仅本阶段发生的事件 `stage_events`（每条 50–80 字，schema 硬门控；
    非累积历史；跨阶段历史由 `memory_timeline` + `memory_digest.jsonl` +
    `world_event_digest.jsonl` 共同承载）
  - 当前状态（生死、恋爱、等级等随时间变化的状态）
  - 当前性格与性格转变
  - 当前心情与情感基线（驱动力、欲望、恐惧、心理创伤）
  - 当前口吻与口癖变化（相对基线的 override）
  - 当前行为模式变化（压力下、面对陌生人、面对亲密者、冲突风格）
  - 知识边界（知道/不知道/不确定）
  - 误解：角色主观认为对但客观错误的认知（含真相和原因）
  - 隐瞒：角色知道但故意不说的信息（含对象和原因）
  - 阶段间变化 delta：从上一阶段到当前阶段的关键变化摘要
    （触发事件、性格变化、关系变化、状态变化、情绪基调转变、口吻转变）
  - 对其他角色的关系状态与信任度
  - schema: `schemas/stage_snapshot.schema.json`

### analysis/

与该作品相关的分析产物与证据：

- `progress/` — 流水线进度文件（pipeline.json, phase0/3/4 进度, extraction.log）
- `chapter_summaries/` — Phase 0 章节摘要（每 chunk 一个 JSON）
- `scene_splits/` — Phase 4 中间产物（每章一个 JSON，.gitignore）
- `world_overview.json` — Phase 1 世界观概览
- `stage_plan.json` — Phase 1 阶段规划
- `candidate_characters.json` — Phase 1 候选角色
- `consistency_report.json` — Phase 3.5 一致性检查报告
- `evidence/` — 证据引用材料
- `conflicts/` — 矛盾与修订记录

不要为每个 stage 单独生成报告文件，交接信息应直接写入 progress 文件。

### indexes/

跨目录查询索引与 simulation engine 加载提示：

- `load_profiles.json` — 给运行时引擎的按需加载配置
- 其他索引按实体类型组织

## 设计规则

- `sources/works/{work_id}/` 存放源文本与标准化正文
- `works/{work_id}/` 存放该作品的基础 canon 包
- 用户侧状态应存放在 `users/{user_id}/`
- 对中文作品：
  - `work_id` 本身可以直接使用中文
  - 作品级 canon 默认保留中文名称和中文标识值，不转拼音
  - 由标识派生的文件夹名也应保持中文
- 用户对话不得改写作品级世界事实或大事件记录
- 用户侧角色漂移、关系变化和对话历史应归入 `users/{user_id}/`
- 世界材料是活的 canon 资产 — 后续章节可以修订和扩充
- 只有源文本证据可以修订世界 canon，用户对话不可以
- 运行时加载 `fixed_relationships.json`（Tier 0）；阶段性关系变化由
  `stage_snapshots/` 中的 `relationship_shifts` 提供

## 剧情阶段模型

- 每个提取 stage 对应一个剧情阶段（stage N = 阶段 N）
- 阶段规划在分析阶段按自然剧情边界确定，每个 stage 的章节数可以不同
  （默认目标 10 章，最小 5 章，最大 15 章，可在作品 config 中调整）
- 阶段 N 是累积的：选择阶段 N 意味着提取阶段 1..N 的全部内容
- **时间性原则**：当前所选阶段是角色的"现在"，之前的阶段是按顺序发生的
  历史事件。角色能记住发生过的事情，但必须用当前阶段的状态、性格和口吻
  与用户对话。世界状态同理——只有当前阶段的快照反映"此刻"的世界
- 世界和角色各自维护独立的 `stage_catalog.json` + `stage_snapshots/`，
  共享同一套 `stage_id`
- 每个阶段条目包含 `summary`（一句话总结），用于用户在开始对话时
  选择角色所处的剧情阶段
- `stage_catalog.json` 仅用于 bootstrap 阶段选择，运行时不加载
- `world_event_digest.jsonl` 提供世界事件时间线，运行时 stage 1..N 过滤加载

## 增量抽取建议

- 后续 agent 应优先读取 `analysis/progress/pipeline.json` 来确定当前阶段
- 每次有实质进度变化时，优先更新 `analysis/progress/` 下的进度文件
- work-local 进度推进默认不需要同步改 `ai_context/` 或 `docs/logs/`，除非
  连带改变了仓库级规则或架构

## 证据引用建议

- work-scoped JSON 中的 `evidence_refs` 默认使用紧凑章节引用：
  - `0001`、`0004`、`0011-0013`
- 不要默认把完整章节路径重复写进每个 JSON
- 只有当证据指向作品外文件或非章节文件时，才写完整路径
