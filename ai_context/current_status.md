# Current Status

## Project Stage

The project is currently in the "architecture scaffold created, first real work
package onboarded, early extraction artifacts beginning to appear" stage.

## What Has Already Been Completed

- The project goal is now defined as a long-lived multi-character novel
  roleplay system.
- An earlier incorrect assumption that the project was only about one female
  lead has been corrected. The current scope is:
  - identify characters from the novel
  - let the user specify which characters to build
  - generate an independent package for each selected character
- The core deliverables have been defined:
  - character bible
  - character memory timeline
  - character voice library
  - character behavior rules
  - final roleplay prompt
- The deep-roleplay requirements have been defined:
  - personality consistency
  - memory consistency
  - language-style consistency
  - relationship-logic consistency
- New contexts must choose an active work-stage.
- Stage information must now be modeled as:
  - work-level stage selection in the world layer
  - aligned character-side stage projections
- At conversation start, the system should present the work's available stage
  catalog, then load matching character-side stage projections.
- For one user and one character, the system must support:
  - multiple context branches
  - permanently retained memories
  - merging selected contexts into a long-lived relationship core
- The required information layers have been defined:
  - objective plot
  - target character definition
  - target character memory
  - target character misunderstandings, concealments, and biased beliefs
  - target character voice style
  - target character behavior rules
  - conflict and revision notes
- The high-level architecture has been confirmed:
  - `Source Layer`
  - `Extraction Layer`
  - `Canonical World Layer`
  - `Canonical Character Layer`
  - `User Layer`
  - `Simulation Engine`
  - `Session Runtime`
- Future multi-terminal support has been confirmed:
  - direct AI-agent loading
  - frontend app
  - mobile-chat MCP or similar messaging terminal
- The system must keep the core roleplay engine decoupled from terminal
  adapters.
- The standard per-round analysis format has been confirmed.
- A reference-style `ai_context/` handoff set has been created.
- The current top-level repo structure has been narrowed to:
  - `sources/`
  - `works/`
  - `users/`
  - `interfaces/`
  - `simulation/`
  - `prompts/`
  - `schemas/`
  - `docs/architecture/`
  - `docs/logs/`
- First-pass formal architecture docs have been created:
  - `README.md`
  - `docs/architecture/system_overview.md`
  - `docs/architecture/data_model.md`
  - `simulation/README.md`
  - `simulation/flows/conversation_records.md`
- Project-level log and git rules have been added:
  - `docs/logs/README.md`
  - `.gitignore`
- A reusable prompt library for fresh agents and user-facing flows now exists:
  - `prompts/`
  - including ingestion, analysis, runtime, and review templates
- The first-pass schema set has been created:
  - `schemas/work_manifest.schema.json`
  - `schemas/character_manifest.schema.json`
  - `schemas/world_stage_catalog.schema.json`
  - `schemas/world_stage_snapshot.schema.json`
  - `schemas/stage_catalog.schema.json`
  - `schemas/stage_snapshot.schema.json`
  - `schemas/user_profile.schema.json`
  - `schemas/long_term_profile.schema.json`
  - `schemas/role_binding.schema.json`
  - `schemas/relationship_core.schema.json`
  - `schemas/context_manifest.schema.json`
  - `schemas/session_manifest.schema.json`
  - `schemas/runtime_session_request.schema.json`
- The `ai_context/` docs are now maintained in English as the default AI-facing
  language.
- The first real source work package has now been onboarded:
  - `sources/works/我和女帝的九世孽缘/`
  - source format normalized from a local `epub`
  - `537` normalized chapters are available under `chapters/`
  - source metadata exists in:
    - `manifest.json`
    - `metadata/book_metadata.json`
    - `metadata/chapter_index.json`
- The first real work-scoped canonical package scaffold now exists:
  - `works/我和女帝的九世孽缘/`
  - with:
    - `world/`
    - `characters/`
    - `analysis/`
    - `indexes/`
- The first-pass candidate-character identification result now exists under:
  - `works/我和女帝的九世孽缘/analysis/incremental/candidate_characters_initial.md`
- A first real source-batch plan now exists under:
  - `works/我和女帝的九世孽缘/analysis/incremental/source_batch_plan.md`
- A first real world-batch tracker now exists under:
  - `works/我和女帝的九世孽缘/analysis/incremental/world_batch_progress.md`
- A first real world-batch extraction report now exists under:
  - `works/我和女帝的九世孽缘/analysis/incremental/world_batch_001.md`
