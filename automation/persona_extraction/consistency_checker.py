"""Cross-stage consistency checker — Phase 3.5.

Runs after all Phase 3 stages complete. Performs programmatic checks
(zero tokens) across all stages to find issues that single-stage
validation cannot detect: alias drift, relationship jumps, annotation
degradation, etc.

Produces ``consistency_report.json`` under the work's analysis dir.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .validator import importance_for_target, importance_min_examples

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ConsistencyIssue:
    severity: str          # "error" or "warning"
    category: str          # e.g. "alias", "relationship", "evidence_refs"
    location: str          # e.g. "角色名/S003"
    message: str

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "location": self.location,
            "message": self.message,
        }

    def __str__(self) -> str:
        return f"[{self.severity}] {self.category} @ {self.location}: {self.message}"


@dataclass
class ConsistencyReport:
    passed: bool
    error_count: int = 0
    warning_count: int = 0
    issues: list[ConsistencyIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [i.to_dict() for i in self.issues],
        }

    def summary(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        lines = [
            f"Consistency check: {status}",
            f"  Errors: {self.error_count}, Warnings: {self.warning_count}",
        ]
        for issue in self.issues:
            lines.append(f"  {issue}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_consistency_check(
    project_root: Path,
    work_id: str,
    character_ids: list[str],
    stage_ids: list[str],
) -> ConsistencyReport:
    """Run all cross-stage programmatic checks.

    Args:
        project_root: Repository root.
        work_id: Work identifier.
        character_ids: List of target character IDs.
        stage_ids: Ordered list of stage IDs (from stage plan).

    Returns:
        ConsistencyReport with all issues found.
    """
    work_dir = project_root / "works" / work_id
    issues: list[ConsistencyIssue] = []

    # Load importance map for example count thresholds
    imp_path = (project_root / "works" / work_id / "analysis"
                / "candidate_characters.json")
    importance_map: dict[str, str] = {}
    if imp_path.exists():
        try:
            imp_data = json.loads(imp_path.read_text(encoding="utf-8"))
            importance_map = {
                c["character_id"]: c.get("importance", "")
                for c in imp_data.get("candidates", [])
                if c.get("character_id")}
        except (json.JSONDecodeError, OSError, KeyError):
            pass

    issues.extend(_check_alias_consistency(work_dir, character_ids, stage_ids))
    issues.extend(_check_field_completeness(work_dir, character_ids, stage_ids))
    issues.extend(_check_relationship_continuity(work_dir, character_ids, stage_ids))
    issues.extend(_check_evidence_refs_coverage(work_dir, character_ids, stage_ids))
    issues.extend(_check_memory_id_correspondence(work_dir, character_ids, stage_ids))
    issues.extend(_check_memory_digest_summary_equality(
        work_dir, character_ids, stage_ids))
    issues.extend(_check_target_map_counts(
        work_dir, character_ids, stage_ids, importance_map))
    issues.extend(_check_stage_id_alignment(work_dir, character_ids, stage_ids))
    issues.extend(_check_world_event_digest(work_dir, stage_ids))
    issues.extend(_check_world_event_digest_summary_equality(
        work_dir, stage_ids))

    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    passed = error_count == 0

    return ConsistencyReport(
        passed=passed,
        error_count=error_count,
        warning_count=warning_count,
        issues=issues,
    )


def save_report(
    report: ConsistencyReport,
    project_root: Path,
    work_id: str,
) -> Path:
    """Save the consistency report to the analysis directory."""
    path = (project_root / "works" / work_id / "analysis"
            / "consistency_report.json")
    path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Consistency report saved: %s", path)
    return path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    """Read a JSON file read-only.

    Phase 3.5 must not mutate tracked artifacts as a side effect — any
    write here would leave uncommitted dirt that blocks ``checkout_master``
    (see requirements §11.10 "Phase 3.5 产物提交契约"). Parse errors are
    the repair agent's responsibility; here we just log and return None.
    """
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return None


def _load_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file read-only (see _load_json docstring)."""
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(line) for line in lines if line.strip()]
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return []


