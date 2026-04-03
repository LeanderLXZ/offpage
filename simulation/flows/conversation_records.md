# Conversation Records

## Goal

Design one stable model for:

- turn-by-turn conversation backup
- active session transcripts
- context-scoped session history
- account-level conversation archives after merge
- on-demand transcript retrieval
- crash recovery and replay safety

## Two Storage Zones

### 1. Active Runtime Zone

Writable conversation state should live under:

- `users/{user_id}/contexts/{context_id}/`

Use this zone for:

- current context state
- active sessions
- active transcripts
- active turn journals
- session summaries and memory updates

### 2. Account Archive Zone

Merged long-term conversation archives should live under:

- `users/{user_id}/conversation_library/`

Use this zone for:

- archived context bundles
- archived session transcripts
- account-level archive indexes
- work/character-scoped archive refs

## Active Session Write Model

Recommended active-session files:

- `sessions/{session_id}/manifest.json`
- `sessions/{session_id}/transcript.jsonl`
- `sessions/{session_id}/turn_journal.jsonl`
- `sessions/{session_id}/turn_summaries.jsonl`
- `sessions/{session_id}/memory_updates.jsonl`
- context-level `session_index.json`

## Per-Turn Backup Flow

For each user turn:

1. allocate `turn_id`
2. append the user input to `transcript.jsonl`
3. append `user_input_committed` to `turn_journal.jsonl`
4. generate the model reply
5. append the assistant output to `transcript.jsonl`
6. append `assistant_output_committed` to `turn_journal.jsonl`
7. append:
   - `turn_summaries.jsonl`
   - `memory_updates.jsonl`
8. update:
   - session manifest
   - context `session_index.json`
   - context summary files
9. append `turn_closed` to `turn_journal.jsonl`

This makes the transcript itself the first backup, and the turn journal the
recovery aid.

## Crash Recovery Rule

If a process dies after user input is saved but before the assistant reply is
saved:

- `transcript.jsonl` still contains the user message
- `turn_journal.jsonl` shows the turn as incomplete

The engine should be able to:

- detect the incomplete turn
- decide whether to retry generation
- avoid silently losing the user input

## Startup Loading Rule

Startup should load summary-layer state only.

Recommended startup inputs:

- current context manifest
- relationship summary
- shared-memory summary
- session index
- recent turn summaries
- archive-library manifest
- current work/character-scoped archive refs

Startup should not load:

- full active transcripts
- full archived transcripts
- all old session logs

## On-Demand Retrieval Rule

Recommended retrieval order for user conversation history:

1. current context summary files
2. `session_index.json`
3. current or archived `turn_summaries.jsonl`
4. archived `key_moments.jsonl`
5. full `transcript.jsonl`

Only open the full transcript when:

- exact wording matters
- summary layers are insufficient
- continuity is disputed
- the user explicitly asks for the prior dialogue

## Merge And Archive Flow

When the user chooses to merge a context into long-term account state:

1. close or freeze the current writable context
2. create a new `archive_id`
3. create:
   - `conversation_library/archives/{archive_id}/manifest.json`
   - `context_summary.json`
   - `session_index.json`
   - `key_moments.jsonl`
4. move or copy the selected session transcripts into the archive bundle
5. update:
   - `archive_index.jsonl`
   - binding-level `archive_refs.json`
   - `long_term_profile.json`
   - `relationship_core`
6. mark the source context as:
   - `merged`
   - or `merged_archived`
7. write back `archive_ref` into the source context manifest

Recommended default:

- archive by reference-preserving move or stubbed promotion, not silent
  deletion

## Archive Index Model

Recommended account-level files:

- `conversation_library/manifest.json`
- `conversation_library/archive_index.jsonl`
- `conversation_library/archive_refs.json`

Recommended per-archive files:

- `archives/{archive_id}/manifest.json`
- `archives/{archive_id}/context_summary.json`
- `archives/{archive_id}/session_index.json`
- `archives/{archive_id}/key_moments.jsonl`
- `archives/{archive_id}/sessions/{session_id}/...`

## Suggested Retrieval Keys

Useful metadata for archive and session indexes:

- `archive_id`
- `context_id`
- `session_id`
- `user_id`
- `work_id`
- `character_id`
- `stage_id`
- `lifecycle`
- `merge_reason`
- `started_at`
- `closed_at`
- `merged_at`
- `topics`
- `relationship_tags`
- `important_entities`
- `turn_count`

## Additional Safeguards

Recommended extras:

- append-only ids for turns and journal events
- hash or checksum fields for archived transcript bundles
- redaction support for sensitive user content
- local export / import tooling for account archives
- rebuildable local indexes rather than git-tracked heavy search databases
- explicit retention policy for old contexts and archived transcripts
