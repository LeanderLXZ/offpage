"""CLI entry point for the extraction orchestrator."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from automation.ingestion.validator import validate_source_package
from .config import get_config
from .git_utils import preflight_check
from .llm_backend import create_backend
from .orchestrator import ExtractionOrchestrator
from .process_guard import launch_background
from .rate_limit import RateLimitHardStop, WEEKLY_EXIT_CODE
from .scene_archive import run_scene_archive

# Phase 4 does not need git preflight (no commits) and uses its own lock.
VALID_PHASES = ("auto", "0", "1", "1.5", "2", "3", "3.5", "4")


def _load_pipeline_status(project_root: Path, work_id: str) -> dict | None:
    """Read pipeline.json for ``--background`` stage-aware validation only.

    Decision #51: ``--background`` must inspect ``phases.phase_1_5`` to
    decide whether ``--characters`` is required (avoiding stdin deadlock at
    ``confirm_with_user``). Kept as a thin JSON read so cli.py does not
    pull the full ``PipelineProgress`` dataclass surface — that lives
    inside the orchestrator path. Missing / unreadable / malformed file
    → ``None`` (caller treats this as "phase_1_5 not done").
    """
    path = (project_root / "works" / work_id / "analysis"
            / "progress" / "pipeline.json")
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def main(argv: list[str] | None = None) -> None:
    cfg = get_config()
    parser = argparse.ArgumentParser(
        prog="persona-extract",
        description="Automated stage extraction for Offpage",
    )
    parser.add_argument(
        "work_id",
        help="Work ID (directory name under sources/works/)",
    )
    parser.add_argument(
        "--project-root", "-r",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: cwd)",
    )
    parser.add_argument(
        "--backend", "-b",
        choices=["claude", "codex"],
        default=cfg.runtime.default_backend,
        help=f"LLM backend to use "
             f"(default: {cfg.runtime.default_backend}, "
             f"from [runtime].default_backend)",
    )
    parser.add_argument(
        "--reviewer-backend",
        choices=["claude", "codex"],
        default=None,
        help="LLM backend for reviewer (default: same as --backend)",
    )
    parser.add_argument(
        "--model", "-m",
        default="claude-opus-4-7",
        help="Model for extraction (default: claude-opus-4-7)",
    )
    parser.add_argument(
        "--effort",
        choices=["low", "medium", "high", "max"],
        default="max",
        help="Effort level for LLM reasoning (default: max)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=cfg.phase3.max_turns,
        help=f"Max agent turns per invocation "
             f"(default: {cfg.phase3.max_turns}, from [phase3].max_turns)",
    )
    parser.add_argument(
        "--characters", "-c",
        nargs="+",
        default=None,
        help="Pre-select character IDs (skip interactive prompt)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=20,
        help="Chapters per summarization chunk (default: 20)",
    )
    parser.add_argument(
        "--end-stage",
        type=int,
        default=None,
        help="Stop after stage N completes (0 = baseline only, omit = all)",
    )
    parser.add_argument(
        "--start-phase",
        choices=VALID_PHASES,
        default="auto",
        help="Start from this phase (default: auto-detect). "
             "Phases: 0 (summarization), 1 (analysis), 1.5 (confirmation), "
             "2 (baseline), 3 (extraction), 3.5 (consistency), 4 (scenes)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help=f"Max parallel workers. If omitted, defaults to "
             f"[phase0].concurrency ({cfg.phase0.concurrency}) for the full "
             f"pipeline / auto path, and [phase4].concurrency "
             f"({cfg.phase4.concurrency}) for --start-phase 4 standalone "
             f"runs. Pass an explicit value to override both.",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Auto-yes the 'Resume from existing progress?' prompt. "
             "run_full is the phase-agnostic resume entry point and skips "
             "/ self-heals already-completed phases on every invocation; "
             "this flag only silences the interactive confirm "
             "(decision #51).",
    )
    parser.add_argument(
        "--background", action="store_true",
        help="Run in background (survives SSH disconnect). "
             "Stage-aware validation (decision #51): phase_1_5 not done "
             "→ --characters required (else Phase 1.5 stdin prompt "
             "deadlocks the daemon); phase_1_5 done → --resume or "
             "--characters required (else 'Resume from existing "
             "progress?' stdin prompt deadlocks the daemon).",
    )
    parser.add_argument(
        "--max-runtime",
        type=int,
        default=cfg.runtime.max_runtime_min_default,
        help=f"Max total runtime in minutes (0 = unlimited; "
             f"default: {cfg.runtime.max_runtime_min_default}, "
             f"from [runtime].max_runtime_min_default). "
             f"Rate-limit pause time is excluded.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args(argv)

    # Logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    project_root = args.project_root.resolve()
    if not (project_root / "schemas").exists():
        print(f"[ERROR] {project_root} does not look like an Offpage "
              f"project root (no schemas/ directory).")
        sys.exit(1)

    # Resolve --concurrency default by start phase: [phase4].concurrency
    # for the standalone Phase 4 entry point, [phase0].concurrency for
    # the full pipeline / auto path. Explicit --concurrency wins over
    # either default.
    if args.concurrency is None:
        args.concurrency = (
            cfg.phase4.concurrency
            if args.start_phase == "4"
            else cfg.phase0.concurrency)

    # --- Phase 4 standalone path (independent lock, no git operations) ---
    if args.start_phase == "4":
        if args.background:
            extra = [a for a in sys.argv[1:] if a != "--background"]
            launch_background(args.work_id, project_root, extra)
            sys.exit(0)
        backend = create_backend(
            args.backend, project_root,
            max_turns=args.max_turns, model=args.model,
            effort=args.effort)
        try:
            success = run_scene_archive(
                project_root, args.work_id, backend,
                concurrency=args.concurrency,
                end_stage=args.end_stage or 0,
                resume=args.resume,
            )
        except RateLimitHardStop as exc:
            print(f"\n[RATE_LIMIT_HARD_STOP] {exc.reason}: {exc.detail}")
            print("  See works/<work_id>/analysis/progress/"
                  "rate_limit_exit.log and re-run --resume after reset.")
            sys.exit(WEEKLY_EXIT_CODE)
        sys.exit(0 if success else 1)

    # --- Background mode (Phase 0-3.5) ---
    if args.background:
        # Decision #51: --background can't survive any stdin prompt; the
        # validator must cover every prompt site reachable on the daemon
        # path.
        #
        #   * Phase 1.5 not done → confirm_with_user fires TWO stdin
        #     prompts: (1) character selection, bypassed by --characters;
        #     (2) "Extract up to stage N", bypassed by --end-stage. Both
        #     are required when phase_1_5 is pending.
        #   * Phase 1.5 done    → run_full asks "Resume from existing
        #     progress? [Y/n]"; --resume (auto_resume signal) silences it,
        #     --characters takes the preset branch which also skips it.
        #     The end_stage prompt is not reached on this branch
        #     (run_extraction_loop accepts max_stages=None as legitimate
        #     "no limit" semantics).
        #
        # Either way every branch must reject any combination that lets
        # a stdin prompt reach the daemon.
        pipeline_status = _load_pipeline_status(project_root, args.work_id)
        phase15_done = (
            pipeline_status is not None
            and pipeline_status.get("phases", {}).get("phase_1_5") == "done")
        if not phase15_done:
            if not args.characters:
                print("[ERROR] --background requires --characters when "
                      "phase_1_5 is not yet done (orchestrator would block "
                      "on the interactive Phase 1.5 character-selection "
                      "prompt).")
                sys.exit(1)
            if args.end_stage is None:
                print("[ERROR] --background requires --end-stage when "
                      "phase_1_5 is not yet done (orchestrator would block "
                      "on the interactive Phase 1.5 'Extract up to stage N' "
                      "prompt). Pass --end-stage <N> where N is the number "
                      "of stages to extract (or 0 for baseline-only).")
                sys.exit(1)
        else:
            if not args.resume and not args.characters:
                print("[ERROR] --background requires --resume or "
                      "--characters when phase_1_5 is done (orchestrator "
                      "would block on the 'Resume from existing "
                      "progress?' prompt).")
                sys.exit(1)
        extra = [a for a in sys.argv[1:] if a != "--background"]
        launch_background(args.work_id, project_root, extra)
        sys.exit(0)

    # --- Standard Phase 0-3.5 path ---

    # Create backends
    backend = create_backend(
        args.backend, project_root,
        max_turns=args.max_turns, model=args.model,
        effort=args.effort)

    reviewer_backend = None
    if args.reviewer_backend:
        reviewer_backend = create_backend(
            args.reviewer_backend, project_root,
            max_turns=30, model=args.model,
            effort=args.effort)

    orch = ExtractionOrchestrator(
        project_root=project_root,
        work_id=args.work_id,
        backend=backend,
        reviewer_backend=reviewer_backend,
        chunk_size=args.chunk_size,
        max_runtime_minutes=args.max_runtime,
        start_phase=args.start_phase,
        concurrency=args.concurrency,
    )

    # Acquire lock
    if not orch.acquire_lock():
        sys.exit(1)

    # --- Pre-flight: check git working tree ---
    # Scope the dirty check to the extraction's commit path — unrelated
    # dirt (IDE config, editor state under .claude/) shouldn't block a run
    # since the orchestrator only commits under works/{work_id}/.
    problems = preflight_check(
        project_root,
        ignore_patterns=["extraction_progress.json", "__pycache__",
                         "scene_archive"],
        scope_paths=[f"works/{args.work_id}/"])
    if problems:
        for p in problems:
            print(f"[PREFLIGHT] {p}")
        orch.release_lock()
        sys.exit(1)

    # --- Ingestion gate: source package must validate before any phase ---
    # Mirrors `python -m automation.ingestion.validator <work_id>` so users
    # who skip the manual gate cannot bypass the schema + structure_mode
    # ⇔ chapter_index profile cross-file assertion (decision #27j).
    ingest_report = validate_source_package(project_root, args.work_id)
    if not ingest_report.passed:
        print(ingest_report.summary())
        orch.release_lock()
        sys.exit(1)

    try:
        # Decision #51: run_full is the phase-agnostic resume entry point.
        # It internally does migrate_legacy_progress + load + self-heal
        # (rebuild phase3_stages.json from stage_plan.json when phase_1_5
        # done) + reconcile_with_disk + branch on phase_1_5 done →
        # run_extraction_loop, otherwise drives Phase 0 → 1 → 1.5 → 2 → 3
        # with each phase already skip-detecting completed work. --resume
        # only silences the "Resume from existing progress? [Y/n]" prompt.
        orch.run_full(
            preset_characters=args.characters,
            preset_end_stage=args.end_stage,
            auto_resume=args.resume,
        )

        print("\nDone.")
    except RateLimitHardStop as exc:
        # Raised from rate_limit.wait_if_paused (weekly / probe
        # hard-stop). Reach here from either the main-thread pre-launch
        # gate or from a worker's Future.result() re-raise. Details are
        # already in rate_limit_exit.log; print a concise operator hint
        # and exit with the agreed signal.
        print(f"\n[RATE_LIMIT_HARD_STOP] {exc.reason}: {exc.detail}")
        print("  See works/<work_id>/analysis/progress/"
              "rate_limit_exit.log and re-run --resume after reset.")
        sys.exit(WEEKLY_EXIT_CODE)
    finally:
        orch.release_lock()


if __name__ == "__main__":
    main()
