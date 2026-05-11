# yejunlin_fix_and_phase012_todo_complete

- **Started**: 2026-05-11 06:21:40 EDT
- **Branch**: extraction/<work_id> (per-work fix) + main (framework via worktree `../offpage-main`)
- **Status**: PRE

## 背景 / 触发

上一轮会话验证 phase 0/1/1.5/2 产物合法性，schema gate 全过；但跨文件语义检查发现一处引用断裂：`Character C` 在 `target_baseline.Character A.targets` + `fixed_relationships.FR-002` 被引用，但 phase 1 candidate_characters lane 漏抽他（仅在 chunk_026 / C0505 出场一次）——`candidate_characters.json` 30 条候选中无对应 `character_id` entry。

后果（一进 phase 3 即触发）：

1. `automation/persona_extraction/validator.py::load_importance_map("Character C")` 返回空 → `importance_min_examples` 走"其他"档 = 1（而非核心档 5），影响 phase 3 stage_snapshot 内针对Character C的 voice / behavior 最小例子数
2. decision #13 set-equal 约束要求 phase 3 三结构 keys == baseline.targets，`Character C` 会成为强制 key，但 phase 3 prompt 没有他的 identity 上下文

同一轮 todo_list 复盘发现 phase 0/1/1.5/2 全跑完后，3 条 In Progress 任务的"runtime 验证待跑"项已达成：

- **T-ANALYSIS-SCHEMA-TIGHTEN** — 完成标准最后一项明文要求"现有 works 清掉后 phase 0+1+1.5+2 全过 schema gate 不报红"，本次重抽即按此标准
- **T-PHASE2-TARGET-BASELINE** — 完成标准全 5 项 ✅，含"phase 2 跑通至少一个 work：每个 candidate character 产出 target_baseline.json schema 合规"（Character A + Character B 均 PASS）
- **T-PHASE0-CHUNK-SCHEMA-EXPAND** — runtime 验证：`observed_impact` 135 entries 0 empty / 2 fallback / 133 真实事件；`power_levels` "凡人/淬体/聚灵" 是本作真实力量体系（非"练气筑基金丹元婴"仙侠默认）；foundation schema PASS（决策 #54 后 foundation 改由 phase 1 lane 直产）

用户在本轮 /go 前确认：3 条全部标完成 + 补 `Character C` entry（importance=`重要配角`，对齐 baseline 内 `Character A.target_baseline.targets` 把他列为核心 tier 至亲 + FR-002 血缘锚点的剧情权重）。

## 结论与决策

**两类改动落两个分支两个 commit**：

1. **extraction 分支** (`extraction/<work_id>`，原 checkout `/home/leander/Leander/offpage`) — 改 `works/<work_id>/analysis/candidate_characters.json` 补 `Character C` entry。works/ 仅在 extraction / library 分支 tracked，main 分支 framework-only，此改动绝不能 land 在 main。

2. **main 分支** (`../offpage-main` worktree) — 改 `docs/todo_list.md`（Index 缓存段刷新：In Progress 5→2、Total 16→13；In Progress 段去掉 3 条已完成条目正文）+ `docs/todo_list_archived.md`（在 `## Completed` 段加 3 条瘦身条目）+ `logs/change_logs/2026-05-11_062140_yejunlin_fix_and_phase012_todo_complete.md`（本 log，PRE/POST 同文件）。

**`Character C` entry 字段**：

```json
{
  "character_id": "Character C",
  "canonical_name_candidate": "Character C",
  "importance": "重要配角",
  "aliases": [],
  "first_seen_context": "..." (按 candidate_characters schema 必填字段补)
}
```

具体字段集以现有 candidate_characters.json 内 30 条 entry 的 schema-required 字段为准（Step 4 时按现有 entry 形态对齐填）。

## 计划动作清单

- file: `works/<work_id>/analysis/candidate_characters.json`（**extraction 分支**） → 在 `candidates[]` 数组末尾追加 `Character C` entry，所有 schema-required 字段按现有 entry 形态填，importance=`重要配角`，aliases=`[]`
- file: `../offpage-main/docs/todo_list.md`（**main 分支**） → Index 段三档子表：从 In Progress 段移除 T-ANALYSIS-SCHEMA-TIGHTEN / T-PHASE2-TARGET-BASELINE / T-PHASE0-CHUNK-SCHEMA-EXPAND 三行；In Progress 计数 5→2、Total 16→13；正文 In Progress 段删除 3 条完整条目（行 519-733）；正文不动 T-BASELINE-DEPRECATE / T-INGEST-STRUCTURE-MODE
- file: `../offpage-main/docs/todo_list_archived.md`（**main 分支**） → 在 `## Completed` 段追加 3 条瘦身条目（每条：标题 + 完成形式 + 1 行摘要 + 本次 log 链接 + 完成时间戳）
- file: `../offpage-main/logs/change_logs/2026-05-11_062140_yejunlin_fix_and_phase012_todo_complete.md`（**main 分支**） → 本 log 文件，PRE 段已写、Step 8 追加 POST 段

