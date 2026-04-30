# 系统概览

## 目标

构建一个可复用的、多终端的长篇小说角色扮演引擎。

系统应支持：

- 在进入下游运行时选择之前，输入或创建 `user_id`
- 在加载下游资产之前选择源作品
- 除角色状态外，还能提取并保存世界状态
- 从小说中提取一个或多个角色
- 保存基于原作的世界资产包
- 保存基于原作的角色资产包
- 将用户特有的关系成长数据独立保存
- 在对话开始时选择作品级别的阶段（stage）
- 默认将该阶段投射到目标角色及任何基于原作的用户侧角色槽位
- 在初始账户创建后锁定引导设置选项
- 在实时角色扮演过程中持续写入用户级 session/context 状态
- 通过明确的退出意图关闭 session，并询问是否将已关闭的 context 合并到用户持有的长期历史记录中
- 通过 agent、应用程序和 MCP 终端加载同一套核心逻辑

## 仿真引擎主目录

仓库级别的运行时编排应位于：

- `simulation/`

推荐拆分方式：

- `docs/architecture/`
  - 静态的仓库结构与数据模型边界
- `simulation/`
  - 引导流程、启动加载、检索路由、持续回写、
    显式关闭/合并，以及服务契约
- `works/{work_id}/indexes/`
  - 作品特有的加载配置和检索提示，供仿真引擎使用

## 两个作品资产包

每部作品应有两个独立的资产包根目录：

1. `sources/works/{work_id}/`
   - 原始及规范化的源材料
   - 章节文本与源数据元信息

2. `works/{work_id}/`
   - 该作品的持久化、基于原作的规范资产包
   - 世界、角色、分析和索引

## 作品命名空间

每部小说应作为独立的命名空间，以 `work_id` 标识。

该命名空间应涵盖：

- 源语料库
- 规范作品资产包
- 作品级分析输出
- 世界资产包
- 角色资产包
- 作品级用户关系数据
- 用户级运行时编译输入

运行时请求和持久化的用户状态 manifest 也应显式携带 `work_id`，而不仅仅依赖目录位置，以确保多作品运行时状态不会产生歧义。

因此，面向用户的流程应从以下步骤开始：

1. 输入 `user_id`
2. 判断这是新设置还是已有设置
3. 如果是新设置：
   - 选择作品
   - 选择目标角色
   - 选择当前活跃的作品阶段（stage）
   - 选择用户侧角色或对应身份
   - 如果用户侧角色基于原作，则默认将该侧绑定到与目标相同的活跃作品阶段
   - 锁定设置
4. 如果是已有设置：
   - 显示已锁定的账户信息
   - 列出可恢复的 context
5. 创建或恢复 context

## 内容语言策略

对于作品级生成材料，内容文本应默认使用源作品的语言。

示例：

- 中文作品应保留其原始中文标题
- 中文作品可以使用中文 `work_id`
- 中文作品应生成中文角色资产包
- 中文作品应生成中文世界资产包
- 中文作品应生成中文的作品级用户/关系材料
- 中文作品也应默认保留作品级实体名称和标识符值为中文
- 由这些标识符派生的作品级文件夹名称也应默认保持中文

字段名称可保持英文以保证结构一致性：

- JSON 键名
- schema 属性名
- 仓库级结构标识符

但作品级规范中的标识符值不必是英文。当使用拼音替代会使原作数据更难以检查时，应避免用纯拼音 ID 替换源标签。

同样，`works/{work_id}/` 下由标识符派生的路径段也不必是英文。如果规范标识符是中文，生成的文件夹或文件路径段应沿用中文。

这同样适用于作品资产包根目录本身。如果 `work_id` 是中文，则 `sources/works/` 和 `works/` 下的根文件夹应直接使用该中文路径段。

## 核心层

### 1. 源语料库

存储原始和规范化的小说文本以及未来的检索工件。

### 2. 分析层

存储增量提取结果、证据引用和冲突记录。

推荐位置：

- `works/{work_id}/analysis/` 用于持久化和增量的作品级分析
- 如需草稿笔记，应保留在同一作品资产包下，而非恢复仓库级 `analysis/` 目录

自动化提取流程：

0. **阶段 0 — 章节归纳**：按分组（chunk，约 25 章/组）逐组归纳，产出每章
   结构化摘要。存储在 `analysis/chapter_summaries/`
