# TODO List Archived（归档清单）

---

## File guide

### Purpose

接收从 `docs/todo_list.md` 移走的两类任务条目：

- **Completed**：包括完整完成、部分完成、改方案后完成
- **Abandoned**：包括方案被颠覆、外部前提消失、合并到其他任务等

`docs/todo_list.md` 是**正在做和将来做**的事，本文件是**已经做完和决定不做**的事。两者互不重叠，原 todo 条目移过来后从源文件删除。

### 为什么要瘦身存档

不是为了保留完整改动记录——那个职责由 `git log` + `logs/change_logs/{timestamp}_{slug}.md` 共同承担。本文件仅作 **快速浏览索引**：

- 看 ID / 标题 → 知道有这件事
- 看完成形式 → 知道走到哪一步收尾的
- 看 1 行摘要 → 知道大概改了什么
- 看 log 链接 → 想了解细节就跳过去

**绝不在本文件保留改动清单原文 / 验证步骤 / 待决策项 / 长篇上下文**——这些在原 todo 段落里有，原 todo 一并被瘦身。需要追溯历史时去 git history 看 todo_list.md 删除前的版本，或去 change_logs 看落地详情。

### 条目格式

#### Completed 段

```markdown
### [T-XXX] 中文标题 · 完成于 YYYY-MM-DD · {完整 / 部分 / 改方案后} 完成

- 1 行摘要：实际改了什么 / 走到哪一步
- 关联 log: [logs/change_logs/YYYY-MM-DD_HHMMSS_slug.md](../logs/change_logs/YYYY-MM-DD_HHMMSS_slug.md)
- 关联 commit:（可选）`<short-sha>`
```

完成形式三档：

- **完整完成**：按原 todo 的完成标准全部达成
- **部分完成**：核心达成、留下次要尾巴；尾巴**必须作为新 todo 条目**重新登记到 `todo_list.md`，本归档行的摘要里标"尾巴去 T-YYY"
- **改方案后完成**：方案与原 todo 不同（更优 / 受新约束影响 / 实测后调整），但目的达成；摘要里 1 句话说清"原方案 vs 实际方案"

#### Abandoned 段

```markdown
### [T-YYY] 中文标题 · 废弃于 YYYY-MM-DD

- 废弃原因：1–2 句话
- 关联 log: [logs/change_logs/YYYY-MM-DD_HHMMSS_slug.md](../logs/change_logs/YYYY-MM-DD_HHMMSS_slug.md)
```

### 排序

每段内部按"完成 / 废弃日期"**降序**（新的在上）。同一天有多条按 ID 字母序。

### 不记录什么

✗ 仍在进行的任务 → `docs/todo_list.md`
✗ 历史 design 决策 → `ai_context/decisions.md`
✗ 落地细节 / diff / 验证日志 → `logs/change_logs/`
✗ 改动清单原文 → 不要从源 todo 拷过来
✗ 完整 PRE / POST log 内容 → 引一个链接就够了

### 读取时机

- 用户问"X 这件事我们之前做过 / 讨论过吗？" → 先在本文件 grep ID / 关键词
- 用户问"为什么不做 Y？" → 在 Abandoned 段查 → 引到对应 change_log
- 默认不主动加载（不进入 session 启动序列）

---

## Completed

### [T-ANALYSIS-SCHEMA-TIGHTEN] 收紧 phase 0 chunk + phase 1 candidate / world_overview schema 字段（chunk 删 `key_events` + `summary` 100-150→150-200；candidate 删 `recommended` + `aliases.first_appearance` + Phase 1.5 默认勾选改基于 `importance==主角`；world_overview `major_regions` / `levels` item 升对象 + `core_rules` 20→30 / 100→150）· 完成于 2026-05-11 · 完整完成

- 1 行摘要：完成标准最后一项"现有 `works/<work_id>/` 整 untracked 目录清掉后从 phase 0 全新跑 e2e — schema gate 不报红 + phase 0/1/1.5/2 全过"在 `extraction/<work_id>` 上达成；本次产物 27 chunks × `chapter_summary_chunk.schema` 全 PASS（`summary` 长度落在新 150-200 范围、`key_events` 字段从产物结构中消失）+ phase 1 三 lane `foundation` / `stage_plan` / `candidate_characters` schema 全 PASS（candidate 新 schema 形态：`recommended` / `aliases.first_appearance` 字段从产物结构中消失；Phase 1.5 用户选目标默认 = `importance == "主角"` 程序判定走通）+ phase 2 baseline `validate_baseline` 0 errors / 0 warnings；schema/prompt/code/ai_context/docs 改动 + 静态 gate 全过的代码侧前 4 项验证标准已于 2026-05-08 落地，本次补完 e2e 验证项。
- 关联 log: [logs/change_logs/2026-05-11_062140_yejunlin_fix_and_phase012_todo_complete.md](../logs/change_logs/2026-05-11_062140_yejunlin_fix_and_phase012_todo_complete.md)

