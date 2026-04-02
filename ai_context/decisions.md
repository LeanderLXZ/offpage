# Key Decisions

## Confirmed Decisions

1. This project is not a one-off prompt project.
   - The goal is a long-lived character-asset system and roleplay framework.

2. The original novel is the highest authority.
   - Character conclusions should be grounded in source text rather than
     unsupported invention.

3. The project must use incremental processing.
   - Long novels may be hundreds of thousands or millions of words and should
     not be shoved into one model call.

4. Character data must be layered.
   - Plot, character definition, memory, voice, behavior, and conflicts must
     not be collapsed into one vague summary.

5. Objective fact and subjective character cognition must be separated.
   - Characters may misunderstand, conceal, or distort things, and those layers
     should be preserved.

6. Explicit canon and reasonable inference must be separated.
   - Inference is allowed, but it must be labeled explicitly.

7. The priority of roleplay is behavioral and decision consistency, not only
   voice imitation.
   - Psychological and behavioral logic should come before surface phrasing.

8. User data must be stored separately from canonical character data.
   - User identity, relationship history, preferences, and boundaries should
     not be merged into character canon.

9. The final system should allow another AI to read the character assets and
   continue roleplay.
   - Therefore the data must be structured, low-conflict, and maintainable.

10. The system should not rely on one giant total prompt.
    - Prefer long-term data plus retrieval plus runtime compilation.

11. Time-stage differences must be preserved.
    - A target character should not be flattened into a timeless static profile.

12. Conflicts and revisions must be recorded explicitly.
    - New source material should not silently overwrite older conclusions.

13. Single-round chapter analysis should use a fixed structure.
    - Recommended structure:
      - plot summary for this segment
      - newly revealed target-character definition
      - newly revealed target-character memory points
      - newly revealed voice traits
      - newly revealed behavior traits
      - conflicts or revisions against prior understanding
      - updated character profile summary

14. The core roleplay system must be terminal-agnostic.
    - Character data, user data, memory writeback, and runtime compilation
      should not be tied to one frontend or chat channel.

15. Terminal access should go through adapter layers.
    - The project should support:
      - direct AI-agent loading
      - frontend app integration
      - mobile-chat MCP or similar message adapters
    - Therefore terminal-specific logic should not duplicate the core roleplay
      system.

16. New user contexts must choose a character time stage.
    - The same character may differ substantially across stages in personality,
      history, relationships, and knowledge boundaries.

17. Character stages must be explicit snapshots.
    - Do not rely on vague labels like "early" or "late" without structure.
    - Schemas should support both `stage_id` and stage-snapshot files.

18. Character packages must contain a user-selectable stage catalog.
    - Stage-choice information is part of character data.
    - It should not depend on the user inventing or remembering stage names.

19. Stage options should be provided from character data before conversation
    start.
    - The system should present multiple summarized key timeline nodes and let
      the user choose from them.

20. One user and one character should support multiple context branches.
    - Different branches may represent different worlds, different relation
      starting points, or experimental setups.

21. Contexts must support persistence and merging.
    - Users should be able to keep some contexts long-term.
    - Users should also be able to merge selected context content into the
      long-term relationship core.

22. User-character pairs need an independent long-term relationship core.
    - That core stores retained shared memory, relationship state, and
      user-specific character drift.
    - It belongs to the user layer, not the character canon layer.

23. The project supports arbitrary specified characters, not only one heroine.
    - The user should be able to choose which character or characters to build.

24. Character identification and character construction should be separate.
    - The system may first identify candidate characters from source text and
      then let the user select which ones to package.

25. The repository should remain lightweight.
    - Schemas, templates, code, and docs can be committed.
    - Full novel bodies, databases, indexes, embeddings, caches, full user
      histories, and large runtime artifacts should not be committed by
      default.

26. `docs/logs/` should store historical summaries, not bulk data.
    - Logs should explain what changed and why, not copy raw source text,
      database contents, or long runtime outputs.

27. World data must be a first-class layer, not hidden inside character notes.
    - This project should track world foundation, history, state, locations,
      and map structure explicitly.

28. World data must be layered.
    - Keep these separate:
      - stable world foundation
      - historical events and eras
      - dynamic world-state changes
      - location identity
      - location-state changes
      - factions and institutions
      - explicit map facts vs. inferred geography

29. Canonical assets should be scoped by work.
    - World packages, character packages, work analysis, and work indexes
      should be isolated by `work_id`.
    - User-specific state is not part of canonical work assets, but it should
      still reference `work_id` under `users/{user_id}/works/{work_id}/`.

