<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `角色A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# Handoff

## Mental Model

Architecture agreed, scaffolding + schemas done, first work package
under stage extraction. No finished character package yet, no real
user package, no runtime code.

## Quick Start

1. Read `ai_context/` in order (see `instructions.md`).
2. On follow-up, continue from `ai_context/` + user request.
3. Detail → `docs/architecture/system_overview.md`, `data_model.md`,
   `schema_reference.md`.
4. Runtime flow → `simulation/README.md`, `simulation/flows/`,
   `simulation/retrieval/`, `simulation/prompt_templates/`.
5. Extraction pipeline → `automation/README.md`.

## Current Work Continuation

Real `work_id` lives under `works/` + `sources/works/`.

```bash
# Foreground
python -m automation.persona_extraction "<work_id>" --resume

# Background (survives SSH disconnect), default runtime cap
python -m automation.persona_extraction "<work_id>" \
    --resume --background --max-runtime 360

# Follow log
tail -f works/<work_id>/analysis/progress/extraction.log
```

Pipeline checks PID lock + clean git tree (scope-limited) before
starting. `jsonschema` is a HARD dep in `automation/pyproject.toml`.
Full CLI + background semantics → `automation/README.md`.

Manual repair scenarios → `prompts/review/*.md`.

### Extraction-branch artifact drift (resume gate)

Before `--resume` on an existing `extraction/<work_id>` branch, check
the already-produced stage products against the **current** schemas —
schema tightening over the 2026-04 cleanup series invalidates earlier
products. Known break points on surviving branches:

Files likely broken by newer schema gates (exact bounds → each schema
file):

- `world/stage_snapshots/{stage_id}.json` — new required anchors
  (`timeline_anchor` + `location_anchor`); `character_status_changes` +
  `evidence_refs` removed; per-field `maxItems` / `maxLength` tightened.
- `world/stage_catalog.json` + `characters/*/canon/stage_catalog.json`
  — `order` field removed.
- `world/foundation/fixed_relationships.json` — `source_type` +
  `evidence_refs` removed.
- `memory_timeline/{stage_id}.json` — `scene_refs` removed; `time` /
  `location` required short strings.
- `characters/*/canon/stage_snapshots/{stage_id}.json` — `timeline_anchor`
  + `snapshot_summary` required; `character_arc` is now a short
  string (old `{arc_summary, arc_stages[], current_position}` object
  rejected); top-level `memory_refs` + `evidence_refs` removed;
  per-item `evidence_ref` in every `dialogue_examples` /
  `action_examples` removed; `boundary_state.hard_boundaries` added;
  various capacity tightens / widenings.
- `characters/*/canon/voice_rules.json` — per-item `evidence_ref` in
  `dialogue_examples` removed; container caps tightened.
- `characters/*/canon/behavior_rules.json` — `relationship_behavior_map`
  → `target_behavior_map`; inner `relationship_type` → `target_type`.

Remediation options: rerun affected stages, write a one-off patch
script, or carry forward only from the next stage (older stages stay
INVALID until rerun). Decide before `--resume` — repair agent's L1
gate will trip on every pre-tightening file otherwise.

## What The User Cares About

- Deep roleplay, not shallow mimicry or generic AI tone
- Stage differences + knowledge boundaries preserved
- Canon vs inference labelled; no silent blur
- No cross-context memory leak; character not written as omniscient
- Incremental updates, never restart from scratch
- Content language = work language (no English summaries of Chinese canon)
- No raw text pasted into logs / docs / answers
- **No real book / character / chapter / plot names** in docs,
  requirements, README, prompt templates, schemas, or `ai_context/`.
  Use generic placeholders (`角色A`, `<work_id>`, `S001`). Only
  `works/`, `sources/`, and `docs/logs/` may carry work-specific
  references.

## After Each Milestone

1. `docs/logs/` entry with HHMMSS timestamp (mandatory for schema /
   architecture / prompt / simulation / directory changes).
2. Update `current_status.md`, `next_steps.md`, and this file only
   when durable.
