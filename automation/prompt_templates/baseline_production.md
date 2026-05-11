# Baseline 产出（全书分析后）

你现在接手本地项目 Offpage，你没有任何额外背景知识，请完全按本提示词执行。

## 任务

基于全书分析阶段的产出（phase 1 已落 `world/foundation/foundation.json`、`analysis/candidate_characters.json`、`analysis/stage_plan.json`、`analysis/chapter_summaries/`），为作品 `{work_id}` 产出 phase 2 baseline 5 件：

1. **补齐 `world/foundation/foundation.json` 的 `major_factions[].key_figures`**——phase 1 foundation lane 不写该字段（身份合并未完成），phase 2 单独 LLM 补丁式补齐
2. **世界级 fixed_relationships baseline**——`world/foundation/fixed_relationships.json`
3. **每角色 identity baseline**——`characters/{char_id}/canon/identity.json` + `manifest.json`
4. **每角色 target_baseline**——`characters/{char_id}/canon/target_baseline.json`（**准入门槛收紧**，详见产出 4）
5. **世界与角色 stage_catalog 初始化**——空数组占位

**foundation 不再由 phase 2 产出**——决策 #54 把 foundation 前移到 phase 1 foundation lane 直接产，phase 2 仅补 `key_figures` 字段。

identity 与 target_baseline 都是 character-level 恒定文件——identity 记录
角色基础事实（aliases / core_wounds / key_relationships 等），target_baseline
记录该角色与其它角色之间的全部 target 关系（全书视野，phase 3 只读不写）。
两者 phase 2 一次产出后永不变化；运行时与当前 stage_snapshot 配套加载。
voice / behavior / boundary / failure_modes 不在 Phase 2 产出——由 Phase 3
char_snapshot lane 在每个 stage_snapshot 中直接生成（S001 从原文 + identity
推演基线种子，S002+ 从前一 stage_snapshot 演变）。

## 作品信息

- work_id: `{work_id}`
- 书名: `{title}`
- 语言: `{language}`
- 目标角色: {target_characters}
- 作品目录: `{work_dir}`
- schemas 目录: `{schemas_dir}`

## 必读文件

请按顺序读取以下文件：

{files_to_read}

## 产出 1：补齐 `foundation.major_factions[].key_figures`

phase 1 foundation lane 已经落盘 `{work_dir}/world/foundation/foundation.json`，但 `major_factions[].key_figures` 字段被刻意留空——因为 phase 1 阶段身份合并（由 candidate_characters lane 并行处理）尚未完成，foundation lane 拿不到 character_id 终态。phase 2 在身份合并完成后单独一个轻量 LLM call 补齐该字段。

### 读取契约

- 输入：`{work_dir}/world/foundation/foundation.json`（phase 1 foundation lane 已产）+ `{work_dir}/analysis/candidate_characters.json`（phase 1 candidate_characters lane 已产）+ 目标角色清单（`{target_characters}`，phase 1.5 用户已确认）
- 合法 character_id 集 = **`candidate_characters.candidates[].character_id` 全集**（phase 1.5 已确认的目标角色清单是其子集；非目标角色但合法的 candidate 仍可作为 faction 关键人物）

### 输出形态

读取 `foundation.json` 后，**仅修改 `major_factions[]` 数组的 `key_figures` 字段**——其他字段（`work_id` / `genre` / `tone` / `world_structure` / `power_system` / `core_rules` / `world_lines` / `major_factions[].name` / `major_factions[].description`）**一字不动**直接保留。

为每个 `major_factions[i]`：
- 阅读其 `name` + `description`
- 在 `candidate_characters.candidates[]` 里找到该势力的关键人物（核心成员 / 领袖 / 代表人物等），用 `character_id` 列出
- 写到 `major_factions[i].key_figures` 数组里（≤10 项，每项 ≤30 字）
- **每个 character_id 必须 ∈ `candidate_characters.candidates[].character_id` 全集**——非法 character_id 会触发 schema gate 失败 + tolerance gate 兜底 + 失败则 `sys.exit(1)`

如果某势力在 candidates 中找不到对应关键人物（势力存在但全是 raw 名未在身份合并中出现 / 或势力只在 chunk-level 提到但无主要角色归属），`key_figures` 写空数组 `[]`。

### 落盘

把修改后的整份 foundation 写回原路径 `{work_dir}/world/foundation/foundation.json`，覆盖原文件。schema 契约 → `schemas/world/foundation.schema.json`，bound 以 schema 为准。

