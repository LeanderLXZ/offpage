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
        target_baseline.json
        memory_timeline/{stage_id}.json
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
      rate_limit_pause.json         # §11.13 暂停契约（仅限额激活时存在）
      rate_limit_exit.log           # 限额硬停退出说明（仅 exit 2 路径写入）
      failed_lanes/                 # Phase 3 lane 级失败诊断（§11 T-LOG）
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
  - 仅本阶段发生的事件 `stage_events`（每条 50–100 字，schema 硬门控；
    仅收录世界公共层事件，角色私事/内心决定应写入该角色 memory_timeline。
    作为 `world_event_digest.jsonl` 的直接来源，1:1 复制；跨阶段时间线由
    digest 聚合，不在快照里累积）
  - 当前世界状态
  - 人物关系转变
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
  `schemas/character/identity.schema.json`
- `target_baseline.json` — 角色 target 关系 baseline（全书视野），与
  `identity.json` 并列的 character-level 恒定文件。Phase 2 一次性产出
  全部 target 列表，Phase 3 全程只读不写；运行时与 identity + 当前阶段
  snapshot 一同加载。内容涵盖：
  - `targets[]`：每条对应一个对方角色，含 `target_character_id`（对方
    identity.character_id，规避化名 / 隐藏身份歧义）+ `relationship_type`
    （中文短词，柔性 string；14 候选 至亲 / 恋人 / 挚友 / 师长 / 弟子 /
    朋友 / 同僚 / 主人 / 下属 / 宠物 / 武器 / 对手 / 敌人 / 路人，候选
    无法准确描述时允许用更精确中文短词，需在 `description` 说明差异）+
    `tier` ∈ {核心 / 重要 / 次要 / 普通}（站在本角色视角对该 target 的
    相对重要性；与 `relationship_type` 正交）+ `description`（关系描述）
  - Phase 3 `stage_snapshot` 三结构（`voice_state.target_voice_map` /
    `behavior_state.target_behavior_map` / 顶层 `relationships`）的
    keys 必须**双向相等**于 `targets[].target_character_id`；多 / 少均
    cross-file 硬失败
  - schema: `schemas/character/target_baseline.schema.json`
- `memory_timeline/{stage_id}.json` — 角色视角的记忆时间线，按阶段拆分（JSON
  数组，每个元素为一条记忆）。加载阶段 N 时只需读取阶段 1..N 的文件。内容涵盖：
  - 客观事件与角色的主观体验（可能与事实不同）
  - 情感影响与获得的新认知
  - 角色在该事件中产生的误解（如有）
  - 角色因该事件而隐瞒的信息（如有）
  - 该事件对角色关系的影响
  - 记忆重要程度（trivial → defining）
  - schema: `schemas/character/memory_timeline_entry.schema.json`
- `stage_catalog.json` — 角色阶段目录，每个阶段包含一句话总结
  （`summary`）供用户选择（仅 bootstrap 阶段选择，运行时不加载）
- `stage_snapshots/{stage_id}.json` — 角色在每个阶段的**自包含**状态快照
  （voice / behavior / boundary / failure_modes 全部内联，无独立 baseline
  文件；运行时与 `identity.json` + `target_baseline.json` 配套加载即可）。
  内容涵盖：
  - 仅本阶段发生的事件 `stage_events`（每条 50–80 字，schema 硬门控；
    非累积历史；跨阶段历史由 `memory_timeline` + `memory_digest.jsonl` +
    `world_event_digest.jsonl` 共同承载）
  - 当前状态（生死、恋爱、等级等随时间变化的状态）
  - 当前性格与性格转变
  - 当前心情与情感基线（驱动力、欲望、恐惧、心理创伤）
  - `voice_state`（内联）：基础语气 / 语言习惯 / 用词偏好 / 口头禅 /
    禁忌 / `emotional_voice_map` / `target_voice_map` / 典型对话示例
  - `behavior_state`（内联）：`core_goals` / `obsessions` / 决策风格 /
    情绪触发器 / `emotional_reaction_map` / `target_behavior_map` /
    习惯性行为 / 压力应对
  - `boundary_state`（内联）：`hard_boundaries` / `soft_boundaries` /
    `common_misconceptions`
  - `failure_modes`（内联，4 子类）：`common_failures` / `tone_traps` /
    `relationship_traps` / `knowledge_leaks`，全量记录本阶段 active 的
    崩坏防护清单（继承未消除 + 新增；已消除的不写）
  - 知识边界（知道/不知道/不确定；条数上限 50/30/30，每条 ≤ 50 字，
    schema 硬门控）
  - 误解：角色主观认为对但客观错误的认知（含真相和原因）
  - 隐瞒：角色知道但故意不说的信息（含对象和原因）
  - 阶段间变化 delta：从上一阶段到当前阶段的关键变化摘要
    （触发事件、性格变化、关系变化、状态变化、情绪基调转变、口吻转变）
  - 对其他角色的关系状态与信任度（顶层 `relationships`；keys 与
    `target_baseline.targets[].target_character_id` **双向相等**）
  - schema: `schemas/character/stage_snapshot.schema.json`

### analysis/

与该作品相关的分析产物与证据：

- `progress/` — 流水线进度文件：
  - `pipeline.json` / `phase0_summaries.json` / `phase3_stages.json` /
    `phase4_scenes.json` / `extraction.log` — 各阶段主进度
  - `rate_limit_pause.json` — 仅 §11.13 token 限额暂停激活期间存在，
    记录 `resume_at` / `reason` / probe leader claim；暂停解除后由
    controller 自动删除。**勿手动编辑或删除运行中的暂停文件**
  - `rate_limit_exit.log` — 限额硬停退出的说明文件（weekly 或 probe
    session 超 `probe_max_wait_h`）。仅 exit 2 路径写入，重跑
    `--resume` 前可留作 triage
  - `failed_lanes/` — Phase 3 lane 级失败诊断目录，文件名格式
    `{stage_id}__{lane_type}_{lane_id}__{pid}.log`，保留天数由
    `[logging].failed_lanes_retention_days` 控制（默认 30），到期
    由下次启动清理——**误删会丢失失败现场**
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
- 角色侧 voice / behavior / boundary / failure_modes 全部内联在
  `stage_snapshots/` 中逐 stage 演化，无独立 baseline 文件；character-level
  恒定文件只有 `identity.json` 与 `target_baseline.json`，运行时与当前
  阶段 snapshot 配套加载即可

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
- work-local 进度推进默认不需要同步改 `ai_context/` 或 `logs/change_logs/`，除非
  连带改变了仓库级规则或架构

