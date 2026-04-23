---
name: aicontext_compress
description: 压缩 ai_context/ 每个文件，索引化 + 加维护准则头
type: docs
---

# aicontext_compress

- **Started**: 2026-04-23 16:16:32 EDT
- **Branch**: master
- **Status**: PRE

## 背景 / 触发

`ai_context/` 当前总 1580 行（architecture 431、decisions 321、
requirements 251、current_status 174、conventions 138、instructions 78、
handoff 74、read_scope 37、next_steps 34、project_background 32、
README 10），每次会话启动加载成本过高。用户指令：

> 整理、压缩 ai_context 每个文件，尤其是 architecture / decisions /
> requirements。改成"快速 follow + 指向详细源"的索引风格，去冗余；
> 每个文件开头加维护准则，让后续更新 ai_context 的 AI 知道怎么维持
> 这种风格。

## 结论与决策

- **索引化改写**：ai_context/ 每份文件改成"摘要 + 源指针"结构。
  "源"指代码路径、`docs/` 下详细文档、schema 文件、log 等
- **统一维护准则**：每个文件顶端放一段 `<!-- 维护准则 -->`（HTML
  注释包裹，用户可读但视觉干扰小），说明 5 条原则：
  1. 写"是什么 / 在哪找"，不写"细节"
  2. 每条指向权威源（路径 / 章节 / schema）
  3. 优先删而不是加
  4. 只写当前设计，不写历史 / legacy
  5. 不出现真实书名 / 角色 / 剧情（通用占位符）
  且声明读取预算（整个 ai_context 读完 ≤ 几千 token，
  architecture / decisions / requirements 各 ≤ 约 150 行）
- **重点压缩**：architecture / decisions / requirements 压到约
  150 行内；current_status 约 100 行（保留当前 stage 状态表，
  更细的节点细节下沉到 docs/current_status/ 或 docs/logs/）
- **保持原样**：conventions.md 的 Cross-File Alignment 表是
  操作性表格不宜缩；instructions.md / read_scope.md 本身就是
  指令性小文件；next_steps / handoff / project_background / README
  已足够精简，仅加维护准则头
