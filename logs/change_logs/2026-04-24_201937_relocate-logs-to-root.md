# relocate-logs-to-root

- **Started**: 2026-04-24 20:19:37 EDT
- **Branch**: master (worktree at ../persona-engine-master)
- **Status**: PRE

## 背景 / 触发

用户要求把目前 `docs/` 下的两个历史目录搬到仓库根：

- `docs/logs/` → `logs/change_logs/`
- `docs/review_reports/` → `logs/review_reports/`

并修正所有引用路径，使文档 / skill / prompt / ai_context 全部对齐新位置。

`logs/` 是新建的根级目录，承担"历史记录簇"的角色：
`change_logs/`（PRE/POST/REVIEW 三时点变更日志）+ `review_reports/`
（全仓库对齐审计快照）。

## 结论与决策

- 物理结构：
  - 创建根级 `logs/`
  - `git mv docs/logs logs/change_logs`
  - `git mv docs/review_reports logs/review_reports`
- 引用路径替换（全仓 grep + 逐文件 Edit）：
  - `docs/logs/` → `logs/change_logs/`
  - `docs/review_reports/` → `logs/review_reports/`
- 仅做路径替换，**不**改三时点契约 / 文件名规则 / 工作流语义。
- 描述只写当前设计，不写"原为 docs/logs / 已迁移自 …"——历史走 git。

## 计划动作清单

- file: `docs/logs/` → 物理移动到 `logs/change_logs/`（git mv，保留历史）
- file: `docs/review_reports/` → 物理移动到 `logs/review_reports/`（git mv）
- file: `CLAUDE.md` L35 → 引用替换
- file: `AGENTS.md` L35 → 引用替换
- file: `ai_context/current_status.md` L58 → 引用替换
- file: `ai_context/README.md` L17 → 引用替换
- file: `ai_context/conventions.md` L18/L47/L73 → 引用替换
- file: `ai_context/read_scope.md` L29/L30 → 引用替换
- file: `ai_context/handoff.md` L99/L104 → 引用替换
- file: `ai_context/instructions.md` L48 → 引用替换
- file: `ai_context/decisions.md` L14/L134 → 引用替换
- file: `.agents/skills/check-review/SKILL.md` 全文 → 引用替换
- file: `.agents/skills/full-review/SKILL.md` L25/L89/L101 → 引用替换
- file: `.agents/skills/post-check/SKILL.md` 全文 → 引用替换
- file: `.agents/skills/go/SKILL.md` 全文 → 引用替换
- file: `.claude/commands/full-review.md` L20/L84/L96 → 引用替换
- file: `.claude/commands/go.md` L22/L23 → 引用替换
- file: `.claude/commands/post-check.md` 全文 → 引用替换
- file: `.claude/commands/check-review.md` 全文 → 引用替换
- file: `docs/todo_list.md` L12/L26/L38/L42 → 引用替换
- file: `prompts/review/全仓库对齐审计.md` L27/L85/L94 → 引用替换
- file: `works/README.md` L246 → 引用替换

## 验证标准

- [ ] `logs/change_logs/` 目录存在且包含全部原 `docs/logs/` 内容（git mv 历史保留）
- [ ] `logs/review_reports/` 目录存在且包含全部原 `docs/review_reports/` 内容
- [ ] `docs/logs/` 与 `docs/review_reports/` 不存在
- [ ] `grep -rn "docs/logs\b" .` 仅命中本 PRE log 自身（描述路径的字面引用）
- [ ] `grep -rn "docs/review_reports\b" .` 仅命中本 PRE log 自身
- [ ] CLAUDE.md / AGENTS.md 镜像约束保持（仅标题行差异）
- [ ] `.agents/skills/{go,post-check}/SKILL.md` 与 `.claude/commands/{go,post-check}.md` 正文逐字一致

## 执行偏差

无（PRE log 自身随 `git mv docs/logs logs/change_logs` 自动迁移到目标
路径 `logs/change_logs/2026-04-24_201937_relocate-logs-to-root.md`；
POST 段落就地写入该路径）。

<!-- POST 阶段填写 -->

