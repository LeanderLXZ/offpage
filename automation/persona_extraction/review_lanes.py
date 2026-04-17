"""Parallel review lanes and commit gate for Phase 3 stage extraction.

After extraction + programmatic post-processing, each entity (world +
each character) is validated/reviewed/fixed independently in parallel
"review lanes" (审校通道). A final commit gate (提交门控) checks
cross-entity consistency before allowing stage commit.
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .post_processing import _parse_stage_number, _stage_from_id
from .schema_autofix import attempt_schema_autofix

if TYPE_CHECKING:
    from .llm_backend import LLMBackend
    from .progress import StageEntry, PipelineProgress

logger = logging.getLogger(__name__)


@dataclass
class LaneResult:
    """Result of a single review lane."""
    lane_id: str          # "world" or character_id
    lane_type: str        # "world", "char_snapshot", or "char_support"
    passed: bool
    verdict_text: str = ""
    findings: str = ""
    error: str = ""


def _attempt_lane_autofix(
    project_root: Path,
    work_id: str,
    stage_id: str,
    lane_type: str,
    lane_char: str | None,
) -> bool:
    """Run schema autofix on all files validated by a lane.

    Returns True if at least one fix was applied.
    """
    schema_dir = project_root / "schemas"
    work_dir = project_root / "works" / work_id
    any_fixed = False

    if lane_type == "world":
        # World stage snapshot
        world_snap = (work_dir / "world" / "stage_snapshots"
                      / f"{stage_id}.json")
        world_schema = schema_dir / "world_stage_snapshot.schema.json"
        if world_snap.exists() and world_schema.exists():
            fixed, descs = attempt_schema_autofix(world_snap, world_schema)
            if fixed:
                any_fixed = True
                for d in descs:
                    logger.info("  autofix [world snapshot]: %s", d)

    elif lane_type == "char_snapshot" and lane_char:
        char_dir = work_dir / "characters" / lane_char / "canon"

        # Character stage snapshot
        char_snap = char_dir / "stage_snapshots" / f"{stage_id}.json"
        snap_schema = schema_dir / "stage_snapshot.schema.json"
        if char_snap.exists() and snap_schema.exists():
            fixed, descs = attempt_schema_autofix(char_snap, snap_schema)
            if fixed:
                any_fixed = True
                for d in descs:
                    logger.info("  autofix [%s snapshot]: %s", lane_char, d)

    elif lane_type == "char_support" and lane_char:
        char_dir = work_dir / "characters" / lane_char / "canon"

        # Memory timeline
        mem_path = char_dir / "memory_timeline" / f"{stage_id}.json"
        mem_schema = schema_dir / "memory_timeline_entry.schema.json"
        if mem_path.exists() and mem_schema.exists():
            # memory_timeline is a JSON array of entries — autofix each entry
            try:
                entries = json.loads(
                    mem_path.read_text(encoding="utf-8"))
                if isinstance(entries, list):
                    entry_fixed = False
                    schema_data = json.loads(
                        mem_schema.read_text(encoding="utf-8"))
                    from .schema_autofix import (
                        _apply_fix, _collect_all_errors,
                    )
                    for entry in entries:
                        if isinstance(entry, dict):
                            # _collect_all_errors sorts deepest-first
                            errs = _collect_all_errors(entry, schema_data)
                            for err in errs:
                                result = _apply_fix(entry, schema_data,
                                                    err)
                                if result:
                                    entry_fixed = True
                                    logger.info(
                                        "  autofix [%s memory]: %s",
                                        lane_char, result)
                    if entry_fixed:
                        any_fixed = True
                        mem_path.write_text(
                            json.dumps(entries, ensure_ascii=False,
                                       indent=2) + "\n",
                            encoding="utf-8")
            except (json.JSONDecodeError, OSError):
                pass

    return any_fixed


def lane_key(lane_type: str, lane_id: str) -> str:
    """Canonical lane identifier used for retry bookkeeping and rollback.

    Format:
      - ``"world"`` for the world lane (there is exactly one)
      - ``"char_snapshot:{char_id}"`` for each character snapshot lane
      - ``"char_support:{char_id}"`` for each character support lane

    This matches the keys used by ``StageEntry.lane_retries`` and the
    ``lane_filter`` argument of :func:`run_parallel_review`.
    """
    if lane_type == "world":
        return "world"
    return f"{lane_type}:{lane_id}"


def rollback_lane_files(
    project_root: Path,
    work_id: str,
    stage_id: str,
    lane_type: str,
    lane_char: str | None,
) -> list[Path]:
    """Delete the on-disk artifacts owned by a single review lane.

    Per the writer-boundary rule (§11.4b), each lane writes exactly one
    set of files:

    - **world lane**: ``world/stage_snapshots/{stage_id}.json``
    - **char_snapshot lane**: ``characters/{char}/canon/stage_snapshots/{stage_id}.json``
    - **char_support lane**: ``characters/{char}/canon/memory_timeline/{stage_id}.json``
      + git-restore any modified baseline files for that character

    Cumulative products (``memory_digest.jsonl``, ``world_event_digest.jsonl``,
    ``stage_catalog.json``) are **not** touched here: post-processing is
    idempotent and upserts only the entries for the current stage, so
    re-running it after a lane re-extraction safely overwrites the stale
    entries for this stage while preserving data from other stages and
    other lanes.

    Returns the list of files that were actually removed (for logging).
    """
    import subprocess

    work_dir = project_root / "works" / work_id
    removed: list[Path] = []

    if lane_type == "world":
        world_snap = (work_dir / "world" / "stage_snapshots"
                      / f"{stage_id}.json")
        if world_snap.exists():
            world_snap.unlink()
            removed.append(world_snap)
    elif lane_type == "char_snapshot" and lane_char:
        char_snap = (work_dir / "characters" / lane_char / "canon"
                     / "stage_snapshots" / f"{stage_id}.json")
        if char_snap.exists():
            char_snap.unlink()
            removed.append(char_snap)
    elif lane_type == "char_support" and lane_char:
        # Delete memory_timeline for this stage
        mt = (work_dir / "characters" / lane_char / "canon"
              / "memory_timeline" / f"{stage_id}.json")
        if mt.exists():
            mt.unlink()
            removed.append(mt)
        # Restore baseline files via git checkout HEAD
        char_canon = work_dir / "characters" / lane_char / "canon"
        baseline_files = [
            "identity.json", "voice_rules.json", "behavior_rules.json",
            "boundaries.json", "failure_modes.json", "manifest.json",
        ]
        for name in baseline_files:
            p = char_canon / name
            if p.exists():
                try:
                    subprocess.run(
                        ["git", "checkout", "HEAD", "--", str(p)],
                        cwd=str(project_root),
                        capture_output=True, timeout=10)
                except Exception:
                    pass  # best-effort restore

    for p in removed:
        logger.info("  [lane rollback] removed %s", p)
    return removed


def run_parallel_review(
    project_root: Path,
    progress: "PipelineProgress",
    stage: "StageEntry",
    backend: "LLMBackend",
    reviewer_backend: "LLMBackend",
    *,
    validate_fn,
    build_reviewer_fn,
    build_fix_fn,
    parse_verdict_fn,
    is_fixable_fn,
    run_with_retry_fn,
    lane_filter: list[str] | None = None,
) -> list[LaneResult]:
    """Run review lanes in parallel for the entities in a stage.

    Each lane: validate → review → (optional) fix → re-validate/re-review.

    Args:
        validate_fn: callable(project_root, work_id, stage_id, char_ids, lane_type, lane_char_id) → report
        build_reviewer_fn: callable(project_root, progress, stage, report_str, lane_type, lane_char_id) → prompt
        build_fix_fn: callable(project_root, progress, stage, findings, lane_type, lane_char_id) → prompt
        parse_verdict_fn: callable(text) → {"verdict": str, "findings": str}
        is_fixable_fn: callable(verdict) → bool
        run_with_retry_fn: callable(backend, prompt, timeout_seconds) → LLMResult
        lane_filter: optional list of :func:`lane_key` values to run; when
            given, only those lanes execute (used by lane-independent retry
            to review only the lanes that were just re-extracted, while
            preserving earlier PASS results for the rest).

    Returns list of LaneResult (one per lane that actually ran).
    """
    lanes: list[tuple[str, str]] = []  # (lane_id, lane_type)

    # World lane
    lanes.append(("world", "world"))

    # Character lanes — 2 per character (snapshot + support)
    for char_id in progress.target_characters:
        lanes.append((char_id, "char_snapshot"))
        lanes.append((char_id, "char_support"))

    if lane_filter is not None:
        allowed = set(lane_filter)
        lanes = [(lid, ltype) for lid, ltype in lanes
                 if lane_key(ltype, lid) in allowed]
        if not lanes:
            return []

    results: list[LaneResult] = []

    def _run_lane(lane_id: str, lane_type: str) -> LaneResult:
        return _execute_single_lane(
            lane_id=lane_id,
            lane_type=lane_type,
            project_root=project_root,
            progress=progress,
            stage=stage,
            backend=backend,
            reviewer_backend=reviewer_backend,
            validate_fn=validate_fn,
            build_reviewer_fn=build_reviewer_fn,
            build_fix_fn=build_fix_fn,
            parse_verdict_fn=parse_verdict_fn,
            is_fixable_fn=is_fixable_fn,
            run_with_retry_fn=run_with_retry_fn,
        )

    n_lanes = len(lanes)
    with ThreadPoolExecutor(max_workers=n_lanes) as executor:
        futures = {
            executor.submit(_run_lane, lid, ltype): (lid, ltype)
            for lid, ltype in lanes
        }
        for future in as_completed(futures):
            lid, ltype = futures[future]
            try:
                result = future.result()
            except Exception as e:
                logger.error("Lane %s raised exception: %s", lid, e)
                result = LaneResult(
                    lane_id=lid, lane_type=ltype,
                    passed=False, error=str(e))
            results.append(result)

    return results


def _execute_single_lane(
    lane_id: str,
    lane_type: str,
    project_root: Path,
    progress: "PipelineProgress",
    stage: "StageEntry",
    backend: "LLMBackend",
    reviewer_backend: "LLMBackend",
    validate_fn,
    build_reviewer_fn,
    build_fix_fn,
    parse_verdict_fn,
    is_fixable_fn,
    run_with_retry_fn,
    *,
    max_fix_attempts: int = 2,
) -> LaneResult:
    """Execute a single review lane: validate → review → fix(×2) → re-check."""
    lane_char = lane_id if lane_type in ("char_snapshot", "char_support") else None
    lane_label = f"[{lane_type}:{lane_id}]"

    # --- Step 1: Programmatic validation ---
    char_ids = ([lane_char] if lane_char else [])
    report = validate_fn(
        project_root, progress.work_id, stage.stage_id,
        char_ids, lane_type, lane_char)

    if not report.passed:
        logger.info("%s Programmatic validation FAIL: %s",
                    lane_label, report.summary())

        # --- Step 1b: Attempt schema autofix (0 tokens, <1s) ---
        fix_applied = _attempt_lane_autofix(
            project_root, progress.work_id, stage.stage_id,
            lane_type, lane_char)
        if fix_applied:
            report = validate_fn(
                project_root, progress.work_id, stage.stage_id,
                char_ids, lane_type, lane_char)
            if report.passed:
                logger.info("%s Schema autofix resolved all errors",
                            lane_label)
            else:
                logger.info("%s Schema autofix helped but %d error(s) remain",
                            lane_label,
                            sum(1 for i in report.issues
                                if i.severity == "error"))
                return LaneResult(
                    lane_id=lane_id, lane_type=lane_type,
                    passed=False,
                    findings=(
                        "Programmatic validation failures "
                        "(after schema autofix):\n" +
                        "\n".join(str(i) for i in report.issues
                                 if i.severity == "error")))
        else:
            return LaneResult(
                lane_id=lane_id, lane_type=lane_type,
                passed=False,
                findings=(
                    "Programmatic validation failures "
                    "(no autofix applicable):\n" +
                    "\n".join(str(i) for i in report.issues
                             if i.severity == "error")))

    # --- Step 2: Semantic review ---
    reviewer_prompt = build_reviewer_fn(
        project_root, progress, stage, report.summary(),
        lane_type=lane_type, lane_character_id=lane_char)

    review_result = run_with_retry_fn(
        reviewer_backend, reviewer_prompt, timeout_seconds=600)

    if not review_result.success:
        logger.error("%s Review agent failed: %s",
                     lane_label, review_result.error)
        return LaneResult(
            lane_id=lane_id, lane_type=lane_type,
            passed=False, error=f"Review agent error: {review_result.error}")

    verdict = parse_verdict_fn(review_result.text)

    if verdict["verdict"] == "PASS":
        logger.info("%s Semantic review PASS", lane_label)
        return LaneResult(
            lane_id=lane_id, lane_type=lane_type,
            passed=True, verdict_text=review_result.text)

    # --- Step 3: FAIL — attempt targeted fix (up to max_fix_attempts) ---
    findings = verdict.get("findings", "")
    logger.info("%s Semantic review FAIL: %s", lane_label, findings[:300])

    if not is_fixable_fn(verdict):
        logger.info("%s Systemic issue, not fixable", lane_label)
        return LaneResult(
            lane_id=lane_id, lane_type=lane_type,
            passed=False, findings=findings)

    accumulated_findings = findings
    for fix_attempt in range(1, max_fix_attempts + 1):
        logger.info("%s Attempting targeted fix %d/%d...",
                    lane_label, fix_attempt, max_fix_attempts)
        fix_prompt = build_fix_fn(
            project_root, progress, stage, accumulated_findings,
            lane_type=lane_type, lane_character_id=lane_char)

        fix_result = run_with_retry_fn(
            backend, fix_prompt, timeout_seconds=600)

        if not fix_result.success:
            logger.error("%s Targeted fix %d failed: %s",
                         lane_label, fix_attempt, fix_result.error)
            return LaneResult(
                lane_id=lane_id, lane_type=lane_type,
                passed=False,
                error=f"Fix {fix_attempt} failed: {fix_result.error}")

        # Re-validate after fix
        re_report = validate_fn(
            project_root, progress.work_id, stage.stage_id,
            char_ids, lane_type, lane_char)

        if not re_report.passed:
            logger.warning("%s Post-fix-%d validation still FAIL: %s",
                           lane_label, fix_attempt, re_report.summary())
            # Don't re-review; accumulate and retry fix
            accumulated_findings = (
                f"Previous findings:\n{accumulated_findings}\n\n"
                f"Post-fix validation errors:\n{re_report.summary()}")
            continue

        # Re-review after fix
        re_reviewer_prompt = build_reviewer_fn(
            project_root, progress, stage, re_report.summary(),
            lane_type=lane_type, lane_character_id=lane_char)

        re_review = run_with_retry_fn(
            reviewer_backend, re_reviewer_prompt, timeout_seconds=600)

        if not re_review.success:
            logger.error("%s Re-review after fix %d failed: %s",
                         lane_label, fix_attempt, re_review.error)
            return LaneResult(
                lane_id=lane_id, lane_type=lane_type,
                passed=False,
                error=f"Re-review error after fix {fix_attempt}: "
                      f"{re_review.error}")

        re_verdict = parse_verdict_fn(re_review.text)
        if re_verdict["verdict"] == "PASS":
            logger.info("%s Fix %d successful, re-review PASS",
                        lane_label, fix_attempt)
            return LaneResult(
                lane_id=lane_id, lane_type=lane_type,
                passed=True, verdict_text=re_review.text)

        # Still FAIL — accumulate findings for next attempt
        new_findings = re_verdict.get("findings", "")
        accumulated_findings = (
            f"Previous findings:\n{accumulated_findings}\n\n"
            f"After fix attempt {fix_attempt}:\n{new_findings}")
        logger.info("%s Fix %d unsuccessful, still FAIL",
                    lane_label, fix_attempt)

    # All fix attempts exhausted
    logger.info("%s All %d fix attempts exhausted, lane FAIL",
                lane_label, max_fix_attempts)
    return LaneResult(
        lane_id=lane_id, lane_type=lane_type,
        passed=False, findings=accumulated_findings)


# ---------------------------------------------------------------------------
# Commit gate (提交门控)
# ---------------------------------------------------------------------------

@dataclass
class GateIssue:
    """A single commit-gate finding with lane attribution and recovery hint.

    Fields:
        message: human-readable issue text (also what gets printed)
        severity: ``"error"`` (fails the gate) or ``"warning"`` (logged only)
        lane_type: ``"world"``, ``"char_snapshot"``, or ``"char_support"`` when the issue is attributable
            to a single lane; ``""`` when it is unattributed (rare — only
            structural failures with no clear owner like ``stage_id`` parse
            failure)
        lane_id: ``"world"`` or character_id matching ``lane_type``;
            ``""`` when unattributed
        category: one of ``"snapshot_missing"``, ``"snapshot_stage_id"``,
            ``"snapshot_parse"``, ``"catalog_missing"``, ``"digest_missing"``,
            ``"lane_review"``, ``"reference_warning"``. Drives the
            orchestrator's recovery cascade — see §11.4b "失败处理 B" in
            ``docs/requirements.md``.
    """
    message: str
    severity: str             # "error" | "warning"
    lane_type: str = ""       # "world" | "char_snapshot" | "char_support" | ""
    lane_id: str = ""         # "world" | char_id | ""
    category: str = ""

    @property
    def lane_key_str(self) -> str:
        """Canonical lane key, or empty string when unattributed."""
        if not self.lane_type:
            return ""
        return lane_key(self.lane_type, self.lane_id)


# Categories that can be repaired by re-running post_processing alone (no LLM).
# Anything else falls through to lane re-extraction or full-stage rollback.
POST_PROCESSING_RECOVERABLE: frozenset[str] = frozenset({
    "catalog_missing",
    "digest_missing",
    "world_event_digest_missing",
})


def run_commit_gate(
    project_root: Path,
    work_id: str,
    stage_id: str,
    character_ids: list[str],
    lane_results: list[LaneResult],
) -> tuple[bool, list[GateIssue]]:
    """Run the commit gate after all review lanes complete.

    Scope: structural + identifier-level 一致性 only. Content-level cross-entity
    conflicts (world settings vs character cognition) are the character lane
    semantic reviewer's job (§11.4b in requirements). This gate is a zero-token
    last-line guard, not a replacement for semantic review.

    Each issue is annotated with ``lane_type`` / ``lane_id`` / ``category`` so
    the orchestrator can route recovery via the same lane-independent retry
    path used by review failures (see §11.4b "失败处理 B" in requirements).

    Checks:
    1. All lanes passed
    2. World + character snapshot files exist
    3. ``stage_id`` field in each snapshot matches current stage_id
    4. ``stage_catalog.json`` (world + per-character) **exists** and contains
       current stage. Missing file → ``catalog_missing`` (post-processing
       recoverable).
    5. Each character's ``memory_digest.jsonl`` **exists** and has entries for
       current stage (stage encoded in ``memory_id`` prefix; digest entries
       carry NO ``stage_id`` field per memory_digest_entry.schema.json).
       Missing file → ``digest_missing`` (post-processing recoverable).
    5b. ``world/world_event_digest.jsonl`` **exists** and has entries for
       current stage (stage encoded in ``event_id`` prefix ``E-S{stage:03d}-``).
       Missing file / empty / no stage entries → ``world_event_digest_missing``
       (post-processing recoverable — post_processing rebuilds from world
       snapshot's ``stage_events``).
    6. Lightweight cross-entity reference check (warn-only): names referenced
       in world snapshot ``relationship_shifts`` / ``character_status_changes``
       should resolve via world cast or active character aliases

    Returns ``(passed, list_of_GateIssue)``. ``passed`` is True iff there are
    no error-severity issues; warnings are present in the list but do not
    affect ``passed``.
    """
    issues: list[GateIssue] = []
    work_dir = project_root / "works" / work_id

    # --- Check 1: All lanes passed ---
    failed_lanes = [r for r in lane_results if not r.passed]
    if failed_lanes:
        for r in failed_lanes:
            msg = r.error or r.findings or "unknown failure"
            issues.append(GateIssue(
                message=(f"审校通道 [{r.lane_type}:{r.lane_id}] 未通过: "
                         f"{msg[:200]}"),
                severity="error",
                lane_type=r.lane_type, lane_id=r.lane_id,
                category="lane_review",
            ))
        return False, issues

    # --- Check 2 + 3: snapshot existence and stage_id alignment ---
    world_snapshot = (work_dir / "world" / "stage_snapshots"
                      / f"{stage_id}.json")
    if not world_snapshot.exists():
        issues.append(GateIssue(
            message=f"世界快照缺失: {world_snapshot}",
            severity="error",
            lane_type="world", lane_id="world",
            category="snapshot_missing",
        ))
    else:
        try:
            ws_data = json.loads(
                world_snapshot.read_text(encoding="utf-8"))
            ws_stage = ws_data.get("stage_id", "")
            if ws_stage != stage_id:
                issues.append(GateIssue(
                    message=(f"世界快照 stage_id 不匹配: "
                             f"expected={stage_id}, got={ws_stage}"),
                    severity="error",
                    lane_type="world", lane_id="world",
                    category="snapshot_stage_id",
                ))
        except (json.JSONDecodeError, ValueError):
            issues.append(GateIssue(
                message=f"世界快照 JSON 解析失败: {world_snapshot}",
                severity="error",
                lane_type="world", lane_id="world",
                category="snapshot_parse",
            ))

    for char_id in character_ids:
        # Check snapshot (owned by char_snapshot lane)
        char_snap_path = (work_dir / "characters" / char_id / "canon"
                          / "stage_snapshots" / f"{stage_id}.json")
        if not char_snap_path.exists():
            issues.append(GateIssue(
                message=f"角色快照缺失: {char_snap_path}",
                severity="error",
                lane_type="char_snapshot", lane_id=char_id,
                category="snapshot_missing",
            ))
        else:
            try:
                cs_data = json.loads(
                    char_snap_path.read_text(encoding="utf-8"))
                cs_stage = cs_data.get("stage_id", "")
                if cs_stage != stage_id:
                    issues.append(GateIssue(
                        message=(f"[{char_id}] 角色快照 stage_id 不匹配: "
                                 f"expected={stage_id}, got={cs_stage}"),
                        severity="error",
                        lane_type="char_snapshot", lane_id=char_id,
                        category="snapshot_stage_id",
                    ))
            except (json.JSONDecodeError, ValueError):
                issues.append(GateIssue(
                    message=f"[{char_id}] 角色快照 JSON 解析失败",
                    severity="error",
                    lane_type="char_snapshot", lane_id=char_id,
                    category="snapshot_parse",
                ))

        # Check memory_timeline existence (owned by char_support lane)
        mt_path = (work_dir / "characters" / char_id / "canon"
                   / "memory_timeline" / f"{stage_id}.json")
        if not mt_path.exists():
            issues.append(GateIssue(
                message=f"[{char_id}] memory_timeline 缺失: {mt_path}",
                severity="error",
                lane_type="char_support", lane_id=char_id,
                category="snapshot_missing",
            ))

    # --- Check 4 + 5 + 5b: programmatically-maintained files ---
    # File existence is a hard gate — post_processing.py is supposed to write
    # these. A missing file here means PP never wrote (or something deleted
    # them); route to a free PP rerun via POST_PROCESSING_RECOVERABLE so the
    # orchestrator recovers without an LLM call.
    world_catalog = work_dir / "world" / "stage_catalog.json"
    if not world_catalog.exists():
        issues.append(GateIssue(
            message=f"world stage_catalog.json 缺失: {world_catalog}",
            severity="error",
            lane_type="world", lane_id="world",
            category="catalog_missing",
        ))
    else:
        _validate_catalog_has_stage(
            world_catalog, stage_id, issues,
            label="world", lane_type="world", lane_id="world")

    world_event_digest = work_dir / "world" / "world_event_digest.jsonl"
    if not world_event_digest.exists():
        issues.append(GateIssue(
            message=(f"world_event_digest.jsonl 缺失: "
                     f"{world_event_digest}"),
            severity="error",
            lane_type="world", lane_id="world",
            category="world_event_digest_missing",
        ))
    else:
        _validate_world_event_digest_has_stage(
            world_event_digest, stage_id, issues,
            lane_type="world", lane_id="world")

    for char_id in character_ids:
        char_dir = work_dir / "characters" / char_id / "canon"
        # Catalog is derived from snapshot → route to char_support for PP rerun
        char_catalog = char_dir / "stage_catalog.json"
        if not char_catalog.exists():
            issues.append(GateIssue(
                message=f"[{char_id}] stage_catalog.json 缺失: {char_catalog}",
                severity="error",
                lane_type="char_support", lane_id=char_id,
                category="catalog_missing",
            ))
        else:
            _validate_catalog_has_stage(
                char_catalog, stage_id, issues,
                label=char_id, lane_type="char_support", lane_id=char_id)
        # Digest is derived from memory_timeline → route to char_support
        digest = char_dir / "memory_digest.jsonl"
        if not digest.exists():
            issues.append(GateIssue(
                message=f"[{char_id}] memory_digest.jsonl 缺失: {digest}",
                severity="error",
                lane_type="char_support", lane_id=char_id,
                category="digest_missing",
            ))
        else:
            _validate_digest_has_stage(
                digest, stage_id, issues,
                label=char_id, lane_type="char_support", lane_id=char_id)

    # --- Check 6: cross-entity reference resolution (warn-only) ---
    if world_snapshot.exists():
        warnings = _cross_entity_reference_warnings(
            work_dir, world_snapshot, character_ids)
        for w in warnings:
            issues.append(GateIssue(
                message=w, severity="warning",
                lane_type="world", lane_id="world",
                category="reference_warning",
            ))

    passed = not any(i.severity == "error" for i in issues)
    return passed, issues


def _validate_catalog_has_stage(
    catalog_path: Path, stage_id: str,
    issues: list["GateIssue"],
    *, label: str, lane_type: str, lane_id: str,
) -> None:
    """Check that a stage_catalog contains an entry for the given stage.

    Lane attribution: world catalog → world lane; per-character catalog →
    that character's lane. Both belong to ``catalog_missing`` category,
    which the orchestrator routes to a post_processing rerun before any
    LLM call.
    """
    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        stages = data.get("stages", [])
        found = any(s.get("stage_id") == stage_id for s in stages)
        if not found:
            issues.append(GateIssue(
                message=(f"[{label}] stage_catalog 缺少 "
                         f"stage_id={stage_id} 的条目"),
                severity="error",
                lane_type=lane_type, lane_id=lane_id,
                category="catalog_missing",
            ))
    except (json.JSONDecodeError, ValueError):
        issues.append(GateIssue(
            message=f"[{label}] stage_catalog JSON 解析失败",
            severity="error",
            lane_type=lane_type, lane_id=lane_id,
            category="catalog_missing",
        ))


def _validate_digest_has_stage(
    digest_path: Path, stage_id: str,
    issues: list["GateIssue"],
    *, label: str, lane_type: str, lane_id: str,
) -> None:
    """Check that memory_digest contains entries for the given stage.

    Stage is encoded in the ``memory_id`` prefix (``M-S{stage:03d}-{seq:02d}``).
    ``memory_digest_entry.schema.json`` does NOT permit a ``stage_id`` field,
    so we parse the stage segment out of the ID instead.

    A digest miss is attributed to the owning character lane and routed to
    a post_processing rerun (post_processing rebuilds digest entries from
    the snapshot's ``memory_timeline``, so it can recover whenever the
    snapshot itself is intact).
    """
    try:
        text = digest_path.read_text(encoding="utf-8").strip()
        if not text:
            issues.append(GateIssue(
                message=f"[{label}] memory_digest.jsonl 为空",
                severity="error",
                lane_type=lane_type, lane_id=lane_id,
                category="digest_missing",
            ))
            return
        stage_num = _parse_stage_number(stage_id)
        if stage_num == 0:
            # Unattributed: stage_id parse failure is a Phase 1 / progress
            # bug, not a per-lane fault. Leaves lane fields empty so the
            # orchestrator falls through to full-stage rollback.
            issues.append(GateIssue(
                message=(f"[{label}] 无法从 stage_id='{stage_id}' "
                         f"中提取阶段数字"),
                severity="error",
                category="digest_missing",
            ))
            return
        found = False
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if _stage_from_id(entry.get("memory_id", "")) == stage_num:
                    found = True
                    break
            except json.JSONDecodeError:
                continue
        if not found:
            issues.append(GateIssue(
                message=(f"[{label}] memory_digest 缺少阶段 "
                         f"S{stage_num:03d} 的条目"),
                severity="error",
                lane_type=lane_type, lane_id=lane_id,
                category="digest_missing",
            ))
    except (OSError, ValueError):
        issues.append(GateIssue(
            message=f"[{label}] memory_digest.jsonl 读取失败",
            severity="error",
            lane_type=lane_type, lane_id=lane_id,
            category="digest_missing",
        ))


def _validate_world_event_digest_has_stage(
    digest_path: Path, stage_id: str,
    issues: list["GateIssue"],
    *, lane_type: str, lane_id: str,
) -> None:
    """Check that world_event_digest contains entries for the given stage.

    Stage is encoded in the ``event_id`` prefix (``E-S{stage:03d}-{seq:02d}``),
    mirroring memory_digest (see ``world_event_digest_entry.schema.json``).
    A miss is attributed to the world lane and routed to post_processing,
    which rebuilds the digest from the world snapshot's ``stage_events``.
    """
    try:
        text = digest_path.read_text(encoding="utf-8").strip()
        if not text:
            issues.append(GateIssue(
                message="world_event_digest.jsonl 为空",
                severity="error",
                lane_type=lane_type, lane_id=lane_id,
                category="world_event_digest_missing",
            ))
            return
        stage_num = _parse_stage_number(stage_id)
        if stage_num == 0:
            issues.append(GateIssue(
                message=(f"无法从 stage_id='{stage_id}' 中提取阶段数字 "
                         f"(world_event_digest)"),
                severity="error",
                category="world_event_digest_missing",
            ))
            return
        found = False
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if _stage_from_id(entry.get("event_id", "")) == stage_num:
                    found = True
                    break
            except json.JSONDecodeError:
                continue
        if not found:
            issues.append(GateIssue(
                message=(f"world_event_digest 缺少阶段 "
                         f"S{stage_num:03d} 的条目"),
                severity="error",
                lane_type=lane_type, lane_id=lane_id,
                category="world_event_digest_missing",
            ))
    except (OSError, ValueError):
        issues.append(GateIssue(
            message="world_event_digest.jsonl 读取失败",
            severity="error",
            lane_type=lane_type, lane_id=lane_id,
            category="world_event_digest_missing",
        ))


# ---------------------------------------------------------------------------
# Cross-entity reference resolution (lightweight warn-only)
# ---------------------------------------------------------------------------

# Match CJK-heavy tokens of length ≥ 2. Coarse filter — false positives are
# acceptable since the check is warn-only.
_NAME_TOKEN_RE = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf][\u4e00-\u9fff\u3400-\u4dbfA-Za-z0-9_·]+"
)


def _collect_alias_index(work_dir: Path,
                          character_ids: list[str]) -> set[str]:
    """Collect a set of known names: world cast + active character aliases."""
    names: set[str] = set()

    # World cast names
    cast_dir = work_dir / "world" / "cast"
    if cast_dir.is_dir():
        for cast_file in cast_dir.glob("*.json"):
            try:
                data = json.loads(cast_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError, OSError):
                continue
            # Cast file may be {"characters": [...]}, a list, or nested; walk.
            _walk_names(data, names)

    # Active character identities
    for cid in character_ids:
        identity_path = (work_dir / "characters" / cid / "canon"
                         / "identity.json")
        if not identity_path.exists():
            continue
        try:
            data = json.loads(identity_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError, OSError):
            continue
        # character_id itself counts as a name
        names.add(cid)
        # Names from identity: name_zh/name, aliases[].name
        for key in ("name", "name_zh", "display_name"):
            v = data.get(key)
            if isinstance(v, str) and v:
                names.add(v)
        for alias in data.get("aliases", []) or []:
            if isinstance(alias, dict):
                for k in ("name", "text", "alias"):
                    v = alias.get(k)
                    if isinstance(v, str) and v:
                        names.add(v)
            elif isinstance(alias, str):
                names.add(alias)

    return {n for n in names if len(n) >= 2}


def _walk_names(node, out: set[str]) -> None:
    """Recursively collect plausible-name string fields from a cast record."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("name", "name_zh", "display_name", "alias", "aliases",
                     "text", "character_id"):
                _walk_names(v, out)
            elif isinstance(v, (dict, list)):
                _walk_names(v, out)
    elif isinstance(node, list):
        for item in node:
            _walk_names(item, out)
    elif isinstance(node, str) and node:
        out.add(node)


def _cross_entity_reference_warnings(
    work_dir: Path,
    world_snapshot_path: Path,
    character_ids: list[str],
) -> list[str]:
    """Warn when world snapshot mentions character names not in any roster.

    Reference miss is warn-only: a mentioned character may simply be outside
    the user's active extraction scope. Full content-level cross-consistency
    is owned by the character lane semantic reviewer.
    """
    warnings: list[str] = []
    try:
        snap = json.loads(world_snapshot_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError):
        return warnings  # snapshot parse failure is reported elsewhere

    names = _collect_alias_index(work_dir, character_ids)
    if not names:
        return warnings  # no roster to check against — skip silently

    for field in ("relationship_shifts", "character_status_changes"):
        entries = snap.get(field, []) or []
        for entry in entries:
            if not isinstance(entry, str):
                continue
            tokens = set(_NAME_TOKEN_RE.findall(entry))
            if not tokens:
                continue
            # At least one token must resolve; otherwise flag as unresolved.
            if not any(t in names for t in tokens):
                warnings.append(
                    f"world {field} 条目未找到任何可解析的角色名: "
                    f"'{entry[:60]}'")

    return warnings
