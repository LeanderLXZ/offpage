# skill_descriptions_green_tier_dedup

- **Started**: 2026-05-14 11:38:32 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

会话上下文：用户让我审计 14 个 skill/command 文件（`.claude/commands/` 8 份 + `.claude/skills/` 6 份，每份有 `.agents/skills/X/SKILL.md` 镜像，共 28 个文件 14 对镜像）有没有啰嗦、冗杂、过度、没必要的话语。

我交付了"按文件 + 跨文件共性"两层分析，标注 14+ 处冗余点并按风险分三档（🟢 几乎零风险 / 🟡 需要小心改写 / 🔴 不该动）。

用户问"修改后不影响 skills 的功能效果吧"——我诚实回答**部分有风险**，把改动重新划档：
- 🟢 真正零风险（纯重复 / 同文件内交叉）
- 🟡 信息密度变化（措辞本身是功能）
- 🔴 不该动（frontmatter description / fail-loudly 三态措辞）

用户拍板：「帮我先把绿色的部分改了吧 /go」。

## 结论与决策

本轮 scope = **仅绿色档**，目标"零功能影响下的去重瘦身"：

### 在 scope
1. **约束段去重**——10 个文件的"约束 / 限制"末段里，**正文已写过的硬规则**条目删掉，只留正文未出现的真硬底线 + 真"meta"规则
2. **`/full-review` 自身内部交叉去重**——「额外要求」段 5 条里 4 条与「重点检查项」语义重复，删该段并把唯一独立的"重点放在真实影响"hint 并入「审计要求」尾部
3. **`/recent-activity` "延后读取"三处声明 → 两处**——通过 (1) 的约束段去重自然实现（约束段最后那条 delayed-read bullet 删掉，保留 Step 3a 的指针 + Step 5b 的机制）

### 不在 scope（推迟到第二轮）
- 🟡 Progress reporting 五连模板压缩
- 🟡 `/go` 子任务展开规则 240→30 字
- 🟡 `/plan` 零写规则 4 句合 1
- 🟡 `/post-check` "输出顺序"4 处 → 1 处
- 🟡 `/post-check` 重点检查项 vs `/full-review` 重点检查项跨文件去交叉
- 🟡 `/commit` auto-sync 双子流程合表
- 🟡 `/todo-add` CREATE/UPDATE 差量重写
- 🔴 镜像 footer 统一改写——文字虽是冗余但路径错改会立刻复发 24a0d6e 修过的 self-reference bug，留下一轮专门做
- 🔴 frontmatter `description` 缩短——是 skill router 的激活信号
- 🔴 fail-loudly 三态模板压缩——节列表 per-skill 真信息

## 计划动作清单

每个 `.claude/` 文件改完必须**同 commit** 镜像到对应 `.agents/skills/X/SKILL.md`（body 逐字一致，`.agents` 侧多 YAML frontmatter；`.claude/skills/` 侧两边都有 frontmatter）。镜像 footer 本身**不动**（仍按当前两套口径写）。

### 1. `/commit` 约束段（8 行 → 2 行）
- file: `.claude/commands/commit.md` L94-101 + 镜像 `.agents/skills/commit/SKILL.md`
- 删：「只提交本次 working tree 改动」「不 add -A」「forward 必须经用户确认 / auto-sync 跳过询问」「发现可疑停手问」(正文 Step 1-5 都已显式写)
- 留并合并：不 push / --force / --amend；auto-sync 仅本地，永不 push；可疑路径停手问

### 2. `/push` 约束段（5 行 → 2 行）
- file: `.claude/commands/push.md` L46-52 + 镜像
- 删：「只 push 一个分支」「不 commit/merge/rebase」「behind>0 停手」「不替用户 push 非追踪」(正文 Step 1-3 都已写)
- 留并合并：不 --force 类（除非授权）+ 不动 working tree；非正常状态停手问

### 3. `/post-check` 约束段（6 行 → 2 行）
- file: `.claude/commands/post-check.md` L207-214 + 镜像
- 删：「不是全仓 review」「只读 + 单写单 commit 例外」「双轨都跑」「文件+行号」(正文 L3-5 + Step 5 + Step 3-6 都已写)
- 留：「不走过场」（meta）+「输出顺序硬约束」（黄档不动，原样保留）

### 4. `/todo-add` 约束段（17 行 → 4 行）
- file: `.claude/commands/todo-add.md` L161-178 + 镜像
- 删：「不动无关段位」「ID 查重必须做」「预览必须等确认」「会话不清晰主动问」「ID 不变（已在 Step 3/5）」「索引规则单源（已在 Step 6）」(正文 Step 2-6 + Step 5 都已显式写)
- 留：不 commit / 不 push；UPDATE 优先 CREATE + 多条疑似命中要问；In Progress 单槽；索引单源指向位置

