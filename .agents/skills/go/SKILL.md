---
name: go
description: Heavyweight plan-to-ship path (PRE log → implement → verify → docs & alignment → review → ship) for multi-file / cross-file changes. Triggers: go / full /go / this change needs review / spans multiple modules / heavyweight landing.
---

> **Language**: per `ai_context/skills_config.md §Language`. Surface → axis (read once; the per-step `> Language` reminders that used to repeat on every step are gone — inline re-anchors survive ONLY at the disk→user seams where drift actually bites):
>
> | Surface | Axis |
> |---|---|
> | disk-bound output — PRE/POST log, docs, ai_context, code / skill / config edits, commit message | `content_language` |
> | user-facing — chat prose, `<ask tool>` prompts + labels, progress entries, Strategy / findings / state lines | `conversation_language` |
> | code identifiers, file paths, field names, frontmatter keys, structural prefixes (`Step N:` / `LOG:` / `PRE` / `POST` / `Status:` / `REVIEWED-*`), quoted tool stdout/stderr | stay English |
>
> Re-anchors are kept at: **Step 0** (Language-axes anchor line) · **Step 3** (verify report) · **Step 5** (review render + sub-agent injection) · **Step 6** (wrap-up) — these are the disk→user seams + sub-agent boundary. **Sub-agents do not inherit this config — whoever dispatches one MUST append the two axis values to its prompt.**

# /go — heavyweight landing path

Execute per the discussion above; if a step is N/A this round, say so explicitly ("skip Step X"). If `$ARGUMENTS` is present, it is the focus of this change.

The seven steps map one role each: **Step 0** work-location · **Step 1** PRE-log registration · **Step 2** implement · **Step 3** verify · **Step 4** docs-&-alignment maintenance · **Step 5** review · **Step 6** ship. Other skills cite these roles, not the numbers.

## Progress reporting

> Progress-tool entries (`content` field) are user-facing → `conversation_language` (the `Step N:` prefix stays English; subtitle after the colon translates). Same for sub-task entries `Step Na:` / `Step Nb:` / ….

The flow below is split into `## Step 0:` ~ `## Step 6:`.

**Before entering Step 0**: call **<progress tool>** to pre-register Step 0 ~ Step 6 (one entry per step, `content` as `Step N: <sub-section title>`, all `status` = `pending`). This is a hard requirement — **do not proceed without calling <progress tool>**.

On entering each step: call **<progress tool>** to flip the current step to `in_progress` (in the same call, mark the previous step `completed`), then do the actual work. **Do not skip the call when crossing steps.** Progress shows through the <progress tool> UI; **do not print progress lines like `[/go] Step N: ...` in the conversation**.

Skipping a step: call **<progress tool>** to mark the entry `completed`, and print one line `Step N skipped (reason: …)` — the reason is information the UI lacks, so keep this line; do not silently skip.

Final step done: call **<progress tool>** to mark the last entry `completed`.

**Sub-tasks (optional, enable on demand)**: when a step's internal work is obviously several independent small tasks (e.g. Step 2 simultaneously changing schema / prompt / code / config blocks), upon entering that step you may **expand** `Step N: <title>` into `Step Na:` / `Step Nb:` / … (alphabetical, replacing the original entry in the same call), flipping state as sub-tasks progress. **Only the currently active step expands**; others stay collapsed. Once its sub-tasks are all `completed`, **on entering the next step fold them back into one** `Step N: <title>` `status=completed`. UI is always "current step fine-grained + others collapsed". Do not nest a second layer (no `2a-1`).

**<progress tool> resolution**: Claude → `TodoWrite` (rendered as "Update Todos"); Codex → `update_plan`; other runtimes (no structured progress tool, e.g. Copilot agent mode) → maintain a markdown checkbox list in the response text, rewriting the whole block before each state change. Semantic alignment: pre-register + flip state + mark complete (incl. sub-task expand / fold-back).

**<ask tool> resolution**: Claude → `AskUserQuestion` (max 4 questions per call, batch beyond); other runtimes → enumerate questions + options in the response text and let the user answer in one pass (still max 4 per batch).

