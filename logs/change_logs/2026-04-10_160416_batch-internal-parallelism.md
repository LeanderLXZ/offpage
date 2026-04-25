# Batch-Internal 1+N Parallelism

Date: 2026-04-10

## Summary

Removed the sequential dependency between world extraction and character
extraction within a batch. World and all N characters now run fully in
parallel (1+N LLM calls via ThreadPoolExecutor). Also fixed documentation
inconsistencies around baseline correction scope and memory_timeline input.

## 4 Changes

1. **Baseline correction scope** (docs fix): every batch can correct and
   supplement baseline files (voice_rules, behavior_rules, boundaries,
   failure_modes) — not just batch 1. Updated flow diagram, generation
   rules diagram, and descriptive text in requirements.md.

2. **memory_timeline as input** (docs fix): documented that character
   extraction reads prev_batch's memory_timeline (was already in code
   but missing from some docs). Updated generation rules and §9.3.

3. **Remove world snapshot dependency from character extraction** (code +
   docs): character extraction prompt no longer references
   {world_snapshot_path}. Both world and characters read the same source
   text independently. Cross-consistency verified at commit gate (review
   lanes still read world snapshot for cross-check after extraction).

4. **Batch-internal 1+N parallelism** (code + docs): orchestrator now
   dispatches world + N character extractions in a single ThreadPoolExecutor
   (was: world first → then N characters parallel). Batch steps reduced
   from 7 to 6.

## Files Modified

**Code**:
- `automation/persona_extraction/orchestrator.py` — merged steps 2-3 into
  single parallel step; renumbered steps 1-6; updated docstring
- `automation/persona_extraction/prompt_builder.py` — removed
  world_snapshot_path param from build_character_extraction_prompt and
  _build_character_read_list; updated docstrings
- `automation/persona_extraction/validator.py` — fixed misleading comments
  about baseline creation timing
- `automation/prompt_templates/character_extraction.md` — removed
  "世界快照参照" section

**Documentation**:
- `docs/requirements.md` — flow diagram (①② merged), §9.3 rewrite
  (1+N parallel, no world dependency, baseline every batch), generation
  rules diagram (unified batch template + memory_timeline input),
  §11.3 agent context model, §11.4b review lanes diagram, step numbering
- `docs/architecture/extraction_workflow.md` — §6 title/description,
  §6.1/6.2 headings, generation rules, flow diagram, design decisions
- `ai_context/architecture.md` — Phase 3 description
- `ai_context/current_status.md` — batch-internal parallelism, prompt
  templates description
- `automation/README.md` — title, flow steps, directory annotations
