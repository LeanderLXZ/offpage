---
name: compress-ai-context
description: Prune stale + compress bloated ai_context entries; migrate old single-file decisions logs to the two-tier index + archive format. Triggers: /compress-ai-context / compress ai_context / prune stale ai_context entries / migrate decisions format.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (prune deletions, compress patches, snapshot files copied, follow-up todo entry written into `docs/todo_list.md`, the trailing reminder line if redirected to a file) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / scan summary printed in chat / per-entry preview wrappers / final wrap-up status line) uses `conversation_language`. Code identifiers, file paths, field names, frontmatter keys, section headings (`## Decisions`, `### [T-XXX]`), and structural prefixes (`Step N:`, `PRUNE:`, `COMPRESS:`, `SNAPSHOT:`, etc.) stay English regardless.

# /compress-ai-context — Prune stale + compress bloated ai_context entries

Maintenance counterpart to `/update-docs`: where `/update-docs` *adds*
narrative into `ai_context/` + `docs/` from session discussions, this
skill *trims* and *relocates* existing `ai_context/` content per the
canonical compactness contract. Two phases (both optional / opt-in via
Step 1 gateway): **prune** stale entries (entries that no longer
reflect current architecture / requirements), then **compress**
bloated-but-still-accurate entries by pushing rationale to linked
docs. A third conditional phase — **decisions format migration**
(Step 4.5) — runs between them when Step 1's probe detects
`ai_context/decisions.md` entries still in the single-file fat format
instead of the two-tier index + archive pair (`docs/decisions.md` #35).

**Architecture (post-T-COMPRESS-AI-CONTEXT-PARALLEL refactor)**:
coordinator + scatter-gather. The main agent owns gateway asks /
plan freeze / snapshot / docs landings / completion gate /
verification aggregation; per-file work (scan + classify + apply
on ai_context files) is dispatched to sub-agents in parallel when
total work ≥ threshold. Sub-agents never write to shared files
(docs/, README.md Contents) — those are coordinator-serial. Plan
freezes before any Edit; one `take_snapshot` per phase captures the
frozen-plan file set; rollback after the run is one `cp` away.
Sentinel-aware throughout (won't touch plugin-canonical territory).

## Progress reporting

> **Language**: progress-tool entries (`content` field) are user-facing — write them in `conversation_language` per `ai_context/skills_config.md §Language`. The `Step N:` prefix stays English (structural label); subtitle text after the colon translates to `conversation_language`. Same rule applies to sub-task entries `Step Na:` / `Step Nb:` / ….

The flow below is split into `## Step 0:` ~ `## Step 9:`.

**Before entering Step 0**: call **<progress tool>** to pre-register all of Step 0 ~ Step 9 (one entry per step, `content` = `Step N: <sub-section title>`, `status` = `pending` for all). Step 4.5 (decisions format migration) is conditional — insert its entry only when Step 1's probe fires AND the user confirms migration (Q2 = yes). This is a hard requirement — **do not proceed without calling <progress tool>**.

Each time you enter a step: call **<progress tool>** to flip the current step to `in_progress` (mark the previous step `completed` in the same call), then do the real work. **Do not skip the call across step boundaries**. Progress is rendered directly by the <progress tool> UI — **do not print `[/compress-ai-context] Step N: ...` style progress lines in the conversation**.

Skipping a step: call **<progress tool>** to mark the entry directly `completed`, and print one line `Step N skipped (reason: …)` in the conversation — "reason" is information the UI lacks, keep that line; do not silently skip. Steps 2–4 are skipped wholesale when the Step 1 gateway answer is "no".

Final step completion: call **<progress tool>** to mark the last entry `completed`.

**<progress tool> resolution**: Claude → `TodoWrite` (rendered as "Update Todos"); Codex → `update_plan`; other runtimes (no structured progress tool, e.g. Copilot agent mode) → maintain a markdown checkbox list in the response text as step state, rewriting the whole block on every state change. Semantic alignment: pre-register + flip state + mark complete.

**<ask tool> resolution**: Claude → `AskUserQuestion` (max 4 questions per call, batch beyond); other runtimes (no structured ask tool, e.g. Codex / Copilot agent mode) → enumerate questions + options per question in the response text and let the user answer in one pass (still max 4 per batch, batch beyond).

## Step 0: Load skills_config

`Read` `ai_context/skills_config.md`.

- File missing / any section header missing → fail loudly: print the missing items + prompt to complete per plugin template, stop
- Section content `(none)` or empty → skip the related steps for that section (treat as N/A in this project)
- Section lists concrete paths but the path does not exist → fail loudly: report the section drifting to a nonexistent path, stop and wait for the user to fix

This skill uses:
`## Language` (drives `content_language` for disk artifacts + `conversation_language` for user-facing surface; the L1 directive at top of this file already routes both buckets),
`## Timezone` (Step 4 / Step 7 snapshot timestamps via the command template),
`## Activity sources` (TODO list path for the optional follow-up todo created in Step 4 when the user picks `Auto-prune + create follow-up todo`).

Also `Read` `ai_context/conventions.md §Compactness Requirements` — this is the canonical contract this skill enforces; do not re-author its rules locally.

## Step 1: Gateway ask (prune + migration opt-in)

**Migration probe (deterministic, before the ask)**: run

```
python3 -c "import sys, json; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts'); \
from holo_update_check import decisions_fat_format_check; \
print(json.dumps(decisions_fat_format_check('.')))"
```

Non-empty result = `ai_context/decisions.md` still carries fat-format
entries (block > 3 non-empty lines, or no `→ docs/decisions.md #N`
pointer) → carry `<fat_entries>` (the finding list) into the ask below.
Empty result / file absent → no migration question; `<fat_entries>` = ∅.

Ask via **<ask tool>** — one batched call; question 2 only when `<fat_entries>` ≠ ∅:

Question 1: `Scan ai_context for stale entries to prune before compressing?`

1. **No — compress only (recommended; faster)** — skip Steps 2–4 (prune phase)
2. **Yes — prune first, then compress** — enter Steps 2–4 (prune phase)

Question 2 (conditional): `Detected <N> decisions entries in the old single-file format. Migrate to the two-tier index + archive format (ai_context index + docs/decisions.md) before compressing?`

1. **Yes — migrate (recommended)** — enter Step 4.5 after the prune phase (or directly, when prune was declined)
2. **No — keep the current format** — skip Step 4.5; fat entries are then eligible for plain compression in Step 5 like any other bloated entry, and `/holo:update` will keep surfacing them as `decisions_fat_format` findings

Default = Q1 option 1 (no) + Q2 option 1 (yes). Most invocations are pure compression. The prune phase is opt-in because (a) it requires whole-repo grep for live-ref detection and is materially slower, and (b) stale detection is LLM-semantic so it should be deliberately invoked, not implicit. The migration question is asked only on positive detection, so it costs nothing on already-migrated projects.

## Step 2: Prune scan (when Step 1 = yes)

For each of the 5 ai_context files
(`decisions.md` / `conventions.md` / `requirements.md` /
`architecture.md` / `handoff.md`):

1. **Parse via `${CLAUDE_PLUGIN_ROOT}/scripts/sentinel_parse.py`** (`parse(path) -> ParsedFile`). Consider **only gap-territory content** (`ParsedFile.preamble_user_gaps` + each `Section.user_gaps`). **Skip plugin-canonical territory** (`preamble_plugin_blocks` + each `Section.plugin_blocks`) — that content is owned by `/holo:update`, out of scope for this skill.

2. **Apply file-type starter heuristics** (inspection triggers, NOT sufficient evidence on their own):
   - `decisions.md` — pointer-target file/function in the `→` line does not exist; entry self-marks `superseded by #N`; entry references a removed/renamed module that `grep` cannot find.
   - `conventions.md` — Cross-File Alignment row lists files that no longer exist; row's lockstep relationship references removed flow.
   - `requirements.md` — paired `docs/requirements.md §N` section absent; requirement references a removed feature.
   - `architecture.md` — referenced `docs/architecture/<topic>.md` / module / file absent.
   - `handoff.md` — referenced command / skill no longer in `commands/` or `skills/`; `## Next Steps` table row references a todo already in `docs/todo_list_archived.md ## Completed` / `## Abandoned`.

3. **LLM semantic judgment** (the main driver): for each entry, read it and judge — is it still aligned with the current architecture / requirements? Was the decision overturned by a later decision (search `ai_context/decisions.md` for newer #N entries on the same topic)? Has the referenced module / file / flow been removed or restructured? Heuristics from #2 raise candidates for inspection; LLM decides the actual `stale` verdict.

4. **Live-reference grep** for each `stale` candidate. Scope = `repo - logs/ - docs/todo_list_archived.md` (the two historical roots; references inside them don't count as live). Search for: the entry's stable identifier (e.g. `decisions.md #19` for a decisions entry; conventions row title; requirement number); plus the entry's key terms (module names, file paths it mentions). Classify each candidate as `stale + no live refs` (safe orphan) or `stale + has live refs` (needs user decision).

Print to the conversation a scan summary in this shape:

```
PRUNE scan:
- ai_context/decisions.md: 23 entries scanned, 2 stale (0 orphan, 2 with live refs)
- ai_context/conventions.md: 34 rows scanned, 0 stale
- ai_context/requirements.md: 16 entries scanned, 1 stale (1 orphan, 0 with live refs)
- ai_context/architecture.md: 12 entries scanned, 0 stale
- ai_context/handoff.md: 3 sections scanned, 0 stale
Total: 3 stale candidates (1 orphan, 2 with live refs)
```

If `Total: 0 stale`, skip to Step 5 with a one-line `0 stale entries found, prune phase no-op` notice.

## Step 3: Prune per-case ask (only when `stale + has live refs` set is non-empty)

For each `stale + has live refs` case (batched up to 4 questions per `AskUserQuestion` call; batch beyond if > 4 cases):

Question: `Stale entry "<file>:<entry-id-or-title>" still has N live ref(s) at <file:line>, <file:line>, … . How to handle?`

1. **Auto-prune + create follow-up todo (recommended)** — delete the entry; defer the dangling-ref cleanup to a new bundled `T-XXX` entry created in Step 4 (single todo per skill invocation, listing all such dangling refs as its change manifest).
2. **Auto-prune + leave dangling refs** — delete the entry; leave the live refs in place (they'll grep-fail; user accepts the broken state).
3. **Skip (keep entry as-is)** — do not prune; entry stays even though LLM judged it stale.

`stale + no live refs` cases are NOT asked — they go straight to apply in Step 4.

## Step 4: Prune apply

> **Compactness Requirements**: any new content this step writes (the bundled follow-up todo entry created when "Auto-prune + create follow-up todo" was picked) follows the universal contract — see the 4-rule blockquote in Step 7 (and `ai_context/conventions.md §Compactness Requirements`, the canonical source).

a. **Snapshot-on-plan-freeze**: by the end of Step 3 the prune plan is frozen (which entries delete + whether a follow-up todo is needed). Before any `Edit`, call `take_snapshot(target_root, slug='compress-ai-context-prune', file_paths=[touched ai_context files + docs/todo_list.md if a follow-up todo will land])` **once**, covering all files in the frozen plan. Not pre-emptively at skill startup, and not piecemeal per-Edit. Snapshot root is resolved by the helper from `ai_context/skills_config.md ## File snapshots` (default `<target_root>/logs/file_snapshots/`); callers do not pass the root, the helper reads it. Capture the returned snapshot dir path for the wrap-up.

b. **Apply each pruned entry via `Edit`** (one `Edit` per entry; no batched `replace_all`). For `decisions.md` entries: do NOT renumber surviving entries (per `decisions.md §Format` global-append-only rule); just delete the offending block. For `conventions.md` rows: delete the table row only. For all 5 files: also remove any redundant surrounding `---` separator or trailing blank line if the surrounding structure breaks. Prune-phase apply stays coordinator-serial (no sub-agent dispatch) — prune touches at most a handful of entries per file and the safety bias dominates parallelism gain.

c. **Create bundled follow-up todo** (only if ≥ 1 case picked "Auto-prune + create follow-up todo"): append ONE new entry to `docs/todo_list.md ## Next` with slug like `T-PRUNE-DANGLING-REFS-<YYYYMMDD>`, body listing each dangling ref as a change-manifest bullet (file:line + short context). Update the top `## Index` Next sub-table per `docs/todo_list.md "## File guide → Index maintenance"` rules.

d. **Print apply summary**:

```
PRUNE applied:
- 1 orphan entry deleted (no live refs)
- 1 entry deleted + dangling refs (logged in T-PRUNE-DANGLING-REFS-20260521)
- 1 entry kept (user picked Skip)
SNAPSHOT: <snapshot_root>/<YYYY-MM-DD_HHMMSS>_compress-ai-context-prune/   (default snapshot_root = logs/file_snapshots/)
```

## Step 4.5: Decisions format migration (conditional — Step 1 Q2 = yes)

> **Language**: disk-bound — the rewritten index entries, the archive entries, and any archive skeleton created here land in `content_language` per `ai_context/skills_config.md §Language`. Entry text being MOVED is copied verbatim — never translated, never re-authored.

Runs only when Step 1's probe fired AND the user picked "Yes — migrate". Numbered 4.5: it sits between the prune and compress phases without renumbering Steps 5–9 (cross-doc citations pin those numbers).

a. **Precondition**: `docs/decisions.md` must exist. If absent, stop this step and print `docs/decisions.md missing — run /holo:update first (its --fix lands the archive template), then re-run /compress-ai-context`. Do NOT hand-author the archive skeleton here — template landing is Reconcile's job.

b. **Snapshot**: `take_snapshot(target_root, slug='compress-ai-context-migrate', file_paths=['ai_context/decisions.md', 'docs/decisions.md'])` — once, before any Edit (same snapshot-on-plan-freeze contract as Steps 4a / 7a). The plan is the `<fat_entries>` list from Step 1 — but when the prune phase (Steps 2–4) deleted or edited any `ai_context/decisions.md` entry, re-run the Step 1 probe first and use the refreshed list (the Step-1 freeze predates those edits).

c. **Migrate each fat entry** (coordinator-serial; one entry = one pair of Edits; process in file order):
   - **Move**: append the entry's full text **verbatim** to `docs/decisions.md`, under a theme section matching the entry's section in the index (create the `## <section>` header in the archive if absent, mirroring the index's section order; remove the archive's PROGRESSIVE `_(none yet — …)_` marker on first landing). Keep the entry's number unchanged.
   - **Rewrite**: replace the index entry's body with the 1–2-line index form — decision statement distilled from the entry's first sentence(s) + `→ docs/decisions.md #N` pointer. No fact inversion, no dropped negation; boundaries / measurements / history stay in the archive text only.
   - Entries already in index form (≤ 3 non-empty lines AND pointer present) are untouched even if they sit between fat ones.

d. **Verify before proceeding** (hard gate; any failure → print the failure + jump to Step 8c's rollback ask, scoped to the `_compress-ai-context-migrate/` snapshot from 4.5b instead of the compress snapshot; on rollback, the run continues into Step 5 with the migration undone):
   - Numbering lockstep: the sorted `#N` set of index entries == the sorted `#N` set of archive entries (both from `^N. ` line-starts, HTML comments stripped).
   - No dangling refs: every `decisions.md #N` / `docs/decisions.md #N` reference outside `logs/` resolves in the index.
   - Probe re-run: the Step 1 probe command now returns `[]`.

e. **Print migration summary**:

```
MIGRATE applied:
- <N> entries moved to docs/decisions.md (sections created: <list or none>)
- index rewritten to 1–2-line form; numbering lockstep verified (#min–#max, <count> entries)
SNAPSHOT: <snapshot_root>/<YYYY-MM-DD_HHMMSS>_compress-ai-context-migrate/
```

## Step 5: Compress scan + plan freeze (scatter-gather)

**Trigger** (per file): file > 150 lines OR any single entry > 5 lines. Files matching neither are skipped silently. The thresholds come verbatim from `conventions.md §Compactness Requirements` — the decisions index's own tighter 1–2-line-per-entry target is enforced at write time by `/go` / `/update-docs` and by Step 4.5's migration, NOT re-checked by this scan. Landing-target routing: when a bloated entry lives in `ai_context/decisions.md` (two-tier index form), its compression moves the surplus into the paired `docs/decisions.md` entry (same `#N`; lockstep pair) instead of a `docs/architecture/<topic>.md` landing.

a. **Coordinator pre-scan**: parse each of the 5 ai_context files via `${CLAUDE_PLUGIN_ROOT}/scripts/sentinel_parse.py` (gap-territory only, same as Step 2). Produce a **stable bloated-id list** `bloated_ids = [(file_path, entry_id), ...]` using the thresholds **verbatim from `ai_context/conventions.md §Compactness Requirements`** (entry > 5 lines OR file body > 150 lines — DO NOT raise the thresholds locally "to limit scope"; the coordinator both counts and acts on this list, so any local threshold relaxation trivially defeats the Step 5d coverage invariant on a smaller set). Set `<total_bloated> = len(bloated_ids)`. The list (not just the count) is the union anchor consumed by Step 5d's coverage invariant; entry-id is whatever stable identifier the file's format provides (`decisions.md` #N / `conventions.md §<section>` / `requirements.md` #N / `architecture.md §<section>` / `handoff.md §<section>.<row-label-or-bullet-keyword>`).

b. **Dispatch decision (hard contract — coordinator inline mode is forbidden above threshold)**:
   - `<total_bloated> ≥ 8` → **MUST scatter**: dispatch up to 5 sub-agents in parallel, one per file that has ≥ 1 bloated entry. Each sub-agent receives: (i) its file path; (ii) the gap-territory content; (iii) the §Compactness Requirements contract; (iv) the classification rubric (a)/(b)/(c) below; (v) the language-axes directive at the **tail** of its prompt per `ai_context/conventions.md §Cross-File Alignment` (sub-agent dispatch tail-position rule, decisions.md #16). Sub-agents must read `ai_context/conventions.md §Compactness Requirements` before classifying. The coordinator MAY NOT choose inline mode at this threshold "to save context" or "because I already have the files in scope" — that reasoning is exactly the [decisions.md #19](../../ai_context/decisions.md) anti-pattern (single-pass-incomplete from main-agent context exhaustion) the scatter-gather architecture was introduced to defeat. If the coordinator nonetheless lacks parallel-dispatch capability in its runtime (e.g. a non-Claude harness that cannot fan out sub-agents), it MUST surface that as an explicit one-line declaration `scatter-mode unavailable: <runtime reason>` BEFORE entering inline fallback, so the user can see the deviation and decide. **Valid runtime-reason** = structural unavailability the runtime cannot fix mid-run (e.g. `harness lacks Task/sub-agent dispatch primitive`; `parallel-tool-use disabled in this client`; `sub-agent quota exhausted for this session`). **Invalid runtime-reason** (= disguised coordinator preference; coordinator MUST NOT use these) = `I have all files in context already`; `context budget too tight`; `to save tokens / API cost`; `dispatch is slow`. If the runtime has the primitive at all, scatter is mandatory above threshold — efficiency reasoning is exactly the anti-pattern.
   - `<total_bloated> < 8` → **inline mode permitted**: coordinator runs the per-entry classification serially. No sub-agent dispatch.

c. **Per-entry classification** (executed by sub-agent in scatter mode, by coordinator in inline mode):
   1. **Identify the linked-doc target** — typically the entry's `→` pointer line (`→ docs/architecture/<topic>.md`); or, when the entry has no explicit pointer, grep `docs/` for the entry's key terms to find a plausible existing doc. If no target exists, the new-doc creation case (rare).
   2. **Classify** as:
      - **(a) doc already covers rationale** — the linked doc already documents the design / rationale this entry contains; compression simply removes the duplication, leaving a one-line decision + one-line rationale + pointer in ai_context. Decisions-index carve-out: for `ai_context/decisions.md` entries in the two-tier form, the compressed shape is statement + `→ docs/decisions.md #N` pointer ONLY — the rationale line lands in the paired archive entry, never stays in the index.
      - **(b) rationale needs landing in docs first** — the linked doc exists but does not cover this entry's rationale yet; compression includes a docs/ patch that lands the rationale **then** trims ai_context.
      - **(c) no linked doc exists** — needs a brand-new `docs/architecture/<topic>.md` file; rare; flagged in the plan so user can confirm before `Write`-ing a new file.
   3. **Propose the patch** (does NOT Edit anything in this step) — record the proposed compressed body for ai_context + the proposed docs landing block + the docs target path + classification tag.

d. **Plan merge + docs-landing conflict resolution + coverage invariant** (coordinator-owned, executed after sub-agents return / inline mode collects all proposals):
   - Aggregate all proposals into a single plan: `{proposed_ids: [(file_path, entry_id), ...], proposed_edits: {file_path: [{entry_id, classification, body}, ...]}, deferred_ids: [(file_path, entry_id), ...], deferred: [{file_path, entry_id, rationale}, ...], docs_landings: [{target, classification, body}], new_doc_files: [path]}`. Note `proposed_ids` and `deferred_ids` are flat id-only lists derived from `proposed_edits` / `deferred`, kept alongside for the coverage-invariant union check.
   - **Conflict resolution**: when multiple ai_context entries land rationale into the same `docs/architecture/<topic>.md`, the coordinator owns the merge order and produces a single combined docs Edit for that target (preserving section ordering, deduping overlapping rationale). Sub-agents do NOT see other sub-agents' proposals; conflict resolution is exclusively coordinator-side.
   - **Coverage invariant (hard contract — blocks plan freeze)**: every bloated entry in Step 5a's `bloated_ids` MUST appear in the plan as **either** (i) a compress entry with proposed body in `proposed_edits` **or** (ii) a deferred entry in `deferred` with a one-line rationale. The two id-lists' set union MUST equal `bloated_ids` exactly: `set(proposed_ids) | set(deferred_ids) == set(bloated_ids)` AND `set(proposed_ids) & set(deferred_ids) == ∅` (every id appears exactly once). The coordinator MAY NOT silently drop entries from the plan "to stay safe" or "to limit scope" — every omission must be a `deferred` entry with explicit rationale that the user will see in Step 6. Valid deferred-rationale examples: `entry is self-marked inherently uncompressible per its body text`; `entry already ≤ 5 lines, only marginally over target`; `entry's linked-doc target does not yet exist and creating a new doc is out-of-scope for this round`. Invalid deferred-rationale (= still a coordinator silent-narrow): `entry is large but I want to stay conservative`; `entry's rationale feels load-bearing to me`. If the coordinator believes an entry truly shouldn't be touched, the rationale must name a structural reason, not an aesthetic preference. Plan freeze CANNOT complete until the set-equality + disjointness conditions both hold.
   - **Plan freeze**: by the end of Step 5d, the full set of files to be touched (ai_context source files + docs targets + new doc files + possibly `docs/architecture/README.md` Contents) is fixed AND the coverage-invariant set conditions both hold. This frozen file list feeds Step 7's snapshot call.

e. **Print scan summary to conversation** (replaces the verbose per-entry preview that the prior design printed; full preview is moved to Step 6 in summary form only). The `Total:` line is the `<total_bloated>` Step 5a produced and the same number Step 5d's coverage invariant uses + Step 6's planned/deferred ratio cites — it is the **anchor count** that propagates through the rest of the flow, so it must be printed verbatim (not a smaller "but I'll focus on N" subset):

```
COMPRESS scan:
- ai_context/decisions.md: 8 entries scanned, 3 bloated (2 already-covered / 1 needs-docs-landing)
- ai_context/architecture.md: 4 entries scanned, 1 bloated (1 already-covered)
- ai_context/conventions.md: 6 entries scanned, 0 bloated
- ai_context/requirements.md: 3 entries scanned, 0 bloated
- ai_context/handoff.md: 3 sections scanned, 0 bloated
Total: 4 bloated entries across 2 files (scatter mode: 5 sub-agents dispatched / inline mode)
Scan thresholds used: entry > 5 lines OR file > 150 lines (verbatim from ai_context/conventions.md §Compactness Requirements; coordinator MUST NOT raise these locally)
Docs landings: docs/architecture/section-version-sentinel.md (+rationale block); docs/architecture/smart-merge.md (+rationale block); (NEW) docs/architecture/<topic>.md
```

If `Total: 0 bloated`, skip to Step 8 with a one-line `0 bloated entries found, compress phase no-op` notice.

## Step 6: Simple plan report + single batched ask

**Print a simple plan report** (per-entry one-liner; do NOT print before/after snippets, do NOT print landing-block bodies — the safety net is the snapshot taken at Step 7a + Step 8's multi-axis verify + rollback ask, not pre-confirmation preview). The report's header MUST surface the coverage ratio `<M planned> / <T total bloated> ; <D deferred>` so the user can immediately see whether the coordinator scoped down — `M + D == T` is enforced by Step 5d's coverage invariant; if the printed ratio shows otherwise, the coordinator violated the invariant and the user should reject the plan via the Step 6 ask:

```
COMPRESS plan (<M> planned / <T> total bloated ; <D> deferred — coverage invariant: <M>+<D>==<T>):
  classification breakdown: <X> already-covered / <Y> needs-docs-landing / <Z> new-doc-file
- ai_context/decisions.md:
  - #13 → (a) docs/architecture/section-version-sentinel.md
  - #14 → (b) docs/architecture/smart-merge.md
  - #15 → (a) docs/architecture/section-version-sentinel.md
- ai_context/architecture.md:
  - §Key Boundaries.sentinel-ownership → (a) docs/architecture/section-version-sentinel.md
Deferred (<D> entries — not compressed this round):
- ai_context/decisions.md #19 → "self-marked inherently-uncompressible per entry body"
- ai_context/decisions.md #22 → "already 7 lines, only marginally over ≤ 5 target"
- ai_context/architecture.md §Top-Level Structure → "list of directory bullets, each ≤ 1 line; no rationale to push elsewhere"
Docs landing schedule (coordinator-owned, serial):
- docs/architecture/section-version-sentinel.md — 3 entries (0 need new rationale)
- docs/architecture/smart-merge.md — 1 entry (1 needs new rationale appended)
- (NEW) docs/architecture/<topic>.md — only present if classification (c) appeared
docs/architecture/README.md Contents update: yes / no (yes if any (c))
Snapshot target: <snapshot_root>/<YYYY-MM-DD_HHMMSS>_compress-ai-context-compress/   (default snapshot_root = logs/file_snapshots/, configurable via ai_context/skills_config.md ## File snapshots)
```

Per-entry one-liner format: `<entry-id> → <classification>(a/b/c) <docs-target-path>`. No body text. Deferred entries use a separate one-liner format `<entry-id> → "<rationale>"` — the rationale is visible to the user so silent narrow-scoping cannot hide behind summary numbers. The classification tag is sufficient for the user to spot mis-classification (e.g. an entry tagged (b) "needs docs landing" when the linked doc already covers the rationale); the deferred rationale is sufficient to spot scope-evasion (e.g. a rationale like "feels load-bearing" should be rejected via Tweak per the Step 6 ask).

Ask via **<ask tool>** — one question, three options. **Framing rule**: the recommended option must commit to the full planned set; per-entry deferral is an explicit opt-out the user actively picks via Tweak, never a coordinator-induced default. This reverses the prior framing where "Confirm" meant "accept whatever scope the coordinator chose":

Question: `Proceed with compress plan above? (<M> planned / <D> deferred; review the Deferred list — any rationale that looks aesthetic rather than structural should be rejected via Tweak)`

1. **Compress all <M> planned entries (recommended — coordinator commits to the full planned set)** — proceed to Step 7. Picks up only the entries already in `proposed_edits`; the `<D>` deferred entries stay un-touched per their printed rationale. Picking this option means the user has read the Deferred list and accepts every rationale; deferred entries do NOT count as gate-fail residue in Step 7d.
2. **Tweak — move entries between planned ↔ deferred** — wait for the user's free-form tweak instruction (typical: "promote #19 from deferred to compress, the 'inherently-uncompressible' rationale is no longer valid"; "demote #14 to deferred, the docs landing scope is too invasive"; "re-route entry Y to docs/<other>.md"; "rework entry Z classification (b) → (a) because the rationale is already covered"); coordinator updates the plan, re-validates the coverage invariant (`M + D == T`), re-prints the simple report, re-enters Step 6.
3. **Cancel — drop all compress patches** — abort the compress phase; prune-phase changes (if any) stay landed; skip to Step 8 wrap-up.

The `<ask tool>`'s auto-appended "Other" fallback covers free-form responses (e.g. "apply 1 / 3 / 5, drop 2 / 4"). Option labels stay concise. **Do not regress to per-entry full-preview** — full preview defeats the simple-report contract; users who need to see the proposed body should run `/compress-ai-context`, then inspect the snapshot diff after Step 7 lands and use the Step 8 rollback ask to revert specific entries.

## Step 7: Compress apply (scatter-gather) + completion gate

> **Language**: disk-bound — compress patches (ai_context entry shrinks + docs/ rationale landings + new-doc files) all written in `content_language` per `ai_context/skills_config.md §Language`. Snapshot files are byte-copies of source. Sub-agent prompts dispatched in Step 7b include the language-axes directive at the **tail** of the prompt per `ai_context/conventions.md §Cross-File Alignment` (sub-agent dispatch tail-position rule, decisions.md #16) — reply in `conversation_language`, write disk artifacts in `content_language`.

> **Compactness Requirements**: the compressed ai_context bodies written here follow the universal contract —
> - Shorter is better than longer. Each entry is a summary, not a detail dump.
> - Compactness must not sacrifice accuracy or completeness — never drop important information just to fit the length target.
> - Aim for ≤ 5 lines per entry, and push longer detail to the linked source (`docs/<topic>.md`, schemas, script docstrings).
> - Do not compress or touch content unrelated to the current edit.

a. **Snapshot-on-plan-freeze**: by the end of Step 6 the compress plan is frozen (per-file entry list + docs landing schedule + new-doc files + `docs/architecture/README.md` Contents flag). Before any `Edit`, call `take_snapshot(target_root, slug='compress-ai-context-compress', file_paths=[every ai_context file touched + every docs/ landing target + every new-doc path + docs/architecture/README.md if Contents update is scheduled])` **once**, covering all files in the frozen plan. Not piecemeal per-sub-agent, not piecemeal per-Edit. Snapshot root resolved from `ai_context/skills_config.md ## File snapshots` (default `logs/file_snapshots/`). Capture the returned snapshot dir path for the wrap-up.

b. **Sub-agent apply (parallel, ai_context only)**: dispatch one sub-agent per ai_context file that has ≥ 1 entry in the compress plan (max 5 in parallel; threshold same as Step 5b — scatter mode dispatches sub-agents, inline mode runs Step 7b coordinator-side serially). Each sub-agent receives:
   - Its file path + the exact list of `(entry-id, classification, compressed_body)` triples for that file (from the frozen plan).
   - The §Compactness Requirements blockquote copied verbatim into its prompt.
   - The instruction: **only Edit your assigned ai_context file**; do NOT Edit docs/, README.md, or any file outside your scope. Use one `Edit` per entry (no batched `replace_all`).
   - The language-axes directive at the **tail** of the prompt (reply in `conversation_language`; disk Edits in `content_language`).
   Sub-agents return per-entry success/failure to the coordinator. **Sub-agents do NOT see other sub-agents' files** — there is no cross-agent coordination at this layer.

c. **Coordinator apply (serial, docs / new-doc / Contents)**: after all sub-agents return success, the coordinator applies the docs landing schedule **serially**:
   - For each `docs/architecture/<topic>.md` in the docs landing schedule: one `Edit` appending the combined rationale block produced by Step 5d's conflict resolution (single Edit per docs file regardless of how many ai_context entries land there).
   - For each new-doc path (classification (c)): one `Write` creating `docs/architecture/<topic>.md` with header + rationale body.
   - If any new-doc was created and `docs/architecture/README.md` exists: one `Edit` updating its Contents index, inserting the new entry per the file's existing alphabetical / topical order.
   Serial execution is deliberate — multiple parallel writers on the same docs file would last-writer-wins; serialization is the simplest correct path and docs edits are cheap.

d. **Completion gate (re-scan + residue classification)**: re-run the Step 5 trigger check across the 5 ai_context files (file > 150 lines OR any single entry > 5 lines). If any bloated entry remains, **classify each residual against Step 6's frozen `deferred` list** (the list the user saw + approved at Step 6 ask option 1):
   - **deferred-by-design**: residual entry-id appears in Step 6's `deferred` list. The user already saw + accepted its rationale at Step 6. This is **NOT a gate failure** — print one line `residue: <N> entries deferred-by-design per Step 6 plan (acceptable):` followed by the list, then continue to wrap-up. Does not block Step 8.
   - **missed-by-coordinator**: residual entry-id is NOT in Step 6's `deferred` list — meaning it was in `proposed_edits` (user expected it to be compressed) but the Step 7b sub-agent / coordinator apply failed to actually shrink it below the 5-line / 150-line trigger. This IS a hard gate failure. Print `COMPRESS completion-gate FAILED — <N> entries planned but not compressed:` followed by the residual list (file:entry-id + reason: file-still-too-long / entry-still-too-long + which sub-agent / Edit was responsible if known). The user can choose: (i) re-run `/compress-ai-context` (will pick up the residue); (ii) accept the residue (acknowledging the apply phase under-delivered, the entry stays bloated until next round); (iii) roll back via Step 8's rollback ask.
   - **Why split**: the previous unified "any residue = FAIL" framing made it impossible to distinguish "user-approved deferral" from "coordinator silently dropped the entry from the apply phase" — both surface the same way, so the FAIL became background noise and gate-fail messages got dismissed as "by-design" even when they weren't. Splitting at this gate is the structural counterpart to Step 6's `deferred` list invariant: the same list governs both "what the user agreed to skip" (Step 6) and "what counts as acceptable residue here" (Step 7d).
   - This gate exists because the original single-agent design exhibited "compress only a small subset per invocation" behavior; the scatter-gather + completion gate combo is the architectural answer to that pain point.

e. **Print apply summary**:

```
COMPRESS applied:
- 6 entries compressed across 4 ai_context files (sub-agents: 4 dispatched, 0 failed / coordinator inline)
- 4 docs/ landings (3 appended to existing files, 1 new file: docs/architecture/<topic>.md)
- docs/architecture/README.md Contents updated: yes / no
Completion gate: ✓ no residue / ✓ <N> deferred-by-design (acceptable) / ✗ <N> missed-by-coordinator (hard FAIL — see list above)
SNAPSHOT: <snapshot_root>/<YYYY-MM-DD_HHMMSS>_compress-ai-context-compress/   (default snapshot_root = logs/file_snapshots/)
```

## Step 8: Multi-axis verify + rollback ask + wrap-up

> **Language**: user-facing — render verification result lines (✓ / ✗ per axis), the rollback `<ask tool>` prompt + option labels, the wrap-up summary, and the reminder to `/commit` in `conversation_language` per `ai_context/skills_config.md §Language`. Structural prefixes (`✓`, `✗`, `SNAPSHOT:`, file paths, `axis:`) stay English; only summary prose translates.

> **Language (sub-agent dispatch)**: sub-agents spawned in Step 8b receive the language-axes directive at the **tail** of their prompt per `ai_context/conventions.md §Cross-File Alignment` (sub-agent dispatch tail-position rule, decisions.md #16) — reply in `conversation_language`; no disk writes expected from verify sub-agents (they are read-only by contract).

### a. Scripted fast-fail (always runs)

These checks are cheap and deterministic; any failure here means the apply phase broke something structural and the user should likely rollback before proceeding.

1. **Sentinel integrity**: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sentinel_parse.py" --self-test` (12-group regression). Failure → flag `axis: sentinel — script self-test FAILED`.
2. **Sentinel parse on touched files**: for each ai_context file touched by this run, re-parse via `${CLAUDE_PLUGIN_ROOT}/scripts/sentinel_parse.py`'s `parse(path)`; failure → flag `axis: sentinel — <path> parse FAILED`. The Edits in Step 7 are confined to gap-territory so this should not break sentinels; if it does, something went wrong.
3. **Drift sanity**: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/holo_update_check.py" --plugin-root "${CLAUDE_PLUGIN_ROOT}" --target . --json` produces a JSON dict where every finding-category list is empty (`agents_sync.stale/missing/orphan/asset_orphan = []`, `missing_template = []`, `missing_section = []`, `missing_field = []`, `gitignore_missing_lines = []`, `claude_agents_lang_drift = []`, `missing_l1_directive = []`, `l1_directive_drift = []`, `lang_mirror_drift = []`, `legacy_skip_marker = []`, `decisions_fat_format = []`, `sentinel_layout_drift = []`). Any non-empty list → flag `axis: drift — <category>: <N> findings` with the JSON snippet. Exception: `decisions_fat_format` non-empty when Step 4.5 did not run to completion this round (user declined at Step 1 Q2, or the Step 4.5a precondition stopped it) is expected and does NOT count as a verify failure — note it in the Step 8d wrap-up (one line: `decisions_fat_format: <N> entries remain unmigrated (migration declined/skipped)`); when Step 4.5 DID complete, also carry its Step 4.5e migration summary into the wrap-up. (The no-arg invocation is the script's check mode; `--fix` enables the auto-fix branch — this skill does NOT pass `--fix` here.)
4. **Import sanity**: `python3 -c "import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts'); import holo_update_check; import sentinel_parse"` exits 0. Failure → flag `axis: import — <error>`.
5. **External-reference sanity** — for each pruned `decisions.md` entry, grep the repo (excluding `logs/` + `docs/todo_list_archived.md`) for `decisions.md #N` references where `N` is the deleted entry's number; flag any that now point at a non-existent entry. (Compress preserves numbers — this is empty for compress-only runs; prune with "leave dangling refs" picked produces expected flagged refs that DO NOT count as a verify failure.)

Any failure in scripts 1–4 → print the failure summary and jump directly to the **rollback ask** in Step 8c without dispatching the LLM sub-agents (their work is moot if the apply phase is structurally broken).

### b. LLM multi-axis verify (parallel sub-agents)

**Scope**: compress-phase entries only; prune-phase deletions are covered by Step 8a's external-ref grep (#5). The three axes below (semantic preservation / information density / compactness compliance) are defined for *compressed* entries — they have no meaning on deleted entries, so prune-phase changes do not enter this LLM verify.

**Threshold**: dispatch when `compress entries ≥ 5`. Below that, the coordinator runs the three LLM checks inline serially (small-batch overhead from sub-agent dispatch outweighs parallelism gain).

Three sub-agents dispatched in parallel, each read-only (no Edits, no Writes). Each sub-agent receives:
- The snapshot dir path (`<snapshot_root>/<...>_compress-ai-context-compress/`; `<snapshot_root>` resolved per `ai_context/skills_config.md ## File snapshots`, default `logs/file_snapshots/`).
- The current state of the ai_context + docs files touched this round.
- The §Compactness Requirements blockquote.
- The language-axes directive at the **tail** of its prompt.

**Sub-agent 1 — semantic preservation**: read snapshot copy of each touched ai_context file + current state. For each compressed entry, judge: did the compression drop any fact / constraint / decision / rationale that is NOT now reflected in either (a) the linked docs target or (b) the surviving compressed body? Flag any drop as `axis: semantic — <file>:<entry-id> dropped: <quote of dropped content>`.

**Sub-agent 2 — information density**: read current state of touched ai_context entries. For each compressed entry, judge: is the body over-compressed to the point of losing actionable meaning (e.g. shrunk to "see docs" with no decision summary, or a single sentence too abstract to navigate)? The contract is `≤ 5 lines aim`, NOT `1 line ceiling` — compression that ABSTRACTS without LANDING the rationale to docs is over-compression. Flag: `axis: density — <file>:<entry-id> over-compressed: <reason>`.

**Sub-agent 3 — compactness compliance**: read current state of touched ai_context entries against `ai_context/conventions.md §Compactness Requirements` 4 rules + the §Format pointer requirement + `docs/architecture/<topic>.md` existence + section presence. For each compressed entry, judge: (i) does the entry end with a `→ <pointer>` line? (ii) does the pointer target exist? (iii) if the pointer names a section (`→ docs/architecture/<topic>.md §<section>`), does that section exist in the target? Flag: `axis: compliance — <file>:<entry-id> <which-rule-failed>`.

Coordinator aggregates the three sub-agent reports into a single findings list.

### c. Rollback ask (only when any axis flagged)

If steps a–b produced **any** flagged finding (including expected dangling-refs from prune option 2; the user still gets to decide acceptance):

Print the consolidated findings list, grouped by axis, then ask via **<ask tool>** — one question, three options:

Question: `<N> verification findings flagged across <M> axes. How to handle?`

1. **Accept — keep changes as-is, warning only (recommended when findings are intentional / minor)** — the round stays landed; flagged findings echoed in the wrap-up summary as warnings; user follows up later if needed.
2. **Partial rollback — restore specific entries from snapshot** — wait for the user's per-entry instruction (e.g. "rollback decisions.md #14 + #15"); coordinator `cp` the specified entries' enclosing files from the snapshot dir back to the working tree, refreshing the affected files entirely (snapshot copies the whole file, not entry-level). Print which files were restored. After partial rollback, re-run **Step 8a scripted fast-fail only** (cheap re-validation) to confirm no new structural break; if scripted checks pass, proceed to wrap-up; if they fail, surface the failure and let the user decide.
3. **Full rollback — restore all touched files from snapshot** — `cp` the entire snapshot dir contents back over the working tree (or use the snapshot helper's restore primitive if one exists); the compress phase is effectively reverted. Prune-phase changes (if any) stay landed — they have a separate snapshot. Print `COMPRESS phase fully rolled back from snapshot <path>`. Skip directly to the wrap-up.

**No-findings path**: if both 8a and 8b are clean, print `✓ all verification axes clean` and proceed directly to wrap-up (no ask needed).

### d. Wrap-up

```
✓ /compress-ai-context complete.
Prune: <N> pruned / <M> kept / <K> skipped (snapshot: <path>)
Compress: <X> entries compressed across <Y> files (snapshot: <path>)
Completion gate: ✓ no residue (or: ✗ N residual — see Step 7d list)
Verify: <V> axes checked, <F> findings flagged (action: accept / partial rollback <files> / full rollback)
Follow-up todo: T-PRUNE-DANGLING-REFS-<YYYYMMDD> (if any prune case picked option 1)
```

If `prune phase = no-op` (Step 1 = no, or Step 2 = 0 stale) AND `compress phase = 0 findings` (Step 5 found nothing bloated), print one line `nothing to do — ai_context is within the compactness contract` and stop without snapshots (skip Step 9 too — mark its progress entry directly `completed`).

Do not enter `/go` or invoke any skill other than the user-confirmed `/commit` handoff in Step 9.

## Step 9: Commit ask

**Skip wholesale** (mark progress-tool entry directly `completed` + print one line `Step 9 skipped (reason: no on-disk changes)`) when the run produced no on-disk changes — i.e. Step 8d wrap-up hit the "nothing to do" branch, OR Step 8c chose Full rollback. Partial rollback still leaves some changes landed, so Step 9 still runs.

Ask via **<ask tool>** — one question, two options:

Question: `Commit the changes from this round?`

1. **Yes — invoke /commit (recommended)** — hand off to `/commit`; it handles staging, split-by-logical-unit, and message style per project convention.
2. **No — leave changes unstaged** — print one line `Changes left in working tree; run /commit when ready.` and stop.

This is the only commit handoff; no push regardless of answer.

## Constraints

- **No push** — commit is opt-in via Step 9's user-confirmed `/commit` handoff; this skill never pushes.
- **No touching code / schema / `.gitignore` / `plugin.json` / `logs/` / `templates/`** — out of scope; touches limited to `ai_context/*.md` + `docs/architecture/<topic>.md` (+ `docs/architecture/README.md` Contents when a new doc is created) + `docs/decisions.md` (Step 4.5 migration target + Step 5/7 index-entry compression landings) + `docs/todo_list.md` (only when "Auto-prune + create follow-up todo" was picked).
- **Sentinel-block protection is load-bearing** — every parse goes through `${CLAUDE_PLUGIN_ROOT}/scripts/sentinel_parse.py`; this skill operates only on gap-territory content. Sentinel-bearing blocks are plugin-canonical (owned by `/holo:update`); editing them is out of scope. Step 8a re-parses every touched file to catch any accidental sentinel break.
- **Snapshot-on-plan-freeze, not snapshot-on-apply** — `take_snapshot` is invoked once per phase, **after that phase's plan is frozen (end of Step 3 for prune; end of Step 6 for compress) and before any `Edit`**, covering all files in the frozen plan in a single call. Skill startup does NOT snapshot. Sub-agents in Step 7b do NOT call `take_snapshot` — the snapshot precedes their dispatch.
- **Coordinator owns shared-file writes** — sub-agents (Step 5b scan / Step 7b apply) write only to their assigned ai_context file. Docs / new-doc / `docs/architecture/README.md` Contents writes are coordinator-serial in Step 7c. This is a load-bearing invariant against parallel-writer races on shared docs targets.
- **Sub-agents do NOT call `take_snapshot` and do NOT write to shared files** — Step 5b scan sub-agents, Step 7b apply sub-agents, and Step 8b verify sub-agents are all forbidden from invoking `take_snapshot` (snapshot is coordinator-driven at the end of each phase's plan-freeze, in Step 4a / Step 7a) and from writing to shared files (`docs/`, `README.md`, `docs/architecture/README.md`, etc.). Step 7b sub-agents write only to their assigned ai_context file; Step 8b sub-agents are read-only by contract.
- **Completion contract: compress Step 7d re-scan + residue split** — canonical statement in Step 7d. In one line: re-run the Step 5 trigger after apply; residue matching Step 6's `deferred` list = deferred-by-design (`✓`, acceptable), residue not matching = missed-by-coordinator (`✗`, hard FAIL).
- **Scatter-mode hard contract above threshold** — `total_bloated ≥ 8 → MUST scatter`; coordinator inline mode at/above threshold is forbidden (the [decisions.md #19](../../ai_context/decisions.md) anti-pattern). Canonical statement + valid/invalid runtime-reason taxonomy + the `scatter-mode unavailable: <runtime reason>` fallback in Step 5b.
- **Plan coverage invariant** — canonical statement in Step 5d: every id in `bloated_ids` is either compressed or deferred-with-rationale; `set(proposed_ids) | set(deferred_ids) == set(bloated_ids)` AND `set(proposed_ids) & set(deferred_ids) == ∅` block plan freeze. Scan thresholds taken verbatim from `conventions.md §Compactness Requirements`; coordinator may NOT raise them locally to shrink `bloated_ids`.
- **Step 6 ask framing** — recommended option must commit to the full planned set (`Compress all <M>`); per-entry deferral is an explicit opt-out the user picks via Tweak. The coordinator MAY NOT default the user toward accepting a narrowed plan; the deferred list is always visible.
- **No batched confirm for stale + no live refs** — the safety net is the snapshot + Step 8 verify + rollback ask, not user pre-confirmation. The only ask in the prune phase is the per-case 3-option ask for `stale + has live refs`. The only ask in the compress phase is the Step 6 simple-plan 3-option ask + the conditional Step 8c rollback ask.
- **No per-entry preview in Step 6** — the safety net is the snapshot + Step 8 multi-axis verify + rollback ask, not preview-then-confirm. Step 6 prints a simple plan report (per-entry one-liner: id + classification + docs target) without body content. Reverting to full per-entry preview is a contract regression.
- **Sub-agent dispatch thresholds** — Step 5/7 scatter mode requires `total_bloated ≥ 8`; Step 8b multi-axis verify requires `compress entries ≥ 5`. Below these, the coordinator runs the phase inline serially. Thresholds exist to avoid dispatch overhead on small jobs.
- **No numbering check / no auto-reorder** — `decisions.md` global-append-only numbering is enforced by `decisions.md §Format` rule text only; this skill does not validate, fix, or rearrange numbers. Sole exception: Step 4.5d's migration gate verifies index ↔ archive numbering-set equality (it moves entries between the pair, so lockstep verification is part of its own contract) — it still never renumbers.
- **Migration moves verbatim** — Step 4.5 copies entry text into `docs/decisions.md` unchanged (no re-authoring, no translation, no summarizing of the archive side); only the index side is distilled. Numbers never change; entries already in index form are untouched; a declined migration is skipped for the whole run (no re-ask).
- **Compactness contract is owned by `conventions.md §Compactness Requirements`** — this skill body MUST NOT re-author the rules. Edits to the contract rule itself happen via `/go` editing `conventions.md`, not via this skill.
- **No fan-out / no PRE-POST log** — auditing of cross-file alignment is `/full-review`'s job. `logs/change_logs/` is `/go`-only. The Step 8 multi-axis verify is THIS round's verify (scoped to the touched file set), not a cross-repo review.
