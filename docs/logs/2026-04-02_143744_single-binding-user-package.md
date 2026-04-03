# Single-Binding User Package

## Why

The user pointed out that the `users/_template/` structure was still modeling
one `user_id` as a container for multiple `work_id` and `character_id`
branches, but the intended runtime rule is stricter:

- each generated `user_id` should lock one work
- lock one target character
- lock one user-side role / counterpart setup
- allow multiple contexts and sessions only under that one locked binding

The old nested `works/{work_id}/characters/{character_id}/` tree therefore
made the user package look more general than the actual product rule.

## What Changed

- simplified the user package model to a single-binding root under
  `users/{user_id}/`
- moved:
  - `role_binding.json`
  - `long_term_profile.json`
  - `relationship_core/`
  - `contexts/{context_id}/...`
  directly under the user root
- replaced scoped archive refs with binding-level
  `conversation_library/archive_refs.json`
- removed default `personas/` references from startup and architecture docs
- updated the `users/_template/` skeleton to match the simplified layout
- updated `users/README.md`, `ai_context/`, formal architecture docs,
  simulation docs, prompts, schemas, and work load profiles to stop
  referencing the old multi-work user tree

## Main Files Updated

- `users/README.md`
- `users/_template/`
- `ai_context/architecture.md`
- `ai_context/current_status.md`
- `ai_context/decisions.md`
- `ai_context/handoff.md`
- `ai_context/instructions.md`
- `ai_context/read_scope.md`
- `docs/architecture/data_model.md`
- `docs/architecture/system_overview.md`
- `simulation/flows/conversation_records.md`
- `simulation/flows/close_and_merge.md`
- `simulation/retrieval/load_strategy.md`
- `schemas/role_binding.schema.json`
- `schemas/relationship_core.schema.json`
- `schemas/context_manifest.schema.json`
- `schemas/session_manifest.schema.json`
- `schemas/runtime_session_request.schema.json`
- `prompts/runtime/用户入口与上下文装载.md`
- `prompts/runtime/users状态回写.md`
- `prompts/shared/最小结构读取入口.md`
- `prompts/analysis/角色信息抽取.md`
- `works/我和女帝的九世孽缘/indexes/load_profiles.json`

## Outcome

The repository now consistently documents the user package as:

1. one locked binding per `user_id`
2. multiple contexts and sessions under that binding
3. canonical work / character data still loaded from `works/{work_id}/...`
4. all mutable user drift and conversation history kept under `users/{user_id}/`

This removes an unnecessary directory layer while keeping explicit `work_id`,
`character_id`, and `stage_id` inside manifests and runtime records.
