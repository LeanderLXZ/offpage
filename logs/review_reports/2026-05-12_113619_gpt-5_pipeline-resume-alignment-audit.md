**Review 模型**：Codex（`gpt-5`）

# /full-review — Pipeline Resume Alignment Audit

## Findings

**H1** `automation/persona_extraction/progress.py:185` — `PipelineProgress.load()` 会把当前格式的 `phase_2` 当成 legacy key 迁移，导致已完成的 Phase 2 状态在续跑时丢失。

结论：当前 `PHASE_KEYS` 已包含 `"phase_2"`（baseline 阶段），`save()` 也原样写出当前 `self.phases`，但 `load()` 对磁盘上的任意 `"phase_2"` 都执行 `_LEGACY_PHASE_KEY_MAP["phase_2"] -> "phase_1_5"`。这会把当前格式 `pipeline.json::phases.phase_2 = done` 误归到 `phase_1_5`，然后 `__post_init__` 再补一个新的 `phase_2 = pending`。

证据：
- `PHASE_KEYS` 当前阶段名包含 `"phase_1_5"` 与 `"phase_2"`：`automation/persona_extraction/progress.py:112`
- legacy map 仍把 `"phase_2"` 映射为 `"phase_1_5"`：`automation/persona_extraction/progress.py:120`
- `save()` 写出的就是当前 `self.phases`：`automation/persona_extraction/progress.py:160`
- `load()` 无条件对 raw key 做 legacy map：`automation/persona_extraction/progress.py:181`
- Phase 2 是否已完成直接控制 baseline 分支：`automation/persona_extraction/orchestrator.py:2235`

我用临时目录做了 round-trip 复现：保存 `phase_1_5=done, phase_2=done` 后再 `PipelineProgress.load()`，结果 `phase_2_done? False`，loaded phases 中 `phase_2` 变回 `pending`。

影响范围：每次从已落盘 `pipeline.json` 续跑时，baseline 完成状态会被忘记；轻则重复 validate Phase 2，重则在已有 baseline 文件不再通过当前校验时触发自动 Phase 2 recovery。这个问题还会放大 H2。

**H2** `automation/persona_extraction/orchestrator.py:2273` — validation-triggered Phase 2 recovery 可以改写 `target_baseline.json`，但没有在已有 Phase 3 committed 产物时阻断或清理级联产物。

结论：`run_baseline_production()` 的 docstring 已明确说明重跑 Phase 2 可能改写 `target_baseline.json`，且 baseline 变化后必须清空所有 Phase 3 stage snapshots / memory / digests / progress；但 `run_extraction_loop()` 在 existing baseline validation 失败时会直接重跑 Phase 2 并 commit baseline recovery，没有检测已经存在的 Phase 3 committed artifacts，也没有执行/要求 reset。

证据：
- Phase 2 重跑级联警告写明 baseline 改写会使所有 Phase 3 stage snapshot 与新 baseline targets 不一致：`automation/persona_extraction/orchestrator.py:1910`
- 同一 docstring 写明“重跑 phase 2 必须配套清空所有 phase 3 产物”：`automation/persona_extraction/orchestrator.py:1918`
- 同一 docstring 写明本函数不自动清理 Phase 3 产物：`automation/persona_extraction/orchestrator.py:1925`
- existing baseline validation 失败时，代码直接调用 `self.run_baseline_production(...)` 并提交 recovery：`automation/persona_extraction/orchestrator.py:2273`
- Phase 3 reconcile 对 `COMMITTED` stage 只检查文件存在和 commit SHA；不会重新校验 D4 baseline target key 集合：`automation/persona_extraction/progress.py:705`
- Phase 3.5 已声明不再负责 D4 target key equality：`automation/persona_extraction/consistency_checker.py:10`

影响范围：如果 Phase 2 recovery 后 baseline targets 发生变化，已有 committed Phase 3 artifacts 可能继续被视作有效；Phase 3.5 不会兜底 D4，最终可能产出 baseline 与 stage snapshots 不一致的角色包。结合 H1，这条路径更容易在普通续跑中被误触发。

