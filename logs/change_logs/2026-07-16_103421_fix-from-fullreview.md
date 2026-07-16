# fix-from-fullreview

- **Started**: 2026-07-16 10:34:21 EDT
- **Branch**: main
- **Type**: GO
- **Status**: DONE

## Background / Trigger

本会话跑了一轮 `/full-review` 全仓对齐审计（决策 #62 落地后的首次），报告归档在
`logs/review_reports/2026-07-16_100448_opus-4-8_full-review-findings.md`（commit `69ee115`）。
审计用 4 个 sub-agent 并行分片（Code 三片 + Surface 一片）+ 主循环独立复核，产出
H=10 / M=20 / L=16 / OQ=6 共 52 条。

随后经 `/fix` Auto triage（经 `/go` 落地）。AI 原推荐 fix=13 / todo=17 / skip=16，
6 个 OQ 因上一轮报告的 §Recommendations 未给每 OQ 独立处置而记为 `unknown`，
在 Step 4a.0 逐条询问 —— **用户对 OQ1–OQ6 全部选择 Adopt**，由此把 H4 / H7 / M15 / M5
从 todo 提升为 fix，并扩大 H3 的范围、新增 conventions.md（OQ5）与 smoke 断言（OQ6）。
最终 fix 集 = 17 条 findings + 6 条 OQ 决议。

审计的核心结论：`ai_context/` 全线干净、决策编号 lockstep 双向零差集、代码侧 T3 迁移
零残留；**实质问题集中在「决策 #62 的意图未在代码中完整实现」** —— 删了 T3，但全文重写
经 `$` 锚点 + T2 无复验复活；语义门在有 L0–L2 error 时静默失效；数组内 schema 违规三层
都修不动。另有两条编排层缺陷（reconcile 时序、中文 work_id 的 git scope 守卫）命中主用例。

## Conclusion and decisions

**方向**：最小补丁修 17 条 + 落实 6 条 OQ 决议。不做顺手重构。

**本轮改**（按 finding）：

- repair 层治本三条：H3（T2 加类型守卫 + verify_fn + 按 OQ1 把 `$` 锚点移出 T2 路由）、
  H4（动态算 `l3_file_set`，按 OQ2）、H5（数组下标路径拼接改 `[i]`）。
- 编排层两条：H1（reconcile 移到分支切换之后）、H2（porcelain 加 `core.quotePath=false`）。
- defer 语义两条：H6（崩溃按 entry 逐个判定）、H7（台账收 coverage_shortage warning，按 OQ3）。
- 红线一条：H9（`Character B` → 占位符）+ OQ5（conventions §Generic Placeholders 范围扩到代码注释）。
- prompt 一条：H10（3 个 phase 1 lane 模板补「上限不是配额」，从既有模板复用措辞）。
- 文档/契约六条：M2（config 说明写反）、M11（source_note schema 的 T3 描述）、
  M12/M13/M14（decisions 归档 #48/#55/#25a 收口）、M16（枚举补两项）、M15（works/ 补分支限定，按 OQ4）。
- 测试一条：M5（smoke 加 FIELD_ALLOCATION ⇄ schema 断言，按 OQ6）。

**本轮不改**（已明确留 todo，Step 5 不要顺手做）：H8（rate_limit ISO 热循环 —— 触发条件是
推断，建议先加观测再修）、M1/M9（timeline_anchor 指令冲突 + lane_scope 散文）、M3
（ContextRetriever off-by-one）、M4（stage_catalog 不该进 repair）、M6/M7/M8（json_repair
两条 + communicate 挂起）、M10（#11e 裁剪规则覆盖不全）、M17（`_smoke_triage` 失效 ——
是 H3/H4 的下游，本轮修完后它可能自愈也可能仍需改断言，不在本轮范围）、M18/M19/M20，
以及全部 16 条 Low。

**授权例外**：用户经 OQ6 明确采纳「断言加在 smoke test」，覆盖 fix brief 中
anti-over-engineering 的 "no new tests" 约束 —— 仅 M5 这一处允许新增断言，不扩展。

## Planned action list

