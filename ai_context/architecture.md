# Architecture Snapshot

For full details see `docs/architecture/system_overview.md` and
`docs/architecture/data_model.md`. This file is the compressed summary.

## Top-Level Structure

- `sources/` — raw novel inputs and normalized source work packages
- `works/` — source-grounded canonical work packages (world, characters,
  analysis, indexes)
- `users/` — all user-specific mutable state, grouped by `user_id`
- `simulation/` — runtime-engine lifecycle, retrieval, service contracts
- `prompts/` — reusable prompt templates for agents and user-facing flows
- `schemas/` — persistence and runtime-request schemas
- `interfaces/` — future terminal adapters (agent, app, MCP)
- `docs/architecture/` — formal architecture docs
- `ai_context/` — compressed handoff for future AI sessions

## System Layers

1. **Source** (`sources/works/{work_id}/`) — raw text, normalized chapters,
   metadata
2. **Extraction** (`works/{work_id}/analysis/`) — incremental batch extraction,
   evidence, conflicts
3. **World** (`works/{work_id}/world/`) — world foundation, stages, events,
   locations, factions, cast, social relationships
4. **Character** (`works/{work_id}/characters/{character_id}/`) — bible,
   memory, voice, behavior, stage projections
5. **User** (`users/{user_id}/`) — one locked binding per user; role binding,
   long-term profile, relationship core, contexts, sessions
6. **Simulation Engine** (`simulation/`) — bootstrap, load, retrieval,
   continuous writeback, close/merge flow
7. **Interface** (`interfaces/`) — terminal adapters (future)

## Key Boundaries

- Work-scoped canon under `works/`, user-mutable state under `users/`.
- User conversations never rewrite canonical world or character data.
- One `user_id` = one locked work-target-counterpart binding.
- Chinese works use Chinese identifiers and path segments by default.
- JSON field names may remain English; content text follows work language.

## Runtime Load Formula

Startup loads (in order):

1. World baseline + selected world-stage snapshot + stage relationships
2. Target character baseline + selected stage projection
3. User role binding + long-term profile + relationship core
4. Current context manifest + character_state + relationship_state + shared
   memory
5. Recent session summaries

On-demand: events, locations, factions, history, full transcripts, archive
records, raw source chapters.

See `simulation/retrieval/load_strategy.md` for the full tier model.

## Stage Model

- World package exposes a `stage_catalog.json` with selectable timeline nodes.
- Character packages project the same `stage_id` into character-specific state.
- Stage N is cumulative through 1..N; the latest stage is the active present.
- User selects a stage at setup; it applies to target character and any
  canon-backed user-side role by default.

## Context Lifecycle

- States: `ephemeral` → `persistent` → `merged`
- Session/context state updates **continuously** during live roleplay.
- `character_state.json` in each context tracks real-time character changes
  (mood, personality drift, voice drift, agreements, events, memories).
- `long_term_profile` and `relationship_core` update **only after explicit
  merge confirmation** at session close.
- Merge is append-first, not destructive overwrite.

## Self-Contained Stage Snapshots

Each `stage_snapshots/{stage_id}.json` is **self-contained**: it includes the
complete character state for that stage (voice_state, behavior_state,
boundary_state, relationships, personality, mood, knowledge). Runtime loads
a single snapshot directly — no baseline merge needed.

Baseline files (`voice_rules.json`, `behavior_rules.json`, `boundaries.json`)
still exist as extraction anchors but are **not loaded at runtime**. Only
`identity.json`, `failure_modes.json`, and `hard_boundaries` are loaded
alongside the stage snapshot.

See `simulation/contracts/baseline_merge.md` for the full model description.

## Inter-Character Relationship Evolution

- `relationships` in each stage snapshot records per-target attitude, trust,
  intimacy, guardedness, voice/behavior shifts, driving events, target's
  known status (as perceived by this character), and a relationship history
  summary from stage 1 to present.
- `stage_delta.personality_changes` and `stage_delta.relationship_changes`
  are structured objects that require attribution (which character or event
  caused the change).
- Memory timeline is split per-stage: `canon/memory_timeline/{stage_id}.jsonl`.
  Loading stage N reads files for stages 1..N at startup.

## Historical Recall and Cognitive Conflict

- Historical recall (past nicknames, speech habits, knowledge state) is served
  by memory_timeline + relationship_history_summary at startup. Past stage
  snapshots are loaded on-demand for deeper detail.
- Cognitive conflict (e.g., character believes someone is dead but they appear)
  is handled by runtime prompt rules, not pre-written scenario data.
- See `prompts/runtime/历史回忆处理规则.md` and
  `prompts/runtime/认知冲突处理规则.md`.

## Roleplay Logic Chain

`memory and relationship → psychological reaction → behavior decision → language realization`

Not: `surface tone imitation → generic reply`
