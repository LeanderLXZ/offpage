**Review 模型**：Codex (GPT-5)（`gpt-5`）

# /full-review — Repo Alignment Review

审计范围：按 `ai_context/skills_config.md` 读取 `ai_context/`、`docs/requirements.md`、`docs/architecture/`，并扫描 `schemas/`、`automation/`、`simulation/`、`prompts/`、`works/`、`users/_template/`、`README.md`、`.gitignore`。本轮只归档 review 报告，不修改业务代码 / schema / prompt / docs。

## Findings

### High 1 — 角色快照提取 prompt 未传入 `target_baseline.json`，D4 硬约束在生成侧不可满足

结论：规范要求 Phase 3 每个角色阶段调用都读取 `identity.json + target_baseline.json`，并在单 stage validate 层强制 `voice_state.target_voice_map` / `behavior_state.target_behavior_map` / `relationships` 的 key set 等于 baseline targets；但实际 `char_snapshot` read list 没有加入 `target_baseline.json`，模板运行时说明也只写 `identity.json + 当前 stage_snapshot`。这使提取 worker 只能靠猜测满足 baseline 全量 key 集。

为什么是问题：D4 规则要求既不能漏 baseline target，也不能写 baseline 外 target。worker 看不到 baseline 时，无法为“baseline 已列但本 stage / cumulative 从未登场”的 target 生成占位，也无法判断原文中出现的新 target 是否 baseline 未覆盖。结果会把本应在生成前可控的约束推迟到 repair 阶段，增加重复抽取 / 文件级 repair / Phase 3 卡死风险。

影响范围：所有 `char_snapshot` lane；尤其是 target_baseline 已落地后的 S003+ 抽取、resume、repair lifecycle。

证据：

- `docs/requirements.md:1414-1415`：编排脚本预先列出 read list，且 `identity.json + target_baseline.json` 每个 stage 都传入；target_baseline 在 Phase 3 全程只读不写，并作为单 stage validate 层硬约束。
- `automation/persona_extraction/prompt_builder.py:433-471`：`_build_char_snapshot_read_list()` 只加入 `stage_snapshot.schema.json`、`identity.json`、previous `stage_snapshot`、源章节；没有加入 `target_baseline.json`。
- `automation/prompt_templates/character_snapshot_extraction.md:23-35`：模板只强调 read list 中包含 `identity.json`，并写明运行时只加载 `identity.json + 当前 stage_snapshot`。
- `automation/prompt_templates/character_snapshot_extraction.md:150-167`：模板要求 baseline 列出的从未登场 target 也必须保留占位，且 baseline 未覆盖 target 不得写入 snapshot；但该 baseline 未被传给 worker。

更高优先级真相：`docs/requirements.md` 与 `ai_context/decisions.md` 的 D4 目标是较新的约束；`prompt_builder.py` / prompt 模板属于半迁移状态。

建议：在 `_build_char_snapshot_read_list()` 中加入 `characters/{character_id}/canon/target_baseline.json`；同步修正模板“文件角色定位 / 运行时模型”措辞，区分 extraction 输入与 runtime 加载；增加一个 prompt-builder regression，断言 char_snapshot read list 包含 target_baseline。

### High 2 — Phase 2 `foundation.json` 缺少 schema gate，文档承诺的 baseline 全量 schema 校验没有兑现

结论：文档承诺 Phase 2 后 `validate_baseline()` 校验所有 baseline 文件 schema，且 `foundation` 是必需文件；实际 validator 只检查 `foundation.json` 存在、JSON 可解析、`work_id` 非空，没有调用 `schemas/world/foundation.schema.json`。

为什么是问题：`foundation.json` 是运行时 Tier 0 的静态世界背景。schema 中包含长度、条数、结构等约束；这些约束目前被绕过，超长 / 过量 / 错形 foundation 可通过 Phase 2，后续进入世界抽取和运行时上下文。

影响范围：Phase 2 baseline 出口、后续 world stage extraction、未来 simulation runtime Tier 0。

证据：

