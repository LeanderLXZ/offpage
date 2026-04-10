"""Parallel review lanes and commit gate for Phase 3 batch extraction.

After extraction + programmatic post-processing, each entity (world +
each character) is validated/reviewed/fixed independently in parallel
"review lanes" (审校通道). A final commit gate (提交门控) checks
cross-entity consistency before allowing batch commit.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_backend import LLMBackend
    from .progress import BatchEntry, PipelineProgress

logger = logging.getLogger(__name__)


@dataclass
class LaneResult:
    """Result of a single review lane."""
    lane_id: str          # "world" or character_id
    lane_type: str        # "world" or "character"
    passed: bool
    verdict_text: str = ""
    findings: str = ""
    error: str = ""


def run_parallel_review(
    project_root: Path,
    progress: "PipelineProgress",
    batch: "BatchEntry",
    backend: "LLMBackend",
    reviewer_backend: "LLMBackend",
    *,
    validate_fn,
    build_reviewer_fn,
    build_fix_fn,
    parse_verdict_fn,
    is_fixable_fn,
    run_with_retry_fn,
) -> list[LaneResult]:
    """Run review lanes in parallel for all entities in a batch.

    Each lane: validate → review → (optional) fix → re-validate/re-review.

    Args:
        validate_fn: callable(project_root, work_id, stage_id, char_ids, lane_type, lane_char_id) → report
        build_reviewer_fn: callable(project_root, progress, batch, report_str, lane_type, lane_char_id) → prompt
        build_fix_fn: callable(project_root, progress, batch, findings, lane_type, lane_char_id) → prompt
        parse_verdict_fn: callable(text) → {"verdict": str, "findings": str}
        is_fixable_fn: callable(verdict) → bool
        run_with_retry_fn: callable(backend, prompt, timeout_seconds) → LLMResult

    Returns list of LaneResult (one per lane).
    """
    lanes: list[tuple[str, str]] = []  # (lane_id, lane_type)

    # World lane
    lanes.append(("world", "world"))

    # Character lanes
    for char_id in progress.target_characters:
        lanes.append((char_id, "character"))

    results: list[LaneResult] = []

    def _run_lane(lane_id: str, lane_type: str) -> LaneResult:
        return _execute_single_lane(
            lane_id=lane_id,
            lane_type=lane_type,
            project_root=project_root,
            progress=progress,
            batch=batch,
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
    batch: "BatchEntry",
    backend: "LLMBackend",
    reviewer_backend: "LLMBackend",
    validate_fn,
    build_reviewer_fn,
    build_fix_fn,
    parse_verdict_fn,
    is_fixable_fn,
    run_with_retry_fn,
) -> LaneResult:
    """Execute a single review lane: validate → review → fix → re-check."""
    lane_char = lane_id if lane_type == "character" else None
    lane_label = f"[{lane_type}:{lane_id}]"

    # --- Step 1: Programmatic validation ---
    char_ids = ([lane_char] if lane_char else [])
    report = validate_fn(
        project_root, progress.work_id, batch.stage_id,
        char_ids, lane_type, lane_char)

    if not report.passed:
        logger.info("%s Programmatic validation FAIL: %s",
                    lane_label, report.summary())
        return LaneResult(
            lane_id=lane_id, lane_type=lane_type,
            passed=False,
            findings=("Programmatic validation failures:\n" +
                      "\n".join(str(i) for i in report.issues
                               if i.severity == "error")))

    # --- Step 2: Semantic review ---
    reviewer_prompt = build_reviewer_fn(
        project_root, progress, batch, report.summary(),
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

    # --- Step 3: FAIL — attempt targeted fix if fixable ---
    findings = verdict.get("findings", "")
    logger.info("%s Semantic review FAIL: %s", lane_label, findings[:300])

    if not is_fixable_fn(verdict):
        logger.info("%s Systemic issue, not fixable", lane_label)
        return LaneResult(
            lane_id=lane_id, lane_type=lane_type,
            passed=False, findings=findings)

    logger.info("%s Attempting targeted fix...", lane_label)
    fix_prompt = build_fix_fn(
        project_root, progress, batch, findings,
        lane_type=lane_type, lane_character_id=lane_char)

    fix_result = run_with_retry_fn(
        backend, fix_prompt, timeout_seconds=600)

    if not fix_result.success:
        logger.error("%s Targeted fix failed: %s",
                     lane_label, fix_result.error)
        return LaneResult(
            lane_id=lane_id, lane_type=lane_type,
            passed=False, error=f"Fix failed: {fix_result.error}")

    # --- Step 4: Re-run semantic review after fix ---
    re_report = validate_fn(
        project_root, progress.work_id, batch.stage_id,
        char_ids, lane_type, lane_char)

    re_reviewer_prompt = build_reviewer_fn(
        project_root, progress, batch, re_report.summary(),
        lane_type=lane_type, lane_character_id=lane_char)

    re_review = run_with_retry_fn(
        reviewer_backend, re_reviewer_prompt, timeout_seconds=600)

    if not re_review.success:
        logger.error("%s Re-review failed: %s",
                     lane_label, re_review.error)
        return LaneResult(
            lane_id=lane_id, lane_type=lane_type,
            passed=False, error=f"Re-review error: {re_review.error}")

    re_verdict = parse_verdict_fn(re_review.text)
    if re_verdict["verdict"] == "PASS":
        logger.info("%s Fix successful, re-review PASS", lane_label)
        return LaneResult(
            lane_id=lane_id, lane_type=lane_type,
            passed=True, verdict_text=re_review.text)
    else:
        logger.info("%s Fix unsuccessful, still FAIL", lane_label)
        return LaneResult(
            lane_id=lane_id, lane_type=lane_type,
            passed=False,
            findings=re_verdict.get("findings", findings))


# ---------------------------------------------------------------------------
# Commit gate (提交门控)
# ---------------------------------------------------------------------------

def run_commit_gate(
    project_root: Path,
    work_id: str,
    stage_id: str,
    character_ids: list[str],
    lane_results: list[LaneResult],
) -> tuple[bool, list[str]]:
    """Run the commit gate after all review lanes complete.

    Checks:
    1. All lanes passed
    2. World-character stage_id alignment
    3. Cross-entity consistency (programmatic)
    4. Programmatically-maintained files (digest, catalog) are valid

    Returns (passed, list_of_issues).
    """
    issues: list[str] = []
    work_dir = project_root / "works" / work_id

    # --- Check 1: All lanes passed ---
    failed_lanes = [r for r in lane_results if not r.passed]
    if failed_lanes:
        for r in failed_lanes:
            msg = r.error or r.findings or "unknown failure"
            issues.append(
                f"审校通道 [{r.lane_type}:{r.lane_id}] 未通过: "
                f"{msg[:200]}")
        return False, issues

    # --- Check 2: stage_id alignment ---
    world_snapshot = (work_dir / "world" / "stage_snapshots"
                      / f"{stage_id}.json")
    if not world_snapshot.exists():
        issues.append(f"世界快照缺失: {world_snapshot}")
    for char_id in character_ids:
        char_snapshot = (work_dir / "characters" / char_id / "canon"
                         / "stage_snapshots" / f"{stage_id}.json")
        if not char_snapshot.exists():
            issues.append(f"角色快照缺失: {char_snapshot}")

    # --- Check 3: Cross-consistency (lightweight programmatic) ---
    if world_snapshot.exists():
        try:
            ws_data = json.loads(
                world_snapshot.read_text(encoding="utf-8"))
            ws_stage = ws_data.get("stage_id", "")
            if ws_stage != stage_id:
                issues.append(
                    f"世界快照 stage_id 不匹配: "
                    f"expected={stage_id}, got={ws_stage}")
        except (json.JSONDecodeError, ValueError):
            issues.append(f"世界快照 JSON 解析失败: {world_snapshot}")

    for char_id in character_ids:
        char_snap_path = (work_dir / "characters" / char_id / "canon"
                          / "stage_snapshots" / f"{stage_id}.json")
        if char_snap_path.exists():
            try:
                cs_data = json.loads(
                    char_snap_path.read_text(encoding="utf-8"))
                cs_stage = cs_data.get("stage_id", "")
                if cs_stage != stage_id:
                    issues.append(
                        f"[{char_id}] 角色快照 stage_id 不匹配: "
                        f"expected={stage_id}, got={cs_stage}")
            except (json.JSONDecodeError, ValueError):
                issues.append(
                    f"[{char_id}] 角色快照 JSON 解析失败")

    # --- Check 4: Programmatically-maintained files exist ---
    schema_dir = project_root / "schemas"

    world_catalog = work_dir / "world" / "stage_catalog.json"
    if world_catalog.exists():
        _validate_catalog_has_stage(world_catalog, stage_id, issues,
                                    "world")

    for char_id in character_ids:
        char_dir = work_dir / "characters" / char_id / "canon"
        char_catalog = char_dir / "stage_catalog.json"
        if char_catalog.exists():
            _validate_catalog_has_stage(char_catalog, stage_id, issues,
                                        char_id)
        digest = char_dir / "memory_digest.jsonl"
        if digest.exists():
            _validate_digest_has_stage(digest, stage_id, issues, char_id)

    passed = len(issues) == 0
    return passed, issues


def _validate_catalog_has_stage(
    catalog_path: Path, stage_id: str,
    issues: list[str], label: str,
) -> None:
    """Check that a stage_catalog contains an entry for the given stage."""
    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        stages = data.get("stages", [])
        found = any(s.get("stage_id") == stage_id for s in stages)
        if not found:
            issues.append(
                f"[{label}] stage_catalog 缺少 stage_id={stage_id} 的条目")
    except (json.JSONDecodeError, ValueError):
        issues.append(f"[{label}] stage_catalog JSON 解析失败")


def _validate_digest_has_stage(
    digest_path: Path, stage_id: str,
    issues: list[str], label: str,
) -> None:
    """Check that memory_digest contains entries for the given stage."""
    try:
        text = digest_path.read_text(encoding="utf-8").strip()
        if not text:
            issues.append(f"[{label}] memory_digest.jsonl 为空")
            return
        found = False
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("stage_id") == stage_id:
                    found = True
                    break
            except json.JSONDecodeError:
                continue
        if not found:
            issues.append(
                f"[{label}] memory_digest 缺少 stage_id={stage_id} 的条目")
    except (OSError, ValueError):
        issues.append(f"[{label}] memory_digest.jsonl 读取失败")
