**Review 模型**：Codex（`codex`）

# Findings

## High

### 1. `relationship_core` / `pinned_memories` 没有单一真实契约，模板已经同时携带两套互相冲突的存储形态

- 结论：
  当前仓库同时存在两套不兼容的用户层约定：
  1. `schemas/user/relationship_core.schema.json` 与 `users/_template/relationship_core/manifest.json` 把 `pinned_memories` 定义为 `relationship_core/manifest.json` 内联数组。
  2. `users/README.md`、`simulation/flows/startup_load.md`、`simulation/retrieval/load_strategy.md` 又要求运行时读取单独的 `relationship_core/pinned_memories.jsonl`。
  3. 模板目录里两者还同时存在：`manifest.json` 里有 `"pinned_memories": []`，并且仓库还跟踪了空的 `users/_template/relationship_core/pinned_memories.jsonl`。
- 为什么这是问题：
  这不是单纯文档表述差异，而是“写入位置”和“读取位置”都分叉了。后续任何 runtime writer / loader / merge 逻辑，只要有人按 schema 实现、有人按 runtime docs 实现，就会出现一边写 manifest、另一边只读 jsonl 的静默丢数据问题。
- 影响范围：
  `users/_template/`、schema 层、runtime 设计文档、后续所有 relationship merge / startup load / pinned memory promotion 实现。
- 证据：
  - `schemas/user/relationship_core.schema.json:66` 定义内联 `pinned_memories`
  - `users/_template/relationship_core/manifest.json:12` 写入 `"pinned_memories": []`
  - `users/_template/relationship_core/pinned_memories.jsonl` 作为独立文件已存在
  - `users/README.md:46-48`、`users/README.md:174-175`、`users/README.md:247-248` 指向 `relationship_core/pinned_memories.jsonl`
  - `simulation/flows/startup_load.md:38-39` 要求启动读取 `relationship_core/pinned_memories.jsonl`
  - `simulation/retrieval/load_strategy.md:89-93` 也把 `pinned_memories.jsonl` 当作 on-demand 读取目标
  - `docs/architecture/data_model.md:351-352`、`docs/architecture/data_model.md:436-437` 仍写成 `relationship_core/pinned_memories.json`
- 应视为更高优先级真相：
  仓库内部目前无法唯一判断。模板目录同时保留 manifest 字段和 jsonl 文件，说明“真实契约”尚未收敛；这会直接误导后续 AI 和实现者。

### 2. Phase 3.5 的 `evidence_refs` 覆盖率检查没有覆盖 world stage snapshot，和需求承诺不一致

- 结论：
  文档把 Phase 3.5 第 4 项定义为“快照和记忆条目中 evidence_refs 为空的比例”，但实现只检查角色 `stage_snapshot` 和 `memory_timeline`，没有检查 `world/stage_snapshots/{stage_id}.json` 的 `evidence_refs`。
- 为什么这是问题：
  `world_stage_snapshot` 本身就带 `evidence_refs` 字段。当前一致性检查会让世界层快照在完全缺失章节锚点时仍然通过 Phase 3.5，导致世界包的可追溯性回退无法被这道质量门发现。
- 影响范围：
  Phase 3.5 一致性审计、世界层 traceability、后续依赖 `evidence_refs` 做人工复核或补抽定位的流程。
- 证据：
  - `docs/requirements.md:2027`：第 4 项写的是“快照和记忆条目中 evidence_refs 为空的比例”
  - `docs/architecture/extraction_workflow.md:262`：同样写“evidence_refs 覆盖率”
  - `schemas/world/world_stage_snapshot.schema.json:104`：world snapshot 明确有 `evidence_refs`
  - `automation/persona_extraction/consistency_checker.py:329-370`：`_check_evidence_refs_coverage()` 只遍历 `character_ids` 下的 snapshot 和 timeline，没有读取任何 `world/stage_snapshots/*.json`