30. User flow should choose a work before character generation or roleplay.
    - The user should first choose which source novel they are operating in.

31. User data should be rooted by user rather than stored inside work
    packages.
    - Keep each user's mutable data under `users/{user_id}/`.
    - Namespace work-specific relationship state, contexts, and sessions under
      `users/{user_id}/works/{work_id}/`.
    - Do not store user-linked drift inside `works/{work_id}/`.

32. Character stage and world state should remain compatible.
    - Do not silently combine an early character stage with a late-world state
      unless the system is explicitly modeling an alternate branch.

33. Work-scoped generated content should default to the work's original
    language.
    - For example, if a work is Chinese, generated character data, world data,
      and work-scoped user / relationship materials should also be written in
      Chinese by default.

34. Structured field names may remain English even when content text follows
    the work language.
    - JSON keys, schema field names, and similar structural identifiers may
      stay in English for consistency across the repo.

35. AI-facing handoff docs may use a different language from canonical package
    content.
    - `ai_context/` may remain English for stable AI handoff.
    - This does not change the rule that generated canon and work-scoped
      content should follow the source work language by default.

36. World data should be treated as a living canon asset, not a one-shot
    static summary.
    - World foundation, history, world state, location state, factions, and
      geography may all be expanded, corrected, or refined as later text
      reveals more.

37. World revisions must be incremental and traceable.
    - New source evidence should update world materials incrementally.
    - Contradictions, corrections, and uncertainty should be recorded
      explicitly instead of silently overwriting prior world conclusions.

38. Persistent source-grounded work data should converge under a single
    `works/{work_id}/` package.
    - Source ingestion data should remain separate under
      `sources/works/{work_id}/`.

39. The world package may contain work-level cast and social views.
    - It is acceptable for `world/` to expose:
      - which characters exist in the work
      - brief role summaries
      - stage-scoped relationship views
    - These views improve indexing and runtime retrieval.

40. Detailed character canon must still live under character packages.
    - The world package may contain brief summaries and projections.
    - But detailed voice, behavior, memory, stage, and psychological material
      should remain under `characters/{character_id}/`.

41. Prefer explicit `indexes/` or `views/` over vague `other/` directories.
    - Cross-cutting lookup material should have intentional names.

42. Canonical world data may be revised by later source reading, but only by
    source evidence.
    - Later chapters may correct or refine prior world conclusions.
    - User conversations, runtime branches, or relationship drift must not
      rewrite canonical world foundation, world history, or world-state facts.

43. The world package should track major work-level events, not only static
    setting.
    - Important events across places and periods are shared simulation inputs,
      not character-only notes.

44. Detailed character-side knowledge and misunderstanding should remain in
    character packages by default.
    - The world package should not duplicate a separate character-knowledge
      layer unless the user explicitly wants that extra index.

45. Detailed event interpretation remains a character-layer concern.
    - The world package should keep concise event records and stage-scoped
      relationship views.
    - Character memory detail, emotional coloring, roleplay-relevant
      interpretation, and knowledge boundaries should remain under
      `characters/{character_id}/`.

46. World relationships should be stored by stage rather than in one timeless
    global graph.
    - Runtime should normally load only the relationship file for the selected
      `stage_id`.
    - Earlier relationship states should be retrieved on demand when needed.
47. Once an active character set exists, the default extraction flow for a
    work should use coordinated source batches that update shared world canon
    and relevant character packages together.
    - Start with work selection and candidate identification.
    - Confirm the active character set as early as practical.
    - Read each source batch once and emit world updates plus relevant
      character updates from that same batch.
    - If no active character set exists yet, or a batch is almost entirely
      shared-world material, temporary world-only output is acceptable.

48. Any source-reading batch may update multiple canonical assets.
    - A batch is not limited to adding only "new" information.
    - One batch may supplement or revise:
      - world data
      - the selected target character
      - other already-known characters
    - Source evidence discovered later may therefore propagate across the
      whole work package.

49. Targeted character supplement does not mean isolated character updates.
    - Even during a character-focused supplement pass, the system should still
      emit world corrections and other-character corrections when the source
      segment justifies them.

50. Users should bind to canonical character packages by reference instead of
    duplicating those base packages.
    - When a user selects a target character, the runtime should load the
      canonical base from `works/{work_id}/characters/{character_id}/`.
    - User-specific relationship state, drift, and history should then be
      layered from `users/{user_id}/works/{work_id}/characters/{character_id}/`.

