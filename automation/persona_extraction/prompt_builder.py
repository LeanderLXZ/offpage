"""Prompt builder — assembles context-aware prompts for each stage.

Instead of letting the agent explore and discover files on its own,
the orchestrator pre-computes exactly what the agent needs and injects
it into the prompt. This reduces cold-start time and drift risk.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .progress import StageEntry, PipelineProgress

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

_TEMPLATE_DIR = Path(__file__).parent.parent / "prompt_templates"


def _load_template(name: str) -> str:
    path = _TEMPLATE_DIR / name
    return path.read_text(encoding="utf-8")


def _render_template(template: str, context: dict[str, Any]) -> str:
    """Render a template with {key} placeholders, ignoring other braces.

    Unlike str.format(), this only substitutes keys present in *context*
    and leaves all other ``{...}`` sequences (e.g. JSON examples) untouched.
    """
    import re
    def _replace(m: re.Match) -> str:
        key = m.group(1)
        if key in context:
            return str(context[key])
        return m.group(0)  # leave as-is
    return re.sub(r"\{(\w+)\}", _replace, template)


# ---------------------------------------------------------------------------
# Analysis prompt
# ---------------------------------------------------------------------------

def build_summarization_prompt(
    project_root: Path,
    work_id: str,
    chunk_index: int,
    total_chunks: int,
    start_chapter: int,
    end_chapter: int,
    *,
    prior_error: str = "",
) -> str:
    """Build prompt for a single summarization chunk.

    Args:
        prior_error: If non-empty, an L3 retry trigger; the previous failure
            message is injected as a 重试说明 block so the LLM can correct
            JSON syntax / schema bound issues. Same shape as
            ``build_scene_split_prompt``.
    """
    template = _load_template("summarization.md")

    source_dir = project_root / "sources" / "works" / work_id
    manifest = _read_json(source_dir / "manifest.json")

    # Build chapter file list
    chapter_files = []
    for ch in range(start_chapter, end_chapter + 1):
        chapter_files.append(f"- `{source_dir}/chapters/C{ch:04d}.txt`")

    summaries_dir = (project_root / "works" / work_id
                     / "analysis" / "chapter_summaries")
    output_path = summaries_dir / f"chunk_{chunk_index:03d}.json"

    retry_note = ""
    if prior_error:
        retry_note = (
            f"\n## 重试说明\n\n"
            f"上一次尝试校验失败，错误信息如下：\n\n"
            f"```\n{prior_error}\n```\n\n"
            f"请特别注意修正以上问题。"
        )

    context = {
        "work_id": work_id,
        "title": manifest.get("title", work_id) if manifest else work_id,
        "language": manifest.get("language", "zh") if manifest else "zh",
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "start_chapter": f"C{start_chapter:04d}",
        "end_chapter": f"C{end_chapter:04d}",
        "chunk_chapter_count": end_chapter - start_chapter + 1,
        "source_dir": str(source_dir),
        "chapter_file_list": "\n".join(chapter_files),
        "output_path": str(output_path),
        "retry_note": retry_note,
    }

    return _render_template(template, context)


# ---------------------------------------------------------------------------
# Phase 1 lane fan-out — chunk projection + per-lane prompt builders
# ---------------------------------------------------------------------------
#
# Phase 1 fans out into 3 lanes (monolithic) or 2 lanes (light_novel; stage_plan
# is derived programmatically from chapter_index, no LLM call). Each lane runs
# its own claude -p with a narrow projection of the chunk JSON inputs:
#
#   - world_overview lane: chunk-level secondary fields (chunk_arc_summary +
#     chunk_world_rules + chunk_power_levels + chunk_factions WITHOUT
#     members_present + chunk_regions) + summaries[].chapter
#   - stage_plan lane: chunk_arc_summary + chunk_regions + per-summary plot
#     fields (chapter / summary / key_events / characters_present /
#     emotional_tone / identity_notes)
#   - candidate_characters lane: per-summary identity fields (chapter /
#     characters_present / identity_notes) + chunk_factions[].{name,members_present}
#
# The projected chunks are staged at
#   works/{work_id}/analysis/.phase1_lane_inputs/{lane}/chunk_NNN.json
# (gitignored; cleaned by orchestrator on run_analysis exit). The prompt
# template tells the LLM to read from that directory.

PHASE1_LANES: tuple[str, ...] = (
    "world_overview",
    "stage_plan",
    "candidate_characters",
)


def _phase1_lane_inputs_root(project_root: Path, work_id: str) -> Path:
    return (project_root / "works" / work_id / "analysis"
            / ".phase1_lane_inputs")


def _project_chunk_for_world_overview(chunk: dict) -> dict:
    """Chunk-level secondary fields only (faction members_present stripped).
    summaries[] dropped — full-book setting writeup does not depend on
    per-chapter anchors."""
    factions = []
    for fac in chunk.get("chunk_factions") or []:
        clean = {k: v for k, v in fac.items() if k != "members_present"}
        factions.append(clean)
    return {
        "work_id": chunk.get("work_id"),
        "chunk_index": chunk.get("chunk_index"),
        "chapters": chunk.get("chapters"),
        "chunk_arc_summary": chunk.get("chunk_arc_summary", ""),
        "chunk_world_rules": chunk.get("chunk_world_rules") or [],
        "chunk_power_levels": chunk.get("chunk_power_levels") or [],
        "chunk_factions": factions,
        "chunk_regions": chunk.get("chunk_regions") or [],
    }


def _project_chunk_for_stage_plan(chunk: dict) -> dict:
    """chunk_arc_summary + chunk_regions + per-summary chapter+summary only.
    key_events / characters_present / emotional_tone / identity_notes dropped —
    orthogonal to chapter-boundary plot-arc merging task; their token surface
    fed LLM thinking long-tail without informing turning-point detection."""
    return {
        "work_id": chunk.get("work_id"),
        "chunk_index": chunk.get("chunk_index"),
        "chapters": chunk.get("chapters"),
        "chunk_arc_summary": chunk.get("chunk_arc_summary", ""),
        "chunk_regions": chunk.get("chunk_regions") or [],
        "summaries": [
            {
                "chapter": s.get("chapter"),
                "summary": s.get("summary", ""),
            }
            for s in chunk.get("summaries") or []
            if s.get("chapter")
        ],
    }


def _project_chunk_for_candidates(chunk: dict) -> dict:
    """Per-summary identity-tracking fields + chunk_factions[].{name, members_present}.
    Includes summary — cross-chunk identity merging needs event context to
    surface implicit identity links (e.g. Character A is Character B's
    incarnation) beyond what short identity_notes captures."""
    factions = []
    for fac in chunk.get("chunk_factions") or []:
        factions.append({
            "name": fac.get("name", ""),
            "members_present": fac.get("members_present") or [],
        })
    return {
        "work_id": chunk.get("work_id"),
        "chunk_index": chunk.get("chunk_index"),
        "chapters": chunk.get("chapters"),
        "chunk_factions": factions,
        "summaries": [
            {
                "chapter": s.get("chapter"),
                "summary": s.get("summary", ""),
                "characters_present": s.get("characters_present") or [],
                "identity_notes": s.get("identity_notes", ""),
            }
            for s in chunk.get("summaries") or []
            if s.get("chapter")
        ],
    }


_LANE_PROJECTORS = {
    "world_overview": _project_chunk_for_world_overview,
    "stage_plan": _project_chunk_for_stage_plan,
    "candidate_characters": _project_chunk_for_candidates,
}


def prepare_phase1_lane_inputs(
    project_root: Path,
    work_id: str,
    *,
    lanes: tuple[str, ...] = PHASE1_LANES,
) -> dict[str, Path]:
    """Project every chapter_summaries/chunk_*.json into a per-lane tmpdir.

    Returns ``{lane_name: lane_inputs_dir}``. Caller is responsible for
    ``cleanup_phase1_lane_inputs`` after the lane's LLM call completes
    (run_analysis wraps both in try/finally).

    Each chunk is projected once per lane via ``_LANE_PROJECTORS``; the
    projector keeps only the fields that lane's prompt actually reads
    (decision #52 — narrow per-lane field surface keeps lane input tokens
    proportional to lane scope, not total chunk surface).
    """
    summaries_dir = (project_root / "works" / work_id
                     / "analysis" / "chapter_summaries")
    if not summaries_dir.exists():
        raise FileNotFoundError(
            f"chapter_summaries dir not found: {summaries_dir}; "
            f"phase 0 must complete before phase 1 lane fan-out")

    root = _phase1_lane_inputs_root(project_root, work_id)
    out: dict[str, Path] = {}
    for lane in lanes:
        if lane not in _LANE_PROJECTORS:
            raise ValueError(f"unknown phase 1 lane: {lane}")
        lane_dir = root / lane
        # Wipe any stale projection from a previous (interrupted) run before
        # writing — projection is deterministic, no state worth preserving.
        if lane_dir.exists():
            for f in lane_dir.iterdir():
                if f.is_file():
                    f.unlink()
        lane_dir.mkdir(parents=True, exist_ok=True)
        projector = _LANE_PROJECTORS[lane]
        for chunk_file in sorted(summaries_dir.glob("chunk_*.json")):
            try:
                chunk = json.loads(chunk_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                raise RuntimeError(
                    f"failed to read chunk for projection: "
                    f"{chunk_file} ({exc})") from exc
            projected = projector(chunk)
            (lane_dir / chunk_file.name).write_text(
                json.dumps(projected, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        out[lane] = lane_dir
    return out


def cleanup_phase1_lane_inputs(project_root: Path, work_id: str) -> None:
    """Remove the .phase1_lane_inputs tmpdir tree (idempotent)."""
    root = _phase1_lane_inputs_root(project_root, work_id)
    if not root.exists():
        return
    import shutil
    shutil.rmtree(root, ignore_errors=True)


def _phase1_retry_note(prior_error: str) -> str:
    if not prior_error:
        return ""
    return (
        f"\n## 重试说明\n\n"
        f"上一次尝试校验失败，错误信息如下：\n\n"
        f"```\n{prior_error}\n```\n\n"
        f"请特别注意修正以上问题。"
    )


def _phase1_common_context(project_root: Path, work_id: str) -> dict[str, Any]:
    source_dir = project_root / "sources" / "works" / work_id
    manifest = _read_json(source_dir / "manifest.json")
    chapter_index = _read_json(source_dir / "metadata" / "chapter_index.json")

    chapter_count = 0
    if chapter_index:
        if isinstance(chapter_index, list):
            chapter_count = len(chapter_index)
        else:
            chapter_count = len(chapter_index.get("chapters", []))

    return {
        "work_id": work_id,
        "title": manifest.get("title", work_id) if manifest else work_id,
        "language": manifest.get("language", "zh") if manifest else "zh",
        "chapter_count": chapter_count,
        "work_dir": str(project_root / "works" / work_id),
    }


def build_world_overview_prompt(
    project_root: Path,
    work_id: str,
    lane_inputs_dir: Path,
    *,
    prior_error: str = "",
) -> str:
    """Phase 1 world_overview lane prompt."""
    template = _load_template("analysis_world_overview.md")
    context = _phase1_common_context(project_root, work_id)
    context["lane_inputs_dir"] = str(lane_inputs_dir)
    context["retry_note"] = _phase1_retry_note(prior_error)
    return _render_template(template, context)


def build_stage_plan_prompt(
    project_root: Path,
    work_id: str,
    lane_inputs_dir: Path,
    *,
    prior_error: str = "",
) -> str:
    """Phase 1 stage_plan lane prompt (monolithic only — light_novel mode
    derives stage_plan programmatically and does NOT call this builder)."""
    template = _load_template("analysis_stage_plan.md")
    context = _phase1_common_context(project_root, work_id)
    context["lane_inputs_dir"] = str(lane_inputs_dir)
    context["retry_note"] = _phase1_retry_note(prior_error)
    return _render_template(template, context)


def build_candidate_characters_prompt(
    project_root: Path,
    work_id: str,
    lane_inputs_dir: Path,
    *,
    prior_error: str = "",
) -> str:
    """Phase 1 candidate_characters lane prompt."""
    template = _load_template("analysis_candidate_characters.md")
    context = _phase1_common_context(project_root, work_id)
    context["lane_inputs_dir"] = str(lane_inputs_dir)
    context["retry_note"] = _phase1_retry_note(prior_error)
    return _render_template(template, context)


# ---------------------------------------------------------------------------
# Baseline production prompt
# ---------------------------------------------------------------------------

def build_baseline_prompt(
    project_root: Path,
    work_id: str,
    target_characters: list[str],
) -> str:
    """Build prompt for baseline production (world foundation + character identity)."""
    template = _load_template("baseline_production.md")

    source_dir = project_root / "sources" / "works" / work_id
    manifest = _read_json(source_dir / "manifest.json")
    work_dir = project_root / "works" / work_id

    # Build file read list
    files: list[str] = []

    # Schemas needed — includes the two stage_catalog schemas the
    # baseline must produce empty instances of.
    for schema in ("character/identity.schema.json",
                   "character/character_manifest.schema.json",
                   "character/target_baseline.schema.json",
                   "world/fixed_relationships.schema.json",
                   "world/world_stage_catalog.schema.json",
                   "character/stage_catalog.schema.json"):
        files.append(f"- `{project_root / 'schemas' / schema}`")

    # Analysis outputs
    for name in ("world_overview.json", "candidate_characters.json",
                 "stage_plan.json"):
        p = work_dir / "analysis" / name
        if p.exists():
            files.append(f"- `{p}`")

    # Chapter summaries (for reference)
    summaries_dir = work_dir / "analysis" / "chapter_summaries"
    if summaries_dir.exists():
        for p in sorted(summaries_dir.glob("chunk_*.json")):
            files.append(f"- `{p}`")

    context = {
        "work_id": work_id,
        "title": manifest.get("title", work_id) if manifest else work_id,
        "language": manifest.get("language", "zh") if manifest else "zh",
        "target_characters": ", ".join(target_characters),
        "target_characters_list": json.dumps(
            target_characters, ensure_ascii=False),
        "work_dir": str(work_dir),
        "schemas_dir": str(project_root / "schemas"),
        "files_to_read": "\n".join(files),
    }

    return _render_template(template, context)


# ---------------------------------------------------------------------------
# 1+2N split extraction prompts
# ---------------------------------------------------------------------------

def build_world_extraction_prompt(
    project_root: Path,
    progress: PipelineProgress,
    stage: StageEntry,
    *,
    stages: list[StageEntry] | None = None,
    reviewer_feedback: str = "",
) -> str:
    """Build prompt for world extraction (parallel with char lanes in 1+2N)."""
    template = _load_template("world_extraction.md")

    work_id = progress.work_id
    work_dir = project_root / "works" / work_id
    source_dir = project_root / "sources" / "works" / work_id

    prev_stage = _find_previous_committed_stage(stages or [], stage)
    prev_world_snapshot = ""
    if prev_stage:
        ws_path = (work_dir / "world" / "stage_snapshots"
                   / f"{prev_stage.stage_id}.json")
        if ws_path.exists():
            prev_world_snapshot = str(ws_path)

    files_to_read = _build_world_read_list(
        project_root, work_id, stage, prev_stage)

    context = {
        "work_id": work_id,
        "stage_id": stage.stage_id,
        "chapters": stage.chapters,
        "chapter_range": stage.chapters,
        "target_characters": ", ".join(progress.target_characters),
        "source_dir": str(source_dir),
        "work_dir": str(work_dir),
        "schemas_dir": str(project_root / "schemas"),
        "prev_world_snapshot": prev_world_snapshot,
        "files_to_read": "\n".join(f"- {f}" for f in files_to_read),
        "is_first_stage": (
            stages is not None and len(stages) > 0
            and stage.stage_id == stages[0].stage_id),
        "reviewer_feedback": reviewer_feedback,
        "retry_note": (
            f"\n\n## 重试注意\n\n"
            f"上一次提取被 reviewer 打回，具体问题如下：\n\n"
            f"{reviewer_feedback}\n\n"
            f"请重点修复以上问题。"
        ) if reviewer_feedback else "",
    }

    return _render_template(template, context)


def build_char_snapshot_prompt(
    project_root: Path,
    progress: PipelineProgress,
    stage: StageEntry,
    character_id: str,
    *,
    stages: list[StageEntry] | None = None,
    reviewer_feedback: str = "",
) -> str:
    """Build prompt for character snapshot extraction (stage_snapshot only).

    This is the heavier of the two character sub-processes. Input includes
    the previous stage snapshot for delta calculation and style reference.
    """
    template = _load_template("character_snapshot_extraction.md")

    work_id = progress.work_id
    work_dir = project_root / "works" / work_id
    source_dir = project_root / "sources" / "works" / work_id

    prev_stage = _find_previous_committed_stage(stages or [], stage)
    files_to_read = _build_char_snapshot_read_list(
        project_root, work_id, character_id, stage, prev_stage)

    quality_requirements = _build_quality_requirements(
        project_root, work_id, progress.target_characters)

    prev_char_snapshot = ""
    if prev_stage:
        char_dir = work_dir / "characters" / character_id / "canon"
        cs_path = (char_dir / "stage_snapshots"
                   / f"{prev_stage.stage_id}.json")
        if cs_path.exists():
            prev_char_snapshot = str(cs_path)

    context = {
        "work_id": work_id,
        "stage_id": stage.stage_id,
        "chapters": stage.chapters,
        "chapter_range": stage.chapters,
        "character_id": character_id,
        "source_dir": str(source_dir),
        "work_dir": str(work_dir),
        "schemas_dir": str(project_root / "schemas"),
        "prev_char_snapshot": prev_char_snapshot,
        "files_to_read": "\n".join(f"- {f}" for f in files_to_read),
        "is_first_stage": (
            stages is not None and len(stages) > 0
            and stage.stage_id == stages[0].stage_id),
        "quality_requirements": quality_requirements,
        "reviewer_feedback": reviewer_feedback,
        "retry_note": (
            f"\n\n## 重试注意\n\n"
            f"上一次提取被 reviewer 打回，具体问题如下：\n\n"
            f"{reviewer_feedback}\n\n"
            f"请重点修复以上问题。"
        ) if reviewer_feedback else "",
    }

    return _render_template(template, context)


def build_char_support_prompt(
    project_root: Path,
    progress: PipelineProgress,
    stage: StageEntry,
    character_id: str,
    *,
    stages: list[StageEntry] | None = None,
    reviewer_feedback: str = "",
) -> str:
    """Build prompt for character support extraction (memory + baseline).

    Input does NOT include the previous stage snapshot — memory timeline
    is event-by-event subjective recording, independent of aggregate state.
    """
    template = _load_template("character_support_extraction.md")

    work_id = progress.work_id
    work_dir = project_root / "works" / work_id
    source_dir = project_root / "sources" / "works" / work_id

    prev_stage = _find_previous_committed_stage(stages or [], stage)
    files_to_read = _build_char_support_read_list(
        project_root, work_id, character_id, stage, prev_stage)

    context = {
        "work_id": work_id,
        "stage_id": stage.stage_id,
        "chapters": stage.chapters,
        "chapter_range": stage.chapters,
        "character_id": character_id,
        "source_dir": str(source_dir),
        "work_dir": str(work_dir),
        "schemas_dir": str(project_root / "schemas"),
        "files_to_read": "\n".join(f"- {f}" for f in files_to_read),
        "is_first_stage": (
            stages is not None and len(stages) > 0
            and stage.stage_id == stages[0].stage_id),
        "reviewer_feedback": reviewer_feedback,
        "retry_note": (
            f"\n\n## 重试注意\n\n"
            f"上一次提取被 reviewer 打回，具体问题如下：\n\n"
            f"{reviewer_feedback}\n\n"
            f"请重点修复以上问题。"
        ) if reviewer_feedback else "",
    }

    return _render_template(template, context)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_previous_committed_stage(
    stages: list[StageEntry], current: StageEntry
) -> StageEntry | None:
    """Find the most recent committed stage before the current one."""
    for b in reversed(stages):
        if b.stage_id == current.stage_id:
            continue
        if b.state.value == "committed":
            return b
    return None


def _build_world_read_list(
    project_root: Path,
    work_id: str,
    stage: StageEntry,
    prev_stage: StageEntry | None,
) -> list[str]:
    """Pre-compute file list for world extraction (Phase A)."""
    files: list[str] = []
    work_dir = project_root / "works" / work_id
    source_dir = project_root / "sources" / "works" / work_id

    # Schemas (world only)
    files.append("schemas/world/world_stage_snapshot.schema.json")

    # World foundation (always needed)
    foundation_dir = work_dir / "world" / "foundation"
    if foundation_dir.exists():
        for p in sorted(foundation_dir.rglob("*.json")):
            files.append(str(p.relative_to(project_root)))

    # Only the most recent world stage_snapshot (for delta calculation)
    if prev_stage:
        ws = (work_dir / "world" / "stage_snapshots"
              / f"{prev_stage.stage_id}.json")
        if ws.exists():
            files.append(str(ws.relative_to(project_root)))

    # NOTE: world stage_catalog.json removed — now programmatically maintained.

    # Source chapters for this stage
    start, end = _parse_chapter_range(stage.chapters)
    for ch in range(start, end + 1):
        ch_file = source_dir / "chapters" / f"C{ch:04d}.txt"
        if ch_file.exists():
            files.append(str(ch_file.relative_to(project_root)))

    return _deduplicate(files)


def _build_char_snapshot_read_list(
    project_root: Path,
    work_id: str,
    character_id: str,
    stage: StageEntry,
    prev_stage: StageEntry | None,
) -> list[str]:
    """Pre-compute file list for character snapshot extraction.

    Includes identity (character-level constant), previous stage_snapshot
    (for delta/style), and source chapters. Does NOT include memory_timeline.
    """
    files: list[str] = []
    work_dir = project_root / "works" / work_id
    source_dir = project_root / "sources" / "works" / work_id
    char_dir = work_dir / "characters" / character_id / "canon"

    files.append("schemas/character/stage_snapshot.schema.json")

    # identity.json — character-level constant, also used for alias cross-ref
    if char_dir.exists():
        identity = char_dir / "identity.json"
        if identity.exists():
            files.append(str(identity.relative_to(project_root)))

    # Previous stage_snapshot for delta calculation and style reference
    if prev_stage and char_dir.exists():
        cs = char_dir / "stage_snapshots" / f"{prev_stage.stage_id}.json"
        if cs.exists():
            files.append(str(cs.relative_to(project_root)))

    # Source chapters
    start, end = _parse_chapter_range(stage.chapters)
    for ch in range(start, end + 1):
        ch_file = source_dir / "chapters" / f"C{ch:04d}.txt"
        if ch_file.exists():
            files.append(str(ch_file.relative_to(project_root)))

    return _deduplicate(files)


def _build_char_support_read_list(
    project_root: Path,
    work_id: str,
    character_id: str,
    stage: StageEntry,
    prev_stage: StageEntry | None,
) -> list[str]:
    """Pre-compute file list for character support extraction.

    Includes identity (character-level constant), previous memory_timeline
    (for continuation), and source chapters. Does NOT include stage_snapshot.
    """
    files: list[str] = []
    work_dir = project_root / "works" / work_id
    source_dir = project_root / "sources" / "works" / work_id
    char_dir = work_dir / "characters" / character_id / "canon"

    files.append("schemas/character/memory_timeline_entry.schema.json")

    # identity.json — character-level constant, also used for alias cross-ref
    if char_dir.exists():
        identity = char_dir / "identity.json"
        if identity.exists():
            files.append(str(identity.relative_to(project_root)))

    # Previous memory_timeline for continuation
    if prev_stage and char_dir.exists():
        mt = char_dir / "memory_timeline" / f"{prev_stage.stage_id}.json"
        if mt.exists():
            files.append(str(mt.relative_to(project_root)))

    # Source chapters
    start, end = _parse_chapter_range(stage.chapters)
    for ch in range(start, end + 1):
        ch_file = source_dir / "chapters" / f"C{ch:04d}.txt"
        if ch_file.exists():
            files.append(str(ch_file.relative_to(project_root)))

    return _deduplicate(files)


def _build_character_read_list(
    project_root: Path,
    work_id: str,
    character_id: str,
    stage: StageEntry,
    prev_stage: StageEntry | None,
) -> list[str]:
    """Legacy: combined read list for single-character extraction.

    Kept for backward compatibility with coordinated extraction prompt.
    """
    files = _build_char_snapshot_read_list(
        project_root, work_id, character_id, stage, prev_stage)
    files.extend(_build_char_support_read_list(
        project_root, work_id, character_id, stage, prev_stage))
    return _deduplicate(files)


def _deduplicate(files: list[str]) -> list[str]:
    """Deduplicate file list while preserving order."""
    seen: set[str] = set()
    unique: list[str] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique


def _parse_chapter_range(chapters: str) -> tuple[int, int]:
    """Parse 'C0001-C0010' into (1, 10)."""
    parts = chapters.split("-")
    if len(parts) == 2:
        return int(parts[0].lstrip("C")), int(parts[1].lstrip("C"))
    return int(parts[0].lstrip("C")), int(parts[0].lstrip("C"))


def _chunk_covers_range(chunk_path: Path, stage_start: int,
                        stage_end: int) -> bool:
    """Check if a chunk summary file covers any chapters in the stage range.

    Chunk files are named like chunk_0001_0025.json (start_end chapters).
    """
    stem = chunk_path.stem  # e.g. "chunk_0001_0025"
    parts = stem.split("_")
    if len(parts) >= 3:
        try:
            chunk_start = int(parts[1])
            chunk_end = int(parts[2])
            # Overlap check
            return chunk_start <= stage_end and chunk_end >= stage_start
        except ValueError:
            pass
    # If we can't parse, include it as fallback
    return True


# ---------------------------------------------------------------------------
# Scene split prompt (Phase 4)
# ---------------------------------------------------------------------------

def build_scene_split_prompt(
    project_root: Path,
    work_id: str,
    chapter_id: str,
    lines: list[str],
    *,
    prior_error: str = "",
) -> str:
    """Build prompt for scene splitting of a single chapter."""
    template = _load_template("scene_split.md")

    # Build numbered text
    numbered = "\n".join(f"{i + 1}\t{line}" for i, line in enumerate(lines))

    retry_note = ""
    if prior_error:
        retry_note = (
            f"\n## 重试说明\n\n"
            f"上一次尝试校验失败，错误信息如下：\n\n"
            f"```\n{prior_error}\n```\n\n"
            f"请特别注意修正以上问题。"
        )

    context = {
        "work_id": work_id,
        "chapter_id": chapter_id,
        "chapter_text": numbered,
        "retry_note": retry_note,
    }

    return _render_template(template, context)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IMPORTANCE_THRESHOLDS = {"主角": 5, "重要配角": 3}


def _build_quality_requirements(
    project_root: Path,
    work_id: str,
    target_characters: list[str],
) -> str:
    """Build a markdown table of per-target min examples from importance."""
    candidates_path = (project_root / "works" / work_id / "analysis"
                       / "candidate_characters.json")
    candidates = _read_json(candidates_path)
    if not candidates:
        return ("| target | importance | 最低 examples |\n"
                "|--------|-----------|---------------|\n"
                "| （未找到 candidate_characters.json，默认全部 ≥3） "
                "| — | 3 |")

    # Build {character_id: importance}
    importance_map: dict[str, str] = {}
    for c in candidates.get("candidates", []):
        cid = c.get("character_id", "")
        if cid:
            importance_map[cid] = c.get("importance", "")

    lines = [
        "| target | importance | 最低 examples |",
        "|--------|-----------|---------------|",
    ]
    for char_id in target_characters:
        imp = importance_map.get(char_id, "")
        min_ex = _IMPORTANCE_THRESHOLDS.get(imp, 1)
        lines.append(f"| {char_id} | {imp or '—'} | {min_ex} |")

    # Also list other known important characters not in target set
    for cid, imp in importance_map.items():
        if cid not in target_characters and imp in _IMPORTANCE_THRESHOLDS:
            min_ex = _IMPORTANCE_THRESHOLDS[imp]
            lines.append(f"| {cid} | {imp} | {min_ex} |")

    lines.append("| 其他泛化类型 | — | 1 |")
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