### [T-PHASE2-TARGET-BASELINE] phase 2 产出 per-character target_baseline，作为 phase 3 全模式的 target keys 锚点 · 完成于 2026-05-11 · 完整完成

- 1 行摘要：完成标准最后一项"phase 2 跑通至少一个 work：每个 candidate character 产出 `target_baseline.json`，schema 合规"在 `extraction/<work_id>` 上达成；本次确认的 2 个 target character（`Character A` / `Character B`）均产出 `target_baseline.json` 通过 `schemas/character/target_baseline.schema.json` schema gate（含 `targets` 数组 `tier` ∈ {核心 / 重要 / 次要 / 普通} + `relationship_type` 柔性中文短词 + `description` ≤100 字 + `targets` cap 通过 `targets_cap.schema.json` $ref 共享）；schema 落地 + character_manifest 含 `target_baseline_path` + `validate_baseline()` 把 `target_baseline.json` 列为必须文件 + ai_context / docs 同步等前 4 项代码侧验证标准已于 2026-04-29 落地。phase 3 stage_snapshot keys == baseline 的运行时硬约束消费验证留给 phase 3 启动后跑。
- 关联 log: [logs/change_logs/2026-05-11_062140_yejunlin_fix_and_phase012_todo_complete.md](../logs/change_logs/2026-05-11_062140_yejunlin_fix_and_phase012_todo_complete.md)

### [T-PHASE0-CHUNK-SCHEMA-EXPAND] chapter_summary_chunk schema 二级字段扩展（命中 world_overview / foundation 不可信字段）· 完成于 2026-05-11 · 完整完成

- 1 行摘要：runtime 验证项三条全过——(1) `summarization.md` 实跑后 LLM 正确填 chunk-level 5 个二级字段（27 chunks 全产 `chunk_arc_summary` + 5 条 `chunk_world_rules` + `chunk_power_levels` + `chunk_factions` + `chunk_regions`），`chunk_world_rules.observed_impact` 共 135 entries 0 empty / 2 fallback `"未在本 chunk 直接观察"` / 133 真实事件描述，无静默留空；(2) phase 1 foundation lane 产 `power_system.levels` 反映本作真实力量体系（`凡人/淬体/聚灵/破元境九层巅峰/天元境一层` 等本作特化命名，非"练气筑基金丹元婴"仙侠默认模板），`world_structure.summary` 反映原文真实区域结构；(3) `foundation.json` schema 全 PASS（决策 #54 后 foundation 路径前移到 phase 1 直产 `world/foundation/foundation.json`，本 todo 的"foundation 质量改善"目的等价达成）。schema / prompt / ai_context / docs 改动 + 静态 gate 全过的代码侧验证标准已于 2026-05-04 落地。
- 关联 log: [logs/change_logs/2026-05-11_062140_yejunlin_fix_and_phase012_todo_complete.md](../logs/change_logs/2026-05-11_062140_yejunlin_fix_and_phase012_todo_complete.md)

### [T-PHASE1-PARALLEL-LANES] Phase 1 三 lane 并行 + 字段裁剪 + light_novel stage_plan 跳过 LLM · 完成于 2026-05-07 · 完整完成

