---
name: update-docs
description: Land conversation narrative into ai_context/ + docs/ files (semantic match → file + section; direct write + opt-in commit). Triggers: /update-docs / update docs / record discussion in ai_context / land discussion into docs.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (patch content written into `ai_context/` + `docs/` files, marker-line removals, the commit message when the opt-in commit runs) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / candidate file list rendered in chat / final changed-files summary line) uses `conversation_language`. Code identifiers, file paths, field names, frontmatter keys, section headings (`## §6`, `### [T-XXX]`), and structural prefixes (`Step N:`, `PATCH:`, etc.) stay English regardless.

# /update-docs — Land conversation narrative into `ai_context/` + `docs/`

Take what the user just discussed in the session and land it as patches
to the corresponding `ai_context/` + `docs/` files. Lightweight sibling
of `/go` for **doc-only narrative authoring**: no PRE/POST log, no
multi-agent review, no fan-out; after the write it **offers an opt-in
commit** (via `<ask tool>`) of just the files it touched, without
invoking `/commit`. Sibling of `/todo-add` for **prose content**
instead of single todo entries.

## Progress reporting

> **Language**: progress-tool entries (`content` field) are user-facing — write them in `conversation_language` per `ai_context/skills_config.md §Language`. The `Step N:` prefix stays English (structural label); subtitle text after the colon translates to `conversation_language`.

The flow below is split into `## Step 0:` ~ `## Step 3:`.

**Before entering Step 0**: call **<progress tool>** to pre-register all of Step 0 ~ Step 3 (one entry per step, `content` = `Step N: <sub-section title>`, `status` = `pending` for all). This is a hard requirement — **do not proceed without calling <progress tool>**.

Each time you enter a step: call **<progress tool>** to flip the current step to `in_progress` (mark the previous step `completed` in the same call), then do the real work. **Do not skip the call across step boundaries**. Progress is rendered directly by the <progress tool> UI — **do not print `[/update-docs] Step N: ...` style progress lines in the conversation**.

Skipping a step: call **<progress tool>** to mark the entry directly `completed`, and print one line `Step N skipped (reason: …)` in the conversation — "reason" is information the UI lacks, keep that line; do not silently skip.

Final step completion: call **<progress tool>** to mark the last entry `completed`.

**<progress tool> resolution**: Claude → `TodoWrite` (rendered as "Update Todos"); Codex → `update_plan`; other runtimes (no structured progress tool, e.g. Copilot agent mode) → maintain a markdown checkbox list in the response text as step state, rewriting the whole block on every state change. Semantic alignment: pre-register + flip state + mark complete.

**<ask tool> resolution**: Claude → `AskUserQuestion` (max 4 questions per call, batch beyond); other runtimes (no structured ask tool, e.g. Codex / Copilot agent mode) → enumerate questions + options per question in the response text and let the user answer in one pass (still max 4 per batch, batch beyond).

## Step 0: Load skills_config

`Read` `ai_context/skills_config.md`.

- File missing / any section header missing → fail loudly: print the missing items + prompt to complete per plugin template, stop
- Section content `(none)` or empty → skip the related steps for that section (treat as N/A in this project)
- Section lists concrete paths but the path does not exist → fail loudly: report the section drifting to a nonexistent path, stop and wait for the user to fix

This skill uses:
`## Language` (drives `content_language` for patch content + `conversation_language` for user-facing surface; the L1 directive at top of this file already routes both buckets).

## Step 1: Identify candidate files + compose patches

> **Language**: disk-bound — patch content composed here will land in `ai_context/` + `docs/` files at Step 3 and is therefore disk-bound from the moment of composition. Write the patch text (paragraph additions, marker-line removals, list entries, table rows, decisions log entries) in `content_language` per `ai_context/skills_config.md §Language`. Code identifiers, file paths, field names, section headings (`## Goal`, `### [T-XXX]`, `**Updated**`), and the PROGRESSIVE marker token `_(none yet — delete this marker once content is added)_` stay English regardless.

> **Compactness Requirements**: patches landing in `ai_context/` follow the universal contract —
> - Shorter is better than longer. Each entry is a summary, not a detail dump.
> - Compactness must not sacrifice accuracy or completeness — never drop important information just to fit the length target.
> - Aim for ≤ 5 lines per entry, and push longer detail to the linked source (`docs/<topic>.md`, schemas, script docstrings).
> - Do not compress or touch content unrelated to the current edit.

Scan the recent conversation turns and identify "what the user just decided / discussed that should land as narrative." For each candidate point:

