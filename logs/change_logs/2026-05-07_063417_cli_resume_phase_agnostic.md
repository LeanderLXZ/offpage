# cli_resume_phase_agnostic

- **Started**: 2026-05-07 06:34:17 EDT
- **Branch**: main (worktree at `../offpage-main`)
- **Status**: PRE

## 背景 / 触发

- 上一轮 `/go` 落地 codex 6 项 finding 后，用户切到 `extraction/<work_id>` 想后台跑 extraction，命令 `python -m automation.persona_extraction.cli ... --resume --background` 启动后立即退出：`[ERROR] No existing progress for '...'.`（cli.py:281 触发）。
- 根因：cli.py:248-310 的 `if args.resume:` 分支硬要求 `Phase3Progress` 已存在或 `phase_1_5` done（用 stage_plan 重建）；当前状态 phase 0 done、phase 1/1.5/3 都没跑过，不满足，所以 resume 被拒。
- 用户原话："我需要改造 CLI，让任何时候都可以 resume，这也是原本的设计"。
- 现状（已 read 验证）：`orchestrator.py::run_full` (L2658-2782) 已具备完整 resume-from-anywhere 能力——它顺序走 Phase 0 (`run_summarization` 内置 schema-gated `_chunk_passes_full_check` skip)、Phase 1 (`run_analysis` 同样有产物存在则跳过的 retry-aware 逻辑)、Phase 1.5 (`confirm_with_user` 用 preset_characters 旁路)，并在 phase_1_5 done + phase3 在手时直接进 `run_extraction_loop`；其内部 self-heal 路径也包含 `migrate_legacy_progress` + stage_plan rebuild + reconcile_with_disk。所以 cli.py 那个 `--resume` 分支是 **多余且重叠的旁路**，反而把 resume 锁死到只能从 Phase 3 开始。

## 结论与决策

把 cli.py 的 `--resume` 从"专修 Phase 3 loop 的旁路"改成"传给 `run_full` 的 auto-yes 信号"——`run_full` 是真正的 resume entry point，按 phase 顺序自检 + skip + self-heal。`--background` 校验改成阶段感知（读 pipeline.json 的 phase_1_5 状态，未 done 时强制要求 `--characters` 避免后台撞 stdin）。

不在本次范围：confirm_with_user 的两处 input（已被 preset_characters / preset_end_stage 兜底）、Phase 3 内部两处 commit/squash-merge prompt（与 resume 无关）、run_summarization / run_analysis / run_baseline_production 的 skip-detection（已 OK）、schemas/、simulation/。

## 计划动作清单

- file: `automation/persona_extraction/cli.py`
  - 删 L248-311 整个 `if args.resume: ... else: orch.run_full(...)` 二分；改成无条件 `orch.run_full(preset_characters=args.characters, preset_end_stage=args.end_stage, auto_resume=args.resume)`
  - 删除随之失效的 import：`Phase3Progress`、`StageEntry`、`migrate_legacy_progress`（grep 全文确认它们只在 L248-311 用过）
  - L184-192 `--background` 校验改造：从"requires --resume or --characters"改成"读 pipeline.json，若 phase_1_5 not done 则 require --characters"。新增 `_load_pipeline_status(project_root, work_id)` helper（仅本文件用，纯 json.loads 包装；缺失/parse 错误 → None）
  - `--resume` 帮助文本从 "Resume from existing progress (skip analysis)" 改成"任意阶段从已落盘进度续跑（auto-yes 'Resume from existing progress?' 提示；run_full 已具备阶段无关 self-heal）"
- file: `automation/persona_extraction/orchestrator.py::run_full` (L2658-2782)
  - 签名增加 `auto_resume: bool = False`
  - L2730 `resume = input("Resume from existing progress? [Y/n]: ").strip()` 改造：if `auto_resume` → `print("  Auto-resuming (--resume passed).")` + 直接走 run_extraction_loop（合并到现有 `if preset_characters:` 分支即可，逻辑等价）
  - 不动 confirm_with_user / Phase 3 内部 prompts
- file: `automation/persona_extraction/_smoke_cli_resume_background_validation.py`（新建）
  - 4 场景：(A) phase_1_5 done + --resume --background 不带 --characters → 应该接受（顺利进 launch_background；本 smoke mock launch_background 不真启动）; (B) phase_1_5 pending + --resume --background 不带 --characters → 应该拒绝 sys.exit(1) + "phase_1_5 is not yet done"; (C) phase_1_5 pending + --background --characters X → 应该接受; (D) pipeline.json 缺失 + --background --characters X → 应该接受（视作 phase_1_5 未 done，但 --characters 满足旁路）
