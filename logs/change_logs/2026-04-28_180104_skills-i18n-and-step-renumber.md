# skills-i18n-and-step-renumber

- **Started**: 2026-04-28 18:01:04 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

紧接 commit 01c1a3a（skills-config-extraction）后用户提了三个改进点：

1. `ai_context/skills_config.md` 写中文不合适——ai_context 是英文真相
   层（CLAUDE.md L59 `ai_context/ stays English`），新建的中文 config
   破了这条 convention。skills 里对应的节引用也得跟着改英文。
2. 改造后多个 skill 出现 `## 0a. 加载配置` 后接 `## 0. ...` 的反人类
   序号——`0a / 0` 是过渡补丁，应统一规整为 `## 0. 加载配置 → ## 1.
   ... → ## 2. ...`。
3. `docs/todo_list.md` 的关键段名（`下一步` / `讨论中（未定案）` /
   `正在执行`）和字段名（`重要` / `立即可做` / `改动规模` / `依赖` 等）
   写中文也是项目专属耦合，做 plugin 不通用——改英文。3 个 todo skill
   （todo / todo-list / todo-add）里的对应引用一并跟改。

## 结论与决策

**做什么**：

1. **skills_config.md 英文化**：9 节标题与正文全英文。Section 名映射：
   - 后台进程 → Background processes
   - 保护分支前缀 → Protected branch prefixes
   - 主分支策略 → Main branch policy
   - 禁提路径 → Do-not-commit paths
   - 源码目录 → Source directories
   - 示例产物目录 → Example artifact directories
   - 核心组件关键词 → Core component keywords
   - 敏感内容占位规则 → Sensitive content placeholder rules
   - 时区 → Timezone
2. 5 个 skill（commit / go / full-review / post-check / monitor）
   正文里所有 `## 后台进程` 等中文节引用 → 改成 `## Background processes`
   等英文（与 skills_config.md 节名逐字一致）。
3. **5 个 skill 序号重排**：`## 0a. 加载配置` → `## 0. Load skills config`，
   原 `## 0. ...` → `## 1. ...`，依此类推全文 step 序号 +1。
   - commit: 0 改动有效性 / 1 分支正确性 / 2 追踪状态 / 3 Commit / 4 Forward
     → 0 加载 + 1 改动有效性 + 2 分支 + 3 追踪 + 4 Commit + 5 Forward
   - go: 0 环境锁定 / 1 PRE / 2 需求 / 3 实现 / 4 测试 / 5 文档 / 6 review
     / 7 POST / 8 commit / 9 同步 → 0 加载 + 1 环境 + 2 PRE + 3 需求 + 4 实现
     + 5 测试 + 6 文档 + 7 review + 8 POST + 9 commit + 10 同步
   - full-review: 顶层无 step 编号，只是 0a 改 0；保持
   - post-check: 0 范围 / 0.5 intent / 1 alignment / 2 sub agent / 3 检查
     / 4 回写 / 5 输出 / 6 等待 → 0 加载 + 1 范围 + 1.5 intent + 2 alignment
     + 3 sub agent + 4 检查 + 5 回写 + 6 输出 + 7 等待
   - monitor: 0 场景登记 / 1 识别 / 2 单轮 / 3 处理 / 4 循环 → 0 加载 +
     1 场景 + 2 识别 + 3 单轮 + 4 处理 + 5 循环
4. **docs/todo_list.md + docs/todo_list_archived.md 段名 / 字段英文化**：
   - 段名：`正在执行` → `In Progress`、`下一步` → `Next`、
     `讨论中（未定案）` → `Discussing (Undecided)`、
     `已完成` → `Completed`、`废弃` → `Abandoned`
   - 字段：保留中文标题（`**上下文**` / `**改动清单**` / `**完成标准**`
     等是条目内字段，未在 skill 里硬引用，留中文不影响 plugin 通用化）；
     **索引段子表表头**英文化（`重要` → `Importance`、`立即可做` →
     `Ready` 等）；汇总行措辞英文化
   - 顶部"如何维护索引"段中文内容保留（user-facing 文档），但段名
     `## 文件说明 → 如何维护索引` → `## File guide → Index maintenance`
     （todo skill 引用此段名，得同步）
5. **3 个 todo skill 引用同步**：
   - todo / todo-list：`## 索引（自动生成，勿手改）` 段名引用、
     "如何维护索引" 段名引用全改英文（`## Index (auto-generated; do not hand-edit)`、
     `Index maintenance` 等，与 todo_list.md 顶部刷新后的段名逐字一致）
   - todo-add：解析 `$ARGUMENTS` 段位映射 `下一步 / 讨论中 / 正在执行`
     → `Next / Discussing / In Progress`；正文所有引用同步
6. **镜像同步**：5 改造 skill + 3 todo skill = 8 对镜像文件全部同步。
7. **PRE log 文件名时间戳格式**：保持 offpage 既有 `EDT` 字面（不是
   plugin 通用化范畴；本次不改）。

