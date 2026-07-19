# semantic-no-truncation

- **Started**: 2026-07-18 21:54:02 EDT
- **Branch**: main
- **Type**: GO
- **Status**: PRE

## Background / Trigger

用户以 `T-SEMANTIC-FULLFILE-COST` 触发 `/go`，先经一轮 `/plan` 讨论收敛范围。

该 todo 原本挂在 `## Discussing` 段、带 4 个待决项，涵盖两件事：

1. **质量缺口** —— `repair/checkers/semantic.py` 里硬编码 `_SEMANTIC_MAX_CHARS = 50000`，
   超出部分直接丢弃。实测 `stage_snapshot` 约 59KB，即每个 stage 的每份大文件
   尾部约 15% 从未被任何一次语义审校看到过。
2. **成本疑问** —— todo 正文称"检查吃掉 repair 92% 的 token"，据此提出降 Phase A
   effort / 按 importance 分级跳审等方案。

讨论中核对了真实账本 `logs/runs/<work_id>_2026-07-16_144353.jsonl`（todo 引用的
那次 3-stage 跑），发现第 2 点的支撑数据对不上账：

- 账本 lane 标签只有 `repair[S00N]`，**不区分** Phase A / gate 复检 / T1 / T2，
  todo 那张四行分类表（34+2+38+24 = 98 次调用）无法从账本复现；
- 该文件里 repair 实际共 **69 次**调用、**$46.23**、占全跑 $157.86 的 **29.3%**，
  而 todo 写的是"约 21%"。

## Conclusion and decisions

**做**：

1. **彻底删除 L3 语义审校的截断，且不引入 config 键。** 用户明确拍板"不应该有任何
   截断，也不应该进 config"。理据：Phase A 是整条 repair 链路中**唯一一次**全文
   审阅，后续 T1/T2 修复与 Phase B gate 复检都只处理 Phase A 报出的问题 ——
   Phase A 没看到的内容，后面没有任何环节会再看到它。在这里省输入等于直接削减
   找问题的能力。截断不存在"多少字符算该丢"的合理取舍，因此它不是配置项；留一个
   键等于把"何时开始漏审"做成可调旋钮。删除后若文件真的撑爆 context，LLM 调用会
   报错并经 `SemanticReviewLLMUnavailable` 转成阻塞 issue —— 用响亮失败取代静默漏检。
2. **订正 `docs/todo_list.md` 中 `T-SEMANTIC-FULLFILE-COST` 的成本口径。** 用账本
   可复现的数字替换不可复现的四行分类表与 92% / 21% 结论，并显式记录"账本 lane
   标签不区分调用类型"这一测量局限，避免后续决策继续引用它。

**不做**（留在 `## Discussing`，等 #65/#66/#67 落地后的新账本再评估）：

3. **Phase A 不降 effort。** todo 自述需要 xhigh 基线数据才好判断；加一个默认值
   等于现状的旋钮是纯增复杂度。
4. **不按 importance 分级跳过 L3。** 实测残留问题多为跨字段一致性
   （`cross_field_consistency` / `voice_ownership`），按 target 切字段并不能等比例
   降成本，却会在跨字段问题上开洞。
5. **不把 Phase B gate 复检的输入 scope 化。** 讨论中核实：gate 走
   `check_scoped` → `_review_file`，prompt 仍塞整份 JSON，scope 过滤发生在返回值上
   （决策 #66 的原意即是防打地鼠收敛，并未承诺省 token）。据账本估算，输出 token
   约占 repair 成本 2/3、输入约 1/3，而 1/3 中 Phase A 的份额按本轮决策必须保留，
   故该优化收益上限仅约 repair 成本的百分之十几，且判定单字段常需兄弟字段上下文，
   有质量风险。杠杆排序为：调用次数 ≫ 输出档位 ≫ 输入大小，本项属最小者。

## Planned action list

- file: `extraction/repair/checkers/semantic.py` → 删除 `_SEMANTIC_MAX_CHARS`
  常量与截断分支；补注释说明"此处刻意不截断"及其理由，防止后续被"顺手加个保护"重新引入
- file: `extraction/repair/protocol.py` → `RepairConfig` 注释中"L3 reads a whole
  ~50k-char stage_snapshot"的措辞随之校正（该 50k 引自被删的截断值）
- file: `extraction/config.toml` → `[repair].semantic_timeout_s` 注释中"通读整份
  ~50k 字符的 stage_snapshot"同上校正
- file: `docs/todo_list.md` → 订正 `T-SEMANTIC-FULLFILE-COST` 正文成本口径 +
  条目移出 `## Discussing`（截断部分本轮完成，剩余待决项保留）；刷新顶部 `## Index`