- file: `automation/README.md`
  - grep `--resume` 看是否提及旧"phase3 progress required"语义；若有，改成新描述
- file: `docs/architecture/extraction_workflow.md`
  - 同上 grep；若任何 §x.y resume 段提及旧语义，改成新描述
- file: `ai_context/decisions.md`
  - 加 §51：CLI `--resume` 阶段无关续跑契约。Body 写：cli.py 的 `--resume` 只是 run_full 的 auto-yes 信号；run_full 是真正的 resume entry point，按 phase 顺序自检 + skip + self-heal；--background 与 --resume 正交，--background 仅约束"phase_1_5 not done 时必须 --characters"避免 stdin 死锁。Plumbing → cli.py + orchestrator.run_full(auto_resume=...)

## 验证标准

- [ ] 全 import chain 无回归：`python -c "import automation.persona_extraction.cli, automation.persona_extraction.orchestrator, automation.persona_extraction.scene_archive, automation.persona_extraction.consistency_checker, automation.persona_extraction.post_processing, automation.persona_extraction.manifests, automation.repair_agent.coordinator"`
- [ ] 现有 4 个 smoke 全过：`_smoke_memory_digest_correspondence` / `_smoke_post_processing_replace_slice` / `_smoke_recovery_sweep` / `_smoke_l3_gate`
- [ ] 35 个 schema metaschema check 0 失败
- [ ] grep `if args.resume:` cli.py → 0 命中
- [ ] grep `Phase3Progress\|StageEntry\|migrate_legacy_progress` cli.py → 0 命中
- [ ] grep `auto_resume` orchestrator.py → ≥ 2 命中（签名 + 使用点）
- [ ] grep `auto_resume` cli.py → ≥ 1 命中
- [ ] 新 smoke `_smoke_cli_resume_background_validation` 4 场景全过
- [ ] grep "phase3 progress" automation/README.md docs/architecture/extraction_workflow.md → 0 命中（无残留旧语义）
- [ ] `python -m automation.persona_extraction.cli --help 2>&1 | head -40` 正常输出

## 执行偏差

- **Step 7 review 即修**：Step 3 / Step 4 新写的文字三处含"不再要求 phase3 progress 必须存在"等 history-narration 措辞，与 conventions.md §Generic Placeholders 的"No history narration"约束擦边。三处都改成正面描述（如"与磁盘上具体哪个 phase 已落盘无关"、"`--resume` 是 run_full 的 auto-yes 信号"），保留语义但去掉"过去 → 现在"叙述。

## 已落地变更

### cli.py 重构

- `automation/persona_extraction/cli.py`
  - 顶部 import：删 `Phase3Progress` / `StageEntry` / `migrate_legacy_progress`（这三个 symbol 在 cli.py 里只在被删的 `if args.resume:` 分支用过）；加 `import json`
  - 新增 `_load_pipeline_status(project_root, work_id) -> dict | None`（仅本文件用）：纯 json.loads 包装读 `works/{work_id}/analysis/progress/pipeline.json`，缺失/parse error → None
  - L184-192 `--background` 校验改造：从"requires --resume or --characters" 改为阶段感知——读 pipeline.json，`phases.phase_1_5 != "done"` 则强制要求 `--characters`（避免后台撞 `confirm_with_user` 的 stdin 死锁）
  - 删 L249-311 整个 `try: if args.resume: ... else: orch.run_full(...)` 二分；改成无条件 `orch.run_full(preset_characters=args.characters, preset_end_stage=args.end_stage, auto_resume=args.resume)`（节约 ~60 行重复 self-heal 代码）
  - `--resume` 帮助文本：从 "Resume from existing progress (skip analysis)" 改成"Auto-yes the 'Resume from existing progress?' prompt..."（阐明 run_full 才是 phase-agnostic resume entry，--resume 只 silent 那个交互确认）
  - `--background` 帮助文本：从"Requires --resume or --characters" 改成"Stage-aware validation: when phase_1_5 is not yet done, --characters is required..."

### orchestrator.run_full 加 auto_resume 参数

- `automation/persona_extraction/orchestrator.py::run_full`
  - 签名增加 `auto_resume: bool = False`，更新 docstring 说明 auto_resume 只 silent 一处 input，phase-level skip / self-heal 不变
  - `if pipeline and phase3 and pipeline.is_done("phase_1_5"):` 块内：把 `if preset_characters:` 改成 `if preset_characters or auto_resume:`，分别 print 不同来源的 "Auto-resuming" 标识
  - 其它三处 stdin 点（confirm_with_user 两处 + Phase 3 commit/squash-merge prompt 两处）保持不动——它们与 resume 语义正交

