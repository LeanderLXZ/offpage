# Runtime Writeback And Dual-Stage Alignment

## Summary

Realigned the runtime prompt library and architecture docs with the project's
intended user-flow model.

## What Changed

- clarified that runtime writeback should be continuous during live roleplay
  rather than waiting for a separate manual trigger
- clarified that `prompts/runtime/用户入口与上下文装载.md` is the runtime
  orchestrator, not only a one-time loader
- clarified that `prompts/runtime/users状态回写.md` serves both as:
  - the entry prompt's internal writeback subflow
  - a standalone repair / merge prompt when needed
- extended stage-selection rules so they apply not only to the primary target
  character, but also to any canon-backed user-side role slot
- clarified that context content may be promoted or fully merged into
  user-owned long-term state under `relationship_core`
- updated runtime-related schemas to support:
  - user-side counterpart role fields
  - user-side counterpart stage fields
  - writeback policy
  - explicit context-merge requests

## Files Updated

- `prompts/runtime/用户入口与上下文装载.md`
- `prompts/runtime/users状态回写.md`
- `prompts/runtime/会话稀释保护检查清单.md`
- `prompts/runtime/写回前防污染检查清单.md`
- `prompts/README.md`
- `README.md`
- `users/README.md`
- `docs/architecture/system_overview.md`
- `docs/architecture/data_model.md`
- `ai_context/current_status.md`
- `ai_context/architecture.md`
- `ai_context/decisions.md`
- `ai_context/next_steps.md`
- `ai_context/handoff.md`
- `schemas/runtime_session_request.schema.json`
- `schemas/context_manifest.schema.json`
- `schemas/session_manifest.schema.json`

## Notes

- This is a historical log entry under `docs/logs/`.
