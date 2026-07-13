# fix_from_postcheck_phase2_lane_split

- **Started**: 2026-07-13 15:28:47 EDT
- **Branch**: main
- **Type**: GO
- **Status**: PRE

## Background / Trigger

/post-check（对 `577722f` phase2_lane_split_repair_integration，写回见
[2026-07-13_104934_phase2_lane_split_repair_integration.md](2026-07-13_104934_phase2_lane_split_repair_integration.md)
REVIEWED-PARTIAL）→ /fix Auto 分流，fix bucket = M2 / M3 / M4 / L2 +
OQ1 采纳方案 A。M1（lane A 溯源基线 resume 洗白窗口）因建议文含 todo
备选被 Auto 静默 skip，本轮不处理。

Anti-over-engineering：post-review 修复只打最小补丁——不顺手重构、不加
抽象、不加测试、不加 flag；3 行能解决就不提 helper。

## Conclusion and decisions

- **M2**：`FileRegenFixer` 的 `lane_regen` 返回 True 时改为 reload 传入
  本次 `fix()` 的**全部** files 条目（identity 双文件 lane 中 T1 已设
  `f.content` 的兄弟文件不再陈旧）；`sub_lane_regen`（单文件作用域）不动。
- **M3 + OQ1（方案 A）**：`docs/decisions.md` 第二条重复 "27m."
  （stage_plan 拐点先行）改号 "27n."；index `ai_context/decisions.md`
  "27a–27m" → "27a–27n"；#52 正文引 stage_plan 反锚定的 "#27m" → "#27n"。
  第一条 27m（chunk 二级字段）与 #53 的引用不动。
- **M4**：在上一轮 log 的 Execution deviations 末尾追加一行勘误补记
  （append-only，不改写既有段落）：deviation #8 所称 "#27l 指针" 实为
  第一条 "27m."（chunk 二级字段）条目内的指针行；commit message 同误，
  勘误以 log 为准。
- **L2**：`run_baseline_production` 入口对 `target_characters` 用
  `dict.fromkeys()` 去重一行。

## Planned action list

- file: `extraction/repair/fixers/file_regen.py` → lane_regen True 分支 reload 全部 files 条目
- file: `extraction/persona_extraction/orchestrator.py` → `run_baseline_production` 入口 target_characters 去重一行
- file: `docs/decisions.md` → 第二条 "27m." 改号 "27n."；#52 正文 "#27m" 引用改 "#27n"（仅 stage_plan 语义处）
- file: `ai_context/decisions.md` → #27 索引行 "27a–27m" → "27a–27n"
- file: `logs/change_logs/2026-07-13_104934_phase2_lane_split_repair_integration.md` → Execution deviations 追加勘误一行（M4）

## Validation criteria

- [ ] import：`extraction.repair.fixers.file_regen` + `extraction.persona_extraction.orchestrator` 无错
- [ ] smoke：既有 phase2 smoke 全过（lane_regen 端到端场景含在内）+ `_smoke_l3_gate` 回归
- [ ] 单元断言：双文件场景下 lane_regen True 后两个 FileEntry.content 均为盘上新内容
- [ ] grep：`docs/decisions.md` "^27m." 恰 1 条、"^27n." 恰 1 条；`ai_context/decisions.md` 含 "27a–27n"；#52 正文无指向 stage_plan 的 "#27m" 残留
- [ ] 去重断言：`dict.fromkeys` 出现在 run_baseline_production 入口

## Execution deviations

1. **M3 改号引用面比 brief 宽**：brief 只列 #52 正文，实测 stage_plan
   语义引用共 10 处需同步（docs/decisions.md #52/#56 + extraction_workflow
   ×2 + schema_reference ×1 + stage_plan.schema.json description ×2 +
   docs/todo_list.md T-LIGHTNOVEL 活动条目 ×3 + smoke 注释 ×2 + index
   "27a–27m" 区间）；todo_list_archived / logs 内历史引用按 OQ1 方案 A
   冻结不动（歧义窗口已接受）。

<!-- POST phase fills in -->

## Landed changes

/post-check REVIEWED-PARTIAL 的 fix bucket 落地：M2（lane_regen True 时
reload 全部 files 条目）+ L2（target_characters 入口去重）+ M3/OQ1 方案 A
（重复 "27m." 第二条改号 "27n."，index 区间 + 全部 stage_plan 语义引用
10 处同步）+ M4（上一轮 log 追加勘误补记 #9）。文件级明细即本 commit diff。

## Diff from plan

- M3 引用面从 brief 的 1 处扩到 10 处（见 Execution deviations #1）；
  其余按计划逐项落地，无删减。

## Validation results

- [x] import 无错（file_regen / orchestrator）
- [x] smoke：phase2 全量 SMOKE ALL PASS + `_smoke_l3_gate` + `_smoke_stage_plan_schema_min8` 回归 OK
- [x] 单元断言：双文件 lane_regen True 后两个 FileEntry.content 均为盘上新内容（含 T1 已 patch 兄弟文件）
- [x] grep：`^27m.` ×1 / `^27n.` ×1（docs/decisions.md）；`27a–27n` 在 index；stage_plan 语义 `#27m` 残留 = 0（仅剩 #53/#54 历史 plumbing 的 chunk 语义引用）
- [x] `dict.fromkeys` 在 run_baseline_production 入口（orchestrator.py:2235）
- [x] stage_plan.schema.json（description-only 改动）metaschema 通过

## Completed

- **Status**: DONE
- **Finished**: 2026-07-13 15:38:56 EDT
