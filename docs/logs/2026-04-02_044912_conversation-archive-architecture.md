# Conversation Archive Architecture

## Why

The user asked for a full redesign of conversation-record handling so the
runtime engine could:

- back up every user input and assistant output
- keep full local transcripts under `users/`
- promote merged contexts into an account-level conversation archive library
- retrieve active-context and archived conversation history on demand
- keep real user data out of git

## What Changed

- introduced an account-level `conversation_library/` model under
  `users/{user_id}/`
- added a dedicated engine design doc:
  - `simulation/flows/conversation_records.md`
- extended active session design to include:
  - `transcript.jsonl`
  - `turn_journal.jsonl`
  - `turn_summaries.jsonl`
  - `memory_updates.jsonl`
- defined per-turn backup order:
  - commit user input
  - generate reply
  - commit assistant output
  - then update summaries and state
- defined merge-time archive promotion into:
  - `conversation_library/archives/{archive_id}/`
- added archive indexes and scoped archive refs for retrieval
- updated runtime loading rules so startup loads summary-layer user state while
  full transcripts remain on-demand
- kept `users/` local-only by default under `.gitignore`

## Main Files Updated

- `users/README.md`
- `simulation/README.md`
- `simulation/flows/conversation_records.md`
- `simulation/flows/startup_load.md`
- `simulation/flows/live_update.md`
- `simulation/flows/close_and_merge.md`
- `simulation/contracts/service_boundary.md`
- `simulation/contracts/runtime_packets.md`
- `simulation/retrieval/load_strategy.md`
- `docs/architecture/data_model.md`
- `docs/architecture/system_overview.md`
- `prompts/runtime/用户入口与上下文装载.md`
- `prompts/runtime/users状态回写.md`
- `works/<work_id>/indexes/load_profiles.json`
- relevant `ai_context/` handoff and decisions files

## Outcome

The engine design now treats conversation history as:

1. active local session data
2. summary-layer startup context
3. on-demand transcript recall
4. account-level archived conversation history after merge

This keeps runtime startup light while preserving full local conversation
provenance.
