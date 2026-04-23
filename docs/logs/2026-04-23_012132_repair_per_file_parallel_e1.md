# 2026-04-23 01:21 · Repair per-file 并发（E1 方案）落地

## 背景

Phase 3 S001 实测：extract 22m + repair 47m = 69m/stage。49 stage 外推
~56 小时。repair 是最大瓶颈，且 coordinator.run() 读代码发现**本来就
是纯 per-file 逻辑**（Phase A L3 prompt 只喂单文件 content；跨文件语义
校验是 Phase 3.5 独立承担）——所以 repair 单线程串行其实只是"调用方
式"问题，不是设计本质。

方案对比（2026-04-22 讨论）:
| 方案 | wall-clock | 复杂度 |
|---|---|---|
| E0（现状）| 69m | —— |
| B（SemanticChecker 内并发）| ~32m | 低，但架构半吊子 |
| E1（per-file 独立 repair 事务）| ~32m | 低，且架构干净 |
| E2（事件驱动 extract→repair overlap）| ~28m | 高（双池 + 回调）|

选 E1：速度与 B 相同，架构显著更清洁，并是 E2 的天然前置。E2 挂在
`docs/todo_list.md` 讨论中待观察。

## 改动清单

### Code

1. [automation/persona_extraction/orchestrator.py](../../automation/persona_extraction/orchestrator.py)
   `[4/5] Repair agent` 块：单次 `run_repair(files=[all 11])` → `ThreadPoolExecutor`
   分发，每文件一次 `run_repair(files=[single])`。每 worker 独立
   `RepairRecorder`。`as_completed` 汇聚，每 `fut.result()` 用
   try/except 包裹，单文件异常不影响同池其他文件。
2. 新 helper `_repair_slug(file_path)` 在 orchestrator 顶部：
   `<readable-last-2-segs>_<8-char-md5>` 形式，保证跨中文 ASCII 折叠
   的路径仍唯一。
3. [automation/persona_extraction/config.py](../../automation/persona_extraction/config.py)
   `RepairAgentConfig.repair_concurrency: int = 10`。
4. [automation/config.toml](../../automation/config.toml) `[repair_agent]`
   段加 `repair_concurrency = 10` + 中文注释（`rate_limit_pause` 频繁时
   降到 4-5）。

### 未改动（调查后确认不需要）

- **lane_states 取值扩展**：现有 "complete" / 缺失 二态已足够。E1 下
  lane 仍由 extract 成功标记 "complete"；repair 失败走
  FAILED → ERROR → resume reset → smart skip → re-repair 路径，与
  现有行为一致。
- **Resume 逻辑重写**：现有 `_process_stage` 的 REVIEWING 状态处理
  （orchestrator.py:1618）已经覆盖"repair 中途崩溃，resume 重跑"
  场景。per-file 崩溃 → stage ERROR → auto reset → 重走 Step 4。
  per-file 并发化不引入新失败模式。

### Docs

- [docs/requirements.md](../../docs/requirements.md) §11.4 新增
  "Per-file 并发执行" 子段；§11.4.8 Phase 3 行描述更新；§11.11
  artifact 命名改为 `repair_{stage_id}_{slug(file)}.jsonl` +
  slug 说明；§11.12 配置表 `[repair_agent]` 描述加 "per-file 并发"
- [docs/architecture/extraction_workflow.md](../../docs/architecture/extraction_workflow.md)
  流程图 `repair_agent.run()` 块替换为 `per-file 并发` 块；Repair Agent
  bullets 增补 per-file 并发调度段 + per-file JSONL 说明
- [ai_context/architecture.md](../../ai_context/architecture.md)
  三阶段 preamble 增补并发调度 + cross-file 一致性归属 Phase 3.5 说明
- [ai_context/decisions.md](../../ai_context/decisions.md) §25 尾巴补
  per-file 并发分发描述
- [docs/todo_list.md](../../docs/todo_list.md) 删除 T-REPAIR-PARALLEL
  条目（已完成即删除，本日志即其归档）

## 并行架构

```
Stage 进入
│
├─▶ [并行层 A · Extract pool] ThreadPoolExecutor(max_workers=1+2N=5)
│       └─ 1 world + N char_snapshot + N char_support 子进程
│       └─ as_completed → 全部 lane 产物落盘
│
├─▶ Post-processing（程序化 0s）
│       └─ 生成 digest / catalog 派生文件
│
├─▶ [并行层 B · Repair pool] ThreadPoolExecutor(max_workers=10)
│       └─ N 个 future 各自跑 coordinator.run(files=[single])
│       └─ as_completed → 汇聚全部 RepairResult → all_pass 判定
│
└─▶ Git commit（单次）
```

两池**串联不共存**，峰值并发 = max(5, 10) = 10。与 E2 的嵌套并发相比
避免 rate limit 压力。

## 验证

- Import smoke：`from automation.persona_extraction import cli, orchestrator`
  + `from automation.repair_agent.coordinator import run as repair_run`
  + `from automation.repair_agent.recorder import RepairRecorder`
- `python -m automation.persona_extraction --help` 正常
- `_repair_slug` 跨中文路径无碰撞：`姜寒汐/.../S001.json` vs
  `王枫/.../S001.json` md5 suffix 分辨
- `_repair_slug` 长度 ≤ 70，包 filename ≈ 90 chars < ext4/NTFS 上限 255
- `concurrent.futures` dispatch 模拟：11 个 fake task 并发 0.1s 完成
- Per-file exception 容错：try/except 捕获 worker 异常，合成
  `RepairResult(passed=False)` 加入聚合，不波及其他 worker

## 期望耗时

| 指标 | 当前 | E1 后 |
|---|---|---|
| S001 | 69m | ~32m |
| 49 stage | ~56h | ~26h |
| 节省 | | ~30h |
| 代码改动 | | ~120 行（manager + helper + config + docs）|
| 工作量 | | 实际 ~2h |

实测数据要在下次 stage 跑完后验证。

## 未解决

- 实测一轮后要看 `repair_concurrency=10` 是否频繁撞 rate limit；若是 →
  下调到 4–5。config.toml 注释已给指引
- `total_round_limit=5` 语义从"stage 全局"变"单文件"；更宽容，观察
  几 stage 后决定是否调

## 相关

- E2 方案挂在 `docs/todo_list.md` 的 T-REPAIR-PARALLEL-EVENT-DRIVEN，
  实测 E1 后根据真实 extract vs repair 耗时比再评估是否值得
