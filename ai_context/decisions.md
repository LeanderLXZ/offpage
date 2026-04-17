# Key Decisions

Decisions already embodied in `docs/architecture/` or `simulation/` are
not repeated here. This file records only the non-obvious rules and
constraints beyond what the architecture docs already say.

## Roleplay Philosophy

1. Priority is deep behavioral / decision consistency, not surface voice
   imitation. Chain: memory / relationship → psychological reaction →
   behavior decision → language realization.
2. Objective fact and subjective character cognition must be separated.
   Characters may misunderstand, conceal, or distort.
3. Stage differences must be preserved. No flattening into a timeless
   static profile.

## Data Separation

4. User data stored separately from canonical character data. User drift
   never pollutes canon.
5. World data is a first-class layer, not hidden inside character notes.
6. World materials are living canon — only source-text evidence may
   revise them. User conversations must not.
7. Conflicts, revisions, contradictions recorded explicitly, not
   silently overwritten.

## Work Scope

8. Each novel = independent namespace (`work_id`). User flow chooses
   work before character.
9. Chinese works: `work_id`, entity names, identifier values, and
   generated path segments default to Chinese.
10. `ai_context/` remains English. JSON field names may remain English.

## Character Depth Dimensions

11a. `identity.json` carries two cross-story fields beyond static bio:
    `core_wounds` (root traumas with origin and behavioral impact) and
    `key_relationships` (relationship arcs with initial state,
    evolution, turning points). Loaded at runtime with the stage
    snapshot.
11b. `behavior_state` separates `core_goals` (rational,
    re-prioritizable) from `obsessions` (irrational, trauma / emotion-
    tied, not subject to cost-benefit). `emotional_baseline` mirrors
    with `active_goals` + `active_obsessions`.
11c. `character_arc` in stage_snapshot = bird's-eye view stage 1 →
    current (arc_summary, arc_stages key nodes, current_position).
    Complements `stage_delta` (last step only).

## Extraction

12. stage (extraction) = stage (runtime), 1:1. Split by natural story
    boundaries (target 10 ch, min 5, max 15). Stage N cumulative
    through 1..N. `stage_id` is a meaningful Chinese name.
13. Phase 2.5 produces world foundation + character baselines (skeleton
    drafts) from full-book context. Phase 3 uses 1+2N split extraction
    per stage (1 world + N char_snapshot + N char_support); any stage
    may correct any existing baseline (via char_support process) or
    already-written asset across the whole work package.
14. No per-stage report files; update progress in-place.
15. `target_voice_map` / `target_behavior_map` use specific character
    names for main / important characters (≥3–5 examples each); generic
    types brief or omitted. Runtime loads only entries matching user's
    role. Fallback = backward scan through previous snapshots (pure
    code I/O, no extra LLM call).

## User Model

16. One `user_id` = one locked work-target-counterpart binding. Setup
    locks after creation; changes require new package or explicit
    migration.
17. Canon-backed user-side roles inherit target stage by default.
18. Session / context state updates continuously. Long-term profile and
    relationship core update only after explicit merge confirmation.
19. Context-level `character_state.json` tracks real-time mood,
    personality, voice, agreements, relationship delta, events,
    memories — promoted to long-term layers only at merge.
20. Merge is append-first. Events / memories added, never overwritten.
21. Session close is explicit. System asks about merge.
22. Full transcripts stay local; startup loads summary layer only.

## Automated Extraction (non-obvious only)

23. Each phase step is a fresh `claude -p` / `codex` call with no shared
    session memory. Context between steps is entirely file-based.
24. Extraction prompts do NOT read
    `simulation/contracts/baseline_merge.md`, `memory_digest.jsonl`,
    `world_event_digest.jsonl`, or `stage_catalog.json`. The
    self-contained snapshot contract is embedded directly in the
    prompt; digests / catalog are programmatically maintained by
    `post_processing.py` (0 token, idempotent).
