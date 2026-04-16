# Key Decisions

Decisions already embodied in `docs/architecture/` or `simulation/` are not
repeated here. This file records only the non-obvious rules and constraints
that a new AI should know beyond what the architecture docs already say.

## Roleplay Philosophy

1. The priority is deep behavioral and decision consistency, not surface voice
   imitation. The chain is: memory/relationship → psychological reaction →
   behavior decision → language realization.
2. Objective fact and subjective character cognition must be separated.
   Characters may misunderstand, conceal, or distort things.
3. Time-stage differences must be preserved. A character must not be flattened
   into a timeless static profile.

## Data Separation

5. User data must be stored separately from canonical character data. User
   drift never pollutes character canon.
6. World data is a first-class layer, not hidden inside character notes.
7. World materials are living canon assets — later chapters may revise them.
   Only source-text evidence may revise canonical world data; user
   conversations must not.
8. Conflicts, revisions, and contradictions must be recorded explicitly, not
   silently overwritten.

## Work Scope

9. Each novel is an independent namespace (`work_id`). User flow chooses work
   before character.
10. For Chinese works, `work_id`, entity names, identifier values, and
    generated path segments should all default to Chinese.
11. `ai_context/` remains English as the AI handoff layer. JSON field names may
    remain English.

## Character Depth Dimensions

12a. `identity.json` carries two cross-story fields beyond static bio:
    `core_wounds` (root psychological traumas with origin and behavioral
    impact) and `key_relationships` (relationship arcs with initial state,
    evolution summary, turning points). These are loaded at runtime
    alongside the stage snapshot.
12b. `behavior_state` separates `core_goals` (rational, re-prioritizable
    targets) from `obsessions` (irrational fixations tied to trauma or
    emotion, not subject to cost-benefit reasoning). `emotional_baseline`
    mirrors the same split with `active_goals` + `active_obsessions`.
12c. `character_arc` in stage_snapshot provides a bird's-eye view from
    stage 1 to the current stage (arc_summary, arc_stages key nodes,
    current_position). Complements `stage_delta` which covers only the
    previous-to-current change.

## Extraction

12. stage (extraction) = stage (runtime), 1:1. "Stage" is the pipeline
    term; "stage" is the content/runtime term. Both kept for clarity.
    Stages are split by natural story boundaries during the analysis phase.
    Each stage may have a different chapter count (target 10, min 5, max 15).
    Stage N = stage N candidate. Stage N is cumulative through 1..N.
13. Once active characters are confirmed, Phase 2.5 produces world foundation
    and all character baselines (identity.json, manifest.json, voice_rules.json,
    behavior_rules.json, boundaries.json, failure_modes.json) from full-book
    context as skeleton drafts. Then **1+N split extraction** per stage: one
    world call, then N parallel character calls. All stages may correct any
    existing baseline. Targeted character supplement only when gaps remain.
14. Any stage may revise any already-written asset across the whole work
    package, not only the current target.
15. Do not generate per-stage report files. Update progress files in-place.
16. `target_voice_map` (voice_state) and `target_behavior_map`
    (behavior_state) are parallel structures mapping specific targets to
    voice/behavior differences. Only main characters and important supporting
    characters require detailed entries (at least 3-5 examples each);
    generic types (strangers, passersby) are brief or omitted — LLM can
    infer from overall personality. Important characters use concrete names
    (e.g. "角色名（真面目）"), not generic types. At runtime, only entries
    matching the user's role are loaded. Fallback: if the current stage
    snapshot lacks a matching entry (character absent for several stages),
    the engine scans backwards through previous stage snapshots — pure
    code-level file I/O before the LLM call, no extra LLM invocation.

## User Model

17. One `user_id` = one locked work-target-counterpart binding. Setup locks
    after initial creation; changes require new package or explicit migration.
18. Canon-backed user-side roles inherit the target stage by default.
19. Session/context state updates continuously. Long-term profile and
    relationship core update only after explicit merge confirmation.
