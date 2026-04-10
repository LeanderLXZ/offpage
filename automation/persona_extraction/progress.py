"""Extraction progress tracking and state machine.

Progress file lives at:
  works/{work_id}/analysis/incremental/extraction_progress.json

State machine per batch:
  pending → extracting → extracted → post_processing → reviewing
                │                                        │  │
                └→ error                                 │  └→ fixing → passed → committed
                                                         │               │
                                                         └→ failed ──────┘
                                                              └→ retrying → extracting
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BatchState(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    POST_PROCESSING = "post_processing"
    REVIEWING = "reviewing"
    PASSED = "passed"
    COMMITTED = "committed"
    FIXING = "fixing"
    FAILED = "failed"
    RETRYING = "retrying"
    ERROR = "error"


# Valid transitions
_TRANSITIONS: dict[BatchState, set[BatchState]] = {
    BatchState.PENDING:          {BatchState.EXTRACTING, BatchState.EXTRACTED,
                                  BatchState.ERROR},
    BatchState.EXTRACTING:       {BatchState.EXTRACTED, BatchState.ERROR},
    BatchState.EXTRACTED:        {BatchState.POST_PROCESSING,
                                  BatchState.REVIEWING},  # REVIEWING kept for compat
    BatchState.POST_PROCESSING:  {BatchState.REVIEWING, BatchState.ERROR},
    BatchState.REVIEWING:        {BatchState.PASSED, BatchState.FAILED,
                                  BatchState.FIXING},
    BatchState.FIXING:           {BatchState.PASSED, BatchState.FAILED},
    BatchState.PASSED:           {BatchState.COMMITTED},
    BatchState.COMMITTED:        set(),  # terminal
    BatchState.FAILED:           {BatchState.RETRYING},
    BatchState.RETRYING:         {BatchState.EXTRACTING, BatchState.EXTRACTED,
                                  BatchState.ERROR},
    BatchState.ERROR:            {BatchState.EXTRACTING, BatchState.PENDING},
}


@dataclass
class BatchEntry:
    batch_id: str
    stage_id: str
    chapters: str               # e.g. "0001-0010"
    chapter_count: int
    state: BatchState = BatchState.PENDING
    retry_count: int = 0
    max_retries: int = 2
    last_reviewer_feedback: str = ""
    committed_sha: str = ""
    last_updated: str = ""
    error_message: str = ""
    fail_source: str = ""  # "programmatic" or "semantic" — which check caused FAIL

    def can_transition(self, target: BatchState) -> bool:
        return target in _TRANSITIONS.get(self.state, set())

    def transition(self, target: BatchState) -> None:
        if not self.can_transition(target):
            raise ValueError(
                f"Invalid transition: {self.state.value} → {target.value} "
                f"(batch {self.batch_id})"
            )
        self.state = target
        self.last_updated = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "stage_id": self.stage_id,
            "chapters": self.chapters,
            "chapter_count": self.chapter_count,
            "state": self.state.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_reviewer_feedback": self.last_reviewer_feedback,
            "committed_sha": self.committed_sha,
            "last_updated": self.last_updated,
            "error_message": self.error_message,
            "fail_source": self.fail_source,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BatchEntry:
        return cls(
            batch_id=d["batch_id"],
            stage_id=d["stage_id"],
            chapters=d["chapters"],
            chapter_count=d["chapter_count"],
            state=BatchState(d.get("state", "pending")),
            retry_count=d.get("retry_count", 0),
            max_retries=d.get("max_retries", 2),
            last_reviewer_feedback=d.get("last_reviewer_feedback", ""),
            committed_sha=d.get("committed_sha", ""),
            last_updated=d.get("last_updated", ""),
            error_message=d.get("error_message", ""),
            fail_source=d.get("fail_source", ""),
        )


@dataclass
class ExtractionProgress:
    """Full extraction progress for a work."""
    work_id: str
    target_characters: list[str] = field(default_factory=list)
    batch_size: int = 10
    extraction_branch: str = ""
    batches: list[BatchEntry] = field(default_factory=list)
    analysis_done: bool = False
    characters_confirmed: bool = False
    baseline_done: bool = False
    created_at: str = ""
    last_updated: str = ""

    # ---- Queries ----

    def next_pending_batch(self) -> BatchEntry | None:
        """Return the first actionable batch, respecting sequential order.

        Batches are sequential — batch N+1 depends on batch N's output.
        We scan in order and return the first non-committed batch that is
        actionable.  If a batch is stuck (failed/error beyond max retries),
        we return None to block the pipeline rather than skipping ahead.
        """
        for b in self.batches:
            if b.state == BatchState.COMMITTED:
                continue
            # In-progress states (interrupted run) — resume immediately
            if b.state in (BatchState.EXTRACTING, BatchState.EXTRACTED,
                           BatchState.REVIEWING, BatchState.FIXING,
                           BatchState.RETRYING):
                return b
            # Pending — normal next batch
            if b.state == BatchState.PENDING:
                return b
            # Failed — retry if allowed, otherwise block
            if b.state == BatchState.FAILED:
                if b.retry_count < b.max_retries:
                    return b
                return None  # blocked — needs manual intervention
            # Error — retry if allowed, otherwise block
            if b.state == BatchState.ERROR:
                if b.retry_count < b.max_retries:
                    return b
                return None  # blocked — needs manual intervention
        return None

    def all_committed(self) -> bool:
        return all(b.state == BatchState.COMMITTED for b in self.batches)

    def completed_batch_count(self) -> int:
        return sum(1 for b in self.batches
                   if b.state == BatchState.COMMITTED)

    def last_committed_batch(self) -> BatchEntry | None:
        for b in reversed(self.batches):
            if b.state == BatchState.COMMITTED:
                return b
        return None

    def expand_batches(self, full_plan_batches: list[dict],
                       max_batches: int = 0) -> int:
        """Append new batches from the full batch plan that are not yet tracked.

        Args:
            full_plan_batches: All batches from source_batch_plan.json.
            max_batches: Expand up to this many total batches (0 = all).

        Returns:
            Number of new batches added.
        """
        existing_ids = {b.batch_id for b in self.batches}
        target = full_plan_batches[:max_batches] if max_batches > 0 \
            else full_plan_batches
        added = 0
        for b in target:
            if b["batch_id"] not in existing_ids:
                self.batches.append(BatchEntry(
                    batch_id=b["batch_id"],
                    stage_id=b["stage_id"],
                    chapters=b["chapters"],
                    chapter_count=b.get("chapter_count", 0),
                ))
                added += 1
        return added

    # ---- Persistence ----

    def progress_path(self, project_root: Path) -> Path:
        return (project_root / "works" / self.work_id
                / "analysis" / "incremental" / "extraction_progress.json")

    def save(self, project_root: Path) -> Path:
        path = self.progress_path(project_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.last_updated = _now_iso()
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False,
                                   indent=2),
                        encoding="utf-8")
        logger.info("Progress saved: %s", path)
        return path

    @classmethod
    def load(cls, project_root: Path, work_id: str) -> ExtractionProgress | None:
        path = (project_root / "works" / work_id
                / "analysis" / "incremental" / "extraction_progress.json")
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls.from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            logger.warning("Failed to load progress from %s: %s", path, exc)
            return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_id": self.work_id,
            "target_characters": self.target_characters,
            "batch_size": self.batch_size,
            "extraction_branch": self.extraction_branch,
            "batches": [b.to_dict() for b in self.batches],
            "analysis_done": self.analysis_done,
            "characters_confirmed": self.characters_confirmed,
            "baseline_done": self.baseline_done,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExtractionProgress:
        return cls(
            work_id=d["work_id"],
            target_characters=d.get("target_characters", []),
            batch_size=d.get("batch_size", 10),
            extraction_branch=d.get("extraction_branch", ""),
            batches=[BatchEntry.from_dict(b) for b in d.get("batches", [])],
            analysis_done=d.get("analysis_done", False),
            characters_confirmed=d.get("characters_confirmed", False),
            baseline_done=d.get("baseline_done", False),
            created_at=d.get("created_at", ""),
            last_updated=d.get("last_updated", ""),
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
