---
name: run-prompt
description: Load a prompt file (path or fuzzy-matched stem) and execute its body as the current task. Read-only resolution. Triggers: run prompt / run-prompt <name> / run <prompt> / load <prompt>.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (logs / docs / commit messages / code comments / files written) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / status lines / strategy declarations / findings rendered in chat) uses `conversation_language`. Code identifiers, file paths, field names, frontmatter keys, and structural prefixes (`Step N:`, `LOG:`, etc.) stay English regardless.

# /run-prompt — Run a specified prompt file

Execute the contents of the specified prompt file as the current task. Equivalent to "pasting the prompt file into the chat box as a user message", but skips the copy-paste plus auto-fuzzy-matches the filename.

## Step 0: Parse $ARGUMENTS

`$ARGUMENTS` must be non-empty; missing → fail loudly: print `/run-prompt requires a prompt file path or name argument (e.g. /run-prompt ./prompts/<category>/<prompt-name>.md or /run-prompt <prompt-name>)`, stop.

Argument form detection (in this order):

- **Path form**: starts with `/`, `./`, `../`, or contains `/` → treat as relative / absolute path
- **Name form**: plain filename stem (no `/`, with or without `.md` extension) → treat as fuzzy-match key

## Step 1: Resolve to a single prompt file

**Path form**:

- `Read` that path directly
- File missing → fail loudly: `$ARGUMENTS resolved to path '<arg>' but file does not exist`, stop

**Name form**:

- Resolve `<prompt_sources_path>` from `ai_context/skills_config.md ## Activity sources.Prompt sources.Path`
  - Section body `(none)` → fail loudly: `name-form $ARGUMENTS requires a configured prompt-sources directory; ai_context/skills_config.md ## Activity sources.Prompt sources.Path is (none). Either rerun with an explicit path or set the section value.`, stop
- Strip any `.md` suffix to obtain the stem
- `find <prompt_sources_path> -type f \( -name '<stem>' -o -name '<stem>.md' \)` searches the whole tree
  - **0 matches** → fail loudly: `no .md file named '<stem>' found under <prompt_sources_path>` + run `find <prompt_sources_path> -maxdepth 2 -type f -name '*.md'` to list candidates and help the user verify, stop
  - **1 match** → use that file
  - **≥ 2 matches** → list all matching full paths, prompt `multiple prompts share that name, please rerun with the full path`, stop

## Step 2: Extract prompt body

After reading the file, judge the structure:

- **If the file contains exactly one outer fenced code block** (``` followed by an optional language marker such as `text` / `markdown`, then a matching closing ```):
  this is the project's "ready-to-use prompt" wrapper format (canonical: a single fenced block holding the prompt body) → extract the **inner content** of that code block as the prompt body (excluding the fence lines themselves)
- **Otherwise** (no fence / multiple fence pairs / unmatched fence) → use the whole file body as the prompt body

## Step 3: Print resolution summary + take over execution

Print one line: `running prompt: <path relative to working dir>` (so the user can confirm resolution at a glance).

Then **take over execution by treating the prompt body as the user instruction for this turn** — start work per the prompt's guidance.

**Input field completion**:

- Many prompts end with a "user-supplied input" list (canonical fields: raw material path / book title / author / language / other notes)
- If the prompt ends with such a list **and** `$ARGUMENTS` is only the prompt selector (without those fields attached) → **first list the fields to fill + one example format line, wait for the user's reply before proceeding**; do not infer arbitrarily or fall back to defaults
- If `$ARGUMENTS` already attaches input information beyond the prompt selector (e.g. `/run-prompt <prompt-name> path=/tmp/book.epub title=Test`) → substitute into the corresponding fields and execute directly

## Constraints

- **Do not modify the prompt file itself** — this skill reads + executes prompt content only, never writes back to the file
- **No recursive /run-prompt** — a loaded prompt must not invoke `/run-prompt` on another file during execution; if a prompt flow needs to branch into another prompt, do it via explicit steps (read + follow) instead of nested triggering
- **No commit / no push / no git state change** — this skill's work ends at "load and execute per the prompt"; commit / push and other git actions occur only when the prompt itself explicitly requires them (and per that prompt's own rules)
- **Do not bypass the prompt's internal safety / scope constraints** — a prompt may explicitly state safety boundaries (e.g. "do not write into `<output-dir>`"); after loading that prompt this skill must comply, no excuse of "called via /run-prompt so it doesn't count"