20. Context-level `character_state.json` tracks real-time character changes
    (mood, personality, voice, agreements, relationship delta, events,
    memories). These are promoted to long-term layers only at merge.
21. Merge is append-first. Events and memories are added, never overwritten.
22. Session close is explicit (exit keyword or close intent). System then asks
    about merge.
23. Full transcripts stay local; startup loads summary layer only.

## Automated Extraction

24. Each phase step (summarization chunk, analysis, baseline production, stage
    extraction) is a fresh `claude -p` call with no shared session memory.
    Context between steps is entirely file-based.
24a. Extraction prompts do NOT read `simulation/contracts/baseline_merge.md`,
    `memory_digest.jsonl`, `world_event_digest.jsonl`, or
    `stage_catalog.json`. The self-contained snapshot contract is embedded
    directly in the extraction prompt. `memory_digest.jsonl`,
    `world_event_digest.jsonl`, and `stage_catalog.json` are maintained
    programmatically by `post_processing.py` (0 token, idempotent).
25. Three-layer quality check per stage: programmatic validation (free) +
    per-lane semantic review (independent LLM agent) + commit gate
    (programmatic cross-consistency). Only semantic errors cause FAIL.
25a. Parallel review lanes (审校通道): after extraction + post-processing,
    world and each character get independent validate → review → fix
    pipelines running in parallel. Each lane's reviewer has narrowed input
    (only its own files + schema + programmatic report; character lanes
    also read world snapshot for cross-consistency). Targeted fix input
    is similarly narrowed (no full chunk summaries by default).
25b. Commit gate (提交门控): programmatic (0 token) check after all lanes
    pass. Scope is **structural + identifier level only** — snapshot file
    existence, `stage_id` field alignment, catalog/digest entry coverage,
    plus a warn-only cross-entity reference resolution (names in world
    `relationship_shifts` / `character_status_changes` should resolve via
    world cast or active character aliases; unresolved → warning, not
    failure). Content-level world-vs-character conflicts are the character
    lane semantic reviewer's job, not the gate's. Memory digest check
    parses the stage from `memory_id`'s `M-S{stage:03d}-` prefix — the
    schema forbids a `stage_id` field on digest entries. Each gate finding
    is emitted as a `GateIssue(message, severity, lane_type, lane_id,
    category)` so the orchestrator can route recovery the same way it
    routes review failures (see 25c). Gate failures cascade by category:
    `catalog_missing` / `digest_missing` (in `POST_PROCESSING_RECOVERABLE`)
    → free post-processing rerun + re-gate; `snapshot_missing` /
    `snapshot_stage_id` / `snapshot_parse` / `lane_review` → lane
    re-extraction consuming the same `lane_retries` budget as review
    failures AND as initial-extraction lane errors (see 25c.1);
    unattributed structural issues or exhausted budget →
    full-stage rollback. Lane-retry budget is shared across initial
    extraction, review, and gate paths and cleared only after the gate
    finally PASSes — pre-gate clearing would let a stage ping-pong the
    quota indefinitely. Re-extraction LLM failures inside the cascade
    are not escalated to a full rollback; they leave the snapshot
    missing on disk and the next iteration catches it via the gate's
    `snapshot_missing` path, naturally consuming another quota slot.
    No per-lane commit: the gate requires all lanes pass before git commit.
25b.1 Commit ordering: `git commit` first; only a non-empty SHA transitions
    the stage to `COMMITTED`. Empty SHA (no diff or commit failure) reverts
    the stage to `FAILED` so resume can retry. Avoids "progress says
    committed, git has no object" drift.
25b.2 `--end-stage` has strict prefix semantics: Phase 3.5, squash-merge
    prompt, and Phase 4 only run after **all** Phase 3 stages commit. A
    prefix run exits with a "re-run without --end-stage to finalize"
    message.
25b.3 `jsonschema` is a HARD automation dependency (declared in
    `automation/pyproject.toml`). Validator raises ImportError on load if
    missing, rather than silently degrading the gate.
