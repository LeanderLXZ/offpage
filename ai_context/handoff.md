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

## Practical Starting Advice

- read all of `ai_context/` first
- if no source text has been provided yet, prioritize schemas and directory
  structure
- read `docs/architecture/system_overview.md` and
  `docs/architecture/data_model.md`
- define the unified character-service interface and terminal-adapter boundary
  early
- define the full flow for:
  `character identification -> user selection -> character-package generation`
- define `stage_catalog`, `stage_id`, `context_id`, `relationship_core`, and
  context-merge rules early
- once the user starts providing chapters, follow the agreed 7-part analysis
  structure
- after each meaningful milestone, update `current_status.md`,
  `next_steps.md`, and this file
