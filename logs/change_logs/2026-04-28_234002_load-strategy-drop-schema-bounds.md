# load-strategy-drop-schema-bounds

- **Started**: 2026-04-28 23:40:02 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

todo_list 条目 `T-LOAD-STRATEGY-WORLD-EVENTS-BOUND` 起源于 `simulation/retrieval/load_strategy.md:17` world `stage_events` summary 写的 `50–80 chars`，与 schema / decisions #27h #31 的 `50–100` 漂移。

`/todo` 拉出该条复核时，用户提出更通用的判断：load 文档不应该重申 bound——bound 是写入端（schema 在 extraction 时把关）的约束，loader 只是"存了多少读多少"，复述具体数值只会制造漂移源。本次正是因复述漂移而触发。

判定准则确定为：**这个数字改了之后，谁要跟着改？** 跟 schema 走 → 删；跟 loader 代码走 → 留。原 todo 条目仅修 L17 单点；现升级为通用清理。

## 结论与决策

清掉 `simulation/retrieval/load_strategy.md` 里所有"复述 schema bound"的具体数值；保留 loader 自己的行为参数 / 预算估算。

**该删（schema 重申 / 复述具体数值）：**
- L17 `summary (50–80 chars, hard schema gate)` — world event_digest summary
- L22-23 `background_summary ≤ 200 chars`, `key_relationships ≤ 10 entries` — 已经是"指针"用法，但顺手把复述的具体数值清掉，只保留指向 schema 的指针
- L41 `summary (30–50 chars, hard schema gate)` — memory_digest summary

**保留（loader 行为，不是 schema bound）：**
- L38 `recent 2 stages (N + N-1)` — loader 取窗口策略
- L39-40 `stage 1..N filtered` — loader filter
- L46 `~30-40 tokens per entry; 49 stages × ~15 entries ≈ 22-29K tokens` — prompt 预算估算

## 计划动作清单

- file: `simulation/retrieval/load_strategy.md`
  - L17 删去 `(50–80 chars, hard schema gate)`，保留 `summary` 字段名；末尾备注改成"length capped at extraction time by world stage_snapshot schema"
  - L22-23 删去具体数值 `≤ 200 chars` / `≤ 10 entries`，保留"caps live in `identity.schema.json` … bounded at extraction time"
  - L41 删去 `(30–50 chars, hard schema gate)`，保留 `summary` 字段名
- file: `docs/todo_list.md`
  - 把 `T-LOAD-STRATEGY-WORLD-EVENTS-BOUND` 整条移到 `docs/todo_list_archived.md` `## Completed`，瘦身格式（标题 + 完成形式 + 1 行摘要 + 本 log 链接）
  - 同步刷新顶部 Index 段（`Discussing` 7 → 6，total 11 → 10）
- file: `docs/todo_list_archived.md`
  - `## Completed` 段追加瘦身条目

## 验证标准

- [ ] `simulation/retrieval/load_strategy.md` 三处 schema 数值已删，loader 行为参数（recent 2 stages / 1..N filter / token 估算）原样保留
- [ ] `grep -nE '(50.{1,3}80|50.{1,3}100|30.{1,3}50|≤ 200 chars|≤ 10 entries)' simulation/retrieval/load_strategy.md` 返回空
- [ ] `docs/todo_list.md` 正文已无 `T-LOAD-STRATEGY-WORLD-EVENTS-BOUND` 条目；Index 段子表 / 汇总行已刷新
- [ ] `docs/todo_list_archived.md` `## Completed` 段已加该条瘦身记录，链向本 log

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

- `simulation/retrieval/load_strategy.md`
  - L17-21（world_event_digest 块）：删去 `summary (50–80 chars, hard schema gate)` 内的 `(50–80 chars, hard schema gate)`；末尾追加 "(length capped at extraction time by the world stage_snapshot schema)"
  - L22-24（identity 块）：删去 `(e.g. background_summary ≤ 200 chars, key_relationships ≤ 10 entries)`；保留 "caps live in `identity.schema.json`, so Tier 0 size is bounded at extraction time, no loader-side filtering required"
  - L41-46（memory_digest 块）：删去 `summary (30–50 chars, hard schema gate)` 内的 `(30–50 chars, hard schema gate)`；末尾追加 "(length capped at extraction time by the memory_timeline schema)"；loader 行为参数（regex / token 估算 22-29K）原样保留
- `docs/todo_list.md`
  - 删除正文 L662-695 的 `T-LOAD-STRATEGY-WORLD-EVENTS-BOUND` 整条
  - Index 段：从 Discussing 子表删除该行；段标题 `### ⚪ Discussing (7)` → `(6)`；汇总行 `Total: 11 — … Discussing 7` → `Total: 10 — … Discussing 6`
- `docs/todo_list_archived.md`
  - `## Completed` 段顶部追加 `[T-LOAD-STRATEGY-WORLD-EVENTS-BOUND]` 瘦身条目（改方案后完成 · 含 1 行摘要 + 链向本 log）

## 与计划的差异

无

## 验证结果

- [x] `simulation/retrieval/load_strategy.md` 三处 schema 数值已删，loader 行为参数（recent 2 stages / 1..N filter / token 估算）原样保留 — 已 Read 复核
- [x] `grep -nE '(50.{1,3}80|50.{1,3}100|30.{1,3}50|≤ 200 chars|≤ 10 entries)' simulation/retrieval/load_strategy.md` 返回空 — 已跑，无残留
- [x] `docs/todo_list.md` 正文已无 `T-LOAD-STRATEGY-WORLD-EVENTS-BOUND` 条目；Index 段子表 / 汇总行已刷新 — `grep` 全文 0 命中
- [x] `docs/todo_list_archived.md` `## Completed` 段已加该条瘦身记录，链向本 log — 已 Read 确认

## Step 7 全库 review 发现（scope 外同类问题，未本次修，向用户汇报）

- `simulation/retrieval/index_and_rag.md` L44-49 / L222-225：同一类"复述 schema bound"模式（`30–50 字 / 150–200 字 / ≤15 字` 等），与 load_strategy.md 同属 conventions.md `Cross-File Alignment` 表"Loading strategy"行
- `simulation/contracts/baseline_merge.md:59`：`character_arc … single string (≤ 200 chars)` 同样复述 schema bound
- `ai_context/decisions.md:102` (#34)：`Character stage_snapshot.stage_events = … 50–80 CJK chars, hard gate` — 决策历史叙述里嵌入具体数值；属边界情况（决策记录 vs 文档复述）

均为 scope 外发现，本次未动；建议下次在用户决定后通用清理或登记 todo。

## Completed

- **Status**: DONE
- **Finished**: 2026-04-29 00:13:26 EDT
