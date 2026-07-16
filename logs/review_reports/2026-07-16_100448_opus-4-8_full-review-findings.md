# /full-review — 全仓对齐审计

- **Review model**: Claude Opus 4.8 (1M context) (`claude-opus-4-8[1m]`)
- **Date**: 2026-07-16 10:04:48 EDT
- **Branch**: main（HEAD `70dd98b`）
- **Scope**: 全仓。Code 维度分三片（编排/状态机、repair/validation、core/prompts），
  Surface 维度一片（ai_context / docs / schemas / simulation / works / users / README /
  .gitignore）。4 个 sub-agent 并行 + 主循环独立复核。
- **焦点**：决策 #62（repair 去 T3）落地后的首次全仓审计。

## 方法与验证强度

除标注「推断」外，每条 finding 都由主循环**独立读取引用行号**确认；标注「实证」的条目
额外在只读环境下**实跑复现**。本轮未修改任何文件（本报告除外）。

## Findings

### High

**H1** `extraction/persona_extraction/orchestrator.py:3821` — `reconcile_with_disk`
在切到抽取分支**之前**运行，从 `main` 续跑会把全部 COMMITTED stage 进度抹掉。

- **为什么是问题**：`run_full` 在 `orchestrator.py:3821` 调用 reconcile，而
  `create_extraction_branch` 在 `orchestrator.py:3890`。此时 HEAD 在 `main`，stage 产物
  只在 extraction 分支被跟踪（`git ls-tree -r main -- works/` 只有 `works/README.md`），
  工作树里不存在 → `progress.py:754-758` 判定「committed artifacts missing on disk」→
  `clear_lane_states()` + `force_reset_to_pending()` + 清空 `committed_sha`，并在
  `orchestrator.py:3828` **落盘持久化**。
  注意 `_git_object_exists` 查的是跨分支共享的 object DB，故 `sha_ok` 为 True ——
  触发条件纯粹是 `len(existing) < len(all_paths)`，这在 `main` 上必然成立。
  `phase3_stages.json` 因 `.gitignore:8` 忽略 `works/*/analysis/progress/` 而跨分支存活，
  正是这个「进度存活、产物不存在」的组合触发误判。
- **影响范围**：命中所有**干净退出**后的续跑 —— `--end-stage` 前缀跑（README 明确推荐
  「重跑不带 `--end-stage` 来收尾」）、`--max-runtime` 优雅停止、Ctrl+C。只有 SIGKILL
  （HEAD 留在 extraction 分支）幸免，而文档恰把 SIGKILL 描述为异常路径。
  **推断**（未实跑完整链路）：切回分支后文件重现 → `orchestrator.py:3048` smart-skip →
  重跑 PP + 全量 repair（真实 LLM 开销）→ `commit_stage` 空 diff → sha 为空 → FAILED →
  `next_pending_stage`（`progress.py:633-634`）返回 None → 整条流水线 BLOCKED。
- **实证**：构造 COMMITTED stage + 产物缺失 → `{'reverted': 1, 'sha_missing': 1}`，
  state 变 PENDING，sha 被清空。
- **证据**：`orchestrator.py:3815-3828`、`orchestrator.py:3885-3895`、
  `lifecycle/progress.py:754-771`、`cli.py:335-344`（CLI 无 checkout）、`.gitignore:8`。

---

**H2** `extraction/persona_extraction/core/git_utils.py:83-94, 161-169` — git scope
守卫对中文 `work_id` 全线失效，提取产物会被带上 `main`。

- **为什么是问题**：`preflight_check` / `checkout_main` 用未加 `core.quotePath=false` 的
  `git status --porcelain` 解析路径。git 对非 ASCII 路径做八进制转义 + 加引号，
  `fname.startswith("works/{work_id}/")` 恒为 False。
  **同一 bug 已在 `commit_stage`（`git_utils.py:208-215`）被显式修复并写了注释**
  （「without it git octal-escapes ... the `startswith(scope_prefix)` check below would
  always fail」）—— 修复没有同步到另外两个调用点。全文件 `quotePath` 仅此一处。
- **影响范围**：决策 #9 规定中文作品用中文 `work_id`，故这是**主路径**而非边角，且故障
  静默（ASCII 的 `ignore_patterns` 仍能匹配）。
  `checkout_main:169` 的 `if scoped_dirty or (not gs.clean and not scope_paths)` ——
  `scoped_dirty` 恒空、`scope_paths` 非空 → 条件 False → 直接 `git checkout main`，
  未跟踪的 `works/<中文work_id>/.../S###.json` 跟着切到 main。这正是该函数 docstring
  （`git_utils.py:148-152`）声明要防的场景，也直接违反 `conventions.md` §Git
  「main 永不携带真实 work ID、原著小说或提取产物」。`preflight_check` 的 `significant`
  恒空 → 脏树上照常起跑。
- **实证**（临时 repo，中文路径）：
  ```
  默认 porcelain     : ?? "works/\344\270\255\346\226\207\344\275\234\345\223\201/..."  → startswith = False
  quotePath=false   : ?? works/中文作品/analysis/S002.json                            → startswith = True
  ```
- **证据**：`core/git_utils.py:83-94`、`:145-180`、`:208-215`。

---

**H3** `extraction/repair/fixers/source_patch.py:130-136` + `field_patch.py:24-26` —
T2 无复验守卫，且 `$` 锚点 issue 会整体替换全文件；#62 删除的「全文重生成」以 T2 形态复活，
可在报 PASS 的同时把文件写坏。

- **为什么是问题**：三处叠加。
  1. `coordinator.py:108-112` 的 `_build_fixers` 只把 `verify_fn` 传给 T1
     （`LocalPatchFixer`）；T2（`SourcePatchFixer`）没有。`source_patch.py:130-136`
     只要 `apply_field_patch` 不抛异常就 `resolved.add(...)`。而 #62 的
     「apply patch 后立即 scoped 复验，过了才算 resolved（止 self-report-resolved spin）」
     只覆盖 T1 —— 恰恰**最需要复验的判断类问题全部走 T2**：
     `protocol.py:241-247` 把 `semantic` 与 `cross_file` 都路由到 `(2, 2)`。
  2. `field_patch.py:24-26` 的 `if not tokens: return new_value  # root replacement`
     —— json_path 为 `$` 时 LLM 返回值**无任何类型/形状校验地替换文档根**。
  3. 携带 `json_path="$"` 的 issue 恰好路由到 T2：`targets_baseline_missing`
     （`targets_keys_eq_baseline.py:55-64`，cross_file）、`semantic_unavailable` /
     `semantic_unparseable` / `semantic_check_crashed`（`semantic.py:145-204`，semantic）、
     以及 LLM 漏写 json_path 时的默认值（`semantic.py:225`）。
- **影响范围**：语义荒谬 + 数据破坏双重。`targets_baseline_missing` 描述的是**兄弟文件
  缺失**（`target_baseline.json` 不可读），「修法」却是让 LLM 重写本快照全文。
  `semantic_unavailable` 更甚 —— **语义复审后端故障**会触发整份快照被 LLM 覆写。
  放大器：`targets_keys_eq_baseline.py:45-46` 的 `if not isinstance(content, dict): continue`
  对非 dict 内容静默跳过，被写坏的文件因此顺利通过 L2 复查；`schema.py:39-43` 对 list
  内容按 per-entry 校验，空 list = 零条目 = 零 issue。
  边界（如实标注）：T2 的 `llm_call` 抛错时会安全跳过（`source_patch.py:118-122`），
  故销毁路径限于「T2 调用成功但返回根级值」。且 `semantic_*` 类 issue 因文件在
  `l3_file_set` 中，L3 gate 仍会报错 —— 但该残留属 `DEFERRABLE_CATEGORIES`
  （`deferred_repair_log.py:43-44`），按 #60 走台账后 **stage 照常 commit**，
  即被写坏的文件会被提交。
