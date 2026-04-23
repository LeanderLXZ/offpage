<!--
MAINTENANCE — 更新 ai_context/ 前读：这是 AI 快速 follow 项目的索引，不是详细手册。
1. 写"是什么 / 在哪找"，指向权威源（代码路径 / docs/*.md / schema / log）
2. 优先删而不是加；新增前先看能否合并已有条目
3. 只写当前设计，不写"旧 / legacy / 已废弃 / 原为"
4. 不出现真实书名 / 角色 / 剧情，用通用占位符（`<work_id>`, `角色A`, `S001`）
5. 预算：architecture / decisions / requirements 各 ≤ ~150 行；全目录读完 ≤ 几千 token
-->

# Current Status

## Project Stage

Architecture scaffold done. One work package under automated extraction.
Phase 0/1/2/2.5/4 complete; Phase 3 in progress — S001 committed
(sha `3bf25bf`), S002 in ERROR awaiting `--resume`, S003–S049 pending.
No runtime code yet.

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
- S001 committed (sha `3bf25bf`, 2026-04-22)
- S002 ERROR awaiting `--resume` (preflight false-positive from 2026-04-22 working-tree state)
- S003–S049 pending

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
- `docs/logs/` + `docs/review_reports/` write-mostly — do not proactively read
- No per-stage report files; progress updated in-place
- Stages split by natural story boundaries (target 10, min 5, max 15)
