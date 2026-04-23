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
    """
    path: str
    schema: dict | None = None
    content: dict | list | None = None  # pre-loaded; None = read from path
    is_jsonl_slice: bool = False
    jsonl_full_content: list[dict] | None = None
    jsonl_key_field: str = ""

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
    """Per-tier retry limits."""
    t0_max: int = 1
    t1_max: int = 3
    t2_max: int = 3
    t3_max: int = 1
    t3_max_per_file: int = 1  # global cap per file across entire run
    max_total_rounds: int = 5


@dataclass
class RepairConfig:
    """Configuration for a repair run."""
    max_rounds: int = 5
    block_on: Literal["error", "all"] = "error"
    run_semantic: bool = True
    l3_gate_enabled: bool = True
    triage_enabled: bool = True          # source-discrepancy triage on L3
    accept_cap_per_file: int = 5         # max SourceNotes per file
                                         # (shared by L3 source_inherent +
                                         # L2 coverage_shortage)
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
    triage_round: int                  # 1 = pre-T3, 2 = post-T3


@dataclass
class TriageVerdict:
    """Per-issue output of one triage decision, pre-validation.

    Either produced by the standalone triage LLM call, or self-reported
    by T2 / T3 fixers through their ``source_inherent`` return channel.
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
    category: Literal["json_syntax", "schema", "structural", "semantic"]
    severity: Literal["error", "warning"]
    rule: str
    message: str
    context: dict[str, Any] | None = None

    @property
    def fingerprint(self) -> str:
        return f"{self.file}::{self.json_path}::{self.rule}"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.file} {self.json_path}: {self.message}"


# Mapping from issue category to the lowest fixer tier that can handle it.
START_TIER: dict[str, int] = {
    "json_syntax": 0,
    "schema": 0,
    "structural": 0,
    "semantic": 1,
}


def is_coverage_shortage(issue: "Issue") -> bool:
    """True when an issue is a `min_examples` shortage routable to the
    coverage_shortage accept_with_notes fast path.

    Such issues are demoted to `severity=warning` and carry a
    `context.coverage_shortage=True` flag. They must:
      * route `START_TIER=2, MAX_TIER=2` (skip T0/T1/T3) — T0 can't
        invent examples, T1 has no source access, T3 file-regen won't
        make the novel longer.
      * after a failed T2 try, trigger a 0-token program-constructed
        SourceNote (see ``Triager.build_coverage_shortage_verdict``)
        instead of a blocking error.
    """
    ctx = issue.context or {}
    return bool(ctx.get("coverage_shortage"))


# Coverage-shortage issues try T2 exactly once; they never escalate
# to T3 (file regeneration can't add source material that isn't there).
COVERAGE_SHORTAGE_START_TIER = 2
COVERAGE_SHORTAGE_MAX_TIER = 2


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
    # T2/T3 self-reported source_inherent candidates. Keyed by issue
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
