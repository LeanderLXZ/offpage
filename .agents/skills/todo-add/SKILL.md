---
name: todo-add
description: Add a just-decided item to docs/todo_list.md (semantic match → update or create + Index refresh; direct write + opt-in commit). Triggers: add to todo / register todo / todo-add / put it in next / put it in discussing / update todo.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (the todo entry inserted into `docs/todo_list.md`, the `## Index` refresh, the `**Updated**` field, the commit message when the opt-in commit runs) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / wrap-up status line) uses `conversation_language`. Code identifiers, file paths, field names, frontmatter keys, and structural prefixes (`Step N:`, `T-XXX`, `### [T-XXX]`, segment headings like `## Next`) stay English regardless.

# /todo-add — Add session discussion result to todo_list

Add an item just discussed / decided in the current session to `docs/todo_list.md`: **if a
corresponding entry exists, update it** (switch segment if needed); **if it does not exist, create
a new one**. The target segment can be specified via `$ARGUMENTS`. The entry is written directly
(no preview / confirmation gate); after the write the skill **offers an opt-in commit** (via
`<ask tool>`) of just `docs/todo_list.md` — it never invokes `/commit` and never pushes.

## Progress reporting

> **Language**: progress-tool entries (`content` field) are user-facing — write them in `conversation_language` per `ai_context/skills_config.md §Language`. The `Step N:` prefix stays English (structural label); subtitle text after the colon translates to `conversation_language`.

The flow below is split into `## Step 1:` ~ `## Step 7:`.

**Before entering Step 1**: call **<progress tool>** to pre-register all of Step 1 ~ Step 7 (one entry per step, `content` = `Step N: <sub-section title>`, `status` = `pending` for all). This is a hard requirement — **do not proceed without calling <progress tool>**.

Each time you enter a step: call **<progress tool>** to flip the current step to `in_progress` (mark the previous step `completed` in the same call), then do the real work. **Do not skip the call across step boundaries**. Progress is rendered directly by the <progress tool> UI — **do not print `[/todo-add] Step N: ...` style progress lines in the conversation**.

Skipping a step: call **<progress tool>** to mark the entry directly `completed`, and print one line `Step N skipped (reason: …)` in the conversation — "reason" is information the UI lacks, keep that line; do not silently skip.

Final step completion: call **<progress tool>** to mark the last entry `completed`.

**<progress tool> resolution**: Claude → `TodoWrite` (rendered as "Update Todos"); Codex → `update_plan`; other runtimes (no structured progress tool, e.g. Copilot agent mode) → maintain a markdown checkbox list in the response text as step state, rewriting the whole block on every state change. Semantic alignment: pre-register + flip state + mark complete.

**<ask tool> resolution**: Claude → `AskUserQuestion` (max 4 questions per call, batch beyond); other runtimes (no structured ask tool, e.g. Codex / Copilot agent mode) → enumerate questions + options per question in the response text and let the user answer in one pass (still max 4 per batch, batch beyond).

## Step 1: Parse $ARGUMENTS (target segment)

| Value | Target segment |
|---|---|
| Not passed / `next` / `next-step` | `## Next` |
| `discuss` / `discussing` | `## Discussing (Undecided)` |
| `executing` / `in-progress` | `## In Progress` (single slot, see Step 5 for limit) |

Illegal value → print "segment `<val>` not recognized, allowed: Next / Discussing / In Progress" and stop.

When `$ARGUMENTS` is not passed: UPDATE mode defaults to the existing segment; CREATE mode defaults to
"Next".

## Step 2: Lock the item to register

From the last few turns of the current session, grab the "item" to register — typically the specific
problem + conclusion + trigger that the user just decided / discussed.

When information is insufficient (missing motivation / status / trigger chain / change-direction) **actively
ask the user to fill the gap** — "Which discussion is being registered? Add a sentence or two of key
background / trigger / desired outcome." Do not guess, do not stitch on the user's behalf.

## Step 3: Decide UPDATE vs CREATE

