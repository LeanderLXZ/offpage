# T-RESUME：Lane 级失败与 SIGKILL 可恢复

## 背景

Phase 3 每个 stage 并发 1+2N 个 lane（1 world + N char_snapshot + N
char_support）。改动前的行为：

- 任一 lane 失败 → `rollback_to_head()` 整仓 `git reset --hard` +
  `git clean`，已成功的 N-1 个 lane 产物全部丢失
- EXTRACTING 中 SIGKILL / 断电 → 同样 `rollback_to_head` + 强制
  PENDING，下次 `--resume` 必须 1+2N 全部重跑

对 50+ 阶段的 work，单 lane 失败重跑整个 stage 意味着：重复生成已成功
lane 产物 + 烧额外 LLM token。前置 T-LOG（`failed_lanes/` 日志）已
提供 lane 级失败诊断，但 resume 仍是 stage 级。

## 目标

**Lane 粒度的 resume**：`--resume` 只重跑「未确认完成」或产物文件损坏
的 lane，保留其它已确认完成的 lane 产物。失败保留磁盘产物，不再 reset。

## 核心决策

- **Lane complete 判据**：lane_states[name] == "complete" 当且仅当
  子进程退出 0 且 per-stage 产物文件 `json.loads` 成功。纯 JSON 校验
  零 LLM 成本，作为文件腐败的 belt-and-suspenders。
- **SIGKILL 与半截文件**：lane_states 的 complete 迁移发生在子进程
  正常退出**之后**；SIGKILL → 状态迁移未发生 → resume 识别为需重跑。
  `phase3_stages.json` 用 `tempfile + fsync + os.replace` 原子写，
  SIGKILL 中途主文件不会坏。
- **char_support baseline 保护**：char_support lane 除写 memory_timeline
  per-stage 产物外，还累积修改 5 个 baseline 文件（identity /
  voice_rules / behavior_rules / boundaries / failure_modes）。
  partial write 污染 baseline 后影响后续 stage。resume 时若
  support:{c} 未标 complete，先 `git checkout HEAD -- <5 baseline>`
  再重跑；未在 HEAD 则 unlink。
- **不做 lane 间交叉一致性检查**：这项由 review 阶段兜底，不在 resume
  层防御。跨 lane 一致性是 review 的职责。

## 代码改动

### 新增 `automation/persona_extraction/lane_output.py`

- 常量：`WORLD_LANE`、`SNAPSHOT_PREFIX`、`SUPPORT_PREFIX`、
  `BASELINE_FILENAMES`（5 个）
- `expected_lane_names(chars)` → `["world", "snapshot:{c}",
  "support:{c}", ...]`
- `lane_product_path(work_root, stage_id, lane_name)` → Path
- `baseline_paths(work_root, char_id)` → 5 个 Path
- `verify_lane_output(work_root, stage_id, lane_name) -> (bool, str)`
  —— 存在性 + JSON 解析检查
- `expected_lane_dirty_paths(...)` —— preflight 的 ignore_patterns
  候选（3 个 per-stage 产物 + 5 个 baseline/char）

### `automation/persona_extraction/progress.py`

- 新增 `_is_parseable_json(path)`、`_atomic_write_json(path, data)`
- `StageEntry.lane_states: dict[str, str]`（`field(default_factory=dict)`）
  + helpers：`mark_lane_complete` / `is_lane_complete` / `reset_lane`
  / `clear_lane_states` / `expected_lane_names` / `all_lanes_complete`
  / `missing_lanes`
- `to_dict` / `from_dict` 同步；`from_dict` 对缺 `lane_states`
  的旧记录返回 `{}`，向后兼容
- 三个 `save()` 方法改用 `_atomic_write_json`
- `reconcile_with_disk` 重写为 lane-aware：对每个 `lane_states`
  entry 跑 `verify_lane_output`；坏的 → `reset_lane()` + `unlink()`；
  后续 orphan-cleanup 循环用 `p not in claimed_paths and p.exists()`
  双重守卫避免 double-unlink

### `automation/persona_extraction/git_utils.py`

- 新增 `reset_paths(project_root, paths)`：对每个 path
  `git cat-file -e HEAD:<rel>` 探测 tracking 状态；tracked →
  `git checkout HEAD -- <rel>`；untracked → `unlink()` if exists
- **删除** `rollback_to_head()` 和 `ROLLBACK_CLEAN_EXCLUDES`（无调用方）

### `automation/persona_extraction/orchestrator.py`

- Imports：移除 `rollback_to_head`，新增 `reset_paths`、所有
  `lane_output` helpers
