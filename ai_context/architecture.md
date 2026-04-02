# Architecture Snapshot

## Active Structure

The repository now uses a work-scoped canon package direction in the actual
filesystem, with top-level `users/` acting as the root for all user-specific
state.

Preferred top-level structure going forward:

- `sources/`
  - raw novel inputs and normalized source work packages
- `works/`
  - preferred home for source-grounded work canon packages
- `users/`
  - all user-specific state, grouped by `user_id`
- `interfaces/`
  - external adapters and terminal integration entry points
- `prompts/`
  - reusable prompt templates for fresh agents and user-facing flows
- `schemas/`
  - first-pass persistence and runtime-request schemas
- `docs/architecture/`
  - formal architecture docs
- `ai_context/`
  - compressed handoff context for future AI sessions

New persistent source-grounded work data should prefer `works/{work_id}/`.

## System Layers

### Work Scope Layer

Role:

- treat each novel as an independent namespace identified by `work_id`
- prevent character, world, relationship, and runtime data from different
  books from bleeding into one another
- ensure the user selects a work before selecting characters, contexts, or
  runtime state

Recommended scope rule:

- source ingestion remains under `sources/works/{work_id}/`
- persistent source-grounded work data should prefer `works/{work_id}/`
- all user-specific mutable state should live under `users/{user_id}/`
- work-scoped generated content should default to the language declared by the
  selected work
- for Chinese works, `work_id` itself may be Chinese, and work-scoped canon
  should keep Chinese names and Chinese identifier values by default rather
  than pinyin-only ids
- generated work-scoped folder names and identifier-derived path segments
  should follow those Chinese identifiers by default

### Canonical Work Package Layer

Location:

- preferred under `works/{work_id}/`

Role:

- keep the source-grounded canon information for one work in one place
- make indexing, loading, and work-level retrieval simpler
- reduce cross-directory scattering of world, character, analysis, and index
  assets

Suggested structure:

- `works/{work_id}/manifest.json`
- `works/{work_id}/world/`
- `works/{work_id}/characters/`
- `works/{work_id}/analysis/`
- `works/{work_id}/indexes/`

### Source Layer

Location:

- planned under `sources/`

Role:

- accept `txt`, `epub`, web-crawled text, or user-provided excerpts
- normalize content format
- preserve source, chapter, paragraph, and scene-level location metadata

### Extraction Layer

Location:

- `works/{work_id}/analysis/`

Role:

- process new text incrementally
- extract objective plot facts
- extract world facts and world-state changes
- extract historical events and timeline anchors
- extract major work-level event records
- extract locations, regions, routes, and map hypotheses
- extract factions, institutions, and power structures
- extract character-related facts
- extract character-memory points
- extract character knowledge or ignorance about major events
- extract voice samples
- extract behavior samples
- extract relationship changes
- identify candidate characters and aliases from the novel
- emit update packets that may touch the world layer and multiple character
  packages from one source-reading batch
- record contradictions and uncertainty
- record world-level contradictions, revisions, and unresolved questions
- keep extraction scratch, incremental packets, and persistent analysis inside
  the relevant work package rather than a repo-level `analysis/` directory

### Canonical World Layer

Location:

- recommended under `works/{work_id}/world/`

Role:

- store the stable world foundation for one work
- store historical events and timeline anchors
- store major work-level events that matter across character simulations
- store dynamic world-state changes
- store location dossiers and location-state changes
- store faction and institution records
- store map structure, route hypotheses, and unresolved geography questions
- store concise character-event knowledge views for runtime retrieval

Suggested structure:

- `works/{work_id}/world/manifest.json`
- `works/{work_id}/world/foundation/`
- `works/{work_id}/world/history/`
- `works/{work_id}/world/events/`
- `works/{work_id}/world/state/`
- `works/{work_id}/world/locations/{location_id}/`
- `works/{work_id}/world/factions/{faction_id}/`
- `works/{work_id}/world/maps/`
- `works/{work_id}/world/knowledge/`
  - concise character awareness / ignorance about major events
- `works/{work_id}/world/cast/`
  - work-level character index and brief summaries
- `works/{work_id}/world/social/`
  - relationship graph and relationship timeline views

Key boundary:

- keep stable world rules separate from changing world state
- keep historical events separate from present-state assumptions
- keep location identity separate from temporary location conditions
- keep explicit map facts separate from inferred or still-uncertain geography
- keep world-content language aligned with the selected work language by
  default
- keep work-scoped entity names and identifier values aligned with the source
  work language by default
- keep identifier-derived path segments under `works/{work_id}/` aligned with
  those same work-scoped identifiers by default
- treat world materials as incrementally revisable assets rather than
  one-pass summaries
- preserve correction history when later chapters change prior world
  understanding
