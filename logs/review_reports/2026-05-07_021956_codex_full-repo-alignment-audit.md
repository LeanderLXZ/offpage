**Review 模型**：Codex (GPT-5)（`codex`）

# /full-review — full-repo-alignment-audit

审计时间：2026-05-07_021956 America/New_York

范围：按 `ai_context/skills_config.md` 读取 `ai_context/`，再审计 `docs/requirements.md`、`docs/architecture/`、`schemas/`、`automation/`、`simulation/`、`prompts/`、`works/`、`users/_template/`、`README.md`、`.gitignore`。本轮只归档 review 报告，不修改业务代码 / schema / prompt / docs。

验证补充：

- 35 个 `schemas/**/*.schema.json` 均可由 `jsonschema.validators.validator_for(...).check_schema(...)` 加载，`schema_check_failures = 0`。
- `.agents/skills/full-review/SKILL.md` 去掉 YAML frontmatter 后，与 `.claude/commands/full-review.md` 正文逐字一致。
- 当前分支：`main`；review 前工作区无脏文件，仅 `main...origin/main [ahead 36]`。

## Findings

### High

#### H1. Phase 3.5 的 `memory_digest` 对账实际空跑，缺失和摘要漂移都可能漏检

结论：文档要求 Phase 3.5 程序化检查 `memory_digest.jsonl` 与 `memory_timeline` 一一对应，并验证 `memory_digest.summary == memory_timeline.digest_summary`。实际代码用同一个 `_load_json()` 去读顶层为 JSON 数组的 `memory_timeline/{stage_id}.json`，但 `_load_json()` 明确把 list / scalar 返回为 `None`。结果两个 memory 检查分支里的 `isinstance(timeline, list)` 永远拿不到真值，无法收集 `timeline_ids` / `timeline_by_id`。

为什么是问题：这是检查器自身盲区。缺失的 digest 条目不会被报 error；digest 中多出来的旧条目只会在空 timeline 集合下变成 warning；`summary` 与 `digest_summary` 的 1:1 文本相等检查完全不会执行。后续 runtime 依赖 memory_digest 作为启动压缩记忆索引，这会让缺失或陈旧的记忆索引进入可提交产物。

影响范围：Phase 3.5 consistency gate、post-processing 后的 memory digest、runtime 启动记忆加载。

证据：

- `docs/architecture/extraction_workflow.md:336`-`337`：要求 memory_digest 对应与摘要一致两项程序化检查。
- `docs/requirements.md:2267`-`2268`：要求 memory_digest 条目与 memory_timeline memory_id 一一对应，且 summary 文本完全等于 digest_summary。
- `docs/requirements.md:3341`：memory_timeline 使用 JSON 数组格式。
- `automation/persona_extraction/consistency_checker.py:163`-`188`：`_load_json()` 只接受 top-level object；非 dict 直接 warning 后返回 `None`。
- `automation/persona_extraction/consistency_checker.py:390`-`397`：memory_id correspondence 试图在 `isinstance(timeline, list)` 后收集 timeline ids，但这里的 timeline 来自 `_load_json()`。
- `automation/persona_extraction/consistency_checker.py:438`-`445`：summary equality 同样依赖 `_load_json()` 返回 list，因此不会建立 `timeline_by_id`。

建议：为 list-shaped JSON 增加专用只读 loader，或让 `_load_json()` 返回 `object` 后由调用方判型；给 Phase 3.5 加一条 fixture：memory_timeline 有 1 条而 memory_digest 为空时必须 error，summary 不一致时也必须 error。

#### H2. ingestion / `structure_mode` gate 没有接入 extraction CLI，且运行时仍默认 `monolithic`

结论：架构文档把 `sources/works/{work_id}/manifest.json`、`book_metadata.json`、`chapter_index.json` 列为入库前 schema 硬门控，`structure_mode` 必填且决定 Phase 0/1 双模式调度；实际 extraction CLI 只做 `works/{work_id}/` 脏工作区 preflight，没有调用 `automation.ingestion.validator.validate_source_package()`。调度读取层还会优先读 `works/{work_id}/manifest.json` 的旧副本，缺失时从 source manifest 读，再缺失时返回 `"monolithic"`。

