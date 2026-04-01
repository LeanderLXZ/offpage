# World Data Living Asset Rule

## Summary

Added an explicit project rule that world information should be treated like
character information in one key respect:

- it is not a one-shot static summary
- it should be incrementally expanded, corrected, and revised
- conflicts and uncertainty should be preserved explicitly

## Why This Was Needed

The architecture already described world packages, world-state snapshots, and
location state.

But it was still possible to read that model as "generate a world summary once"
instead of "maintain a living canon asset that changes as source understanding
improves."

For long-form novels, later chapters can change or clarify:

- historical interpretation
- faction relationships
- city status
- location identity
- map understanding
- cosmology or power-system details

## New Direction

World materials should now be maintained incrementally, similar in spirit to
character materials.

That means:

- later text can expand earlier world records
- later text can correct earlier world records
- uncertainty should remain labeled
- contradictions should be preserved instead of silently overwritten

## Implementation Impact

Future world-package schemas and extraction packets should support:

- revision notes
- contradiction tracking
- unresolved world questions
- traceable world-state updates
