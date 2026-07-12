---
name: branch-inventory
description: Read-only inventory of every local + remote branch, grouped by lifecycle bucket (age / ahead-behind / worktree). Triggers: branch inventory / what other branches exist / look at branch status / branch-inventory / clean up branches.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (logs / docs / commit messages / code comments / files written) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / status lines / strategy declarations / findings rendered in chat) uses `conversation_language`. Code identifiers, file paths, field names, frontmatter keys, and structural prefixes (`Step N:`, `LOG:`, etc.) stay English regardless.

# /branch-inventory — Full-branch inventory

List every local + remote branch grouped by role, and annotate each branch with git state + process binding. **Read-only, touches no git / no process**.

## Step 0: Load skills config

`Read` `ai_context/skills_config.md` and pull:

- `## Main branch policy` → main branch name (typical: `main`)
- `## Protected branch prefixes` → list of protected prefixes (typical: `extraction/`)
- `## Background processes` → pgrep patterns + Process artifacts (used to link protected-prefix branches with active processes)

Any section missing or entirely `(none)` → fall back to git defaults (main = `main`, protected = ∅, pgrep = ∅), and explicitly print a **config degraded** notice at the top of the output.

## Step 1: Parse $ARGUMENTS

- Empty / `all` → list everything
- String → treat as a branch-name substring filter (show only branches whose name contains the substring)

## Step 2: Collect local branches

- `git branch -vv` → parse each row: branch name, HEAD short sha, tracking branch, ahead/behind counts
- For each row run `git log -1 --format='%cI %s' {branch}` → get the last commit ISO time + subject
- Compute age: `now - last_commit` (use the skills_config `## Timezone` command template to get now, output in "3d 4h" form)

## Step 3: Collect remote branches

- `git branch -r` → list every remote branch (drop `HEAD ->` rows)
- For remote branches with no matching local branch: tag as **remote-only**

## Step 4: Collect worktree bindings

- `git worktree list --porcelain` → parse each worktree's path / branch
- Build a branch → worktree reverse mapping

## Step 5: Link active processes (protected-prefix branches only)

For each branch matching `## Protected branch prefixes` (typical `extraction/*`):

- Does the branch correspond to an active worktree (Step 4 mapping)?
- If it has a worktree: run `pgrep -f '{pgrep_pattern}'` inside that worktree path to check
- Or derive from `## Background processes` pid-file paths (e.g. `works/{work_id}/analysis/progress/*.pid`): does the branch name contain work_id ∧ is the pid-file process alive?

Produce an "active process binding" flag per protected-prefix branch (true / false / unknown).

## Step 6: Group + output

Output in the following order (one table per group; **list empty groups as "(none)"** so the full picture is visible at a glance):

1. **Main**: single row for `{main_branch}`
2. **Resting branches**: by default includes `library`, `master`, and similar common resting branches (if present in this repo)
3. **Protected (active)**: protected-prefix branches ∧ have an active process binding
4. **Protected (abandoned)**: protected-prefix branches ∧ no active process (likely abandoned)
5. **Other local**: all remaining local branches
6. **Remote-only**: branches that exist only on remote

Per-row table:

| branch | last commit (ISO + age) | ahead/behind | tracking | worktree | process | note |

End with a **suggested actions** summary (**do not execute**, list only):

- `Protected (abandoned)` → suggest checking whether `git branch -d` is safe (user decides; may still hold unmerged extraction intermediates)
- Local branches ahead by several unpushed commits → remind that `/push` may be needed
- Local behind tracking → remind that `git fetch` / `git pull` may be needed
- Worktree pointing at a deleted branch → remind that `git worktree prune` may be needed

## Constraints

- Read-only: no `git checkout` / `merge` / `push` / `fetch` / `pull` / `branch -d` / `worktree prune` / `remote update` / `commit`
- When branch count > 50, show only the first 20 rows per group + "(… N more folded)" notice to avoid flooding the chat
