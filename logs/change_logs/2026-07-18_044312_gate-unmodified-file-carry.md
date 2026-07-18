# gate-unmodified-file-carry

- **Started**: 2026-07-18 04:43:12 EDT
- **Branch**: main
- **Type**: GO
- **Status**: PRE

## Background / Trigger

用户 `T-GATE-UNMODIFIED-FILE-CARRY /go`。该 todo 由 `/post-check`（对 commit
`e67abb5` / 决策 #66）的 **H1（High，CONFIRMED）** 经 `/fix` triage 登记而来，
见 `docs/todo_list.md` §Next 与
`logs/change_logs/2026-07-17_112727_gate-scoped-recheck.md` 的 review 回写。

**缺陷**：`coordinator.py` 的 `gate_targets = (l3_file_set & modified_files) -
still_broken` 把「本轮没有产生任何 patch 的文件」整体排除在 L3 gate 之外。决策
#66 的 `_gate_scope`「携带未修语义 path」只对**已进 gate_targets 的文件**生效，
覆盖不到「文件整体未被触碰」这一半。

失效链（两文件、均 L0–L2 干净）：F 带不可修语义 error（无 source / apply 失败 →
F 本轮零 patch），G 本轮可修 → `modified_files={G}`，F 不进 gate_targets、从不被
复检 → `combined_blocking` 里没有 F 的 issue → `tracker.diff` 判其 **resolved**
→ `current_issues` 清空后 break → Phase C 因 `gate_ever_ran=True` 走 **reuse**
分支（而非全文 fallback），`last_gate_issues` 只含 G 的结果 → **PASS**。F 上那条
Phase A 明确报出、从未修好的语义 error 静默进 commit。

**pre-existing**：旧的全文 gate 有完全相同的 `& modified_files` 门控，同样不复检
未修改文件；#66 只是让这个洞变得显眼。

## Conclusion and decisions

**根因定位在 `coordinator.py:494`**：

```python
combined_blocking = recheck_blocking + gate_blocking
report = tracker.diff(current_issues, combined_blocking)
```

本轮未被 gate 的文件，其语义 issue 在这一行**没有任何来源能把它放回集合**，于是
下一行的 diff 判它 resolved。

**采用修法 C（用户 2026-07-18 拍板）—— 轮内携带 + Phase C 同步**：

- 在 494 行把「本轮未被 gate 的文件的语义 issue」**原样携带**进
  `combined_blocking`。判据：没复检 = 状态未知 = fail-closed 保持原样。
- 已被 gate 的文件**无需携带**——`_gate_scope` 会把该文件所有未修语义 path 放进
  scope，gate 结果已对它们做出判决，再携带会重复计数。
- 携带集同样按 `accepted_fps` 过滤（与 `recheck_blocking` 一致），避免已被 triage
  接受的 source_inherent issue 被永久携带。
- 新增 `outstanding_semantic`（= 本轮 gate 结果 + 携带集），在三个安全阀 break
  **之前**赋值，使其能跨 break 存活；Phase C 的 reuse 分支改用它替代
  `last_gate_issues`（后者语义上只是它的子集，替换后成为死变量，一并删除）。

**为何不选 A / B**（记录取舍，避免未来重提）：
- A（只改 Phase C 兜底）只修**出口**判决；轮内 diff / 三个安全阀 / `resolved=N`
  日志仍是错的，且「All blocking issues resolved」仍可能提前 break。
- B（把带未修语义 issue 的干净文件也纳入 gate_targets）会**每轮每文件多烧一次
  LLM 调用**去复 confirm 一个「因为没人能修才没被改动」的问题，与 #66「不为没改
  的东西付复检成本」相悖。
- C 在源头修正账目，diff / 安全阀 / 日志 / 提前 break 全部自动变准确，且零 LLM
  成本增加。

**边界**：不动 `gate_targets` 的 `& modified_files` 门控本身（gate 仍只复检被改
过的文件，#66 的定点化收益保住）；不动 Phase C 的 `gate_ever_ran` 分支条件；不动
L1（`gate_blocking` 不过滤 `accepted_fps`，方向保守=假 FAIL，另案）。

## Planned action list

- file: `extraction/repair/coordinator.py:~317` → 新增
  `outstanding_semantic: list[Issue] = []`；删除 `last_gate_issues` 声明
- file: `extraction/repair/coordinator.py:~494` → 计算 `carried_semantic`
  （category=="semantic" 且 file 不在 `gate_scopes` 且不在 `accepted_fps`）；
  `combined_blocking` 加上它；赋值 `outstanding_semantic = gate_blocking +
  carried_semantic`（置于安全阀 break 之前）
- file: `extraction/repair/coordinator.py:~483` → 删除 `last_gate_issues = gate_blocking`
- file: `extraction/repair/coordinator.py:~539-546` → Phase C reuse 分支改用
  `outstanding_semantic`（logger / `_emit` / `extend` 三处）
- file: `extraction/repair/tests/_smoke_l3_gate.py` → 新增场景 G：G 文件走 T0 可修
  的 schema minLength（制造「本轮有 patch → gate 运行」），F 文件带不可修语义
  error（无 source_context → T2 跳过 → F 永不被改动）→ 断言 **FAIL** 且 F 的
  issue 出现在结果里（修复前此场景会 PASS）
- file: `ai_context/decisions.md` + `docs/decisions.md` → #66 补充边界（本轮补齐
  「文件整体未被触碰」那一半）或新增条目，Step 4 依 lifecycle check 决定