- `_extraction_output_exists`：改为调用 `verify_lane_output` 聚合
  （现在也校验 JSON parse）
- `_process_stage` 新增 `_verify_lane(lane_name, result)` 内部闭包：
  成功分支先跑 `verify_lane_output`，校验失败则改写为 lane 失败并
  复用 T-LOG 日志流程
- 三个 `_extract_*` 闭包 return 前调用 `_verify_lane`
- 新增 `_lane_key(proc_type, proc_id)` 映射 orchestrator 内部
  tuple → lane_states 字符串键
- EXTRACTING resume 路径：**移除** `rollback_to_head`，改为
  `force_reset_to_pending`（保留 lane_states）
- PENDING 分支：先 `reconcile_with_disk` 对账 lane_states；
  `is_partial_resume = bool(stage.lane_states)` 时把
  `expected_lane_dirty_paths` 并入 preflight `ignore_patterns`；
  smart-skip 自动 backfill lane_states（向后兼容旧记录）；
  `missing_lanes` 驱动 ThreadPoolExecutor；support lane 进执行前
  先 `reset_paths(baseline_paths(...))`
- 主线程 `as_completed` 循环集中 `mark_lane_complete` +
  `phase3.save`——串行执行，无竞态，无需锁
- 失败判定用 `all_lanes_complete` 替代错误列表；失败时仍进 ERROR，
  **但不回滚**；lane_states 保留，下次 `--resume` 续跑
- REVIEWING 无产物安全网：原先 `rollback_to_head` 改为
  `clear_lane_states`（stage 向前推进到 POST_PROCESSING 的同时清状态）

## 文档改动

- `docs/requirements.md` §11.2 / §11.5 / §12.9：lane-level resume 段
  + 失败场景矩阵 + atomic write 说明；`phase3_stages.json` schema
  文档里加 `lane_states`
- `docs/architecture/extraction_workflow.md` §6.5：新增 Lane 级 resume
  小节（7 步骤 resume 流程、完成标准、atomic write）；Phase 4 章节
  去掉「Phase 3 的 repo-wide rollback 不会清掉它们」（Phase 3 不再
  rollback）
- `ai_context/current_status.md`：T-RESUME 新 bullet（lane_states /
  atomic write / scoped baseline reset / lane-aware reconcile）；
  移除旧的「any missing lane re-runs the full extraction」描述
- `ai_context/architecture.md`：Key Design 「Smart resume」重写为
  lane-level；Phase 4 描述去掉「preserved from Phase 3 rollback」
- `automation/README.md`：去掉「Phase 3 的 rollback 不会清掉它们」
- `docs/todo_list.md`：删除 T-RESUME 条目（已完成）；T-TOKEN-WATCH
  从「下一步」提升到「立即执行」

## 失败场景覆盖

| 场景 | 改后行为 |
|------|---------|
| 某 lane `run_with_retry` 重试耗尽 | 已成功 lane 的 lane_states=complete 保留；失败 lane 无状态；stage → ERROR |
| 子进程 exit 0 但产物非 JSON | `_verify_lane` 改写为 lane 失败 → 按上条处理；T-LOG 记录原因 |
| SIGKILL / 断电 EXTRACTING 中 | state 留 EXTRACTING，lane_states 保留；resume 降为 PENDING 走 partial-resume |
| SIGKILL 发生在 phase3.save 写盘瞬间 | atomic write（temp + fsync + rename）主文件不坏；最坏 case 丢最后一次 complete 标记 → resume 重跑一个已成功 lane（幂等） |
| post-processing / repair FAIL | 原本就保留产物 + lane_states 全 complete，resume 从 EXTRACTED/REVIEWING 继续，不碰 lane 层 |

## 验证

- `progress.StageEntry` lane_states 序列化 round-trip + 旧 JSON 加载
  为 `{}`
- `verify_lane_output`：missing / invalid-JSON / valid 三类 √
- `reset_paths`：tracked / untracked / nonexistent / 嵌套 baseline √
- 原子写：tempfile 中途 kill 主文件保留完好 √
- `reconcile_with_disk`：保留合法 + 丢弃腐败 + 清理 orphan √

## 风险与未覆盖项

- 并发锁粒度：phase3.save 在主线程 `as_completed` 里串行，不需要锁；
  lane 闭包不 save
- baseline 非-git-tracked case：已处理（`cat-file -e HEAD:` 探测后
  走 unlink fallback）
- `--end-stage`、Phase 3.5、squash-merge：未触碰
- `run_with_retry` / repair_agent 语义：未触碰
- T-RETRY（按 subtype 分流重试策略）：仍在「讨论中」，本次不动
