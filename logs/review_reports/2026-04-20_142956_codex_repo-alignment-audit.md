**Review 模型**：Codex（`codex`）

# Repo Alignment Audit

## Findings

### High

1. `REVIEWING`/`PASSED` 恢复路径对“当前 stage 产物已缺失”的检测不成立，存在把缺失文件直接带过审校并提交删除的风险。
   - 结论：`orchestrator` 在进入 repair agent 前，只检查“任一角色的 `stage_snapshots/` 目录是否存在”，而不是检查“当前 `stage_id` 的 world/snapshot/timeline 文件是否都还在”。随后 `_collect_stage_files()` 对缺失文件直接返回 `None` 并跳过，repair agent 根本看不到缺失项；最终 `commit_stage()` 又会 `git add -A works/`，把删除也一起提交。
   - 为什么这是问题：这条链路会把“恢复安全网”变成假安全网。只要某个 stage 在 `POST_PROCESSING` 之后、`COMMITTED` 之前被外部删掉当前 stage 文件，恢复流程就可能在没有报错的情况下继续审校剩余文件，并把缺失文件的删除提交进 extraction branch。
   - 影响范围：Phase 3 中所有 `REVIEWING`/`PASSED` 恢复场景；一旦命中，既破坏 stage 自包含契约，也会污染 git 历史。
   - 证据：
     - `automation/persona_extraction/orchestrator.py:1551-1564`
     - `automation/persona_extraction/orchestrator.py:427-460`
     - `automation/persona_extraction/orchestrator.py:501-556`
     - `automation/persona_extraction/git_utils.py:141-145`

### Medium

2. target-map 例句数量门控对带注释的主角/重要配角名称失效，主角条目会被按“其他”阈值放行。
   - 结论：`load_importance_map()` 只返回 `{character_id: importance}`，而 `StructuralChecker._check_target_map()` 用 `self._importance_map.get(target_name, "其他")` 做精确匹配；但实际样例里的 `target_type` 经常写成带括号说明的字符串，如 `<character_a>（<phase_alias>）`。这类条目匹配不到 `candidate_characters.json` 中的 `<character_a>`，于是阈值从主角的 5 条降成默认的 1 条。
   - 为什么这是问题：文档和 prompt 都把 `target_voice_map` / `target_behavior_map` 的样本数当成核心质量门控；当前实现却会对最重要的对象降级放行，等于把“高风险退化”伪装成“通过结构校验”。
   - 影响范围：所有 `target_type` 不是裸 `character_id` 的快照；尤其是使用“角色名 + 阶段注释/认知标签”的写法时。
   - 证据：
     - `automation/persona_extraction/validator.py:64-80`
     - `automation/repair_agent/checkers/structural.py:182-205`
     - `works/<work_id>/analysis/candidate_characters.json:54-90`
     - `works/<work_id>/characters/<character_b>/canon/stage_snapshots/阶段01_<location_a>初遇.json:478-492`
     - `works/<work_id>/characters/<character_b>/canon/stage_snapshots/阶段01_<location_a>初遇.json:770-784`
     - 对照可见，`consistency_checker` 已经改成 substring 匹配：`automation/persona_extraction/consistency_checker.py:400-456`

3. `automation/README.md` 的 Phase 3 状态机仍然写着 `failed → retrying → extracting`，与实际代码和 `ai_context` 已不一致。
   - 结论：代码里的状态机已经明确去掉 stage 级 `retrying`，并且 `FAILED` 只能进 `ERROR`，再由 `--resume` 复位到 `PENDING`；但 `automation/README.md` 仍保留旧路径。
   - 为什么这是问题：这是操作层文档，不是边角注释。后续维护者如果按 README 理解恢复语义，会误判哪些状态能自动重试、哪些状态需要 `--resume` 或磁盘 reconcile 介入。
   - 影响范围：运维操作、故障排查、以及任何把 README 当流程真相的后续 AI/开发者。
   - 证据：
     - 旧文档：`automation/README.md:229-235`
     - 当前代码真相：`automation/persona_extraction/progress.py:11-20`
     - 当前状态迁移：`automation/persona_extraction/progress.py:332-345`
     - `ai_context` 当前叙述：`ai_context/current_status.md:59-60`

4. `relationship_core` / 用户会话文件的存储格式在 schema、模板、架构文档、运行时加载文档之间出现 split-brain。
   - 结论：`relationship_core.schema.json` 把 `pinned_memories` 定义为 `manifest.json` 内联数组，模板 `users/_template/relationship_core/manifest.json` 也这么写；但 `users/README.md`、`simulation/flows/startup_load.md`、`simulation/retrieval/load_strategy.md` 又把它描述成独立的 `pinned_memories.jsonl` 文件。与此同时，`docs/architecture/data_model.md` 还在用 `turn_summaries.json` / `memory_updates.json` / `history/timeline.json` 这套旧文件名，而用户目录说明和 load strategy 已经切到 `.jsonl`。
   - 为什么这是问题：这不是单纯的文档排版差异，而是“同一份数据到底存哪里、读哪个文件、是否需要双写”的根本分叉。运行时还没落地时，这类分叉最容易直接固化进新实现。
   - 影响范围：未来的 runtime loader、merge/writeback、用户数据 schema 扩展，以及任何据此实现 `users/` I/O 的代码。
   - 证据：
     - schema/模板内联数组：`schemas/relationship_core.schema.json:66-95`
     - schema/模板内联数组：`users/_template/relationship_core/manifest.json:1-17`
     - 独立 `.jsonl` 文档：`users/README.md:46-48`
     - 独立 `.jsonl` 启动加载：`simulation/flows/startup_load.md:33-35`
     - 独立 `.jsonl` 检索加载：`simulation/retrieval/load_strategy.md:86-90`
     - 架构文档旧文件名：`docs/architecture/data_model.md:333-336`
     - 架构文档旧文件名：`docs/architecture/data_model.md:373-383`
     - 架构文档旧文件名：`docs/architecture/data_model.md:396-403`
     - 架构文档旧文件名：`docs/architecture/data_model.md:414-421`

