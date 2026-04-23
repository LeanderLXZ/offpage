# Instructions For Future AI Agents

## Entry Point

`ai_context/` is the handoff entry point. Do not reread full chat history,
the novel, or large artifact directories by default. Do not load `prompts/`
unless the user asks.

After finishing `ai_context/`, **stop and wait for the next instruction.**
Do not start modifying code, schemas, prompts, or docs on your own
initiative — even if you spot something that looks off. Reading
`ai_context/` is context loading, not a task brief. Only act when the user
gives an explicit request.

## Reading Order

1. `conventions.md`
2. `project_background.md`
3. `requirements.md`
4. `read_scope.md`
5. `current_status.md`
6. `architecture.md`
7. `decisions.md`
8. `next_steps.md`
9. `handoff.md`

Dilution protection (when to re-read what) lives in `CLAUDE.md` /
`AGENTS.md` as a three-question self-check — not duplicated here.

## Update Expectations

Update `ai_context/` only for durable repository truth (instructions,
prompts, schemas, architecture, directory rules, data-model conventions,
retrieval strategy). Runtime / extraction progress goes in work-local or
user-local progress files.

For durable changes, update the relevant subset of: `current_status.md`,
`handoff.md`, `next_steps.md`, `architecture.md`, `decisions.md`, plus one
timestamped entry under `docs/logs/`.

## Logging (critical)

Every meaningful change outside `ai_context/` → one log file at
`docs/logs/{YYYY-MM-DD_HHMMSS}_{slug}.md`, written **across three
timepoints** (PRE / POST / REVIEW) by `/go` and `/after-check`:

- **PRE** (created at /go Step 1, before any file change): 背景 / 结论与决策 / 计划动作清单 / 验证标准
- **POST** (appended at /go Step 7, before commit): 已落地变更 / 与计划差异 / 验证结果 / 状态 DONE|BLOCKED
- **REVIEW** (appended at /after-check Step 5): 双轨复查摘要 + 状态 REVIEWED-PASS|PARTIAL|FAIL

HHMMSS is mandatory. See `conventions.md` §Logging for the full
contract and Cross-File Alignment table.

Layer summary:
- `ai_context/` — compressed current truth
- `docs/architecture/` — formal architecture documentation
- `docs/logs/` — timestamped historical records (write-mostly)
- `docs/todo_list.md` — see next section

## TODO list file (`docs/todo_list.md`)

Chinese-language working queue of planned-but-unfinished engineering
tasks (file paths, line numbers, change lists, verification, deps).
Sections: 立即执行 / 下一步 / 讨论中（未定案）. Read-on-demand —
**not** part of the session-start `ai_context/` reading order.

Full usage rules (what to record, how to update, when to delete, how to
read) live inside `docs/todo_list.md` itself under `## 文件说明`. Read
that section before editing the list; do not duplicate the rules here.

## Project Focus

The core is decision logic, memory logic, and relationship logic — not
surface tone mimicry. Keep layers separate (objective plot, character
definition, memory, misunderstanding, voice, behavior, conflicts). The
original novel is the highest authority. Explicit canon vs inference.
Stage differences preserved. Runtime uses retrieval + compilation, not
one giant prompt.
