---
name: todo-check
description: Render the docs/todo_list.md Index verbatim (trusts the index; no re-parse). Read-only. Triggers: todo-check / what is next / what's on the todo list / what should I do now.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (logs / docs / commit messages / code comments / files written) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / status lines / strategy declarations / findings rendered in chat) uses `conversation_language`. Code identifiers, file paths, field names, frontmatter keys, and structural prefixes (`Step N:`, `LOG:`, etc.) stay English regardless. When `content_language` ≠ `conversation_language`, prose cells rendered into chat are translated on the fly into `conversation_language`; this is **display-only** — never write the translation back to disk.

# /todo-check — todo_list index display

Read the `## Index (auto-generated; do not hand-edit)` section at the top of `docs/todo_list.md` and render it verbatim to the user, ending with "which entry do you want to see?". **Read-only** — do not parse the body, re-bucket, generate recommendations, change todo_list, change code, or commit. `$ARGUMENTS` is an optional ID keyword filter (e.g. `schema` shows only entries whose ID contains schema); without it, show everything.

The index section is a deterministic cache, refreshed in sync by whoever maintains `docs/todo_list.md` whenever entries change (rules live in the "Index maintenance" section at the top of todo_list.md). `/todo-check` trusts the index and does not re-parse.

## Steps

### 1. Read the index

`Read` `docs/todo_list.md` **with `limit=100` required** — the index section is at the top of the file, and reading the whole ~700-line file slows the response significantly and wastes context. From what is read, extract the `## Index (auto-generated; do not hand-edit)` section — everything from that heading up to the next H2 heading (`## File guide`).

File missing → print "⚠️ docs/todo_list.md missing" and stop.
Index section missing (heading not found) → print "⚠️ docs/todo_list.md top is missing the index section; first backfill per the «Index maintenance» section of todo_list.md before calling /todo-check" and stop.
After 100 lines `## File guide` is still not seen (meaning the index section has grown past 100 lines and got truncated) → re-`Read` `docs/todo_list.md` **without `limit`** to get the full text, then extract the section from the full text; do not stop.
Index section is present but all three subtables are tagged "_(none)_" → still render normally, simply showing "no tasks yet".

### 2. Filter (optional)

If `$ARGUMENTS` is provided: in all three subtables keep rows whose ID contains the keyword (case-insensitive); drop others. If a section becomes empty after filtering, keep its heading but write "_(no matching entries)_".

No `$ARGUMENTS` → show everything.

### 3. Render

Print the index section to the user. Preserve markdown table structure (column count, separators, row order); do not reorder, re-judge, or append recommendations.

Per-cell render rules (the top-of-file Language directive routes the buckets; these spell out which cells are prose vs structural for this index table):

- When `content_language` = `conversation_language` → print verbatim.
- When they differ → translate natural-language cells (Title / Brief / Status text / Open decisions / Blocked by / Scope / Ready and similar prose cells) into `conversation_language` on the fly (display-only, per the top directive).
- Stay verbatim regardless of language: task IDs (`T-XXX`), file paths, dates / timestamps, numeric counts (`Importance`, the `(N)` count after each bucket heading), bucket headings (`### 🟢 In Progress (N)` / `### 🟡 Next (N)` / `### ⚪ Discussing (N)` — emoji + English label is a structural prefix), table column headers (`ID` / `Title` / `Brief` / `Updated` / etc. — field names), and inline `` `code` `` spans.
- The summary row (`**Total**: N — 🟢 In Progress 0 ｜ 🟡 Next 0 ｜ ⚪ Discussing 1`): translate only the word `Total` if a natural rendering exists in `conversation_language`; bucket labels + numbers stay as-is.

**Skip the blockquote that immediately follows the `## Index ...` heading** (consecutive lines starting with `>` — that is meta guidance for the todo_list maintainer and is noise to `/todo-check` users). Subtables / summary rows after the blockquote render normally.

If filtered by `$ARGUMENTS`, append a `(filtered by keyword "<keyword>")` line at the end of the summary row — render the wrapper text in `conversation_language`; the `<keyword>` value itself stays as the user typed it.

### 4. Ask + stop

Print one final line asking which entry the user wants to see. Render this line in `conversation_language` per `ai_context/skills_config.md §Language` (a user-facing prompt). The English baseline is:

```
Which entry do you want to see? Tell me the ID (e.g. `T-XXX`), or say something else.
```

Translate the prose to `conversation_language` when it differs from English; the `T-XXX` placeholder and the inline `` `code` `` formatting stay verbatim.

After printing, **stop** — do not enter `/go`, do not change code, do not change todo_list, do not commit; wait for the user's response.

## Constraints

- **Read-only**: no file changes, no commit, no push
- **Trust the index section**: do not parse the body, re-bucket, or append recommendations; index rules have a single source of truth in the "Index maintenance" section of `docs/todo_list.md`
