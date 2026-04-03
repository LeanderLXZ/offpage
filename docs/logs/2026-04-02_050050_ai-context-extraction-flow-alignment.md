# AI Context Extraction Flow Alignment

Date: `2026-04-02 05:00:50` America/New_York

## Why

`ai_context/` still carried an older durable memory that described extraction
as a strict `world-first -> selected-character` sequence. The current prompt
library and work-local extraction flow had already moved to a coordinated
batch model:

- identify candidates first
- confirm the active character set early
- read each batch once
- co-produce world updates and relevant character updates from that same batch
- reserve targeted character supplement for genuine gaps

`ai_context/architecture.md` also still mentioned a world-side
`character-event awareness` output that is no longer part of the current
`world/` structure.

## What Changed

- updated `ai_context/current_status.md`
- updated `ai_context/handoff.md`
- updated `ai_context/next_steps.md`
- updated `ai_context/decisions.md`
- updated `ai_context/architecture.md`

## Result

Durable AI handoff memory now matches the current extraction architecture:

- progress-first continuation still applies
- temporary world-only batches are allowed when no active character set exists
  yet or the batch is overwhelmingly shared-world material
- once active characters exist, the default is coordinated same-batch world
  plus character extraction
- targeted character supplement remains a fallback rather than the primary
  default