51. For Chinese works, work-scoped canon below `work_id` should keep Chinese
    names and Chinese identifier values by default.
    - Work titles and display names should also stay in the original Chinese
      by default.
    - `work_id` itself may also be Chinese when the work root is derived from
      the original title.
    - This applies to work-scoped entities such as characters, locations,
      factions, events, and stages.
    - Generated work-scoped folder names and identifier-derived path segments
      should follow the same Chinese labels by default.
    - Do not replace source labels with pinyin-only ids when that would make
      canon inspection less readable.

52. `ai_context/` remains the first-follow-up authority for ordinary project
    continuation.
    - When a new AI resumes work from handoff, it should first follow
      `ai_context/` and the current user request.
    - It should not proactively treat `prompts/` as binding instructions on
      the first follow-up unless the user explicitly asks to use a prompt, a
      prompt file is directly named, or the task itself is prompt work.
    - The prompt library remains available as reusable workflow tooling, but
      it is not the default authority for ordinary continuation after handoff.
    - Structural field names may still remain English.

53. The world package should record major shared events, not small scene-level
    incidents by default.
    - Minor interactions, local beats, and character-specific moment-to-moment
      developments should normally stay in character-layer canon, memory, or
      batch analysis.

54. The world package should track only the main cast and high-frequency
    supporting characters by default.
    - One-off minor roles and low-importance extras do not need to be promoted
      into work-level world views unless later source evidence makes them
      structurally important.

55. User-scoped runtime writeback should be continuous during live roleplay.
    - `sessions/` and current `contexts/` should be maintained as the
      conversation progresses.
    - The system should not require a separate manual "writeback now" step
      before user-scoped state can be updated.
    - Long-term promotion into `relationship_core` remains selective.

56. Stage selection should apply to every canon-backed role slot in a context.
    - The primary target character must always select a stage from character
      data.
    - If the user-side role is also a canonical character, that side should
      also select a stage from character data.
    - Free-form user personas or custom identities do not require a canon
      stage.

57. Context content may be promoted or fully merged into user-owned long-term
    state.
    - Users should be able to retain selected context material as
      `pinned_memories`.
    - Users should also be able to partially or fully merge a context into the
      long-term `relationship_core` when policy and evidence justify it.
    - Such promotion must remain inside `users/{user_id}/...` and must not
      rewrite canonical work data.

58. Runtime request objects and persisted user-scoped manifests should carry
    explicit `work_id`.
    - Do not rely only on directory paths to recover the active work scope.
    - At minimum, runtime requests, relationship-core manifests, context
      manifests, and session manifests should all include `work_id`.

59. Prompt-library entry should still respect project handoff memory.
    - A fresh agent launched from a prompt template does not need to read the
      full repo or the full `ai_context/`.
    - But it should still read a minimal `ai_context` subset before acting, so
      prompt-local instructions do not drift away from durable project rules.

60. Runtime stage loading should use a unified work-scoped stage axis.
    - A selected `stage_id` should first identify one work-level timeline
      checkpoint for the selected work.
    - The world layer should expose stage choices and stage snapshots for that
      same work-level checkpoint.
    - Character packages may still store character-specific stage projections,
      but those projections should align to the chosen work-level `stage_id`
      rather than silently drifting onto separate implicit timelines.

61. User bootstrap selections should be locked after initial setup.
    - At initial setup, the user chooses or confirms:
      - `user_id`
      - `work_id`
      - target `character_id`
      - active `stage_id`
      - user-side role mode
      - if needed, the user-side canon-backed counterpart reference
    - Those bootstrap choices should not be casually edited during ordinary
      runtime use.
    - If a user truly needs a different binding, treat that as an explicit new
      scoped setup or migration action rather than an in-place runtime tweak.

62. Canon-backed user-side roles should inherit the target stage by default.
    - If the user-side identity is also a canonical character, that side should
      normally use the same selected work-stage as the target role.
    - Explicit cross-stage pairings are a future branch feature, not the
      default runtime behavior.

63. Session exit and long-term merge should be explicit.
    - Runtime should support user-provided exit keywords or equivalent close
      intents that end the current dialogue session.
    - After session close, the system should explicitly ask whether to merge the
      current context into user-owned long-term history.
    - `session` and `context` data should still be updated continuously during
      live roleplay.
    - Long-term self-profile or relationship-profile updates should happen only
      after explicit merge confirmation.

