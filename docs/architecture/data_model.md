# Data Model

## Top-Level Tree

```text
persona-engine/
  ai_context/
  analysis/
  docs/
  interfaces/
  schemas/
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

- world-package text content
- character-package text content
- work-scoped user / relationship text content
- work-scoped analysis summaries unless a special AI-facing layer says
  otherwise

Structured field names may remain English:

- JSON keys
- schema property names
- path conventions

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

## World Package

Each work should have one canonical world package under:

```text
works/{work_id}/world/
```

Recommended contents:

- `manifest.json`
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
- `mysteries/open_questions.jsonl`
- `knowledge/character_event_awareness/{character_id}.json`
- `cast/character_index.json`
- `cast/character_summaries.json`
- `social/relationship_graph.json`
- `social/relationship_timeline.jsonl`

World packages are expected to grow and be revised incrementally as later text
expands or corrects prior understanding.

Those canonical revisions should be driven by source-text evidence only.
User dialogue, runtime branches, and relationship drift should not rewrite
canonical world facts or event records.

The `cast/` and `social/` subtrees are work-level views for indexing and
retrieval convenience. Detailed character canon should still live under
`characters/`.

The `events/` and `knowledge/` subtrees are also concise work-level views.
Detailed event memory and character-specific interpretation should remain under
`characters/`.

## Character Package

Each target character should live under:

```text
works/{work_id}/characters/{character_id}/
```

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

Character packages may hold richer event detail than the world package,
including memory-weight, emotional interpretation, and roleplay-relevant
character perspective.

## User Package

User state should be rooted by user:

```text
users/{user_id}/
```

Recommended contents:

- `profile.json`
- `personas/{persona_id}.json`
- `works/{work_id}/manifest.json`
- `works/{work_id}/characters/{character_id}/role_binding.json`
- `works/{work_id}/characters/{character_id}/relationship_core/manifest.json`
- `works/{work_id}/characters/{character_id}/relationship_core/pinned_memories.jsonl`
- `works/{work_id}/characters/{character_id}/contexts/{context_id}/manifest.json`
- `works/{work_id}/characters/{character_id}/contexts/{context_id}/relationship_state.json`
- `works/{work_id}/characters/{character_id}/contexts/{context_id}/shared_memory.jsonl`

Important boundary:

- canonical base world and character data should stay under `works/{work_id}/`
- user-specific drift, relationship state, and history should stay under
  `users/{user_id}/`
- the user package should reference the canonical character package rather than
  duplicating it

## Session Package

Each branch context may own multiple sessions:

```text
users/{user_id}/works/{work_id}/characters/{character_id}/contexts/{context_id}/sessions/{session_id}/
```

Recommended contents:

- `manifest.json`
- `transcript.jsonl`
- `turn_summaries.jsonl`
- `memory_updates.jsonl`

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

- selecting a work
- selecting a character
- selecting or listing available stages
- creating or resuming a context
- passing a user persona
- choosing a terminal type