## 已落地变更

**目录搬迁（git mv，保留 history）**：

- `docs/logs/` → `logs/change_logs/`（149 份历史 log 全量迁移）
- `docs/review_reports/` → `logs/review_reports/`（6 份审计报告全量迁移）
- 新增根级 `logs/` 目录（包含上述两个子目录）

**引用路径替换（19 个文件）**：

- `CLAUDE.md` L35 — `docs/logs/, docs/review_reports/` → `logs/change_logs/, logs/review_reports/`
- `AGENTS.md` L35 — 镜像同上
- `ai_context/current_status.md` L58 — write-mostly 条目路径更新
- `ai_context/README.md` L17 — 加载层级路径更新
- `ai_context/conventions.md` L18 / L47 / L73 — Logging 节 + Cross-File
  Alignment 表 + Generic Placeholders 豁免清单 4 处替换
- `ai_context/read_scope.md` L29 / L30 — Do Not Read By Default 路径
- `ai_context/handoff.md` L99 / L104 — work-specific 例外路径 + Milestone
  log 路径
- `ai_context/instructions.md` L48 — Logging 段路径
- `ai_context/decisions.md` L14 / L134 — discussion chains + write-mostly
  条目
- `.agents/skills/check-review/SKILL.md` 全文 review_reports 路径
- `.agents/skills/full-review/SKILL.md` 全文（review_reports 归档路径 +
  logs 不默认读规则）
- `.agents/skills/post-check/SKILL.md` 全文 intent 基线路径
- `.agents/skills/go/SKILL.md` 全文 PRE log 路径
- `.claude/commands/check-review.md` / `full-review.md` / `go.md` /
  `post-check.md` —— 镜像同对应 SKILL.md
- `docs/todo_list.md` L12 / L26 / L38 / L42 — 文件说明节 4 处
- `prompts/review/全仓库对齐审计.md` L27 / L85 / L94 — 提示词内嵌路径
- `works/README.md` L246 — 增量抽取建议路径
- `logs/change_logs/README.md`（原 `docs/logs/README.md`）—— 跟进 commit
  补：标题 `# Logs` → `# Change Logs`；Git Rule 段 `docs/logs/` →
  `logs/change_logs/`（首次 commit 后被发现：grep sweep 误把
  `logs/change_logs/` 整个排除导致这条遗漏）

## 与计划的差异

唯一差异：`logs/change_logs/README.md` 的两处自我描述（标题 + Git Rule
段路径）属计划外补丁。原计划假定该 README 内容只描述"仓库历史日志"
通用语义，与目录改名无耦合；实际上含 1 处直链 `docs/logs/`。已在跟进
commit 中修复，残留为 0。其他 19 个文件 + 2 个目录搬迁均如约落地；未
触动 `docs/requirements.md` / `docs/architecture/`（这两处确认无引用）。

## 验证结果

- [x] `logs/change_logs/` 存在且含 149 份原 `docs/logs/` 内容（git mv
  保留 rename history，`git status` 显示 R 标记）
- [x] `logs/review_reports/` 存在且含 6 份原 `docs/review_reports/` 内容
- [x] `docs/logs/` / `docs/review_reports/` 已不存在（`docs/` 仅余
  `architecture/`、`requirements.md`、`todo_list.md`）
- [x] `grep -rn "docs/logs"` 全仓 0 命中（除 .git / logs/ 历史快照）
- [x] `grep -rn "docs/review_reports"` 全仓 0 命中
- [x] 新路径引用统计：`logs/change_logs/` 38 处、`logs/review_reports/`
  21 处，跨 19 个文件
- [x] CLAUDE.md / AGENTS.md 镜像差异保持原状（Sync 段互引、标题行——
  本次未引入新差异）
- [x] `.agents/skills/{go,post-check,full-review,check-review}/SKILL.md`
  与 `.claude/commands/{...}.md` 镜像约束保持原状（每对仅在自我引用的
  镜像约束段不同——本次未引入新差异）
- [x] `works/*/analysis/logs/`（runtime per-work 日志目录）未被误改

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 20:26:22 EDT
