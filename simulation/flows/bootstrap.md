# Bootstrap Flow

## Goal

Resolve the scoped runtime setup before the first roleplay turn.

## Steps

1. Resolve `user_id`.
2. Detect whether this is:
   - a new scoped setup
   - an existing locked setup
3. If new:
   - choose `work_id`
   - choose target `character_id`
   - choose active `stage_id`
   - choose user-side role mode
   - if the user-side role is canon-backed, bind it to the same `stage_id` by
     default
4. Create or confirm:
   - `role_binding.json`
   - work-scoped user manifest
   - `long_term_profile.json`
   - `relationship_core/`
   - `contexts/`
5. Lock the setup for ordinary runtime.
6. Create or resume a `context_id`.

## Outputs

- one locked runtime binding
- one selected work-stage binding
- one target-character binding
- one active context

## Guardrails

1. Do not silently edit a locked setup during ordinary runtime.
2. If the user truly wants another work, character, or stage, treat that as a
   new setup or explicit migration.
3. If the selected stage is incompatible with the loaded canon package, stop
   and surface the mismatch.
4. Do not start roleplay before the stage binding is explicit.