- only source-text evidence may revise canonical world materials
- user conversation and runtime interaction must not rewrite canonical world
  foundation, history, or world-state facts
- world may expose cast, event, and relationship views for indexing
  convenience
- world may store concise character knowledge-state summaries about major
  events
- world event records should prefer major shared work-level events rather than
  small scene beats already covered by character-layer material
- world cast views should focus on the main cast and high-frequency
  supporting characters rather than one-off minor roles
- detailed character psyche, memory, voice, behavior, and stage data should
  stay under `characters/`
- detailed character-side event interpretation and memory detail should stay
  under `characters/`

### Canonical Character Layer

Location:

- recommended under `works/{work_id}/characters/{character_id}/`

Role:

- store the character bible
- store the character memory timeline
- store the relationship map
- store voice rules
- store behavior rules
- store boundaries and failure modes
- store stage snapshots
- store the stage catalog and stage summaries

Key boundary:

- character packages contain canon-grounded, user-independent baseline data
- user-caused relationship drift, nickname drift, or long-term interaction
  effects must not be written back into the character baseline
- stages must be explicit snapshots, not vague prose like "early" or "late"
- stage-selection data should be part of character assets, not handwritten
  externally at runtime
- content text should default to the work language, while field names may
  remain English
- for Chinese works, character-side names and identifier values such as
  `character_id` and `stage_id` should default to Chinese labels if they are
  work-scoped canon identifiers
- character package folders and stage-snapshot path segments derived from
  those identifiers should use the same Chinese labels by default

### User Layer

Location:

- rooted under `users/{user_id}/`
- work-specific state nested under `users/{user_id}/works/{work_id}/`

Role:

- store user identity and persona
- store bootstrap selections and setup-lock state for one user-scoped binding
- store user-to-character relationship settings
- store the active user-side role binding for the current target relationship
- store long-term interaction memory
- store user-owned long-term self-profile changes that are scoped to one work
  and one target relationship
- store user preferences and boundaries
- store the long-lived relationship core for one user and one character
- store multiple branchable contexts
- store pinned or merged shared memories
- support continuous session/context writeback during live roleplay

Suggested structure:

- `users/{user_id}/`
  - reusable user profile and optional cross-work preferences
- `users/{user_id}/works/{work_id}/characters/{character_id}/role_binding.json`
  - selected target-character reference, stage binding, user-side role binding,
    setup-lock state, and loading / writeback preferences for this user
- `users/{user_id}/works/{work_id}/characters/{character_id}/long_term_profile.json`
  - user-owned long-term self profile for this work-character relationship,
    updated only when a context is explicitly merged
- `users/{user_id}/works/{work_id}/characters/{character_id}/relationship_core/`
  - long-lived relation state and pinned memory for this user-character pair
- `users/{user_id}/works/{work_id}/characters/{character_id}/contexts/{context_id}/`
  - one specific branch context and its state, memory, and sessions

Key boundary:

- a reusable user identity may exist across works
- the user layer is where "what this character became in relation to this user"
  is stored
- ordinary runtime should not casually mutate the bootstrap binding once it has
  been locked
- work-specific relationship and memory state must not leak across different
  novels
- the user layer should reference canonical base packages in `works/{work_id}/`
  instead of duplicating them
- these changes do not pollute character canon by default
- user-scoped manifests such as `relationship_core`, `context`, and `session`
  records should carry explicit `work_id` in file content rather than relying
  only on the directory path
- session and context state may be updated continuously during live roleplay
- only explicitly retained or merged content should flow into
  `relationship_core`
- work-scoped user / relationship materials should default to the selected
  work language

### Runtime Compilation Layer

Location:

- if persisted, prefer user-scoped context trees under
  `users/{user_id}/works/{work_id}/characters/{character_id}/contexts/{context_id}/`

Role:

- dynamically choose the relevant work first
- retrieve the needed world baseline and world stage snapshot
- retrieve the relevant shared work-level events
- dynamically choose the relevant work-stage
- retrieve the target character's projection for that same selected work-stage
- dynamically resolve the user-side role or counterpart identity
- if that user-side role is also a canonical character, retrieve its selected
  stage projection for the same work-stage unless an explicit branch override
  exists
- retrieve the needed memory and relationship state
- inject behavior constraints and voice constraints
- compile the minimum useful context for one roleplay turn
- combine:
  - world baseline
  - relevant world-level event summaries
  - relevant world-stage snapshot
  - relevant location-state snapshot if needed
  - character baseline
  - selected target-stage projection
  - user persona or user-side role binding
  - if needed, user-side canonical role stage projection
  - user-owned long-term self profile
  - user-to-character relationship core
  - current context-branch state

Key boundary:

- do not push the entire character package into the model every turn
- do not push the entire world bible or full map history every turn
- do not treat compiled runtime state as canonical work truth
- prefer selection and compilation over full-context dumping

### Interface And Adapter Layer

Location:

- planned under `interfaces/`

Role:

- expose one unified capability surface to different terminals
- transform terminal input into a normalized character-session request
- transform runtime output into terminal-specific response formats
- isolate terminal differences so the roleplay core does not depend on a
  specific UI or protocol

Suggested substructure:

- `interfaces/agent/`
  - direct entry points for AI agents and scripts
- `interfaces/app/`
  - service interfaces for a frontend app or web API
- `interfaces/mcp/`
  - protocol adapters for mobile-chat MCP style integration

Key boundary:

- terminals should not directly read or write character-canon files
- terminals should go through a unified service boundary for character loading,
  memory writeback, and session recovery
- all terminals should share the same character, user, and runtime model

### Session Layer

Location:

- recommended inside work-scoped user context trees under:
  - `users/{user_id}/works/{work_id}/characters/{character_id}/contexts/{context_id}/sessions/`

Role:

- store full dialogue
- store turn summaries
- store memory changes
- store relation changes

Key boundary:

- not every conversation detail should become long-term memory
- only what the roleplay model should plausibly retain should be written back

## Terminal Integration Model

The project is expected to support at least these terminal families:

1. `AI Agent Direct Load`
   - direct loading of characters, users, and context by an agent or script
   - suited to orchestration, research, and internal tooling

2. `Frontend App`
   - a user-facing interface that starts roleplay conversations
   - suited to productized experience

3. `Mobile Chat MCP / Messaging Adapter`
   - message-oriented integration through MCP-like mobile chat systems
   - suited to more natural daily conversation entry points

Core principle:

- the roleplay core must be terminal-agnostic
- the user, character, session, and compilation model must stay unified
- terminals are only different I/O shells

## Suggested Service Boundary

The stable model above the data layers is a unified character service with at
least these capabilities:

- `list_available_works`
- `load_work_manifest`
- `load_work_canon_package`
- `build_world_package`
- `load_world_context`
- `get_work_cast_index`
- `get_work_relationship_timeline`
- `list_world_locations`
- `get_world_state_snapshot`
- `list_detected_characters`
- `build_character_package`
- `apply_source_batch_updates`
- `load_character_context`
- `load_user_context`
- `list_character_stages`
- `get_character_stage_catalog`
- `create_context`
- `start_session`
- `resume_session`
- `compile_runtime_context`
- `generate_reply`
- `commit_memory_updates`
- `pin_memory`
- `merge_contexts`
- `promote_context_to_relationship_core`
- `list_available_characters`

All terminals should use this same service surface.

## Incremental Source-Reading Flow

The recommended extraction order for one work is:

1. `Work Selection`
   - choose the source work first

2. `Candidate Identification`
   - identify candidate characters from metadata, headings, and targeted reads

3. `World-First Batch Extraction`
   - read the source in batches to build:
     - world foundation
     - history and major events
     - world-state changes
     - locations, factions, and geography
     - concise character-event awareness summaries where relevant

4. `Selected-Character Batch Extraction`
   - after the shared world layer has a usable base, read the source in
     batches for one specified character
   - keep using the agreed 7-part structure for the target-character output

Important update rule:

- every source-reading batch may add, supplement, or revise existing data
- this applies not only to the current target character, but also to:
  - world materials
  - other character packages
- later source evidence should be allowed to propagate across the whole work
  package as long as the update remains source-grounded

## Character Selection Model

This is not a heroine-only system. It is a system for arbitrary user-selected
characters.

The recommended flow separates character generation into three stages:

1. `Work Selection`
   - choose the source novel or work first
   - bind downstream analysis, world state, user relationship data, and
     runtime compilation to that work

2. `Character Identification`
   - collect names, aliases, appearance evidence, and candidate-character lists
     from the source text

3. `World-First Extraction`
   - build the shared world layer in batches before deep character packaging

4. `Character Construction`
   - let the user explicitly choose which character or characters to build
   - generate an independent package for each selected character through
     additional source batches

5. `User Role Binding`
   - let one user choose which canonical character package to load
   - store that user's mutable relationship, context, and session state under
     `users/{user_id}/`

This avoids:

- mixing data across different novels
- silently focusing on only one default character
- mixing multiple characters into one package
- leaving future AI sessions unclear about which character is being handled
- forcing deep character extraction before the shared world context exists

After a user selects a role, the runtime should load:

- canonical base data from `works/{work_id}/characters/{character_id}/`
- user-specific state from
  `users/{user_id}/works/{work_id}/characters/{character_id}/`

## Stage Selection Model

When creating runtime state, the system should first choose which work-scoped
timeline stage is active for the selected work.

