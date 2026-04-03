"""Prompt builder — assembles context-aware prompts for each batch.

Instead of letting the agent explore and discover files on its own,
the orchestrator pre-computes exactly what the agent needs and injects
it into the prompt. This reduces cold-start time and drift risk.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .progress import BatchEntry, ExtractionProgress

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

_TEMPLATE_DIR = Path(__file__).parent.parent / "prompt_templates"


def _load_template(name: str) -> str:
    path = _TEMPLATE_DIR / name
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Analysis prompt
# ---------------------------------------------------------------------------

def build_analysis_prompt(project_root: Path, work_id: str) -> str:
    """Build prompt for the analysis phase (overview + batch plan + candidates)."""
    template = _load_template("analysis.md")

    # Gather context
    source_dir = project_root / "sources" / "works" / work_id
    manifest = _read_json(source_dir / "manifest.json")
    metadata = _read_json(source_dir / "metadata" / "book_metadata.json")
    chapter_index = _read_json(source_dir / "metadata" / "chapter_index.json")

    chapter_count = 0
    if chapter_index:
        chapter_count = len(chapter_index.get("chapters", []))

    context = {
        "work_id": work_id,
        "title": manifest.get("title", work_id) if manifest else work_id,
        "language": manifest.get("language", "zh") if manifest else "zh",
        "chapter_count": chapter_count,
        "source_dir": str(source_dir),
        "work_dir": str(project_root / "works" / work_id),
        "schemas_dir": str(project_root / "schemas"),
    }

    return template.format(**context)


# ---------------------------------------------------------------------------
# Coordinated extraction prompt
# ---------------------------------------------------------------------------

def build_extraction_prompt(
    project_root: Path,
    progress: ExtractionProgress,
    batch: BatchEntry,
    *,
    reviewer_feedback: str = "",
) -> str:
    """Build prompt for coordinated world + character extraction."""
    template = _load_template("coordinated_extraction.md")

    work_id = progress.work_id
    work_dir = project_root / "works" / work_id
    source_dir = project_root / "sources" / "works" / work_id

    # Determine previous batch output for style reference
    prev_batch = _find_previous_committed_batch(progress, batch)
    prev_world_snapshot = ""
    prev_char_snapshots: dict[str, str] = {}
    if prev_batch:
        ws_path = (work_dir / "world" / "stage_snapshots"
                   / f"{prev_batch.stage_id}.json")
        if ws_path.exists():
            prev_world_snapshot = str(ws_path)
        for char_id in progress.target_characters:
            cs_path = (work_dir / "characters" / char_id / "canon"
                       / "stage_snapshots" / f"{prev_batch.stage_id}.json")
            if cs_path.exists():
                prev_char_snapshots[char_id] = str(cs_path)

    # Build file read list for the agent
    files_to_read = _build_read_list(
        project_root, work_id, progress.target_characters,
        batch, prev_batch)

    context = {
        "work_id": work_id,
        "batch_id": batch.batch_id,
        "stage_id": batch.stage_id,
        "chapters": batch.chapters,
        "chapter_range": batch.chapters,
        "target_characters": ", ".join(progress.target_characters),
        "target_characters_list": json.dumps(
            progress.target_characters, ensure_ascii=False),
        "source_dir": str(source_dir),
        "work_dir": str(work_dir),
        "schemas_dir": str(project_root / "schemas"),
        "prev_world_snapshot": prev_world_snapshot,
        "prev_char_snapshots_json": json.dumps(
            prev_char_snapshots, ensure_ascii=False),
        "files_to_read": "\n".join(f"- {f}" for f in files_to_read),
        "is_first_batch": batch.batch_id == "batch_001",
        "reviewer_feedback": reviewer_feedback,
        "retry_note": (
            f"\n\n## 重试注意\n\n"
            f"上一次提取被 reviewer 打回，具体问题如下：\n\n"
            f"{reviewer_feedback}\n\n"
            f"请重点修复以上问题。"
        ) if reviewer_feedback else "",
    }

    return template.format(**context)


# ---------------------------------------------------------------------------
# Reviewer prompt
# ---------------------------------------------------------------------------

def build_reviewer_prompt(
    project_root: Path,
    progress: ExtractionProgress,
    batch: BatchEntry,
    programmatic_report: str,
) -> str:
    """Build prompt for semantic review."""
    template = _load_template("semantic_review.md")

    work_id = progress.work_id
    work_dir = project_root / "works" / work_id

    prev_batch = _find_previous_committed_batch(progress, batch)

    context = {
        "work_id": work_id,
        "batch_id": batch.batch_id,
        "stage_id": batch.stage_id,
        "chapters": batch.chapters,
        "target_characters": ", ".join(progress.target_characters),
        "work_dir": str(work_dir),
        "schemas_dir": str(project_root / "schemas"),
        "prev_stage_id": prev_batch.stage_id if prev_batch else "(无)",
        "programmatic_report": programmatic_report,
    }

    return template.format(**context)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_previous_committed_batch(
    progress: ExtractionProgress, current: BatchEntry
) -> BatchEntry | None:
    """Find the most recent committed batch before the current one."""
    for b in reversed(progress.batches):
        if b.batch_id == current.batch_id:
            continue
        if b.state.value == "committed":
            return b
    return None


def _build_read_list(
    project_root: Path,
    work_id: str,
    character_ids: list[str],
    batch: BatchEntry,
    prev_batch: BatchEntry | None,
) -> list[str]:
    """Pre-compute the list of files the extraction agent should read."""
    files: list[str] = []
    work_dir = project_root / "works" / work_id
    source_dir = project_root / "sources" / "works" / work_id

    # Schemas
    for schema in ("stage_snapshot.schema.json",
                   "world_stage_snapshot.schema.json",
                   "memory_timeline_entry.schema.json"):
        files.append(f"schemas/{schema}")

    # Architecture reference
    files.append("simulation/contracts/baseline_merge.md")

    # Checklist
    files.append("prompts/shared/批次执行检查清单.md")

    # Source chapters for this batch
    start, end = _parse_chapter_range(batch.chapters)
    for ch in range(start, end + 1):
        ch_file = source_dir / "chapters" / f"{ch:04d}.txt"
        if ch_file.exists():
            files.append(str(ch_file.relative_to(project_root)))

    # Previous batch output (style reference)
    if prev_batch:
        ws = (work_dir / "world" / "stage_snapshots"
              / f"{prev_batch.stage_id}.json")
        if ws.exists():
            files.append(str(ws.relative_to(project_root)))
        for char_id in character_ids:
            cs = (work_dir / "characters" / char_id / "canon"
                  / "stage_snapshots" / f"{prev_batch.stage_id}.json")
            if cs.exists():
                files.append(str(cs.relative_to(project_root)))

    # Existing world/character files (for cumulative awareness)
    for p in (work_dir / "world").rglob("*.json"):
        files.append(str(p.relative_to(project_root)))
    for char_id in character_ids:
        char_dir = work_dir / "characters" / char_id / "canon"
        if char_dir.exists():
            for p in char_dir.rglob("*"):
                if p.is_file():
                    files.append(str(p.relative_to(project_root)))

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique.append(f)

    return unique


def _parse_chapter_range(chapters: str) -> tuple[int, int]:
    """Parse '0001-0010' into (1, 10)."""
    parts = chapters.split("-")
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    return int(parts[0]), int(parts[0])


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