## Step 0: Setup — load config + lock work location

> User-facing — render the `<ask tool>` prompts, option labels, the Strategy line, and the Language-axes anchor line in `conversation_language`. Structural prefixes (`Strategy:` / `Language axes:`) lead the line; axis values are echoed verbatim from §Language.

**0a — Load skills config.** `Read` `ai_context/skills_config.md`.

- File missing / any section header missing → fail loudly: print the missing items + prompt to complete per plugin template, stop.
- Section content `(none)` or empty → skip the related steps for that section (treat as N/A).
- Section lists a concrete path but it does not exist → fail loudly: report the drift, stop, wait for the user to fix.

This skill uses: `## Background processes` (0b dirty-question process detection), `## Do-not-commit paths` (Step 6 commit scan), `## Timezone` (Step 1 / Step 6 timestamps), `## Sensitive content placeholder rules` (Step 4 / Step 5), `## Data contract directories` (Step 3 / Step 5 contract scan).

**0b — Lock the work location.** The `/go` git contract: **Step 0 asks once** (work location); **Steps 1–5 never ask mid-run**; **Step 6** decides whether to ask once more (worktree follow-up / stash pop). `/go` does not implicitly "switch to main first" — branch switching / worktree launch is the user's explicit pick here.

- `git branch --show-current` → current branch `<X>`; `git status --porcelain` → clean / dirty; probe per `## Background processes` (pgrep patterns + artifact paths; skip when empty). Merge the dirty summary + associated processes into one line `<dirty summary / associated process P>`.
- **Orphan-stash probe** (before either question): `git stash list | grep -F "/go autostash"` to count earlier `/go` autostash entries still on the stack. Non-zero means a previous `/go` crashed between Step 1 and Step 6 (no pop); pushing another autostash on top makes the stack ambiguous. Carry as `<stash-orphan-count>` (default 0).
- **<ask tool>** one question, different option sets for clean / dirty:

**Clean path** (working tree clean, no associated processes) — Question: "Current branch is `<X>`. Please choose `/go`'s work location."

1. **Execute in place on current branch `<X>` (recommended)** — stay on `<X>`; edits / PRE log / commit all land there.
2. **Switch to a specified branch then execute** — branch name required; uses `git checkout` (not worktree): local branch exists → `git checkout`; else ask base branch then `git checkout -b <branch> <base>`.
3. **Execute in a separate worktree** — branch name required; enters worktree follow-up.

**Dirty path** (working tree dirty or associated process) — Question: "Current branch is `<X>`; working tree detected `<dirty summary / associated process P>`. Please choose how to handle it." When `<stash-orphan-count>` > 0, prepend: `⚠️ Detected <stash-orphan-count> existing "/go autostash" entr(y/ies) from a previous crashed run; consider \`git stash drop\` / \`git stash pop\` before re-stashing (option 4 pushes another on top).`

1. **Commit current WIP progress, then execute `/go` (recommended)** — reuse the `/commit` Step 1–3 scan contract (do-not-commit paths + untracked files + large-file fallback; **does not bypass** Step 6 safety checks) for one WIP commit (default `wip: <X> snapshot before /go`, subject overridable by `$ARGUMENTS`), then stay on `<X>`.
2. **Execute `/go` directly without handling** — uncommitted changes commit together with this change (user confirms intended).
3. **Execute in a separate worktree** — branch name required; enters worktree follow-up (worktree and current dirty tree do not interfere).
4. **Stash current changes (`git stash`) then execute `/go`** — `git stash push -u -m "/go autostash <X>"`, stay on `<X>`; Step 6 auto `git stash pop`. When `<stash-orphan-count>` > 0 the label gains a `(WARN: <N> orphan autostash already on stack)` suffix.

**Worktree follow-up (Clean opt 3 / Dirty opt 3)** — ask: "Which branch should the worktree check out? Provide the branch name."
- Branch exists locally → `git worktree add ../<repo>-<branch> <branch>`; edits / PRE log / commit under that path.
- Branch does not exist → ask "Branch `<branch>` does not exist. Provide the base branch (default = `<X>`)", then `git worktree add -b <branch> ../<repo>-<branch> <base>`.
- Path conflict (directory exists) → stop and report; let the user decide.

