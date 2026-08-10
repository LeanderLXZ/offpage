"""Cross-stage consistency gate — Phase 3.5.

Runs after all Phase 3 stages complete. This is the last gate stage files
pass through, so it answers two questions no earlier phase can:

* **Is the cross-stage structure whole?** Phase 3 validates one stage at a
  time and cannot see a missing file, a catalog gap, or a derived
  projection that drifted out of sync with its primary.
* **Are the debts settled?** Phase 3's repair records what its capped tiers
  could not fix into ``deferred_repairs/{stage_id}.jsonl`` and commits the
  stage anyway (decision #60, record-and-continue). Those ledgers had no
  consumer; here they become a blocking verdict.

Three layers, all zero-token and programmatic:

* **L1 structure** — files and catalogs that must exist, exist.
* **L2 derived consistency** — code-projected artifacts still match their
  primaries 1:1 (decisions §32 / §33). Since decision #61 moved digests out
  of repair, this gate is the only thing that can catch a projection drift.
* **L3 ledger settlement** — deferred debts are re-adjudicated rather than
  trusted: schema-class debts are re-validated against the current file (a
  settled one disappears on its own), semantic-class debts clear only via a
  recorded resolution.

Auxiliary checks (field completeness, relationship continuity, target-map
example counts) run alongside and count toward the verdict.

**Coverage ledger.** Every check reports ``checked`` / ``skipped`` / ``hit``.
A file that cannot be read is *skipped*, and a skip fails the gate — before
this, an unreadable file silently ``continue``d and "everything passed"
looked identical to "nothing was examined".

Verdict: ``passed = error_count == 0 AND skipped_total == 0``.

Produces ``consistency_report.json`` under the work's analysis dir.

D4 (``stage_snapshot.{voice_state.target_voice_map,
behavior_state.target_behavior_map, relationships}`` keys ==
``target_baseline.targets[].target_character_id``) is enforced by the
**phase 3 single-stage validate layer** through
``extraction/repair/checkers/targets_keys_eq_baseline.py``;
violations route into the file-level repair lifecycle (L1/L2/L3 there =
**repair framework checker tiers**, decision #25 — unrelated to this
module's L1/L2/L3 layer names, and also distinct from phase 0's JSON-format
``L1/L2/L3`` in decision #40). This phase 3.5 module no longer owns that rule.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ...persona_extraction.lifecycle.deferred_repair_log import (
    issue_key,
    read_deferred_ledger,
    read_resolutions,
)
from ..shared.importance import importance_for_target, importance_min_examples

logger = logging.getLogger(__name__)

# Debt categories that code can re-adjudicate on its own. Everything else
# needs a recorded resolution — a semantic claim cannot be re-derived from
# the file without the judgement that produced it.
REVALIDATABLE_CATEGORIES = frozenset({"schema", "structural"})


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ConsistencyIssue:
    severity: str          # "error" or "warning"
    # For L3 debts this is the debt's ORIGINAL category (semantic /
    # schema / structural) — not a generic "debt" label. Downstream it
    # decides both how the debt can be settled and which repair tier the
    # seeded fix routes to; ``layer`` already says "this is a debt".
    category: str          # e.g. "memory_id", "semantic", "schema"
    location: str          # e.g. "<character_id>/S003"
    message: str
    layer: str = ""        # "L1" | "L2" | "L3" | "aux"
    file: str = ""         # L3 only — absolute path of the debt's file
    json_path: str = ""    # L3 only — field the debt sits on
    # Original rule name, carried verbatim rather than re-derived from the
    # message. It is half of a debt's identity (``file::json_path::rule``),
    # so parsing it back out of prose would silently break the match between
    # "debt recorded" and "debt settled" — and a debt that can never be
    # matched can never be cleared.
    rule: str = ""

    def to_dict(self) -> dict:
        out = {
            "severity": self.severity,
            "category": self.category,
            "location": self.location,
            "message": self.message,
        }
        if self.layer:
            out["layer"] = self.layer
        if self.file:
            out["file"] = self.file
        if self.json_path:
            out["json_path"] = self.json_path
        if self.rule:
            out["rule"] = self.rule
        return out

    def __str__(self) -> str:
        prefix = f"{self.layer} " if self.layer else ""
        return (f"[{self.severity}] {prefix}{self.category} @ "
                f"{self.location}: {self.message}")


@dataclass
class CheckCoverage:
    """What one check actually examined.

    ``skipped`` is the load-bearing field: it is the difference between
    "examined and found nothing" and "never looked", which a pass/fail count
    alone cannot express.
    """
    name: str
    layer: str
    checked: int = 0
    skipped: int = 0
    hit: int = 0
    skipped_targets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "layer": self.layer,
            "checked": self.checked,
            "skipped": self.skipped,
            "hit": self.hit,
            "skipped_targets": self.skipped_targets[:20],
        }


class Coverage:
    """Collects per-check coverage during a run."""

    def __init__(self) -> None:
        self._by_name: dict[str, CheckCoverage] = {}

    def check(self, name: str, layer: str) -> CheckCoverage:
        if name not in self._by_name:
            self._by_name[name] = CheckCoverage(name=name, layer=layer)
        return self._by_name[name]

    def entries(self) -> list[CheckCoverage]:
        return list(self._by_name.values())

    def skipped_total(self) -> int:
        return sum(c.skipped for c in self._by_name.values())


@dataclass
class ConsistencyReport:
    passed: bool
    error_count: int = 0
    warning_count: int = 0
    issues: list[ConsistencyIssue] = field(default_factory=list)
    coverage: list[CheckCoverage] = field(default_factory=list)
    skipped_total: int = 0

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "skipped_total": self.skipped_total,
            "coverage": [c.to_dict() for c in self.coverage],
            "issues": [i.to_dict() for i in self.issues],
        }

    def summary(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        lines = [
            f"Consistency check: {status}",
            f"  Errors: {self.error_count}, Warnings: {self.warning_count}, "
            f"Skipped: {self.skipped_total}",
        ]
        for c in self.coverage:
            flag = " ⚠" if c.skipped else ""
            lines.append(
                f"  [{c.layer}] {c.name}: checked={c.checked} "
                f"hit={c.hit} skipped={c.skipped}{flag}")
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
    revalidate_schema: Callable[[str], list[str]] | None = None,
) -> ConsistencyReport:
    """Run all cross-stage programmatic checks (zero tokens).

    Args:
        project_root: Repository root.
        work_id: Work identifier.
        character_ids: List of target character IDs.
        stage_ids: Ordered list of stage IDs (from stage plan).
        revalidate_schema: ``file_path -> [json_path, ...]`` returning the
            schema violations a file currently has. Supplied by the caller
            because schema binding lives with the orchestrator's file
            wiring, not here. When ``None``, L3 cannot re-adjudicate
            schema-class debts and keeps them open (fail-closed: an
            unverifiable debt is not a settled one).

    Returns:
        ConsistencyReport with all issues and the coverage ledger.
    """
    work_dir = project_root / "works" / work_id
    issues: list[ConsistencyIssue] = []
    cov = Coverage()

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

    # ---- L1: structural wholeness ----
    issues.extend(_check_stage_files_present(
        work_dir, character_ids, stage_ids, cov))
    issues.extend(_check_stage_id_alignment(
        work_dir, character_ids, stage_ids, cov))

    # ---- L2: derived-projection consistency ----
    issues.extend(_check_memory_id_correspondence(
        work_dir, character_ids, stage_ids, cov))
    issues.extend(_check_memory_digest_summary_equality(
        work_dir, character_ids, stage_ids, cov))
    issues.extend(_check_world_event_digest(work_dir, stage_ids, cov))
    issues.extend(_check_world_event_digest_summary_equality(
        work_dir, stage_ids, cov))

    # ---- L3: deferred-debt settlement ----
    issues.extend(_check_deferred_ledgers(
        work_dir, stage_ids, cov, revalidate_schema))

    # ---- Auxiliary content checks ----
    issues.extend(_check_field_completeness(
        work_dir, character_ids, stage_ids, cov))
    issues.extend(_check_relationship_continuity(
        work_dir, character_ids, stage_ids, cov))
    issues.extend(_check_target_map_counts(
        work_dir, character_ids, stage_ids, importance_map, cov))

    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    skipped_total = cov.skipped_total()
    # A skip means a check never looked at something it was asked to look
    # at. Passing on that basis would report "clean" for an unexamined
    # artifact, so it fails the gate exactly like an error does.
    passed = error_count == 0 and skipped_total == 0

    return ConsistencyReport(
        passed=passed,
        error_count=error_count,
        warning_count=warning_count,
        issues=issues,
        coverage=cov.entries(),
        skipped_total=skipped_total,
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

def _load_json(path: Path) -> dict | None:
    """Read a JSON file read-only, returning the object or None.

    Phase 3.5 must not mutate tracked artifacts as a side effect — any
    write here would leave uncommitted dirt that blocks ``checkout_main``
    (see requirements §11.10 "Phase 3.5 产物提交契约"). Parse errors are
    the repair agent's responsibility; here we just log and return None.

    Every consumer in this module operates on object-shaped schemas
    (``identity.json``, ``stage_snapshot.json``, ``target_baseline.json``
    etc.); list-shaped or scalar files are returned as ``None`` so the
    standard "missing / unreadable" branch handles them.
    """
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return None
    if not isinstance(raw, dict):
        logger.warning(
            "Loaded %s but top-level is %s, expected object",
            path, type(raw).__name__)
        return None
    return raw


def _load_json_array(path: Path) -> list | None:
    """Read a JSON file whose top-level is an array, returning the list or None.

    Companion to ``_load_json`` for list-shaped schemas. The two cannot share
    a loader because ``_load_json`` enforces a dict top-level (every consumer
    expecting an object schema benefits from that shape check). Files whose
    schema declares a top-level array — currently ``memory_timeline/
    {stage_id}.json`` — must be read through this helper. Parse errors and
    non-list top levels return ``None``; callers handle that as the standard
    "missing / unreadable" branch.
    """
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return None
    if not isinstance(raw, list):
        logger.warning(
            "Loaded %s but top-level is %s, expected array",
            path, type(raw).__name__)
        return None
    return raw


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

def _check_stage_files_present(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
    cov: Coverage,
) -> list[ConsistencyIssue]:
    """L1 — every stage's primary artifacts exist and parse.

    This is the single place a missing / unparseable stage artifact is
    reported. Every other check treats an unreadable file as a *skip* and
    moves on, so without this layer a wholesale gap would surface only as
    silence.
    """
    c = cov.check("stage_files_present", "L1")
    issues: list[ConsistencyIssue] = []

    for stage_id in stage_ids:
        world_ss = work_dir / "world" / "stage_snapshots" / f"{stage_id}.json"
        c.checked += 1
        if _load_json(world_ss) is None:
            c.hit += 1
            issues.append(ConsistencyIssue(
                "error", "completeness", f"world/{stage_id}",
                "world stage_snapshot missing or unparseable",
                layer="L1", file=str(world_ss)))

    for char_id in character_ids:
        for stage_id in stage_ids:
            snap_path = _snapshot_path(work_dir, char_id, stage_id)
            c.checked += 1
            if _load_json(snap_path) is None:
                c.hit += 1
                issues.append(ConsistencyIssue(
                    "error", "completeness", f"{char_id}/{stage_id}",
                    "stage_snapshot missing or unparseable",
                    layer="L1", file=str(snap_path)))

            tl_path = _timeline_path(work_dir, char_id, stage_id)
            c.checked += 1
            if _load_json_array(tl_path) is None:
                c.hit += 1
                issues.append(ConsistencyIssue(
                    "error", "completeness", f"{char_id}/{stage_id}",
                    "memory_timeline missing or unparseable",
                    layer="L1", file=str(tl_path)))

    return issues


def _check_deferred_ledgers(
    work_dir: Path,
    stage_ids: list[str],
    cov: Coverage,
    revalidate_schema: Callable[[str], list[str]] | None,
) -> list[ConsistencyIssue]:
    """L3 — re-adjudicate the deferred-repair debts, don't trust the ledger.

    The ledger states what repair could not fix *at the time it ran*. By now
    a debt may have been settled, so replaying its claim verbatim would fail
    the gate forever. Two settlement routes, matching what each debt class
    can actually be proven by:

    * **schema / structural** — re-validate the file. The debt is settled iff
      its ``json_path`` no longer appears in the violation set. This is why
      the ledger can self-heal without anyone writing to it.
    * **semantic** — no programmatic re-derivation exists, so it clears only
      against a recorded resolution (``{stage_id}.resolved.jsonl``).

    Without ``revalidate_schema`` the first route is unavailable; those debts
    stay open rather than being assumed settled.
    """
    c = cov.check("deferred_ledgers", "L3")
    issues: list[ConsistencyIssue] = []
    # file path -> current schema violation json_paths (computed lazily; a
    # file usually carries several debts and revalidation is not free).
    violation_cache: dict[str, set[str]] = {}

    for stage_id in stage_ids:
        rows = read_deferred_ledger(work_dir, stage_id)
        if not rows:
            continue
        resolved = read_resolutions(work_dir, stage_id)

        for row in rows:
            c.checked += 1
            fpath = row.get("file", "")
            jpath = row.get("json_path", "")
            category = row.get("category", "")
            rule = row.get("rule", "")

            if category in REVALIDATABLE_CATEGORIES:
                # No resolution shortcut here on purpose: for a debt code can
                # re-derive, the file is the truth. Honouring a stored
                # resolution would permanently suppress the debt even if the
                # field broke again later.
                if revalidate_schema is None:
                    c.skipped += 1
                    c.skipped_targets.append(f"{stage_id}:{issue_key(row)}")
                    issues.append(ConsistencyIssue(
                        "error", category or "schema", f"{stage_id}",
                        f"{rule} at {jpath} cannot be re-adjudicated "
                        "(no schema revalidator supplied)",
                        layer="L3", file=fpath, json_path=jpath, rule=rule))
                    continue
                if fpath not in violation_cache:
                    try:
                        violation_cache[fpath] = set(revalidate_schema(fpath))
                    except Exception as exc:  # defensive: never abort the gate
                        logger.warning(
                            "revalidate_schema failed for %s: %s", fpath, exc)
                        c.skipped += 1
                        c.skipped_targets.append(fpath)
                        violation_cache[fpath] = set()
                        issues.append(ConsistencyIssue(
                            "error", category or "schema", f"{stage_id}",
                            f"{rule} at {jpath} could not be re-validated "
                            f"({exc})",
                            layer="L3", file=fpath, json_path=jpath,
                            rule=rule))
                        continue
                if jpath not in violation_cache[fpath]:
                    continue  # settled — the file no longer violates it
            elif issue_key(row) in resolved:
                # Semantic debts have no programmatic re-derivation, so a
                # recorded resolution is the only evidence they can offer.
                continue

            c.hit += 1
            issues.append(ConsistencyIssue(
                "error", category or "semantic", f"{stage_id}",
                f"unsettled {rule} at {jpath}: {row.get('message', '')}",
                layer="L3", file=fpath, json_path=jpath, rule=rule))

    return issues


def _check_field_completeness(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
    cov: Coverage,
) -> list[ConsistencyIssue]:
    """Verify every snapshot has all required dimensions."""
    c = cov.check("field_completeness", "aux")
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
                # Absence is L1's verdict to render; counting it here too
                # would double-report the same missing file.
                c.skipped += 1
                c.skipped_targets.append(f"{char_id}/{stage_id}")
                continue
            c.checked += 1

            fields_to_check = list(required_fields)
            if idx > 0:
                fields_to_check.extend(non_first_stage_fields)

            for fld in fields_to_check:
                val = snapshot.get(fld)
                if val is None:
                    c.hit += 1
                    issues.append(ConsistencyIssue(
                        "error", "completeness", f"{char_id}/{stage_id}",
                        f"Required field '{fld}' missing", layer="aux"))
                elif isinstance(val, (list, dict, str)) and not val:
                    c.hit += 1
                    issues.append(ConsistencyIssue(
                        "warning", "completeness", f"{char_id}/{stage_id}",
                        f"Field '{fld}' is empty", layer="aux"))

    return issues


def _check_relationship_continuity(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
    cov: Coverage,
) -> list[ConsistencyIssue]:
    """Flag relationship changes between adjacent stages without driving_events."""
    c = cov.check("relationship_continuity", "aux")
    issues: list[ConsistencyIssue] = []

    for char_id in character_ids:
        prev_rels: dict[str, dict] = {}
        for stage_id in stage_ids:
            snapshot = _load_json(_snapshot_path(work_dir, char_id, stage_id))
            if snapshot is None:
                c.skipped += 1
                c.skipped_targets.append(f"{char_id}/{stage_id}")
                prev_rels = {}
                continue

            curr_rels: dict[str, dict] = {}
            for rel in snapshot.get("relationships", []):
                # Schema: target_character_id is the canonical key
                # (#13 D4 set-equal anchor). A missing value here means
                # an upstream contract violation; log + skip rather than
                # silently keying by target_label (would mis-align
                # prev/curr delta comparison).
                target = rel.get("target_character_id")
                if not target:
                    logger.warning(
                        "consistency_checker: relationship entry missing "
                        "target_character_id in %s/%s — skipping",
                        char_id, stage_id)
                    continue
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
                                c.checked += 1
                                events = rel.get("driving_events", [])
                                if not events:
                                    c.hit += 1
                                    issues.append(ConsistencyIssue(
                                        "warning", "relationship",
                                        f"{char_id}/{stage_id}/{target}",
                                        f"'{fld}' changed from '{old_val}' to "
                                        f"'{new_val}' without driving_events",
                                        layer="aux"))

            prev_rels = curr_rels

    return issues


def _check_memory_id_correspondence(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
    cov: Coverage,
) -> list[ConsistencyIssue]:
    """Verify memory_digest.jsonl ↔ memory_timeline memory_id correspondence."""
    c = cov.check("memory_id_correspondence", "L2")
    issues: list[ConsistencyIssue] = []

    for char_id in character_ids:
        # Collect all memory_ids from timeline files
        timeline_ids: set[str] = set()
        for stage_id in stage_ids:
            timeline = _load_json_array(
                _timeline_path(work_dir, char_id, stage_id))
            if timeline is None:
                c.skipped += 1
                c.skipped_targets.append(f"{char_id}/{stage_id}")
                continue
            c.checked += 1
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
            c.hit += 1
            issues.append(ConsistencyIssue(
                "error", "memory_id", f"{char_id}/memory_digest",
                f"memory_id '{mid}' in timeline but missing from digest",
                layer="L2"))

        for mid in orphan_in_digest:
            c.hit += 1
            issues.append(ConsistencyIssue(
                "warning", "memory_id", f"{char_id}/memory_digest",
                f"memory_id '{mid}' in digest but not in any timeline",
                layer="L2"))

    return issues


def _check_memory_digest_summary_equality(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
    cov: Coverage,
) -> list[ConsistencyIssue]:
    """Verify memory_digest.summary == timeline.digest_summary (1:1 text).

    Decisions §33 requires memory_digest entries to be a literal 1:1 copy
    of the matching memory_timeline ``digest_summary``. Post-processing
    writes them that way; if repair later rewrites ``digest_summary``
    but post-processing is not re-run, the two drift. Compare by
    ``memory_id`` and flag any text mismatch as an error.
    """
    c = cov.check("memory_digest_summary_equality", "L2")
    issues: list[ConsistencyIssue] = []

    for char_id in character_ids:
        timeline_by_id: dict[str, str] = {}
        for stage_id in stage_ids:
            timeline = _load_json_array(
                _timeline_path(work_dir, char_id, stage_id))
            if timeline is None:
                c.skipped += 1
                c.skipped_targets.append(f"{char_id}/{stage_id}")
                continue
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
            c.checked += 1
            if summary != timeline_by_id[mid]:
                c.hit += 1
                issues.append(ConsistencyIssue(
                    "error", "memory_digest_summary",
                    f"{char_id}/memory_digest/{mid}",
                    "memory_digest.summary != memory_timeline.digest_summary "
                    "(1:1 copy contract violated; re-run post-processing)",
                    layer="L2"))

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
    cov: Coverage | None = None,
) -> list[ConsistencyIssue]:
    """Verify target maps have enough examples.

    Thresholds based on character importance from candidate_characters:
    main ≥5, important supporting ≥3, others ≥1.
    """
    c = (cov or Coverage()).check("target_map_counts", "aux")
    issues: list[ConsistencyIssue] = []
    imp = importance_map or {}

    for char_id in character_ids:
        for stage_id in stage_ids:
            snapshot = _load_json(_snapshot_path(work_dir, char_id, stage_id))
            if snapshot is None:
                c.skipped += 1
                c.skipped_targets.append(f"{char_id}/{stage_id}")
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
                target = (entry.get("target_character_id")
                          or entry.get("target_type") or "?")
                examples = entry.get("dialogue_examples", [])
                # Never-appeared baseline targets keep an empty entry
                # (D4 state 3); skip threshold to avoid false positives.
                if len(examples) == 0:
                    continue
                c.checked += 1
                min_ex = _min_examples_for_target(target, imp)
                if len(examples) >= min_ex:
                    continue
                json_path = (f"$.voice_state.target_voice_map[{idx}]"
                             f".dialogue_examples")
                if json_path in accepted_paths:
                    continue
                c.hit += 1
                issues.append(ConsistencyIssue(
                    "warning", "target_map",
                    f"{char_id}/{stage_id}/voice/{target}",
                    f"target_voice_map has {len(examples)} "
                    f"dialogue_examples (want >={min_ex})", layer="aux"))

            # target_behavior_map
            behavior_state = snapshot.get("behavior_state", {})
            for idx, entry in enumerate(
                    behavior_state.get("target_behavior_map", [])):
                target = (entry.get("target_character_id")
                          or entry.get("target_type") or "?")
                examples = entry.get("action_examples", [])
                if len(examples) == 0:
                    continue
                c.checked += 1
                min_ex = _min_examples_for_target(target, imp)
                if len(examples) >= min_ex:
                    continue
                json_path = (f"$.behavior_state.target_behavior_map[{idx}]"
                             f".action_examples")
                if json_path in accepted_paths:
                    continue
                c.hit += 1
                issues.append(ConsistencyIssue(
                    "warning", "target_map",
                    f"{char_id}/{stage_id}/behavior/{target}",
                    f"target_behavior_map has {len(examples)} "
                    f"action_examples (want >={min_ex})", layer="aux"))

    return issues


def _check_stage_id_alignment(
    work_dir: Path, character_ids: list[str], stage_ids: list[str],
    cov: Coverage,
) -> list[ConsistencyIssue]:
    """Verify world/character stage_catalogs and snapshot dirs are aligned."""
    c = cov.check("stage_id_alignment", "L1")
    issues: list[ConsistencyIssue] = []
    expected = set(stage_ids)

    # World catalog
    world_catalog = _load_json(work_dir / "world" / "stage_catalog.json")
    if world_catalog is None:
        c.skipped += 1
        c.skipped_targets.append("world/stage_catalog.json")
    else:
        c.checked += 1
        world_stages = {s.get("stage_id")
                        for s in world_catalog.get("stages", [])}
        for sid in expected - world_stages:
            c.hit += 1
            issues.append(ConsistencyIssue(
                "error", "stage_alignment", "world/stage_catalog",
                f"stage_id '{sid}' missing from world stage_catalog",
                layer="L1"))

    # World snapshots directory
    world_snap_dir = work_dir / "world" / "stage_snapshots"
    if not world_snap_dir.exists():
        c.skipped += 1
        c.skipped_targets.append("world/stage_snapshots/")
    else:
        c.checked += 1
        world_files = {p.stem for p in world_snap_dir.glob("*.json")}
        for sid in expected - world_files:
            c.hit += 1
            issues.append(ConsistencyIssue(
                "error", "stage_alignment", "world/stage_snapshots",
                f"stage_snapshot file missing for '{sid}'", layer="L1"))

    # Character catalogs and snapshots
    for char_id in character_ids:
        char_dir = work_dir / "characters" / char_id / "canon"

        catalog = _load_json(char_dir / "stage_catalog.json")
        if catalog is None:
            c.skipped += 1
            c.skipped_targets.append(f"{char_id}/stage_catalog.json")
        else:
            c.checked += 1
            char_stages = {s.get("stage_id")
                           for s in catalog.get("stages", [])}
            for sid in expected - char_stages:
                c.hit += 1
                issues.append(ConsistencyIssue(
                    "error", "stage_alignment",
                    f"{char_id}/stage_catalog",
                    f"stage_id '{sid}' missing from character stage_catalog",
                    layer="L1"))

        snap_dir = char_dir / "stage_snapshots"
        if not snap_dir.exists():
            c.skipped += 1
            c.skipped_targets.append(f"{char_id}/stage_snapshots/")
        else:
            c.checked += 1
            char_files = {p.stem for p in snap_dir.glob("*.json")}
            for sid in expected - char_files:
                c.hit += 1
                issues.append(ConsistencyIssue(
                    "error", "stage_alignment",
                    f"{char_id}/stage_snapshots",
                    f"stage_snapshot file missing for '{sid}'", layer="L1"))

    return issues


def _check_world_event_digest(
    work_dir: Path, stage_ids: list[str], cov: Coverage,
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

    c = cov.check("world_event_digest", "L2")
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
            c.skipped += 1
            c.skipped_targets.append(f"world/{stage_id}")
            continue
        c.checked += 1

        stage_events = snapshot.get("stage_events", [])
        n_events = len([e for e in stage_events
                        if isinstance(e, str) and e.strip()])

        snum = _stage_num(stage_id)
        stage_digest = (digest_by_stage_num.get(snum, [])
                        if snum is not None else [])

        if not stage_digest and n_events > 0:
            c.hit += 1
            issues.append(ConsistencyIssue(
                "error", "world_event_digest",
                f"world/{stage_id}",
                f"world_event_digest has no entries for stage "
                f"(expected {n_events} from stage_events)", layer="L2"))
        elif len(stage_digest) != n_events:
            c.hit += 1
            issues.append(ConsistencyIssue(
                "error", "world_event_digest",
                f"world/{stage_id}",
                f"world_event_digest has {len(stage_digest)} entries "
                f"but stage_events has {n_events} items "
                f"(1:1 mapping required)", layer="L2"))

    return issues


def _check_world_event_digest_summary_equality(
    work_dir: Path, stage_ids: list[str], cov: Coverage,
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

    c = cov.check("world_event_digest_summary_equality", "L2")
    issues: list[ConsistencyIssue] = []
    for stage_id in stage_ids:
        snap_path = work_dir / "world" / "stage_snapshots" / f"{stage_id}.json"
        snapshot = _load_json(snap_path)
        if snapshot is None:
            c.skipped += 1
            c.skipped_targets.append(f"world/{stage_id}")
            continue
        stage_events = snapshot.get("stage_events", [])
        if not isinstance(stage_events, list):
            c.skipped += 1
            c.skipped_targets.append(f"world/{stage_id}:stage_events")
            continue
        for i, event_text in enumerate(stage_events):
            if not isinstance(event_text, str) or not event_text.strip():
                continue
            expected = event_text.strip()
            actual = digest_by_stage_seq.get((stage_id, i + 1))
            if actual is None:
                continue
            c.checked += 1
            if actual != expected:
                c.hit += 1
                issues.append(ConsistencyIssue(
                    "error", "world_event_digest_summary",
                    f"world/{stage_id}/E-{stage_id}-{i + 1:02d}",
                    "world_event_digest.summary != stage_events[i] "
                    "(1:1 copy contract violated; re-run post-processing)",
                    layer="L2"))

    return issues
