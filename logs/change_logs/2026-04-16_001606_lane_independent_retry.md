# Lane-Independent Retry + 极端场景回滚

## 背景

Phase 3 提取循环原本在任何 review lane FAIL 时都会触发**全阶段回滚**
（`git reset --hard HEAD` + stage-level retry）。该策略有两个问题：

- **成本不对称**：4 个 lane（world + 3 character）并行提取，只要 1 个
  character lane 的语义审校未过，就把已 PASS 的 world + 其它 character
  的结果一起丢弃，浪费约 3N 倍的 LLM token
- **误伤语义**：大部分语义审校失败属于"该 lane 可在本地修复"范畴
  （例如角色 A 的 target_voice_map 示例不够），不需要整阶段重来

目标：**通道级独立重试，只有在所有通道内修复手段都失败时才全阶段回滚。**

## 新架构

### 失败分级（三层）

1. **通道内可修复（Level 0 / 1 / 2 / 3 targeted fix）**
   schema autofix → 程序校验 → 定向 LLM 修复。全部发生在
   `review_lanes.py` 内，该 lane 的输出被就地重写。不动 state、不动
   `lane_retries` 计数。

2. **通道内不可修复（lane 重试）**
   整个 lane 的"修复瀑布"走完仍 FAIL（系统性问题：理解偏差、文件丢失、
   结构性漏洞）。此时：
   - 回滚**仅该 lane 的磁盘产物**（`rollback_lane_files`）
   - 自增 `stage.lane_retries[lane_key]`
   - 仅重跑这些 lane 的提取（`ThreadPoolExecutor`，并行）
   - 重跑后**重新审校全部 lane**（跨 lane 依赖：world reviewer 会读
     character 的 memory_timeline，character reviewer 会读 world
     snapshot，之前通过的 lane 判定可能被新数据改写）
   - 上限：`lane_max_retries = 2`

3. **lane 重试耗尽（最极端情况 → 全阶段回滚）**
   有任一 lane 的 `used >= lane_max_retries` 仍未 PASS。此时：
   - `rollback_to_head()` 整阶段回滚
   - 清空 `stage.lane_retries = {}`
   - 聚合所有失败 lane 的反馈写入 `stage.last_reviewer_feedback`
   - `transition(FAILED)` 进入 stage-level 重试
   - stage-level 上限 `max_retries = 2`

最坏情况（2 × 2 = 4）一个阶段总共可尝试 5 组合：原提取 + 2 次 lane
重试 + 2 次 stage 重试。

### Idempotent 后处理

lane 重跑后需要重新生成 digest / catalog。`run_stage_post_processing`
早已按"仅重写当前 stage 条目"的语义写入，设计成 upsert：

- `generate_memory_digest`：只加载当前 stage 的 `memory_timeline`，覆盖
  digest 中该 stage 的条目
- `generate_world_event_digest`：同上
- `upsert_stage_catalog`：幂等

因此 lane 重跑后直接再调用一次即可，不需要额外路径。

## 改动范围

### 数据结构（`progress.py`）

- `StageEntry` 新增两个字段：
  - `lane_retries: dict[str, int]` — lane_key → 已用次数。key 由
    `review_lanes.lane_key(lane_type, lane_id)` 生成
    （`"world"` / `"character:{char_id}"`）
  - `lane_max_retries: int = 2`
- `to_dict()` / `from_dict()` 序列化；`from_dict` 对旧文件给
  默认值（空 dict / 2），保持向后兼容
- `reconcile_with_disk()` 两条还原路径都清空 `lane_retries`（COMMITTED
  对象丢失 → revert PENDING；中间态 → purge + revert）

### Lane 工具（`review_lanes.py`）

- `lane_key(lane_type, lane_id)` — 约定 world 退化为 `"world"`（固定单
  一 lane），character 拼 `"character:{id}"`
