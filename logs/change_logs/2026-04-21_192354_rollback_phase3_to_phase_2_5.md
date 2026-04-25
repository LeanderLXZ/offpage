# 2026-04-21 19:23 EDT — rollback phase 3 → phase 2.5

## 起因

2026-04-21 Phase 3 stage 01 最后一次以 `T3_CORRUPTED` FAIL（详见
`2026-04-21_191403_coverage-shortage-accept.md`）。代码已随
`coverage_shortage` accept_with_notes 补丁更新（commits
`8e6a870 / 068fad4 / 993c281`），但 stage 01 的产物（世界 + 两位角色的
snapshots / memory_timeline / digest / stage_catalog 里已登记的条目）
仍然是失败前的残留，且工作区里还有 T3_CORRUPTED 带来的脏修改。

为配合下一轮 `--resume` 从干净的 phase 2.5 状态重跑 stage 01，需把所有
stage 01 的产物整体回滚掉。代码 / schema / ai_context / docs / prompts
一律不动。

## 改动概要

- `git rm` 5 份 `阶段01_南林初遇.json`：
  - `world/stage_snapshots/`
  - `characters/姜寒汐/canon/stage_snapshots/`
  - `characters/王枫/canon/stage_snapshots/`
  - `characters/姜寒汐/canon/memory_timeline/`
  - `characters/王枫/canon/memory_timeline/`
- truncate 3 份 jsonl 到 0 字节（仍 tracked）：
  - `world/world_event_digest.jsonl`
  - `characters/姜寒汐/canon/memory_digest.jsonl`
  - `characters/王枫/canon/memory_digest.jsonl`
- 清空 3 份 `stage_catalog.json` 的 `stages` 数组：
  - `world/stage_catalog.json`
  - `characters/姜寒汐/canon/stage_catalog.json`
  - `characters/王枫/canon/stage_catalog.json`
- `works/.../analysis/progress/phase3_stages.json` 49 个条目一次性复位
  （本地进度文件，非 tracked）：
  - `state` → `pending`
  - `last_reviewer_feedback` / `committed_sha` / `error_message` 清空
  - 丢掉 `lane_states` / `product_paths`（若存在）
  - 原子写入（tempfile + fsync + replace）

## 未动

- 代码 / schema / prompt / ai_context / docs：全部保留（含本轮
  coverage_shortage 补丁）
- Phase 0/1/2/2.5/4 所有产物：保留
- 两位角色的 `identity` / `voice_rules` / `behavior_rules` / `boundaries`
  / `failure_modes`（Phase 2 / 2.5 baseline）：保留
- `.claude/settings.json` 的本地脏修改：非本次回滚范围，留给用户自行处置

## 预期效果

- 仓库回到 Phase 2.5 结束状态；下一次 `--resume` 从 stage 01 开始重跑
- 新 repair agent 路径（L2 `min_examples` → `coverage_shortage` triage）
  在重跑中生效，之前 16 次 T3_CORRUPTED 的失败模式不再出现

## 校验

- `git status` 干净（除 `.claude/settings.json` 明示保留项）
- `phase3_stages.json`：49 个条目 state 全部为 `pending`
- 3 份 digest jsonl 字节数 = 0
- 3 份 stage_catalog.json 的 `stages` 数组为 `[]`
- 5 份 `阶段01_南林初遇.json` 已从 index + working tree 移除
