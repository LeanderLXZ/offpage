<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `Character A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# Requirements — Compressed Index

Authoritative source: `docs/requirements.md` (Chinese). Each section
below summarises in a few lines + points to the corresponding section
there for full text.

## §1 Overall Goal

Long-lived novel character roleplay. Deep behavior / memory /
relationship consistency, not surface tone mimicry. Arbitrary
characters, stage-based state, multi-terminal.

## §2 Stage Model

- Natural story-boundary splits (target 10, min 8, max 15). Every
  boundary propagates to world / character / memory / retrieval.
- Stage N cumulative through 1..N; latest stage = "now".
- Shared `stage_id` (`S###`, 3-digit zero-pad) across world / character /
  memory; paired `stage_title` (short label, work language — exact cap
  in schema) for bootstrap selector.
- Cross-stage recall uses behavioral details (nicknames, speech,
  attitude, knowledge state), not just event summaries.
- → `docs/requirements.md` §2.

## §3 Three Deep-Roleplay Goals

1. Structured character data (identity with `core_wounds` +
   `key_relationships` as character-level constant; per-stage snapshot
   with personality, triggers, goals vs obsessions, relationships,
   voice, boundaries, failure modes, `character_arc`).
2. Character-perspective memory (subjective, not plot summary).
3. Stable voice + behavior per emotion / target / situation.
- → `docs/requirements.md` §3.

### §3.1 Identity / Name Tracking

Multi-name tracking (alias types: real name / alias / appellation /
form of address / honorific title / Daoist title — across stage range
and source) under a stable `character_id`. **Cross-chunk identity
merging** in the analysis phase is mandatory.
→ `docs/requirements.md` §3.1 + `schemas/character/identity.schema.json`.

## §4 Runtime Loading

Six categories: basic identity / personality core / speech style /
memory / behavior rules / forbidden deviations. Plus cognitive conflict
and historical recall rules. Full formula → `architecture.md` §Runtime
Load Formula + `simulation/retrieval/load_strategy.md`.

## §5 User Flow

New: work → character → stage → self-role → user package → context.
Existing: load account → select / create context. One-time setup lock
(changes need new package or explicit migration). Close / merge:
selective long-term promotion. Per-turn journaling for crash recovery;
merged contexts = immutable account history.
→ `docs/requirements.md` §5.

## §6 Data Separation

Objective vs subjective; canon vs inference; character canon vs user
data; knowledge boundaries; stage boundaries; multi-work namespaces;
content-language consistency. Hard schema gates in `conventions.md`
§Data Separation.

## §7 Information Layering

Five layers: immutable (identity + target_baseline — both character-level
constants produced in phase 2; target_baseline anchors phase 3 target keys
via cross-file `set-equal` check at the phase 3 single-stage validate layer,
violations route through the file-level repair lifecycle; `targets` cap
via shared `schemas/character/targets_cap.schema.json` $ref, also
referenced by stage_snapshot's three target structures) / self-contained
stage snapshot (carries
inline failure_modes / voice_state / behavior_state / boundary_state) /
historical memory (timeline + digests + FTS5) / session-mutable (per-turn
context state) / cross-session (long_term_profile + relationship_core,
merge-only).
Load tiers: startup core → structured on-demand → transcript recall →
raw source.
→ `docs/requirements.md` §7 + `architecture.md` §Runtime Load Formula.

## §8 Source Ingestion

Formats TXT / EPUB / MOBI / HTML / user excerpts. Pipeline: raw →
normalize → chapter split (zero-padded) → metadata. Source package =
input layer, never modified downstream, excluded from git. Chinese
works → Chinese `work_id`.
→ `docs/requirements.md` §8 + `extraction/ingestion/`.

## §9 Extraction Process — Phase 0–4

Phase 0 chapter summarization (parallel chunks; each chunk carries
chunk-level analysis fields — `chunk_arc_summary` / `chunk_world_rules`
/ `chunk_power_levels` / `chunk_factions` / `chunk_regions`) → Phase 1
global analysis (monolithic mode = 3 parallel lanes
`foundation` / `stage_plan` / `candidate_characters`; light_novel mode
= 2 lanes `foundation` + `candidate_characters` with orchestrator
程序化 `_build_light_novel_stage_plan`, decision #52) → Phase 1.5
active character confirmation → Phase 2 baseline production (per-character
`identity.json` + `target_baseline.json` + `fixed_relationships.json`
+ `manifest.json` + foundation `major_factions[].key_figures` 替换;
single LLM call, decision #54) → Phase 3 coordinated stage extraction
(world + per-character snapshot per stage, with file-level repair
lifecycle) → Phase 4 scene archival → package validation.
Self-contained snapshots per stage (stage N = complete current state,
including unchanged fields).
→ `docs/requirements.md` §9.

## §10 Output Quality Protection

- §10.1 Runtime anti-dilution — anchor re-injection, rolling session
  state, deep calibration checkpoints. Implemented by
  `simulation/prompt_templates/`.
- §10.2 Extraction cross-stage quality — fresh context per stage (no
  in-session dilution); protected by prompt_builder schema injection,
  validator + semantic review, Phase 3.5 consistency check.
- → `docs/requirements.md` §10.

## §11 Automated Extraction Pipeline

Python orchestrator at `extraction/persona_extraction/`. Phase 0
parallel summarization → Phase 1 analysis → Phase 1.5 user confirm →
Phase 2 baseline → Phase 3 stage loop (1+2N split extraction, PP,
repair agent, commit) → Phase 3.5 cross-stage consistency → Phase 4
scene archive (independent). Supports Claude CLI and Codex CLI backends.

- Repair agent (per-stage quality gate) → `extraction/repair/` +
  `docs/requirements.md` §11.4
- Token-limit auto-pause → `docs/requirements.md` §11.13 +
  `extraction/persona_extraction/core/rate_limit.py`
- Full pipeline detail → `architecture.md` §Automated Extraction
  Pipeline + `extraction/README.md` +
  `docs/architecture/extraction_workflow.md`.

## §12 Memory System and Retrieval

Three-layer memory: `stage_snapshot` (aggregated state) /
`memory_timeline` (subjective process) / `scene_archive` (original text
split by scene). Two-level retrieval funnel on `scene_archive` +
`memory_timeline`:

- Level 1 (default, <20ms) — jieba + work-level vocab dict + FTS5 →
  top-K summaries → LLM judges relevance.
- Level 2 (fallback, rare) — LLM `search_memory` tool → embedding
  search on summary vectors.

Proactive context-state association (location / recent events /
emotion) for jieba matching each turn. Tech: `jieba` + `sqlite FTS5` +
optional `bge-large-zh-v1.5`. Single SQLite — no separate vector DB.
Vocab dict at `works/{work_id}/indexes/vocab_dict.txt` (committed);
retrieval artifacts under `works/{work_id}/retrieval/` (not committed);
`scene_archive` produced in Phase 4, fully regenerated on merge.

→ `docs/requirements.md` §12 +
`simulation/retrieval/index_and_rag.md`.