def _snapshot_path(work_dir: Path, char_id: str, stage_id: str) -> Path:
    return (work_dir / "characters" / char_id / "canon"
            / "stage_snapshots" / f"{stage_id}.json")


def _timeline_path(work_dir: Path, char_id: str, stage_id: str) -> Path:
    return (work_dir / "characters" / char_id / "canon"
            / "memory_timeline" / f"{stage_id}.json")


def _digest_path(work_dir: Path, char_id: str) -> Path:
    return work_dir / "characters" / char_id / "canon" / "memory_digest.jsonl"


def _extraction_notes_path(work_dir: Path, char_id: str, stage_id: str) -> Path:
    return (work_dir / "characters" / char_id / "canon"
            / "extraction_notes" / f"{stage_id}.jsonl")


def _load_coverage_shortage_paths(
    work_dir: Path, char_id: str, stage_id: str,
) -> set[str]:
    """Return the set of ``json_path`` entries for which a
    ``coverage_shortage`` SourceNote exists in this stage's notes file.

    Phase 3.5 uses this to suppress min_examples warnings already
    documented by the repair agent — otherwise every coverage_shortage
    accept would show up as a consistency warning on every run.
    """
    notes_path = _extraction_notes_path(work_dir, char_id, stage_id)
    if not notes_path.exists():
        return set()
    paths: set[str] = set()
    for note in _load_jsonl(notes_path):
        if note.get("discrepancy_type") == "coverage_shortage":
            jp = note.get("json_path")
            if jp:
                paths.add(jp)
    return paths


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------

def _check_alias_consistency(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
) -> list[ConsistencyIssue]:
    """Verify stage_snapshot active_aliases match identity.json aliases."""
    issues: list[ConsistencyIssue] = []

    for char_id in character_ids:
        identity_path = work_dir / "characters" / char_id / "canon" / "identity.json"
        identity = _load_json(identity_path)
        if identity is None:
            issues.append(ConsistencyIssue(
                "error", "alias", f"{char_id}/identity.json",
                "identity.json missing or unreadable"))
            continue

        # Collect all known alias names from identity.json
        identity_aliases = set()
        for alias in identity.get("aliases", []):
            name = alias.get("name") or alias.get("text", "")
            if name:
                identity_aliases.add(name)
        # Add canonical name
        canonical = identity.get("canonical_name", "")
        if canonical:
            identity_aliases.add(canonical)

        for stage_id in stage_ids:
            snapshot = _load_json(_snapshot_path(work_dir, char_id, stage_id))
            if snapshot is None:
                continue
            active = snapshot.get("active_aliases", {})
            active_names = active.get("active_names", [])
            for entry in active_names:
                name = entry.get("name", "") if isinstance(entry, dict) else str(entry)
                if name and name not in identity_aliases:
                    issues.append(ConsistencyIssue(
                        "warning", "alias", f"{char_id}/{stage_id}",
                        f"active_alias '{name}' not in identity.json aliases"))

    return issues


def _check_field_completeness(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
) -> list[ConsistencyIssue]:
    """Verify every snapshot has all required dimensions."""
    issues: list[ConsistencyIssue] = []

    # Fields required in every stage snapshot
    required_fields = [
        "active_aliases", "voice_state", "behavior_state", "boundary_state",
        "relationships", "knowledge_scope", "misunderstandings", "concealments",
        "emotional_baseline", "current_personality", "current_mood",
        "current_status", "stage_events",
    ]
    # These fields are only meaningful from the second stage onward:
    # first-stage snapshots may omit them (prompt: "第一个阶段可省略
    # 或仅写起点状态").
    non_first_stage_fields = ("stage_delta", "character_arc")

    for char_id in character_ids:
        for idx, stage_id in enumerate(stage_ids):
            snapshot = _load_json(_snapshot_path(work_dir, char_id, stage_id))
            if snapshot is None:
                issues.append(ConsistencyIssue(
                    "error", "completeness", f"{char_id}/{stage_id}",
                    "stage_snapshot missing"))
                continue

            fields_to_check = list(required_fields)
            if idx > 0:
                fields_to_check.extend(non_first_stage_fields)

            for fld in fields_to_check:
                val = snapshot.get(fld)
                if val is None:
                    issues.append(ConsistencyIssue(
                        "error", "completeness", f"{char_id}/{stage_id}",
                        f"Required field '{fld}' missing"))
                elif isinstance(val, (list, dict, str)) and not val:
                    issues.append(ConsistencyIssue(
                        "warning", "completeness", f"{char_id}/{stage_id}",
                        f"Field '{fld}' is empty"))

    return issues