- 1 行摘要：`automation/prompt_templates/` 删除 `analysis.md`，新增 3 件 lane 专用 prompt（`analysis_world_overview.md` / `analysis_stage_plan.md`（含 #27m 步骤 2.1/2.2/2.3 反锚定自检三子步） / `analysis_candidate_characters.md`（含步骤 1.5 跨 chunk 身份合并））；`automation/persona_extraction/prompt_builder.py` 删 `build_analysis_prompt`，加 `build_world_overview_prompt` / `build_stage_plan_prompt` / `build_candidate_characters_prompt` 三入口 + `_project_chunk_for_world_overview` / `_project_chunk_for_stage_plan` / `_project_chunk_for_candidates` 三个内部裁剪函数 + `prepare_phase1_lane_inputs` / `cleanup_phase1_lane_inputs` 两个 tmpdir helper；`orchestrator.py::run_analysis` 整体重写为 fan-out（monolithic = 3 lane 并行 + try/finally cleanup tmpdir / light_novel = 2 lane LLM + `_build_light_novel_stage_plan` 程序化派生 stage_plan 跳过 LLM）；per-lane retry = schema gate + `prior_error` 注入下一次 prompt（与 phase 0/4 同形态），per-lane 独立 `[phase1].exit_validation_max_retry` 预算；新增 `[phase1].lane_concurrency = 3` config + `Phase1Config.lane_concurrency` 字段；`.gitignore` 加 `works/*/analysis/.phase1_lane_inputs/`；ai_context/decisions.md 新增 #52 durable 决策 + #27i 通路描述 + #27m 路径同步 + ai_context/architecture.md Phase 1 bullet 重写 + docs/architecture/extraction_workflow.md §3 完整重写 + docs/architecture/schema_reference.md 4 处 phase 1 来源同步 + automation/README.md prompt_templates 树 + Phase 1 双模式段 + schema gate 表同步 + ai_context/conventions.md Cross-File Alignment 表更新 chunk schema 消费方。**执行偏差**：原计划集成 `repair_agent.run` 走 L1/L2/L3 + T0/T1/T2/T3 lifecycle，盘点后发现 phase 2 实际不调 repair_agent + phase 1 输出非 stage-anchored，改用更轻的 `prior_error` 注入式 retry（与 phase 0/4 同形态），具体见 PRE log 偏差段。Smoke 全过：jsonschema metaschema 4 件（world_overview / stage_plan / candidate_characters / chapter_summary_chunk）+ prompt_builder import + orchestrator import + 三 projector 字段集精确匹配（多余 / 缺失字段都 fail）+ run_analysis 结构 grep（含 ThreadPoolExecutor / prior_error / light_novel skip）+ `.gitignore` 命中验证。Runtime 端到端验证留给下一次 /loop。
- 关联 log: [logs/change_logs/2026-05-07_132608_phase1_parallel_lanes.md](../logs/change_logs/2026-05-07_132608_phase1_parallel_lanes.md)

### [T-PHASE0-RECOVERY-SWEEP] phase 0 主循环结束后对 timeout/max_turns 失败 chunk 用 effort=high 单次 sweep 救火 · 完成于 2026-05-06 · 完整完成

- 1 行摘要：`progress.py ChunkEntry` 加 `recovery_attempted: bool = False`（向后兼容 `from_dict.get(...,False)`）；`config.py Phase0Config.recovery_effort = 'high'` + `automation/config.toml [phase0] recovery_effort = "high"`；`llm_backend.py LLMBackend.run / ClaudeBackend.run / CodexBackend.run / run_with_retry` 全加 `effort: str | None = None` per-call kwarg（claude `--effort` 透传，codex 暂忽略保持接口一致）；`orchestrator.py` 新增 `_run_recovery_sweep`（filter `state=='failed'` AND error 含 `'timed out'` / `'error_max_turns'` AND `recovery_attempted==False` 的 chunk → ThreadPoolExecutor max_workers=concurrency 并发跑 `_summarize_chunk(_recovery_effort='high')`，含完整 L1/L2/L3+tolerance 流程；不论成败置 `recovery_attempted=True`），`run_summarization` 主循环结束 + gate 检查之间调一次；`_summarize_chunk` 加 `_recovery_effort` 内部 kwarg + 3 处 L3 retry 递归调用全部透传。docs 同步：`ai_context/decisions.md` 加 #49 durable + `architecture.md` Key Design 段加 recovery sweep bullet + `docs/architecture/extraction_workflow.md` Phase 0 段加 recovery sweep 段落 + `docs/requirements.md` `phase0_summaries.json` 描述加 `recovery_attempted` 字段说明；新建 `_smoke_recovery_sweep.py` 4 场景测试（filter / success / failure / no-candidate no-op）全过；既有 `_smoke_l3_gate.py` 4 场景仍全过（无回归）。
- 关联 log: [logs/change_logs/2026-05-06_163155_phase0_recovery_sweep.md](../logs/change_logs/2026-05-06_163155_phase0_recovery_sweep.md)

### [T-LENGTH-TOLERANCE-GATE] 各 LLM phase 终点接 length-bound tolerance（±10%）兜底 + max_turns 50→80 + chunk_size default 25→20 · 完成于 2026-05-06 · 完整完成

