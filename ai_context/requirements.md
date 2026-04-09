# Requirements (Compressed English Reference)

Authoritative source: `docs/requirements.md` (Chinese). Refer to it for full
details, examples, and rationale. This file is a quick-reference index only.

## §1 Overall Goal

Long-lived novel character roleplay system. Deep roleplay, not surface mimicry.
Arbitrary characters, stage-based state, long-term memory, multiple terminals.

## §2 Stage Model

- Batch N = Stage N. Batch splitting is the **most critical output** of the
  analysis phase — every batch boundary becomes a stage boundary that all
  downstream structures (world snapshots, character snapshots, memory timelines,
  runtime stage selection) depend on. Accuracy of story boundaries matters more
  than even chapter counts. Target 10 chapters, min 5, max 15; variable per
  batch. Cumulative through 1..N.
- Selected stage = "now"; prior stages = history. Current-stage personality/voice only.
- World info architecture: foundation layer (setting, power system, cosmology) +
  entity tracking (events, locations, factions, main cast) + fixed vs dynamic
  relationships + per-stage world snapshots. World and character snapshots share
  stage_id for timeline alignment.
- Character snapshots: events, status, personality/voice shifts, mood, relationships.
- Inter-character relationships evolve per stage: attitude/trust/intimacy change,
  event-driven transitions, knowledge boundaries affect behavior, concealment
  tracking, mutual influence. See §2.5 for full example.
- Cross-stage historical recall: behavioral details (nicknames, speech habits,
  attitudes, knowledge state), not just event summaries. Current personality
  used when recalling. See §2.6 for "臭小子" example.
- Stage selection: one-line summary per stage, fixed for entire context.

## §3 Three Deep-Roleplay Goals

1. Structured character data (identity with `core_wounds` and
   `key_relationships`, personality, triggers, goals vs obsessions,
   relationships, memories, language style, boundaries, failure modes,
   `character_arc`)
2. Character-perspective memory (subjective, not objective plot summaries)
3. Stable voice and behavior simulation (per-emotion, per-target, per-situation)

### §3.1 Character Identity and Name Tracking

Characters may have multiple names, aliases, or identity changes across the story.
Five scenarios: (1) disguise/amnesia/alias — actions under alias still belong to
the same character entity; (2) unnamed early, named later — pre-naming data linked
retroactively; (3) name change (e.g. receiving a dao-name from master) — all names
recorded with effective stage range; (4) dual identity in parallel (e.g. weapon name
+ human-form name) — same entity, different contextual names; (5) relationship-based
nicknames — different characters call the target differently, may change per stage.

Requirements: stable `character_id` that never changes; aliases list with name text,
type (本名/化名/代称/称呼/封号/道号), effective stage range, and source; extraction
must match new names against existing aliases before creating new entities; runtime
loads aliases with the stage snapshot for dialogue generation and character recognition.

Analysis-phase identity consolidation: chunk-based summarization works
independently per chunk, so the same character may appear under different names
across chunks. The global analysis phase (which reads all chunk summaries) MUST
perform cross-chunk identity merging — unify aliases into a single candidate
entry with all known names before producing the candidate list.

See `docs/requirements.md` §3 "角色标识与名称跟踪" for full scenarios.

## §4 Runtime Loading

Six categories: basic identity, personality core, speech style, memory library,
behavior rules, forbidden deviations. Plus runtime behavior rules for cognitive
conflict handling and historical recall processing. See `docs/requirements.md` §4.

## §5 User Flow and Session Lifecycle

- New user: select work → character → stage → self-role → create user package → context
- Existing user: load account → select/create context
- One-time setup lock; changes require new package or explicit migration
- Close and merge: exit keyword → ask merge → selective promotion to long-term
- Context tracks real-time state (emotions, drift, agreements, relationship delta,
  events, memories); long-term profile updated only after merge confirmation
- Crash recovery: per-turn journaling, safe resume after interruption
- Conversation archive: merged contexts become immutable account-level history

## §6 Data Separation

Objective vs subjective, canon vs inference, character canon vs user data,
knowledge boundaries, stage boundaries, multi-work namespace disambiguation,
content language consistency (work language → all generated content including
user-side data).

## §7 Information Layering and Loading

Five layers: immutable (identity incl. core_wounds + key_relationships,
hard_boundaries, failure_modes) →
self-contained stage snapshot (complete voice/behavior with core_goals +
obsessions/boundary/relationship state + character_arc, loaded directly
without baseline merge; `target_voice_map` and
`target_behavior_map` filtered by user role at load time; fallback: if
current snapshot lacks a matching target entry, engine scans backwards
through previous stage snapshots — pure code I/O, no extra LLM call) →
historical
memories (memory_timeline split per stage; recent 2 stages N + N-1 full at
startup + memory_digest.jsonl compressed index for distant-history
awareness; rest via FTS5 on-demand; past snapshots on-demand) →
session-mutable (context state, updated per turn) →
cross-session accumulated (long_term_profile, relationship_core, merge-only).

Baseline files = extraction anchors only, NOT loaded at runtime.

Four load tiers: startup core (summaries only) → structured on-demand →
transcript recall → raw source verification. Per-work config can customize.

## §8 Source Ingestion

