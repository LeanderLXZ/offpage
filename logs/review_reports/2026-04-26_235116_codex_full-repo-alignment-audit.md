**Review 模型**：Codex (GPT-5)（`codex`）

# /full-review — full-repo-alignment-audit

审计时间：2026-04-26_235116 America/New_York

范围：`ai_context/`、`docs/`、`schemas/`、`automation/`、`simulation/`、`prompts/`、`works/`、`users/_template/`、`README.md`、`.gitignore`。未默认读取 `logs/change_logs/`、原文大语料、完整 evidence。

验证补充：

- 37 个 `schemas/**/*.schema.json` 均可由 `jsonschema.Draft202012Validator.check_schema` 加载。
- 关键 automation 模块 import smoke 通过：`orchestrator` / `consistency_checker` / `post_processing` / `validator` / `scene_archive` / `repair_agent.coordinator`。
- 当前分支：`main`。

## Findings

### High

#### H1. Phase 0 会把不完整或陈旧的 chunk summary 当作完成，Phase 1 可能基于缺章摘要继续

结论：Phase 0 的完成门控没有兑现“全部 chunk 成功且 schema-gated 后才进入 Phase 1”的文档契约。不完整的新 chunk 会返回 success，陈旧的 `done` chunk 只要文件存在就跳过，最终 gate 只数文件数量。

为什么这是问题：Phase 1 的 stage plan、候选角色、world_overview 都依赖 Phase 0 摘要。如果一个 chunk 缺少部分章节摘要，后续阶段边界、候选角色频率、身份合并都会在缺上下文的情况下生成，而且 pipeline 仍会记录 Phase 0 done。

影响范围：Phase 0 resume、Phase 1 analysis、后续全部 stage 切分与提取质量。

证据：

- `docs/architecture/extraction_workflow.md:47`-`51` 要求每个 chunk 落盘后 schema gate，全部 chunk 成功后才进入 Phase 1。
- `automation/persona_extraction/orchestrator.py:489`-`493` 在 `summaries` 数量少于预期时仍 `return idx, True`。
- `automation/persona_extraction/orchestrator.py:722`-`726` 对 `state == done` 且文件存在的 chunk 直接跳过，不复验 JSON/schema/summary count。
- `automation/persona_extraction/orchestrator.py:741`-`748` 对已有文件只要有 `summaries` 就标 done 并跳过。
- `automation/persona_extraction/orchestrator.py:820`-`824` 最终 gate 只统计 `chunk_NNN.json` 是否存在。

建议：把 chunk 完成判据统一为“存在 + JSON 可解析 + schema 通过 + 覆盖该 chunk 的所有章节”；resume 时对 `done` chunk 做同样 reconcile。

#### H2. Phase 1 三件套缺失时仍可标记 `phase_1` done

结论：Phase 1 的 schema gate 会跳过缺失文件，且当 `stage_plan` 缺失时跳出 retry loop，随后仍 `mark_done("phase_1")`。

为什么这是问题：文档把 `world_overview.json` / `stage_plan.json` / `candidate_characters.json` 作为 Phase 1 的硬产物和 schema gate 对象。缺任一文件都应阻断，而不是把失败交给下游。

影响范围：Phase 1.5 target confirmation、Phase 2 baseline、Phase 3 stage expansion、Phase 4 chapter-to-stage 映射。

证据：

- `docs/architecture/extraction_workflow.md:60`-`66` 列出 Phase 1 三件套输出。
- `docs/architecture/extraction_workflow.md:71`-`83` 要求三件套 jsonschema 校验，失败重试，耗尽则终止。
- `automation/persona_extraction/orchestrator.py:898`-`905` 对 `data is None` 的文件直接 `continue`。
- `automation/persona_extraction/orchestrator.py:964`-`967` 在 `stage_plan` 缺失时也 `break`。
- `automation/persona_extraction/orchestrator.py:969`-`972` 无论三件套是否齐全，都会标记 `phase_1` done。

