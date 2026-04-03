# Current Status

## Project Stage

Architecture scaffold created. First real work package onboarded. Early
extraction artifacts exist. No implementation code yet.

## What Exists

### Infrastructure

- Full directory scaffold, architecture docs, schemas, prompt library
- `ai_context/` handoff set
- `simulation/` runtime-engine design docs (flows, contracts, retrieval)
- First-pass schemas for all major entities (work, world, character, user,
  session, context, role binding, relationship core, long-term profile,
  runtime request, context character state)
- Expanded character-package schemas for deep roleplay support:
  - `identity.schema.json` — baseline identity
  - `voice_rules.schema.json` — per-emotion, per-target voice model
  - `behavior_rules.schema.json` — per-emotion reaction patterns, triggers
  - `memory_timeline_entry.schema.json` — subjective memory with
    misunderstanding/concealment tracking
  - `boundaries.schema.json` — hard/soft boundaries, common misconceptions
  - `failure_modes.schema.json` — AI roleplay failure prevention
  - `stage_snapshot.schema.json` — enhanced with misunderstandings,
    concealments, stage_delta
- User package template at `users/_template/`

### First Work Package: 我和女帝的九世孽缘

- Source: `sources/works/我和女帝的九世孽缘/` — 537 normalized chapters from epub
- Canon: `works/我和女帝的九世孽缘/` — world, analysis, indexes
- Candidate characters identified:
  `works/我和女帝的九世孽缘/analysis/incremental/candidate_characters_initial.md`
- Batch plan:
  `works/我和女帝的九世孽缘/analysis/incremental/source_batch_plan.md`
- World batch 1 complete (阶段1_南林初遇):
  - `world/stage_catalog.json`
  - `world/stage_snapshots/阶段1_南林初遇.json`
  - First-pass foundation, events, locations, factions, cast, social files
- Next batch: `batch_002` (chapters 0011-0020)

## Current Gaps

- No finished character package yet
- No real user package yet (only template)
- No simulation-engine service implementation
- No terminal adapter implementation
- No automated ingestion or extraction pipeline
- World schemas incomplete (no formal schema for foundation, timeline, events,
  locations, maps, state snapshots)
- Character baseline files (relationships.json, bible.md) still lack schemas
- Full extraction workflow not yet formally defined end-to-end
- No final roleplay prompt produced

## Rules In Effect

- Content language follows work language (Chinese for Chinese works)
- `ai_context/` is English for AI handoff
- Real user packages stay local (not committed)
- Full novels, databases, indexes, large artifacts not committed
- `works/*/analysis/incremental/` and `works/*/indexes/` are git-tracked
- `docs/logs/` is write-mostly; do not proactively read
- No per-batch report files; use progress files in-place
- Default batch size: 10 chapters (configurable per work)