### 新 smoke 文件

- `automation/persona_extraction/_smoke_cli_resume_background_validation.py`（新建，~165 行）
  - 4 场景覆盖 `--background` 校验矩阵：
    - (A) phase_1_5 done + --resume --background no --characters → 接受
    - (B) phase_1_5 pending + --resume --background no --characters → 拒绝 sys.exit(1) + msg
    - (C) phase_1_5 pending + --background --characters X → 接受
    - (D) pipeline.json absent + --background --characters X → 接受
  - 用 `unittest.mock.patch` mock `launch_background` + `validate_source_package`，让校验矩阵可在 tempdir 跑无副作用

### 文档同步

- `automation/README.md`
  - L102-119 在"### 断点续跑"段后补 5 行说明 `--resume` 阶段无关 + 列举 phase-by-phase skip / self-heal 行为
  - L134 `--background` 说明从"要求 --resume 或 --characters" 改成阶段感知校验描述
- `docs/architecture/extraction_workflow.md`
  - "## 自动化编排" 段末新增 "### CLI `--resume` 阶段无关续跑" 子段，详述 run_full phase-by-phase routing + --background 校验逻辑 + --resume / --background 正交关系
- `ai_context/decisions.md`
  - 新增 §51 — 完整的 CLI `--resume` 阶段无关续跑契约。含 plumbing pointer：cli.py + orchestrator.run_full + 新 smoke

## 与计划的差异

- 无功能性偏差。仅 Step 7 触发了 wording cleanup（已记入"执行偏差"段）。
- PRE log 列出的所有计划文件均已落地；新加的 _smoke 文件、orchestrator auto_resume 参数、cli.py refactor、3 份文档同步均按计划完成。

## 验证结果

- [x] 全 import chain 无回归：cli + orchestrator + scene_archive + consistency_checker + post_processing + manifests + validator + ingestion.validator + repair_agent.coordinator + repair_agent.checkers.schema 全 import 通过
- [x] 5 个 smoke 全过：`_smoke_memory_digest_correspondence` 4/4 / `_smoke_post_processing_replace_slice` 4/4 / `_smoke_recovery_sweep` 4/4 / `_smoke_l3_gate` 4/4 / **新** `_smoke_cli_resume_background_validation` 4/4
- [x] 35 个 schema metaschema check 0 失败
- [x] grep `if args.resume:` cli.py → 0 命中
- [x] grep `Phase3Progress|StageEntry|migrate_legacy_progress` cli.py → 仅 1 命中（L288 comment 解释 run_full 内部能力，不是 import 残留）
- [x] grep `auto_resume` orchestrator.py → 5 命中（签名 + docstring + 2 个使用点 + 1 个 print 标识）
- [x] grep `auto_resume` cli.py → 1 命中（传递点）
- [x] `python -m automation.persona_extraction.cli --help` 输出正常
- [x] grep "phase3 progress" automation/README.md docs/architecture/extraction_workflow.md → 2 命中均为 negation context（"--与--无关"）描述新契约的覆盖范围，非旧语义残留
- [x] history-narration scrub：本次新加的 4 处文字（README.md / extraction_workflow.md / decisions.md / cli.py docstring）均无"不再 / legacy / deprecated / formerly / 原为"等 conventions.md §Generic Placeholders 禁的措辞

## Completed

- **Status**: DONE
- **Finished**: 2026-05-07 06:43:41 EDT

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实

- 落实率：12/12 项计划 + 10/10 项验证标准全过
- Missed updates: 0 条（计划项 + 验证标准两侧都 100% 落实）

### 轨 2 — 影响扩散

- Findings: High=0 / Medium=1 / Low=0
  - **[M]** `ai_context/architecture.md::Key Design` 段缺一行 CLI `--resume` 阶段无关 + `--background` 阶段感知索引（Cross-File Alignment "Extraction workflow" 行触发）。其他类似条目 Lane-level resume / Phase 0 recovery sweep / Length-bound tolerance gate 都在该段有 1 行 + decision pointer，本次新增 decision #51 没补对应索引。
- Open Questions: 0 条

## 复查时状态

- **Reviewed**: 2026-05-07 06:51:04 EDT
- **Status**: REVIEWED-PARTIAL
  - 理由：轨 1 全落实；轨 2 有 1 Medium（architecture.md "Key Design" 段索引缺失），无 High
- **Conversation ref**: 同会话内 /post-check 输出
