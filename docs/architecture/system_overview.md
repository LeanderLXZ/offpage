# System Overview

## Goal

Build a reusable, multi-terminal character roleplay engine for long-form
novels.

The system should support:

- extracting one or many characters from a novel
- preserving canon-grounded character packages
- preserving user-specific relationship growth separately
- choosing a character stage at conversation start
- loading the same core logic through agent, app, and MCP terminals

## Core Layers

### 1. Source Corpus

Stores raw and normalized novel text plus future retrieval artifacts.

### 2. Analysis

Stores incremental extraction results, evidence references, and conflict notes.

### 3. Character Packages

Stores canon-grounded, user-independent character assets.

Each package includes:

- character manifest
- character bible
- memory timeline
- voice and behavior rules
- stage catalog
- stage snapshots

### 4. User Packages

Stores user identity, persona, relationship cores, context branches, and
session history.

This is where long-term relationship memory and user-specific character drift
belong.

### 5. Runtime Compilation

Compiles:

- character canon
- selected character stage
- user persona
- relationship core
- current context branch
- recent session state

into a minimal runtime context for the model.

### 6. Interfaces

Expose the same core roleplay engine to:

- direct AI agents
- frontend applications
- mobile chat MCP-style adapters

## Runtime Load Formula

At conversation start, the system should load:

`character baseline + stage snapshot + user persona + relationship core + current context + recent session state`

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
