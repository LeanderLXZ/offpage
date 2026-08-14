# phase35-settlement-loop-fixes

- **Started**: 2026-08-14 12:16:36 EDT
- **Branch**: main
- **Type**: GO
- **Status**: DONE

## Background / Trigger

上一轮 `/go`（commit `1342a50`，Phase 3.5 六段重做，决策 #72/#73）之后跑
`/post-check` 判 **REVIEWED-FAIL**，随后经 `/fix` Auto 模式分发到本轮。

Source review：`logs/change_logs/2026-08-10_164040_phase35-rework-six-segment.md`
（Type: GO, status: REVIEWED-FAIL）。
Findings selected for fix：**H1, M1, M2, M3, MU1**；OQ1 采纳方向 A。
丢弃：L1（留 todo，Auto 模式不自动登记）、L2（跳过，属安全方向）。

三条实质缺陷都落在**结清回路的判定边界**上，与上一轮 `/go` 复审阶段
自查修掉的两个（`rule` 字段缺失、resolution 庇护 schema 债）同族——都是
"某条路径下债被静默认定为已结清 / 已干净"。

**Anti-over-engineering reminder（来自 `/fix` brief，逐字保留）**：
post-review fixes — minimal patches only. No opportunistic refactor /
"while I'm here" cleanup / new abstractions / new tests / new flags. If a
3-line edit solves it, do not extract helpers. Reviewers picked these
findings precisely because they are worth fixing on their own — do not
bundle adjacent rewrites unless the reviewer flagged them.

## Conclusion and decisions

五处定点修复，**不做**任何顺带重构、不加抽象、不加配置键、不加测试文件。

**H1 —— revalidator 异常后同文件其余债被静默结清**（假 PASS）。异常分支
写入 `violation_cache[fpath] = set()` 后 `continue`，该文件的下一条债命中
空缓存、`jpath not in set()` → True → 判 settled。按 OQ1 **方向 A** 修：
异常时缓存**哨兵值**而非空集合，命中哨兵的债一律计 skipped 并各自报出。
选 A 不选 B（一次性报完该文件所有债后跳过剩余行）的理由：A 让 coverage
账本的 `checked` / `skipped` 逐条计数保持准确，而账本的准确性正是本次
重做的承诺之一。

**M1 —— 审校返回不可解析文本被当作"无断裂"**。`_extract_json_array`
对"合法空数组"与"解析失败"都返回 `[]`，下游无法区分。改为解析失败返回
`None`、合法空数组返回 `[]`；`_p35_parse_findings` 收到 `None` 时按后端
失败同路径报阻塞 issue。这是把代码注释里已援引的决策 #70「响亮失败优于
静默半审」真正落实。

**M2 —— Cross-File Alignment 行引用已不存在的常量名**。改
`_REVALIDATABLE_CATEGORIES` → `REVALIDATABLE_CATEGORIES`（上一轮复审中
该常量已转 public）。该行的全部价值就是被 grep 到。

**M3 —— 无 `S###` 文件名的 semantic 债无法结清**（永久 FAIL 死锁）。
`_p35_record_resolutions` 经 `_p35_stage_of` 从**文件名**推导 stage_id，
对 `world/stage_catalog.json` 返回 `None` → 不写 resolution。改用**台账行
自带的 `stage_id`**——它本就是权威来源，无需推导。需让 `ConsistencyIssue`
携带 `stage_id`（L3 层已有该值在手）。

**MU1 —— README 目录树漏列新模块**。补 `cross_stage_projection.py` 与
`cross_stage_review.md` 两行。

**不改**：`is_regression` 判据、#48 容差门触发条件、`_p35_stage_of` 本身
（段 5 重投影仍按文件名定位 stage，那里语义正确）。

## Planned action list

- file: `extraction/validation/gates/phase3_5_consistency.py` → H1 哨兵值
  改造（`_check_deferred_ledgers` 的 revalidation 异常分支）+ M3 所需的
  `ConsistencyIssue.stage_id` 字段
- file: `extraction/persona_extraction/orchestrator.py` → M1
  （`_extract_json_array` 返回 `None` 语义 + `_p35_parse_findings` /
  `_review_one` 相应分支）+ M3（`_p35_record_resolutions` 改用
  `issue.stage_id`）
- file: `ai_context/conventions.md` → M2 常量名更正
- file: `extraction/README.md` → MU1 目录树补两行

## Validation criteria

- [ ] `python -c "import extraction.persona_extraction.orchestrator"` 无报错
- [ ] `python -c "import extraction.validation.gates.phase3_5_consistency"` 无报错
- [ ] **H1 回归**：同文件 2 条 schema 债 + revalidator 全程抛异常 → 报出
      **2 条** issue（修复前为 1 条），coverage `skipped` 计满
- [ ] **H1 不误伤**：revalidator 正常时行为不变（已结清的债仍自动销账）
- [ ] **M1**：`_extract_json_array` 对合法空数组返回 `[]`、对散文 /
      截断 JSON 返回 `None`；三者下游可区分
- [ ] **M1 端到端**：审校返回不可解析文本时产出阻塞 issue 而非 0 finding
- [ ] **M3**：`world/stage_catalog.json` 的 semantic 债能写出 resolution，
      且该 resolution 能在下次复扫中被识别为已结清
- [ ] **M2 grep**：`_REVALIDATABLE_CATEGORIES`（带下划线）在仓内 0 命中
- [ ] **MU1 grep**：`cross_stage_projection.py` / `cross_stage_review.md`
      出现在 `extraction/README.md` 目录树段
- [ ] repair 既有 smoke 通过（`python -m extraction.repair.tests`）
- [ ] 结清回路端到端复测（schema 自愈 / semantic 凭 resolution /
      resolution 不庇护重新写坏的 schema 债）仍全部通过
