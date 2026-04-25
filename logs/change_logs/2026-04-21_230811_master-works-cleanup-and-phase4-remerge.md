# 2026-04-21 master 分支 works/ 清理 + Phase 4 scene_archive 重 merge

## 背景

stage_id 英文化（`1573506` refactor + `9cce39f` / `e7e2a20` 补齐）之后排查受影响的已生成产物时，发现两件事需要一并处理：

1. **分支纪律偏离**：`works/我和女帝的九世孽缘/` 下 25 个 baseline / analysis 产物（Phase 1 + Phase 2.5 输出）同时存在于 `master` 和 `extraction/我和女帝的九世孽缘` 分支。按 `ai_context/decisions.md` §26 / `conventions.md` §Git，extraction-data commits 应**只**活在 extraction 分支；master 只承载代码 / schema / prompt / docs / ai_context。
2. **Phase 4 scene_archive.jsonl 残留旧 stage_id**：1591 条场景里 `scene_id` 已是新 `SC-S###-##`（代码按序号算），但 `stage_id` 字段仍是旧中文 `阶段NN_xxx` —— 因为 Phase 4 合并在英文化之前跑的。

## 处理 1：master 清理 extraction 数据

在 `/tmp/persona-master` worktree 执行：

```
git rm -r "works/我和女帝的九世孽缘/"
```

删除 25 个 tracked 文件：

- `analysis/`：candidate_characters.json / stage_plan.json / world_overview.json
- `characters/{姜寒汐,王枫}/canon/`：behavior_rules / boundaries / failure_modes / identity / memory_digest / stage_catalog / voice_rules
- `characters/{姜寒汐,王枫}/manifest.json`
- `manifest.json`
- `world/foundation/{fixed_relationships,foundation}.json`
- `world/{manifest,stage_catalog}.json` + `world/world_event_digest.jsonl`

这些在 extraction 分支上继续保留（通过下一步的 merge 时 `git checkout HEAD --` 恢复）。

**未处理**：`sources/works/我和女帝的九世孽缘/manifest.json` 是人工 ingestion 产物（非 LLM 输出，validator-gated），按指示仅清 `works/`，`sources/` 保持不动。

## 处理 2：extraction 分支 merge master 并恢复 works/

在主 worktree（extraction 分支）执行：

```
git merge master --no-commit --no-ff
# 此时 index 上 works/我和女帝的九世孽缘/ 被标记为删除
git checkout HEAD -- "works/我和女帝的九世孽缘/"
git commit -m "Merge master: strip works data from master (extraction-only)"
```

合并结果：master 的代码改动进入 extraction；`works/我和女帝的九世孽缘/` 在 extraction 侧保留全部 25 个文件。

## 处理 3：Phase 3 stale 进度 + Phase 4 scene_archive 重 merge

在 extraction 分支（主 worktree）：

```
rm "works/我和女帝的九世孽缘/analysis/progress/phase3_stages.json"
python -m automation.persona_extraction "我和女帝的九世孽缘" --start-phase 4
```

- `phase3_stages.json`：本地文件（非 tracked），49 条全 pending + 旧中文 stage_id + 缺 `stage_title`。下次 `--resume` 走 `orchestrator.py:1915-1940` 自愈路径，从 `stage_plan.json` 重建 49 条 pending（带新 `stage_title`）。
- `--start-phase 4`：537/537 scene_splits 已 passed，进入 merge-only 分支，0 LLM 调用。`merge_scene_archive()` 以 `stage_plan.json` 为唯一 stage_id 来源覆写 `retrieval/scene_archive.jsonl`（也是本地文件）。

## 不需要 LLM 回滚

stage_id 英文化的三个 commit（`1573506` / `9cce39f` / `e7e2a20`）里所有数据迁移都是字符串替换，无 LLM 参与。Phase 0/1/2.5 的 tracked 产物已经在 refactor commit 中同步；其余 baseline（voice_rules / behavior_rules / boundaries / 角色 manifest）本身不引用 stage_id，天然对齐。Phase 3 已在 `8e407be` 提前清空。所以整个链路唯一需要数据层动作的就是 Phase 4 scene_archive —— 而它是 stage_plan 的纯派生产物，代码重 merge 即可。

## 分支纪律后续

今后 master 应始终保持不含任何 `works/<work_id>/` 下的 extraction 产物。orchestrator 已有 try/finally checkout_master + SessionStart hook 双保险；这次清理把历史遗留拉回约定状态。
