# Data Model

## Top-Level Tree

```text
persona-engine/
  ai_context/
  docs/
  interfaces/
  prompts/
  schemas/
  simulation/
  sources/
  users/
  works/
```

## Work Scope Rule

Each novel should be treated as an independent namespace identified by
`work_id`.

At minimum, these layers should be scoped by `work_id`:

- source corpus
- canonical work package
- work-scoped analysis outputs
- world package
- character packages
- work-specific user relationship data
- user-scoped runtime artifacts when persisted

## Content Language Rule

The `language` declared by `sources/works/{work_id}/manifest.json` should act
as the default content language for work-scoped generated materials.

That default should apply to:

- work titles and display names
- world-package text content
- character-package text content
- work-scoped user / relationship text content
- work-scoped analysis summaries unless a special AI-facing layer says
  otherwise
- `work_id` itself when the selected work is Chinese
- work-scoped entity names and identifier values

Structured field names may remain English:

- JSON keys
- schema property names
- repo-level structural path conventions

But identifier values inside work-scoped canon do not need to be English.
For Chinese works, prefer the original Chinese labels over pinyin-only ids for
locations, events, factions, stages, and other work-scoped entities.

The same rule applies to generated work-scoped path segments under
`works/{work_id}/`. If a canonical identifier is Chinese, the derived folder
or file-name segment should also be Chinese by default.

If `work_id` itself is Chinese, the root folders under `sources/works/` and
`works/` should use that same Chinese path segment.

## Source Work Package

Each novel should live under:

```text
sources/works/{work_id}/
```

Recommended contents:

- `manifest.json`
- `raw/`
- `normalized/`
- `chapters/`
- `scenes/`
- `chunks/`
- `metadata/`
- `rag/`

## Canonical Work Package

Persistent source-grounded canonical data for one work should live under:

```text
works/{work_id}/
```

Recommended contents:

- `manifest.json`
- `world/`
- `characters/`
- `analysis/`
- `indexes/`

## Simulation Engine Directory

Repo-level runtime-engine contracts and future implementation should live
under:

```text
simulation/
```

Recommended contents:

- `README.md`
- `contracts/`
- `flows/`
- `retrieval/`

Important boundary:

- `simulation/` describes runtime orchestration
- `works/{work_id}/` stores canonical work truth
- `users/{user_id}/` stores mutable user state
- work-specific load and retrieval hints still belong in
  `works/{work_id}/indexes/`

## World Package

Each work should have one canonical world package under:

```text
works/{work_id}/world/
```

Recommended contents:

- `manifest.json`
- `stage_catalog.json`
- `stage_snapshots/{stage_id}.json`
- `foundation/setting.json`
- `foundation/cosmology.json`
- `foundation/power_system.json`
- `history/timeline.jsonl`
- `events/{event_id}.json`
- `state/world_state_snapshots/{state_id}.json`
- `locations/{location_id}/identity.json`
- `locations/{location_id}/state_snapshots/{state_id}.json`
- `factions/{faction_id}.json`
- `maps/region_graph.json`
- `maps/map_notes.md`
- `cast/character_index.json`
- `cast/character_summaries.json`
- `social/stage_relationships/{stage_id}.json`

World packages are expected to grow and be revised incrementally as later text
expands or corrects prior understanding.

The stage subtree is the work-scoped timeline anchor used by runtime loading.
It should describe the selectable work stages that a user can choose at
conversation start. Those stage records should summarize the current world
state for that stage, while earlier developments remain available as historical
events.

Those canonical revisions should be driven by source-text evidence only.
User dialogue, runtime branches, and relationship drift should not rewrite
canonical world facts or event records.

The `cast/` and `social/` subtrees are work-level views for indexing and
retrieval convenience. Detailed character canon should still live under
`characters/`.

The `events/` subtree should focus on major shared work-level events rather
than minor beat-by-beat scenes that belong in character-layer memory or
analysis.

The `cast/` subtree should focus on the main cast and high-frequency
supporting characters. One-off minor roles do not need to be promoted into the
world package by default.

The world package should not duplicate a separate `knowledge/` layer for
character-specific understanding or misunderstanding of events by default.
Those finer-grained memory and cognition records should remain under
`characters/`.

Open questions also do not need a dedicated `mysteries/` subtree by default.
Unless the user explicitly wants one, those uncertainties should stay in:

- batch reports under `analysis/`
- revision notes
- or stage / event files where the uncertainty is directly relevant

Relationship files in `world/social/` should be stage-scoped snapshots rather
than one global timeless graph.

Recommended semantics:

- `social/stage_relationships/{stage_id}.json` stores the relationship view
  that is current at that selected stage
