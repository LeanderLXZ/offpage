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
#   - foundation lane: chunk-level secondary fields (chunk_arc_summary +
#     chunk_world_rules + chunk_power_levels + chunk_factions INCLUDING
#     members_present + chunk_regions). summaries[] dropped — full-book
#     setting writeup does not depend on per-chapter anchors. Output:
#     `works/{work_id}/world/foundation/foundation.json`; schema:
#     `schemas/world/foundation.schema.json`. `major_factions[].key_figures`
#     IS produced by this lane as raw names — chunk_factions[].members_present[]
#     是 chunk-LLM 视野下的角色 raw 名（化名 / 真名 / 称呼任一），foundation
#     lane 跨 chunk 合并去重直接写入 key_figures 不做身份合并。phase 2 baseline
#     LLM 后续 lookup candidate_characters.aliases 把能匹配的 raw 名替换为
#     character_id，匹配不上保留 raw 名 — 双阶段语义，详见决策 #54。
#   - stage_plan lane: chunk_arc_summary + chunk_regions + per-summary
#     chapter + summary only (the 150-200 CJK-char summary now carries the
#     turning-point text signal directly; characters_present / emotional_tone
#     / identity_notes are orthogonal to plot-arc merging and dropped)
#   - candidate_characters lane: per-summary chapter + summary +
#     characters_present + identity_notes + chunk_factions[].{name,members_present}
#
# The projected chunks are staged at
#   works/{work_id}/analysis/.phase1_lane_inputs/{lane}/chunk_NNN.json
# (gitignored; cleaned by orchestrator on run_analysis exit). The prompt
# template tells the LLM to read from that directory.

PHASE1_LANES: tuple[str, ...] = (
    "foundation",
    "stage_plan",
    "candidate_characters",
)


def _phase1_lane_inputs_root(project_root: Path, work_id: str) -> Path:
    return (project_root / "works" / work_id / "analysis"
            / ".phase1_lane_inputs")


def _project_chunk_for_foundation(chunk: dict) -> dict:
    """Chunk-level secondary fields only (INCLUDING faction members_present).
    summaries[] dropped — full-book setting writeup does not depend on
    per-chapter anchors.

    Decision #54 修订段：foundation lane writes `major_factions[].key_figures`
    as raw names (chunk_factions[].members_present[] 跨 chunk 合并去重)。
    Phase 2 baseline LLM 后续替换能匹配 candidate_characters.aliases 的
    raw 名为 character_id，匹配不上保留 raw 名。所以 foundation lane 需要
    members_present 字段透传——不再 strip。
    """
    factions = []
    for fac in chunk.get("chunk_factions") or []:
        factions.append({
            "name": fac.get("name", ""),
            "description": fac.get("description", ""),
            "members_present": fac.get("members_present") or [],
        })
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
    characters_present / emotional_tone / identity_notes dropped —
    orthogonal to chapter-boundary plot-arc merging task; their token surface
    fed LLM thinking long-tail without informing turning-point detection.
    The 150-200 CJK-char `summary` now carries the turning-point text signal
    directly (decision #53 — original key_events field deleted from chunk
    schema)."""
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
    "foundation": _project_chunk_for_foundation,
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


def build_foundation_prompt(
    project_root: Path,
    work_id: str,
    lane_inputs_dir: Path,
    *,
    prior_error: str = "",
) -> str:
    """Phase 1 foundation lane prompt (decision #54). Output:
    `world/foundation/foundation.json`. Schema:
    `schemas/world/foundation.schema.json`.
    """
    template = _load_template("analysis_foundation.md")
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
    """Build prompt for phase 2 baseline production (decision #54 — phase 2
    缩水到 5 件：foundation.major_factions[].key_figures 补齐 +
    fixed_relationships + identity + target_baseline + manifest + 空
    stage_catalog；foundation 主体由 phase 1 foundation lane 直接产出，
    phase 2 不再二次综合)."""
    template = _load_template("baseline_production.md")

    source_dir = project_root / "sources" / "works" / work_id
    manifest = _read_json(source_dir / "manifest.json")
    work_dir = project_root / "works" / work_id

    # Build file read list
    files: list[str] = []

    # Schemas needed — includes the two stage_catalog schemas the
    # baseline must produce empty instances of, plus foundation schema
    # (decision #54 — phase 2 reads foundation.json to补齐 key_figures).
    for schema in ("character/identity.schema.json",
                   "character/character_manifest.schema.json",
                   "character/target_baseline.schema.json",
                   "world/foundation.schema.json",
                   "world/fixed_relationships.schema.json",
                   "world/world_stage_catalog.schema.json",
                   "character/stage_catalog.schema.json"):
        files.append(f"- `{project_root / 'schemas' / schema}`")

    # Phase 1 foundation lane output (decision #54 — foundation.json is now
    # produced by phase 1 foundation lane at world/foundation/foundation.json;
    # phase 2 reads it to补齐 major_factions[].key_figures via a separate LLM
    # call within this same baseline_production run).
    foundation_path = work_dir / "world" / "foundation" / "foundation.json"
    if foundation_path.exists():
        files.append(f"- `{foundation_path}`")

    # Other phase 1 analysis outputs
    for name in ("candidate_characters.json", "stage_plan.json"):
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
        "summaries_dir": str(summaries_dir),
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
    lane_scope: str = "ALL",
) -> str:
    """Build prompt for character snapshot extraction (stage_snapshot only).

    This is the heavier of the two character sub-processes. Input includes
    the previous stage snapshot for delta calculation and style reference.

    ``lane_scope`` selects which slice of the stage_snapshot the LLM
    writes — decision #55 ``char_snapshot`` sub-lane fan-out. ``ALL``
    (the legacy / fallback single-lane behaviour) makes the LLM write
    every field; ``char_expression`` / ``char_decision`` /
    ``char_cognition`` restrict output to the assigned field subset via
    the ``{lane_scope}`` placeholder + ``{lane_field_whitelist}``
    rendered table. The field allocation lives in
    ``snapshot_merge.FIELD_ALLOCATION`` — never duplicate it here.
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

    lane_scope_block, lane_field_whitelist = _render_lane_scope_block(
        lane_scope)

    if lane_scope == "ALL":
        output_relative_path = (
            f"works/{work_id}/characters/{character_id}/canon/"
            f"stage_snapshots/{stage.stage_id}.json"
        )
    else:
        output_relative_path = (
            f"works/{work_id}/characters/{character_id}/canon/"
            f"stage_snapshots/.partial/{stage.stage_id}_{lane_scope}.json"
        )

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
        "lane_scope": lane_scope,
        "lane_scope_block": lane_scope_block,
        "lane_field_whitelist": lane_field_whitelist,
        "output_relative_path": output_relative_path,
    }

    return _render_template(template, context)


