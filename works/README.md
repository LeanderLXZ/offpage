# Works

This directory is the preferred home for source-grounded, work-scoped canon
packages.

Recommended layout:

```text
works/{work_id}/
  manifest.json
  world/
  characters/
  analysis/
  indexes/
```

Design rule:

- `sources/works/{work_id}/` stores source and normalized text
- `works/{work_id}/` stores the canonical base package for that work
- user-specific state should live under `users/{user_id}/`

Recommended meaning of each subtree:

- `world/`
  - world foundation, history, major events, state, locations, factions, maps
  - plus work-level cast, event-knowledge, and social views
- `characters/`
  - detailed character packages
- `analysis/`
  - work-relevant analysis artifacts and evidence grounded in the source text
- `indexes/`
  - cross-cutting indexes such as character, location, event, and relation
    lookup views

Important boundary:

- `world/` may include brief cast summaries and relationship graph / timeline
  views for indexing convenience
- `world/` may also include concise character knowledge summaries about major
  events
- detailed character psyche, memory, voice, behavior, and stage data should
  still live under `characters/`
- user dialogue must not rewrite canonical world facts or major event records
- user-specific character drift, relationship changes, and conversation history
  belong under `users/{user_id}/`
