# Data Model

## Top-Level Tree

```text
persona-engine/
  ai_context/
  analysis/
  characters/
  docs/
  interfaces/
  runtime/
  schemas/
  sessions/
  sources/
  users/
```

## Work Package

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

## Character Package

Each target character should live under:

```text
characters/{character_id}/
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

## User Package

Each user should live under:

```text
users/{user_id}/
```

Recommended contents:

- `profile.json`
- `personas/{persona_id}.json`
- `characters/{character_id}/relationship_core/manifest.json`
- `characters/{character_id}/relationship_core/pinned_memories.jsonl`
- `characters/{character_id}/contexts/{context_id}/manifest.json`
- `characters/{character_id}/contexts/{context_id}/relationship_state.json`
- `characters/{character_id}/contexts/{context_id}/shared_memory.jsonl`

## Session Package

Each branch context may own multiple sessions:

```text
users/{user_id}/characters/{character_id}/contexts/{context_id}/sessions/{session_id}/
```

Recommended contents:

- `manifest.json`
- `transcript.jsonl`
- `turn_summaries.jsonl`
- `memory_updates.jsonl`

## Service Contract Inputs

The first-pass runtime contract is modeled by:

- `schemas/runtime_session_request.schema.json`

This request model should support:

- selecting a character
- selecting or listing available stages
- creating or resuming a context
- passing a user persona
- choosing a terminal type
