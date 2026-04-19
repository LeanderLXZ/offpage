# T-LOG：Phase 3 lane 级失败诊断日志

## 背景

此前 `claude -p` 失败路径（`automation/persona_extraction/llm_backend.py`）
在非零 exit 时只保留 stderr，完全丢弃 stdout；这让长时失败（例如触达
`--max-turns` 时）的根因不可见——stderr 常常为空，但 stdout 其实包含
`{"subtype":"error_max_turns","num_turns":50,...}` 这类关键诊断 JSON。
PID 打印也无 lane 标识，tail extraction.log 时无法快速回推某个 PID
是哪个 1+2N lane。

## 范围

只做诊断信号的捕获与落盘。**不改**重试策略、不改失败处理语义
（`rollback_to_head` + stage→ERROR 保持不变）。重试策略的调整是 T-RETRY
的范围，需等本次改动先把诊断信号变可见后再决定。

## 本次改动

### `automation/persona_extraction/llm_backend.py`

- `LLMResult` 扩 5 个诊断字段，均带安全默认值（向后兼容）：
  `raw_stdout`、`raw_stderr`、`subtype`、`num_turns`、`total_cost_usd`
- 新增辅助函数 `_parse_claude_json()`、`_build_diagnostic_error()`
- `ClaudeBackend.run()` 与 `CodexBackend.run()` 签名加 `lane_name` 可选参数
  - PID start / heartbeat / finish 三处打印统一带 `[{lane_name}]` 标签
  - 超时路径改为 `proc.communicate()` 捕获被 kill 子进程的残留 stdout/stderr
  - 失败路径捕获 stdout 并尝试解析 claude 的 JSON 输出；解析到的
    `subtype` / `num_turns` 前置到 `error` 字段，原 stderr 附在冒号后
- `run_with_retry()` 签名加 `lane_name` + `on_failure` 回调；每次失败
  （含重试中间态）均触发 `on_failure(result, attempt)`

### `automation/persona_extraction/failed_lane_log.py`（新建）

- 单一函数 `write_failed_lane_log(work_root, stage_id, lane_type, lane_id,
  result, prompt_length)`
- 写 `works/{work_id}/analysis/progress/failed_lanes/{stage_id}__{lane_type}_{lane_id}__{pid}.log`
- 文件内容：header（lane 元数据 + `subtype` / `num_turns` /
  `total_cost_usd`，解析到才写）+ 完整 stdout + stderr
- **不写 prompt**：prompt 可由 git 状态 + stage_id 复现，不需入盘；日志
  定位为 CLI 输出诊断
- 文件名 sanitize 保留 CJK 字符，失败容错（目录/文件创建失败返回 None）

### `automation/persona_extraction/orchestrator.py`

- import `write_failed_lane_log`
- `_process_stage()` 内新增 `_log_lane_failure(lane_type, lane_id,
  prompt_length)` 工厂，生成绑定当前 `stage.stage_id` + `work_root` 的
  回调
- 三个 lane 入口（`_extract_world` / `_extract_char_snapshot` /
  `_extract_char_support`）分别传入 `lane_name` 与 `on_failure` 回调
- 每次失败写一行 `[LOG] {lane_type}:{lane_id} failure → {path}` 到
  stdout，便于 tail 时立即看到日志位置

### 文档

- `docs/requirements.md`：§11.5 加 "Lane 级失败诊断日志" 条目；§11.7
  补 `LLMResult` 新字段与 `lane_name` 语义；进度目录树加 `failed_lanes/`
- `docs/architecture/extraction_workflow.md`：§6 新增 6.4 小节
  "Lane 级失败诊断"
- `ai_context/current_status.md`：编排器特性清单补一条
- `docs/todo_list.md`：删除 T-LOG 条目（任务已完成）；T-RESUME 与
  T-TOKEN-WATCH 的"依赖 T-LOG" 改为"T-LOG 已完成"；T-RETRY 讨论上下文
  更新为可基于实际 subtype 决策

## 验证

- `python -m compileall` 三个核心模块全 OK
- 单元级：`_parse_claude_json` 处理合法 JSON / 非 JSON / 非 dict
  JSON（如数组）均返回安全值
- 整合级（mock Popen）：
  - 失败路径 with JSON stdout → `LLMResult.subtype` / `num_turns` /
    `total_cost_usd` 全部解析出来，`error` 串带前缀标签
  - 成功路径 with JSON stdout → 未回归
  - `run_with_retry` rate_limit 重试 3 次 → `on_failure` 回调被调用 3 次
- 磁盘：`write_failed_lane_log` 在临时目录写入中文 stage_id +
  lane_id 的文件名，git check-ignore 确认 `failed_lanes/` 子目录
  已被 `works/*/analysis/progress/` 这条 ignore 覆盖

## 开销

- 时间：成功路径零新增开销（已在内存的字段多赋值）；失败路径
  `<20ms`（JSON 解析 + 文件写入）
- Token：零。失败日志不进任何 prompt，只供人工诊断
- 磁盘：每失败一次 ~10KB，预期累计 <100KB（`progress/` 已 gitignore）

## 未做（有意留到后续）

- **T-RESUME**（lane 级失败不整体回滚 + `--resume` 按 lane 续跑）：依赖
  `failed_lanes` 字段进 `StageEntry`，需要更大改动
- **T-TOKEN-WATCH**（跨调用 token 累计）：现在 `LLMResult` 已带
  `total_cost_usd` / `num_turns`，T-TOKEN-WATCH 只需加 jsonl 持久化
- **T-RETRY**（智能重试）：等真实失败样本进来后，按 `subtype` 分流

## 后续动作

- 下次真实失败或人工 SIGTERM 某个运行中 lane，验证 `failed_lanes/*.log`
  写入完整
- 分支策略：本次改动先在 `extraction/我和女帝的九世孽缘` 落地（master
  worktree 被另一个会话占用），待 master 空闲后 merge 过去
