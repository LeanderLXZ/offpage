# Runtime Packets

## Goal

The simulation engine should assemble a few predictable packet types instead
of dumping arbitrary files into the model context.

## 1. Bootstrap Request

Purpose:

- resolve or create the scoped setup before runtime starts

Recommended fields:

- `user_id`
- `work_id`
- target `character_id`
- `stage_id`
- `user_role_mode`
- optional `user_canon_character_id`
- optional `context_id`
- `setup_locked`

## 2. Startup Packet

Purpose:

- support the first in-character reply with the minimum stable context

Recommended sections:

- `scope`
  - `user_id`
  - `work_id`
  - target `character_id`
  - `stage_id`
  - `context_id`
- `identity`
  - target baseline summary
  - selected-stage target snapshot
  - user-side role binding
  - active persona summary when used
- `world`
  - work summary
  - selected-stage world snapshot
  - selected-stage relationship snapshot
  - minimal foundation rules
- `relationship`
  - long-term relationship core summary
  - pinned-memory summary
  - current context relationship state
- `session`
  - current context summary
  - current context shared-memory summary
  - current session index summary
  - current scope archive-ref summary
  - recent session summaries
  - full transcript excluded from startup by default
- `retrieval_policy`
  - startup-required files used
  - on-demand buckets available

## 3. Retrieval Request

Purpose:

- ask for deeper context only when the turn actually needs it

Recommended fields:

- `need_type`
  - `world_fact`
  - `historical_recall`
  - `relationship_history`
  - `location_lookup`
  - `faction_lookup`
  - `event_verification`
  - `character_memory`
  - `user_memory`
  - `context_history`
  - `archive_history`
  - `session_transcript`
  - `raw_source_check`
- `work_id`
- `stage_id`
- optional `context_id`
- optional `session_id`
- optional `character_id`
- optional `event_id`
- optional `location_id`
- optional `faction_id`
- optional `chapter_refs`
- optional `output_mode`

## 4. Turn Packet

Purpose:

- provide the model the exact packet needed for one response

Recommended sections:

- `active_identity`
- `current_world_situation`
- `current_relationship_state`
- `user_turn_intent`
- `retrieved_supporting_evidence`
- `response_constraints`

## 5. Writeback Patch

Purpose:

- describe what should be persisted after this turn

Recommended sections:

- `backup_events`
- `session_updates`
- `context_updates`
- `relationship_change_candidates`
- `memory_promotion_candidates`
- `archive_candidates`
- `notes`

## 6. Close Packet

Purpose:

- support explicit close and optional merge

Recommended fields:

- `context_id`
- `close_reason`
- `merge_prompt_required`
- `merge_decision`
- `long_term_updates`

## Reference Style

Within runtime packets, evidence should prefer compact refs.

Examples:

- `0001`
- `0008-0010`
- `阶段1_南林初遇`
- `王枫第九世复生与姜寒汐南林重逢`

Do not repeat full chapter paths inside every packet unless the path itself is
the meaningful distinction.
