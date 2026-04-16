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
    lane_type: str        # "world" or "character"
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

    elif lane_type == "character" and lane_char:
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
) -> list[LaneResult]:
    """Run review lanes in parallel for all entities in a stage.

    Each lane: validate → review → (optional) fix → re-validate/re-review.

    Args:
        validate_fn: callable(project_root, work_id, stage_id, char_ids, lane_type, lane_char_id) → report
        build_reviewer_fn: callable(project_root, progress, stage, report_str, lane_type, lane_char_id) → prompt
        build_fix_fn: callable(project_root, progress, stage, findings, lane_type, lane_char_id) → prompt
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
) -> LaneResult:
    """Execute a single review lane: validate → review → fix → re-check."""
    lane_char = lane_id if lane_type == "character" else None
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
        project_root, progress, stage, findings,
        lane_type=lane_type, lane_character_id=lane_char)

    fix_result = run_with_retry_fn(
        backend, fix_prompt, timeout_seconds=600)

    if not fix_result.success:
        logger.error("%s Targeted fix failed: %s",
                     lane_label, fix_result.error)
        return LaneResult(
            lane_id=lane_id, lane_type=lane_type,
            passed=False, error=f"Fix failed: {fix_result.error}")

    # --- Step 4: Re-validate + re-review after fix ---
    re_report = validate_fn(
        project_root, progress.work_id, stage.stage_id,
        char_ids, lane_type, lane_char)

    # Gate: if programmatic validation still fails after fix, don't bother
    # with semantic review — the fix introduced structural/schema errors.
    if not re_report.passed:
        logger.warning("%s Post-fix validation still FAIL: %s",
                       lane_label, re_report.summary())
        return LaneResult(
            lane_id=lane_id, lane_type=lane_type,
            passed=False,
            error=f"Post-fix validation failed: {re_report.summary()}")

    re_reviewer_prompt = build_reviewer_fn(
        project_root, progress, stage, re_report.summary(),
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

    Scope: structural + identifier-level 一致性 only. Content-level cross-entity
    conflicts (world settings vs character cognition) are the character lane
    semantic reviewer's job (§11.4b in requirements). This gate is a zero-token
    last-line guard, not a replacement for semantic review.

    Checks:
    1. All lanes passed
    2. World + character snapshot files exist
    3. ``stage_id`` field in each snapshot matches current stage_id
    4. ``stage_catalog.json`` (world + per-character) contains current stage
    5. Each character's ``memory_digest.jsonl`` has entries for current stage
       (stage encoded in ``memory_id`` prefix; digest entries carry NO
       ``stage_id`` field per memory_digest_entry.schema.json)
    6. Lightweight cross-entity reference check (warn-only): names referenced
       in world snapshot ``relationship_shifts`` / ``character_status_changes``
       should resolve via world cast or active character aliases

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

    # --- Check 5: Lightweight cross-entity reference resolution (warn-only) ---
    # Resolve character names mentioned in world snapshot's relationship_shifts
    # and character_status_changes against (a) world cast roster, (b) active
    # character aliases. Failures are WARNINGS — the character may legitimately
    # be out of the user's active extraction scope. We log the warnings into
    # issues but do NOT fail the gate on reference misses; the content-level
    # truth is enforced by the character lane semantic reviewer.
    if world_snapshot.exists():
        warnings = _cross_entity_reference_warnings(
            work_dir, world_snapshot, character_ids)
        for w in warnings:
            issues.append(f"[WARN] {w}")

    # Warnings (prefixed ``[WARN]``) do NOT fail the gate.
    hard_issues = [i for i in issues if not i.startswith("[WARN]")]
    passed = len(hard_issues) == 0
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
    """Check that memory_digest contains entries for the given stage.

    Stage is encoded in the ``memory_id`` prefix (``M-S{stage:03d}-{seq:02d}``).
    ``memory_digest_entry.schema.json`` does NOT permit a ``stage_id`` field,
    so we parse the stage segment out of the ID instead.
    """
    try:
        text = digest_path.read_text(encoding="utf-8").strip()
        if not text:
            issues.append(f"[{label}] memory_digest.jsonl 为空")
            return
        stage_num = _parse_stage_number(stage_id)
        if stage_num == 0:
            issues.append(
                f"[{label}] 无法从 stage_id='{stage_id}' 中提取阶段数字")
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
            issues.append(
                f"[{label}] memory_digest 缺少阶段 S{stage_num:03d} 的条目")
    except (OSError, ValueError):
        issues.append(f"[{label}] memory_digest.jsonl 读取失败")


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