- The first populated world package now exists under:
  - `works/我和女帝的九世孽缘/world/`
  - including:
    - `manifest.json`
    - `stage_catalog.json`
    - `stage_snapshots/阶段1_南林初遇.json`
    - first-pass `foundation/`, `history/`, `events/`, `locations/`,
      `factions/`, `cast/`, and stage-scoped `social/`
- The old repo-level `analysis/` directory has now been retired.
  - Work-related analysis should stay under `works/{work_id}/analysis/`.
- Old top-level scaffold directories for `characters/`, `worlds/`, `runtime/`,
  and `sessions/` have now been retired from the intended repo layout.
- A dedicated top-level `simulation/` directory now exists for runtime-engine
  lifecycle docs and future implementation work.
- Top-level `users/` is now intended to hold full user packages directly under
  `users/{user_id}/`.
- The architecture has now been extended in docs to treat world data as a
  first-class layer.
- The architecture has now been extended in docs to scope canonical assets by
  `work_id`.
- The preferred user-flow direction is now:
  - enter `user_id`
  - determine new or existing setup
  - if new: choose work
  - choose target character
  - choose the active work-stage
  - choose the user-side role or counterpart identity
  - if that side is canon-backed, inherit the same stage by default
  - lock the setup
- The preferred user-data direction is now user-rooted:
  - all user-specific state should live under `users/{user_id}/`
  - work-specific relationship, context, and session state should live under
    `users/{user_id}/works/{work_id}/`
- The user package direction now includes a work-character-scoped
  `long_term_profile.json` for merged long-term self-profile changes.
- The root `users/{user_id}/profile.json` is now treated as a global user
  profile rather than the default sink for one branch's relationship drift.
- The preferred work-package direction is now:
  - `sources/works/{work_id}/` for source ingestion
  - `works/{work_id}/` for source-grounded canon and analysis
- The world package is now allowed to expose:
  - cast index
  - brief character summaries
  - stage-scoped relationship views
  - while detailed character canon stays under `characters/`
- The content-language rule is now:
  - work-scoped generated content defaults to the selected work language
  - work titles and display names should stay in the original work language by
    default
  - for Chinese works, `work_id` itself may be Chinese, and work-scoped canon
    names and identifier values should also default to Chinese rather than
    pinyin-only forms
  - generated work-scoped folder names and identifier-derived path segments
    should follow those same Chinese labels by default
  - structural field names may remain English
  - `ai_context/` remains English as the AI handoff layer
- The world-data rule is now:
  - world materials are living canon assets
  - they should be incrementally expanded, corrected, and revised
  - later source reading may revise them
  - user conversations must not rewrite canonical world data
  - world events should focus on major shared events rather than small
    scene-level incidents
  - world cast views should focus on the main cast and high-frequency
    supporting characters rather than one-off minor roles
  - world relationships should be stored as stage-scoped snapshots
  - runtime should normally load only the selected stage relationship file
  - detailed character-side knowledge boundaries should remain under
    `characters/`
  - world conflicts and uncertainty should be recorded explicitly
- The runtime stage model is now being documented as a unified work-stage axis:
  - the world layer exposes selectable stage catalog data
  - the selected `stage_id` is treated as a work-level timeline checkpoint
  - character stage snapshots project that same `stage_id` into
    character-specific state
- The preferred extraction flow is now:
  - candidate identification first
  - confirm or refresh the active character set as early as practical
  - once the active set exists, use coordinated source batches to update
    shared world canon and relevant character packages together
  - if no active character set exists yet, or a batch is almost entirely
    shared-world material, temporary world-only output is acceptable
  - use targeted character supplement passes only when coordinated batches
    still leave clear package gaps
- The default extraction planning direction now assumes:
  - configurable batch size per work
  - default batch size `10` when not overridden
  - batch `N` as the default stage `N` candidate
  - stage `N` extraction as cumulative through `1..N`
- The source-batch update rule is now:
  - any one source-reading batch may supplement or revise world data and any
    already-known character package
  - batch focus does not limit correction scope
- The runtime prompt direction is now:
  - `用户入口与上下文装载` acts as the user-side runtime orchestrator
  - user-scoped `session` / `context` updates should happen continuously during
    live roleplay rather than waiting for a separate manual writeback request
  - long-term profile and relationship-core updates should happen only after
    explicit merge confirmation
  - startup should load summary-layer user state
  - full user transcripts should be recalled on demand rather than loaded by
    default
  - merged contexts may archive full conversation bundles into an
    account-level conversation library
  - `users状态回写` acts both as an internal writeback subflow and as a
    standalone repair / merge prompt when needed
- Fresh agents launched through the prompt library are now expected to read a
  minimal `ai_context` subset before relying only on prompt-local rules.