def _check_relationship_continuity(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
) -> list[ConsistencyIssue]:
    """Flag relationship changes between adjacent stages without driving_events."""
    issues: list[ConsistencyIssue] = []

    for char_id in character_ids:
        prev_rels: dict[str, dict] = {}
        for stage_id in stage_ids:
            snapshot = _load_json(_snapshot_path(work_dir, char_id, stage_id))
            if snapshot is None:
                prev_rels = {}
                continue

            curr_rels: dict[str, dict] = {}
            for rel in snapshot.get("relationships", []):
                # Schema: target_character_id is the canonical key
                target = rel.get("target_character_id",
                                 rel.get("target_label", ""))
                if target:
                    curr_rels[target] = rel

            if prev_rels:
                for target, rel in curr_rels.items():
                    if target in prev_rels:
                        prev = prev_rels[target]
                        # Check if attitude/trust/intimacy changed
                        # Schema fields: attitude (str), trust (int), intimacy (int)
                        for fld in ("attitude", "trust", "intimacy"):
                            old_val = prev.get(fld)
                            new_val = rel.get(fld)
                            if old_val is not None and new_val is not None \
                                    and old_val != new_val:
                                events = rel.get("driving_events", [])
                                if not events:
                                    issues.append(ConsistencyIssue(
                                        "warning", "relationship",
                                        f"{char_id}/{stage_id}/{target}",
                                        f"'{fld}' changed from '{old_val}' to "
                                        f"'{new_val}' without driving_events"))

            prev_rels = curr_rels

    return issues


def _check_evidence_refs_coverage(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
) -> list[ConsistencyIssue]:
    """Flag snapshots with empty ``evidence_refs``.

    ``evidence_refs`` exists on character stage_snapshot (chapter anchor
    for the snapshot as a whole) and on world_stage_snapshot (chapter
    anchor for the world-level snapshot). An empty list means the
    snapshot has no chapter anchor for later verification.
    """
    issues: list[ConsistencyIssue] = []

    for stage_id in stage_ids:
        world_snap = _load_json(
            work_dir / "world" / "stage_snapshots" / f"{stage_id}.json")
        if world_snap is not None and not world_snap.get("evidence_refs"):
            issues.append(ConsistencyIssue(
                "warning", "evidence_refs", f"world/{stage_id}",
                "world stage_snapshot has empty evidence_refs"))

    for char_id in character_ids:
        for stage_id in stage_ids:
            snapshot = _load_json(_snapshot_path(work_dir, char_id, stage_id))
            if snapshot is not None:
                refs = snapshot.get("evidence_refs", [])
                if not refs:
                    issues.append(ConsistencyIssue(
                        "warning", "evidence_refs", f"{char_id}/{stage_id}",
                        "stage_snapshot has empty evidence_refs"))

    return issues


