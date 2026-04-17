# Startup Load

## Goal

Compile the minimum useful packet for the first reply.

## Load Order

1. Read `sources/works/{work_id}/manifest.json` if present.
2. Read `works/{work_id}/indexes/load_profiles.json` if present.
3. Read `works/{work_id}/world/manifest.json`.
4. Read selected `world/stage_snapshots/{stage_id}.json`.
5. Read `works/{work_id}/world/foundation/foundation.json`.
5b. Read `works/{work_id}/world/foundation/fixed_relationships.json`.
6. Read `works/{work_id}/world/world_event_digest.jsonl` filtered to
   stage 1..N (N = user-selected stage).
8. Read target character baseline.
9. Read target character selected-stage snapshot.
10. Read target character memory_timeline: recent 2 stages (N + N-1) full.
10b. Read target character `memory_digest.jsonl` filtered to stage 1..N
    (N = user-selected stage, for distant-history awareness).
11. Load scene_archive full_text for the most recent
    `scene_fulltext_window` scenes (default 10; configurable via
    `works/{work_id}/indexes/load_profiles.json`) where the target
    character is in `characters_present`. **Summaries are NOT loaded at
    startup** — they live in the FTS5 index and are retrieved on demand.
13. Load vocab dict (`works/{work_id}/indexes/vocab_dict.txt`) into jieba
    as custom dictionary for per-turn keyword matching.
14. Read `users/{user_id}/profile.json`.
15. Read the active persona summary when used.
16. Read `role_binding.json`.
17. Read `long_term_profile.json`.
18. Read `relationship_core/manifest.json`.
19. Read `relationship_core/pinned_memories.jsonl` when present.
20. Read current context summary files.
21. Read current context `character_state.json`.
22. Read current context `session_index.json`.
23. Read recent session summaries.
24. Read `users/{user_id}/conversation_library/manifest.json` when present.
25. Read scoped archive refs for the current `work_id` and `character_id`
    when present.

## Startup Rules

1. Prefer selected-stage summaries over full historical dumps.
2. Prefer concise work-level indexes over broad directory sweeps.
3. Do not load raw chapter text by default.
4. Do not load all world events, locations, factions, or history up front.
5. When a work-specific load profile exists, treat it as the local override on
   top of repo-level defaults.
6. Do not load full active or archived `transcript.jsonl` files at startup.
7. Memory_timeline beyond the 2 recent stages is not loaded at startup.
   `memory_digest.jsonl` (stage 1..N filtered) provides compressed awareness of historical
   stages; detailed entries are available via FTS5/embedding on-demand.
8. Scene_archive full_text is only loaded for the most recent
   `scene_fulltext_window` scenes (default 10). Summaries are **not** loaded
   at startup — both older full_text and all summaries live in the FTS5
   index and surface on demand.
9. Vocab dict is loaded into jieba at startup for per-turn keyword matching.
   This enables the two-level retrieval funnel (jieba+FTS5 → embedding
   fallback) described in `simulation/retrieval/index_and_rag.md`.

## Output

The result should be one startup packet that is ready for the first reply
without requiring the full canon package in context.
