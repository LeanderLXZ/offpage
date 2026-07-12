---
name: save-chat
description: Save the current AI conversation (or a user-specified slice) to logs/chats/ as self-contained HTML — script renders the verbatim transcript, AI writes a summary header. Triggers: save chat / save-chat / save this conversation.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (the summary fragment the AI authors, the HTML written into `logs/chats/`, the commit message when the opt-in commit runs) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / the located-file confirmation line / final status line) uses `conversation_language`. The transcript body is rendered **verbatim from the session record** — it is NOT translated, it stays in whatever language each turn was originally written. Code identifiers, file paths, field names, frontmatter keys, CLI flags, and structural prefixes (`Step N:`, `--from`, etc.) stay English regardless.

# /save-chat — Save the conversation to `logs/chats/` as HTML

Save the current session's AI ↔ user conversation (or a user-specified slice) into
`logs/chats/` as a **self-contained HTML** file: an **AI-authored summary header** (key
topics / decisions, tables, bullets, optional inline-SVG diagram) above the **verbatim
transcript**. The transcript is rendered by a bundled script straight from the session
record on disk, so the AI re-emits **only the summary** — cost stays flat no matter how
long the conversation is. After the write the skill **offers an opt-in commit** (via
`<ask tool>`) of just the new file — it never invokes `/commit` and never pushes.

## Progress reporting

> **Language**: progress-tool entries (`content` field) are user-facing — write them in `conversation_language` per `ai_context/skills_config.md §Language`. The `Step N:` prefix stays English (structural label); subtitle text after the colon translates to `conversation_language`.

The flow below is split into `## Step 0:` ~ `## Step 5:`.

**Before entering Step 0**: call **<progress tool>** to pre-register all of Step 0 ~ Step 5 (one entry per step, `content` = `Step N: <sub-section title>`, `status` = `pending` for all). This is a hard requirement — **do not proceed without calling <progress tool>**.

Each time you enter a step: call **<progress tool>** to flip the current step to `in_progress` (mark the previous step `completed` in the same call), then do the real work. **Do not skip the call across step boundaries**. Progress is rendered directly by the <progress tool> UI — **do not print `[/save-chat] Step N: ...` style progress lines in the conversation**.

Skipping a step: call **<progress tool>** to mark the entry directly `completed`, and print one line `Step N skipped (reason: …)` in the conversation — "reason" is information the UI lacks, keep that line; do not silently skip.

Final step completion: call **<progress tool>** to mark the last entry `completed`.

**<progress tool> resolution**: Claude → `TodoWrite` (rendered as "Update Todos"); Codex → `update_plan`; other runtimes (no structured progress tool, e.g. Copilot agent mode) → maintain a markdown checkbox list in the response text as step state, rewriting the whole block on every state change. Semantic alignment: pre-register + flip state + mark complete.

**<ask tool> resolution**: Claude → `AskUserQuestion` (max 4 questions per call, batch beyond); other runtimes (no structured ask tool, e.g. Codex / Copilot agent mode) → enumerate questions + options per question in the response text and let the user answer in one pass.

**<script> resolution**: the bundled renderer is `${CLAUDE_PLUGIN_ROOT}/skills/save-chat/scripts/transcript_to_html.py` (run with `python3`). When `${CLAUDE_PLUGIN_ROOT}` is unset, fall back to the `skills/save-chat/scripts/` path under the installed plugin root.

## Step 0: Load skills_config

`Read` `ai_context/skills_config.md`.

- File missing / any required section header missing → fail loudly: print the missing items + prompt to complete per plugin template, stop
- Section content `(none)` or empty → skip the related step for that section (treat as N/A)
- Section lists a concrete path that does not exist → fail loudly: report the drift, stop

This skill uses:
`## Timezone` (the filename timestamp — run the `Command template`; on missing/failure use the §Timezone-declared fallback `date '+%Y-%m-%d_%H%M%S'`),
`## Language` (drives the summary/commit-message `content_language` + user-facing `conversation_language`; the L1 directive at top already routes both buckets).

The output directory is `logs/chats/` — a sibling of the `## Activity sources.Change logs.Path` parent (`logs/`). It is **auto-created** by the script; no dedicated config section.

## Step 1: Resolve scope + locate the transcript

**Scope** (from `$ARGUMENTS`):

- empty → the whole current session
- `last N` → the last N turns
- a range (`#5-#20`, `5..20`, `from 5 to 20`) → that turn range
- a semantic slice ("the part about X") → resolve to a **single contiguous** turn range (see `--list` below); if the topic is scattered, pick the enclosing range and note the widening in the wrap-up

**Locate** the transcript by running the `<script>` once with `--list` (it prints `index | role | preview` per turn and the resolved file name on stderr):

```
python3 <script> --list
```

The script resolves the file via `$CLAUDE_CODE_SESSION_ID` (→ `~/.claude/projects/<dir>/<id>.jsonl`), falling back to the newest transcript whose `cwd` matches the current directory. Use the `--list` output to (a) confirm the right session was picked, and (b) map a `last N` / semantic scope to concrete `--from` / `--to` indices.

