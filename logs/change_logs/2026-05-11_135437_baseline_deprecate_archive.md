# baseline_deprecate_archive

- **Started**: 2026-05-11 13:54:37 EDT
- **Branch**: main (framework via worktree `../offpage-main`)；extraction/<work_id> 当前 dirty 但不动
- **Status**: PRE

## 背景 / 触发

本次会话先后做了：
1. 上一轮 /go (commit 979413f) 归档了 T-ANALYSIS-SCHEMA-TIGHTEN / T-PHASE2-TARGET-BASELINE / T-PHASE0-CHUNK-SCHEMA-EXPAND 三条 todo，留 In Progress 2 条：T-BASELINE-DEPRECATE + T-INGEST-STRUCTURE-MODE
2. 然后用户启动 phase 3 后台跑 S001+S002（PID 997418），36m35s 后 S001 FAIL 中止——FAIL 原因是 Character B.stage_snapshots/S001.json 的 `knowledge_scope.knows[0]` + `relationships[0].target_known_status` 两处把Character A写成"破境重修无修为"，与 S001 内事件"修炼<technique>至淬体六层"矛盾。L3 LLM semantic checker 抓出，repair_agent lifecycle 1 "Regression detected — stopping" 后 `Total repair attempts: 1` 终止
3. 但 phase 3 S001 抽取实际产出了 Character B + Character A 各自 stage_snapshots/S001.json（含 5/5 lane 全 complete），即使最终 commit FAILED 这些文件物理存在工作区（untracked）

用户问 T-BASELINE-DEPRECATE 是否可以归档。本助手核对完成标准 5 项后判定可以归档（形式 = 改方案后完成）。本轮 /go 执行归档。

## 结论与决策

**完成标准核查**（已在前一轮对话明确）：

- 标准 1 (4 件套 schema 删除 + stage_snapshot 加 failure_modes) ✅
- 标准 2 (至少一个 legacy work migration) ⚪ N/A — 本仓库无 legacy 4 件套 work，migration script 无适用对象
- 标准 3 (phase 1/2 不产 4 件套) ✅ — 本轮 phase 2 跑通时 `works/<work_id>/characters/{Character A,Character B}/canon/` 均无 4 件套文件
- 标准 4a (phase 3 char_snapshot read list 不含 4 件套/manifest) ✅ — [automation/persona_extraction/prompt_builder.py:685-723](../automation/persona_extraction/prompt_builder.py) `_build_char_snapshot_read_list` 实际只读 schema/character/stage_snapshot.schema.json + identity.json + prev stage snapshot + source chapters
- 标准 4b (stage_snapshot.failure_modes 字段产出正确) ✅ — Character B S001 failure_modes 4 sub-class items 数 9/10/7/6，Character A S001 = 9/10/7/7；items 含完整字段 id/name/description/why_it_happens/correct_behavior/common_triggers
- 标准 4c (命中 maxItems 时裁剪生效) ⚪ 未触顶 — S001 实际 items 6-10 远低于 maxItems 10-15，本轮没机会触发裁剪。prompt 已含决策 #11e maxItems-aware truncation rule，后续 stage 内容密集时自然验证
- 标准 5 (ai_context/docs 同步) ✅

**结论**：5 项标准 4 ✅ + 2 ⚪（标准 2 N/A，标准 4c 未触顶但设计已落地），形式 = **改方案后完成**。

**S001 FAIL 与本归档无关**：FAIL 原因在 `knowledge_scope.knows` + `relationships.target_known_status` 与 `stage_events` 事实矛盾（决策 #11f prev_stage 四态规则 B 态执行不到位），与"4 件套废弃 / failure_modes inline 进 stage_snapshot"完全无关——failure_modes 字段在 FAIL 文件里照样产出形态正确。

**T-CHAR-SNAPSHOT-SUB-LANES 的依赖描述同步更新**：T-BASELINE-DEPRECATE 是它的最后一个硬前置（上一轮 T-PHASE2-TARGET-BASELINE 已转"依赖物已就位"指针）。本轮归档后该依赖应进一步转为"全部依赖已就位"，Ready 状态从 ⏸ Blocked → ✅ Ready。

## 计划动作清单