25. Quality check per stage via `repair_agent`: four-layer checkers
    (L0 json_syntax → L1 schema → L2 structural → L3 semantic) ×
    four-tier fixers (T0 programmatic → T1 local_patch → T2
    source_patch → T3 file_regen), orthogonal. Field-level surgical
    patches via json_path. Semantic LLM at most 2 calls (initial +
    final verify). Missing catalog / digest routes to PP rerun.
26. Extraction runs on a dedicated git branch. Each passing stage
    committed. Rollback = `git reset` to last committed stage. After
    all stages complete, squash-merge to main.
27. Orchestrator pre-computes the read list per call (world /
    character). Only the most recent snapshot + memory_timeline
    included. Agents do not explore freely.

## Memory System

28. Three-layer memory (`stage_snapshot` / `memory_timeline` /
    `scene_archive`). No separate dialogue corpus.
29. ID convention: `{TYPE}-S{stage:03d}-{seq:02d}` for `memory_digest`
    (`M-`), `world_event_digest` (`E-`), `scene_archive` (`SC-`).
    3-digit stage ≤999, 2-digit seq ≤99 per stage. Stage encoded in ID;
    digest / archive entries carry no separate `stage_id` field —
    runtime loader filters via regex `S(\d{3})`. Story-time field =
    `time` across all three.
30. When simulating character A, only load scenes where A is in
    `characters_present` and A's own memory_timeline. Do not load
    others'.
31. `stage_events` is world-public only (each 50–80 字, hard gate).
    Personal / internal items belong in character `memory_timeline`,
    never in world `stage_events`.
32. `world_event_digest.summary` = 1:1 copy of the source
    `stage_events` entry (boundary enforced at write time in prompt +
    repair agent). 5-level importance inferred by keyword
    (trivial / minor / significant / critical / defining), default
    significant.
33. `memory_digest.summary` = 1:1 copy of the memory_timeline
    `digest_summary` (30–50 字, hard gate).
34. Character `stage_snapshot.stage_events` holds only this stage's
    events, not accumulated history (each 50–80 字, hard gate).
    Cross-stage history = `memory_timeline` + `memory_digest` +
    `world_event_digest`.
35. `fixed_relationships.json` (structural bonds: blood, lineage,
    faction) is not stage-dependent. Phase 2.5 produces skeleton;
    subsequent stages may correct. Loaded at runtime as Tier 0.

## Retrieval

36. Two-level retrieval funnel: Level 1 = jieba + vocab dict + FTS5
    (<20ms, default); Level 2 = embedding via LLM tool use (rare). No
    separate vector DB — single SQLite with optional embedding BLOB.
37. Proactive context-state association: engine extracts current
    location, recent events, emotion, conversation partner for jieba
    matching each turn — not just user input.
38. Vocab dict (work-level, jieba custom-dict format) auto-generated
    from extraction output. At `works/{work_id}/indexes/vocab_dict.txt`,
    committed to git.
39. Retrieval artifacts under `works/{work_id}/retrieval/` (not
    committed). Intermediate Phase 4 splits under
    `works/{work_id}/analysis/scene_splits/` must not be git-tracked —
    else `git checkout --` during rollback silently destroys them.
    `scene_archive.jsonl` fully regenerated on each merge.

## JSON Repair

40. LLM-produced JSON often has format errors (unescaped quotes,
    trailing commas, truncation) while content is intact. Three-level
    repair: L1 regex (0 token) → L2 LLM on broken JSON only (minimal) →
    L3 full re-run (last resort). See
    `automation/persona_extraction/json_repair.py`.

## Repository

41. No novels, databases, indexes, large artifacts, or real user
    packages in git.
42. `works/*/analysis/` and `works/*/indexes/` tracked as canonical
    assets; `works/*/retrieval/` local-only.
43. `docs/logs/` is write-mostly historical — do not proactively read.
44. `prompts/` = manual scenarios only (ingest, review, supplement,
    cold start). Extraction prompts in `automation/prompt_templates/`;
    runtime rules in `simulation/prompt_templates/`. Each module
    self-contained.
