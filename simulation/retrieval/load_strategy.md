# Load Strategy

## Goal

Separate startup-required loading from on-demand expansion so runtime does not
pay the cost of loading the entire canon package every turn.

## Tier 0: Startup Core

Load before the first reply:

- work manifest
- world manifest
- world stage catalog
- selected world stage snapshot
- selected stage relationship snapshot
- minimum world foundation rules
- target character identity (`identity.json`)
- target character failure modes (`failure_modes.json`)
- target character hard boundaries (`boundaries.json` → `hard_boundaries` only)
- target character selected-stage snapshot (self-contained: voice, behavior,
  boundaries, relationships, personality, mood, knowledge — no baseline merge)
- target character memory timeline (`memory_timeline/{stage_id}.jsonl` for
  stages 1..N of selected stage N)
- user profile summary
- active persona summary when used
- user role binding
- long-term profile
- long-term relationship summary
- pinned-memory summaries
- current context manifest and relationship summary
- current context character state (emotional state, personality drift, voice
  drift, mutual agreements, relationship delta, context events, context
  memories)
- current context shared-memory summary
- current context session-index summary
- conversation-library manifest
- current work/character archive-ref summary
- recent session summaries

## Tier 1: Structured Expansion

Load only if the turn needs it:

- `world/events/{event_id}.json`
- `world/locations/{location_id}/...`
- `world/factions/{faction_id}.json`
- `world/history/timeline.jsonl`
- older `world/social/stage_relationships/{stage_id}.json`
- past stage snapshots (`canon/stage_snapshots/{past_stage_id}.json` — for
  deep historical recall of past-stage voice, behavior, or relationship details)
- `users/{user_id}/relationship_core/pinned_memories.jsonl`
- older context manifests or older session summaries
- `users/{user_id}/conversation_library/archive_refs.json`
- `users/{user_id}/conversation_library/archives/{archive_id}/context_summary.json`
- `users/{user_id}/conversation_library/archives/{archive_id}/key_moments.jsonl`

Recommended trigger mapping:

- world fact question
  - event, location, or faction files
- historical recall (past events, timeline)
  - timeline plus older world stage snapshots or relationship snapshots
- past-stage behavioral detail (past voice, speech habits, reactions)
  - load past `stage_snapshots/{past_stage_id}.json` on demand
  - see `prompts/runtime/历史回忆处理规则.md` for when this is needed
- relationship clarification
  - current stage relationship first, then older stage files if needed
- character memory
  - memory_timeline already loaded at startup; use loaded memories first
- user shared-memory recall
  - pinned memories, current context shared memory, or older context summaries
- archived conversation recall
  - archive refs, archive summaries, and key moments before opening full
    archived transcripts

## Tier 2: User Transcript Recall

Load full dialogue history only when the turn needs exact conversation recall:

- `users/{user_id}/contexts/{context_id}/session_index.json`
- `users/{user_id}/contexts/{context_id}/sessions/{session_id}/turn_summaries.jsonl`
- `users/{user_id}/contexts/{context_id}/sessions/{session_id}/transcript.jsonl`
- `users/{user_id}/contexts/{context_id}/sessions/{session_id}/memory_updates.jsonl`
- `users/{user_id}/conversation_library/archives/{archive_id}/session_index.json`
- `users/{user_id}/conversation_library/archives/{archive_id}/sessions/{session_id}/turn_summaries.jsonl`
- `users/{user_id}/conversation_library/archives/{archive_id}/sessions/{session_id}/transcript.jsonl`
- `users/{user_id}/conversation_library/archives/{archive_id}/sessions/{session_id}/memory_updates.jsonl`

Recommended trigger mapping:

- user asks what happened in a previous conversation
- exact prior wording matters
- the engine needs continuity details that summaries do not preserve

## Tier 3: Verification Depth

Load raw chapter evidence only when:

- summaries conflict
- the user asks for close textual support
- output mode requires higher fidelity
- existing canon files are too coarse to answer safely

## Retrieval Order

1. selected `stage_id` and explicit entity ids
2. work indexes under `works/{work_id}/indexes/`
3. concise summaries and stage snapshots
4. detailed canon files and summary-layer user history
5. full user transcript when needed
6. raw source text

## Work-Level Override

Whenever present, `works/{work_id}/indexes/load_profiles.json` should define:

- startup-required packets
- on-demand buckets
- work-specific retrieval notes
- fidelity escalation rules
