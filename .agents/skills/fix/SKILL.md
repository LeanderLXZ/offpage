---
name: fix
description: Triage findings from /post-check / /full-review / /check-review into fix / todo / skip, then delegate fixes to /go or /do. Triggers: fix / fix it / triage findings / handle the review findings / /fix.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (logs / docs / commit messages / code comments / files written / fix brief composed for the delegated `/go` / `/do` discussion context) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / status lines / strategy declarations / per-finding summary table rendered in chat) uses `conversation_language`. Code identifiers, file paths, field names, frontmatter keys, and structural prefixes (`Step N:`, `H1`, `M1`, `L1`, `OQ1`, `REVIEWED-PASS`, etc.) stay English regardless.

# /fix — post-audit triage handoff

Triage findings from the most recent review surface — `/post-check`, `/full-review`, or `/check-review` — into three buckets (fix / todo / skip) and delegate the fix bucket to `/go` or `/do`. `/fix` does not modify code on its own; every landing is delegated. The discipline baked into this skill is that AI's recommended disposition is **only a starting position** — the user always picks (Auto = "accept all recommendations as a single bulk action"; Item-by-item = "decide per finding"). Open Questions (OQ) share the same 3-option schema with H/M/L findings.

**Discipline (anti-over-engineering, applies to both Auto and Item-by-item modes)** — before delegating, the fix brief handed to `/go` / `/do` always carries this paragraph verbatim:

> Anti-over-engineering reminder: post-review fixes — minimal patches only. No opportunistic refactor / "while I'm here" cleanup / new abstractions / new tests / new flags. If a 3-line edit solves it, do not extract helpers. Reviewers picked these findings precisely because they are worth fixing on their own — do not bundle adjacent rewrites unless the reviewer flagged them.

This reminder propagates the discipline of `/do` Step 1.0 (Dilution Self-Check) and `/go`'s no-opportunistic-edit discipline into the delegated round.

## Progress reporting

> **Language**: progress-tool entries (`content` field) are user-facing — write them in `conversation_language` per `ai_context/skills_config.md §Language`. The `Step N:` prefix stays English (structural label); subtitle text after the colon translates to `conversation_language`.

The flow below is split into `## Step 0:` ~ `## Step 5:`.

**Before entering Step 0**: call **<progress tool>** to pre-register Step 0 ~ Step 5 (**one entry per parent Step**, `content` as `Step N: <sub-section title>`, all `status` = `pending`). Step 4 registers as a single entry `Step 4: triage dispatch (Auto or Item-by-item)` — 4a / 4b are mutually exclusive runtime branches, not separate entries; the chosen branch flips Step 4 `in_progress` then `completed`. This is a hard requirement — **do not proceed without calling <progress tool>**.

On entering each step: call **<progress tool>** to flip the current step to `in_progress` (in the same call, mark the previous step `completed`), then do the actual work. **Do not skip the call when crossing steps.** Progress is shown directly through the <progress tool> UI; **do not print progress lines like `[/fix] Step N: ...` in the conversation**.

Skipping a step: call **<progress tool>** to mark the corresponding entry `completed` directly, and print one line in the conversation `Step N skipped (reason: …)` — the "reason" is information the UI lacks, so keep this line; do not silently skip.

Final step done: call **<progress tool>** to mark the last entry `completed`.

**<progress tool> resolution**: Claude → `TodoWrite` (rendered as "Update Todos"); Codex → `update_plan`; other runtimes (no structured progress tool, e.g. Copilot agent mode) → maintain a markdown checkbox list in the response text as step state, rewriting the whole block before each state change. Semantic alignment: pre-register + flip state + mark complete.

**<ask tool> resolution**: Claude → `AskUserQuestion` (max 4 questions per call, batch beyond); other runtimes (no structured ask tool, e.g. Codex / Copilot agent mode) → enumerate questions + options per question in the response text and let the user answer in one pass (still max 4 per batch, batch beyond).

