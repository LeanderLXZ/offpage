<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `Character A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# Next Steps

## Highest Priority

1. **Refine schemas into directly writable instance formats.**
   - World package: timeline, events, locations, maps still need
     directly writable schemas. `foundation` already has a permissive
     schema at `schemas/world/foundation.schema.json` (see
     `docs/architecture/schema_reference.md`).

## Medium Priority

2. Write first-pass code stubs from `simulation/contracts/` and `simulation/flows/`.
3. Define evidence-record format for traceable canon support.
4. Define request / response formats for terminal adapters.
5. Define user-context and session indexes for on-demand transcript recall.

## Later

6. Implement the unified character-service interface.
7. Support richer stage slicing (including relationship-stage slicing).
8. Add automatic evaluation for roleplay consistency.
9. Add more complete crawling and import support.
