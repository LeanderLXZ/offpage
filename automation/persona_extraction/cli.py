"""CLI entry point for the extraction orchestrator."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .git_utils import preflight_check
from .llm_backend import create_backend
from .orchestrator import ExtractionOrchestrator
from .process_guard import launch_background
from .progress import ExtractionProgress
from .scene_archive import run_scene_archive

# Phase 4 does not need git preflight (no commits), but shares the lock.
VALID_PHASES = ("auto", "0", "1", "2", "2.5", "3", "3.5", "4")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="persona-extract",
        description="Automated batch extraction for persona-engine",
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
        default="claude",
        help="LLM backend to use (default: claude)",
    )
    parser.add_argument(
        "--reviewer-backend",
        choices=["claude", "codex"],
        default=None,
        help="LLM backend for reviewer (default: same as --backend)",
    )
    parser.add_argument(
        "--model", "-m",
        default="claude-opus-4-6",
        help="Model for extraction (default: claude-opus-4-6)",
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
        default=50,
        help="Max agent turns per invocation (default: 50)",
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
        "--end-batch",
        type=int,
        default=None,
        help="Stop after batch N (0 = all)",
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
        default=10,
        help="Max parallel workers for Phase 0 and Phase 4 (default: 10)",
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
        default=0,
        help="Max total runtime in minutes (0 = unlimited). "
             "Stops gracefully after limit.",
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

    # --- Phase 4 standalone path (no lock — no git operations) ---
    if args.start_phase == "4":
        if args.background:
            extra = [a for a in sys.argv[1:] if a != "--background"]
            launch_background(args.work_id, project_root, extra)
            sys.exit(0)
        backend = create_backend(
            args.backend, project_root,
            max_turns=args.max_turns, model=args.model,
            effort=args.effort)
        success = run_scene_archive(
            project_root, args.work_id, backend,
            concurrency=args.concurrency,
            end_batch=args.end_batch or 0,
            resume=args.resume,
        )
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
            progress = ExtractionProgress.load(project_root, args.work_id)
            if not progress:
                print(f"[ERROR] No existing progress for '{args.work_id}'.")
                sys.exit(1)
            orch.run_extraction_loop(progress,
                                     max_batches=args.end_batch or 0)
        else:
            orch.run_full(
                preset_characters=args.characters,
                preset_end_batch=args.end_batch,
            )

        print("\nDone.")
    finally:
        orch.release_lock()


if __name__ == "__main__":
    main()