- [ ] 反过度工程自查：改动文件数 = 4，无新增文件、无新增配置键、
      无新增抽象

## Execution deviations

1. **计划 4 个文件，实际 6 个** —— Step 4 增改
   `docs/requirements.md` §11.10 与 `docs/architecture/extraction_workflow.md`
   §7 各两处行为澄清：①「复验拿不到结论 ≠ 已结清」，复验失败标记按文件
   生效、该文件每条债各自记 skipped；②审校「返回不可解析内容」与「调用
   失败」同属响亮失败，都不得与「审过且干净的空发现」混同。两处都是本轮
   代码行为的文档面，属 Step 4 的本职（文档跟随实现），不是顺带扩张。

2. **`_p35_record_resolutions` 之外，`_p35_settle_debts` 的 SourceContext
   `stage_id` 也改用台账值**（1 行）。同一 M3 根因：从文件名推导 stage
   在 work 级产物上得不到结果，那里原本会退化成假的 `"phase3.5"`。

3. **`_review_one` 的调用失败 issue 对齐为 `category="semantic"` +
   `rule="cross_stage_review_unavailable"`**（2 行）。原先把规则名塞在
   category 位；M1 新增的「不可解析」分支是它的同族路径，两者形状必须
   一致，否则报告里同一类问题呈现两副面孔。

4. **Step 5 自查修掉一处本轮引入的计数缺陷**：`_dedupe_findings` 原以
   `(file, json_path, rule)` 为键，而 M1 新增的「审校不可解析」issue 不带
   file / json_path —— 于是**多个失败窗口会被折叠成一条**，低报未审范围。
   键补上 `location`（每窗口唯一）。不影响原有的重叠去重语义：两个窗口
   报同一断裂时 location 同为 `subject/stage_id`。已双向验证。

5. **未新增决策条目** —— 本轮是决策 #72 实现的缺陷修复，不是新的争议性
   决策（准入判据：存在像样备选、且未来读者可能重新提出）。OQ1 的哨兵
   方案 A vs B 取舍记在本日志 §Conclusion，不进 decisions 索引。

6. **未动** `ai_context/architecture.md` —— 其 Phase 3.5 行在摘要层级上
   仍然准确，本轮的边界细节属 docs/ 层；按 ai_context 维护规则（每条
   ≤ 5 行、细节推到链接来源）不再加载。

<!-- POST phase fills in -->

## Landed changes

`/post-check` 判 REVIEWED-FAIL 后的跟进修复：结清回路上的三条判定边界缺陷
（H1 假 PASS / M1 静默当作干净 / M3 永久 FAIL 死锁）+ 两处引用与目录树同步
（M2 / MU1），另在 Step 5 自查中补掉一处本轮引入的失败窗口计数折叠。
文件级明细见本次 commit diff。

## Diff from plan

见上方 §Execution deviations 六条。要点：计划 4 文件、实际 6（多出的两个是
Step 4 的行为澄清文档同步）；M3 的根因在两处而非一处，SourceContext 的
stage_id 一并改；`_review_one` 的失败 issue 形状对齐；Step 5 自查修掉
`_dedupe_findings` 的键缺失；未新增决策条目、未动 ai_context/architecture.md。

## Validation results

- [x] `import extraction.persona_extraction.orchestrator` — 无报错
- [x] `import extraction.validation.gates.phase3_5_consistency` — 无报错
- [x] **H1 回归** — 同文件 2 条 schema 债 + revalidator 全程抛异常 → 报出
      **2 条**（修复前 1 条），coverage `checked=2 hit=0 skipped=2`，
      两条各自携带 `stage_id`
- [x] **H1 不误伤** — revalidator 正常时三种情形行为不变：全部已结清 → 0
      issue；两条仍违规 → 2；一条结清一条仍在 → 1
- [x] **M1** — `_extract_json_array` 三态可区分：合法空数组 `[]` /
      有内容数组与围栏包裹正常解析 / 散文·截断 JSON·空串均 `None`
- [x] **M1 端到端** — `_p35_parse_findings` 对不可解析文本产出 1 条
      `error` + `rule=cross_stage_review_unparseable`；对 `[]` 产出 0 条
- [x] **M3** — `world/stage_catalog.json` 债的 `_p35_stage_of` 推导为
      `None`，但 `issue.stage_id=S049` 来自台账；写 resolution 后复扫未决
      归零
- [x] **M2 grep** — `_REVALIDATABLE_CATEGORIES`（带下划线）在
      extraction/docs/ai_context 中 0 命中
- [x] **MU1 grep** — `cross_stage_projection.py` / `cross_stage_review.md`
      均出现在 `extraction/README.md` 目录树（行 296 / 310）
- [x] repair 既有 smoke 通过（`_smoke_triage` + `_smoke_l3_gate`）
- [x] 结清回路端到端复测 — schema 自愈 / semantic 凭 resolution /
      resolution 不庇护重新写坏的 schema 债，三条全过
- [x] 反过度工程自查 — 零新增文件（除 PRE 日志）、零新增配置键、
      零新增抽象；代码净改动 +82/−32
- [x] 额外（Step 5 自查后补）— `_dedupe_findings` 双向验证：2 个失败窗口
      保留 2 条、重叠窗口同一断裂仍折叠为 1 条
- [x] pyflakes 干净（仅剩 1 处既有 f-string 告警，非本轮引入）

**未验证（需真实运行）**：与上一轮同——段 2/3/4 的 LLM 环节仍未端到端跑过。
本轮修的三条缺陷恰好都只在真实运行时显形，静态验证以构造用例覆盖。

## Completed

- **Status**: DONE
- **Finished**: 2026-08-14 12:30:02 EDT