- runtime should normally load only the selected stage's relationship file
- earlier relationship states remain available for on-demand historical lookup

## Runtime Load Tiers

Recommended startup-required world load:

- `world/manifest.json`
- `world/stage_catalog.json`
- selected `world/stage_snapshots/{stage_id}.json`
- selected `world/social/stage_relationships/{stage_id}.json`
- lightweight `world/foundation/` files needed for global rules

If it exists, `works/{work_id}/indexes/load_profiles.json` should refine the
default startup packet for that work.

Recommended on-demand world load:

- `world/events/{event_id}.json`
- `world/history/timeline.jsonl`
- `world/locations/{location_id}/...`
- `world/factions/{faction_id}.json`
- chapter originals or chunk-level evidence needed for verification

## Character Package

Each target character should live under:

```text
works/{work_id}/characters/{character_id}/
```

For Chinese works, the `{character_id}` directory segment should follow the
canonical Chinese identifier directly rather than a pinyin-only rewrite.

Recommended contents:

- `manifest.json`
- `canon/identity.json`
- `canon/bible.md`
- `canon/memory_timeline.jsonl`
- `canon/relationships.json`
- `canon/voice_rules.json`
- `canon/behavior_rules.json`
- `canon/boundaries.json`
- `canon/failure_modes.json`
- `canon/stage_catalog.json`
- `canon/stage_snapshots/{stage_id}.json`

For Chinese works, the `{stage_id}` path segment should also follow the
canonical Chinese stage identifier directly.

Character packages may hold richer event detail than the world package,
including memory-weight, emotional interpretation, and roleplay-relevant
character perspective.

The recommended semantics are:

- work-level `stage_id` is selected first from the world package
- character packages project that same `stage_id` into character-specific
  state
- stage `N` is cumulative through the prior stages, but the selected snapshot
  should render the latest stage as the active present rather than flattening
  all history into one timeless summary

## User Package

User state should be rooted by user:

```text
users/{user_id}/
```

Recommended contents:

- `profile.json`
- `personas/{persona_id}.json`
- `conversation_library/manifest.json`
- `conversation_library/archive_index.jsonl`
- `conversation_library/scopes/{work_id}/{character_id}/archive_refs.json`
- `conversation_library/archives/{archive_id}/manifest.json`
- `conversation_library/archives/{archive_id}/context_summary.json`
- `conversation_library/archives/{archive_id}/session_index.json`
- `conversation_library/archives/{archive_id}/key_moments.jsonl`
- `users/{user_id}/works/{work_id}/manifest.json`
- `users/{user_id}/works/{work_id}/characters/{character_id}/role_binding.json`
- `users/{user_id}/works/{work_id}/characters/{character_id}/long_term_profile.json`
- `users/{user_id}/works/{work_id}/characters/{character_id}/relationship_core/manifest.json`
- `users/{user_id}/works/{work_id}/characters/{character_id}/relationship_core/pinned_memories.jsonl`
- `users/{user_id}/works/{work_id}/characters/{character_id}/contexts/{context_id}/manifest.json`
- `users/{user_id}/works/{work_id}/characters/{character_id}/contexts/{context_id}/relationship_state.json`
- `users/{user_id}/works/{work_id}/characters/{character_id}/contexts/{context_id}/shared_memory.jsonl`
- `users/{user_id}/works/{work_id}/characters/{character_id}/contexts/{context_id}/session_index.json`

A first-pass dedicated schema for `role_binding.json` now exists at:

- `schemas/role_binding.schema.json`

Important boundary:

- canonical base world and character data should stay under `works/{work_id}/`
- user-specific drift, relationship state, and history should stay under
  `users/{user_id}/`
- the root `users/{user_id}/profile.json` should remain a global user profile
  rather than a dump of one work-character branch's emotional or relationship
  drift
- work- and character-scoped long-term profile changes should be written to
  `long_term_profile.json`
- the user package should reference the canonical character package rather than
  duplicating it
- `role_binding.json` should be able to store the primary target role,
  stage binding, the current user-side role mode, and whether bootstrap setup
  has been locked
- if the user-side role is also a canonical character, the user package should
  also persist that side's selected `character_id`
- if the user-side role is canon-backed, it should inherit the active selected
  work-stage by default unless an explicit branch override exists
- runtime request objects and user-scoped manifests should carry `work_id`
  explicitly in file content, not only via directory paths
- session and context state may be updated continuously during live roleplay
- only retained, promoted, or merged content should flow into
  `relationship_core`
- long-term profile and relationship-core updates should happen only after
  explicit merge confirmation at close time or via explicit merge action
