# TODO List（待办任务清单）

---

## 文件说明

### 用途

记录**计划完成但尚未完成**的具体工程任务。区别于：
- `ai_context/next_steps.md`：**架构方向**和高层 roadmap（用英文）
- `ai_context/current_status.md`：**当前项目状态快照**
- `docs/logs/`：**历史记录**（时间戳，只追加不修改）
- `docs/architecture/`：**正式架构文档**

本文件是**工程级**的待办队列，含文件路径、行号、改动清单、验证步骤。

### 记录什么

✓ 具体到文件/函数级的改动任务
✓ 每条任务必须包含：**动机**、**改动清单**（含文件路径和行号）、**验证方法**、**预估工作量**、**依赖**、**完成标准**
✓ 讨论中尚未定案的方案及其权衡

### 不记录什么

✗ 架构方向 / 高层 roadmap → 写进 `ai_context/next_steps.md`
✗ 已完成任务 → **完成即删除**（历史价值写进 `docs/logs/` 时间戳日志）
✗ 临时调试笔记 / 中间思考 → 对话上下文或 plan，不持久化
✗ 当前运行状态 / 进度 → 写进 `works/*/analysis/progress/`

### 如何更新 / 删除

**添加任务**：放进合适的分节（立即执行 / 下一步 / 讨论中）。新任务必须有上方"记录什么"列出的全部字段。

**任务进入执行**：不改位置（仍在"立即执行"或"下一步"）；若中途发现需要拆解，原位扩展或增加子任务。

**任务完成**：
1. **立即从本文件删除整条**。不留"已完成"标记、不划删除线、不移到"历史"节——本文件无历史层
2. 若该任务产生了值得沉淀的结论、新架构决策、或可复用经验，写一条 `docs/logs/{YYYY-MM-DD_HHMMSS}_{slug}.md`
3. 若完成涉及 `ai_context/` 的持久事实变化（current_status / decisions / next_steps 等），同步更新
4. **从"下一步"首条提升一条到"立即执行"**，保持 pipeline 不空转；若"下一步"也空则跳过。提升时不改任务内容，仅挪位置

**任务废弃**：写一条 `docs/logs/` 记录废弃原因后从本文件删除；若废弃的是"立即执行"条目，同样触发上述第 4 步的提升。

**讨论转落地**：讨论中章节产生结论时，无论整体定案还是阶段性结论，都要立即把结果反映到对应章节——
- **整体定案**：把条目从"讨论中"整条移到"立即执行"或"下一步"，补全成完整任务（动机/清单/验证/依赖/完成标准）
- **部分定案**：把已定案的子任务单独拆出迁移到对应章节（作为独立任务条目），未定案部分继续留在"讨论中"并更新上下文说明已拆分出去的部分
- **结论颠覆原假设**：若讨论结果反而证明某已在"立即执行/下一步"的任务不再必要，按"任务废弃"流程处理

### 读取时机

- 用户问及待办 / 即将做什么 / 接下来该做什么
- 开始任意改动前 **先查一次**，避免重复规划
- 讨论到可能已登记的话题时
- **默认不主动读取**（不进入 session 启动的 `ai_context/` 读取序列）

---

## 立即执行

### [T-RESUME] Lane 级失败不整体回滚 + `--resume` 按 lane 续跑

**动机**