- file: `extraction/persona_extraction/orchestrator.py` → **H1**: `reconcile_with_disk`
  (:3821) 移到 `create_extraction_branch` (:3890) 之后。
- file: `extraction/persona_extraction/core/git_utils.py` → **H2**: `preflight_check`
  (:83-94) + `checkout_main` (:161-169) 的 `git status --porcelain` 加
  `-c core.quotePath=false`（照抄 `commit_stage` :208-215）。
- file: `extraction/repair/fixers/source_patch.py` → **H3**: 接受并使用 `verify_fn`
  （与 `local_patch.py` 同构），patch 后即时 scoped 复验才算 resolved。
- file: `extraction/repair/field_patch.py` → **H3**: `apply_field_patch` 根替换分支
  (:24-26) 加类型守卫（新值类型须与原文档一致）。
- file: `extraction/repair/coordinator.py` → **H3**: `_build_fixers` (:108-112) 给 T2 传
  `verify_fn`；**H4**: `l3_file_set` / `had_semantic` (:295-298) 改为动态计算，Phase A 后对
  已修完 L0–L2 error 的文件补跑 L3；**H7**: 确认超 cap 的 coverage_shortage 能进 defer 路径。
- file: `extraction/repair/protocol.py` → **H3/OQ1**: `$` 锚点的三类 issue 移出 T2 路由。
- file: `extraction/repair/checkers/schema.py` → **H5**: `absolute_path` 的 int 下标拼
  `[i]` 而非 `.{i}`。
- file: `extraction/persona_extraction/lifecycle/deferred_repair_log.py` → **H6**:
  `deferrable_issues` (:61-71) 改按 entry 逐个判定崩溃；**H7/OQ3**: 一并接受
  `coverage_shortage` 的 warning 级 issue。
- file: `extraction/persona_extraction/core/run_metrics.py` → **H9**: `Character B` → `<character_id>`。
- file: `ai_context/conventions.md` → **OQ5**: §Generic Placeholders 项目补充里把权威文档
  范围显式扩到 `extraction/**/*.py` 注释。
- file: `extraction/persona_extraction/prompts/analysis_foundation.md` /
  `analysis_candidate_characters.md` / `analysis_stage_plan.md` → **H10**: 补「maxLength /
  maxItems 是硬上限、不是配额」声明。
- file: `extraction/config.toml` + `extraction/persona_extraction/core/config.py` → **M2**:
  `defer_unresolved_semantic` 说明改为与 `DEFERRABLE_CATEGORIES` 一致（四类可 defer，
  仅 json_syntax 硬 ERROR）。
- file: `extraction/persona_extraction/tests/_smoke_4_lane_merge_and_slice.py` → **M5/OQ6**:
  加断言 `FIELD_ALLOCATION ∪ PROGRAM_INJECTED_FIELDS == schema 顶层属性集`。
- file: `schemas/shared/source_note.schema.json` → **M11**: `triage_round` 的 description
  同步为「1 = max_tier 封顶后；2 = L3 gate 后」。
- file: `docs/decisions.md` → **M12**: #48 触发点改「tier 封顶后」+ Plumbing 指向
  `coordinator.py:720-725`；**M13**: #55 标题 + 正文补 #62 收口注；**M14**: #25a 补
  `> **经 #62 收紧**` 注。
- file: `ai_context/skills_config.md` → **M15/OQ4**: §Do-not-commit 的 `works/` 补
  「（main / 框架提交）」限定。
- file: `docs/architecture/schema_reference.md` → **M16**: :226 别名 type 枚举补
  `昵称` / `绰号`（8 → 10 项）。

## Validation criteria

- [ ] `python -m compileall -q extraction` 退出码 0
- [ ] import smoke：`extraction.repair.{coordinator,protocol,field_patch,checkers.schema,fixers.source_patch}`
      + `extraction.persona_extraction.{orchestrator,core.git_utils,core.run_metrics,lifecycle.deferred_repair_log}`
      + `extraction.persona_extraction.core.config` 无 error
- [ ] 8 个 smoke test 回归：7 个原本 PASS 的必须仍 PASS（`_smoke_triage` 本轮不修，
      允许仍 FAIL，但需记录其状态是否因 H3/H4 而变化）
