<!--
MAINTENANCE — 更新 ai_context/ 前读：这是 AI 快速 follow 项目的索引，不是详细手册。
1. 写"是什么 / 在哪找"，指向权威源（代码路径 / docs/*.md / schema / log）
2. 优先删而不是加；新增前先看能否合并已有条目
3. 只写当前设计，不写"旧 / legacy / 已废弃 / 原为"
4. 不出现真实书名 / 角色 / 剧情，用通用占位符（`<work_id>`, `角色A`, `S001`）
5. 预算：architecture / decisions / requirements 各 ≤ ~150 行；全目录读完 ≤ 几千 token
-->

# Project Background

Long-lived novel character roleplay system. A reusable character-asset
system that can be updated and loaded across sessions — not a one-off
prompt experiment.

## Goal

Deep, stable roleplay of specific novel characters — consistent
personality, memory, knowledge boundaries, and behavioral patterns
across long conversations and multiple sessions.

## Guiding Principles

- **Deep roleplay over surface mimicry.** Behavioral / decision consistency is priority; tone is secondary.
- **Original novel = highest authority.** All character data traces to source text.
- **Incremental, not from scratch.** Long novels processed in stages; data builds over time.
- **Layered, not one giant prompt.** Source / world / character / user / runtime — each layer has clear boundaries.

## Build Order

1. Character-asset system (schemas, data model)
2. Extraction workflows (stage processing, incremental updates)
3. Runtime roleplay engine (loading, retrieval, session management)
4. Terminal integrations (agent, app, MCP)

Requirements → `requirements.md`. Architecture → `architecture.md`.
