# todo-workflow-redesign

- **Started**: 2026-04-27 16:16:04 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

`/todo` skill 当前每次调用都让 LLM 重做"读全文 → 解析 8 条任务字段 → 三档分类推断 → 生成主表 → 生成 2-4 条建议"全套；解析+分档本质是确定性算法，跑在 LLM 上既慢又不稳定（同份输入不同次跑分类边界会摇）。同时现有"立即执行 / 下一步"两段定位模糊（"立即执行"既是高优先级队列又是"下一个该做的"），任务真正"正在跑"的中间态没有归处——/go 启动后到 commit 完成之间任务卡在哪一段说不清。

讨论收敛到：

1. 把"解析+分档"的结果**缓存到 todo_list.md 顶部 `## 索引` 段**（含三张子表，每段列定义不同）
2. 索引由 LLM 在每次添加 / 修改 todo 条目时**顺手维护**——不写 Python 脚本、不挂 hook，只在 todo_list.md 文件开头写清规则（怎么写条目 + 怎么维护索引），让 Claude 读到规则就知道维护
3. `/todo` skill **彻底简化**：只读索引段渲染 + 提一句"想看哪条？"，删掉所有解析 + 分档 + 建议生成逻辑
4. 新增 `docs/todo_list_archived.md`，分 `## 已完成` / `## 废弃`；任务完成 / 废弃后**整条移到归档**（瘦身存档），不再"立即从 todo_list 删除"
5. **立即执行 → 正在执行**重命名：单槽位，/go 启动一个 todo 任务时移入，commit 完成（或废弃）后移出到归档；防止中途 ctrl-c / 用户手动暂停时上下文丢失

## 结论与决策

**新流转**:

```
讨论中 ──(定案)──▶ 下一步 ──(/go 启动)──▶ 正在执行 ──(commit 完)──▶ archived ## 已完成
                                                                ▲
任何节点 ─────────────(废弃)──────────────────────────────────── archived ## 废弃
```

**索引三段不同列**（同一文件三张子表）:

- 正在执行: ID / 标题 / 开始时间 / 当前状态
- 下一步: ID / 简介 / 重要 / 立即可做 / 改动规模 / 依赖
- 讨论中: ID / 简介 / 待决策项数 / 阻塞依赖

**正在执行单槽**: 同时只能 1 条任务在该段；多任务并行会让"中途出问题询问用户"的兜底失效。

**归档瘦身**: 标题 + 完成形式（完整 / 部分 / 改方案后 / 废弃）+ 1 行摘要 + log 链接；原文细节去 git history / change_logs 找。

**`/todo` skill 改造**: 删建议、删解析、删分档；只读 `## 索引` 段原文渲染 + 末尾一句"想看哪条？告诉我 ID 或说点别的"。

**索引维护机制**: LLM-only，写进 todo_list.md 顶部"如何维护索引"段；不引入脚本、不引入 hook。

## 计划动作清单

- file: `docs/todo_list.md` →
  - 顶部新增 `## 索引（自动生成，勿手改）` 段，含三张子表（首次填充：当前所有 8 条任务按新分段+新列重排）
  - 重写 `## 文件说明`，新增"如何维护索引"小节；旧规则保留并改写（立即执行 → 正在执行；完成 → 移归档；废弃 → 移归档；提升 pipeline 规则随重命名调整）
  - `## 立即执行` 改为 `## 正在执行`（当前空段——T-CHAR-SNAPSHOT 还没 /go 启动，留在"下一步"或保留在原段位置取决于是否启动；本次无 /go 启动该任务，故 `## 正在执行` 当前为空）
  - 重新检查所有 8 个现存条目位置：原"立即执行"段下唯一条目 T-CHAR-SNAPSHOT-13-DIM-VERIFY 应进入"下一步"段（未 /go，不属于"正在执行"）
- file: `docs/todo_list_archived.md` →
  - 新建文件，含 `## 文件说明` + `## 已完成` + `## 废弃` 模板段（条目格式说明）
- file: `.claude/commands/todo.md` →
  - 整段改写：删除现有的 9 个步骤（读 / 解析 / 推断 / 分档 / 出表 / 统计 / 建议 / 等待 / 约束）
  - 新版：(1) 读 docs/todo_list.md 的 `## 索引` 段 (2) 原样渲染 (3) 末尾一句"想看哪条？告诉我 ID 或说点别的" (4) 等待——共 4 个简短步骤
  - `` 仍可作为 ID 关键字过滤
- file: `.agents/skills/todo/SKILL.md` →
  - frontmatter 保留，正文与 `.claude/commands/todo.md` 逐字一致

## 验证标准

