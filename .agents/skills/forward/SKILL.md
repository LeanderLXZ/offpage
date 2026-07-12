---
name: forward
description: Merge the current branch into one or more sibling branches with per-branch conflict triage. No push / force / rebase. Triggers: forward / sync to develop / push commits to other branches / push to X Y Z.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (logs / docs / commit messages / code comments / files written) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / status lines / strategy declarations / findings rendered in chat) uses `conversation_language`. Code identifiers, file paths, field names, frontmatter keys, and structural prefixes (`Step N:`, `LOG:`, etc.) stay English regardless.

# /forward — Explicit branch sync

`git merge` the latest commit on the current branch (= source branch) into one or more target branches.
**Pure merge, no push / no --force / no --amend / no rebase** — only fast-forward / merge-commit the current branch into each target.

## Progress reporting

The flow below is split into `## Step 0:` ~ `## Step 5:` (the leading `## $ARGUMENTS parsing` section is argument parsing, not a formal step).

**Before entering Step 0**: call **<progress tool>** to pre-register all of Step 0 ~ Step 5 (one entry per step, `content` = `Step N: <sub-section title>`, `status` = `pending` for all; `$ARGUMENTS` parsing is not counted). This is a hard requirement — **do not proceed without calling <progress tool>**.

Each time you enter a step: call **<progress tool>** to flip the current step to `in_progress` (mark the previous step `completed` in the same call), then do the real work. **Do not skip the call across step boundaries**. Progress is rendered directly by the <progress tool> UI — **do not print `[/forward] Step N: ...` style progress lines in the conversation**.

Skipping a step: call **<progress tool>** to mark the entry directly `completed`, and print one line `Step N skipped (reason: …)` in the conversation — "reason" is information the UI lacks, keep that line; do not silently skip.

Final step completion: call **<progress tool>** to mark the last entry `completed`.

**<progress tool> resolution**: Claude → `TodoWrite` (rendered as "Update Todos"); Codex → `update_plan`; other runtimes (no structured progress tool, e.g. Copilot agent mode) → maintain a markdown checkbox list in the response text as step state, rewriting the whole block on every state change. Semantic alignment: pre-register + flip state + mark complete.

**<ask tool> resolution**: Claude → `AskUserQuestion` (max 4 questions per call, batch if more); other runtimes (no structured ask tool, e.g. Codex / Copilot agent mode) → number questions in the response text with options per question and let the user answer all at once (still max 4 per batch, batch if more).

## `$ARGUMENTS` parsing

`$ARGUMENTS` = target branch name list (space-separated), processed by these rules:

1. **`$ARGUMENTS` empty** → targets = all "candidate non-current branches", defined as:
   every local branch listed by `git branch --format='%(refname:short)'`, excluding the current branch
2. **`$ARGUMENTS` non-empty** → tokenize and take each token as a target branch name; all tokens enter the candidate list (do not verify existence / sync state here, leave that to Step 2)

The source branch is always `git branch --show-current` (**the current branch**) — `/forward` does not accept a "source" argument. To change source → user must `git checkout <source>` first, then run `/forward`.

## Step 0: Load skills config

`Read` `ai_context/skills_config.md`.

- File missing / some section title missing → fail loudly: print missing items + prompt to fill per plugin template, stop
- A section's content is `(none)` or empty → skip the related steps for that section (treat as project doesn't have this item)
- A section lists a concrete path but the path doesn't exist → fail loudly: report that the section drifted to a missing path, stop and wait for user to fix

Subsequent steps referring to "skills_config.md `## XX`" cite this config. This skill uses:
`## Background processes` (Step 2 candidate triage: process detection),
`## Protected branch prefixes` (Step 2 candidate triage: protected branch classification),
`## Main branch policy` (Step 2 candidate triage: main branch protection notice).

## Step 1: Pre-check

- `git branch --show-current` to get source branch; detached HEAD → stop and report, ask user to checkout first
- `git status --porcelain` to inspect the working tree:
  - **dirty** (any staged / unstaged / untracked-not-ignored change) → **stop and report**, ask user to `/commit` or `git stash` first; `/forward` does not accept a dirty source
  - clean → enter Step 2
- Source branch commit count = 0 (empty repo / new branch with no commits) → stop and report

## Step 2: Candidate triage (classification)

For each target branch resolved from `$ARGUMENTS`, classify one by one:

