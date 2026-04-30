# strip_extraction_state_from_ai_context

- **Started**: 2026-04-30 10:00:12 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

上一轮 `/go`（log `2026-04-30_093855_check_review_docs_alignment.md`）落地后，
用户在 Step 10 末尾发现 `ai_context/current_status.md` §First Work Package
— Phase 3 State 提到 "S001 + S002 committed / S003 ERROR / S004–S049
pending" 的描述与现实不符——extraction 实际状态已全部清空，尚未开始；
原描述是历史快照，从未被同步刷新。

进一步澄清两条规则：

1. ai_context 不应记录 extraction 进度（已经有 `works/{work_id}/analysis/
   progress/` 承担运行时进度记录）
2. ai_context 只记录项目工程进度，不记录提取进度、不记录真实作品相关
   信息（包括具体 stage / sha / 角色数量等 work-specific 状态）

这与 conventions §Generic Placeholders（"No real book / character / place
/ plot names"）+ 各 ai_context 文件顶部的 maintenance 注释（"No real book
/ character / plot names — use placeholders"）一脉相承——本轮把规则
扩展到"extraction 进度状态"层面：runtime / per-work state 完全不入
ai_context。

## 结论与决策

**改的范围**：仅 ai_context/ 内"具体 extraction 进度 / first-work 状态
/ 真实作品提及"内容；不动 schema、code、prompt、`works/` 任何运行时
产物。

**改的方式**：

1. **`ai_context/current_status.md`**
   - §Project Stage：删 `Phase 0/1/1.5/2/4 complete; Phase 3 in progress
     — S001 + S002 committed, S003 in ERROR awaiting --resume, S004–S049
     pending. Phase 3.5 pending` 句；改为 framework-only 的工程进度描述
   - §Project Stage 第二段（"Recent schema change ... Existing committed
     S001 / S002 snapshots ... need migration ... before Phase 3 resumes"）
     ：删 S001 / S002 具体提及；schema deprecation 的 durable 信息已在
     `decisions.md §11d`，本段无新增价值，整段删
   - §What Exists 末条 `One first work package in progress (Chinese web
     novel, 500+ chapters)` —— 真实作品信息，整条删
   - §First Work Package — Phase 3 State 整段（line 38-47，含 sha /
     stage / target characters）—— 整段删
   - §Current Gaps 首条 `No finished character package yet (Phase 3 in
     progress)` —— 把 "(Phase 3 in progress)" 限定删除，措辞改成
     extraction 流程未端到端跑通，与具体 work 解耦

2. **`ai_context/next_steps.md`**
   - §Highest Priority #1 整条（"Continue automated extraction for the
     onboarded work package" + 5 行 sub-bullet）—— extraction 流水线
     end-to-end 是工程目标，但具体进度（S001 sha / Phase 3 / Phase 3.5
     blocking）属 progress 层。整条删，让 #2 (Refine schemas) 升为 #1
   - 重新编号 #1–#10 → #1–#9

3. **`ai_context/handoff.md`**
   - §Mental Model 句 "Architecture agreed, scaffolding + schemas done,
     first work package under stage extraction. No finished character
     package yet, no real user package, no runtime code." —— 删 "first
     work package under stage extraction"，保留其余工程层描述
   - §Current Work Continuation 段 —— 段标题"Current Work Continuation"
     暗示"当前正在执行某 work"语境；改为通用 CLI 用法说明 `## Running
     Extraction`，删 "Real `work_id` lives under `works/` + `sources/works/`."
     这种导向当前 work 的措辞；保留 CLI 命令模板（用 `<work_id>` 占位）
   - §Extraction-branch artifact drift (resume gate) 段 —— 工程级 process
     rule（resume 前要先读 todo_list 的 In Progress / Next 段），与
     specific work / stage 无关，保留不动
   - §What The User Cares About / §After Each Milestone / §Quick Start
     段 —— 通用工程规则，保留不动

**不动**：
- `ai_context/conventions.md`、`ai_context/decisions.md`、`ai_context/
  requirements.md`、`ai_context/architecture.md`、`ai_context/
  project_background.md`、`ai_context/instructions.md`、`ai_context/
  README.md`、`ai_context/read_scope.md`、`ai_context/skills_config.md`
  ——本轮 grep 已确认这些文件中只有 `S001` 占位、`extraction/{work_id}`
  branch 模型的结构性描述，不含 work-specific 提取进度
- `decisions.md §11d` 内 "S001 derives a baseline seed from source +
  identity; S002+ evolves from prev snapshot" —— 这是设计决策（S001 vs
  S002 的语义差异），不是某次 extraction 的状态
- 任何 schema / code / prompt / `works/` 实际产物
- `docs/todo_list.md` 中提到 first-work 进度的条目（todo_list 不在
  ai_context 范围内；如有 stale 描述可单独处理）

## 计划动作清单

- file: `ai_context/current_status.md` → 改 §Project Stage（删具体 stage
  / sha / Phase 3 in progress 句 + 整段第二段）；删 §First Work Package
  — Phase 3 State 整段；§What Exists 删末条 first-work 描述；§Current
  Gaps 首条改通用化措辞