- `docs/architecture/extraction_workflow.md:138-142`：Phase 2 出口验证校验所有 baseline 文件 schema 合规性，`foundation` 与 `fixed_relationships` 等均为必须 error。
- `automation/persona_extraction/prompt_builder.py:179-187`：baseline prompt 的 schema read list 包含 identity、character_manifest、target_baseline、fixed_relationships、world_stage_catalog、character stage_catalog，但缺少 `world/foundation.schema.json`。
- `automation/persona_extraction/validator.py:183-195`：`validate_baseline()` 对 `foundation.json` 只做存在 / JSON / `work_id` 检查，没有 `_validate_schema(...)`。
- `schemas/world/foundation.schema.json:18-80`：schema 定义了 `tone.maxLength`、`world_structure.major_regions.maxItems`、`power_system.levels.maxItems`、嵌套 description 长度等实际约束。

建议：把 `world/foundation.schema.json` 加入 baseline prompt read list；在 `validate_baseline()` 中对 foundation 调 `_validate_schema()`；加一条回归测试，用超长 `tone` 或过量 `major_regions` 证明当前应阻断。

### High 3 — `stage_id` 内部对齐基本未生效，L2 / Phase 3.5 承诺存在盲区

结论：规范要求 L2 structural / Phase 3.5 校验 `stage_id` 对齐；实际 repair structural checker 只有在数据中带 `_repair_hints.expected_stage_id` 时才检查，但仓库中没有任何 producer 写入该 hint。Phase 3.5 consistency checker 只比较 catalog 与 snapshot 文件名集合，不读取 snapshot 内部 `stage_id`。memory_timeline / memory_digest correspondence 也只比较 memory_id 集合，不校验 timeline 文件内 entry 的 `stage_id` 或 `M-S###-*` 段是否属于所在 stage。

为什么是问题：这是推断自代码路径的检查器盲区。一个 `stage_snapshots/S003.json` 内部写 `stage_id: S002`，或 `memory_timeline/S003.json` 中出现 `M-S002-*` / `stage_id: S002`，schema 仍可通过 pattern，digest 也可能完成 1:1 对应，但后续 runtime / retrieval 按 stage 过滤时会使用错误阶段语义。

影响范围：repair agent L2 structural、Phase 3.5 consistency、memory digest / runtime retrieval 的 stage-scoped 读取。

证据：

- `docs/requirements.md:1612-1618`：L2 structural 承诺包含 `stage_id` 对齐，并吸收原提交门控中的 stage_id alignment。
- `docs/architecture/extraction_workflow.md:298-305`：Phase 3.5 检查清单包含 `stage_id 对齐 — 世界/角色 catalog 与 snapshot 目录对齐`。
- `automation/repair_agent/checkers/structural.py:65-75`：只有 `data["_repair_hints"]["expected_stage_id"]` 存在时才检查 `data["stage_id"] != expected`。
- `rg "_repair_hints" automation docs schemas prompts ai_context README.md works users/_template`：只有 `automation/repair_agent/checkers/structural.py` 命中，未发现 hint producer。
- `automation/persona_extraction/orchestrator.py:1737-1745`：repair file list 传入 `_collect_stage_files(...)`，没有携带 per-file expected stage hint。
- `automation/persona_extraction/consistency_checker.py:536-589`：`_check_stage_id_alignment()` 只看 world / character catalog 中的 stage_id 集合与 snapshot 文件名集合，未读取 snapshot 内部 `stage_id`。
- `automation/persona_extraction/consistency_checker.py:370-407`：memory digest correspondence 只收集 timeline / digest 的 `memory_id` 集合并比较 missing / orphan，未检查 timeline entry `stage_id` 与文件 stage 是否一致。

建议：在 repair file collection 中按路径注入 expected stage，或让 checker 从路径推导 expected stage；Phase 3.5 增加对 world snapshot、character snapshot、memory_timeline entry、event / memory id stage segment 的内部对齐检查；用故意错写内部 stage_id 的 fixture 做回归。

### Medium 1 — `works/README.md` 仍记录已废弃的 4-piece character baseline，示例产物说明会误导后续生成

结论：`ai_context/current_status.md` 明确 4-piece character baseline 已废弃，`failure_modes` 已内联到 `stage_snapshot`；但 tracked 的 `works/README.md` 仍把 `voice_rules.json` / `behavior_rules.json` / `boundaries.json` / `failure_modes.json` 列为推荐目录结构和 schema 说明，并且没有把 `target_baseline.json` 放进角色 canon 结构。

为什么是问题：`works/README.md` 是仓库内已跟踪的样例 / 包结构说明。AI 或人工按它创建作品包时，会产出当前 schema 不再支持的文件，并漏掉 D4 依赖的 target_baseline。

