# Persona Engine

Persona Engine is a work-scoped, multi-character roleplay architecture for
long-form novels.

The project is designed around two work-scoped package families:

- source work packages under `sources/works/{work_id}/`
- canonical work packages under `works/{work_id}/`
- user state packages under `users/{user_id}/`

The work package is where source-grounded base information should converge for
one work, including:

- world data
- character data
- work-scoped analysis and evidence
- work-level indexes

The intended user flow is:

1. choose work
2. choose character
3. choose stage
4. create or resume context

The current repository state is an architecture scaffold. The first goal is to
make the data model stable enough that future AI sessions, scripts, and product
surfaces can all build on the same package format.

When a user chooses a target character, the system should load the canonical
base package from `works/{work_id}/characters/{character_id}/` and then apply
user-specific relationship state, context state, and history from
`users/{user_id}/`.

Start here:

- `ai_context/`
- `docs/architecture/system_overview.md`
- `docs/architecture/data_model.md`
- `works/README.md`
- `schemas/`