**M1** `automation/persona_extraction/cli.py:159` — `--background` help 和多处 docs 漏写 pending `phase_1_5` 时必须同时提供 `--end-stage`。

结论：CLI 运行逻辑已经按最新决策要求：`--background` 且 `phase_1_5` 未 done 时，必须同时提供 `--characters` 和 `--end-stage`，否则 daemon 仍可能撞到 Phase 1.5 的第二个 stdin prompt。但 help text、README、architecture docs、ai_context summary 仍只写了 `--characters`。

证据：
- stale help text 只写 `phase_1_5 not done -> --characters required`：`automation/persona_extraction/cli.py:158`
- 实际 guard 要求 `--characters`：`automation/persona_extraction/cli.py:271`
- 实际 guard 还要求 `--end-stage`：`automation/persona_extraction/cli.py:278`
- README 后台运行说明 pending 分支只列 `--characters`：`automation/README.md:145`
- extraction workflow docs 同样只列 `--characters`：`docs/architecture/extraction_workflow.md:578`
- ai_context architecture summary 同样只列 `--characters`：`ai_context/architecture.md:172`

影响范围：操作者按文档启动后台任务时会被 CLI 拒绝，或误解 daemon-safe 参数组合。代码本身保护了 prompt deadlock，问题主要在操作文档和 help 的漂移。

**L1** `works/README.md:235` — stage chapter count 说明仍写“最小 5 章”，与当前 schema/config/docs 的 8-15 硬约束冲突。

结论：当前 stage plan monolithic 路径的章节数下限已经是 8，且 schema 描述明确 light_novel 的 `chapter_count=1` 是程序派生且不走 schema validate 的已知例外；`works/README.md` 仍写“最小 5 章”。

证据：
- `works/README.md` 写默认 10、最小 5、最大 15：`works/README.md:235`
- schema 当前 `minimum = 8`、`maximum = 15`：`schemas/analysis/stage_plan.schema.json:50`
- config 当前 `min_chapter_count = 8`：`automation/config.toml:23`

影响范围：这是产物目录说明漂移，容易误导后续手工检查 stage plan 或作品 config 的人；运行时约束本身没有因此失效。

**L2** `automation/config.toml:36` — Phase 0 chunk size / summary length 注释和架构概览仍停留在旧值，和当前 CLI/schema 不一致。

结论：当前 CLI 默认 `--chunk-size` 是 20，chapter summary schema 要求 per-summary `summary` 150-200 字；但 config 注释仍按“每 chunk 读 25 章 + 25× per-summary 100-150 字”估算，system overview 也写“约 25 章/组”。

证据：
- CLI 默认 chunk size 是 20：`automation/persona_extraction/cli.py:119`
- config 注释仍写 25 章和 100-150 字：`automation/config.toml:36`
- schema 当前 per-summary 是 150-200 字：`schemas/analysis/chapter_summary_chunk.schema.json:163`
- system overview 仍写 chunk 约 25 章/组：`docs/architecture/system_overview.md:126`

影响范围：低风险文档/注释漂移；它不会改变运行时行为，但会误导 timeout、token、吞吐估算。

## False Positives / Checked Non-Issues

- `works/` 下本地存在被 ignore 的真实提取产物，但 `git ls-files works users` 只显示 `works/README.md` 与 `users/_template/` 示例文件；当前仓库没有把真实 work artifacts 误提交进 main。这不是 finding。
- `light_novel` 模式的 `stage_plan.chapter_count=1` 与 schema `minimum=8` 冲突是已记录的 trade-off：schema 描述写明该程序派生产物不走 phase 1 schema validate。这次不作为 bug；见 OQ3。
- JSON Schema 自身可通过 metaschema 校验；我跑了 `jsonschema.validators.validator_for(...).check_schema(...)`，结果为 `schemas ok`。

## Alignment Summary

整体上，schema、prompt、config 对 Phase 1/2/3 的最新结构基本对齐：`stage_plan` 8-15 约束、Phase 1 foundation 前移、Phase 2 baseline replacement、Phase 3 D4 单阶段 repair gate 这些主线在核心文件里能互相印证。