- [ ] `docs/todo_list.md` 顶部 `## 索引` 段三张子表渲染合规（markdown 表格语法正确）
- [ ] 8 个现存任务条目全部在新索引中出现，分段位置与正文段落归属一致
- [ ] `## 立即执行` 在正文中已不再出现，全部改为 `## 正在执行`
- [ ] `docs/todo_list_archived.md` 创建成功，模板 + 说明段齐全
- [ ] `.claude/commands/todo.md` 与 `.agents/skills/todo/SKILL.md` 正文逐字一致（diff 仅 frontmatter）
- [ ] `grep -rn "立即执行" docs/ .claude/ .agents/` 无残留旧称（除归档 / change_logs 等历史文件）
- [ ] `grep -rn "todo_list" ai_context/ docs/` 检查没有依赖旧两段命名的描述
- [ ] /todo skill 新版步骤数 ≤ 5，无解析 / 推断 / 分档 / 建议生成

## 执行偏差

无重大偏差。两点 Step 6 review 时发现并就地修：

1. `docs/todo_list.md:153` 写了"旧规则用'段落=立即执行 → 🔴 高'区分；现'立即执行'段已不存在..." 的 legacy 对比解释——违反"docs describe current only"约束。已删除。
2. `.claude/commands/go.md:66` Step 5 原文是"已完成条目**清除**、状态变化更新"——与新流转（完成 → 移归档）不一致，且没提刷索引。改为"整条移到 `docs/todo_list_archived.md` 的 `## 已完成` 段（瘦身... ）+ 同步刷新顶部 `## 索引` 段"。`.agents/skills/go/SKILL.md` 同步镜像。

<!-- POST 阶段填写 -->

## 已落地变更

- **`docs/todo_list.md`**（重写 + 重排）
  - 顶部新增 `## 索引（自动生成，勿手改）` 段：三张子表（正在执行 / 下一步 / 讨论中），列定义按段不同，含 8 条任务全量首次填充
  - 重写 `## 文件说明`：新增"任务流转"图、"如何维护索引"小节（触发时机 + 三张子表列定义 + 字段推断规则）；旧"如何更新 / 删除"重写为"如何更新条目"，覆盖添加 / /go 启动 / 完成 / 废弃 / 讨论转落地 5 种动作
  - `## 立即执行` → `## 正在执行`，当前空段
  - 8 条任务正文条目按新分段重排：T-CHAR-SNAPSHOT-13-DIM-VERIFY、T-PHASE35-IMPORTANCE-AWARE 在"下一步"；其余 6 条留在"讨论中"
- **`docs/todo_list_archived.md`**（新建）
  - 含 `## 文件说明`（用途 + 为什么瘦身 + 条目格式 + 排序 + 不记录什么 + 读取时机）+ `## 已完成` 占位 + `## 废弃` 占位
- **`.claude/commands/todo.md`**（整段重写）
  - 4 步：读索引段 → 过滤（可选）→ 渲染 → 提问 + 停手
  - 删除原 9 步（解析 / 推断 / 分档 / 出表 / 统计 / 建议 / 等待 / 约束）
  - `$ARGUMENTS` 仍作 ID 关键字过滤
- **`.agents/skills/todo/SKILL.md`**（镜像）
  - frontmatter description 重写
  - 正文与 `.claude/commands/todo.md` 逐字一致
- **`.claude/commands/go.md` + `.agents/skills/go/SKILL.md`**（Step 5 措辞更新，双轨同步）
  - "已完成条目清除" → "整条移到 todo_list_archived.md ## 已完成 段（瘦身规则）+ 同步刷新顶部 ## 索引 段"
- **`ai_context/handoff.md` L51-58**（resume gate 段落）
  - "## 立即执行 section" → "## 正在执行 and ## 下一步 sections"，并指引"先看 ## 索引 更快"
- **`ai_context/instructions.md` `## TODO List` 段**
  - 新增段落命名（正在执行 / 下一步 / 讨论中）、`## 索引` 缓存说明、`docs/todo_list_archived.md` 引用

## 与计划的差异

PRE 计划清单全部落地。两处 Step 6 修复（见上方"执行偏差"）属于全库 review 应有的连带更新，不是计划外扩张。

## 验证结果

- [x] `docs/todo_list.md` 顶部 `## 索引` 段三张子表渲染合规 — 三段标题齐全（🟢 正在执行 / 🟡 下一步 / ⚪ 讨论中），表头列定义符合 PRE 规划
- [x] 8 个现存任务条目全部在新索引中出现 — `for id in ...; grep` 8/8 ✓
- [x] `## 立即执行` 在正文中已不再出现 — `grep -rn "立即执行" docs/ .claude/ .agents/ ai_context/`（除归档 / change_logs）零结果
- [x] `docs/todo_list_archived.md` 创建成功 — 3126 字节，模板 + 说明段齐全
- [x] `.claude/commands/todo.md` 与 `.agents/skills/todo/SKILL.md` 正文逐字一致 — `diff` clean
- [x] `grep -rn "立即执行"` 无残留旧称（除归档 / change_logs / 本 log 自身）— 零结果
- [x] `grep -rn "todo_list" ai_context/ docs/` 描述均与新两段命名一致 — 无依赖旧命名的描述
- [x] /todo skill 新版步骤数 ≤ 5 — 实际 4 步，无解析 / 推断 / 分档 / 建议生成

## Completed

- **Status**: DONE
- **Finished**: 2026-04-27 16:58:40 EDT
