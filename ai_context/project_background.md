# Project Background

Long-lived novel character roleplay system. A reusable character-asset
system that can be updated and loaded across sessions — not a one-off
prompt experiment.

## Goal

Deep, stable roleplay of specific novel characters — consistent
personality, memory, knowledge boundaries, and behavioral patterns across
long conversations and multiple sessions.

## Guiding Principles

- **Deep roleplay over surface mimicry.** Behavioral and decision
  consistency is the priority; tone is secondary.
- **The original novel is the highest authority.** All character data
  traces back to source text.
- **Incremental, not from scratch.** Long novels processed in stages;
  character data builds up over time.
- **Layered, not one giant prompt.** Source, world, character, user,
  runtime state — each in its own layer with clear boundaries.

## Build Order

1. Character-asset system (schemas, data model)
2. Extraction workflows (stage processing, incremental updates)
3. Runtime roleplay engine (loading, retrieval, session management)
4. Terminal integrations (agent, app, MCP)

For requirements see `requirements.md`; for architecture see
`architecture.md`.
