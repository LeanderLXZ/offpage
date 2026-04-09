# Next Steps

## Highest Priority

1. **Continue automated extraction for 我和女帝的九世孽缘.**
   - Phase 0 (summarization) and Phase 1 (analysis) are complete
   - Run: `cd automation && python -m persona_extraction "我和女帝的九世孽缘" -r .. -c 姜寒汐 王枫`
   - This will skip Phase 0-1 (outputs exist), auto-confirm Phase 2 with
     preset characters, then proceed through Phase 2.5 → Phase 3 → Phase 3.5 → Phase 4
   - 40 batches total, target characters: 姜寒汐, 王枫
   - Monitor the first 2-3 batches for output quality, tune prompt templates
     in `automation/prompt_templates/` if needed
   - Note: need clean git working tree before running (stash or commit pending
     changes first)

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