建议：把缺失文件纳入 `schema_failures` 或单独 `missing_failures`，共享 retry budget；重试耗尽后 `sys.exit(1)`。

#### H3. L3 semantic checker 的 LLM 调用失败会 false-pass

结论：repair agent 的 L3 semantic checker 文档上是四层检查器的一环，但 orchestrator 传入的 `_llm_call` 不检查 `LLMResult.success`，semantic checker 对异常、空响应、不可解析响应都返回 `[]`。如果 L0-L2 没有 blocking issue，Phase A 会判定通过。

为什么这是问题：当语义审校后端失败、限额失败或返回空输出时，系统会把“未完成审校”当作“没有语义问题”，从而让错误的 stage 文件进入 PASSED / commit。

影响范围：Phase 3 repair gate，尤其是 source-grounded 事实准确性、关系连续性、角色心理逻辑等 L3 才能发现的问题。

证据：

- `automation/README.md:284`-`291` 把 L3 semantic 定义为事实准确性、逻辑一致性、跨阶段连续性的检查层。
- `automation/persona_extraction/orchestrator.py:1768`-`1775` `_llm_call` 直接返回 `result.text`，不处理 `success=False` / `error`。
- `automation/repair_agent/checkers/semantic.py:109`-`115` 捕获异常后返回空 issue。
- `automation/repair_agent/checkers/semantic.py:125`-`130` 空或不可解析语义响应返回空 issue。
- `automation/repair_agent/coordinator.py:167`-`177` 在无 blocking issue 时直接 PASS。

建议：`_llm_call` 在 `success=False` 时抛出专用异常；semantic checker 应把 LLM 调用失败 / parse fail 转成 blocking `semantic_unavailable` issue，除非配置显式关闭 L3。

#### H4. `RateLimitHardStop` 会被 worker 层的 broad `except Exception` 吞掉

结论：requirements 要求 `RateLimitHardStop` 从 worker thread 透传到主线程并由 CLI 退出 2；实际多个 worker `Future.result()` 包裹层捕获 `Exception` 后把它降级为普通失败。

为什么这是问题：周限额 / probe 耗尽时，后台流程不一定按 hard-stop 合同退出，可能继续把章节、chunk 或 repair file 标成失败，污染进度状态并反复重试。

影响范围：Phase 0 并发摘要、Phase 3 repair 并发、Phase 4 scene archive，并影响 `rate_limit_exit.log` 语义。

证据：

- `automation/persona_extraction/rate_limit.py:51`-`65` 定义 `RateLimitHardStop` 并说明 worker future 应在主线程 re-raise。
- `docs/requirements.md:2519`-`2523` 要求 hard stop 统一 `sys.exit(2)`。
- `docs/requirements.md:2543` 明确要求 `Future.result()` 在主线程 re-raise。
- `automation/persona_extraction/orchestrator.py:781`-`787` Phase 0 worker 异常被转成 `(success=False, msg=str(exc))`。
- `automation/persona_extraction/orchestrator.py:1836`-`1846` repair worker 异常被 synthetic failed result 吞掉。
- `automation/persona_extraction/scene_archive.py:908`-`918` Phase 4 worker 异常被转成 chapter ERROR。

建议：在这些 broad catch 前先 `except RateLimitHardStop: raise`，并让 CLI 顶层统一处理。

#### H5. `ai_context` 的当前 extraction handoff 指向已不存在的当前分支状态

结论：`ai_context` 仍声明首个 work package Phase 0/1/1.5/2/4 complete、S001/S002 committed、S003 ERROR 可 `--resume`；但当前 `extraction/<work_id>` HEAD 只含 `sources/works/.gitkeep` 和 `works/README.md`，本地 `works/<work_id>/analysis/progress/` 也只有 `rate_limit_pause.json.lock`，没有 `pipeline.json` / `phase3_stages.json`。