## 验证标准

- [ ] `Character C` entry 通过 candidate_characters schema 验证（`python3` import validator + `_validate_schema` 跑过单文件，0 error）
- [ ] 跨文件引用完整：`Character C` 现在出现在 cand_ids 集合中，target_baseline.Character A.targets `Character C` + fixed_relationships.FR-002 `Character C` 两处都能从 cand_ids 查到
- [ ] `load_importance_map(... "<work_id>")` 返回的 dict 含 `"Character C": "重要配角"` key
- [ ] `docs/todo_list.md` Index 段：In Progress 子表只剩 2 行（T-BASELINE-DEPRECATE + T-INGEST-STRUCTURE-MODE），Total 汇总行 `Total: 13 — 🟢 In Progress 2 ｜ 🟡 Next 3 ｜ ⚪ Discussing 8`
- [ ] `docs/todo_list.md` 正文 In Progress 段不再含 T-ANALYSIS-SCHEMA-TIGHTEN / T-PHASE2-TARGET-BASELINE / T-PHASE0-CHUNK-SCHEMA-EXPAND 三条
- [ ] `docs/todo_list_archived.md` `## Completed` 段含 3 条新增瘦身条目，每条带 log 链接
- [ ] `grep -n` 全仓库（docs/ + ai_context/）：3 条 todo ID 仅在 archived / log / git-history 出现，**不再**在 todo_list.md 出现
- [ ] worktree-main commit 后 `git status` clean
- [ ] extraction 分支 commit 后 `git status` clean

## 执行偏差

**2026-05-11 06:30 EDT — `Character C` 补 entry 取消**

Step 4 实施前发现 blocker：`schemas/analysis/candidate_characters.schema.json` `candidates.maxItems = 30` 已满；补第 31 条会破 schema gate。

并行盘点全仓引用得到两组事实：
1. **40 处 orphan refs**（被 `target_baseline` / `fixed_relationships` / `foundation.key_figures` 引用但 candidates 没有的 character_id）。多数是势力名（`<location>` / `<location>`）、物品名（`冰麒麟幼崽`）、配角漏抽（`仙庭庭主` / `冷寒依` / `叶虚枫` 等）—— 按决策 #54 `foundation.key_figures` 双阶段语义，phase 2 LLM "匹配不上保留 raw 名（不报错、不删除）"是显式合法。`fixed_relationships.parties[]` 允许 string 形态（包括势力名）。**只有 `Character C` 是 `target_baseline.targets[].target_character_id` 引用** —— 该字段语义要求是真 character_id。
2. **1 处 unreferenced candidate** = `Character H`（次要配角，freq=低，description 末尾还带"陆清姚与Character H..."的身份合并疑似注释）—— 是唯一可被换出去的候选。

向用户提了三选一：A) 上调 maxItems 30→35（framework 改动）/ B) 换掉 `Character H` / C) 不修。**用户选 C 不修**。

**本轮 /go 范围缩窄**：从"3 条 todo 标完成 + 补 `Character C`"改为"仅 3 条 todo 标完成"。`Character C` 引用断裂作为已记录的 known issue 留到 phase 3 启动前再处理（届时若仍要修，可选 A / B 方案；本 log 已记录三方案权衡）。

PRE 段「计划动作清单」第 1 条（candidate_characters.json 修改）作废；「验证标准」前 3 条（Character C entry schema valid / 跨文件闭环 / importance_map 含 key）作废，由 Step 5 跳过。Step 9 commit 缩减为单分支单 commit（仅 main 分支 framework）。

**2026-05-11 06:50 EDT — Step 7 review 发现的小修：T-CHAR-SNAPSHOT-SUB-LANES 依赖描述更新**

Step 7 规范线 grep 发现 T-CHAR-SNAPSHOT-SUB-LANES 段（Next 段，行 ~736 → 改动后 ~428）的「依赖」段「硬前置 1」+「启动门槛」+ Index 段对应行 Deps 列共 3 处引用 T-PHASE2-TARGET-BASELINE。本次 T-PHASE2-TARGET-BASELINE 已完成 → 上述引用从"硬前置 + blocker"语义变为"依赖物已就位 + 指针引用"。按 Step 7 规则"一行能修的小问题 → 发现即修"处理：

- 正文「依赖」段：拆原"硬前置 1: T-PHASE2-TARGET-BASELINE / 硬前置 2: T-BASELINE-DEPRECATE / 启动门槛 = 双方都跑过 runtime 验证"→ 改为"依赖物已就位: T-PHASE2-TARGET-BASELINE 已完成于 2026-05-11 / 硬前置: T-BASELINE-DEPRECATE / 启动门槛 = BASELINE-DEPRECATE 跑过 runtime 验证"。
- Index 段对应行 Deps 列：`T-PHASE2-TARGET-BASELINE + T-BASELINE-DEPRECATE` → `T-BASELINE-DEPRECATE`。

