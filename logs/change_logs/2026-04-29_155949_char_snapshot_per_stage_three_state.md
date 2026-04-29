# char_snapshot_per_stage_three_state

- **Started**: 2026-04-29 15:59:49 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

承接 T-CHAR-SNAPSHOT-PER-STAGE 的 /plan 讨论（同会话）。原 todo 计划同时
做 prompt 三态规则 + schema stage_delta 结构化，但 T-BASELINE-DEPRECATE
已锁定"stage_delta 维持自由文本"——schema 部分被否决。/plan 把 todo
收敛为纯 prompt 改动，已在 commit `f48bcac` 改写并 sync 到三分支。

本 /go 落地收敛后的 prompt 改动。

## 结论与决策

按 [todo_list.md `T-CHAR-SNAPSHOT-PER-STAGE`](../../docs/todo_list.md)
当前条目执行：

- 在 `automation/prompt_templates/character_snapshot_extraction.md`
  「未出场角色的继承规则」段后追加：
  - **出场角色 / 字段的三态规则**：(B) 出场且有变化 → 重写 / (C) 出场
    且无变化 → 保留 / (D) resolved-revealed-消除 → 在 stage_delta 写明
    消除原因（与 maxItems 裁剪是两件不同的事）
  - **per-stage 推演原则**：除 character_arc 和 (A) 类继承外，所有字段
    必须基于本阶段原文 + prev_snapshot **推演得出**，不可静默照搬
- stage_delta 字段说明（现行 `核心规则 #2 列表中的 stage_delta 项`，
  非显式行号——需 grep 定位）补一句：自由文本应能体现 (B) 的关键变化
  和 (D) 的消除原因，不要写"无明显变化"敷衍

**作用域分界**：仅 prompt 改动 + ai_context/decisions.md 一行新决策注释。
**不动 schema**（stage_delta 维持自由文本，沿用 T-BASELINE-DEPRECATE
的拍板）。**不动代码**（prompt 模板由 prompt_builder.py 直接 read，无需
代码改）。Runtime 验证（跑 1-2 stage 抽查 stage_delta 是否捕捉到三态）
留作后续——本 /go 不跑 extraction。

## 计划动作清单

- file: `automation/prompt_templates/character_snapshot_extraction.md`
  → 在 `核心规则 #2` 列表中"未出场角色的继承规则"段后插入"出场角色 /
  字段的三态规则"+「per-stage 推演原则」两段（约 20 行 prompt 文字）
- file: `automation/prompt_templates/character_snapshot_extraction.md`
  → stage_delta 字段说明（在 `核心规则 #2` 的字段维度列表里）追加
  "应能体现 (B) 关键变化 + (D) 消除原因，不写"无明显变化"敷衍" 一句
- file: `ai_context/decisions.md` → 11d 决策项末尾追加一句指向
  prompt 三态规则
- file: `docs/todo_list.md` → T-CHAR-SNAPSHOT-PER-STAGE 整条移到
  `docs/todo_list_archived.md` 的 `## Completed` 段（瘦身：标题 + 完成
  形式 + 1 行摘要 + 本 log 链接）；从 todo_list.md 删除原条目；同步
  刷新顶部 Index

## 验证标准

- [ ] `grep -n "出场角色 / 字段的三态规则\|per-stage 推演原则" automation/prompt_templates/character_snapshot_extraction.md` 各命中 ≥ 1 行
- [ ] `grep -n "stage_delta" automation/prompt_templates/character_snapshot_extraction.md` 至少有一条新增的 "(B)/(D)" 提示
- [ ] `grep -n "T-CHAR-SNAPSHOT-PER-STAGE" docs/todo_list.md` = 0（已移走）
- [ ] `grep -n "T-CHAR-SNAPSHOT-PER-STAGE" docs/todo_list_archived.md` ≥ 1（已归档）
- [ ] todo_list.md 顶部 Index 与正文一致（Next 4 → 3，Total 12 → 11）
- [ ] 没有任何代码 / schema 改动（git status 只列 prompt + ai_context + 2 份 todo md）

## 执行偏差

发现 PRE 计划遗漏一个连带更新点（已纳入本 /go）：

- T-BASELINE-DEPRECATE 条目（仍在 In Progress 段）的 "依赖" 段引用了
  "与 T-CHAR-SNAPSHOT-PER-STAGE 部分解耦：PER-STAGE 仅在 prompt 文件
  上有改动重叠"——PER-STAGE 现已完成归档，引用过时；改为 "PER-STAGE
  已完成并归档" 描述

## 已落地变更

- `automation/prompt_templates/character_snapshot_extraction.md`：
  - 在「未出场角色的继承规则」段（[行 114](../../automation/prompt_templates/character_snapshot_extraction.md#L114)）后追加
    「出场角色 / 字段的三态规则（B/C/D 类）」段（[行 116-120](../../automation/prompt_templates/character_snapshot_extraction.md#L116-L120)）+
    「per-stage 推演原则」段（[行 122](../../automation/prompt_templates/character_snapshot_extraction.md#L122)）
  - stage_delta 字段说明（[行 107](../../automation/prompt_templates/character_snapshot_extraction.md#L107)）追加 "(B)
    类关键变化 + (D) 类消除原因 / 不写'无明显变化'敷衍" 提示
- `ai_context/decisions.md`：在 11e 后追加 11f 决策项，文档化 prev_stage
  四态规则 + per-stage 推演原则 + stage_delta 自由文本必须捕捉 (B)/(D)
  的契约
- `docs/todo_list_archived.md`：T-CHAR-SNAPSHOT-PER-STAGE 整条归档
  到 `## Completed` 段顶部（瘦身：标题 + 改方案后完成 + 1 行摘要 +
  log 链接）
- `docs/todo_list.md`：删除 T-CHAR-SNAPSHOT-PER-STAGE 整条；索引段
  Next 4→3 + Total 12→11；T-BASELINE-DEPRECATE 依赖段同步过时引用

## 与计划的差异

PRE 列了 4 项动作；实际 5 项（多了 T-BASELINE-DEPRECATE 依赖段过时
引用更新）。其余按计划。

## 验证结果

- [x] `grep -n "出场角色 / 字段的三态规则\|per-stage 推演原则" automation/prompt_templates/character_snapshot_extraction.md` 各命中 1 行
- [x] `grep -n "stage_delta" automation/prompt_templates/character_snapshot_extraction.md` 含新增 (B)/(D) 提示（L107）
- [x] T-CHAR-SNAPSHOT-PER-STAGE 在 todo_list.md = 0 条（仅剩 T-BASELINE-DEPRECATE 依赖段已更新过的引用，不再含原条目）
- [x] T-CHAR-SNAPSHOT-PER-STAGE 在 archived ≥ 1 条（顶部归档项）
- [x] todo_list.md 顶部 Index 与正文一致（Next 3 / Total 11）
- [x] 没有任何代码 / schema 改动（git status 显示 4 markdown + 1 新 log）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-29 16:10:58 EDT
