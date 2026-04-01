# World Layer And Work Scope Direction

## Summary

This milestone updates the architecture direction in two major ways:

- world data is now treated as a first-class canonical layer
- canonical assets should now be scoped by `work_id`

## Why This Changed

The earlier scaffold focused mainly on source text, character packages, user
relationship data, and runtime compilation.

That was not enough for long-form novels where roleplay quality depends on more
than character tone. The system also needs structured knowledge about:

- world foundation
- historical events
- changing world state
- locations and their conditions
- factions and institutions
- map and route structure

At the same time, multi-book support requires stronger isolation so different
works do not pollute one another's characters, world rules, user contexts, or
runtime state.

## New Direction

### 1. Add A Canonical World Layer

The project should eventually track:

- world foundation
- history timeline
- world-state snapshots
- location records
- location-state snapshots
- faction records
- map graph and geography notes
- open world questions and uncertain claims

### 2. Scope Canonical Assets By Work

The preferred direction is now:

- `sources/works/{work_id}/`
- `worlds/{work_id}/`
- `characters/{work_id}/{character_id}/`
- work-specific user relationship data under the selected `work_id`
- runtime artifacts under the selected `work_id`

### 3. Use A Hybrid User Model

Keep:

- a reusable global user profile

Separate by work:

- relationship cores
- branch contexts
- session continuity
- pinned shared memories with a character in that work

## User Flow Impact

The recommended runtime flow is now:

1. choose work
2. choose character
3. choose stage
4. create or resume context

## Current Limitation

These are architecture and documentation updates only.

The repository does not yet have:

- a world package schema set
- real world extraction artifacts
- full migration to work-scoped directories across all layers
