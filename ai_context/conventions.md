<!--
MAINTENANCE — read before editing this file.
This file is an index for fast project follow-up, not a detailed manual.
1. Write "what / where to find"; link to authoritative sources (code paths, docs/*.md, schemas, logs).
2. Prefer deletion over addition; check if a new item merges into an existing one before adding.
3. Describe the current design only — no "legacy / deprecated / formerly / renamed from".
4. No real book / character / plot names — use placeholders (`<work_id>`, `Character A`, `S001`).
Shorter is better than longer; push detail into the linked source rather than growing this file.
-->

# Operational Conventions

Rules easy to forget during long sessions. Dilution self-check triggers
live in `CLAUDE.md` / `AGENTS.md`.

## Logging

`logs/change_logs/` uses a three-timepoint contract (PRE / POST / REVIEW) — one
log file spans one `/go` → `/post-check` lifecycle. Filename:
`YYYY-MM-DD_HHMMSS_slug.md` (HHMMSS mandatory —
`TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'`).

- **PRE** (`/go` Step 1) — context / decision / planned action list / verification criteria
- **POST** (`/go` Step 7) — landed changes / diff vs plan / verification results / DONE|BLOCKED
- **REVIEW** (`/post-check` Step 5) — two-track review summary + REVIEWED-PASS|PARTIAL|FAIL

Rules:

- No PRE log → `/go` must not modify files.
- `/post-check` is the only skill allowed to write back to logs.
- Pre-contract single-timepoint logs stay as-is.

Full text → `.claude/commands/go.md`, `.claude/commands/post-check.md`.

## Cross-File Alignment

When a concept changes, update every file in its row:

| Changed | Also update |
|---------|-------------|
| `schemas/**/*.schema.json` | `docs/architecture/schema_reference.md`, `schemas/README.md`, prompt templates, `extraction/validation/gates/phase2_baseline.py` |
| `docs/requirements.md` | `ai_context/requirements.md`, `ai_context/decisions.md` |
| Loading strategy | `simulation/retrieval/load_strategy.md`, `simulation/flows/startup_load.md`, `simulation/retrieval/index_and_rag.md`, `docs/architecture/data_model.md`, `ai_context/architecture.md` |
| Extraction workflow | `docs/architecture/extraction_workflow.md`, `extraction/persona_extraction/prompts/`, `extraction/persona_extraction/`, `ai_context/architecture.md` |
| Runtime prompts | `simulation/prompt_templates/`, `simulation/` |
| Any durable decision | `ai_context/decisions.md` |
| `/go` or `/post-check` run | `logs/change_logs/` PRE / POST / REVIEW segments all present |
| Project-specific anchors used by skills (background processes, protected branch prefix, main-branch policy, do-not-commit paths, source / data-contract / example-artifact directories, core-component keywords, sensitive-content rules, timezone) | `ai_context/skills_config.md` corresponding section |
| `structure_mode` (source / works manifest dispatch signal) | `schemas/work/work_manifest.schema.json` + `schemas/work/works_manifest.schema.json` (both declare the enum field; source-side authoritative, canon-side copied by `manifests.write_works_manifest`), `schemas/work/chapter_index.schema.json` (items `oneOf` profile must match mode), `schemas/analysis/stage_plan.schema.json` (`stages.maxItems`/`stage_title.maxLength` loosened so light_novel 1:1 derivation passes; `chapter_count.minimum=8` / `maximum=15` directly hard-gates monolithic LLM output via decision #27i schema-gate-as-retry-trigger — light_novel derivation bypasses schema validate entirely, `chapter_count=1` derived products being schema-invalid is a known trade-off documented in decision #27m; `chapters.pattern` stays `^C[0-9]{4}-C[0-9]{4}$` — light_novel uses degenerate single-chapter range so phase 2/3/4 consumers parse identically), `extraction/ingestion/validator.py` (cross-file assertion), `extraction/persona_extraction/cli.py` (ingestion validator call site — `validate_source_package` runs after lock + preflight, before any phase begins), `extraction/persona_extraction/lifecycle/manifests.py::write_works_manifest` (copy-forward + assert) + `read_structure_mode` (Phase 0/1 dispatch read; source-manifest authoritative, raises on missing field or source/works mismatch — no implicit default-fill), `extraction/persona_extraction/orchestrator.py` (Phase 0 chunking + Phase 1 `_build_light_novel_stage_plan` direct-write — light_novel 模式 stage_plan lane 不进 LLM fan-out, see decision #52 — + STAGE_MIN/MAX bypass + stage_title soft-truncate to schema cap), `extraction/persona_extraction/lifecycle/progress.py::_expected_chapter_count` (must parse `chapters` format produced by orchestrator — currently `C####-C####` for both modes), `prompts/ingestion/原始资料规范化.md` (task step 2 LLM judgment with confidence gate ≥ 0.8 directly fills / < 0.8 stops for human-confirm; manifest fill instructions + title derivation), `docs/requirements.md` (§8.4 manifest field + §9.2 phase 0/1 flow), `docs/architecture/{schema_reference,extraction_workflow}.md`, `ai_context/{architecture,decisions}.md` |
| `schemas/analysis/chapter_summary_chunk.schema.json` (chunk schema fields/bounds) | `extraction/persona_extraction/prompts/summarization.md` (Phase 0 LLM authoring contract — must teach the LLM every field, including the chunk-level secondary fields' semantics + the `observed_impact` non-empty fallback rule), `extraction/persona_extraction/prompts/analysis_foundation.md` + `analysis_stage_plan.md` + `analysis_candidate_characters.md` (Phase 1 lane input contracts — each lane reads only its own projected subset of chunk fields; decision #52 + #54), `extraction/persona_extraction/prompt_builder.py` (`_project_chunk_for_foundation` / `_project_chunk_for_stage_plan` / `_project_chunk_for_candidates` projectors must stay aligned with the chunk schema field set), `docs/architecture/{schema_reference,extraction_workflow}.md`, `ai_context/{architecture,decisions}.md`. **Phase 2 不再消费 chunk-level 字段产 foundation**（decision #54 把 foundation 前移到 phase 1 foundation lane 直接产；phase 2 仅补 `foundation.major_factions.key_figures`，输入是 phase 1 落盘的 foundation + candidate_characters，非 chunk-level 字段）。 |
| `schemas/world/foundation.schema.json` (phase 1 foundation lane 落盘契约 + phase 2 `key_figures` 补齐契约，decision #54) | `extraction/persona_extraction/prompts/analysis_foundation.md` (phase 1 foundation lane LLM authoring contract — produces all fields except `major_factions[].key_figures`), `extraction/persona_extraction/prompts/baseline_production.md` (phase 2 `key_figures` 补齐 LLM call contract), `extraction/persona_extraction/prompt_builder.py` (`build_foundation_prompt` 产 phase 1 foundation lane prompt；`build_baseline_prompt` 单次 LLM call 含 phase 2 `key_figures` 替换 + identity + target_baseline + fixed_relationships + manifest 五件合一，决策 #54 修订段), `extraction/persona_extraction/orchestrator.py` (`run_analysis` foundation lane 输出路径 `world/foundation/foundation.json` + `run_baseline_production` 新增 key_figures 补齐 LLM call), `extraction/validation/gates/phase2_baseline.py` (`validate_baseline` 引用 schema 路径), `schemas/README.md` + `extraction/README.md`, `docs/architecture/{schema_reference,extraction_workflow}.md`, `ai_context/{architecture,decisions}.md` |
| `schemas/character/stage_snapshot.schema.json` 顶层属性增删 / 重命名（含 `stage_delta` / `failure_modes` / `behavior_state` 子键） | sub-lane 字段归属表 `extraction/persona_extraction/phases/snapshot_merge.py::FIELD_ALLOCATION` + `SHARED_KEY_SUBKEYS`（同源给 prompt + merge 用，新增 / 改名属性必须挂到对应 sub-lane 之一 `char_expression` / `char_decision` / `char_internal` / `char_social`，否则 merge hard gate 报"字段集合不全覆盖"；shared 顶层键如 `failure_modes` / `stage_delta` / `behavior_state` 拆 subkey 时必须更新 `SHARED_KEY_SUBKEYS`）+ `extraction/persona_extraction/prompts/character_snapshot_extraction.md`（`{lane_scope}` 注入的"本次仅写字段"白名单段）+ `docs/architecture/extraction_workflow.md` §6.2 sub-lane 字段表 + `ai_context/decisions.md` #55 + `docs/requirements.md` §9.3。决策 #55。 |
| `extraction/` 包内文件迁移（在 `persona_extraction/{core,lifecycle,phases,prompts,tests}/` / `validation/{gates,shared}/` / `repair/{checkers,fixers,tests}/` 之间挪文件，或子包改名） | 所有 `from .xxx` / `from ..xxx` 相对 import 同步加深 / 减层；所有 `from extraction.X.Y` 绝对 import 同步；`extraction/config.toml` 注释路径 + section 名（如 `[repair]`）+ `extraction.persona_extraction.core.config.load_config()` 入口提示；`extraction/pyproject.toml` description；`extraction/validation/README.md`（gates/shared 成员声明）；`ai_context/skills_config.md`（`## Source directories` + 其他段可能引用代码路径）；`.claude/hooks/session_branch_check.sh` 第 24 行 `pgrep -f 'extraction\.persona_extraction'` 模式；`.gitignore` 内 `extraction/*` 引用项（如 `extraction/config.local.toml`）；`docs/{requirements,architecture/extraction_workflow,architecture/schema_reference,architecture/data_model}.md` + `ai_context/{architecture,conventions,current_status,decisions,handoff,requirements}.md` + `extraction/README.md` 内所有路径引用；`schemas/README.md` + `schemas/**/*.schema.json` 描述里若 `$comment` 引用代码路径同步；`prompts/{README,ingestion/*,review/*}.md` 内若引用代码路径同步；`works/README.md` 顶层文档若引用 extraction 包路径同步。决策 #57。 |

After any change, grep for the old phrasing to catch stale references.

### Identifier rename — multi-form scan checklist

When renaming an identifier (e.g. `chapter0001` → `C0001`,
`stage0001` → `S001`), a single literal grep is **not enough** —
identifiers tend to leak into multiple syntactic forms across the
repo. Before declaring "no residue", grep all four forms below
across `schemas/` / `prompts/` / `extraction/` / `docs/` /
`ai_context/` / `simulation/` (exclude `sources/` / `users/` /
`works/` / `logs/change_logs/` / `docs/todo_list_archived.md` since
those legitimately carry historical snapshots):

1. **Old literal prefix** — `chapter[0-9]{4}` / `stage[0-9]{4}`
2. **Bare numeric pattern in JSON Schema** — `"\^\\d{4}\$"` /
   `"\^\\d{4}-\\d{4}\$"` (zero-padded numerics often hide there)
3. **Python f-string format spec** — **must grep with the generic
   regex `\{[a-z_]+:04d\}`** (covers any variable name like `ch`,
   `chapter_num`, `start`, `end`). **Never** use a specific variable
   name (e.g. `\{ch:04d\}`) as the only grep form — sibling code
   using a different name (e.g. `\{chapter_num:04d\}` in another
   module) will silently slip through. Apply to path concatenations,
   dict-key construction, log/print f-strings, and any
   `f"...{var:04d}..."` site
4. **File-name literals in docs / examples** — `0001\.txt` /
   `"0001-0010"` (renames usually drift in prose examples)

Codify the four forms into the PRE log "Validation criteria"
section when planning an identifier rename, so /post-check can
verify each independently.

## Naming and Identifiers

- Chinese works → Chinese `work_id`, `character_id`, path segments.
- `stage_id` = `S###` (3-digit zero-pad), aligned with the
  `M-S###-##` / `E-S###-##` / `SC-S###-##` / `SN-S###-##` ID family.
- `stage_title` = human-readable short name (work language; length cap in schema);
  sibling of `stage_id` in `stage_plan.json` and every
  `stage_catalog.json` entry; label shown at bootstrap stage selection.
- `chapter_id` = `C####` (4-digit zero-pad), enforced by
  `schemas/work/chapter_index.schema.json` `pattern: "^C[0-9]{4}$"`.
  `volume_id` (optional, multi-volume sources only) = `V###`
  (3-digit zero-pad). Width split rationale: chapter count per work can
  reach the thousands (≤ 9999 covers it); volume count stays small
  (≤ 999), so `V###` keeps the ID compact without ambiguity.
- `ai_context/` stays English. JSON field names may be English;
  content text follows work language.

## Generic Placeholders

Canonical docs (`schemas/`, `docs/requirements.md`, `docs/architecture/`,
`ai_context/`, `prompts/`, `extraction/persona_extraction/prompts/`) stay
work-agnostic:

- No real book / character / place / plot names.
- Examples use structural placeholders (`<character_id>`, `S001`).
- Schema `description` examples stay structural, not narrative (or omitted).
- No history narration ("legacy", "deprecated", "formerly", "renamed from").

Exempt (history is the point): `logs/change_logs/`, `logs/review_reports/`,
`docs/todo_list_archived.md`, `ai_context/decisions.md`, `works/*/` sample
outputs, git commit messages.

## Data Separation — Hard Schema Gates

- User data under `users/`; never write canon from user context.
- `identity.json` + `target_baseline.json` are the character-level constant baselines (Phase 2 produced, immutable from Phase 3 onward); voice / behavior / boundary / failure_modes live inline in `stage_snapshot` and evolve per stage. Phase 3 stage_snapshot three structures (`voice_state.target_voice_map` / `behavior_state.target_behavior_map` / top-level `relationships`) MUST have keys **set-equal** to `target_baseline.targets[].target_character_id` (bidirectional cross-file hard fail; tri-state via content emptiness — appeared = filled, seen-before = inherited, never-appeared = empty entry; fixed_relationship exception may pre-fill the relationships entry's relationship fields when bound by `world/foundation/fixed_relationships.json`). Validation runs at the phase 3 single-stage validate layer (peer of schema validate), violations route through the file-level repair lifecycle (L1/L2/L3); fix the baseline by hand and re-run the affected stages when phase 2 misses a target.
- Stage snapshots are **self-contained** — runtime loads identity + current stage_snapshot; no baseline merge.
- **Bounds only in schema.** All `maxLength` / `minLength` / `maxItems` / `required` live in `schemas/**.schema.json`; no duplicates anywhere else. Exact values → schema file. Index → `docs/architecture/schema_reference.md`. Cross-schema sharing of a single bound is done via `$ref` to a shared fragment located near the schemas it serves — placed in the directory of the domain that uses it (e.g. target-array cap is shared by `target_baseline.targets` + stage_snapshot's three target structures, both in `schemas/character/`, so the fragment lives there as `schemas/character/targets_cap.schema.json`). Still single-source, no duplication.
- **Bounds are caps, not targets.** Every extraction prompt template must explicitly tell the LLM that `maxLength` / `maxItems` are **hard ceilings, not quotas** — write what's actually in the source, do not pad / inflate / invent items to fill the cap. Without this, models default to writing exactly N items per array because "the schema says ≤N".
- **maxItems-aware truncation.** When a field exceeds its `maxItems` cap, the LLM ranks + truncates during extraction (not afterwards via schema fail). Priority anchors: current-stage relevance → identity-anchor relation → coverage breadth → cross-stage stability (for full-state evolving fields like `failure_modes`). Sub-classes count maxItems independently. → `extraction/persona_extraction/prompts/character_snapshot_extraction.md` §maxItems 触顶时的裁剪规则.
- **No chapter anchors on snapshots.** No schema (world / character / `stage_snapshot` / `memory_timeline`) carries `evidence_refs` / `source_type` / `scene_refs`; no per-item `evidence_ref` in `dialogue_examples` / `action_examples`. Anchoring uses `timeline_anchor` (+ `location_anchor` for world) and `memory_timeline`.
- **`stage_catalog`** — world catalog at `schemas/world/world_stage_catalog.schema.json`; character catalog at `schemas/character/stage_catalog.schema.json`. Both bootstrap-only, not runtime-loaded; sort by `stage_id` lex (no `order` field). `snapshot_path` differs: character → `canon/stage_snapshots/{stage_id}.json`; world → `world/stage_snapshots/{stage_id}.json`.

## Git

Three-branch model (main is the only branch ever pushed to remote):

| Branch | Role | Pushes to remote? |
|---|---|---|
| `main` | Framework only — code / schema / prompt / docs / `ai_context/` / skills. Never carries real work IDs, source novels, or extraction artefacts. | ✅ |
| `extraction/{work_id}` | Per-work in-progress extraction. Each passing stage committed. | ❌ local only |
| `library` | Archive of completed works. Each finished `extraction/{work_id}` squash-merges here. | ❌ local only |

Flow rules:

- Default branch = `main`. Stay on `main` unless actively running extraction.
- Code / schema / prompt / docs / `ai_context/` / skill commits go to `main` first; extraction and library branches sync via `git merge main`.
- `extraction/{work_id}` carries stage outputs only. **Squash-merge to `library` on completion** (never to main — main must stay artefact-free).
- **After a successful squash-merge the orchestrator interactively offers (`[y/N]`, default N) to delete the source `extraction/{work_id}` branch (`git branch -D`) and run `git gc --prune=now`** so accumulated regen commits become unreachable and are reclaimed. Branch deletion is destructive — the prompt always runs even when `[git].auto_squash_merge=true`. Once the user opts in, the `library` squash is the only retained record; `extraction/{work_id}` is a disposable scratchpad.
- `library` periodically `git merge main` to absorb framework updates; never flows back to main.
- Enforcement: orchestrator `try/finally: checkout_main(...)` + `.claude/hooks/session_branch_check.sh`. Detail → `architecture.md` §Git Branch Model.
- Never commit: novels, databases, embeddings, caches, real user packages, real `work_id`-named manifests on `main`.
- Don't amend others' commits.
- `/go` git contract: when not already on main-clean, `/go` automatically opens `../<repo>-main` as a `git worktree`, does all edits + commit there, then `git worktree remove --force` after commit. Main checkout is never moved off its branch during Steps 1–8, so in-flight extraction / dirty work continues undisturbed. Step 9 fast-forwards main into each non-main branch and asks **exactly once at the very end** whether to `git checkout main` — no inline prompts between steps or between branches.

## Post-Change Checklist

1. All aligned files updated? (table above)
2. PRE log at `/go` Step 1, POST at Step 7 (same file)?
3. `ai_context/` updated only if durable?
4. Grepped for stale old references?
5. Python import smoke test if code / schema changed?