- 1 行摘要：`automation/persona_extraction/validator.py` 末尾追加 `relaxed_schema_for_length` + `validate_with_length_tolerance` helper（`_validate_schema` / `validate_baseline` 加 `length_tolerance: float = 0.0` kwarg 透传）；5 处 LLM 终点接 strict-retry-exhausted 兜底——orchestrator._summarize_chunk Phase 0 L3 / orchestrator.run_analysis Phase 1 exit_validation 耗尽 / orchestrator.run_baseline_production Phase 2 / scene_archive Phase 4 final attempt / repair_agent.coordinator T3_EXHAUSTED 改判 `LENGTH_TOLERANCE_PASS` (Phase 2/3/3.5/4)；`config.toml [phase3] max_turns` 50→80 + `cli.py --chunk-size default` + `orchestrator.__init__ chunk_size: int = 20` 默认 25→20；ai_context/architecture.md Key Design 段 + decisions.md #48 + docs/requirements.md / docs/architecture/extraction_workflow.md / 同步描述；`_smoke_l3_gate.py` 加场景 D（lifecycle 2 length-only fail → tolerance PASS）。静态 gate 全过：5 个 unit case (strict pass / minLength 95 vs 100 tol pass / 89 < 90 fail / 95+enum mix fail / maxLength 160 vs 150 tol pass + relaxed_schema deep-copy)；TOML phase3.max_turns=80；argparse default 20；4 场景 _smoke_l3_gate (A/B/C 不动 + D PASS)；orchestrator/scene_archive/post_processing/coordinator import 全过；grep "chunk_size = 25" / "default: 25" / "max_turns = 50" 残留 0。runtime 验证（重跑<character> phase 0 27 chunks）由后续 /loop 跑。
- 关联 log: [logs/change_logs/2026-05-06_121047_length_tolerance_gate.md](../logs/change_logs/2026-05-06_121047_length_tolerance_gate.md)

### [T-PHASE0-SUMMARIZE-TIMEOUT-BUMP] phase 0 summarize 子进程超时 600s → 1800s 并解耦于 phase3.review_timeout_s · 完成于 2026-05-04 · 完整完成

- 1 行摘要：runtime 验证发现 wave 1 全部 10 chunk 撞 600s 子进程超时（25 章 + chunk-level 5 个二级聚合字段 + opus-4-7 effort=max 单 chunk wall 常 ≥600s）；`Phase0Config` 加 `summarize_timeout_s: int = 1800`、`automation/config.toml [phase0]` 加同名键 + 中文注释、`orchestrator.py:_summarize_chunk` 改用 `phase0.summarize_timeout_s`（原借用 `phase3.review_timeout_s` 不动，仍服务 phase 3 reviewer 短链）；automation/README.md / docs/architecture/extraction_workflow.md / docs/requirements.md 同步硬超时数字与配置分节描述；ai_context/decisions.md 加 #47 durable 决策。smoke 全过：TOML / load_config / orchestrator import / grep 残留 0。
- 关联 log: [logs/change_logs/2026-05-04_154622_phase0_summarize_timeout_bump.md](../logs/change_logs/2026-05-04_154622_phase0_summarize_timeout_bump.md)

### [T-CHAPTER-MULTIVOL] chapter_id 格式改 C0001 + chapter_index 加多卷字段 · 完成于 2026-04-30 · 完整完成

- 1 行摘要：(1) `schemas/work/chapter_index.schema.json` `chapter_id` 加 `pattern: "^C[0-9]{4}$"` + 新增 3 个可选字段 `volume_id`（`^V[0-9]{3}$`）/ `volume_title` / `volume_chapter_seq`（多卷书必填三件套，单卷书不填）；(2) `prompts/ingestion/原始资料规范化.md` 例子改 `C0001` / `chapters/C0001.txt` + 多卷书识别条件与三字段填写指引；(3) <character> `sources/works/<work_id>/` 全量迁移 537 章（chapter_index.json 537 条 `chapter_id` / `normalized_path` 字段值改写、`chapters/0001.txt`~`0537.txt` 重命名为 `C####.txt`，epub 内部 `source_path` 保持原样）；(4) `ai_context/conventions.md` § Naming and Identifiers 加 chapter_id / volume_id 命名规则与位宽理由；(5) `ai_context/decisions.md` Work Scope 加 #10a；(6) `docs/architecture/schema_reference.md` 同步描述。`automation.ingestion.validator` 校验通过、jsonschema 校验通过、全库 `chapter[0-9]{4}` 残留为 0。子章节切分约定推到 T-INGEST-STRUCTURE-MODE。
- 关联 log: [logs/change_logs/2026-04-30_215840_chapter_id_multivol.md](../logs/change_logs/2026-04-30_215840_chapter_id_multivol.md)

