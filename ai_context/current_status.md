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

Architecture scaffold done; schemas + extraction pipeline + simulation
design landed. No runtime code yet. Per-work extraction state lives in
`works/{work_id}/analysis/progress/`, not here — `ai_context/` tracks
framework-level engineering progress only.

## What Exists

- Full directory scaffold + formal architecture docs (`docs/architecture/`)
- Character + world + user schemas — complete index at `docs/architecture/schema_reference.md`
- Simulation-engine **design** only (no implementation) — `simulation/` flows, contracts, retrieval, prompt templates
- Manual-scenario prompts — `prompts/` (ingest, review, supplement, cold start)
- Automated extraction orchestrator — `automation/persona_extraction/` + CLI `persona-extract`; pipeline detail in `architecture.md` §Automated Extraction Pipeline + `automation/README.md`
- User package template at `users/_template/` (no real user package)

## Current Gaps

- Extraction pipeline not yet exercised end-to-end (no character package completed)
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
- The following `works/*` tracking rules apply only to `extraction/{work_id}` and `library` branches; `main` is framework-only and contains no `works/{work_id}/` artefacts (only `works/README.md`):
  - `works/*/analysis/`: only `world_overview`, `stage_plan`, `candidate_characters`, `consistency_report` tracked; `progress/`, `chapter_summaries/`, `scene_splits/`, `evidence/*` local
  - `works/*/world/`, `works/*/characters/`, `works/*/indexes/` tracked; `works/*/retrieval/` local
- `logs/change_logs/` + `logs/review_reports/` write-mostly — do not proactively read
- No per-stage report files; progress updated in-place
- Stages split by natural story boundaries (target 10, min 5, max 15)
