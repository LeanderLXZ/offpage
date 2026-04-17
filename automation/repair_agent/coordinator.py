"""Coordinator — three-phase check → fix → verify orchestration.

Phase A: Full validation (L0–L3 if configured)
Phase B: Fix loop — escalate T0→T1→T2→T3 with scoped recheck and
         an embedded L3 gate (re-runs semantic checker on files that
         were modified this round AND had semantic issues in Phase A)
Phase C: Final confirmation — reuses the last L3 gate result instead of
         issuing a fresh semantic call when possible

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
    importance_map: dict[str, str] | None = None,
) -> CheckerPipeline:
    pipeline = CheckerPipeline()
    pipeline.register(JsonSyntaxChecker())
    pipeline.register(SchemaChecker())
    pipeline.register(StructuralChecker(importance_map=importance_map))
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
    importance_map: dict[str, str] | None = None,
) -> list[Issue]:
    """Run all checkers without any repair. Returns issue list."""
    pipeline = _build_pipeline(llm_call=llm_call,
                                importance_map=importance_map)
    return pipeline.run(files, run_semantic=run_semantic)


def run(
    files: list[FileEntry],
    config: RepairConfig | None = None,
    source_context: SourceContext | None = None,
    llm_call: Callable[..., str] | None = None,
    importance_map: dict[str, str] | None = None,
) -> RepairResult:
    """Three-phase repair: check → fix loop → verify.

    Args:
        importance_map: ``{character_id: importance}`` — raises the
            structural min-examples threshold for main / important
            characters (主角 → 5, 重要配角 → 3, others → 1).
    """
    if config is None:
        config = RepairConfig()

    pipeline = _build_pipeline(llm_call=llm_call,
                                importance_map=importance_map)
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
    # Files that had at least one semantic issue in Phase A — the L3 gate
    # only re-checks these (and only when they were patched this round).
    l3_file_set: set[str] = {
        i.file for i in all_issues if i.category == "semantic"
    }

    # =================================================================
    # Phase B — Fix loop (with embedded L3 gate)
    # =================================================================
    logger.info("Phase B: entering fix loop")
    prev_report = None
    current_issues = list(blocking)
    # Tracks the most recent L3 gate blocking issues so Phase C can
    # reuse them instead of paying for another semantic call.
    last_gate_issues: list[Issue] | None = None
    gate_ever_ran = False

    for round_num in range(config.max_rounds):
        logger.info("Fix round %d — %d issues remaining",
                     round_num + 1, len(current_issues))

        # Group issues by starting tier
        tier_groups = _group_by_start_tier(current_issues)

        modified_files: set[str] = set()
        for tier in sorted(tier_groups.keys()):
            fixer = fixers.get(tier)
            if fixer is None:
                continue

            tier_issues = tier_groups[tier]
            tier_modified = _run_fixer_with_escalation(
                fixer, fixers, tier, tier_issues, files,
                source_context, config, tracker,
            )
            modified_files.update(tier_modified)

        if not modified_files:
            logger.info("No patches applied in round %d — stopping",
                         round_num + 1)
            break

        # Scoped recheck (L0–L2 only, 0 token)
        recheck_issues = pipeline.run_scoped(
            files, patched_paths=[], max_layer=2)
        recheck_blocking = _filter_blocking(recheck_issues, config)

        # ---- L3 gate: re-check semantic layer on modified L3 files ----
        gate_blocking: list[Issue] = []
        gate_targets = l3_file_set & modified_files
        if (config.l3_gate_enabled and config.run_semantic
                and gate_targets):
            logger.info(
                "L3 gate: re-checking %d file(s) modified this round",
                len(gate_targets))
            gate_file_entries = [f for f in files if f.path in gate_targets]
            gate_issues = pipeline.run_layer(gate_file_entries, layer=3)
            gate_blocking = _filter_blocking(gate_issues, config)
            tracker.record_l3_gate(
                {i.fingerprint for i in gate_blocking})
            gate_ever_ran = True
            last_gate_issues = gate_blocking
            logger.info(
                "L3 gate result: %d blocking semantic issue(s) remain",
                len(gate_blocking))

        # Merge L0-L2 recheck + L3 gate findings for round diff & next round
        combined_blocking = recheck_blocking + gate_blocking
        report = tracker.diff(current_issues, combined_blocking)
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
        if tracker.is_l3_gate_reemerge():
            logger.warning(
                "L3 gate reemerge in round %d — semantic layer not "
                "converging, stopping", round_num + 1)
            break

        prev_report = report
        current_issues = combined_blocking

        if not current_issues:
            logger.info("All blocking issues resolved after round %d",
                         round_num + 1)
            break

    # =================================================================
    # Phase C — Final confirmation
    # =================================================================
    # Always do a cheap L0–L2 sweep on the final artifacts.
    final_issues = pipeline.run(files, max_layer=2, run_semantic=False)

    # For L3: reuse the last gate result when available; only fall back
    # to a fresh semantic call if Phase A had semantic issues AND the
    # gate never ran (e.g. semantic fixers never modified an L3 file).
    if had_semantic and config.run_semantic:
        if gate_ever_ran:
            logger.info(
                "Phase C: reusing last L3 gate result (%d issue(s))",
                len(last_gate_issues or []))
            final_issues.extend(last_gate_issues or [])
        else:
            logger.info(
                "Phase C: fallback semantic verification (gate never ran)")
            l3_fallback = pipeline.run_layer(files, layer=3)
            final_issues.extend(l3_fallback)

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
) -> set[str]:
    """Run a fixer tier; if retries exhausted, escalate to next tier.

    Returns the set of file paths that had at least one fingerprint
    marked resolved by a fixer call. Used by the caller to decide which
    files to feed through the L3 gate.
    """
    modified_files: set[str] = set()
    remaining = list(issues)
    tier = start_tier

    while remaining and tier <= 3:
        fixer_obj = all_fixers.get(tier)
        if fixer_obj is None:
            tier += 1
            continue

        # Enforce T3 global per-file cap: drop issues from files that
        # have already exhausted their T3 quota before invoking T3.
        if tier == 3:
            t3_cap = config.retry_policy.t3_max_per_file
            before = len(remaining)
            remaining = [
                i for i in remaining
                if tracker.tier_uses_on_file(i.file, 3) < t3_cap
            ]
            dropped = before - len(remaining)
            if dropped:
                logger.warning(
                    "T3 global cap reached — dropping %d issue(s) from "
                    "files that already used their T3 budget", dropped)
            if not remaining:
                break

        max_retries = _tier_max(config, tier)
        for attempt in range(max_retries):
            if not remaining:
                break

            attempted = list(remaining)
            result = fixer_obj.fix(
                files=files,
                issues=attempted,
                strategy="standard",
                source_context=source_context,
                attempt_num=attempt,
                max_attempts=max_retries,
            )

            # Track files touched by successful patches (fingerprint →
            # file). This is what the L3 gate needs: any file that was
            # written to during this round.
            fingerprint_to_file = {i.fingerprint: i.file for i in attempted}
            for fp in result.resolved_fingerprints:
                f_path = fingerprint_to_file.get(fp)
                if f_path:
                    modified_files.add(f_path)

            # Record T3 usage per-file (one use per file T3 wrote to in
            # this invocation), so the cap above catches subsequent rounds.
            if tier == 3:
                for fp in result.resolved_fingerprints:
                    f_path = fingerprint_to_file.get(fp)
                    if f_path:
                        modified_files.add(f_path)
                # Each file seen in resolved_fingerprints had its content
                # regenerated — record exactly once per file.
                for f_path in {
                    fingerprint_to_file.get(fp)
                    for fp in result.resolved_fingerprints
                    if fingerprint_to_file.get(fp)
                }:
                    tracker.record_tier_use_on_file(f_path, 3)

            # Remove resolved issues
            remaining = [
                i for i in remaining
                if i.fingerprint not in result.resolved_fingerprints
            ]

            # Record attempts only for issues that were actually attempted
            for issue in attempted:
                status = ("resolved" if issue.fingerprint in result.resolved_fingerprints
                          else "persisting")
                tracker.record_attempt(RepairAttempt(
                    issue_fingerprint=issue.fingerprint,
                    tier=tier,
                    attempt_num=attempt,
                    strategy="standard",
                    result=status,
                ))

        # Escalate remaining to next tier
        if remaining:
            logger.info("Escalating %d issues from T%d to T%d",
                        len(remaining), tier, tier + 1)
        tier += 1

    return modified_files


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
