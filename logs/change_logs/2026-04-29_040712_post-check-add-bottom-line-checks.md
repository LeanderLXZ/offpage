# post-check-add-bottom-line-checks

- **Started**: 2026-04-29 04:07:12 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

会话内讨论：`/post-check` 当前 Step 4「重点检查项」缺 4 类有价值的兜底：

- A. **todo_list 漂移**：本次实质完成了某 todo 条目但没移到 archived
- B. **commit message vs 实际 diff 匹配度**：commit body 描述 vs diff 不一致，git log 长期可见
- C. **change_log / docs 内部引用链接断链**：log 引用 #25 但已改成 #26、archived 关联 log 路径打错等
- D. **悬挂引用 / 过度删除**：diff 删了某符号但 grep 仍有引用方未更新

放轨 1 还是轨 2？决议：A 命中 → Missed Updates（轨 1，对账型）；B/C/D 命中 → Findings（轨 2，扩散型）。

## 结论与决策

只在 Step 4「重点检查项」flat list 里加 4 行，**不重排结构、不另起轨道**。次序：

```
- 跨文件不一致：……
- 歧义：……
- 冲突：……
- 残留旧逻辑 / legacy 措辞：……
- 悬挂引用 / 过度删除：……   ← 新增 D（与"残留旧逻辑"反向，紧邻它）
- change_log / docs 内链断链：……   ← 新增 C
- todo_list 漂移：……   ← 新增 A
- bug / 行为风险：……
- README / 目录结构：……
- ai_context 漂移：……
- commit message vs diff 匹配度：……   ← 新增 B（最后做收口）
```

不动 Step 1 / Step 2 / Step 3 / Step 5 / Step 6 / Step 7 流程；仅扩 Step 4 列表。

不加（讨论过的非候选，待 `/full-review` 或别处覆盖）：配置向后兼容、测试覆盖回退、import 循环 / 死代码、Cross-File Alignment 反向更新、Skill 镜像同步。

## 计划动作清单

镜像约束：4 份正文逐字一致——

- file: `.claude/commands/post-check.md` Step 4 — 在「残留旧逻辑」后插入 D，「README / 目录结构」前依次插入 C / A，列表末尾追加 B
- file: `.agents/skills/post-check/SKILL.md` Step 4 — 同步同位置同措辞（YAML frontmatter 不动）

每条新增的措辞（落到镜像里时直接写）：

```
- **悬挂引用 / 过度删除**：本次 diff 若删除了符号 / 文件 / 段落，grep 仓库剩余位置是否还有引用方未更新；这是「残留旧逻辑」的反向——旧目标已没，旧引用还在
- **change_log / docs 内链断链**：本次 log 或修改过的 docs 里引用 `decisions.md #25` / `[xxx](path)` / `详见 logs/change_logs/.../X.md` 等，核对编号未漂移、相对路径存在、anchor 锚点真实
- **todo_list 漂移**：本次改动若实质完成了某 todo 条目（PRE log 「完成标准」段含「本 todo 条目移到 archived」、或 diff 等价于某条 Next/Discussing 条目的「改动清单」），核对 `docs/todo_list.md` 该条目是否已整条移到 `docs/todo_list_archived.md` `## Completed` + Index 段是否同步刷新。漏移 → 列入 Missed Updates
- **commit message vs diff 匹配度**：commit body 描述 vs `git diff --stat` 实际改动 是否互相覆盖——body 列了 N 处但 diff 只动 M 处，或 diff 改了文件 body 没提
```

## 验证标准

- [ ] `.claude/commands/post-check.md` 与 `.agents/skills/post-check/SKILL.md` 正文（从一级标题 `# /post-check` 起到末尾镜像约束段）逐字一致——`diff <(awk '/^# \/post-check/,0' .claude/commands/post-check.md) <(awk '/^# \/post-check/,0' .agents/skills/post-check/SKILL.md)` 返回空
- [ ] Step 4 列表共 11 项（原 7 + 新 4）
- [ ] grep 验证 4 条新增 keyword（"悬挂引用"、"change_log / docs 内链断链"、"todo_list 漂移"、"commit message vs diff"）在两份镜像各出现 1 次
- [ ] 其它步骤（Step 1 / 2 / 3 / 5 / 6 / 7 / 约束段）未被改动

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

- `.claude/commands/post-check.md` Step 4 列表
  - 「残留旧逻辑」后插入「悬挂引用 / 过度删除」（D）
  - 接着插入「change_log / docs 内链断链」（C）
  - 接着插入「todo_list 漂移」（A）
  - 列表末尾追加「commit message vs diff 匹配度」（B）
- `.agents/skills/post-check/SKILL.md` Step 4 列表 — 同位置同措辞镜像同步

Step 1 / 2 / 3 / 5 / 6 / 7 / 镜像约束段未触及。

## 与计划的差异

无

## 验证结果

- [x] 镜像正文逐字一致 — `diff <(awk '/^# \/post-check/,0' ...)` 返回空（"OK: 镜像正文逐字一致"）
- [x] Step 4 列表共 11 项 — 两份镜像各 11 个 `- **`-prefix 行
- [x] 4 条新增 keyword 在两份镜像各出现 1 次 — grep 验证
- [x] 其它步骤未被改动 — 只 edit 了 Step 4 段落

## Completed

- **Status**: DONE
- **Finished**: 2026-04-29 04:09:19 EDT
