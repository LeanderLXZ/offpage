<!--
MAINTENANCE — 更新 ai_context/ 前读：这是 AI 快速 follow 项目的索引，不是详细手册。
1. 写"是什么 / 在哪找"，指向权威源（代码路径 / docs/*.md / schema / log）
2. 优先删而不是加；新增前先看能否合并已有条目
3. 只写当前设计，不写"旧 / legacy / 已废弃 / 原为"
4. 不出现真实书名 / 角色 / 剧情，用通用占位符（`<work_id>`, `角色A`, `S001`）
5. 预算：architecture / decisions / requirements 各 ≤ ~150 行；全目录读完 ≤ 几千 token
-->

# AI Context

Compressed handoff index for future AI sessions. Each file points to
authoritative sources instead of re-stating them.

Read `instructions.md` first — it lists the session-start reading order.
Only load heavier layers (`docs/logs/`, `docs/review_reports/`,
`docs/architecture/`, raw sources) when the task directly requires it.