为什么是问题：`structure_mode` 是 light_novel 1 chapter = 1 stage 路径的根开关。缺失、非法、或与 `chapter_index` profile 不一致时，文档说应在 Phase 0 前阻断；代码路径却可能 fail-open 到 monolithic，导致 light_novel 源被 token-budget chunking / LLM stage boundary 流程处理，后续 stage_plan、chapter-to-stage 映射和 Phase 4 场景归档都会建立在错误阶段模型上。

影响范围：新作品入库、Phase 0 chunking、Phase 1 stage planning、light_novel 路径、resume 时读取旧 works manifest 的场景。

证据：

- `docs/architecture/extraction_workflow.md:29`-`38`：三份 metadata 均为 schema 硬门控；`structure_mode` 必填；需运行 `python -m automation.ingestion.validator <work_id>`，失败必须回修才进 Phase 0。
- `docs/architecture/extraction_workflow.md:44`-`47`：Phase 0/1 双模式调度由 source manifest `structure_mode` 决定。
- `automation/ingestion/validator.py:1`-`7`：validator 自述为 ingestion gate，运行在 Phase 0 之前。
- `automation/ingestion/validator.py:94`-`143`：`validate_source_package()` 实现 required files + schema validation。
- `automation/ingestion/validator.py:175`-`220`：实现 `structure_mode` 与 `chapter_index` profile 的跨文件断言。
- `automation/persona_extraction/cli.py:223`-`237`：extraction CLI preflight 只检查 git dirty；未调用 ingestion validator。
- `automation/persona_extraction/manifests.py:101`-`117`：`read_structure_mode()` 优先读 works manifest，source manifest 次之，最后默认 `"monolithic"`。
- `automation/persona_extraction/orchestrator.py:870`-`875`、`automation/persona_extraction/orchestrator.py:1183`-`1198`：Phase 0 / Phase 1 直接用 `read_structure_mode()` 的字符串判断 `is_light_novel`。
- `automation/README.md:355`-`358`：README 仍写 `structure_mode` default `monolithic`，与架构文档的 required / no-default 契约冲突。

建议：在 CLI 获取 lock 后、Phase 0 前调用 `validate_source_package()`，任何 error 直接退出；`read_structure_mode()` 不应静默默认，且应以 source manifest 为权威并校验 enum；同步修正 `automation/README.md` 的 default 描述。

### Medium

#### M1. scene split prompt 允许 30 字 summary，schema 却硬要求最少 50 字

结论：`scene_split` prompt 同一段一边说长度上下限以 schema 为准，一边明确说“能 30 字写清的 summary 不要为凑 50 字注水”；schema 对 `summary` 的 `minLength` 是 50。这会让模型按 prompt 生成小于 50 字的合法感文本，然后被 schema gate 拒绝。

为什么是问题：这不是质量偏好差异，而是 prompt 与 schema 的直接冲突。Phase 4 scene archive 是大批量章节任务，短 summary 会制造可避免的 retry / repair churn，并把错误原因归到生成质量而非规范漂移。

影响范围：Phase 4 scene_archive、scene split prompt、schema gate retry 成本。

证据：

- `automation/prompt_templates/scene_split.md:29`：写明 “能 30 字写清的 summary 不要为凑 50 字注水”。
- `automation/prompt_templates/scene_split.md:34`：同文件又写 `summary` 长度 50-100 字。
- `schemas/analysis/scene_split.schema.json:46`-`50`：`summary.minLength = 50`、`maxLength = 100`。

建议：二选一收敛：若 50 字是硬契约，删掉 30 字示例并强调最短 50；若确实允许短摘要，则下调 schema `minLength`，并同步 docs / validator 期望。

#### M2. Phase 4 缺章 / 空章不会进入 FAILED 状态，retry 与进度语义失真

结论：`scene_archive._process_chapter()` 遇到 chapter file missing 或 empty 时直接返回 `(chapter_id, False, "...")`，没有调用失败标记逻辑。并行 runner 只有在 `entry.state == FAILED` 且 retry budget 未耗尽时才重试；否则仅打印 `[FAIL]` 并计数。最终 incomplete 分支保存 progress，但这些 chapter 仍保持非终态 `PENDING`。

