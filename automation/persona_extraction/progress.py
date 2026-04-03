"""Extraction progress tracking and state machine.

Progress file lives at:
  works/{work_id}/analysis/incremental/extraction_progress.json

State machine per batch:
  pending → extracting → extracted → reviewing → passed → committed
                │                       │
                └→ error                └→ failed → retrying → extracting
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
    REVIEWING = "reviewing"
    PASSED = "passed"
    COMMITTED = "committed"
    FAILED = "failed"
    RETRYING = "retrying"
    ERROR = "error"


# Valid transitions
_TRANSITIONS: dict[BatchState, set[BatchState]] = {
    BatchState.PENDING:     {BatchState.EXTRACTING},
    BatchState.EXTRACTING:  {BatchState.EXTRACTED, BatchState.ERROR},
    BatchState.EXTRACTED:   {BatchState.REVIEWING},
    BatchState.REVIEWING:   {BatchState.PASSED, BatchState.FAILED},
    BatchState.PASSED:      {BatchState.COMMITTED},
    BatchState.COMMITTED:   set(),  # terminal
    BatchState.FAILED:      {BatchState.RETRYING},
    BatchState.RETRYING:    {BatchState.EXTRACTING},
    BatchState.ERROR:       {BatchState.EXTRACTING, BatchState.PENDING},
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
    created_at: str = ""
    last_updated: str = ""

    # ---- Queries ----

    def next_pending_batch(self) -> BatchEntry | None:
        """Return the first actionable batch (pending, or error/failed needing retry)."""
        # First: any batch in-progress that got interrupted
        for b in self.batches:
            if b.state in (BatchState.EXTRACTING, BatchState.EXTRACTED,
                           BatchState.REVIEWING, BatchState.RETRYING):
                return b
        # Then: first pending
        for b in self.batches:
            if b.state == BatchState.PENDING:
                return b
        # Then: failed batches that can still retry
        for b in self.batches:
            if b.state == BatchState.FAILED and b.retry_count < b.max_retries:
                return b
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
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_id": self.work_id,
            "target_characters": self.target_characters,
            "batch_size": self.batch_size,
            "extraction_branch": self.extraction_branch,
            "batches": [b.to_dict() for b in self.batches],
            "analysis_done": self.analysis_done,
            "characters_confirmed": self.characters_confirmed,
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
            created_at=d.get("created_at", ""),
            last_updated=d.get("last_updated", ""),
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