- **实证**（`_smoke_triage` scenario A 现场）：stub 的 T2 返回 `"[]"` →
  文件从 `{"summary": "..."}` 变为 `[]`，`result.passed = True`。
- **证据**：`coordinator.py:95-112`、`fixers/source_patch.py:63-72, 118-142`、
  `fixers/local_patch.py:53-63, 130-143`、`field_patch.py:16-32`、`protocol.py:200-260`、
  `checkers/targets_keys_eq_baseline.py:41-64`、`checkers/semantic.py:145-225`。
- **相关（同根，建议一并处理）**：`targets_keys_eq_baseline.py:140-146` 的其余 issue
  锚在大容器 `$.relationships` / `$.voice_state.target_voice_map`，T2 会整段数组重写。
  #62 只给 `checkers/{schema,semantic}.py` 做了叶子锚点收敛，这个 checker 漏了。

---

**H4** `extraction/repair/checkers/__init__.py:52` + `coordinator.py:295-298` —
文件在 Phase A 只要有任意 L0–L2 error，整轮 repair 的 L3 语义复审就被永久跳过，
最后以 PASS 收场（0 次语义调用）。

- **为什么是问题**：分层跳过本身**是有意设计**（`checkers/__init__.py:3-4` docstring：
  「Files with errors at a lower layer are skipped by subsequent layers」——不浪费 token
  语义复审一个 schema 已坏的文件）。缺陷在于 Phase A 的跳过**后续从未被补偿**：
  `coordinator.py:295-298` 把 `had_semantic` / `l3_file_set` **冻结在 Phase A 结果上**，
  而 Phase B 的 L3 gate 以 `gate_targets = l3_file_set & modified_files` 为条件
  （`coordinator.py:398-399`）、Phase C 的 fallback 以 `if had_semantic and
  config.run_semantic` 为条件（`coordinator.py:479`）—— 二者都因 Phase A 从未跑过 L3
  而恒为空 / False。T0 把 schema 错修掉后，文件直接 PASS。
- **影响范围**：真实运行中 schema / structural 抖动很常见，命中即等于该文件整轮无语义门。
  这是典型的「文档声称会拦、代码实际不拦」。
- **实证**：注入一个 L1 error → 语义 checker 调用 **0** 次；无 L1 error → 调用 **1** 次。
- **证据**：`checkers/__init__.py:3-4, 43-62`、`coordinator.py:295-298, 398-399, 477-479`。

---

**H5** `extraction/repair/checkers/schema.py:54-55` — SchemaChecker 产出的 `json_path`
在数组元素上无法被 `field_patch` 解析，所有「数组内的 schema 违规」在 T0/T1/T2 三层全部修不动。

- **为什么是问题**：`schema.py:54` 用 `[str(p) for p in error.absolute_path]` +
  `".".join(...)`。jsonschema 对数组下标给的是 int，`str(p)` 变成 `"0"`，于是产出
  `$.relationships.1.attitude` 这种「点 + 数字」形式。而 `field_patch._parse_path`
  （`field_patch.py:182-196`）把 `.1` 解析成**字符串** token `"1"`，`_navigate`
  （`field_patch.py:199-204`）拿字符串访问 list → `raise KeyError`。
  三个 fixer 全部在这里静默 `continue`：`local_patch.py:97-99`、
  `programmatic.py:198-200 / 262-264 / 178-181`、`source_patch.py:102-104`。
- **影响范围**：`stage_snapshot` 是数组密集结构（`relationships[]` /
  `target_voice_map[]` / `dialogue_examples[]`），数组内的 `maxLength` / `type` /
  `required` / `additionalProperties` 违规**一次都修不了**，全部落进 #60 defer 台账。
  这直接削掉 #62「机械类起 T0 封顶 T1」路由的大半实际收益。
  StructuralChecker / SemanticChecker 用的是 `[idx]` 括号形式，**不受影响** ——
  只有 schema category 中招。
- **实证**：
  ```
  $.relationships.1.attitude   → KeyError: "Cannot navigate <class 'list'> with key '1'"
  $.relationships[1].attitude  → OK: 'b'
  ```
- **证据**：`checkers/schema.py:50-58`、`field_patch.py:182-204`。

---

**H6** `extraction/persona_extraction/lifecycle/deferred_repair_log.py:61-71` —
repair worker 崩溃被同批次的可延后 issue 掩盖，崩溃文件当 PASS 提交且不进台账。

- **为什么是问题**：`deferrable_issues` 把**所有** failed entry 的 error issue **跨 entry
  展平**后统一判定。worker 崩溃产生的合成 `RepairResult` 带 `issues=[]`
  （`orchestrator.py:3341-3352`），本身不贡献 error issue；只要同 stage 另有任一可延后
  issue，`error_issues` 非空且 `all(...)` 只检查兄弟 issue → 返回 DEFER →
  `orchestrator.py:3379-3391` 写台账、清 `error_message`、fall through 到 PASS/commit。
  崩溃文件从未被校验，**也不在 deferred 台账里**，未来的 Phase 3.5 收尾 pass 无从知晓。
  该函数 docstring（`deferred_repair_log.py:57-59`）明确承诺「worker 崩溃返回 None 硬停」
  —— 该承诺仅在崩溃文件是**唯一** failed entry 时成立。
- **影响范围**：每 stage 的 repair 文件集本就有多个文件（world snapshot + catalog +
  N 角色 × 3），共现是**常态**而非边角。属「错误处理掩盖 bug」。
- **实证**：
  ```
  仅崩溃              → None（硬停，符合 docstring）
  崩溃 + 可延后 issue → DEFER，台账仅 1 条；崩溃文件静默通过
  ```
- **证据**：`lifecycle/deferred_repair_log.py:20-22, 43-44, 55-71`、
  `orchestrator.py:3341-3352, 3362-3391`。

---

**H7** `extraction/repair/coordinator.py:529-532, 884-901` — `coverage_shortage`
超出 `accept_cap_per_file` 时 stage 被硬 ERROR 停机（而非 defer）。

- **为什么是问题**：`_filter_blocking`（`coordinator.py:529-532`）把 `coverage_shortage`
  当作 blocking（即使 `severity=warning`）；`_run_coverage_shortage_triage`
  （`coordinator.py:884-901`）命中 per-file cap 后把多余 issue 留在 blocking 集里。
  它们最终以 **severity=warning** 出现在 `RepairResult.issues` 中，`passed=False`。
  而 `deferrable_issues`（`deferred_repair_log.py:61-71`）只收集 `severity == "error"`
  的 issue → error 集为空 → 返回 `None`（其语义是「worker 崩溃，不可 defer」）→
  orchestrator（`:3371-3379`）走 hard-ERROR 分支。
- **影响范围**：baseline 常有 ~15 个 target（决策 #54 / `targets_cap` 20），一个快照上
  出现 ≥6 处薄内容非常现实。这正是 #62 想根除的「min_examples 卡死 Phase 3」，
  换了个入口复活 —— 且以最坏形式（hard stop，不是 defer）。
