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
    """A file to be checked / repaired."""
    path: str
    schema: dict | None = None
    content: dict | list | None = None  # pre-loaded; None = read from path

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
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)


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


@dataclass
class RepairResult:
    """Final output of a repair run."""
    passed: bool
    issues: list[Issue] = field(default_factory=list)
    history: dict[str, list[RepairAttempt]] = field(default_factory=dict)
    report: str = ""