1. **阶段 1 — 全书分析**（基于摘要）：跨 chunk 角色身份合并 → 世界观概览
   (`world_overview.json`) → 剧情阶段划分 (`stage_plan.json`) →
   候选角色识别 (`candidate_characters.json`)
2. **阶段 1.5 — 用户确认**：用户选定目标角色、确认 stage 边界
3. **阶段 2 — Baseline 产出**：基于全书摘要上下文，产出世界 foundation
   (`world/foundation/foundation.json`) 和已确认角色的 identity baseline
   (`identity.json`, `manifest.json`)。这些是初稿，后续阶段可修正
4. **阶段 3 — 1+2N 分层阶段提取**：逐 stage 读原文，采用 1+2N 架构：1 次
   世界提取 + N 次角色快照提取 + N 次角色支撑提取并行。每次调用只传最近
   一个 snapshot/memory + identity，不传全部历史。`stage_snapshot` 含本
   stage 全量 voice / behavior / boundary / failure_modes 字段（演变链
   承载，无独立 baseline 文件）；任何阶段 char_support 可修正 identity
5. **阶段 3.5 — 跨阶段一致性检查**：Phase 3 全部 stage 提交后，运行程序化
   跨阶段一致性检查（零 token），可选 LLM 裁定标记项。有 error 时阻断 Phase 4
6. **阶段 4 — 场景切分**：Phase 3.5 通过后，逐 stage 范围读原文，按自然场景
   边界切分产出 scene_archive 条目。各 stage 间无依赖，可并行。与 Phase 3
   分离以避免单次调用任务过重影响质量

任何一个阶段仍可能修订或补充多个下游资产，包括世界层和多个角色资产包。

### 3. 世界资产包

存储基于原作的、与用户无关的世界资产。

每个资产包可能包含：

- 世界 manifest
- 世界阶段目录
- 世界基础设定
- 力量体系规则
- 历史时间线
- 重大共享事件注册表及事件摘要
- 作品阶段快照（stage snapshot）
- 世界状态快照
- 地点记录
- 地点状态快照
- 势力/阵营记录
- 地图图谱与地理注记
- 作品级角色索引及主要角色和高频配角的简要介绍
- 阶段级关系视图

这些资产应以增量方式维护。

新文本可能会：

- 扩展先前的世界理解
- 修正早期的假设
- 澄清不确定的地理信息
- 修订城市、势力或机构的明显状态
- 细化重大事件的时间线、范围或含义

这些修订应具有可追溯性，基于源文本驱动，而非静默覆盖先前的理解。

重要边界：

- 规范世界资产可被后续的源文本阅读所修订
- 用户对话和运行时分支不得重写规范世界历史、世界状态事实或事件记录
- 世界资产包应优先记录重大共享事件，而非已由角色资产包更好承载的小场景级细节
- 世界资产包默认不应复制独立的角色知识层
- 世界资产包不应被一次性的次要角色杂乱填充，除非这些角色后来在结构上变得重要
- 详细的角色侧事件记忆和解读应保留在角色资产包中

### 4. 角色资产包

存储基于原作的、与用户无关的角色资产。

每个资产包包含：

- 角色 manifest（`paths.target_baseline_path` 指向下条文件）
- `identity.json` — 角色基础事实（character-level 恒定文件之一）
- `target_baseline.json` — 全书视野下与其它角色之间的全部 target 关系
  （character-level 恒定文件之二，phase 3 全程只读不写）
- 记忆时间线
- 与作品时间线对应的阶段目录
- 与作品级 `stage_id` 对应的**自包含阶段快照**（stage_snapshot；含本阶段
  全量 voice / behavior / boundary / failure_modes 字段）

阶段快照是运行时角色扮演的唯一状态来源（配合不变层 identity +
target_baseline）。每个快照包含该阶段的完整状态：

- `voice_state`：语气基调、情绪语气矩阵（emotional_voice_map）、
  **对象语气矩阵**（target_voice_map，按具体角色区分的说话差异）
- `behavior_state`：**core_goals**（理性目标）、**obsessions**（执念）、
  决策风格、情绪反应矩阵（emotional_reaction_map）、
  **对象行为矩阵**（target_behavior_map，按具体角色区分的行为差异）
- `emotional_baseline`：dominant_traits、**active_goals**（活跃理性目标）、
  **active_obsessions**（活跃执念）、active_fears、active_wounds
- `boundary_state`、`relationships`、`knowledge_scope`、`misunderstandings`、
  `concealments`、`stage_delta`
