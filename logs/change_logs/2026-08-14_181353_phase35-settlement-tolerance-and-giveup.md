# phase35-settlement-tolerance-and-giveup

- **Started**: 2026-08-14 18:13:53 EDT
- **Branch**: main
- **Type**: GO
- **Status**: DONE

## Background / Trigger

Phase 3.5（决策 #72 六段最终关卡）在真实数据上首跑（33m11s / 159 次 LLM
调用）：台账债 38 → 8，段 3 审校发现 12 条、结清 10 条，最终判 FAIL、
Phase 4 被阻。逐条追查这 8 条残留后，发现其中 3 条是**结构性死结**，
再跑多少次都不会变；另有一个洞会在台账清空后变成假 PASS：

1. **长度容忍度两边不一致。** repair 轮循环用决策 #48 的容忍门
   （`min/maxLength` ±10%，且必须整个错误集合都是长度类才放宽）判
   `LENGTH_TOLERANCE_PASS`，而 Phase 3.5 结清 schema 债走的复校是严格
   `validate_only`。实测两条债正好卡在容忍带内（`200 → 208`、`30 → 33`）：
   修复循环判 PASS 不写决议，最终关卡判 unsettled，永久 FAIL。
2. **`$` 根锚点债无法结清。** 一条 `semantic_unparseable`（L3 审校器自身
   输出不可解析，属基础设施故障而非内容缺陷）被按 semantic 内容债记进
   台账；段 2 以「无法定位」静默跳过，而 semantic 类只认决议记录才算
   结清 —— 没有任何环节会给它写决议，永久挂账。
3. **段 4 未结清的审校发现被静默丢弃。** 段 4 有 2 条修不掉（`S040`
   inter_stage_continuity / `S017` irreversible_regression），既不进台账
   也不进最终报告 —— 段 6 只复检程序化层 + 台账债。本次因台账仍有 8 条
   而照样 FAIL，但台账一旦清空，审校发现修不掉也会判 PASS 放行 Phase 4。
4. **没有第二次机会。** 每条债只有一次 repair 事务；事务因安全阀提前
   终止（`L3 gate reemerge` / `max_tier reached`）后即成终局。

## Conclusion and decisions

方向：**Phase 3.5 不自造判定 —— 复用既有权威；未结清项一律回写台账，
台账是判定的唯一输入；每项两次机会，仍失败则记录放弃并放行。**

1. **容忍度对齐**：`_length_tolerance_pass` 提升为公开
   `length_tolerance_pass`，Phase 3.5 的 schema 复校委托给它。语义完全
   保留：只有整个文件的错误集合都是长度类时才放宽。
2. **unverified 债独立成类**：`semantic_unavailable` /
   `semantic_check_crashed` / `semantic_unparseable` 三条规则（审校器
   自身失败）提升为公开 `BACKEND_FAILURE_RULES`，Phase 3.5 对它们走
   **重新检查**而非打补丁 —— 对该文件跑一次**不带 seed** 的完整 repair
   事务（Phase A 全文语义审校本身就是复检，发现的问题自带真实
   `json_path` 并顺势被修）。按 **rule** 判定而非 category，使已写在磁盘
   上的历史行同样被正确归类。
3. **未结清项回写台账**：新增 `append_deferred_repairs()`（按 `issue_key`
   去重；不能复用截断语义的 `write_deferred_repairs`）。段 4 的残留发现
   写入台账，段 6 像对待其它债一样重新裁决 —— 既阻断当次，也活到下次
   运行（省掉重复支付段 3 的审校开销）。
4. **两次机会 + 记录放弃**：`_p35_settle_debts` 加 `attempts=2`；第二次
   必须携带第一次的失败原因并提高 effort，否则只会复现同一终止条件。
   两次仍失败 → 决议行写 `resolution="given_up"` + `attempts` +
   `last_error`。**异常（LLM 不可用 / 崩溃）不算用尽机会** —— 基础设施
   故障保持 error，绝不静默放弃。
5. **放弃语义（用户决策）**：`given_up` 在门里降级为 warning（不阻断
   Phase 4），但必须在 verdict 里单独成段显著列出。`fixed` 决议行
   仍只写给非 revalidatable 类（给 schema 债写 `fixed` 会永久压制它）；
   `given_up` 行所有类别都写 —— 它不声称已修好，只降级严重度，文件
   真被修好时 schema 复校仍会让债自然消失。

## Planned action list

- file: `extraction/repair/protocol.py` → `_BACKEND_FAILURE_RULES` 提升为
  公开 `BACKEND_FAILURE_RULES` + `is_backend_failure()` 判定助手
- file: `extraction/repair/checkers/semantic.py` → 改为消费公开常量
- file: `extraction/repair/coordinator.py` → `_length_tolerance_pass` 提升
  为公开 `length_tolerance_pass`
- file: `extraction/persona_extraction/lifecycle/deferred_repair_log.py` →
  `is_unverified_row()`；`append_deferred_repairs()`；决议行新增
  `resolution` / `attempts` / `last_error`；`read_resolutions()` 返回
  `key → resolution kind` 映射；`append_resolution` 写前去重
- file: `extraction/validation/gates/phase3_5_consistency.py` → L3 新增
  unverified 裁决路线；`given_up` 降级为 warning；模块 docstring 同步
- file: `extraction/persona_extraction/orchestrator.py` →
  `_p35_build_revalidator` 委托容忍判定；`_p35_settle_debts` 两次机会 +
  unverified 分支 + 返回未结清项；段 4 残留回写台账；段 6 verdict 增加
  放弃清单段
