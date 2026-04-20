# T-TOKEN-WATCH 完成 + 单源 TOML 配置落地

**时间**：2026-04-20 00:08 (America/New_York)
**类型**：feat（基础设施）
**触发**：todo_list `T-TOKEN-WATCH` 立即执行项；用户要求"触及 token limit 时
暂停新 LLM 请求，等限额刷新后自动继续——除等待时间外应与无限额时等价"。

---

## 一、做了什么

### 1. Token-limit 自动暂停-恢复机制（subscription model）

新增 `automation/persona_extraction/rate_limit.py`，引入
`RateLimitController`。覆盖路径：

- **检测**：`run_with_retry` 在 `LLMResult.error == "rate_limit"` 时调用
  `controller.record_pause(stderr, lane_name=...)`。stderr 解析顺序：
  ISO 8601 → "Resets at HH:MM TZ" → "in N hours/minutes" → 失败回落到
  `parse_fallback_strategy`（默认 `probe`）。
- **暂停文件**：`works/{work_id}/analysis/progress/rate_limit_pause.json`，
  写入用 `tempfile + os.replace` 原子落盘，跨进程通过 `fcntl.flock`
  合并——后到的 lane 看到既存文件时取**最迟 reset 时刻**，避免互相覆盖
  导致提早恢复。
- **门控**：`controller.wait_if_paused(probe_fn=...)` 在每个 lane 入口和
  orchestrator 提交线程池前都会调用；命中暂停后以 30 秒 chunk 分段
  sleep（保留 SIGINT 响应），到点后视策略：
  - `parse` 命中：直接返回；
  - `probe` 命中：发一次最小 `claude -p` 探测，仍限则继续循环。
- **重试不计数**：`run_with_retry` 在 rate_limit 路径上 `attempt -= 1`，
  使限额刷新后的重发与第一次提交完全等价（仅多耗等待时间）。
- **周限额硬停**：`weekly_max_wait_h` 默认 12h；超过即写
  `rate_limit_exit.log` 后 `sys.exit(2)`，避免无意义阻塞。
- **运行时窗口扣除**：orchestrator 的 `_check_runtime_limit()`
  在比较前先扣 `controller.paused_seconds_total`，使
  `--max-runtime` 反映的是真实工作时长而非挂钟时长。

### 2. 单源 TOML 配置（automation/config.toml）

新增 `automation/persona_extraction/config.py`：

- 用 `tomllib`（Python 3.11+ stdlib）读取，frozen `@dataclass` 表达
  schema；无第三方依赖。
- 段：`[stage] [phase0] [phase1] [phase3] [phase4] [repair_agent]
  [backoff] [rate_limit] [runtime] [logging] [git]`。
- 加载入口 `get_config()` 进程内单例；首次访问时合并
  `config.toml` → 同目录可选的 `config.local.toml`（后者
  `.gitignore`）。
- 覆盖优先级：CLI flag > 环境变量 > `config.toml` > `config.local.toml`
  > 代码默认值。

把先前所有硬编码常量都改读 config：并发度、超时、修复 retry、熔断窗、
快速空失败序列、心跳、默认 backend、默认 max-runtime、
extraction-branch 前缀、auto-squash 开关。CLI argparse 默认值改成
"读 config，help 注明来源"。

### 3. todo_list 维护

- `T-TOKEN-WATCH` 完成 → 从「立即执行」整条移除；
- 提升时本应从「下一步」首条提升一条，但讨论中曾提到的
  `T-SCENE-CAP`（Phase 4 单章 scene 数量上限）尚未在「下一步」中存在；
  本次将其作为新条目登记进「下一步」（含动机/清单/验证/依赖/完成
  标准），由用户后续从「下一步」按节奏提升。
- 「立即执行」节当前显式标记"无"+ 提示从「下一步」提升。

## 二、改了哪些文件

**新增**（3 个）：

- `automation/config.toml`
- `automation/persona_extraction/config.py`
- `automation/persona_extraction/rate_limit.py`

**修改**（13 个）：

- `automation/persona_extraction/llm_backend.py` — 接入 controller +
  rate_limit 不计 retry；阈值/心跳/backoff 改读 config。
- `automation/persona_extraction/orchestrator.py` — 实例化并
  `set_active_rl(controller)`；6 处 `run_with_retry` 调用改读 config
  超时；`_check_runtime_limit()` 扣暂停时长；branch 前缀/
  auto-squash 改读 config。
- `automation/persona_extraction/scene_archive.py` — 熔断常量改读
  config；提交前调 `_gate()`；standalone Phase 4 路径自管 controller。
- `automation/persona_extraction/json_repair.py` — `repair_timeout`
  改可选，缺省读 `phase0.json_repair_l2_timeout_s`；带 lane_name。
- `automation/persona_extraction/cli.py` — argparse 默认从 config 取，
  help 注明来源。
- `.gitignore` — 加 `automation/config.local.toml`。
- `ai_context/current_status.md`、`ai_context/architecture.md`、
  `ai_context/decisions.md`（新增条目 45/46）。
- `docs/architecture/extraction_workflow.md` — rate-limit 段引 config。
- `docs/requirements.md`、`automation/README.md`（新「配置」段）、
  `docs/todo_list.md`。

## 三、验证

- `python -m automation.persona_extraction --help` 显示 config 来源默认
  值（`--backend claude (config.toml)` 等）。
- 5 条 rate-limit 冒烟用例全部通过：解析 reset 路径、probe 提升路径、
  probe 循环路径、合并较新 reset、合并较旧 reset。
- 周限额硬停路径：构造 23.5h 等待，验证 `sys.exit(2)` 与
  `rate_limit_exit.log` 落盘。
- 全部修改/新增文件 `python -m py_compile` 通过。

## 四、关键决策（写进 decisions §45/§46 的精炼版）

1. **TOML 单源**：所有可调旋钮集中一处；本地覆盖文件不入库；优先级
   CLI > env > config.toml > config.local.toml > 代码默认。
2. **反应式而非预查**：不在 launch 前查询配额；只在 stderr 命中限额
   关键字时切换到暂停态。原因：subscription 模式无可靠 quota API，
   预查会引入额外失败面。
3. **flock 合并**：跨 lane/进程并发命中限额时取最迟 reset，避免互相
   覆盖导致集体提前唤醒后再次撞限。
4. **probe 回落**：解析失败时不是简单 sleep，而是 sleep + 探测，
   保证恢复时机贴合真实状态。
5. **不计 retry**：rate-limit 重发与第一次提交业务等价，必须不消耗
   重试预算。
6. **--max-runtime 扣暂停**：用户配置的"运行时长"语义指实际工作时长。

## 五、未落地（后续）

- `failed_lanes_retention_days`：config 字段已定义，但定时清理逻辑
  尚未接入 startup hook。低优先级。
- `T-SCENE-CAP` 已新登记到 todo_list 「下一步」，待用户提升后做。
- `T-RETRY` 仍在「讨论中」；T-TOKEN-WATCH 与 T-LOG 双双落地后，
  按 subtype 分流的失败重试条件已具备，可在收集到几次真实失败样本
  后定案。