**不做什么**：

- 不改 ai_context 其他文件（conventions.md / requirements.md 等本身已是英文）
- 不改 todo 条目正文（每条 `**上下文**` / `**改动清单**` 中文字段保留——
  那是条目内容，不是结构标签；改了会让历史条目不一致而无收益）
- 不改 plan 4 个 skill（无项目专属，不动）
- 不改 logs/change_logs/ 既有 PRE log 措辞（历史快照不重写）
- ai_context/skills_config.md 顶部说明性注释（"由 .agents/skills/* 在
  运行时按需读取..."）也英文化，与文件主体一致

## 计划动作清单

- file: ai_context/skills_config.md → 全文英文化（9 节标题 + 正文）
- file: .agents/skills/commit/SKILL.md → 0a→0 + 旧 0~4 → 1~5；节引用英文
- file: .agents/skills/go/SKILL.md → 0a→0 + 旧 0~9 → 1~10；节引用英文
- file: .agents/skills/full-review/SKILL.md → 0a→0；节引用英文
- file: .agents/skills/post-check/SKILL.md → 0a→0 + 旧 0~6 → 1~7；节引用英文
- file: .agents/skills/monitor/SKILL.md → 0a→0 + 旧 0~4 → 1~5；节引用英文
- file: docs/todo_list.md → 段名英文（In Progress / Next / Discussing /
  File guide / Index maintenance）+ 索引子表表头英文 + 汇总行英文
- file: docs/todo_list_archived.md → 段名英文（Completed / Abandoned）
- file: .agents/skills/todo/SKILL.md → 段名 / 索引引用英文化
- file: .agents/skills/todo-list/SKILL.md → 同上
- file: .agents/skills/todo-add/SKILL.md → $ARGUMENTS 段位映射改英文
- file: .claude/commands/{commit,go,full-review,post-check,monitor,
  todo,todo-list,todo-add}.md → 8 对镜像同步

## 验证标准

- [ ] ai_context/skills_config.md 9 节标题全英文，文件正文无中文
- [ ] 5 改造 skill 全部以 `## 0. Load skills config` 起头；后续 step
  连续编号不跳号
- [ ] grep -n "## 后台进程\|## 保护分支前缀\|## 主分支策略\|## 禁提路径\|
  ## 源码目录\|## 示例产物目录\|## 核心组件关键词\|## 敏感内容占位规则\|
  ## 时区" .agents/skills/ → 0 命中
- [ ] grep -n "0a\." .agents/skills/ .claude/commands/ → 0 命中
- [ ] docs/todo_list.md 顶部 3 段名 + 索引 / 文件说明段名英文
- [ ] docs/todo_list_archived.md 段名 Completed / Abandoned 英文
- [ ] 3 todo skill 引用与 todo_list.md 实际段名 / 表头逐字一致
- [ ] 8 对镜像 diff 全部 OK identical
- [ ] /todo skill 概念上仍可解析：grep "## Index (auto-generated"
  在 todo / todo-list 与 todo_list.md 中三方一致

## 执行偏差

无。Step 7 sub-agent 审计零 finding；步骤号连续 + 镜像一致 + 节引用
逐字对齐 + skills_config.md 全英文（grep CJK 字符 0 命中）+ 未误碰
plan / check-review / CLAUDE.md / AGENTS.md / instructions.md。

<!-- POST 阶段填写 -->

## 已落地变更

- `ai_context/skills_config.md`：完全重写为全英文。9 节标题映射：
  后台进程→Background processes、保护分支前缀→Protected branch
  prefixes、主分支策略→Main branch policy、禁提路径→Do-not-commit
  paths、源码目录→Source directories、示例产物目录→Example artifact
  directories、核心组件关键词→Core component keywords、敏感内容占位
  规则→Sensitive content placeholder rules、时区→Timezone。每节填值
  保持 offpage 真实状态不变；占位值 `（无）`→`(none)`。
- `.agents/skills/commit/SKILL.md`：0a→0；旧 0–4→1–5（共 6 step）；
  L37/L65/L72/L77 节引用改英文（## Do-not-commit paths / ## Background
  processes / ## Protected branch prefixes）；Step 4→5 cross-ref 更新；
  Step 2 措辞通用化（不再写死 "main"，改"按 ## Main branch policy 判断"）。
- `.agents/skills/go/SKILL.md`：完全重写。0a→0；旧 0–9→1–10（共 11 step）；
  description 11 步流程；所有 Step X→Step X+1 cross-ref 更新（Step 1
  环境锁定 / Step 2 PRE log / Step 7 全库 review / Step 8 POST / Step 9
  commit / Step 10 同步）；节引用全英文；worktree 表 `<MAIN>` 占位
  保留；Step 8 POST log timestamp 显式引用 `## Timezone`。
- `.agents/skills/full-review/SKILL.md`：0a→0；节引用改英文（##
  Source directories / ## Example artifact directories / ## Core
  component keywords / ## Timezone）；`（无）`→`(none)`；引用 `/go`
  Step 0→Step 1。
