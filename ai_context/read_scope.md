<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `角色A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# Read Scope

## Default Priority

Read first:

- `ai_context/`
- When relevant: `works/{work_id}/analysis/`, `works/{work_id}/world/`,
  `works/{work_id}/characters/`, `users/{user_id}/`

Do not proactively read `prompts/` unless the user asks or the task is
prompt-related.

## Do Not Read By Default

- `sources/` — large raw corpus
- `users/.../sessions/` — full conversation history
- `works/.../analysis/evidence/` — full evidence
- `docs/logs/` — full history
- `docs/review_reports/` — past audit snapshots
- Databases, vector stores, indexes, large generated artifacts

## When To Read Deeper

- User explicitly asks
- Task depends on specific source evidence
- Compressed context is insufficient
- A conflict needs provenance verification

## Practical Rule

Prefer targeted reads, specific files, minimal excerpts, summaries
first. Avoid scanning the full novel, loading all session history,
reading all evidence files, reading all logs, or bulk-pasting source
text into answers.
