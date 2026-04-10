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
3. Explicit canon and reasonable inference must be labeled separately.
4. Time-stage differences must be preserved. A character must not be flattened
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
12b. `behavior_state.core_drives` is split into `core_goals` (rational,
    re-prioritizable targets) and `obsessions` (irrational fixations tied
    to trauma or emotion, not subject to cost-benefit reasoning). The same
    split applies in `emotional_baseline`: `active_desires` → `active_goals`
    + `active_obsessions`. Old fields kept for backward compatibility.
12c. `character_arc` in stage_snapshot provides a bird's-eye view from
    stage 1 to the current stage (arc_summary, arc_stages key nodes,
    current_position). Complements `stage_delta` which covers only the
    previous-to-current change.

## Extraction

12. batch (extraction) = stage (runtime), 1:1. "Batch" is the pipeline
    term; "stage" is the content/runtime term. Both kept for clarity.
    Batches are split by natural story boundaries during the analysis phase.
    Each batch may have a different chapter count (target 10, min 5, max 15).
    Batch N = stage N candidate. Stage N is cumulative through 1..N.
13. Once active characters are confirmed, Phase 2.5 produces world foundation
    and all character baselines (identity.json, manifest.json, voice_rules.json,
    behavior_rules.json, boundaries.json, failure_modes.json) from full-book
    context as skeleton drafts (source_type: inference). Then **1+N split
    extraction** per batch: one world call, then N parallel character calls.
    All batches may correct any existing baseline (upgrading inference → canon).
    Targeted character supplement only when gaps remain.
14. Any batch may revise any already-written asset across the whole work
    package, not only the current target.
15. Do not generate per-batch report files. Update progress files in-place.
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

24. Each phase step (summarization chunk, analysis, baseline production, batch
    extraction) is a fresh `claude -p` call with no shared session memory.
    Context between steps is entirely file-based.
24a. Extraction prompts do NOT read `simulation/contracts/baseline_merge.md`,
    `memory_digest.jsonl`, or `stage_catalog.json`. The self-contained
    snapshot contract is embedded directly in the extraction prompt.
    `memory_digest.jsonl` and `stage_catalog.json` are maintained
    programmatically by `post_processing.py` (0 token, idempotent).
25. Three-layer quality check per batch: programmatic validation (free) +
    per-lane semantic review (independent LLM agent) + commit gate
    (programmatic cross-consistency). Only semantic errors cause FAIL.
25a. Parallel review lanes (审校通道): after extraction + post-processing,
    world and each character get independent validate → review → fix
    pipelines running in parallel. Each lane's reviewer has narrowed input
    (only its own files + schema + programmatic report; character lanes
    also read world snapshot for cross-consistency). Targeted fix input
    is similarly narrowed (no full chunk summaries by default).
25b. Commit gate (提交门控): programmatic (0 token) check after all lanes
    pass. Verifies stage_id alignment, world-character consistency, and
    programmatically-maintained file validity. Any lane failure or gate
    failure → full batch rollback. No per-lane commit.
25c. Failure triage after review: fixable issues (≤5 specific field/value
    errors, no missing files) → targeted fix agent makes minimal edits +
    re-validate; systemic issues (file missing, structural,
    understanding-level) → full rollback + retry.
26. Extraction runs on a dedicated git branch. Each passing batch is committed.
    Rollback on failure = git reset. After all batches complete, squash-merge
    to main (one clean commit); the extraction branch can then be deleted.
27. Batch boundaries should follow natural story arcs (min 5, max 15, default
    10 chapters). stage_id should be a meaningful Chinese name.
28. The orchestrator pre-computes the file read list for each call (world /
    character). Only the most recent snapshot and memory_timeline are included
    (not full history). `memory_digest.jsonl`, `stage_catalog.json`, and
    `baseline_merge.md` are excluded from the read list. Agents should not
    explore freely.

## Memory System and Retrieval

29. Three-layer memory: stage_snapshot (aggregated state, current stage only),
    memory_timeline (subjective process per event, first-person summary),
    scene_archive (original text split by scene). No separate dialogue corpus.
