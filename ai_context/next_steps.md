# Next Steps

## Highest Priority

1. Implement the unified work-stage model end to end.
   - Define the first real `works/{work_id}/world/stage_catalog.json`
   - Define the first real `works/{work_id}/world/stage_snapshots/{stage_id}.json`
   - Define how character stage snapshots project the same work-level `stage_id`
   - Enforce the runtime rule that world state and character state stay aligned
     to the same selected stage by default

2. Formalize the locked user bootstrap model.
   - Define the first real new-user setup flow:
     - `user_id`
     - `work_id`
     - target `character_id`
     - active `stage_id`
     - user-side role mode
     - optional canon-backed user-side counterpart
   - Define how `setup_locked` is persisted
   - Define how existing users are loaded and displayed before context recovery
   - Define what counts as an explicit migration rather than an ordinary edit

3. Implement the explicit close-and-merge runtime lifecycle.
   - Define exit keywords or equivalent close intents
   - Define the question shown after session close
   - Define how merge acceptance versus decline changes writeback behavior
   - Define how `long_term_profile` and `relationship_core` are updated only
     after merge confirmation
   - Keep `session / context` updates continuous during live roleplay

4. Use the first real work package to move into shared world-first extraction.
   - Start the first world-focused batch extraction using default `5`-chapter
     batches unless work config overrides it
   - Treat batch `N` as the default stage `N` candidate
   - Define how stage `N` extraction accumulates `1..N`
   - Define how each batch updates:
     - world canon
     - world stage snapshots
     - world events
     - character event-awareness views
   - Allow later batches to revise already-written world conclusions when the
     source justifies it

5. After a usable world base exists, use the first real work package to move
   into selected character construction.
   - The current candidate list exists for:
     - `我和女帝的九世孽缘`
     - `works/我和女帝的九世孽缘/analysis/incremental/candidate_characters_initial.md`
   - Let the user choose one or two target characters
   - Start the first character extraction using default `5`-chapter batches
     unless work config overrides it
   - Keep the fixed 7-part per-batch structure
   - Ensure each stage yields:
     - one-line selection summary
     - cumulative history through that stage
     - current-state portrayal for status, voice, mood, and relationships

6. Formalize work-scoped directory rules across the repo.
   - Canonical direction:
     - source package under `sources/works/{work_id}/`
     - canonical work package under `works/{work_id}/`
     - world, characters, analysis, and indexes inside the work package
     - do not reintroduce a repo-level `analysis/` directory
     - all user-specific mutable state under `users/{user_id}/`
   - Prefer explicit `indexes/` over vague `other/`.

7. Refine the first-pass schemas into directly writable instance formats.
   - Continue detailing:
     - `bible.json`
     - `memory_timeline.jsonl`
     - `relationships.json`
     - `voice_rules.json`
     - `behavior_rules.json`
     - `boundaries.json`
     - `role_binding.json`
     - `long_term_profile.json`
     - world stage schemas
     - `stage_catalog.json`
     - `stage_snapshots/{stage_id}.json`
     - world package schemas
   - Clarify content-language behavior:
      - default inheritance from `work_manifest.language`
      - whether package-level overrides are ever allowed
      - how global user-profile language differs from work-scoped user content
   - Align schema expectations with the new rule that work-scoped canon
     identifiers and `work_id` itself may be Chinese for Chinese works
   - Align generated folder names and path-building rules with those same
     Chinese work-scoped identifiers

8. Produce a minimal usable template set.
   - At minimum:
     - one blank canonical work-package template
     - one blank character-package template
     - one blank world-package template
     - one blank user-package template
     - one blank `relationship_core` template
     - one blank `long_term_profile` template
     - one blank `context` template

9. Define the standard incremental chapter or excerpt processing format.
   - Clarify:
     - input format
     - output structure
     - persistent update packet format
     - conflict-recording format
     - how batch size is configured per work
     - how batch `N` maps to stage `N`
     - how stage `N` accumulates prior stages while still rendering the latest
       stage as present state
      - how one source batch can update world data and multiple character
        packages at once
      - how world updates and character updates are emitted separately but stay
        cross-linkable
      - how world corrections and world-state revisions are persisted

10. Define the unified character-service interface.
   - It should support:
     - AI agents
     - frontend apps
     - mobile-chat MCP terminals
   - The goal is one shared capability surface, not three duplicated logic
     stacks.

11. Formalize the full workflow for:
   `work selection -> character identification -> world-first extraction -> character selection -> character construction`
   - At minimum:
     - how work selection happens first
     - how candidate characters are collected from source text
     - how world-first batches are chosen and persisted
     - how the user specifies which characters to build
     - how a user binds to one selected canonical character package
     - how single-character and multi-character generation should be organized
     - how aliases and name collisions should be handled
     - how work-scoped Chinese identifiers are stored without losing the
       original source labels
     - how those same identifiers propagate into generated folder names

12. Define the user-context lifecycle model.
   - At minimum:
     - `work_id`
     - `context_id`
     - `stage_id`
     - default inherited stage binding for any canon-backed user-side role
     - `setup_locked`
     - `ephemeral / persistent / merged`
     - continuous `session / context` writeback rhythm during live roleplay
     - explicit close-session trigger
     - merge confirmation after close
     - how relationship-core writeback works
     - how long-term-profile writeback works
     - how context merging works
     - which memories can be pinned permanently

13. Define the stage-catalog display and selection format.
   - At minimum:
     - how the world package exposes key timeline nodes
     - how character packages expose aligned stage projections
     - which fields each stage summary contains
     - how stage options are shown before a conversation starts
     - how the same mechanism applies to any canon-backed user-side role slot
     - how stage-catalog selection maps to `stage_id`

## Medium Priority

14. Write first-pass code stubs or a more explicit contract document for the
   unified character service.
15. Define the evidence-record format for traceable canon support.
16. Define the runtime character-compilation format in more detail.
17. Define request and response formats for terminal adapters.
18. Promote the current ad hoc candidate-identification file into a stable,
    machine-writable packet format once the schema is ready.
19. Define how world-stage selection and character-stage selection interact.
20. Define how world event records and character knowledge-state views interact
    at runtime.
21. Add explicit world-source-authority notes to the first writable package
    templates.
22. Add explicit language-policy notes to the first writable package templates.
23. Decide which prompt-library workflows under `prompts/` should later be
    upgraded into real skills or scripted tools.

## Later

24. Improve batch construction for multiple character packages.
25. Support richer stage slicing and relationship-stage slicing.
26. Add automatic evaluation for roleplay consistency.
27. Add more complete crawling and import support.
