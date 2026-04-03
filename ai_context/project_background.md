# Project Background

## What This Project Is

A long-lived novel character roleplay system. Not a one-off prompt experiment
or a temporary character card. The goal is a reusable character-asset system
that can be updated, corrected, and loaded by AI systems over time.

## Why It Exists

The user wants AI to perform deep, stable roleplay as specific novel
characters — maintaining consistent personality, memory, knowledge boundaries,
and behavioral patterns across long conversations and multiple sessions.

## Guiding Principles

- **Deep roleplay over surface mimicry.** The priority is behavioral and
  decision consistency, not just matching a character's tone of voice.
- **The original novel is the highest authority.** All character data must
  trace back to source text evidence.
- **Incremental, not from scratch.** The system processes long novels in
  batches and builds up character data over time.
- **Structured layers, not one giant prompt.** Source text, world data,
  character data, user data, and runtime state are kept in separate layers
  with clear boundaries.

## Architectural Mindset

Build in this order:

1. Character-asset system (schemas, data model)
2. Extraction workflows (batch processing, incremental updates)
3. Runtime roleplay engine (loading, retrieval, session management)
4. Terminal integrations (agent, app, MCP)

For specific requirements, see `requirements.md`. For architecture details,
see `architecture.md`.