为什么这是问题：新 agent 按 handoff 运行 resume 会面对缺失的 work state；更糟的是，它会相信 S001/S002 的产物仍是当前分支可恢复状态，实际当前 extraction branch 后续提交已删除这些产物。

影响范围：会话入口、恢复指令、下一轮 extraction 操作决策。

证据：

- `ai_context/current_status.md:15`-`18` 声明 work package under extraction、S001/S002 committed、S003 ERROR。
- `ai_context/current_status.md:30`-`34` 重复列出 S001/S002 sha。
- `ai_context/next_steps.md:15`-`22` 把 resume 作为最高优先级，并声明 committed stages + lane products preserved。
- `ai_context/handoff.md:29`-`35` 给出 `python -m automation.persona_extraction "<work_id>" --resume`。
- 命令证据：`git ls-tree -r --name-only extraction/<work_id> | rg '^(works|sources/works)/'` 只输出 `sources/works/.gitkeep` 与 `works/README.md`。
- 命令证据：`find works/<work_id>/analysis/progress -maxdepth 2 -type f` 只输出 `rate_limit_pause.json.lock`。

建议：要么恢复/重建 extraction branch 的 progress 与 work artifacts，要么立即更新 `ai_context/current_status.md` / `next_steps.md` / `handoff.md`，把当前分支状态和可执行恢复方式写清楚。

### Medium

#### M1. `memory_importance` 是 digest 必需字段的来源，但在 memory_timeline schema 中可省略

结论：prompt 要求每条 memory_timeline 写 `memory_importance`，memory_digest schema 又要求 `importance`；但 `memory_timeline_entry.schema.json` 的 `required` 不包含 `memory_importance`，post-processing 缺失时默认写成 `minor`。

为什么这是问题：缺失 importance 不会被 L1 gate 阻断，所有未标重要度的 defining/critical 记忆会被静默降级为 `minor`，影响远期记忆排序和检索策略。

影响范围：Phase 3 char_support、`memory_digest.jsonl`、runtime historical recall。

证据：

- `automation/prompt_templates/character_support_extraction.md:66` 要求 `memory_importance` 5 级枚举。
- `schemas/character/memory_timeline_entry.schema.json:8`-`16` required 不含 `memory_importance`。
- `schemas/character/memory_timeline_entry.schema.json:136`-`140` 仅把 `memory_importance` 定义为 optional property。
- `schemas/character/memory_digest_entry.schema.json:8`-`14` 要求 digest `importance`。
- `automation/persona_extraction/post_processing.py:184`-`189` 缺失时默认 `entry.get("memory_importance", "minor")`。

建议：把 `memory_importance` 加入 memory_timeline required，或改为程序化 importance 推断并在文档/prompt 中承认推断来源。

#### M2. stage_snapshot 的自包含维度在 docs/prompt 中必需，但 schema 未硬门控

结论：requirements 与 extraction prompt 要求每个 stage_snapshot 包含 `emotional_baseline`、`current_status`、`misunderstandings`、`concealments`、`stage_delta` 等完整维度；schema 顶层 required 不包含其中多项，并且 `voice_state` / `behavior_state` 等对象内部没有 required 子字段。

为什么这是问题：L1 schema gate 可通过结构上“空壳但合法”的快照。Phase 3.5 虽会补查部分字段，但那发生在 stage commit 之后，不能替代 per-stage repair gate。

影响范围：角色状态完整性、runtime self-contained snapshot 可靠性、跨阶段追踪。

证据：

- `docs/requirements.md:940`-`946` 要求每个 stage_snapshot 包含全部维度。
- `automation/prompt_templates/character_snapshot_extraction.md:56`-`71` 重复要求完整填充各维度。
- `schemas/character/stage_snapshot.schema.json:8`-`25` required 未包含 `emotional_baseline`、`current_status`、`misunderstandings`、`concealments`、`stage_delta`。
- `schemas/character/stage_snapshot.schema.json:220`-`224` `voice_state` 只有 properties，无内部 required。
- `schemas/character/stage_snapshot.schema.json:355`-`359` `behavior_state` 只有 properties，无内部 required。
- `schemas/character/stage_snapshot.schema.json:714`-`718` `stage_delta` 是 optional property。