- [ ] **H3 专项**：构造 json_path=`$` 的 T2 修复场景 → 断言文件不被整体替换成非法类型
      （复现审计中「文件被写成 `[]` 且 passed=True」的场景，断言现已被守卫拦住）
- [ ] **H4 专项**：构造「先有 L1 error、T0 修完」的场景 → 断言语义 checker 被调用 ≥1 次
      （审计实测当前为 0 次）
- [ ] **H5 专项**：`extract_subtree(doc, "$.relationships[1].attitude")` 可解析；
      SchemaChecker 对数组内违规产出的 json_path 能被 `field_patch` 成功导航
- [ ] **H6 专项**：`deferrable_issues([crash, semantic])` 返回 `None`（审计实测当前返回 DEFER）
- [ ] **H7 专项**：超 cap 的 coverage_shortage（severity=warning）能进 deferrable 集而非硬 ERROR
- [ ] **H2 专项**：中文路径的 `git status -c core.quotePath=false --porcelain` 解析后
      `startswith(scope)` 为 True
- [ ] 34 个 schema 元校验全部合法（`jsonschema` `check_schema`）
- [ ] grep 残留 = 0：`Character B|Character A|Character E|Character D|Character F|Character G|<work_id>` 在全仓
      （排除 `.git` / `logs/` / `works/` / `sources/` / `todo_list_archived.md`）
- [ ] `grep -c '不是配额|硬上限'` 在三个 phase 1 lane 模板均 ≥ 1
- [ ] decisions 索引 ↔ 归档编号 lockstep 仍为双向零差集

## Execution deviations

- **H1 落点与计划不同（更优）**：计划写「把 reconcile 移到 `create_extraction_branch`
  之后」。实测发现 resume 与 fresh-start **两条路径都汇入 `run_extraction_loop`**，
  而它在 `:2644-2650` 的 `try` 内自己切分支。故把 reconcile 从 `run_full` 移入
  `run_extraction_loop` 切分支之后这一个点，同时覆盖两条路径（而非在两处各加一次）。
  副作用（可接受）：resume 提示里的 "Completed: X/Y" 现在打印的是 reconcile **之前**
  的计数，随后 `[RECONCILE]` 行会报告它改了什么 —— 顺序更诚实。
- **H3 的 OQ1 落地形态**：没有逐个 rule 枚举，而是提炼出根因谓词
  `is_unpatchable_root`（`json_path ∈ {"$", ""}` 且 `category != "json_syntax"`）→
  `NO_FIX_TIER = -1`。coordinator 的 `fixers.get(-1) → None → continue` 天然让这类
  issue 落入 defer，**无需改 coordinator**。`json_syntax` 显式豁免 —— 它由 T0 在原始
  文本上修（`programmatic.py:68-70`），不走 `apply_field_patch`，且不可 defer，
  一刀切会把它变成硬 ERROR 回归。
- **H6/H7 合并为一次重写**：两者都落在 `deferrable_issues` 同一函数，拆成两次编辑
  反而更难读，故一次改完（新增 `_is_deferrable_issue` / `_is_coverage_shortage`
  两个私有 helper）。
- **`_smoke_triage.py` 状态变化（M17 本轮不修，但需记录）**：仍 FAIL，但语义已变 ——
  修复前 `[A] passed=True notes=0`（**假阳性：文件被写成 `[]` 却报 PASS**），
  修复后 `[A] passed=False notes=0`（**不再假阳性**）。断言
  `expected at least one accepted note` 仍不满足，因为该场景本就依赖 H4 修复前被
  跳过的语义 checker 产出 `fact_mismatch`。M17 已留 todo；修它需要重构 fixture
  （给角色快照补 `target_baseline.json`），超出本轮范围。