## 产出 2：fixed_relationships.json

世界级固定关系网络——**仅记录全书从开始到结束都未改变的结构性纽带**。

位置：`{work_dir}/world/foundation/fixed_relationships.json`

必须遵循 `schemas/world/fixed_relationships.schema.json`。

**判定核心**：是否在本作时间线内**贯穿不变**。关系类型只是常见示例：

- ✅ **属于 fixed**：血缘 / 自始即有的师承 / 自始即有的门派归属 / 长辈
  晚辈等贯穿始终的结构性关系。这些关系是世界视角的客观事实，不同于
  角色 identity.json 中的主观关系感知
- ❌ **不属于 fixed**（**任何在故事中才建立 / 改变 / 解除的关系都不是
  fixed**）：故事中才结成的师承、加入的门派、收养、结义、结婚 / 离婚、
  决裂、归化、敌对转盟友、盟友转敌对等。这些走 character/stage_snapshot
  的 `relationships`，按 stage 演进；写入此处会污染世界级骨架

```json
{{
  "schema_version": "1.0",
  "work_id": "{work_id}",
  "relationships": [
    {{
      "relationship_id": "FR-001",
      "type": "血缘 / 自始即有的师承 / 自始即有的门派归属 / 长辈晚辈 / ...",
      "parties": ["角色A", "角色B"],
      "description": "关系描述（≤100 字）"
    }}
  ]
}}
```

初稿基于全书摘要 + chunk-level 二级字段推断（`chunk_factions.members_present`
经 Phase 1.5 身份合并后可作为势力归属信号；血缘 / 自始即有的师承等结构性
关系仍需结合摘要确认），后续 stage 读到原文后修正和补充（修正限于补漏、
订正描述等，不应把 stage-acquired 关系反向迁入此处）。

## 产出 3：角色 Identity Baseline

为每个目标角色产出 `identity.json` 和 `manifest.json`。

目标角色列表：{target_characters_list}

### identity.json

位置：`{work_dir}/characters/{{char_id}}/canon/identity.json`

必须遵循 `schemas/character/identity.schema.json`。

重点字段：
- `canonical_name`：角色最终/最通用的正式名称
- `aliases`：结构化别名数组（从身份合并结果直接转化），每条含 name、type（本名/化名/代称/称呼/昵称/绰号/封号/道号/武器名/其他）、effective_stages（可先留空，提取时填充）、source、used_by
- `gender`、`species`、`birth_origin`、`appearance_summary`、`background_summary`、`initial_social_position`、`affiliations`、`distinguishing_features`
- `core_wounds`：角色的核心创伤——跨全故事始终影响角色行为和心理的根源性伤痛。每条含：
  - `wound`：创伤内容
  - `origin`：创伤的来源/成因
  - `behavioral_impact`：对行为的长期影响
- `key_relationships`：角色的核心人物关系（仅记录对角色有重大影响的关系）。每条含：
  - `target`：关系对象
  - `initial_relationship`：故事开始时的关系状态
  - `relationship_arc`：全局演变弧线概述（如"仇人→被迫共处→产生真情→结为伴侣"）
  - `turning_points`：关键转折点列表

注意：这些信息基于全书摘要产出，是初稿。后续 stage 提取读到原文后会修正。
对于不确定的字段直接留空或省略，不要强行填写以示"推断"。
core_wounds 和 key_relationships 基于全书摘要可以产出较准确的初稿——全书
视野有利于识别贯穿故事的创伤和关系弧线。

### manifest.json

位置：`{work_dir}/characters/{{char_id}}/manifest.json`

必须遵循 `schemas/character/character_manifest.schema.json`。

- `character_id`：与目录名一致
- `canonical_name`：与 identity.json 一致
- `aliases`：从 identity.json 的结构化 aliases 中提取名称的扁平字符串数组
- `paths`：填入正确的相对路径。**注意**：
  - `stage_snapshot_root` 必须指向 `characters/{{char_id}}/canon/stage_snapshots`（不是 `canon/stages`）
  - `target_baseline_path` 必须指向 `characters/{{char_id}}/canon/target_baseline.json`（即下方"产出 4"所产文件）

## 产出 4：角色 Target Baseline

为每个目标角色产出 `target_baseline.json`——全书视野下该角色与其它
角色之间的**有过 dialogue / action 交互的** target 关系列表
（character-level 恒定文件，与 identity / fixed_relationships 同源思路：
phase 2 一次拍，phase 3 各 stage 只读不写）。

