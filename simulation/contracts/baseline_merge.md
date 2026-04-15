# Self-Contained Stage Snapshot Model

## Overview

Each `stage_snapshots/{stage_id}.json` is **self-contained**: it includes the
complete character state for that stage (voice, behavior, boundaries,
relationships, personality, knowledge, mood). Runtime loads a single snapshot
and does not need to merge it with baseline files.

## Baseline Files: Extraction Anchor Only

Baseline files (`voice_rules.json`, `behavior_rules.json`, `boundaries.json`,
`failure_modes.json`) still exist in the character package. They record
**cross-stage stable character foundations** — the character's inherent style,
behavior patterns, boundaries, and failure modes. Stage-specific changes
(voice shifts, behavior drift, emotional fluctuations) are covered by
stage snapshots. Their role:

- **Extraction anchor**: Phase 2.5 produces skeleton baselines (source_type:
  inference) from full-book summaries. Subsequent stages refine them with
  raw text evidence (upgrading inference to canon).
- **Cross-stage reference**: baseline represents the character's stable core
  and can be useful for understanding the arc of change.
- **Partially loaded at runtime**: `failure_modes.json` and `boundaries.json`
  (`hard_boundaries` only) are loaded at Tier 0 startup. `voice_rules.json`
  and `behavior_rules.json` are NOT loaded — voice and behavior state is
  self-contained in the stage snapshot.

## What Is Loaded at Runtime

| File | When |
|---|---|
| `identity.json` | Tier 0 startup (immutable identity) |
| `failure_modes.json` | Tier 0 startup (AI safety rules, stage-independent) |
| `boundaries.json` → `hard_boundaries` only | Tier 0 startup (immutable hard limits) |
| `stage_snapshots/{stage_id}.json` | Tier 0 startup (complete stage state) |
| `memory_timeline/{stage_id}.json` × stages 1..N | Tier 0 startup (historical memories) |
| Past `stage_snapshots/{past_stage_id}.json` | Tier 1 on-demand (deep historical recall) |

## Extraction Workflow

- **Phase 2.5 (baseline production)**: `identity.json`, `manifest.json`,
  `voice_rules.json`, `behavior_rules.json`, `boundaries.json`,
  `failure_modes.json` are produced from full-book chapter summaries as
  skeleton drafts (source_type: inference). `world/foundation/foundation.json`
  is also produced at this stage.
- **Stage 1 (stage 1)**: review and correct all Phase 2.5 baseline drafts
  with raw text evidence. Produce stage 1 snapshot (self-contained).
- **Stage N (stage N)**: use baseline + prior stage snapshots as reference.
  Produce a new self-contained stage N snapshot with the complete state for
  that stage. Unchanged content from prior stages should still be included
  in the snapshot — do not omit it. Any stage may correct any existing
  baseline file.
- `stage_delta` records what changed from the previous stage, for human and
  AI understanding of the arc. This is informational, not a merge instruction.
- `character_arc` provides a bird's-eye view from stage 1 to the current
  stage (arc_summary, key nodes, current_position). Complements stage_delta.

## Why Self-Contained

- **Simpler runtime**: AI reads one document, no merge logic needed.
- **More reliable**: no risk of merge errors or missing overrides.
- **Independently verifiable**: each stage can be reviewed on its own.
- **History recall is separate**: past-stage details come from memory_timeline
  and on-demand loading of past stage snapshots, not from the override mechanism.
