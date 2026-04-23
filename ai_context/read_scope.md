<!--
MAINTENANCE — 更新 ai_context/ 前读：这是 AI 快速 follow 项目的索引，不是详细手册。
1. 写"是什么 / 在哪找"，指向权威源（代码路径 / docs/*.md / schema / log）
2. 优先删而不是加；新增前先看能否合并已有条目
3. 只写当前设计，不写"旧 / legacy / 已废弃 / 原为"
4. 不出现真实书名 / 角色 / 剧情，用通用占位符（`<work_id>`, `角色A`, `S001`）
5. 预算：architecture / decisions / requirements 各 ≤ ~150 行；全目录读完 ≤ 几千 token
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
