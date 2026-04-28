# skills-config-extraction

- **Started**: 2026-04-28 17:09:53 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

用户已有第二个项目要复用 .agents/skills/ 这套 plugin。当前 6 个 skill
（commit / go / full-review / post-check / monitor / check-review）正文里
有大量 offpage 项目专属 hardcode：长跑进程名 persona_extraction、目录
sources/ works/ users/ automation/ simulation/、分支前缀 extraction/、
时区 America/New_York、业务实体 "真实书名 / 角色 / 剧情" 等等，会让
plugin 装到第二个项目时无法直接跑。

经过多轮讨论（plan 模式）拍板：把项目专属抓手集中到一份 skills_config.md，
由各 skill 在运行时按需读取——既不污染 session start，又能让长会话
里改 config 后下次 skill 触发即生效，并保持 skill 自包含可复制。

## 结论与决策

**做什么**：

1. 新增 ai_context/skills_config.md（9 节）：后台进程 / 保护分支前缀 /
   主分支策略 / 禁提路径 / 源码目录 / 示例产物目录 / 核心组件关键词 /
   敏感内容占位规则 / 时区。每节按 offpage 当前真实状态填值，行为零变化。
2. 改 ai_context/conventions.md 的 Cross-File Alignment 表：新增一行
   "项目专属抓手变化 → 同步 skills_config.md"。
3. 改 6 个 skill：
   - 加极简 0a 段：Read skills_config.md，三态判断（结构缺 → fail
     loudly；某节 `（无）`/留空 → 跳过该节相关步骤；填了路径但路径
     不存在 → fail loudly 提示漂移）
   - 把 hardcode 引用改成 "skills_config.md `## XX`" 引用
   - 镜像同步 .claude/commands/<n>.md
4. /check-review 引用 ai_context 时保留 hardcode 核心文件清单，加兜底
   "如本项目 ai_context 结构不同则读所有 .md"——不依赖 skills_config.md。
5. /full-review 工作方式：实现线 / 产物线分别按 skills_config.md
   `## 源码目录` `## 示例产物目录` 跑；缺失 / 留空时按各节定义的
   缺失行为降级（实现线退化为扫所有非白名单子目录、产物线跳过）。

**不做什么**：

- 不改 CLAUDE.md / AGENTS.md / instructions.md 的默认加载链——
  skills_config.md 不进 session start，由 skill 按需读
- 不动 plan / todo / todo-list / todo-add 4 个 skill（无项目专属抓手）
- skills_config.md 不放"缺失行为"详细说明（保持纯数据；解释在 plugin
  README——本次不写 README，作为后续 todo）
- 不删 skill 正文里的 ai_context 核心文件名（保留 hardcode + 兜底）

## 计划动作清单

- file: ai_context/skills_config.md → 新增，9 节按 offpage 当前真实状态填值
- file: ai_context/conventions.md → Cross-File Alignment 表新增一行
- file: .agents/skills/commit/SKILL.md → 加 0a 段；hardcode 替换为节引用
  - L37 禁提路径扫描 → `## 禁提路径`
  - L53 进程检测 → `## 后台进程`
  - L67 长跑分支判断 → `## 保护分支前缀`
  - L73 约束段 ai_context 引用 → 通用化措辞
- file: .agents/skills/go/SKILL.md → 加 0a 段；hardcode 替换
  - L11 工作流硬规则 → `## 主分支策略` + `## 保护分支前缀`
  - L13 Step 0 进程检测 → `## 后台进程`
  - L27/L33 时间戳命令 → `## 时区`
  - L62/L74 业务实体占位 → `## 敏感内容占位规则`
  - L107 Step 8 禁提扫描 → `## 禁提路径`
  - L115 Step 9 长跑分支判断 → `## 保护分支前缀`
- file: .agents/skills/full-review/SKILL.md → 加 0a 段；hardcode 替换
  - L8 "Offpage 仓库" → "当前仓库"
  - L36-38 三条审计线 → 实现线/产物线/组件线引用对应节
  - L46 流水线组件关键词 → `## 核心组件关键词`
  - L92 时间戳命令 → `## 时区`
