# System Overview

## Goal

Build a reusable, multi-terminal character roleplay engine for long-form
novels.

The system should support:

- entering or creating a `user_id` before downstream runtime choices
- selecting a source work before loading downstream assets
- extracting and preserving world state in addition to character state
- extracting one or many characters from a novel
- preserving canon-grounded world packages
- preserving canon-grounded character packages
- preserving user-specific relationship growth separately
- choosing a work-scoped stage at conversation start
- projecting that same stage onto the target character and any canon-backed
  user-side role slot by default
- locking bootstrap setup choices after initial account creation
- continuously writing user-scoped session/context state during live roleplay
- closing a session via explicit exit intent and asking whether to merge the
  closed context into long-term user-owned history
- loading the same core logic through agent, app, and MCP terminals

## Simulation Engine Home

Repo-level runtime orchestration should live under:

- `simulation/`

Recommended split:

- `docs/architecture/`
  - static repo structure and data-model boundaries
- `simulation/`
  - bootstrap, startup loading, retrieval routing, continuous writeback,
    explicit close / merge, and service contracts
- `works/{work_id}/indexes/`
  - work-specific load profiles and retrieval hints consumed by the simulation
    engine

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

Runtime requests and persisted user-state manifests should also carry
`work_id` explicitly, not only rely on directory position, so multi-work
runtime state remains unambiguous.

The user-facing flow should therefore begin with:

1. enter `user_id`
2. determine whether this is a new or existing scoped setup
3. if new:
   - choose work
   - choose the target character
   - choose the active work-stage
   - choose the user-side role or counterpart identity
   - if the user-side role is canon-backed, bind that side to the same active
     work-stage by default
   - lock the setup
4. if existing:
   - display the locked account information
   - list recoverable contexts
5. create or resume a context

## Content Language Policy

For work-scoped generated materials, content text should default to the source
work language.

Examples:

- a Chinese work should keep its original Chinese title
- a Chinese work may use a Chinese `work_id`
- a Chinese work should produce Chinese character packages
- a Chinese work should produce Chinese world packages
- a Chinese work should produce Chinese work-scoped user / relationship
  materials
- a Chinese work should also keep work-scoped entity names and identifier
  values in Chinese by default
- generated work-scoped folder names derived from those identifiers should
  also stay in Chinese by default

Field names may remain English for structural consistency:

- JSON keys
- schema property names
- repo-level structural identifiers

But identifier values inside work-scoped canon do not need to be English.
Avoid replacing source labels with pinyin-only ids when that makes the canon
harder to inspect.

Likewise, identifier-derived path segments under `works/{work_id}/` do not
need to be English. If a canonical identifier is Chinese, the generated folder
or file segment should follow it.

The same applies to the work package root itself. If `work_id` is Chinese, the
root folders under `sources/works/` and `works/` should use that Chinese path
segment directly.

## Core Layers

### 1. Source Corpus

Stores raw and normalized novel text plus future retrieval artifacts.

### 2. Analysis

Stores incremental extraction results, evidence references, and conflict notes.

Recommended location:

- `works/{work_id}/analysis/` for persistent and incremental work-scoped
  analysis
- if scratch notes are needed, keep them under the same work package rather
  than reviving a repo-level `analysis/` directory

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
- world stage catalog
- world foundation
- power-system rules
- history timeline
- major shared event registry and event summaries
- work-stage snapshots
- world-state snapshots
- location records
- location-state snapshots
- faction records
- map graph and geography notes
- work-level cast index and brief summaries for the main cast and
  high-frequency supporting characters
- stage-scoped relationship views

These assets should be maintained incrementally.

New text may:

- expand prior world understanding
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
- world packages should prefer major shared events over small scene-level beats
  that are already better carried by character packages
- world packages should not duplicate a separate character-knowledge layer by
  default
- world packages should not be cluttered with one-off minor roles unless they
  later become structurally important
- detailed character-side event memory and interpretation should remain in the
  character package

### 4. Character Packages

Stores canon-grounded, user-independent character assets.

Each package includes:

- character manifest
- character bible
- memory timeline
- voice and behavior rules
- stage catalog keyed to the work timeline
- stage projections or stage snapshots keyed to the same work-level `stage_id`

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

`role_binding.json` should be able to store:

- the selected target character and `stage_id`
- the current user-side role mode
- if the user-side role is another canonical character, that role's
  `character_id`
- whether the user-side canon role inherits the target `stage_id`
- whether the initial setup has been locked
- loading and writeback preferences for this user-character pair

A first-pass dedicated schema for this file now exists at:

- `schemas/role_binding.schema.json`

