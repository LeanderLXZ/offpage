# Operational Conventions

This file lists operational rules that are easy to forget during long
sessions. Re-read triggers live in `CLAUDE.md` / `AGENTS.md` Dilution
Self-Check.

## Logging

`docs/logs/` 采用 **三时点契约**（PRE / POST / REVIEW）：一份 log 文件贯穿一次 `/go` 从决策到落地到复查的完整生命周期。

- Filename format: `YYYY-MM-DD_HHMMSS_slug.md`
  - **HHMMSS is mandatory.** Get it with:
    `TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'`
  - Bad: `2026-04-08_foo.md` — Good: `2026-04-08_012400_foo.md`

### 三时点

1. **PRE（/go Step 1）** — 在任何代码 / schema / prompt / docs / ai_context / skill 改动之前写入：
   - `背景 / 触发`：会话上下文、用户原始需求
   - `结论与决策`：已拍板的方案
   - `计划动作清单`：准备改的文件 + 每份的改动要点
   - `验证标准`：checkbox 级，完成时要怎么验
   - `执行偏差`：占位段落，中途偏离计划时追加
2. **POST（/go Step 7）** — 同一份 log 追加：
   - `已落地变更`：实际改了什么
   - `与计划的差异`：新增 / 删除 / 修改
   - `验证结果`：PRE 验证标准逐项打勾或打叉
   - `Completed`：`Status: DONE | BLOCKED` + `Finished` 时间戳
3. **REVIEW（/after-check Step 5）** — 同一份 log 追加双轨复查摘要：
   - `复查结论` 的轨 1 / 轨 2 计数（完整报告在对话里，log 不贴全文）
   - `复查时状态`：`REVIEWED-PASS | REVIEWED-PARTIAL | REVIEWED-FAIL`
   - `Conversation ref`：指向同会话 /after-check 输出

### 契约要点

- `/go` 启动即先落 PRE log → 回显路径给用户（`LOG: docs/logs/...md`）。**没 PRE log 不得改文件**
- `/after-check` 强制读 PRE 段作为 intent 基线；log 缺失 → 对账轨跳过 + 扩散轨继续
- `/after-check` 回写 log 是**唯一的写操作例外**，其他仍然只读
- 历史 log（本契约之前已存在的单时点 log）不动；新契约从本次之后的 /go 起生效

## Cross-File Alignment

When you change a concept, update **all** files that reference it. The
alignment graph:

| Changed | Also update |
|---------|-------------|
| `schemas/**/*.schema.json` | `docs/architecture/schema_reference.md`, `schemas/README.md`, prompt templates, validator.py |
| `docs/requirements.md` | `ai_context/requirements.md`, `ai_context/decisions.md` |
| Loading strategy | `simulation/retrieval/load_strategy.md`, `simulation/flows/startup_load.md`, `simulation/retrieval/index_and_rag.md`, `docs/architecture/data_model.md`, `ai_context/architecture.md` |
| Extraction workflow | `docs/architecture/extraction_workflow.md`, `automation/prompt_templates/`, `automation/persona_extraction/`, `ai_context/architecture.md` |
| Runtime prompts | `simulation/prompt_templates/`, `simulation/` |
| Any durable decision | `ai_context/decisions.md` |
| /go or /after-check triggered change | `docs/logs/` 的 PRE / POST / REVIEW 三段按时点写齐（缺 PRE 不得动文件；/after-check 强制回写 REVIEW 摘要） |

After changes, grep for the old phrasing to catch stale references.

## Naming and Identifiers

- Chinese works → Chinese `work_id`, `character_id`, and path segments.
- `stage_id` is always the compact English code `S###` (three digits,
  zero-padded, e.g. `S001`), regardless of work language. It aligns with
  the `M-S###-##` / `E-S###-##` / `SC-S###-##` / `SN-S###-##` family.
- `stage_title` carries the human-readable short name (≤ 15 chars,
  Chinese for Chinese works). It lives alongside `stage_id` in
  `stage_plan.json` and every `stage_catalog.json` entry, and is the
  label shown at bootstrap stage selection.
- `ai_context/` remains English.
- JSON field names may be English; content text follows work language.

## Generic Placeholders in Canonical Docs

`schemas/`, `docs/requirements.md`, `docs/architecture/`, `ai_context/`,
`prompts/`, and `automation/prompt_templates/` describe the current
design and are read by LLMs at extraction time. They must stay
work-agnostic:

- No real book titles, character names, place names, plot details.
- Schema `description` examples stay structural ("例如：某关键他人做出
  自我牺牲行为"), not narrative; or omit the example entirely.
- Field identifiers in examples use placeholders like
  `<character_id>` / `<stage_id>` (e.g. `S001`).
- Do not narrate history ("旧 / legacy / 已废弃 / 原为 / 已移除 /
  renamed from"). History lives in `docs/logs/` + git.

Exempt (history is the point): `docs/logs/`, `docs/review_reports/`,
`works/*/` sample outputs, git commit messages.

## Data Separation — Hard Rules

- User data under `users/` — never touch `works/` canon from user context.
- Baseline files = extraction anchors only, **not loaded at runtime**.
- Stage snapshots are **self-contained** — never merge with baseline at
  runtime.
- Length rules are hard schema gates: world + character `stage_events`
  50–80 字 per entry; memory_timeline `event_description` 150–200 字,
  `digest_summary` 30–50 字; `knowledge_scope` items ≤ 50 字 each;
  `relationships[*].relationship_history_summary` ≤ 300 字 (default; tunable
  via `[repair_agent].relationship_history_summary_max_chars`).
- Count caps (hard schema gates): `knowledge_scope.knows` ≤ 50,
  `does_not_know` ≤ 30, `uncertain` ≤ 30. Over-limit → trim by dropping
  items least relevant to current-stage decisions / core_wounds /
  active_obsessions / active relationships; prefer dropping daily
  commonsense, early details without triggers, items already in
  `memory_timeline`.

## Git

- Do not commit: novels, databases, embeddings, caches, user packages.
- Do not amend others' commits.
- **Default branch is `master`.** Always stay on `master` unless actively
  running extraction. Checkout extraction branch only when starting or
  resuming `python -m automation.persona_extraction`. When extraction
  pauses or finishes, checkout back to `master` immediately.
- **Code changes go to `master` first.** All modifications to code,
  schemas, prompts, docs, and `ai_context/` must be committed on
  `master`, then merged into the extraction branch (`git merge master`
  from the extraction branch). Never develop directly on the extraction
  branch.
- Extraction branch is for extraction data commits only (stage outputs).
  Squash-merge to `master` when all stages complete.
- Enforcement: (1) `run_extraction_loop` / `run_full` in
  `automation/persona_extraction/orchestrator.py` wrap extraction in
  `try / finally: checkout_master(...)`, so every exit path returns to
  `master`; (2) a SessionStart Claude Code hook
  (`.claude/hooks/session_branch_check.sh`) warns on new sessions when
  the working tree is on a non-master branch with no orchestrator
  process running. See `architecture.md` §Git Branch Model.

## Post-Change Checklist

After completing a task, run through:

1. Did I update all aligned files? (See table above)
2. Did I create the PRE log at /go Step 1 and update its POST段 at Step 7 (同一份文件)?
3. Did I update `ai_context/` if the change is durable?
4. Did I grep for stale references to the old state?
5. Did I run the relevant Python imports to verify no breakage?
