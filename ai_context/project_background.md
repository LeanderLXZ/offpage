<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `Character A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# Project Background

Long-lived novel character roleplay system. A reusable character-asset
system that can be updated and loaded across sessions — not a one-off
prompt experiment.

## Goal

Deep, stable roleplay of specific novel characters — consistent
personality, memory, knowledge boundaries, and behavioral patterns
across long conversations and multiple sessions.

## Guiding Principles

- **Deep roleplay over surface mimicry.** Behavioral / decision consistency is priority; tone is secondary.
- **Original novel = highest authority.** All character data traces to source text.
- **Incremental, not from scratch.** Long novels processed in stages; data builds over time.
- **Layered, not one giant prompt.** Source / world / character / user / runtime — each layer has clear boundaries.

## Build Order

1. Character-asset system (schemas, data model)
2. Extraction workflows (stage processing, incremental updates)
3. Runtime roleplay engine (loading, retrieval, session management)
4. Terminal integrations (agent, app, MCP)

Requirements → `requirements.md`. Architecture → `architecture.md`.