- file: `docs/requirements.md` §11.4 gate 段 → 去掉本轮已修复的「代价」说明并改述
- file: `docs/architecture/extraction_workflow.md` → 同步
- file: `docs/todo_list.md` + `docs/todo_list_archived.md` → 完成后归档该条目 +
  刷新 Index

## Validation criteria

- [ ] `python -c "import extraction.repair.coordinator"` 无 error
- [ ] `python -m extraction.repair.tests._smoke_l3_gate` 全场景（A–F 原有 + 新增 G）过
- [ ] **新增场景 G 断言 FAIL** —— 且验证其针对性：临时回退携带逻辑时该场景应 PASS
      （证明它真的抓的是本缺陷，不是恒真断言）
- [ ] `grep -n "last_gate_issues" extraction/repair/coordinator.py` = 0（无悬挂引用）
- [ ] `python -m extraction.repair.tests._smoke_triage` 与改动前同状态（该 smoke 在
      clean HEAD 即失败，pre-existing，只需确认未被本轮进一步破坏）

## Execution deviations

- **场景 G 首版无效，已重做**：初版用 `minLength` 超短制造「T0 可修的 G 文件」，
  但 `ProgrammaticFixer._fix_string_length` **故意不 pad `minLength`**（补内容 =
  编造，见其 docstring / OQ2），只 truncate `maxLength`。结果 T0 修不动 G →
  `No patches applied` → `gate never ran` → Phase C 走**全文 fallback** 重新发现
  F 的问题 → 测试虽然 FAIL 但**原因不对**，中和修复后仍 FAIL（即断言恒真、抓不到
  本缺陷）。改用 `maxLength` 超限（200 → 上限 150）让 T0 确定性截断后，
  `gate_ever_ran=True`、Phase C 走 reuse 分支，才真正命中目标路径。
  —— 这条是 PRE「验证其针对性」标准直接抓出来的，否则会留下一个假阳性回归测试。
- **针对性已实证**：临时中和携带逻辑后 `_smoke_l3_gate` exit=1，断言输出
  `Repair PASSED / Final issues: 0`（缺陷如实复现）；恢复后 exit=0。

<!-- POST phase fills in -->

## Landed changes

按修法 C 关闭「本轮零 patch 的文件其未修语义 issue 被判 resolved → Phase C
gate-reuse 报 PASS」这条已确认的假 PASS：在 `combined_blocking` 处原样携带这些
issue（fail-closed），新增 `outstanding_semantic`（gate 结果 + 携带集，安全阀
break 前赋值）供 Phase C 使用并替代删除 `last_gate_issues`。决策 #67；回归测试
`_smoke_l3_gate` 场景 G。

## Diff from plan

- **计划外（复审驱动，属同一缺陷的正确性收尾）**：携带判据由 `gate_scopes` 改为
  新增的 `gated_files`（只在 gate 真跑的分支内填充）。`gate_scopes` 是无条件构建
  的，用它当「被 gate 过」的判据会在 `l3_gate_enabled=False` 且 `run_semantic=True`
  时让文件既不被 gate 也不被携带 —— 在另一个配置下重开本条要堵的洞。当前生产不可
  达（唯一 `l3_gate_enabled=False` 的调用点同时关了 `run_semantic`），属潜伏缺陷。
- 决策条目形态：新增 #67 而非 supersede #66（#66 = 已进 gate 的文件**内部** scope；
  #67 = 文件**整体**未进 gate，两者互补不重叠，#66 无需改动）。
- 其余按计划；todo 条目已归档 + Index 刷新。

## Validation results

- [x] `import extraction.repair.coordinator` — IMPORT OK
- [x] `_smoke_l3_gate` A–G 全过（exit=0）
- [x] **场景 G 针对性已实证**：临时中和携带逻辑 → exit=1，断言输出
  `Repair PASSED / Final issues: 0`（缺陷如实复现）；恢复 → exit=0。首版用
  `minLength` 的写法无效（T0 故意不 pad → 无 patch → gate 没跑 → Phase C 走全文
  fallback → FAIL 但原因不对），改 `maxLength` 后才命中 reuse 路径
- [x] `grep last_gate_issues` = 0（无悬挂引用）
- [x] `_smoke_triage` 当前 exit=1 = clean HEAD exit=1（pre-existing，未被本轮进一步破坏）
- [x] todo Index ↔ 正文一致（Next 4/4、Discussing 8/8、Total 12）

## 待观察 / 已知未做

- **`is_regression` 会比以前更早触发**（复审 Code L3，属预期副作用）：旧代码把未
  gate 文件的 semantic issue 误记为 `resolved`，虚增了 `introduced > resolved` 的
  分母；现在计数变准，「多文件 + 存在不可修语义问题」的 run 会少跑若干修复轮。
  方向 fail-closed（提前 FAIL 而非假 PASS）。若后续观察到可修问题的修复率下降，
  根因在此。
- **未做（另案，PRE 边界显式延后）**：`outstanding_semantic` 在 Phase C 不按
  `accepted_fps` 过滤（`final_issues` 过滤了但紧接的 extend 绕过），某轮 triage
  接受 + 随后一轮零 patch 提前 break 时会残留成**假 FAIL**。建议登记为
  `T-GATE-ACCEPTED-FPS-FILTER`（一行过滤即可）。

## Completed

- **Status**: DONE
- **Finished**: 2026-07-18 05:02:44 EDT
