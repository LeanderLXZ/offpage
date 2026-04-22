# 2026-04-22 Phase 4 chapter 级 in-process retry + 11 章修复

## 背景

2026-04-22 午间 Phase 4 全量重跑（537 章 / `--start-phase 4`）出 526
PASSED + 11 FAILED 后 orchestrator 自然退出，未触发 merge。失败 11 章
全部是同一类校验错误：

```
Incomplete coverage: last scene ends at line N, but chapter has N+1 lines
```

LLM 系统性漏切章节最末 1 行（推测是空行 / 分隔符），其中 0496 多一条
`end_line 93 > total lines 92` 边界越界。

排查发现 `_run_parallel` 设计上 max_retries=2 字段存在、`_mark_failed`
也按 `retry_count > max_retries` 升级 ERROR——但调度本身是 `pending_iter`
单遍消费，FAILED 章节不重新入队，所谓 "in-process retry" 其实**没有发生**，
只能靠 `--resume` 跨次重试。

用户的判断："Phase 4 每个线程应该用到 checker/fixer，每线程 retry 2 次
（toml 可配）；checker/fixer 框架长期应跨 phase 通用化，各 phase 的
validate/fix 方式对齐。"

## 决定走 A 方案（B / C 不做）

- **A**（本次落地）：Phase 4 单进程内 retry，toml 配
  `[phase4].max_retries_per_chapter=2`。`_run_parallel` 加
  `retry_queue` + `_next_chapter()`，FAILED 章节回插队列、prompt 注入
  `prior_error` 重新切分。
- **B 不做**：repair_agent 的 Issue / Fixer 模型深度绑定
  "schema + json_path + 文件 patch"。Phase 4 失败语义本质是"重新
  调用 LLM 切分"——只对应 T3 file_regen 的退化版，T0/T1/T2 没有施力
  空间。强套等于把 4-tier 框架降级成"调一次 LLM"。
- **C 不做**（暂不做，未否决）：抽通用 "check + fix 协议"
  （`check(产物) -> issues` / `fix(产物, issues, attempt_idx) -> 新产物`
  / `retry_budget` / `on_give_up`），repair_agent 重构成 Phase 3
  特化、Phase 4 实现简化版。属于设计 / 重构层议题，独立立项更合适，
  本次只做 A。

## 代码改动

`automation/persona_extraction/scene_archive.py`：

1. 删 `import itertools`（被 `_next_chapter` 替代）。
2. `_run_scene_archive_inner` 创建 / 加载 `ChapterEntry` 时，从
   `cfg.phase4.max_retries_per_chapter` 注入 `max_retries`。已存在条目
   也刷新 max_retries——toml 调高后 `--resume` 即生效。
3. `_run_parallel`：
   - 新增 `retry_queue: list[str]` + `_next_chapter()` helper。
   - 任务结果分支：success → `[OK]` 计数；failure 时检查
     `entry.state == FAILED and entry.retry_count <= entry.max_retries`
     → 重置 PENDING、入 retry_queue、打印 `[RETRY] {cid} attempt
     {n}/{N+1}`；否则 → terminal `[FAIL]` + 计入熔断计数。
   - 新槽位填充改成 `while len(futures) < concurrency`，先吃
     retry_queue 再吃 pending_iter。
   - 最后一行 stats 加 `Retried: N`。

`automation/persona_extraction/config.py`：`Phase4Config` 加
`max_retries_per_chapter: int = 2`。

`automation/config.toml` `[phase4]` 加 `max_retries_per_chapter = 2`
+ 注释说明语义（总尝试数 = 1 + budget）。

## 验证

`--start-phase 4 --resume`（PID 349435）：
- 11 章 FAILED → reconcile 重置 PENDING → 全部 fan-out
- `[RETRY]` 出现 3 次（0018 / 0024 / 0496 各 1 次），全部第 2 次成功
- 8 章首次就过——新 prompt 软上限 + prior_error 注入合力
- 1m40s 跑完，0 终态失败，`scene_archive.jsonl` merge 落盘
- 4.16 MB / 1236 scenes / 537 chapters / 49 stages
- per-chapter 场景数 min=1 / max=5 / avg=2.30；分布
  1=105, 2=223, 3=156, 4=48, 5=5；**>5 章节 0 个**（prompt 硬约束 ≤5
  完全生效）

## 行为变更副作用

- **Circuit breaker 触发门槛事实变高 ~3x**：`recent_failures` 只在
  terminal failure 计数。systemic outage 下要等 8 章耗尽 retry budget
  才触发熔断（≈ 8 × (1 + max_retries) = 24 次失败）。可接受——
  熔断本意是"挡住持久失败"，短时抖动应自愈。但首跑出现 `[BREAKER]`
  时延迟会比从前明显。
- **`[FAIL]` 日志频次降低**：之前每次 raw 失败一行，现在只在终态出。
  操作员扫日志统计失败数会比实际偏少。可用 `Retried: N` 终末统计
  补回。
- **periodic save 节奏变疏**：`(completed + failed) % 10` 不计 retried。
  retry 风暴下保存间隔拉长，进程 SIGKILL 最多丢 retry_count 字段；
  下次启动 `reconcile_with_disk()` 兜底重置 PENDING。低风险。

## 文档同步

- `automation/README.md` §"Phase 4：场景切分"工作流加一条 retry 说明
- `ai_context/architecture.md` Phase 4 段加 retry 描述
- `ai_context/current_status.md` Phase 4 项加 retry 描述
- `ai_context/decisions.md` 加 39a 决策（A 方案 + 拒 B + 暂缓 C 的理由）
- `docs/requirements.md` §1949 公式 `<` → `<=`（与代码 `_mark_failed`
  + 默认值 `max_retries=2 → 3 次总尝试` 的语义对齐）；§2249 删
  "保留 retry_count，不清零" 一句（与代码清零行为对齐）

## 不做的事

- **不实现 C**：抽通用 check+fix 协议是更大的重构议题，本次不夹带。
- **不动 `_mark_failed`** 边界判定：现有 `>` 语义就是 1+budget 总
  尝试，与新增 retry condition 自洽。
- **不调 circuit breaker 阈值**：默认 8/60s/180s 保留；后续若大批量
  重跑发现熔断触发太晚再单调。
- **不加 max_retries 字段到 reconcile_with_disk 的清零白名单**：
  reconcile_with_disk 对 PASSED 之外的所有状态都清零 retry_count，
  现有行为正确（任何半完成态都不可信，给新预算）。

## 关联

- 11 章修复结果：`scene_archive.jsonl` 已生成、merged=true，Phase 4
  完成。等用户决定切回 master 时机。
- 用户 C 提议（"check+fix 协议跨 phase 通用化"）暂未立项；如要立项
  应单独写 design doc 而不是拼到本次。
