# Load Strategy

## Goal

Separate startup-required loading from on-demand expansion so runtime does not
pay the cost of loading the entire canon package every turn.

## Tier 0: Startup Core

Load before the first reply:

- work manifest
- world manifest
- selected world stage snapshot
- world foundation (`foundation.json` + `fixed_relationships.json`)
- `world_event_digest.jsonl` stage 1..N filtered (N = user-selected stage).
  Each entry is `{event_id, summary (50–80 chars, hard schema gate),
  importance, involved_characters?, time?, location?}` — summary is a
  1:1 copy of the world stage_snapshot `stage_events` entry; stage is
  encoded in `event_id` prefix `E-S###`; loader filters via regex
- target character identity (`identity.json`, loader-level field whitelist
  filter — loads canonical_name/aliases/background/core_wounds/key_relationships;
  **strips `evidence_refs` and large nested evidence fields at load time** to
  cut Tier 0 tokens without schema churn; no Phase 2/2.5 rerun required)
- target character failure modes (`failure_modes.json`)
- target character hard boundaries (`boundaries.json` → `hard_boundaries` only)
- target character selected-stage snapshot (self-contained: voice, behavior,
  boundaries, relationships, personality, mood, knowledge — no baseline merge).
  **Filtered loading**: `target_voice_map` and `target_behavior_map` are loaded
  only for entries matching the user's role — canon character = exact match on
  `target_type`; OC character = match by closest relationship type from role
  binding. Other target entries are omitted to save prompt budget.
  **Fallback for absent characters**: if the current stage snapshot does not
  contain a matching target entry (e.g. the character did not appear in recent
  stages and inheritance was missed), the engine scans backwards through
  `stage_snapshots/` to find the most recent snapshot containing that target
  entry. This is a safety net — normal path is self-contained snapshots.
- target character memory timeline: recent 2 stages (N + N-1) full text
- target character `memory_digest.jsonl`: compressed index, stage 1..N
  filtered (N = user-selected stage) for distant-history awareness.
  Each entry is `{memory_id, summary (30–50 chars, hard schema gate),
  importance, time?, location?}` — summary is a 1:1 copy of the
  memory_timeline `digest_summary`; stage is encoded in the `memory_id`
  prefix `M-S###`, so
  the loader filters via regex (no redundant `stage_id` field). Target
  ~30-40 tokens per entry; 49 stages × ~15 entries ≈ 22-29K tokens.
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

### Tier 0: Scene Archive Startup

- Scene archive **summaries are NOT loaded at startup** — they are an on-demand
  FTS5 index only, not part of Tier 0. Memory_digest + world_event_digest
  already give the LLM an event-level overview; scene summaries would duplicate
  that at much higher token cost.
- Load scene_archive **full_text** for the most recent `scene_fulltext_window`
  scenes (**default 10**, configurable via
  `works/{work_id}/indexes/load_profiles.json::scene_fulltext_window`) where
  the target character is in `characters_present`. These serve as voice /
  style anchors for the immediately preceding narrative. Older scenes stay
  in FTS5 and are pulled on demand (Tier 1).
- `scene_id` format: `SC-S{stage:03d}-{seq:02d}` (e.g. `SC-S003-07`). Stage
  is encoded in the ID; the loader filters recent scenes by parsing this
  prefix.

## Tier 1: Structured Expansion

Load only if the turn needs it:

- `world/events/{event_id}.json`
- `world/locations/{location_id}/...`
- `world/factions/{faction_id}.json`
- `world/history/timeline.jsonl`
- past stage snapshots (`canon/stage_snapshots/{past_stage_id}.json` — for
  deep historical recall of past-stage voice, behavior, or relationship details)
- `users/{user_id}/relationship_core/pinned_memories.jsonl`
- older context manifests or older session summaries
- `users/{user_id}/conversation_library/archive_refs.json`
- `users/{user_id}/conversation_library/archives/{archive_id}/context_summary.json`
- `users/{user_id}/conversation_library/archives/{archive_id}/key_moments.jsonl`
- FTS5 scene_archive retrieval (jieba + vocab dict → FTS5, filtered by
  `characters_present`, `stage_id`, `time`, `location`). Scene summaries
  live here — they are not in Tier 0 and surface only when the query hits
  the index.
- FTS5 memory_timeline retrieval (for entries beyond the 2 recent stages
  not loaded at startup; memory_digest provides awareness, FTS5 provides
  detail when the LLM needs it)
- Embedding retrieval via LLM tool use (fallback when FTS5 insufficient)

Recommended trigger mapping:

- world fact question
  - event, location, or faction files
- historical recall (past events, timeline)
  - timeline plus older world stage snapshots or relationship snapshots
- past-stage behavioral detail (past voice, speech habits, reactions)
  - load past `stage_snapshots/{past_stage_id}.json` on demand
  - see `simulation/prompt_templates/历史回忆处理规则.md` for when this is needed
- relationship clarification
  - current stage relationship first, then older stage files if needed
- character memory (specific past event)
  - memory_digest already loaded — LLM scans it to locate relevant stage
  - FTS5 search on memory_timeline for detailed entries
- character dialogue style reinforcement
  - search scene_archive filtered by `characters_present` and `stage_id`
- specific scene recall
  - search scene_archive by semantic query, `time`, or `location`
- user shared-memory recall
  - pinned memories, current context shared memory, or older context summaries
- archived conversation recall
  - archive refs, archive summaries, and key moments before opening full
    archived transcripts

### Context-Driven Retrieval (Two-Level Funnel)

Every turn, the engine runs jieba segmentation on user input + context state
keywords (current location, recent events, emotion) and matches against the
work-level vocab dict. This is <10ms and always runs.

**Level 1 — jieba + FTS5 (default, <20ms):**

- Matched keywords → FTS5 query → top-K summaries injected into prompt
- LLM judges relevance itself — no extra LLM call
- No match → no retrieval, reply from loaded context only

**Level 2 — Embedding via tool use (fallback, 200-300ms):**

- LLM decides Level 1 candidates are insufficient
- LLM calls `search_memory` tool with semantic query
- Engine runs embedding search on summary vectors, returns results
- LLM generates reply with new context (second LLM call)

Most turns end at Level 1 or skip retrieval entirely. Level 2 is rare.

**Proactive association:** The engine also extracts context keywords
(location, recent events, emotion, conversation partner) for jieba
matching — not just user input. This lets the character naturally recall
related memories without the user asking. LLM decides whether to mention
a retrieved memory based on conversational fit.

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

Scene archive `full_text` can also serve as a verification source — it
contains the original text and may be sufficient before escalating to
raw chapter files.

## Retrieval Order

1. selected `stage_id` and explicit entity ids
2. work indexes under `works/{work_id}/indexes/`
3. concise summaries and stage snapshots
4. memory_digest (startup-loaded overview) → memory_timeline (FTS5/embedding on-demand)
5. scene_archive entries (startup-loaded full_text for recent
   `scene_fulltext_window` scenes only; summaries live in FTS5 and are
   pulled on demand)
6. detailed canon files and summary-layer user history
7. full user transcript when needed
8. raw source text

## Work-Level Override

Whenever present, `works/{work_id}/indexes/load_profiles.json` should define:

- startup-required packets
- on-demand buckets
- work-specific retrieval notes
- fidelity escalation rules
