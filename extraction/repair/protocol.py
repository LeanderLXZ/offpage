"""Data classes shared across checkers, fixers, and coordinator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------

@dataclass
class FileEntry:
    """A file to be checked / repaired.

    For accumulated JSONL files where the repair stack operates on the
    current-stage slice only, ``is_jsonl_slice`` flips the write path:
    ``content`` is the patched slice, ``jsonl_full_content`` is the
    original full list, and ``jsonl_key_field`` is the per-entry id key
    used to merge the slice back into the full list at write time. This
    prevents a filtered subset from overwriting prior-stage entries.

    ``current_stage_keys`` (decision #58 / M2) carries the set of
    ``jsonl_key_field`` values that belong to the current stage at slice
    load time. Without it, ``_merge_jsonl_slice`` only knew how to
    *replace* by key — a repair that *removed* an entry from the slice
    would have its full-list counterpart silently re-survive the merge.
    With this set, the merge drops all full-list entries whose key is in
    ``current_stage_keys`` and then takes the patched slice as the
    authoritative current-stage content, so removals stick.
    """
    path: str
    schema: dict | None = None
    content: dict | list | None = None  # pre-loaded; None = read from path
    is_jsonl_slice: bool = False
    jsonl_full_content: list[dict] | None = None
    jsonl_key_field: str = ""
    current_stage_keys: frozenset[str] | None = None

    def load(self) -> dict | list | None:
        """Load content from disk if not already loaded."""
        if self.content is not None:
            return self.content
        import json
        p = Path(self.path)
        if not p.exists():
            return None
        try:
            text = p.read_text(encoding="utf-8")
            if p.suffix == ".jsonl":
                return [json.loads(line) for line in text.splitlines() if line.strip()]
            return json.loads(text)
        except (json.JSONDecodeError, OSError):
            return None


@dataclass
class SourceContext:
    """Context for T2 source_patch fixer — points to original chapters."""
    work_path: str
    stage_id: str
    chapter_summaries_dir: str
    chapters_dir: str


@dataclass
class RetryPolicy:
    """Per-tier retry limits (within a single repair run).

    Each tier is additionally hard-capped at 2 attempts by the
    coordinator (T-REPAIR-NO-REEXTRACT); the 2nd attempt only re-targets
    fields the immediate re-verify still flags.
    """
    t0_max: int = 1
    t1_max: int = 3
    t2_max: int = 3
    max_total_rounds: int = 5


@dataclass
class RepairConfig:
    """Configuration for a repair run."""
    max_rounds: int = 5
    block_on: Literal["error", "all"] = "error"
    run_semantic: bool = True
    l3_gate_enabled: bool = True
    triage_enabled: bool = True          # source-discrepancy triage on L3
    accept_cap_per_file: int = 5         # max SourceNotes per file per
                                         # run (shared by L3
                                         # source_inherent + L2
                                         # coverage_shortage; accumulates
                                         # on disk)
    # Hard timeout (seconds) for each kind of repair LLM call. Every call
    # site passes its own value explicitly — same ownership model as
    # ``effort`` (decision #65): the injected ``llm_call`` holds no default
    # budget, so a config change can never be silently shadowed. Budgets
    # differ by call kind: L3 reads the stage_snapshot in full, T1/T2
    # patch single fields, triage reads the stage's chapters once.
    # ``repair/`` never reads config.toml — the injector fills these in.
    semantic_timeout_s: int = 900        # L3 semantic review (Phase A full
                                         # check + per-round gate recheck)
    t1_timeout_s: int = 600              # T1 local_patch (no source text)
    t2_timeout_s: int = 600              # T2 source_patch (loads chapters)
    triage_timeout_s: int = 300          # source-discrepancy triage
    # Reasoning depth for the **re-read** calls (decision #65): L3 gate
    # recheck / T1 / T2 / triage / Phase C fallback all share it — they
    # re-read a file whose issues are already known, so they need less depth
    # than a cold pass. Phase A's full semantic check is the cold read: it
    # passes no effort at all and inherits the backend default
    # (``[llm].effort``). Same call-site-passes ownership as the timeouts.
    recheck_effort: str = "medium"
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)


# Allowed values for SourceNote.discrepancy_type. Keep in sync with the
# jsonschema at schemas/shared/source_note.schema.json.
DISCREPANCY_TYPES: tuple[str, ...] = (
    "author_contradiction",
    "typo",
    "name_mixup",
    "pronoun_confusion",
    "title_drift",
    "time_shift",
    "space_conflict",
    "duplicated_passage",
    "world_rule_conflict",
    "death_state_conflict",
    "logic_jump",
    "coverage_shortage",
    "other",
)


@dataclass
class SourceEvidence:
    """Evidence anchoring a source_inherent claim to an original chapter.

    All fields must be program-verified before a SourceNote is written:
    ``quote`` is a verbatim substring of the chapter text; both SHA-256
    hashes cover the corresponding text content.
    """
    chapter_number: int
    line_range: tuple[int, int]
    quote: str
    quote_sha256: str
    chapter_sha256: str


@dataclass
class SourceNote:
    """One accepted source-inherent L3 issue (`accept_with_notes`)."""
    note_id: str                       # SN-S{stage:03d}-{seq:02d}
    stage_id: str
    file: str                          # path of the extracted product
    json_path: str
    issue_fingerprint: str
    issue_category: str                # "semantic" (L3 source_inherent) or
                                       # "structural" (L2 coverage_shortage)
    issue_rule: str
    issue_severity: str
    issue_message: str
    discrepancy_type: str              # one of DISCREPANCY_TYPES
    source_evidence: SourceEvidence
    rationale: str
    extraction_choice: str
    future_fixer_hint: dict[str, Any]
    accepted_at: str                   # ISO 8601 with timezone
    triage_round: int                  # 1 = residual (post-cap), 2 = post-gate


@dataclass
class TriageVerdict:
    """Per-issue output of one triage decision, pre-validation.

    Either produced by the standalone triage LLM call, or self-reported
    by T2 fixers through their ``source_inherent`` return channel.
    The coordinator only accepts a verdict when both ``source_inherent``
    and ``evidence_verified`` are true.
    """
    issue_fingerprint: str
    source_inherent: bool
    discrepancy_type: str = "other"
    chapter_number: int | None = None
    line_range: tuple[int, int] | None = None
    quote: str = ""
    rationale: str = ""
    extraction_choice: str = ""
    evidence_verified: bool = False


# ---------------------------------------------------------------------------
# Issue — the universal checker output
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    """A problem found by any checker layer."""
    file: str
    json_path: str
    category: Literal[
        "json_syntax", "schema", "structural", "semantic", "cross_file"]
    severity: Literal["error", "warning"]
    rule: str
    message: str
    context: dict[str, Any] | None = None

    @property
    def fingerprint(self) -> str:
        return f"{self.file}::{self.json_path}::{self.rule}"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.file} {self.json_path}: {self.message}"


# ---------------------------------------------------------------------------
# Rule-based tier routing (T-REPAIR-NO-REEXTRACT Step C)
# ---------------------------------------------------------------------------
#
# Route each issue by "what fixing it needs", keyed on the issue *rule*
# first and falling back to *category*. Each entry is (start_tier,
# max_tier); tiers are 0=programmatic (0 token), 1=local_patch (LLM, NO
# source), 2=source_patch (LLM WITH chapter text). T3 (full-file regen)
# no longer exists.
#
#   * MECHANICAL (start T0, cap T1): deterministic-ish fixes. T0 handles
#     most; the few it can't → one light no-source T1 rewrite. Never
#     loads source. Covers json_parse, schema type/min-max length,
#     additionalProperties, id-format, stage_id alignment.
#   * JUDGEMENT, no source (start T1, cap T1): needs a model but not the
#     original text — enum choice, a clean length rewrite. Skips T0.
#   * SEMANTIC / needs original text (start T2, cap T2): must read the
#     source chapters — skip the wasted no-source T1 round.
#   * coverage_shortage: handled separately (start/cap T2 + 0-token
#     accept) via ``is_coverage_shortage``.

_MECHANICAL_TIERS = (0, 1)
_JUDGEMENT_TIERS = (1, 1)
_SEMANTIC_TIERS = (2, 2)

# Per-rule overrides (checked before the category fallback).
RULE_TIERS: dict[str, tuple[int, int]] = {
    # --- mechanical ---
    "json_parse": _MECHANICAL_TIERS,
    "schema_type": _MECHANICAL_TIERS,
    "schema_maxLength": _MECHANICAL_TIERS,
    "schema_minLength": _MECHANICAL_TIERS,
    "schema_additionalProperties": _MECHANICAL_TIERS,
    "schema_required": _MECHANICAL_TIERS,
    "memory_id_format": _MECHANICAL_TIERS,
    "event_id_format": _MECHANICAL_TIERS,
    "stage_id_alignment": _MECHANICAL_TIERS,
    "relationship_history_summary_max_length": _MECHANICAL_TIERS,
    # --- judgement, no source ---
    "schema_enum": _JUDGEMENT_TIERS,
}

# Category fallback when the rule isn't explicitly routed above.
CATEGORY_TIERS: dict[str, tuple[int, int]] = {
    "json_syntax": (0, 1),
    "schema": (0, 1),
    "structural": (0, 1),
    "semantic": _SEMANTIC_TIERS,
    "cross_file": _SEMANTIC_TIERS,
}


def route_tiers(issue: "Issue") -> tuple[int, int]:
    """Return ``(start_tier, max_tier)`` for an issue.

    coverage_shortage routes to T2 only (0-token accept downstream);
    otherwise the per-rule table wins, then the per-category fallback.

    **Root-anchored issues never reach an LLM tier.** Handing ``json_path ==
    "$"`` to T1/T2 means the model rewrites the entire document — exactly the
    T3 full-file regeneration decision #62 deleted, wearing a different hat
    (``apply_field_patch`` replaces the root outright). So a root-anchored
    issue is clamped to T0, and one that would *start* at an LLM tier has no
    fixer at all → ``NO_FIX_TIER`` → it defers (#60). T0 stays allowed: its
    useful root-anchored fix patches a *child* path (``$.field``) with a
    deterministic default, so e.g. a missing top-level required field is still
    mechanically fixable. (T0 may still hand ``$`` itself to
    ``apply_field_patch`` — e.g. "root should be an array" — where the root
    type guard rejects it and the issue defers rather than mangling the file.)
    Three classes reach NO_FIX in practice:

      * ``targets_baseline_missing`` — a *sibling* file is missing; rewriting
        this file cannot fix it.
      * ``semantic_unavailable`` / ``semantic_check_crashed`` /
        ``semantic_unparseable`` — the L3 *reviewer* failed. An infrastructure
        fault is not a content defect; rewriting the file is not the answer.
      * an LLM-reported semantic issue that omitted ``json_path`` (defaults to
        ``"$"``) — a degraded fallback, not a genuine root-level defect.
    """
    if is_coverage_shortage(issue):
        return (COVERAGE_SHORTAGE_START_TIER, COVERAGE_SHORTAGE_MAX_TIER)
    if issue.rule in RULE_TIERS:
        base = RULE_TIERS[issue.rule]
    else:
        base = CATEGORY_TIERS.get(issue.category, (0, 1))
    if is_root_anchored(issue):
        if base[0] >= 1:
            return (NO_FIX_TIER, NO_FIX_TIER)
        return (base[0], 0)
    return base


def issue_start_tier(issue: "Issue") -> int:
    return route_tiers(issue)[0]


def issue_max_tier(issue: "Issue") -> int:
    return route_tiers(issue)[1]


def is_coverage_shortage(issue: "Issue") -> bool:
    """True when an issue is a `min_examples` shortage routable to the
    coverage_shortage accept_with_notes fast path.

    Such issues are demoted to `severity=warning` and carry a
    `context.coverage_shortage=True` flag. They must:
      * route start=T2, cap=T2 (skip T0/T1) — T0 can't invent examples,
        T1 has no source access.
      * after a failed T2 try, trigger a 0-token program-constructed
        SourceNote (see ``Triager.build_coverage_shortage_verdict``)
        instead of a blocking error.
    """
    ctx = issue.context or {}
    return bool(ctx.get("coverage_shortage"))


# Coverage-shortage issues try T2 exactly once, then take the 0-token
# accept fast path (no source material can be invented).
COVERAGE_SHORTAGE_START_TIER = 2
COVERAGE_SHORTAGE_MAX_TIER = 2


# Sentinel start_tier for issues no fixer may touch: the coordinator's
# ``fixers.get(tier)`` returns None for it, so the issue is left alone and
# falls through to the residual / defer path (#60).
NO_FIX_TIER = -1


# Rules that say the L3 *reviewer itself* failed — backend down, empty or
# unparseable output. They are infrastructure faults, not content defects,
# so no fixer can settle one: the answer is to run the check again.
#
# Public because three layers key on the same set and each would otherwise
# invent its own copy: the semantic checker (which never lets a scoped
# filter drop one), the deferred ledger (which classifies such a row as
# unverified rather than as a semantic content debt), and Phase 3.5 (which
# routes it to re-verification instead of a field patch).
BACKEND_FAILURE_RULES: frozenset[str] = frozenset({
    "semantic_unavailable",
    "semantic_check_crashed",
    "semantic_unparseable",
})


def is_root_anchored(issue: "Issue") -> bool:
    """True when an issue anchors at the whole document rather than a field.

    ``json_syntax`` is deliberately excluded: T0 repairs it on the raw text
    (see ``ProgrammaticFixer``), never through ``apply_field_patch``, and it
    is not deferrable — treating it as root-anchored would hard-ERROR the
    stage instead of letting T0 fix it.
    """
    return (issue.json_path in ("$", "")
            and issue.category != "json_syntax")


# ---------------------------------------------------------------------------
# Repair tracking
# ---------------------------------------------------------------------------

@dataclass
class RepairAttempt:
    """Record of one fix attempt on one issue."""
    issue_fingerprint: str
    tier: int
    attempt_num: int
    strategy: str
    result: Literal["resolved", "persisting", "regression"]


@dataclass
class RoundReport:
    """Diff between consecutive validation rounds."""
    resolved: list[Issue] = field(default_factory=list)
    persisting: list[Issue] = field(default_factory=list)
    introduced: list[Issue] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

@dataclass
class FixResult:
    """Result from a single fixer invocation."""
    patched_paths: list[str] = field(default_factory=list)
    resolved_fingerprints: set[str] = field(default_factory=set)
    # T2 self-reported source_inherent candidates. Keyed by issue
    # fingerprint; each value is an un-validated TriageVerdict. The
    # coordinator runs the same quote-substring verification on these
    # as it does on the standalone triage LLM output.
    source_inherent_candidates: dict[str, TriageVerdict] = field(
        default_factory=dict)


@dataclass
class RepairResult:
    """Final output of a repair run."""
    passed: bool
    issues: list[Issue] = field(default_factory=list)
    history: dict[str, list[RepairAttempt]] = field(default_factory=dict)
    report: str = ""
    accepted_notes: list[SourceNote] = field(default_factory=list)