Additional rule:

- world stage, target-character state, and any canon-backed user-side role
  should remain aligned to the same selected work-stage by default
- if the system later supports deliberate alternate-world branching, that
  branch should be explicit rather than implicit drift

That choice directly affects:

- the active world state
- what major work events are now history versus current state
- what the character knows and does not know
- what the character has and has not experienced yet
- the current priority of values and emotional maturity
- the character's stance toward other people
- stage-specific voice details and behavior patterns

Recommended model:

- maintain an explicit work-scoped stage catalog for the world layer
- maintain work-stage snapshots for world state
- maintain character-side stage projections that align to that same work-stage
- each selectable stage entry should contain at least:
  - `stage_id`
  - a stage title
  - a one-line selection summary
  - a summary of world, experience, relationships, and personality at that
    stage
- require the selected work-stage before creating a new context
- always load world baseline and world stage first, then load character
  baseline and the matching character-stage projection

## Conversation-Start Stage Selection

Stage selection should not rely on the user remembering or typing arbitrary
stage names.

Preferred flow:

1. the user enters `user_id`
2. the system determines whether this is a new or existing scoped setup
3. for a new setup, the user selects:
   - `work_id`
   - target `character_id`
   - active work `stage_id`
   - user-side role mode
   - if needed, user-side canon counterpart reference
4. if the user-side role is canon-backed, it inherits that same work-stage by
   default
5. the system locks the bootstrap setup
6. the system either resumes an existing context or creates a new one
7. conversation begins

For existing setups:

1. the user enters `user_id`
2. the system shows the current locked account binding
3. the system offers recoverable contexts
4. the user resumes one or creates a new context within the same locked setup

Benefits:

- stage options come from persistent canon data rather than ad hoc user memory
- every terminal can show the same stage choices
- the user does not need to memorize the full original timeline
- runtime never loads a stage setting with unclear provenance
- long-running accounts do not silently mutate their identity binding midstream

## Context Lifecycle Model

For one user and one character, the project should not use one flat pool of
conversation history. It should support branch contexts and long-term memory
promotion.

Suggested context states:

1. `ephemeral`
   - temporary branch
   - does not write into the long-term relationship core by default

2. `persistent`
   - retained branch
   - remains available for later restoration

3. `merged`
   - some or all content from the context has been merged into the long-term
     relationship core
   - used when "this character should permanently remember certain things about
     this user"

Continuous writeback rule:

- live runtime should keep `sessions/` and current `contexts/` updated as the
  conversation progresses
- long-term promotion remains selective rather than automatic for every turn
- when a merge policy allows it or the user explicitly requests it, a context
  may be partially or fully promoted into long-term relationship state
- session close should support exit keywords or equivalent close intents
- after close, the system should ask whether to merge the current context into
  long-term user-owned history before updating long-term profiles

Also support a pinned-memory mechanism:

- specific shared memories can be marked as long-term retained memories
- those memories can keep affecting roleplay even after the original branch
  context ends

## Long-Term Relationship Memory Model

To support "the character should permanently remember some things about this
user," the user layer should contain a stable long-term relationship core:

- `relationship_core`
- `long_term_profile`

It should include at least:

- current relationship labels
- long-term trust and dependence changes
- permanently retained key shared memories
- append-only promoted event history
- append-only promoted user memory history
- user-specific nickname shifts, voice shifts, and behavior shifts
- major merged turning points such as conflict, reconciliation, promises, or
  shared milestones

Recommended runtime load order:

1. world baseline
2. selected world-stage snapshot
3. target-character baseline
4. selected target-stage projection
5. user persona or user-side role binding
6. if the user-side role is also a canonical character, that side's aligned
   stage projection
7. `long_term_profile`
8. `relationship_core`
9. current `context_id` branch
10. recent session state

## Roleplay Logic Chain

The intended internal roleplay order is:

1. determine the current stage of the target character
2. if the user-side role is also canon-backed, determine that side's current
   stage as well
3. determine what the character knows and does not know
4. determine the character's current relationship state toward the user
5. determine what emotion, defense, or desire the user's input activates
6. infer the character's likely behavior tendency
7. render the response in the character's voice

So the core chain is:

`memory and relationship -> psychological reaction -> behavior decision -> language realization`

not:

`surface tone imitation -> generic reply`

## Runtime Model

Long-term roleplay should not depend on one giant prompt.

The better model is:

- persistent data stored statically
- retrieval as needed on each turn
- dynamic compilation of runtime character context
- handoff to the model for execution
- outer terminal adapters handling agent/app/MCP integration

More concretely, the current target load formula is:

`character baseline + stage snapshot + user persona or user-side role binding + optional user-side canonical stage reference + user relationship core + current context branch + recent session state`