Grab the full set of existing entries from the two paths declared at `ai_context/skills_config.md ## Activity sources.TODO list.Path` (live) and `## Activity sources.Archived TODO list.Path` (archive):
`grep -hoE 'T-[A-Z0-9-]+' <todo_list_path> <archived_todo_list_path> | sort -u`
to get the ID set; and read the titles + context of existing entries, do a **semantic match** to
judge whether the item to register corresponds to an existing entry (by content intent, not just
literal ID).

Decision:

- **UPDATE mode**: a matching entry found → record the existing `T-XXX` + existing segment
  + existing entry content snapshot (for the Step 4 merge). If more than one suspected match, ask via
  **<ask tool>** — one question with each suspected match as one option (label: `Update T-AAA: <title>` / `Update T-BBB: <title>`, max 3 matches) plus a final `Create new entry instead` option.
  Do not decide for the user.
- **CREATE mode**: no match found → distill a new `T-XXX` slug from content intent (short English
  code, all uppercase + hyphens), non-colliding with the existing ID set; rename on collision.

Segment decision in UPDATE mode:

- `$ARGUMENTS` explicitly passes a segment → obey (even on cross-segment move)
- `$ARGUMENTS` not passed → default to the existing segment; but if this round's discussion
  **strongly implies** a segment change (typical: Discussing entry just decided → should move to Next / Next entry
  has `/go` started → should move to In Progress), apply the implied move directly (subject to the
  **In Progress** single-slot guard in Step 5) and report it in the Step 6 wrap-up.

## Step 4: Compose entry draft / merged entry

> **Language**: disk-bound — the entry draft / merged entry being composed here will land in `docs/todo_list.md` at Step 5 and is therefore disk-bound from the moment of composition. Write the draft text (title, **Context**, **Done criteria**, **Dependencies**, **Updated**, segment-specific fields) in `content_language` per `ai_context/skills_config.md §Language`. Code identifiers, file paths, field names, segment headings (`### [T-XXX]`, `**Updated**`) stay English regardless.

**CREATE mode**: compose the full entry per the target segment's field requirements. Shared by all segments:

