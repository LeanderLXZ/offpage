# Self-Contained Stage Snapshot Model

## Overview

Each `stage_snapshots/{stage_id}.json` is **self-contained**: it includes the
complete character state for that stage (voice, behavior, boundaries,
relationships, personality, knowledge, mood). Runtime loads a single snapshot
and does not need to merge it with baseline files.

## Baseline Files: Extraction Anchor Only

Baseline files (`voice_rules.json`, `behavior_rules.json`, `boundaries.json`)
still exist in the character package. Their role:

- **Extraction anchor**: stage 1 extraction fills baseline files as the starting
  reference. Subsequent stages use baseline as a comparison point to understand
  what changed, but the stage snapshot itself is self-contained.
- **Cross-stage reference**: baseline represents the character's "initial state"
  and can be useful for understanding the arc of change.
- **Not loaded at runtime**: runtime loads `identity.json` + `failure_modes.json`
  + the selected stage snapshot. Baseline voice/behavior/boundary files are not
  part of the startup packet.

## What Is Loaded at Runtime

| File | When |
|---|---|
| `identity.json` | Tier 0 startup (immutable identity) |
| `failure_modes.json` | Tier 0 startup (AI safety rules, stage-independent) |
| `boundaries.json` → `hard_boundaries` only | Tier 0 startup (immutable hard limits) |
| `stage_snapshots/{stage_id}.json` | Tier 0 startup (complete stage state) |
| `memory_timeline/{stage_id}.jsonl` × stages 1..N | Tier 0 startup (historical memories) |
| Past `stage_snapshots/{past_stage_id}.json` | Tier 1 on-demand (deep historical recall) |

## Extraction Workflow

- **Batch 1 (stage 1)**: fill baseline files AND stage 1 snapshot. Stage 1
  snapshot should be self-contained (effectively a copy of baseline content
  plus stage-specific fields like events, mood, relationships).
- **Batch N (stage N)**: use baseline + prior stage snapshots as reference.
  Produce a new self-contained stage N snapshot with the complete state for
  that stage. Unchanged content from prior stages should still be included
  in the snapshot — do not omit it.
- `stage_delta` records what changed from the previous stage, for human and
  AI understanding of the arc. This is informational, not a merge instruction.

## Why Self-Contained

- **Simpler runtime**: AI reads one document, no merge logic needed.
- **More reliable**: no risk of merge errors or missing overrides.
- **Independently verifiable**: each stage can be reviewed on its own.
- **History recall is separate**: past-stage details come from memory_timeline
  and on-demand loading of past stage snapshots, not from the override mechanism.
