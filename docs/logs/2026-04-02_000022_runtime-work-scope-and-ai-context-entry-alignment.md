# Runtime Work-Scope And AI-Context Entry Alignment

## Summary

Aligned the runtime contracts, shared prompt entry, and formal project memory
after a review found that prompt-launched agents could bypass `ai_context/`
and that runtime/user-state manifests still relied too heavily on path-based
work scoping.

## What Changed

- added explicit `work_id` fields to runtime-related schemas:
  - `runtime_session_request`
  - `context_manifest`
  - `session_manifest`
  - `relationship_core`
- updated docs to state that runtime requests and persisted user-scoped
  manifests should carry `work_id` explicitly instead of relying only on
  directory paths
- updated the shared prompt entry so fresh agents read a minimal `ai_context`
  subset before proceeding only from prompt-local instructions
- corrected a stale top-level user-flow summary in `ai_context/handoff.md`
  so it now matches the newer dual-role, dual-stage runtime flow
- fixed a formatting typo in the runtime writeback anti-pollution checklist
- corrected the recommended user-package paths in
  `docs/architecture/data_model.md` so they include the full
  `users/{user_id}/...` prefix

## Files Updated

- `schemas/runtime_session_request.schema.json`
- `schemas/context_manifest.schema.json`
- `schemas/session_manifest.schema.json`
- `schemas/relationship_core.schema.json`
- `schemas/README.md`
- `prompts/shared/最小结构读取入口.md`
- `prompts/README.md`
- `prompts/runtime/写回前防污染检查清单.md`
- `README.md`
- `users/README.md`
- `docs/architecture/data_model.md`
- `docs/architecture/system_overview.md`
- `ai_context/current_status.md`
- `ai_context/architecture.md`
- `ai_context/decisions.md`
- `ai_context/handoff.md`

## Notes

- This is a historical log entry under `docs/logs/`.
