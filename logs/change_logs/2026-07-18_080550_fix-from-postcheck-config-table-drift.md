# fix-from-postcheck-config-table-drift

- **Started**: 2026-07-18 08:05:50 EDT
- **Branch**: main
- **Type**: DO
- **Status**: DONE

## Motivation

落地 `/post-check`（`logs/change_logs/2026-07-18_070924_repair-timeout-config.md`，
REVIEWED-PARTIAL）经 `/fix` Auto 分派的 fix 桶两条：M2 + L2。两条同属一类问题
——「配置分节表」在 `extraction/README.md` 与 `docs/requirements.md` 两份镜像
之间的漂移，且都是既有欠账（非上一轮引入），但上一轮正好改到这两张表。

## Change list

- file: `extraction/README.md:68`（M2）→ 删除 `[phase3]` 行里的
  `concurrency（默认 12，覆盖 2 角色场景 sub-lane on 时峰值 1 + 2×4 + 2 = 11）`
  一段。该键在 `Phase3Config` 与 `config.toml [phase3]` 中均不存在；那个默认值
  12 与该推导实际归属 `[phase0].concurrency`（`core/config.py:47`，注释原文即此
  推导）与 `[phase4].concurrency`（`core/config.py:102`）。
- file: `docs/requirements.md:2627`（L2）→ §配置分节表新增 `[phase2]` 行
  （用途措辞对齐 `extraction/README.md:64-67` 的既有表述）。
- file: `docs/requirements.md:2630`（L2）→ 同表 `[repair]` 行：把无对应键的
  「lifecycle 上限」订正为实际键名 `total_round_limit`（lifecycle 概念已随决策
  #62 删除），补上遗漏的 `defer_unresolved_semantic`（决策 #60 的行为开关），
  并补 triage 开关。

## Verification summary

- `grep -n "concurrency" extraction/README.md` → `[phase3]` 行已无该键；
  余下命中均为 `[phase2].lane_concurrency` / `[repair].repair_concurrency` /
  CLI `--concurrency`，均为真实存在的键。
- `grep -n "\[phase2\]" docs/requirements.md:2627` → 新行已落位，表格结构完整。
- `[repair]` 行逐键比对 `extraction/config.toml [repair]` 实际键集
  （`t0/t1/t2_retry` / `total_round_limit` / `triage_enabled` /
  `triage_accept_cap_per_file` / 四个 timeout / `repair_concurrency` /
  `defer_unresolved_semantic`）→ 表中所述均可对应到真实键，无虚构项。
- 两份镜像（`extraction/README.md` §配置分段 ⇄ `docs/requirements.md`
  §配置分节表）的 `[phase2]` / `[phase3]` / `[repair]` 三行口径已一致。
- 纯文档改动，无可执行代码 / 数据契约变更，未跑 smoke。

## Execution deviations

none
