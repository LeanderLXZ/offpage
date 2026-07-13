# Baseline lane：角色 target_baseline

你现在接手本地项目 Offpage，你没有任何额外背景知识，请完全按本提示词执行。

## 任务

基于全书分析阶段的产出，为作品 `{work_id}` 的**单个角色** `{char_id}` 产出
`{work_dir}/characters/{char_id}/canon/target_baseline.json`——全书视野下该角色与其它
角色之间的**有过 dialogue / action 交互的** target 关系列表
（character-level 恒定文件，与 identity / fixed_relationships 同源思路：
phase 2 一次拍，phase 3 各 stage 只读不写）。

必须遵循 `schemas/character/target_baseline.schema.json`。

## 作品信息

- work_id: `{work_id}`
- 书名: `{title}`
- 语言: `{language}`
- 本 lane 角色（baseline 主角）: `{char_id}`
- 作品目录: `{work_dir}`
- schemas 目录: `{schemas_dir}`

## 必读文件

请按顺序读取以下文件：

{files_to_read}

全书摘要在 `{lane_inputs_dir}/` 下（`chunk_*.json`，已按本 lane 需要裁剪字段：每章 `chapter` + `summary` + `characters_present`）。

## 准入门槛（决策 #54，重要）

**只有当本角色（baseline 主角，character_id = `{char_id}`）与目标角色在全书摘要描述中**被反映为有过 dialogue / action 交互**时，才纳入 baseline。**

具体判定（依据 `{lane_inputs_dir}/` 下所有 chunk 文件的 `summaries[]` 内容，而非原文）：

- ✅ **有 dialogue / action 交互**：摘要里出现"X 对 Y 说……" / "X 救 / 打 / 教 / 责备 Y" / "X 与 Y 联手……" / "X 杀 Y" / "X 救起 Y" 等动作或对话描述——双方至少一方对另一方有具体动作 / 对话
- ❌ **仅被提及但无交互**：摘要里只出现"……提到 Y" / "……听说 Y 的事" / "Y 在远方做某事"——本角色与 Y 没有发生在同一场景的具体动作或对话
- ❌ **末章/局部短暂出生 + 引发异象 + 无后续互动**：纯被动客体（如刚出生即引发异象，本身无主动 dialogue / action）不纳入
- ✅ **关键路人**：即使只有一次交互，但该交互对本角色后续剧情驱动力极大（如关键命运转折 / 命运伏笔），仍纳入并标 `tier=核心`

**血亲 / 师承等结构性关系不再默认核心 tier**——按准入门槛 + 实际剧情驱动力分级。若血亲无 dialogue / action 交互（如末章才出生的婴儿、远房从未谋面的亲属），同样不纳入 baseline。

## 字段

- `character_id`：本 baseline 描述的角色 ID（= `{char_id}`，与 identity.character_id /
  目录名 / manifest.character_id 三者一致）
- `targets[]`：每条对应一个对方角色。每条含：
  - `target_character_id`：对方角色的 identity.character_id（**统一用
    identity ID，不要用 canonical_name 或 aliases**——规避化名 / 隐藏身份
    导致的歧义；合法值 = `candidate_characters.candidates[].character_id`）
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

## 规则

- 中文作品的 character_id 直接使用中文角色名
- 所有产出文件必须是格式良好的 JSON
- 创建目录结构时确保所有中间目录存在
- 这是基于摘要的初稿——宁可保守少写，不可编造细节
- **`maxLength` / `maxItems` 是上限不是配额**：schema 给的字段长度 / 条数
  上限只是硬门控，不是要写到的目标，不要为了凑数而虚构、扩写、灌水
- **只写本 lane 的输出文件** `characters/{char_id}/canon/target_baseline.json`——
  不要创建或修改任何其他文件（foundation / fixed_relationships / identity /
  manifest 由并行 lane 产出；stage_catalog / digest 由后续 phase 程序化维护）
{retry_note}
