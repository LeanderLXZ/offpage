# Context-Level Character State

Timestamp: 2026-04-02 15:51 EDT

## Summary

Added a context-level character runtime state layer to track how the simulated
character changes during live conversation with the user. Previously, context
directories only stored metadata manifests — there was no container for
real-time character drift such as emotional state, personality shifts, voice
changes, mutual agreements, or relationship deltas.

## What Changed

### New Files

- `schemas/context_character_state.schema.json`
  - Fields: emotional_state, personality_drift, voice_drift,
    mutual_agreements, relationship_delta, context_events, context_memories
- `users/_template/contexts/{context_id}/character_state.json`

### Schema Updates

- `schemas/relationship_core.schema.json`
  - Added `mutual_agreements` array for durable agreements promoted from
    context merge
- `schemas/long_term_profile.schema.json`
  - Added `character_drift_history` array (categories: emotional, personality,
    voice, behavior) for accumulated character changes promoted from context
    merge

### Engine Document Updates

- `simulation/flows/startup_load.md` — load order now includes
  `character_state.json`
- `simulation/retrieval/load_strategy.md` — Tier 0 startup core now includes
  context character state
- `simulation/flows/live_update.md` — continuous writeback list now includes
  `character_state.json`
- `simulation/flows/close_and_merge.md` — merge flow now extracts drift,
  agreements, events, and memories from `character_state.json` into long-term
  layers

### Runtime Prompt Updates

- `prompts/runtime/用户入口与上下文装载.md` — load order and per-turn evaluation
  list updated
- `prompts/runtime/users状态回写.md` — writeback target list, continuous
  writeback rules, and merge extraction rules updated

## Data Flow

- During conversation: `character_state.json` updated in real time
- On close + merge confirmation only: extracted and appended into
  `long_term_profile.json` and `relationship_core`

## Motivation

User requirement: both context-level and user-profile-level should track
simulated character changes (mood, personality, voice habits, mutual
agreements). Context level was previously empty — only metadata, no state
content.
