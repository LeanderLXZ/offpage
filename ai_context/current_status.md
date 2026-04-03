# Current Status

## Project Stage

Architecture scaffold created. First real work package onboarded. Automated
extraction orchestrator built but not yet tested end-to-end. No runtime
implementation code yet.

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
- Canon directory: `works/我和女帝的九世孽缘/` — **currently empty** (previous
  extraction products were cleaned from git history)
- No `extraction_progress.json` exists — next run must start fresh
- Previous batch 1 world extraction existed but needs to be re-done

### Automated Extraction Orchestrator

- `automation/` directory with Python package `persona_extraction`
- CLI entry point: `persona-extract` command
- LLM backend abstraction supporting Claude CLI and Codex CLI
- Progress tracking with state machine (pending → committed)
- Two-layer quality check: programmatic (jsonschema) + semantic (LLM reviewer)
- Git integration: extraction branch, per-batch commits, auto-rollback
- Prompt templates: analysis, coordinated extraction, semantic review
- Breakpoint recovery via progress file

### Schema Documentation

- `docs/architecture/schema_reference.md` — complete index of all schemas
  with usage, locations, and runtime loading rules

## Current Gaps

- No finished character package yet
- No real user package yet (only template)
- No simulation-engine service implementation
- No terminal adapter implementation
- World schemas incomplete (no formal schema for foundation, timeline, events,
  locations, maps, state snapshots)
- Character baseline files (relationships.json, bible.md) still lack schemas
- No final roleplay prompt produced
- Automated extraction pipeline exists but not yet tested end-to-end

## Rules In Effect

- Content language follows work language (Chinese for Chinese works)
- `ai_context/` is English for AI handoff
- Real user packages stay local (not committed)
- Full novels, databases, indexes, large artifacts not committed
- `works/*/analysis/incremental/` and `works/*/indexes/` are git-tracked
- `docs/logs/` is write-mostly; do not proactively read
- No per-batch report files; use progress files in-place
- Batches split by natural story boundaries (target 10 ch, min 5, max 20)
