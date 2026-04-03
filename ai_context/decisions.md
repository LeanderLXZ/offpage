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

## Extraction

12. Source reading uses configurable batch size (default 10). Batch N = stage N
    candidate. Stage N is cumulative through 1..N.
13. Once active characters are confirmed, coordinated batches co-produce world
    + character updates. Targeted character supplement only when gaps remain.
14. Any batch may revise any already-written asset across the whole work
    package, not only the current target.
15. Do not generate per-batch report files. Update progress files in-place.

## User Model

16. One `user_id` = one locked work-target-counterpart binding. Setup locks
    after initial creation; changes require new package or explicit migration.
17. Canon-backed user-side roles inherit the target stage by default.
18. Session/context state updates continuously. Long-term profile and
    relationship core update only after explicit merge confirmation.
19. Context-level `character_state.json` tracks real-time character changes
    (mood, personality, voice, agreements, relationship delta, events,
    memories). These are promoted to long-term layers only at merge.
20. Merge is append-first. Events and memories are added, never overwritten.
21. Session close is explicit (exit keyword or close intent). System then asks
    about merge.
22. Full transcripts stay local; startup loads summary layer only.

## Repository

23. Keep the repo lightweight. Do not commit novels, databases, indexes, large
    artifacts, or real user packages.
24. `works/*/analysis/incremental/` and `works/*/indexes/` are git-tracked as
    canonical work assets.
25. `docs/logs/` is write-mostly historical. Do not proactively read.
26. `prompts/` is available as workflow tooling but is not the default
    authority for ordinary continuation after handoff — `ai_context/` is.
