# 2026-04-01 17:49:02 - User-Rooted State Model

## Summary

The architecture was adjusted so user state is rooted by user rather than
stored inside work packages.

## New Boundary

- `works/{work_id}/`
  - source-grounded canonical base information only
- `users/{user_id}/`
  - all user-specific state

This includes:

- user persona
- user-specific character drift
- user and character shared events
- relationship history
- dialogue history
- session and context state

## Character Loading Rule

When a user selects a target character, the system should:

1. load the canonical base package from
   `works/{work_id}/characters/{character_id}/`
2. load user-specific state from
   `users/{user_id}/works/{work_id}/characters/{character_id}/`
3. compile the final runtime context from those two layers