**<skill tool> resolution**: Claude → `Skill` (handoff to the named skill with `$ARGUMENTS` as the args field); other runtimes — print "User: please run `/go <slug>` next" (or `/do <slug>` / `/todo-add`) and let the user invoke manually. Semantic alignment: `/fix` writes the fix brief into conversation context first, then triggers the next skill so the receiving skill reads the brief as the discussion baseline.

## Step 0: Load skills config

`Read` `ai_context/skills_config.md`.

- File missing / any section header missing → fail loudly: print the missing items + prompt to complete per plugin template, stop
- Section content `(none)` or empty → skip the related steps for that section (treat as N/A in this project)
- Section lists concrete paths but the path does not exist → fail loudly: report the section drifting to a nonexistent path, stop and wait for the user to fix

Subsequent steps referencing "skills_config.md `## XX`" use this config. This skill uses:
`## Language` (L1 + L3 directives throughout — already loaded via the file header read),
`## Activity sources.Change logs.Path` + `Filename time pattern` (Step 1 disk fallback for `REVIEWED-*` change-log entries),
`## Activity sources.Review reports.Path` + `Filename pattern` (Step 1 disk fallback for `/full-review` outputs).

After reading, print one line **Language-axes anchor**: `Language axes: conversation_language=<value> · content_language=<value> (source: ai_context/skills_config.md §Language)`. Both axis values are echoed **verbatim** from the §Language section; the bracketed source path stays English; the natural-language prefix translates to `conversation_language` (rendered in the project's chosen language). This is a deliberate high-salience anchor planted before Steps 1–5 accumulate context.

## Step 1: Locate findings source

Resolution rule (three-tier; first non-empty wins):

1. **`$ARGUMENTS` slug / keyword match.** Treat `$ARGUMENTS` as either a slug or a model keyword:
   - Match against `<change_logs_path>/*.md` filenames (path per `skills_config.md ## Activity sources.Change logs`) — pick the most recent file whose filename contains the slug, then check it has a `## Review conclusion` writeback from `/post-check` (else reject)
   - Match against `<review_reports_path>/*.md` filenames (path per `skills_config.md ## Activity sources.Review reports`) — pick the most recent file whose filename contains the slug or model keyword (`claude` / `opus` / `sonnet` / `codex` / `gpt` follow the same alias rules as `/check-review` Step 0 / `## Activity sources.Review reports`)
   - Match against an in-session `/check-review` re-check output (no disk artifact; identified by the `Source Report:` line in the rendered output) — `$ARGUMENTS` slug treated as a substring against that source-report path
   - No match → fail loud listing the existing slugs / model entries under the two paths
2. **Most recent review surface in current session.** Scan the conversation context (most recent first) for any of these markers, take the most recent:
   - `/post-check` Step 6 output — identified by the `## Scope` / `## Track 1` / `## Track 2` heading sequence + the Step 5 writeback `LOG: <path>` echo printed in the same conversation
   - `/full-review` rendered output — identified by the `## Findings` / `## Alignment Summary` / `## Residual Risks` / `## Open Questions / Ambiguities` / `## Recommendations` heading sequence + the archive path echo
   - `/check-review` Step 4 output — identified by the `Source Report:` / `Per-Finding Review:` / `Proposed Execution Plan` heading sequence
3. **Disk fallback.** No in-session review surface found:
   - `ls -1t <change_logs_path>/*.md` and pick the most recent file that has a `## Review conclusion` section (search the body)
   - `ls -1t <review_reports_path>/*.md` and pick the most recent
   - Pick whichever has the newer mtime
4. **None.** No tier resolves → **fail loud**: print "no recent `/post-check` / `/full-review` / `/check-review` output found in this session or on disk; run one of those skills first, then `/fix`." and **stop the skill**.

After resolving, parse the source body and build the **findings table** in memory — one row per finding with these columns:

- **ID**: stable from the source (`H1`, `M2`, `L3`, `OQ1`, …). Renumber only if the source has no IDs (backfill in source order, note in the conversation "IDs backfilled this round"); never rename IDs that the source already issued
- **Severity bucket**: `High` / `Medium` / `Low` / `OQ` (Open Question)
- **File:line**: the evidence anchor cited by the finding (or `(no file anchor)` if the finding is repo-wide)
- **Description**: 1-sentence summary trimmed from the source
- **AI-recommended disposition** + **token set**: derived from the **set** of disposition tokens the source's "Recommendations" entry contains (`/post-check` Step 6 §Recommendations, `/full-review` Output §Recommendations, `/check-review` Step 4 §Recommendations). Apply this alias map to identify tokens in the prose (the three upstream review skills emit non-uniform tokens; normalize them here):
  - `fix` ← `fix`
  - `todo` ← `todo` / `leave as todo` / `leave todo` / `park todo` / `park as todo` / `defer to todo` / `defer` (OQ surface wording)
  - `skip` ← `skip` / `skip — <reason>`
  - `adopt` (OQ-only) ← treated as `fix` for bucket-routing purposes (adopted OQ-answer joins the fix delegation brief; see Step 4b.1 for OQ-surface wording)
  
  Collect every recognized token in the entry's prose (deduped, preserving prose-order) → call it the **token set**. Pure token-count detection: separator words (`or` / `/` / `;` / `,`) do not change the count. Then categorize the disposition:
  - `|set| == 0` (no token recognized, or source has no Recommendations section / entry for this ID) → `unknown`
  - `|set| == 1` → that single token (`fix` / `todo` / `skip` / `adopt`)
  - `|set| >= 2 ∧ skip ∈ set` → `silent_skip` (Auto resolves to skip without asking — see Step 4a.1)
  - `|set| >= 2 ∧ skip ∉ set ∧ todo ∈ set` → `silent_skip_todo_eligible` (Auto resolves to skip; Step 5 wrap-up surfaces the ID so the user can re-register as todo via Item-by-item if wanted)
  - `|set| >= 2 ∧ skip ∉ set ∧ todo ∉ set` → `needs_input` (Auto asks the user mid-flight at Step 4a.0; the preserved token set drives the option-order rule there)
  
  Retain the token set on the row even for single-token findings, so Step 4a.0's option-order rule (AI's offered tokens first by internal precedence `fix → todo → skip`, then fill the missing third) can reference it. `silent_skip` and `silent_skip_todo_eligible` are NOT asked at Step 4a.0 — they are dropped by the Step 4a.1 filter without user input

