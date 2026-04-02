# Service Boundary

## Purpose

This file defines the stable capability surface that terminal adapters should
target.

The adapters in `interfaces/` should call these capabilities instead of
reading or writing work canon or user state directly.

## Boundary Rules

1. Adapters should not resolve file paths on their own beyond selecting the
   scoped request.
2. The engine should load canonical base data from `works/{work_id}/`.
3. The engine should load mutable state from `users/{user_id}/`.
4. Returned packets should prefer summaries, ids, and refs over raw chapter
   text.
5. `work_id` should remain explicit in requests and persisted manifests.

## Capability Groups

### Bootstrap And Setup

- `resolve_user_setup`
- `create_user_setup`
- `lock_user_setup`
- `show_locked_setup`
- `list_available_works`
- `list_available_characters`
- `list_work_stages`
- `create_context`
- `resume_context`

### Startup Loading

- `load_work_manifest`
- `load_world_startup_packet`
- `load_character_startup_packet`
- `load_user_startup_packet`
- `load_context_startup_packet`
- `compile_startup_packet`

### Turn Routing And Retrieval

- `classify_turn_need`
- `retrieve_stage_context`
- `retrieve_world_event`
- `retrieve_location_or_faction`
- `retrieve_history_slice`
- `retrieve_character_memory_slice`
- `retrieve_user_memory_slice`
- `retrieve_context_history_slice`
- `retrieve_account_archive_slice`
- `retrieve_session_transcript`
- `retrieve_raw_evidence`
- `compile_turn_packet`

### Response Generation

- `generate_reply`

### Continuous Writeback

- `backup_user_input`
- `backup_assistant_output`
- `append_turn_journal_event`
- `append_session_summary`
- `update_context_state`
- `append_relationship_candidate`
- `append_memory_candidate`

### Explicit Long-Term Actions

- `pin_memory`
- `merge_context`
- `promote_context_to_relationship_core`
- `archive_context_conversation`
- `close_session`

## Recommended Request Shape

Every runtime-facing request should carry at least:

- `user_id`
- `work_id`
- target `character_id`
- `stage_id`
- `context_id` when one already exists
- output or fidelity mode when relevant

## Recommended Response Shape

The boundary should return packets grouped by meaning rather than by raw file:

- identity packet
- world packet
- relationship packet
- user-state packet
- retrieved evidence packet
- writeback patch

That keeps the terminal adapter focused on presentation instead of filesystem
assembly.
