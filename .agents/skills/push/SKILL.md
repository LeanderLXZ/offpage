---
name: push
description: Fast-forward push a local branch to its remote (default = current, never main). No force / no protected branches. Triggers: push / push it / push up / /push <branch>.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (logs / docs / commit messages / code comments / files written) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / status lines / strategy declarations / findings rendered in chat) uses `conversation_language`. Code identifiers, file paths, field names, frontmatter keys, and structural prefixes (`Step N:`, `LOG:`, etc.) stay English regardless.

# /push — Push a branch to remote

Push the specified local branch to its remote. **No commit, no merge, no rebase** — this is just a clean push.

## Progress reporting

The flow below is divided into `## Step 0:` ~ `## Step 3:` (the preceding `## $ARGUMENTS parsing` section is argument parsing, not a formal step).

**Before entering Step 0**: call **<progress tool>** to pre-register Step 0 ~ Step 3 (one entry per step, `content` set to `Step N: <sub-section title>`, `status` all `pending`; `$ARGUMENTS` parsing is not counted). This is a hard requirement — **do not proceed without calling <progress tool>**.

On entering each step: call **<progress tool>** to flip the current step to `in_progress` (in the same call, mark the previous step `completed`), then do the actual work. **Do not skip the call when crossing steps.** Progress is shown directly in the <progress tool> UI; **do not print `[/push] Step N: ...` style progress lines in conversation**.

Skipping a step: call **<progress tool>** to mark that entry `completed` directly, and print one line in conversation: `Step N skipped (reason: …)` — the "reason" is information the UI lacks, keep that line; do not silently skip.

Final step done: call **<progress tool>** to mark the last entry `completed`.

**<progress tool> resolution**: Claude → `TodoWrite` (rendered as "Update Todos"); Codex → `update_plan`; other runtimes (no structured progress tool, e.g. Copilot agent mode) → maintain a markdown checkbox list in the response text as step state, rewriting the whole block on every state change. Semantic alignment: pre-register + flip state + mark complete.

## `$ARGUMENTS` parsing

- `$ARGUMENTS` empty → target branch = `git rev-parse --abbrev-ref HEAD` (current branch). Detached HEAD (output `HEAD`) → stop and report, ask the user to checkout first
- Otherwise → target branch = `$ARGUMENTS` trimmed of surrounding whitespace (take only the first token; extra tokens → error stop, ask the user to restate)

## Step 1: Verify target branch

- `git rev-parse --verify <target>` confirms the local branch exists; missing → stop and report
- `git config --get branch.<target>.remote` + `branch.<target>.merge` fetch the tracking remote / remote branch name
  - No tracking → stop and ask the user: should `git push -u origin <target>` set up tracking? continue only on affirmative reply
- The HEAD does not need to be on the target branch; use `git push <remote> <target>:<remote-branch>` directly (no checkout needed)

## Step 2: Pre-push inventory

- `git fetch <remote> <remote-branch>` fetches the latest remote ref
- Compute ahead / behind: `git rev-list --left-right --count <target>...<remote>/<remote-branch>`
  - ahead=0, behind=0 → already in sync, skip Step 3, print "nothing to push" and wrap up
  - ahead>0, behind=0 → fast-forward viable, enter Step 3
  - behind>0 (regardless of ahead) → remote has commits the local branch lacks, **stop and report**, let the user decide (pull / rebase / abandon); **do not auto force push**
- Also list the ahead commits (`git log --oneline <remote>/<remote-branch>..<target>`) so the user can eyeball them before push

## Step 3: Push

- Execute `git push <remote> <target>:<remote-branch>` (do not pass `--force` / `--force-with-lease` / `--no-verify`)
- Push succeeds → re-run `git rev-list --left-right --count <target>...<remote>/<remote-branch>` to verify 0/0, print the result
- Push fails (hook block, permissions, network, etc.) → print the raw error, stop and let the user handle; **do not retry / do not bypass**

## Constraints

- No `--force` / `--force-with-lease` / `--no-verify` / `--no-gpg-sign` (unless the user explicitly authorizes in this turn); do not touch the working tree (no checkout / commit / merge / rebase)
- Any state outside "local ahead, remote ancestor" (behind>0 / no tracking / push failed) → stop and ask, do not bypass