- file: `ai_context/decisions.md` + `docs/decisions.md` → 新决策 #74
- file: `ai_context/conventions.md` → §Cross-File Alignment 台账一行更新
- file: `docs/architecture/extraction_workflow.md` → Phase 3.5 段落同步
- file: `docs/todo_list.md` + `docs/todo_list_archived.md` → 条目维护

## Validation criteria

- [ ] 改动的 6 个模块 `python -c "import ..."` 全部无 error
- [ ] `python -m extraction.repair.tests` 全通过（含 `_smoke_l3_gate`）
- [ ] 真实数据复现：用 `extraction/{work_id}` 分支上的实际文件跑复校，
      两条长度债（`200→208` / `30→33`）判为 settled，其余不受影响
- [ ] 真实台账复现：`semantic_unparseable` 行被 `is_unverified_row()`
      识别为 unverified 类
- [ ] `given_up` 决议行使对应债在门里降级为 warning 且 `passed` 不被其阻断；
      无决议行的同一条债仍判 error
- [ ] grep 残留 = 0：`_length_tolerance_pass` / `_BACKEND_FAILURE_RULES`
      两个私有名在仓内无引用；`read_resolutions` 所有调用点已适配新返回类型

## Execution deviations

- 计划外新增 `extraction/repair/__init__.py` 导出（`length_tolerance_pass`
  / `BACKEND_FAILURE_RULES`）—— orchestrator 从包级 API 取，不深入子模块。
- 计划外文档：`docs/requirements.md` §11.10（L3 三路线 + 两次机会 + 回写
  台账 + 放弃语义）、`ai_context/requirements.md`、`ai_context/architecture.md`、
  `extraction/README.md`。原计划只写 `docs/architecture/extraction_workflow.md`，
  但 §Cross-File Alignment 的 `docs/requirements.md ↔ ai_context/requirements.md`
  成对规则要求同步。
- `docs/decisions.md` 两处散文引用旧私有名 `_BACKEND_FAILURE_RULES`，
  随公开化一并改为 `protocol.BACKEND_FAILURE_RULES`。
- `docs/todo_list.md` / `docs/todo_list_archived.md` **未改动**：本轮既未完成
  也未产生 todo 条目（`T-PHASE35-DEFERRED-FIX` 已在上一轮归档）。
- `_p35_settle_debts` 返回类型由 `set[str]` 改为
  `tuple[set[str], list[ConsistencyIssue]]` —— 未结清项必须回传给调用方才能
  回写台账；「无 repair entry」由静默 warning 改为抛异常，走调用方的故障
  路径（wiring bug 不该被当成用尽机会而释放）。
- Step 5 复审新增 6 处计划外改动（详见 §Validation results）：容差守卫折进
  `length_tolerance_pass` 本体 + 同步简化 coordinator 调用点；审校器失败类
  残留不计入机会且不进 re-seed；无 stage 可挂的发现经 `_merge_carried` 并入
  判定；段 2 输入按 severity 过滤；提交面判据加入「本轮是否写过台账」；
  决议行去重改为整行比对。
- 移除计划中的 `is_backend_failure()` helper —— 本轮无调用点，是投机 API。
- 段 4 未结清发现「阻断当次」的原始措辞与「两次机会后放行」冲突，按后者
  （用户决策）统一：它在被发现的这一轮即为 warning。文档口径已随之修正。

<!-- POST phase fills in -->

## Landed changes

Phase 3.5 结清回路补齐：容差判定统一到 `length_tolerance_pass`（守卫折进
函数本体）、unverified 债按 rule 归类并走重跑审校、未结清项回写台账、每文件
两次机会后记录放弃并降级放行，另修复审查出的 4 处假 PASS / 无限重付路径。

## Diff from plan

- 新增：`extraction/repair/__init__.py` 包级导出；`docs/requirements.md` +
  `ai_context/{requirements,architecture}.md` + `extraction/README.md` 同步
  （原计划只改 `docs/architecture/extraction_workflow.md`）。
- 新增（复审驱动）：`_merge_carried`（无 stage 发现并入判定）、段 2 输入
  severity 过滤、提交面判据纳入台账写入、审校器失败类不计入机会 + 不进
  re-seed、决议行整行去重、`append_deferred_repairs` 调用内去重。
- 移除：计划中的 `is_backend_failure()`（无调用点）。
- 未做：`docs/todo_list.md` / `docs/todo_list_archived.md` —— 本轮既未完成
  也未产生 todo 条目。

## Validation results

- [x] 改动模块 `import` 全部无 error
- [x] `python -m extraction.repair.tests` —— 2 个 smoke 模块全过（含容差门
      Scenario C、backend-failure Scenario E）
- [x] 真实数据复现 —— 两条长度债（`200→208` / `30→33`）判为 settled；人为
      超出容忍带后仍报出；structural 错误不被容差接受、混合集合整体拒绝
- [x] 真实台账复现 —— `semantic_unparseable` 行被 `is_unverified_row()`
      识别；错填成 `schema` 类别的 unverified 行不走复验路线
- [x] `given_up` 降级为 warning 且不阻断；无决议行的同一条债仍判 error；
      `fixed` 行只结清 semantic、schema 债仍由文件说了算
- [x] grep 残留 —— 代码与 docs 侧 0 命中（仅 `logs/` 历史日志保留，属豁免面）

## Completed

- **Status**: DONE
- **Finished**: 2026-08-14 18:57:43 EDT
