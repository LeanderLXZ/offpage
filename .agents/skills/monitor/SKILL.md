---
name: monitor
description: Periodic progress report (default 5min) for background processes declared in skills_config.md; diagnose only — no kill / restart / config change. Triggers: monitor please / monitor 5min / monitor X process.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (logs / docs / commit messages / code comments / files written) uses `content_language`; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / progress-tool entry `content` / status lines / strategy declarations / findings rendered in chat) uses `conversation_language`. Code identifiers, file paths, field names, frontmatter keys, and structural prefixes (`Step N:`, `LOG:`, etc.) stay English regardless.

# /monitor — Background-process progress monitor

Monitor running background tasks at a fixed interval, periodically reporting progress, errors, efficiency, and estimated completion time to the user. **Read-only**: when an issue surfaces, first diagnose the cause and give the user information plus recommendations; do not rush to act.

`$ARGUMENTS`: refresh interval + optional scenario description. Examples:
- `/monitor` → default 5 minutes
- `/monitor 3min` → 3 minutes
- `/monitor 5min about to run a batch starting from phase X, target N items, default background parallelism` → 5 minutes + scenario context
- `/monitor 5min pid=12345 logs=path/to/log` → ad-hoc monitoring target (used when skills_config.md `## Background processes` is empty)

Parse rule: the first token shaped like `{N}min` / `{N}s` / `{N}m` / plain number (interpreted as minutes) → interval; the rest is scenario description (may include ad-hoc PID / log-path overrides). Default 5 minutes.

## 0. Load skills config

`Read` `ai_context/skills_config.md`.

- File missing / a section heading missing → fail loudly: print the missing item + suggest filling in from the plugin template, stop
- `## Background processes` content is `(none)` or empty: check whether `$ARGUMENTS` provides an ad-hoc PID / process pattern / log path; if none, print "this project's skills_config.md `## Background processes` is not declared, and $ARGUMENTS did not specify a monitoring target either; monitor has nothing to watch, stopping" and exit
- A section lists a concrete path but the path does not exist → fail loudly: report the drift to a missing path and stop for the user to fix

When subsequent steps reference "skills_config.md `## XX`" they refer back to this config. This skill uses:
`## Background processes` (Step 2 process inventory), `## Timezone` (Step 3 per-round Timestamp).

## 1. Scenario registration

- Print: "monitoring interval = {N}min; scenario = {scenario description or 'unspecified'}"
- If the scenario description mentions a specific phase / target / parallelism → record it, and use it later to judge whether observation deviates from expectation
- Ask whether there is any additional signal to watch (e.g. a specific log path, specific PID, specific work directory) — record what the user provides; otherwise scan the defaults

**Task-shape inference** (drives Progress / ETA semantics; no user field):

Infer from scenario description + `## Background processes` artifacts whether this monitoring target is:

- **finite** — bounded work with a definable "done" state (chunk extraction, backtest run, training epoch loop, batch pipeline). Progress = `N / M (xx%)`; ETA = projected wall-clock to completion; "time remaining" framing
- **always-on** — open-ended daemon with no terminal "done" (live trading, news feed monitor, server, long-running orchestrator without target N). Progress = throughput over a windowed period (events/min, trades/hr); ETA = "next scheduled checkpoint / next milestone / next round-trip"; "time elapsed" framing replaces "time remaining"

Default to `finite` when ambiguous; switch to `always-on` only when scenario explicitly indicates open-ended (`watch …`, `daemon`, `live`, `always-on`, no target N anywhere). Print one line: `task shape = finite | always-on` so the user can correct.

## 2. Identify monitored processes and artifacts

Inventory in the first round, then refresh each round:

- List PID + command line per skills_config.md `## Background processes` pgrep patterns (add any other scripts mentioned in the scenario / ad-hoc `$ARGUMENTS` overrides)
- Read `.pid` / `.json` progress files at the process-artifact paths from skills_config.md `## Background processes`
- Tail the latest log file at the process-log paths from skills_config.md `## Background processes`
- User-specified custom paths take precedence

## 3. Per-round report contents — 7-aspect framework

Each round emits one report block organised by **aspects** (categories of information), not by fixed line-item fields. The aspect taxonomy is fixed; the layout (table vs list, grouping, column choice) is designed on the fly from the actual process structure in Round 1 and reused thereafter. **No round-0 layout confirmation** — print directly; if the user wants a different layout, they will say so.

### Core aspects (every round, when applicable)

1. **Time** — timestamp (HH:MM:SS via skills_config.md `## Timezone` template; fall back to `date '+%H:%M:%S'` system tz if section missing); total wall-clock runtime; **ETA per lane + overall** (for `finite`; for `always-on` substitute "time elapsed" + "next checkpoint / next milestone"). Mark `sample insufficient` explicitly when too few rounds to extrapolate.

2. **State** — each monitored unit's state-machine value: `pending / running / done / failed / paused / retrying / waiting-on-resource / awaiting-user`. **Render the topology (phase → lane → sub-lane → unit) implicitly through grouping / indentation / table row hierarchy** — do not list "topology" as a separate aspect. State is distinct from Progress: a `paused` unit is not stuck, a `failed` unit is not done.

