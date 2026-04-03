# Next Steps

## Highest Priority

1. **Run automated extraction for 我和女帝的九世孽缘.**
   - Run: `cd automation && python -m persona_extraction "我和女帝的九世孽缘" -r ..`
   - This is a fresh start (`works/` is empty, no progress file exists)
   - The pipeline will interactively ask for character selection and parameters
   - Monitor the first 2-3 batches for output quality, tune prompt templates
     in `automation/prompt_templates/` if needed

3. **Refine schemas into directly writable instance formats.**
   - Character package schemas (bible, memory, voice, behavior, stage)
   - World package schemas (foundation, timeline, events, locations, maps)
   - Clarify content-language inheritance from `work_manifest.language`

4. **Produce minimal usable templates.**
   - Blank canonical work-package template
   - Blank character-package template
   - Blank world-package template

## Medium Priority

6. Write first-pass code stubs from `simulation/contracts/` and
   `simulation/flows/`.
7. Define the evidence-record format for traceable canon support.
8. Define request and response formats for terminal adapters.
9. Define user-context and session indexes for on-demand transcript recall.

## Later

10. Implement the unified character-service interface.
11. Support richer stage slicing and relationship-stage slicing.
12. Add automatic evaluation for roleplay consistency.
13. Add more complete crawling and import support.