- **实证**（分片 B 实跑，6 个主角 tier target 各 1 条例句、cap=5）：
  ```
  passed=False  notes=5  remaining=[('min_examples','warning')]
  deferrable_issues -> None   => orchestrator would HARD-ERROR the stage
  ```
- **证据**：`coordinator.py:529-532, 884-901`、`deferred_repair_log.py:61-71`、
  `orchestrator.py:3371-3379`、`protocol.py:287-290`。

---

**H8** `extraction/persona_extraction/core/rate_limit.py:93-97, 181-192` —
`parse_reset_time` 的 ISO 分支无锚点、无未来性校验，可能进入无退避的热重试死循环。

- **为什么是问题**：三个解析分支里只有 ISO 分支既不锚定 `reset` 关键字、也不校验结果在未来，
  且它是**第一个**被尝试的分支。`_RESET_ISO`（`:93-97`）匹配 stderr 中**任意位置**的 ISO
  时间戳（对比 `:79-84` 的 `_RESET_AT_ABS` 与 `:87-91` 的 `_RESET_IN_REL` 都锚定了
  `[Rr]esets?`）；ISO 分支（`:181-192`）直接 `return dt`，无 `dt > now` 校验
  （对比 `:211-212` 绝对时间分支有 `if candidate <= now_in_tz: candidate += timedelta(days=1)`）。
- **影响链**（代码路径已核实，触发条件为**推断**）：stderr 含任一非 reset 语义的时间戳
  （日志前缀 / request 时间）→ `record_pause:382-383` `resume_at = 过去时刻 + 60s` →
  `wait_if_paused:475-479` `wait_s <= 0` → `_clear()` 立即返回 →
  `llm_backend.py:662-663` `attempt -= 1; continue` → 同一 prompt 立刻重发。
  `attempt` 永不增长，rate-limit 分支无任何退避 → 零间隔子进程热循环，直到窗口耗尽
  （`weekly` 硬停也走不到，因为 `wait_s` 每次都 ≤ 0）。
- **实证**：`stderr = "2026-07-16T09:30:00Z [error] request failed: usage limit reached"`
  （now = 12:00）→ `parse_reset_time` 返回 `09:30:00+00:00`，**在过去**。
- **证据**：`core/rate_limit.py:79-97, 178-192, 208-214, 380-385, 473-481`、
  `core/llm_backend.py:658-666`。

---

**H9** `extraction/persona_extraction/core/run_metrics.py:86, 126, 127` —
真实角色名泄漏进 `main` 分支的代码注释。

- **为什么是问题**：三处注释用 `snapshot:Character B` / `char_snapshot:Character B:char_social`
  作为 lane 名示例。`Character B` 是正在抽取的真实作品角色名（由 git log 佐证），非结构性占位符。
  `conventions.md` §Generic Placeholders 要求示例用 `<character_id>` / `S001`
  （同段 `repair[S001]` 就是正确写法）；§Git 规定 main「永不携带真实 work ID、原著小说
  或提取产物」，而 main 是**唯一 push 远端**的分支。
  **加重情节**：上一轮 `/post-check` 曾把同一个名字从 `docs/decisions.md` scrub 掉
  （当时定级 H2、验证标准含 `grep Character B/Character A`），代码注释被漏掉 —— 说明该轮的 verify
  grep 范围只覆盖了 `docs/`。
- **影响范围**：全仓 grep 确认仅此一文件三处（排除豁免的 `logs/` / `works/` / `sources/` /
  `todo_list_archived.md`）。严格讲 §Generic Placeholders 的列举范围未含 `.py`，
  但 handoff §用户在意的事明确「**不出现真实书名 / 角色 / 剧情名称**」。
- **证据**：`core/run_metrics.py:84-90, 124-128`；`conventions.md` §Generic Placeholders
  + §Git；`logs/change_logs/2026-07-15_173316_fix-from-postcheck.md`。

---

**H10** `extraction/persona_extraction/prompts/analysis_{foundation,candidate_characters,stage_plan}.md`
— 3/12 抽取 prompt 缺失强制的「上限不是配额」声明。

- **为什么是问题**：`conventions.md` §Data Separation 要求「**每个**提取 prompt 模板必须
  显式告诉 LLM `maxLength` / `maxItems` 是**硬上限，不是配额** —— 写原文里真实存在的内容，
  不要为凑满上限而填充 / 注水 / 编造条目。缺了这句，模型会因为『schema 说 ≤N』而默认每个
  数组正好写 N 条。」三个 phase 1 lane 模板完全没有这句。
- **影响范围**：`analysis_candidate_characters.md` 灌水压力最大 —— `candidates` maxItems 30、
  `aliases` maxItems 30、`description` minLength 100 / maxLength 200。缺声明会让模型默认凑满
  30 个候选角色，**直接污染 Phase 1.5 的用户选择**。`analysis_foundation.md` 产
  `foundation.json`（`core_rules` 30 / `major_factions` 20 / `major_regions` 30 /
  `power_system.levels` 20）。`analysis_stage_plan.md` 风险较低（bound 只有
  `stage_title` 80 / `boundary_reason` 100）。
  编造 canon 直接违反项目第一原则「原著小说 = 最高权威」。
  `baseline_key_figures.md` 同为 0 命中，但它是纯 in-place 替换 lane（`:40` 明确
  「不新增、不删除」），无生成面，**不计入本条**。
- **实证**（逐文件 `grep -c '不是配额|硬上限'`）：
  ```
  analysis_candidate_characters.md  0      character_snapshot_extraction.md  1
  analysis_foundation.md            0      character_support_extraction.md   1
  analysis_stage_plan.md            0      scene_split.md                    1
  baseline_key_figures.md           0*     summarization.md                  1
  baseline_fixed_relationships.md   1      world_extraction.md               2
  baseline_identity.md              1      baseline_target_baseline.md       1
  ```
- **证据**：上述三文件；`conventions.md` §Data Separation；
  `schemas/analysis/candidate_characters.schema.json`；`schemas/world/foundation.schema.json`。

### Medium

**M1** `extraction/persona_extraction/prompts/character_snapshot_extraction.md:150, 313`
vs `prompt_builder.py:922-924` — `timeline_anchor` 上的正面指令冲突。
`prompt_builder` 注入的 hard-gate 块把 `timeline_anchor` 列入「**程序注入字段（不要写）**」，
同一 prompt 的 `:133` 却把它列入「结构性骨架（schema 顶层 required，缺一会被 L1 gate 拒绝）」、
`:150` 写「**必填**」、`:313` 要求「均已填写」；而 `prompt_builder.py:931-932` 明确说
「§核心规则 / §maxItems 段照常适用」= 让模型同时遵守两条互斥指令。
归属核实：`snapshot_merge.py:103-134` 的 `FIELD_ALLOCATION` 中 `timeline_anchor` 不属于任何
sub-lane；`:204-211` `PROGRAM_INJECTED_FIELDS` 含它；`:507-515` merge 后由 `stage_title` 派生注入。
**影响**：`config.toml:135` `char_snapshot_sub_lanes = true` 是生产路径。任一 sub-lane 听从
「必填」→ 触发 merge gate 1（partial 顶层字段集必须**等于** lane 分配，多写即 hard fail）→
`MergeError` → 整个 char_snapshot lane 重跑。`snapshot_summary`（`:313` 同句）归 `char_internal`，
无此问题 —— 只有 `timeline_anchor` 冲突。

