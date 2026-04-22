"""CLI entry point for the extraction orchestrator."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import get_config
from .git_utils import preflight_check
from .llm_backend import create_backend
from .orchestrator import ExtractionOrchestrator
from .process_guard import launch_background
from .progress import (
    Phase3Progress, PipelineProgress, StageEntry,
    migrate_legacy_progress,
)
from .rate_limit import RateLimitHardStop, WEEKLY_EXIT_CODE
from .scene_archive import run_scene_archive

# Phase 4 does not need git preflight (no commits) and uses its own lock.
VALID_PHASES = ("auto", "0", "1", "2", "2.5", "3", "3.5", "4")


def main(argv: list[str] | None = None) -> None:
    cfg = get_config()
    parser = argparse.ArgumentParser(
        prog="persona-extract",
        description="Automated stage extraction for persona-engine",
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
        default=25,
        help="Chapters per summarization chunk (default: 25)",
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
             "Phases: 0 (summarization), 1 (analysis), 2 (confirmation), "
             "2.5 (baseline), 3 (extraction), 3.5 (consistency), 4 (scenes)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=cfg.phase0.concurrency,
        help=f"Max parallel workers for Phase 0 / Phase 4 "
             f"(default: {cfg.phase0.concurrency}, "
             f"from [phase0].concurrency / [phase4].concurrency)",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from existing progress (skip analysis)",
    )
    parser.add_argument(
        "--background", action="store_true",
        help="Run in background (survives SSH disconnect). "
             "Requires --resume or --characters (no interactive prompts).",
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
        print(f"[ERROR] {project_root} does not look like a persona-engine "
              f"project root (no schemas/ directory).")
        sys.exit(1)

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
        if not args.resume and not args.characters:
            print("[ERROR] --background requires --resume or --characters "
                  "(no interactive prompts in background mode).")
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
    problems = preflight_check(
        project_root,
        ignore_patterns=["extraction_progress.json", "__pycache__",
                         "scene_archive"])
    if problems:
        for p in problems:
            print(f"[PREFLIGHT] {p}")
        orch.release_lock()
        sys.exit(1)

    try:
        if args.resume:
            # Try new format first, then legacy migration
            pipeline = PipelineProgress.load(project_root, args.work_id)
            phase3 = Phase3Progress.load(project_root, args.work_id)

            # Self-heal: rebuild phase3 from stage_plan when pipeline has
            # phase_2 done but phase3_stages.json was deleted/corrupted.
            if (pipeline and pipeline.is_done("phase_2")
                    and phase3 is None):
                stage_plan_path = (
                    project_root / "works" / args.work_id
                    / "analysis" / "stage_plan.json")
                if stage_plan_path.exists():
                    import json as _json
                    sp = _json.loads(
                        stage_plan_path.read_text(encoding="utf-8"))
                    phase3 = Phase3Progress(
                        work_id=args.work_id,
                        stage_size=sp.get("default_stage_size", 10),
                        stages=[
                            StageEntry(
                                stage_id=b["stage_id"],
                                chapters=b["chapters"],
                                chapter_count=b.get("chapter_count", 10),
                                stage_title=b.get("stage_title", ""),
                            )
                            for b in sp.get("stages", [])
                        ],
                    )
                    phase3.save(project_root)
                    print(f"[REBUILT] phase3_stages.json from stage_plan "
                          f"({len(phase3.stages)} stages, all pending).")

            if not pipeline or not phase3:
                migrated = migrate_legacy_progress(
                    project_root, args.work_id)
                if migrated:
                    pipeline, phase3 = migrated
                    print("  [MIGRATE] Converted legacy progress to new format.")
                else:
                    print(f"[ERROR] No existing progress for '{args.work_id}'.")
                    sys.exit(1)

            # Self-heal: reconcile phase3 with actual disk state.
            rec = phase3.reconcile_with_disk(
                project_root, pipeline.target_characters)
            if rec["reverted"] or rec["purged_files"]:
                print(f"[RECONCILE] Phase 3: reverted {rec['reverted']} "
                      f"stage(s), purged {rec['purged_files']} stale "
                      f"artifact(s), {rec['sha_missing']} committed_sha "
                      f"missing from git")
                phase3.save(project_root)

            orch.pipeline = pipeline
            orch.phase3 = phase3
            orch.run_extraction_loop(pipeline, phase3,
                                     max_stages=args.end_stage)
        else:
            orch.run_full(
                preset_characters=args.characters,
                preset_end_stage=args.end_stage,
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