- **Confirm only when the resolution is ambiguous** — i.e. `$CLAUDE_CODE_SESSION_ID` was unset and the fallback matched more than the obvious file, OR the `--list` preview clearly does not match this conversation. Then ask via **<ask tool>** whether to proceed with the located file or supply an explicit `--transcript <path>`. When the env var resolved a single file that matches, do not ask.
- **Degrade**: if the script exits with a locate error and you cannot supply `--transcript` (non-Claude runtime / no on-disk transcript / compacted-away history), fall back to **authoring the HTML by hand from context** — read `template.html`, fill `{{SUMMARY}}` + `{{TRANSCRIPT}}` yourself (omit tool calls, keep user/assistant text), write to `logs/chats/<timestamp>_<ai>_<slug>.html`. Note the degrade in the wrap-up.

## Step 2: Author the summary fragment

> **Language**: disk-bound — the summary fragment lands inside the HTML and is therefore `content_language` per `ai_context/skills_config.md §Language`. Code identifiers / file paths stay English. The transcript body is NOT authored here (the script renders it verbatim).

Write a **concise** HTML fragment summarizing the conversation's core — this is the **only** content the AI emits, so keep it tight and high-signal:

- A short lead paragraph (what this conversation was about).
- A **key topics / decisions** `<table>` and/or `<ul>` bullets (decisions made, open questions, files touched).
- Optionally a small **inline `<svg>`** diagram if it genuinely clarifies (timeline / flow) — keep it lightweight; do **not** reference external JS/CSS (the file must stay self-contained — no mermaid/CDN).

Use only tags the template styles: `h2` / `h3` / `p` / `ul` / `ol` / `li` / `table` / `code` / `strong` / `a` / inline `svg`. Write the fragment to a temp file, e.g. `${TMPDIR:-/tmp}/save-chat-summary.html`.

## Step 3: Render via the script

Compute the filename timestamp via `skills_config.md ## Timezone` (`Command template`; fallback per §Timezone). Pick:

- `--ai` = the runtime family (`claude` under Claude Code; `codex` under Codex; etc.)
- `--slug` = a short kebab-case English topic distilled from the conversation
- `--title` / `--kicker` = a human title for the header (`content_language`)

Run:

```
python3 <script> \
  --ai <ai> --slug <slug> --title "<title>" \
  --timestamp <YYYY-MM-DD_HHMMSS> \
  --summary-file ${TMPDIR:-/tmp}/save-chat-summary.html \
  [--from <i>] [--to <j>]
```

The script writes `logs/chats/<timestamp>_<ai>_<slug>.html` (auto-creating `logs/chats/`) and prints the path to stdout. It keeps only genuine user/assistant **text** turns — tool calls, tool results, thinking, `isMeta` injections, and sub-agent sidechains are dropped.

## Step 4: Verify + report

- Confirm the output file exists and is non-trivial (`wc -c`); if the body looks empty or the wrong session was captured, stop and report rather than committing a bad log.
- Print one line: `✓ saved logs/chats/<file> (<N> turns<, range i–j if a subset>)`.

## Step 5: Commit offer (opt-in)

> **Language**: user-facing — render the `<ask tool>` commit prompt + option labels and the final state line in `conversation_language` per `ai_context/skills_config.md §Language`. The commit message itself is disk-bound — author it in `content_language`. Structural tokens (`✓`, `git`, `docs(chats)`, file paths, short SHA) stay English regardless.

Ask via **<ask tool>** whether to commit:

Question: `Commit logs/chats/<file> now?`

1. **Commit now** — stage and commit just the new HTML file
2. **Don't commit** — leave it in the working tree

**On "Commit now"**:

- Stage only the file this skill wrote: `git add logs/chats/<file>` — scope to that one path; do **not** `git add -A` / do not sweep unrelated working-tree changes.
- Commit with a concise one-line message in `content_language`, conventional-commit style, e.g. `docs(chats): log <slug>`.
- Plain `git commit` only: no `--amend`, no `--no-verify`, no `--force`, **no push**, and **do not invoke `/commit`** (this is a raw `git add` + `git commit`, not a delegation).
- Print one line: `✓ committed <short-sha> <message>`.

**On "Don't commit"**: print `Left uncommitted — run /commit to persist.` and stop.

Do not enter `/go`, do not push.

## Constraints

- **Summary is the only AI-authored content** — the transcript body is rendered verbatim by the script from the on-disk session record; never hand-retype or paraphrase the transcript (that defeats the token budget and risks drift from what was actually said). The one exception is the Step 1 **degrade** path (no reachable transcript), which is explicitly hand-authored.
- **Tool turns omitted** — tool calls, tool results, thinking, `isMeta` injections, and sub-agent sidechains are dropped; only genuine user/assistant text turns are kept.
- **Self-contained output** — single HTML with inline CSS only; no external JS/CSS/CDN, so the file opens offline anywhere.
- **Opt-in commit only / no push** — after the write, offer (via `<ask tool>`) a plain commit of just the new `logs/chats/` file; never `git add -A`, never `--amend` / `--no-verify` / `--force`, never push, never invoke `/commit`. On decline, persistence is delegated to `/commit`.
- **Read-only on history** — `/save-chat` only creates a new file under `logs/chats/`; it never edits prior chat logs, code, docs, or `ai_context/`.
