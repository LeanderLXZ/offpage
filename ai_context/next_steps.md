# Next Steps

## Highest Priority

1. **Continue automated extraction for the onboarded work.**
   - Phase 0–2.5 complete; Phase 3 in progress (1/49 stages committed,
     1 ERROR, 47 pending); Phase 4 scene archive independently done
   - Run: `python -m automation.persona_extraction "<work_id>" --resume`
   - `--resume` resets the ERROR stage to PENDING and picks up the
     next missing lane; finished stages + lane products are preserved
   - Monitor the next 2-3 stages for output quality, tune prompt
     templates in `automation/prompt_templates/` if needed
   - Note: need clean git working tree before running (stash or commit
     pending changes first)

2. **Refine schemas into directly writable instance formats.**
   - World package schemas (timeline, events, locations, maps — foundation
     schema is now implicit in baseline_production.md)
   - Clarify content-language inheritance from `work_manifest.language`

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