- file: `../offpage-main/docs/todo_list.md`（**main 分支**） →
  - Index 段：`### 🟢 In Progress (2)` → `### 🟢 In Progress (1)`；删 T-BASELINE-DEPRECATE 行；汇总行 `Total: 13 — 🟢 In Progress 2 ｜ 🟡 Next 3 ｜ ⚪ Discussing 8` → `Total: 12 — 🟢 In Progress 1 ｜ 🟡 Next 3 ｜ ⚪ Discussing 8`
  - 正文 In Progress 段：删 T-BASELINE-DEPRECATE 整段（原行 202-335）；保留 T-INGEST-STRUCTURE-MODE 一条
- file: `../offpage-main/docs/todo_list.md` T-CHAR-SNAPSHOT-SUB-LANES 段（**顺手对齐**） →
  - 「依赖」段：原"硬前置: T-BASELINE-DEPRECATE / 启动门槛 = BASELINE-DEPRECATE 跑过 runtime 验证" → 改为"依赖物已就位: T-BASELINE-DEPRECATE 已完成于 2026-05-11"；同时上轮已有"依赖物已就位: T-PHASE2-TARGET-BASELINE 已完成于 2026-05-11"指针保留 → 两个依赖均已就位
  - Index 段 Deps 列：`T-BASELINE-DEPRECATE` → `无（依赖物均已就位）`
  - Index 段 Ready 列：`⏸ Blocked` → `✅ Ready`（依赖全清空）
- file: `../offpage-main/docs/todo_list_archived.md`（**main 分支**） → 在 `## Completed` 段顶部插一条 T-BASELINE-DEPRECATE 瘦身条目（完成形式"改方案后完成"+ 1 行摘要列证据 + 关联本次 log 链接）
- file: `../offpage-main/logs/change_logs/2026-05-11_135437_baseline_deprecate_archive.md`（**main 分支**） → 本 log 文件，PRE 段已写、Step 8 追加 POST 段

## 验证标准

- [ ] `docs/todo_list.md` Index 段：In Progress 子表只剩 1 行（T-INGEST-STRUCTURE-MODE），Total 汇总行 `Total: 12 — 🟢 In Progress 1 ｜ 🟡 Next 3 ｜ ⚪ Discussing 8`
- [ ] `docs/todo_list.md` 正文 In Progress 段不再含 T-BASELINE-DEPRECATE 整段
- [ ] `docs/todo_list_archived.md` `## Completed` 段顶含 1 条新增 T-BASELINE-DEPRECATE 瘦身条目，带本次 log 链接
- [ ] T-CHAR-SNAPSHOT-SUB-LANES 段的「依赖」改写为"依赖物均已就位"指针；Index 段 Ready 列 ⏸ Blocked → ✅ Ready
- [ ] `grep -n` 全仓库（除 archived / logs）：T-BASELINE-DEPRECATE 仅作为"依赖物已就位"指针出现在 T-CHAR-SNAPSHOT-SUB-LANES 段，不再出现在 In Progress 段或别处
- [ ] worktree-main commit 后 `git status` clean
- [ ] Step 10 extraction 分支同步：因 dirty 自动跳过，library 分支正常 merge

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

**main 分支（worktree `../offpage-main`，单 commit）**：

- `docs/todo_list.md` Index 段：
  - `### 🟢 In Progress (2)` → `### 🟢 In Progress (1)`
  - 删 T-BASELINE-DEPRECATE 行
  - 汇总行 `Total: 13 — 🟢 In Progress 2 ｜ 🟡 Next 3 ｜ ⚪ Discussing 8` → `Total: 12 — 🟢 In Progress 1 ｜ 🟡 Next 3 ｜ ⚪ Discussing 8`
  - T-CHAR-SNAPSHOT-SUB-LANES 行：Ready 列 `⏸ Blocked` → `✅ Ready`、Deps 列 `T-BASELINE-DEPRECATE` → `无（依赖物均已就位）`
