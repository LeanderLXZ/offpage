# 当前提取状态

## 作品

- `work_id`: `我和女帝的九世孽缘`
- 书名：`我和女帝的九世孽缘`
- 最后更新：`2026-04-02T03:42:11-0400`

## 续跑入口

后续任何 world / character / planning 类抽取任务，默认先读本文件，再读对应的 batch plan / progress 文件，不要默认从头开始。

推荐读取顺序：

1. `analysis/incremental/extraction_status.md`
2. 与当前任务直接对应的 progress 文件
3. `source_batch_plan.md`
4. `indexes/load_profiles.json`
5. 已有 world / character canon
6. 只读取本批真正需要的章节

## source 规划状态

- `source_batch_plan.md`：已建立
- 规划规则：默认 `10` 章一批，`batch_N -> 阶段N`，阶段抽取累计到 `1..N`
- 当前推荐下一个 source batch：`batch_002`（`0011-0020`）

## world 提取状态

- 当前状态：已开始
- 最近完成：
  - `batch_id`: `batch_001`
  - 章节范围：`0001-0010`
  - 阶段候选：`阶段1_南林初遇`
- 已生成：
  - `world/manifest.json`
  - `world/stage_catalog.json`
  - `world/stage_snapshots/阶段1_南林初遇.json`
  - 首批 `foundation / history / events / locations / factions / cast / social/stage_relationships`
- 当前下一步：
  - `next_batch_id`: `batch_002`
  - `next_batch_range`: `0011-0020`
  - 目标：确认柳村 / 南林危机是否阶段性收束，并把阶段 `2` 的当前状态与历史事件继续拆开落盘

## character 提取状态

- 当前状态：未开始正式角色包抽取
- 候选角色识别：已完成初版
- 当前候选入口：
  - `candidate_characters_initial.md`
- 推荐后续顺序：
  1. 姜寒汐
  2. 王枫
  3. 萧浩
  4. 楚妍儿

## 当前证据引用约定

- work-scoped JSON 里的 `evidence_refs` 默认使用紧凑章节引用，而不是完整路径。
- 推荐写法：
  - `0001`
  - `0004`
  - `0011-0013`
- 默认可按以下规则还原为原文路径：
  - `sources/works/{work_id}/chapters/{chapter_id}.txt`
- 只有当证据来自：
  - 非章节文件
  - 当前作品之外的文件
  - 或路径本身需要保留
  时，才优先使用完整路径。

## 当前加载策略入口

- work-level 启动 / 按需加载规则：
  - `indexes/load_profiles.json`
- 默认运行时策略：
  - 启动只加载当前 stage 的必要摘要
  - 历史关系、旧阶段、事件细节、角色记忆与原文章节全部按需补读

## 更新规则

- 每次 world / character / source planning 有实质进度推进时，都应同步更新本文件。
- 如果只是 work-local 进度变化，默认不需要同步更新 `ai_context/` 或 `docs/logs/`。

## 当前 world 精简规则

- `world/` 不再单独维护：
  - `mysteries/`
  - `knowledge/character_event_awareness/`
- 角色相关的详细认知、记忆与误解，应主要进入：
  - `characters/{character_id}/`
  - `world/cast/` 的简要角色视图
- 角色关系改为按阶段存储在：
  - `world/social/stage_relationships/{stage_id}.json`
- 运行时默认加载当前所选阶段对应的关系文件，不默认加载整段历史关系。