- file: `ai_context/next_steps.md` → 删 Highest Priority #1 整条 +
  重新编号
- file: `ai_context/handoff.md` → 改 §Mental Model；改 §Current Work
  Continuation 段标题与首句、保留 CLI 模板

## 验证标准

- [ ] `grep -n "S001\|S002\|S003\|S004\|S049\|Phase 3 in progress\|--resume\|onboarded\|first work package\|first-work\|First Work Package" ai_context/current_status.md ai_context/next_steps.md ai_context/handoff.md` 命中数 = 0（除 maintenance comment 中的 `S001` 占位例子和 `--resume` 在 CLI 模板中的合法用法外；这两类是工程指引不是状态）
- [ ] `grep -rn "Chinese web novel\|500+ chapters\|2 target characters confirmed\|991c09f\|7639c8b\|char_support.*error_max_turns" ai_context/` 命中数 = 0
- [ ] `ai_context/current_status.md` 阅读后无任何 first-work / specific stage / specific sha 描述，§Project Stage 仅描述 framework 工程层
- [ ] `ai_context/next_steps.md` Highest Priority 段不含 first-work 进度
- [ ] `ai_context/handoff.md` 段标题不含 "Current Work Continuation"（改为通用化的 "Running Extraction"），CLI 模板仍可用
- [ ] 上一轮 commit `c46fd8d` 引入的 `current_status.md:64` main vs extraction/library 限定行保留不动（本轮不回退已落地正确改动）

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

- `ai_context/current_status.md`（净减 ~22 行）
  - §Project Stage 重写：删 `Phase 0/1/1.5/2/4 complete; Phase 3 in progress — S001 + S002 committed, S003 in ERROR awaiting --resume, S004–S049 pending. Phase 3.5 pending` 句；删 `Recent schema change (2026-04-29)` 整段（含 S001/S002 specific migration 提及）；改写为 framework-only 工程描述，并显式声明"Per-work extraction state lives in `works/{work_id}/analysis/progress/`, not here — `ai_context/` tracks framework-level engineering progress only"
  - §What Exists 删末条 `One first work package in progress (Chinese web novel, 500+ chapters)`
  - §First Work Package — Phase 3 State 整段删除（line 38-47 含 sha / stage / "2 target characters confirmed" / `--resume` resume command）
  - §Current Gaps 首条 `No finished character package yet (Phase 3 in progress)` → `Extraction pipeline not yet exercised end-to-end (no character package completed)`，去除"in progress"暗示
  - §Rules In Effect 完全保留（包括上一轮 commit `c46fd8d` 引入的 main vs extraction/library 分支语境限定行）
- `ai_context/next_steps.md`（净减 ~8 行）
  - §Highest Priority #1 整条删（"Continue automated extraction for the onboarded work package" + 5 行 sub-bullet 含 sha / stage state / `--resume` 行为说明 / preflight 描述）
  - 重新编号 #1–#10 → #1–#9：原 #2 (Refine schemas) 升为 #1
- `ai_context/handoff.md`（净增 2 行；改动行 ~5 行）
  - §Mental Model：`first work package under stage extraction` → `extraction pipeline done. No character package completed end-to-end yet`
  - §Current Work Continuation → §Running Extraction：段标题改通用化；删导向 specific work 的 `Real \`work_id\` lives under \`works/\` + \`sources/works/\`.` 句；保留 CLI 模板（`<work_id>` 占位）+ pipeline preflight 说明 + manual repair 指引
  - §Extraction-branch artifact drift (resume gate) 完整保留（工程级 process rule，与 specific work 解耦）

## 与计划的差异

无。计划清单 3 个文件 / 改动要点全部按 PRE 落实；handoff.md §Running Extraction 改名 + 改写首句的细节与 PRE 计划描述一致。

## 验证结果

- [x] `grep -n "S001|S002|S003|S004|S049|Phase 3 in progress|--resume|onboarded|first work package|first-work|First Work Package|Current Work Continuation"` on changed files — 0 命中（除 maintenance comment 中的 `S001` 占位例子，已被 `grep -v "Character A.*S001"` 过滤；`--resume` 仅在 handoff.md CLI 模板 / resume gate 工程指引中合法保留）
- [x] `grep -rn "Chinese web novel|500+ chapters|2 target characters confirmed|991c09f|7639c8b|char_support.*error_max_turns" ai_context/` — 0 命中
- [x] `current_status.md` 阅读后 §Project Stage 仅描述 framework 工程层；§What Exists / §Current Gaps 不含 specific stage / sha / 真实作品提及
- [x] `next_steps.md` Highest Priority 段不含 first-work 进度（顶条由 schema refinement 接替）
- [x] `handoff.md` 段标题改为 "Running Extraction"；CLI 模板用 `<work_id>` 占位，仍可直接执行
- [x] 上一轮 commit `c46fd8d` 引入的 main vs extraction/library 分支语境限定行保留（`current_status.md:44`，原 line 64，因前段被删后整体上移）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-30 10:03:52 EDT