- file: `docs/todo_list_archived.md` → 若条目整体完成则归档（视 Step 4 判定）

## Validation criteria

- [ ] `python -c "import extraction.repair.checkers.semantic"` 无 error
- [ ] `grep -rn "_SEMANTIC_MAX_CHARS" extraction/` 残留 = 0
- [ ] `grep -rn "50000\|50k\|5 万字符" extraction/ docs/ ai_context/` 无指向已删截断的残留描述
- [ ] `python -m extraction.repair.tests` smoke 全通过
- [ ] `docs/todo_list.md` 顶部 `## Index` 的条目计数与正文段一致

## Execution deviations

- **新增**：`extraction/persona_extraction/core/config.py::RepairAgentConfig` 的
  `semantic_timeout_s` 注释同样引用了被删的 50k 值，一并校正（PRE 计划里只列了
  `protocol.py` + `config.toml` 两处）。
- **新增**：`docs/decisions.md` 三处（#48 / #66 / #68 条目内）以 "~50k 字符
  stage_snapshot" 描述 L3 输入规模，改为"整份 stage_snapshot"。属措辞对齐，
  不改这三条决策本身。
- **新增**：`docs/todo_list.md` 的 `T-GATE-SCOPED-RECHECK` 条目两处引用 50k
  截断，随之校正。
- **新增（既存漂移，非本轮引入）**：`docs/todo_list.md` 顶部 Index 的 `**Total**`
  行写 "11 — Next 3"，与三个子表表头（0 / 2 / 8）及正文实际条目数（0 / 2 / 8）
  均不一致。按 Step 4 的 gap-fix 就地订正为 "10 — Next 2"。
- **未做（PRE 计划中的条件项）**：`docs/todo_list_archived.md` 未动 ——
  `T-SEMANTIC-FULLFILE-COST` 只完成了截断那半，成本那半仍有 4 个待决项，
  条目继续留在 `## Discussing`，不满足归档条件。
- **Step 5 就地修复**：注释挂 `(decision #70)` 指针并随之收短（理据落在决策
  条目里，代码注释只留索引）；订正注释中"溢出必转 `semantic_unavailable`"的
  过窄断言（实际两条路径 `semantic_unavailable` / `semantic_check_crashed`，
  均阻塞）；删 `docs/todo_list.md` 正文两处"原条目……"历史叙事（违反
  §只描述当前设计，该记录已由决策 #70 背景段 + 本日志承载）；补齐
  `T-SEMANTIC-FULLFILE-COST` 的 `**更新时间**` 并刷新 `T-GATE-SCOPED-RECHECK`
  的（正文 + Index 同步）。

<!-- POST phase fills in -->

## Landed changes

删除 L3 语义审校输入的 50k 截断，Phase A 恢复为无条件通读整份文件，并以决策 #70
固化"不做成配置项"；同步订正三处引用旧截断值的注释、`docs/decisions.md` 三处措辞，
以及 `docs/todo_list.md` 中 `T-SEMANTIC-FULLFILE-COST` 的成本口径与顶部 Index。

## Diff from plan

见上方 `## Execution deviations`：多做 4 项（决策 #70 条目、`core/config.py`
注释、`docs/decisions.md` 三处措辞对齐、Index `Total` 行既存漂移订正），
少做 1 项（归档条件未满足，`docs/todo_list_archived.md` 未动）。
讨论中明确排除的三项（Phase B gate 输入 scope 化 / Phase A 降 effort /
按 importance 分级跳审）全部未触碰，边界已写入决策 #70。

## Validation results

- [x] `python -c "import extraction.repair.checkers.semantic"` 无 error —— `import OK`
- [x] `grep -rn "_SEMANTIC_MAX_CHARS" extraction/` 残留 = 0
- [x] `grep -rn "50k|50000|5 万字符"` 无指向已删截断的残留 —— `extraction/` /
      `ai_context/` / `docs/` 均已清理；仅存于决策 #70 自身的"背景"段（归档允许）
      与 `docs/todo_list_archived.md`（归档快照，已登记为待议项）
- [x] `python -m extraction.repair.tests` 全通过 —— `all 2 smoke module(s) passed`，
      含 L3 gate 的 7 个场景（scope 过滤 / backend-failure 穿透 / 未 gate 文件携带
      未修 issue），Step 5 就地修复后重跑仍全绿
- [x] `docs/todo_list.md` Index 与正文一致 —— 正文实测 In Progress 0 / Next 2 /
      Discussing 8，与三个子表表头一致；`**Total**` 行由既存的 "11 / Next 3"
      订正为 "10 / Next 2"

## Completed

- **Status**: DONE
- **Finished**: 2026-07-18 22:06:12 EDT