**M2** `extraction/config.toml:192-201` + `core/config.py:129-140` —
`defer_unresolved_semantic` 的开关说明与代码**语义相反**。
两处都写「残留的 error **只剩** `category=="semantic"`」且「任何残留的 json_syntax /
**schema / structural / cross_file** error … 仍然硬 ERROR」；实际
`DEFERRABLE_CATEGORIES = {"semantic","schema","structural","cross_file"}`
（`deferred_repair_log.py:43-44`），**只有 `json_syntax` 硬 ERROR**。
代码与 #60/#62 一致，**文档是错的**。`config.toml` 是决策 #45 的操作者单源 ——
读文档的人会对流水线停机语义做出完全相反的判断。

**M3** `extraction/repair/context_retriever.py:94-110` — T2 章节升级阶梯 off-by-one，
第 2 次尝试拿到与第 1 次完全相同的 top-3 上下文；「全章节」分支不可达。
`source_patch.py:6-9` docstring 声明 `attempt 0: top-3 / attempt 1: top-5+adjacent /
attempt 2: all`。实际分支是 `attempt_num >= max_attempts or attempt_num >= 3` → all；
`attempt_num >= 2` → top-5+adjacent；else → top-3。coordinator 传的
`max_attempts = _tier_max(config, 2) = min(t2_max, 2) = 2`（`coordinator.py:587, 606-613`），
循环 `for attempt in range(2)` → attempt ∈ {0,1}。attempt=1 时三个条件全不成立 → 落到 else
→ **又是 top-3**。`attempt_num >= max_attempts` 按循环构造恒不成立，all-chapters 分支是死代码。
**影响**：T2 第二次尝试是拿同样上下文重问一遍，纯烧 token；「扩大检索范围再试」从未生效。

**M4** `extraction/persona_extraction/orchestrator.py:1311-1313, 1336-1338` —
`_collect_stage_files` 把 `stage_catalog.json` 放进 repair 文件集，违反 #61 的
primary/derived 二分，且与它自己的 docstring 直接矛盾。
`orchestrator.py:1272-1283` docstring 明写「Only primary LLM outputs enter repair:
world / character stage_snapshots and memory_timeline」，但两处把 `stage_catalog.json`
加了进去。catalog 是 100% 程序派生产物 —— `post_processing.py:451` `upsert_stage_catalog`
由 snapshot 确定性重投影（`:599` / `:684`）。
**影响**：T1 会花 LLM token 去改一个 post-repair PP 重跑（`orchestrator.py:3429`）必然覆盖的
文件（改动被静默丢弃）；更糟的是 catalog 上的 schema/structural 违规会让 stage 走 FAIL/DEFER，
而那本该由确定性重生成解决。两个 digest 文件确认已正确排除（#61 落地无误）。

**M5** `extraction/persona_extraction/phases/snapshot_merge.py` — `FIELD_ALLOCATION` 与
`stage_snapshot.schema.json` 之间**不存在任何 hard gate**，与 conventions 的表述不符。
`conventions.md` §Cross-File Alignment 声称新增/改名的 schema 顶层属性「必须挂到某 sub-lane，
否则 merge hard gate 报错」。实际 `snapshot_merge.py` 完全不加载 schema；5 道 merge gate
（`:246-296`、`:302-356`）只校验 partial ⇄ `FIELD_ALLOCATION`，从不校验
`FIELD_ALLOCATION` ⇄ schema。
**现状：当前完全对齐**（已实跑比对 —— schema 25 个顶层属性 = `FIELD_ALLOCATION` ∪
`PROGRAM_INJECTED_FIELDS`，双向差集为空；`failure_modes`(4) / `stage_delta`(6) /
`behavior_state`(8) 子键亦精确对齐）。这是**潜在陷阱**而非现行故障：未来给 schema 加一个
**非 required** 顶层属性时无任何机制报错 —— 该字段将永远不被任何 sub-lane 产出，静默缺失。
lockstep 靠人记，正是 conventions 自己说要避免的。

**M6** `extraction/persona_extraction/core/json_repair.py:43-48` — `_fix_inner_quotes`
会破坏本已正确转义的字符串。
匹配到 `"key": "value"` 后无条件 `value.replace('"', '\\"')`，不区分 `"` 与已转义的 `\"`。
对 `"summary": "他说\"你好\"，然后走了",` 这样**本身合法**的行：value = `他说\"你好\"…` →
replace 后 = `他说\\"你好\\"…` → 落盘成 `\\"`（JSON 里是「转义反斜杠 + 未转义引号」）→
该行由合法变非法。触发条件是文件**别处**有语法错误导致 `json.loads` 先失败（`:215`），
L1 随后对全文逐行跑 —— 无辜行被连坐。

**M7** `extraction/persona_extraction/core/json_repair.py:282-305` —
`try_repair_jsonl_file` 在仍有坏行时返回成功。
`:296-297` 修不好的行 `fixed_lines.append(line)` 原样保留；`:299-301`
`if repairs > 0: write; return True`。只要有**一行**修好就返回 `True`，哪怕另有行仍不可解析。
`all(_is_valid_json(...))` 的完整性校验只存在于 `:302` 的 `elif`（`repairs == 0`）分支
—— 逻辑上正好覆盖不到需要它的那个场景。

**M8** `extraction/persona_extraction/core/llm_backend.py:301-305, 337-344` —
子进程超时后 `communicate()` 可能永久挂起。
`Popen` 未设 `start_new_session=True`；超时路径 `proc.kill()` 只杀直接子进程，随后
`proc.communicate()`（**无 timeout**）等待 stdout/stderr 管道 EOF。`claude -p` 带 `Bash` 工具
（`:244-246`）会派生继承管道的孙进程 → 杀掉 claude 后孙进程仍持写端 → `communicate()`
永久阻塞，lane 线程死锁，`--max-runtime` 也救不了（非抢占式）。这正是决策 #49 描述的
phase 0 撞 1800s wall 的高频场景。`CodexBackend:500-508` 同构。
同仓 `process_guard.py:227` 正确用了 `start_new_session=True` —— 说明是遗漏而非取舍。

**M9** `extraction/persona_extraction/prompts/character_snapshot_extraction.md` 的
`{lane_scope}` 散文与 4-lane 拓扑不符。
`prompt_builder.py:926-930` 渲染的文案：「`failure_modes` / `stage_delta` 子键划分：
这两个顶层字段被拆给**两个** sub-lane」。实际 `snapshot_merge.py:138-180`：
`failure_modes` 跨 **3** lane（expression / internal / social），`stage_delta` 跨 2，
且 `behavior_state` 也被拆 —— 第三个被拆字段在这段散文里完全没提。
白名单**表格**由 `FIELD_ALLOCATION` 运行时派生因而正确（`:904-913`），坏的只有旁边的散文。
给 LLM 的是自相矛盾的上下文。

**M10** `extraction/persona_extraction/prompts/*.md` — #11e 的 maxItems 裁剪规则只落在
12 个模板中的 1 个。
`ai_context/decisions.md` #11e 要求「**所有**抽取 prompt 必须指示 LLM 在抽取时就按
`maxItems` 上限排序 + 截断」并给出四级优先级锚点。实际只有
`character_snapshot_extraction.md:63-85` 有完整的 §maxItems 裁剪规则。
`world_extraction.md` / `summarization.md` / `scene_split.md` 匹配数 0；
`baseline_identity.md` / `baseline_fixed_relationships.md` 各 1（只有「不是配额」那句，
无排序 + 截断规则）；`analysis_foundation.md:103` 只覆盖 `key_figures` 单字段。
**最高风险实例**：`summarization.md:43` `chunk_world_rules[]`（最多 5 条）—— 信息密集的
chunk 世界规则超 5 条时无优先级指导，模型只能随机丢弃或直接 schema fail 重跑。

