---
name: check-review
description: Re-check the latest review report — verify each finding is still present + attach file:line evidence. Read-only; user confirms then /go. Triggers: re-check review / re-check codex review / check-review.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (logs / docs / commit messages / code comments / files written) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / status lines / strategy declarations / findings rendered in chat) uses `conversation_language`. Code identifiers, file paths, field names, frontmatter keys, and structural prefixes (`Step N:`, `LOG:`, etc.) stay English regardless.

# /check-review — Re-check a review report

Perform "truth re-check + plan design" on the **most recent** review report for the specified model under the path declared at `ai_context/skills_config.md ## Activity sources.Review reports.Path` (typically `logs/review_reports/`). **No code changes**; only confirm whether each finding / risk / open question is still genuinely present, and produce a draft landing plan; once the user confirms details, run `/go` to execute.

`$ARGUMENTS` = model filter keyword, **optional**. Mapping rules:
- Empty (no arg) → no model filter; take the **latest by timestamp** in the directory
- `claude` / `opus` / `sonnet` / `haiku` → synonymous aliases; match reports whose slug begins with `opus-` / `sonnet-` / `haiku-` (the Claude family is treated as one source)
- `codex` / `gpt` → synonymous aliases; match reports whose slug is `codex` or begins with `gpt-` (codex and gpt series are treated as one source)
- `gpt-5`, `opus-4-7`, and similar concrete slugs → exact match
- Argument given but no match: error out, listing existing model slugs under the review-reports directory (path per `## Activity sources.Review reports.Path`) for selection

## 0. Pick the file

1. Enumerate every file matching the filename pattern declared at `ai_context/skills_config.md ## Activity sources.Review reports.Filename pattern` (typically `{YYYY-MM-DD_HHMMSS}_{model}_{slug}.md`) under the path declared at `## Activity sources.Review reports.Path` (typically `logs/review_reports/`)
2. Filter per `$ARGUMENTS` mapping rules (skip filter if no argument)
3. Take the **latest** by descending timestamp (only 1; do not merge several)
4. Print: "Selected: `{filename}` (model: {model}, generated: {timestamp})"
5. If argument is given but no match: error out and list every model slug in the directory plus the timestamp of its most recent report
6. If the directory is empty: error out and stop

## 1. Read the report end to end

Read the selected report in full; break out every entry from `Findings` (by High / Medium / Low), `Open Questions / Ambiguities`, `Alignment Summary`, `Residual Risks`, and the suggested landing order into an item checklist. **Do not skim, do not skip Low.**

## 2. Load the sources of truth

- Core `ai_context/` files: conventions / requirements / architecture / decisions / handoff (if this project's `ai_context/` structure differs, fall back to every `.md` file)
- `docs/requirements.md`, `docs/architecture/`
- Code files + line numbers referenced in the report: read the current code directly; do not rely on the report's quoted excerpts
- If the report timestamp is older and commits happened since: `git log --since={report timestamp} --oneline` for a quick scan to identify entries that may already be fixed

## 3. Re-check each entry

For each finding / risk / open question, produce:

- **Re-check verdict**: `genuine` / `partially genuine` / `no longer valid` (already fixed / misjudged / version mismatch)
- **Evidence**: cite the concrete current code / doc file + line number, directly confirming or refuting the report's description; distinguish "direct evidence" from "inference"
- **Impact assessment**: still affects the current main line? does severity need adjusting (raise / lower / keep), with reasoning
- **Plan draft** (only for "genuine / partially genuine"):
  - Which file / function / doc section / schema field / prompt segment to change
  - Change boundary (**no incidental refactor / scope creep**)
  - Risks and rollback path
  - Cross-file consequential updates: cross-check the "Cross-File Alignment" section of `ai_context/conventions.md` and list them (skip this item if the section does not exist)
- **Dependency ordering**: dependencies between this plan and other findings' plans; whether they can be combined into one commit
- **Defer / reject**: state "not this round" with reasoning (logging into `docs/todo_list.md` is for the next /go; here we only flag)

## 4. Output structure

Output markdown (**no write to disk, no code changes, no commit**):

1. `Source Report`: file path, report model, generation timestamp
2. `Per-Finding Review`: per entry with re-check verdict / evidence / plan draft
   - **Strictly reuse the source report's finding IDs** (`H1` / `M1` / `L1`...); if the source report lacks IDs, backfill numbering in source order and note in this report "IDs backfilled this round". After re-check, **preserve the same IDs** — even when severity is adjusted or items are merged, do not renumber (mark withdrawn as "withdrawn", merged as "merged into H1")
3. `Revised Priority`: re-rank by post-check severity (still cite the original IDs, do not rename)
4. `Proposed Execution Plan`: which items to do this round, commit split, ordering (cite by ID)
5. `Deferred / Rejected`: deferred or rejected entries and reasons (cite by ID)
6. `Open Questions for User`: open points needing the user's decision; number each `OQ1` / `OQ2`...
7. `Recommendations`
   - **Reference only; the user's decision wins.** Before each recommendation pass three self-checks:
     1. **Necessary?** — what happens if not fixed? Merely cosmetic / OCD-driven → lean toward "skip" or "park as todo"
     2. **Can it be simpler?** — if a 3-line edit solves it, do not extract a helper / add a layer / add config / add a flag
     3. **Outside source report scope?** — is the opportunistic "related fix" I'm tacking on already exceeding this round's target
   - One flat list: per finding ID (keep original ID) + per OQ give "Suggest {fix / park todo / skip}: {one-line reason / recommended approach}"

## 5. Wait for confirmation

After output, **stop**. Do not enter `/go`, do not write a log, do not change files; wait for the user to confirm / adjust each item before executing. Typical handoffs: `/fix` for triage (bulk-accept AI recommendations OR decide per finding, with delegation to `/go` or `/do`), or `/go` directly when the user has already decided every item.

## Constraints

- This is a re-check, not a second-round review; do not add findings outside the report (unless the report obviously missed a sibling issue sharing the same root cause, which must be tagged "supplemental to report")
- Do not blindly trust the report when its wording is vague, nor reject without evidence; every conclusion must land on file + line number
- Divergence between models is itself a signal: when your re-check conclusion differs significantly from the report, state the disagreement clearly and let the user adjudicate