25c. Failure triage — **lane-independent retry first, full rollback last**.
    Inside a lane: Level 0 schema autofix → Level 1 programmatic
    validation → Level 2/3 targeted LLM fix. If the lane still FAILs
    (or hits a systemic issue — file missing, structural,
    understanding-level), roll back only that lane's products and
    re-extract only that lane (≤ `lane_max_retries`=2). Previously
    PASSED lanes are preserved on disk. After any lane re-extraction
    we re-run post-processing (idempotent upsert) and re-review all
    lanes (cross-dependency: world reviewer reads character
    memory_timelines; character reviewers read world snapshot).
    Full-stage rollback is triggered only when a failing lane
    exhausts its lane quota — at that point the stage transitions to
    FAILED and enters the stage-level retry loop (≤ `max_retries`=2).
25c.1 Initial-extraction lane errors (Step 2 — the 1+N parallel agents)
    follow the same lane-attributed model: a single lane's LLM error
    no longer triggers a full-stage rollback. The successful lanes'
    outputs stay on disk, only the failed lane's partial products are
    cleaned via `rollback_lane_files`, and only that lane is
    re-submitted on the next round — consuming the same `lane_retries`
    budget. Full rollback fires only when a lane exhausts the budget.
    This unifies the retry model across initial extraction, review,
    and gate paths.
26. Extraction runs on a dedicated git branch. Each passing stage is committed.
    Rollback on failure = git reset. After all stages complete, squash-merge
    to main (one clean commit); the extraction branch can then be deleted.
27. Stage boundaries should follow natural story arcs (min 5, max 15, default
    10 chapters). stage_id should be a meaningful Chinese name.
28. The orchestrator pre-computes the file read list for each call (world /
    character). Only the most recent snapshot and memory_timeline are included
    (not full history). `memory_digest.jsonl`, `world_event_digest.jsonl`,
    `stage_catalog.json`, and `baseline_merge.md` are excluded from the read
    list. Agents should not explore freely.

## Memory System and Retrieval

29. Three-layer memory: stage_snapshot (aggregated state, current stage only),
    memory_timeline (subjective process per event, first-person summary),
    scene_archive (original text split by scene). No separate dialogue corpus.
30. memory_timeline entries include `memory_id` (pattern `M-S###-##`),
    `time`, `location`, `scene_refs` (linking back to scene_archive),
    `event_description` (150–200 字 objective narration, hard gate),
    `digest_summary` (30–50 字 independently written, hard gate — the
    1:1 source of memory_digest), `subjective_experience` (unbounded,
    first-person with psychological detail and causal reasoning). Entry
    count controlled by importance filtering.
31. scene_archive entries use `scene_id` (pattern `SC-S###-##`) plus
    `time`, `location`, `characters_present`, `summary`, `full_text`,
    `chapter`, `stage_id`. Work-level asset, not per-character. One
    scene never crosses a chapter boundary. `stage_id` is **authoritative
    from `stage_plan.json`** — scene_archive.jsonl is fully
    regenerated on each merge; per-stage seq counter guarantees unique
    IDs.
32. Startup loads: memory_timeline recent 2 stages (N + N-1) full text;
    `memory_digest.jsonl` stage 1..N (~30-40 tokens/entry:
    `{memory_id, summary 30–50, importance, time?, location?}` — stage
    encoded in `M-S###` prefix for loader filtering; summary copied 1:1
    from memory_timeline `digest_summary`); scene_archive
    full_text for the most recent `scene_fulltext_window` scenes
    (**default 10**; configurable via `load_profiles.json`). Scene
    **summaries are NOT loaded at startup** — they live in FTS5 and
    surface on demand. Identity is loaded with a field whitelist
    (strips `evidence_refs` and large nested evidence arrays at load
    time; no schema change, no Phase 2/2.5 rerun required). Vocab
    dict into jieba. FTS5 covers distant memory and scene retrieval;
    no separate embedding needed for memory_timeline.