**Switch-branch follow-up (Clean opt 2)** — same "branch name → ask base if absent" flow, but `git checkout` / `git checkout -b <branch> <base>`, no worktree. Clean-path only — switching on a dirty tree pollutes it; use Dirty opt 1 / 4 first.

After selecting, print **two declaration lines**:
- **Strategy line**: `Strategy: <chosen path>` (e.g. `current branch develop in place` / `switch to feature/x in place` / `../holo-main worktree isolation (branch=main)` / `WIP commit then stay on develop` / `stash then stay on develop (Step 6 auto pop)`). Natural-language portion translates; `Strategy:` leads.
- **Language-axes anchor line**: `Language axes: conversation_language=<value> · content_language=<value> (source: ai_context/skills_config.md §Language)` — axis values verbatim from §Language; bracketed source stays English. A deliberate high-salience anchor planted before Steps 1–6 accumulate context.

If `git checkout` / `git worktree add` / WIP commit / `git stash` fails → stop and report, wait for the user. **No further questioning after Step 0** until the end of Step 6.

## Step 1: PRE log registration (register before acting)

> **Cross-skill protocol ownership**: this Step defines the PRE log template (section names, `Status: PRE` token, the `## Background / Trigger` / `## Conclusion and decisions` / `## Planned action list` / `## Validation criteria` / `## Execution deviations` subsection set) — consumed by `/post-check`'s intent-baseline read. Renaming any subsection, the `Status` token, or the header structure requires a lockstep edit in `/post-check` per `ai_context/conventions.md §Cross-File Alignment` (row: "PRE/POST/REVIEW change-log protocol"). `/recent-activity` reads only the file head 25 lines and is heading-insensitive — not a lockstep consumer.

> **Language**: the PRE log is a disk artifact → `content_language`, even though its `## Background / Trigger` / `## Conclusion and decisions` paraphrase a `conversation_language` discussion (translate the gist; don't carry the discussion's language over). The `LOG:` echo line is user-facing.

**Before any code / schema / prompt / docs / ai_context / skill change**, create this round's log file and write the PRE section. This is the intent baseline for `/post-check` and the anti-drift anchor for Step 5; mandatory.

- Filename: `<change_logs_path>/<filename pattern with slug substituted>` — `<change_logs_path>` is `## Activity sources.Change logs.Path` and the pattern is `.Filename time pattern` (defaults: `logs/change_logs/` + `{YYYY-MM-DD}_{HHMMSS}_{slug}.md`). HHMMSS per the `## Timezone` command template; if §Timezone is missing / fails, use its declared fallback (system-tz `date '+%Y-%m-%d_%H%M%S'`). slug = semantic short English name.
- Echo the path back: one line `LOG: logs/change_logs/...md` (label `LOG:` stays English) for later `/post-check` reference.

The PRE section must contain:

```markdown
# {slug}

- **Started**: {YYYY-MM-DD HH:MM:SS} {timezone abbrev per `## Timezone`}
- **Branch**: {work branch at /go entry}
- **Type**: GO
- **Status**: PRE

## Background / Trigger
{session context, user original ask, upstream discussion chain summary}

## Conclusion and decisions
{plan decided at /go entry: direction picked, what changes, what does not}

## Planned action list
- file: {path} → {change focus}
- ...

## Validation criteria
- [ ] {e.g. Import has no error}
- [ ] {e.g. data contract validation passes}
- [ ] {e.g. grep residue = 0}
- ...