当前任一 lane 失败 → [orchestrator.py:1316](automation/persona_extraction/orchestrator.py#L1316) 触发 `rollback_to_head`，全仓库 `git reset --hard` + `git clean`，成功的 N-1 lane 产物（可能 ~50m 工作）全部丢弃。下次 `--resume` 必须 N lane 重跑。

**关键约束（用户明确）**

- **不做 lane 之间的文件交叉一致性检查**。lane 间本就独立并行，现有 review 阶段已处理对齐；新加交叉检查会拖慢流程且修复复杂
- 跨 lane 的一致性由 review 阶段兜底，不在 resume 层面防御

**改动清单**

1. **失败时保留成功 lane 产物**
   - 删除 [orchestrator.py:1316](automation/persona_extraction/orchestrator.py#L1316) 的 `rollback_to_head(self.project_root)`
   - 改为：仅清理**失败 lane** 可能残留的半成品文件（根据 lane 写入路径定点删除，不碰其他 lane）
   - 清理的目标文件在失败 lane 类型里固定：
     - `world` → `works/{work_id}/world/stage_snapshots/{stage_id}.json`
     - `char_snapshot:{char}` → `works/{work_id}/characters/{char}/canon/stage_snapshots/{stage_id}.json`
     - `char_support:{char}` → `works/{work_id}/characters/{char}/canon/memory_timeline/{stage_id}.json`（注意 char_support 还可能改 baseline，这块见第 6 点）

2. **StageEntry 增加 `failed_lanes` 字段**
   - 形如 `failed_lanes: [{"lane_type":"char_snapshot","char_id":"王枫","last_error":"exit 1: ...","failed_at":"2026-04-18T10:02:36Z"}]`
   - `StageEntry` dataclass 同步加字段 + `to_dict` / `from_dict` 序列化
   - `phase3_stages.json` schema 向前兼容（缺省 `failed_lanes: []`）

3. **`_extraction_output_exists` → `_missing_lanes`**
   - 位置：[orchestrator.py:375](automation/persona_extraction/orchestrator.py#L375)
   - 现在返回 `bool`，改为返回 `list[LaneKey]`（`LaneKey` 可以是 `tuple[str, str]` 如 `("char_snapshot", "王枫")`）
   - 空列表 → 全部完成，跳过 extraction 步骤
   - 非空 → 作为本次要执行的 lane 集合

4. **重跑入口按 lane 过滤**
   - 改造 [orchestrator.py:1298-1306](automation/persona_extraction/orchestrator.py#L1298-L1306) 的 `ThreadPoolExecutor` submit 循环
   - 只为 `missing_lanes` 里的 lane 提交 future；已完成 lane 直接跳过
   - `n_workers` 同步按 `len(missing_lanes)` 动态计算，不再写死 `1 + 2 * n_chars`

5. **State 流转**
   - Extraction 完全成功 → `failed_lanes = []`，state → `EXTRACTED`
   - Extraction 部分失败 → `failed_lanes` 记录缺失 lane，state → `ERROR`
   - `--resume` 在 `run_extraction_loop` 里把 `ERROR` 重置为 `PENDING` 时，**保留** `failed_lanes`（下一轮 `_missing_lanes` 用它判断哪些 lane 要跑）
   - 注意：`_missing_lanes` 本身走磁盘文件检查，不完全依赖 `failed_lanes`——这两者应该一致，`failed_lanes` 起到"加速判断 + 可观测"作用

6. **char_support 触碰 baseline 的特殊情况**
   - `char_support` 提示词允许修正 baseline（voice_rules / behavior_rules / boundaries / failure_modes）
   - 如果 char_support lane 成功、char_snapshot lane 失败，baseline 已改；重跑 char_snapshot 时会读到新 baseline，行为正确（没问题）
   - 如果 char_support lane 失败、其他 lane 成功，baseline 改动未提交（因为 ThreadPoolExecutor 在同一进程下文件系统可见，但 git 未 commit），清理时**也要回滚 baseline 的 uncommitted 改动**
   - 实现方案：`char_support` lane 失败时，记录失败瞬间 `git diff baseline_paths` 并 `git checkout -- baseline_paths` 恢复；其他 lane 不动
   - 或更激进：规定 `char_support` 只有在全阶段 ready commit 时才落盘 baseline（需要重构 support prompt，先不做）

7. **边界 case**
   - 失败 lane 的半成品 JSON 是空文件 / 部分写入：清理时 `os.remove` 能处理；不存在也 OK
   - 失败 lane 重跑时撞到另一个已存在的"旧" lane 文件（上阶段残留）：不会发生，每阶段 `stage_id` 唯一
   - review 阶段仍应跑完整 5 文件交叉一致性（review 内部已这样）——这块不改

**验证方法**

- 手动 kill：跑到阶段中间对某个 lane PID 发 SIGKILL，验证：
  - 该 lane 的半成品文件被清理，其他 lane 文件保留
  - `phase3_stages.json` stage state 变 `ERROR`，`failed_lanes` 仅列被 kill 的 lane
  - `--resume` 后 `_missing_lanes` 正确识别，只重跑被 kill 的 lane
  - review / post-processing / repair 后续流程仍正常
- 多轮 kill：连续 kill 两个不同 lane，验证 `failed_lanes` 追加正确
- char_support baseline 回滚：特意让 char_support 修改 baseline 再 kill，验证 baseline 恢复到 HEAD

**预估工作量**：200-300 行 Python + 手动测试，约 0.5 天

**依赖**：无（T-LOG 已完成，`failed_lanes/` 日志已可辅助诊断）

**完成标准**

- 手动 kill 单 lane 能触发 per-lane resume
- 真实 exit 1 发生时，只重跑失败 lane
- 成功的 lane 产物不因他 lane 失败而丢失

---

## 下一步

### [T-TOKEN-WATCH] 跨调用 token 累计 + 预启动 budget 检查

**动机**

当前系统没有任何 token 使用监看机制：
- 每次 claude -p 成功调用的 `usage.input_tokens` / `usage.output_tokens` / `total_cost_usd` 只在 LLMResult 里短暂存在（[llm_backend.py:225-228](automation/persona_extraction/llm_backend.py#L225-L228)），**未持久化**
- 无法回答"本 work 提取迄今累计消耗多少 token / USD"
- 无法在启动新阶段前判断"剩余 quota 够不够跑完这个阶段"
- 订阅用户的 5-hour / weekly 限额、API 用户的 TPM 都可能在运行中触达，目前只能等 rate_limit 错误冒出来再处理

**改动清单**

1. **累计 token 使用到 work-local jsonl**
   - 路径：`works/{work_id}/analysis/progress/token_usage.jsonl`（local-only，不 commit）
   - 每条记录一次成功的 claude -p 调用：
     ```json
     {"ts":"2026-04-18T10:02:36Z","stage_id":"阶段02_离开南林","lane":"char_snapshot:王枫","pid":179868,"duration_s":2325,"input_tokens":45823,"output_tokens":12045,"cache_read_tokens":...,"cache_write_tokens":...,"cost_usd":0.3421,"num_turns":8,"session_id":"..."}
     ```
   - 失败调用也记一条（含部分 usage，如果 stdout 可解析到）
   - 写入点：`llm_backend.py` 成功路径的 `LLMResult` 构造后 → 调用新的 `token_usage.append(...)` 工具

2. **新增 `token_usage` 工具模块**
   - 位置：`automation/persona_extraction/token_usage.py`
   - 接口：
     - `append(work_root, record: dict)` — 原子追加一行（flock 防并发写冲突）
     - `summary(work_root, since: datetime | None = None) -> dict` — 汇总区间内的总 token / USD
     - `per_stage(work_root) -> dict[stage_id, summary]` — 按阶段分组

3. **Orchestrator 启动时打印当前累计**
   - 位置：`orchestrator.py` Phase 3 入口
   - 打印形如：
     ```
     Token usage so far: input=12.4M  output=3.1M  cost=$48.21
     Last stage avg: input=230K/lane  output=58K/lane  cost=$0.92/lane
     ```
   - 便于用户直观看消耗速率

4. **阶段启动前的 budget 预检（可选 flag）**
   - CLI flag `--token-budget-usd <N>` 和 `--token-budget-tokens <N>`（二选一）
   - 每进入新阶段前，估算"剩 49-X 个阶段 × 历史阶段平均成本"是否超 budget
   - 超了：打印警告，`--strict-budget` 时直接停机等用户
   - 默认行为不变（无 flag 则不启用预检）

5. **`--show-usage` 命令**
   - `python -m automation.persona_extraction {work_id} --show-usage`（不跑提取，只打印累计）
   - 用于独立查看而无需启动提取

**验证方法**

- 跑一个阶段（或手动触发单次 claude -p 成功调用），检查 `token_usage.jsonl` 有新行
- 并发写冲突测试：并行 5 lane 同时写，确认无行损坏
- `--show-usage` 打印和手工 awk 统计一致

**预估工作量**：150-200 行 Python，2-3 小时

**依赖**：无（T-LOG 已完成并扩展了 `LLMResult`，可直接复用新增字段）

**完成标准**

- 每次成功 claude -p 调用在 `token_usage.jsonl` 留一条
- 运行开始打印累计摘要
- `--show-usage` 可独立查询

---

## 讨论中（未定案）

### [T-RETRY] claude -p 失败的智能重试策略

**上下文**

某次长 lane 跑 38m 后 exit 1，未被 `run_with_retry` 重试。用户提问：短时间内 exit 是否可以重试或退避？T-LOG 完成后，长时失败现在可见 `subtype` / `num_turns`，重试决策可基于实际信号。

**现有机制**（[llm_backend.py:335-372 `run_with_retry`](automation/persona_extraction/llm_backend.py#L335-L372)）

| 错误类型 | 识别 | 处理 |
|---|---|---|
| `fast_empty_failure` | duration < 5s + stderr 空 + exit N | 重试 3 次（30s → 60s → 120s） |
| `rate_limit` | stderr 含 "rate limit" / "too many requests" | 重试 3 次（60s → 120s → 180s） |
| `token_limit` | stderr 含 "context window" / "max_tokens" 等 | **不重试** |
| 通用长时 exit N | stderr 空 + duration 长 | **不重试** |

**待决策项**

1. **短时间阈值扩大？** 当前 5s 过严。char_snapshot 正常 10-20m，任何 <60s（或 <120s）失败都不是真正工作后失败，更可能是 CLI launch 错误或 API 连接失败。候选阈值：60s 或 120s。
   - 支持扩大：风险小（<2 分钟浪费），覆盖面更广
   - 反对扩大：仍在盲猜，不如等 T-LOG 完成后按 subtype 分流
2. **长时 exit 是否也重试一次？** 本次阶段 02 属此类。
   - 代价：再跑 40m；若也失败总计浪费 ~80m
   - 收益：若是瞬态错误能自愈
   - 观点：**等 T-LOG 完成，根据 stdout subtype 分类**：
     - `error_max_turns` → 不重试（同 prompt 同样触达）
     - `error_during_execution` → 重试 1 次（瞬态可能性大）
     - 无 subtype / 解析失败 → 可选重试 1 次
3. **退避策略** 暂无调整需求，现有 30s/60s/120s 合理

**未落地原因**

- T-LOG 已完成，stdout/subtype 可见——盲猜问题已解除
- 尚未收集足够的真实失败样本来验证不同 subtype 的重试收益

**争议**

- 短时阈值是否一次扩大到 60s？风险小；可独立先行
- 长时 exit 按 subtype 分流是否一步到位？待收集几次真实失败后决定
- 结论：**待定案**，需要几次真实失败样本佐证

**依赖**：T-LOG 已完成；可基于 `failed_lanes/` 日志样本决策

---
