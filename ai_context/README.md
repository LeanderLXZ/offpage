# AI Context

This directory is the compressed project handoff context for future AI agents.
It is not intended to be the full human-facing project documentation set.

Goals:

- help a new AI catch up quickly
- avoid rereading full history by default
- preserve the current project background, rules, architecture, status, and
  next steps

Recommended read order for a new AI:

1. `instructions.md`
2. `read_scope.md`
3. `project_background.md`
4. `requirements.md`
5. `current_status.md`
6. `architecture.md`
7. `decisions.md`
8. `next_steps.md`
9. `handoff.md`

Only read heavier context when one of the following is true:

- the user explicitly asks for historical tracing
- the compressed context here is insufficient
- a conclusion needs source verification
- the current task directly depends on a specific source file, session record,
  or artifact

`docs/logs/` is the history layer and should not be read proactively by
default.