64. User-owned long-term history should be append-first and scope-safe.
    - Promoted events and memory points should be appended rather than silently
      overwriting older records.
    - Work- and character-scoped long-term profile changes should stay under
      `users/{user_id}/works/{work_id}/characters/{character_id}/...`.
    - Do not dump work-specific emotional drift, event memory, or relationship
      state into the global root `users/{user_id}/profile.json` by default.

65. Source extraction should expose configurable batch size and default stage
    cadence.
    - The default extraction batch size should be `10` chapters unless work
      config explicitly overrides it.
    - In the default workflow, batch `N` forms the `N`th stage candidate for
      that extraction line.
    - Stage `N` material should be cumulative through stages `1..N`, while the
      most recent stage state is treated as the active present and earlier
      stages remain historical background.

66. Runtime-engine design should live under a dedicated top-level
    `simulation/` directory.
    - Repo-wide static topology and data-model boundaries still belong under
      `docs/architecture/`.
    - Bootstrap, loading, retrieval, writeback, close-flow, and service
      contracts should live under `simulation/`.
    - Work-specific load profiles and retrieval indexes should remain under
      `works/{work_id}/indexes/`.

67. User contexts may persist full dialogue history locally, but startup should
    load only summary-layer user state by default.
    - Summary-layer user state may be loaded at startup, including:
      - role binding
      - long-term profile
      - relationship-core summaries
      - pinned memories
      - current context summaries
      - recent session summaries
    - Full `transcript.jsonl` files should be retrieved only on demand through
      context/session indexes when exact dialogue recall is needed.

68. Real user packages under `users/` should stay local and not be committed by
    default.
    - `.gitignore` should keep actual user state excluded.
    - `users/README.md` may remain committed as the structural reference.

69. Active sessions should back up every input and output in append-first
    local transcript files.
    - User input should be committed before reply generation is treated as
      durable.
    - Assistant output should be committed before the turn is considered
      closed.
    - A turn journal or equivalent append-only recovery log should make
      incomplete turns detectable after crashes.

70. Merged contexts should promote full conversation records into an
    account-level archive library.
    - The account archive library belongs under `users/{user_id}/`.
    - Archived conversation bundles should remain scoped by metadata such as
      `work_id`, `character_id`, `context_id`, and `stage_id`.
    - The source context should keep a lightweight `archive_ref` or equivalent
      provenance marker after promotion.

71. User conversation history should support on-demand indexed retrieval at
    both the active-context layer and the account-archive layer.
    - Current context history should route through session indexes and session
      summaries before loading full transcripts.
    - Account-level archive recall should route through archive indexes,
      scoped archive refs, archive summaries, and key moments before loading
      archived transcripts.

72. World relationships should be split into fixed and dynamic categories.
    - Fixed relationships are immutable structural bonds that do not change
      across stages, such as parent-child, sibling, or blood-relative ties.
    - Dynamic (stage) relationships evolve over time, such as romantic
      involvement, alliances, rivalries, or status-dependent roles.
    - Fixed relationships should be stored under
      `social/fixed_relationships/`.
    - Dynamic relationships should continue using
      `social/stage_relationships/{stage_id}.json`.
    - Runtime should load all fixed relationships at startup plus the
      selected stage's dynamic relationship file.

73. Source work packages do not need a formal JSON schema.
    - Instead, the source package construction process should be documented
      as a step-by-step specification in `docs/architecture/data_model.md`.
    - Source packages are the input layer and should not be modified by
      downstream processes.

74. `docs/logs/` should not be proactively read by AI agents.
    - Logs are a write-mostly historical archive.
    - AI agents should only read log entries when the user explicitly asks,
      when rollback is needed, or when decision provenance must be verified.
    - In all other cases, `ai_context/` is the authoritative compressed
      current truth.

75. `works/*/analysis/incremental/` and `works/*/indexes/` should be tracked
    by git as canonical work assets.
    - These are not large ephemeral artifacts but structured extraction
      outputs and retrieval indexes that form part of the canonical work
      package.

76. Do not generate per-batch report files.
    - Batch handoff information should be written directly into progress files
      (e.g. `world_batch_progress.md`, `character_batch_progress/{character_id}.md`).
    - Do not create files like `world_batch_001.md`, `world_batch_002.md`, etc.
    - The `extraction_status.md` and progress files are sufficient to track
      what happened in each batch.
    - The `prompts/shared/批次交接模板.md` template defines the fields to
      record, but those fields should be updated in-place in progress files
      rather than spawning separate report files.
