# Handoff

## If You Are A New AI On This Project

Start from the mental model of "architecture agreed, scaffold created,
implementation still missing." Do not assume there is already a complete
pipeline or finished character data in the repo.

## Most Important Facts Right Now

- The project goal is a long-lived multi-character novel roleplay system.
- The priority is deep roleplay, not shallow imitation.
- The original novel is the highest authority.
- Keep these layers separate:
  - objective plot
  - target character definition
  - target character memory
  - target character misunderstandings, concealments, and biased beliefs
  - target character voice style
  - target character behavior rules
  - conflict and revision notes
- The high-level architecture is already defined.
- The repository already contains a first-pass directory scaffold, architecture
  docs, and schemas, but no real business implementation yet.
- One real work package now exists under:
  - `sources/works/我和女帝的九世孽缘/`
  - it is normalized from a local `epub`
  - it contains `537` normalized chapters
- A matching work-scoped canonical package scaffold now exists at:
  - `works/我和女帝的九世孽缘/`
- The first-pass candidate-character identification result for that work now
  exists at:
  - `works/我和女帝的九世孽缘/analysis/incremental/candidate_characters_initial.md`
- A first real source-batch plan now exists at:
  - `works/我和女帝的九世孽缘/analysis/incremental/source_batch_plan.md`
- A first real world-batch tracker now exists at:
  - `works/我和女帝的九世孽缘/analysis/incremental/world_batch_progress.md`
- The first populated world package for that work now exists at:
  - `works/我和女帝的九世孽缘/world/`
  - currently through:
    - `stage_catalog.json`
    - `stage_snapshots/阶段1_南林初遇.json`
    - first-pass foundation, event, location, faction, cast, and stage-scoped
      social files
- World data is now part of the intended canonical model, not optional side
  commentary.
- A dedicated runtime-engine design directory now exists under:
  - `simulation/`
- The preferred architecture direction is now work-scoped:
  - enter `user_id` first
  - determine whether the user is new or existing
  - if new: choose work first
  - then choose the target character
  - then choose the active work-stage
  - then choose the user-side role or counterpart identity
  - if that side is also canon-backed, bind it to the same stage by default
  - then lock the setup
- The preferred persistent package root for source-grounded canonical work data
  is now:
  - `works/{work_id}/`
- Keep source packages separate under:
  - `sources/works/{work_id}/`
- The preferred user-data direction is now user-rooted:
  - all user-specific state should live under `users/{user_id}/`
  - work-specific state should be nested under
    `users/{user_id}/works/{work_id}/`
- The content-language rule is now:
  - work-scoped generated content should follow the selected work language by
    default
  - work titles and display names should stay in the original work language by
    default
  - for Chinese works, `work_id` itself may be Chinese, and work-scoped canon
    names and identifier values should also stay in Chinese by default
  - generated work-scoped folder names and identifier-derived path segments
    should follow those same Chinese labels by default
  - English may still be used for JSON keys and schema field names
  - `ai_context/` remains English as the AI-facing handoff layer
- `ai_context/` is the primary compressed truth source for future AI sessions.
- On the first follow-up after handoff, do not proactively route yourself
  through `prompts/` unless the user explicitly asks for prompt use, names a
  prompt file, or the task is itself prompt-related.
- A reusable prompt library now exists under:
  - `prompts/`
  - these templates are written so a fresh agent with no prior project context
    can still start the right workflow
  - but the shared prompt-entry rules should still read a minimal `ai_context`
    subset before relying only on prompt-local instructions
- The long-term goal is that another AI can load a character package and
  stably roleplay a user-specified character.
- Do not assume the project is only about one heroine. Characters are selected
  explicitly at generation time.
- The project should support at least three terminal families:
  - direct AI-agent loading
  - frontend app integration
  - mobile-chat MCP or similar message terminals
- Therefore the core roleplay engine must remain terminal-agnostic.
- New user contexts should choose an active work-stage that then projects onto
  the target character.
- Stage options should come from persistent canon data, not from user-written
  ad hoc labels.
- The world layer should expose the selectable work-stage axis.
- Before a conversation starts, the system should display multiple summarized
  timeline nodes from the work-stage catalog.
- If the user-side role is also a canonical character, that side should also
  align to the same selected stage by default.
- After the first setup is completed, the account binding should be treated as
  locked during ordinary runtime use.
- One user and one character should support multiple context branches.
- Some contexts or memory points should be permanently retained or merged into
  the long-term relationship core.
- Live runtime should keep user-scoped `session` and `context` state updated
  continuously rather than waiting for a separate manual writeback step.
- Long-term self-profile and relationship-core updates should happen only after
  explicit merge confirmation.
- User summaries may be loaded at startup, but full session transcripts should
  be recalled on demand rather than loaded by default.
- Merged contexts may archive full conversation bundles into an account-level
  `conversation_library/` under `users/{user_id}/`.
- Exact prior dialogue recall should route through current-context indexes or
  archive indexes before loading full transcript files.
- Runtime requests and persisted user-scoped manifests should carry explicit
  `work_id`, not rely only on path position.
- `docs/logs/` is the historical-summary layer and should not be read by
  default.
- Keep the repo lightweight. Do not treat full novel bodies, databases,
  indexes, or large runtime artifacts as normal commit content.
- Treat real `users/{user_id}/...` packages as local runtime state rather than
  normal commit content.
- Do not reread the full normalized novel by default when continuing current
  source-work tasks. Start from:
  - work metadata
  - chapter index
  - the current candidate-character identification file
  - the current source-batch plan
  - the current world-batch tracker
  - the latest world-batch report
  - the existing early-stage world package files
  - targeted chapter reads only when needed
