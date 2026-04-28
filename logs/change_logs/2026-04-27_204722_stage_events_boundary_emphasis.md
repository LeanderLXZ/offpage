# stage_events_boundary_emphasis

- **Started**: 2026-04-27 20:47:22 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

会话中讨论 character `stage_snapshot` 拆分并行化时，曾误将 `stage_events`
列入跨 lane 耦合点。重新核对决策 31/34 后澄清：

- world `stage_events` = 世界公共层事件（势力变迁、地形/资源变化、规则
  揭示、跨角色公共事件，如 boss 复活、奇观、地震等天灾）
- character `stage_events` = 该角色亲历 / 亲为 / 对其处境或认知有直接
  影响的事件（其他角色的私事、与该角色无关的世界变迁均不写入）

两者边界已分布在 schema、prompt、docs 多处，但表述各处偏弱、缺少正负
样例对照，且 character 侧没有把"世界事件需以角色视角重写、不可直接
复制"这条隐含规则显式化。本次只做表述强化，不动 schema 结构 / 边界。

## 结论与决策

只做表述强化（description / prompt 文字），**不改**：

- 字段结构 / required 列表
- 长度边界（字符 / 条数 maxItems / minLength / maxLength）
- L1 / L2 检查器逻辑（边界判定仍由 LLM + 语义 review 承担，不下沉到 L1）
- post_processing 1:1 复制契约
- character `stage_events` 的运行时加载方式

只在以下位置补强表述：

1. character `stage_snapshot.schema.json` 的 `stage_events.description`
2. world `world_stage_snapshot.schema.json` 的 `stage_events.description`
3. `automation/prompt_templates/character_snapshot_extraction.md` 的 stage_events 段落
4. `automation/prompt_templates/world_extraction.md` 的核心规则 / 判定表
5. `docs/architecture/schema_reference.md` 两处 `stage_events` 行
6. `docs/architecture/data_model.md` 两处 `stage_events` 注解

## 计划动作清单

- file: `schemas/character/stage_snapshot.schema.json` → `stage_events.description` 加上"事件归属判定"语句：本字段=该角色亲历/亲为/直接影响其处境或认知的事件；其他角色私事不写；世界级公共事件由 world `stage_events` 承载，仅当该角色亲历该世界事件时才以**角色视角**重写一条（不直接复制世界层文本）。
- file: `schemas/world/world_stage_snapshot.schema.json` → `stage_events.description` 在已有"世界公共层事件（势力变迁、地形/资源变化、规则揭示、跨角色公共事件）"后追加具体例子：大 boss 复活、世界奇观、天灾（地震 / 灵脉断裂）。明确"角色私人剧情、与角色绑定的内心决定、单角色经济活动一律不写入"。
- file: `automation/prompt_templates/character_snapshot_extraction.md` → 第 67 行所在 bullet 重写：先讲事件归属（角色相关 only），再讲"如本阶段有该角色亲历的世界事件，须以角色视角重写一条，不可直接抄录世界层文本"，再讲长度。
- file: `automation/prompt_templates/world_extraction.md` → 核心规则第 2 条扩写"世界层边界"，加 boss 复活 / 奇观 / 天灾的正例与"角色 A 暗中给角色 B 设局"的反例；在判定表里把"角色 A 与角色 B 的私下交易"列为反例。
- file: `docs/architecture/schema_reference.md` → 第 149 行 world stage_events 描述、第 316 行 character stage_events 描述同步加上简短归属说明。
- file: `docs/architecture/data_model.md` → 第 214 / 319 行附近的 stage_events 注解同步语义。

## 验证标准

