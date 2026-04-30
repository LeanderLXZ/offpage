# Skills Config (project instance)

Loaded on demand by `.agents/skills/*` at runtime. **Not** loaded by
default at session start — only the specific skill that needs it reads it.

Each section below is filled with this project's actual values.
**Section headers (the `## …` lines) MUST exist** — a missing header
means the config is structurally incomplete; skills will fail loudly and
stop. If this project has no value for a section, write `(none)` or
leave the body empty — skills will skip the related step. If a section
lists concrete paths but those paths don't exist on disk, skills will
fail loudly and report the drift.

When porting to another project, edit only this file — skill bodies
under `.agents/skills/*` stay untouched.

## Background processes

Used by skills to detect "is there an in-flight long-running job on this
branch / worktree?", so they don't disturb it
(e.g. `/commit` Step 5 forward, `/go` Step 1 worktree lock,
`/monitor` process inventory).

- pgrep patterns:
  - `persona_extraction`
- Process artifacts:
  - `works/*/analysis/progress/*.pid`
  - `works/*/analysis/progress/*.json`
- Process logs:
  - `works/*/analysis/logs/`

## Protected branch prefixes

Used by skills to identify branches that must not be auto-forwarded /
merged into without care (e.g. `/commit` Step 5, `/go` Step 10 branch sync).

- Prefixes:
  - `extraction/`

## Main branch policy

Drives `/go` worktree-lock decision and Step 10 sync direction.

- Main branch: `main`
- Rule: changes to code / schema / prompt / docs / ai_context / skill
  land on `main` first; other branches sync forward via `git merge main`.

## Do-not-commit paths

Project-specific paths that must never be committed, on top of
`.gitignore` + `ai_context/conventions.md` (used by `/commit` Step 3,
`/go` Step 9).

- `sources/` (raw source material)
- `*.sqlite*`
- `embeddings/`
- `caches/`
- `works/` (extraction artifacts)
- `users/` (real user packages)

## Source directories

Used by `/full-review` "implementation track" and `/post-check` Track 2
implementation track for code-level scans.

- `automation/`
- `simulation/`

## Data contract directories

Project-specific directories holding data-shape contracts —
JSON Schema, Protobuf, OpenAPI, Pydantic models, SQL DDL, Avro,
GraphQL schemas, etc. Used by `/full-review` and `/post-check` "spec
track" plus `/go` Step 7 spec track. Many projects don't have a
dedicated directory (contracts inline in code) — leave as `(none)` and
the related scans degrade gracefully.

- `schemas/`

## Example artifact directories

Used by `/full-review` "artifact track" and `/post-check` Track 2
artifact-and-structure track. E.g. example outputs, user templates,
fixture data.

- `works/`
- `users/_template/`

## Core component keywords

Used by `/full-review` to locate key architectural components for
alignment audits ("does the orchestrator / validator / consistency
checker / post-processing actually enforce the gates the docs claim?").

- `orchestrator`
- `validator`
- `consistency checker`
- `post-processing`

## Sensitive content placeholder rules

Real-world content that must NOT appear in docs / prompts / ai_context;
must be replaced by structural placeholders (used by `/go` Step 3 / Step 7,
`/post-check` Track 2 residual scan).

- Real business entity names (e.g. book / character / customer /
  private-domain data / real user emails)

## Timezone

Drives timestamp generation across skills (`/go` Step 2 PRE log /
Step 8 POST log, `/full-review` archived report filename, `/monitor`
per-cycle Timestamp).

- Command template: `TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'`
