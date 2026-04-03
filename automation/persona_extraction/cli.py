"""CLI entry point for the extraction orchestrator."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .llm_backend import create_backend
from .orchestrator import ExtractionOrchestrator
from .progress import ExtractionProgress


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
        "--end-batch",
        type=int,
        default=None,
        help="Stop after batch N (0 = all)",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from existing progress (skip analysis)",
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
    )

    if args.resume:
        progress = ExtractionProgress.load(project_root, args.work_id)
        if not progress:
            print(f"[ERROR] No existing progress for '{args.work_id}'.")
            sys.exit(1)
        orch.run_extraction_loop(progress)
    else:
        orch.run_full(
            preset_characters=args.characters,
            preset_end_batch=args.end_batch,
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