- `.agents/skills/post-check/SKILL.md`：0a→0；旧 0–6→1–7（含 1.5）；
  Step 0.5→1.5 cross-ref / Step 4→5 / Step 5→6 / Step 6→7 更新；节引用
  英文（## Example artifact directories / ## Sensitive content
  placeholder rules / ## Protected branch prefixes）；`（无）`→`(none)`；
  引用 `/go` Step 0→1, Step 6→7。
- `.agents/skills/monitor/SKILL.md`：完全重写。0a→0；旧 0–4→1–5；
  description 节引用英文（## Background processes）；节引用全英文
  （## Background processes / ## Timezone）；`（无）`→`(none)`；
  Step 1→2 / Step 2→3 cross-ref 更新。
- `docs/todo_list.md`：顶部段名 / 表头 / 汇总全英文。
  `## 索引（自动生成，勿手改）`→`## Index (auto-generated; do not hand-edit)`；
  `🟢 正在执行`→`🟢 In Progress`；`🟡 下一步`→`🟡 Next`；
  `⚪ 讨论中`→`⚪ Discussing`；表头 标题/开始时间/当前状态→Title/Start
  time/Status；简介/重要/立即可做/改动规模/依赖→Brief/Importance/
  Ready/Scope/Deps；待决策项数/阻塞依赖→Open decisions/Blocked by；
  汇总行 `**Total**: 11 — 🟢 In Progress 0 ｜ 🟡 Next 4 ｜ ⚪ Discussing 7`。
  cell 值映射：🔴 高→🔴 High、🟢 中低→🟢 Med-Low、🟡 中→🟡 Medium、
  ✅ 可做→✅ Ready、💬 需先讨论→💬 Discuss first、🟡 中量→🟡 Medium、
  🟢 小量→🟢 Small。`_（无）_`→`_(none)_`。
  ## 文件说明→## File guide + 7 个子节英文化（Purpose / Task flow /
  What to record / What NOT to record / How to update entries /
  Index maintenance / When to read）；Index maintenance 内列定义表
  + 字段推断规则全部用英文术语；`## 正在执行` placeholder→`## In
  Progress` + `_(empty — `/go` will move...)_`；`## 下一步`→`## Next`；
  `## 讨论中（未定案）`→`## Discussing (Undecided)`。T-PLUGIN-README
  完成标准里的 `（无）`→`(none)`。
- `docs/todo_list_archived.md`：## 文件说明→## File guide；## 用途→
  ## Purpose；## 已完成→## Completed；## 废弃→## Abandoned；条目格式
  小节内中文头小调（已完成段→Completed 段、废弃段→Abandoned 段）；
  Abandoned 段 placeholder 改英文。
- `.agents/skills/todo/SKILL.md`：description + 正文段名 / 段引用全
  改英文（## Index... / ## File guide / Index maintenance / `_(none)_`
  / `_(no matching entries)_` / `(filtered by keyword "<keyword>")` /
  Importance / Ready / Scope）。
- `.agents/skills/todo-list/SKILL.md`：与 todo/SKILL.md 正文逐字一致，
  仅 frontmatter `name` 不同（todo-list）。
- `.agents/skills/todo-add/SKILL.md`：description + Step 1 段位映射
  表 + Step 4/5/6/7 + 约束段全部段名英文（## Next / ## Discussing
  (Undecided) / ## In Progress）；In Progress 时间字段引用
  `## Timezone`；Step 6 索引段引用改 `## Index (auto-generated; do
  not hand-edit)` + `## File guide → Index maintenance`。
- `.claude/commands/{commit,go,full-review,post-check,monitor,todo,
  todo-list,todo-add}.md`：8 文件全部从对应 SKILL.md 镜像同步，diff
  全 OK。

## 与计划的差异

无。所有计划项落实，PRE 验证标准 9/9 通过。

## 验证结果

- [x] ai_context/skills_config.md 9 节标题全英文，文件正文无中文 —
  sub-agent grep CJK 0 命中
- [x] 5 改造 skill 全部以 `## 0. Load skills config` 起头；后续 step
  连续编号不跳号 — commit 0–5 / go 0–10 / full-review 仅 0 / post-check
  0–7 含 1.5 / monitor 0–5
- [x] grep 中文节名 → 0 命中
- [x] grep `0a\.` → 0 命中
- [x] docs/todo_list.md 顶部 3 段名 + 索引 / 文件说明段名英文
- [x] docs/todo_list_archived.md ## Completed / ## Abandoned 英文
- [x] 3 todo skill 引用与 todo_list.md 实际段名 / 表头逐字一致
- [x] 8 对镜像 diff 全部 OK identical
- [x] /todo skill 概念上仍可解析：所有 todo skills 引用 `## Index
  (auto-generated...)` 与 todo_list.md L5 一致

## Completed

- **Status**: DONE
- **Finished**: 2026-04-28 18:34:44 EDT
