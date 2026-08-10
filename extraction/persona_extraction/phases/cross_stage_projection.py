"""Thin cross-stage projections for the Phase 3.5 continuity review.

Phase 3's semantic review reads one stage file at a time, so no LLM in the
pipeline has ever seen a character's stages *side by side*. That blind spot
hides exactly the failures that matter most in a long-running roleplay
asset: an arc that contradicts itself, a cultivation realm that goes
backwards, a relationship number that jumps without a driving event,
knowledge the character "forgets" it already learned.

Feeding 53 full snapshots to an LLM to find those would be enormous and
mostly wasted — the answer lives in a handful of fields per stage. So this
module projects each stage down to just the continuity-bearing fields and
concatenates them into one compact timeline document per subject.

The projection is deliberately lossy and deliberately code-only (zero
tokens): what it drops (voice examples, behaviour examples, boundary text,
failure modes) cannot produce a cross-stage contradiction on its own, and
what it keeps is enough to *locate* one. The reviewer reports a
``stage_id`` + ``json_path``; the fix pass then reads the real file.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Relationship fields that carry a comparable across-stage signal. Prose
# fields (summary / history) are excluded on purpose: they are long and a
# drift in them is not by itself a continuity break.
_REL_SIGNAL_FIELDS = ("attitude", "trust", "intimacy", "guardedness")


@dataclass
class ProjectionDoc:
    """One subject's timeline document, ready to hand to a reviewer."""
    subject: str          # character_id, or "world"
    kind: str             # "character" | "world"
    blocks: list[tuple[str, str]]   # [(stage_id, rendered block), ...]
    skipped_stages: list[str]
    window_label: str = ""          # set on windowed slices

    @property
    def text(self) -> str:
        return "\n".join(b for _, b in self.blocks)

    @property
    def stage_count(self) -> int:
        return len(self.blocks)

    @property
    def char_len(self) -> int:
        return len(self.text)

    @property
    def stage_span(self) -> str:
        if not self.blocks:
            return ""
        return f"{self.blocks[0][0]}–{self.blocks[-1][0]}"


def split_windows(
    doc: ProjectionDoc,
    max_chars: int,
    overlap_stages: int = 1,
) -> list[ProjectionDoc]:
    """Slice a projection into windows that fit ``max_chars``.

    A whole-work timeline can run into the hundreds of thousands of
    characters, and handing that to one call trades away the reviewer's
    ability to actually notice a local break. Windows restore that, at the
    cost of long-range comparisons across a window boundary.

    ``overlap_stages`` re-includes the tail of the previous window so a
    break *at* a boundary — the adjacent-stage case, which is the dominant
    failure mode — is still visible to at least one window.

    A single stage larger than ``max_chars`` gets its own window rather
    than being dropped or split mid-block: an oversized stage is still
    reviewable, a truncated one is not.
    """
    if doc.char_len <= max_chars or not doc.blocks:
        return [doc]

    windows: list[ProjectionDoc] = []
    current: list[tuple[str, str]] = []
    size = 0

    for block in doc.blocks:
        block_len = len(block[1]) + 1
        if current and size + block_len > max_chars:
            windows.append(_window_from(doc, current, len(windows) + 1))
            current = current[-overlap_stages:] if overlap_stages else []
            size = sum(len(b[1]) + 1 for b in current)
        current.append(block)
        size += block_len

    if current:
        windows.append(_window_from(doc, current, len(windows) + 1))

    total = len(windows)
    for w in windows:
        w.window_label = f"{w.window_label}/{total}"
    return windows


def _window_from(
    doc: ProjectionDoc, blocks: list[tuple[str, str]], index: int,
) -> ProjectionDoc:
    return ProjectionDoc(
        subject=doc.subject,
        kind=doc.kind,
        blocks=list(blocks),
        skipped_stages=[],
        window_label=str(index),
    )


def build_character_projection(
    work_dir: Path,
    character_id: str,
    stage_ids: list[str],
    *,
    include_knowledge: bool = True,
) -> ProjectionDoc:
    """Project one character's stage snapshots into a timeline document.

    ``include_knowledge`` adds the knowledge-scope lists, which is what
    makes "knew it in stage N, does not know it in stage N+1" detectable.
    It is the single largest contributor to document size, hence the switch.
    """
    blocks: list[tuple[str, str]] = []
    skipped: list[str] = []

    for stage_id in stage_ids:
        path = (work_dir / "characters" / character_id / "canon"
                / "stage_snapshots" / f"{stage_id}.json")
        snap = _load_json(path)
        if snap is None:
            skipped.append(stage_id)
            continue
        blocks.append((stage_id, _render_character_stage(
            snap, stage_id, include_knowledge=include_knowledge)))

    return ProjectionDoc(
        subject=character_id,
        kind="character",
        blocks=blocks,
        skipped_stages=skipped,
    )


