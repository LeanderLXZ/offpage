# review_skills_findings_id_recommendations

- **Started**: 2026-05-07 14:59:22 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

用户对 3 个 review skill 的输出格式提出 3 项一致改进：
1. **强制 H/M/L finding 编号**：每条 finding 必须打 `H1` / `H2` / `M1` / `L1` 这样的序号 ID（同优先级内 1-起递增），方便后续在 /go / /post-check / 对话中精准引用某条
2. **加 Recommendations 段**：报告末尾给出 AI 对 Findings + Open Questions 的整改建议（including AI 对 Open Questions 的方向性建议），但**强制带上"不要过度工程"提醒**——AI 倾向把建议放大成大改造、Open Questions 倾向替用户拍板，规则要明确
3. **重排末尾段顺序**：当前 Open Questions 放在 Findings 后、Alignment Summary / Residual Risks 之前；改为 Open Questions 放在最后第二块、Recommendations 是最后一块——让用户读完背景 / Findings / 风险后再看到不确定项 + 建议

涉及 3 个 skill 各自的对话输出模板：`post-check`（Step 6 双轨报告）/ `full-review`（输出格式）/ `check-review`（输出结构）。每个 skill 都有镜像（`.claude/commands/<name>.md` ↔ `.agents/skills/<name>/SKILL.md`），共 6 文件。

## 结论与决策

每个 skill 的报告模板做 3 项改造（**只动模板和约束文字，不动流程步骤 / Step 编号 / log 回写格式**）：

A. **强制编号约束**：在「输出格式 / 输出结构 / Step 6 模板」里明示——同优先级内从 1 起递增（`H1`、`H2`、`H3`...；`M1`、`M2`...；`L1`、`L2`...）。建议命名：`**H1**` / `**M1**` / `**L1**`，markdown 加粗以保持视觉权重；模板示例同步刷成新格式

B. **重排末尾段**：把 `Open Questions` 从中段（Findings / 轨 2 之后）移到末尾倒数第二段；新增 `Recommendations` 作为最后一段。新顺序 = `... → Alignment Summary → Residual Risks → Open Questions → Recommendations`

C. **新加 Recommendations 段**：模板里说明三层内容：
   - **针对 Findings 的整改建议**：对每条 H/M/L 给"建议做 / 建议留作 todo / 建议跳过"+ 一句话理由
   - **针对 Open Questions 的方向性建议**：每个 Open Question 给 1-2 条候选方向 + 推荐项 + 一句话理由，**明确"用户拍板优先，本节仅供参考"**
   - **anti-overengineering 提醒**：硬约束行——`原则：不超出本次 intent / 报告 scope 扩功能；能 1 行修就别写 10 行；Open Questions 给方向不替用户做选择；推荐保守路径而非"全部修"`

D. **post-check Step 5 log 摘要小同步**：`Findings: High={h} / Medium={m} / Low={l}` 保留计数（这里是计数摘要，不是 ID 列表，不需展开），但把"Open Questions: {q} 条"挪到统一段位（不影响 log 格式契约的 PASS/PARTIAL/FAIL 判定）

**不改的事**：不动 Step 编号、不动 progress reporting 段、不动结果归档路径 / 命名约定、不动镜像约束段、不动 commit message 格式。

## 计划动作清单

- file: `.claude/commands/post-check.md` → Step 6 模板（行 158-184 区间）：(1) Findings 列表示例改为 `**H1**` / `**M1**` / `**L1**`；(2) Open Questions 段从行 177 移到 Residual Risks 之后；(3) 新增 Recommendations 段为模板最后一段；(4) Step 6 段头描述与 Step 7 / 约束段相应文案小同步（"完整报告就是 /post-check 输出的最后一段实质内容" → 仍然成立，因 Recommendations 仍是报告内）
- file: `.agents/skills/post-check/SKILL.md` → 与 `.claude/commands/post-check.md` 同步（镜像约束一致）
- file: `.claude/commands/full-review.md` → 输出格式段（行 78-88 区间）：(1) Findings 描述加"严重性内编号 H1/M1/L1"；(2) 在 Residual Risks 之后加 Open Questions 段（原本在第 2 项位置，现移到末尾倒数第二）；(3) 新增 Recommendations 作为输出格式第 5 项
- file: `.agents/skills/full-review/SKILL.md` → 与 `.claude/commands/full-review.md` 同步
- file: `.claude/commands/check-review.md` → 输出结构段（行 47-56 区间）：(1) Per-Finding Review 描述加"沿用 source report 的 ID 标号 + 复核后保持同 ID"；(2) Open Questions for User 从第 6 项移到倒数第二项；(3) 新增 Recommendations 作为第 7 项
- file: `.agents/skills/check-review/SKILL.md` → 与 `.claude/commands/check-review.md` 同步

## 验证标准

