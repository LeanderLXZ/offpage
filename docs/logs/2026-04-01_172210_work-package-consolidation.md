# 2026-04-01 17:22:10 - Work Package Consolidation

## Summary

The preferred package direction was consolidated around a single work-scoped
simulation root:

- `sources/works/{work_id}/`
  - source ingestion, normalization, chapter text, and source metadata
- `works/{work_id}/`
  - persistent simulation-needed data for that work

This change is intended to reduce scattering across top-level directories and
make work-level indexing, loading, and retrieval simpler.

## Key Decisions Reinforced

- New persistent simulation-facing data should prefer `works/{work_id}/`.
- Source and normalized text should remain under `sources/works/{work_id}/`.
- Inside `works/{work_id}/`, the preferred subtrees are:
  - `world/`
  - `characters/`
  - `users/`
  - `analysis/`
  - `runtime/`
  - `indexes/`
- Prefer explicit names like `indexes/` over vague buckets like `other/`.

## World Package Boundary

The world package is allowed to expose work-level views that help indexing and
runtime retrieval, including:

- which characters exist in the work
- brief role summaries
- relationship graph views
- relationship timeline views

However, detailed character canon should still remain in
`works/{work_id}/characters/{character_id}/`, especially:

- voice rules
- behavior rules
- memory timelines
- stage catalogs and stage snapshots
- deeper psychological or roleplay-specific character material

## Status

This direction is now reflected in the architecture docs and AI handoff docs,
but the repository has not yet fully migrated existing artifacts into the
preferred `works/{work_id}/` layout.