1. **Semantic match against `ai_context/` + `docs/` files.** Map the topic to its natural home:
   - project goal / scope / stakeholders → `ai_context/project_background.md` + matching `docs/` section if present
   - current state snapshot → `ai_context/handoff.md §Current State` (2-col table)
   - architecture decisions → `ai_context/architecture.md` + `docs/architecture/<topic>.md`
   - durable engineering decisions ("why" rationale) → `ai_context/decisions.md` + `docs/decisions.md` (lockstep pair — index line + full archive entry, same `#N`). Entry criterion: only genuinely contested decisions a future reader might re-propose. **Lifecycle check before appending**: overturns an existing `#N` → supersede in place in BOTH files (number stays; a tried-and-reverted approach keeps a half-line `(tried X, reverted, see log)` trace in the archive entry); topic killed with in-conversation evidence → prune from both files (gap stays); otherwise append — do **not** renumber
   - user-visible requirements → `docs/requirements.md` (long-form) + `ai_context/requirements.md` (summary line) — lockstep pair
   - planned-but-unfinished tasks → **redirect to `/todo-add`**, this skill does not touch `docs/todo_list.md`
   - user preferences / taste rules → `ai_context/handoff.md §What The User Cares About`
   - roadmap / next directions → `ai_context/handoff.md §Next Steps` (2-col table)

2. **Cross-file alignment surfacing.** Consult `ai_context/conventions.md §Cross-File Alignment` and surface any lockstep pairs touched by the candidate (e.g. `docs/requirements.md` + `ai_context/requirements.md`; `docs/architecture/<topic>.md` + `ai_context/architecture.md`). Patch each member of the pair, not just one side. When the alignment table absent, judge by intuition — the canonical pairs above are the ones that recur.

