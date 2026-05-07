# cli_background_validation_completeness

- **Started**: 2026-05-07 06:56:23 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

- 上一轮 `/post-check` 对 df4cdbe (cli_resume_phase_agnostic) 出 REVIEWED-PARTIAL：1 Medium Finding（architecture.md 缺索引）+ 1 Residual Risk（cli.py `--background` 校验只覆盖 phase_1_5 not done 维度，phase_1_5 done 时既无 `--resume` 也无 `--characters` 的组合会让 daemon 撞 run_full L2730 `input("Resume from existing progress? [Y/n]: ")` stdin 死锁）。
- 用户原话："修复"——按 /post-check 报告里两条全修。
- Residual Risk 实际是漏校验分支，按 bug 修；不是单纯风险登记。

## 结论与决策

单 commit 双修：(1) architecture.md "Key Design" 段补一行 CLI `--resume` / `--background` 索引，对齐既有 "Lane-level resume / Phase 0 recovery sweep / Length-bound tolerance gate" 三条同性质条目格式；(2) cli.py L213-227 `if args.background:` 块补对偶分支——phase_1_5 done 时也要 `--resume` 或 `--characters` 二选一，保证 daemon 路径下任何 stdin prompt 都被跳过。同步 README + extraction_workflow + decisions.md §51 + smoke 文件场景表。

不在本次范围：confirm_with_user 内部 stdin 设计（preset_characters / preset_end_stage 旁路已在）、run_full 内 input() 位置（L2730——非 daemon 路径合法交互点）、schemas / simulation / works/、其他 Findings 之外的旁枝。

## 计划动作清单

### Fix 1 — architecture.md Key Design 索引

- file: `ai_context/architecture.md` "## Automated Extraction Pipeline" 内 "### Key Design" 段（L162-172）
  - 在合适位置（参考既有 "Lane-level resume (Phase 3)" / "Phase 0 recovery sweep" / "Length-bound tolerance gate" 三条的格式）补 1 行：CLI `--resume` 阶段无关续跑契约简述 + → decision #51 指针
  - 不动同段其他既有条目；不动 architecture.md 其他段

### Fix 2 — cli.py 双分支校验

- file: `automation/persona_extraction/cli.py` L213-227 `if args.background:` 块
  - 当前单分支："phase_1_5 not done + 无 --characters → 拒绝"
  - 补对偶："phase_1_5 done + 既无 --resume 也无 --characters → 拒绝"——daemon 进 run_full 后 L2730 input() 会撞 stdin
  - 重写后：
    ```python
    if not phase15_done:
        if not args.characters:
            print("[ERROR] --background requires --characters when "
                  "phase_1_5 is not yet done (orchestrator would block "
                  "on the interactive Phase 1.5 prompt).")
            sys.exit(1)
    else:
        if not args.resume and not args.characters:
            print("[ERROR] --background requires --resume or --characters "
                  "when phase_1_5 is done (orchestrator would block on "
                  "the 'Resume from existing progress?' prompt).")
            sys.exit(1)
    ```
  - `--background` 帮助文本同步：阐述完整双分支契约

### Fix 2 测试 — smoke 扩 6 场景

- file: `automation/persona_extraction/_smoke_cli_resume_background_validation.py`
  - 现 4 场景 A/B/C/D 不变
  - 新增 (E)：phase_1_5 done + --background **无任何旁路** (no --resume / no --characters) → expect sys.exit(1) + msg 含 "phase_1_5 is done" 关键字
  - 新增 (F)：phase_1_5 done + --background --characters X (no --resume) → expect 接受（旁路成立）
  - 主函数 results 列表 + Summary 里包含 6 场景

### Fix 3 — 文档同步

- file: `automation/README.md` L130-138 `--background` 段：单边 → 双边契约
- file: `docs/architecture/extraction_workflow.md` "### CLI `--resume` 阶段无关续跑" 子段：补对偶分支
- file: `ai_context/decisions.md` §51：现措辞 "未 done 则强制要求 --characters；已 done 则 --characters 可省" 改成 "未 done 强制 --characters；已 done 强制 --resume 或 --characters 二选一"——既有措辞错把 "done 时无需任何旁路" 当结论，是这条 Residual Risk 的根因措辞

## 验证标准

