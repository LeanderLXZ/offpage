**Review 模型**：Claude Opus 4.7（`claude-opus-4-7`）

# /full-review — 2026-05-12 11:25 EDT

四线并行审计（规范线 / 实现线 / 风险线 / 产物线）。本轮触发口令未附带 `<keyword>`，按全仓口径走，重点放在最新两项重构落点 — 决策 #54（foundation 前移）+ 决策 #55（char_snapshot sub-lane 拆分）— 及其在 schema / prompt / 代码 / 文档间的连锁兑现。

---

## Findings

### High

**H1** [automation/persona_extraction/orchestrator.py:869-892](../../automation/persona_extraction/orchestrator.py#L869-L892) — **char_snapshot sub-lane fan-out 与既有并发上限缺乏全局门槛**

决策 #55 在 phase 3 char_snapshot lane 内嵌套 `ThreadPoolExecutor(max_workers=3)`，叠加 phase 3 外层 `n_workers = max(1, len(lanes_to_run))` 与 repair Phase B 的 `repair_concurrency=10`，理论峰值并发 LLM 调用 = `1 + 3*3 (sub-lane) + 3 (support) = 13`（3 角色）或 `21`（5 角色）；repair 阶段叠加 sub_lane_regen 回调时可达 `10 × 3 = 30`。[config.py:99-104](../../automation/persona_extraction/config.py#L99-L104) 自述「Anthropic Opus subscription tolerates ~8-10 concurrent claude -p calls」。无全局 semaphore，只能 `wait_if_paused` 事后补救。生产期可观察到：阶段 1 早期密集 rate_limit pause / probe 误判 overload → `RateLimitHardStop` exit 2。决策 #55 引入 3× 并发未配相应外层降量。**这是本轮最值得优先修的**。

**H2** [automation/persona_extraction/orchestrator.py:867-892](../../automation/persona_extraction/orchestrator.py#L867-L892) — **RateLimitHardStop 会丢弃 sub-lane 已完成成果**

`_run_char_snapshot_sub_lanes` 在 `as_completed` 收到任一 sub-lane 抛 `RateLimitHardStop` 时，进入 except 块 `pool.shutdown(wait=False, cancel_futures=True)` + `_clear_snapshot_partials(...)`，**删掉已成功落盘的 partial**。下次 `--resume` 操作员清完 rate_limit 后，3 个 sub-lane 必须全部重抽。`cancel_futures=True` 对已启动 future 无效（`max_workers=3` + 提交 3 即全部 running），剩余 sub-lane 在自己的 `wait_if_paused` 里继续睡眠，`with` 块的 `__exit__` 隐式 `shutdown(wait=True)` 又会阻塞数小时。叠加 **H1** 的并发风险——hard-stop 大概率正发生在 3× 并发把订阅窗口打满那一刻——这套丢工作的惩罚正好命中 fan-out 想优化的场景。

**H3** [automation/persona_extraction/orchestrator.py:967-973](../../automation/persona_extraction/orchestrator.py#L967-L973) — **合并后 stage_snapshot 写盘非原子**

`final_path.write_text(json.dumps(...))` 直接覆盖；SIGKILL / 磁盘满落在 line 971-973 之间会留下截断 JSON。`verify_lane_output`（[lane_output.py:109-114](../../automation/persona_extraction/lane_output.py#L109-L114)）下次 resume 会捕获并重抽（3× LLM 调用代价），但 partial 清理（[orchestrator.py:977](../../automation/persona_extraction/orchestrator.py#L977)）在 write 之后跑——截断文件 + 已清 partial 双输；同模块的 [`_atomic_write_json`](../../automation/persona_extraction/progress.py#L48-L72) 早已可复用。修复一行：把直写换为 `_atomic_write_json(final_path, payload)`。

### Medium

**M1** [docs/architecture/schema_reference.md:13-16](../../docs/architecture/schema_reference.md#L13-L16) — **schema 子目录文件计数表 post #54 漂移**

索引宣称 `analysis/ = 5 files` / `character/ = 7 files`，磁盘实际 `analysis/ = 4`（决策 #54 删 `world_overview.schema.json`）/ `character/ = 8`（targets_cap 加入）。conventions §Cross-File Alignment row 1 把 schema_reference.md 钉为权威索引，新 agent 跟着 5 文件清单去找 `world_overview` 会扑空，跟着 7 文件清单读不到 `targets_cap.schema.json` 单源 $ref。`ls schemas/analysis | wc -l = 4`、`ls schemas/character | wc -l = 8`。

**M2** [works/README.md:235](../../works/README.md#L235) — **「最小 5 章」与 schema + 全部其他文档冲突**

行 235 写 `（默认目标 10 章，最小 5 章，最大 15 章，可在作品 config 中调整）`；[stage_plan.schema.json](../../schemas/analysis/stage_plan.schema.json) `chapter_count.minimum=8`、[requirements.md:30](../../docs/requirements.md#L30) / [data_model.md:494](../../docs/architecture/data_model.md#L494) / [ai_context/requirements.md:25](../../ai_context/requirements.md#L25) / [decisions.md:91](../../ai_context/decisions.md#L91) 全部「最小 8 章」。用户照此调 config → phase 1 schema gate 死循环。

**M3** [schemas/runtime/scene_archive_entry.schema.json:31](../../schemas/runtime/scene_archive_entry.schema.json#L31) — **`chapter` 描述仍用 pre-`C####` 字面例「0042」+ 无 pattern**

决策 #10a + commit `4a65837` 把全 phase chapter 引用统一为 `^C[0-9]{4}$`；唯独 scene_archive_entry 的 `chapter` 描述写 `4 位零填充，例如 0042`，且 property 本身没 pattern 约束。代码端 [scene_archive.py](../../automation/persona_extraction/scene_archive.py) 写 `C####`，schema 文字会误导后续 agent 倒退到裸数字形态。

**M4** [automation/persona_extraction/snapshot_merge.py:265-270](../../automation/persona_extraction/snapshot_merge.py#L265-L270) — **`failure_modes` 「两 sub-lane 都不写」被 merge 视为硬错，但 schema 标 optional**

`_check_shared_key_coverage("failure_modes", ..., allow_absent_both=False)`。`_validate_partial_fields` 允许 per-lane 不写（[snapshot_merge.py:209-213](../../automation/persona_extraction/snapshot_merge.py#L209-L213)），schema `failure_modes` 非 required。当 LLM 合理判定本 stage 无 failure modes 时（如背景平稳 stage），两 sub-lane 都不写就被判错，整 lane 重抽。对照 `stage_delta` 用了 `allow_absent_both=True`（[snapshot_merge.py:441](../../automation/persona_extraction/snapshot_merge.py#L441)）——同类约束不对称。两条出路：(a) 把 `failure_modes` 改 `allow_absent_both=True`；(b) prompt 强制其中一 sub-lane 必须至少写空字典（与 schema optional 语义打架，不推荐）。

**M5** [automation/persona_extraction/orchestrator.py:614-630](../../automation/persona_extraction/orchestrator.py#L614-L630) — **recovery sweep `RateLimitHardStop` 时不主动取消同伴 future**

`_run_recovery_sweep` 的 `as_completed` 循环里 `except RateLimitHardStop: raise` 让 hard-stop 顺着 `with ThreadPoolExecutor` 出口；`__exit__` 进 `shutdown(wait=True)`，会等其他正在 sleep（含 `wait_if_paused` 数小时）的 chunk 跑完。一次本应"快速终止"的 hard-stop 被拖成数小时。修法：raise 前先 `executor.shutdown(wait=False, cancel_futures=True)`。

**M6** [automation/persona_extraction/orchestrator.py:1023-1034](../../automation/persona_extraction/orchestrator.py#L1023-L1034) — **`sub_lane_regen` 回调未校验 `file_path` 所属 work_id**

回调只查 `stage_id == stage.stage_id` + `character_id in pipeline.target_characters`，未校验路径前缀 `works/{pipeline.work_id}/`。`_CHAR_SNAPSHOT_PATH_RE`（[file_regen.py:52-68](../../automation/repair_agent/fixers/file_regen.py#L52-L68)）也没锚 work_id。多 work 仓库（本仓支持）里若两 work 共用 char_id，跨 work file_path 会被接受 → 写到当前 orchestrator 的 work_root，潜在覆盖他 work 文件。当前 `_collect_stage_files`（[orchestrator.py:1131](../../automation/persona_extraction/orchestrator.py#L1131)）上游已守门，但 defense-in-depth 缺失一行 obvious 检查。

**M7** [automation/persona_extraction/orchestrator.py:2598-2606](../../automation/persona_extraction/orchestrator.py#L2598-L2606) — **`_extraction_output_exists` smart-skip 只验 JSON 可解析，不验 D4 set-equal**

PENDING 分支若发现 per-stage 文件全部 parseable，**直接 mark 全 lane 完成 + transition EXTRACTED 不重抽**。如果旧 stage_snapshot 文件 schema-valid 但语义对不上当前 `target_baseline.json`（例如 phase 2 重抽过 baseline 后没清 stage_snapshot），merge 期的 D4 set-equal 不再被触发；只能等 repair_agent `TargetsKeysEqBaselineChecker` 接力——而 smart-skip 本身就跳过了 repair。

**M8** [ai_context/decisions.md:46](../../ai_context/decisions.md#L46) — **决策 11d 标题用 `**4-piece character baseline deprecated.**` 违反同文 MAINTENANCE 规则**

文件顶部 `MAINTENANCE` 行 6 + [conventions.md:111](../../ai_context/conventions.md#L111) 都禁止 "legacy / deprecated / formerly / renamed from" 标题语；这是 ai_context 内唯一在标题位写 "deprecated" 的决策。grep 仓库找 stale 引用的 agent 会被这条假阳性反复打住。改成「current = voice / behavior / boundary state inlined in stage_snapshot; failure_modes inlined」即可。

**M9** [works/README.md:44-50](../../works/README.md#L44-L50) — **character canon 树遗漏 `memory_digest.jsonl` 与 `extraction_notes/`**

树只列 `identity.json` / `target_baseline.json` / `memory_timeline/` / `stage_catalog.json` / `stage_snapshots/`。缺：(a) `canon/memory_digest.jsonl`（[data_model.md:332](../../docs/architecture/data_model.md#L332) 明列、`post_processing.generate_memory_digest` 实际产出）；(b) `canon/extraction_notes/{stage_id}.jsonl`（决策 #25a，[schema_reference.md:500](../../docs/architecture/schema_reference.md#L500) 索引、`repair_agent/notes_writer.py` 写）。world 侧同样缺 `world/extraction_notes/`。把 README 当目录蓝本的读者会少认两类已 tracked 路径。

**M10** [works/README.md:55-60](../../works/README.md#L55-L60) — **`analysis/progress/extraction.log` 路径与实际布局不一致**

README 树写 `extraction.log` 直接在 `analysis/progress/` 下，行 183 重复；实际代码（[automation/README.md:290](../../automation/README.md#L290) + 本地 work 样本）写到 `progress/extraction_logs/extraction.log{,.1,.2}` rolling 形态。也漏 `repair_logs/` 与 rate-limit `.lock` 子目录。`progress/` 整棵被 `.gitignore` 屏蔽（行 7），无 tracking 漂移，但文档蓝本误导。

**M11** [automation/persona_extraction/orchestrator.py:441-457](../../automation/persona_extraction/orchestrator.py#L441-L457) — **`char_snapshot_sub_lanes` 取值锁定在 orchestrator 初始化时**

`self.char_snapshot_sub_lanes` 在 `__init__` 一次性从 `get_config()` 读完；多 stage 单次 run 内 `force_reset_to_pending` 重入 `run_extraction_loop` 不重建 orchestrator → 跨 stage flag 静态。CLI flag 也同样 sticky。决策 #55「light_novel 用户按 work 手切」隐含 per-work 行为——但代码上只在新调用生效。如果某 light_novel work 用户没显式 `--no-char-snapshot-sub-lanes`，会按 toml 默认 `true` 付 3× 启动开销。

**M12** [automation/persona_extraction/rate_limit.py:648-663](../../automation/persona_extraction/rate_limit.py#L648-L663) — **`_account_slept` 多 lane 入门时计时漂移**

lane A 在 t=0 入 `wait_if_paused` sleep 1800s，lane B 在 t=1000 入仅剩 800s；两者都在 t=1800 醒。先抢到 `_account_lock` 的累加生效，决定 `slept` = 800 或 1800。`--max-runtime` 对 pause 时间最多准估，最少估漏一半。`--max-runtime` 是 advisory，定级 M。

**M13** [automation/persona_extraction/snapshot_merge.py:39-42](../../automation/persona_extraction/snapshot_merge.py#L39-L42) — **MergeError 失败路径 docstring 把清理职责挂错到 `reconcile_with_disk`**

docstring 写 `MergeError → 整 lane 重抽，PENDING/ERROR partial 由 progress.reconcile_with_disk 清`。实际 orchestrator 在 [orchestrator.py:894-984](../../automation/persona_extraction/orchestrator.py#L894-L984) 的失败/hard-stop 路径里 7 处显式 `_clear_snapshot_partials(...)`；`reconcile_with_disk` 只负责 `--resume` 时孤立 partial 收尾。维护者若信 docstring 删掉显式清理 → 重抽被 stale partial 污染。

**M14** [works/README.md:69-74](../../works/README.md#L69-L74) — **`indexes/` 树列字段没标"尚未启用"**

`load_profiles.json` / `character_index.json` / `location_index.json` / `event_index.json` / `relation_index.json` 全列入推荐树。[data_model.md:176](../../docs/architecture/data_model.md#L176) 明示「加载 profile / FTS5 / embedding 索引，尚未启用」；automation 无任何代码产生它们，4 项无 schema。`world/cast/character_index.json` 同样情况（works/README 行 38-40, 103）。

### Low

**L1** [ai_context/requirements.md:81-82](../../ai_context/requirements.md#L81-L82) — bound 数字 `15` 在 ai_context 字面复述，决策 #27b（bounds-only-in-schema）要求只指向 schema 文件。

**L2** [prompts/review/手动补抽与修复.md:33-35](../../prompts/review/手动补抽与修复.md#L33-L35) — 同文 prompt 字面写 `150–200 字 / 30–50 字 / 50–100 字 / 50–80 字`，对应 schema 一旦放宽会静默漂移；姐妹文件 `数据包审校.md` 已用「具体见 `schemas/...`」正确写法。

**L3** [works/README.md:66-67, 199-200](../../works/README.md#L66-L67) + [docs/architecture/data_model.md:488-489](../../docs/architecture/data_model.md#L488-L489) — `analysis/evidence/` + `analysis/conflicts/` 列在标准树但全 phase 无 writer；决策 #27c + #25a 后真实归属是 `{entity}/canon/extraction_notes/{stage_id}.jsonl`。

**L4** [schemas/world/world_stage_snapshot.schema.json:105](../../schemas/world/world_stage_snapshot.schema.json#L105) — `location_changes` description 用「旧地点」字面（语义本是 in-story old，无 software 历史含义）；conventions §Cross-File Alignment 鼓励 grep `旧`，留这一处会反复触发审计假阳性。

**L5** [automation/persona_extraction/prompt_builder.py:122-126](../../automation/persona_extraction/prompt_builder.py#L122-L126) + `:350-351` + [orchestrator.py:123-125](../../automation/persona_extraction/orchestrator.py#L123-L125) + `:1582-1584` + `:1679-1681` — 5 处 in-code 注释用 `renamed from / moved from … to` 形态描述 #54 改名（`world_overview` → `foundation`）。冗余且违反 conventions「describe current only」。

**L6** [automation/persona_extraction/consistency_checker.py:378-383](../../automation/persona_extraction/consistency_checker.py#L378-L383) — 构 `curr_rels` mapping 时 fallback 到 `target_label`。`target_character_id` 是 D4 set-equal 锚（#13），到这一步若仍缺只能说明上游违约；用 `target_label` 当 dict key 会把 prev/curr delta 比对错位。

**L7** [automation/persona_extraction/snapshot_merge.py:16-37](../../automation/persona_extraction/snapshot_merge.py#L16-L37) — module docstring 列「5 道 merge hard gate」，gate 5 实为反向 anti-rule（per #11f 不查 entry 数 ≥ prev），4 正 + 1 反，"5" 措辞误导。

**L8** [automation/persona_extraction/orchestrator.py:452](../../automation/persona_extraction/orchestrator.py#L452) — `char_snapshot_sub_lanes` 三态（None / True / False）只有 CLI 行注释处文档化；未来调用者需要知道 None / False 区分。

**L9** [automation/persona_extraction/rate_limit.py:403-435](../../automation/persona_extraction/rate_limit.py#L403-L435) — 3 sub-lane 并发各自 `record_pause` → `merged_count` 增 3 → 同一 incident 日志被放大 3×（行 421-425）。无正确性问题，仅日志噪音。

**L10** [automation/persona_extraction/orchestrator.py:894-902](../../automation/persona_extraction/orchestrator.py#L894-L902) — sub-lane error joiner `"; ".join(...)` 无总长上限；3 sub-lane 各 ~KB 级 stderr 时合并 ~30KB 进 `stage.error_message`，[orchestrator.py:2686](../../automation/persona_extraction/orchestrator.py#L2686) 路径不截断（对照 `commit_stage` 失败路径行 2932 截到 2000）。

**L11** [automation/persona_extraction/snapshot_merge.py:322-362](../../automation/persona_extraction/snapshot_merge.py#L322-L362) — `_validate_targets_set_equal` 拒 `relationships=None` 但接 `relationships=[]`，路径自洽，仅作 OQ 留底。

**L12** [automation/persona_extraction/orchestrator.py:1078-1083](../../automation/persona_extraction/orchestrator.py#L1078-L1083) — `_clear_snapshot_partials` 把 `OSError` 吞成 warning；只读文件系统的真异常会接力到 `final_path.write_text` 才裸抛，没就近 fail loudly。

**L13** [automation/repair_agent/fixers/file_regen.py:52-53](../../automation/repair_agent/fixers/file_regen.py#L52-L53) — `_CHAR_SNAPSHOT_PATH_RE` 锁 `S[0-9]{3}` 3 位。`stage_num >= 1000` 时不匹配 → silent fallback 到默认全文 regen 跳过 sub-lane。理论性。

**L14** [automation/persona_extraction/cli.py:267-291](../../automation/persona_extraction/cli.py#L267-L291) — `--background` validator 读 `pipeline.json` 无锁；`_atomic_write_json` 保证 全/旧 二态，定级 L。

**L15** [automation/persona_extraction/post_processing.py:165-168](../../automation/persona_extraction/post_processing.py#L165-L168) + `:362-366` — JSONL digest 写盘 `open("w")` 截断式；SIGKILL 中段 → 截断 + 后续 read 静默 drop malformed line → 历史 stage digest 丢。同 H3，应统一走 `_atomic_write_json` 形态（或对应 JSONL 版本）。

**L16** [automation/persona_extraction/orchestrator.py:2078-2098](../../automation/persona_extraction/orchestrator.py#L2078-L2098) — character 选择 prompt 的 EOFError fallback 在 recommended_ids 为空时再 `sys.exit(1)`；daemon 路径丢上下文 scrollback。

**L17** [works/README.md:30-32](../../works/README.md#L30-L32) — `locations/{location_id}/identity.json` + `state_snapshots/{state_id}.json` 列出无 schema；决策 #27c 把 location 信息内联到 `world_stage_snapshot.{timeline_anchor, location_anchor}` + `foundation`。

**L18** [works/README.md:25-26](../../works/README.md#L25-L26) — `state/world_state_snapshots/{state_id}.json` 同上无 schema；现状由 `world_stage_snapshot.schema.json`（stage_id 键）覆盖。

**L19** [users/README.md:131-135](../../users/README.md#L131-L135) — `conversation_library/archive_index.jsonl` 无 per-entry schema；`transcript.jsonl` / `turn_journal.jsonl` / `turn_summaries.jsonl` / `memory_updates.jsonl` 同上未硬约束。scaffold 阶段可接受，留 todo。

---

## Alignment Summary

| 层 | 对齐情况 | 说明 |
|---|---|---|
| 决策 #54 (foundation 前移) | ✅ 强对齐 | schema / prompt / 代码 / docs 主路径全部已搬迁；唯一漂移在 5 处代码注释（L5）的"renamed from"风格残留 |
| 决策 #55 (char_snapshot sub-lane) | ⚠️ 字段层强 / 行为层有缺口 | `FIELD_ALLOCATION ∪ PROGRAM_INJECTED_FIELDS` == schema 顶层 properties 全等；但 (a) 嵌套并发无外层降量 [H1]、(b) hard-stop 丢工作 [H2]、(c) 非原子写盘 [H3]、(d) `failure_modes` absent 双不对称 [M4]、(e) 多文档站点（works/README、ai_context/requirements）尚未引用 sub-lane 概念（OQ1） |
| schema vs 文档索引 | ⚠️ 中等漂移 | schema_reference.md 子目录计数表 [M1]、scene_archive_entry chapter 描述 [M3]、works/README directory tree [M9 / M10 / M14] 三处需修 |
| ai_context vs docs | ✅ 高度一致 | 唯一显著点是 decisions.md 11d 标题用词违反自家规则 [M8]；其他 §1–§12 章节级一致 |
| prompts/ (manual) | ✅ 基本一致 | `数据包审校.md` 严格遵 bounds-only-in-schema；`手动补抽与修复.md` 一处显式 bounds 残留 [L2] |
| 产物 vs 规范 | ✅ 高一致 | works/README directory tree 与本地 work 实际产出有 3 处轻度偏差 [M9 / M10 / L17 / L18]；用户模板按 placeholder 设计预期不通过 schema validate，符合契约 |
| `.gitignore` | ✅ 覆盖完整 | character snapshot `.partial/` 已加（#55）；world 侧无 sub-lane 故无需对称项 |

**真相优先级**：schema 文件 > docs/requirements.md > docs/architecture/* > ai_context/* > README 文件。当 [M2] 「最小 5 章」与 schema 「min 8」冲突时，以 schema 为准。

---

## Residual Risks

- **跨 character baseline_keys 无版本号**：[H1] / [H2] / [M7] 的根因部分在于 `target_baseline.json` 一旦在 phase 2 重抽，老的 stage_snapshot 文件 schema-valid 但 D4 set-equal 失效，目前只靠 repair_agent 接力。增加 baseline 写入时间戳 / hash 让 stage_snapshot 携带 baseline_fingerprint，可让 smart-skip 主动 invalidate。**推断**性建议，未确认是否值当。

- **Phase 2 `key_figures` raw 名 → character_id 替换无 schema 后置门**：[orchestrator.py:1950-1960](../../automation/persona_extraction/orchestrator.py#L1950-L1960) 单次 `run_with_retry` 后没有显式 `jsonschema.validate(foundation.json, foundation.schema.json)` 作 last-mile gate。`validate_baseline`（[validator.py:201-217](../../automation/persona_extraction/validator.py#L201-L217)）加载了 schema 但路径调用未深查。下一轮值得 spot-check。**推断**。

- **`works/<work_id>/` 本地未跟踪产物**：抽样 1 个 chunk_001 通过当前 schema validate；migration tail 风险目前可控。但完整 27 chunk × 7 phase × N stage 未逐项校验，留作残余风险。

- **light_novel 模式 sub-lane 并发的 cost-benefit 实测缺失**：决策 #55 把开关默认值定为 `true`，理由是 monolithic 模式收益 > 开销，light_novel 模式由用户手切。没有跑过 A/B 数据；M11 暴露的"flag 静态"问题让"手切"在 multi-stage 单 run 内不生效。

- **`extraction_notes/` 写但 docs tree 没列**：[M9] 修后 works/README 蓝本完整；当前实际跑出来的 notes 文件未被 README 提示存在，新接手用户可能误删 / 漏 commit。

- **多 work 跨污染兜底单点**：[M6] 当前唯一防线是上游 `_collect_stage_files` 不传跨 work 路径。无 defense-in-depth 二层守门。

---

## Open Questions / Ambiguities

**OQ1** `ai_context/requirements.md` 完全没提决策 #55 sub-lane 概念（只 §11 抽象到「Phase 3 stage loop」）；commit `7530eed` 明确「不补 ai_context/requirements.md §11 sub-lane mention（L4，按 /post-check 建议保持 shorter is better 极简索引原则）」。若此为终态，[conventions.md Cross-File Alignment 表 row 7](../../ai_context/conventions.md#L52) 现在指向 `docs/requirements.md §9.3 + ai_context/decisions.md #55`——与 row 现状一致，但 row 7 没列 `ai_context/requirements.md`，**确认这是有意为之**还是 row 漏列。

**OQ2** `schemas/runtime/scene_archive_entry.chapter` 是否有意保留宽松形态（允许 `C0042-C0043` 跨章节 range）？若是，建议加 `pattern: "^C[0-9]{4}(-C[0-9]{4})?$"` 明示意图；若否，描述应收紧到单 chapter 形态。决策 #10a 没就 range 形态拍板。

**OQ3** works/README.md「最小 5 章」是 #27m 前的草稿残留，还是有意保留 per-work config override 余地？schema `chapter_count.minimum=8` 是硬门，配置无法低于 8。

**OQ4** sub-lane 失败日志 `lane_name=f"char_snapshot:{cid}:{sub_lane}"`（[orchestrator.py:849](../../automation/persona_extraction/orchestrator.py#L849)）：同 work 同 char 3 sub-lane 共前缀，`failed_lane_log` 的文件名冲突行为是否在 `_log_lane_failure` 内做了区分？

**OQ5** `_run_char_snapshot_sub_lanes` 行 867 入口先 `wait_if_paused`，再启 3 sub-lane；如其中一 sub-lane 启动几秒后撞 rate_limit，3 sub-lane 各自 `record_pause` 合到同 window。设计意图是"3 sub-lane 同步睡过去 → 醒后全部 retry（不消耗 retry slot per [llm_backend.py:657](../../automation/persona_extraction/llm_backend.py#L657)）"？

**OQ6** `prior_attempt_context` 在 lifecycle 2 时被广播到 3 sub-lane（[orchestrator.py:232](../../automation/persona_extraction/orchestrator.py#L232)），即使 lifecycle 1 失败只与 `voice_state`（char_expression 范畴）相关。是有意"让 LLM 自己判定 scope 相关性"还是缺一层 per-sub-lane 过滤？600 char × 3 重复占 context 预算。

**OQ7** smart-skip ([M7] / [orchestrator.py:2598](../../automation/persona_extraction/orchestrator.py#L2598)) 只查 JSON parseable；带 sub-lane 后 merge 时的 D4 set-equal 无法对磁盘文件复查。repair_agent `TargetsKeysEqBaselineChecker` 是否覆盖此漏洞？（本轮未进 repair_agent 全路径审计。）

**OQ8** `_clear_snapshot_partials` 在 `_run_char_snapshot_sub_lanes` 内 7 个调用点：launch 前、R2 hard-stop、5 处失败路径、success merge 后。是否值得收敛为 `try/finally` 模式以防未来分支增加时漏调？

**OQ9** [orchestrator.py:887](../../automation/persona_extraction/orchestrator.py#L887) `pool.shutdown(wait=False, cancel_futures=True)`：`max_workers=3` + 提交 3 时 future 全 running，`cancel_futures=True` 是 no-op。是有意等同伴跑完，还是需要 backend 端 cancellation 机制（[H2] 关联）？

---

## Recommendations

仅供参考，用户拍板优先；不超出本轮 review scope 扩功能、不过度工程。

- **H1** — 建议修：在 phase 3 主 ThreadPoolExecutor（[orchestrator.py:2652](../../automation/persona_extraction/orchestrator.py#L2652)）启动前根据 `char_snapshot_sub_lanes` 把 `n_workers` 限制为 `max(1, total_concurrency // sub_lane_factor)`；或引入 `phase3.global_concurrency` 顶门，sub-lane 与 support 共享。这是本轮唯一已落地 3× 并发但未配外层降量的实际生产风险。
- **H2** — 建议修：把 `_clear_snapshot_partials` 从 `RateLimitHardStop` 路径移除（partial 保留供下次 resume），并在 hard-stop 路径加 `_log_lane_failure` 而不删 partial；ThreadPoolExecutor 改 `shutdown(wait=False, cancel_futures=True)` 后立即 raise。同时考虑给 sub-lane 也加 `wait_if_paused` 入口前的 cancellation 检查。
- **H3** — 建议修：`final_path.write_text(...)` → `_atomic_write_json(final_path, payload)`。一行改动，复用现成 helper。
- **M1** — 建议修：把 schema_reference.md 子目录计数表删除（或自动生成）；或直接更新 `4 / 8` 当前值。`5 file` / `7 file` 是死字段，从 #54 后就漂移。
- **M2** — 建议修：works/README.md `最小 5 章` → `最小 8 章`，与 schema 对齐。OQ3 同时关闭。
- **M3** — 建议修：scene_archive_entry chapter 描述例改 `C0042` / `C0042-C0043`，可选加 pattern。OQ2 同时关闭。
- **M4** — 建议修：snapshot_merge.py `failure_modes` 改 `allow_absent_both=True`（对照 `stage_delta` 已是此形态）。或在 prompt 端强制至少一 sub-lane 写空字典（不推荐，与 schema 打架）。
- **M5** — 建议修：recovery sweep raise 前 `executor.shutdown(wait=False, cancel_futures=True)`。3 行改动。
- **M6** — 建议修：sub_lane_regen 回调加 `file_path.is_relative_to(work_root)` 检查；同 [file_regen.py:52](../../automation/repair_agent/fixers/file_regen.py#L52) 正则锚入 work_id 段。
- **M7** — 建议留 todo：smart-skip 加 baseline_fingerprint 校验需要 cross-phase 元数据，工程量超出本次 review scope。先在 docs 注明"smart-skip 不重检 D4，请勿手改 target_baseline 后 --resume"。
- **M8** — 建议修：decisions.md 11d 标题改写为"voice / behavior / boundary state inlined in stage_snapshot; failure_modes inlined top-level field"——描述当前事实，不写 deprecated。
- **M9** — 建议修：works/README.md character canon 树补 `memory_digest.jsonl` 与 `extraction_notes/`；world 侧补 `extraction_notes/`。
- **M10** — 建议修：works/README.md 树把 `extraction.log` 改 `extraction_logs/extraction.log{,.1,.2,...}`，附 `repair_logs/`、`rate_limit_pause.lock` 等。或直接指向 automation/README.md §6.x 不重复。
- **M11** — 建议留 todo：flag 跨 stage 静态属于"配置在 run 边界生效"的合理设计；M11 文档化即可（在 ai_context/decisions.md #55 末段加一句"flag 在 orchestrator init 一次性捕获"）。
- **M12** — 建议留 todo：`_account_slept` 计时漂移属 advisory 字段，不阻塞，留作 future hardening。
- **M13** — 建议修：snapshot_merge.py docstring 行 39-42 把"由 progress.reconcile_with_disk 清"改为"由 orchestrator 失败路径 `_clear_snapshot_partials` 显式清；reconcile_with_disk 只负责 --resume 时孤立 partial"。
- **M14** — 建议修：works/README.md `indexes/` 树后加注「尚未启用 — 见 docs/architecture/data_model.md §X」，与 data_model.md 对齐。
- **L1** — 建议跳过：bound `15` 在 ai_context 字面复述属"对索引读者友好"，与 #27b 精神冲突但工程价值低。
- **L2** — 建议修：bounds 改指 schema 文件，对齐姐妹 prompt `数据包审校.md`。
- **L3** — 建议留 todo：`evidence/` + `conflicts/` 在 works/README + data_model 都列；要么删，要么改成"reserved for future use"。
- **L4** — 建议跳过：「旧地点」语义合法，假阳性而已。
- **L5** — 建议留 todo：5 处代码注释「renamed from」违反 conventions「current only」；本轮工程价值低，未来涉及 prompt_builder / orchestrator 内同段编辑时顺手清。
- **L6** — 建议修：consistency_checker.py `target_label` fallback 改为 raise / log + skip；defensive 但不应当默认 dict key 用。
- **L7** — 建议修：snapshot_merge.py docstring「5 道 merge hard gate」→「4 道正向 gate + 1 道反向 anti-rule」。
- **L8** — 建议跳过：三态 None/True/False 设计正确，注释清晰度低优先级。
- **L9** — 建议留 todo：日志放大 3× 的修法是 record_pause 内 dedupe 同 lane prefix；非紧急。
- **L10** — 建议留 todo：error joiner 截断逻辑统一到 commit_stage 已有的 2000 char cap。
- **L11** — 建议跳过：OQ 留底。
- **L12** — 建议修：`_clear_snapshot_partials` OSError 路径 raise 而非 warning，让真异常 fail loudly。
- **L13** — 建议跳过：1000+ stage 理论值；本仓 STAGE_MAX = 15。
- **L14** — 建议跳过：`--background` validator 无锁场景对齐 atomic write 已 sufficient。
- **L15** — 建议修：post_processing.py JSONL 写盘改原子（`tempfile.NamedTemporaryFile + os.replace`），同 H3 形态。决策 #50 数据丢失场景由此封口。
- **L16** — 建议跳过：daemon 路径 fall-through 到 sys.exit(1) 设计正确，scrollback 丢失属 daemon 限制本身。
- **L17 / L18** — 建议留 todo：works/README.md location 树要么删要么标"内联到 world_stage_snapshot"，与决策 #27c 一致。
- **L19** — 建议留 todo：user 端 jsonl 文件 schema 化作 future hardening，scaffold 阶段可接受。
- **OQ1** — 推荐用户确认 ai_context/requirements.md §11 "Phase 3 stage loop" 抽象级是否终态；如是，conventions.md Cross-File Alignment row 7 应显式注明"sub-lane 细节不在 ai_context/requirements.md 同步"。
- **OQ2** — 推荐用户拍板 scene_archive_entry chapter 是否允许范围形态。
- **OQ3** — 已并入 M2。
- **OQ4–OQ9** — 行为/语义判断，需要用户在跑实际多角色多 stage 流程时观察并校准。

---

## Review 元数据

- 模型：claude-opus-4-7（Claude Opus 4.7 with 1M context）
- 触发：`/full-review`（未带 keyword）
- 时间：2026-05-12 11:25 EDT
- 并行审计线：4（规范 / 实现 / 风险 / 产物）
- 总 Findings：H 3 + M 14 + L 19 = 36 条 + 9 OQ
- 仓库分支：`main`，工作区干净（pre-review），git status 仅本 review report 待 commit
- 重点对齐范围：决策 #54 / #55 端到端兑现 + 高频 schema / prompt / 代码三方一致性

发现真正需要现在动手的硬伤集中在 H1 / H2 / H3 三条（决策 #55 落地后的并发 + 工作丢失 + 原子写）；中等漂移以文档为主（schema_reference 计数、works/README directory tree、decisions.md 11d 标题）；low 多为「过去做过、现在留了注释残留」+ 「未来值得收紧但今天不挡路」。
