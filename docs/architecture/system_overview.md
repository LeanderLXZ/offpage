# System Overview

## Goal

Build a reusable, multi-terminal character roleplay engine for long-form
novels.

The system should support:

- selecting a source work before loading downstream assets
- extracting and preserving world state in addition to character state
- extracting one or many characters from a novel
- preserving canon-grounded world packages
- preserving canon-grounded character packages
- preserving user-specific relationship growth separately
- choosing a character stage at conversation start
- loading the same core logic through agent, app, and MCP terminals

## Two Work Packages

Each work should have two distinct package roots:

1. `sources/works/{work_id}/`
   - raw and normalized source material
   - chapter text and source metadata

2. `works/{work_id}/`
   - the persistent source-grounded canonical package for that work
   - world, characters, analysis, and indexes

## Work Namespace

Each novel should act as its own namespace identified by `work_id`.

That namespace should scope:

- source corpus
- canonical work package
- work-scoped analysis outputs
- world package
- character packages
- work-specific user relationship data
- user-scoped runtime compilation inputs

The user-facing flow should therefore begin with:

1. choose work
2. choose character
3. choose stage
4. create or resume a context

## Content Language Policy

For work-scoped generated materials, content text should default to the source
work language.

Examples:

- a Chinese work should produce Chinese character packages
- a Chinese work should produce Chinese world packages
- a Chinese work should produce Chinese work-scoped user / relationship
  materials

Field names may remain English for structural consistency:

- JSON keys
- schema property names
- repo-level structural identifiers

## Core Layers

### 1. Source Corpus

Stores raw and normalized novel text plus future retrieval artifacts.

### 2. Analysis

Stores incremental extraction results, evidence references, and conflict notes.

Recommended split:

- top-level `analysis/` for extraction-side scratch or transitional artifacts
- `works/{work_id}/analysis/` for persistent simulation-relevant analysis

Recommended extraction order:

1. identify candidate characters
2. read the source in batches for shared world extraction
3. read the source in batches for one selected character at a time

Any one source-reading batch may still revise or supplement multiple
downstream assets, including the world layer and multiple character packages.

### 3. World Packages

Stores canon-grounded, user-independent world assets.

Each package may include:

- world manifest
- world foundation
- power-system rules
- history timeline
- major event registry and event summaries
- world-state snapshots
- location records
- location-state snapshots
- faction records
- map graph and geography notes
- work-level cast index and brief character summaries
- concise per-character event knowledge summaries
- work-level relationship graph / timeline views

These assets should be maintained incrementally.

New text may:

- expand prior world knowledge
- correct earlier assumptions
- clarify uncertain geography
- revise the apparent state of cities, factions, or institutions
- refine the chronology, scope, or meaning of major events

Those revisions should be traceable and source-driven rather than silently
overwriting earlier understanding.

Important boundary:

- canonical world assets may be revised by later source reading
- user conversations and runtime branches must not rewrite canonical world
  history, world-state facts, or event records
- world packages may keep concise character knowledge summaries about major
  events
- detailed character-side event memory and interpretation should remain in the
  character package

### 4. Character Packages

Stores canon-grounded, user-independent character assets.

Each package includes:

- character manifest
- character bible
- memory timeline
- voice and behavior rules
- stage catalog
- stage snapshots

Character construction should normally happen after an initial world-first
batch pass has established the shared world context for the work.

### 5. User Packages

Stores user identity, persona, relationship cores, context branches, and
session history.

This is where long-term relationship memory and user-specific character drift
belong.

Recommended split:

- `users/{user_id}/` as the user root
- work-scoped user / relationship data inside
  `users/{user_id}/works/{work_id}/`

Work-scoped user / relationship materials should default to the selected work
language.

When the user selects a target character, the runtime should load the
canonical base from `works/{work_id}/characters/{character_id}/` and then
layer user-specific state from
`users/{user_id}/works/{work_id}/characters/{character_id}/`.

### 6. Runtime Compilation

Compiles:

- world baseline
- relevant work-level event summaries
- world-state snapshot
- relevant location state if needed
- character canon
- selected character stage
- user persona
- relationship core
- current context branch
- recent session state

into a minimal runtime context for the model.

That runtime context may depend on facts first discovered during world-first
batch extraction and later refined during targeted character extraction.

If runtime state is persisted, it should prefer user-scoped context trees
rather than `works/{work_id}/`.

### 7. Interfaces

Expose the same core roleplay engine to:

- direct AI agents
- frontend applications
- mobile chat MCP-style adapters

## Runtime Load Formula

At conversation start, the system should load:

`world baseline + relevant world events + world state + character baseline + stage snapshot + user persona + relationship core + current context + recent session state`

## Stage Selection

Stage selection is part of the character package, not an external free-form
input.

Each character package should include a `stage_catalog.json` containing:

- stage ids
- stage titles
- short summaries
- relationship and knowledge-state hints

At the beginning of a new conversation:

1. the terminal selects a character
2. the system reads that character's stage catalog
3. the system displays the available stage summaries
4. the user chooses one
5. a new context is created with that `stage_id`

The selected character stage should remain compatible with the world state for
the chosen work.

## Relationship Memory

User-specific memory is split into:

- `relationship_core`
  - long-lived retained memory
- `contexts/{context_id}`
  - branch-specific continuity

Contexts can later be:

- temporary
- persistent
- merged into the relationship core

Recommended location:

- `users/{user_id}/works/{work_id}/characters/{character_id}/`