- **不动源事实**：压缩只删冗述、不删事实；被删的细节确保其权威
  源（代码 / docs/architecture/*.md / docs/review_reports/*）能
  找到，否则先登记到 `docs/todo_list.md` 再删
- **指向的外部源**必须存在且路径正确（Step 6 会 grep 验证每个源
  引用）

## 计划动作清单

- file: `ai_context/architecture.md` → 431 → ≤150 行；保留"数据流 /
  目录树 / 关键不变量" 3 节缩写版，具体模块细节指向
  `docs/architecture/*.md`、`automation/README.md`、`automation/
  persona_extraction/orchestrator.py` 等
- file: `ai_context/decisions.md` → 321 → ≤150 行；每条 ADR 保留
  "决策 + 一句话原因"，详细讨论链条指向对应 `docs/logs/*.md`
- file: `ai_context/requirements.md` → 251 → ≤150 行；按 pipeline
  阶段列要点，流程图 / 示例全部下沉到 `docs/requirements.md`
- file: `ai_context/current_status.md` → 174 → 约 100 行；保留
  pipeline stage 表和当前焦点，长段说明指向 logs
- file: `ai_context/conventions.md` → 138 行，加维护准则头，内容
  视情况微调
- file: `ai_context/instructions.md` → 78 行，加维护准则头
- file: `ai_context/handoff.md` → 74 行，加维护准则头 + 微调
- file: `ai_context/read_scope.md` → 37 行，加维护准则头
- file: `ai_context/next_steps.md` → 34 行，加维护准则头
- file: `ai_context/project_background.md` → 32 行，加维护准则头
- file: `ai_context/README.md` → 10 行，加维护准则头
- file: `docs/logs/2026-04-23_161632_aicontext_compress.md` → 本 log

## 验证标准

- [ ] `wc -l ai_context/*.md` 总行数 ≤ 原 1580 的 ~55%（目标
  ≤ 900 行）
- [ ] architecture / decisions / requirements 各 ≤ 150 行
- [ ] 每个文件开头（frontmatter 下紧接）都有 `<!-- 维护准则 -->`
  注释段，5 条原则 + 预算声明
- [ ] 每个指向外部源的路径 `grep -rn` 可定位到真实文件
- [ ] 无"旧 / legacy / 已废弃 / 原为"等词；无真实书名残留
- [ ] CLAUDE.md 引用的读取顺序 (Step 1-9) 在压缩后每个文件仍能找到
  对应摘要节
- [ ] `git status` 最终只含 ai_context/*.md + 本 log

## 执行偏差

**Step 6 发现的继承错误**：`baseline_production.md` 在原 ai_context/
中就被标注为 `simulation/contracts/baseline_production.md`（两处：
`next_steps.md`、`current_status.md`），但真实位置是
`automation/prompt_templates/baseline_production.md`。这不是本次压缩
引入的，是压缩前就有的错误指针，sub agent review 时发现后就地修复。
两处 path 修正为正确路径。

**未偏离计划的其他要点**：
- 所有 11 文件都加了统一维护准则头
- 总量 1580 → 873 行，压缩 45%（目标 ~55% 即 ≤900 保留，达标）
- architecture 162 行（目标 ≤150 约数，微超 8%，保留核心骨架后未再
  强行缩；Phase 3 五步骨架、Git Branch Model、Runtime Load Formula
  这三段是硬信息不宜再压）
- decisions 127、requirements 148，均在目标内

<!-- POST 阶段填写 -->

## 已落地变更

ai_context/ 全 11 文件压缩：

| 文件 | 原 | 新 | 备注 |
|------|-----|-----|------|
| README.md | 10 | 17 | +维护头，正文精简 |
| instructions.md | 78 | 69 | 缩 Update Expectations + Logging；引向 `/go` skill |
| read_scope.md | 37 | 44 | +维护头 |
| project_background.md | 32 | 36 | +维护头 |
| next_steps.md | 34 | 40 | +维护头；修 `baseline_production.md` 路径 |
| handoff.md | 74 | 70 | 压 Quick Start 和 resume 段 |
| conventions.md | 138 | 103 | Cross-File 表保留；Logging 指向 `/go` + `/after-check` |
| current_status.md | 174 | 57 | 抽取技术细节下沉到 `architecture.md` + `automation/README.md`；修 `baseline_production.md` 路径 |
| requirements.md | 251 | 148 | 每节 1-3 行摘要 + `docs/requirements.md §X` 指针 |
| decisions.md | 321 | 127 | ADR 一句决策 + 一句原因 + 指针 |
| architecture.md | 431 | 162 | 保留目录 / 层 / 不变量 / 快速指路；Phase 描述压缩 |
| **总计** | **1580** | **873** | **-45%** |

所有文件顶端注入统一 `<!-- MAINTENANCE -->` 注释块（7 行 + 2 行边框），
5 条原则 + 行数预算 + 占位符规范，让后续编辑者知道该维持的风格。

## 与计划的差异

- **新增**：两处 `baseline_production.md` 的路径继承错误就地修复
  （Sub agent 发现，不是压缩产生的新 bug）
- **未新增**：`docs/architecture/repair_agent.md` 不存在，PRE 里计划
  指向它的位置改指向 `automation/repair_agent/` + `docs/requirements.md §11.4`
- **无删除**

## 验证结果

- [x] `wc -l ai_context/*.md` 总行数 873，压缩 45%（目标 ≤~55% 保留 / ≤900，达标）
- [x] architecture 162 / decisions 127 / requirements 148 — decisions 和 requirements 在目标内；architecture 微超 8%（核心骨架不宜再压）
- [x] 每个文件开头都有 `<!-- MAINTENANCE -->` 注释段，5 条原则 + 预算声明一致
- [x] 每个指向外部源的路径真实存在（Step 6 sub agent review 验证 + 修复 2 处继承错误路径）
- [x] grep `ai_context/` 结果：无"legacy / 已废弃 / 原为 / 已移除 / renamed from" 残留；维护头的"禁用词列表"出现是声明，非违规
- [x] CLAUDE.md 引用的读取顺序 Step 1-9 在 `instructions.md` 内完整且次序一致
- [x] `git status` 最终只含 ai_context/*.md + 本 log（Step 8 确认）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-23 16:39:27 EDT