33. Two-level retrieval funnel:
    Level 1 (default, <20ms): jieba segmentation + work-level vocab dict
    matching + FTS5 query → top-K summaries injected into main LLM prompt.
    No match = no retrieval. LLM judges relevance itself.
    Level 2 (fallback, 200-300ms): LLM calls `search_memory` tool (tool use)
    → engine runs embedding search on summary vectors → second LLM call.
    Rare. No separate vector DB — single SQLite file with optional embedding
    BLOB column.
34. When simulating character A, only load scenes where A is in
    `characters_present` and A's own memory_timeline. Do not load other
    characters' memories or scenes where A is absent.
35. Phase 3.5 (cross-stage consistency check) runs after all Phase 3 stages
    commit. Primarily programmatic (zero tokens) with optional LLM
    adjudication only for flagged items. Errors block Phase 4. This catches
    cross-stage drift that per-stage validation cannot detect (e.g. alias
    mismatches, relationship discontinuity, digest correspondence gaps).
36. scene_archive is produced in Phase 4, independent from Phase 3 (only
    requires `stage_plan.json` from Phase 1 — treated as the
    authoritative stage-id source). Per-chapter LLM calls output scene
    boundary annotations; program extracts full_text from source.
    Parallel execution (`--concurrency`, default 10). Programmatic
    validation only (no semantic review). `scene_id` format:
    `SC-S{stage:03d}-{seq:02d}` (e.g. `SC-S003-07`), with per-stage
    seq counter; supports up to 999 stages × 99 scenes/stage.
37. Retrieval artifacts (fts.sqlite, scene_archive.jsonl) live under
    `works/{work_id}/retrieval/` and are not committed to git (.gitignore).
    Intermediate Phase 4 splits under
    `works/{work_id}/analysis/scene_splits/`. Lightweight
    indexes and vocab dict go to `works/{work_id}/indexes/`.
38. Proactive character association: engine extracts context-state keywords
    (current location, recent events, emotion, conversation partner) for
    jieba matching each turn — not just user input. This widens the FTS5
    candidate pool so the character can naturally recall related memories
    without being asked. LLM decides whether to mention a memory.
39. Vocab dict (work-level, jieba custom dictionary format) is auto-generated
    from extraction output. Contains character names/aliases, locations,
    techniques, event keywords. Stored at
    `works/{work_id}/indexes/vocab_dict.txt`, committed to git.

## JSON Repair

40. LLM-produced JSON frequently contains format errors (unescaped inner
    quotes, trailing commas, truncation) while content is intact. Use the
    three-level repair pipeline before re-running: L1 programmatic regex
    (zero tokens) → LLM repair on broken JSON only (minimal tokens) →
    L3 full re-run (last resort). See `automation/persona_extraction/
    json_repair.py`.

## Resilience

40a. Phase 4 uses an independent PID lock (`.scene_archive.lock`), allowing
    it to run in parallel with Phase 3 (`.extraction.lock`). Phase 4 does
    not perform git operations and has no data dependency on Phase 3 output.
40b. Fast empty failures (CLI exit code ≠ 0, duration <5s, empty stderr)
    are retried with exponential backoff (30s → 60s → 120s) in
    `run_with_retry`. This prevents wasted rapid-fire retries when the
    CLI itself fails to launch.
40c. Phase 4 `_run_parallel` includes a global circuit breaker: if ≥8
    failures occur within a 60s window, all workers pause for 180s before
    resuming. This prevents failure storms under systemic issues.
40d. Phase 4 intermediate state (`.scene_archive.lock` and
    `works/{work_id}/analysis/scene_splits/`) **must not be
    git-tracked**. They are in `.gitignore`; if an extraction branch
    already tracks them, `git rm --cached` is required. Without this,
    `git checkout -- .` during Phase 3 rollback restores tracked splits
    to their last committed version, silently destroying newer split
    files. Phase 3 rollback also excludes them from `git clean -fd`.
