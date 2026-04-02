# Instructions For Future AI Agents

## Primary Rule

Use `ai_context/` as the default handoff entry point for this project. Do not
begin by rereading the full chat history, the full novel corpus, or large
artifact directories.

For the first follow-up after handoff, do not proactively load or obey
`prompts/` content unless the user explicitly asks for a prompt-driven
workflow, names a prompt file, or the task is directly about prompt design or
prompt execution.

## Default Reading Order

1. `ai_context/project_background.md`
2. `ai_context/read_scope.md`
3. `ai_context/current_status.md`
4. `ai_context/architecture.md`
5. `ai_context/decisions.md`
6. `ai_context/next_steps.md`
7. `ai_context/handoff.md`

## Update Expectations

After a meaningful project change, update `ai_context/` deliberately instead of
leaving the latest state only in chat history.

### For Routine Runtime-State Or Extraction-Progress Updates

If the change is only a local runtime-state movement or a work-local extraction
progress update, do not update `ai_context/` or `docs/logs/` by default.

Typical examples:

- advancing `world_batch_progress.md`
- advancing `character_batch_progress/...`
- updating a work-local `extraction_status.md`
- refreshing local batch cursors, next-batch markers, or stage completion notes
- ordinary user/runtime state changes that do not change repo rules,
  architecture, prompts, schemas, or durable project guidance

In those cases, update the nearest work-local or user-local progress/state file
instead of treating it as a project-level handoff change.

Only promote those changes into `ai_context/` or `docs/logs/` when they also
change durable repository truth such as:

- instructions
- prompts
- schemas
- architecture
- directory rules
- data-model conventions
- retrieval / runtime loading strategy

### For Important Structure Or Documentation Changes

Update:

- `current_status.md`
- `handoff.md`
- `next_steps.md` if priorities changed
- `architecture.md` if the adopted architecture changed
- `decisions.md` if a durable decision was added or reversed

### For Major Character-Data Or Extraction-Workflow Changes

Update:

- `current_status.md`
- `handoff.md`
- `next_steps.md`
- `architecture.md` if the data model or runtime compilation logic changed
- `decisions.md` if schema, separation rules, or roleplay mechanics changed
- one timestamped entry under `docs/logs/` summarizing the historical change

### For Major Architecture Or Service-Interface Changes

Update:

- `architecture.md`
- `decisions.md`
- `current_status.md`
- `handoff.md`
- the relevant formal documents under `docs/architecture/`
- one timestamped entry under `docs/logs/`

## Logging Rules

- `ai_context/` stores compressed current truth.
- `docs/architecture/` stores formal architecture documentation.
- `docs/logs/` stores timestamped historical change records.
- **Do not proactively read `docs/logs/`.**
  - Logs are a write-mostly historical archive, not a regular context source.
  - Only read log entries when:
    - the user explicitly asks to review or reference a log
    - a rollback or historical comparison is needed
    - provenance of a specific decision needs verification
  - In all other cases, rely on `ai_context/` as the compressed current truth.
- Do not create `ai_context/` or `docs/logs/` churn for routine runtime-state
  or extraction-progress updates that are already captured in work-local
  progress files.
- Do not leave the latest state only in code or chat history.
- Use the real local time when creating log entries.
- Use the `America/New_York` timezone.
- Do not invent approximate timestamps manually.

## Git And Repository Size Rules

- Keep the repository lightweight.
- By default, do not commit large raw corpus files, databases, or runtime
  artifacts.
- Do not commit or upload these as part of normal code changes:
  - full novel bodies
  - large chapter dumps or derived text corpora
  - database files
  - vector indexes
  - embeddings, caches, or large intermediate artifacts
  - full user conversation histories
  - large runtime outputs
- Schemas, templates, code, docs, and config files are fine to commit.
- Raw corpus data, user data, databases, and retrieval indexes should usually
  remain local and be excluded by `.gitignore`.
- Only consider versioning data samples when the user explicitly wants that,
  and prefer very small samples.

### Commit Guidance

- A commit is appropriate only when the work is a coherent milestone.
- If validation is incomplete, the commit message should say so clearly.
- Do not create code commits for large data imports, cache churn, or local-only
  artifact changes.

## Scope Guidance

- Prefer compressed summaries over full raw content.
- Follow `ai_context/read_scope.md` before exploring the repo.
- On the first follow-up after handoff, treat `prompts/` as optional reference
  material rather than default task authority unless the user explicitly routes
  the task through prompt files.
- Do not paste large chunks of source text or historical material into
  `ai_context/`.
- Do not proactively read the full `sources/` corpus unless the user asks or
  the task truly depends on it.
- Do not proactively read full work-scoped session history under
  `users/{user_id}/works/{work_id}/.../sessions/` unless needed.
- Unless the user explicitly asks for it, do not paste large source text,
  database contents, or index contents into answers, logs, or docs.

## Project-Specific Guidance

- The core of this project is not surface tone mimicry. It is the recovery of
  a character's decision logic, memory logic, and relationship logic.
- Keep these layers separate:
  - objective plot
  - target character definition
  - target character memory
  - target character misunderstandings or concealments
  - target character voice style
  - target character behavior rules
  - conflict and revision notes
- The original novel is the highest authority.
- Always distinguish explicit canon from reasonable inference.
- Preserve stage differences so the target character does not collapse into one
  flat static profile.
- Do not assume the project serves one fixed character. The user should specify
  the target character when generating or loading packages.
- The runtime should not degrade into one giant prompt. Prefer retrieval and
  compilation.
- Raw novel corpus, user memory, and database-like artifacts should normally be
  treated as local data, not regular repository content.