### [T-CONSISTENCY-TARGETS-SUBSET] phase 3 stage_snapshot 三结构 keys == baseline.targets 强校验 + map 切 character_id keying + targets_cap 路径回滚 · 完成于 2026-04-30 · 完整完成

- 1 行摘要：D4 由"prompt 软约束 + 文档承诺"升级到代码强校验：(1) snapshot `voice_state.target_voice_map` / `behavior_state.target_behavior_map` 切 `target_character_id` keying（保留 `target_type` 作 sibling 元数据），与顶层 `relationships` 统一；(2) 三结构 keys 必须**双向相等**于 `baseline.targets[].target_character_id`（多/少都 fail），三态由内容是否填充承载，fixed_relationship 例外可预填关系字段，"fixed = 全书贯穿不变"严控（故事中才建立 / 改变 / 解除的师承 / 门派 / 婚姻 / 收养 / 决裂 等都不算）；(3) 校验从 phase 3.5 末端搬到 phase 3 单 stage validate 层，新增 L2 cross-file checker `repair_agent/checkers/targets_keys_eq_baseline.py`，越界走 file-level repair lifecycle (L1/L2/L3)；(4) `targets_cap.schema.json` 从 `schemas/_shared/` 回滚到 `schemas/character/`（共享面只在 character 域内），$ref + decision #27b + README 同步。docs / ai_context / prompt 全链 ⊆ → == 同步刷新。
- 关联 log: [logs/change_logs/2026-04-30_034614_targets_keys_eq_baseline.md](../logs/change_logs/2026-04-30_034614_targets_keys_eq_baseline.md)

### [T-CHAR-SNAPSHOT-PER-STAGE] character_snapshot prompt 补 prev_stage 出场字段三态规则 · 完成于 2026-04-29 · 改方案后完成

- 1 行摘要：原方案 = prompt 三态 + schema stage_delta 结构化（changed/removed/added），但被 T-BASELINE-DEPRECATE 拍板的"stage_delta 维持自由文本"否决；改方案 = 仅 prompt 改动。`character_snapshot_extraction.md` 在已有 (A) 未出场继承 后追加：(B) 出场且有变化 → 重写 + stage_delta 点出 / (C) 出场且无变化 → 保留 prev 但 required 必填 / (D) resolved-revealed-消除 → 在 stage_delta 写明消除原因（与 maxItems 裁剪两件事）；per-stage 推演原则；stage_delta 字段说明禁"无明显变化"敷衍。`ai_context/decisions.md` 加 11f。
- 关联 log: [logs/change_logs/2026-04-29_155949_char_snapshot_per_stage_three_state.md](../logs/change_logs/2026-04-29_155949_char_snapshot_per_stage_three_state.md)

### [T-REPAIR-T3-LIFECYCLE-RESET] T3 触发后开新 repair lifecycle，单文件最多 2 个 lifecycle · 完成于 2026-04-29 · 完整完成

- 1 行摘要：`max_lifecycles_per_file=2`（取代旧 `t3_max_per_file=1`）；coordinator 抽 `_run_one_lifecycle`，外层 lifecycle 循环；lifecycle 1 触发 T3 即返回（无 Post-T3 corruption 检查 / 无当轮 L3 gate / 无 Phase C），状态机重置后进入 lifecycle 2，禁用 T3 + 升 T3 即 `T3_EXHAUSTED`；T3 prompt 携带 `prior_attempt_context`（resolved+remaining 摘要 ≤600 char）；triage cap 改为 per-lifecycle，磁盘 jsonl append-only，lifecycle 2 启动前读已 accept fingerprint 过滤；recorder 事件加 `cycle` 字段；`T3_CORRUPTED` 路径完整删除。Smoke 三场景（A 单 lifecycle PASS / B lifecycle 1 T3→lifecycle 2 PASS / C 持续失败→T3_EXHAUSTED）+ 6 triage 场景全过。
- 关联 log: [logs/change_logs/2026-04-29_030118_repair-t3-lifecycle-reset.md](../logs/change_logs/2026-04-29_030118_repair-t3-lifecycle-reset.md)

