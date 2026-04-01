# Character Packages

Each character should have an isolated package under `characters/{character_id}/`.

Recommended layout:

```text
characters/
  {character_id}/
    manifest.json
    canon/
      identity.json
      bible.md
      memory_timeline.jsonl
      relationships.json
      voice_rules.json
      behavior_rules.json
      boundaries.json
      failure_modes.json
      stage_catalog.json
      stage_snapshots/
        {stage_id}.json
      evidence/
```

Key rule:

- character packages are canon-facing and user-independent

This means user-caused memory, relationship drift, custom nicknames, and
long-term personalization do not belong here. Those belong under `users/`.