After resolving, **fail-fast on three empty conditions**:

- **No findings at all** (h+m+l+oq == 0, e.g. a `REVIEWED-PASS` log) → print `Selected findings source: <path>; no findings to triage. /fix exited.` and stop
- **`$ARGUMENTS` resolved via tier 1 but in-session has a more recent review** → print one extra transparency line: `Note: tier-1 ($ARGUMENTS) selected; in-session <type> at <path> would have been picked otherwise.`
- (other empty cases are caught downstream at Step 4)

Print one summary line:

`Selected findings source: <path or "in-session /post-check">; H={h} M={m} L={l} OQ={oq}; recommendations: fix={f} todo={t} skip={s} auto-skipped-by-multi={n} (todo-eligible={k}) unknown={u} needs_input={ni}; gaps={u+ni}`

where `n = count(silent_skip) + count(silent_skip_todo_eligible)`, `k = count(silent_skip_todo_eligible)` (subset of `n`), and `gaps = u + ni` — findings that will trigger a mid-Auto targeted ask at Step 4a.0 if Auto is picked.

If `gaps > 0`, append one extra line: `Note: {gaps} findings need your input mid-Auto (Step 4a.0 will ask in batches of ≤ 4); Auto still proceeds for the rest.`

## Step 2: Recommend `/go` vs `/do`

Compute the AI's recommendation per `/do`'s envelope rules (single source of truth: see `skills/do/SKILL.md` Step 1.1):

