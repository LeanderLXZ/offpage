"""Per-lane failure diagnostic log writer.

Writes human-readable diagnostic files to
``works/{work_id}/analysis/progress/failed_lanes/`` whenever a Phase 3
extraction lane fails. The prompt is intentionally NOT written to disk —
it can be rebuilt from git state plus stage_id, and keeping the log
diagnostic-only avoids duplicating bulk content.
"""

from __future__ import annotations

import datetime as _dt
import logging
import re
from pathlib import Path

from .llm_backend import LLMResult

logger = logging.getLogger(__name__)


_FILENAME_UNSAFE = re.compile(r"[^\w\u4e00-\u9fff.-]+")


def _sanitize(token: str) -> str:
    """Replace characters that are awkward in filenames while keeping CJK."""
    return _FILENAME_UNSAFE.sub("_", token).strip("_") or "unknown"


def write_failed_lane_log(
    work_root: Path,
    stage_id: str,
    lane_type: str,
    lane_id: str,
    result: LLMResult,
    prompt_length: int,
) -> Path | None:
    """Persist diagnostic output for a failed extraction lane.

    Returns the path to the log file, or None if writing failed.
    """
    dir_path = work_root / "analysis" / "progress" / "failed_lanes"
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
    except OSError:
        logger.exception("failed to create %s", dir_path)
        return None

    stage_token = _sanitize(stage_id)
    lane_type_token = _sanitize(lane_type)
    lane_id_token = _sanitize(lane_id)
    pid = result.pid if result.pid is not None else 0
    filename = (
        f"{stage_token}__{lane_type_token}_{lane_id_token}"
        f"__{pid}.log"
    )
    path = dir_path / filename

    iso_ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    header_lines = [
        f"timestamp: {iso_ts}",
        f"stage_id: {stage_id}",
        f"lane_type: {lane_type}",
        f"lane_id: {lane_id}",
        f"pid: {pid}",
        f"duration_seconds: {result.duration_seconds:.1f}",
        f"prompt_length: {prompt_length}",
        f"error: {result.error or ''}",
    ]
    if result.subtype is not None:
        header_lines.append(f"subtype: {result.subtype}")
    if result.num_turns is not None:
        header_lines.append(f"num_turns: {result.num_turns}")
    if result.total_cost_usd is not None:
        header_lines.append(f"total_cost_usd: {result.total_cost_usd}")

    body = (
        "\n".join(header_lines)
        + "\n\n---STDOUT---\n"
        + (result.raw_stdout or "")
        + "\n\n---STDERR---\n"
        + (result.raw_stderr or "")
        + "\n"
    )
    try:
        path.write_text(body, encoding="utf-8")
    except OSError:
        logger.exception("failed to write %s", path)
        return None
    return path
