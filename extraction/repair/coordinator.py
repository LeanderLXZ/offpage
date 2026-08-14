"""Coordinator — three-phase check → fix → verify orchestration.

Phase A: Full validation (L0–L3 if configured)
Phase B: Fix loop — escalate T0→T1→T2 (each tier capped at 2 attempts,
         routed per issue rule by ``protocol.route_tiers``) with a scoped
         L0–L2 recheck and an embedded, SCOPED L3 gate. The gate re-reviews a
         narrow per-file set of json_paths — what a fix touched this round
         plus any semantic issue still open on that file — never the whole
         file. Its job is "did this fix land + is the known problem still
         there", Phase A already did the one full semantic pass. There is NO
         full-file regeneration tier — issues the capped tiers can't fix are
         left for Phase C to surface (and the caller to defer).
Phase C: Final confirmation — reuses the last L3 gate result instead of
         issuing a fresh semantic call when possible

Source-discrepancy triage (when ``config.triage_enabled``) hooks into
Phase B at two points:
  round 1 — post-capped-tiers, to accept residual L3 issues that are
            author bugs in the source novel as SourceNotes
  round 2 — post-L3-gate and pre-FAIL, to accept any remaining L3
            residuals that program-verify as source-inherent

A run is a single Phase A→B→C pass (no lifecycle reset — that machinery
existed only to host the removed T3 regen). Residual length-bound schema
misses are accepted via the decision #48 tolerance gate after the capped
tiers rather than hard-failing.

Public API:
    run(files, config, ...) → RepairResult
    validate_only(files, ...) → list[Issue]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from .checkers import CheckerPipeline
from .checkers.json_syntax import JsonSyntaxChecker
from .checkers.schema import SchemaChecker
from .checkers.structural import StructuralChecker
from .checkers.targets_keys_eq_baseline import TargetsKeysEqBaselineChecker
from .checkers.semantic import SemanticChecker
from .context_retriever import ContextRetriever
from .fixers.programmatic import ProgrammaticFixer
from .fixers.local_patch import LocalPatchFixer
from .fixers.source_patch import SourcePatchFixer
from .notes_writer import NotesWriter
from .recorder import RepairRecorder
from .protocol import (
    FileEntry,
    Issue,
    RepairAttempt,
    RepairConfig,
    RepairResult,
    SourceContext,
    SourceNote,
    TriageVerdict,
    is_coverage_shortage,
    issue_max_tier,
    issue_start_tier,
)
from .tracker import IssueTracker
from .triage import Triager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline & fixer factory
# ---------------------------------------------------------------------------

def _build_pipeline(
    llm_call: Callable[..., str] | None = None,
    importance_map: dict[str, str] | None = None,
    extra_checkers: list[Any] | None = None,
    config: RepairConfig | None = None,
) -> CheckerPipeline:
    cfg = config or RepairConfig()
    pipeline = CheckerPipeline()
    pipeline.register(JsonSyntaxChecker())
    pipeline.register(SchemaChecker())
    pipeline.register(StructuralChecker(importance_map=importance_map))
    pipeline.register(TargetsKeysEqBaselineChecker())
    pipeline.register(SemanticChecker(llm_call=llm_call,
                                      timeout_s=cfg.semantic_timeout_s))
    for checker in extra_checkers or []:
        pipeline.register(checker)
    return pipeline


# Hard cap on attempts per tier (T-REPAIR-NO-REEXTRACT): a tier tries at
# most twice; the 2nd attempt only re-targets fields the immediate
# re-verify still flags. Configured ``t*_max`` above this is clamped down.
_TIER_ATTEMPT_CAP = 2


def _build_fixers(
    llm_call: Callable[..., str] | None = None,
    retriever: ContextRetriever | None = None,
    pipeline: CheckerPipeline | None = None,
    config: RepairConfig | None = None,
) -> dict[int, object]:
    cfg = config or RepairConfig()
    # Immediate re-verify for the LLM tiers: scoped L0–L2 recheck (0 token)
    # returning the set of issue fingerprints still present after a patch.
    verify_fn: Callable[[list[FileEntry]], set[str]] | None = None
    if pipeline is not None:
        def verify_fn(files: list[FileEntry]) -> set[str]:
            issues = pipeline.run_scoped(files, patched_paths=[], max_layer=2)
            return {i.fingerprint for i in issues}

    return {
        0: ProgrammaticFixer(),
        1: LocalPatchFixer(llm_call=llm_call, verify_fn=verify_fn,
                           timeout_s=cfg.t1_timeout_s,
                           recheck_effort=cfg.recheck_effort),
        2: SourcePatchFixer(llm_call=llm_call, retriever=retriever,
                            verify_fn=verify_fn,
                            timeout_s=cfg.t2_timeout_s,
                            recheck_effort=cfg.recheck_effort),
    }


def _tier_max(config: RepairConfig, tier: int) -> int:
    """Max retry attempts for a given tier (hard-capped at 2)."""
    configured = {
        0: config.retry_policy.t0_max,
        1: config.retry_policy.t1_max,
        2: config.retry_policy.t2_max,
    }.get(tier, 1)
    return min(configured, _TIER_ATTEMPT_CAP)


# ---------------------------------------------------------------------------
# Lifecycle outcome (one Phase A→B→C pass)
# ---------------------------------------------------------------------------

@dataclass
class _LifecycleOutcome:
    terminated_by: str
    final_issues: list[Issue] = field(default_factory=list)
    final_blocking: list[Issue] = field(default_factory=list)
    accepted_notes: list[SourceNote] = field(default_factory=list)
    tracker_history: dict[str, list[RepairAttempt]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_only(
    files: list[FileEntry],
    llm_call: Callable[..., str] | None = None,
    run_semantic: bool = False,
    importance_map: dict[str, str] | None = None,
    extra_checkers: list[Any] | None = None,
    config: RepairConfig | None = None,
) -> list[Issue]:
    """Run all checkers without any repair. Returns issue list.

    ``config`` only supplies ``semantic_timeout_s`` here (no fixers run);
    ``None`` uses the ``RepairConfig`` defaults.
    """
    pipeline = _build_pipeline(
        llm_call=llm_call,
        importance_map=importance_map,
        extra_checkers=extra_checkers,
        config=config,
    )
    return pipeline.run(files, run_semantic=run_semantic)


def run(
    files: list[FileEntry],
    config: RepairConfig | None = None,
    source_context: SourceContext | None = None,
    llm_call: Callable[..., str] | None = None,
    importance_map: dict[str, str] | None = None,
    recorder: RepairRecorder | None = None,
    extra_checkers: list[Any] | None = None,
    seed_issues: list[Issue] | None = None,
) -> RepairResult:
    """Single-pass three-phase repair (Phase A → B → C).

    Args:
        importance_map: ``{character_id: importance}`` — raises the
            structural min-examples threshold for main / important
            characters (main → 5, important supporting → 3, others → 1).
        recorder: optional ``RepairRecorder`` that receives a structured
            JSONL event at each phase / round / issue / fix / triage /
            completion transition. ``None`` disables structured logging.
        extra_checkers: optional additional ``BaseChecker`` instances
            registered on top of the built-in pipeline (decision #59 —
            phase 2 baseline reference checkers carry their hints via
            constructor injection, keeping ``FileEntry.content`` clean).
        seed_issues: when given, Phase A's discovery scan is skipped and
            these issues are fixed directly. For a caller that already
            knows what is wrong — Phase 3.5 settling a recorded debt, say —
            re-running discovery would re-read every file in full to
            re-derive a conclusion it was handed. The fix loop, scoped
            recheck, L3 gate and safety valves are unchanged, so a seeded
            run still proves its fixes landed rather than trusting them.
    """
    if config is None:
        config = RepairConfig()

    pipeline = _build_pipeline(
        llm_call=llm_call,
        importance_map=importance_map,
        extra_checkers=extra_checkers,
        config=config,
    )
    retriever = ContextRetriever()
    fixers = _build_fixers(
        llm_call=llm_call,
        retriever=retriever,
        pipeline=pipeline,
        config=config,
    )

    triager: Triager | None = None
    notes_writer: NotesWriter | None = None
    if config.triage_enabled and source_context is not None:
        triager = Triager(llm_call=llm_call, retriever=retriever,
                          timeout_s=config.triage_timeout_s,
                          recheck_effort=config.recheck_effort)
        notes_writer = NotesWriter(source_context.work_path)

    outcome = _run_one_lifecycle(
        files=files,
        config=config,
        source_context=source_context,
        pipeline=pipeline,
        fixers=fixers,
        triager=triager,
        notes_writer=notes_writer,
        recorder=recorder,
        seed_issues=seed_issues,
    )

    passed = outcome.terminated_by == "PASS"
    report_text = _build_report(
        outcome.final_issues,
        outcome.tracker_history,
        passed,
        terminated_by=outcome.terminated_by,
        accepted_notes=outcome.accepted_notes,
    )

    return RepairResult(
        passed=passed,
        issues=outcome.final_issues,
        history=outcome.tracker_history,
        report=report_text,
        accepted_notes=outcome.accepted_notes,
    )


# ---------------------------------------------------------------------------
# One lifecycle (one full Phase A → B → C pass)
# ---------------------------------------------------------------------------

def _run_one_lifecycle(
    *,
    files: list[FileEntry],
    config: RepairConfig,
    source_context: SourceContext | None,
    pipeline: CheckerPipeline,
    fixers: dict[int, object],
    triager: Triager | None,
    notes_writer: NotesWriter | None,
    recorder: RepairRecorder | None,
    seed_issues: list[Issue] | None = None,
) -> _LifecycleOutcome:
    """Execute one complete Phase A → B → C pass.

    Returns a ``_LifecycleOutcome`` describing why the run ended and the
    state the final ``RepairResult`` builder needs.
    """
    def _emit(event: str, **fields: Any) -> None:
        if recorder is not None:
            recorder.write(event, cycle=0, **fields)

    tracker = IssueTracker()
    accepted_notes: list[SourceNote] = []
    notes_per_file: dict[str, int] = {}

    # =================================================================
    # Phase A — Full check (L0–L3)
    # =================================================================
    logger.info("Phase A: full validation")
    seeded = seed_issues is not None
    _emit("phase_start", phase="A",
          file_count=len(files), run_semantic=config.run_semantic,
          seeded=seeded)
    if seeded:
        logger.info("Phase A: seeded with %d known issue(s) — "
                    "skipping discovery scan", len(seed_issues))
        all_issues = list(seed_issues)
    else:
        all_issues = pipeline.run(files, run_semantic=config.run_semantic)

    blocking = _filter_blocking(all_issues, config)

    if not blocking:
        logger.info("Phase A: no blocking issues — pass")
        _emit("phase_a_result", blocking=0, total=len(all_issues))
        _emit("complete", status="PASS",
              resolved=0, persisting=0, issues_remaining=0)
        return _LifecycleOutcome(
            terminated_by="PASS",
            final_issues=all_issues,
            final_blocking=[],
            accepted_notes=accepted_notes,
            tracker_history=tracker.get_history(),
        )

    logger.info("Phase A: %d blocking issues found", len(blocking))
    _emit("phase_a_result", blocking=len(blocking), total=len(all_issues))
    for i in blocking:
        start_tier = issue_start_tier(i)
        _emit("issue",
              fingerprint=i.fingerprint,
              file=i.file,
              json_path=i.json_path,
              category=i.category,
              rule=i.rule,
              severity=i.severity,
              message=i.message,
              start_tier=start_tier)
    # A file only receives an L3 verdict in Phase A when it was already clean
    # at L0–L2 — ``CheckerPipeline`` skips higher layers for files with a
    # lower-layer error (by design: don't burn tokens semantically reviewing a
    # schema-broken file). So "Phase A reported no semantic issue" does NOT
    # mean "this file passed semantic review"; it usually means L3 never ran.
    # Keying the gate on Phase A's semantic issues therefore let a file whose
    # L0–L2 errors T0 had just fixed sail through the whole round with zero
    # semantic review and still report PASS. Track every file under review and
    # let the L3 gate below re-check whichever of them this round modified.
    # A seeded run knows its issue set exactly, so it can key the semantic
    # machinery on whether any seed actually is semantic — a purely
    # mechanical settle then costs zero L3 calls. The reasoning above only
    # applies to a discovery run, where "Phase A reported nothing semantic"
    # is genuinely ambiguous.
    had_semantic = config.run_semantic and (
        any(i.category == "semantic" for i in blocking) if seeded else True)
    l3_file_set: set[str] = {f.path for f in files}

    # =================================================================
    # Phase B — Fix loop (with embedded L3 gate + triage hooks)
    # =================================================================
    logger.info("Phase B: entering fix loop")
    _emit("phase_start", phase="B")
    prev_report = None
    current_issues = list(blocking)
    # The round's full semantic picture: this round's gate verdicts PLUS the
    # semantic issues carried on files the round never gated. Assigned before
    # the safety-valve breaks so it survives them, and handed to Phase C.
    outstanding_semantic: list[Issue] = []
    gate_ever_ran = False

    for round_num in range(config.max_rounds):
        logger.info("Fix round %d — %d issues remaining",
                     round_num + 1, len(current_issues))
        _emit("round_start",
              round=round_num + 1, issues_remaining=len(current_issues))

        # Round-local: a length-tolerance terminal from one tier group is
        # only valid within the round it fired (M1 — must not leak forward).
        lifecycle_signal = ""  # "" | "LENGTH_TOLERANCE_PASS"
        tier_groups = _group_by_start_tier(current_issues)

        modified_files: set[str] = set()
        # Exact json_paths touched this round, per file — drives the scoped
        # L3 gate below (re-review only what changed, not the whole file).
        round_modified_paths: dict[str, set[str]] = {}
        round_fixer_candidates: dict[str, TriageVerdict] = {}

        for tier in sorted(tier_groups.keys()):
            fixer = fixers.get(tier)
            if fixer is None:
                continue

            tier_issues = tier_groups[tier]
            tier_modified, tier_paths, tier_cands, tier_signal = (
                _run_fixer_with_escalation(
                    fixer, fixers, tier, tier_issues, files,
                    source_context, config, tracker,
                    pipeline=pipeline,
                    triager=triager,
                    notes_writer=notes_writer,
                    accepted_notes=accepted_notes,
                    notes_per_file=notes_per_file,
                )
            )
            modified_files.update(tier_modified)
            for fpath, jpaths in tier_paths.items():
                round_modified_paths.setdefault(fpath, set()).update(jpaths)
            round_fixer_candidates.update(tier_cands)
            if tier_signal:
                lifecycle_signal = tier_signal
                # Do NOT break here: length-only residual arises in the
                # start_tier=0 group (processed first), but semantic issues
                # route start_tier=2 into a later group. Breaking would skip
                # those groups and PASS a file with unprocessed semantic
                # problems (M1). Let every tier group run; the terminal is
                # gated below on the residual being the ENTIRE blocking set.

        if (lifecycle_signal == "LENGTH_TOLERANCE_PASS"
                and _all_length_only(current_issues)):
            # The length-bound tolerance gate accepted the residual
            # schema minLength/maxLength issues (decision #48). Only a
            # terminal PASS when the WHOLE round-blocking set was length-only
            # (M1) — otherwise the non-length issues (e.g. semantic) still
            # need Phase B recheck / L3 gate / Phase C below. Terminate as
            # PASS without re-running Phase C — Phase C uses the strict
            # pipeline and would re-flag the same length issues we just
            # intentionally relaxed.
            logger.info(
                "Length-bound tolerance gate: PASS (decision #48)")
            _emit("complete", status="PASS",
                  issues_remaining=0,
                  accepted_notes=len(accepted_notes))
            return _LifecycleOutcome(
                terminated_by="PASS",
                final_issues=[],
                final_blocking=[],
                accepted_notes=accepted_notes,
                tracker_history=tracker.get_history(),
            )

        if not modified_files:
            logger.info("No patches applied in round %d — stopping",
                         round_num + 1)
            _emit("no_patches", round=round_num + 1)
            break
        _emit("round_patched",
              round=round_num + 1,
              modified_files=sorted(modified_files))

        # Scoped recheck (L0–L2 only, 0 token). Already-accepted
        # coverage_shortage issues resurface here because the note is
        # sidecar and the underlying JSON wasn't modified — drop them by
        # fingerprint so the loop doesn't spin.
        recheck_issues = pipeline.run_scoped(
            files, patched_paths=[], max_layer=2)
        accepted_fps = {n.issue_fingerprint for n in accepted_notes}
        recheck_blocking = [
            i for i in _filter_blocking(recheck_issues, config)
            if i.fingerprint not in accepted_fps
        ]

        # ---- Self-inflicted length sweep (0 token) ----
        # An LLM tier rewriting a prose field to fix a semantic issue
        # routinely lands a value longer than its ``maxLength``. That
        # overrun is a BRAND-NEW fingerprint on a path this round just
        # touched, so the diff below counts it as ``introduced`` and the
        # regression valve breaks the round — leaving a mechanically
        # trivial overrun permanently unfixed (it was the dominant source
        # of deferred length debt in production ledgers). Sweep those with
        # T0 before the diff: deterministic, in-round, no valve trip.
        # Strictly scoped to overruns this round CAUSED (new fingerprint +
        # path we patched); pre-existing length issues keep their normal
        # tier routing and the decision #48 tolerance gate.
        if _sweep_self_inflicted_length(
                recheck_blocking,
                files=files,
                fixers=fixers,
                prior_fingerprints={i.fingerprint for i in current_issues},
                round_modified_paths=round_modified_paths):
            recheck_issues = pipeline.run_scoped(
                files, patched_paths=[], max_layer=2)
            recheck_blocking = [
                i for i in _filter_blocking(recheck_issues, config)
                if i.fingerprint not in accepted_fps
            ]

        # ---- L3 gate (scoped) ----
        # Gate the files this round actually modified, minus any that still
        # carry an L0–L2 error: the checker pipeline skips L3 for those on
        # purpose (don't burn tokens semantically reviewing a schema-broken
        # file), and the round is going to FAIL on that error anyway — a
        # semantic verdict here buys no decision.
        #
        # The gate re-checks a NARROW, per-file set of json_paths
        # (T-GATE-SCOPED-RECHECK). Its job is "did this fix land", not
        # "re-audit the whole book" — Phase A already did the one full
        # semantic pass. A full-file re-review surfaces a different set of
        # nondeterministic untouched-field nits every round, each a fresh
        # ``introduced`` fingerprint, so the loop whacks moles until it hits
        # the round cap.
        #
        # Per-file scope = (paths a fix TOUCHED this round) ∪ (paths of
        # semantic issues CARRIED into this round for that file):
        #   * touched paths verify the fix landed;
        #   * carried semantic paths keep an issue the round did NOT fix — on
        #     a path no fix touched — from silently vanishing. The round diff
        #     below compares ``current_issues`` (full Phase-A set) against
        #     ``combined_blocking``; if such an issue never re-enters the gate
        #     result it reads as ``resolved`` and PASSes a still-broken file.
        #     Re-checking its own path re-surfaces it so it persists to FAIL.
        # Scoping PER FILE (not a flat union across files) stops one file's
        # touched path from unblocking a same-named path's jitter on another
        # file. Untouched CLEAN fields are still never re-scanned, so the
        # whack-a-mole the scoping fixed stays fixed. A file whose scope comes
        # out empty (nothing touched, no carried semantic issue) is skipped.
        gate_blocking: list[Issue] = []
        still_broken = {
            i.file for i in recheck_blocking if i.severity == "error"
        }
        gate_targets = (l3_file_set & modified_files) - still_broken
        gate_scopes: dict[str, list[str]] = {}
        for fpath in gate_targets:
            fscope = _gate_scope(fpath, round_modified_paths, current_issues)
            if fscope:
                gate_scopes[fpath] = fscope
        # Files the gate ACTUALLY adjudicated this round. Not the same as
        # ``gate_scopes``: that is built unconditionally above, while the gate
        # only runs when it is enabled. Keying the carry below on gate_scopes
        # would, with the gate disabled but semantics on, leave those files
        # neither gated nor carried — reopening the very hole this carry
        # closes. Only membership here means "a verdict was rendered".
        gated_files: set[str] = set()
        if (config.l3_gate_enabled and config.run_semantic and gate_scopes):
            logger.info(
                "L3 gate: re-checking %d file(s), scoped per file to "
                "touched + carried semantic path(s)", len(gate_scopes))
            # Re-read tier (decision #65): the gate re-reads files whose
            # issues Phase A already surfaced, so it needs less reasoning
            # depth than the cold full pass — which omits effort entirely and
            # inherits the backend default (``[llm].effort``).
            for f in files:
                fscope = gate_scopes.get(f.path)
                if not fscope:
                    continue
                f_gate_issues = pipeline.run_semantic_scoped(
                    [f], paths=fscope, effort=config.recheck_effort)
                gate_blocking.extend(_filter_blocking(f_gate_issues, config))
                gated_files.add(f.path)
            tracker.record_l3_gate(
                {i.fingerprint for i in gate_blocking})
            gate_ever_ran = True

            # ---- Post-gate triage (round 2) ----
            if gate_blocking and triager and notes_writer and source_context:
                gate_blocking = _run_triage_round(
                    triager=triager,
                    notes_writer=notes_writer,
                    config=config,
                    source_ctx=source_context,
                    issues=gate_blocking,
                    triage_round=2,
                    accepted_notes=accepted_notes,
                    notes_per_file=notes_per_file,
                    fixer_candidates=round_fixer_candidates,
                )

            logger.info(
                "L3 gate result: %d blocking semantic issue(s) remain",
                len(gate_blocking))
            _emit("l3_gate_result",
                  round=round_num + 1,
                  targets=sorted(gate_scopes),
                  scope_paths=sorted({p for ps in gate_scopes.values()
                                      for p in ps}),
                  blocking=len(gate_blocking))

        # ---- Carry semantic issues on files this round never gated ----
        # ``gate_targets`` only covers files a fix actually modified, so a file
        # nothing touched this round gets no semantic verdict at all. Its open
        # issues have no other source to re-enter ``combined_blocking`` (the
        # L0–L2 recheck can't see semantics), so without this they silently
        # vanish, the diff below reads that as ``resolved``, and Phase C's
        # gate-reuse path PASSes a file with a known factual error
        # (T-GATE-UNMODIFIED-FILE-CARRY). Nothing re-checked them → their state
        # is unknown → carry them unchanged (fail-closed).
        # Files the gate actually adjudicated need no carry: ``_gate_scope``
        # puts every still-open semantic path of that file into its scope, so
        # the gate result already covers them — carrying would double-count.
        # Already-accepted issues are excluded, mirroring ``recheck_blocking``,
        # so a triage-accepted SourceNote isn't carried forever.
        carried_semantic = [
            i for i in current_issues
            if i.category == "semantic"
            and i.file not in gated_files
            and i.fingerprint not in accepted_fps
        ]
        if carried_semantic:
            logger.info(
                "Carrying %d semantic issue(s) on %d ungated file(s)",
                len(carried_semantic),
                len({i.file for i in carried_semantic}))

        combined_blocking = (
            recheck_blocking + gate_blocking + carried_semantic)
        # Assigned here — before the safety valves below can break out — so
        # Phase C sees this round's semantic picture on every exit path.
        outstanding_semantic = gate_blocking + carried_semantic
        report = tracker.diff(current_issues, combined_blocking)
        logger.info(
            "Round %d result: resolved=%d, persisting=%d, introduced=%d",
            round_num + 1, len(report.resolved),
            len(report.persisting), len(report.introduced),
        )
        _emit("round_result",
              round=round_num + 1,
              resolved=len(report.resolved),
              persisting=len(report.persisting),
              introduced=len(report.introduced))

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
    final_issues = pipeline.run(files, max_layer=2, run_semantic=False)
    accepted_fps = {n.issue_fingerprint for n in accepted_notes}
    if accepted_fps:
        final_issues = [
            i for i in final_issues if i.fingerprint not in accepted_fps
        ]

    if had_semantic and config.run_semantic:
        if gate_ever_ran:
            # The last round's gate verdicts PLUS the semantic issues carried
            # on files that round never gated — reusing only the gate result
            # would drop the latter and PASS a still-broken file
            # (T-GATE-UNMODIFIED-FILE-CARRY).
            logger.info(
                "Phase C: reusing last L3 gate result + carried semantic "
                "issue(s) (%d total)", len(outstanding_semantic))
            _emit("phase_c", mode="gate_reuse",
                  carried=len(outstanding_semantic))
            final_issues.extend(outstanding_semantic)
        else:
            # Same rule as the gate: only files that are clean at L0–L2 get a
            # semantic verdict. ``run_layer`` bypasses the pipeline's
            # prior-error skip, so without this filter a file with an
            # unfixable schema error would burn an L3 call it cannot act on.
            still_broken = {
                i.file for i in final_issues if i.severity == "error"
            }
            fallback_files = [f for f in files if f.path not in still_broken]
            if fallback_files:
                logger.info(
                    "Phase C: fallback semantic verification on %d clean "
                    "file(s) (gate never ran)", len(fallback_files))
                _emit("phase_c", mode="fallback_l3")
                # Re-read tier, same reasoning as the gate (decision #65):
                # Phase A is the cold read; this re-reads files it already
                # reviewed, so it needs less reasoning depth.
                l3_fallback = pipeline.run_layer(
                    fallback_files, layer=3, effort=config.recheck_effort)
                final_issues.extend(l3_fallback)

    final_blocking = _filter_blocking(final_issues, config)
    passed = len(final_blocking) == 0

    logger.info("Repair complete: %s (%d issues remaining, %d note(s))",
                "PASS" if passed else "FAIL",
                len(final_blocking), len(accepted_notes))
    _emit("complete",
          status="PASS" if passed else "FAIL",
          issues_remaining=len(final_blocking),
          accepted_notes=len(accepted_notes))

    return _LifecycleOutcome(
        terminated_by="PASS" if passed else "FAIL",
        final_issues=final_issues,
        final_blocking=final_blocking,
        accepted_notes=accepted_notes,
        tracker_history=tracker.get_history(),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _filter_blocking(issues: list[Issue],
                     config: RepairConfig) -> list[Issue]:
    """Issues that must be fixed or accepted before the stage can pass.

    Errors are always blocking. `coverage_shortage` warnings are also
    blocking: they carry a severity=warning demotion so they can't
    legitimately FAIL the stage, but they still need to enter the fix
    pipeline (start=T2) and then the 0-token triage fast path. If we
    dropped them here, they'd be silently ignored and leave the stage
    under the `importance_min_examples` floor.
    """
    if config.block_on == "all":
        return list(issues)
    return [i for i in issues
            if i.severity == "error" or is_coverage_shortage(i)]


def _group_by_start_tier(issues: list[Issue]) -> dict[int, list[Issue]]:
    groups: dict[int, list[Issue]] = {}
    for issue in issues:
        groups.setdefault(issue_start_tier(issue), []).append(issue)
    return groups


def _gate_scope(fpath: str,
                round_modified_paths: dict[str, set[str]],
                current_issues: list[Issue]) -> list[str]:
    """Json_paths the scoped L3 gate re-checks on ``fpath`` this round.

    Two contributors (see the L3 gate block for the full rationale):
      * paths a fix TOUCHED this round on ``fpath`` — verify the fix landed;
      * paths of semantic issues CARRIED into this round for ``fpath`` — an
        issue the round did NOT fix, on a path no fix touched, would drop out
        of the round diff and false-PASS a still-broken file; re-checking its
        own path keeps it alive until it is fixed or the run FAILs.

    Restricted to ``fpath`` (per-file, not a flat cross-file union) so one
    file's touched path can't unblock a same-named path's jitter on another.
    """
    paths = set(round_modified_paths.get(fpath, set()))
    paths |= {i.json_path for i in current_issues
              if i.file == fpath and i.category == "semantic"}
    return sorted(paths)


def _run_fixer_with_escalation(
    fixer,
    all_fixers: dict,
    start_tier: int,
    issues: list[Issue],
    files: list[FileEntry],
    source_context: SourceContext | None,
    config: RepairConfig,
    tracker: IssueTracker,
    *,
    pipeline: CheckerPipeline,
    triager: Triager | None,
    notes_writer: NotesWriter | None,
    accepted_notes: list[SourceNote],
    notes_per_file: dict[str, int],
) -> tuple[set[str], dict[str, set[str]], dict[str, TriageVerdict], str]:
    """Run a fixer tier; if attempts are exhausted, escalate to the next
    tier (capped per issue by ``protocol.route_tiers``; no tier > 2).

    Returns ``(modified_files, modified_paths, fixer_candidates,
    lifecycle_signal)``:
      * ``modified_files`` — file paths touched by at least one
        successful fix in this invocation (feeds the L3 gate).
      * ``modified_paths`` — ``{file_path: {json_path, ...}}``, the exact
        json_paths a fix touched this round. Feeds the scoped L3 gate so it
        re-reviews only what changed, not the whole file. Only paths carrying
        a semantic-reviewable JSON change are recorded — sidecar-note accepts
        (coverage_shortage) touch ``modified_files`` but NOT this map, since
        no JSON changed for the gate to re-read.
      * ``fixer_candidates`` — T2 self-reported source_inherent verdicts,
        carried forward as priors for the post-gate triage.
      * ``lifecycle_signal`` — ``""`` for normal completion, or
        ``"LENGTH_TOLERANCE_PASS"`` when the residual issues were all
        pure ``minLength``/``maxLength`` schema misses that passed the
        relaxed (×0.9 floor / ×1.1 ceil) re-validation (decision #48) —
        the caller treats this as a terminal PASS.
    """
    modified_files: set[str] = set()
    modified_paths: dict[str, set[str]] = {}
    remaining = list(issues)
    tier = start_tier
    # T2 self-report verdicts — used as priors for the residual triage.
    t2_self_report: dict[str, TriageVerdict] = {}
    # Issues that hit their per-issue max_tier without being fixed.
    capped_out: list[Issue] = []
    lifecycle_signal = ""

    while remaining and tier <= 2:
        fixer_obj = all_fixers.get(tier)
        if fixer_obj is None:
            tier += 1
            continue

        max_retries = _tier_max(config, tier)
        for attempt in range(max_retries):
            if not remaining:
                break

            # coverage_shortage issues only get ONE T2 fix attempt — the
            # novel either gains more examples on the first source_patch or
            # it doesn't; retrying doesn't add source material. On later
            # attempts drop them from the fix() call but KEEP them in
            # `remaining` so the post-T2 0-token accept fast path below can
            # pick them up (removing them from `remaining` here would make
            # `cs_remaining` empty and silently skip the accept path).
            if attempt > 0 and tier == 2:
                attempted = [i for i in remaining
                             if not is_coverage_shortage(i)]
            else:
                attempted = list(remaining)
            if not attempted:
                break
            result = fixer_obj.fix(
                files=files,
                issues=attempted,
                strategy="standard",
                source_context=source_context,
                attempt_num=attempt,
                max_attempts=max_retries,
            )

            # Capture T2 self-reports (source_inherent escape hatch).
            if result.source_inherent_candidates and tier == 2:
                t2_self_report.update(result.source_inherent_candidates)

            fingerprint_to_issue = {i.fingerprint: i for i in attempted}
            for fp in result.resolved_fingerprints:
                issue = fingerprint_to_issue.get(fp)
                if issue:
                    modified_files.add(issue.file)
                    modified_paths.setdefault(issue.file, set()).add(
                        issue.json_path)

            # M4: a fixer (T1) can write a file to disk yet report the issue
            # NOT resolved (apply succeeds but the immediate re-verify still
            # flags it). Its semantic content changed, so the L3 gate must
            # still re-check it — add every file whose json_path was patched
            # this round, regardless of resolution. Record the exact patched
            # json_path too, so the scoped gate re-reviews just that subtree.
            patched_json_paths = set(result.patched_paths)
            if patched_json_paths:
                for issue in attempted:
                    if issue.json_path in patched_json_paths:
                        modified_files.add(issue.file)
                        modified_paths.setdefault(issue.file, set()).add(
                            issue.json_path)

            remaining = [
                i for i in remaining
                if i.fingerprint not in result.resolved_fingerprints
            ]

            for issue in attempted:
                status: Literal["resolved", "persisting"] = (
                    "resolved"
                    if issue.fingerprint in result.resolved_fingerprints
                    else "persisting")
                tracker.record_attempt(RepairAttempt(
                    issue_fingerprint=issue.fingerprint,
                    tier=tier,
                    attempt_num=attempt,
                    strategy="standard",
                    result=status,
                ))

        # ---- coverage_shortage fast path (0 token, post-T2) ----
        # After T2's one attempt at adding examples, any remaining
        # coverage_shortage issues are accepted via a program-constructed
        # SourceNote — no source material can be invented.
        if (tier == 2 and triager is not None and notes_writer is not None
                and source_context is not None):
            cs_remaining = [i for i in remaining if is_coverage_shortage(i)]
            if cs_remaining:
                accepted_cs = _run_coverage_shortage_triage(
                    triager=triager,
                    notes_writer=notes_writer,
                    config=config,
                    source_ctx=source_context,
                    issues=cs_remaining,
                    accepted_notes=accepted_notes,
                    notes_per_file=notes_per_file,
                )
                if accepted_cs:
                    modified_files.update(i.file for i in accepted_cs)
                    accepted_fps = {i.fingerprint for i in accepted_cs}
                    remaining = [i for i in remaining
                                 if i.fingerprint not in accepted_fps]

        # ---- escalation / per-issue cap ----
        if remaining:
            next_tier = tier + 1
            at_cap = [i for i in remaining if issue_max_tier(i) < next_tier]
            if at_cap:
                capped_out.extend(at_cap)
                at_cap_fps = {x.fingerprint for x in at_cap}
                remaining = [i for i in remaining
                             if i.fingerprint not in at_cap_fps]
                logger.info("Capping %d issue(s) at T%d (max_tier reached)",
                            len(at_cap), tier)
            if remaining:
                logger.info("Escalating %d issues from T%d to T%d",
                            len(remaining), tier, next_tier)
        tier += 1

    # Anything the capped tiers couldn't fix.
    residual = capped_out + remaining

    # ---- Residual source_inherent triage (post-cap, before defer) ----
    # Accept residual L3 semantic issues that are author bugs in the
    # source novel as SourceNotes so they don't become blocking. Only
    # semantic issues are eligible; the rest fall through to Phase C
    # (and the caller's deferred-repair ledger).
    if (residual and triager is not None and notes_writer is not None
            and source_context is not None):
        residual = _run_triage_round(
            triager=triager,
            notes_writer=notes_writer,
            config=config,
            source_ctx=source_context,
            issues=residual,
            triage_round=1,
            accepted_notes=accepted_notes,
            notes_per_file=notes_per_file,
            fixer_candidates=t2_self_report,
        )

    # ---- Length-bound tolerance gate (decision #48) ----
    # When every residual issue is a pure minLength / maxLength schema
    # miss, re-validate the affected files with a relaxed schema (×0.9
    # floor / ×1.1 ceil); if they pass, accept them and signal a terminal
    # PASS instead of leaving them to fail Phase C.
    if length_tolerance_pass(residual, files):
        logger.info(
            "Length-bound tolerance gate accepted %d residual "
            "issue(s) (decision #48).", len(residual))
        lifecycle_signal = "LENGTH_TOLERANCE_PASS"

    return modified_files, modified_paths, t2_self_report, lifecycle_signal


_LENGTH_RULES = ("schema_minLength", "schema_maxLength")


def _all_length_only(issues: list[Issue]) -> bool:
    """True when every issue is a pure minLength/maxLength schema miss."""
    return bool(issues) and all(
        i.category == "schema" and i.rule in _LENGTH_RULES
        for i in issues)


def _sweep_self_inflicted_length(
    recheck_blocking: list[Issue],
    *,
    files: list[FileEntry],
    fixers: dict[int, object],
    prior_fingerprints: set[str],
    round_modified_paths: dict[str, set[str]],
) -> bool:
    """T0-repair length overruns this round's own patches introduced.

    Selection is deliberately narrow — an issue qualifies only when all
    three hold:

    1. it is a pure ``minLength`` / ``maxLength`` schema miss;
    2. its fingerprint was NOT in the round's incoming issue set (so it
       appeared as a consequence of this round's patching, not before it);
    3. its ``json_path`` is one a fix actually touched this round.

    Anything failing those keeps its normal ``route_tiers`` routing and the
    decision #48 tolerance gate — this sweep never pre-empts them.

    Returns True when at least one patch was applied (caller re-runs the
    scoped recheck to pick up the new state).
    """
    t0 = fixers.get(0)
    if t0 is None:
        return False

    self_inflicted = [
        i for i in recheck_blocking
        if i.category == "schema"
        and i.rule in _LENGTH_RULES
        and i.fingerprint not in prior_fingerprints
        and i.json_path in round_modified_paths.get(i.file, set())
    ]
    if not self_inflicted:
        return False

    logger.info(
        "Self-inflicted length sweep: T0-repairing %d overrun(s) a fix "
        "introduced this round", len(self_inflicted))
    result = t0.fix(
        files=files,
        issues=self_inflicted,
        strategy="standard",
        source_context=None,
        attempt_num=0,
        max_attempts=1,
    )
    return bool(result.patched_paths)


def length_tolerance_pass(issues: list[Issue],
                          files: list[FileEntry]) -> bool:
    """True when ``issues`` are all length misses the tolerance accepts.

    Two conditions, and the first is not optional: **every** issue must be a
    pure ``minLength`` / ``maxLength`` schema miss, and the affected files
    must then pass the ×0.9 floor / ×1.1 ceil re-check (decision #48).

    The category guard lives inside rather than at each call site because
    the re-check alone cannot stand in for it: it runs JSON Schema, which is
    blind to whole checker layers. A structural issue would sail through a
    relaxed schema validation and read as "tolerated", silently clearing a
    debt that has nothing to do with length.

    Public because this IS the project's definition of "close enough on a
    length bound". Any later gate that re-adjudicates a schema debt must ask
    the same question the fix loop asked before declaring PASS — a stricter
    second opinion turns a tolerated overrun into a debt nothing can ever
    settle (the fix loop passes it, the gate fails it, forever).
    """
    if not _all_length_only(issues):
        return False
    from extraction.validation.shared.schema_tolerance import (
        validate_with_length_tolerance)

    affected_paths = {i.file for i in issues}
    files_by_path = {f.path: f for f in files}
    for fp in affected_paths:
        fe = files_by_path.get(fp)
        if fe is None or fe.schema is None:
            return False
        content = fe.content if fe.content is not None else fe.load()
        if content is None:
            return False
        # JSONL files validate per-entry (mirrors SchemaChecker).
        entries = content if isinstance(content, list) else [content]
        for entry in entries:
            ok, _ = validate_with_length_tolerance(entry, fe.schema)
            if not ok:
                return False
    return True


def _run_triage_round(
    *,
    triager: Triager,
    notes_writer: NotesWriter,
    config: RepairConfig,
    source_ctx: SourceContext,
    issues: list[Issue],
    triage_round: int,
    accepted_notes: list[SourceNote],
    notes_per_file: dict[str, int],
    fixer_candidates: dict[str, TriageVerdict],
) -> list[Issue]:
    """Run one triage pass; persist accepted notes; return remaining issues.

    ``triage_round`` is 1 for the residual (post-cap) triage and 2 for
    post-gate triage. Enforces the per-file accept cap from config.
    """
    if not issues:
        return []

    # Only L3 `semantic` issues are eligible for accept_with_notes.
    # Mechanical errors (L0 syntax / L1 schema / L2 structural) can't be
    # "the source novel's fault" — keep them in the queue untouched.
    semantic_issues = [i for i in issues if i.category == "semantic"]
    non_semantic = [i for i in issues if i.category != "semantic"]
    if not semantic_issues:
        return list(issues)

    by_file: dict[str, list[Issue]] = {}
    for i in semantic_issues:
        by_file.setdefault(i.file, []).append(i)

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    round_notes: list[SourceNote] = []
    accepted_fps: set[str] = set()

    for file_path, file_issues in by_file.items():
        already = notes_per_file.get(file_path, 0)
        cap_remaining = config.accept_cap_per_file - already
        if cap_remaining <= 0:
            continue

        file_prior = {
            fp: v for fp, v in fixer_candidates.items()
            if any(i.fingerprint == fp for i in file_issues)
        }

        verdicts = triager.triage_file(
            file_path=file_path,
            issues=file_issues,
            source_ctx=source_ctx,
            accept_cap=cap_remaining,
            fixer_candidates=file_prior,
        )

        for v in verdicts:
            issue = next((i for i in file_issues
                          if i.fingerprint == v.issue_fingerprint), None)
            if issue is None:
                continue
            note_id = notes_writer.allocate_note_id(
                file_path, source_ctx.stage_id)
            note = triager.build_source_note(
                verdict=v,
                issue=issue,
                source_ctx=source_ctx,
                note_id=note_id,
                accepted_at=now_iso,
                triage_round=triage_round,
            )
            if note is None:
                continue
            round_notes.append(note)
            accepted_notes.append(note)
            accepted_fps.add(v.issue_fingerprint)
            notes_per_file[file_path] = (
                notes_per_file.get(file_path, 0) + 1)

    if round_notes:
        notes_writer.append(round_notes)
        logger.info(
            "triage round %d: accepted %d issue(s) as source_inherent",
            triage_round, len(round_notes))

    remaining_semantic = [
        i for i in semantic_issues if i.fingerprint not in accepted_fps
    ]
    return non_semantic + remaining_semantic


def _run_coverage_shortage_triage(
    *,
    triager: Triager,
    notes_writer: NotesWriter,
    config: RepairConfig,
    source_ctx: SourceContext,
    issues: list[Issue],
    accepted_notes: list[SourceNote],
    notes_per_file: dict[str, int],
) -> list[Issue]:
    """Accept L2 `min_examples` shortages via program-constructed
    SourceNotes (0 token). Returns the list of issues actually accepted.

    Shares ``accept_cap_per_file`` with the L3 source_inherent triage —
    overflow issues stay blocking and surface as warnings on the final
    report. ``triage_round=1`` (treated as first-pass acceptance) because
    coverage_shortage runs once per issue per stage.
    """
    if not issues:
        return []

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    accepted_issues: list[Issue] = []
    round_notes: list[SourceNote] = []

    by_file: dict[str, list[Issue]] = {}
    for i in issues:
        by_file.setdefault(i.file, []).append(i)

    for file_path, file_issues in by_file.items():
        already = notes_per_file.get(file_path, 0)
        cap_remaining = config.accept_cap_per_file - already
        if cap_remaining <= 0:
            logger.info(
                "coverage_shortage: %s — cap reached, %d issue(s) stay "
                "blocking", file_path, len(file_issues))
            continue

        taken = 0
        for issue in file_issues:
            if taken >= cap_remaining:
                logger.info(
                    "coverage_shortage: %s — per-file cap %d reached, "
                    "dropping %d remaining issue(s)",
                    file_path, config.accept_cap_per_file,
                    len(file_issues) - taken)
                break
            verdict = triager.build_coverage_shortage_verdict(
                issue, source_ctx)
            if verdict is None:
                continue
            note_id = notes_writer.allocate_note_id(
                file_path, source_ctx.stage_id)
            note = triager.build_source_note(
                verdict=verdict,
                issue=issue,
                source_ctx=source_ctx,
                note_id=note_id,
                accepted_at=now_iso,
                triage_round=1,
            )
            if note is None:
                continue
            round_notes.append(note)
            accepted_notes.append(note)
            accepted_issues.append(issue)
            notes_per_file[file_path] = (
                notes_per_file.get(file_path, 0) + 1)
            taken += 1

    if round_notes:
        notes_writer.append(round_notes)
        logger.info(
            "coverage_shortage: accepted %d issue(s) as 0-token SourceNote",
            len(round_notes))

    return accepted_issues


def _build_report(
    issues: list[Issue],
    history: dict[str, list[RepairAttempt]],
    passed: bool,
    *,
    terminated_by: str,
    accepted_notes: list[SourceNote] | None = None,
) -> str:
    lines = [f"Repair {'PASSED' if passed else 'FAILED'}"]
    lines.append(f"Final issues: {len(issues)}")

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    lines.append(f"  errors: {len(errors)}, warnings: {len(warnings)}")

    if accepted_notes:
        lines.append(f"Accepted source_inherent notes: {len(accepted_notes)}")
        for n in accepted_notes:
            lines.append(f"  {n.note_id} [{n.discrepancy_type}] "
                         f"{n.file} {n.json_path}")

    if history:
        total_attempts = sum(len(v) for v in history.values())
        lines.append(f"Total repair attempts: {total_attempts}")

    if errors:
        lines.append("\nRemaining errors:")
        for i in errors:
            lines.append(f"  {i}")

    return "\n".join(lines)