影响范围：新作品包手工创建、样例产物对齐、后续 agent context loading。

证据：

- `ai_context/current_status.md:20-26`：4-piece baseline deprecated；S001 / S002 因缺新字段需迁移或重抽。
- `works/README.md:45-52`：目录树仍列出 `voice_rules.json`、`behavior_rules.json`、`boundaries.json`、`failure_modes.json`。
- `works/README.md:130-154`：继续描述这些 baseline 文件，并引用 `schemas/character/voice_rules.schema.json`、`behavior_rules.schema.json`、`boundaries.schema.json`、`failure_modes.schema.json` 等旧路径。

建议：刷新 `works/README.md` 的 canon 目录结构，删除 4-piece baseline，补 `target_baseline.json`，并把 voice / behavior / boundary / failure_modes 的归属改为 stage_snapshot 内联字段。

### Medium 2 — Source-discrepancy triage smoke test 已失效，D4 后没有继续覆盖原 triage 路径

结论：`automation.repair_agent._smoke_triage` 当前失败。场景 A 期望 semantic issue 被 triage accept 并写 SourceNote，但 fixture 创建的是 character `stage_snapshot` 路径且没有 target_baseline；D4 的 `TargetsKeysEqBaselineChecker` 会先报 missing baseline，使原本要测的 semantic / triage 路径没有执行。

为什么是问题：SourceNote / source-discrepancy triage 是 repair lifecycle 的关键语义豁免路径。smoke 红灯或被新 L2 规则遮蔽，会让后续修改无法判断 triage 是否仍可用。

影响范围：repair agent smoke suite、source inherent issue acceptance、T2/T3 之前的 triage gate。

证据：

- 运行 `python -m automation.repair_agent._smoke_triage` 失败：`[A] passed=True  notes=0  T3 regen calls=0  triage calls=0`，随后 `AssertionError: expected at least one accepted note`。
- `automation/repair_agent/_smoke_triage.py:49-86`：fixture 写入 `characters/A001/canon/stage_snapshots/S001.json`，但没有创建 `target_baseline.json`。
- `automation/repair_agent/_smoke_triage.py:133-158`：场景 A 明确断言存在 accepted note，且 T3 regen 应跳过。
- `automation/repair_agent/checkers/targets_keys_eq_baseline.py:13-22`：该 checker 适用于 character stage_snapshot；missing target_baseline 会产生 error。
- `automation/repair_agent/checkers/targets_keys_eq_baseline.py:50-65`：baseline missing / unreadable 时直接追加 `targets_baseline_missing` error 并 continue。

建议：给 smoke fixture 补最小 `target_baseline.json` 与 snapshot 三结构，或改用不会触发 D4 的 fixture 路径；然后恢复 `python -m automation.repair_agent._smoke_triage` 为绿色。

### Medium 3 — Codex backend 宣称可用，但仍通过 argv 传大 prompt，已知会撞 ARG_MAX

结论：项目文档 / todo 承认支持 Claude CLI 与 Codex CLI，但 `CodexBackend.run()` 仍把完整 prompt 当作 positional argv。代码注释已说明大 prompt 约 128 KiB 会失败；这对提取类 prompt 是现实风险。

为什么是问题：这是已知风险，不是本轮新发现的实现漏洞；但它会让 `--backend codex` 在常规长 prompt 下不可用，和“支持 Codex backend”的对外叙述不完全一致。

影响范围：`--backend codex` 的 extraction / reviewer 调用。

证据：

- `automation/persona_extraction/llm_backend.py:416-423`：`CodexBackend.run()` 注释说明 prompt 仍走 argv，large prompts 会失败；命令构造为 `["codex", "--quiet", "--full-auto", prompt]`。
- `docs/todo_list.md:27-28`：`T-CODEX-STDIN` 已记录同一问题，说明 ClaudeBackend 已改 stdin tempfile，CodexBackend 未改。

建议：在有 Codex CLI 环境的机器上验证 stdin / tempfile 调用方式后修复；在修复前把 Codex backend 标注为实验性或限制用途。

## False Positives / 已排除项