- `rollback_lane_files(project_root, work_id, stage_id, lane_type,
  lane_char)` — 只删除本 lane 的磁盘产物：
  - world lane：`world/stage_snapshots/{stage_id}.json`
  - character lane：`characters/{id}/canon/stage_snapshots/{stage_id}.json`
    + `characters/{id}/canon/memory_timeline/{stage_id}.json`
- `run_parallel_review` 新增可选参数 `lane_filter: list[str] | None`
  （保留以备将来优化；当前由于跨 lane reviewer 依赖，调用方不使用它，
  每轮审校全部 lane）

### 编排（`orchestrator.py`）

- `_extract_world` / `_extract_character` 闭包上提到 `_process_stage`
  开头（原来嵌套在 `if state in (PENDING, RETRYING)` 分支内，Step 4
  retry loop 不可见）
- Step 4 改为 `while True:` 审校循环：
  1. `run_parallel_review` 一次
  2. 全 PASS → `break`
  3. 否则按 `used < lane_max_retries` 划分 retriable / exhausted
  4. `exhausted` 非空 → 聚合反馈、全阶段回滚、清空 `lane_retries`、
     transition FAILED、`return`
  5. 全部 retriable → 自增计数、`rollback_lane_files`、并行重跑提取、
     重跑 `run_stage_post_processing`、回到步骤 1
- 提取失败（`retry_extraction_errors` 非空）作为意外按全阶段回滚兜底
- Step 4 成功退出后，打印本阶段用掉的 lane 重试并清空计数
- `--resume` 的"blocked stage 自动重置"路径额外清空
  `lane_retries = {}` 与 `last_reviewer_feedback = ""`（与
  `retry_count = 0` / `error_message = ""` 保持一致）

### 需求与架构文档

- `docs/requirements.md` §11.4b 新增"通道级独立重试"小节，描述三层
  失败分级、`lane_max_retries=2`、跨 lane 依赖不可跳过重审、极端场景
  才全阶段回滚、幂等后处理
- `docs/architecture/extraction_workflow.md` 阶段流程图加入 lane FAIL
  / lane 重试耗尽两条分支
- `automation/README.md` 失败处理说明改为三层描述
- `ai_context/requirements.md` §11 review lanes 段更新
- `ai_context/current_status.md` 新增 Lane-independent retry 段落
- `ai_context/architecture.md` 扩写 "Lane FAIL" 行为描述
- `ai_context/decisions.md` 25b / 25c 以 lane-retry-first 表述重写

## 向后兼容

- 旧 `phase3_stages.json` 读入时 `lane_retries` 自动填空 dict、
  `lane_max_retries` 自动填 2
- `rollback_lane_files` 对不存在的文件安全（`if p.exists(): p.unlink()`），
  不会因中断状态的部分产物报错
- 跨 lane reviewer 依赖没有改动；只是把"重审一次"扩展为"lane 重跑后重
  审"，PASS 语义不变

## 轻量测试

- `python -c "from persona_extraction import orchestrator,
  progress, review_lanes"` 全部导入成功
- `StageEntry` 序列化往返（含 `lane_retries` 填值）
- 旧格式反序列化（无 `lane_retries` / `lane_max_retries` 字段）默认
  值正确
- `lane_key` 两种形态：`"world"` / `"character:<id>"`
- `rollback_lane_files` 对缺失文件不报错、对存在文件正确删除

仍需在真实 Phase 3 环境中跑通一遍含 lane FAIL 的实际阶段，确认
状态机转移与磁盘一致性。

## 风险与后续

- 如果 lane 修复瀑布本身 bug 导致"每次 lane 重跑都稳定失败"，最坏
  情况会走到全阶段回滚 + stage 重试 × 2，token 成本约 3–5 倍正常
  阶段 — 符合 §10.2 "每阶段独立 claude -p，无会话稀释" 的前提，但
  监控应关注 `lane_retries > 0` 的阶段占比
- `lane_filter` 参数保留但当前未使用：跨 lane reviewer 读对方产出导
  致 lane 独立 PASS 结论随时可能被新产出推翻，"只审未过的 lane" 是
  不安全的。如果未来把 reviewer 输入缩小到同 lane 内，可激活该参数