- file: .agents/skills/post-check/SKILL.md → 加 0a 段；hardcode 替换
  - L35 产物结构线 → `## 示例产物目录`
  - L46 业务实体占位 → `## 敏感内容占位规则`
  - L83 commit 分支提示 → `## 保护分支前缀`
- file: .agents/skills/monitor/SKILL.md → 加 0a 段；hardcode 替换
  - L8 / L26-30 进程盘点 → `## 后台进程` + $ARGUMENTS 临时参数兜底
  - L37 时间戳命令 → `## 时区`
- file: .agents/skills/check-review/SKILL.md → 加 0a 段（仅说明 / 时区）；
  ai_context 核心文件保留 hardcode + 兜底句
- file: .claude/commands/commit.md → 镜像同步 SKILL.md 正文
- file: .claude/commands/go.md → 镜像同步
- file: .claude/commands/full-review.md → 镜像同步
- file: .claude/commands/post-check.md → 镜像同步
- file: .claude/commands/monitor.md → 镜像同步
- file: .claude/commands/check-review.md → 镜像同步

## 验证标准

- [ ] ai_context/skills_config.md 存在，9 节齐备，每节有真实内容（offpage 当前状态）
- [ ] ai_context/conventions.md 的 Cross-File Alignment 表含新增一行
- [ ] 6 个 skill 的 SKILL.md 都有 ## 0a. 加载配置 段，三态判断写明
- [ ] 6 个 skill 的 SKILL.md 与 .claude/commands/<n>.md 正文逐字一致
  （除 SKILL.md 的 YAML frontmatter；命令模式：
  `diff <(awk '/^# \//{p=1}p' .agents/skills/<n>/SKILL.md) .claude/commands/<n>.md`
  → 输出为空）
- [ ] grep -n "persona_extraction" .agents/skills/ .claude/commands/ →
  剩余出现仅限说明性注释，不是命令模板里的硬编码
- [ ] grep -n "America/New_York" .agents/skills/ .claude/commands/ → 0
  （时区命令统一引用 `## 时区` 节）
- [ ] grep -rn "Offpage 仓库" .agents/skills/ .claude/commands/ → 0
- [ ] grep -rn "真实书名" .agents/skills/ .claude/commands/ → 0
- [ ] grep -rn "extraction/\\* lane\\|feature lane" .agents/skills/ .claude/commands/ → 0

## 执行偏差

- /check-review 0a 段：PRE 计划是"加 0a 段（仅说明 / 时区）"，执行
  到 Step 6 全库 review 时被 sub agent 抓到 "声明了 `## 时区` /
  `## 敏感内容占位规则` / `## 核心组件关键词` 但正文从未引用"——
  实际 check-review 不生成时间戳、不直接扫敏感内容 / 组件关键词。
  最终方案改为 **完全移除 0a 段**（check-review 不依赖
  skills_config.md），保留 ai_context 核心文件 hardcode + "如本项目
  ai_context 结构不同则读所有 .md" 兜底句。
- conventions.md Cross-File Alignment 表初稿漏了 `## 主分支策略`，
  Step 6 review 抓到后补全（已含 main-branch policy）。
- /go Step 7 POST log `**Finished**: {timestamp}` 初稿未显式引用
  `## 时区`，Step 6 review 抓到后补一句 "按 skills_config.md
  `## 时区` 的命令模板取，与 PRE Started 同时区"。

<!-- POST 阶段填写 -->

## 已落地变更

