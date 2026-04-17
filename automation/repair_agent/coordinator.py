"""Coordinator — three-phase check → fix → verify orchestration.

Phase A: Full validation (L0–L3 if configured)
Phase B: Fix loop — escalate T0→T1→T2→T3 with scoped recheck
Phase C: Final semantic verify (if Phase A found semantic issues)

Public API:
    run(files, config, ...) → RepairResult
    validate_only(files, ...) → list[Issue]
"""

from __future__ import annotations

import logging
from typing import Callable

from .checkers import CheckerPipeline
from .checkers.json_syntax import JsonSyntaxChecker
from .checkers.schema import SchemaChecker
from .checkers.structural import StructuralChecker
from .checkers.semantic import SemanticChecker
from .fixers.programmatic import ProgrammaticFixer
from .fixers.local_patch import LocalPatchFixer
from .fixers.source_patch import SourcePatchFixer
from .fixers.file_regen import FileRegenFixer
from .protocol import (
    FileEntry,
    Issue,
    RepairAttempt,
    RepairConfig,
    RepairResult,
    SourceContext,
    START_TIER,
)
from .tracker import IssueTracker

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline & fixer factory
# ---------------------------------------------------------------------------

def _build_pipeline(
    llm_call: Callable[..., str] | None = None,
) -> CheckerPipeline:
    pipeline = CheckerPipeline()
    pipeline.register(JsonSyntaxChecker())
    pipeline.register(SchemaChecker())
    pipeline.register(StructuralChecker())
    pipeline.register(SemanticChecker(llm_call=llm_call))
    return pipeline


def _build_fixers(
    llm_call: Callable[..., str] | None = None,
) -> dict[int, object]:
    return {
        0: ProgrammaticFixer(),
        1: LocalPatchFixer(llm_call=llm_call),
        2: SourcePatchFixer(llm_call=llm_call),
        3: FileRegenFixer(llm_call=llm_call),
    }