- [ ] 6 个文件改完后，`diff .claude/commands/post-check.md .agents/skills/post-check/SKILL.md` 仅在 YAML frontmatter（一边有一边没）+ 镜像约束段（路径互引）有差异，**正文逐字一致**（用 `sed -n '/^# \/post-check/,/^---$/p'` 提取后 diff 应只剩极小差）
- [ ] 同样 diff 验证 full-review / check-review 两对镜像
- [ ] 6 文件中 grep `\*\*\[H\]\*\*` / `\*\*\[M\]\*\*` / `\*\*\[L\]\*\*` 残留 = 0（旧 unindexed 格式应替换为 `**H1**` 等示例）
- [ ] 6 文件中 grep `^## Recommendations$` 命中正文中应有的位置（每个 skill 报告模板新增段）
- [ ] 模板顺序结构上 Open Questions 在 Recommendations 之前、在 Residual Risks 之后（用 grep -n 提取行号验证顺序）
- [ ] 每个 skill 的 Recommendations 段都包含"不过度工程 / overengineering"字眼 + "用户拍板优先"字眼

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

修改（6 件 mirror 文件 + 本日志）：

post-check 报告模板（Step 6 模板段）：
- `.claude/commands/post-check.md` 行 158-185 区间整段重写：
  - Findings 列表示例从 `**[H]** / **[M]** / **[L]**` 改为 `**H1** / **H2** / **M1** / **L1**`
  - 加"强制带序号 ID"约束段（同优先级内 1 起递增、不重排、撤回保留占位）
  - 末尾段顺序调整：原 `Open Questions → Alignment Summary → Residual Risks` 改为 `Alignment Summary → Residual Risks → Open Questions → Recommendations`
  - 新增 `## Recommendations` 段（性质 + 4 项硬性原则 + 三块内容：针对 Findings / 针对 OQ / 总览）
- `.agents/skills/post-check/SKILL.md` 行 158-185 区间镜像同步

full-review 输出格式段：
- `.claude/commands/full-review.md` 行 78-88 区间扩成 1-5 项：
  - 第 1 项 Findings 加强制 H1/M1/L1 编号 + 不重排约束
  - 顺序改为 `Findings → Alignment Summary → Residual Risks → Open Questions → Recommendations`
  - 新增第 5 项 `Recommendations`（同 post-check 的硬性原则 + 三块内容）
- `.agents/skills/full-review/SKILL.md` 行 83-93 区间镜像同步

check-review 输出结构段：
- `.claude/commands/check-review.md` 行 47-56 区间扩成 1-7 项：
  - 第 2 项 Per-Finding Review 加"强制沿用 source report finding ID + 复核后保留同 ID"约束
  - 第 3-5 项加"按 ID 引用，不改名"约束
  - 新增第 7 项 `Recommendations`
- `.agents/skills/check-review/SKILL.md` 行 52-61 区间镜像同步

新增 1 件：
- `logs/change_logs/2026-05-07_145922_review_skills_findings_id_recommendations.md` — 本日志

## 与计划的差异

无。计划 6 文件全部按 PRE 计划改动；4 项硬性原则 + 三块内容结构在 3 个 skill 间保持一致措辞。

## 验证结果

- [x] 6 镜像逐字 diff: post-check / full-review / check-review 三对镜像在"# /<name>"起到"镜像约束"前的主体逐字一致（SC1）
- [x] 旧 `**[H]**` / `**[M]**` / `**[L]**` 残留 = 0（SC2）
- [x] 6 文件均有 `H1` / `M1` / `L1` 命名出现：post-check 各 4 hits（含模板示例 + 约束说明 + 序号规则）/ full-review 各 1 hit / check-review 各 1 hit（SC3）
- [x] 6 文件均有 `## Recommendations` / `5. Recommendations` / `7. Recommendations` 命中 1 处（SC4）
- [x] post-check 段顺序：Alignment Summary (181) → Residual Risks (184) → Open Questions (187) → Recommendations (190)（SC5 ✓ Open Questions 倒数第二、Recommendations 最后）
- [x] full-review 段顺序：1. Findings → 2. Alignment Summary → 3. Residual Risks → 4. Open Questions → 5. Recommendations（SC6 ✓）
- [x] check-review 段顺序：1. Source Report → 2. Per-Finding → 3. Revised Priority → 4. Proposed Plan → 5. Deferred → 6. Open Questions → 7. Recommendations（SC7 ✓）
- [x] 3 skill 各含"不超出本次/scope/source report"硬约束 + "用户拍板优先"措辞（SC8 各 hit=1）
- [x] 跨 skill 检查：grep `[H]` / `[M]` / `[L]` 老格式在其他 .claude/commands/ + .agents/skills/ 目录下残留 0；/go skill 不引用 review finding 编号格式（无连带更新）

## Completed

- **Status**: DONE
- **Finished**: 2026-05-07 15:04:54 EDT