- [ ] 全 import chain 无回归：`python -c "import automation.persona_extraction.cli, automation.persona_extraction.orchestrator, automation.persona_extraction.scene_archive, automation.persona_extraction.consistency_checker, automation.persona_extraction.post_processing, automation.persona_extraction.manifests, automation.repair_agent.coordinator"`
- [ ] 现有 5 个 smoke 全过：`_smoke_memory_digest_correspondence` / `_smoke_post_processing_replace_slice` / `_smoke_recovery_sweep` / `_smoke_l3_gate` / `_smoke_cli_resume_background_validation`（其中最后一项扩为 6 场景）
- [ ] 35 个 schema metaschema check 0 失败
- [ ] grep `phase_1_5 is done` cli.py → ≥ 1 命中（新拒绝路径 msg）
- [ ] grep `phase_1_5 is not yet done` cli.py → 维持 1 命中（既有拒绝路径 msg 不变）
- [ ] grep "Key Design" ai_context/architecture.md 找到段落，新加行包含 "decision #51" 引用
- [ ] grep "已 done 则 --characters 可省" decisions.md → 0 命中（旧措辞清理）
- [ ] `python -m automation.persona_extraction.cli --help` → 正常输出

## 执行偏差

无。

## 已落地变更

### Fix 1 — architecture.md Key Design 索引

- `ai_context/architecture.md` L172 新增一条 "**CLI `--resume` phase-agnostic resume**"，格式与同段既有 "Lane-level resume / Phase 0 recovery sweep / Length-bound tolerance gate" 三条对齐：1 段简述 + → cli.py + orchestrator.run_full + decision #51 plumbing pointer

### Fix 2 — cli.py 双分支校验

- `automation/persona_extraction/cli.py` L208-239 `if args.background:` 块改造：
  - 旧：单分支只检 "phase_1_5 not done + 无 --characters → 拒绝"
  - 新：双分支
    - phase_1_5 not done + 无 --characters → 拒绝（msg 含 "phase_1_5 is not yet done"）
    - phase_1_5 done + 既无 --resume 也无 --characters → 拒绝（msg 含 "phase_1_5 is done"）
  - 注释扩写：明确两个 stdin prompt site（confirm_with_user / run_full resume prompt）+ 各自的 bypass 条件
- `automation/persona_extraction/cli.py` `--background` 帮助文本改造：从单边 "Stage-aware validation: when phase_1_5 is not yet done, --characters is required..." 改成双分支描述

### Fix 2 测试 — smoke 扩 6 场景

- `automation/persona_extraction/_smoke_cli_resume_background_validation.py`
  - 顶部 docstring 改写：单分支语义 → 双分支语义；4 场景列表 → 6 场景
  - 新增 `_scenario_e`：phase_1_5=done + --background 不带任何旁路 → expect sys.exit(1) + msg 含 "phase_1_5 is done"
  - 新增 `_scenario_f`：phase_1_5=done + --background --characters X (no --resume) → expect 接受
  - main() results 列表加 (E, F)；6 场景全跑

### 文档同步

- `automation/README.md` `--background` 段：单边描述 → 双边契约（用 bullet list 阐述两分支）
- `docs/architecture/extraction_workflow.md` "### CLI `--resume` 阶段无关续跑" 子段末段：单边 → 双边契约
- `ai_context/decisions.md` §51：现措辞 "未 done 则强制要求 --characters；已 done 则 --characters 可省"（错把 "done 时无需任何旁路" 当结论）改成 "未 done 强制 --characters；已 done 强制 --resume 或 --characters 二选一"。同时把 "4 场景" 引用改成 "6 场景"

## 与计划的差异

无。PRE 计划清单全部按原方案落地。

## 验证结果

- [x] 全 import chain 无回归：cli + orchestrator + scene_archive + consistency_checker + post_processing + manifests + repair_agent.coordinator 全 import 通过
- [x] 5 个 smoke 全过：_smoke_memory_digest_correspondence 4/4 + _smoke_post_processing_replace_slice 4/4 + _smoke_recovery_sweep 4/4 + _smoke_l3_gate 4/4 + _smoke_cli_resume_background_validation **6/6**（A/B/C/D/E/F 全 OK）
- [x] 35 个 schema metaschema check 0 失败
- [x] grep "phase_1_5 is done" cli.py → 1 命中（新拒绝路径 msg）
- [x] grep "phase_1_5 is not yet done" cli.py → 1 命中（既有拒绝路径 msg 不变）
- [x] grep "decision #51" ai_context/architecture.md → L172 命中（新加 Key Design 条目）
- [x] grep "已 done 则 --characters 可省" decisions.md → 0 命中（旧措辞清理）
- [x] python -m automation.persona_extraction.cli --help → 正常输出

## Completed

- **Status**: DONE
- **Finished**: 2026-05-07 07:01:37 EDT