def _tier_max(config: RepairConfig, tier: int) -> int:
    """Max retry attempts for a given tier."""
    return {
        0: config.retry_policy.t0_max,
        1: config.retry_policy.t1_max,
        2: config.retry_policy.t2_max,
        3: config.retry_policy.t3_max,
    }.get(tier, 1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_only(
    files: list[FileEntry],
    llm_call: Callable[..., str] | None = None,
    run_semantic: bool = False,
) -> list[Issue]:
    """Run all checkers without any repair. Returns issue list."""
    pipeline = _build_pipeline(llm_call=llm_call)
    return pipeline.run(files, run_semantic=run_semantic)


def run(
    files: list[FileEntry],
    config: RepairConfig | None = None,
    source_context: SourceContext | None = None,
    llm_call: Callable[..., str] | None = None,
) -> RepairResult:
    """Three-phase repair: check → fix loop → verify."""
    if config is None:
        config = RepairConfig()

    pipeline = _build_pipeline(llm_call=llm_call)
    fixers = _build_fixers(llm_call=llm_call)
    tracker = IssueTracker()

    # =================================================================
    # Phase A — Full check (L0–L3)
    # =================================================================
    logger.info("Phase A: full validation")
    all_issues = pipeline.run(
        files, run_semantic=config.run_semantic)

    blocking = _filter_blocking(all_issues, config)
    if not blocking:
        logger.info("Phase A: no blocking issues — pass")
        return RepairResult(passed=True, issues=all_issues,
                            report="No blocking issues found.")

    logger.info("Phase A: %d blocking issues found", len(blocking))
    had_semantic = any(i.category == "semantic" for i in all_issues)

    # =================================================================
    # Phase B — Fix loop
    # =================================================================
    logger.info("Phase B: entering fix loop")
    prev_report = None
    current_issues = list(blocking)

    for round_num in range(config.max_rounds):
        logger.info("Fix round %d — %d issues remaining",
                     round_num + 1, len(current_issues))

        # Group issues by starting tier
        tier_groups = _group_by_start_tier(current_issues)

        any_patched = False
        for tier in sorted(tier_groups.keys()):
            fixer = fixers.get(tier)
            if fixer is None:
                continue

            tier_issues = tier_groups[tier]
            result = _run_fixer_with_escalation(
                fixer, fixers, tier, tier_issues, files,
                source_context, config, tracker,
            )
            if result:
                any_patched = True

        if not any_patched:
            logger.info("No patches applied in round %d — stopping",
                         round_num + 1)
            break

        # Scoped recheck (L0–L2 only, 0 token)
        recheck_issues = pipeline.run(
            files, max_layer=2, run_semantic=False)
        recheck_blocking = _filter_blocking(recheck_issues, config)

        report = tracker.diff(current_issues, recheck_blocking)
        logger.info(
            "Round %d result: resolved=%d, persisting=%d, introduced=%d",
            round_num + 1, len(report.resolved),
            len(report.persisting), len(report.introduced),
        )

        # Safety valves
        if tracker.is_regression(report):
            logger.warning("Regression detected in round %d — stopping",
                           round_num + 1)
            break
        if tracker.is_stalled(prev_report, report):
            logger.warning("Stalled in round %d — stopping", round_num + 1)
            break

        prev_report = report
        current_issues = recheck_blocking

        if not current_issues:
            logger.info("All blocking issues resolved after round %d",
                         round_num + 1)
            break

    # =================================================================
    # Phase C — Final semantic verify (if Phase A had semantic issues)
    # =================================================================
    if had_semantic and config.run_semantic:
        logger.info("Phase C: final semantic verification")
        final_issues = pipeline.run(
            files, run_semantic=True)
    else:
        final_issues = pipeline.run(
            files, max_layer=2, run_semantic=False)

    final_blocking = _filter_blocking(final_issues, config)
    passed = len(final_blocking) == 0

    report_text = _build_report(final_issues, tracker, passed)
    logger.info("Repair complete: %s (%d issues remaining)",
                "PASS" if passed else "FAIL", len(final_blocking))

    return RepairResult(
        passed=passed,
        issues=final_issues,
        history=tracker.get_history(),
        report=report_text,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _filter_blocking(issues: list[Issue],
                     config: RepairConfig) -> list[Issue]:
    if config.block_on == "all":
        return list(issues)
    return [i for i in issues if i.severity == "error"]


def _group_by_start_tier(issues: list[Issue]) -> dict[int, list[Issue]]:
    groups: dict[int, list[Issue]] = {}
    for issue in issues:
        tier = START_TIER.get(issue.category, 0)
        groups.setdefault(tier, []).append(issue)
    return groups


def _run_fixer_with_escalation(
    fixer,
    all_fixers: dict,
    start_tier: int,
    issues: list[Issue],
    files: list[FileEntry],
    source_context: SourceContext | None,
    config: RepairConfig,
    tracker: IssueTracker,
) -> bool:
    """Run a fixer tier; if retries exhausted, escalate to next tier.

    Returns True if any patches were applied.
    """
    any_patched = False
    remaining = list(issues)
    tier = start_tier

    while remaining and tier <= 3:
        fixer_obj = all_fixers.get(tier)
        if fixer_obj is None:
            tier += 1
            continue

        max_retries = _tier_max(config, tier)
        for attempt in range(max_retries):
            if not remaining:
                break

            result = fixer_obj.fix(
                files=files,
                issues=remaining,
                strategy="standard",
                source_context=source_context,
                attempt_num=attempt,
                max_attempts=max_retries,
            )

            # Record attempts
            for issue in remaining:
                status = ("resolved" if issue.fingerprint in result.resolved_fingerprints
                          else "persisting")
                tracker.record_attempt(RepairAttempt(
                    issue_fingerprint=issue.fingerprint,
                    tier=tier,
                    attempt_num=attempt,
                    strategy="standard",
                    result=status,
                ))

            if result.patched_paths:
                any_patched = True

            # Remove resolved issues
            remaining = [
                i for i in remaining
                if i.fingerprint not in result.resolved_fingerprints
            ]

        # Escalate remaining to next tier
        if remaining:
            logger.info("Escalating %d issues from T%d to T%d",
                        len(remaining), tier, tier + 1)
        tier += 1

    return any_patched


def _build_report(issues: list[Issue], tracker: IssueTracker,
                  passed: bool) -> str:
    lines = [f"Repair {'PASSED' if passed else 'FAILED'}"]
    lines.append(f"Final issues: {len(issues)}")

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    lines.append(f"  errors: {len(errors)}, warnings: {len(warnings)}")

    history = tracker.get_history()
    if history:
        total_attempts = sum(len(v) for v in history.values())
        lines.append(f"Total repair attempts: {total_attempts}")

    if errors:
        lines.append("\nRemaining errors:")
        for i in errors:
            lines.append(f"  {i}")

    return "\n".join(lines)
