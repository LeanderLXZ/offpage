"""Smoke test for cli.py --background stage-aware validation (decision #51).

The validation logic at cli.py's `if args.background:` block reads
``works/{work_id}/analysis/progress/pipeline.json`` and decides whether
``--characters`` is required:

  - phase_1_5 == "done" → no Phase 1.5 stdin prompt awaits, --characters
    is optional; CLI proceeds to launch_background.
  - phase_1_5 != "done" (or pipeline.json missing / unreadable) →
    --characters mandatory; without it, sys.exit(1) with a specific
    error message.

Four scenarios cover the matrix:

  (A) phase_1_5 done + --resume --background, no --characters
        → accept (proceed to launch_background)
  (B) phase_1_5 pending + --resume --background, no --characters
        → reject with sys.exit(1) + "phase_1_5 is not yet done"
  (C) phase_1_5 pending + --background --characters X
        → accept (--characters short-circuits the Phase 1.5 prompt)
  (D) pipeline.json absent + --background --characters X
        → accept (no pipeline → treated as phase_1_5 not done, but
          --characters satisfies the requirement)

The smoke patches ``launch_background`` so accepted paths exit 0 without
actually daemonizing, and patches ``validate_source_package`` /
``preflight_check`` so the test only exercises the validation branch.

Run:  python -m automation.persona_extraction._smoke_cli_resume_background_validation
"""

from __future__ import annotations

import json
import sys
import tempfile
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from unittest.mock import patch


WORK_ID = "smoke_work"


def _make_project(root: Path, *, phase_1_5: str | None) -> Path:
    """Build a minimal project root with sources/ + optional pipeline.json.

    phase_1_5: "done" / "pending" / None (omit pipeline.json entirely).
    """
    project = root / "project"
    (project / "schemas").mkdir(parents=True, exist_ok=True)

    src = project / "sources" / "works" / WORK_ID
    (src / "metadata").mkdir(parents=True, exist_ok=True)
    (src / "manifest.json").write_text(json.dumps({
        "schema_version": "1.0.0",
        "work_id": WORK_ID,
        "structure_mode": "monolithic",
    }, ensure_ascii=False), encoding="utf-8")

    if phase_1_5 is not None:
        prog = project / "works" / WORK_ID / "analysis" / "progress"
        prog.mkdir(parents=True, exist_ok=True)
        (prog / "pipeline.json").write_text(json.dumps({
            "work_id": WORK_ID,
            "phases": {
                "phase_0": "done",
                "phase_1": "done" if phase_1_5 == "done" else "pending",
                "phase_1_5": phase_1_5,
            },
        }, ensure_ascii=False), encoding="utf-8")

    return project


@contextmanager
def _capture_argv_and_stdio(argv: list[str]):
    """Patch sys.argv + capture stdout/stderr; restore on exit."""
    saved_argv = sys.argv
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    sys.argv = ["persona-extract"] + argv
    sys.stdout = StringIO()
    sys.stderr = StringIO()
    try:
        yield sys.stdout, sys.stderr
    finally:
        sys.argv = saved_argv
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr


def _run(argv: list[str]) -> tuple[int, str]:
    """Invoke cli.main([...]) and return (exit_code, stdout+stderr)."""
    from automation.persona_extraction import cli

    with _capture_argv_and_stdio(argv) as (out, err):
        with patch.object(cli, "launch_background") as mock_launch, \
                patch.object(cli, "validate_source_package",
                             side_effect=AssertionError(
                                 "should not reach validate_source_package")):
            mock_launch.return_value = None
            try:
                cli.main(argv)
                code = 0
            except SystemExit as e:
                code = e.code if isinstance(e.code, int) else 1
        text = out.getvalue() + err.getvalue()
    return code, text


def _scenario_a(root: Path) -> bool:
    """phase_1_5 done + --resume --background, no --characters → accept."""
    project = _make_project(root, phase_1_5="done")
    code, text = _run([
        WORK_ID, "--project-root", str(project),
        "--resume", "--background",
    ])
    ok = code == 0 and "phase_1_5 is not yet done" not in text
    print(f"[A] phase_1_5=done + --resume --background no --characters: "
          f"exit={code} → {'OK' if ok else 'FAIL'}")
    if not ok:
        print(f"  stdout/stderr: {text!r}")
    return ok


def _scenario_b(root: Path) -> bool:
    """phase_1_5 pending + --resume --background → reject."""
    project = _make_project(root, phase_1_5="pending")
    code, text = _run([
        WORK_ID, "--project-root", str(project),
        "--resume", "--background",
    ])
    ok = code == 1 and "phase_1_5 is not yet done" in text
    print(f"[B] phase_1_5=pending + --resume --background no --characters: "
          f"exit={code} expect 1 + msg → {'OK' if ok else 'FAIL'}")
    if not ok:
        print(f"  stdout/stderr: {text!r}")
    return ok


def _scenario_c(root: Path) -> bool:
    """phase_1_5 pending + --background --characters X → accept."""
    project = _make_project(root, phase_1_5="pending")
    code, text = _run([
        WORK_ID, "--project-root", str(project),
        "--background", "--characters", "char_a",
    ])
    ok = code == 0 and "phase_1_5 is not yet done" not in text
    print(f"[C] phase_1_5=pending + --background --characters X: "
          f"exit={code} → {'OK' if ok else 'FAIL'}")
    if not ok:
        print(f"  stdout/stderr: {text!r}")
    return ok


def _scenario_d(root: Path) -> bool:
    """pipeline.json absent + --background --characters X → accept."""
    project = _make_project(root, phase_1_5=None)
    code, text = _run([
        WORK_ID, "--project-root", str(project),
        "--background", "--characters", "char_a",
    ])
    ok = code == 0 and "phase_1_5 is not yet done" not in text
    print(f"[D] no pipeline.json + --background --characters X: "
          f"exit={code} → {'OK' if ok else 'FAIL'}")
    if not ok:
        print(f"  stdout/stderr: {text!r}")
    return ok


def main() -> int:
    results: list[bool] = []
    for fn, name in [
        (_scenario_a, "A"),
        (_scenario_b, "B"),
        (_scenario_c, "C"),
        (_scenario_d, "D"),
    ]:
        with tempfile.TemporaryDirectory(prefix=f"smoke_cli_bg_{name}_") as td:
            results.append(fn(Path(td)))

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\nSummary: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
