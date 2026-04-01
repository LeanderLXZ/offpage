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
  - `sources/works/wo-he-nvdi-de-jiushi-nieyuan/`
  - it is normalized from a local `epub`
  - it contains `537` normalized chapters
- A matching work-scoped canonical package scaffold now exists at:
  - `works/wo-he-nvdi-de-jiushi-nieyuan/`
- The first-pass candidate-character identification result for that work now
  exists at:
  - `works/wo-he-nvdi-de-jiushi-nieyuan/analysis/incremental/candidate_characters_initial.md`
- World data is now part of the intended canonical model, not optional side
  commentary.
- The preferred architecture direction is now work-scoped:
  - choose work first
  - then choose character
  - then choose stage
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
  - English may still be used for JSON keys and schema field names
  - `ai_context/` remains English as the AI-facing handoff layer
- `ai_context/` is the primary compressed truth source for future AI sessions.
- The long-term goal is that another AI can load a character package and
  stably roleplay a user-specified character.
- Do not assume the project is only about one heroine. Characters are selected
  explicitly at generation time.
- The project should support at least three terminal families:
  - direct AI-agent loading
  - frontend app integration
  - mobile-chat MCP or similar message terminals
- Therefore the core roleplay engine must remain terminal-agnostic.
- New user contexts should choose a character stage.
- Stage options should come from the character package itself, not from
  user-written ad hoc labels.
- Before a conversation starts, the system should display multiple summarized
  timeline nodes from the character's stage catalog.
- One user and one character should support multiple context branches.
- Some contexts or memory points should be permanently retained or merged into
  the long-term relationship core.
- `docs/logs/` is the historical-summary layer and should not be read by
  default.
- Keep the repo lightweight. Do not treat full novel bodies, databases,
  indexes, or large runtime artifacts as normal commit content.
- Do not reread the full normalized novel by default when continuing current
  source-work tasks. Start from:
  - work metadata
  - chapter index
  - the current candidate-character identification file
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
- Preferred extraction order for one work:
  - candidate identification first
  - world-first batch extraction next
  - selected-character batch extraction after the shared world base exists
- World packages should include major work-level events, not only static
  setting.
- World packages may include concise character knowledge summaries about major
  events.
  - Keep detailed event memory and interpretation under `characters/`.
- World packages may include work-level cast and social views.
  - brief character summaries are fine there
  - relationship graph / timeline views are fine there
  - detailed character psyche, memory, voice, and stage data still belong
    under `characters/`

## The Roleplay Logic You Should Preserve

Do not think of this project as "write a prompt that sounds like the
character."

The intended logic is:

- reconstruct the character's current time stage
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
- for current source-work tasks, begin with the existing work metadata and
  candidate-character analysis before opening raw chapter files widely
- the persistent candidate-character analysis file now lives under the work
  package rather than top-level `analysis/`
- for source extraction, prefer building the shared world layer in batches
  before deep extraction for one selected character
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
- define the unified character-service interface and terminal-adapter boundary
  early
- define the canonical construction flow:
  `work selection -> character identification -> world-first extraction -> character selection -> character-package generation`
- define the user/runtime flow:
  `user selection -> work selection -> role binding -> stage selection -> context creation`
- define the world package and work-scoped directory rules early
- preserve the source work language in generated canonical content
- define `stage_catalog`, `stage_id`, `context_id`, `relationship_core`, and
  context-merge rules early
- remember that any one source-reading batch may revise world data and other
  character packages, not only the current target
- once the user selects a target character, continue with the agreed 7-part
  batch-analysis structure for that target while still propagating justified
  world or other-character corrections
- after each meaningful milestone, update `current_status.md`,
  `next_steps.md`, and this file