def _check_memory_id_correspondence(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
) -> list[ConsistencyIssue]:
    """Verify memory_digest.jsonl ↔ memory_timeline memory_id correspondence."""
    issues: list[ConsistencyIssue] = []

    for char_id in character_ids:
        # Collect all memory_ids from timeline files
        timeline_ids: set[str] = set()
        for stage_id in stage_ids:
            timeline = _load_json(_timeline_path(work_dir, char_id, stage_id))
            if isinstance(timeline, list):
                for entry in timeline:
                    mid = entry.get("memory_id", "")
                    if mid:
                        timeline_ids.add(mid)

        # Collect all memory_ids from digest
        digest_entries = _load_jsonl(_digest_path(work_dir, char_id))
        digest_ids: set[str] = set()
        for entry in digest_entries:
            mid = entry.get("memory_id", "")
            if mid:
                digest_ids.add(mid)

        # Check correspondence
        missing_in_digest = timeline_ids - digest_ids
        orphan_in_digest = digest_ids - timeline_ids

        for mid in missing_in_digest:
            issues.append(ConsistencyIssue(
                "error", "memory_id", f"{char_id}/memory_digest",
                f"memory_id '{mid}' in timeline but missing from digest"))

        for mid in orphan_in_digest:
            issues.append(ConsistencyIssue(
                "warning", "memory_id", f"{char_id}/memory_digest",
                f"memory_id '{mid}' in digest but not in any timeline"))

    return issues


def _check_memory_digest_summary_equality(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
) -> list[ConsistencyIssue]:
    """Verify memory_digest.summary == timeline.digest_summary (1:1 text).

    Decisions §33 requires memory_digest entries to be a literal 1:1 copy
    of the matching memory_timeline ``digest_summary``. Post-processing
    writes them that way; if repair later rewrites ``digest_summary``
    but post-processing is not re-run, the two drift. Compare by
    ``memory_id`` and flag any text mismatch as an error.
    """
    issues: list[ConsistencyIssue] = []

    for char_id in character_ids:
        timeline_by_id: dict[str, str] = {}
        for stage_id in stage_ids:
            timeline = _load_json(_timeline_path(work_dir, char_id, stage_id))
            if isinstance(timeline, list):
                for entry in timeline:
                    mid = entry.get("memory_id", "")
                    digest_summary = entry.get("digest_summary", "")
                    if mid and isinstance(digest_summary, str):
                        timeline_by_id[mid] = digest_summary

        for entry in _load_jsonl(_digest_path(work_dir, char_id)):
            mid = entry.get("memory_id", "")
            summary = entry.get("summary", "")
            if not mid or mid not in timeline_by_id:
                continue
            if summary != timeline_by_id[mid]:
                issues.append(ConsistencyIssue(
                    "error", "memory_digest_summary",
                    f"{char_id}/memory_digest/{mid}",
                    "memory_digest.summary != memory_timeline.digest_summary "
                    "(1:1 copy contract violated; re-run post-processing)"))

    return issues


def _min_examples_for_target(target: str,
                             importance_map: dict[str, str]) -> int:
    """Shared rule: main → 5, important → 3, others → 1.

    Delegates to :func:`validator.importance_for_target` (substring +
    most-important tie-break) so the consistency checker and the repair
    agent's L2 structural checker agree on what each target counts as.
    """
    return importance_min_examples(
        importance_for_target(target, importance_map))


