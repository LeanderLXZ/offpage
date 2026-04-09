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
) -> str:
    """Build prompt for a single summarization chunk."""
    template = _load_template("summarization.md")

    source_dir = project_root / "sources" / "works" / work_id
    manifest = _read_json(source_dir / "manifest.json")

    # Build chapter file list
    chapter_files = []
    for ch in range(start_chapter, end_chapter + 1):
        chapter_files.append(f"- `{source_dir}/chapters/{ch:04d}.txt`")

    summaries_dir = (project_root / "works" / work_id
                     / "analysis" / "incremental" / "chapter_summaries")
    output_path = summaries_dir / f"chunk_{chunk_index:03d}.json"

    context = {
        "work_id": work_id,
        "title": manifest.get("title", work_id) if manifest else work_id,
        "language": manifest.get("language", "zh") if manifest else "zh",
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "start_chapter": f"{start_chapter:04d}",
        "end_chapter": f"{end_chapter:04d}",
        "chunk_chapter_count": end_chapter - start_chapter + 1,
        "source_dir": str(source_dir),
        "chapter_file_list": "\n".join(chapter_files),
        "output_path": str(output_path),
    }

    return _render_template(template, context)


def build_analysis_prompt(project_root: Path, work_id: str) -> str:
    """Build prompt for the analysis phase (from summaries → batch plan + candidates)."""
    template = _load_template("analysis.md")

    # Gather context
    source_dir = project_root / "sources" / "works" / work_id
    manifest = _read_json(source_dir / "manifest.json")
    chapter_index = _read_json(source_dir / "metadata" / "chapter_index.json")

    chapter_count = 0
    if chapter_index:
        if isinstance(chapter_index, list):
            chapter_count = len(chapter_index)
        else:
            chapter_count = len(chapter_index.get("chapters", []))

    summaries_dir = (project_root / "works" / work_id
                     / "analysis" / "incremental" / "chapter_summaries")

    context = {
        "work_id": work_id,
        "title": manifest.get("title", work_id) if manifest else work_id,
        "language": manifest.get("language", "zh") if manifest else "zh",
        "chapter_count": chapter_count,
        "work_dir": str(project_root / "works" / work_id),
        "summaries_dir": str(summaries_dir),
    }

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

    # Schemas needed
    for schema in ("identity.schema.json", "character_manifest.schema.json"):
        files.append(f"- `{project_root / 'schemas' / schema}`")

    # Analysis outputs
    for name in ("world_overview.json", "candidate_characters.json",
                 "source_batch_plan.json"):
        p = work_dir / "analysis" / "incremental" / name
        if p.exists():
            files.append(f"- `{p}`")

    # Chapter summaries (for reference)
    summaries_dir = work_dir / "analysis" / "incremental" / "chapter_summaries"
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
# Coordinated extraction prompt (LEGACY — kept for backward compatibility;
# orchestrator now uses build_world_extraction_prompt + build_character_extraction_prompt)
# ---------------------------------------------------------------------------

def build_extraction_prompt(
    project_root: Path,
    progress: ExtractionProgress,
    batch: BatchEntry,
    *,
    reviewer_feedback: str = "",
) -> str:
    """Legacy: build prompt for coordinated world + character extraction.

    No longer called by the orchestrator (replaced by 1+N split), but kept
    because the reviewer and targeted-fix prompts still reference
    ``_build_read_list`` which delegates here.
    """
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

    return _render_template(template, context)


# ---------------------------------------------------------------------------
# 1+N split extraction prompts
# ---------------------------------------------------------------------------

