**Review 模型**：Claude Opus 4.7 (1M context) (`claude-opus-4-7[1m]`)

# /full-review — 全仓库对齐审计（2026-05-13 23:00 ET）

四线并行扫描（spec / impl / risk / artifact）后的合并 findings。重点针对最近三轮重构落地后的状态：
- 决策 #55（char_snapshot 4 sub-lane 拆分，commit a137e50 / 7210ac9 / a2f0e19）
- 决策 #56（pipeline-resume alignment 三处修复）
- 决策 #57（extraction 包结构 + validation 子包预留位）
- 决策 #54（foundation 前移 phase 1 + phase 2 仅补 key_figures）

仓库当前在 `main` clean；`works/<work_id>/` 是 local-only（git 不跟踪，符合三分支模型）。

---

## Findings

### High

**H1** `extraction/persona_extraction/orchestrator.py` Phase 0 / Phase 1 / Phase 3 outer pools + repair pool + Phase 4 pool **不调用 `executor.shutdown(wait=False, cancel_futures=True)`** 就直接 `raise RateLimitHardStop`

- **结论**：5 个外层 ThreadPoolExecutor 路径在 `as_completed` 循环里 `raise RateLimitHardStop` 时，没有先 cancel_futures。`with ThreadPoolExecutor(...)` 的隐式 `__exit__` 会 `shutdown(wait=True)` 阻塞，直到**所有**已提交的 worker 各自跑完（或各自再撞同一次 pause / hard stop 再 raise 上来）才解锁。
- **证据**：
  - [orchestrator.py:1651-1660](extraction/persona_extraction/orchestrator.py#L1651-L1660)（Phase 0 chunk pool）— `raise` 无 `cancel_futures`
  - [orchestrator.py:2066-2068](extraction/persona_extraction/orchestrator.py#L2066-L2068)（Phase 1 lane pool）— `fut.result()` 未显式 catch `RateLimitHardStop`，propagate 时 `__exit__` 阻塞
  - [orchestrator.py:2913-2939](extraction/persona_extraction/orchestrator.py#L2913-L2939)（Phase 3 outer lane pool）— `future.result()` 未 catch hard stop；Phase 3 高峰 1+2N+N lanes 全部要解开
  - [orchestrator.py:3140-3162](extraction/persona_extraction/orchestrator.py#L3140-L3162)（repair per-file pool）— `raise` 无 `cancel_futures`
  - [phases/scene_archive.py:965-983](extraction/persona_extraction/phases/scene_archive.py#L965-L983)（Phase 4 chapter pool）— `raise` 无 `cancel_futures`
- **正确范本**：[orchestrator.py:732-737](extraction/persona_extraction/orchestrator.py#L732-L737)（recovery sweep）+ [orchestrator.py:1004-1014](extraction/persona_extraction/orchestrator.py#L1004-L1014)（`_run_char_snapshot_sub_lanes` sub-executor，决策 #55 R2 写明的模式）都先 `pool.shutdown(wait=False, cancel_futures=True)` 再 raise
- **影响**：hard-stop（weekly ≥ 12h 或 probe ≥ 6h）路径上每个外层 pool 都白等到 worker 自行解套；Phase 3 N=2 角色时 11 个并发 lane 都得各自再 wait_if_paused 撞一次 hard stop 才能退出。CLI 退出码正确，但 wall time 从设计的"撞 hard stop 立即 exit 2"退化为分钟到小时级累计等待。前台拖死 user 体验，daemon 路径也烧同样 wall。决策 #55 R2 显式声明的"sub-executor `shutdown(wait=False, cancel_futures=True)` 并立即 raise"在内层做了，外层 4-5 个 sister pool 没跟上。
- **推断**：未经实测复现 hard-stop 路径，仅对照源码 + 决策 #55 R2 + 已正确实现的两个反例（recovery + sub-lane sub-executor）推断。

### Medium

**M1** [schemas/README.md:12](schemas/README.md#L12) 写"phase 3 产出由 `…snapshot_merge.py::merge_partials` 合并 **3 sub-lane** partial，决策 #55"——决策 #55 已是 **4** sub-lane（`char_expression` / `char_decision` / `char_internal` / `char_social`）。schemas/README 是 schema 层最高曝光索引，其他位置（schema_reference.md:346 / extraction_workflow.md:254-265 / ai_context/architecture.md:158 / docs/requirements.md §9.3）都已是 4——独此一处漂移，误导新读者数错合并面。

**M2** [extraction/persona_extraction/prompts/character_snapshot_extraction.md:102,104,139,177](extraction/persona_extraction/prompts/character_snapshot_extraction.md) 反复使用"stage_delta 自由文本"措辞，与 schema 矛盾。`stage_snapshot.schema.json:850-921` 的 `stage_delta` 是 `additionalProperties: false` 的**结构化对象**（6 properties：`trigger_events` / `personality_changes` / `relationship_changes` / `status_changes` / `mood_shift` / `voice_shift`）；决策 #55 sub-lane mutex 也明确依赖这 6 subkey 拓扑。LLM 若按字面"自由文本"理解，可能 emit `"stage_delta": "..."`（string），触发 schema retry。同问题在 [docs/architecture/extraction_workflow.md:405](docs/architecture/extraction_workflow.md#L405)。建议改为"narrative content within stage_delta 的 string/array 子字段"。

**M3** [ai_context/conventions.md:51](ai_context/conventions.md#L51) Cross-File Alignment 表 + [ai_context/decisions.md:393 (#54 Plumbing)](ai_context/decisions.md#L393) 声称 `prompt_builder.py` 应有 `build_factions_keyfigures_prompt`——`grep "^def build_"` 显示该函数**不存在**于 [prompt_builder.py](extraction/persona_extraction/prompt_builder.py)（实际只有 `build_summarization_prompt` / `build_foundation_prompt` / `build_stage_plan_prompt` / `build_candidate_characters_prompt` / `build_baseline_prompt` / `build_world_extraction_prompt` / `build_char_snapshot_prompt` / `build_char_support_prompt` / `build_scene_split_prompt`）。功能并入 `build_baseline_prompt`（与 fixed_relationships / identity / target_baseline / manifest 同一次 LLM call，per `baseline_production.md` 「产出 1」段）——属于决策定稿与实现落地的命名漂移；要么决策/约定改名跟上实现，要么再补一次拆 prompt。

**M4** [ai_context/requirements.md:103-107](ai_context/requirements.md#L103-L107) §9 Extraction 摘要写"ingest → chapter summarization → global analysis (identity merge → **world overview** → stage plan → candidates → baseline production)"——把 Phase 1 描述成串行链且把 baseline production 收尾在 Phase 1。决策 #52 已把 Phase 1 拆成 3 lane 并行（foundation / stage_plan / candidate_characters，无 world_overview）；决策 #54 把 baseline 明确为 **Phase 2**。ai_context/requirements.md 是 session-start 顺序中第 3 个读的文件，错印会塑造下游 AI 的 Phase 1/2 心智。

**M5** [ai_context/decisions.md:56-57](ai_context/decisions.md#L56-L57)（决策 #11d）写"`stage_delta` stays free-text (no structural changed/removed/added upgrade in this round)"——post-#55 已经依赖 6 subkey 结构化形态做 sub-lane mutex；schema 也是结构化对象。决策表 wording 与现行 schema 矛盾，与 M2 同根源。

**M6** [docs/todo_list_archived.md:93,98,103,133](docs/todo_list_archived.md#L93) 含真实作品名"<work_id>"。`feedback_no_specific_refs_in_docs` memory + `conventions.md` §Generic Placeholders 规定 canonical docs 不带真实命名；豁免清单是 `works/` / `sources/` / `logs/change_logs/` / `logs/review_reports/` / git commit messages。`docs/todo_list_archived.md` 没在豁免之列，但 archived 的归档性质类似 logs/。**Open Question OQ2**：明确把 `docs/todo_list*.md` 纳入豁免，还是脱敏 4 处？

**M7** [extraction/repair/fixers/file_regen.py:120,152-153](extraction/repair/fixers/file_regen.py#L120) 内注释 "the orchestrator's 3-sub-lane parallel re-extract + merge path"——决策 #55 是 4 sub-lane。行为不受影响（callback opaque），但代码内文档与 M1 同样误导后续维护者按 3 数算 timing/cost。

**M8** [extraction/persona_extraction/cli.py:128](extraction/persona_extraction/cli.py#L128) `--end-stage` help 文字 `"0 = baseline only"` 是 Phase 3 语义；但 Phase 4 standalone 路径 [cli.py:242](extraction/persona_extraction/cli.py#L242) 把 `end_stage=args.end_stage or 0` 给 `_collect_chapters`，而 `_collect_chapters` 的 `if end_stage > 0` 判断让 0 = "no limit"。同一 flag 在两个 phase 语义相反：Phase 3 `--end-stage 0` = baseline-only，Phase 4 standalone `--end-stage 0` = 全跑所有章。foot-gun，help 文案误导。

**M9** [extraction/persona_extraction/lifecycle/progress.py:794-815](extraction/persona_extraction/lifecycle/progress.py#L794-L815) `Phase3Progress.reconcile_with_disk` R3 sweep 只扫 `.partial/{stage_id}_*.json`，**没有平行扫描** `analysis/progress/.partial_prev/{char_id}/`。决策 #55 的 slice lifecycle 依赖 orchestrator `_clear_prev_snapshot_slices` 在 success / failure 路径清；hard-stop 路径不清（[orchestrator.py:1006-1009](extraction/persona_extraction/orchestrator.py#L1006-L1009) 显式注释解释）。若 prev 阶段在两次 run 之间被 repair 重写，下一次 stage 启动前的 `_clear_prev_snapshot_slices` + `_write_prev_snapshot_slices` 兜底（[orchestrator.py:951-952](extraction/persona_extraction/orchestrator.py#L951-L952)）能保证 freshness 对**当前** stage；但**跨 stage** 的 stale slice 在 prev_stage_id 不再被运行时永久堆积。仅磁盘累积，不破坏正确性。

### Low

**L1** [schemas/world/foundation.schema.json:5](schemas/world/foundation.schema.json#L5) description 含"原 `schemas/analysis/world_overview.schema.json` 已删除，内容合并入本 schema"——违反 `conventions.md` §Generic Placeholders 第 4 条"no history narration（'renamed from / 已废弃 / legacy'）in canonical docs"。同问题 [schemas/README.md:9](schemas/README.md#L9) "原 `world_overview` 已删除"。Provenance 应只活在 `decisions.md`。

**L2** [docs/architecture/schema_reference.md:13](docs/architecture/schema_reference.md#L13) "Phase 1 三件套入 git" header 在 `analysis/` 行——决策 #54 后 foundation 已迁到 `world/`，`analysis/` 实际只剩 `stage_plan` + `candidate_characters` 两件被跟踪。文字暗示三件都在 `analysis/`，与同表第 9 行（已正确写 foundation 在 `schemas/world/`）矛盾。

**L3** [orchestrator.py:732-746](extraction/persona_extraction/orchestrator.py#L732-L746) `_run_recovery_sweep` hard-stop 路径在 `recovery_attempted=True` 标记前 raise（line 732-737 早于 line 746）。设计上正确（hard-stop 不算"试过失败"，下次 resume 应该再 sweep）但未在决策 #49 文档中说明。

**L4** [extraction/persona_extraction/lifecycle/progress.py:178-192](extraction/persona_extraction/lifecycle/progress.py#L178-L192) `PipelineProgress.save()` 无条件写 `schema_version: _SCHEMA_VERSION (=2)`。未来若产生 v3 文件，被本版本 load 后再 save 会**静默降级**到 v2。short term 无影响，long-term forward-compat trap。

**L5** [orchestrator.py:3268-3277](extraction/persona_extraction/orchestrator.py#L3268-L3277) `commit_stage` 把"nothing-to-commit / scope-leak refusal / git commit non-zero exit"三种语义都坍缩成 `StageState.FAILED + error_message = "git commit produced no object"`。运维排查时把 scope-leak 错认成 missing artifacts。

**L6** [users/_template/relationship_core/manifest.json](users/_template/relationship_core/manifest.json) 在多处用占位符（`{user_id}` / `{stage_id}`），但 `trust_level` / `intimacy_level` / `dependence_level` 给的是具体整数 `0`。schema validate（minimum 0, maximum 100）放过，但模板风格不一致——要么全占位、要么明确"0 是默认锚"。

**L7**（已并入 M8）

---

## Alignment Summary

整体高度对齐。三大热补丁（#55 / #56 / #57）落地完整，所有 Cross-File Alignment table 关键行（51 / 52 / 53）的目标文件都做了对应更新，**唯独 M3 一处函数名漂移**——`build_factions_keyfigures_prompt` 计划存在、实际未拆出。

最对齐：schemas/character/stage_snapshot 全字段表 / snapshot_merge.py FIELD_ALLOCATION / character_snapshot_extraction.md lane_scope 注入 / docs/architecture/extraction_workflow.md §6.2 表 / ai_context/architecture.md：四方说法一致。

最不对齐：**sub-lane 数 "3 vs 4"** 这条非常局部的术语——schemas/README.md / file_regen.py 注释 / 决策 #11d 的 stage_delta free-text 措辞，都是 #55 收尾时的扫尾遗漏。

实现 vs 决策最不一致的一块：**rate-limit hard-stop 路径的外层 pool cancel_futures 缺失**（H1）——决策 #55 R2 只把模式应用在 sub-lane sub-executor，"snitch up" 没传到 4-5 个 sister 外层 pool；与决策口径完全不符。

---

## Residual Risks

1. **N ≥ 3 角色峰值并发**（决策 #55 + todo `T-PHASE3-PEAK-CAP-N-CHARS`）— 当前 cap = 12 不够覆盖 N=3 (16) / N=4 (21)；RateLimitController 兜底但**不是设计意图**。当前作品 N=2 安全，扩到 N=3 后会频繁触发 rate-limit pause。
2. **Phase 2 未接 repair** — 单次 `run_with_retry` + `validate_baseline` + length-tolerance + 失败 `sys.exit(1)`，无 L1/L2/L3 fixer 自愈。todo `T-PHASE2-REPAIR-AGENT` 已登记。
3. **light_novel 模式 `chapter_count=1` schema-invalid** — 决策 #27m 已知 trade-off，todo `T-LIGHTNOVEL-SCHEMA-ONEOF` 已登记。若未来外部工具加入对 light_novel 产物的 schema 校验需切到 oneOf + structure_mode dispatch。
4. **Simulation engine 仍是设计** — `simulation/` 全 Markdown 无 .py 实现；运行时尚未存在。current_status.md 已声明。
5. **schemas/README + foundation.schema 描述里的"已删除"provenance** —— 单条 L1 看是小事，但说明 decision provenance 仍在向 canonical 层渗漏；下一轮 /go 不补这块的话，会持续小幅度漂移。

---

## Open Questions / Ambiguities

**OQ1** "stage_delta 自由文本"在 prompt 与决策 #11d 里是**故意的简称**（指 sub-field 内容是叙述性 text）还是 #55 前的真遗留？建议口径统一为"stage_delta 是结构化对象，sub-field 内容可自由叙述"，prompt 拆开举两条 char_decision / char_social 各自该写哪 3 个 subkey。

**OQ2** `docs/todo_list_archived.md` 含真实作品名（M6）—— 算不算 `logs/` 类的归档豁免？建议在 `conventions.md` §Generic Placeholders Exempt 行明确把 `docs/todo_list_archived.md` 写进豁免（或仍要求脱敏）。

**OQ3** `build_factions_keyfigures_prompt`（M3）—— "整合到 build_baseline_prompt 单次 LLM call"是决策 #54 修订段（2026-05-11）已采用的最终形态吗？若是，conventions.md 第 51 行 + decisions #54 Plumbing 列表两处的函数名应该删/改；若否，需要拆出来。

**OQ4** Cancel-futures pattern（H1）—— 全局加一个 `_cancel_pool_and_raise(pool, exc)` helper 集中所有外层 pool，还是 5 个 site 各自 `try/except RateLimitHardStop: pool.shutdown(wait=False, cancel_futures=True); raise`？前者维护更稳，后者改动小。

---

## Recommendations

仅供参考；用户拍板优先。

- **H1**: 建议**修**。加 helper 或 5 个 site 各自补 `cancel_futures=True`。决策 #55 R2 已是契约，复用模式即可。Phase 3 + repair pool 优先（hard-stop 路径最频繁）。
- **M1**: 建议**修**（一行改）。schemas/README.md:12 `3 sub-lane` → `4 sub-lane`，顺手列出 4 个 sub-lane 名字。
- **M2**: 建议**修**。character_snapshot_extraction.md 4 处 "stage_delta 自由文本" + extraction_workflow.md:405 改为"stage_delta 是结构化对象，sub-field 内容是叙述性 text"；同时把 6 subkey 在 prompt 里枚举，让 LLM 看到 sub-lane allocation。
- **M3**: 建议**确认 + 改文档**（OQ3）。若整合方案是最终形态，conventions.md:51 + decisions #54 Plumbing 删掉 `build_factions_keyfigures_prompt`；否则拆出来。
- **M4**: 建议**修**。ai_context/requirements.md §9 重写：Phase 1 = 3 lane 并行（monolithic）/ 2 lane + 程序 stage_plan（light_novel），Phase 2 是独立 baseline，删 "world overview" 旧术语。
- **M5**: 建议**修**（一行）。decisions.md #11d 把 "free-text" 改成 "structured object with narrative sub-field content"，加 forward-ref 到 #55。
- **M6**: 建议**留 todo**（先做 OQ2 决策）。
- **M7**: 建议**修**（一行）。file_regen.py 注释 "3-sub-lane" → "4-sub-lane"。
- **M8**: 建议**修**。cli.py:128 help 文字补 "(Phase 3 only; Phase 4 standalone treats 0 as all)"，或把 Phase 4 路径单独加 `--end-chapter` 区分。
- **M9**: 建议**留 todo 或顺手修**。reconcile_with_disk 加一段 `.partial_prev/` 平行 sweep（与 `.partial/` 同模板）。低优先；磁盘 GC 性质。
- **L1**: 建议**修**（删 2 处 provenance 句）。一致性回归 `conventions.md` 规则。
- **L2**: 建议**修**（一行 wording）。
- **L3**: 建议**跳过**（行为正确，文档完善与否纯锦上添花）。
- **L4**: 建议**留 todo**（forward-compat 性质，触发点远）。
- **L5**: 建议**留 todo**（运维 quality-of-life，未阻塞当前工作流）。
- **L6**: 建议**跳过 或 加注释**。模板风格选择由 user 拍板。
- **OQ1**: 建议**修**（口径决定 M2 / M5 措辞）。
- **OQ2**: 建议**user 拍板**。
- **OQ3**: 建议**user 拍板**（决定 M3 是改代码还是改文档）。
- **OQ4**: 建议**user 拍板**（决定 H1 修法形态）。

---

## False Positives

无显式 false positive。所有 finding 已经 spot-verify（直接 grep / 直接 Read）。Implementation-track 子代理初版回报里曾把 `build_factions_keyfigures_prompt` 缺失定为 "documentation/audit-spec mismatch"，本报告升为 M3 真实漂移（conventions.md + decisions.md 两处明文声明）。
