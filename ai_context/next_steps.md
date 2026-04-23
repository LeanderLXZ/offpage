<!--
MAINTENANCE — 更新 ai_context/ 前读：这是 AI 快速 follow 项目的索引，不是详细手册。
1. 写"是什么 / 在哪找"，指向权威源（代码路径 / docs/*.md / schema / log）
2. 优先删而不是加；新增前先看能否合并已有条目
3. 只写当前设计，不写"旧 / legacy / 已废弃 / 原为"
4. 不出现真实书名 / 角色 / 剧情，用通用占位符（`<work_id>`, `角色A`, `S001`）
5. 预算：architecture / decisions / requirements 各 ≤ ~150 行；全目录读完 ≤ 几千 token
-->

# Next Steps

## Highest Priority

1. **Continue automated extraction for the onboarded work package.**
   - Phase 0/1/2/2.5/4 complete; Phase 3 in progress — S001 committed
     (sha `3bf25bf`, 2026-04-22), S002 in ERROR awaiting `--resume`,
     S003–S049 pending.
   - Resume command → `handoff.md` §Current Work Continuation.
   - `--resume` auto-resets ERROR → PENDING; committed stages + lane
     products preserved.
   - Preflight tolerates dirt **outside** the work scope (editor state,
     other local changes); scope-internal dirt still blocks.

2. **Refine schemas into directly writable instance formats.**
   - World package: timeline, events, locations, maps — foundation
     schema still implicit in `automation/prompt_templates/baseline_production.md`.

## Medium Priority

3. Write first-pass code stubs from `simulation/contracts/` and `simulation/flows/`.
4. Define evidence-record format for traceable canon support.
5. Define request / response formats for terminal adapters.
6. Define user-context and session indexes for on-demand transcript recall.

## Later

7. Implement the unified character-service interface.
8. Support richer stage slicing (including relationship-stage slicing).
9. Add automatic evaluation for roleplay consistency.
10. Add more complete crawling and import support.
