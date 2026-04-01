# Next Steps

## Highest Priority

1. Refine the first-pass schemas into directly writable instance formats.
   - Continue detailing:
     - `bible.json`
     - `memory_timeline.jsonl`
     - `relationships.json`
     - `voice_rules.json`
     - `behavior_rules.json`
     - `boundaries.json`
     - `stage_catalog.json`
     - `stage_snapshots/{stage_id}.json`

2. Produce a minimal usable template set.
   - At minimum:
     - one blank character-package template
     - one blank user-package template
     - one blank `relationship_core` template
     - one blank `context` template

3. Define the standard incremental chapter or excerpt processing format.
   - Clarify:
     - input format
     - output structure
     - persistent update packet format
     - conflict-recording format

4. Define the unified character-service interface.
   - It should support:
     - AI agents
     - frontend apps
     - mobile-chat MCP terminals
   - The goal is one shared capability surface, not three duplicated logic
     stacks.

5. Define the full workflow for:
   `character identification -> character selection -> character construction`
   - At minimum:
     - how candidate characters are collected from source text
     - how the user specifies which characters to build
     - how single-character and multi-character generation should be organized
     - how aliases and name collisions should be handled

6. Define the user-context lifecycle model.
   - At minimum:
     - `context_id`
     - `stage_id`
     - `ephemeral / persistent / merged`
     - how relationship-core writeback works
     - how context merging works
     - which memories can be pinned permanently

7. Define the stage-catalog display and selection format.
   - At minimum:
     - how the character package exposes key timeline nodes
     - which fields each stage summary contains
     - how stage options are shown before a conversation starts
     - how stage-catalog selection maps to `stage_id`

## Medium Priority

8. Write first-pass code stubs or a more explicit contract document for the
   unified character service.
9. Define the evidence-record format for traceable canon support.
10. Define the runtime character-compilation format in more detail.
11. Define request and response formats for terminal adapters.
12. Once the user provides the first real novel content, perform the first
   structured extraction pass.

## Later

13. Improve batch construction for multiple character packages.
14. Support richer stage slicing and relationship-stage slicing.
15. Add automatic evaluation for roleplay consistency.
16. Add more complete crawling and import support.
