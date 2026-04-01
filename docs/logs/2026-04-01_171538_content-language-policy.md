# Content Language Policy

## Summary

Added a project-level rule for generated content language:

- work-scoped generated content should default to the selected work language
- structural field names may remain English
- `ai_context/` remains English as the AI-facing handoff layer

## Why This Was Needed

The project had already standardized `ai_context/` in English for AI handoff,
but there was no equally explicit rule for the language of generated canonical
materials.

Without that rule, a Chinese source work could easily drift into English-only
character notes, world notes, or relationship notes, which would weaken
fidelity to the original text and reduce usability for the intended workflow.

## New Direction

For a work with `language: "zh"`:

- character-package content should default to Chinese
- world-package content should default to Chinese
- work-scoped user / relationship content should default to Chinese

This rule applies to content text, not to structural identifiers.

The following may still remain English:

- JSON keys
- schema field names
- repo path conventions

## Current Limitation

The current schemas still need a more explicit writable-instance rule for:

- how content language inherits from `work_manifest.language`
- whether package-level overrides are allowed
- how global user-profile language differs from work-scoped user content