5. baseline prompt 要求按 stage-catalog schema 生成空 catalog，但 prompt builder 没有把这两个 schema 放进“必读文件清单”。
   - 结论：`baseline_production.md` 明确要求创建 `world/stage_catalog.json` 和 `characters/{char_id}/canon/stage_catalog.json`，并强调遵循对应 schema；但 `build_baseline_prompt()` 只注入了 identity / manifest / voice / behavior / boundaries / failure_modes / fixed_relationships 这些 schema，没有注入 `world_stage_catalog.schema.json` 和 `stage_catalog.schema.json`。
   - 为什么这是问题：这里的 agent 被提示“请按顺序读取，不要跳过”；缺 schema 就意味着它是在“要求按 schema 产出”与“实际看不到 schema 真相”的条件下工作。当前 catalog 恰好结构简单，但这是实打实的 prompt/implementation 漂移。
   - 影响范围：Phase 2.5 baseline 产出的一致性，尤其是未来如果 catalog schema 扩展时。
   - 证据：
     - builder 注入列表：`automation/persona_extraction/prompt_builder.py:157-165`
     - prompt 明示要按 schema 创建：`automation/prompt_templates/baseline_production.md:222-250`

## False Positives Checked

- `works/*/analysis/progress/`、`chapter_summaries/`、`scene_splits/`、`retrieval/` 在工作区里确实存在，但本轮检查没有把它们记为“已提交 artifact 漂移”。
  - 原因：`.gitignore` 已忽略这些目录（`/.gitignore:1-19`），`git status --ignored` 也显示为 ignored。本轮看到的是本地运行产物，而不是被纳入版本控制的 canon。

## Open Questions / Ambiguities

1. `relationship_core` 的 `pinned_memories` 以哪一种为准：
   - `manifest.json` 内联数组，还是独立 `pinned_memories.jsonl`？
   - 如果最终保留 sidecar，`relationship_core.schema.json` 是否也要拆分或补一个 sidecar schema？

2. 用户与归档 session 文件最终应统一为 `.json` 还是 `.jsonl`？
   - 当前 `docs/architecture/data_model.md` 和 `users/README.md`/`simulation/retrieval/load_strategy.md` 明显不一致。

3. baseline 阶段的 `stage_catalog.json` 初始化是否仍然是明确保留的设计？
   - 现在 docs 更强调 post-processing 自动维护，但 baseline prompt 仍要求先创建空 catalog。

## Alignment Summary

- 对齐较好：
  - `ai_context/`、`docs/architecture/extraction_workflow.md`、`progress.py`、`orchestrator.py` 对 Phase 3 主流程、repair agent、lane-level resume 的高层设计基本一致。
  - sample work 的核心 canon 结构（world / characters / stage snapshots / digests）与 schema 和 prompt 的主干模型是对得上的。

- 最不对齐：
  - 恢复/恢复后门控的实现细节，与它自称提供的“安全恢复”之间还有漏洞。
  - `automation/README.md` 和 `docs/architecture/data_model.md` 仍保留多处旧状态机/旧文件格式。
  - 用户侧数据模型在 schema、模板、README、runtime load 文档之间还没有唯一真相。

## Residual Risks

1. `relationship_history_summary` 在 prompt 中被视为必要质量项，但当前程序化门控没有显式检查它是否存在；后续如果样本退化，较可能以“结构上通过、扮演质量下降”的形式漏过。
   - 证据：`automation/prompt_templates/character_snapshot_extraction.md:68-71`
   - 证据：`automation/prompt_templates/character_snapshot_extraction.md:93-96`
   - 代码侧只显式检查 `driving_events`：`automation/repair_agent/checkers/structural.py:101-128`

2. `memory_timeline` 文档主叙述更强调 `scene_refs` 追溯链，但一致性检查当前只看 `evidence_refs` 覆盖率，没有校验 `scene_refs` 的存在性或可追溯性。
   - 证据：`docs/architecture/schema_reference.md:194-200`
   - 证据：`automation/persona_extraction/consistency_checker.py:326-355`

3. `users/_template` 中若干辅助文件（如 `session_index.json`、`archive_refs.json`、独立 `pinned_memories.jsonl`）仍没有对应 schema；在 runtime 真正落地前，这些文件最容易继续自由漂移。

## Suggested Landing Order

1. 先修 `REVIEWING`/`PASSED` 恢复链路的缺失文件检测与 file-collection 逻辑，再补一条针对“stage 文件被外部删除后 resume”的回归测试。
2. 统一 target-map importance 解析规则，让 repair gate 与 consistency checker 使用同一套 canonical/substring 逻辑。
3. 同步更新 `automation/README.md` 的状态机描述，避免继续传播旧恢复语义。
4. 选定用户侧文件真相：`pinned_memories`、`turn_summaries`、`memory_updates`、`history/timeline` 到底是 `.json` 还是 `.jsonl`，以及是否 sidecar。
5. 如果 baseline 仍需初始化空 catalog，就把两个 stage-catalog schema 加进 baseline prompt builder；如果不再需要，就删掉 baseline prompt 的该段要求。
