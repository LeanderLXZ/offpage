# Architecture Snapshot

## Active Structure

The repository now has a first-pass architecture scaffold. The active top-level
structure includes:

- `sources/`
  - raw novel inputs, normalized text, chapters, scenes
- `analysis/`
  - incremental analysis outputs, evidence, conflict notes
- `characters/`
  - long-lived packages for individual characters
- `users/`
  - long-lived user and relationship data
- `sessions/`
  - session records, turn summaries, memory updates
- `runtime/`
  - compiled runtime context
- `interfaces/`
  - external adapters and terminal integration entry points
- `schemas/`
  - first-pass persistence and runtime-request schemas
- `docs/architecture/`
  - formal architecture docs
- `ai_context/`
  - compressed handoff context for future AI sessions

## System Layers

### Source Layer

Location:

- planned under `sources/`

Role:

- accept `txt`, `epub`, web-crawled text, or user-provided excerpts
- normalize content format
- preserve source, chapter, paragraph, and scene-level location metadata

### Extraction Layer

Location:

- planned under `analysis/`

Role:

- process new text incrementally
- extract objective plot facts
- extract character-related facts
- extract character-memory points
- extract voice samples
- extract behavior samples
- extract relationship changes
- identify candidate characters and aliases from the novel
- record contradictions and uncertainty

### Canonical Character Layer

Location:

- planned under `characters/{character_id}/`

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

### User Layer

Location:

- planned under `users/{user_id}/`

Role:

- store user identity and persona
- store user-to-character relationship settings
- store long-term interaction memory
- store user preferences and boundaries
- store the long-lived relationship core for one user and one character
- store multiple branchable contexts
- store pinned or merged shared memories

Suggested structure:

- `users/{user_id}/characters/{character_id}/relationship_core/`
  - long-lived relation state and pinned memory for this user-character pair
- `users/{user_id}/characters/{character_id}/contexts/{context_id}/`
  - one specific branch context and its state, memory, and sessions

Key boundary:

- the user layer is where "what this character became in relation to this user"
  is stored
- these changes do not pollute character canon by default
- only explicitly retained or merged content should flow into
  `relationship_core`

### Runtime Compilation Layer

Location:

- planned under `runtime/compiled_context/`

Role:

- dynamically choose the relevant character stage
- retrieve the needed memory and relationship state
- inject behavior constraints and voice constraints
- compile the minimum useful context for one roleplay turn
- combine:
  - character baseline
  - selected stage snapshot
  - user-to-character relationship core
  - current context-branch state

Key boundary:

- do not push the entire character package into the model every turn
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

- planned under `sessions/`

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

- `list_detected_characters`
- `build_character_package`
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

## Character Selection Model

This is not a heroine-only system. It is a system for arbitrary user-selected
characters.

The recommended flow separates character generation into two stages:

1. `Character Identification`
   - collect names, aliases, appearance evidence, and candidate-character lists
     from the source text

2. `Character Construction`
   - let the user explicitly choose which character or characters to build
   - generate an independent package for each selected character

This avoids:

- silently focusing on only one default character
- mixing multiple characters into one package
- leaving future AI sessions unclear about which character is being handled

## Stage Selection Model

When creating a new dialogue context, the user should choose which source
timeline stage the target character is in.

That choice directly affects:

- what the character knows and does not know
- what the character has and has not experienced yet
- the current priority of values and emotional maturity
- the character's stance toward other people
- stage-specific voice details and behavior patterns

Recommended model:

- maintain an explicit `stage_catalog` in the character package
- include multiple summarized key timeline nodes in that catalog
- each stage entry should contain at least:
  - `stage_id`
  - a stage title
  - a short summary
  - a summary of experience, relationships, and personality at that stage
- maintain explicit `stage_snapshots`
- require `stage_id` when creating a new context
- always load character baseline first and then the selected stage snapshot

## Conversation-Start Stage Selection

Stage selection should not rely on the user remembering or typing arbitrary
stage names.

Preferred flow:

1. the user selects a target character
2. the system reads that character's `stage_catalog`
3. the system presents multiple key timeline nodes and summaries
4. the user selects one `stage_id`
5. a new context is created and the conversation begins

Benefits:

- stage options come from character data itself
- every terminal can show the same stage choices
- the user does not need to memorize the full original timeline
- runtime never loads a stage setting with unclear provenance

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

Also support a pinned-memory mechanism:

- specific shared memories can be marked as long-term retained memories
- those memories can keep affecting roleplay even after the original branch
  context ends

## Long-Term Relationship Memory Model

To support "the character should permanently remember some things about this
user," the user layer should contain a stable long-term relationship core:

- `relationship_core`

It should include at least:

- current relationship labels
- long-term trust and dependence changes
- permanently retained key shared memories
- user-specific nickname shifts, voice shifts, and behavior shifts
- major merged turning points such as conflict, reconciliation, promises, or
  shared milestones

Recommended runtime load order:

1. target-character baseline
2. selected stage snapshot
3. user persona
4. `relationship_core`
5. current `context_id` branch
6. recent session state

## Roleplay Logic Chain

The intended internal roleplay order is:

1. determine the current stage of the target character
2. determine what the character knows and does not know
3. determine the character's current relationship state toward the user
4. determine what emotion, defense, or desire the user's input activates
5. infer the character's likely behavior tendency
6. render the response in the character's voice

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

`character baseline + stage snapshot + user relationship core + current context branch + recent session state`