**M11** `schemas/shared/source_note.schema.json:145` — live 数据契约仍以已删除的 T3
定义字段语义。
```
"triage_round": { "enum": [1,2],
  "description": "1 = 在 T3 触发之前被 triage 接受；2 = T3 跑完且 L3 gate 仍有残留时被 triage 接受。" }
```
`triage_round` 在 `:24` 是 **required**，是仍在写入的字段。全仓只剩这一处说 T3：
`extraction/repair/protocol.py:151` 已是 `# 1 = residual (post-cap), 2 = post-gate`，
`docs/requirements.md:2101` 已是 `# 1 = max_tier 封顶后; 2 = L3 gate 后`。
**schema 是数据契约单源，却是最后掉队的一处。更高优先级真相 = 代码 + requirements。**

**M12** `docs/decisions.md:455`（#48）— live 决策的触发条件已不存在。
#48 不是废止条目 —— `docs/decisions.md:884` 明写「decision #48 长度容差门**保留**，
改在封顶后触发」。但 #48 自身仍写触发点为 `Phase 3 repair framework lifecycle 2 即将
T3_EXHAUSTED`，Plumbing 指向 `coordinator.py`（`T3_EXHAUSTED` terminal-state branch）。
已验证 `grep max_lifecycles_per_file|T3_EXHAUSTED|file_regen|lane_regen` 在 `extraction/`
**0 命中**；容差门实际在 `coordinator.py:720-725`（tier 封顶后）触发。
**这是本轮唯一「live 条目内容本身错误」的一处**（其余是缺注）。正确口径见
`extraction_workflow.md:791-794`。

**M13** `docs/decisions.md:469-470, 547-553`（#55）— 标题与正文把 T3 sub-lane 重抽当落地
设计，无 #62 修正注。标题仍是「…+ 程序 merge + **lifecycle 2 sub-lane 重抽**」，正文整段描述
`Repair lifecycle 2 T3 重抽` / `max_lifecycles_per_file = 2` / `T3_EXHAUSTED`。
而 `docs/decisions.md:869-870`（#62）已明写彻底删除 `sub_lane_regen`（#55）。
**对照组证明是遗漏而非有意**：`ai_context/decisions.md:270` 同一条已正确收口为
「（sub-lane 重抽经 #62 删）」。

**M14** `docs/decisions.md:222`（#25a）— 唯一漏挂 #62 修正注的子条目。
#25（L215）/ #59（L720）/ #60（L782）都挂了 `> **经 #62 收紧/扩展**`，#25a 独独没有，
仍写「每 lifecycle `accept_cap_per_file=5`」「Lifecycle 2 从磁盘读回指纹」
「T3 输出直接流入 lifecycle 2」。

> M11–M14 的共同影响面：`docs/decisions.md` 是决策理据的单一事实来源，按设计
> 「仅当需要某条决策的『为什么』时才打开」。未来 AI 一旦为搞清 #48 的触发时机而查档，
> 会读到一个代码里已不存在的终止状态机。

**M15** `ai_context/skills_config.md:64` 与决策 #42 直接冲突。
skills_config §Do-not-commit 写「本项目专属、**绝不可被 commit** 的路径」并列
`works/`（extraction 产物）；`ai_context/decisions.md:296` / `docs/decisions.md:892`（#42）
却写「`works/*/analysis/` + `works/*/indexes/` 作为 **canonical 跟踪**」。二者都没带分支限定词
—— 唯一能调和它们的信息在 `ai_context/architecture.md`（`main` = works/ 仅 tracked README，
抽取数据提交只属于抽取分支）。
**更高优先级真相 = #42 + architecture.md 的三分支模型**；skills_config 的绝对措辞需补
「main / 框架提交」限定。这条会误导 `/holo:commit` 类 skill 拒绝提交本该 canonical 的产物。

**M16** `docs/architecture/schema_reference.md:226` — 别名 `type` 枚举漏 2 项，
且与同文件自相矛盾。文档 8 项（本名/化名/代称/称呼/封号/道号/武器名/其他）vs
`schemas/character/identity.schema.json` 实际 **10 项**（多 `昵称` / `绰号`）。
同一文件 `:65` 写的却是「10 项中文枚举」并列全；`docs/requirements.md:316-317` 同样列全 10 项
且明写「所有阶段（分析、baseline、提取）统一使用此类型枚举」。
**三处一致、仅 226 行是残留旧值 → 真相 = schema。**照 226 行写 prompt 会漏掉两类合法别名。
未被任何 todo 覆盖。

**M17** `extraction/repair/tests/_smoke_triage.py` 已失效，跑不过（exit 1）。
```
line 157: assert result.accepted_notes, "expected at least one accepted note"
AssertionError  [A] passed=True  notes=0  T3 regen calls=0  triage calls=0
```
根因是 H4 + H3 的叠加：`_write_work_layout`（`:50-87`）造的角色快照没有
`target_baseline.json` → `targets_baseline_missing`(L2 error) → 语义 checker 被跳过（H4）→
期望的 `fact_mismatch` 从未产生 → 转而是 `$` 锚点走 T2，stub 的 `"[]"` 被当作根替换套用（H3）
→ 无残留 → triage 不触发。
**注意**：该测试在 `5d9ef6f`（restructure）的 commit message 中已被记为「HEAD 即坏，正交」，
而 #62（`010fb03`）**重写了它**（13 insert / 115 delete）却仍未修好 —— 一个跨两次重构持续
失效的检查。`_smoke_l3_gate.py` 三个场景全部通过；其余 6 个 phase smoke 全部通过。
措辞残留：`:156/158/173/482` 仍讲 "T3 regen calls" / "pre-T3 triage"，stub 里还留着
`"regeneration tool"` 分支（`:115-117, 241-242, 435-437`）。

**M18** `works/README.md:219-221` + `docs/architecture/data_model.md:521` —
断言「schema 也未定义」，但 schema 存在。两处都写 indexes/「整棵子树尚未启用——当前无 writer，
**schema 也未定义**」。实际 `schemas/work/load_profiles.schema.json` 存在，`$id` 明确指向
`works/{work_id}/indexes/load_profiles.json`，且已登记在 `schemas/README.md:10` +
`docs/architecture/schema_reference.md:116-119`。「无 writer」属实（已由 todo
`T-PHASE5-RETRIEVAL` 跟踪），**「schema 未定义」是错的**。

**M19** `docs/architecture/extraction_workflow.md:394` — 同文件内自相矛盾。
描述 live 配置开关行为时写「Fallback 模式（`char_snapshot_sub_lanes = false`）：单 lane
char_snapshot + **file-level 2 lifecycle 标准流程**」，而同文件 `:376-377` / `:719` / `:781`
都已正确写「单遍 Phase A→B→C，无 lifecycle 重置」。

**M20** `docs/requirements.md:2567` — 配置索引表仍列已删除的旋钮。
`| [repair] | 各 tier 重试、**lifecycle 上限**、triage 接受上限、总轮数、per-file 并发 |`
—— `max_lifecycles_per_file` 已从 `config.toml` + `core/config.py` 删除（代码 0 命中）。

### Low