为什么是问题：缺章 / 空章是确定性输入前置条件失败，不应表现成“尚未处理”。在 ingestion validator 没有接入 CLI 的现状下，Phase 4 可能遇到这种文件层失败；它会在每次运行中重新尝试，没有 prior_error、没有 retry_count 耗尽、progress 也无法准确告诉操作者这是永久阻塞输入。

影响范围：Phase 4 scene_archive resume、progress reporting、长期后台任务监控。

证据：

- `automation/persona_extraction/scene_archive.py:387`-`394`：chapter missing / empty 直接 return false，没有标记 entry state。
- `automation/persona_extraction/scene_archive.py:971`-`982`：retry 仅对 `entry.state == ChapterState.FAILED` 生效。
- `automation/persona_extraction/scene_archive.py:984`-`986`：非 FAILED 分支只计入 failed 并打印。
- `automation/persona_extraction/scene_archive.py:831`-`840`：最终 incomplete 保存 progress，但判断只基于非 PASSED 状态，未修正错误状态。

建议：把 missing / empty 统一落入 `_mark_failed()` 或专用 `ERROR` / `BLOCKED_INPUT` 终态；写入 error_message 与 last_updated，并让 resume 能清楚显示不可自动修复的输入缺口。

#### M3. post-processing 在当前 stage 源数组为空时保留旧 digest slice

结论：`generate_memory_digest()` 从当前 stage 的 memory_timeline 构造 `new_entries`；如果没有任何 digest entry，函数追加 warning 后立即返回，不读取 / upsert 现有 `memory_digest.jsonl`。`generate_world_event_digest()` 对空 `stage_events` 也同样 early-return。调用方把这些 issues 作为 warnings 收集，而不是 error。

为什么是问题：schema / prompt 允许某些阶段没有 meaningful memory 或 world-level public event，但 post-processing 在“源数组为空”时没有删除该 stage 已存在的派生条目。如果 repair 删除了当前 stage 全部 memory / world events，或者一次重跑从非空变为空，旧 digest 仍可能留在 JSONL 中。world digest 的计数漂移后续更容易被 Phase 3.5 抓到；memory digest 目前又受 H1 影响， stale 条目可能只剩 warning 甚至误导 runtime。

影响范围：post-processing resume / repair 后重跑、memory_digest.jsonl、world_event_digest.jsonl、runtime 启动摘要索引。

证据：

- `automation/persona_extraction/post_processing.py:101`-`110`：memory digest 没有 `new_entries` 时 warning 后 return，跳过 upsert / stale removal。
- `automation/persona_extraction/post_processing.py:274`-`278`：world event digest 对空 `stage_events` warning 后 return。
- `automation/persona_extraction/post_processing.py:547`-`577`：调用方把 world / character digest issues 都收进 `warnings`。
- `automation/prompt_templates/character_support_extraction.md:31`-`34`：memory_timeline 条目数由实际事件决定，没有 meaningful event 时可少写。
- `schemas/world/world_stage_snapshot.schema.json:75`-`78`：`stage_events` 只有 `maxItems: 15`，未定义 `minItems`。

建议：post-processing 应按 stage 做 replace-slice 语义：即使当前 stage 派生数组为空，也要删除 digest 中该 stage 的旧条目并保存；是否把 empty 作为 warning 保留可另行决定，但不应保留 stale derived data。

### Low

#### L1. `users/_template` 是“可替换模板”还是“schema-valid 样例”没有写清楚

结论：`ai_context/skills_config.md` 把 `users/_template/` 列入 Example artifact directories，本轮按“样例产物”视角抽查时，发现它使用 `{user_id}`、`{context_id}`、`{session_id}`、`{stage_id}` 这类 literal placeholders，按对应 schema pattern 不会通过。但这些文件也可能本来就是 substitution template，而不是可直接 schema validate 的 fixture。

为什么是问题：这会影响后续 agent / CI 是否应把 `users/_template` 纳入 artifact validation。若它是 fixture，当前不合格；若它是模板，应在 README / validator allowlist 中明确排除 literal placeholder 文件，避免 review 反复把它当漂移。

证据：