- `character_arc`：角色从阶段 1 到当前的整体弧线概览

target_voice_map 和 target_behavior_map 每条 entry 以 `target_character_id`
为身份键，覆盖 baseline.targets 全集；详细度按 `tier` 分层——核心 / 重要
target 详细记录（每 target 至少 3-5 条原文示例），次要 / 普通 target
简要记录；从未登场的 baseline target 字段保持空（D4 状态 3）。`target_type`
sibling 字段记关系类型 / 角色定位，仅供 OC 路径 fallback 使用。

**运行时过滤加载**：target_voice_map 和 target_behavior_map 按用户扮演
角色过滤——canon 角色（已绑定 baseline character_id）走 `target_character_id`
精确匹配；OC 角色（无 baseline character_id）按 role_binding 设定特征
+ entry 的 sibling `target_type` 标签 fallback 匹配。**Fallback**：
如果当前 stage snapshot 缺少匹配条目（如该角色近期未出场），引擎向前
扫描最近包含该条目的 stage snapshot。

角色构建通常应在初始的世界优先阶段处理建立了该作品的共享世界背景之后进行。

### 5. 用户资产包

存储用户身份、人设、关系核心（relationship core）、context 分支和 session 历史。

这是长期关系记忆和用户特有的角色偏移所属之处。

推荐拆分方式：

- `users/{user_id}/` 作为用户根目录
- 每个 `user_id` 对应一个已锁定的作品-目标-对应角色绑定

作品级用户/关系材料应默认使用所选作品的语言。

当用户选择目标角色时，运行时从 `works/{work_id}/characters/{character_id}/`
加载所选阶段的自包含快照（不加载 baseline，不做合并），然后叠加来自
`users/{user_id}/` 的用户特定状态。

`role_binding.json` 应能存储：

- 选定的目标角色和 `stage_id`
- 当前用户侧角色模式
- 如果用户侧角色是另一个规范角色，则为该角色的 `character_id`
- 用户侧规范角色是否继承目标 `stage_id`
- 初始设置是否已锁定
- 该用户-角色对的加载和回写偏好

该文件的首版专用 schema 现位于：

- `schemas/user/role_binding.schema.json`

`relationship_core` manifest、`context` manifest、`session` manifest 和运行时请求载荷都应显式包含 `work_id`，以使这些对象在其路径上下文之外仍然是自描述的。

### 6. 仿真引擎

推荐的仓库级主目录：

- `simulation/`

编译内容包括：

- 世界基线
- 选定的世界阶段快照
- 相关的作品级事件摘要
- 基于选定阶段推导的当前世界状态视图
- 如有需要，相关的地点状态
- 角色规范数据
- 选定的目标角色阶段投射
- 用户人设或用户侧角色绑定
- 如果用户侧角色也是规范角色，则为该角色选定的对齐阶段投射
- 用户持有的该作品-角色对的长期自我档案
- 关系核心（relationship core）
- 当前 context 分支
- 近期 session 状态

以上内容编译为模型所需的最小运行时上下文。

该运行时上下文可能依赖于在世界优先阶段提取中首次发现、并在后续针对性角色提取中进一步精化的事实。

如果运行时状态需要持久化，应优先使用用户级 context 树，而非 `works/{work_id}/`。

在实时对话中，运行时持久化应在用户层持续进行：

- `sessions/`、`contexts/` 和 `contexts/{context_id}/character_state.json` 应接收轻量级的持续更新
- 每个活跃 session 应在每个输入/输出周期追加到转录备份和回合日志中
- `relationship_core` 和 `pinned_memories` 应更有选择性地更新
- 作品-角色级的长期档案仅在用户确认合并时才更新
- context 在策略和证据允许时，可在后续部分或全部合并到用户持有的长期历史记录中
- 已合并的 context 还可将完整的转录包提升到账户级对话存档库中

### 7. 接口层

将同一核心角色扮演引擎暴露给：

- 直接 AI agent
- 前端应用程序
- 移动端聊天 MCP 风格适配器

这些适配器应面向 `simulation/contracts/` 下的引擎契约，而非直接读取仓库文件。

## 运行时加载公式

在对话开始时，系统应加载：

`世界 foundation（含 fixed_relationships）+ 选定的世界阶段快照 + world_event_digest 1..N + 角色不变层（identity + target_baseline）+ 选定阶段的自包含快照 + memory_timeline 近期 2 阶段全量 + memory_digest 1..N 过滤 + scene_archive 最近 N 条 full_text（默认 10；摘要不进启动，按需从 FTS5 取）+ 用户绑定 + 长期档案 + 关系核心 + 当前 context + 近期 session 状态`

