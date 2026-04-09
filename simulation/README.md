# Simulation Engine

## Purpose

`simulation/` is the dedicated home for runtime-engine design and future
implementation.

Use this directory for:

- bootstrap and setup flow
- startup loading rules
- on-demand retrieval strategy
- runtime packet contracts
- continuous writeback rules
- explicit close-and-merge lifecycle
- terminal-agnostic service boundaries

Do not use this directory for:

- source text
- work canon
- user state
- batch extraction reports

Those assets still belong under:

- `sources/works/{work_id}/`
- `works/{work_id}/`
- `users/{user_id}/`

## Why This Is Separate From `docs/architecture/`

`docs/architecture/` should describe stable repo structure and data-model
boundaries.

`simulation/` should describe how the runtime engine actually starts, loads,
retrieves, updates, and closes.

That split keeps two different concerns from being mixed together:

- static architecture truth
- operational engine contracts

## Directory Map

```text
simulation/
  README.md
  contracts/
    service_boundary.md
    runtime_packets.md
  flows/
    bootstrap.md
    conversation_records.md
    startup_load.md
    live_update.md
    close_and_merge.md
  retrieval/
    load_strategy.md
    index_and_rag.md
```

## Core Design Goals

1. Do not rely on one giant startup prompt.
2. Load only the minimum packet needed for the first response.
3. Keep startup-required data separate from on-demand data.
4. Prefer structured retrieval before raw chapter loading.
5. Keep canonical work data separate from mutable user state.
6. Update `session` and `context` continuously during live conversation.
7. Keep long-term merge explicit rather than automatic.
8. Keep the engine reusable across agent, app, and MCP terminals.

## Source-Of-Truth Split

- `ai_context/`
  - durable AI handoff rules and repo-level decisions
- `docs/architecture/`
  - repo topology and data-model boundaries
- `works/{work_id}/`
  - source-grounded canon plus work-level retrieval indexes
- `users/{user_id}/`
  - mutable runtime state and long-term user-owned drift
- `simulation/`
  - lifecycle, contracts, routing, and future engine code

## Engine Pipeline

1. bootstrap
2. startup load
3. turn classification
4. on-demand retrieval
5. reply compilation
6. live writeback
7. explicit close and merge

## Startup Core

The default startup packet should prefer summaries and selected-stage views.

Load by default:

- `works/{work_id}/manifest.json`
- `works/{work_id}/world/manifest.json`
- `works/{work_id}/world/stage_catalog.json`
- selected `world/stage_snapshots/{stage_id}.json`
- selected `world/social/stage_relationships/{stage_id}.json`
- lightweight world foundation files needed for global rules
- target character baseline
- target character selected-stage snapshot
- `users/{user_id}/profile.json`
- active `persona` summary when used
- role binding
- `long_term_profile.json`
- `relationship_core` summaries
- pinned-memory summaries
- current context manifest and relationship summaries
- recent session summaries

When present, `works/{work_id}/indexes/load_profiles.json` should refine this
default split for that specific work.

## Retrieval Rule

Startup should not load:

- full world history
- all events
- all locations and factions
- all character memory
- full user-session transcripts
- raw chapter text

Those become on-demand retrieval targets.

Recommended order:

1. structured ids and stage-aware files
2. work-level indexes
3. concise summaries
4. detailed canon files
5. raw chapter evidence only when needed

For the user layer, keep a clear split:

- startup may load summary-layer user state
- full `users/.../transcript.jsonl` files should remain local and on-demand
- transcript recall should route through context/session indexes and session
  summaries before opening the full transcript

## Memory Retrieval

Two retrieval libraries support the runtime:

1. **scene_archive** — original text split by scene (work-level, stored under
   `works/{work_id}/rag/scene_archive.jsonl`)
2. **memory_timeline** — character subjective memories (character-level,
   stored under `works/{work_id}/characters/{character_id}/canon/memory_timeline/`)

Two-level retrieval funnel:

1. **jieba + vocab dict + FTS5** (default, <20ms per turn) — every turn,
   jieba segments user input + context keywords, matches against work-level
   vocab dict, queries FTS5 for top-K summaries. No match = no retrieval.
2. **Embedding via LLM tool use** (fallback, 200-300ms) — LLM calls
   `search_memory` tool when FTS5 candidates are insufficient. Rare.

The engine also extracts context-state keywords (location, recent events,
emotion) to enable **proactive character association** — the character may
naturally recall related memories without being asked.

Tech: `jieba` (segmentation), `sqlite FTS5` (primary), `bge-large-zh-v1.5`
(optional embedding fallback). Single SQLite file, no separate vector DB.

See `simulation/retrieval/index_and_rag.md` and `docs/requirements.md` §12.

## First Read Order For Runtime Work

1. this file
2. `simulation/contracts/service_boundary.md`
3. `simulation/contracts/runtime_packets.md`
4. `simulation/flows/conversation_records.md` when the task touches user
   history, transcript backup, or archive retrieval
5. the relevant `simulation/flows/*.md`
6. `simulation/retrieval/load_strategy.md`
7. the target work's `indexes/load_profiles.json` if present
