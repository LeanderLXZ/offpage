# Index And RAG Plan

## Recommendation

Start with structured retrieval, not a heavy vector stack.

## Phase 1: Structured Retrieval

Use committed work-level indexes such as:

- `indexes/load_profiles.json`
- `indexes/entity_aliases.json`
- `indexes/event_index.json`
- `indexes/location_index.json`
- `indexes/faction_index.json`
- `indexes/stage_entity_map.json`
- `indexes/chapter_summary_index.jsonl`
- `indexes/scene_index.jsonl`

This phase needs no extra package by default.

## Phase 2: Lexical Retrieval

If structured retrieval becomes too coarse, add local lexical search.

Recommended first option:

- `sqlite FTS5`

Good lexical targets:

- chapter summaries
- scene summaries
- event summaries
- character memory summaries

## Phase 3: Optional Semantic Retrieval

Only add embeddings when:

- works become too large for structured + lexical search
- paraphrastic user questions regularly miss lexical recall
- cross-file recall quality becomes the bottleneck

Even then, prefer:

1. metadata filter first
2. lexical shortlist second
3. embedding rerank third

## Artifact Placement

Commit-friendly indexes:

- `works/{work_id}/indexes/`

Local large retrieval artifacts:

- `sources/works/{work_id}/rag/chunks.jsonl`
- `sources/works/{work_id}/rag/fts.sqlite`
- optional local embedding cache

Large caches and local databases should usually stay uncommitted.

## Prompt Contract

When a runtime or extraction agent needs retrieval, the recommended order is:

1. read `works/{work_id}/analysis/incremental/extraction_status.md` if it
   exists
2. read `works/{work_id}/indexes/load_profiles.json` if it exists
3. load stage summary and current-state packet first
4. expand into event, location, faction, history, or character memory only
   when required
5. read raw chapter text only for verification or high-fidelity mode

## Tooling Advice

You do not need to install a dedicated vector database for the first usable
version.

Recommended order:

1. JSON / JSONL canon files plus work-level indexes
2. local `sqlite FTS5`
3. optional embedding tooling later
