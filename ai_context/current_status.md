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
- New contexts must choose a character stage.
- Stage information must live inside character data as summarized key timeline
  nodes.
- At conversation start, the system should present the character's available
  stage catalog for user selection.
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
  - `Runtime Compiler`
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
  - `analysis/`
  - `users/`
  - `interfaces/`
  - `schemas/`
  - `docs/architecture/`
  - `docs/logs/`
- First-pass formal architecture docs have been created:
  - `README.md`
  - `docs/architecture/system_overview.md`
  - `docs/architecture/data_model.md`
- Project-level log and git rules have been added:
  - `docs/logs/README.md`
  - `.gitignore`
- The first-pass schema set has been created:
  - `schemas/work_manifest.schema.json`
  - `schemas/character_manifest.schema.json`
  - `schemas/stage_catalog.schema.json`
  - `schemas/stage_snapshot.schema.json`
  - `schemas/user_profile.schema.json`
  - `schemas/relationship_core.schema.json`
  - `schemas/context_manifest.schema.json`
  - `schemas/session_manifest.schema.json`
  - `schemas/runtime_session_request.schema.json`
- The `ai_context/` docs are now maintained in English as the default AI-facing
  language.
- The first real source work package has now been onboarded:
  - `sources/works/wo-he-nvdi-de-jiushi-nieyuan/`
  - source format normalized from a local `epub`
  - `537` normalized chapters are available under `chapters/`
  - source metadata exists in:
    - `manifest.json`
    - `metadata/book_metadata.json`
    - `metadata/chapter_index.json`
- The first real work-scoped canonical package scaffold now exists:
  - `works/wo-he-nvdi-de-jiushi-nieyuan/`
  - with:
    - `world/`
    - `characters/`
    - `analysis/`
    - `indexes/`
- The first-pass candidate-character identification result now exists under:
  - `works/wo-he-nvdi-de-jiushi-nieyuan/analysis/incremental/candidate_characters_initial.md`
- Old top-level scaffold directories for `characters/`, `worlds/`, `runtime/`,
  and `sessions/` have now been retired from the intended repo layout.
- Top-level `users/` is now intended to hold full user packages directly under
  `users/{user_id}/`.
- The architecture has now been extended in docs to treat world data as a
  first-class layer.
- The architecture has now been extended in docs to scope canonical assets by
  `work_id`.
- The preferred user-flow direction is now:
  - choose work
  - choose character
  - choose stage
- The preferred user-data direction is now user-rooted:
  - all user-specific state should live under `users/{user_id}/`
  - work-specific relationship, context, and session state should live under
    `users/{user_id}/works/{work_id}/`
- The preferred work-package direction is now:
  - `sources/works/{work_id}/` for source ingestion
  - `works/{work_id}/` for source-grounded canon and analysis
- The world package is now allowed to expose:
  - cast index
  - brief character summaries
  - relationship graph / timeline views
  - while detailed character canon stays under `characters/`
- The content-language rule is now:
  - work-scoped generated content defaults to the selected work language
  - structural field names may remain English
  - `ai_context/` remains English as the AI handoff layer
- The world-data rule is now:
  - world materials are living canon assets
  - they should be incrementally expanded, corrected, and revised
  - later source reading may revise them
  - user conversations must not rewrite canonical world data
  - world events and character event-awareness summaries belong in the world
    layer
  - world conflicts and uncertainty should be recorded explicitly
- The preferred extraction order is now:
  - candidate identification first
  - world-first batch extraction next
  - selected-character batch extraction after that
- The source-batch update rule is now:
  - any one source-reading batch may supplement or revise world data and any
    already-known character package
  - batch focus does not limit correction scope

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
- Current source-analysis entry:
  - `works/wo-he-nvdi-de-jiushi-nieyuan/analysis/incremental/candidate_characters_initial.md`

## Current Gaps

- No reusable automated chapter-ingestion workflow has been implemented yet.
- No reusable automated incremental extraction workflow has been implemented
  yet.
- Only an initial candidate-character identification result exists so far.
  There is not yet a stable batch-extraction packet format or any finished
  character package.
- No populated world package has been created yet for the first real work.
- No world schema set exists yet for:
  - world foundation
  - world timeline
  - world event records
  - world-state snapshots
  - location-state snapshots
  - map graph
  - character event-awareness summaries
- The repository has now started migrating to the preferred user-rooted state
  layout, but no real user package has been created yet.
- The package schemas do not yet explicitly document inheritance or override
  behavior for content language beyond the current work-level `language`
  field.
- No real character package has been created yet.
- No real user package has been created yet.
- No runtime compiler implementation exists yet.
- The unified service interface and terminal-adapter boundary are not yet
  implemented.
- The current schemas are first-pass only and still need to be refined into
  directly writable instance formats.
- The full execution workflow for character identification, character
  selection, world-first extraction, and batch character-package generation is
  not yet fully defined.
- The formal schema for incremental update packets and evidence records is not
  yet defined.
- No service-layer code or interface stubs exist yet.
- No final roleplay prompt has been produced yet.

## Current Data And Commit Rules

- Full novel bodies, databases, indexes, full user histories, and large runtime
  artifacts should not be committed by default.
- Those artifacts should stay local and be excluded through `.gitignore`.
- `docs/logs/` is now defined as a historical-summary layer, not a bulk-data
  archive.

## Most Important Current Fact

Do not treat this project as "business logic exists and only needs patches."
The repository still has an early scaffold-first architecture, but it now also
has one real normalized source work package and one matching work-scoped
canonical package scaffold. The next priority is to populate
`works/{work_id}/` with source-grounded outputs and define the first real
`users/{user_id}/` package shape for roleplay state.