最不对齐的是“进度恢复/自动 recovery”这一层：`PipelineProgress.load()` 的 legacy 迁移逻辑和当前 `pipeline.json` 格式混在一起，直接影响续跑状态机；而 Phase 2 recovery 的 destructive cascade 只写在 docstring 里，没有对应 guard。其次是后台运行说明和若干低层文档注释的 drift。

样例产物线未发现已提交真实作品产物与“main 只保留 framework/template”的叙述冲突。

## Residual Risks

- 本轮遵守 read scope，没有读取 `sources/`、完整 `users/.../sessions/`、完整 work evidence 或历史 `logs/change_logs/`；这些区域可能仍有项目外部数据或历史决策细节未覆盖。
- H1 的修复需要小心兼容 legacy `pipeline.json`。如果简单移除 `_LEGACY_PHASE_KEY_MAP`，旧进度文件可能无法正确前迁。
- H2 的最稳妥行为涉及 destructive reset policy；当前 review 只确认缺口，没有替用户决定是“阻断并提示手工 reset”还是“实现自动 reset”。
- `light_novel` 的 schema-invalid trade-off 当前已被文档承认，但如果未来有外部工具独立校验 `stage_plan.json`，这会重新变成契约问题。

## Open Questions / Ambiguities

**OQ1** `PipelineProgress.load()` 应该如何区分 legacy 和 current `pipeline.json`？

推荐澄清：只有在出现明确 legacy shape（例如存在 `phase_2_5`，或缺失 `phase_1_5` 且带旧版本标记）时才迁移；长期建议给 `pipeline.json` 增加 `schema_version`。

**OQ2** Phase 2 validation-triggered recovery 遇到已有 Phase 3 committed artifacts 时，默认策略应该是阻断还是自动 destructive reset？

推荐澄清：默认阻断并打印需要清理的路径；只有显式 `--reset-phase3-after-baseline-change` 一类开关才允许自动清理。

**OQ3** `light_novel` 的 `chapter_count=1` 是否应继续作为 schema 外例外，还是应该进入 schema 正式契约？

推荐澄清：如果所有生产路径都只由 orchestrator 生成且不会被外部 validator 消费，可以继续留 todo；如果要支持通用 artifact validation，应把 schema 改成 mode-aware `oneOf` 或增加结构模式字段。

## Recommendations

- H1 建议修：给 `PipelineProgress.load()` 加 current-vs-legacy 判定，避免 current `phase_2` 被 remap；加一个 round-trip regression test 覆盖 `phase_1_5=done, phase_2=done`。
- H2 建议修：Phase 2 validation-triggered recovery 前检测 `phase3_stages.json` 和 stage snapshot/digest 产物；若存在 committed/non-empty Phase 3，默认 hard stop，并输出 reset 指令或要求显式 destructive flag。
- M1 建议修：同步更新 CLI help、`automation/README.md`、`docs/architecture/extraction_workflow.md`、`ai_context/architecture.md`，把 pending `phase_1_5` 的后台要求写成 `--characters` + `--end-stage`。
- L1 建议修：把 `works/README.md` 的 stage 下限改为 8，并注明 `light_novel` 单 subsection 例外由 orchestrator 程序派生。
- L2 建议修：把 Phase 0 相关注释/docs 调整为默认 chunk size 20、per-summary 150-200 字；若 timeout 经验值仍基于 25 章，需要重新标注为历史估算或重算。
- OQ1 建议修：优先用 shape-based migration 快速止血，后续加 `schema_version`。
- OQ2 建议修：先选择“阻断 + 明确人工 reset”作为安全默认，再评估自动 reset。
- OQ3 建议留 todo：除非近期要引入外部 artifact validator，否则不急于扩大 schema 变更面。

建议落地顺序：H1 → H2 → M1 → L1/L2；H1 和 H2 应优先一起处理，因为 H1 会增加 H2 路径被普通续跑触发的概率。
