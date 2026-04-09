"""Cross-batch consistency checker — Phase 3.5.

Runs after all Phase 3 batches complete. Performs programmatic checks
(zero tokens) across all batches to find issues that single-batch
validation cannot detect: alias drift, relationship jumps, annotation
degradation, etc.

Produces ``consistency_report.json`` under the work's incremental dir.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .json_repair import try_repair_json_file, try_repair_jsonl_file

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ConsistencyIssue:
    severity: str          # "error" or "warning"
    category: str          # e.g. "alias", "relationship", "source_type"
    location: str          # e.g. "姜寒汐/阶段03"
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
    """Run all cross-batch programmatic checks.

    Args:
        project_root: Repository root.
        work_id: Work identifier.
        character_ids: List of target character IDs.
        stage_ids: Ordered list of stage IDs (from batch plan).

    Returns:
        ConsistencyReport with all issues found.
    """
    work_dir = project_root / "works" / work_id
    issues: list[ConsistencyIssue] = []

    # Load importance map for example count thresholds
    imp_path = (project_root / "works" / work_id / "analysis"
                / "incremental" / "candidate_characters.json")
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
    issues.extend(_check_source_type_distribution(work_dir, character_ids, stage_ids))
    issues.extend(_check_evidence_refs_coverage(work_dir, character_ids, stage_ids))
    issues.extend(_check_memory_id_correspondence(work_dir, character_ids, stage_ids))
    issues.extend(_check_target_map_counts(
        work_dir, character_ids, stage_ids, importance_map))
    issues.extend(_check_stage_id_alignment(work_dir, character_ids, stage_ids))

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
    """Save the consistency report to the incremental directory."""
    path = (project_root / "works" / work_id / "analysis" / "incremental"
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
    """Load a JSON file, attempting repair if needed."""
    if not path.exists():
        return None
    try:
        try_repair_json_file(path)
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return None


def _load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file, attempting repair if needed."""
    if not path.exists():
        return []
    try:
        try_repair_jsonl_file(path)
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
        "current_status",
    ]
    # stage_delta is only meaningful from the second stage onward
    delta_field = "stage_delta"

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
                fields_to_check.append(delta_field)

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
                target = rel.get("target", rel.get("target_id", ""))
                curr_rels[target] = rel

            if prev_rels:
                for target, rel in curr_rels.items():
                    if target in prev_rels:
                        prev = prev_rels[target]
                        # Check if attitude/trust changed
                        for fld in ("attitude", "trust_level", "intimacy_level"):
                            old_val = prev.get(fld)
                            new_val = rel.get(fld)
                            if old_val and new_val and old_val != new_val:
                                events = rel.get("driving_events", [])
                                if not events:
                                    issues.append(ConsistencyIssue(
                                        "warning", "relationship",
                                        f"{char_id}/{stage_id}/{target}",
                                        f"'{fld}' changed from '{old_val}' to "
                                        f"'{new_val}' without driving_events"))

            prev_rels = curr_rels

    return issues


def _check_source_type_distribution(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
) -> list[ConsistencyIssue]:
    """Flag batches where source_notes are all canon (lazy annotation)."""
    issues: list[ConsistencyIssue] = []

    for char_id in character_ids:
        for stage_id in stage_ids:
            snapshot = _load_json(_snapshot_path(work_dir, char_id, stage_id))
            if snapshot is None:
                continue
            source_notes = snapshot.get("source_notes", [])
            if not source_notes:
                continue
            types = [n.get("source_type") for n in source_notes]
            unique = set(types)
            if unique == {"canon"} and len(types) >= 3:
                issues.append(ConsistencyIssue(
                    "warning", "source_type", f"{char_id}/{stage_id}",
                    f"All {len(types)} source_notes are 'canon' — "
                    f"may indicate lazy annotation"))

    return issues


def _check_evidence_refs_coverage(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
) -> list[ConsistencyIssue]:
    """Flag snapshots or memory entries with empty evidence_refs."""
    issues: list[ConsistencyIssue] = []

    for char_id in character_ids:
        for stage_id in stage_ids:
            # Check snapshot
            snapshot = _load_json(_snapshot_path(work_dir, char_id, stage_id))
            if snapshot is not None:
                refs = snapshot.get("evidence_refs", [])
                if not refs:
                    issues.append(ConsistencyIssue(
                        "warning", "evidence_refs", f"{char_id}/{stage_id}",
                        "stage_snapshot has empty evidence_refs"))

            # Check memory_timeline entries
            timeline = _load_json(_timeline_path(work_dir, char_id, stage_id))
            if isinstance(timeline, list):
                for i, entry in enumerate(timeline):
                    refs = entry.get("evidence_refs", [])
                    mid = entry.get("memory_id", f"entry_{i}")
                    if not refs:
                        issues.append(ConsistencyIssue(
                            "warning", "evidence_refs",
                            f"{char_id}/{stage_id}/memory/{mid}",
                            "memory_timeline entry has empty evidence_refs"))

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


def _min_examples_for_target(target: str,
                             importance_map: dict[str, str]) -> int:
    """主角 → 5, 重要配角 → 3, others → 1. Substring match."""
    for name, importance in importance_map.items():
        if name in target:
            if importance == "主角":
                return 5
            if importance == "重要配角":
                return 3
            return 1
    return 1


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

            # target_voice_map
            voice_state = snapshot.get("voice_state", {})
            for entry in voice_state.get("target_voice_map", []):
                target = entry.get("target_type", "?")
                examples = entry.get("dialogue_examples", [])
                min_ex = _min_examples_for_target(target, imp)
                if len(examples) < min_ex:
                    issues.append(ConsistencyIssue(
                        "warning", "target_map",
                        f"{char_id}/{stage_id}/voice/{target}",
                        f"target_voice_map has {len(examples)} "
                        f"dialogue_examples (want >={min_ex})"))

            # target_behavior_map
            behavior_state = snapshot.get("behavior_state", {})
            for entry in behavior_state.get("target_behavior_map", []):
                target = entry.get("target_type", "?")
                examples = entry.get("action_examples", [])
                min_ex = _min_examples_for_target(target, imp)
                if len(examples) < min_ex:
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
