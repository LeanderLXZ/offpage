# Current Status

## Project Stage

The project is currently in the "architecture scaffold created, waiting for
data onboarding and implementation work" stage.

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
- The first-pass project directory scaffold has been created:
  - `sources/`
  - `analysis/`
  - `characters/`
  - `users/`
  - `sessions/`
  - `runtime/`
  - `interfaces/`
  - `schemas/`
  - `docs/architecture/`
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

## Current Gaps

- No real novel corpus has been imported yet.
- No chapter-ingestion or incremental extraction workflow has been implemented
  yet.
- No real character package has been created yet.
- No real user package has been created yet.
- No runtime compiler implementation exists yet.
- The unified service interface and terminal-adapter boundary are not yet
  implemented.
- The current schemas are first-pass only and still need to be refined into
  directly writable instance formats.
- The full execution workflow for character identification, character
  selection, and batch character-package generation is not yet defined.
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
The repository now has a first-pass directory and data-model scaffold. The next
priority is to turn those schemas into writable instances and begin real source
ingestion.
