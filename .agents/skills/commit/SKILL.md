---
name: commit
description: Commit the current working tree — choose all-as-one (fast) or scan & split into logical units; safety-net checks (forbidden paths / large files) run silently. No push / force / amend. Triggers: commit / commit it / commit the current changes.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (the commit message body, any in-place file edits like `.gitignore` additions) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / wrap-up `commit OK: <sha> <subject>` line) uses `conversation_language`. Code identifiers, file paths, field names, frontmatter keys, structural prefixes (`Step N:`, `commit OK:`, commit SHAs, branch names) stay English regardless.

# /commit — Quickly confirm and commit the current changes

Run a light verification of the current working tree, then commit. **No full-repo review, no ai_context / docs alignment** (that is `/go`'s job). The expensive part — judging whether each change is worth its own commit + splitting into logical units — is **opt-in** (Step 1 mode choice); the cheap safety net (forbidden paths / large files) always runs but stays silent unless it finds something.

## Progress reporting

> **Language**: progress-tool entries (`content` field) are user-facing — write them in `conversation_language` per `ai_context/skills_config.md §Language`. The `Step N:` prefix stays English (structural label); subtitle text after the colon translates to `conversation_language`.

The flow below is divided into `## Step 0:` ~ `## Step 3:` (the preceding `## $ARGUMENTS parsing` section is argument parsing, not a formal step).

**Before entering Step 0**: call **<progress tool>** to pre-register Step 0 ~ Step 3 (one entry per step, `content` set to `Step N: <sub-section title>`, `status` all `pending`; `$ARGUMENTS` parsing is not counted). This is a hard requirement — **do not proceed without calling <progress tool>**.

On entering each step: call **<progress tool>** to flip the current step to `in_progress` (in the same call, mark the previous step `completed`), then do the actual work. **Do not skip the call when crossing steps.** Progress is shown directly in the <progress tool> UI; **do not print `[/commit] Step N: ...` style progress lines in conversation**.

Skipping a step: call **<progress tool>** to mark that entry `completed` directly, and print one line in conversation: `Step N skipped (reason: …)` — the "reason" is information the UI lacks, keep that line; do not silently skip.

Final step done: call **<progress tool>** to mark the last entry `completed`.

**<progress tool> resolution**: Claude → `TodoWrite` (rendered as "Update Todos"); Codex → `update_plan`; other runtimes (no structured progress tool, e.g. Copilot agent mode) → maintain a markdown checkbox list in the response text as step state, rewriting the whole block on every state change. Semantic alignment: pre-register + flip state + mark complete.

**<ask tool> resolution**: Claude → `AskUserQuestion` (max 4 questions per call); other runtimes (no structured ask tool, e.g. Codex / Copilot agent mode) → enumerate the question + options in the response text and let the user answer in one pass.

## `$ARGUMENTS` parsing

`$ARGUMENTS` as a whole is taken as a hint / subject for the commit message (see Step 3); when empty the message is summarized from the diff.

## Step 0: Load skills config

`Read` `ai_context/skills_config.md`.

- File missing / a section heading missing → fail loudly: print the missing item + prompt to fill it in per the plugin template, stop
- A section's content is `(none)` or empty → skip the section's related steps (treat as not applicable to this project)
- A section lists a concrete path but the path does not exist → fail loudly: report that the section has drifted to a non-existent path, stop and wait for the user to fix

When later steps reference "skills_config.md `## XX`", they refer to this config. This skill uses:
`## Do-not-commit paths` (Step 2 safety-net scan).

## Step 1: Change scope + commit mode

- `git status` + `git diff --stat` inspect the working tree and index.
- **No changes at all** (working tree clean + empty index) → print "no changes to commit" and end; remaining steps skipped.
- Otherwise call **<ask tool>** one question — `How to commit <N> changed files?`:
  1. **All changes as one commit (fast) (recommended)** — skip the per-change worth-judging + logical split; stage the whole change set and commit it in one go (Step 3 mode A). Best for a single-topic working tree.
  2. **Scan & split into logical commits** — AI reads the diff, flags noise (whitespace-only / temp debug / accidental save) and groups the rest into independent commits (Step 3 mode B). Best for a mixed working tree.

  Cache the pick as `<MODE>` (A = all-as-one / B = scan-split). Both modes still run the Step 2 safety net.

## Step 2: Safety net (silent unless triggered)

The cheap checks below run in **both** modes; when everything is clean, proceed **without narration** (at most one line `pre-commit checks: clean`). Only **stop and ask** when something is found — never `git add -A` on your own.

- **Forbidden paths** — scan the change set against `skills_config.md ## Do-not-commit paths` + (`.gitignore` + `ai_context/conventions.md`) fallback. Skip when `## Do-not-commit paths` is `(none)`. (`.gitignore` already blocks *untracked* ignored files; this layer catches *tracked* files + policy paths `.gitignore` cannot.)
- **Untracked files** — `git ls-files --others --exclude-standard`; if any look relevant, ask whether to include / add to `.gitignore` / leave alone.
- **Large / binary files** (> 1MB or binary) — list separately, ask the user to confirm inclusion (cheap insurance against a hard-to-revert blob).

## Step 3: Commit

> **Language**: disk-bound — the commit message text is `content_language` (it paraphrases the change — translate the gist, don't carry the conversation's language over); repo-convention prefixes (`feat:` / `fix:` / `log:` / `docs:` …, per `git log --oneline -10`) stay English. The pre-commit preview wrapper + the post-commit `commit OK: <short-sha> <subject>` line render in `conversation_language`.

- Message style follows `git log --oneline -10` (prefix / verb tense / language convention). `$ARGUMENTS` non-empty → expand it as the subject; otherwise summarize from the diff.
- `git add <specific files>` + `git commit` — **never `git add -A` / `git add .`** (avoid accidentally staging sensitive files).
- **Mode A (all-as-one)** — stage the whole change set, one commit, no split.
- **Mode B (scan-split)** — group the change set along logical units (independent topics → separate commits); do not stuff unrelated topics into one.
- After the commit(s), `git status` confirms clean. Print one line `commit OK: <short-sha> <subject>` (one per commit in mode B).

## Constraints

- No `git push`, no `--force`, no `--amend`, no branch switching, no merge (unless the user explicitly requests).
- No cross-branch sync — that is `/forward`'s job.
- Safety net (Step 2) runs in both modes; anything suspicious (forbidden paths, huge diff, unresolved conflicts) → stop and ask, do not bypass.
