# Next Steps

## Highest Priority

1. **Continue automated extraction for the onboarded work.**
   - Phase 0/1/2/2.5/4 complete; Phase 3 in progress — S001 committed
     (sha `3bf25bf`, 2026-04-22), S002 in ERROR awaiting `--resume`,
     S003–S049 pending
   - Source + works + world manifests populated and schema-gated
   - Run: `python -m automation.persona_extraction "<work_id>" --resume`
   - `--resume` auto-resets S002 ERROR → PENDING and continues; earlier
     committed stages + lane products are preserved
   - Note: preflight tolerates dirt **outside** the work scope
     (editor state, other local changes). Dirty files inside
     `works/<work_id>/` still block — stash or commit before running.

2. **Refine schemas into directly writable instance formats.**
   - World package schemas (timeline, events, locations, maps — foundation
     schema is still implicit in baseline_production.md)

## Medium Priority

3. Write first-pass code stubs from `simulation/contracts/` and
   `simulation/flows/`.
4. Define the evidence-record format for traceable canon support.
5. Define request and response formats for terminal adapters.
6. Define user-context and session indexes for on-demand transcript recall.

## Later

7. Implement the unified character-service interface.
8. Support richer stage slicing and relationship-stage slicing.
9. Add automatic evaluation for roleplay consistency.
10. Add more complete crawling and import support.