### 5. `/branch-inventory` 限制段（4 行 → 2 行）
- file: `.claude/skills/branch-inventory/SKILL.md` L73-78 + 镜像
- 删：「不执行建议动作（已在 L66）」「skills_config 降级（已在 L18）」
- 留：只读完整动作清单（这是 itemized 有价值的）+ 分支数 > 50 截断（NEW）

### 6. `/extraction-status` 限制段（4 行 → 2 行）
- file: `.claude/skills/extraction-status/SKILL.md` L78-82 + 镜像
- 删：「skills_config 缺失停手（已在 L18）」「pgrep/kill -0 显式声明」(可并入只读条)
- 留：只读完整 mutating 禁单 + 不读巨型 log（NEW）

### 7. `/monitor` 约束段（5 行 → 3 行）
- file: `.claude/skills/monitor/SKILL.md` L72-78 + 镜像
- 删：「问题只报不修（已在 Step 4 L58/60）」「速率标注样本（已在 Step 3）」
- 留：只读 mutating 禁单；汇报紧凑只报变化（NEW）；顺带报但不抢主场景（NEW）

### 8. `/recent-activity` 约束段（13 行 → 2 行）
- file: `.claude/skills/recent-activity/SKILL.md` L151-164 + 镜像
- 删：只读（已 L14）、skills_config fail-loudly（已 L23）、ISO 8601（已 Step 6）、当前分支（已 Step 2）、--no-merges（已 Step 2）、缺更新时间字段跳过（已 Step 4）、3*N 过采样（已 Step 2/Step 4）、正文截断 25 行（已 Step 2/5b）、**延后读取（已 Step 3a + 5b）**、块视图（已 Step 6）
- 留：只读简短一行（itemized 有用）+ 不接受时间窗参数（NEW）

### 9. `/run-prompt` 限制段（5 行 → 4 行）
- file: `.claude/skills/run-prompt/SKILL.md` L54-60 + 镜像
- 删：「解析失败立即停手」(Step 0/1 已显式)
- 留其余 4 条（都是 NEW meta）

### 10. `/todo` 约束段（6 行 → 2 行）
- file: `.claude/skills/todo/SKILL.md` L47-54 + 镜像
- 删：不解析正文 / 不重新分档 / 不生成建议 / 逃生口 / $ARGUMENTS 仅过滤（正文 L8 + L10 + L31 + Step 4 都已写）
- 留：只读完整 + 信任索引段（带索引规则单源指向）

### 11. `/full-review` 内部交叉去重（5 行 → 0 行）
- file: `.claude/commands/full-review.md` L125-131 「额外要求」段 + 镜像
- 删 5 条中前 4 条（"文档冲突 / ai_context 过时 / 样例不一致 / 检查器盲区"在「重点检查项」L49-58 都已覆盖）
- 唯一独立的"覆盖全仓库但重点真实影响"hint → 并入「审计要求」L74 之后或「重点检查项」段首
- 整段「## 额外要求」删除

## 验证标准

- [ ] **镜像逐字一致**：每个改动的 `.claude/X` 与对应 `.agents/skills/X/SKILL.md` 用 `diff` 比对正文，零差异（仅 footer 路径方向 + frontmatter 在不同侧）
- [ ] **行数缩减验证**：22 个 `.claude/` + `.agents/` 配对文件按上述目标行数缩减（约束段从 78 行总体降到 ~25 行）
- [ ] **正文未涉及**：除上面列出的「约束 / 限制 / 额外要求」段，其他正文一字不改（`git diff --stat` 显示只有 footer 区域之前最后一段的改动）
- [ ] **frontmatter 未涉及**：`.agents/` 侧 + `.claude/skills/` 侧的 YAML frontmatter 一字不改（这是黄档 / 红档）
- [ ] **镜像 footer 未涉及**：所有 `---\n**镜像约束**...` footer 段一字不改（避免复发 24a0d6e self-reference bug）
- [ ] **`/full-review` 不出现「## 额外要求」二级标题**（grep 残留 = 0）

## 执行偏差

