# Startup Load

## Goal

Compile the minimum useful packet for the first reply.

## Load Order

1. Read `works/{work_id}/manifest.json` if present.
2. Read `works/{work_id}/indexes/load_profiles.json` if present.
3. Read `works/{work_id}/world/manifest.json`.
4. Read `works/{work_id}/world/stage_catalog.json`.
5. Read selected `world/stage_snapshots/{stage_id}.json`.
6. Read selected `world/social/stage_relationships/{stage_id}.json`.
7. Read the minimum `world/foundation/` files required for global rules.
8. Read target character baseline.
9. Read target character selected-stage snapshot.
10. Read `users/{user_id}/profile.json`.
11. Read the active persona summary when used.
12. Read `role_binding.json`.
13. Read `long_term_profile.json`.
14. Read `relationship_core/manifest.json`.
15. Read `relationship_core/pinned_memories.jsonl` when present.
16. Read current context summary files.
17. Read current context `session_index.json`.
18. Read recent session summaries.
19. Read `users/{user_id}/conversation_library/manifest.json` when present.
20. Read scoped archive refs for the current `work_id` and `character_id`
    when present.

## Startup Rules

1. Prefer selected-stage summaries over full historical dumps.
2. Prefer concise work-level indexes over broad directory sweeps.
3. Do not load raw chapter text by default.
4. Do not load all world events, locations, factions, or history up front.
5. When a work-specific load profile exists, treat it as the local override on
   top of repo-level defaults.
6. Do not load full active or archived `transcript.jsonl` files at startup.

## Output

The result should be one startup packet that is ready for the first reply
without requiring the full canon package in context.