- `users/_template/profile.json:3`：`"user_id": "{user_id}"`。
- `users/_template/role_binding.json:12`：`"stage_id": "{stage_id}"`。
- `schemas/user/user_profile.schema.json:17`：`user_id` pattern 要求 lowercase id。
- `schemas/user/role_binding.schema.json:76`：`stage_id` pattern 要求 `^S[0-9]{3}$`。

建议：给 `users/_template/README` 或 `users/README.md` 增加一句职责声明；若希望它参与 schema validation，就改成 schema-valid sentinel ids；若它只是模板，就把验证脚本显式跳过 literal placeholder。

## False Positives / Checked And Not Filed

- Python cache / mypy cache：仓库工作区存在 `__pycache__` / `.mypy_cache` 之类本地缓存，但 `git ls-files` 未显示它们被跟踪，`.gitignore` 覆盖 `__pycache__/` 和 `*.pyc`，本轮不作为 artifact 污染 finding。
- Schema registry：`schemas/**/*.schema.json` 均能被 jsonschema 加载；`docs/architecture/schema_reference.md` 覆盖当前 concrete schemas。未把 `character/targets_cap` 这类域内 `$ref` 片段当作缺失 registry 项。
- `/full-review` mirror：`.agents/skills/full-review/SKILL.md` 与 `.claude/commands/full-review.md` 只有 YAML frontmatter 差异；从一级标题起正文一致。
- `works/` / `sources/` 本地生成物：工作区内存在真实 extraction 产物和 source 文件，但 `.gitignore` 对实际 payload 路径生效；本轮没有把未跟踪本地数据当作已提交产物漂移。

## Open Questions / Ambiguities

1. `structure_mode` 的权威读取顺序应否永远 source manifest 优先？现有注释说 source authoritative，但实现优先 works manifest。若 works manifest 只是 Phase 1.5 副本，建议 source-first 或至少检测二者不一致并阻断。
2. empty `memory_timeline` / empty `stage_events` 是否应完全合法？目前 prompt / schema 暗示合法，post-processing 却把它作为 warning。需要决定 warning 是否只是信息提示，还是应在某些阶段变成 hard gate。
3. `users/_template` 是否是模板而非 fixture？这个决定会影响未来产物 validation 的 allowlist。

## Alignment Summary

整体架构文档对 extraction pipeline 的阶段职责、Phase 3.5 consistency gate、Phase 4 scene archive、light_novel 双模式调度写得很清楚；多数 schema 也能加载，说明数据契约层没有基础损坏。

最不对齐的是“hard gate 是否真的接在运行路径上”：ingestion validator 已实现但未进入 CLI；Phase 3.5 文档承诺的 memory digest 检查因 loader 判型错误而空跑；post-processing 的派生数据更新语义与“1:1 当前源数据”契约不一致。

prompt / schema 层还有少量直接冲突，最明确的是 scene split summary 30 字 vs schema minLength 50。这个问题小但高频，会在 Phase 4 批处理里放大成 retry 成本。

## Residual Risks

- 本轮没有读取完整 `logs/change_logs/` 历史，只在当前 ai_context / docs / code 真相内审计；若某些“默认 monolithic”语义有历史决策支撑，需要通过 change log 复核再改。
- 未跑完整 extraction 或 repair integration tests； findings 基于静态代码路径、schema / prompt / docs 对照，以及轻量 schema sanity check。
- Phase 3.5 里 world_event_digest 的 count / summary 检查看起来比 memory_digest 更接近可用，但建议在修 H1 时一并加 fixture，避免同类 loader / id parsing 问题后来复发。

## 建议落地顺序

1. 先修 H1：给 consistency checker 增加 list-shaped JSON loader 与 memory digest regression fixture。这是明确 checker blind spot，优先级最高。
2. 再修 H2：把 ingestion validator 接进 CLI，并移除 `structure_mode` fail-open default；同步改 `automation/README.md`。
3. 修 M3：post-processing 改成 per-stage replace-slice，包括 empty slice stale removal。
4. 修 M1 / M2：收敛 scene split prompt/schema；把 Phase 4 missing / empty chapter 变成明确失败终态。
5. 澄清 L1：决定 `users/_template` 的 fixture / template 身份，再更新 README 或 validator allowlist。