**L1** #62 已删概念在注释 / docstring 中残留（不影响运行时，但会误导后续开发）：
`extraction/repair/triage.py:4-8`（以 T3 定义两个调用点）、
`extraction/repair/fixers/__init__.py:1`（`"""Fixer registry — T0 through T3"""`）、
`extraction/validation/gates/phase2_baseline.py:22-31`（既说 `T0–T3 fixers`，又把层级写成
`L0=schema / L1=structural / L2=cross-check / L3=semantic` —— 与实际
`L0=json_syntax / L1=schema / L2=structural / L3=semantic` 不符）、
`orchestrator.py:10, 1279, 3241, 3252, 3256`、`llm_backend.py:274`、
`snapshot_merge.py:71-72, 528-529`、`docs/todo_list.md:336`。
其中 `orchestrator.py:1279` 尤为讽刺 —— 用「T3 会重写 derived file」来论证 #61 的排除理由，
而 T3 已不存在。`protocol.py:205` / `coordinator.py:22` 是有意的「T3 已不存在」说明，可保留。

**L2** `extraction/repair/checkers/structural.py:151-153` — `# JSONL checks
(memory_digest, world_event_digest)`，#61 后这两个文件已不进 repair（该路径现在实际服务
`memory_timeline/{stage_id}.json`）。

**L3** `extraction/persona_extraction/phases/snapshot_merge.py:525-533` —
`compute_fingerprint` 已成死代码。计算结果在 `orchestrator.py:1108-1112` 仅被 log 和塞进
`LLMResult.text`；唯一调用点 `orchestrator.py:2907` 不消费 `.text`。它服务的 lifecycle-2
accept-list 已被 #62 删除。

**L4** `extraction/persona_extraction/phases/snapshot_merge.py:434` —
`timeline_anchor_max_length: int = 50` 硬编码，重复 schema 边界；
`orchestrator.py:1082-1091` 调用 `merge_partials` 时不传该参数，故始终用硬编码值。
schema 当前也是 50（已核对），但违反 conventions §Data Separation「边界只写在 schema」。
对比 `orchestrator.py:156-182` 的 `_stage_title_max_length()` —— 同类问题那里是读 schema
+ WARN 兜底，此处不是。

**L5** `extraction/persona_extraction/core/llm_backend.py:266, 589` —
`_probe_fn_for` 的「最小成本探针」实际授予全套工具。`:589` 传 `allowed_tools=[]`，
但 `:266` `tools = allowed_tools or CLAUDE_DEFAULT_TOOLS` —— 空列表 falsy，回落成
`["Read","Write","Edit","Bash","Glob","Grep"]`。应改用 `if allowed_tools is None`。
（实证确认。）

**L6** `extraction/persona_extraction/core/git_utils.py:228-231` — `commit_stage` 的
「无内容可提交」判定查错了对象：用全树 `git status --porcelain` 而非 `git diff --cached`。
索引为空但树内别处有脏文件时会跳过该早退、走到 `git commit` 拿非零退出，
日志报 "Commit failed" 掩盖真实原因（"nothing to commit"）。

**L7** `extraction/persona_extraction/core/git_utils.py:46-49` — `git_status` 假定
`.git` 是目录。在 git worktree 中 `.git` 是文件，`in_rebase` / `in_merge` 恒为 False。

**L8** `extraction/persona_extraction/core/schema_loader.py:37-40, 43-67` —
`_load_fragment` 按路径字符串 `lru_cache`，长驻进程内 schema 改动不会重载；
`_inline_refs` 无环检测，自引用 `$ref` 链会 RecursionError。

**L9** `extraction/config.toml:169-171` — `t1_retry = 3` / `t2_retry = 3` 被
`coordinator.py:115-122` `_tier_max` 的 `min(configured, _TIER_ATTEMPT_CAP)` 静默夹到 2。
`config.toml:168` 的注释说明了这点，但「可配置键实际不可配」仍与 #45 单源精神相悖。

**L10** `extraction/persona_extraction/lifecycle/deferred_repair_log.py:36` —
TYPE_CHECKING 导入了不存在的名字 `RepairFileEntry`（`protocol.py` 里没有；那是
`orchestrator.py:204` 处 `FileEntry as RepairFileEntry` 的本地别名）。运行时因
`from __future__ import annotations` 无碍，但类型检查会报 NameError。

**L11** `extraction/repair/coordinator.py:257` + `notes_writer.py:107-126` —
同一 issue 的 SourceNote 会在重跑时重复落盘，与 #25a「同一问题永不写两次」相悖。
`notes_per_file` 每次 run 从空 dict 起算，`NotesWriter` 只从磁盘读回 `_load_max_seq`，
没有 fingerprint 回读。`--resume` 重跑同一 stage 会把相同的 coverage_shortage /
source_inherent 再接受一遍并 append。下游 `_load_coverage_shortage_paths`
（`phase3_5_consistency.py:250-269`）用 set 消化，功能上无害，只是台账噪声。

**L12** `docs/architecture/README.md` — 整份内容对本项目已失效。sentinel 内仍写
「第一个关注点出现时再创建；**在此之前本目录有意保持为空**」——该目录已有 4 份实质文档
（含 63KB 的 `extraction_workflow.md`）。示例文件名（`data-flow.md` / `auth-model.md` /
`branch-strategy.md`）均不存在。并指向 `ai_context/architecture.md` 的 4 个**英文段名**，
逐个验证**全部 MISSING**（已中文化为 `## 顶层结构` / `## 系统分层` / `## 关键边界` /
`## 运行时 / 入口点`）。属 plugin canonical 段，修复须落在 sentinel 外的 gap。

**L13** `works/README.md:40, 76, 221` — 3 处指针指向不存在的章节，均写
`见 docs/architecture/data_model.md §Indexing`。该文件无此标题 —— 实际是
`## 作品索引包`（`data_model.md:513`）。**推断**：中文化提交 `66d0e48` 改了标题，未回改指针。

**L14** `docs/todo_list.md` Index 中 `T-LIGHTNOVEL-SCHEMA-ONEOF` 摘要数字错：
写「schema 现在只允许 **≥5**」，实际 `stage_plan.schema.json:52` 是 `minimum=8`；
同文件正文 `:283` 却正确写着 monolithic `minimum=8, maximum=15`。该 Index 自称是缓存且警告
「这里漂移意味着 `/todo` 会给出错误答案」—— 正是它自己描述的失效模式。

**L15** `docs/requirements.md:3407` — 3407 行的权威文档末尾残留模板占位符
`## 段` + `_(none yet — delete this marker once content is added)_`。全仓仅此一处。

**L16** `ai_context/skills_config.md:62-63` — `embeddings/` / `caches/` 列为
do-not-commit，但 `.gitignore` 无对应条目（`.cache/` ≠ `caches/`）；两目录当前也不存在，
属纸面规则。

## Alignment Summary

**对齐良好的层**：

- **`ai_context/` 全线干净** —— #62 的口径已正确收口（`architecture.md` 流水线段准确写
  「3 tier T0/T1/T2，按 rule 路由到 `(start,max)` + 每 tier 封顶 2 次，单遍无整文件 regen」
  + #60 四类 defer）。**会话起始阅读集不会误导未来 AI**，这是本轮最重要的正面结论。
- **决策对 lockstep** —— `#1–#62` 在索引与归档间**双向零差集**（机械验证）；`docs/` 多出的
  19 个子条目是索引明写「含子条目，细节见归档」的设计；无重号；全仓无悬空 `#N` 引用。
  （`#57` 在 `todo_list_archived.md:128` 的悬空引用是 `66d0e48` 中**用户逐例确认**的接受状态。）
