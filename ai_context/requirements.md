# Requirements (Compressed English Reference)

Authoritative source: `docs/requirements.md` (Chinese). This file is a
quick-reference index only.

## §1 Overall Goal

Long-lived novel character roleplay. Deep roleplay, not surface mimicry.
Arbitrary characters, stage-based state, long-term memory, multi-terminal.

## §2 Stage Model

- Stage splitting is the analysis phase's most critical output — every
  boundary propagates to all downstream structures (world / character
  snapshots, memory timelines, runtime stage selection). Story-boundary
  accuracy matters more than chapter counts. Target 10, min 5, max 15;
  variable per stage. Stage N cumulative through 1..N.
- Selected stage = "now"; prior stages = history. Current-stage
  personality / voice only.
- World snapshots: foundation (setting, power system, cosmology) + entity
  tracking (events, locations, factions, cast) + fixed vs dynamic
  relationships + per-stage snapshots sharing `stage_id` with character
  snapshots.
- Character snapshots: events, status, personality / voice shifts, mood,
  relationships.
- Inter-character relationships evolve per stage (attitude, trust,
  intimacy, event-driven transitions, knowledge boundaries, concealment,
  mutual influence).
- Cross-stage historical recall uses behavioral details (nicknames,
  speech, attitude, knowledge state), not just event summaries;
  current-stage personality interprets recall.
- Stage selection: one-line summary per stage, fixed for the context.

## §3 Three Deep-Roleplay Goals

1. Structured character data (identity with `core_wounds` and
   `key_relationships`, personality, triggers, goals vs obsessions,
   relationships, memories, language style, boundaries, failure modes,
   `character_arc`)
2. Character-perspective memory (subjective, not objective plot summary)
3. Stable voice + behavior per emotion, per target, per situation

### §3.1 Identity / Name Tracking

Characters may carry multiple names across disguise / amnesia / aliases,
unnamed-then-named, dao-name / honorific changes, dual identity, or
relationship-based nicknames. Requirements: stable `character_id` (never
changes); aliases list with name, type (本名/化名/代称/称呼/封号/道号),
stage range, source. Extraction must match new names against existing
aliases before creating new entities. Runtime loads aliases with the
stage snapshot.

Analysis-phase **cross-chunk identity merging** is mandatory — chunk
summarization processes independently, so the global analysis phase must
unify aliases before emitting candidates.

## §4 Runtime Loading

Six categories: basic identity, personality core, speech style, memory
library, behavior rules, forbidden deviations. Plus runtime rules for
cognitive conflict and historical recall processing.

## §5 User Flow

- New user: work → character → stage → self-role → user package → context
- Existing user: load account → select / create context
- One-time setup lock; changes need new package or explicit migration
- Close / merge: exit keyword → merge prompt → selective long-term promotion
- Context tracks real-time state; long-term profile updates only on merge
- Per-turn journaling for crash recovery; merged contexts = immutable
  account history

## §6 Data Separation

Objective vs subjective; canon vs inference; character canon vs user
data; knowledge boundaries; stage boundaries; multi-work namespaces;
content language consistency (work language → all generated content
including user data).

## §7 Information Layering

Five layers:

1. Immutable — identity (incl. `core_wounds` + `key_relationships`),
   `hard_boundaries`, `failure_modes`
2. Self-contained stage snapshot — voice / behavior / boundary /
   relationship + `character_arc`, loaded directly, no baseline merge.
   `target_voice_map` / `target_behavior_map` filtered by user role at
   load time. Fallback: if current snapshot lacks a matching target, the
   engine scans backwards through previous snapshots (pure code I/O).
3. Historical memories — memory_timeline recent 2 stages full;
   `memory_digest.jsonl` compressed index for distant; FTS5 on-demand for
   rest; past snapshots on-demand.
4. Session-mutable — context state, updated per turn.
5. Cross-session — `long_term_profile`, `relationship_core`, merge-only.

Baseline files (`voice_rules.json`, `behavior_rules.json`,
`boundaries.json`) = extraction anchors only, NOT loaded at runtime.

Load tiers: startup core → structured on-demand → transcript recall →
raw source verification. Per-work config can customize.

## §8 Source Ingestion

Formats: TXT, EPUB, MOBI, HTML, user excerpts. Pipeline: raw →
normalize (UTF-8, clean) → chapter split (zero-padded) → metadata. Source
package = input layer, never modified downstream, excluded from git.
Chinese works use Chinese `work_id`.

## §9 Extraction Process

Seven steps: ingest → chapter summarization (parallel chunks) → global
analysis (identity merge → world overview → stage plan → candidates →
baseline production) → active character confirmation → coordinated stage
extraction (world + character per stage; may correct baselines) →
targeted supplement → package validation.