- **Step 5 自查抓到并修掉的自伤回归（重要）**：OQ1 的初版实现把**所有** `$` 根锚点
  issue 一律判为 `NO_FIX_TIER`。实测发现这会误伤 `schema_required` / `schema_type`
  等**根级 schema 问题**——`SchemaChecker` 在文档根出错时 `absolute_path` 为空即产出
  `json_path="$"`，而"缺顶层 required 字段"是极常见且 **T0 本来就能机械修复**的
  （`programmatic._fix_missing_required` 打的是 `$.{field}` **子路径** + 确定性默认值，
  从不动根本身）。一刀切会让它们全部变成"不可修 → defer"。
  **修正**：谓词更名 `is_unpatchable_root` → `is_root_anchored`，路由改为"根锚点
  **永不升 LLM 层**"——`max_tier` 钳到 T0；只有本就起步于 LLM 层（`start_tier >= 1`）
  的才 `NO_FIX_TIER`。实测确认 `schema_required@$` 仍由 T0 补齐、三类无解 issue 仍
  正确 defer、`json_syntax` 阶梯不变。
- **连带补的两处异常兜底**（同属 H3 根守卫的下游，不修会崩 worker，而按 H6 崩溃
  现在硬停 stage）：`local_patch.py:125` 的 `except` 增补 `TypeError`；
  `programmatic.py` 的 `_try_fix` 调用点包 `try/except TypeError → 视为不可修`
  （T0 在"根应为 array 但实为 object"时会撞上新守卫）。旧行为是 T0 默默把根替换成
  `[current]`——同样是全文破坏，只是无声。
- **Step 5 复审补全 H1 的未覆盖路径**（分片 B 报告，就地修）：`extraction_branch`
  的补齐原在 `run_full:3889-3894`，**位于 resume 分支两个 `return` 之后**。一份
  legacy `pipeline.json`（该字段为空 + `phase_1_5` done）走 resume → `run_extraction_loop`
  的 `if pipeline.extraction_branch:` 守卫为假 → 不切分支 → reconcile 仍在 main 上跑
  → 正是 H1 要消灭的灾难态。**修正**：把补齐提到 pipeline load 之后、resume 判断之前；
  删掉此时已不可达的 `elif` 分支。（该洞非本轮引入——改动前 reconcile 无条件在 main
  上跑，属"总是坏"；但半修的 High 不可接受，故就地补全。）
- **Step 5 复审补的第二处 H4 收口**（分片 A 报告，就地修）：L3 gate 的建集只看
  `modified_files`，会对**仍带 L0–L2 error** 的文件跑语义复审——与本 log 上文
  「对已修完 L0–L2 error 的文件补跑 L3」的自述、以及 coordinator 新注释自己援引的
  设计理由（不为 schema 已坏的文件烧 token）都矛盾，且那次调用买不到任何决策
  （该轮注定 FAIL 在那个 error 上）。**修正**：`gate_targets` 扣掉本轮 recheck 仍报
  error 的文件；Phase C 的 fallback 同样只对 L0–L2 干净的文件跑（`run_layer` 会绕过
  pipeline 的跳过规则）。实测：仍报错文件语义调用 0 次、已修干净文件 1 次。
- **Step 5 复审补的 docs/requirements.md §11.4 同步**（分片 C 报告 High-1 + M2 + M3）：
  该文件**整体漏出了本轮文档同步**（不在 Planned action list 里，也不属已知的
  M18/M19/M20）。它是权威规格，却把本轮修掉的 bug 写成"当且仅当"条件：
  `:1887-1890` 的「L3 gate 触发条件 = Phase A 有过 L3 issue **且** 本轮被改」正是
  H4 的缺陷本身，下一个读者会照它改回去。一并修的还有：`:1819/:1837/:1843` 的
  L3_files 伪代码块（同一 bug 的另一处载体）、`:1850` 的 defer 判据（缺
  coverage_shortage + 仍是摊平口径）、`:1764` 的 T2 行（缺即时复验）、`:1897` 的
  LLM 预算模型（M ≡ N 后失真），并补上此前规格从未记载的根锚点路由规则。
  `ai_context/requirements.md` §11 是三行指针、不含 tier 细节，lockstep 无需跟随。
- **越界（保留 + 记录）**：`ai_context/skills_config.md` 的 `users/` bullet 顺带加了
  `users/_template/ 除外`。M15/OQ4 只要求改 `works/`。事实正确（`.gitignore:37-39`
  `users/*` + `!users/_template`，`git ls-files users/` 确有 `_template/**` 跟踪），
  与 `works/` 那条同属"绝对措辞与实际跟踪状态不符"，故保留。