- **git 追踪纪律** —— `git ls-files -ci` 0 命中；`works/` 只有 README（与 handoff
  「无完成的角色包」一致）；决策 #39（`scene_splits/` 不跟踪）+ #42（`retrieval/` 仅本地）
  均正确落实。
- **schemas/ 本体** —— 34 文件元校验全部合法；4 个 `$ref` 全部解析、0 dangling；
  字段名集合零漂移；除 M16 外所有枚举一致。
- **#62 跨文件数值口径** —— tier 集合、单轮 A→B→C、rule 路由映射、per-tier cap（一致 = 2）、
  defer 类别数（一致 = 4）、`accept_cap_per_file=5`、`max_rounds=5` 六份文档 + 代码逐项对齐，
  **无任何数字或定义分歧**。
- **代码侧 #62 迁移彻底** —— `file_regen` / `lane_regen` / `sub_lane_regen` /
  `max_lifecycles` / `T3_EXHAUSTED` / `T3_TRIGGERED` / `prior_attempt_context` 在
  `*.py` / `*.toml` 源码中**零命中**。compileall + import smoke 全绿。

**最不对齐的层**（按严重度）：

1. **repair 的 tier 语义与守卫（最严重）** —— #62 把「不再全文重跑」写进了决策，代码也删了
   T3，但 `$` 锚点 + T2 无复验（H3）让全文重写以更弱保护的形式复活；语义门在有 L0–L2 error
   时静默失效（H4）；数组内 schema 违规三层都修不动（H5）。**决策的意图未在代码中完整实现。**
2. **编排层的分支时序与 scope 守卫** —— reconcile 早于 checkout（H1）、中文 work_id 的
   scope 判定失效（H2）。两者都在「干净退出后续跑」这一**主用例**上。
3. **`docs/decisions.md` 的旧条目未随 #62 收口** —— M12–M14。`ai_context/` 已收口而归档没有，
   形成「索引对、归档错」的倒置。
4. **prompt 层的强制声明覆盖不全** —— H10（3/12 缺 cap-not-quota）、M10（1/12 有 maxItems
   裁剪规则）、M1/M9（指令自相矛盾）。

**跨文档冲突的优先级裁定**：

| 冲突 | 更高优先级真相 |
|---|---|
| `source_note.schema.json:145` vs `protocol.py:151` + `requirements.md:2101`（M11） | **代码 + requirements** |
| `config.toml:192-201` / `config.py:129-140` vs `deferred_repair_log.py:43-44`（M2） | **代码**（文档写反） |
| `skills_config.md:64` vs 决策 #42（M15） | **#42 + `architecture.md` 三分支模型** |
| `schema_reference.md:226` vs `identity.schema.json` + `:65` + `requirements.md:316`（M16） | **schema** |
| `docs/decisions.md` #48/#55/#25a vs #62 + 代码（M12–M14） | **#62 + 代码** |
| `extraction_workflow.md:394` vs 同文件 `:376-377/:719/:781`（M19） | **同文件多数派 + 代码** |
| `character_snapshot_extraction.md:150` vs `prompt_builder.py:922`（M1） | **`prompt_builder`（程序注入方）** |

## Residual Risks

- **#62 的「治本」意图与实际收益差距**：H3/H4/H5 三条叠加后，`coverage_shortage` → 0-token
  接受这条招牌路径之外，机械类路由（T0 封顶 T1）在数组字段上大半失效、语义门可被静默跳过。
  建议在真实跑一遍后用 `logs/runs/` + `deferred_repairs/` 台账验证实际 tier 分布，
  而非依赖设计意图。
- **`deferred_repairs/` 台账的可信度**：H6（崩溃文件不进台账）+ L11（重复落盘）会让台账既漏记
  又有噪声。`T-PHASE35-DEFERRED-FIX` 明确「等真实台账数据积累后据此设计 fixer 形态」——
  台账失真会直接误导那个设计决策。
- **`_smoke_triage` 长期失效（M17）**：这是唯一覆盖 #25a triage 接受路径的测试，跨两次重构
  持续红灯。意味着 SourceNote 接受链路**当前无任何通过的自动化验证**。
- **中文 work_id 的其它 porcelain 消费点**：H2 修好后建议全仓 grep `--porcelain`，
  确认无第四处同类漏网。
- **SSoT 数字复述**：`schema_reference.md` ~15 处 + prompts ~40 处硬编码 bound 当前与 schema
  **全部一致**（已逐个核对），未发生漂移，且已由 todo `T-PROMPT-SCHEMA-INJECT` 登记为
  drift risk。不作为本轮发现，但它是 M16 那类漂移的温床 —— M16 正是这个风险已经兑现的实例。
- **未覆盖区域**：`sources/` / `users/*/sessions/` / `works/*/analysis/evidence/` 按
  `instructions.md` §阅读范围 默认跳过，未扫描。`simulation/` 仅设计文档（0 个 `.py`），
  与 handoff 一致，未做逐句语义对读。requirements ↔ architecture 做了结构比对与 Phase 序列
  交叉验证，未做逐节语义对读。

## Open Questions / Ambiguities

**OQ1** `$` 锚点 issue 该如何修？三类 issue 携带 `json_path="$"` 但性质迥异：
`targets_baseline_missing` 是**兄弟文件缺失**（本文件无错，不该被改）；
`semantic_unavailable` / `semantic_unparseable` 是**基础设施故障**（不该进 fixer，该重试或直接
defer）；LLM 漏写 json_path（`semantic.py:225`）是**降级兜底**。仓库自身无法决定这三类是否都该
被 T2 处理。倾向：三类都不该进 T2 —— 但这是产品/架构判断。

**OQ2** H4 的修法取舍：是「Phase A 之后对已修完 L0–L2 error 的文件补跑一次 L3」（更贵，
但语义门真正生效），还是「把 `l3_file_set` 改为动态计算」（同效），还是接受现状
（有 schema 错的文件不做语义复审是有意的省 token 设计，只是不该报 PASS）？
第三种需要重新定义 PASS 语义。仓库无法单方面决定。

**OQ3** H7 的修法取舍：让 `deferrable_issues` 一并接受 `coverage_shortage` warning，
还是让超 cap 的 coverage_shortage 直接降级为非 blocking？前者让台账更完整，后者更符合
「薄内容不是错误」的原意。

**OQ4** M15 的裁定方向：是给 `skills_config.md §Do-not-commit` 的 `works/` 补
「（main / 框架提交）」限定，还是把该段改为按分支分列？后者更准确但让 skill 消费方复杂化。

**OQ5** H9 的规则范围：`conventions.md` §Generic Placeholders 的列举范围
（`schemas/` / `docs/` / `ai_context/` / `prompts/`）是否应显式含 `extraction/**/*.py`
的注释？上一轮 verify grep 只覆盖 `docs/` 正是因为规则没写代码。

**OQ6** M5 的必要性：`FIELD_ALLOCATION` ⇄ schema 的断言该加在哪 ——
`_smoke_4_lane_merge_and_slice`（便宜，但只在跑 smoke 时发现）还是 `snapshot_merge` 导入时
（真 hard gate，但要加载 schema）？conventions 的措辞承诺的是后者。

## Recommendations

**仅供参考，由用户决定。** 每条都过了三问自查（必要吗 / 能更简单吗 / 是否越界）。

**修（本轮建议落地）**

- **H1** — 修。把 `reconcile_with_disk` 移到 `create_extraction_branch` 之后（或先探测/切分支
  再 reconcile）。**改动极小，但它静默销毁已完成的 stage 进度**，且命中文档推荐的主用例。
  优先级最高。