def build_world_extraction_prompt(
    project_root: Path,
    progress: ExtractionProgress,
    batch: BatchEntry,
    *,
    reviewer_feedback: str = "",
) -> str:
    """Build prompt for world-only extraction (Phase A of 1+N)."""
    template = _load_template("world_extraction.md")

    work_id = progress.work_id
    work_dir = project_root / "works" / work_id
    source_dir = project_root / "sources" / "works" / work_id

    prev_batch = _find_previous_committed_batch(progress, batch)
    prev_world_snapshot = ""
    if prev_batch:
        ws_path = (work_dir / "world" / "stage_snapshots"
                   / f"{prev_batch.stage_id}.json")
        if ws_path.exists():
            prev_world_snapshot = str(ws_path)

    files_to_read = _build_world_read_list(
        project_root, work_id, batch, prev_batch)

    context = {
        "work_id": work_id,
        "batch_id": batch.batch_id,
        "stage_id": batch.stage_id,
        "chapters": batch.chapters,
        "chapter_range": batch.chapters,
        "target_characters": ", ".join(progress.target_characters),
        "source_dir": str(source_dir),
        "work_dir": str(work_dir),
        "schemas_dir": str(project_root / "schemas"),
        "prev_world_snapshot": prev_world_snapshot,
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

    return _render_template(template, context)


def build_character_extraction_prompt(
    project_root: Path,
    progress: ExtractionProgress,
    batch: BatchEntry,
    character_id: str,
    *,
    world_snapshot_path: str = "",
    reviewer_feedback: str = "",
) -> str:
    """Build prompt for single-character extraction (Phase B of 1+N)."""
    template = _load_template("character_extraction.md")

    work_id = progress.work_id
    work_dir = project_root / "works" / work_id
    source_dir = project_root / "sources" / "works" / work_id
    char_dir = work_dir / "characters" / character_id / "canon"

    prev_batch = _find_previous_committed_batch(progress, batch)
    prev_char_snapshot = ""
    if prev_batch:
        cs_path = (char_dir / "stage_snapshots"
                   / f"{prev_batch.stage_id}.json")
        if cs_path.exists():
            prev_char_snapshot = str(cs_path)

    files_to_read = _build_character_read_list(
        project_root, work_id, character_id, batch, prev_batch,
        world_snapshot_path)

    context = {
        "work_id": work_id,
        "batch_id": batch.batch_id,
        "stage_id": batch.stage_id,
        "chapters": batch.chapters,
        "chapter_range": batch.chapters,
        "character_id": character_id,
        "source_dir": str(source_dir),
        "work_dir": str(work_dir),
        "schemas_dir": str(project_root / "schemas"),
        "world_snapshot_path": world_snapshot_path,
        "prev_char_snapshot": prev_char_snapshot,
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

    return _render_template(template, context)


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

    return _render_template(template, context)


# ---------------------------------------------------------------------------
# Targeted fix prompt
# ---------------------------------------------------------------------------

def build_targeted_fix_prompt(
    project_root: Path,
    progress: ExtractionProgress,
    batch: BatchEntry,
    findings: str,
) -> str:
    """Build prompt for targeted fix of specific reviewer findings."""
    template = _load_template("targeted_fix.md")

    work_id = progress.work_id
    work_dir = project_root / "works" / work_id
    source_dir = project_root / "sources" / "works" / work_id

    # Collect affected output files (current batch's products)
    affected: list[str] = []
    # World snapshot
    ws = work_dir / "world" / "stage_snapshots" / f"{batch.stage_id}.json"
    if ws.exists():
        affected.append(f"- `{ws.relative_to(project_root)}`")
    # Character files
    for char_id in progress.target_characters:
        char_dir = work_dir / "characters" / char_id / "canon"
        cs = char_dir / "stage_snapshots" / f"{batch.stage_id}.json"
        if cs.exists():
            affected.append(f"- `{cs.relative_to(project_root)}`")
        mt = char_dir / "memory_timeline" / f"{batch.stage_id}.json"
        if mt.exists():
            affected.append(f"- `{mt.relative_to(project_root)}`")
        md = char_dir / "memory_digest.jsonl"
        if md.exists():
            affected.append(f"- `{md.relative_to(project_root)}`")

    # Evidence: source chapters for this batch
    evidence: list[str] = []
    start, end = _parse_chapter_range(batch.chapters)
    for ch in range(start, end + 1):
        ch_file = source_dir / "chapters" / f"{ch:04d}.txt"
        if ch_file.exists():
            evidence.append(f"- `{ch_file.relative_to(project_root)}`")

    # Also include chapter summaries as lighter evidence
    summaries_dir = (work_dir / "analysis" / "incremental"
                     / "chapter_summaries")
    if summaries_dir.exists():
        for p in sorted(summaries_dir.glob("chunk_*.json")):
            evidence.append(f"- `{p.relative_to(project_root)}`")

    context = {
        "work_id": work_id,
        "batch_id": batch.batch_id,
        "stage_id": batch.stage_id,
        "chapters": batch.chapters,
        "findings": findings,
        "affected_files": "\n".join(affected) if affected else "(无)",
        "evidence_files": "\n".join(evidence) if evidence else "(无)",
    }

    return _render_template(template, context)


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


def _build_world_read_list(
    project_root: Path,
    work_id: str,
    batch: BatchEntry,
    prev_batch: BatchEntry | None,
) -> list[str]:
    """Pre-compute file list for world extraction (Phase A)."""
    files: list[str] = []
    work_dir = project_root / "works" / work_id
    source_dir = project_root / "sources" / "works" / work_id

    # Schemas (world only)
    files.append("schemas/world_stage_snapshot.schema.json")

    # World foundation (always needed)
    foundation_dir = work_dir / "world" / "foundation"
    if foundation_dir.exists():
        for p in sorted(foundation_dir.rglob("*.json")):
            files.append(str(p.relative_to(project_root)))

    # Only the most recent world stage_snapshot (for delta calculation)
    if prev_batch:
        ws = (work_dir / "world" / "stage_snapshots"
              / f"{prev_batch.stage_id}.json")
        if ws.exists():
            files.append(str(ws.relative_to(project_root)))

    # World stage_catalog (to append)
    catalog = work_dir / "world" / "stage_catalog.json"
    if catalog.exists():
        files.append(str(catalog.relative_to(project_root)))

    # Source chapters for this batch
    start, end = _parse_chapter_range(batch.chapters)
    for ch in range(start, end + 1):
        ch_file = source_dir / "chapters" / f"{ch:04d}.txt"
        if ch_file.exists():
            files.append(str(ch_file.relative_to(project_root)))

    return _deduplicate(files)


def _build_character_read_list(
    project_root: Path,
    work_id: str,
    character_id: str,
    batch: BatchEntry,
    prev_batch: BatchEntry | None,
    world_snapshot_path: str | None = None,
) -> list[str]:
    """Pre-compute file list for single-character extraction (Phase B)."""
    files: list[str] = []
    work_dir = project_root / "works" / work_id
    source_dir = project_root / "sources" / "works" / work_id
    char_dir = work_dir / "characters" / character_id / "canon"

    # Schemas (character only)
    for schema in ("stage_snapshot.schema.json",
                   "memory_timeline_entry.schema.json",
                   "memory_digest_entry.schema.json"):
        files.append(f"schemas/{schema}")

    # Architecture reference
    files.append("simulation/contracts/baseline_merge.md")

    # World snapshot just generated by Phase A
    if world_snapshot_path:
        files.append(world_snapshot_path)

    # Character baseline files (identity.json first for alias cross-ref)
    if char_dir.exists():
        identity = char_dir / "identity.json"
        if identity.exists():
            files.append(str(identity.relative_to(project_root)))
        # Other baseline files (not stage_snapshots/ or memory_timeline/)
        for name in ("voice_rules.json", "behavior_rules.json",
                     "boundaries.json", "failure_modes.json",
                     "manifest.json"):
            p = char_dir / name
            if p.exists():
                files.append(str(p.relative_to(project_root)))

    # Only the most recent stage_snapshot (for delta and style reference)
    if prev_batch and char_dir.exists():
        cs = char_dir / "stage_snapshots" / f"{prev_batch.stage_id}.json"
        if cs.exists():
            files.append(str(cs.relative_to(project_root)))

    # Only the most recent memory_timeline (for continuation)
    if prev_batch and char_dir.exists():
        mt = char_dir / "memory_timeline" / f"{prev_batch.stage_id}.json"
        if mt.exists():
            files.append(str(mt.relative_to(project_root)))

    # memory_digest.jsonl (append target, need to see existing)
    if char_dir.exists():
        md = char_dir / "memory_digest.jsonl"
        if md.exists():
            files.append(str(md.relative_to(project_root)))

    # stage_catalog (to append)
    if char_dir.exists():
        sc = char_dir / "stage_catalog.json"
        if sc.exists():
            files.append(str(sc.relative_to(project_root)))

    # Source chapters for this batch (after baselines so agent knows aliases)
    start, end = _parse_chapter_range(batch.chapters)
    for ch in range(start, end + 1):
        ch_file = source_dir / "chapters" / f"{ch:04d}.txt"
        if ch_file.exists():
            files.append(str(ch_file.relative_to(project_root)))

    return _deduplicate(files)


def _build_read_list(
    project_root: Path,
    work_id: str,
    character_ids: list[str],
    batch: BatchEntry,
    prev_batch: BatchEntry | None,
) -> list[str]:
    """Legacy: combined read list for coordinated extraction (kept for
    backward compatibility with reviewer/targeted-fix prompts)."""
    # Merge world + all character lists
    files = _build_world_read_list(
        project_root, work_id, batch, prev_batch)
    for char_id in character_ids:
        files.extend(_build_character_read_list(
            project_root, work_id, char_id, batch, prev_batch))
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
    """Parse '0001-0010' into (1, 10)."""
    parts = chapters.split("-")
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    return int(parts[0]), int(parts[0])


# ---------------------------------------------------------------------------
# Scene split prompt (Phase 4)
# ---------------------------------------------------------------------------

def build_scene_split_prompt(
    project_root: Path,
    work_id: str,
    chapter_id: str,
    lines: list[str],
) -> str:
    """Build prompt for scene splitting of a single chapter."""
    template = _load_template("scene_split.md")

    # Build numbered text
    numbered = "\n".join(f"{i + 1}\t{line}" for i, line in enumerate(lines))

    context = {
        "work_id": work_id,
        "chapter_id": chapter_id,
        "chapter_text": numbered,
    }

    return _render_template(template, context)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