效果：T-CHAR-SNAPSHOT-SUB-LANES 的 Ready 状态仍为 `⏸ Blocked`（被 T-BASELINE-DEPRECATE 阻塞），无需调整。Step 7 后 grep 只剩 1 处 T-PHASE2-TARGET-BASELINE 引用即"依赖物已就位"行，属于有意保留的完成指针，**非悬挂**。

<!-- POST 阶段填写 -->

## 已落地变更

**main 分支（worktree `../offpage-main`，单 commit）**：

- `docs/todo_list.md` Index 段（顶部 `## Index` 子表）：
  - `### 🟢 In Progress (5)` → `### 🟢 In Progress (2)`
  - 删 T-PHASE2-TARGET-BASELINE / T-PHASE0-CHUNK-SCHEMA-EXPAND / T-ANALYSIS-SCHEMA-TIGHTEN 三行
  - 汇总行 `Total: 16 — 🟢 In Progress 5 ｜ 🟡 Next 3 ｜ ⚪ Discussing 8` → `Total: 13 — 🟢 In Progress 2 ｜ 🟡 Next 3 ｜ ⚪ Discussing 8`
- `docs/todo_list.md` 正文 In Progress 段：删除三条整段（原行 340-428 / 519-624 / 626-735，按倒序 Python 切片处理）；In Progress 段保留 T-BASELINE-DEPRECATE + T-INGEST-STRUCTURE-MODE 两条
- `docs/todo_list.md` T-CHAR-SNAPSHOT-SUB-LANES 段（Step 7 review 小修）：「依赖」段两行 + Index Deps 列共 3 处把已完成的 T-PHASE2-TARGET-BASELINE 引用从"硬前置"语义改为"依赖物已就位"指针；Index Deps 列由 `T-PHASE2-TARGET-BASELINE + T-BASELINE-DEPRECATE` → `T-BASELINE-DEPRECATE`
- `docs/todo_list_archived.md` `## Completed` 段顶部插入 3 条新瘦身条目（按 T-ANALYSIS-SCHEMA-TIGHTEN / T-PHASE2-TARGET-BASELINE / T-PHASE0-CHUNK-SCHEMA-EXPAND 顺序，最近完成在最上方），每条 = "完成于 2026-05-11 · 完整完成" + 1 行摘要 + 关联 log 链接到本文件
- `logs/change_logs/2026-05-11_062140_yejunlin_fix_and_phase012_todo_complete.md`：本 log 文件（PRE/POST 同一份）

**extraction/<work_id> 分支**：本次范围缩窄后无改动。

## 与计划的差异

PRE 「计划动作清单」5 条 vs 实际：

- **作废**：`works/<work_id>/analysis/candidate_characters.json` 补 `Character C` entry —— `candidates.maxItems=30` 已满 blocker，用户选"不修"（详见「执行偏差」段）
- **新增**：T-CHAR-SNAPSHOT-SUB-LANES 「依赖」段 + Index Deps 列共 3 处引用更新（Step 7 review 发现的"一行小修"，从已完成的 T-PHASE2-TARGET-BASELINE "硬前置" 语义改为"依赖物已就位" 指针）

## 验证结果

PRE 「验证标准」9 条：

- [ ] ~~`Character C` entry 通过 candidate_characters schema 验证~~ — 作废（用户选不修）
- [ ] ~~跨文件引用完整~~ — 作废
- [ ] ~~`load_importance_map` 返回 dict 含 `Character C` key~~ — 作废
- [x] `docs/todo_list.md` Index 段：In Progress 子表只剩 2 行 + Total 汇总行 `Total: 13 — 🟢 In Progress 2 ｜ 🟡 Next 3 ｜ ⚪ Discussing 8` — 验证通过（grep 子表行 + Total 行匹配）
- [x] `docs/todo_list.md` 正文 In Progress 段不再含 T-ANALYSIS-SCHEMA-TIGHTEN / T-PHASE2-TARGET-BASELINE / T-PHASE0-CHUNK-SCHEMA-EXPAND — `awk '/^## In Progress/,/^## Next/' | grep -c "^### \[T-"` = 2，残留 grep 通过
- [x] `docs/todo_list_archived.md` `## Completed` 段含 3 条新增瘦身条目，每条带 log 链接 — 验证通过（grep `2026-05-11_062140_yejunlin_fix_and_phase012_todo_complete` 在 archived 文件命中 3 次）
- [x] `grep -n` 全仓库（docs/ + ai_context/）：3 条 todo ID 仅在 archived / log / git-history 出现 —— 验证通过（T-ANALYSIS-SCHEMA-TIGHTEN / T-PHASE0-CHUNK-SCHEMA-EXPAND 无残留；T-PHASE2-TARGET-BASELINE 仅剩 1 处 intentional reference 即 T-CHAR-SNAPSHOT-SUB-LANES 修订后的"依赖物已就位"指针）
- [ ] worktree-main commit 后 `git status` clean — Step 9 即将验证
- [ ] extraction 分支 commit 后 `git status` clean — 作废（本次无 extraction 分支改动）

## Completed

- **Status**: DONE
- **Finished**: 2026-05-11 06:53:13 EDT