- 影响判断：
  这是检查器盲区，不是单纯文档漂移。仓库明确要求把“检查器 / 一致性工具本身的盲区”按高优先级处理，这条满足该条件。

## Medium

### 3. 权威需求文档仍然使用不存在的 `repairing` 阶段名，和代码中的正式状态机不一致

- 结论：
  `docs/requirements.md` 的 Phase 3 状态机图仍写 `post_processing → repairing → passed`，但代码里的真实状态名是 `post_processing → reviewing → passed`。
- 为什么这是问题：
  `docs/requirements.md` 被 `ai_context/requirements.md` 明确标为 authoritative source。后续 AI 或运维若按需求文档理解进度文件，会把 `repairing` 当成持久化状态名，但 `phase3_stages.json` / `StageState` 根本不会出现这个值。
- 影响范围：
  需求文档、运维排障、AI handoff、任何基于状态名写脚本或分析日志的人。
- 证据：
  - `docs/requirements.md:1264-1265`：仍显示 `post_processing → repairing`
  - `automation/persona_extraction/progress.py:8-16`：正式状态机是 `post_processing → reviewing`
  - `automation/README.md:232-239`：README 也已同步到 `reviewing`
- 应视为更高优先级真相：
  代码和 `progress.py` docstring 才是当前真实状态机；`docs/requirements.md` 这里已经过时。

### 4. `docs/architecture/data_model.md` 仍在批量引用旧的 `.json` 用户文件名，和模板 / runtime 文档的 `.jsonl` 约定脱节

- 结论：
  `docs/architecture/data_model.md` 仍把 session / archive / pinned memory / world history 多处写成 `.json`，而当前模板与 runtime 文档大量使用 `.jsonl`。
- 为什么这是问题：
  `ai_context/handoff.md` 明确让后续 AI “Architecture detail → `docs/architecture/data_model.md`”。如果这份主文档继续输出旧文件名，未来实现极易把对话、摘要、memory updates、key moments 甚至 world history 写到错误路径或错误格式。
- 影响范围：
  用户层 runtime contract、历史归档、按需加载、未来 loader / writer 实现。
- 证据：
  - `docs/architecture/data_model.md:348`、`:352`、`:395-423`、`:436-453` 仍写 `key_moments.json`、`turn_summaries.json`、`memory_updates.json`、`transcript.json`、`pinned_memories.json`
  - `users/README.md:37-44`、`:174-181` 使用 `key_moments.jsonl`、`turn_summaries.jsonl`、`memory_updates.jsonl`、`transcript.jsonl`、`pinned_memories.jsonl`
  - `simulation/retrieval/load_strategy.md:86-93`、`:156-163` 也使用 `.jsonl`
  - `docs/architecture/data_model.md:222`、`:287` 写 `world/history/timeline.json`
  - `simulation/retrieval/load_strategy.md:86` 写 `world/history/timeline.jsonl`
- 备注：
  这条和 Finding 1 同属 runtime contract 漂移，但范围更广，已超出 `relationship_core` 单点。

## Low

### 5. `docs/logs/` 已跟踪文件里仍有不满足 HHMMSS 规范的历史日志

- 结论：
  仓库约定要求所有日志文件使用 `YYYY-MM-DD_HHMMSS_slug.md`，但实际仍跟踪了 `docs/logs/2026-04-03_stage_boundary_alignment_and_prompt_rewrite.md`。
- 为什么这是问题：
  这会削弱基于文件名排序 / grep 的自动化假设，也说明仓库自己没有完全遵守 `ai_context/conventions.md` 里的 mandatory naming rule。
- 影响范围：
  日志检索、历史排序、任何按文件名正则批处理 `docs/logs/` 的脚本。
- 证据：
  - `ai_context/conventions.md:8-13`：HHMMSS is mandatory
  - 违规文件：`docs/logs/2026-04-03_stage_boundary_alignment_and_prompt_rewrite.md`

# False Positives / 本轮排除项

