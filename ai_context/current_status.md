<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `Character A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# Current Status

## Project Stage

Architecture scaffold done. One work package under automated extraction.
Phase 0/1/1.5/2/4 complete; Phase 3 in progress — S001 + S002 committed,
S003 in ERROR awaiting `--resume`, S004–S049 pending. Phase 3.5 pending
(blocked on all-stages-COMMITTED). No runtime code yet.

## What Exists

- Full directory scaffold + formal architecture docs (`docs/architecture/`)
- Character + world + user schemas — complete index at `docs/architecture/schema_reference.md`
- Simulation-engine **design** only (no implementation) — `simulation/` flows, contracts, retrieval, prompt templates
- Manual-scenario prompts — `prompts/` (ingest, review, supplement, cold start)
- Automated extraction orchestrator — `automation/persona_extraction/` + CLI `persona-extract`; pipeline detail in `architecture.md` §Automated Extraction Pipeline + `automation/README.md`
- User package template at `users/_template/` (no real user package)
- One first work package in progress (Chinese web novel, 500+ chapters)

## First Work Package — Phase 3 State

- 2 target characters confirmed
- S001 committed (sha `991c09f`, 2026-04-23)
- S002 committed (sha `7639c8b`, 2026-04-23)
- S003 ERROR (`char_support` lane — `error_max_turns`); awaiting `--resume`
- S004–S049 pending
- Phase 3.5 pending — blocked on all stages `COMMITTED`

Resume command → `handoff.md` §Current Work Continuation.

## Current Gaps

- No finished character package yet (Phase 3 in progress)
- No real user package (only template)
- No simulation-engine service implementation
- No terminal adapter implementation
- No retrieval implementation (design finalized, awaiting extraction output)
- World schemas partially informal (foundation, timeline, events, locations, maps, state snapshots — foundation skeleton in `automation/prompt_templates/baseline_production.md`)
- No final roleplay prompt produced

## Rules In Effect

- Content language = work language; `ai_context/` stays English
- Real user packages stay local
- No novels / databases / indexes / large artifacts in git
- `works/*/analysis/`: only `world_overview`, `stage_plan`, `candidate_characters`, `consistency_report` tracked; `progress/`, `chapter_summaries/`, `scene_splits/`, `evidence/*` local
- `works/*/world/`, `works/*/characters/`, `works/*/indexes/` tracked; `works/*/retrieval/` local
- `logs/change_logs/` + `logs/review_reports/` write-mostly — do not proactively read
- No per-stage report files; progress updated in-place
- Stages split by natural story boundaries (target 10, min 5, max 15)
