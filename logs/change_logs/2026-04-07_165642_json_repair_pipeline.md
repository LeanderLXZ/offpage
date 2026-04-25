# 2026-04-07 — Three-level JSON repair pipeline for extraction

## What changed

Added `automation/persona_extraction/json_repair.py` — a three-level repair
pipeline for malformed JSON/JSONL produced by LLM extraction agents.

Integrated the repair logic into:

- `orchestrator.py` — Phase 0 chunk skip-check and post-write verification
- `validator.py` — `_load_json()` auto-repair and memory_timeline JSONL repair

## Files added/changed

- **Added**: `automation/persona_extraction/json_repair.py`
- **Changed**: `automation/persona_extraction/orchestrator.py`
- **Changed**: `automation/persona_extraction/validator.py`
- **Changed**: `automation/README.md` (documented repair strategy)

## Why

During the first full Phase 0 run (537 chapters / 22 chunks), 7 out of 22
chunk files contained valid content but had malformed JSON — mostly unescaped
ASCII double quotes used as Chinese book-title marks inside string values
(e.g. `"寻找至宝"渊泉诡心"以救人"`). The original pipeline treated these as
failures requiring a full re-run of the `claude -p` call (~5-7 min + tokens
per chunk).

The three-level strategy eliminates unnecessary re-runs:

| Level | Method | Cost | Handles |
|-------|--------|------|---------|
| L1 | Programmatic regex | 0 tokens | Unescaped inner quotes, trailing commas, truncation, trailing garbage |
| L2 | LLM repair (broken JSON only, no source) | Minimal tokens | Complex format issues L1 cannot fix |
| L3 | Full re-run | Full tokens | Content actually missing — caller's responsibility |

## Design details

### L1 programmatic fixes

1. **Inner quote escaping**: Regex-matches JSON key-value lines (`"key": "value",`),
   escapes bare `"` inside the value portion. Handles both object properties
   and array string elements.
2. **Trailing comma removal**: Strips `,` before `}` or `]`.
3. **Trailing garbage stripping**: Finds the last depth-0 close bracket and
   removes everything after it.
4. **Truncated JSON recovery**: Counts unmatched open brackets/braces and
   appends matching closers.

### L2 LLM repair

Sends only the broken JSON text to the LLM with instructions to fix format
issues and write the repaired file. Does not require re-reading source
material — the content is already in the broken output.

### Integration points

- **Phase 0 skip-check**: Before deciding to re-run a chunk, attempts L1→L2
  repair on the existing file. If repair succeeds, the chunk is skipped.
- **Phase 0 post-write**: After LLM writes a chunk, if `json.loads` fails,
  attempts repair before marking the chunk as failed.
- **Phase 3 `_load_json`**: All JSON loads in the validator auto-attempt L1
  repair on parse failure.
- **Phase 3 memory_timeline**: JSONL files get per-line L1 repair before
  validation.

### JSONL handling

`try_repair_jsonl_file()` processes each line independently with L1 fixes.
L2 is not attempted for JSONL because sending entire files may exceed
reasonable prompt size.