def _check_target_map_counts(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
    importance_map: dict[str, str] | None = None,
) -> list[ConsistencyIssue]:
    """Verify target maps have enough examples.

    Thresholds based on character importance from candidate_characters:
    主角 ≥5, 重要配角 ≥3, others ≥1.
    """
    issues: list[ConsistencyIssue] = []
    imp = importance_map or {}

    for char_id in character_ids:
        for stage_id in stage_ids:
            snapshot = _load_json(_snapshot_path(work_dir, char_id, stage_id))
            if snapshot is None:
                continue

            # coverage_shortage SourceNotes accepted by repair agent —
            # if an accepted note covers this json_path we treat the
            # count as satisfied (no warning).
            accepted_paths = _load_coverage_shortage_paths(
                work_dir, char_id, stage_id)

            # target_voice_map
            voice_state = snapshot.get("voice_state", {})
            for idx, entry in enumerate(
                    voice_state.get("target_voice_map", [])):
                target = entry.get("target_type", "?")
                examples = entry.get("dialogue_examples", [])
                min_ex = _min_examples_for_target(target, imp)
                if len(examples) >= min_ex:
                    continue
                json_path = (f"$.voice_state.target_voice_map[{idx}]"
                             f".dialogue_examples")
                if json_path in accepted_paths:
                    continue
                issues.append(ConsistencyIssue(
                    "warning", "target_map",
                    f"{char_id}/{stage_id}/voice/{target}",
                    f"target_voice_map has {len(examples)} "
                    f"dialogue_examples (want >={min_ex})"))

            # target_behavior_map
            behavior_state = snapshot.get("behavior_state", {})
            for idx, entry in enumerate(
                    behavior_state.get("target_behavior_map", [])):
                target = entry.get("target_type", "?")
                examples = entry.get("action_examples", [])
                min_ex = _min_examples_for_target(target, imp)
                if len(examples) >= min_ex:
                    continue
                json_path = (f"$.behavior_state.target_behavior_map[{idx}]"
                             f".action_examples")
                if json_path in accepted_paths:
                    continue
                issues.append(ConsistencyIssue(
                    "warning", "target_map",
                    f"{char_id}/{stage_id}/behavior/{target}",
                    f"target_behavior_map has {len(examples)} "
                    f"action_examples (want >={min_ex})"))

    return issues


def _check_stage_id_alignment(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
) -> list[ConsistencyIssue]:
    """Verify world/character stage_catalogs and snapshot dirs are aligned."""
    issues: list[ConsistencyIssue] = []
    expected = set(stage_ids)

    # World catalog
    world_catalog = _load_json(work_dir / "world" / "stage_catalog.json")
    if world_catalog:
        world_stages = {s.get("stage_id")
                        for s in world_catalog.get("stages", [])}
        missing = expected - world_stages
        for sid in missing:
            issues.append(ConsistencyIssue(
                "error", "stage_alignment", f"world/stage_catalog",
                f"stage_id '{sid}' missing from world stage_catalog"))

    # World snapshots directory
    world_snap_dir = work_dir / "world" / "stage_snapshots"
    if world_snap_dir.exists():
        world_files = {p.stem for p in world_snap_dir.glob("*.json")}
        missing = expected - world_files
        for sid in missing:
            issues.append(ConsistencyIssue(
                "error", "stage_alignment", f"world/stage_snapshots",
                f"stage_snapshot file missing for '{sid}'"))

    # Character catalogs and snapshots
    for char_id in character_ids:
        char_dir = work_dir / "characters" / char_id / "canon"

        catalog = _load_json(char_dir / "stage_catalog.json")
        if catalog:
            char_stages = {s.get("stage_id")
                           for s in catalog.get("stages", [])}
            missing = expected - char_stages
            for sid in missing:
                issues.append(ConsistencyIssue(
                    "error", "stage_alignment",
                    f"{char_id}/stage_catalog",
                    f"stage_id '{sid}' missing from character stage_catalog"))

        snap_dir = char_dir / "stage_snapshots"
        if snap_dir.exists():
            char_files = {p.stem for p in snap_dir.glob("*.json")}
            missing = expected - char_files
            for sid in missing:
                issues.append(ConsistencyIssue(
                    "error", "stage_alignment",
                    f"{char_id}/stage_snapshots",
                    f"stage_snapshot file missing for '{sid}'"))

    return issues


