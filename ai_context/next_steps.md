# Next Steps

## Highest Priority

1. Implement the unified work-stage model end to end.
   - Extend the first real `works/{work_id}/world/stage_catalog.json`
     and `world/stage_snapshots/{stage_id}.json` that now exist for:
     - `我和女帝的九世孽缘`
     - currently through `阶段1_南林初遇`
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
   - Use `simulation/flows/close_and_merge.md` as the current contract
   - Define exit keywords or equivalent close intents
   - Define the question shown after session close
   - Define how merge acceptance versus decline changes writeback behavior
   - Define how `long_term_profile` and `relationship_core` are updated only
     after merge confirmation
   - Keep `session / context` updates continuous during live roleplay

4. Use the first real work package to move into coordinated world-plus-
   character batch extraction.
   - Continue from the current extraction base for:
     - `works/我和女帝的九世孽缘/analysis/incremental/source_batch_plan.md`
     - `works/我和女帝的九世孽缘/analysis/incremental/world_batch_progress.md`
     - `works/我和女帝的九世孽缘/analysis/incremental/candidate_characters_initial.md`
     - `works/我和女帝的九世孽缘/world/stage_catalog.json`
   - Next recommended target:
     - `batch_002`
     - cumulative through `0011-0020`
   - Keep treating batch `N` as the default stage `N` candidate
   - Keep stage `N` extraction cumulative through `1..N`
   - Once active characters are confirmed, continue using each shared batch to
     update:
     - world canon
     - world stage snapshots
     - world events
     - stage-scoped relationship views
     - relevant character packages
     - work-level retrieval indexes when needed
   - If no active character set is confirmed yet, or a batch is almost
     entirely shared-world material, temporary world-only output is
     acceptable.
   - Allow later batches to revise already-written world conclusions when the
     source justifies it

5. After active characters are confirmed, use the first real work package to
   move into stable character construction through coordinated batches and
   targeted supplement when needed.
   - The current candidate list exists for:
     - `我和女帝的九世孽缘`
     - `works/我和女帝的九世孽缘/analysis/incremental/candidate_characters_initial.md`
   - Let the user choose one or two target characters
   - Prefer growing character packages from the same shared batch reads rather
     than rereading the same material in a separate character-only pass
   - Use targeted supplement passes only when coordinated batch output still
     leaves clear gaps
   - Keep using default `10`-chapter batches unless work config overrides it
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

10. Implement the unified character-service interface from the current
    simulation contracts.
   - It should support:
     - AI agents
     - frontend apps
     - mobile-chat MCP terminals
   - The goal is one shared capability surface, not three duplicated logic
     stacks.

11. Formalize the full workflow for:
   `work selection -> character identification -> active character set confirmation -> coordinated batch extraction -> targeted supplement when needed -> character construction`
   - At minimum:
     - how work selection happens first
     - how candidate characters are collected from source text
     - how active characters are confirmed and refreshed
     - how coordinated batches are chosen and persisted
     - when temporary world-only batches are acceptable
     - when targeted supplement is actually needed
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
     - which summary-layer user files are startup-required
     - how full transcript recall routes through session indexes
     - how archived conversation bundles enter the account library
     - how source contexts retain `archive_ref` after promotion
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

14. Write first-pass code stubs from `simulation/contracts/` and
   `simulation/flows/`.
15. Define the evidence-record format for traceable canon support.
16. Refine the runtime packet format in
   `simulation/contracts/runtime_packets.md` as implementation gets closer.
17. Define request and response formats for terminal adapters.
18. Define user-context and session indexes for on-demand transcript recall.
19. Define account-level conversation archive indexes and archive bundle
    manifests.
20. Promote the current ad hoc candidate-identification file into a stable,
    machine-writable packet format once the schema is ready.
21. Define how world-stage selection and character-stage selection interact.
22. Define how stage-scoped world relationships and character-side knowledge
    boundaries interact at runtime.
23. Add explicit world-source-authority notes to the first writable package
    templates.
24. Add explicit language-policy notes to the first writable package templates.
25. Decide which prompt-library workflows under `prompts/` should later be
    upgraded into real skills or scripted tools.

## Later

26. Improve batch construction for multiple character packages.
27. Support richer stage slicing and relationship-stage slicing.
28. Add automatic evaluation for roleplay consistency.
29. Add more complete crawling and import support.
