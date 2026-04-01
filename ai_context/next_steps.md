# Next Steps

## Highest Priority

1. Use the first real work package to move from identification into selected
   architecture and package scaffolding.
   - Continue migrating persistent artifacts into:
     - `sources/works/{work_id}/` source package
     - `works/{work_id}/` canonical work package
   - The first candidate-analysis artifact has already moved into the work
     package at:
     - `works/wo-he-nvdi-de-jiushi-nieyuan/analysis/incremental/candidate_characters_initial.md`
   - Define the first real user-rooted state package layout under:
     - `users/{user_id}/works/{work_id}/`

2. Use the first real work package to move from identification into shared
   world-first extraction.
   - Start the first world-focused batch extraction using about `8-20`
     chapters per batch.
   - Define how each batch updates:
     - world canon
     - world events
     - character event-awareness views
   - Allow later batches to revise already-written world conclusions when the
     source justifies it.

3. After a usable world base exists, use the first real work package to move
   into selected character construction.
   - The current candidate list exists for:
     - `wo-he-nvdi-de-jiushi-nieyuan`
     - `works/wo-he-nvdi-de-jiushi-nieyuan/analysis/incremental/candidate_characters_initial.md`
   - Let the user choose one or two target characters.
   - Start the first batch extraction using about `8-20` chapters per batch.
   - Keep the fixed 7-part per-batch structure.

4. Define the first-pass world package model for one work.
   - At minimum:
     - world foundation
     - history timeline
     - major event registry
     - world-state snapshots
     - location records
     - location-state snapshots
     - faction records
     - map graph / route hypotheses
     - unresolved-world-question tracking
   - Also define:
     - world revision notes
     - contradiction tracking
     - how later text corrects earlier world assumptions
     - the rule that only source evidence may revise canonical world data
     - cast index and brief character summaries
     - concise character event-awareness summaries
     - work-level relationship graph / timeline views

5. Formalize work-scoped directory rules across the repo.
   - Canonical direction:
     - source package under `sources/works/{work_id}/`
     - canonical work package under `works/{work_id}/`
     - world, characters, analysis, and indexes inside the work package
     - all user-specific mutable state under `users/{user_id}/`
   - Prefer explicit `indexes/` over vague `other/`.

6. Refine the first-pass schemas into directly writable instance formats.
   - Continue detailing:
     - `bible.json`
     - `memory_timeline.jsonl`
     - `relationships.json`
     - `voice_rules.json`
     - `behavior_rules.json`
     - `boundaries.json`
     - `stage_catalog.json`
     - `stage_snapshots/{stage_id}.json`
     - world package schemas
   - Clarify content-language behavior:
     - default inheritance from `work_manifest.language`
     - whether package-level overrides are ever allowed
     - how global user-profile language differs from work-scoped user content

7. Produce a minimal usable template set.
   - At minimum:
     - one blank canonical work-package template
     - one blank character-package template
     - one blank world-package template
     - one blank user-package template
     - one blank `relationship_core` template
     - one blank `context` template

8. Define the standard incremental chapter or excerpt processing format.
   - Clarify:
     - input format
     - output structure
     - persistent update packet format
     - conflict-recording format
     - how one source batch can update world data and multiple character
       packages at once
     - how world updates and character updates are emitted separately but stay
       cross-linkable
     - how world corrections and world-state revisions are persisted

9. Define the unified character-service interface.
   - It should support:
     - AI agents
     - frontend apps
     - mobile-chat MCP terminals
   - The goal is one shared capability surface, not three duplicated logic
     stacks.

10. Formalize the full workflow for:
   `work selection -> character identification -> world-first extraction -> character selection -> character construction`
   - At minimum:
     - how work selection happens first
     - how candidate characters are collected from source text
     - how world-first batches are chosen and persisted
     - how the user specifies which characters to build
     - how a user binds to one selected canonical character package
     - how single-character and multi-character generation should be organized
     - how aliases and name collisions should be handled

11. Define the user-context lifecycle model.
   - At minimum:
     - `work_id`
     - `context_id`
     - `stage_id`
     - `ephemeral / persistent / merged`
     - how relationship-core writeback works
     - how context merging works
     - which memories can be pinned permanently

12. Define the stage-catalog display and selection format.
   - At minimum:
     - how the character package exposes key timeline nodes
     - which fields each stage summary contains
     - how stage options are shown before a conversation starts
     - how stage-catalog selection maps to `stage_id`

## Medium Priority

13. Write first-pass code stubs or a more explicit contract document for the
   unified character service.
14. Define the evidence-record format for traceable canon support.
15. Define the runtime character-compilation format in more detail.
16. Define request and response formats for terminal adapters.
17. Promote the current ad hoc candidate-identification file into a stable,
    machine-writable packet format once the schema is ready.
18. Define how world-state selection and character-stage selection interact.
19. Define how world event records and character knowledge-state views interact
    at runtime.
20. Add explicit world-source-authority notes to the first writable package
    templates.
21. Add explicit language-policy notes to the first writable package templates.

## Later

22. Improve batch construction for multiple character packages.
23. Support richer stage slicing and relationship-stage slicing.
24. Add automatic evaluation for roleplay consistency.
25. Add more complete crawling and import support.
