---
name: recent-activity
description: Reverse-chronological timeline of the latest N project actions (git commits + change logs + todo updates). Triggers: what's been happening lately / recent-activity / recent changes / show the timeline / latest N actions.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (logs / docs / commit messages / code comments / files written) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / status lines / strategy declarations / findings rendered in chat) uses `conversation_language`. Code identifiers, file paths, field names, frontmatter keys, and structural prefixes (`Step N:`, `LOG:`, etc.) stay English regardless.

# /recent-activity — Reverse-chronological timeline of latest N project actions

Merge the most recent N "actions" in the project into a block view sorted in reverse chronological order; each entry not only lists the timestamp but expands the body (commit body / change_log head) so you can directly see "what was done / what was changed / what was deleted / what was rolled back". Three sources, all anchored in `ai_context/skills_config.md ## Activity sources`:

1. **git commits** (current branch, no merges; with commit body)
2. **change logs** (markdown files under the path declared at `## Activity sources.Change logs.Path` whose filename matches `## Activity sources.Change logs.Filename time pattern`; with file body head)
3. **todo entries** (the per-entry field named at `## Activity sources.TODO list.Per-entry updated-time field` of each entry in the file at `## Activity sources.TODO list.Path`; only the entry title is expanded)

## Step 0: Load skills config

`Read` `ai_context/skills_config.md`, taking:

- `## Timezone` → timezone command template (used to parse filename timestamps and to render with timezone)
- `## Activity sources` → change_logs path + filename time pattern + todo_list path + updated-field name

If any section is missing or any path is missing → fail loudly: print missing items + prompt to fill per plugin template, stop.

## Step 1: Parse $ARGUMENTS

Tokenize (whitespace split, order-independent):

| Token shape | Meaning |
|---|---|
| Plain integer / `N=<int>` | Take the most recent N entries (default 10) |
| `commits` / `logs` / `todo` | Source filter (stackable, multiple = OR) |

Defaults: N = 10, source = scan all.

Illegal token → print "unrecognized token `<val>`, allowed: <integer / N=<int> / commits / logs / todo>" and stop.

**N applies to the merged total count** (not per-source N); when one source has many more entries than the others, do not enforce a quota — the reverse ordering naturally takes the top N.

## Step 2: Collect git commits (with body; if source includes commits)

```
git log -n <3*N> --no-merges --pretty=format:'==REC==%n%cI%n%h%n%s%n--BODY--%n%b' HEAD
```

Split on `==REC==`; parse each record as:

- Line 1: `%cI` (ISO timestamp with timezone)
- Line 2: `%h` (short sha)
- Line 3: `%s` (subject)
- Line 4: `--BODY--` separator
- Line 5 to the next `==REC==`: `%b` (commit body, may be multiline; may be empty)

**Body rendering rules**:
- Empty body (most single-line commits) → show `(no body)`
- Non-empty body → preserve **the first 25 lines** verbatim; if longer, append `(… body truncated, run git show <sha> for full content)`
- Do **not** escape backticks / pipes / markdown markers in the body — embed directly as a markdown block (output format is block view not table, no cell boundary conflict)

## Step 3: Collect change_logs (if source includes logs)

Per skills_config.md `## Activity sources` change logs path and filename time pattern:

```
ls -1 <change_logs_path>/*.md | sort -r | head -n <3*N>
```

Filenames in reverse order, **build an index only**: parse the timestamp from each filename (e.g.
`2026-04-30_134108_skills_polish.md` → `2026-04-30T13:41:08`, joined with timezone from skills_config
`## Timezone`), record `(timestamp, filename, slug)`. slug = filename
minus the time prefix and the `.md` suffix, with underscores swapped for spaces. This pass opens no file — building the index first avoids reads on logs that Step 5 trims away after merging.

**Deferred body read** — after Step 5's merge+trim, for only the `log` entries that survive, `Read` each corresponding file (git body already grabbed in Step 2, todo not expanded):
- `Read <change_logs_path>/<filename>` with `limit: 40` (the first 40 lines cover the head section "## Background / ## Change list")
- When rendering, preserve **the first 25 lines** (including the H1/H2 heading and head section content); if over 25 lines, append `(… log truncated, see <filename>)`
- File missing or read failure → that entry body shows `(log read failure: <error>)`, do not stop

## Step 4: Collect todo_list updates (if source includes todo)

`Read` `<todo_list_path>` (per skills_config.md `## Activity sources.TODO list.Path`) for the full text (todo_list is typically ~700 lines; this skill must scan the whole body, no `limit`).

Split by `### [T-XXX]` blocks (note the brackets in the heading need escaping); inside each block grep one line whose label is exactly the value of `## Activity sources.TODO list.Per-entry updated-time field` (typically `**Updated**`):

```
<configured field label>: YYYY-MM-DD HH:MM <TZ>
```

**Skip entries missing this field** (legacy format residue / entries never touched by `/todo-add`; do not count as "recent action").

Sort by timestamp DESC and take the top `3*N`, recording `(timestamp, T-XXX, title first line)`.
**Do not expand entry body** (motivation / change list / status field are not read; for detail let the user open `docs/todo_list.md#T-XXX`).

## Step 5: Merge + reverse-sort + take top N

Merge results from Step 2 / 3 / 4, sort by Timestamp **DESC**, trim to N entries. (Surviving `log` entries then get their body read per Step 3's deferred-read note.)

If the pre-merge total > N: at the end of the output print one line `(… more earlier actions not listed; use N=<larger> to see more)`.

## Step 6: Output (block view)

Fixed format:

```
## /recent-activity — latest N

- N: <N>
- Sources: <commits / logs / todo, the ones actually enabled>
- Actual count: <merged total> (git=<N1>, log=<N2>, todo=<N3>)

---

### 1. <Timestamp> · git · `<sha>`

**<commit subject>**

<commit body — up to 25 lines; empty body shows "(no body)"; over-length appends truncation line>

---

### 2. <Timestamp> · log · [<filename>](<change_logs_path>/<filename>)

**<filename slug>**

<first 25 lines of change_log head — preserve markdown verbatim>

---

### 3. <Timestamp> · todo · [T-XXX](docs/todo_list.md#T-XXX)

**<title first line (truncated ≤ 60 chars)>**

(todo entries expand title only; for detail open docs/todo_list.md#T-XXX)

---
```

Ordinal numbers 1..N reflect post-merge reverse position; timestamps always use ISO 8601 with timezone.

**Do not append recommended actions / commentary at the end** — this skill lists facts only, the user decides what to do with them.

## Constraints

- **Read-only**: no `git checkout` / `merge` / `push` / `fetch` / `commit`, no mutation of todo_list / change_logs, no external API calls
- **Current-branch view** (`HEAD`), no cross-branch aggregation; merge commits ignored (`--no-merges`); each source oversampled to `3*N` then trimmed to N after merging
- No time-window argument (`24h` / `since=...` unsupported); for time filtering use `/branch-inventory` to view commit times, or run `git log --since` directly