- T-XXX ID + short title (in this project's `content_language`)
- **Context**: motivation + status + trigger chain
- **Requirements** (optional; positioned between **Context** and **Change manifest**): what the user wants done / what effect to achieve. Plain prose, no special format rules. Include when this session converged user-facing requirements worth preserving.
- **Solution details** (optional; positioned between **Requirements** and **Change manifest**): the final converged plan — what the solution is, what parts compose it. **Only the final converged version** — do NOT include rejected alternatives or debate history. Plain prose, no special format rules. Include when this session converged a concrete plan worth preserving.
- **Done criteria**
- **Dependencies**
- **Updated-time field** (label per `ai_context/skills_config.md ## Activity sources.TODO list.Per-entry updated-time field`, typically `**Updated**`): `YYYY-MM-DD HH:MM` + timezone abbreviation (per skills_config.md `## Timezone`). **Always set to the current moment** — on CREATE, and on every UPDATE (including same-segment edits); if an existing entry lacks the field (legacy format), backfill it in the same pass. This is the single statement of the rule — the UPDATE-mode note below does not restate it.

Per-segment differences:

- **Next**: must include **change list** (file paths / line numbers / change points), single source, no gaps
- **Discussing**: must include **open decisions** (numbered list, 1–2 sentences each); change list may be deferred
- **In Progress**: requires **start time** (YYYY-MM-DD HH:MM timezone abbreviation — per
  skills_config.md `## Timezone`) + **current status** (in progress / awaiting user decision / paused)

Add as appropriate: **estimate** / **why not landed** / **not doing for now**.

Follow the format of existing entries in `docs/todo_list.md` ("### \[T-XXX\] short title" header,
field titles as `**field name**`).

**UPDATE mode**: take the existing entry as baseline and merge the new info from this round in.
Unchanged fields **stay verbatim**, do not restate; changed fields are merged in. On
segment change, fill in any missing fields per **target segment** field requirements (e.g. Discussing → Next must add **change list**). The **Updated-time field** is refreshed per the rule stated once in CREATE mode above.

## Step 5: Write to todo_list.md

Write the composed result directly (no preview, no confirmation gate):

**CREATE mode**:

a. Locate the target segment (`## In Progress` / `## Next` / `## Discussing (Undecided)`), append
   the entry under `### [T-XXX] short title` heading to the **end** of that segment (within-segment
   priority is user-driven; new entries default to the tail unless the user says "insert at the front").
   Entries are separated by `---` (consistent with existing convention)

b. **In Progress** segment single slot: before writing, grep the segment's existing `### \[T-` count;
   if non-zero, **refuse to write** and prompt "In Progress segment is occupied, finish committing the
   current one or move it back to Next before starting a new task"

**UPDATE mode**:

a. **Same-segment update**: locate the `### [T-XXX]` block (including all its fields, up to the next
   `### [T-` or segment end), replace the whole block with the new version. Other segments untouched.

b. **Cross-segment move**: delete the whole `### [T-XXX]` block from the original segment (along with
   any redundant surrounding `---` separator), append to the end of the target segment per CREATE
   mode a. The **In Progress** single-slot limit applies equally — refuse the move if the target
   segment is non-empty, with the same prompt as above.

**Unified refresh**: segments that changed (CREATE target segment / UPDATE same segment or source+target segments)
+ the top-of-file `## Index (auto-generated; do not hand-edit)` segment — refresh the relevant
sub-table rows + summary row per the column rules and field-inference rules defined in
`docs/todo_list.md` "## File guide → Index maintenance" section; this skill **does not restate the rules**,
that section is the single source of truth.

## Step 6: Wrap-up report

Print (pick one based on this round's mode):

- **CREATE**: ✓ registered `T-XXX` into "<segment>"
- **UPDATE same-segment**: ✓ updated `T-XXX` ("<segment>")
- **UPDATE cross-segment**: ✓ updated `T-XXX` and moved (<original segment> → <new segment>)

Followed by:

- Index refresh: changed sub-table row count X → Y, summary N → N' (CREATE: N+1; UPDATE same-segment: unchanged; UPDATE cross-segment: each sub-table ±1)

Then proceed to Step 7 (commit offer).

## Step 7: Commit offer (opt-in)

> **Language**: user-facing — render the `<ask tool>` commit prompt + option labels and the final state line in `conversation_language` per `ai_context/skills_config.md §Language`. The commit message itself is disk-bound — author it in `content_language`. Structural tokens (`✓`, `git`, `docs(todo)`, file paths, short SHA) stay English regardless.

After the wrap-up, ask via **<ask tool>** whether to commit:

Question: `Commit docs/todo_list.md now?`

1. **Commit now** — stage and commit just `docs/todo_list.md`
2. **Don't commit** — leave it in the working tree

**On "Commit now"**:

- Stage only the file this skill wrote: `git add docs/todo_list.md` — scope to this one path; do **not** `git add -A` / do not sweep unrelated working-tree changes.
- Commit with a concise one-line message in `content_language`, conventional-commit style scoped to the todo change, e.g. `docs(todo): add T-XXX <title>` (CREATE) / `docs(todo): update T-XXX` (UPDATE same-segment) / `docs(todo): move T-XXX to <segment>` (cross-segment).
- Plain `git commit` only: no `--amend`, no `--no-verify`, no `--force`, **no push**, and **do not invoke `/commit`** (this is a raw `git add` + `git commit`, not a delegation).
- Print one line: `✓ committed <short-sha> <message>`.

**On "Don't commit"**: print `Left uncommitted — run /commit or /go to persist.` and stop.

Do not enter `/go`, do not push.

## Constraints

- **Opt-in commit only / no push** — after the write, offer (via `<ask tool>`) a plain commit of just `docs/todo_list.md`; never `git add -A`, never `--amend` / `--no-verify` / `--force`, never push, never invoke `/commit`. On decline, persistence is delegated to `/commit` or `/go`
- **UPDATE takes priority over CREATE**: if an existing entry can be matched, update; on multiple suspected matches or CREATE
  missing key fields, **actively ask the user**, do not decide for them
- **In Progress single slot**: refuse to write (CREATE) / refuse the move (UPDATE cross-segment) if the segment is non-empty
- **Index rules single source**: see `docs/todo_list.md` "Index maintenance" section