def _render_lane_scope_block(lane_scope: str) -> tuple[str, str]:
    """Build the per-sub-lane "本次仅写以下字段" instruction block +
    whitelist table for the prompt template (decision #55).

    Returns ``(lane_scope_block, lane_field_whitelist)``. ``ALL`` mode
    returns an empty block + empty whitelist so the prompt template's
    full-field guidance applies unchanged (single-lane fallback).
    """
    if lane_scope == "ALL":
        return "", ""

    from .snapshot_merge import (
        FIELD_ALLOCATION, SHARED_KEY_SUBKEYS, SUB_LANE_NAMES,
    )
    if lane_scope not in SUB_LANE_NAMES:
        raise ValueError(
            f"invalid lane_scope {lane_scope!r}; expected one of "
            f"{('ALL',) + SUB_LANE_NAMES}")

    top_keys = FIELD_ALLOCATION[lane_scope]
    whitelist_rows = ["| 顶层字段 | 子键限定 |", "|---|---|"]
    for top_key in top_keys:
        if top_key in SHARED_KEY_SUBKEYS:
            subkeys = SHARED_KEY_SUBKEYS[top_key].get(lane_scope, ())
            sub_list = ", ".join(f"`{k}`" for k in subkeys)
            whitelist_rows.append(f"| `{top_key}` | 仅 {sub_list} |")
        else:
            whitelist_rows.append(f"| `{top_key}` | 整个对象 |")
    whitelist = "\n".join(whitelist_rows)

    block = (
        "\n\n## Sub-lane 字段范围（hard gate）\n\n"
        f"本次调用为 sub-lane 模式（`lane_scope = {lane_scope}`，"
        "决策 #55）。**只允许写下表列出的顶层字段 / 子键**——多写、少写、"
        "或写到其他 sub-lane 的字段，merge 阶段都会直接 hard fail，整个 "
        "char_snapshot lane 重跑。\n\n"
        f"{whitelist}\n\n"
        "**程序注入字段（不要写）**：`schema_version` / `work_id` / "
        "`character_id` / `stage_id` / `stage_title` / `timeline_anchor` "
        "/ `chapter_scope` 由 orchestrator 在 merge 后注入，不要在本次输出"
        "里出现。\n\n"
        "**`failure_modes` / `stage_delta` 子键划分**：这两个顶层字段被"
        "拆给两个 sub-lane 分别写不同子键；只允许写本 sub-lane 分到的子键"
        "（见上表"
        "「子键限定」列），其他子键留给另一 sub-lane。`stage_delta` 整段"
        "可省略（S001 无 prev 时合理），但若写则必须写齐分配到的全部子键。\n\n"
        "**§核心规则 / §maxItems 段照常适用**——本 sub-lane 字段范围与字段"
        "内部裁剪 / 三态规则正交，下文给出的规则不因 sub-lane 而改变。\n"
    )
    return block, whitelist


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

    Includes the stage_snapshot schema, identity (character-level
    constant), target_baseline (anchor for the D4 set-equal rule —
    decision #13; the three target-keyed structures must match its
    ``targets[].target_character_id`` set), the previous stage_snapshot
    (for delta / style), and source chapters. Does NOT include
    memory_timeline. Sub-lane mode (decision #55) inherits the same
    read list — every sub-lane needs to see the baseline target set to
    fill its slice of the three target structures.
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

    # target_baseline.json — D4 anchor (decision #13). The three target-
    # keyed structures (voice_state.target_voice_map /
    # behavior_state.target_behavior_map / relationships) must match its
    # targets[].target_character_id set; LLM needs to see it to fill the
    # keys correctly by construction.
    if char_dir.exists():
        baseline = char_dir / "target_baseline.json"
        if baseline.exists():
            files.append(str(baseline.relative_to(project_root)))

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
