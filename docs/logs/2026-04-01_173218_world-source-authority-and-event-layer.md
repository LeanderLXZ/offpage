# 2026-04-01 17:32:18 - World Source Authority And Event Layer

## Summary

The world-data rules were clarified in two important ways.

First, world materials are allowed to be revised incrementally as more of the
source work is read, but those revisions must be driven by source-text
evidence only. User dialogue, runtime branches, and user-character
relationship drift must not rewrite canonical world foundation, world history,
world-state facts, or major event records.

Second, the world layer should track major work-level events in addition to
static setting. Those event records are shared simulation inputs that may be
relevant to many characters.

## Practical Consequences

- `world/` should include concise major-event records.
- `world/` may include concise per-character event-awareness summaries.
- Detailed character-side event memory, emotional interpretation, and
  roleplay-specific meaning should remain under `characters/{character_id}/`.
- Runtime compilation should be able to load relevant shared world events
  before applying character-stage and character-knowledge filters.