Accepted formats: TXT, EPUB, MOBI, HTML, user excerpts. Pipeline: raw →
normalize (UTF-8, clean) → chapter split (zero-padded) → metadata generation.
Source package = input layer, never modified downstream, excluded from git.
Work manifest required. Chinese works use Chinese work_id.

## §9 Extraction Process

Principles: incremental, evidence-backed, Chinese identifiers, explicit
revision tracking, roleplay-focused. Seven-step workflow:

1. Ingest (normalize, split, metadata)
2. Chapter summarization (chunk-based, ~25 ch/chunk, parallelizable)
3. Global analysis (from all summaries, in order):
   a. Cross-chunk character identity merging
   b. World overview (genre, power system, factions, geography, major
      world-lines/eras, core setting rules)
   c. Batch plan (story-boundary-based stage splitting)
   d. Candidate character identification (post-merge, with aliases)
   e. **Baseline production** (new): write world foundation files and
      character identity.json + manifest.json for confirmed characters.
      Full-book context makes these baselines more accurate than batch-1-only.
      voice_rules, behavior_rules, boundaries still deferred to batch extraction
      (need raw text detail). Baselines are drafts — batch extraction corrects
      them when raw text reveals errors.
4. Active character confirmation (user selects)
5. Coordinated batch extraction (world + character per batch; baseline
   correction when needed)
6. Targeted supplement extraction
7. Package validation

Coordinated mode: read once per batch, produce world + character simultaneously.
Self-contained snapshots: stage 1 ≈ baseline + stage fields; stage N = complete
state (unchanged fields included); baseline = extraction anchor only. Source
labeling: canon / inference / ambiguous with explanation. See
`docs/requirements.md` §9 for full details.

## §10 Output Quality Protection

Two distinct quality risks with different mitigations:

**§10.1 Runtime anti-dilution**: long conversations cause attention decay on
loaded character data. Mitigations: character anchor re-injection (every turn
or N turns), rolling session state (every 5-8 turns), deep calibration
checkpoints (every 15-20 turns or after major events).

**§10.2 Extraction cross-batch quality**: each batch is an independent
`claude -p` call (fresh context), so no in-session dilution. Risk is
cross-batch style drift and detail degradation. All mitigations are naturally
satisfied by automation architecture (prompt_builder injects schema + previous
output, validator + semantic review check quality, Phase 3.5 consistency
checker catches global drift). No additional dilution protection code needed.

See `docs/requirements.md` §10 for full details.

## §11 Automated Extraction Pipeline

Python orchestrator in `automation/` drives multi-batch extraction via CLI.
Analysis → user confirmation → extraction loop (per batch: git preflight →
**1+N split extraction** [world call → N parallel character calls] →
programmatic validation → semantic review → git commit or rollback+retry) →
Phase 3.5 cross-batch consistency check → Phase 4 scene archive. Each call
is a fresh agent; context is file-based. Input trimming: only the most recent
stage_snapshot and memory_timeline are passed (not full history). Extraction
timeout 3600s, review 600s. Targeted fix re-runs the original failing check
layer. Commit clears feedback/error fields. Two-layer quality check
(programmatic + semantic). Batch size max 15 chapters. Phase 4 is independent
(only needs Phase 1 batch plan): per-chapter parallel LLM calls for scene
boundary annotation, programmatic validation only, output to
`works/{work_id}/rag/scene_archive.jsonl`. CLI: `--start-phase 4`,
`--concurrency N`. Supports Claude CLI and Codex CLI backends.
See `docs/requirements.md` §11.

## §12 Memory System and Retrieval

Three-layer memory: stage_snapshot (aggregated state, current stage only) →
memory_timeline (first-person subjective process per event, with
`time_in_story`, `location`, `scene_refs`; no length limit) → scene_archive
(original text split by scene, 8 fields including `time_in_story` and
`location`; work-level, not per-character).

Two-level retrieval funnel on scene_archive + memory_timeline:
Level 1 (default, <20ms): jieba + work-level vocab dict + FTS5 → top-K
summaries in prompt; LLM judges relevance. No match = no retrieval.
Level 2 (fallback, rare): LLM tool use (`search_memory`) → embedding
search on summary vectors → second LLM call.

Proactive character association: engine also extracts context-state keywords
(location, recent events, emotion) for jieba matching, so the character
can naturally recall related memories without being asked.

Startup: memory_timeline recent 2 stages (N + N-1) full +
memory_digest.jsonl (compressed index of all stages, ~60-80 tokens/entry);
scene_archive summaries for stages 1..N + N full_text scenes around current
stage (default N=5); vocab dict into jieba. Distant memory detail via FTS5
on-demand (no separate embedding needed for memory_timeline).

scene_archive produced in Phase 4 (independent from Phase 3, only needs
Phase 1 batch plan). Per-chapter parallel, programmatic validation only.

Tech: `jieba` (segmentation), `sqlite FTS5` (primary), `bge-large-zh-v1.5`
(optional embedding fallback). Single SQLite file, no separate vector DB.
Artifacts under `works/{work_id}/rag/`, not committed (.gitignore). Vocab
dict at `works/{work_id}/indexes/vocab_dict.txt`, committed.

See `docs/requirements.md` §12.
