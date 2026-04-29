# t3-cap-boilerplate-followup

- **Started**: 2026-04-29 03:50:33 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

`/post-check` 复审 `35340b1`（T-REPAIR-T3-LIFECYCLE-RESET 落地）后报 REVIEWED-PARTIAL：
轨 1 主要 16 项落实但 3 条 boilerplate 沿用旧"T3 全局每文件最多 1 次 / T3 全局上限"
摘要措辞，未与新 lifecycle 语义同步。详见
`logs/change_logs/2026-04-29_030118_repair-t3-lifecycle-reset.md` 的复查结论段。

用户指示"按建议修复"——本次只吸收这 3 条 Missed Updates 转 PASS，不动其他。

## 结论与决策

仅修这 3 条 boilerplate；不重构、不改逻辑、不动其他文件。所有改写措辞与
新 lifecycle 语义对齐（参见 [decisions.md #25](../ai_context/decisions.md#L79) 与
[requirements.md §11.4.4](../docs/requirements.md) 已落地的 `max_lifecycles_per_file=2`
描述风格）。

## 计划动作清单

- file: `automation/README.md:32`
  - "T3 全文件重生成，**T3 全局每文件最多 1 次**" →
    "T3 全文件重生成，**单文件至多在 lifecycle 1 触发一次**"（与 README L306 已落地的同表述对齐）
- file: `automation/README.md:66`
  - 配置摘要行 "T3 全局上限" → "lifecycle 上限"
- file: `docs/requirements.md:2399`
  - 配置表行 "T3 全局上限" → "lifecycle 上限"

## 验证标准

- [ ] `grep -nE "T3 全局上限|T3 全局每文件" automation/ docs/ ai_context/ --include='*.md'` 命中均在 `logs/` / `todo_list_archived` 之外为 0
- [ ] 三处改后措辞与 [decisions.md #25](../ai_context/decisions.md) / [extraction_workflow.md](../docs/architecture/extraction_workflow.md) / [README.md:306](../automation/README.md#L306) 的 lifecycle 描述风格一致
- [ ] 无其他文件受影响（git diff --stat 仅这 3 个 + 本 log）

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

- `automation/README.md:32` — Phase B 描述内 "T3 全局每文件最多 1 次" → "单文件至多在 lifecycle 1 触发一次；lifecycle 2 禁用 T3，升 T3 即 `T3_EXHAUSTED`"
- `automation/README.md:66` — `[repair_agent]` 配置摘要行 "T3 全局上限" → "lifecycle 上限"
- `docs/requirements.md:2399` — `[repair_agent]` 配置表行 "T3 全局上限" → "lifecycle 上限"

## 与计划的差异

无

## 验证结果

- [x] `grep -nE "T3 全局上限|T3 全局每文件" automation/ docs/ ai_context/ --include='*.md'` 命中均在 `logs/` / `todo_list_archived` 之外为 0 — 已 grep, "OK: clean"
- [x] 三处改后措辞与 decisions.md #25 / extraction_workflow.md / README.md:306 的 lifecycle 描述风格一致 — 均使用 "lifecycle 1 触发 / lifecycle 2 禁用 / T3_EXHAUSTED" 同口径
- [x] 无其他文件受影响 — `git diff --stat` 仅 README.md / requirements.md 两个文件 + 新建本 log

## Completed

- **Status**: DONE
- **Finished**: 2026-04-29 03:51:39 EDT