- The first ordinary follow-up after handoff should now default to
  `ai_context/` plus the live user request, not to `prompts/`.
  - Prompt files should only become the active instruction source when the
    user explicitly asks for them, names one, or the task is directly about
    prompt work.
- The runtime/user-state schema direction is now:
  - runtime request objects should carry explicit `work_id`
  - persisted `relationship_core`, `context`, and `session` manifests should
    also carry explicit `work_id`
  - runtime scope should not rely only on directory paths
- Stage selection is now intended to apply to every canon-backed role slot in
  a context, not only the primary target character.
  - If the user-side identity is also a canonical character, that side should
    normally inherit the same active stage by default.
- Context content is now explicitly expected to support promotion or full
  merge into user-owned long-term state under `relationship_core` when the
  merge policy and evidence justify it.
- Session close is now being documented as an explicit lifecycle point:
  - exit keywords or equivalent close intents end the session
  - the system then asks whether to merge the current context into long-term
    user-owned history
- Repo-level runtime-engine guidance is now being split cleanly from static
  architecture docs:
  - `docs/architecture/` keeps structural and data-model truth
  - `simulation/` keeps lifecycle, loading, retrieval, and close-flow rules

## Current Entry Points

- AI handoff entry:
  - `ai_context/README.md`
- Most important current project-state docs:
  - `ai_context/instructions.md`
  - `ai_context/project_background.md`
  - `ai_context/architecture.md`
  - `ai_context/decisions.md`
  - `ai_context/next_steps.md`
  - `ai_context/handoff.md`
  - `simulation/README.md`
- Current source-analysis entry:
  - `works/我和女帝的九世孽缘/analysis/incremental/candidate_characters_initial.md`
  - `works/我和女帝的九世孽缘/analysis/incremental/source_batch_plan.md`
  - `works/我和女帝的九世孽缘/analysis/incremental/world_batch_progress.md`
  - `works/我和女帝的九世孽缘/analysis/incremental/world_batch_001.md`
  - `works/我和女帝的九世孽缘/world/stage_catalog.json`

## Current Gaps

- No reusable automated chapter-ingestion workflow has been implemented yet.
- No reusable automated incremental extraction workflow has been implemented
  yet in code or scripts.
- A first manual batch-extraction packet format now exists for world work, but
  no reusable machine-written pipeline exists yet.
- Only the first world batch is complete so far.
  - There is still no finished character package.
- The world-stage schemas now exist, but no full world schema set exists yet
  for:
  - world foundation
  - world timeline
  - world event records
  - world-state snapshots
  - location-state snapshots
  - map graph
  - stage relationship snapshots
- The repository has now started migrating to the preferred user-rooted state
  layout, but no real user package has been created yet.
- The new bootstrap-lock, explicit close, and merge-confirmation runtime model
  is documented, but not yet implemented in service code.
- The package schemas do not yet explicitly document inheritance or override
  behavior for content language beyond the current work-level `language`
  field.
- No real character package has been created yet.
- No real user package has been created yet.
- No simulation-engine service implementation exists yet.
- The unified service interface and terminal-adapter boundary are not yet
  implemented.
- The current schemas are first-pass only and still need to be refined into
  directly writable instance formats.
- The full execution workflow for character identification, active character
  selection, coordinated batch extraction, and targeted character supplement is
  not yet fully defined.
- The first-pass runtime schemas now cover:
  - setup lock
  - long-term profile
  - explicit close / merge request modes
  - but they may still need refinement as runtime service behavior becomes
    more concrete.
- The formal schema for incremental update packets and evidence records is not
  yet defined.
- No service-layer code or interface stubs exist yet.
- No final roleplay prompt has been produced yet.

## Current Data And Commit Rules

- Full novel bodies, databases, indexes, full user histories, and large runtime
  artifacts should not be committed by default.
- Those artifacts should stay local and be excluded through `.gitignore`.
- Real `users/{user_id}/...` packages should remain local-only by default.
  - The repo should normally track only `users/README.md`, not actual user
    state.
- User conversation archives and full transcripts should also remain local-only
  under `users/`.
- `docs/logs/` is now defined as a historical-summary layer, not a bulk-data
  archive.

## Most Important Current Fact

Do not treat this project as "business logic exists and only needs patches."
The repository still has an early scaffold-first architecture, but it now also
has one real normalized source work package and one matching work-scoped
canonical package scaffold. The next priority is to populate
`works/{work_id}/` with source-grounded outputs and define the first real
`users/{user_id}/` package shape for roleplay state.