- Keep world layers separate:
  - stable world foundation
  - historical timeline
  - dynamic world state
  - location identity
  - location state
  - factions / institutions
  - explicit geography vs. map inference
- Treat world materials as living canon.
  - Later chapters may expand, correct, or partially overturn earlier world
    understanding.
- Preserve those revisions and uncertainty explicitly.
- Only source-text evidence may revise canonical world materials.
- User conversations and runtime branches must not rewrite canonical world
  facts.
- Preferred extraction flow for one work:
  - candidate identification first
  - confirm the active character set as early as practical
  - once the active set exists, use shared source batches to co-produce world
    updates and relevant character-package updates
  - if the active set is not ready yet, or a batch is almost entirely shared
    world material, temporary world-only output is acceptable
  - use targeted character supplement only when coordinated batches still
    leave clear gaps
- Default extraction planning now assumes:
  - configurable batch size per work
  - default `10` chapters when not overridden
  - batch `N` as the default stage `N` candidate
  - stage `N` extraction as cumulative through `1..N`
- World packages should include major work-level events, not only static
  setting.
- World packages should not record small scene-level incidents by default.
  - Those should usually remain in character-layer canon, memory, or batch
    analysis.
- World packages may include work-level cast and social views.
  - brief character summaries for the main cast and high-frequency supporting
    characters are fine there
  - social layer has two sublayers:
    - `fixed_relationships/` for immutable structural bonds (parent-child,
      sibling, etc.) that hold across all stages
    - `stage_relationships/` for dynamic bonds (romantic, alliance, rivalry,
      etc.) that evolve over time
  - runtime should load all fixed relationships at startup plus the selected
    stage's dynamic file
  - do not promote one-off minor roles into `world/` unless later source
    evidence makes them structurally important
  - detailed character psyche, memory, voice, and stage data still belong
    under `characters/`
  - detailed character knowledge boundaries should also stay under
    `characters/`

## The Roleplay Logic You Should Preserve

Do not think of this project as "write a prompt that sounds like the
character."

The intended logic is:

- reconstruct the character's current time stage
- reconstruct the current world stage that the character is living in
- reconstruct the character's knowledge boundary
- reconstruct the character's relationship to the conversation partner
- determine what the input triggers emotionally
- infer the likely behavioral response
- only then render the response in character voice

In short:

`memory and relationship -> psychological reaction -> behavior decision -> language realization`

## What The User Is Likely To Care About

- avoid shallow mimicry
- avoid generic AI tone
- do not reduce new chapter analysis to ordinary literary summary
- preserve time-stage differences
- preserve current-state versus historical-state distinctions
- do not leak memory across unrelated contexts
- do not write the target character as omniscient
- do not blur explicit canon and inference without labeling
- do not paste large raw source text, database contents, or other large-file
  material into logs, docs, or answers
- keep updating persistent materials instead of restarting from scratch
- keep the project easy for future AI sessions to resume
- do not accidentally rewrite Chinese canon packages into generic English
  summaries unless the user explicitly asks for translation

## Practical Starting Advice

- read all of `ai_context/` first
- on the first follow-up after handoff, continue from `ai_context/` and the
  live user request before consulting `prompts/` unless prompt use is
  explicitly requested
- for current source-work tasks, begin with the existing work metadata and
  candidate-character analysis before opening raw chapter files widely
- there is no longer a repo-level `analysis/` directory
- keep persistent and scratch extraction artifacts under the relevant
  `works/{work_id}/analysis/` path
- for source extraction, prefer confirming the active character set early and
  then using shared batches to co-produce world and character updates
- for `我和女帝的九世孽缘`, the automatic continuation point is now:
  - `next_batch_id = batch_002`
  - cumulative scope through `0011-0020`
- when handling roleplay state, load canonical base packages from
  `works/{work_id}/` and mutable user state from `users/{user_id}/`
- if a task is unrelated to the current source work, prioritize schemas and
  directory structure
- when designing or building runtime flow, remember that work selection should
  happen before character selection
- prefer `works/{work_id}/` for source-grounded canon and `users/{user_id}/`
  for mutable user state
- read `docs/architecture/system_overview.md` and
  `docs/architecture/data_model.md`
- read `simulation/README.md` when the task is about runtime orchestration,
  startup loading, retrieval, session updates, or close flow
- read `simulation/retrieval/load_strategy.md` when the task is specifically
  about startup-required vs. on-demand loading
- define the unified character-service interface and terminal-adapter boundary
  early
- define the canonical construction flow:
  `work selection -> character identification -> active character set confirmation -> coordinated batch extraction -> targeted supplement when needed -> character-package generation`
- define the user/runtime flow:
  `user selection -> new/existing detection -> if new: work selection -> target role binding -> target stage selection -> user-side role binding -> setup lock -> context creation or recovery -> continuous session/context writeback -> explicit close -> merge confirmation`
- define the world package and work-scoped directory rules early
- define the work-stage catalog and world-stage snapshots early
- keep work-specific long-term profile changes in work-scoped user data rather
  than the global root profile
- preserve the source work language in generated canonical content
- define `stage_catalog`, `stage_id`, `context_id`, `relationship_core`, and
  context-merge rules early
- remember that any one source-reading batch may revise world data and other
  character packages, not only the current target
- once the user selects a target character, continue with the agreed 7-part
  batch-analysis structure for that target while still propagating justified
  world or other-character corrections
- do not proactively read `docs/logs/` — it is a write-mostly historical
  archive; only read when the user asks, rollback is needed, or decision
  provenance must be verified
- when creating new user packages, reference the template at
  `users/_template/` for the expected directory structure and file formats
- `works/*/analysis/incremental/` and `works/*/indexes/` are tracked by git
  as canonical work assets
- after each meaningful milestone, update `current_status.md`,
  `next_steps.md`, and this file
