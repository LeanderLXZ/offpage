# phase3_run_metrics_jsonl

- **Started**: 2026-07-15 10:49:45 EDT
- **Branch**: main
- **Type**: GO
- **Status**: PRE

## Background / Trigger
用户想看 Phase 3(及各 phase)的时间 / token 消耗细节。排查后发现:每次
`claude -p` 调用虽解析了 `duration_seconds` / `num_turns` / `total_cost_usd`,
但仅在**失败**时写盘(`failed_lane_log`),成功 run 用完即弃;`logs/runs/` 里
只有手动重定向的 Phase 2 控制台日志,无结构化的 per-phase 时间 / token 账本。
讨论定为"方案 B 精简版":每次 LLM 调用往 `logs/runs/{work_id}_{ts}.jsonl`
追加一行结构化记录,run 启动时间戳进文件名(每 run 一个独立文件)。

## Conclusion and decisions
- 新增 `core/run_metrics.py`:进程级 recorder(单例风格),持有输出文件路径 +
  当前 phase + 线程锁 + 内存行缓存;`init_run_metrics` / `set_phase` /
  `record` / `summarize` 四个模块级入口。
- **不改 `LLMResult`**:成功路径 `result.raw` 已含 `usage`(input/output/
  cache_read/cache_creation_input_tokens)+ `total_cost_usd`;recorder 从
  `result.raw` 读,raw 为空(失败路径)时回退解析 `result.raw_stdout`。
- **单点接入**:在 `run_with_retry` 每次 `backend.run` 返回后调用
  `record(...)` —— 一处覆盖所有 backend(claude/codex)× 所有 phase × 所有
  lane(含 repair)× 每次 attempt(含重试)。
- `phase` 字段由 orchestrator 各 phase 方法顶部 `set_phase(...)` 提供
  (phase0/1/2/3/4);未 init 时 `record` 静默 no-op(单测直调不受影响)。
- 行 schema:`{ts, phase, lane, success, duration_s, num_turns, input_tokens,
  output_tokens, cache_read, cache_creation, cost}`。
- run 结束 `summarize()` 按 phase / lane 聚合打印小表(调用数 / 总耗时 /
  in+out token / cost);best-effort,永不抛。
- 输出目录 `logs/runs/` 不进 do-not-commit 名单,但 jsonl 产物本身是运行数据、
  不提交(仅本次代码 + 日志入 commit)。

## Planned action list
- file: extraction/persona_extraction/core/run_metrics.py → 新增 recorder 模块
- file: extraction/persona_extraction/core/llm_backend.py → import + run_with_retry 内 1 处 record 调用
- file: extraction/persona_extraction/orchestrator.py → run_summarization / run_analysis / run_baseline_production / run_extraction_loop / _run_scene_archive 顶部各 1 处 set_phase
- file: extraction/persona_extraction/cli.py → 标准路径 + Phase 4 standalone 路径各 init_run_metrics + finally summarize
- file: ai_context/architecture.md → 流水线段补一句 run-metrics 账本
- file: docs/architecture/extraction_workflow.md → 补 run-metrics jsonl 说明(如该文件有对应段落)

## Validation criteria
- [ ] `python -c "import extraction.persona_extraction.core.run_metrics"` 无 error
- [ ] `python -c "import extraction.persona_extraction.core.llm_backend"` / `cli` / `orchestrator` 无 error
- [ ] recorder 冒烟:init → set_phase → record(伪造带 raw.usage 的 LLMResult)→ 检查 jsonl 落盘且字段齐全 → summarize 打印表不抛
- [ ] `record` 在未 init 时静默 no-op(不抛)
- [ ] 文件名格式 = `{work_id}_{YYYY-MM-DD_HHMMSS}.jsonl`

## Execution deviations
- 计划外新增 `.gitignore` 一行 `logs/runs/*.jsonl`:jsonl 的 lane 字段含真实
  角色名、文件名含真实 work_id,属运行数据不可入库;本 feature 直接产生该
  产物,故补 ignore 规则(严格必要,防误提交真实数据)。
- 计划外未改 `docs/architecture/extraction_workflow.md` 之外的 docs;
  `LLMResult` 按设计未改动(token 从 `result.raw` 读)。

<!-- POST phase fills in -->

## Landed changes
新增 `core/run_metrics.py` 进程级 run 指标账本;`run_with_retry` 单点每调用
落一行到 `logs/runs/{work_id}_{ts}.jsonl`(时间/token/cost);orchestrator 各
phase 方法顶部 `set_phase` 标注 phase0–4;cli 两条运行路径 init + finally
summarize;`.gitignore` 忽略 `logs/runs/*.jsonl`;架构文档补账本说明。

## Diff from plan
- 计划外新增 `.gitignore` 一行(见 Execution deviations)。
- `docs/architecture/extraction_workflow.md` 已改;`schema_reference` 等其余
  docs 无需动。其余与计划一致。

## Validation results
- [x] 四模块 import 无 error
- [x] recorder 冒烟:init → set_phase → record → jsonl 落盘(11 字段齐全)→
      summarize 打印聚合表不抛;失败路径从 raw_stdout 回退取 usage 成功
- [x] `record` 未 init 时静默 no-op
- [x] 文件名格式 = `{work_id}_{YYYY-MM-DD_HHMMSS}.jsonl`(中文 work_id 正常)

## Completed
- **Status**: DONE
- **Finished**: 2026-07-15 11:01:00 EDT