40e. All progress files self-heal against on-disk artifacts on every
    startup via `reconcile_with_disk()` (Phase 0 chunks, Phase 3 stages,
    Phase 4 chapters). Three rules: (1) terminal state + missing
    artifact → revert to PENDING; (2) PENDING + on-disk artifact →
    purge artifact (treated as incomplete partial run); (3) any
    intermediate state → purge artifact + revert. Phase 3 additionally
    verifies `committed_sha` is reachable via `git cat-file -e`; sha
    lost to reset/rebase is treated as missing artifact. Guards against
    file loss, manual cleanup, partial writes, and history rewrites.
40e2. Phase 3 and Phase 4 share the same retry contract: FAILED items
    auto-retry within the same run (no manual resume needed); all
    failure paths increment retry_count; exceeded max_retries → ERROR
    (blocked). `--resume` resets ERROR to pending with retry_count=0.

## World Snapshot and Catalog

40f. World `stage_snapshot` records only **current stage** events via
    `stage_events` (**single source of truth, each entry 50–80 字, hard
    schema gate**). `stage_events` is world-public only — personal
    thoughts, private episodes, and inner decisions belong in the
    relevant character's `memory_timeline`, not here. It is the direct
    source for `world_event_digest.jsonl` (1:1 mechanical copy);
    cross-stage timeline lives in `world_event_digest.jsonl`.
    `evidence_refs` is a chapter number list (e.g. `["0001", "0002"]`).

40g. `world_event_digest.jsonl` accumulates world events across stages.
    Programmatic: `post_processing.py` reads `stage_events` from world
    stage snapshot → generates digest entries
    `{event_id (E-S###-##), summary 50–80, importance, time?, location?,
    involved_characters?}` (0 token, idempotent; summary is a 1:1 copy
    of the source `stage_events` entry, so world-vs-character boundary
    is enforced at write time in the extraction prompt + world review
    lane, not here). 5-level importance inferred by keyword
    (trivial/minor/significant/critical/defining), defaulting to
    significant. Runtime loads stage 1..N filtered; stage is parsed
    from `event_id` prefix. `stage_catalog.json` is demoted to
    bootstrap stage selector only (not loaded at runtime).

40h. Character `stage_snapshot.stage_events` holds **only this stage's**
    events, not accumulated history. Each entry 50–80 字 (hard schema
    gate). Cross-stage history is carried by `memory_timeline` +
    `memory_digest.jsonl` + `world_event_digest.jsonl`, not the
    snapshot.

40i. ID convention: `{TYPE}-S{stage:03d}-{seq:02d}` for memory_digest
    (`M-`), world_event_digest (`E-`), scene_archive (`SC-`). 3-digit
    stage supports ≤999 stages; 2-digit seq supports ≤99 per stage. Stage
    is encoded in the ID — digest/archive entries carry no separate
    `stage_id` field; the runtime loader filters via regex `S(\d{3})`.
    Story-time field is named `time` across scene_archive,
    memory_timeline, and digest entries.

40g2. `fixed_relationships.json` in `world/foundation/` records structural
    bonds (blood, lineage, faction membership) that are not stage-dependent.
    Phase 2.5 produces a skeleton; subsequent stages may correct it.
    Loaded at runtime as Tier 0 alongside `foundation.json`.

40h. Smart resume: if a stage is PENDING but extraction output already
    exists on disk (world + all character stage_snapshots), the
    orchestrator skips LLM extraction and jumps directly to
    post-processing. Saves tokens when a stage errored after producing
    output (e.g. crash during post-processing or review). Detection:
    `_extraction_output_exists()` in orchestrator.

## Repository

41. Keep the repo lightweight. Do not commit novels, databases, indexes, large
    artifacts, or real user packages.
42. `works/*/analysis/` and `works/*/indexes/` are git-tracked as
    canonical work assets.
43. `docs/logs/` is write-mostly historical. Do not proactively read.
44. `prompts/` contains only manual-scenario prompts (ingest, review,
    supplement, cold start). Extraction prompts live in
    `automation/prompt_templates/`; runtime LLM behavior rules live in
    `simulation/prompt_templates/`. Each module is self-contained.
45. `automation/` and `simulation/` each have their own `prompt_templates/`
    directory. Neither depends on `prompts/`.