- full dialogue history may be persisted locally under
  `sessions/{session_id}/transcript.jsonl`
- each active session should also keep an append-only `turn_journal.jsonl` or
  equivalent backup journal for recovery
- startup should load summary-layer user state by default rather than full
  transcript history
- real user packages under `users/` should stay local and be excluded from git
  by default
- merged contexts may promote full conversation records into an account-level
  `conversation_library/`

## Session Package

Each branch context may own multiple sessions:

```text
users/{user_id}/works/{work_id}/characters/{character_id}/contexts/{context_id}/sessions/{session_id}/
```

Recommended contents:

- `manifest.json`
- `transcript.jsonl`
- `turn_journal.jsonl`
- `turn_summaries.jsonl`
- `memory_updates.jsonl`

Recommended loading semantics:

- `transcript.jsonl` may store the complete dialogue history for that session
- `turn_summaries.jsonl` should act as the summary and routing layer for
  startup and on-demand narrowing
- `memory_updates.jsonl` is a detailed writeback log and should normally be
  read on demand rather than at startup
- `turn_journal.jsonl` should make it possible to detect incomplete turns after
  crashes or interrupted responses

## Conversation Archive Package

Merged long-term conversation records should prefer:

```text
users/{user_id}/conversation_library/archives/{archive_id}/
```

Recommended contents:

- `manifest.json`
- `context_summary.json`
- `session_index.json`
- `key_moments.jsonl`
- `sessions/{session_id}/manifest.json`
- `sessions/{session_id}/transcript.jsonl`
- `sessions/{session_id}/turn_summaries.jsonl`
- `sessions/{session_id}/memory_updates.jsonl`

Recommended rule:

- merged conversation archives should be immutable account-history records
- the source context should keep a lightweight `archive_ref` or equivalent
  provenance marker after promotion

## User Runtime Load Tiers

Recommended startup-required user load:

- `users/{user_id}/profile.json`
- active `personas/{persona_id}.json` when used
- `role_binding.json`
- `long_term_profile.json`
- `relationship_core/manifest.json`
- `relationship_core/pinned_memories.jsonl`
- `contexts/{context_id}/manifest.json`
- `contexts/{context_id}/relationship_state.json`
- `contexts/{context_id}/shared_memory.jsonl`
- recent `turn_summaries.jsonl`
- `conversation_library/manifest.json`
- current scope `archive_refs.json`

Recommended on-demand user load:

- `contexts/{context_id}/session_index.json`
- older context summaries
- older session summaries
- `sessions/{session_id}/transcript.jsonl`
- `sessions/{session_id}/memory_updates.jsonl`
- `conversation_library/archive_index.jsonl`
- `archives/{archive_id}/context_summary.json`
- `archives/{archive_id}/key_moments.jsonl`
- `archives/{archive_id}/sessions/{session_id}/transcript.jsonl`

Recommended lifecycle additions:

- session close should record who or what triggered the close
- session close should record whether the user accepted or declined merge
- the close flow should support exit keywords or equivalent explicit close
  intents

## Work Analysis Package

Persistent simulation-relevant analysis for one work should prefer:

```text
works/{work_id}/analysis/
```

Recommended contents:

- `incremental/`
- `evidence/`
- `conflicts/`

Recommended rule:

- source-reading packets should be batch-scoped
- default batch size should be configurable per work and default to `10`
  chapters when not overridden
- batch `N` is the default source of the `N`th stage candidate for that
  extraction line
- one batch packet may produce updates for:
  - `world/`
  - one selected character package
  - other affected character packages
- later source evidence may therefore revise already-written canonical files
  across the same work package

## Work Index Package

Cross-cutting work-level lookup views should prefer:

```text
works/{work_id}/indexes/
```

Recommended contents:

- `character_index.json`
- `location_index.json`
- `event_index.json`
- `relation_index.json`

## Service Contract Inputs

The first-pass runtime contract is modeled by:

- `schemas/runtime_session_request.schema.json`

This request model should support:

- bootstrapping a new user-scoped binding before `work_id` and `character_id`
  are permanently locked
- loading an existing locked user account before context recovery
- selecting a work
- selecting a character
- selecting or listing available work stages for the primary target role
- selecting a user-side role or counterpart identity
- inheriting the same selected work-stage for any canon-backed user-side role
  by default
- creating or resuming a context
- passing a user persona
- continuously maintaining user-scoped session/context state during `send_message`
- closing a session through explicit exit intent
- asking for and recording merge confirmation after session close
- explicitly promoting or merging context content into long-term user state
- choosing a terminal type
- carrying `work_id` explicitly so requests and persisted runtime manifests stay
  unambiguous across multiple works
