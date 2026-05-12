"""Smoke test for cli.py --background stage-aware validation (decisions #51 + #56).

The validation logic at cli.py's `if args.background:` block reads
``works/{work_id}/analysis/progress/pipeline.json`` and rejects only
the prompt sites that would traceback-exit the daemon. Phase 1.5 not
done has ONE blocking prompt site — character list (bypassed by
``--characters``). The "Extract up to stage N" prompt is non-blocking:
its daemon EOFError path falls back to ``preset_end_stage = None`` =
run all stages (decision #56), aligned with the ``--end-stage`` flag's
"omit = all" design. Phase 1.5 done has one stdin prompt site —
``"Resume from existing progress?"`` — bypassed by ``--resume``
(auto_resume signal) or ``--characters`` (preset path).

Nine scenarios cover the truth table:

  (A) phase_1_5 done + --resume --background, no --characters
        → accept (--resume bypasses the resume prompt)
  (B) phase_1_5 pending + --resume --background, no --characters
        → reject with sys.exit(1) + "character-selection prompt"
          (missing --characters)
  (C) phase_1_5 pending + --background --characters X (no --end-stage)
        → accept (decision #56: --end-stage omit = run all stages;
          daemon EOFError fallback preset_end_stage=None is safe)
  (D) pipeline.json absent + --background --characters X (no --end-stage)
        → accept (no pipeline → treated as phase_1_5 not done; only
          --characters is required since #56)
  (E) phase_1_5 done + --background, no --resume / no --characters
        → reject with sys.exit(1) + "phase_1_5 is done" (would
          deadlock on the 'Resume from existing progress?' prompt)
  (F) phase_1_5 done + --background --characters X, no --resume
        → accept (--characters alone bypasses the resume prompt via
          the preset_characters branch; --end-stage not required on
          this branch since run_extraction_loop accepts max_stages=None)
  (G) phase_1_5 pending + --background --characters X --end-stage 0
        → accept (explicit --end-stage 0 = baseline only still works)
  (H) pipeline.json absent + --background --characters X --end-stage 50
        → accept (explicit --end-stage still works)
  (I) --end-stage -1 → argparse reject (exit 2 + ">= 0" in stderr)
        → ``_nonneg_int`` argparse type guards against negative values
          that would otherwise pass ``args.end_stage is None`` check and
          reach run_extraction_loop with max_stages=-1 (silent truncation
          via line 1853 ``tracker.completed >= max_stages``)

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
    """phase_1_5 pending + --resume --background (no --characters) → reject."""
    project = _make_project(root, phase_1_5="pending")
    code, text = _run([
        WORK_ID, "--project-root", str(project),
        "--resume", "--background",
    ])
    ok = code == 1 and "character-selection prompt" in text
    print(f"[B] phase_1_5=pending + --resume --background no --characters: "
          f"exit={code} expect 1 + msg → {'OK' if ok else 'FAIL'}")
    if not ok:
        print(f"  stdout/stderr: {text!r}")
    return ok


def _scenario_c(root: Path) -> bool:
    """phase_1_5 pending + --background --characters X (no --end-stage) → accept.

    Decision #56: omitting --end-stage is a legitimate "run all stages"
    request. Daemon EOFError on the "Extract up to stage N" prompt falls
    back to preset_end_stage=None, which run_extraction_loop accepts as
    "no limit". The validator must NOT reject this combination.
    """
    project = _make_project(root, phase_1_5="pending")
    code, text = _run([
        WORK_ID, "--project-root", str(project),
        "--background", "--characters", "char_a",
    ])
    ok = code == 0 and "Extract up to stage N" not in text \
        and "character-selection prompt" not in text
    print(f"[C] phase_1_5=pending + --background --characters X (no --end-stage): "
          f"exit={code} expect 0 (accept; --end-stage omit = all) → "
          f"{'OK' if ok else 'FAIL'}")
    if not ok:
        print(f"  stdout/stderr: {text!r}")
    return ok


def _scenario_d(root: Path) -> bool:
    """pipeline.json absent + --background --characters X (no --end-stage) → accept.

    Decision #56: same as scenario C — no-pipeline path is treated as
    phase_1_5 not done; only --characters is required.
    """
    project = _make_project(root, phase_1_5=None)
    code, text = _run([
        WORK_ID, "--project-root", str(project),
        "--background", "--characters", "char_a",
    ])
    ok = code == 0 and "Extract up to stage N" not in text \
        and "character-selection prompt" not in text
    print(f"[D] no pipeline.json + --background --characters X (no --end-stage): "
          f"exit={code} expect 0 (accept; --end-stage omit = all) → "
          f"{'OK' if ok else 'FAIL'}")
    if not ok:
        print(f"  stdout/stderr: {text!r}")
    return ok


def _scenario_e(root: Path) -> bool:
    """phase_1_5 done + --background, no --resume / no --characters → reject."""
    project = _make_project(root, phase_1_5="done")
    code, text = _run([
        WORK_ID, "--project-root", str(project),
        "--background",
    ])
    ok = code == 1 and "phase_1_5 is done" in text
    print(f"[E] phase_1_5=done + --background no --resume no --characters: "
          f"exit={code} expect 1 + msg → {'OK' if ok else 'FAIL'}")
    if not ok:
        print(f"  stdout/stderr: {text!r}")
    return ok


def _scenario_f(root: Path) -> bool:
    """phase_1_5 done + --background --characters X (no --resume) → accept."""
    project = _make_project(root, phase_1_5="done")
    code, text = _run([
        WORK_ID, "--project-root", str(project),
        "--background", "--characters", "char_a",
    ])
    ok = code == 0 and "phase_1_5 is done" not in text
    print(f"[F] phase_1_5=done + --background --characters X (no --resume): "
          f"exit={code} → {'OK' if ok else 'FAIL'}")
    if not ok:
        print(f"  stdout/stderr: {text!r}")
    return ok


def _scenario_g(root: Path) -> bool:
    """phase_1_5 pending + --background --characters X --end-stage 0 → accept."""
    project = _make_project(root, phase_1_5="pending")
    code, text = _run([
        WORK_ID, "--project-root", str(project),
        "--background", "--characters", "char_a",
        "--end-stage", "0",
    ])
    ok = code == 0 and "character-selection prompt" not in text \
        and "Extract up to stage N" not in text
    print(f"[G] phase_1_5=pending + --background --characters X --end-stage 0: "
          f"exit={code} → {'OK' if ok else 'FAIL'}")
    if not ok:
        print(f"  stdout/stderr: {text!r}")
    return ok


def _scenario_h(root: Path) -> bool:
    """pipeline.json absent + --background --characters X --end-stage 50 → accept."""
    project = _make_project(root, phase_1_5=None)
    code, text = _run([
        WORK_ID, "--project-root", str(project),
        "--background", "--characters", "char_a",
        "--end-stage", "50",
    ])
    ok = code == 0 and "character-selection prompt" not in text \
        and "Extract up to stage N" not in text
    print(f"[H] no pipeline.json + --background --characters X --end-stage 50: "
          f"exit={code} → {'OK' if ok else 'FAIL'}")
    if not ok:
        print(f"  stdout/stderr: {text!r}")
    return ok


def _scenario_i(root: Path) -> bool:
    """--end-stage -1 → argparse reject (exit 2 + ">= 0" in stderr).

    Validates the ``_nonneg_int`` argparse type guards against negative
    values that would otherwise pass the ``args.end_stage is None`` check
    and reach run_extraction_loop with max_stages=-1, where line 1853's
    ``tracker.completed >= max_stages`` would immediately be True after
    the first stage (silent truncation).
    """
    project = _make_project(root, phase_1_5="pending")
    code, text = _run([
        WORK_ID, "--project-root", str(project),
        "--background", "--characters", "char_a",
        "--end-stage", "-1",
    ])
    # argparse error → SystemExit(2); stderr should mention ">= 0"
    ok = code == 2 and ">= 0" in text
    print(f"[I] --end-stage -1 → argparse reject: "
          f"exit={code} expect 2 + msg → {'OK' if ok else 'FAIL'}")
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
        (_scenario_e, "E"),
        (_scenario_f, "F"),
        (_scenario_g, "G"),
        (_scenario_h, "H"),
        (_scenario_i, "I"),
    ]:
        with tempfile.TemporaryDirectory(prefix=f"smoke_cli_bg_{name}_") as td:
            results.append(fn(Path(td)))

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\nSummary: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
