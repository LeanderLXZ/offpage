# Project Background

## What This Project Is

This project is meant to become a long-lived novel character roleplay system.
Its core goal is to let AI stably roleplay any user-selected character from a
source novel, not just one fixed protagonist.

It is not a one-off prompt experiment and not a temporary character-card
summary for one chat. The goal is a reusable character-asset system that can be
updated, corrected, and loaded by other AI systems over time.

## Original User Goals

The user wants a system that can:

- read long-form novel content
- support source inputs including:
  - web-crawled text
  - `epub`
  - `txt`
  - user-provided raw excerpts, chapter text, or summaries
- identify and extract the "soul" of specified characters
- let the user choose which characters to build
- create character folders that store personality, history, habits, style,
  boundaries, and related material
- create user folders that store user identity, user role, conversation
  history, and related relationship memory
- let future AI systems read these assets and perform deep, long-term, stable
  roleplay
- let the user choose a character time stage when creating a new context
- let some user-character contexts be retained permanently or merged into a
  longer-lived relationship memory
- support multiple terminals in the future, including:
  - direct AI-agent loading
  - a frontend app
  - mobile-chat MCP style integrations

## Initial Data Reality

The project is still in an early phase and no real novel corpus has been
imported yet.

That means the immediate priority is not extraction optimization. The priority
is to define:

- the information-separation model
- the character-package structure
- the processing workflow
- the handoff documentation

before real source ingestion begins.

## Important User Preferences

The user has repeatedly emphasized these preferences:

- roleplay depth matters more than shallow mimicry
- the system should stay close to the original target character, not drift into
  generic AI-roleplay tone
- the work should focus on information that directly improves roleplay quality,
  not generic literary commentary
- new chapters should update existing materials incrementally rather than
  restart analysis from scratch
- new user contexts should explicitly choose a character stage
- the user should be able to decide which memories are permanently retained and
  which stay branch-local
- the project should support arbitrary specified characters, not only a female
  lead
- the system must separate:
  - objective plot
  - target character definition
  - target character memory
  - target character voice style
  - target character behavior rules
- the system must track conflicts, revisions, and inference boundaries

## Why The Structure Looks Like This

The project is intentionally not a single giant prompt. Instead it is split
into long-lived layers:

- raw input layer
- extraction and analysis layer
- character asset layer
- user asset layer
- relationship-branch and long-term memory layer
- runtime compilation layer
- session and memory-update layer
- terminal adapter layer

This structure is meant to:

- support incremental processing of very long novels
- let character assets keep growing over time
- let future AI sessions catch up quickly
- let the same core system be reused by multiple terminals
- avoid re-understanding the full project history every time

## Architectural Mindset

The guiding sequence is:

- first design the character-asset system correctly
- then define schemas and incremental update rules
- then build source processing and extraction workflows
- then build runtime roleplay compilation and long-term conversation mechanics
- finally add terminal integrations on top of a stable core

The goal is not to stack a fragile prompt that happens to work once. The goal
is to build a durable foundation for long-term consistent roleplay.
