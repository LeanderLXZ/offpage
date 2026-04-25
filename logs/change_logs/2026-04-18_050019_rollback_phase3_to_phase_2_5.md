# 回滚 Phase 3 → Phase 2.5 结束状态，同步 master 最新代码

## 动机

阶段02 离开<location_a>在 repair agent 修复后仍有 3 条语义错误未能消除（<character_a>
memory_timeline 中过早使用"<character_b>"之名；<character_b> stage_snapshot 中 voice_state
台词归属错位 2 处）。决定放弃当前 Phase 3 全部产物，回到 Phase 2.5 结束
点重新开始，顺带把 extraction 分支与 master 已有但尚未合入的代码/架构
改动对齐。

## 改动

### Master
- 新增 `CLAUDE.md`（session entry point 指针文件，内容指向
  `ai_context/` 阅读顺序），提交 `930c715 chore: add CLAUDE.md entry point`

### extraction/<work_id>
1. 清理工作区：丢弃阶段02 修改过的 tracked 文件
   （<character_a>/<character_b> 的 `identity.json` / `memory_digest.jsonl` /
   `stage_catalog.json`，以及 world `stage_catalog.json` /
   `world_event_digest.jsonl`）；删除未跟踪的阶段02 产物
   （两个角色的 `stage_snapshots/阶段02_离开<location_a>.json` +
   `memory_timeline/阶段02_离开<location_a>.json`，以及
   `world/stage_snapshots/阶段02_离开<location_a>.json`）。
2. `git reset --hard d62aed8`（"Phase 2.5 结束，尚未开始 Phase 3"的提交）。
   丢弃 stage 01 数据提交 `f06336c`、以及其后的两个 master merge
   `8afb87c` / `80e2fea`（代码改动都将在下一步的 merge 里重新拿到）。
3. `git merge master --no-ff` → 拿回所有 master 独有的代码/架构：
   - `930c715 chore: add CLAUDE.md entry point`
   - `8f0de8e fix(repair-agent): triage 审计加固`
   - `eb03179 feat(repair-agent): 源文件问题 triage + accept_with_notes`
   - `8afb87c fix(repair-agent): Phase B L3 gate + T3 全局每文件上限`
4. 进度文件修正（`works/*/analysis/progress/` 位于 `.gitignore`）：
   - `pipeline.json`：`phase_3` 由 `pending` 保持；`last_updated` 更新
     到 `2026-04-18T09:00:19+00:00`；`phase_0/1/2/2_5/4` 保持 `done`
   - `phase3_stages.json`：阶段01（原 `committed`，sha `f06336c`）与
     阶段02（原 `error`，带详细 error_message）双双重置为 `pending`，
     清 `committed_sha` / `error_message` / `last_updated`

## 保留

- Phase 0/1/2/2.5 git-tracked 产物：`analysis/` 三件套、两个角色
  `identity.json` + `manifest.json` + 4 份 skeleton baseline +
  `stage_catalog.json`、`world/foundation/` 下 `foundation.json` +
  `fixed_relationships.json` + 空 `stage_catalog.json`
- Phase 4 本地产物 `works/*/retrieval/scene_archive.jsonl`（4.3 MB）
  及 `works/*/analysis/scene_splits/` —— Phase 4 只依赖 Phase 1
  `stage_plan.json`，在 stage_plan 未改变前仍然有效；pipeline 保持
  `phase_4: done`
- Phase 0 产物 `chapter_summaries/` + `phase0_summaries.json`
- extraction.log 历史保留（append-only）

## 验证

- `git ls-tree -r HEAD -- works/.../` 无 `stage_snapshots` / `memory_timeline`
  / `memory_digest` / `world_event_digest` 条目
- `git status --short` 干净
- `git log --oneline -3` → `2838ad3 merge(master): 同步代码/架构到最新
  + 重置 Phase 3 重新开始` / `930c715` / `8f0de8e`

## 后续

```bash
python -m automation.persona_extraction "<work_id>" --resume
```

将从阶段01 <location_a>初遇 开始重新抽取。smart resume 会检查磁盘上是否存在
1+2N 产物，全部缺失 → 正常重跑 LLM 抽取。Phase 4 不会重做。

## 影响范围

- 代码/架构：无（仅把 master 已有改动合并到 extraction）
- 数据：Phase 3 全部产物清空（阶段01 已提交的一份 + 阶段02 WIP）
- ai_context：无更新（Phase 2.5 done / Phase 3 pending / Phase 4 done
  的口径与 `current_status.md` 当前描述一致）
