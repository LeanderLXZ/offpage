---
name: aicontext_header_refine
description: ai_context 维护头全英文化、去硬行数预算、改标题措辞
type: docs
---

# aicontext_header_refine

- **Started**: 2026-04-23 16:41:43 EDT
- **Branch**: master
- **Status**: PRE

## 背景 / 触发

前一轮 `/go`（commit `3e30f62`，log
`2026-04-23_161632_aicontext_compress.md`）给 `ai_context/` 每份
文件加了统一的 `<!-- MAINTENANCE -->` 维护准则头。用户审阅后要求
三处修正：

1. `ai_context/` 原本就该全英文（见 `conventions.md` §Naming 里的
   "`ai_context/` stays English"），但维护头正文是中文的 —— 破坏
   了这个约束
2. 维护头里的"预算：architecture / decisions / requirements 各
   ≤ ~150 行；全目录读完 ≤ 几千 token" 表达成硬预算，但用户意图
   是"只是软建议，没有硬上限"
3. 开头的"更新 ai_context/ 前读"表述宽泛（像是在讲整个目录），
   改成"更新本文件前阅读"指向单个文件更准确

## 结论与决策

- 所有 11 份 `ai_context/*.md` 的 `<!-- MAINTENANCE -->` 注释块
  统一改为英文
- 删去第 5 条"预算"的具体行数 / token 数，保留"短比长好、详细
  下沉到权威源"的软建议；或者直接把这条合并进第 2 条"优先删而
  不是加"，不再单列
- 开头"MAINTENANCE — 更新 ai_context/ 前读" → 英文版
  "MAINTENANCE — read before editing this file"
- 5 条原则内容保持（英文化后）：
  1. Write "what / where to find", link to sources
  2. Prefer deletion; check merge with existing before adding
  3. Current design only; no "legacy / deprecated / formerly"
  4. No real book / character / plot names; use placeholders
  5. Short is better than long; detailed content belongs in linked sources

## 计划动作清单

- file: 11 份 `ai_context/*.md` → 替换顶部维护头注释块，全英文、
  去硬预算、改标题措辞。内容段不动。
- file: `docs/logs/2026-04-23_164143_aicontext_header_refine.md` → 本 log

## 验证标准

- [ ] `grep -rn "更新 ai_context" ai_context/` 为 0（标题中文化消失）
- [ ] `grep -rn "预算" ai_context/` 为 0（硬预算表述消失）
- [ ] `grep -rE "[\\u4e00-\\u9fff]" ai_context/*.md` 命中的行都在
  内容段（不在维护头里）—— 即维护头全英文
- [ ] 11 份文件的维护头内容 100% 一致（逐字）
- [ ] `wc -l` 每份文件变化 ≤ ±2 行（只是替换头，不动正文）
- [ ] master commit 后 extraction 分支 merge 干净

## 执行偏差

**扩大范围**：Step 6 grep 时发现除了维护头之外，`conventions.md` /
`decisions.md` / `architecture.md` 内容段里还有一些中文短语（log
三时点的中文字段名、`字` 作为长度单位、`旧` 作为 legacy 同义词示例）。
既然本次 /go 的 intent 是"ai_context 全英文"，顺便把这些非-literal
的中文段英文化：

- log 三时点字段名：`背景 / 结论与决策 / 计划动作清单 / 验证标准` →
  英文；`已落地变更 / ...` → 英文；`双轨复查摘要` → 英文
- `三时点齐全` → `PRE / POST / REVIEW segments all present`
- `字` 长度单位 → `CJK chars`（architecture.md + conventions.md + decisions.md 多处）
- `("旧", "legacy", "已废弃", "原为", "renamed from")` → `("legacy", "deprecated", "formerly", "renamed from")`

**保留的中文 literal**（真实引用，不改）：
- `simulation/prompt_templates/历史回忆处理规则.md` / `认知冲突处理规则.md` — 真实文件名
- `角色A` — 占位符约定（handoff.md 自身定义）
- `## 文件说明` — `docs/todo_list.md` 里的真实节标题
- `本名/化名/代称/称呼/封号/道号` — `schemas/character/identity.schema.json` 的 enum 值

<!-- POST 阶段填写 -->

## 已落地变更

- 11 份 `ai_context/*.md` 顶部的 `<!-- MAINTENANCE -->` 注释块全部
  替换为英文版（内容为 4 条原则 + 一句"Shorter is better" 软建议，
  不再提硬行数预算）。md5 验证 11 份头完全一致
- 标题由"更新 ai_context/ 前读" → "read before editing this file"
- `conventions.md:23-25, 47, 71, 82-86` — log 字段名 / 三时点表述 /
  legacy 例子 / 长度单位 `字` → 英文等价
- `architecture.md:98` — `(150–200 字) / (30–50 字)` → `CJK chars`
- `decisions.md:91, 93, 94` — 同上 `字` → `CJK chars`
- 本 log 文件

每份 `ai_context/*.md` 正文行数变化 +1（新维护头 9 行 vs 老 8 行）。

## 与计划的差异

- **新增**：Step 6 扩大到正文中文短语的英文化（见上 "执行偏差"）

## 验证结果

- [x] `grep -rn "更新 ai_context" ai_context/` = 0 — 已验证
- [x] `grep -rn "预算" ai_context/` = 0 — 已验证
- [x] 11 份维护头 md5 全同（`5d32ea1c7fff6cc905cd8d235179a701`）— 已验证
- [x] 每份文件 ±2 行（实测 +1）— 已验证
- [x] 维护头全英文 — 已验证；内容段中文仅剩 4 处 real-literal 引用（真实文件名 / schema enum / 约定占位符 / 真实节标题），其余全英文化
- [ ] master commit 后 extraction merge 干净 — 待 Step 8 / Step 9

## Completed

- **Status**: DONE
- **Finished**: 2026-04-23 16:52:07 EDT