- **≥ 6 distinct files implicated by the fix-recommended subset** (count the unique `File:line` anchors of every finding whose AI-recommended disposition is `fix`, plus any cross-file file the finding's description explicitly names) → recommend `/go`
- **Any fix-recommended finding's anchor lives under `docs/` or `ai_context/`** (and the discussion target is that file — not opportunistic) → recommend `/go`
- **Otherwise** → recommend `/do`

Print one line:

`Recommended: /go (or /do). Rationale: <one sentence — e.g. "fix subset touches 7 files across skills/ + docs/", or "fix subset is 3 files inside skills/ only, no docs/ai_context spillover">.`

Cache the recommendation as `<RECOMMENDED>` (and the other as `<OTHER>`) for Step 3 / Step 4.

## Step 3: Top-level mode dispatch (Auto / Item-by-item / Exit)

Call **<ask tool>** with one question. The 4-option ask is shown unconditionally — ambiguity (`gaps > 0`) is handled inside Step 4a at sub-step 4a.0, not gated here.

Question: `${h+m+l+oq} findings selected (fix={f} todo={t} skip={s} auto-skipped-by-multi={n} (todo-eligible={k}) gaps={gaps}); recommended landing path: /<RECOMMENDED>. Choose how to proceed.`

When `gaps > 0`, append to the question body: `Note: Auto will ask {gaps} per-finding questions mid-flight at Step 4a.0 (batched ≤ 4); the rest stays Auto.`

Options (exactly four, recommended option first):

1. **Auto — apply AI recommendations via `/<RECOMMENDED>` (recommended)** — multi-disposition findings containing `skip` or `todo` silently resolve to skip (todo-eligible IDs reported at Step 5); gap findings (`unknown` / `needs_input`) get a per-finding ask at Step 4a.0 batched ≤ 4 per call; only fix-resolved findings reach `/<RECOMMENDED>`; "todo" and "skip" single-token recommendations both drop (no automatic `/todo-add` in Auto mode); fix brief carries the source review path + selected IDs + anti-over-engineering reminder; proceed to Step 4a
2. **Auto — apply AI recommendations via `/<OTHER>`** — same dispatch logic but delegates to `/<OTHER>` instead (user overrides AI's `/go` vs `/do` recommendation); proceed to Step 4a
3. **Item-by-item — decide each finding (and each OQ) myself** — proceed to Step 4b (ignores the silent-skip / gap categorization; every finding gets asked)
4. **Exit — drop the triage** — abort the skill, no delegation, no `/todo-add`; print `/fix exited; no actions taken` and stop

## Disposition schema (shared by Step 4a.0 + Step 4b.1)

Both Step 4a.0 (gap resolution) and Step 4b.1 (item-by-item) ask per-finding with **exactly three options, AI-recommended option first**. The options + order rule are defined once here; each sub-step supplies only its own `<disposition-clause>` / `<suggestion-clause>` wording (below).

**H/M/L findings** — `<ID> (<file:line>): <description>. <disposition-clause>. Choose disposition.`
1. **Fix** — include in this round's delegated landing (the chosen `/go` / `/do` path)
2. **Add todo** — register as a `/todo-add` Next entry instead of fixing this round
3. **Skip** — do not fix, do not register

**Open Questions (OQ)** — same 3-bucket schema, OQ surface — `<OQ ID>: <question text>. <suggestion-clause>. Choose disposition.`
1. **Adopt** — accept AI's suggested answer and fold into this round's fix delegation
2. **Defer to todo** — register the open question as a `/todo-add` Discussing entry for later
3. **Skip** — do not act on this OQ this round

**Option order**: single-token disposition → recommended first, then the rest in `fix → todo → skip` (H/M/L) / `adopt → defer → skip` (OQ); multi-token → AI's offered tokens first by that precedence, then fill the missing one; `unknown` → fixed precedence. A batch may mix H/M/L + OQ — do not split by severity.

## Step 4a: Auto path (recommended option / other option)

> **Language**: disk-bound — the fix brief composed at 4a.1 is disk-bound from the moment of composition (it becomes the discussion context for the delegated `/go` PRE log or `/do` discussion). Write the brief in `content_language` per `ai_context/skills_config.md §Language`. The user-facing wrapper prose around the brief (the "I will hand off the following brief to /go" lead-in line and the `Skill` invocation confirmation) translates to `conversation_language`; the brief content itself stays in `content_language`. Code identifiers, file paths, IDs stay English regardless.

### 4a.0 Resolve gaps (mid-Auto user input)

Count `gaps = count(unknown) + count(needs_input)`. If `gaps == 0`, skip directly to 4a.1.

If `gaps > 0`, batch per-finding `<ask tool>` calls (max 4 per call) using the **Disposition schema** above. Per-finding clause:
- H/M/L `<disposition-clause>`: `AI offered: <token1> / <token2>` when `needs_input` (echo recognized tokens in prose order); `AI recommendation: (none — pick yourself)` when `unknown`.
- OQ `<suggestion-clause>`: `AI offered: <candidate1> / <candidate2>` when `needs_input`; `AI suggestion: (none — pick yourself)` when `unknown`.

After all batches are answered, merge user picks back into the findings table (overwrite each gap row's disposition with the chosen single token: `fix` / `todo` / `skip` for H/M/L, `adopt` / `defer` / `skip` for OQ). Then proceed to 4a.1. **Note**: gap-resolved `todo` and `defer` picks do NOT trigger `/todo-add` in Auto mode (consistent with the bulk-accept design — Auto only delegates the `fix` / `adopt` subset; "todo" picks land as dropped with the rest). If the user wants those gap-picks registered as todos, they re-run `/fix` Item-by-item.

### 4a.1 Filter + compose fix brief

Filter the findings table to keep only rows whose final disposition is `fix` or `adopt`. Drop everything else, including `silent_skip` / `silent_skip_todo_eligible` rows and any gap rows the user picked `todo` / `skip` / `defer` for (no `/todo-add` calls — Auto mode is "accept the recommendations, period").

If the filtered set is **empty** (AI recommended only `todo` / `skip` / `silent_skip` / `silent_skip_todo_eligible` across the board, and the 4a.0 gap-ask didn't promote any to `fix` / `adopt`): print one line `Auto mode found no findings recommended for fix; nothing to delegate. Dropped: {t} todo + {s} skip + {n} auto-skipped-by-multi (of which todo-eligible={k}) + {gaps_resolved_non_fix} gap-resolved-to-todo-or-skip from this round. To register the "todo" recommendations explicitly, re-run /fix in Item-by-item mode.` Then, if `k > 0`, print one additional reminder line: `Note: {k} findings auto-skipped because AI's multi-option included \`todo\`; rerun /fix Item-by-item if you want them registered as todos: <ID list>.` Then **stop the skill** (mark Step 4: completed).

Otherwise, compose the **fix brief** and write it into the conversation as a fenced code block:

```
Source review: <resolved source path> (Type: <GO|review_report|check-review-output>, status: <REVIEWED-PASS|REVIEWED-PARTIAL|REVIEWED-FAIL|n/a>)
Findings selected for fix: <comma-separated ID list, e.g. H1, H3, M2>
OQ resolutions (if any): <OQ1 resolved as "<AI's recommended answer>" | none>

Anti-over-engineering reminder: post-review fixes — minimal patches only. No opportunistic refactor / "while I'm here" cleanup / new abstractions / new tests / new flags. If a 3-line edit solves it, do not extract helpers. Reviewers picked these findings precisely because they are worth fixing on their own — do not bundle adjacent rewrites unless the reviewer flagged them.

Per-finding detail:
- H1 (<file:line>): <description trimmed from source>
- H3 (<file:line>): <description>
- M2 (<file:line>): <description>
- OQ1 (<file:line>): <description> — resolution: <answer>
```

Then invoke **<skill tool>** with the chosen target:

- Target = `<RECOMMENDED>` or `<OTHER>` (per Step 3 selection)
- `$ARGUMENTS` = `fix-from-<source-type>-<source-timestamp>` (e.g. `fix-from-postcheck-2026-05-23_094517`); source-type is `postcheck` / `fullreview` / `checkreview` derived from the resolved source's filename or render type; source-timestamp is the source's filename timestamp (or current timestamp if no filename)

Proceed to Step 5.

## Step 4b: Item-by-item path

### 4b.1 Per-finding asks (batched, max 4 per call)

Iterate over the findings table in **source order** (preserving the source's H1, H2, …, M1, …, L1, …, OQ1, … sequence). For each finding, prepare one `<ask tool>` question with **exactly three options** (AI-recommended option first).

Ask per-finding using the **Disposition schema** above. Per-finding clause:
- H/M/L `<disposition-clause>`: `AI recommends: <token>` (single token); `AI offered: <t1> / <t2>` (multi-token — list in the row's prose-order); `AI recommendation: (none — pick yourself)` (`unknown` — do NOT print "AI recommends: unknown", it reads as a recommendation literally named "unknown").
- OQ `<suggestion-clause>`: `AI suggests: "<answer>"` (single-token `adopt`); `AI offered: <c1> / <c2>` (multi); `AI suggestion: (none — pick yourself)` (`unknown`).

Batch up to **4 findings per `<ask tool>` call** (the Claude `AskUserQuestion` hard limit). Repeat batches until all findings have been answered.

### 4b.2 Summary table

After all batches are answered, print a summary table in chat:

| ID | Severity | File:line | AI rec | User pick |
|---|---|---|---|---|
| H1 | High | path:line | fix | fix |
| H2 | High | path:line | fix | todo |
| ... | ... | ... | ... | ... |

Below the table, print bucket counts:

`Fix bucket: N findings. Todo bucket: M findings. Skip bucket: K findings.`

### 4b.3 Branch on bucket emptiness

- **All three buckets empty** (impossible if user answered every batch — defensive guard) → print `no actions selected; exiting` and stop
- **Only the skip bucket non-empty** → print `all findings skipped; no actions to take; exiting` and stop
- **Fix bucket empty, todo bucket non-empty** → no `/go` / `/do` delegation; proceed to 4b.5 (todo handling) only
- **Fix bucket non-empty** → proceed to 4b.4 (re-ask `/go` vs `/do`)

### 4b.4 Re-ask `/go` vs `/do` (fix bucket only)

Re-compute the recommendation per Step 2's rules, but **against the user's fix bucket** (which may differ from AI's fix subset). Cache the result as `<RECOMMENDED_2>` / `<OTHER_2>`.

Call **<ask tool>** with one question:

Question: `Fix bucket contains N findings. Recommended landing path: /<RECOMMENDED_2>. Choose how to land.`

Options (exactly three, recommended first):

1. **Auto — land via `/<RECOMMENDED_2>` (recommended)** — compose fix brief from the fix bucket; invoke `Skill("<RECOMMENDED_2>")` with `$ARGUMENTS = fix-from-<source-type>-<source-timestamp>` (slug computed as in Step 4a)
2. **Auto — land via `/<OTHER_2>`** — same as above but delegate to `/<OTHER_2>`
3. **Exit — drop the fix bucket (also drop the todo bucket if any)** — abort, no delegation, no `/todo-add`; print `/fix exited; no actions taken` and stop

On option 1 / 2: compose the fix brief in the same format as Step 4a (Source review / Findings selected / OQ resolutions / Anti-over-engineering reminder / Per-finding detail) and invoke `Skill(...)`. Then proceed to 4b.5 for the todo bucket.

### 4b.5 Todo bucket — invoke `/todo-add` per item

When the todo bucket has > 1 item, print one pre-warning line before the first invocation:

`About to invoke /todo-add {N} times sequentially (one per todo-bucket finding); each invocation runs its own Step 5 preview ask — you will see {N} preview prompts in a row.`

Then, for each finding in the todo bucket, **before invoking `<skill tool>`, print a fenced context block** carrying the finding's metadata (so `/todo-add` Step 2 — which reads "from the last few turns of the current session" and is instructed "do not guess, do not stitch on the user's behalf" — can grab it cleanly without re-asking the user). The fenced block format:

```
Todo bucket item from /fix (source review: <path>):
- ID: <finding ID — H1 / M2 / OQ1 / etc.>
- File:line: <evidence anchor>
- Description: <one-line summary trimmed from source>
- Why registered as todo: <user's reason from 4b.1 pick, or "deferred per AI recommendation">
```

Then invoke **<skill tool>** with target = `todo-add` and `$ARGUMENTS = next` (OQs deferred to todo use `$ARGUMENTS = discuss` since they carry open decisions; H/M/L deferred to todo use `next`). The skill body of `/todo-add` will handle UPDATE-vs-CREATE semantic match per its own contract; the fenced block above becomes the canonical session-context Step 2 reads.

> **Important**: do NOT bypass `/todo-add` and write directly to `docs/todo_list.md`. The Index refresh + UPDATE-vs-CREATE semantic match + preview-and-confirm are part of `/todo-add`'s contract; bypassing them violates `ai_context/conventions.md §Cross-File Alignment` (row: "Todo entry format — owner `templates/.../todo_list.md` File guide + consumer `/todo-add`").

If `/todo-add` for any item is cancelled by the user (per its Step 5 Cancel option), continue to the next item — do not abort `/fix`. After all todo items have been processed, proceed to Step 5.

## Step 5: Wrap-up

Print one line summarising what was handed off:

- **Auto path (Step 4a)**: `✓ /fix complete — handed off to /<RECOMMENDED|OTHER> with N findings; source review: <path>. Re-verification not auto-run — invoke /post-check yourself when the delegated round finishes if you need it.`
- **Item-by-item path with fix bucket non-empty (Step 4b.4 option 1 / 2)**: `✓ /fix complete — handed off to /<RECOMMENDED_2|OTHER_2> with N fix findings + registered M todo entries; source review: <path>. Re-verification not auto-run — invoke /post-check yourself when the delegated round finishes if you need it.`
- **Item-by-item path with only todo bucket (Step 4b.5 only)**: `✓ /fix complete — registered M todo entries; no fix delegation; source review: <path>.`
- **Item-by-item path with all-skip**: `✓ /fix complete — all findings skipped; no actions taken; source review: <path>.`

**Auto-path todo-eligible reminder** (Auto path only — Step 4a.1 already prints this for the empty-filter case; this branch covers the non-empty fix-bucket case): if `silent_skip_todo_eligible` count `k > 0`, after the wrap-up line print one extra reminder: `Note: {k} findings auto-skipped because AI's multi-option included \`todo\`; rerun /fix Item-by-item if you want them registered as todos: <ID list>.`

Do not invoke `/post-check` after fixes land — the user decides whether to re-verify (typical follow-up: run the delegated `/go` / `/do`, then optionally `/post-check` again). Do not commit, do not push, do not write to disk beyond the fix brief and the delegated-skill arguments.

## Constraints

- **No code changes by `/fix` itself**. Every landing is delegated to `/go` or `/do`; every todo registration goes through `/todo-add`; every audit re-run is the user's decision (re-invoke `/post-check` manually).
- **Auto mode drops "todo" recommendations**. By design — Auto mode is the bulk-accept path; users who want explicit todo registration pick Item-by-item.
- **Auto mode handles multi-disposition gracefully**. Findings whose recommendation prose contains 2+ tokens silently resolve to skip when `skip` or `todo` is present (todo-eligible IDs surfaced in Step 5 wrap-up); other gaps (`unknown` / `needs_input`) route through the mid-Auto Step 4a.0 ask, not a Step 3 fallback to Item-by-item. Never silently downgrade Auto to Item-by-item just because a single finding is ambiguous.
- **OQ uniformity**. Open Questions share the same 3-option schema as H/M/L findings; do not split them into a separate ask round.
- **Anti-over-engineering reminder is mandatory**. Both Auto and Item-by-item paths embed the same fixed-text reminder paragraph in the fix brief; never omit.
- **Source-resolution failure is fail-loud**. If no review surface is found across all three tiers (arg / session / disk), stop with a hint — do not guess, do not pull findings from random commit messages.
- **Per-finding IDs are stable**. Reuse the source's `H1` / `M1` / `L1` / `OQ1` numbering verbatim; backfill only when the source has no IDs and note it explicitly; never rename.
- **The fix brief is the handoff contract**. The receiving `/go` reads it as its discussion baseline (its PRE-log "Background / Trigger" cites it); the brief must always carry: source review path + finding IDs + anti-over-engineering reminder + per-finding detail.
- **No conversation-history rewriting**. `/fix` reads what the review skills already produced; do not re-render the original review report inside `/fix`'s output (that is the source skill's job and the user has it scrolled up).
