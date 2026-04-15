# Progress 文件与磁盘产物自愈对账

## 背景

之前的进度文件加载是单向的：从磁盘读 JSON 反序列化成内存对象，假定状态字段
即真理。实际场景里这个假定经常失效：

- 用户手动 `rm` 中间产物后再 `--resume`：进度还说 done，但文件没了
- 中间状态（EXTRACTING / SPLITTING）写到一半被 `Ctrl+C`：磁盘上有半个 JSON
- `git reset --hard` 回退到旧 commit：phase3_stages.json 里的 `committed_sha`
  指向不存在的 git 对象
- Orchestrator 之外的人手动塞了一份 stage_snapshot：进度仍是 PENDING，但
  下次跑会被覆盖或被当成"已完成"

之前只有 Phase 4 有一个 `verify_passed()` 局部检查 PASSED 状态，覆盖窄。
Phase 0 仅在迭代到每个 chunk 时双重判定文件存在；Phase 3 几乎无对账。

## 设计

每个 Progress 类加 `reconcile_with_disk(project_root, ...)`，在 `load()` 之后
统一调用。统一规则：

| 内存状态 | 磁盘状态 | 动作 |
|----------|----------|------|
| 终态（done / committed / passed） | 缺产物 | 回退 PENDING，清重试计数 |
| PENDING | 有产物 | 删除产物（不可信的半成品） |
| 任意中间态 | 任意 | 删除产物，回退 PENDING |

**Phase 3 额外**：终态（COMMITTED）还要 `git cat-file -e <sha>` 校验
`committed_sha` 是否仍在仓库里。reset/rebase 丢掉的 commit 视同产物缺失，
强制回退 PENDING。

## 实现

`automation/persona_extraction/progress.py`:
- 新增 `_git_object_exists(project_root, sha)` 工具函数
- `Phase0Progress.reconcile_with_disk()` — chunk 级
- `Phase3Progress.reconcile_with_disk(project_root, target_characters)` —
  stage 级；扫 world stage_snapshot + 每个目标角色的 stage_snapshot +
  memory_timeline 三类 per-stage 文件。累积型文件（memory_digest.jsonl /
  world_event_digest.jsonl / *_catalog.json）无法 per-stage 校验，跳过。
- 新增 `Phase3Progress._stage_artifact_paths()` 静态方法集中维护期望产物清单

`automation/persona_extraction/scene_archive.py`:
- `verify_passed()` → `reconcile_with_disk()` 通用化，覆盖所有状态
- 调用点 [scene_archive.py:702-707] 每次启动都跑（不只 --resume）

`automation/persona_extraction/orchestrator.py`:
- Phase 0 入口 [orchestrator.py:431-446]：load 后立即对账
- Phase 3 入口 [orchestrator.py:1469-1500]：load 后立即对账。同时新增
  **自愈逻辑**：若 `pipeline.is_done("phase_2")` 且 `phase3_stages.json`
  缺失或损坏，从 `stage_plan.json` 重建（49 个 stage 全 pending），
  避免落到 fresh-start 路径重新提示选角色 + 覆写 pipeline.json

## 测试

`python3 -c` 跑了三套 in-memory 用例：

- Phase 0：done+缺文件 → revert；pending+有文件 → purge
- Phase 4：PASSED+缺文件 → revert；SPLITTING+有文件 → purge+revert
- Phase 3：COMMITTED+缺产物 → revert；COMMITTED+全产物+假 sha →
  revert（committed_sha 清空，产物删光）；PENDING+残留 → purge；
  EXTRACTING+残留 → revert+purge

全部 PASS。

## 不在范围

- Phase 1/2/2.5 没有自己的 progress 文件（状态走 pipeline.json + 磁盘
  产物全有/全无），不接入对账
- 累积型 jsonl/catalog 文件无法 per-stage 校验，需要其他机制（如重跑时
  整体重建）；本次保持原样