建议：把真正必须存在的维度移入 schema required；若允许空/省略，则同步放松 docs/prompt，并让 Phase 3.5 的“完整性”定义与 schema 保持一致。

#### M3. scoped preflight 与 `commit_stage()` 的提交范围不一致，会把其他 work 的 dirty 变更带入当前 extraction commit

结论：preflight 只检查 `works/{work_id}/` 范围内的 dirty；但 `commit_stage()` 默认执行 `git add -A works/`。如果另一个 work 目录有 tracked dirty 文件，preflight 会放行，commit 会一起 stage 并提交。

为什么这是问题：当前 work 的 stage commit 可能混入其他 work 的产物，破坏 per-work extraction branch 隔离；如果外部已经有 staged unrelated changes，也可能被同一次 commit 带走。

影响范围：Phase 2 baseline recovery commits、Phase 3 stage commits、consistency report 以外的默认 `commit_stage` 调用。

证据：

- `automation/persona_extraction/git_utils.py:67`-`70` 说明 `scope_paths` 用于只 flag 某个 work scope。
- `automation/persona_extraction/orchestrator.py:1556`-`1559` 传入 `scope_paths=[f"works/{pipeline.work_id}/"]`。
- `automation/persona_extraction/git_utils.py:193`-`198` `files` 为空时执行 `git add -A works/`。
- `automation/persona_extraction/orchestrator.py:1936` Phase 3 stage commit 未传 files。

建议：让 `commit_stage` 接收 `work_id` 或 explicit path list，默认只 add `works/{work_id}/`；提交前检查 index 中是否有 scope 外 staged paths。

#### M4. squash merge 成功后没有执行 disposable branch cleanup

结论：架构/requirements 要求 squash 后删除源 `extraction/{work_id}` branch 并 `git gc --prune=now`；实现保留分支并仅打印手动删除建议。

为什么这是问题：`extraction/{work_id}` 被定义为 disposable scratchpad，允许失败 regen commit。保留分支会继续保存所有历史 blob，违背磁盘回收和 library 作为唯一长期记录的设计。

影响范围：work 完成后的分支生命周期、磁盘占用、后续 agent 对“当前 extraction branch”的判断。

证据：

- `ai_context/conventions.md:101`-`102` 要求 completion squash 后删除 source branch 并 gc。
- `ai_context/architecture.md:142`-`143` 同步描述该 contract。
- `automation/persona_extraction/git_utils.py:302`-`308` 明确 `squash_merge_to` 不删除 source branch。
- `automation/persona_extraction/orchestrator.py:2110`-`2114` squash 成功后打印 branch preserved/manual delete。

建议：在 squash 成功后按配置或交互确认执行 `git branch -D <source>` + `git gc --prune=now`；若仍需人工确认，docs 应把“必须自动删除”降级为“提示人工删除”。

#### M5. rate-limit 分类漏掉文档承诺的 `429`，且 Codex backend 不进入 rate-limit pause

结论：requirements 把 `429` 列为通用 retry/rate-limit 关键词；Claude backend 只匹配 `rate limit` / `rate_limit` / `too many requests`，Codex backend 对非零退出直接返回 `exit N`，不会触发 `run_with_retry` 的 rate-limit pause 分支。

为什么这是问题：429 类限额错误会走普通失败/重试，而不是写共享 pause file 并等待 reset；并发 extraction 更容易消耗 retry budget 或产生 ERROR。

影响范围：Claude CLI / Codex CLI backend，Phase 0/3/4 所有 LLM 调用。

证据：

