# 2026-04-22 20:45 · preflight 缩 scope + repair 结构化记录 + heartbeat 源头减产 + extraction.log 滚动

## 背景

`extraction/{work_id}` 分支刚完成 S001，第二个 stage S002 被 git preflight
以 "Working tree has uncommitted changes" 拦下。调查发现脏文件是
`.claude/settings.json`——与 extraction 产物无任何关系。复盘顺带暴露了三件旁路
小事：repair agent 只落聚合日志、心跳行把 extraction.log 撑到 7960 行、log
无 rotation 会无限追加。本次一把解决四件。

## 改动清单

### 1. `preflight_check` / `checkout_master` 加 `scope_paths`

- [automation/persona_extraction/git_utils.py](../../automation/persona_extraction/git_utils.py)
  `preflight_check(..., scope_paths=...)` — scope 内脏才阻断，scope 外静默
  容许
- `checkout_master(..., scope_paths=...)` — 同语义；无 scope 时退化为整树 clean
  检查（向后兼容）
- 调用方 `cli.py` 初始 preflight、`orchestrator.py` 每 stage preflight 与两处
  `checkout_master` 全部传 `["works/{work_id}/"]`

动机：extraction 的 commit 路径只触及 `works/{work_id}/...`，无关脏文件
（IDE 配置、编辑器临时文件）没理由拦停一整个 stage。

### 2. `RepairRecorder` + coordinator 事件流

- 新增 [automation/repair_agent/recorder.py](../../automation/repair_agent/recorder.py)
  `RepairRecorder` 类：append-only JSONL，每次 write 立即 flush，支持上下文
  管理器
- [automation/repair_agent/coordinator.py](../../automation/repair_agent/coordinator.py)
  `run(..., recorder=...)` 在关键转换处 `_emit(...)`：
  - `phase_start` (A / B) · `phase_a_result` · `issue`（每条 blocking
    issue：fingerprint / file / json_path / category / rule / severity /
    message / start_tier）
  - `round_start` · `round_patched` · `round_result` · `l3_gate_result`
  - `t3_corrupted` · `no_patches` · `phase_c` · `complete`
- [automation/persona_extraction/orchestrator.py](../../automation/persona_extraction/orchestrator.py)
  `[4/5] Repair agent` 开头打开
  `works/{work_id}/analysis/progress/repair_{stage_id}.jsonl` 作为 recorder

动机：聚合统计（"resolved=5, persisting=0"）不足以事后复盘"第 3 个 issue
是什么 / 在 T3 修的是哪条字段"。结构化 JSONL 让 `jq` / Python 一键回放。

### 3. Heartbeat 源头减产（Y + W 方案）

- [automation/persona_extraction/llm_backend.py](../../automation/persona_extraction/llm_backend.py)
  新增 `_HB_RING_MAXLEN=20` + `_heartbeat_visible()` + `_flush_heartbeats()`
- `ClaudeBackend.run` / `CodexBackend.run` 的 heartbeat 线程同时做两件事：
  - **Y**：如果 `sys.stderr.isatty()`（foreground 模式），把心跳行打到
    `sys.stderr`；`--background` 模式下 stderr 被 `launch_background`
    合并进 extraction.log，`isatty()` 返回 False → 心跳不入 log
  - **W**：无论如何，心跳行 append 到 `collections.deque(maxlen=20)` 环形
    buffer；子进程 timeout 或非零退出时 `_flush_heartbeats` 用
    `logger.warning` 一次性 dump 环形 buffer
- `config.heartbeat_interval_s` 默认 30s 不变

动机：老实现每 30s `print(...)` 直接进 log，一个 stage 堆 7000+ 行心跳噪音，
出问题时却又被噪音淹没。Y 保留 foreground 的"还活着"视觉反馈；W 保证
故障时失败前 10 min 的内存/elapsed 曲线不丢。

### 4. `extraction.log` 启动时滚动

- [automation/persona_extraction/process_guard.py](../../automation/persona_extraction/process_guard.py)
  新增 `rotate_extraction_log(path, backup_count)`：`.N → .N+1` 倒序重命名，
  超过 `backup_count` 的最旧一份删除；`log → .1`；`backup_count=0` 退化为
  "永不滚动"
- `launch_background()` 在 `open(log, "a")` 之前调用滚动
- [automation/persona_extraction/config.py](../../automation/persona_extraction/config.py)
  `LoggingConfig.extraction_log_backup_count: int = 3`
- [automation/config.toml](../../automation/config.toml) `[logging]` 段对应项

动机：原实现纯 append 无上限，49 stage × 540KB ≈ 27MB 单跑；跨多次 `--resume`
会线性叠加。启动滚动把每次 run 的日志隔离到独立文件，磁盘占用有上限。

## 文档对齐

- `ai_context/architecture.md` — `checkout_master` 段从"dirty-tree guard"改为
  "scope_paths" 描述
- `docs/architecture/extraction_workflow.md` — 心跳输出策略段、repair 结构化
  JSONL 记录段、log rotation 段
- `docs/requirements.md` §11.11 运行时 artifacts 列表：extraction.log 条目
  补充滚动、新增 `repair_{stage_id}.jsonl` 条目
- `automation/README.md` "分支纪律" 节 dirty guard 段同步
- `docs/todo_list.md` "下一步" 新增 `[T-REPAIR-PARALLEL]`：Phase A / L3 gate
  per-file 并行化（预计 Phase A 耗时从 ~34m 压到 ~max(per-file) ≈ 6m）

## 验证

- Import smoke：`from automation.persona_extraction import cli` 等所有动过的模块
- `python -m automation.persona_extraction --help` 正常
- `rotate_extraction_log` 单测：3 轮滚动 + `backup_count=0` 禁用 + 超过上限删最老
- `preflight_check` scoped to 不存在的 work_id → 空 problems（scope 外脏被容许）
- `RepairRecorder` append 3 条事件，JSONL 行数 & 必填字段检查
- `_heartbeat_visible` / `_flush_heartbeats` 基本调用

## 未做的事

- **没改**：`CodexBackend.run` 仍用 argv 传 prompt（`T-CODEX-STDIN` 仍在
  讨论中），codex 路径不是本次 hot path
- **没做**：Phase A / L3 gate per-file 并行化 —— 已登记 `T-REPAIR-PARALLEL`
  到 `docs/todo_list.md` 下一步
- **没补**：rollback 脚本化（触发器 B）—— 用户决定暂不做，现手工流程 OK

## 其他

- 事件里发现历史 `docs/logs/2026-04-20_191258_rollback_phase3_to_phase_2_5.md`
  已是手工 rollback 的写法。未来若做 `T-REPAIR-PARALLEL` 之后再回头补
  rollback 脚本，可以把 `extraction.log` 归档到
  `docs/logs/rollbacks/` 一并做。