def build_world_projection(
    work_dir: Path, stage_ids: list[str],
) -> ProjectionDoc:
    """Project the world stage snapshots into a timeline document."""
    blocks: list[tuple[str, str]] = []
    skipped: list[str] = []

    for stage_id in stage_ids:
        path = work_dir / "world" / "stage_snapshots" / f"{stage_id}.json"
        snap = _load_json(path)
        if snap is None:
            skipped.append(stage_id)
            continue
        blocks.append((stage_id, _render_world_stage(snap, stage_id)))

    return ProjectionDoc(
        subject="world",
        kind="world",
        blocks=blocks,
        skipped_stages=skipped,
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _render_character_stage(
    snap: dict, stage_id: str, *, include_knowledge: bool,
) -> str:
    """Render one stage as a labelled block.

    Every line carries the ``json_path`` its content came from, so a
    reviewer can anchor a finding precisely without guessing at the schema.
    """
    lines = [
        f"### {stage_id} — {snap.get('stage_title', '')}",
        f"timeline_anchor: {snap.get('timeline_anchor', '')}",
    ]

    arc = snap.get("character_arc")
    if arc:
        lines.append(f"$.character_arc: {arc}")

    summary = snap.get("snapshot_summary")
    if summary:
        lines.append(f"$.snapshot_summary: {summary}")

    lines.extend(_render_list_field(snap, "current_status"))

    delta = snap.get("stage_delta") or {}
    if isinstance(delta, dict):
        for key in ("status_changes", "trigger_events",
                    "personality_changes", "relationship_changes"):
            lines.extend(_render_list_field(
                delta, key, prefix=f"$.stage_delta.{key}"))

    baseline = snap.get("emotional_baseline") or {}
    if isinstance(baseline, dict):
        for key in ("active_goals", "active_obsessions"):
            lines.extend(_render_list_field(
                baseline, key, prefix=f"$.emotional_baseline.{key}"))

    rels = snap.get("relationships")
    if isinstance(rels, list) and rels:
        lines.append("$.relationships:")
        for idx, rel in enumerate(rels):
            if not isinstance(rel, dict):
                continue
            target = rel.get("target_character_id") or rel.get(
                "target_label") or "?"
            signals = " ".join(
                f"{f}={rel.get(f)!r}"
                for f in _REL_SIGNAL_FIELDS if rel.get(f) is not None)
            drivers = rel.get("driving_events") or []
            n_drivers = len(drivers) if isinstance(drivers, list) else 0
            lines.append(
                f"  [{idx}] {target}: {signals} driving_events={n_drivers}")

    if include_knowledge:
        scope = snap.get("knowledge_scope") or {}
        if isinstance(scope, dict):
            for key in ("knows", "does_not_know", "uncertain"):
                lines.extend(_render_list_field(
                    scope, key, prefix=f"$.knowledge_scope.{key}"))

    return "\n".join(lines) + "\n"


def _render_world_stage(snap: dict, stage_id: str) -> str:
    lines = [
        f"### {stage_id} — {snap.get('stage_title', '')}",
        f"timeline_anchor: {snap.get('timeline_anchor', '')}",
        f"location_anchor: {snap.get('location_anchor', '')}",
    ]
    summary = snap.get("snapshot_summary")
    if summary:
        lines.append(f"$.snapshot_summary: {summary}")
    for key in ("current_world_state", "stage_events", "location_changes",
                "relationship_shifts", "unresolved_questions"):
        lines.extend(_render_list_field(snap, key))
    return "\n".join(lines) + "\n"


def _render_list_field(
    obj: dict, key: str, prefix: str | None = None,
) -> list[str]:
    """Render ``obj[key]`` as indexed lines, or nothing when absent/empty."""
    value = obj.get(key)
    if not isinstance(value, list) or not value:
        return []
    label = prefix or f"$.{key}"
    out = [f"{label}:"]
    for idx, item in enumerate(value):
        if isinstance(item, (dict, list)):
            rendered = json.dumps(item, ensure_ascii=False)
        else:
            rendered = str(item)
        out.append(f"  [{idx}] {rendered}")
    return out


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("cross_stage_projection: cannot read %s: %s",
                       path, exc)
        return None
    return raw if isinstance(raw, dict) else None