- `docs/requirements.md:2468`-`2474` 列出 `429` 为通用 retry 关键词。
- `automation/persona_extraction/llm_backend.py:361`-`363` Claude rate-limit signals 不含 `429`。
- `automation/persona_extraction/llm_backend.py:493`-`499` Codex backend 对 returncode 非零直接 `exit N`。
- `automation/persona_extraction/llm_backend.py:606`-`614` 只有 error 包含 `rate_limit` 才进入 pause controller。

建议：统一 backend 错误分类函数，包含 `429`，并让 Codex stderr/stdout 同样映射 `rate_limit:`。

#### M6. manual repair prompt 仍要求 `evidence_ref`，与 no-evidence-field schema contract 冲突

结论：当前数据模型明确禁止 snapshots / memory_timeline / dialogue_examples / action_examples 内携带 `evidence_ref`，但手动补抽与修复 prompt 仍要求“标注 evidence_ref”。

为什么这是问题：人工修复场景最可能在 schema 失败后执行；这个 prompt 会诱导修复者添加 schema-rejected 字段，造成二次失败。

影响范围：manual repair prompts、补抽/修复流程、schema adherence。

证据：

- `prompts/review/手动补抽与修复.md:27`-`29` 要求修复内容标注 `evidence_ref`。
- `ai_context/conventions.md:83` 明确 no `evidence_refs` / `source_type` / `scene_refs`，并禁止 per-item `evidence_ref`。
- `docs/architecture/schema_reference.md:324`-`326` 说明快照层不携带这些回溯字段。

建议：改成“在修复报告/外部 notes 中记录证据，不写入 schema 实例字段”，并指向当前 SourceNote / extraction_notes 机制。

#### M7. `ai_context/decisions.md` 对 `scene_archive` 是否携带 `stage_id` 的说法与 schema/docs 冲突

结论：`ai_context/decisions.md` 说 digest / archive entries 不携带单独 `stage_id`；但 `scene_archive_entry.schema.json` 要求 `stage_id`，requirements 也说 scene_archive 的 `stage_id` 由 `stage_plan.json` 得出。

为什么这是问题：`ai_context` 是新 agent 默认入口。该句会误导 runtime/retrieval 实现者以为 scene_archive 只能从 `scene_id` 解析 stage，而不是读取 required `stage_id` 字段。

影响范围：runtime scene retrieval、Phase 4 archive assembly、future loader implementation。

证据：

- `ai_context/decisions.md:97` 声明 digest / archive entries carry no separate `stage_id` field。
- `schemas/runtime/scene_archive_entry.schema.json:7`-`13` required 包含 `stage_id`。
- `schemas/runtime/scene_archive_entry.schema.json:21`-`24` 定义 `stage_id`。
- `docs/requirements.md:2912`-`2915` 明确 scene_archive `stage_id` 来自 `stage_plan.json`。

建议：把 decision 改成“digest entries 不携带 stage_id；scene_archive 同时携带 `stage_id` 与 stage-coded `scene_id`”。

#### M8. stage_catalog schema 路径/`snapshot_path` 文档存在小范围漂移

结论：`ai_context/conventions.md` 泛写 `schemas/{world,character}/stage_catalog.schema.json`，但 world schema 实际为 `schemas/world/world_stage_catalog.schema.json`。`docs/requirements.md` 的 stage_catalog 映射表把 `snapshot_path` 写成 `canon/stage_snapshots/{stage_id}.json`，这只适用于 character catalog，不适用于 world catalog。

为什么这是问题：schema / docs 对齐审计和后续生成器维护会查错路径；world catalog 的 `snapshot_path` 可能被误写成 character 路径。

影响范围：docs-only drift，影响未来维护和 prompt/schema 修改。

证据：

- `ai_context/conventions.md:85` 写 `schemas/{world,character}/stage_catalog.schema.json`。
- `docs/architecture/data_model.md:213` 写 world catalog schema 为 `schemas/world/world_stage_catalog.schema.json`。
- `docs/requirements.md:1435`-`1439` 在 stage_catalog 映射表中统一写 `canon/stage_snapshots/{stage_id}.json`。
- `docs/requirements.md:1442`-`1443` 又承认 world/character catalog schema 分别不同。