- **未改动的计划项**：无。计划清单 17 条 findings + 6 条 OQ 决议全部落地。
- **未越界（其余）**：本轮未顺手修任何留 todo 的 finding（H8 / M1 / M3 / M4 /
  M6-M10 / M17-M20 / L1-L16）。期间注意到 `source_patch.py:6-9` 的 docstring 重试
  阶梯描述与实际不符（= M3，已留 todo），**未顺手改**。

<!-- POST phase fills in -->

## Landed changes

`/full-review` 17 条 findings + 6 条 OQ 决议一次落地，覆盖 24 个文件。核心是把
决策 #62「删掉 T3 全文重跑」的**意图在代码里补齐**——删了 T3，但全文重写经
`$` 根锚点 + T2 无复验复活（实测可把快照写成 `[]` 并报 PASS）；语义门在有
L0–L2 error 时静默失效（实测调用 0 次）；数组内 schema 违规三层都修不动。
另修两条命中主用例的编排层缺陷（reconcile 早于切分支、中文 work_id 的 git
scope 守卫失效）、defer 语义两条（崩溃被掩盖、薄内容硬停机）、一条 main 上的
真实角色名泄漏，以及 prompt / config / schema / decisions 归档的对齐。
文件级明细见本次 commit diff。

## Diff from plan

- **计划全部落地**，无删减。
- **新增 6 项**（均为 Step 3/5 自查与复审抓出、就地修，详见 §Execution
  deviations）：OQ1 一刀切回归修正、两处 `TypeError` 兜底、H1 的 legacy
  pipeline 路径补全、`is_coverage_shortage` 去重、L3 gate + Phase C 对仍报错
  文件的白烧收口、`docs/requirements.md` §11.4 整体同步。
- 后两项是计划外但必要：前者是我自己引入的内部不一致，后者是权威规格把已修
  的 bug 写成"当且仅当"条件（漏出了 Step 4 的同步清单）。

## Validation results

- [x] `python -m compileall -q extraction` — 退出码 0
- [x] import smoke（11 模块，含本轮全部改动文件）— 无 error
- [x] 8 个 smoke 回归 — 7 PASS；`_smoke_triage` 仍 FAIL（M17 已知，本轮不修）。
      **状态实质变化**：修复前 `[A] passed=True notes=0`（假阳性：文件被写成
      `[]` 却报 PASS），修复后 `[A] passed=False notes=0`（不再假阳性）
- [x] **H3 专项** — 复现审计场景：文件保持原样（不再被替换成 `[]`）、
      `passed=False`（假阳性消除）、不崩溃
- [x] **H4 专项** — T0 修完 L1 error 后语义 checker 调用 1 次（审计时 0 次）；
      且仍报错的文件语义调用 0 次（新收口，不白烧）
- [x] **H5 专项** — `$.relationships[1].attitude` 可导航；`_build_json_path`
      对数组下标产出 `[i]` 形式
- [x] **H6 专项** — `deferrable_issues([crash, semantic])` → `None`（硬停）；
      8 个边界用例全部符合预期
- [x] **H7 专项** — 超 cap 的 `coverage_shortage`（warning）→ DEFER 而非硬 ERROR
- [x] **H2 专项** — 中文路径 `startswith(scope)` 为 True；scope 外仍正确容忍
- [x] **回归专项** — 根级 `schema_required` 仍由 T0 补齐（OQ1 一刀切回归已消除）
- [x] 34 个 schema 元校验 — 全部合法
- [x] 真实名残留 grep（全仓，排除豁免集）— 0
- [x] 三个 phase 1 模板「不是配额」声明 — 各 ≥1
- [x] decisions 索引 ↔ 归档主编号 lockstep — 双向零差集
- [x] `smoke_6` 反向验证 — 注入未分配的 schema 属性后确实报 FAIL（非摆设）

## Completed

- **Status**: DONE
- **Finished**: 2026-07-16 11:07:09 EDT
