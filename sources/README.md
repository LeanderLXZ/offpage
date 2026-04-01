# Sources

This directory stores novel inputs and normalized text artifacts.

Planned layout:

```text
sources/
  raw/
  works/
    {work_id}/
      manifest.json
      raw/
      normalized/
      chapters/
      scenes/
      chunks/
      metadata/
      rag/
```

Guidelines:

- `raw/` at the top level is a local drop zone for newly added novel files
  before they are organized into work-specific folders.
- `raw/` preserves original input files and should not be rewritten.
- `normalized/`, `chapters/`, `scenes/`, and `chunks/` are derived views.
- `rag/` is reserved for indexes, embeddings, and retrieval metadata.