| Label | Trigger | Follow-up |
|---|---|---|
| ❌ missing | `git rev-parse --verify <branch>` fails | Skip Step 3 / Step 4 entirely; annotate in final result list |
| 🔒 protected | Branch matches a prefix listed in skills_config.md `## Protected branch prefixes` (`(none)` → this class does not trigger) | Enter Step 4 prompt (default suggestion: skip) |
| ⚙️ has process | Per skills_config.md `## Background processes`, a pgrep pattern matches (`(none)` → this class does not trigger) | Enter Step 4 prompt (default suggestion: skip) |
| 💾 dirty | The branch's corresponding worktree has uncommitted changes (`git -C <worktree> status --porcelain` non-empty; branches with no actual worktree degrade to "never checked out → treated as clean") | Enter Step 4 prompt |
| ✅ already synced | `git merge-base --is-ancestor <source> <branch>` returns 0 (i.e. source is an ancestor of branch) | Skip Step 3 / Step 4 entirely; final result list marks "already synced, skipped" |
| ⚠️ pre-check conflict | Dry-run detects a merge conflict — git ≥ 2.38 prefers `git merge-tree --write-tree --no-messages <source> <branch>` non-zero exit = conflict; older git falls back to `git merge-tree $(git merge-base <source> <branch>) <source> <branch>` and scans output for `<<<<<<<` markers | Enter Step 4 prompt |
| 🟢 mergeable | None of the above triggers | Enter Step 3 batch execution |

Print a small classification table (one line per branch: `<branch> | <label> | <one-sentence note>`) so the user has a complete view before Step 3 / Step 4.

## Step 3: Batch unobstructed merge

For every target branch marked 🟢, **merge one by one without asking**:

- If the branch = current HEAD (impossible — already excluded in Step 2; keep this as a defensive check) → skip
- Otherwise `git checkout <branch> && git merge <source>`
  - fast-forward succeeds → print one line `✅ <branch>: ff-merge OK`
  - forms a merge commit → reuse git's default commit message (`Merge branch '<source>'`), print one line `✅ <branch>: merge commit OK`
  - **unexpected** conflict at runtime (inconsistent with Step 2 dry-run; possibly from external state change) → `git merge --abort` to return to a clean state, mark that branch ⚠️ for later prompt; do not stop, keep going
- After all are processed, `git checkout <source>` to return to the source branch

## Step 4: Prompt per obstructed branch (only ⚠️ classes prompt)

Handle per classification label:

- **❌ missing / ✅ already synced** → **do not prompt**, fold directly into the final result list
- **🔒 protected / ⚙️ has process / 💾 dirty / ⚠️ pre-check conflict / Step 3 unexpected conflict** → ask one by one via **<ask tool>**, 3 options each:
  1. **Skip this branch (recommended)** — do not touch this branch, record "skipped: <reason>" in the final result
  2. **Merge anyway** — execution mechanism per class:
     - **🔒 protected / ⚙️ has process / ⚠️ pre-check conflict / Step 3 unexpected conflict** → `git checkout <branch> && git merge <source>`; on conflict `git merge --abort` to revert and mark "⚠️ conflict, manual fix needed"; after merge return via `git checkout <source>`
     - **💾 dirty** (target = another worktree's dirty working tree, target branch already checked out there, source-side `git checkout <branch>` will be rejected by git) → **do not** checkout on the source side; instead `git -C <worktree-path> merge <source>` to merge directly inside the target worktree; the target's dirty changes stay intact (git itself will reject the merge because it involves uncommitted changes, in which case return to the prompt and ask the user to commit / stash in the target worktree first); on conflict `git -C <worktree-path> merge --abort` to revert and mark "⚠️ conflict, manual fix needed"
  3. **Stop, I'll handle it manually** — terminate `/forward`, print current done / pending status, **end the whole skill**

After asking through all ⚠️ classes, regardless of the user's choices, enter Step 5.

## Step 5: Final result list

Print a result table (**always print, do not omit**):

```
Source branch: <source>

Target branch | Status
--------------|-------
<b1>          | ✅ merged (ff)
<b2>          | ✅ merged (merge commit)
<b3>          | ✅ already synced, skipped
<b4>          | ⏭ user chose to skip (reason: <label>)
<b5>          | ⚠️ conflict, manual fix needed
<b6>          | ❌ branch missing
```

At the end print `Current HEAD: <source>` to confirm `/forward` did not leave the user on another branch. **No push** (`/push` is a separate operation).

## Constraints

- **Pure merge**: no `git push`, no `--force` / `--force-with-lease`, no `--amend`, no `git rebase`, no `git reset` (do not touch git refs outside `git merge --abort` on conflict)
- **Source is always the current branch**: source change is the user's responsibility via prior `git checkout`; `/forward` does not accept a source argument
- **Dirty source = stop**: do not "stash then forward"; the user decides stash / commit
- **Conflict = stop and ask**: do not auto-resolve conflicts; even if user picks "merge anyway" and hits a real conflict, only abort — never leave a half-merged state
