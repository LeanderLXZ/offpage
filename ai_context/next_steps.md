# Next Steps

## Highest Priority

1. **Continue batch extraction for 我和女帝的九世孽缘.**
   - Next: `batch_002` (chapters 0011-0020)
   - Keep batch N = stage N, cumulative through 1..N
   - Once active characters are confirmed, coordinated batches update world +
     character packages together

2. **Confirm the active character set.**
   - Current candidates:
     `works/我和女帝的九世孽缘/analysis/incremental/candidate_characters_initial.md`
   - Let the user choose one or two target characters
   - Then grow character packages from shared batch reads

3. **Refine schemas into directly writable instance formats.**
   - Character package schemas (bible, memory, voice, behavior, stage)
   - World package schemas (foundation, timeline, events, locations, maps)
   - Clarify content-language inheritance from `work_manifest.language`

4. **Produce minimal usable templates.**
   - Blank canonical work-package template
   - Blank character-package template
   - Blank world-package template

5. **Define the full extraction workflow end-to-end.**
   - Work selection → candidate identification → active set confirmation →
     coordinated batch extraction → targeted supplement → package generation

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