- `docs/todo_list.md` 正文 In Progress 段：Python 切片删 T-BASELINE-DEPRECATE 整段（原 1-idx 行 201-335），保留 T-INGEST-STRUCTURE-MODE 一条
- `docs/todo_list.md` T-CHAR-SNAPSHOT-SUB-LANES「依赖」段重写：原"硬前置: T-BASELINE-DEPRECATE / 启动门槛 = BASELINE-DEPRECATE 跑过 runtime 验证"两条 → "依赖物已就位 2: T-BASELINE-DEPRECATE 已完成于 2026-05-11（4 件套已废弃 + failure_modes 字段产出形态实测正确...）/ 全部依赖已就位 — 本 todo 可启动"。改动清单 line 508 "T-BASELINE-DEPRECATE 引入的「maxItems 统一裁剪规则」段" 历史指针保留（与"依赖物已就位 2"配对，标识 maxItems 规则段是该 todo 落地引入的历史事实）
- `docs/todo_list_archived.md` `## Completed` 段顶部插一条 T-BASELINE-DEPRECATE 瘦身条目（完成形式 = "改方案后完成"，标准 2 转 N/A + 标准 4c 未触顶但设计已落地 + 标准 1/3/4a/4b/5 全 ✅，附Character B 9/10/7/6 + Character A 9/10/7/7 实测数据 + char_snapshot read list 行号引用 + S001 FAIL 与本 todo 无关的备注 + log 链接）
- `logs/change_logs/2026-05-11_135437_baseline_deprecate_archive.md`：本 log 文件（PRE/POST 同一份）

**extraction/<work_id> 分支**：本次范围无改动（extraction 工作区 11 个变更 3M + 8?? 全部保留——属于 phase 3 partial 产物 + 程序化 stage_catalog modified，用户后续会单独决定如何处理，与本 todo 归档正交）。

## 与计划的差异

无。PRE 「计划动作清单」4 项全部按计划执行，无新增 / 删除。

## 验证结果

PRE 「验证标准」7 条：

- [x] `docs/todo_list.md` Index 段：In Progress 子表只剩 1 行（T-INGEST-STRUCTURE-MODE），Total 汇总行 `Total: 12 — 🟢 In Progress 1 ｜ 🟡 Next 3 ｜ ⚪ Discussing 8` — 验证通过
- [x] `docs/todo_list.md` 正文 In Progress 段不再含 T-BASELINE-DEPRECATE 整段 — `awk '/^## In Progress/,/^## Next/' | grep -c "^### \[T-"` = 1（仅 T-INGEST-STRUCTURE-MODE）
- [x] `docs/todo_list_archived.md` `## Completed` 段顶含 1 条新增 T-BASELINE-DEPRECATE 瘦身条目，带本次 log 链接 — Edit 已成功
- [x] T-CHAR-SNAPSHOT-SUB-LANES 段的「依赖」改写为"依赖物均已就位"指针；Index 段 Ready 列 ⏸ Blocked → ✅ Ready — Edit 已成功
- [x] `grep -n` 全仓库（除 archived / logs）：T-BASELINE-DEPRECATE 仅作为完成指针 / 历史引用出现在 T-CHAR-SNAPSHOT-SUB-LANES 段 line 508 / 615，不再出现在 In Progress 段或别处 — 2 处残留均是 intentional reference
- [x] worktree-main commit 后 `git status` clean — Step 9 验证通过（commit aa6dff7，worktree 已 remove）
- [~] Step 10 分支同步实际结果偏离 PRE 预期：
  - **extraction/<work_id> → 同步成功**（merge commit 1d11442）—— 与 PRE 预测的"因 dirty 跳过"不一致。原因：merge 影响的文件 = docs/todo_list*.md + logs/change_logs/* 与 dirty 文件 works/* 不重合，git 自动 merge 顺利，partial 产物保留
  - **library → 同步推迟**（PRE 预测正常同步）—— 原因：`git checkout library` 因 dirty extraction 工作区 stage_catalog × 3 在 library 分支上有不同内容会被覆盖，checkout 失败；当前 HEAD 仍在 extraction。library 同步推迟到 phase 3 partial 处理结束后用户手工 merge 一并完成（同 PRE 内 extraction 同步推迟的归因——属短期运行时状态，不入 todo_list 单独跟踪）

## Completed

- **Status**: DONE
- **Finished**: 2026-05-11 13:58:36 EDT