建议：拆成 world / character 两行；world `snapshot_path` 应为 `stage_snapshots/{stage_id}.json`，character 为 `canon/stage_snapshots/{stage_id}.json`。

### Low

#### L1. bounds-only policy 仍被 docs/prompts 多处复述具体数值

结论：`conventions.md` 和 `schema_reference.md` 要求具体 `maxLength` / `maxItems` 等数值只存在于 schema，但 prompt templates、`schema_reference.md` 局部、`extraction_workflow.md` 仍复述具体 bound。抽查值多数仍匹配 schema，因此当前是 drift risk，不是已确认 runtime bug。

证据：

- `ai_context/conventions.md:81` 要求 exact values 只在 schema。
- `docs/architecture/schema_reference.md:4`-`7` 声明本文档不再复述具体数字。
- `docs/architecture/schema_reference.md:145` 仍写 world anchor `≤15`。
- `automation/prompt_templates/character_support_extraction.md:57`-`71` 复述 memory_timeline 多个具体 bound。
- `automation/prompt_templates/character_snapshot_extraction.md:59`-`71` 复述 stage_snapshot 多个具体 bound。
- `docs/architecture/extraction_workflow.md:47`-`49`、`317`-`320` 复述 Phase 0 / Phase 4 schema bound。

建议：保留“cap not target”原则，把具体数值改为“见 schema”；如果 prompt 为了 LLM 可执行性必须复述数值，就调整 bounds-only policy，明确 prompt 是允许例外并由 schema injection 自动生成。

#### L2. mirror constraints are not literally satisfied for AGENTS/CLAUDE and full-review command/skill

结论：`AGENTS.md` / `CLAUDE.md` 声称除 title line 外完全一致，但 Sync section 自引用不同；`.agents/skills/full-review/SKILL.md` 与 `.claude/commands/full-review.md` 也在 mirror constraint paragraph 上不逐字一致。

证据：

- `AGENTS.md` 与 `CLAUDE.md` diff 仅 title 之外还包含 “Sync with CLAUDE.md/AGENTS.md” section 的互指文本。
- `.agents/skills/full-review/SKILL.md` 正文末尾引用 `.claude/commands/full-review.md`；`.claude/commands/full-review.md` 正文末尾引用 `.agents/skills/full-review/SKILL.md`，因此不可能逐字一致。

建议：把 mirror 规则改为“除 title line 与 mirror target paragraph 外一致”，或用中性措辞让两边正文可以字节级一致。

#### L3. `ai_context` 仍说 foundation schema implicit

结论：`current_status.md` / `next_steps.md` 仍称 foundation schema implicit / partially informal；仓库已有 `schemas/world/foundation.schema.json` 且 schema reference 已登记。timeline/events/locations/maps 仍未完整 schema 化，所以这是部分 stale。

证据：

- `ai_context/current_status.md:48` 写 foundation skeleton 仍在 prompt。
- `ai_context/next_steps.md:26`-`28` 写 foundation schema still implicit。
- `schemas/world/foundation.schema.json:1`-`8` 已存在 schema。
- `docs/architecture/schema_reference.md:172` 起已登记 foundation schema。

建议：更新为“foundation schema exists but remains permissive; timeline/events/locations/maps still need directly writable schemas”。

## Open Questions / Ambiguities