### [T-LOAD-STRATEGY-WORLD-EVENTS-BOUND] load_strategy.md 删除复述 schema 的具体 bound · 完成于 2026-04-28 · 改方案后完成

- 1 行摘要：原方案"L17 把 50–80 改成 50–100"；实际方案升级为通用清理——`simulation/retrieval/load_strategy.md` 三处复述 schema 数值（L17 world event_digest summary `50–80 chars, hard schema gate`、L22-23 identity `≤ 200 chars` / `≤ 10 entries`、L41 memory_digest summary `30–50 chars, hard schema gate`）全部删除，只留"length capped at extraction time by … schema"指针；loader 自身行为参数（recent 2 stages 窗口、stage 1..N filter、token 预算估算）原样保留。判定准则："数字改了之后跟谁走"——跟 schema 走 → 删；跟 loader 代码走 → 留。
- 关联 log: [logs/change_logs/2026-04-28_234002_load-strategy-drop-schema-bounds.md](../logs/change_logs/2026-04-28_234002_load-strategy-drop-schema-bounds.md)

### [T-CHAR-SNAPSHOT-13-DIM-VERIFY] 角色 stage_snapshot "13 必填维度" 表述核对 · 完成于 2026-04-27 · 改方案后完成

- 1 行摘要：原方案候选"字面 17 条" vs 实际方案"指针式"；`docs/architecture/extraction_workflow.md:277` 与 `docs/requirements.md:2139` 改为"以 `schemas/character/stage_snapshot.schema.json` 的 `required` 列表为准"，去掉具体数字与字段示例，避免下次 schema 增减字段时再次漂移。
- 关联 log: [logs/change_logs/2026-04-27_185531_char-snapshot-required-fields-pointer.md](../logs/change_logs/2026-04-27_185531_char-snapshot-required-fields-pointer.md)

---

## Abandoned

### [T-PHASE35-IMPORTANCE-AWARE] Phase 3.5 一致性检查按 importance 调门槛 · 废弃于 2026-04-30

- 废弃原因：核心痛点（`_check_target_map_counts` 对从未登场 / tier=次要/普通 角色 over-error）已在 T-CONSISTENCY-TARGETS-SUBSET commit `620be09` 顺手用"空 examples 跳过"守卫等价解决；剩余 7 个 `_check_*` 的 over-error 风险被 D4 == + schema-required 字段双重稀释，且 T-PHASE2-TARGET-BASELINE / T-BASELINE-DEPRECATE runtime 未跑前调阈值是过早优化。后续如确有需要，按"D4-state + tier 双锚点"重新立项即可。
- 关联 log: [logs/change_logs/2026-04-30_045522_abandon_t_phase35_importance_aware.md](../logs/change_logs/2026-04-30_045522_abandon_t_phase35_importance_aware.md)

### [T-MIGRATE-TARGET-BASELINE-ZH] 迁移现有 target_baseline.json：英文 enum → 中文柔性 string + tier 路人→普通 · 废弃于 2026-04-30

- 废弃原因：前提失效，无可迁移对象。原 todo 假设"phase 2 已 commit baseline 全是英文值，新 schema 校验 fail"，但 `works/` 在 `## Do-not-commit paths` 内，target_baseline.json 从未入库（`git log --diff-filter=D` 全空）；本地当前 work 的 `analysis/` 也只剩空 progress/，无 baseline 文件。下次 phase 2 重跑直接用新中文 schema 生成，无需迁移工具。
- 关联 log: [logs/change_logs/2026-04-30_024305_abandon_t_migrate_target_baseline_zh.md](../logs/change_logs/2026-04-30_024305_abandon_t_migrate_target_baseline_zh.md)

---

### [T-CHAR-SNAPSHOT-TARGET-LIST] target_char_list 生成策略 + fallback 模式是否需要 · 废弃于 2026-04-29

- 废弃原因：被 T-PHASE2-TARGET-BASELINE 方案吞掉。原 todo 围绕 sub-lane step 0 三选一策略（program-only / llm-light / hybrid）+ fallback 是否跑 step 0；新方案 phase 2 全书视野一次拍 per-character target_baseline.json，后续各 stage ⊆ baseline 写 keys，step 0 整个删除，两个决策项都不再需要。
- 关联 log: [logs/change_logs/2026-04-29_203800_abandon_char_snapshot_target_list.md](../logs/change_logs/2026-04-29_203800_abandon_char_snapshot_target_list.md)
