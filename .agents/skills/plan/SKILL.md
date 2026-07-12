---
name: plan
description: Lock the current message into discuss-only mode — no file writes / no mutating Bash, read-only queries only; scope = one message. Triggers: /plan / discuss only / discuss without touching files / analyze the plan / talk it through first.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (logs / docs / commit messages / code comments / files written) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / status lines / strategy declarations / findings rendered in chat) uses `conversation_language`. Code identifiers, file paths, field names, frontmatter keys, and structural prefixes (`Step N:`, `LOG:`, etc.) stay English regardless.

# /plan — Lock into discuss-only mode (current message only)

**Active only when the user's currently sent message contains `/plan`**;
enforces discuss-only mode: **no file writes, no mutating actions**; focus on
in-conversation analysis, listing options, asking, weighing trade-offs.
**Scope = one message** — if the next message does not contain `/plan`,
default behavior resumes immediately, no lock carries over. After discussion
converges the user separately invokes `/go` / `/commit` / `/todo-add` /
`/update-docs` or another standalone skill to land — this skill does not
trigger them.

## Rules

- **Hard scope constraint**: only when the user's **current message
  literally** contains `/plan` does this mode engage; the mode does not span
  messages. Next user message without `/plan` → default behavior resumes,
  all writing tools unlocked. `/plan` appearing in session history does not
  count as activation
- **Zero writes**: Write / Edit / NotebookEdit disabled
- **Bash read-only**: cat / grep / ls / find / git log / git diff /
  git status / wc / head / tail and similar query commands allowed;
  **forbidden** git add / commit / push / pull / merge / checkout / reset /
  rm / mv / mkdir / touch / any file writes / any mutating commands;
  network write requests (POST / PUT / DELETE) also forbidden
- **No writing skills**: `/go` / `/commit` / `/todo-add` / `/update-docs` /
  `/post-check` / `/full-review` and the like may touch files, do not
  trigger them
- **No scratch files**: plan.md / draft.md / notes.md / .scratch — none

## Discussion posture

- **Scope convergence**: user asks scope N → answer scope N. If N+1 can be addressed in one extra line, mention it; do not proactively expand to N+2 / N+3. The most common over-engineering in discussion is piling on "while we're at it"
- **No pre-implementation**: do not write full pseudocode or whole function drafts. When illustration is needed, at most 1-2 line signatures or a single data structure skeleton
- **Simple first + active push back**: when you spot "the simplest version of the user's proposal is X / Y; adding extras makes it more complex", proactively say "recommend not doing X" + a one-line reason; do not default to accepting every framing the user offers
- **Explicitly mark uncertainty**: which items are read facts (line numbers / quotes), which are guesses, which require grep / Read to decide — split them so the user can challenge each
- **Stop when unclear**: spot ambiguous key premise / missing info → ask one line instead of guessing hard; round-trips correcting a guess cost more than one clarification