- **H2** — 修。三行改动：给 `preflight_check` / `checkout_main` 的 `_git(["status",
  "--porcelain"])` 加 `-c core.quotePath=false`，与 `commit_stage:214` 保持一致。
  修法已在同文件有现成范本，无需设计。
- **H3** — 修。最小组合：(a) `apply_field_patch` 的根替换分支加类型守卫（新值类型须与原文档
  一致）；(b) 给 T2 传 `verify_fn`（`_build_fixers` 一行）。**先不做 OQ1 的路由重设计** ——
  守卫 + 复验已能挡住数据破坏，路由归属另议。
- **H5** — 修。`schema.py` 拼路径时对 int 用 `[i]` 而非 `.{i}`（一处改动），或让
  `_parse_path` 把纯数字 dot-token 归一成 int。前者更符合既有 `[idx]` 约定
  （StructuralChecker / SemanticChecker 已在用）。
- **H6** — 修。`deferrable_issues` 改为**按 entry 逐个判定**：任一 entry 是崩溃
  （`issues == []` 且 `passed=False`）即返回 None。纯逻辑，改动小，且现 docstring 已承诺此行为。
- **H9** — 修。三处注释 `Character B` → `<character_id>`（或 `角色A`），与同文件 `repair[S001]`
  的写法对齐。顺带把 verify grep 范围从 `docs/` 扩到全仓。
- **H10** — 修。给三个 phase 1 lane 模板补「上限不是配额」声明。`analysis_candidate_characters.md`
  最紧急（污染 Phase 1.5 用户选择）。可从既有 8 个模板直接复用措辞，无需新设计。
- **M2** — 修。`config.toml:192-201` + `config.py:129-140` 的说明改为与
  `DEFERRABLE_CATEGORIES` 一致。**文档写反了停机语义**，代价是操作者误判，修正成本近乎为零。
- **M11** — 修。`source_note.schema.json:145` 的 description 同步为
  `1 = max_tier 封顶后被接受；2 = L3 gate 后被接受`（照抄 `protocol.py:151` /
  `requirements.md:2101`）。schema 是契约单源，不该是最后掉队的。
- **M12 / M13 / M14** — 修。#48 正文的触发条件改为「tier 封顶后」+ Plumbing 指向
  `coordinator.py:720-725`；#55 标题与正文补 #62 收口注（照 `ai_context/decisions.md:270`
  的措辞）；#25a 补 `> **经 #62 收紧**` 注。三条同属一个改动面，一并落地。
- **M16** — 修。`schema_reference.md:226` 补 `昵称` / `绰号`，与同文件 `:65` 对齐。一行。

**留 todo**

- **H4** — 留 todo（需 OQ2 定夺）。这是「声称会拦、实际不拦」的真问题，但三种修法的语义取舍
  不同，且最优解可能牵动 PASS 定义。建议登记为 todo 并在 OQ2 澄清后落地。
- **H7** — 留 todo（需 OQ3 定夺）。修法二选一都简单，但选哪个取决于「薄内容算不算错误」
  的产品判断。
- **H8** — 留 todo。给 ISO 分支加未来性校验（或给 `resume_at` 设下限）是三行改动，但**触发
  条件是推断**（未在真实 stderr 中观测到裸 ISO 时间戳）。建议先在 `record_pause` 加一行
  WARN 日志观测，有实例再修 —— 避免为假想场景改限流这种敏感路径。
- **M1 / M9** — 留 todo，一并处理。`character_snapshot_extraction.md:133/150/313` 的
  `timeline_anchor` 措辞需改为「由程序注入，不要写」，同时修 `prompt_builder.py:926-930`
  的「两个 sub-lane」散文。M1 会导致整 lane 重跑，值得修；但要与 `{lane_scope}` 块通盘对一遍
  措辞，超出「顺手改」范畴。
- **M3** — 留 todo。off-by-one 修法（`>= max_attempts` 改 `>= max_attempts - 1`）看似一行，
  但要先确认设计意图是「2 次尝试用 top-3 + top-5」还是「保留 all 分支需要 t2_max=3」——
  后者与 `_TIER_ATTEMPT_CAP=2` 冲突。先定意图再改。
- **M4** — 留 todo。把 `stage_catalog.json` 移出 repair 文件集符合 #61，但要确认
  catalog 的 schema 违规是否真能靠 PP 重投影自愈（若 PP 本身有 bug，移出会让问题静默）。
- **M5** — 留 todo（需 OQ6 定夺）。当前**完全对齐**，是潜在陷阱而非故障。加断言的位置有取舍。
- **M6 / M7 / M8** — 留 todo。三条都是 `core/` 的真实缺陷（M8 尤其 —— 会死锁 lane 线程），
  但都不在 #62 这轮的改动面上，且 M8 的修法（`start_new_session=True` + `communicate(timeout=)`）
  需要在真实 phase 0 长跑中验证不引入新问题。
- **M10** — 留 todo。#11e 要求「所有 prompt」，当前 1/12。补齐是明确的对齐工作，但 11 个模板
  的裁剪锚点需逐个按字段语义定制，工作量不小，且优先级低于 H10（后者是防编造，前者是防随机丢弃）。
- **M17** — 留 todo。修 `_smoke_triage` 依赖 H3/H4 先修完（它的失败正是那两条的下游）。
  建议 H3/H4 落地后再回来修测试，否则会为迁就 bug 而改坏断言。
- **M15** — 留 todo（需 OQ4 定夺）。
- **M18 / M19 / M20** — 留 todo，可与下一次 docs 维护一并做。都是单行事实错误，无风险但也不紧急。

**跳过**

- **L1 / L2** — 跳过（或纯顺手）。注释里的 T3 残留不影响运行时。若要清，建议只清
  `orchestrator.py:1279`（用不存在的 T3 论证 #61 的排除理由，最容易误导）+
  `fixers/__init__.py:1`（registry 一行）+ `phase2_baseline.py:22-31`（层级写错，比 T3 更误导）。
  其余批量 grep 清理属「顺手改一下」，不值得单独开一轮。
- **L3 / L4** — 跳过。死代码与硬编码常量，当前值与 schema 一致，无实际影响。
  L4 若要修，`orchestrator.py:156-182` 有现成的读 schema + WARN 范本可抄。
- **L5 / L6 / L7 / L8 / L9 / L10 / L11** — 跳过。均为真实但低影响：L5 探针多拿工具不产生
  副作用（prompt 是 `"1"`）；L6 只影响错误日志措辞；L7 仅影响 worktree 场景（本项目不用）；
  L8 的长驻进程场景不存在；L9 有注释说明；L10 运行时无碍；L11 只是台账噪声。
- **L12** — 跳过（受限）。`docs/architecture/README.md` 是 plugin canonical 段，
  改动会在下次 `/holo:update` 被覆写。若困扰，只能在 sentinel 外的 gap 补一句现状说明。
- **L13 / L14 / L15 / L16** — 跳过或顺手。L14 值得优先（Index 是 `/todo` 的唯一数据源，
  它自己警告过这种漂移），其余是纯文字残留。

**建议落地顺序**：H2（三行，风险最低）→ H6（纯逻辑）→ H5（一处路径拼接）→ H1（时序调整）→
H3（守卫 + 复验）→ H9 + M2 + M11 + M16（文档/注释单行修正）→ M12/M13/M14（decisions 收口）→
H10（prompt 补声明）。H4 / H7 待 OQ2 / OQ3 澄清后再动。