30. memory_timeline entries include `time_in_story`, `location`, `scene_refs`
    (linking back to scene_archive). Not raw text — first-person subjective
    summaries with psychological detail and causal reasoning. No hard length
    limit; entry count controlled by importance filtering.
31. scene_archive entries include `time_in_story` and `location` for temporal
    and spatial retrieval. Eight fields total. Work-level asset, not
    per-character. One scene never crosses a chapter boundary. `stage_id`
    derived from chapter number via batch plan.
32. Startup loads: memory_timeline recent 2 stages (N + N-1) full text +
    memory_digest.jsonl (compressed index of all stages, ~60-80 tokens/entry,
    for distant-history awareness); scene_archive summaries for all relevant
    stages + N full_text scenes around current stage (default N=5); vocab dict
    into jieba. FTS5 on memory_timeline provides on-demand detail retrieval
    for distant stages; no separate embedding needed for memory_timeline
    (scene_archive embedding covers semantic queries via scene_refs
    back-reference).
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
35. Phase 3.5 (cross-batch consistency check) runs after all Phase 3 batches
    commit. Primarily programmatic (zero tokens) with optional LLM
    adjudication only for flagged items. Errors block Phase 4. This catches
    cross-batch drift that per-batch validation cannot detect (e.g. alias
    mismatches, relationship discontinuity, lazy source_type annotation).
36. scene_archive is produced in Phase 4, independent from Phase 3 (only
    requires `source_batch_plan.json` from Phase 1). Per-chapter LLM calls
    output scene boundary annotations; program extracts full_text from
    source. Parallel execution (`--concurrency`, default 10). Programmatic
    validation only (no semantic review). `scene_id` = `scene_{chapter}_{seq}`.
37. Retrieval artifacts (fts.sqlite, scene_archive.jsonl) live under
    `works/{work_id}/rag/` and are not committed to git (.gitignore).
    Intermediate Phase 4 splits under
    `works/{work_id}/analysis/incremental/scene_archive/`. Lightweight
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
    `works/{work_id}/analysis/incremental/scene_archive/`) **must not be
    git-tracked**. They are in `.gitignore`; if an extraction branch
    already tracks them, `git rm --cached` is required. Without this,
    `git checkout -- .` during Phase 3 rollback restores tracked splits
    to their last committed version, silently destroying newer split
    files. Phase 3 rollback also excludes them from `git clean -fd`.
40e. Phase 4 resume verifies that passed chapters' split files actually
    exist on disk (`verify_passed`). Missing files are reset to pending
    and regenerated. This guards against file loss from any cause
    (rollback, manual cleanup, filesystem errors).

## World Snapshot and Catalog

40f. World `stage_snapshot` only records **current stage** events
    (`stage_events` for detail, `key_events` for 1-sentence summaries).
    No cumulative history — previous design had `historical_events`
    growing unbounded. `evidence_refs` simplified to chapter number list
    (e.g. `["0001", "0002"]`), no detailed descriptions; per-event
    `[NNNN]` inline tags provide fine-grained sourcing.

40g. World `stage_catalog` accumulates `key_events` per stage entry.
    Runtime reads all stages' `key_events` in order to build the
    complete world event timeline — no need to load every stage snapshot.
    Programmatic: `post_processing.py` copies `key_events` from snapshot
    to catalog (0 token).

40h. Smart resume: if a batch is PENDING but extraction output already
    exists on disk (world + all character stage_snapshots), the
    orchestrator skips LLM extraction and jumps directly to
    post-processing. Saves tokens when a batch errored after producing
    output (e.g. crash during post-processing or review). Detection:
    `_extraction_output_exists()` in orchestrator.

## Repository

41. Keep the repo lightweight. Do not commit novels, databases, indexes, large
    artifacts, or real user packages.
42. `works/*/analysis/incremental/` and `works/*/indexes/` are git-tracked as
    canonical work assets.
43. `docs/logs/` is write-mostly historical. Do not proactively read.
44. `prompts/` contains only manual-scenario prompts (ingest, review,
    supplement, cold start). Extraction prompts live in
    `automation/prompt_templates/`; runtime LLM behavior rules live in
    `simulation/prompt_templates/`. Each module is self-contained.
45. `automation/` and `simulation/` each have their own `prompt_templates/`
    directory. Neither depends on `prompts/`.
