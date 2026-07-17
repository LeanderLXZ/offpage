# gate-scoped-recheck

- **Started**: 2026-07-17 11:27:27 EDT
- **Branch**: main
- **Type**: GO
- **Status**: PRE

## Background / Trigger

用户 `T-GATE-SCOPED-RECHECK /go`。2026-07-16 挂机跑 S003 时逐行拆 repair
循环发现的**正确性缺陷**：Phase B 每轮末的 L3 gate 把整份文件重读一遍
（`pipeline.run_layer(..., layer=3)` → `SemanticChecker.check` 全文），导致
「修一个冒一个」的打地鼠循环——LLM 全文复审本身不确定，每轮挑出的毛病天然
不同 → 新指纹 → 算 `introduced` → 循环继续，且 `resolved=N/introduced=N/
persisting=0` 恰好从 `is_regression`（`introduced>resolved`）与 `is_stalled`
（persisting 恒 0）两阀中间穿过，每次跑满 `total_round_limit` 才判 FAIL，攒出
本不该有的 defer 债。

现成 `check_scoped(files, paths)` 是死代码（全仓零调用方），且其实现只在
prompt 末尾加软提示 `Focus review on these paths`、**不过滤返回值**，无法根治。

依赖说明：本任务原标 Blocked（等 effort 分档 #65 的基线 stage 跑完做单变量
归因）。用户 2026-07-17 拍板「照跑不误，先落代码」，接受本轮无法做基线对比
验证的归因缺口。

## Conclusion and decisions

让 gate 职责回归「我这一刀改对了吗」而非「再审一遍全书」——全文审计由 Phase A
一次完成。做法：

- gate 改走 scoped 语义：只复检**本轮实际改过的 json_path**，且**在代码层
  按 paths 过滤返回值**（程序保证，不指望 LLM 听 focus 软提示）。
- `check_scoped` 返回值过滤为「在某个 scoped path 上或其后代」的 issue；
  但**后端失败类 issue**（`semantic_unavailable` / `semantic_check_crashed` /
  `semantic_unparseable`，锚在 `$`）永不被过滤——否则复检根本没跑通却被静默
  丢弃 = 假 PASS。
- `introduced` / `is_regression` 语义在 scoped 下自然变正确：gate 只看改过的
  path，「上轮没有这轮有」= 我这一刀改出了新问题 = 回归的真定义。tracker 的
  diff / 安全阀数学无需改，仅更新语义注释；`is_stalled` 的 `len(curr_fps)>0`
  守卫与 `is_l3_gate_reemerge` 复核后保留（scoped 下含义更精确）。
- 有意取舍：放弃「修 A 是否搞坏了跨 path 的 B」的全文复检能力——Phase A 已覆盖
  全量，且现状那个能力实际报的是审校抖动而非真回归。
- 边界：Phase C fallback L3（`gate_ever_ran==False` 时）保持全文——它是「至少
  渲染一次语义判决再 PASS」的兜底，触发时本就无「改过的 path」可 scope。

## Planned action list

- file: `extraction/repair/checkers/semantic.py` → `check_scoped` 返回值按
  `paths` 过滤（后代匹配）；保留后端失败类 issue；加 `_BACKEND_FAILURE_RULES`
  常量 + `_path_in_scope` 辅助
- file: `extraction/repair/checkers/__init__.py` → 新增 `run_semantic_scoped(
  files, paths, **kwargs)`（layer-3 checker 有 `check_scoped` 则走它）
- file: `extraction/repair/coordinator.py` → (a) `_run_fixer_with_escalation`
  额外返回 `modified_paths: dict[file, set[json_path]]`；(b) round 循环聚合本轮
  改过的 path；(c) L3 gate 改调 `run_semantic_scoped(scope_paths)`，guard 加
  `scope_paths` 非空；(d) 更新注释
- file: `extraction/repair/tracker.py` → `diff` / `is_regression` / `is_stalled`
  / `is_l3_gate_reemerge` 更新 scoped 语义注释（数学不变）
- file: `extraction/repair/tests/_smoke_l3_gate.py` → 补 (D) 修复成功→scoped 复检
  0 issue→早退；(E) 改过的 path 上真引入新问题→仍被 introduced 抓到 + 域外 issue
  被过滤
