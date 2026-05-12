# post_check_followup_data_model

- **Started**: 2026-05-12 18:10:10 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

上一轮 `/post-check` (commit `ac96f71` REVIEWED-PARTIAL) 复审本会话
`/go` (commit `69146cc` full_review_findings_fixes) 时发现 2 Medium + 1
Low + 1 OQ：

- **M1** `docs/architecture/data_model.md:325-332` character canon 段漏列
  `canon/extraction_notes/{stage_id}.jsonl`（与本次 /go M9 同源；
  works/README + schema_reference.md:500 已列；data_model 是 pre-existing
  漂移，本次 M9 触发暴露）
- **M2** `docs/architecture/data_model.md:505-515` `## indexes/` 子节
  "推荐内容" 列表无"尚未启用"标注（与本次 /go M14 同源；data_model.md
  line 176 顶级 "可选内容" 段已写 "尚未启用" 但 §Indexing 子节漂移；
  works/README M14 修后形成 cross-file 局部不一致）
- **L1**（L12 fail-loudly 边界）— 跳过（用户表态）
- **OQ1**（候选 a/b/c）— 用户选 a = 现在补

用户拍板：M1 + M2 修，L1 + 其他全跳过。

## 结论与决策

**本轮要修**：M1 + M2 两处 `docs/architecture/data_model.md` docs 对齐，
每处 ≤1 行新增。

**显式不做**：不动 L1（L12 fail-loudly 边界，用户跳过）；不动 ai_context
/ schema / code / prompt / 其他 docs；不写 todo（本会话 PRE/POST 一致
策略）；不引入新决策编号（沿用 #25a / #54 / #55 既有）。

## 计划动作清单

- file: `docs/architecture/data_model.md`
  - M1：line 325-332 character canon 段补一行
    `canon/extraction_notes/{stage_id}.jsonl — repair_agent SourceNote
    写入路径（决策 #25a）`，紧接 `memory_digest.jsonl` 行后
  - M2：line 505-515 `## indexes/` 子节"推荐内容"列表末尾或顶部补一行
    "尚未启用"标注，与同文 line 176 顶级 "可选内容" 段一致；可选指向
    `works/README.md indexes/` 树标注

## 验证标准

- [ ] `grep -n "extraction_notes" docs/architecture/data_model.md` 命中 ≥ 1
- [ ] `grep -n "尚未启用" docs/architecture/data_model.md` 命中 ≥ 2
  （原 line 176 顶级提示 + 新 §Indexing 子节）
- [ ] `git diff` 仅触及 `docs/architecture/data_model.md` 单文件（+ log）
- [ ] 修复后 works/README + schema_reference + data_model 三方对
  `extraction_notes/` 路径表述一致

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

- `docs/architecture/data_model.md`
  - M1：line 333-335 character canon 段在 `memory_digest.jsonl` 后补 3
    行 `canon/extraction_notes/{stage_id}.jsonl` 条目 + 引用决策 #25a +
    指向 `schemas/shared/source_note.schema.json`
  - M2：line 513-516 `## indexes/` 子节"推荐内容"前加 blockquote
    "整棵子树尚未启用"标注 + 引用同文 line 176 顶级提示；列表标题
    `推荐内容：` → `推荐内容（占位）：`

## 与计划的差异

PRE 计划全部落地，无偏差。

## 验证结果

- [x] `grep -c "extraction_notes" docs/architecture/data_model.md = 1`
- [x] `grep -c "尚未启用" docs/architecture/data_model.md = 2`（原 line
  176 + 新 line 513）
- [x] `git diff --stat` 仅触及 `docs/architecture/data_model.md`（+1 log）
- [x] works/README + schema_reference + data_model 三方对
  `extraction_notes/` 路径表述一致（手工核对三方均写
  `canon/extraction_notes/{stage_id}.jsonl`）

## Completed

- **Status**: DONE
- **Finished**: 2026-05-12 18:12:21 EDT
