# Close And Merge

## Goal

Treat session ending as an explicit lifecycle step rather than an implicit
side effect.

## Close Flow

1. Detect close intent or exit keyword.
2. Close the active session.
3. Ask whether the current context should be merged into long-term state.
4. If the user declines:
   - keep `session` and `context` continuity only
5. If the user accepts:
   - extract accumulated character drift from
     `contexts/{context_id}/character_state.json` and append to
     `long_term_profile.json` as `character_drift_history` entries
   - extract personality and voice drift and append to
     `relationship_core` as `personalized_voice_shift` and
     `personalized_behavior_shift` updates
   - extract durable `mutual_agreements` and append to
     `relationship_core`
   - append event and memory entries to `long_term_profile.json`
   - update `relationship_core` relationship labels and levels
   - promote selected memories into `pinned_memories` when justified
   - record `merged_context_ids`
   - create a new conversation `archive_id`
   - archive the selected session transcripts into the account
     `conversation_library/`
   - update account archive indexes
   - write `archive_ref` back into the source context

## Merge Rules

1. Long-term updates should be append-first, not destructive overwrite by
   default.
2. The merge should stay inside
   `users/{user_id}/`.
3. Closing a session must not rewrite canonical work packages.
4. The source context should normally become `merged` or `merged_archived`
   rather than disappearing without provenance.
5. Default archive behavior should preserve a lightweight stub or reference to
   the moved conversation record.
