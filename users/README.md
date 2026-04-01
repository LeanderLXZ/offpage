# Users

This top-level directory is the home for all user-specific state.

Recommended layout:

```text
users/
  {user_id}/
      profile.json
      personas/
        {persona_id}.json
      works/
        {work_id}/
          manifest.json
          characters/
            {character_id}/
              role_binding.json
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

Important boundary:

- keep canonical source-grounded world and character data under
  `works/{work_id}/`
- keep every user-specific change, memory, event, and conversation history
  under `users/{user_id}/`
- when the user selects a character, load the base package from
  `works/{work_id}/characters/{character_id}/` and then layer user state on top
