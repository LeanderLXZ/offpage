<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `角色A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
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
