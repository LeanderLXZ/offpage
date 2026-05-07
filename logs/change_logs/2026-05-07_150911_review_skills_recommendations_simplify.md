# review_skills_recommendations_simplify

- **Started**: 2026-05-07 15:09:11 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

承接上轮 `d7e492b` (review_skills_findings_id_recommendations) 的 review skill 改造。用户反馈 4 项需求：
1. 强制 H/M/L finding 编号 → 已在 d7e492b 落地，**保留**
2. 末尾加 Recommendations 整改建议段 → 已在 d7e492b 落地，**保留**
3. Open Questions 倒数第二段、Recommendations 最后 → 已在 d7e492b 落地，**保留**
4. **Recommendations 只需要一个章节，不用太详细，只给"哪些要修 / 推荐哪个方案 / 哪些可跳过"** → d7e492b 当前是"性质 + 4 项硬性原则 + 三块内容（针对 Findings / 针对 OQ / 总览）"过度详细，**本轮简化**

进入 /go 时工作树呈 dirty 状态 = 用户手动回滚 d7e492b 内容到 pre-d7e492b 状态，作为信号"对当前 Recommendations 不满意"。已 `git restore .` 把工作树拉回 HEAD（clean），本轮在此基础上只做 #4 简化，#1/#2/#3 不动。

## 结论与决策

把 6 镜像文件的 `## Recommendations` 段（post-check Step 6 模板内 + full-review 输出格式第 5 项 + check-review 输出结构第 7 项）替换为一个简化版块——

简化后的内容：

```markdown
## Recommendations

**仅供参考，用户拍板优先**；不超出本次 scope 扩功能、不过度工程。

- **{H1/M1/L1}** → 建议{修 / 留 todo / 跳过}：{一句话理由 / 推荐方案}
- **OQ1** → 推荐{候选 A/B}：{一句话理由}
- ...
```

简化幅度：每个 skill 的 Recommendations 段从 ~20 行（含 4 原则列表 + 三块结构 + 各块示例）→ ~5 行（一个引导句 + 一个 flat list 模板）。

## 计划动作清单

- file: `.claude/commands/post-check.md` Step 6 模板内 `## Recommendations` 段（行 190-216 区间）→ 替换为简化版
- file: `.agents/skills/post-check/SKILL.md` 同段落镜像替换
- file: `.claude/commands/full-review.md` 输出格式第 5 项 `Recommendations`（行 90-101 区间）→ 替换为简化版
- file: `.agents/skills/full-review/SKILL.md` 同段落镜像替换
- file: `.claude/commands/check-review.md` 输出结构第 7 项 `Recommendations`（行 58-70 区间）→ 替换为简化版
- file: `.agents/skills/check-review/SKILL.md` 同段落镜像替换
- file: `logs/change_logs/2026-05-07_150911_review_skills_recommendations_simplify.md` — 本日志

## 验证标准

- [ ] 6 镜像文件 `# /<name> ... 镜像约束之前` 主体逐字一致 diff 通过
- [ ] 6 文件 grep `^## Recommendations|5\. \`Recommendations\`|7\. \`Recommendations\`` 仍各 1 处（段未消失）
- [ ] 6 文件 Recommendations 段总长缩减：post-check 段从 ~22 行 → ~5 行；full-review 第 5 项 ~12 行 → ~5 行；check-review 第 7 项 ~13 行 → ~5 行
- [ ] 6 文件保留"仅供参考，用户拍板优先"+"不过度工程 / 不超出 scope"两个关键短语（防御过度工程倾向）
- [ ] 6 文件保留 H1/M1/L1 + OQ1 命名引用（与 #1 编号约束一致）
- [ ] post-check 段顺序 Alignment Summary → Residual Risks → Open Questions → Recommendations 不变
- [ ] full-review 输出格式 1-5 项顺序不变
- [ ] check-review 输出结构 1-7 项顺序不变
- [ ] 旧"4 项硬性原则" / "段内分三块"措辞 grep 残留 = 0

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

修改（6 件 mirror）+ 1 新 log：
- `.claude/commands/post-check.md` 行 190-216 区间 `## Recommendations` 段（位于 Step 6 模板内）→ 简化为引导句 + flat list 模板，删除"性质 / 4 项硬性原则 / 段内分三块（针对 Findings / 针对 OQ / 总览）" 共 ~20 行细分结构
- `.agents/skills/post-check/SKILL.md` 行 195-218 区间镜像同步
- `.claude/commands/full-review.md` 输出格式第 5 项 `Recommendations`（行 90-101 区间）→ 简化为引导句 + flat list 描述
- `.agents/skills/full-review/SKILL.md` 输出格式第 5 项镜像同步
- `.claude/commands/check-review.md` 输出结构第 7 项 `Recommendations`（行 58-70 区间）→ 简化为引导句 + flat list 描述
- `.agents/skills/check-review/SKILL.md` 输出结构第 7 项镜像同步
- `logs/change_logs/2026-05-07_150911_review_skills_recommendations_simplify.md` — 本日志

简化幅度：post-check Recommendations 段从 ~22 行 → ~5 行（保留段头 + 引导句 + 3 行 list 模板）；full-review / check-review 第 5/7 项各从 ~12 行 → ~3 行（1 引导子项 + 1 flat list 子项）。总 diff: 6 文件 +14/-78（净减 64 行）。

保留：H1/M1/L1 编号约束（#1）+ Open Questions 倒数第二段位（#3）+ "仅供参考，用户拍板优先" + "不过度工程"两个关键短语 + 镜像逐字一致性。

## 与计划的差异

无。

## 验证结果

- [x] 镜像逐字 diff: post-check / full-review / check-review 三对全过（SC1）
- [x] 6 文件 `## Recommendations` / `5. Recommendations` / `7. Recommendations` 各 1 处（段未消失，SC2）
- [x] 旧措辞 grep 残留 0：'硬性原则.*每轮报告都重申' / '段内分三块' / '### 总览' / '针对 Findings$' / '针对 Open Questions$' 在 6 文件中全 0（SC3）
- [x] 关键短语保留：3 个 .claude 文件各 1 个 '仅供参考，用户拍板优先' + 1 个 '不过度工程'（SC4）
- [x] H1/M1/L1/OQ1 命名仍存在：post-check 各 6 hits / full-review 各 3 hits / check-review 各 2 hits（SC5；与 #1 编号约束保持一致）
- [x] 段顺序保留：post-check `Alignment Summary (181) → Residual Risks (184) → Open Questions (187) → Recommendations (190)`；full-review 1-5 项顺序；check-review 1-7 项顺序（SC6）

## Completed

- **Status**: DONE
- **Finished**: 2026-05-07 15:13:49 EDT