注意：voice / behavior / boundary / failure_modes 全部内联进 stage_snapshot，
没有独立 baseline 文件；运行时角色状态完全由自包含的 stage_snapshot 提供。

推荐的加载拆分：

- 启动必需：
  - 世界 foundation（`foundation.json` + `fixed_relationships.json`）+ 选定的世界阶段快照
  - `world_event_digest.jsonl`：stage 1..N 过滤加载（世界事件时间线）
  - 角色不变层：identity.json + target_baseline.json（character-level 恒定文件，phase 2 产出）
  - 选定阶段的**自包含** stage_snapshot（含本 stage 全量 voice / behavior / boundary / failure_modes / relationships）
  - memory_timeline：近期 2 阶段（N + N-1）全量
  - memory_digest.jsonl：stage 1..N 过滤加载（压缩索引，远期感知）
  - scene_archive：最近 `scene_fulltext_window` 条 full_text（默认 10，
    可通过 `load_profiles.json` 覆盖）；**摘要不在启动期加载**，仅存在于
    FTS5 索引，按需检索
  - vocab_dict.txt → jieba 自定义词典
  - 用户摘要层状态（role_binding、long_term_profile、relationship_core）
  - 当前 context 摘要 + 近期 session 摘要
- 按需加载：
  - 特定世界事件、地点/势力记录
  - 历史 stage_snapshot（深层历史回忆时）
  - FTS5/embedding 检索 memory_timeline 和 scene_archive 详情
  - 详细的用户 context 历史、账户存档摘要
  - 完整 session 转录
  - 需要验证时的原始章节证据

当存在时，`works/{work_id}/indexes/load_profiles.json` 应为该作品细化此加载拆分。

## 阶段选择

阶段选择应基于一个作品级的阶段轴，而非各角色独立的自由格式标签。

世界资产包应暴露一个作品级的 `stage_catalog.json`（仅用于 bootstrap 阶段选择，
运行时不加载），包含：

- 阶段 ID
- 阶段标题
- 面向用户的单行摘要（`summary`）
- 累计章节范围或等效的源覆盖范围

世界事件时间线由 `world_event_digest.jsonl` 提供（运行时 stage 1..N 过滤加载）。

角色资产包应为这些相同的 `stage_id` 值暴露投射，包括：

- 截至该阶段的经历和记忆状态
- 截至该阶段的关系状态
- 截至该阶段的当前性格、情绪和语音
- 截至该阶段的当前状态和约束

在新对话开始时：

1. 终端接受或创建 `user_id`
2. 系统判断这是新设置还是已有设置
3. 对于新设置，系统显示作品的可用阶段
4. 用户选择一个活跃的作品阶段
5. 系统将目标角色绑定到该阶段
6. 如果用户侧角色也是规范角色，该侧默认继承相同阶段
7. 锁定设置
8. 使用该阶段绑定创建或恢复 context

任何选定的规范阶段应与所选作品的世界状态保持兼容，除非系统明确在建模分支或替代设置。

## 关系记忆

用户特有的记忆拆分为：

- `long_term_profile`
  - 用户持有的、针对单个作品-角色对的长期自我档案变更
- `relationship_core`
  - 长期保留的记忆
- `contexts/{context_id}`
  - 分支特有的连续性
- `conversation_library`
  - 账户级不可变存档，用于存储已合并的对话记录

Context 后续可以是：

- 临时的
- 持久的
- 合并到关系核心中

实时角色扮演不应在用户状态更新前等待单独的手动回写步骤。

推荐的回写节奏：

- 持续更新 `sessions/` 和当前 `contexts/`
- 有选择性地固定或提升长期记忆
- 支持通过退出关键词或等效关闭意图显式关闭 session
- 关闭后，询问当前 context 是否应合并到 `long_term_profile` 和 `relationship_core` 中
- 当用户请求或策略允许时，支持显式的 context 提升或完全合并到用户持有的长期状态中

运行时加载应保持摘要/详情分离：

- 启动时可加载用户摘要、关系摘要、context 摘要、近期 session 摘要和范围内的存档引用
- 完整的 `transcript.jsonl` 文件应保留在 `users/` 下的本地位置，仅在需要精确对话回溯时通过按需检索打开

推荐位置：

- `users/{user_id}/`