3. **PROGRESSIVE marker awareness.** When the target section currently carries the line `_(none yet — delete this marker once content is added)_`, the patch removes that marker line in the same pass as the first content lands. Do not leave both marker + new content side-by-side. (Source of truth for the marker contract: `ai_context/decisions.md` §Skill Implementation #15.)

4. **Out-of-scope rejection.** Patches that touch any of the following are **rejected** — print a one-line redirect and skip the candidate:
   - `docs/todo_list.md` / `docs/todo_list_archived.md` → use `/todo-add`
   - code (`commands/` / `skills/` / `hooks/` / `scripts/` / `templates/` / `.claude-plugin/`) → use `/go`
   - schema / config (`ai_context/skills_config.md` headers/fields, `.gitignore`, `plugin.json`) → use `/go` (or `/holo:update --fix` for drift)
   - `logs/change_logs/` / `logs/review_reports/` → owned by `/go` and `/full-review` respectively
   - any path outside `ai_context/` + `docs/`

5. **Compose patches.** For each accepted candidate, draft the exact patch text in `content_language`. Use the same field-label / heading conventions as the surrounding file. For `decisions.md` append: number = previous max + 1 (do not renumber existing entries); the patch is a pair — 1–2-line index entry in `ai_context/decisions.md` (statement + `→ docs/decisions.md #N`) + full entry in `docs/decisions.md` (same number, same theme section); a supersede/prune patch likewise edits both files. For `requirements.md` lockstep: long-form + summary line in matching numbering. For `handoff.md` bulleted sections: append bullets in alphabetical / logical order. For appended content: 1 blank line before the new block; for marker-line removal: remove the single marker line plus its trailing blank line if present.

If `$ARGUMENTS` is provided, treat it as a focus filter (file path / section name / topic keyword) and narrow candidates to those matching the filter; do not broaden beyond the user's stated focus.

If after the scan + filter the **accepted** candidate set is empty (no in-scope topics found, or all candidates were rejected per §4), print one line `nothing to land — recent conversation has no in-scope narrative for ai_context/ + docs/; if you expected a patch, name the topic explicitly and re-invoke` and stop. Do not enter Step 2.

Print to the conversation a numbered candidate list — one line per patch — in this shape:

```
1. file: ai_context/handoff.md → section: ## Mental Model → add: <one-line summary>
2. file: ai_context/decisions.md + docs/decisions.md (lockstep) → append: §<bucket> #<N> <one-line summary>
3. file: docs/requirements.md + ai_context/requirements.md (lockstep) → §6.2 + bullet 6 → add: <one-line summary>
4. ... (rejected) file: docs/todo_list.md → redirect to /todo-add
```

This numbered list is the only pre-write surface — patches are applied directly in Step 2, with no separate preview or confirmation.

## Step 2: Apply patches

> **Language**: user-facing — render the changed-files summary line ("✓ landed N patches across M files: …") in `conversation_language` per `ai_context/skills_config.md §Language`. Structural prefixes (`✓`, file paths) stay English; only surrounding prose translates.

Apply the composed patches directly (no preview, no confirmation gate):

a. **Apply patches via `Edit` (or `Write` only when creating a brand-new file under `ai_context/` or `docs/`).** One `Edit` per patch — do not batch unrelated edits into a single `replace_all`.

PROGRESSIVE marker removal — two explicit branches (do not collapse them), picked by the bytes after the marker:

- **Branch A — marker + following blank line → consume both lines**: `old_string` covers the marker line **plus the one blank line** after it; `new_string` is the new content block ending with `\n\n` so spacing to the next section is preserved.
- **Branch B — marker-only (no blank before next content) → consume one line**: `old_string` covers **only the marker line**; `new_string` ends with `\n` so the next section still starts on its own line.

Inline example (marker = `_(none yet — delete this marker once content is added)_`): Branch A `old_string` = `<marker>\n\n` → `## ThisSection\n\n<new content>\n\n## NextSection`; Branch B `old_string` = `<marker>\n` → `## ThisSection\n<new content>\n## NextSection`.

Pick the branch by **first inspecting the literal bytes around the marker in the target file** (via `Read` or by reusing what was read in Step 1); do not guess. Wrong branch → either two consecutive blank lines (Branch A applied to a Branch-B case) or two headings glued together with no separator (Branch B applied to a Branch-A case).

b. **Verify by re-reading the changed sections** if a patch touched > 1 surrounding line (sanity check that the surrounding context still parses as intended). Do not re-read entire files — only the affected section.

c. **Print the summary line**: `✓ landed N patches across M files: <comma-separated file list>`.

Do not enter `/go`, do not invoke any other skill in Step 2; proceed to Step 3 (commit offer).

## Step 3: Commit offer (opt-in)

> **Language**: user-facing — render the `<ask tool>` commit prompt + option labels and the final state line in `conversation_language` per `ai_context/skills_config.md §Language`. The commit message itself is disk-bound — author it in `content_language`. Structural tokens (`✓`, `git`, file paths, short SHA) stay English regardless.

After the patches land, ask via **<ask tool>** whether to commit:

Question: `Commit the N changed file(s) now?`

1. **Commit now** — stage and commit just the files this run wrote / created
2. **Don't commit** — leave them in the working tree

**On "Commit now"**:

- Stage only the exact paths patched / created in Step 2 (the accepted patch set): `git add <file1> <file2> …` — scope to those paths; do **not** `git add -A` / do not sweep unrelated working-tree changes.
- Commit with a concise one-line message in `content_language`, conventional-commit style, e.g. `docs: land <topic> into ai_context/ + docs/`.
- Plain `git commit` only: no `--amend`, no `--no-verify`, no `--force`, **no push**, and **do not invoke `/commit`** (this is a raw `git add` + `git commit`, not a delegation).
- Print one line: `✓ committed <short-sha> <message>`.

**On "Don't commit"**: print `Left uncommitted — run /commit to persist.` and stop.

Do not enter `/go`, do not push.

## Constraints

- **Opt-in commit only / no push** — after the write, offer (via `<ask tool>`) a plain commit of just the files this run touched; never `git add -A`, never `--amend` / `--no-verify` / `--force`, never push, never invoke `/commit`. On decline, persistence is delegated to `/commit`
- **No code / no schema / no config / no logs / no todo_list** — patches outside `ai_context/` + `docs/` are rejected with a one-line redirect to the right skill (`/go` for code/schema/config, `/todo-add` for todo entries)
- **No fan-out / no multi-agent review** — single-pass author-and-write; `/full-review` is the audit path
- **No PRE / POST log** — `logs/change_logs/` is `/go`-only; `/update-docs` writes are attributable via the git diff alone
- **PROGRESSIVE marker contract is load-bearing** — when first content lands into a `_(none yet — delete this marker once content is added)_` section, the marker line is removed in the same pass; never leave marker + new content side-by-side
- **Lockstep pairs are batched** — when `docs/requirements.md` + `ai_context/requirements.md` (or any pair from `ai_context/conventions.md §Cross-File Alignment`) are both touched, both members are patched in this run; the user is not asked to choose between them
- **No silent file creation outside `ai_context/` + `docs/`** — `Write` is used only to create a brand-new file under those two roots (rare — typically a new `docs/architecture/<topic>.md`); even then the file must be one of the documented kinds in `ai_context/conventions.md`, not an arbitrary scratch file