- [ ] 6 份文件均已编辑，描述措辞按计划落地
- [ ] schemas 目录下 `python -m json.tool` 解析两份 schema 通过
- [ ] `jsonschema.Draft7Validator.check_schema` 校验两份 schema 通过
- [ ] grep "stage_events" 复查无 legacy 字样、无相互矛盾的旧描述残留
- [ ] grep 真实书 / 角色 / 剧情名 = 0
- [ ] 整体读一遍：character vs world `stage_events` 的边界规则、归属判定、世界事件如何在角色侧重写——三件事在文档/schema/prompt 三层都说清楚

## 执行偏差

无设计偏差。Review 阶段顺带发现一处旧值漂移（load_strategy.md world
`stage_events` 写 `50–80 chars`，schema 实际 `50–100`），按 dilution
self-check 不属本次 scope，登记到 todo_list 的 `T-LOAD-STRATEGY-WORLD-EVENTS-BOUND`
推迟处理，未在本次 commit 中修。

<!-- POST 阶段填写 -->

## 已落地变更

- `schemas/character/stage_snapshot.schema.json` `stage_events.description`
  重写：补强归属判定（① 角色亲历 / 亲为 / 在场 / 直接影响 ② 他人私事
  不写 ③ 世界事件以**角色视角**重写、不直接复制）。结构、bound 不变。
- `schemas/world/world_stage_snapshot.schema.json` `stage_events.description`
  重写：保留原"仅世界公共层事件"，扩充正例（势力变迁 / 大 boss 复活
  / 奇观 / 地震 / 灵脉断裂 / 跨角色公共战役）+ 反例（私下对话 / 设局
  / 内心决定 / 经济活动）+ 判定准则。结构、bound 不变。
- `automation/prompt_templates/character_snapshot_extraction.md` 第 67
  行所在 bullet 重写：先讲事件归属强约束，再讲世界事件角色视角重写，
  再讲长度。其余 prompt 内容不动。
- `automation/prompt_templates/world_extraction.md`
  - 核心规则第 2 条扩成正例 + 反例并列叙述
  - 「世界层 vs 角色层」判定表追加 2 行：boss 复活 / 出关 / 陨落 ↔
    A 暗中给 B 设局 / 私下交易；天灾（地震 / 洪水 / 规则崩坏）↔ 角色
    单方面的私人计划
- `docs/architecture/schema_reference.md`
  - world 行（L149）补充正例
  - character 行（L316）补充归属判定 + 角色视角重写规则
- `docs/architecture/data_model.md`
  - world `stage_snapshots` 行（L214）补充正负例对比
  - character `stage_snapshots` 行（L319）补充归属判定 + 角色视角重写规则
- `docs/todo_list.md` 新增 `T-LOAD-STRATEGY-WORLD-EVENTS-BOUND` 到讨论中
  段（独立小修，等后续合适时机一并跟进）；索引同步刷新。

## 与计划的差异

无。

PRE 计划的 6 个改动焦点均已落地。额外多出一个 todo_list 条目登记
（review 阶段发现 `simulation/retrieval/load_strategy.md:17` 旧值漂移，
属本次 scope 之外的扫描收益，没有动该文件本身）。

## 验证结果

- [x] 6 份计划内文件全部编辑完成
- [x] `python -c "from jsonschema import Draft7Validator; ..."` 校验
  两份 schema 通过（OK: stage_snapshot.schema.json / OK:
  world_stage_snapshot.schema.json）
- [x] grep "stage_events" 复查无 legacy / 已废弃 / 原为 / formerly /
  renamed from 字样残留
- [x] grep 真实书 / 角色 / 剧情名 = 0（无 我和女帝 / 九世 / 帝姬 / 渡劫
  泄漏；world_extraction.md 中"渡劫 / 战争 / 结丹"是 importance 关键词
  示例，属仙侠题材通用词，按现有约定保留）
- [x] 三层（schema / prompt / architecture docs）边界规则文字一致：
  character = 该角色相关 only；world = 公共层 only；世界事件在角色侧
  以角色视角重写不直接复制

## Completed

- **Status**: DONE
- **Finished**: 2026-04-27 20:52:47 EDT