## Execution deviations
(append during execution; write "none" if no deviation)
```

Write the PRE section, then **enter Step 2**. If the PRE log write fails (IO error, path not writable, disk full, permission denied) → **stop and report; do not enter Step 2**. `ai_context/conventions.md` §Logging "No PRE log → do not start modifying files" is the operative invariant — a failed write means no PRE log exists.

## Step 2: Implement code / schema / prompt / config

Change schema, prompt template, architecture code, config per the discussion.

- **First confirm the PRE "Validation criteria" has ≥ 1 concrete executable item** (e.g. `import has no error` / `grep residue = 0` / `smoke X passes`; not vague "as long as it works"); if vague → add concrete ones now. Step 3 runs exactly this list.
- Consult the Cross-File Alignment table in `ai_context/conventions.md` to list linked files (skip if the table does not exist; judge by intuition).
- **Do not stream-edit across files.** If mid-implementation you sense a doc / sibling file also needs changing, append it to the PRE log's **Execution deviations** and handle it in Step 4 — do not chase it now (that is how drift starts).

## Step 3: Verify (adaptive — smoke + data contract)

> User-facing — render the pass/fail report in `conversation_language`. Quoted tool stdout/stderr stays verbatim; structural labels (`PASS:` / `FAIL:`) stay English.

**Read the PRE "Validation criteria" section first** and run exactly those declared checks — do not silently drop or substitute one (this keeps the verification guarantee honest). Then scale to what actually changed:

- **Skip the whole step** when this round's diff touches **no executable code AND no data-contract file** (pure docs / ai_context / prompt-text / comments) → print `Step 3 skipped: no executable / data-contract change this round`. The skip criterion is the **file types in the diff** (objective), not a subjective "looks safe".
- **Executable code changed** → import check + smoke the key functions / touched code paths.
- **Diff touches `## Data contract directories`** (skip when `(none)`) → run the project's contract validator once (JSON Schema → `jsonschema` / `ajv`; OpenAPI → `openapi-spec-validator` / `redocly lint`; proto → `protoc --lint_out`; pydantic → import + `model_rebuild()`; SQL DDL → migration dry-run).

Fix errors immediately. Each PRE Validation-criteria item ends this step either checked (passed) or explicitly marked blocked with cause — carried into Step 6's POST "Validation results".

## Step 4: Docs & alignment (durable docs + cross-file alignment + maintenance)

> **Compactness** (ai_context writes): shorter beats longer; each entry is a summary, not a dump; ≤ 5 lines / entry, push detail to `docs/<topic>.md` / schemas / docstrings; never sacrifice accuracy for length; do not touch content unrelated to this edit.

Implementation (Step 2) is done — now land the durable record of what was **actually built**, then verify nothing downstream drifted. **Author first, then align in the same step** (no separate pre-implementation authoring pass: docs follow implementation). Findings discovered here that need fresh design prose get written here; findings that need re-discussion go to Step 5's "suggest registering" list, not here.