- file: `ai_context/decisions.md` + `docs/decisions.md` → 新增决策条目
- file: `docs/requirements.md` §11.4 → gate 语义同步
- file: `docs/architecture/extraction_workflow.md` → 同步

## Validation criteria

- [ ] `python -c "import extraction.repair.coordinator, extraction.repair.checkers.semantic, extraction.repair.checkers, extraction.repair.tracker"` 无 error
- [ ] `python -m extraction.repair.tests._smoke_l3_gate` 全场景过（含新增 D/E）
- [ ] grep 确认 gate 调用点不再走 `run_layer(..., layer=3)`（Phase B），Phase C
  fallback 仍保留
- [ ] `check_scoped` 返回值经过 paths 过滤（有单测覆盖域外 issue 被丢 + 后端失败
  类不被丢）

## Execution deviations

- **Step 5 复审发现 High 回归并就地修复（原计划外，但属同一改动的正确性收尾）**：
  首版 scope 只含「本轮改过的 json_path」，会让本轮未修好、又不在改动 path 上
  的语义 error 被 round-diff 误判 resolved → 假 PASS。修复：gate scope 改为
  per-file =「触碰 path ∪ 本轮携带的语义 issue path」，抽出纯函数 `_gate_scope`
  便于单测；顺带修掉 Med 级「跨文件扁平 scope 放行同名 path 抖动」（改 per-file
  迭代，LLM 调用数不变）。
- **未做 prompt focus 段加严**（PRE 计划里的"评估是否需要"）：程序层过滤即根治，
  prompt 加严冗余，故不改——已在决策 #66 记录为有意取舍。
- **Low 级边界未修（记录）**：某文件 scope 含根 `$` 时该文件 gate 退化全文；
  罕见且多为后端失败（fail-closed），加守卫反有丢弃 degraded `$` issue 的假-PASS
  风险，故留作可选后续（建议 todo `T-GATE-ROOT-ANCHOR-SCOPE`）。

## Landed changes

scoped L3 gate 落地：Phase B 每轮末 gate 从「全文复检」改为「per-file 定点复检」
（触碰 path ∪ 携带的语义 issue path），`check_scoped` 代码层过滤返回值 + 后端
失败类永不过滤；tracker 语义注释；smoke 补 D/E/F；决策 #66 + requirements §11.4 +
extraction_workflow + ai_context 同步。Phase C fallback L3 保持全文（兜底）。

## Diff from plan

- 新增（计划外，复审驱动）：`_gate_scope` 纯函数 + scope 携带「未修语义 issue 的
  path」+ per-file 迭代（修 High/Med 回归）；smoke 场景 F（回归测试）。
- 计划内但改形态：`run_semantic_scoped` 由「一次多文件调用」改为「逐文件调用」
  （LLM 调用数等价，换 per-file scope 隔离）。
- 未做：prompt focus 段加严（见 deviations）；stage 实测基线对比（用户拍板先落
  代码，留待后续单独验证）。

## Validation results

- [x] import smoke（coordinator / checkers / semantic / tracker）— IMPORT OK
- [x] `_smoke_l3_gate` 全 6 场景过（A–C 原有 + D 域外过滤 / E 后端失败保留 /
  F 回归：scope 携带未修 path + 无跨文件 bleed）
- [x] gate 调用点 split：Phase B = `run_semantic_scoped`（scoped），Phase C
  fallback 仍 `run_layer(layer=3)`（全文兜底）
- [x] `check_scoped` 返回值经 paths 过滤（D 覆盖域外丢弃 + E 后端失败保留）
- [~] **实测 stage 与基线对比 round 数/墙钟/defer 债 — 未做**（用户拍板先落代码；
  待跑 ≥1 stage 验证，见 todo T-GATE-SCOPED-RECHECK「进展」）
- 旁证：`_smoke_triage.py` 在 clean HEAD 上即失败（pre-existing，与本改动无关，
  已由既有 todo `T-SMOKE-TRIAGE-BROKEN` 跟踪）

## Completed

- **Status**: DONE
- **Finished**: 2026-07-17 11:55:28 EDT
