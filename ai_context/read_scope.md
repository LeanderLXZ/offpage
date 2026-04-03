# Read Scope

## Default Priority

Read these first:

- `ai_context/`
- When relevant: `works/{work_id}/analysis/`, `works/{work_id}/world/`,
  `works/{work_id}/characters/`, `users/{user_id}/`

Do not proactively read `prompts/` unless the user asks or the task is
prompt-related.

## Do Not Read By Default

- Large raw corpus under `sources/`
- Full conversation history under `users/.../sessions/`
- Full evidence under `works/.../analysis/evidence/`
- Full history under `docs/logs/`
- Databases, vector stores, indexes, or large generated artifacts

## When To Read Deeper

Only when:

- The user explicitly asks
- The task depends on specific source evidence
- Compressed AI context is insufficient
- A conflict needs provenance verification

## Practical Rule

Prefer: targeted reads, specific files, minimal excerpts, summaries first.

Avoid: scanning the full novel, reading all session history, loading all
evidence files, reading all logs, bulk-pasting source text into answers.