Self-contained snapshots: stage 1 ≈ baseline + stage; stage N =
complete current state (unchanged fields included); baseline =
extraction anchor only.

## §10 Output Quality Protection

- **§10.1 Runtime anti-dilution** (long conversations): anchor
  re-injection, rolling session state, deep calibration checkpoints.
- **§10.2 Extraction cross-stage quality** (fresh context per stage, no
  in-session dilution): satisfied by prompt_builder schema injection,
  validator + semantic review, Phase 3.5 consistency check. No extra
  dilution code needed.

## §11 Automated Extraction Pipeline

Python orchestrator in `automation/`. Phase 0 parallel summarization
(`--concurrency`, default 10) → Phase 1 analysis → Phase 2 user confirm
→ Phase 2.5 baseline production → Phase 3 stage loop (1+2N split
extraction: 1 world + N char_snapshot + N char_support, post-processing,
repair agent, git commit) → Phase 3.5 cross-stage
consistency → Phase 4 scene archive (independent).

**Repair agent** (`automation/repair_agent/`) replaces per-lane review,
commit gate, and fix cascade. Field-level surgical patches via json_path
(no whole-file rollback). Four-layer checkers (L0–L3) × four-tier fixers
(T0–T3), orthogonal. Fixers escalate from lowest available tier per
issue category. Semantic LLM at most 2 calls (initial + final verify).
Repair fail → stage ERROR; `--resume` resets ERROR → PENDING.

Commit-ordering contract: git commit first; only non-empty SHA →
COMMITTED; empty → FAILED (resume retries). `--end-stage` strict prefix:
finalization (Phase 3.5, squash-merge, Phase 4) only after all stages
COMMITTED.

Each call is a fresh agent (claude -p or codex); context is file-based.
Input trimmed to the most recent snapshot + memory_timeline (not full
history). `baseline_merge.md`, `memory_digest.jsonl`,
`world_event_digest.jsonl`, `stage_catalog.json` excluded from extraction
input — self-contained snapshot contract embedded in the prompt.

Extraction timeout 3600s, review 600s. Stage size max 15. Phase 4 per-chapter
parallel scene boundary annotation; programmatic validation only; output to
`works/{work_id}/retrieval/scene_archive.jsonl`. Supports Claude CLI and
Codex CLI backends.

See `architecture.md` for the full pipeline and `automation/README.md`
for the CLI.

## §12 Memory System and Retrieval

Three-layer memory:

1. `stage_snapshot` — aggregated state, current stage only.
   `stage_events` holds **only this stage's** events (50–80 字, hard
   gate; world-public only — personal / internal items belong in
   character `memory_timeline`).
2. `memory_timeline` — first-person subjective process per event.
   `memory_id` (`M-S###-##`), `time`, `location`, `event_description`
   (150–200 字, hard gate), `digest_summary` (30–50 字, hard gate, 1:1
   source of `memory_digest`), `subjective_experience` (unbounded),
   `scene_refs`.
3. `scene_archive` — original text split by scene. `scene_id`
   (`SC-S###-##`), `time`, `location`, `characters_present`. Work-level.

Two-level retrieval on `scene_archive` + `memory_timeline`:

- **Level 1 (default, <20ms)**: jieba + work-level vocab dict + FTS5 →
  top-K summaries in prompt. LLM judges relevance. No match = no
  retrieval.
- **Level 2 (fallback, rare)**: LLM `search_memory` tool use → embedding
  search on summary vectors → second LLM call.

Proactive association: engine extracts context-state keywords (location,
recent events, emotion) for jieba matching each turn.

Startup loads: memory_timeline recent 2 stages (N + N-1) full;
`memory_digest.jsonl` stage 1..N (~30–40 tokens/entry, summary 1:1 from
`digest_summary`); `world_event_digest.jsonl` stage 1..N (summary 1:1
from world `stage_events`); scene_archive `full_text` for the most recent
`scene_fulltext_window` scenes (default 10, configurable in
`load_profiles.json`). Scene summaries are **not** in Tier 0 — FTS5
only. Identity loaded with a field whitelist (strips `evidence_refs` and
large nested arrays at load time; no schema change). Vocab dict into
jieba.

Tech: `jieba`, `sqlite FTS5` (primary), `bge-large-zh-v1.5` (optional
fallback). Single SQLite — no separate vector DB. Artifacts under
`works/{work_id}/retrieval/` (not committed); vocab dict at
`works/{work_id}/indexes/vocab_dict.txt` (committed).

scene_archive produced in Phase 4 (independent; only requires Phase 1
`stage_plan.json`).
