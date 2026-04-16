"""Extraction progress tracking and state machine.

Progress files live under:
  works/{work_id}/analysis/progress/

  pipeline.json         — phase-level completion status
  phase0_summaries.json — Phase 0 chunk progress
  phase3_stages.json   — Phase 3 stage state machine
  phase4_scenes.json    — Phase 4 per-chapter progress (managed by scene_archive.py)

State machine per stage (Phase 3):
  pending → extracting → extracted → post_processing → reviewing
                │                                          │
                └→ error                                   ├→ passed → committed
                                                           │              │
                                                           └→ failed ─────┘
                                                                  └→ retrying → extracting

Targeted fix is handled inside a review lane (validate → review → fix →
re-verify) and does not surface as a stage-level state.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _git_object_exists(project_root: Path, sha: str) -> bool:
    """Return True if the given object SHA is present in the repo.

    Used to detect committed_sha drift: a commit recorded in progress
    may have been dropped by `git reset --hard` or rebase, in which
    case the stage must be re-run from scratch.
    """
    if not sha:
        return False
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", sha],
            cwd=project_root, capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _progress_dir(project_root: Path, work_id: str) -> Path:
    return project_root / "works" / work_id / "analysis" / "progress"


# ---------------------------------------------------------------------------
# Pipeline progress (phase-level)
# ---------------------------------------------------------------------------

# Phase states
PHASE_PENDING = "pending"
PHASE_RUNNING = "running"
PHASE_DONE = "done"

# Canonical phase keys
PHASE_KEYS = (
    "phase_0", "phase_1", "phase_2", "phase_2_5",
    "phase_3", "phase_3_5", "phase_4",
)


@dataclass
class PipelineProgress:
    """Top-level pipeline status — tracks which phases are done."""
    work_id: str
    extraction_branch: str = ""
    target_characters: list[str] = field(default_factory=list)
    phases: dict[str, str] = field(default_factory=dict)
    created_at: str = ""
    last_updated: str = ""

    def __post_init__(self):
        # Ensure all phase keys exist
        for key in PHASE_KEYS:
            self.phases.setdefault(key, PHASE_PENDING)

    def phase_state(self, key: str) -> str:
        return self.phases.get(key, PHASE_PENDING)

    def set_phase(self, key: str, state: str) -> None:
        self.phases[key] = state
        self.last_updated = _now_iso()

    def mark_done(self, key: str) -> None:
        self.set_phase(key, PHASE_DONE)

    def is_done(self, key: str) -> bool:
        return self.phase_state(key) == PHASE_DONE

    # ---- Persistence ----

    @staticmethod
    def _path(project_root: Path, work_id: str) -> Path:
        return _progress_dir(project_root, work_id) / "pipeline.json"

    def save(self, project_root: Path) -> Path:
        path = self._path(project_root, self.work_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.last_updated = _now_iso()
        data = {
            "work_id": self.work_id,
            "extraction_branch": self.extraction_branch,
            "target_characters": self.target_characters,
            "phases": self.phases,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8")
        logger.info("Pipeline progress saved: %s", path)
        return path

    @classmethod
    def load(cls, project_root: Path, work_id: str) -> PipelineProgress | None:
        path = cls._path(project_root, work_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                work_id=data["work_id"],
                extraction_branch=data.get("extraction_branch", ""),
                target_characters=data.get("target_characters", []),
                phases=data.get("phases", {}),
                created_at=data.get("created_at", ""),
                last_updated=data.get("last_updated", ""),
            )
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            logger.warning("Failed to load pipeline progress: %s", exc)
            return None


# ---------------------------------------------------------------------------
# Phase 0 progress (chunk-level)
# ---------------------------------------------------------------------------

@dataclass
class ChunkEntry:
    chunk_id: str
    chapters: str           # e.g. "0001-0025"
    state: str = "pending"  # pending | done | failed
    retry_count: int = 0
    error_message: str = ""
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapters": self.chapters,
            "state": self.state,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, chunk_id: str, d: dict[str, Any]) -> ChunkEntry:
        return cls(
            chunk_id=chunk_id,
            chapters=d.get("chapters", ""),
            state=d.get("state", "pending"),
            retry_count=d.get("retry_count", 0),
            error_message=d.get("error_message", ""),
            last_updated=d.get("last_updated", ""),
        )


@dataclass
class Phase0Progress:
    """Phase 0 chunk-level progress."""
    work_id: str
    total_chapters: int = 0
    chunk_size: int = 25
    total_chunks: int = 0
    chunks: dict[str, ChunkEntry] = field(default_factory=dict)
    last_updated: str = ""

    def all_done(self) -> bool:
        return all(c.state == "done" for c in self.chunks.values())

    def done_count(self) -> int:
        return sum(1 for c in self.chunks.values() if c.state == "done")

    # ---- Persistence ----

    @staticmethod
    def _path(project_root: Path, work_id: str) -> Path:
        return _progress_dir(project_root, work_id) / "phase0_summaries.json"

    def save(self, project_root: Path) -> Path:
        path = self._path(project_root, self.work_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.last_updated = _now_iso()
        data = {
            "work_id": self.work_id,
            "total_chapters": self.total_chapters,
            "chunk_size": self.chunk_size,
            "total_chunks": self.total_chunks,
            "chunks": {
                cid: entry.to_dict()
                for cid, entry in self.chunks.items()
            },
            "last_updated": self.last_updated,
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8")
        return path

    @classmethod
    def load(cls, project_root: Path, work_id: str) -> Phase0Progress | None:
        path = cls._path(project_root, work_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            prog = cls(
                work_id=data["work_id"],
                total_chapters=data.get("total_chapters", 0),
                chunk_size=data.get("chunk_size", 25),
                total_chunks=data.get("total_chunks", 0),
                last_updated=data.get("last_updated", ""),
            )
            for cid, entry_data in data.get("chunks", {}).items():
                prog.chunks[cid] = ChunkEntry.from_dict(cid, entry_data)
            return prog
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            logger.warning("Failed to load Phase 0 progress: %s", exc)
            return None

    def reconcile_with_disk(self, project_root: Path) -> dict[str, int]:
        """Reconcile in-memory states against on-disk chunk summaries.

        Rules:
          - state == "done" but file missing       → revert to "pending"
          - state != "done" but file exists        → delete partial file
            (interrupted mid-write; re-extract)

        Returns counts: {"reverted": N, "purged": M}.
        """
        summaries_dir = (project_root / "works" / self.work_id
                         / "analysis" / "chapter_summaries")
        reverted = 0
        purged = 0
        for entry in self.chunks.values():
            idx = int(entry.chunk_id.split("_")[-1])
            output_path = summaries_dir / f"chunk_{idx:03d}.json"
            on_disk = output_path.exists()
            if entry.state == "done" and not on_disk:
                entry.state = "pending"
                entry.retry_count = 0
                entry.error_message = ""
                reverted += 1
            elif entry.state != "done" and on_disk:
                output_path.unlink()
                purged += 1
        return {"reverted": reverted, "purged": purged}


# ---------------------------------------------------------------------------
# Phase 3 stage state machine
# ---------------------------------------------------------------------------

class StageState(str, Enum):
    """Phase 3 stage states.

    Review-lane ``targeted fix`` is handled internally within a lane
    (validate → review → fix → re-verify); it is NOT a stage-level state.
    ``FAILED`` here already covers post-review rollback paths.
    """
    PENDING = "pending"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    POST_PROCESSING = "post_processing"
    REVIEWING = "reviewing"
    PASSED = "passed"
    COMMITTED = "committed"
    FAILED = "failed"
    RETRYING = "retrying"
    ERROR = "error"


# Valid transitions
_TRANSITIONS: dict[StageState, set[StageState]] = {
    StageState.PENDING:          {StageState.EXTRACTING, StageState.EXTRACTED,
                                  StageState.ERROR},
    StageState.EXTRACTING:       {StageState.EXTRACTED, StageState.ERROR},
    StageState.EXTRACTED:        {StageState.POST_PROCESSING,
                                  StageState.REVIEWING},  # REVIEWING kept for compat
    StageState.POST_PROCESSING:  {StageState.REVIEWING, StageState.ERROR},
    StageState.REVIEWING:        {StageState.PASSED, StageState.FAILED},
    StageState.PASSED:           {StageState.COMMITTED, StageState.FAILED},
    StageState.COMMITTED:        set(),  # terminal
    StageState.FAILED:           {StageState.RETRYING},
    StageState.RETRYING:         {StageState.EXTRACTING, StageState.EXTRACTED,
                                  StageState.ERROR},
    StageState.ERROR:            {StageState.EXTRACTING, StageState.PENDING},
}


@dataclass
class StageEntry:
    stage_id: str
    chapters: str               # e.g. "0001-0010"
    chapter_count: int
    state: StageState = StageState.PENDING
    retry_count: int = 0
    max_retries: int = 2
    last_reviewer_feedback: str = ""
    committed_sha: str = ""
    last_updated: str = ""
    error_message: str = ""
    fail_source: str = ""  # "programmatic" or "semantic" — which check caused FAIL
    # Per-lane retry tracking (lane_key → retry_count). Keys are the lane
    # identifiers used by review_lanes: "world" for the world lane,
    # "character:{char_id}" for each character lane. Lane retries are
    # bounded by ``lane_max_retries`` and **shared across three paths**:
    #   1. Initial extraction (Step 2): a single lane's LLM error retries
    #      only that lane, preserving sibling outputs.
    #   2. Review-failure retries (Step 4 inner loop).
    #   3. Commit-gate failure cascade (Step 5 outer loop).
    # All three consume the same counter so a stage cannot ping-pong the
    # budget. When any lane exhausts its quota, the whole stage falls
    # back to full-stage rollback (see orchestrator._process_stage Steps
    # 2/4/5 and requirements §11.4b/§11.5). Cleared only after the
    # commit gate finally PASSes (or on stage-level rollback).
    lane_retries: dict[str, int] = field(default_factory=dict)
    lane_max_retries: int = 2

    def can_transition(self, target: StageState) -> bool:
        return target in _TRANSITIONS.get(self.state, set())

    def transition(self, target: StageState) -> None:
        if not self.can_transition(target):
            raise ValueError(
                f"Invalid transition: {self.state.value} → {target.value} "
                f"(stage {self.stage_id})"
            )
        self.state = target
        self.last_updated = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
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
            "lane_retries": dict(self.lane_retries),
            "lane_max_retries": self.lane_max_retries,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> StageEntry:
        return cls(
            stage_id=d["stage_id"],
            chapters=d["chapters"],
            chapter_count=d["chapter_count"],
            state=StageState(d.get("state", "pending")),
            retry_count=d.get("retry_count", 0),
            max_retries=d.get("max_retries", 2),
            last_reviewer_feedback=d.get("last_reviewer_feedback", ""),
            committed_sha=d.get("committed_sha", ""),
            last_updated=d.get("last_updated", ""),
            error_message=d.get("error_message", ""),
            fail_source=d.get("fail_source", ""),
            lane_retries=dict(d.get("lane_retries", {})),
            lane_max_retries=d.get("lane_max_retries", 2),
        )


@dataclass
class Phase3Progress:
    """Phase 3 stage extraction progress."""
    work_id: str
    stage_size: int = 10
    stages: list[StageEntry] = field(default_factory=list)
    last_updated: str = ""

    # ---- Queries ----

    def next_pending_stage(self) -> StageEntry | None:
        """Return the first actionable stage, respecting sequential order.

        Stages are sequential — stage N+1 depends on stage N's output.
        We scan in order and return the first non-committed stage that is
        actionable.  If a stage is stuck (failed/error beyond max retries),
        we return None to block the pipeline rather than skipping ahead.
        """
        for b in self.stages:
            if b.state == StageState.COMMITTED:
                continue
            # In-progress states (interrupted run) — resume immediately
            if b.state in (StageState.EXTRACTING, StageState.EXTRACTED,
                           StageState.POST_PROCESSING, StageState.REVIEWING,
                           StageState.PASSED, StageState.RETRYING):
                return b
            # Pending — normal next stage
            if b.state == StageState.PENDING:
                return b
            # Failed — retry if allowed, otherwise block
            if b.state == StageState.FAILED:
                if b.retry_count < b.max_retries:
                    return b
                return None  # blocked — needs manual intervention
            # Error — retry if allowed, otherwise block
            if b.state == StageState.ERROR:
                if b.retry_count < b.max_retries:
                    return b
                return None  # blocked — needs manual intervention
        return None

    def all_committed(self) -> bool:
        return all(b.state == StageState.COMMITTED for b in self.stages)

    def completed_stage_count(self) -> int:
        return sum(1 for b in self.stages
                   if b.state == StageState.COMMITTED)

    def last_committed_stage(self) -> StageEntry | None:
        for b in reversed(self.stages):
            if b.state == StageState.COMMITTED:
                return b
        return None

    def expand_stages(self, full_plan_stages: list[dict],
                       max_stages: int = 0) -> int:
        """Append new stages from the full stage plan that are not yet tracked.

        Args:
            full_plan_stages: All stages from stage_plan.json.
            max_stages: Expand up to this many total stages (0 = all).

        Returns:
            Number of new stages added.
        """
        existing_ids = {b.stage_id for b in self.stages}
        target = full_plan_stages[:max_stages] if max_stages > 0 \
            else full_plan_stages
        added = 0
        for b in target:
            if b["stage_id"] not in existing_ids:
                self.stages.append(StageEntry(
                    stage_id=b["stage_id"],
                    chapters=b["chapters"],
                    chapter_count=b.get("chapter_count", 0),
                ))
                added += 1
        return added

    # ---- Persistence ----

    @staticmethod
    def _path(project_root: Path, work_id: str) -> Path:
        return _progress_dir(project_root, work_id) / "phase3_stages.json"

    def save(self, project_root: Path) -> Path:
        path = self._path(project_root, self.work_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.last_updated = _now_iso()
        data = {
            "work_id": self.work_id,
            "stage_size": self.stage_size,
            "stages": [b.to_dict() for b in self.stages],
            "last_updated": self.last_updated,
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8")
        logger.info("Phase 3 progress saved: %s", path)
        return path

    @classmethod
    def load(cls, project_root: Path, work_id: str) -> Phase3Progress | None:
        path = cls._path(project_root, work_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                work_id=data["work_id"],
                stage_size=data.get("stage_size", 10),
                stages=[StageEntry.from_dict(b)
                         for b in data.get("stages", [])],
                last_updated=data.get("last_updated", ""),
            )
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            logger.warning("Failed to load Phase 3 progress: %s", exc)
            return None

    def reconcile_with_disk(self, project_root: Path,
                             target_characters: list[str],
                             ) -> dict[str, int]:
        """Reconcile stage states against on-disk artifacts and git history.

        Per-stage expected artifacts:
          - works/{wid}/world/stage_snapshots/{stage_id}.json
          - works/{wid}/characters/{char}/canon/stage_snapshots/{stage_id}.json
          - works/{wid}/characters/{char}/canon/memory_timeline/{stage_id}.json
            for each character in target_characters

        Cumulative artifacts (memory_digest.jsonl, world_event_digest.jsonl,
        *_catalog.json) cannot be checked per-stage and are left alone.

        Rules:
          - state == COMMITTED:
              * any per-stage artifact missing OR committed_sha not in git
                → revert to PENDING, clear committed_sha; remaining
                  per-stage artifacts (if any) are deleted as orphans
          - state == PENDING:
              * any per-stage artifact present → delete (partial run)
          - state in {EXTRACTING, EXTRACTED, POST_PROCESSING, REVIEWING,
                      PASSED, RETRYING, FAILED, ERROR}:
              * delete any per-stage artifacts, revert to PENDING

        Returns counts: {"reverted": N, "purged_files": M, "sha_missing": K}.
        """
        work_dir = project_root / "works" / self.work_id
        reverted = 0
        purged_files = 0
        sha_missing = 0

        for stage in self.stages:
            paths = self._stage_artifact_paths(work_dir, stage.stage_id,
                                                target_characters)
            existing = [p for p in paths if p.exists()]

            if stage.state == StageState.COMMITTED:
                sha_ok = _git_object_exists(project_root, stage.committed_sha)
                if not sha_ok:
                    sha_missing += 1
                if len(existing) < len(paths) or not sha_ok:
                    for p in existing:
                        p.unlink()
                        purged_files += 1
                    stage.state = StageState.PENDING
                    stage.committed_sha = ""
                    stage.retry_count = 0
                    stage.error_message = ""
                    stage.fail_source = ""
                    stage.last_reviewer_feedback = ""
                    stage.lane_retries = {}
                    reverted += 1
                continue

            if stage.state == StageState.PENDING:
                if existing:
                    for p in existing:
                        p.unlink()
                        purged_files += 1
                continue

            # Intermediate states — discard any partial output, revert
            for p in existing:
                p.unlink()
                purged_files += 1
            stage.state = StageState.PENDING
            stage.retry_count = 0
            stage.error_message = ""
            stage.fail_source = ""
            stage.last_reviewer_feedback = ""
            stage.lane_retries = {}
            reverted += 1

        return {"reverted": reverted, "purged_files": purged_files,
                "sha_missing": sha_missing}

    @staticmethod
    def _stage_artifact_paths(work_dir: Path, stage_id: str,
                               target_characters: list[str]) -> list[Path]:
        paths = [work_dir / "world" / "stage_snapshots" / f"{stage_id}.json"]
        for char_id in target_characters:
            char_canon = work_dir / "characters" / char_id / "canon"
            paths.append(char_canon / "stage_snapshots" / f"{stage_id}.json")
            paths.append(char_canon / "memory_timeline" / f"{stage_id}.json")
        return paths


# ---------------------------------------------------------------------------
# Legacy migration helper
# ---------------------------------------------------------------------------

def migrate_legacy_progress(
    project_root: Path, work_id: str,
) -> tuple[PipelineProgress, Phase3Progress] | None:
    """Migrate old extraction_progress.json → pipeline.json + phase3_stages.json.

    Returns the new objects if migration happened, None if no legacy file found.
    """
    legacy_path = (project_root / "works" / work_id
                   / "analysis" / "incremental" / "extraction_progress.json")
    if not legacy_path.exists():
        # Also check analysis/ directly (partially migrated)
        legacy_path = (project_root / "works" / work_id
                       / "analysis" / "extraction_progress.json")
        if not legacy_path.exists():
            return None

    try:
        data = json.loads(legacy_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    pipeline = PipelineProgress(
        work_id=data["work_id"],
        extraction_branch=data.get("extraction_branch", ""),
        target_characters=data.get("target_characters", []),
        created_at=data.get("created_at", ""),
    )
    # Map legacy bool flags to phase states
    if data.get("analysis_done"):
        pipeline.mark_done("phase_1")
    if data.get("characters_confirmed"):
        pipeline.mark_done("phase_2")
    if data.get("baseline_done"):
        pipeline.mark_done("phase_2_5")

    phase3 = Phase3Progress(
        work_id=data["work_id"],
        stage_size=data.get("stage_size", 10),
        stages=[StageEntry.from_dict(b) for b in data.get("stages", [])],
    )

    # Save new files
    pipeline.save(project_root)
    phase3.save(project_root)

    logger.info("Migrated legacy progress: %s", legacy_path)
    return pipeline, phase3