- **Step 4k `/full-review` 额外要求段处理**：PRE 计划"删 5 条中 4 条 + 唯一独立的 'priority hint' 并入审计要求"过激进。重审后 L127 ("文档冲突 → 哪个是更高优先级真相") 与 L128 ("ai_context 过时 → 如何误导后续 AI") 是 finding **表达技巧**（不是 check 重复），与「重点检查项」语义不重叠。改为 merge L127+L128 合 1 条 + L131 priority hint 1 条入「审计要求」末尾；删 L129 / L130（与「重点检查项」L59 / L57-58 是纯 check 重复）+ 段头。
- **Step 4k 接受的小幅 nuance 损失**：原 `额外要求` L130 "检查器盲区 → **高优先级**处理" 的 severity-tagging hint 未显式保留——评估为「审计要求」的"影响范围"通用要求 + "findings 按严重性排序"可吸收，且重写 severity hint 已超绿档 scope。如未来发现 AI 实际把 checker-blind-spot 类 finding 误判 Medium，再恢复一行。

<!-- POST 阶段填写 -->

## 已落地变更

22 个文件改动（净 -96 行：32 insertions / 128 deletions）。改动**仅集中在末尾"约束 / 限制 / 额外要求 / 审计要求"段**，正文 + frontmatter + 镜像 footer 一字未动。

**11 对镜像（每对 .claude/ + .agents/ 两侧逐字同步）**：

| skill | 节标题 | 改前 | 改后 |
|---|---|---|---|
| /commit | `## 约束` | 8 行 | 2 行 |
| /push | `## 约束` | 5 行 | 2 行 |
| /post-check | `## 约束` | 6 行 | 2 行 |
| /todo-add | `## 约束` | 17 行 | 4 行 |
| /branch-inventory | `## 限制` | 4 行 | 2 行 |
| /extraction-status | `## 限制` | 4 行 | 2 行 |
| /monitor | `## 约束` | 5 行 | 3 行 |
| /recent-activity | `## 约束` | 13 行 | 2 行 |
| /run-prompt | `## 限制` | 5 行 | 4 行 |
| /todo | `## 约束` | 6 行 | 2 行 |
| /full-review | `## 审计要求` + `## 额外要求` | 12 + 5 = 17 行（两段）| 13 行（合并到审计要求，删除额外要求段头）|

具体改动位置：
- `.claude/commands/commit.md` L94-101 + `.agents/skills/commit/SKILL.md` L99-107
- `.claude/commands/push.md` L46-52 + `.agents/skills/push/SKILL.md` L51-57
- `.claude/commands/post-check.md` L207-214 + `.agents/skills/post-check/SKILL.md` L212-219
- `.claude/commands/todo-add.md` L161-178 + `.agents/skills/todo-add/SKILL.md` L166-183
- `.claude/skills/branch-inventory/SKILL.md` L73-78 + `.agents/skills/branch-inventory/SKILL.md` L73-78
- `.claude/skills/extraction-status/SKILL.md` L77-82 + `.agents/skills/extraction-status/SKILL.md` L77-82
- `.claude/skills/monitor/SKILL.md` L72-78 + `.agents/skills/monitor/SKILL.md` L72-78
- `.claude/skills/recent-activity/SKILL.md` L151-164 + `.agents/skills/recent-activity/SKILL.md` L151-163
- `.claude/skills/run-prompt/SKILL.md` L54-60 + `.agents/skills/run-prompt/SKILL.md` L54-60
- `.claude/skills/todo/SKILL.md` L47-54 + `.agents/skills/todo/SKILL.md` L47-54
- `.claude/commands/full-review.md` L62-76 + L125-131 + `.agents/skills/full-review/SKILL.md` L67-81 + L130-136

## 与计划的差异

PRE 计划改动量与实际一致：**11 个 skill × 2 镜像 = 22 文件**。
唯一与 PRE 不同：`/full-review` 处理方式比 PRE 计划保留更多 nuance（详见上文"执行偏差"段）。

## 验证结果

- [x] **镜像逐字一致**：11/11 mirror pairs 用 `diff` 验证 body 区域零差异（执行中 inline 验证 + Step 5 汇总 ALL OK）
- [x] **行数缩减**：净 -96 行（32 insertions / 128 deletions across 22 files）
- [x] **正文未涉及**：除上述列出的「约束 / 限制 / 审计要求 / 额外要求」段，正文一字未改（diff 输出全部集中在这些末尾段）
- [x] **frontmatter 未涉及**：`.agents/` 侧 + `.claude/skills/` 侧的 YAML frontmatter 一字未动
- [x] **镜像 footer 未涉及**：所有 `---\n**镜像约束**...` footer 段一字未动（避免复发 24a0d6e self-reference bug）
- [x] **`/full-review` 不出现「## 额外要求」二级标题**：`grep -rn '^## 额外要求' .claude/ .agents/` 返回 0

## Completed

- **Status**: DONE
- **Finished**: 2026-05-14 11:59:10 EDT
