# placeholder-scope-by-main-tracking

- **Started**: 2026-08-15 03:23:44 EDT
- **Branch**: main
- **Type**: DO
- **Status**: DONE

## Motivation

`conventions.md` 内部两条规则互相矛盾，并已造成一次真实泄露。§Git 规定
`main` "永不携带真实 work ID、原著小说或提取产物"；而 §Generic Placeholders
的 plugin canonical 段把 `logs/change_logs/`、`logs/review_reports/`、
归档 todo、`docs/decisions.md` 与 git commit 消息列为"历史本身就是重点"的
例外，允许写真实名称。这些路径恰恰都在 `main` 上被跟踪，而 `main` 推送到
公开远端 —— 于是真实书名与角色名随 34 个文件 + 18 条 commit 消息进入公开
仓库，存续约三个月，直到本轮通过 `git filter-repo` 重写历史清除。

矛盾不解决则必然复发：下一次 `/go` 写变更日志时会再次写入真实名称。本次
在 gap territory 收紧例外清单，把判据从"是否属于历史类内容"改为"是否被
`main` 跟踪"。

## Change list

- file: `ai_context/conventions.md` §Generic Placeholders 项目补充段（gap
  territory，第 202–215 行）→ 新增判据条目：凡 `main` 上被跟踪的文件与
  落在 `main` 历史的 commit 消息一律用占位符，逐项点名 canonical 段列为
  例外的五个路径 + commit 消息；历史类例外仅在从不推送的分支
  （`extraction/{work_id}`）上成立。
- file: 同上 → 新增"仍然豁免"条目，保留 `works/*/` 提取产物、`sources/`、
  `users/` 三项（`main` 不跟踪它们），并注明 `main` 只跟踪
  `works/README.md`。
- file: 同上 → 残留扫描范围从"上述全部路径（含 `.py`）"扩到 "+ `logs/` +
  本次改动的 commit 消息"，并加一句时机要求：写日志与 commit 消息时当场
  用占位符，不要事后补扫（commit 消息一旦推送，修正需要重写历史）。
- file: 同上 → 原"额外例外"条目中 `docs/todo_list_archived.md` 与
  `ai_context/decisions.md` 两项因落在 `main` 上而移出豁免，并入新判据。

## Verification summary

- sentinel 归属：`sentinel_parse.parse` 确认 §Generic Placeholders 仍为
  `plugin_blocks=1 / user_gaps=2`，canonical 例外清单原文逐字保留；
  `git diff` 中涉及 `holo:section` 标记的行数 = 0 —— 改动全部落在 gap，
  不会被下次 `/holo:update` 覆写。
- 结构完好：`holo_update_check.py --json` 报 `sentinel_layout_drift = 0`、
  `missing_section = 0`。
- 本文件自身即新规则的首个适用对象：全文未出现真实书名 / 角色名，
  泄露事件仅以结构化方式描述。

## Execution deviations

none
