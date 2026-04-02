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

For Chinese works, keep the original Chinese work title, allow `work_id`
itself to be Chinese, and keep work-scoped canon under `works/{work_id}/` in
Chinese names, Chinese identifier values, and matching generated folder names
by default. Avoid replacing source labels with pinyin-only ids when that would
make canon harder to read.

The intended user flow is:

1. choose work
2. choose target character
3. choose the target character stage
4. choose the user's current role or counterpart identity
5. if that user-side role is also a canonical character, choose its stage too
6. create or resume context

During live roleplay, the runtime should continuously maintain user-scoped
session and context state under `users/{user_id}/` rather than waiting for a
separate manual writeback step. Promotion into `relationship_core`,
`pinned_memories`, or a merged context remains selective and policy-driven.

The current repository state is an architecture scaffold. The first goal is to
make the data model stable enough that future AI sessions, scripts, and product
surfaces can all build on the same package format.

When a user chooses a target character, the system should load the canonical
base package from `works/{work_id}/characters/{character_id}/` and then apply
user-specific relationship state, context state, and history from
`users/{user_id}/`.

For runtime safety across multiple works, persisted user-state manifests and
runtime request objects should also carry `work_id` explicitly rather than
relying only on directory paths.

Start here:

- `ai_context/`
- `docs/architecture/system_overview.md`
- `docs/architecture/data_model.md`
- `prompts/`
- `works/README.md`
- `schemas/`