3. **Progress** — per-unit + overall completion. For `finite`: `N / M (xx%)` or stage label; for `always-on`: throughput over a windowed period (events/min, trades/hr). Inline delta vs last round (e.g. `1240 (+85)`, `42% (+3pt)`). Overall ≠ simple sum when lanes have different weights — call out the weighting if non-obvious.

4. **Errors & retries** — error count + **retry budget remaining** (burndown, e.g. `2/5 left`) + last error message with file path + line number + repair-lifecycle state if applicable (L1 / L2 / L3, circuit-breaker open / closed / half-open, tolerance-gate triggered). Budget remaining matters more than raw error count — `1/5 left` means one fault from death.

5. **External constraints** — API rate-limit pause state (`paused until 14:32 by <provider>`), quota remaining, cumulative token / dollar burn. Independent from Errors: "paused for rate-limit" looks like "stuck" if only Progress is watched, and is *not* an error. Cheap to report when nominal (`✓ no limits in effect`), costly to miss.

### Conditional aspect (include in core only when applicable)

6. **Artifacts** — files / records produced this round + cumulative count + size + path + delta vs last round. Distinguish `written` vs `committed` (vs `delivered` for jobs with side-channel push). Include in core when scenario or `## Background processes` indicates disk products / committed artifacts / external notifications; otherwise demote to the Anomaly bucket (fire only on write-vs-commit gap or delivery failure).

### Mandatory verdict

7. **Diagnosis** — **always present, never omit**. One sentence: `nominal` / `stuck (cause)` / `waiting on X (until Y)` / `degrading (rate ↓40% vs last round)` / `budget critical (1 retry left)` / `paused for rate-limit` — plus a one-line recommendation if action is warranted (labelled "recommendation", not "executed"; see §4). Raw data without a verdict is not monitoring.

### Anomaly bucket (fire only when triggered)

A single line slot (e.g. `Anomalies: ✓ none` or `Anomalies: ⚠ rate-limit paused / GPU idle`) that surfaces categories which would be pure noise as fixed core rows:

- **Resource saturation** — OOM risk, CPU pegged, GPU idle when scenario said it should be used, disk near full, FD exhaustion
- **Coordination** — stale PID lock, lock contention, worktree lock conflict
- **Throughput regression** — rate dropped > 30% round-over-round (the trend-alert piece of throughput; raw throughput numbers belong in Progress delta, not here)
- **Special-phase entry** — recovery sweep, circuit-breaker open, tolerance-gate triggered, mode flag flipped
- **Artifact write-vs-commit gap** — files landed on disk but not durably committed (limbo state)
- **Scenario-declared domain signals** — quality metrics the user named in `$ARGUMENTS` (Sharpe / max drawdown, validation pass rate, training loss / val accuracy, alert delivery rate); skill only watches these when the scenario explicitly names them — no `skills_config.md` field

The bucket expands into Diagnosis when it has content; when empty, collapse it onto the Diagnosis line (`Diagnosis: nominal, no anomalies`).

### Rendering discipline

- **Layout designed in Round 1, reused thereafter** — eye-track friendliness across rounds matters more than per-round optimisation
- **Stable aspect order across rounds** — never reshuffle Time / State / Progress / Errors / External / Artifacts / Diagnosis
- **Severity prefix** on every row / cell — `✓` nominal / `⚠` warning / `✗` failure — so the user spots red first
- **Inline delta** for any numeric value where it makes sense — `1240 (+85)`, `42% (+3pt)`, `runtime 4h12m (+5m)`
- **Topology shown by grouping** — table row hierarchy or indented list expresses lane → sublane → unit; never flatten when nesting exists
- **Anomaly-triggered aspects stay hidden** when nominal — do not print `Resources: ✓ all nominal` every round; only surface when something fires
- **Aspect is `applicable-only`** — if a category has no data (no external API → no External constraints row; no disk products → no Artifacts row), skip it; do not print empty placeholders

## 4. Handling problems on discovery

- **Do not edit files, do not kill processes, do not restart**
- Locate first: log line number, related work directory, affected schema / prompt / code files
- Provide **information + recommendations**: what the error is, possible causes, recommended next step (retry / tune / switch strategy / observe first), labelled "recommendation" not "executed"
- Severe errors (all processes dead / data corruption / infinite retries) → immediately break the regular reporting cadence, issue one high-priority alert separately, wait for user instruction
- Act only with explicit user approval; otherwise continue read-only monitoring

## 5. Loop cadence

- Run a report immediately on the first round
- Then one round every N minutes; stay quiet between rounds, do not flood the chat
- User interrupt (question / instruction) → respond immediately, resume the cadence afterward
- User says "stop" / "end monitoring" / `/stop` intent → halt and print a final summary (total runtime, final state, list of anomalies observed during this monitoring session)
- All processes finished → proactively print "all processes finished" + final summary, halt the loop

## Constraints

- **Read-only**: no kill / restart / config change / log deletion / artifact mutation
- Reports stay compact: report only new / changed / anomalous items, do not restate unchanged background
- Processes / directories outside the stated scenario → flag anomalies in passing, but do not displace the primary scenario
