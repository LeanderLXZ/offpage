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