- `ai_context/skills_config.md`（新增）：9 节按 offpage 当前真实状态
  填值——后台进程 `persona_extraction` + works/* 进度路径、保护分支前缀
  `extraction/`、主分支 `main` + 先进 main 同步、禁提路径 sources / sqlite /
  embeddings / caches / works / users、源码目录 automation/ + simulation/、
  示例产物目录 works/ + users/_template/、核心组件 orchestrator / validator /
  consistency checker / post-processing、敏感内容占位规则（真实业务实体名）、
  时区 America/New_York。
- `ai_context/conventions.md` L48：Cross-File Alignment 表新增 1 行覆盖
  skills_config.md 全部 9 节（含 main-branch policy）。
- `.agents/skills/commit/SKILL.md`：加 0a 段；L37 禁提路径 → `## 禁提路径`；
  L53 进程检测 → `## 后台进程`；L67 长跑分支判断 → `## 保护分支前缀`。
- `.agents/skills/go/SKILL.md`：加 0a 段；Step 0 工作流 → `## 主分支策略`
  + `<MAIN>` 占位；Step 0 进程检测 → `## 后台进程`；Step 1 PRE log 文件名
  时间戳 + Started timestamp → `## 时区`；Step 2 / Step 6 业务实体占位 →
  `## 敏感内容占位规则`；Step 7 Finished timestamp → `## 时区`；Step 8 禁提
  扫描 → `## 禁提路径`；Step 9 长跑分支判断 → `## 保护分支前缀` + `## 后台进程`。
- `.agents/skills/full-review/SKILL.md`：L8 "Offpage 仓库" → "当前仓库"；
  加 0a 段；工作方式三条审计线 → 实现线 `## 源码目录` / 产物线 `## 示例产物目录`
  / 规范线必跑；重点检查项流水线组件 → `## 核心组件关键词`；归档时间戳 → `## 时区`。
- `.agents/skills/post-check/SKILL.md`：加 0a 段；轨 2 产物线 →
  `## 示例产物目录`；轨 2 残留检查 → `## 敏感内容占位规则`；commit 分支
  提示 → `## 保护分支前缀`。
- `.agents/skills/monitor/SKILL.md`：description 与正文去 persona_extraction /
  simulation / works/ / users/* 硬编码；加 0a 段（含 `## 后台进程` 留空时
  $ARGUMENTS 兜底逻辑）；Step 1 进程盘点 → `## 后台进程`；Step 2 Timestamp
  → `## 时区`。
- `.agents/skills/check-review/SKILL.md`：Step 2 ai_context 加载加兜底句
  "如本项目 ai_context 结构不同则读所有 .md"；Step 3 跨文件连带更新引用
  conventions.md `Cross-File Alignment` 段时加"该段不存在则跳过本项"
  兜底。**未加 0a 段**（已是执行偏差，见上）。
- `.claude/commands/{commit,go,full-review,post-check,monitor,check-review}.md`：
  全 6 文件镜像同步——`# /<n>` 起的正文与对应 SKILL.md 逐字一致。
- `docs/todo_list.md`：新增 `T-PLUGIN-README` 条目到 `## 下一步` 段；
  顶部索引段子表行 + 汇总从 10 / 3 / 7 → 11 / 4 / 7 同步刷新。

## 与计划的差异

- check-review 0a 段从"加（仅说明 / 时区）"改成 **完全移除**（执行偏差 #1）
- conventions.md Cross-File Alignment 表初稿漏 `## 主分支策略`，
  Step 6 补全（执行偏差 #2）
- go Step 7 timestamp 初稿引用不显式，Step 6 补全（执行偏差 #3）
- 其余与 PRE 计划清单完全一致；无新增 / 删除文件操作

## 验证结果

- [x] ai_context/skills_config.md 存在，9 节齐备 — sub agent 实测
  逐节路径 / 模式与 offpage 当前 .gitignore / conventions.md / 实际目录
  对得上
- [x] ai_context/conventions.md Cross-File Alignment 表含新增一行（含
  main-branch policy） — L48 已修复
- [x] 6 个 skill SKILL.md 都有 ## 0a. 加载配置 段 — **5 个有**
  （commit/go/full-review/post-check/monitor），check-review 因执行
  偏差移除；三态判断措辞在 5 个 skill 里逐字一致
- [x] 6 个 skill SKILL.md 与 .claude/commands/<n>.md 正文逐字一致 —
  6/6 mirror diff 输出为空
- [x] grep "persona_extraction" .agents/skills/ .claude/commands/ →
  仅 skills_config.md（配置值，非 hardcode）；6 skill 的 SKILL.md /
  .claude/commands/ 0 命中
- [x] grep "America/New_York" .agents/skills/ .claude/commands/ →
  0 命中
- [x] grep "Offpage 仓库" .agents/skills/ .claude/commands/ → 0 命中
- [x] grep "真实书名" .agents/skills/ .claude/commands/ → 0 命中
- [x] grep "extraction/\* lane\|feature lane" .agents/skills/
  .claude/commands/ → 0 命中

## Completed

- **Status**: DONE
- **Finished**: 2026-04-28 17:39:05 EDT
