# Requirements (Compressed English Reference)

Authoritative source: `docs/requirements.md` (Chinese). Refer to it for full
details, examples, and rationale. This file is a quick-reference index only.

## §1 Overall Goal

Long-lived novel character roleplay system. Deep roleplay, not surface mimicry.
Arbitrary characters, stage-based state, long-term memory, multiple terminals.

## §2 Stage Model

- Batch N = Stage N. Default 10 chapters (configurable). Cumulative through 1..N.
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

1. Structured character data (identity, personality, triggers, relationships,
   memories, language style, boundaries, failure modes)
2. Character-perspective memory (subjective, not objective plot summaries)
3. Stable voice and behavior simulation (per-emotion, per-target, per-situation)

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

Five layers: immutable (identity, hard_boundaries, failure_modes) →
self-contained stage snapshot (complete voice/behavior/boundary/relationship
state, loaded directly without baseline merge) → historical memories
(memory_timeline split per stage, 1..N loaded at startup; past snapshots
on-demand) → session-mutable (context state, updated per turn) →
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
revision tracking, roleplay-focused. Eight-step workflow: ingest → analyze →
batch plan → candidate ID → active confirm → coordinated extraction → targeted
supplement → validate. Coordinated mode: read once per batch, produce world +
character simultaneously. Self-contained snapshots: stage 1 ≈ baseline + stage
fields; stage N = complete state (unchanged fields included); baseline =
extraction anchor only. Source labeling: canon / inference / ambiguous with
explanation. See `docs/requirements.md` §9 for full output file list.

## §10 Dilution Protection

Runtime: character anchor re-injection (voice signature, boundaries, relationship
stance, knowledge scope, emotional state), rolling session state (every 5-8
turns), deep calibration checkpoints (every 15-20 turns or after major events).

Extraction: schema forced re-read per batch, architecture model re-read,
previous batch output as quality baseline, output quality self-check,
cross-session continuity via progress files + previous output.

See `docs/requirements.md` §10 for detailed risk descriptions and required
capabilities.
