<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `Character A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# AI 上下文 <!-- holo:heading -->

<!-- holo:section start -->
供未来 AI 会话使用的压缩 handoff 索引。每个文件都指向
权威来源，而不是重述其内容。

先读 `instructions.md` —— 它列出会话起点的阅读顺序。
仅当任务直接需要时才加载更重的层（`logs/change_logs/`、
`logs/review_reports/`、`docs/`、原始输入）。
<!-- holo:section end -->

本项目收窄：延迟加载的重层是 `docs/architecture/`（而非整个 `docs/`）——
`docs/todo_list.md` 等顶层文件已在 `instructions.md` 的会话起点阅读顺序中。
