# run_full_branch_switch_at_phase0

- **Started**: 2026-05-07 16:42:47 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

用户跑 phase 1 daemon 后发现：daemon 运行期间 `git branch --show-current` 仍是 `main`，phase 0 / phase 1 / phase 1.5 的 LLM 调用 + 产物落地 全部发生在 main worktree。

调查 [`orchestrator.py:run_full`](automation/persona_extraction/orchestrator.py) 后定位到原因：当前 fresh-start 路径（`pipeline.is_done("phase_1_5") == False`）下，`run_summarization` / `run_analysis` / `confirm_with_user` 三个调用在 `try` 块**外**，只有 `run_baseline_production` + `run_extraction_loop` 在 `try` 块内（`create_extraction_branch` 之后）。即：phase 0 / 1 / 1.5 在 main 跑、phase 2/3+ 才在 extraction 分支跑。

`ai_context/architecture.md §Git Branch Model` / `decisions.md #26` / `conventions.md §Git` 三处权威文档反复强调"Extraction runs on extraction/{work_id} branch"，**没有任何 ADR 解释为什么 phase 0/1/1.5 例外**——这是代码实现疏漏（隐性"反正 .gitignore 屏蔽了 progress/ + chapter_summaries/，不会污染 main commit 历史"的实用主义没落到设计层），不是有意决策。用户预期 = 整个提取流程在 extraction 分支跑。

## 结论与决策

修 `run_full` fresh-start 路径，把 `try` 块起点上移，让 `create_extraction_branch()` 在 phase 0 启动**之前**调，phase 0 / 1 / 1.5 / 2 / 3+ 全部在 extraction 分支跑。`finally` 仍走 `checkout_main`，SIGKILL 中断时 git HEAD 会停在 extraction 分支，下次 resume 走两条路径之一都能保证仍在 extraction 分支：

- phase 1.5 未 done 的 resume：走 fresh-start → 改后的 try 块切 ✓
- phase 1.5 done 的 resume：走 [`run_extraction_loop:1715-1721`](automation/persona_extraction/orchestrator.py#L1715-L1721) 已有 try 块切 ✓

`pipeline.extraction_branch` 字段当前由 `confirm_with_user`（line 1623-1626）才填上正式值；run_full 入口需要这个值才能切分支，所以补一段：load 出来的 pipeline 若 extraction_branch 为空则补填 `f"{prefix}{work_id}"`，新建的 pipeline 直接传入。confirm_with_user 内重建 pipeline 的逻辑保留（覆盖会覆盖回同一个值，幂等）。

## 计划动作清单

- file: `automation/persona_extraction/orchestrator.py:run_full` → 三处改动：
  1. line 2826-2830 附近 pipeline 创建 / load 后，统一补填 `extraction_branch = f"{prefix}{work_id}"`（无值时）
  2. 把 `try:` 块起点上移到 `self.run_summarization()` 之前；`create_extraction_branch()` 在所有 phase 调用之前；`finally: checkout_main` 范围相应扩大
  3. confirm_with_user 重新创建 pipeline 后赋值给外层变量（已有），无需改
- file: `ai_context/architecture.md` §Git Branch Model → 把"Idle = main. Orchestrator auto-checks out extraction/{work_id}"明确成"all 5 phases (0/1/1.5/2/3+) run on extraction branch"
- file: `ai_context/decisions.md` #26 / #26a → 同步措辞，把"phase 0/1/1.5 例外不切"的隐含行为反向钉死成"全部在 extraction 分支"

## 验证标准

- [ ] `python -c "from automation.persona_extraction import orchestrator"` import 无报错
- [ ] grep `run_summarization\|run_analysis\|confirm_with_user` 在 `run_full` 内的调用必须在 `try:` 块内（即位置在 line `try:` 之后、`finally:` 之前）
- [ ] grep `create_extraction_branch` 在 `run_full` 内仅出现 1 次，且在 `run_summarization()` 调用**之前**
- [ ] smoke：mock 一个 PipelineProgress(extraction_branch="") 跑 `run_full` 入口的 fill-in 逻辑（不实际跑 phase），断言 `pipeline.extraction_branch == f"{prefix}{work_id}"`
- [ ] 运行时手测（可选，对照测）：`python -m automation.persona_extraction "<work_id>" --start-phase 1 --characters X Y --end-stage 0 --background` 启动后 `git branch --show-current` 应为 `extraction/<work_id>`，pipeline.json `extraction_branch` 字段非空

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

- `automation/persona_extraction/orchestrator.py:run_full` (line 2825-2884)：
  - 新建 / load 出来的 pipeline 都在入口处补填 `extraction_branch = f"{prefix}{work_id}"`（empty 才补，否则保留）
  - `try:` 块起点上移到 `run_summarization()` 之前
  - `create_extraction_branch()` 在 phase 0 启动**之前**调（line 2853），调用失败 `sys.exit(1)`
  - `run_summarization()` (2858) / `run_analysis()` (2859) / `confirm_with_user()` (2860) / `run_baseline_production()` (2869) / `commit_stage()` (2871) / `run_extraction_loop()` (2878) 全部在 try 内
  - `finally: checkout_main(scope_paths=[f"works/{work_id}/"])` 范围扩大到所有 5 个 phase 的覆盖
- `ai_context/architecture.md` line 138：`Idle = main. Orchestrator auto-checks out extraction/{work_id}` 后追加 `**before Phase 0** (the very first LLM call)` 强调时序，明列 5 个 phase 都在 extraction 分支跑
- `ai_context/decisions.md` #26a：补"outer try block in run_full covers all five phases (0/1/1.5/2/3+)"段，并加 `pipeline.extraction_branch` filled at run_full entry 的描述
- `docs/architecture/extraction_workflow.md` line 635-650 段：把"`run_extraction_loop` / `run_full` 把 ... 整体包进 try"重写为"`run_full` 的外层 try 块覆盖**全部 5 个 phase**"，加 SIGKILL 行为说明 + idempotent create_extraction_branch 描述

## 与计划的差异

无 — PRE 计划动作清单全部落地。

## 验证结果

- [x] `python -c "from automation.persona_extraction import orchestrator"` import 无报错
- [x] `run_summarization` (2858) / `run_analysis` (2859) / `confirm_with_user` (2860) 都在 `try:` (2851) ↔ `finally:` (2880) 之间
- [x] `create_extraction_branch` 在 `run_full` 内仅出现 1 次（line 2853），且在 `run_summarization()` (2858) 之前
- [x] smoke 跑过：empty-extraction_branch 的 PipelineProgress 经 fill-in 后变为 `extraction/TEST_WORK`；预填 `extraction/TEST2` 的 pipeline 不被覆盖
- [ ] 运行时手测（可选）：未跑 daemon 实测；下次用户重跑 `--start-phase 1` 时观察 `git branch --show-current = extraction/<work_id>` 即生效

## Completed

- **Status**: DONE
- **Finished**: 2026-05-07 16:47:03 EDT