- `users/_template` 直接按 schema 校验会失败：`{user_id}`、`{stage_id}`、`{context_id}`、`{session_id}` 等占位符不符合 pattern。当前判断为模板 scaffold 的预期行为，不列为 finding；若项目要求 `_template` 同时作为可验证样例，则需要另开任务把占位符换成合法示例值或定义模板校验模式。
- `AGENTS.md` 与 `CLAUDE.md` 除标题外存在“Sync with counterpart”自引用差异的歧义。两文件主体意图一致，且这是入口文件自指文案，不在本轮列为实质风险。
- `current_status.md` 写 Phase 4 complete 而 Phase 3.5 pending，初看像顺序冲突；结合实现与文档，Phase 4 可独立于 Phase 3.5 生成个性化解读，不作为 finding。
- `works/我和女帝的九世孽缘/.../rate_limit_pause.json.lock` 只存在本地且被 `.gitignore` 覆盖，未作为 tracked artifact 漂移问题。

## Open Questions / Ambiguities

- `_template` 文件是否应该“模板占位符合法”还是“展开后合法”：如果后续要把 `users/_template` 纳入 CI schema validation，需要明确单独的模板校验策略。
- D4 baseline missing 在 repair agent 中是否应永远是 error：当前对真实 extraction 是合理硬门控，但 smoke / unit fixture 需要一种最小合法 baseline 写法，否则容易遮蔽更高层路径测试。
- Codex backend 是正式支持面还是实验支持面：如果是正式支持，应优先修复 stdin；如果只是备用，应在 automation README / CLI help 中降低承诺。

## Alignment Summary

对齐较好的部分：

- `ai_context/` 与 `docs/requirements.md` 对 Phase 3 lane 拆分、D4 target_baseline 方向、4-piece baseline 废弃方向总体一致。
- JSON schema 文件本身可解析；本轮 `schemas/**/*.schema.json` 自检未发现 schema syntax 错误。
- `.gitignore` 与大体产物策略一致，真实 work/source/progress 数据没有作为 tracked artifact 泄漏。

最不对齐的部分：

- D4 目标在 docs / prompt / code 三层之间半迁移：规范要求 target_baseline 每 stage 输入，但 char_snapshot prompt builder 没传。
- Phase 2 baseline gate 的文档承诺强于实现，`foundation.json` schema 未接入。
- L2 / Phase 3.5 的 stage alignment 承诺强于实现，当前检查更偏“文件集合齐全”，不是“文件内部 stage 语义齐全”。
- `works/README.md` 仍停留在旧 4-piece baseline 时代。

## Residual Risks

- 未读取 `logs/change_logs/` 历史决策全文；本轮按 skill 要求只在发现冲突时用当前 `ai_context` / docs / code 判定优先级。
- 未运行真实 Phase 3 extraction / repair 全流程，因为当前仓库状态显示已有 work package S003 ERROR 且大量 sources / works 数据按 read_scope 不默认加载。
- `simulation/` 目前没有 runtime code，本轮只能检查文档与目录层风险，无法验证 runtime loader 语义。
- 没有把已发现问题落地修复；本报告只归档 review snapshot。

## Suggested Landing Order

1. 修复 `char_snapshot` read list 与模板，使 extraction 输入包含 `target_baseline.json`，并补 prompt-builder regression。
2. 给 `foundation.json` 接入 `world/foundation.schema.json` prompt read list 与 `validate_baseline()` schema gate。
3. 实装真实 stage alignment：repair path 注入或推导 expected stage；Phase 3.5 检查 snapshot / memory_timeline / digest id 的内部 stage。
4. 更新 `_smoke_triage` fixture，使 D4 合法后继续测试 SourceNote triage 路径，并恢复 smoke 绿灯。
5. 刷新 `works/README.md`，删除 4-piece baseline，补 `target_baseline.json` 与内联 stage_snapshot 说明。
6. 在具备 Codex CLI 的环境里修复 `CodexBackend` stdin / tempfile 传 prompt；修复前降低文档承诺。

## Verification Notes

- `python -m compileall -q automation`：通过。
- schema syntax self-check over `schemas/**/*.schema.json`：`SCHEMA_ERRORS 0`。
- automation import smoke：`imports_ok True True True`。
- `python -m automation.repair_agent._smoke_l3_gate`：通过，输出 `OK — lifecycle reset behaves as expected.`。
- `python -m automation.repair_agent._smoke_triage`：失败，见 Finding Medium 2。
