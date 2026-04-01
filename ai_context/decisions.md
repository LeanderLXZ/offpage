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
      - relationship graph views
      - relationship timeline views
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

44. The world package may include concise character-event knowledge views.
    - It is acceptable to store work-level summaries of what each character
      knows, partly knows, misunderstands, or has not yet learned about major
      events.

45. Detailed event interpretation remains a character-layer concern.
    - The world package should keep concise event records and concise
      knowledge-state summaries.
    - Character memory detail, emotional coloring, and roleplay-relevant
      interpretation should remain under `characters/{character_id}/`.

46. The default extraction order for a work should be world-first, then
    selected-character construction.
    - First read the source in batches to build the shared world layer.
    - After that, read the source in batches for a specified character.

47. Any source-reading batch may update multiple canonical assets.
    - A batch is not limited to adding only "new" information.
    - One batch may supplement or revise:
      - world data
      - the selected target character
      - other already-known characters
    - Source evidence discovered later may therefore propagate across the
      whole work package.

48. Targeted character extraction does not mean isolated character updates.
    - Even during a batch focused on one selected character, the system should
      still emit world corrections and other-character corrections when the
      source segment justifies them.

49. Users should bind to canonical character packages by reference instead of
    duplicating those base packages.
    - When a user selects a target character, the runtime should load the
      canonical base from `works/{work_id}/characters/{character_id}/`.
    - User-specific relationship state, drift, and history should then be
      layered from `users/{user_id}/works/{work_id}/characters/{character_id}/`.
