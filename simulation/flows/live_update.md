# Live Update

## Goal

Run one stable loop for each user turn without overloading the model context
or polluting canonical data.

## Turn Loop

1. Read the user turn.
2. Allocate `turn_id`.
3. Append the user input to the active session transcript backup.
4. Record the input commit in the turn journal.
5. Classify retrieval need.
6. Retrieve extra context only if the current startup packet is insufficient.
7. Compile the turn packet.
8. Generate the reply.
9. Append the assistant output to the transcript backup before returning it.
10. Record the output commit in the turn journal.
11. Persist lightweight updates to user-scoped state.
12. Close the turn in the turn journal.

## Continuous Writeback

Every turn should consider:

- transcript backup status
- turn-journal status
- session summary updates
- current context summary updates
- relationship-change candidates
- memory-promotion candidates

## Writeback Split

Update continuously:

- `sessions/`
- current `contexts/`
- `contexts/{context_id}/character_state.json`
  - emotional state, personality drift, voice drift, mutual agreements,
    relationship delta, context events, context memories
- `transcript.jsonl`
- `turn_journal.jsonl`
- `session_index.json`

Update selectively:

- `relationship_core`
- `pinned_memories`

Update only after explicit merge confirmation:

- `long_term_profile.json`
- long-term relationship-core promotions tied to the closed context

## Canon Safety

1. Do not write user drift into `works/{work_id}/`.
2. Do not rewrite world facts from conversation-derived guesses.
3. Do not rewrite character baseline canon from user interaction.

## Recovery Rule

If the engine stops after the user input was committed but before the
assistant output was committed, recovery should use:

- `transcript.jsonl`
- `turn_journal.jsonl`

to detect the incomplete turn and continue safely rather than losing the
message.