**Author durable docs** (filter by scope actually touched; do not blindly run all):
- **`docs/requirements.md` + `ai_context/requirements.md`** (paired, lockstep): user-visible functional contract / acceptance criteria / boundary changes.
- **`docs/architecture/` + `ai_context/architecture.md`** (paired, lockstep): new module / interface / state machine / call-graph change / branch strategy / workflow contract / entry point.
- **`ai_context/decisions.md` + `docs/decisions.md`** (paired, lockstep): durable decisions this round (decision = "why"; architecture / requirements = "what" — add both when a trigger word above is hit). Entry criterion: record only a genuinely contested decision a future reader might re-propose. **Before appending, run the lifecycle check**: does this round overturn an existing `#N`? → **supersede in place** (replace the entry's content in BOTH files, number stays; if the old approach was actually tried and reverted, keep a half-line `(tried X, reverted, see log)` trace in the archive entry). Did this round kill an entry's whole topic, with the evidence already in this round's context? → prune it from both files (gap stays). Only a genuinely new decision appends: index gets 1–2 lines (statement + `→ docs/decisions.md #N`), archive gets the full entry (statement + rationale + boundary + source pointer) under the same number and section. Full-scan prune stays `/compress-ai-context`'s job — do not sweep beyond this round's evidence.
- **Prompt sources** (`## Activity sources.Prompt sources.Path`; skip `(none)`): prompt behavior / template changes.
- **`README.md`**: only on directory / entry-point / startup change.
- Authoring constraints: replace real content per `## Sensitive content placeholder rules` (skip when empty); write the current design only — no "old / legacy / deprecated / formerly".

**Cross-file alignment** (consult the Cross-File Alignment table in `ai_context/conventions.md`; if absent, judge by the files touched in Step 2 / Step 4) — check schema / prompt / code / docs / ai_context / README consistency across:
- field names / params / return values / state values / error codes
- flow descriptions / state machines / gating timing
- terminology / concept naming

A file that should have synced but did not → fix as a gap-fix (one or two lines in place; a whole rewritten paragraph is authoring, do it here too).

**ai_context durable maintenance**: `handoff.md §Current State` (cell updates: Project Stage / What Exists / Current Gaps / Rules In Effect) · `§Next Steps` (new High / Medium / Later rows) · `§What The User Cares About` (new preference / taste rule).

**todo_list maintenance**: completed entries this round → **move wholesale to the `## Completed` section of the archived TODO list** (`## Activity sources.Archived TODO list.Path`) — slimmed: title + completion form + 1-line summary + this round's log link; then **refresh the top `## Index`** of `docs/todo_list.md` (the `/todo` skill reads only the index). ⚠️ Maintain only entries this change directly produced / completed; Step 5 review findings do **not** register here.

## Step 5: Review (adaptive — scale to change size)

> Disk-bound — an in-place finding fix follows the edited file's `content_language` rules. User-facing — render the "suggest registering to todo_list" chat list in `conversation_language` (structural labels `file:` / `line:` / `suggest segment:` stay English; only the summary prose translates).
>
> **Language anchor reset (render-time)**: before emitting the suggest-list, re-echo verbatim `conversation_language=<value>` · `content_language=<value>` from §Language. Step 4 just wrote `content_language`-bound edits; this refreshes recency at the USER-facing render so listed items stay in `conversation_language` even when sub-agent reports return English-phrased findings.

**Re-read the PRE log first** (Conclusion and decisions / Planned action list / Validation criteria) — after Steps 2–4's editing context you have drifted from original intent; recalibrate before scanning. Anti-over-engineering check: confirm you did **what was planned, no more**.

**Two review dimensions** (the old four lines fold in as checklists — nothing dropped):

1. **Code dimension** — changed code + its upstream / downstream (callers / callees / importers / shared state / shared data flow). Checks BOTH **wiring** (field names / params / return values / state machines / gates still coherent; imports run) AND **correctness** (boundary conditions, null / None, exception paths, concurrency, retry / rollback, error handling hiding bugs; data-loss / security / performance regressions; missed state-machine / gate / invariant branches). One reviewer reviews a file-group fully — wiring and correctness together, the way a human reads a file.
2. **Surface dimension** — `ai_context/` / `docs/` / `## Data contract directories` (skip `(none)`) / prompt-sources path (skip `(none)`) / README / directory structure / committed example artifacts. Checks: descriptions consistent with this change; residual old descriptions / fields / flows; `## Sensitive content placeholder rules` violations; `old / legacy / deprecated / formerly` wording; if filenames / directories changed, trace all reference points.

**Scale the fan-out to the change size** (do not always spawn the max):
- **Small** (≤ 2 files, no data contract, no cross-module spread) → a single serial inline pass covering both dimensions; **no sub-agents**.
- **Medium** → one sub-agent per dimension (2 in parallel).
- **Large** → **shard the Code dimension by file-group** across N sub-agents (each does wiring + correctness on its shard); Surface usually stays one. Scale by sharding files, **not** by adding more dimensions.

> **Each dispatched sub-agent** must (a) read the PRE log's PRE section before scanning — stuff the `LOG:` path into its prompt and require it; independent context drifts otherwise — and (b) carry the language axes appended at the **end** of its prompt (recency-favorable; sub-agents just read English source, so the directive needs recency over the scanned content): "Reply in `conversation_language`=`<value>`; write any disk artifacts in `content_language`=`<value>`; both from `ai_context/skills_config.md §Language`."

**Findings handling** (issues here do NOT get written directly into `docs/todo_list.md`):
- **One-line fixes** (typo, missed placeholder, missing import, obvious slip, single dangling reference) → **fix on the spot**, no tail.
- **Bigger / cross-scope / need re-discussion / outside this round's intent** → **do not write into `docs/todo_list.md` yourself**; list a "**suggest registering to todo_list**" block in chat, each entry with file + line, issue summary, suggested segment. The user decides; then `/todo-add` or the next `/go` lands it — avoid polluting todo_list history with findings outside this round's intent.

## Step 6: Ship — POST log + commit + wrap-up

> **Cross-skill protocol ownership**: this Step defines the POST template (`## Landed changes` / `## Diff from plan` / `## Validation results` / `## Completed` subsection set) and the `Status: DONE | BLOCKED` transition from `PRE`. Consumed by `/post-check` (REVIEW append — expects the POST section to exist and reads `Status` to decide the `REVIEWED-*` flip). Renaming any subsection, the `Status` tokens, or the `Completed` block requires a lockstep edit in `/post-check` per `ai_context/conventions.md §Cross-File Alignment` (row: "PRE/POST/REVIEW change-log protocol").
>
> Disk-bound POST log + commit message use `content_language`. User-facing wrap-up `<ask tool>` prompt / final state line / `stash popped` confirmation use `conversation_language` (structural `stash` / `worktree` / `HEAD` stay English).
>
> **Language anchor reset (render-time)**: before the wrap-up prose / `<ask tool>` prompt / final state line, re-echo verbatim `conversation_language=<value>` · `content_language=<value>` from §Language. Steps just wrote `content_language`-bound disk artifacts; this refreshes recency at the last USER-facing surface `/go` produces.

**6a — POST log.** Append the POST section to **the same log file Step 1 created** (do not create a new file):

```markdown
<!-- POST phase fills in -->

## Landed changes
{one-line outcome summary; the file-level detail IS the commit diff — do not re-enumerate it here}

## Diff from plan
{vs PRE "Planned action list": what was added / removed / modified; "none" if nothing}

## Validation results
- [x] {PRE validation 1} — {output summary}
- [ ] {PRE validation 2} — {failure cause}
- ...

## Completed
- **Status**: DONE | BLOCKED
- **Finished**: {timestamp per `## Timezone`, same timezone as PRE Started}
```

**6b — Commit.** Step 0 locked the work location; the commit **lands on the branch selected there**.
- `git status` shows only this change; scan per `## Do-not-commit paths` + (`.gitignore` + `ai_context/conventions.md`) as fallback.
- Message style aligned with `git log --oneline -10`.
- **This change + PRE/POST log file are one commit** — not split into `<slug>: ...` + `log(<slug>): ...`.
- After commit, `git status` confirms clean.
- **Worktree path**: commit runs inside the worktree; **do not auto-clean** it (cleanup is 6c). `/go` stays at the Step-0 location, never switches back behind the user's back.

**6c — Wrap-up** (stash pop + worktree follow-up). `/go` no longer fans out to other branches — cross-branch sync is `/forward`, invoked explicitly afterward. Handle per the Step-0 path:
- **Clean opt 1 / Clean opt 2 / Dirty opt 1 / Dirty opt 2** → no leftover state; print "`/go` complete; currently on `<branch>`; commit landed. For sync to other branches, use `/forward`", **no questioning**, end.
- **Dirty opt 4 (stash)** → on source branch `<X>`, auto `git stash pop`. pop failure (conflict / stash lost) → stop and report; on success print `stash popped and restored`, **no questioning**, end.
- **Clean opt 3 / Dirty opt 3 (worktree)** → **<ask tool>** once: "`/go` complete; this commit landed on `<branch>`. How to handle worktree `../<path>`?"
  1. **Keep worktree (recommended — convenient for continued work)** — leave it; print the worktree path for next time.
  2. **Clean up immediately (`git worktree remove`)** — run `git worktree remove ../<path>` from the source repo root; the commit landed on the branch ref, so removing the directory loses nothing. Failure due to dirty files → stop and report (do not auto-add `--force`).

Print a final state line: `/go` complete; current HEAD = `<branch>`; worktree handling (kept / cleaned). **Does not switch back to any "main branch"** — `/go` respects the Step-0 work location, leaving "which branch I am on" to the user.