- 先前关于 baseline prompt 未注入 `stage_catalog` schema 的问题，本轮复核后已不成立：
  `automation/persona_extraction/prompt_builder.py:160-170` 已包含
  `world/world_stage_catalog.schema.json` 与 `work/stage_catalog.schema.json`。
- 先前关于 target map 重要度阈值无法识别带注释角色名（如“角色A（某时期）”）的风险，本轮复核后已不成立：
  `automation/persona_extraction/validator.py:88-111` 已改为 substring 匹配并按重要度 / 名称长度决策。
- 先前关于 REVIEWING / PASSED resume 路径可能误提交删除的问题，本轮复核后已不成立：
  `automation/persona_extraction/orchestrator.py:1362-1384` 与 `:1588-1601`
  已补上 on-disk product existence guard。
- 先前关于 `relationship_history_summary` / `scene_refs` 缺少程序化检查的担忧，本轮复核后已不成立：
  `automation/repair_agent/checkers/structural.py:111-146` 与
  `automation/persona_extraction/consistency_checker.py:354-370`
  已覆盖这些字段。

# Open Questions / Ambiguities

1. `relationship_core` 的长期记忆到底应该以哪种形态为 canonical truth：
   `manifest.json` 内联数组，还是 `pinned_memories.jsonl` 独立文件？
2. `docs/architecture/data_model.md` 是否被视为“当前真实契约”，还是允许保留未来态草图？
   如果是前者，当前内容已经明显过时；如果是后者，需要明确标注“future / non-normative”，否则会继续误导后续实现。
3. Phase 3.5 的 `evidence_refs` 覆盖率是否应该把 world snapshot 也纳入 warning 统计？
   依当前 requirements 文案，我的判断是“应该”，但仓库里没有单独的 world-specific 说明。

# Alignment Summary

- 对齐较好：
  `ai_context/`、`automation/README.md`、`automation/persona_extraction/` 主实现，在 extraction branch discipline、lane-level resume、commit-ordering contract、baseline prompt schema 注入等关键链路上基本一致。
- 最不对齐：
  用户层 / runtime storage contract。schema、模板、`users/README.md`、`simulation/`、`docs/architecture/data_model.md` 之间对文件路径与文件格式的描述已经分叉成多个版本。
- 额外说明：
  当前没有 runtime 实现代码，因此这一层的问题主要表现为“契约漂移”；但正因为实现尚未落地，现在不收敛，后面更容易把漂移固化成代码。

# Residual Risks

- `automation/repair_agent/fixers/programmatic.py` 仍保留 `except ImportError: _jsonschema = None` 的 legacy 分支；当前由于 schema checker 已把 `jsonschema` 设为硬依赖，暂未观察到功能性降级，但这类旧分支会继续制造“是否仍允许软降级”的阅读噪音。
- `README.md` 末尾的 “Start here” 仍把 `prompts/` 放进默认阅读列表，而 `AGENTS.md` / `ai_context/read_scope.md` 明确要求默认不要主动读 `prompts/`。这还不足以构成功能性 bug，但会继续给新会话制造偏航风险。
- 由于 runtime 尚未实现，当前大部分 user-layer contract 问题还没在代码里爆炸；一旦开始写 loader / writer，这些冲突会从“文档问题”迅速升级为真实兼容性问题。

# 建议落地顺序

1. 先统一 `relationship_core` / `pinned_memories` 的单一存储契约，并同步 schema、template、`users/README.md`、`simulation/`、`docs/architecture/`。
2. 立即补齐 Phase 3.5 对 world snapshot `evidence_refs` 的检查，避免继续放行无锚点世界快照。
3. 回收 `docs/requirements.md` 中的 `repairing` 状态名，并对 `docs/architecture/data_model.md` 做一次系统性文件名校准。
4. 顺手修正 `docs/logs/2026-04-03_stage_boundary_alignment_and_prompt_rewrite.md` 的命名，恢复日志约束的一致性。