def _check_world_event_digest(
    work_dir: Path, stage_ids: list[str],
) -> list[ConsistencyIssue]:
    """Verify world_event_digest ↔ world snapshot stage_events correspondence.

    For each stage:
    - Digest must have entries for the stage
    - Entry count must match stage_events count in the world snapshot
    - Digest entries carry no stage_id field; stage is parsed from event_id
      prefix ``E-S###-##``.
    """
    import re
    _stage_num_re = re.compile(r"S(\d{3})")

    def _stage_num(stage_id: str) -> int | None:
        m = _stage_num_re.search(stage_id)
        if m:
            return int(m.group(1))
        digits = re.search(r"(\d+)", stage_id)
        return int(digits.group(1)) if digits else None

    def _event_stage_num(entry: dict) -> int | None:
        eid = entry.get("event_id", "")
        m = _stage_num_re.search(eid)
        return int(m.group(1)) if m else None

    issues: list[ConsistencyIssue] = []

    digest_path = work_dir / "world" / "world_event_digest.jsonl"
    digest_entries = _load_jsonl(digest_path)

    # Group digest entries by stage number (parsed from event_id)
    digest_by_stage_num: dict[int, list[dict]] = {}
    for entry in digest_entries:
        n = _event_stage_num(entry)
        if n is not None:
            digest_by_stage_num.setdefault(n, []).append(entry)

    for stage_id in stage_ids:
        snap_path = work_dir / "world" / "stage_snapshots" / f"{stage_id}.json"
        snapshot = _load_json(snap_path)
        if snapshot is None:
            continue

        stage_events = snapshot.get("stage_events", [])
        n_events = len([e for e in stage_events
                        if isinstance(e, str) and e.strip()])

        snum = _stage_num(stage_id)
        stage_digest = (digest_by_stage_num.get(snum, [])
                        if snum is not None else [])

        if not stage_digest and n_events > 0:
            issues.append(ConsistencyIssue(
                "error", "world_event_digest",
                f"world/{stage_id}",
                f"world_event_digest has no entries for stage "
                f"(expected {n_events} from stage_events)"))
        elif len(stage_digest) != n_events:
            issues.append(ConsistencyIssue(
                "error", "world_event_digest",
                f"world/{stage_id}",
                f"world_event_digest has {len(stage_digest)} entries "
                f"but stage_events has {n_events} items "
                f"(1:1 mapping required)"))

    return issues


def _check_world_event_digest_summary_equality(
    work_dir: Path, stage_ids: list[str],
) -> list[ConsistencyIssue]:
    """Verify world_event_digest.summary == world stage_events[i] (1:1 text).

    Decisions §32 requires each world_event_digest entry's ``summary`` to
    be a literal 1:1 copy of the corresponding ``stage_events[i]`` in the
    world stage_snapshot, with ``i = int(event_id seq) - 1``. Post-
    processing writes them that way; repair rewriting ``stage_events``
    without a post-processing re-run would desynchronise them. Flag any
    text mismatch as an error.
    """
    import re
    _event_re = re.compile(r"^E-S(\d{3})-(\d{2})$")

    digest_entries = _load_jsonl(
        work_dir / "world" / "world_event_digest.jsonl")
    digest_by_stage_seq: dict[tuple[str, int], str] = {}
    for entry in digest_entries:
        eid = entry.get("event_id", "")
        m = _event_re.match(eid) if isinstance(eid, str) else None
        if not m:
            continue
        stage_key = f"S{m.group(1)}"
        seq = int(m.group(2))
        summary = entry.get("summary", "")
        if isinstance(summary, str):
            digest_by_stage_seq[(stage_key, seq)] = summary

    issues: list[ConsistencyIssue] = []
    for stage_id in stage_ids:
        snap_path = work_dir / "world" / "stage_snapshots" / f"{stage_id}.json"
        snapshot = _load_json(snap_path)
        if snapshot is None:
            continue
        stage_events = snapshot.get("stage_events", [])
        if not isinstance(stage_events, list):
            continue
        for i, event_text in enumerate(stage_events):
            if not isinstance(event_text, str) or not event_text.strip():
                continue
            expected = event_text.strip()
            actual = digest_by_stage_seq.get((stage_id, i + 1))
            if actual is None:
                continue
            if actual != expected:
                issues.append(ConsistencyIssue(
                    "error", "world_event_digest_summary",
                    f"world/{stage_id}/E-{stage_id}-{i + 1:02d}",
                    "world_event_digest.summary != stage_events[i] "
                    "(1:1 copy contract violated; re-run post-processing)"))

    return issues