`relationship_core` manifests, `context` manifests, `session` manifests, and
runtime request payloads should all include `work_id` explicitly so these
objects remain self-describing outside their path context.

### 6. Simulation Engine

Recommended repo-level home:

- `simulation/`

Compiles:

- world baseline
- selected world-stage snapshot
- relevant work-level event summaries
- current world-state view derived for that selected stage
- relevant location state if needed
- character canon
- selected target character stage projection
- user persona or user-side role binding
- if the user-side role is also a canonical character, that role's selected
  aligned stage projection
- user-owned long-term self profile for this work-character pair
- relationship core
- current context branch
- recent session state

into a minimal runtime context for the model.

That runtime context may depend on facts first discovered during world-first
batch extraction and later refined during targeted character extraction.

If runtime state is persisted, it should prefer user-scoped context trees
rather than `works/{work_id}/`.

During live conversation, runtime persistence should happen continuously at
the user layer:

- `sessions/` and `contexts/` should receive lightweight ongoing updates
- each active session should append to a transcript backup and turn journal on
  every input / output cycle
- `relationship_core` and `pinned_memories` should be updated more selectively
- a work-character-scoped long-term profile should be updated only when the
  user confirms a merge
- contexts may later be partially or fully merged into long-term user-owned
  history when policy and evidence allow
- merged contexts may also promote full transcript bundles into an
  account-level conversation archive library

### 7. Interfaces

Expose the same core roleplay engine to:

- direct AI agents
- frontend applications
- mobile chat MCP-style adapters

These adapters should target the engine contracts under `simulation/contracts/`
rather than reading repo files directly.

## Runtime Load Formula

At conversation start, the system should load:

`world baseline + selected world-stage snapshot + selected stage relationship snapshot + target character baseline + target stage projection + user persona or user-side role binding + optional aligned user-side canonical stage projection + long-term profile + relationship core + current context + recent session state`

Recommended load split:

- startup-required:
  - world baseline
  - selected world-stage snapshot
  - selected stage relationship snapshot
  - target character baseline
  - target stage projection
  - user summary-layer state
  - current context summaries
  - current scope archive refs
  - recent session summaries
- on-demand:
  - specific world events
  - location / faction records
  - historical ranges
  - character memory detail
  - detailed user-context history
  - account archive summaries
  - full session transcripts
  - original chapter evidence when verification is needed

When present, `works/{work_id}/indexes/load_profiles.json` should refine this
split for that work.

## Stage Selection

Stage selection should be grounded in one work-scoped stage axis rather than
in disconnected per-role free-form labels.

The world package should expose a work-scoped `stage_catalog.json`
containing:

- stage ids
- stage titles
- one-line user-facing summaries
- cumulative chapter scope or equivalent source coverage
- hints about the active world situation at that stage

Character packages should expose projections for those same `stage_id` values,
including:

- experience and memory state by that stage
- relationship state by that stage
- current personality, mood, and voice by that stage
- current status and constraints by that stage

At the beginning of a new conversation:

1. the terminal accepts or creates `user_id`
2. the system determines whether this is a new or existing setup
3. for a new setup, the system displays the work's available stages
4. the user chooses one active work-stage
5. the system binds the target character to that stage
6. if the user-side role is also canonical, that side inherits the same stage
   by default
7. the setup is locked
8. a context is created or resumed with that stage binding

Any selected canonical stage should remain compatible with the world state for
the chosen work unless the system is explicitly modeling a branch or alternate
setup.

## Relationship Memory

User-specific memory is split into:

- `long_term_profile`
  - user-owned long-term self-profile changes for one work-character pair
- `relationship_core`
  - long-lived retained memory
- `contexts/{context_id}`
  - branch-specific continuity
- `conversation_library`
  - account-level immutable archive store for merged conversation records

Contexts can later be:

- temporary
- persistent
- merged into the relationship core

Live roleplay should not wait for a separate manual writeback step before user
state is updated.

Recommended writeback rhythm:

- continuously update `sessions/` and current `contexts/`
- selectively pin or promote long-term memories
- support explicit session close via exit keywords or equivalent close intent
- after close, ask whether the current context should be merged into
  `long_term_profile` and `relationship_core`
- support explicit context promotion or full merge into user-owned long-term
  state when the user requests it or policy allows it

Runtime loading should keep a summary/detail split:

- startup may load user summaries, relationship summaries, context summaries,
  recent session summaries, and scoped archive refs
- full `transcript.jsonl` files should remain local under `users/` and be
  opened only through on-demand retrieval when exact dialogue recall is needed

Recommended location:

- `users/{user_id}/works/{work_id}/characters/{character_id}/`