### target_baseline.json

位置：`{work_dir}/characters/{{char_id}}/canon/target_baseline.json`

必须遵循 `schemas/character/target_baseline.schema.json`。

### 准入门槛（决策 #54，重要）

**只有当本角色（baseline 主角，character_id = `{{char_id}}`）与目标角色在 `chapter_summaries/` 摘要描述中**被反映为有过 dialogue / action 交互**时，才纳入 baseline。**

具体判定（依据 phase 0 chunk 摘要——`{summaries_dir}` 下所有 chunk 文件的 `summaries[]` 内容，而非原文）：

- ✅ **有 dialogue / action 交互**：摘要里出现"X 对 Y 说……" / "X 救 / 打 / 教 / 责备 Y" / "X 与 Y 联手……" / "X 杀 Y" / "X 救起 Y" 等动作或对话描述——双方至少一方对另一方有具体动作 / 对话
- ❌ **仅被提及但无交互**：摘要里只出现"……提到 Y" / "……听说 Y 的事" / "Y 在远方做某事"——本角色与 Y 没有发生在同一场景的具体动作或对话
- ❌ **末章/局部短暂出生 + 引发异象 + 无后续互动**：纯被动客体（如刚出生即引发异象，本身无主动 dialogue / action）不纳入
- ✅ **关键路人**：即使只有一次交互，但该交互对本角色后续剧情驱动力极大（如关键命运转折 / 命运伏笔），仍纳入并标 `tier=核心`

**血亲 / 师承等结构性关系不再默认核心 tier**——按准入门槛 + 实际剧情驱动力分级。若血亲无 dialogue / action 交互（如末章才出生的婴儿、远房从未谋面的亲属），同样不纳入 baseline。

### 字段

- `character_id`：本 baseline 描述的角色 ID（与 identity.character_id /
  目录名 / manifest.character_id 三者一致）
- `targets[]`：每条对应一个对方角色。每条含：
  - `target_character_id`：对方角色的 identity.character_id（**统一用
    identity ID，不要用 canonical_name 或 aliases**——规避化名 / 隐藏身份
    导致的歧义）
  - `relationship_type`：关系类型，**中文短词，柔性 string**（schema 不
    再 enum 硬卡）。优先 14 候选：
    - `至亲`（血亲 / 至亲）
    - `恋人`（恋人 / 配偶 / 道侣）
    - `挚友`（深交挚友）
    - `师长`（师父 / 引路人）
    - `弟子`
    - `朋友`
    - `同僚`（同事 / 盟友 / 上下级等阵营关系）
    - `主人`
    - `下属`
    - `宠物`
    - `武器`（具灵性的武器 / 法宝 / 神兵等可互动 target）
    - `对手`（竞争 / 比试，非敌对）
    - `敌人`
    - `路人`（陌生人 / 一面之缘 / 极弱人际关联）

    候选无法准确描述时（例如仙侠中的"道侣"已并入恋人；机甲 / 仙器中
    的"操作者""容器""契约者"等特殊语境角色），允许使用列表外更精确的
    中文短词，但**必须在 `description` 字段说明该词与候选 14 项的差异**；
    不要硬塞进相近候选。
  - `tier`：重要程度（站在本角色视角看对方的相对重要性）。**准入门槛与 tier 分级正交**——准入门槛决定"纳入与否"，tier 决定"重要度梯度"。
    - `核心` = 亲密圈 / 关键宿敌（驱动主要剧情线）
    - `重要` = 对角色行为有显著影响
    - `次要` = 偶有交互
    - `普通` = 极弱关联但仍纳入 baseline（确保 phase 3 三结构 keys ==
      baseline 双向相等约束下 LLM 写入泛弱关联角色不会 fail，同时漏列
      也不会 fail）

    **注意 tier 「普通」 ≠ relationship_type 「路人」**——前者是本角色
    视角下的重要度梯度，后者是关系性质。两维正交，常见组合：「普通 +
    路人」（重要度极低、关系也是路人）；但「核心 + 路人」也合法（关系
    性质虽是路人，因伏笔 / 命运纠缠而对本角色至关重要）。
  - `description`：≤100 字关系描述