1. Phase 3.5 有 error 时是否允许 squash 到 `library`？`library` 被定义为 completed works archive，但 `docs/architecture/extraction_workflow.md:293`-`296` 又强调 failed/pass report 都要在 `_offer_squash_merge` 前 commit，避免被 squash 漏掉。建议明确：consistency failed 是“可归档失败快照”还是“未完成，禁止 archive”。
2. bounds-only policy 是否允许 prompt 模板复述 bound？如果不允许，应自动从 schema 注入；如果允许，应修订 `conventions.md`，避免每轮 review 都报同类漂移。
3. `users/_template` 是否应保持 placeholder-invalid，还是提供 schema-valid sample IDs？当前 README 说明替换占位符后使用，我未将其列为 finding。
4. `memory_importance` 缺失时应该 hard fail，还是由 post-processing 统一推断？当前 prompt/schema/code 三者语义不一致。

## Alignment Summary

对齐较好：

- `main` 分支只保留 framework/scaffold，`works/` tracked 内容只有 README，符合 main artifact-free 规则。
- `schemas/**/*.schema.json` 均可作为 Draft 2020-12 schema 加载。
- `simulation/` 仍是 contracts / flows / prompt_templates / retrieval 设计文档，没有伪装成已实现 runtime。
- `.gitignore` 对 sources、works progress、retrieval、users real packages 的忽略策略整体与 branch model 一致。

最不对齐：

- Extraction gate code vs docs：Phase 0 / Phase 1 / L3 semantic / rate-limit hard-stop 都存在“文档说阻断，代码可能放行或降级”的缺口。
- `ai_context` handoff vs actual extraction branch：当前最高优先 resume 指令不可直接执行。
- Prompt/docs vs schema single-source：bounds-only、stage_snapshot required dimensions、memory importance、manual evidence field 仍有漂移。

## Residual Risks

- 本轮未读取 `logs/change_logs/` 历史决策；若上述行为是近期刻意变更，需由 change log 佐证后再调整 severity。
- 未读取 raw novel / large evidence；未评估内容质量本身，只评估结构、门控和状态一致性。
- 历史 commit `991c09f` / `7639c8b` 中的 artifact schema drift 未作为独立主 finding 展开，因为 handoff 已部分承认 older artifacts 会被新 schema gate 打断；当前更关键的问题是 extraction branch HEAD 与 handoff 不一致。
- 未运行完整 extraction pipeline；实现 findings 基于静态代码路径和轻量 import/schema smoke。

## False Positives Checked

- `main` 上 `works/` 只有 README：符合 `main` framework-only 规则，不是缺失 work package。
- `users/_template` 中 `{user_id}` / `{stage_id}` 等占位符直接 schema validate 会失败，但 `users/README.md:223`-`229` 明确这是替换后使用的模板。
- `ai_context/handoff.md` 提及 `evidence_refs` / `character_status_changes` 等 removed fields，是 extraction-branch drift remediation note，不是当前 schema 指令。
- `character_snapshot_extraction.md` 中的 `relationship_behavior_map` 出现在“错误字段名”表内，不是要求输出旧字段。
- `source_types` 属于 work manifest 输入格式字段，与已移除的 singular `source_type` anchoring 字段不是同一问题。
- Phase 4 scene split resume 仅按 split 文件存在跳过，看起来是设计取舍；未列为 finding。

## 建议落地顺序

1. 先修正 `ai_context/current_status.md` / `next_steps.md` / `handoff.md` 或恢复 extraction branch state，避免下一位 agent 按错误 resume 路径操作。
2. 修 Phase 0 / Phase 1 gate：缺失、partial、stale 文件都应进入 retry/abort，而不是标 done。
3. 修 L3 semantic 和 `RateLimitHardStop`：把“检查未完成”与“检查通过”分开，hard-stop 透传到 CLI。
4. 对齐 `memory_importance` 与 stage_snapshot required dimensions：决定 schema hard gate 还是 docs/prompt 降级。
5. 收紧 git commit/squash lifecycle：commit scope 只限当前 work，squash 后按 contract 删除 disposable branch 或更新 contract。
6. 清理 prompt/docs drift：manual repair `evidence_ref`、scene_archive `stage_id` decision、stage_catalog path、bounds-only 例外。
7. 最后处理 mirror wording 和 foundation-schema stale status 这类低风险文档维护项。
