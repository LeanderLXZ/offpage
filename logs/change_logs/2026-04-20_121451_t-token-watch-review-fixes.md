# T-TOKEN-WATCH review fixes (H1–M5)

落实 `docs/review_reports/2026-04-20_044645_opus-4-7_t-token-watch_review_findings.md`
中 H1/H2/H3 + M1/M2/M3/M4/M5 的全部修复项。

## 变更总览

| 等级 | 内容 | 涉及文件 |
|------|------|---------|
| H1 | `paused_seconds_total` 按 `resume_at` 去重；N lane 共享同一 pause 窗口只计一次 | `rate_limit.py` |
| H2 | `ai_context/current_status.md` Phase 3 进度从 "1/10 committed" 改为 "1/49 committed, 1 ERROR, 47 pending" | `current_status.md` |
| H3 | weekly 硬停改为 `RateLimitHardStop` 异常 + 主线程 `CliRunner` 统一 `sys.exit(2)`，避免 worker 线程直接 `sys.exit` 被吞 | `rate_limit.py` / `cli.py` |
| M1 | 新增 `[rate_limit].probe_max_wait_h = 6`：单次 probe 会话累计等待 ≥ 6h → `RateLimitHardStop("probe_exhausted")` + `rate_limit_exit.log` | `config.toml` / `config.py` / `rate_limit.py` |
| M2 | DST 感知时区解析：PT/MT/CT/ET 走 `zoneinfo.ZoneInfo`（IANA 区），夏令时/冬令时自动对齐；PST/EDT 等明确缩写仍走固定偏移 | `rate_limit.py` |
| M3 | `works/README.md` 补 3 条产物说明：`rate_limit_pause.json` / `rate_limit_exit.log` / `failed_lanes/` | `works/README.md` |
| M4 | 删除 "环境变量" 覆盖层文档（从未实现） | `config.toml` 顶注 / `automation/README.md` / `docs/requirements.md §11.12` / `decisions.md` #45 |
| M5 | 同步 `ai_context/next_steps.md` Phase 3 状态表述 | `next_steps.md` |

## probe 全局化（附带决定）

`unknown` fallback 下不再让每个 lane 各自起 probe，新增 leader 选举：

- `PauseRecord` 新增 `probing_by_pid` / `probing_claim_at` / `probe_session_started_at`
- `_claim_probe_leadership()` 用 `fcntl.flock` 做 CAS，TTL 由
  `[rate_limit].probe_claim_ttl_s`（默认 120s）控制；TTL 过期视为
  leader 已挂，其他 lane 可重新接手
- follower 按 `probe_follower_poll_s`（默认 30s）轮询 pause 记录
- `probe_session_started_at` 是 probe 硬停判定锚点，`record_pause()`
  合并时保留，不被 5h/weekly 类型的新 pause 覆盖

## 位置决定

`automation/config.toml` 保持原位，不迁到顶层 `config/`；simulation 侧
规模起来后再议（当前仅 `prompt_templates/` 文本，无独立配置需求）。

## 文件清单

代码：
- `automation/persona_extraction/rate_limit.py` — `RateLimitHardStop` /
  `_resolve_tz` / `_account_slept` / `_claim_probe_leadership` /
  probe 会话硬停 / record_pause 合并保留 leader 字段
- `automation/persona_extraction/cli.py` — Phase 4 + 主流程两处 try /
  except RateLimitHardStop → `sys.exit(WEEKLY_EXIT_CODE)`
- `automation/persona_extraction/config.py` — `RateLimitConfig` 新增
  `probe_max_wait_h` / `probe_claim_ttl_s` / `probe_follower_poll_s`
- `automation/config.toml` — `[rate_limit]` 补 3 个键 + 顶注删 env
  + `parse_fallback_sleep_s` 注释更新

文档：
- `docs/requirements.md §11.12` + `§11.13`（含 11.13.3/4/5/6/7/9）
- `ai_context/current_status.md` / `ai_context/decisions.md` /
  `ai_context/next_steps.md`
- `automation/README.md` 配置优先级 + `[rate_limit]` 描述
- `works/README.md` 目录树 + `progress/` 说明

## 验证

- import 通过，`get_config()` 返回 3 个新键默认值（6 / 120 / 30）
- `_resolve_tz("PT")` 返回 `ZoneInfo('America/Los_Angeles')`；
  `_resolve_tz("PST")` 返回固定偏移
- 手工模拟：`_account_slept(resume_at=X, slept=1800)` 先记一次；
  第二次传同 `resume_at` 不叠加
- 手工模拟：`probe_session_started_at = now - 7h` → `wait_if_paused`
  raise `RateLimitHardStop("probe_exhausted")`