**该 baseline 是 phase 3 的硬锚点（双向相等）**：phase 3 stage_snapshot
三结构（`voice_state.target_voice_map` / `behavior_state.target_behavior_map`
/ 顶层 `relationships`）的 keys 必须**双向相等**于 `targets[].target_character_id`：
`set(三结构 keys) == set(targets[].target_character_id)`，多/少都
cross-file hard fail（多 = 写出 baseline 之外的角色；少 = 漏写 baseline
列出的角色）。校验在 phase 3 单 stage validate 层执行，违规走 file-level
repair lifecycle。

phase 2 一旦漏判某 target，phase 3 不会自动补救——需要人工编辑 baseline
后重抽该 stage。**所以准入门槛要严格遵守**——严格执行"dialogue / action
交互"判定，不要补"宁可多列"的泛弱关联角色（决策 #54 已废除此原则）。

**容量上限（targets 数组）**通过 `schemas/character/targets_cap.schema.json`
单源约束。下游 stage_snapshot 三结构通过同一份 $ref 共享继承——调整
数字只改这一处。**触顶时按 `tier` 优先级裁剪**：核心 > 重要 > 次要 >
普通，普通先弃；同 tier 内按"对主线剧情驱动力"二次排序。被裁的角色
不进 baseline，phase 3 stage_snapshot 也不得提及（cross-file 双向相等
校验会同时拒绝"baseline 没列却 stage 写入"和"baseline 列了 stage 漏
写"两种违规——后者由 stage_snapshot 写空 entry 满足，详见
character_snapshot_extraction prompt 的 D4 三态规则）。

`tier` 与 `relationship_type` 的关系：tier 描述本角色视角下的"重要度
梯度"，relationship_type 描述"关系性质"。两者正交，不要把 tier 信息
强行塞进 relationship_type。例如同样是 `朋友`，对主角而言可能是 `核心`
（青梅竹马）或 `次要`（点头之交）；同样是 `路人`，可能是 `普通`
（街头偶遇）也可能是 `核心`（命运伏笔的关键路人）。

## 产出 5：世界与角色 Stage Catalog 初始化

为世界包和每个目标角色创建空的 stage_catalog.json，后续提取时逐阶段追加。

- `{work_dir}/world/stage_catalog.json`（遵循 `schemas/world/world_stage_catalog.schema.json`）
- `{work_dir}/characters/{{char_id}}/canon/stage_catalog.json`（遵循 `schemas/character/stage_catalog.schema.json`）

世界 catalog 初始内容：

```json
{{
  "schema_version": "1.0",
  "work_id": "{work_id}",
  "stages": []
}}
```

角色 catalog 初始内容：

```json
{{
  "schema_version": "1.0",
  "character_id": "{{char_id}}",
  "work_id": "{work_id}",
  "stages": []
}}
```

**注意**：后续提取追加 stage 条目时，每条**必须**包含 `stage_id`（紧凑英文代号 S###，排序键）、`stage_title`（短标题）、`summary`（一句话摘要）、`snapshot_path`（快照相对路径）。stage_catalog 仅用于 bootstrap 阶段选择，运行时不加载。

## 不在 baseline 阶段产出的文件

以下文件由 `post_processing.py` 在每阶段提取完成后程序化维护（0 token），
baseline 阶段**不需要**创建任何占位文件：

- `{work_dir}/world/world_event_digest.jsonl` — 从世界 stage_snapshot 的
  `stage_events` 生成；首阶段提取后首次创建，后续阶段 upsert。
- `{work_dir}/characters/{{char_id}}/canon/memory_digest.jsonl` — 从角色
  memory_timeline 生成；同样由首阶段 post-processing 首次创建。

baseline 阶段只需完成上文列出的 foundation.key_figures 补齐 /
fixed_relationships / identity / target_baseline / manifest / 空 stage_catalog。

## 规则

- 中文作品的 work_id、character_id、路径段、内容使用中文；`stage_id` 使用紧凑英文代号 `S###`（如 `S001`），`stage_title` 使用中文短标题
- 中文作品的 character_id 直接使用中文角色名
- 所有产出文件必须是格式良好的 JSON
- 创建目录结构时确保所有中间目录存在
- 这是基于摘要的初稿——宁可保守少写，不可编造细节
- 如果某个字段在摘要中完全无法判断，留空或省略，不要猜测
- **`maxLength` / `maxItems` 是上限不是配额**：schema 给的字段长度 / 条数
  上限只是硬门控，不是要写到的目标。摘要里能支撑 3 条就写 3 条，能写
  50 字就写 50 字，不要为了凑到 maxItems 或 maxLength 而虚构、扩写、
  灌水
