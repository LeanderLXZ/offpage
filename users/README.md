# User Packages

Each user lives under `users/{user_id}/`.

Recommended layout:

```text
users/
  {user_id}/
    profile.json
    personas/
      {persona_id}.json
    characters/
      {character_id}/
        relationship_core/
          manifest.json
          pinned_memories.jsonl
        contexts/
          {context_id}/
            manifest.json
            relationship_state.json
            shared_memory.jsonl
            sessions/
              {session_id}/
                manifest.json
                transcript.jsonl
                turn_summaries.jsonl
                memory_updates.jsonl
```

Key rule:

- user packages store branch-specific and relationship-specific evolution

This layer is allowed to change frequently.
