"""Aggregate entry point: run every repair smoke test in one shot.

    python -m extraction.repair.tests

Runs each smoke module in turn and reports a per-module verdict. Exits
non-zero when any module fails, so this is the single command to invoke
after touching anything under ``extraction/repair/`` (see
``ai_context/conventions.md`` §Post-Change Checklist).

Every module keeps running even after an earlier one fails — one broken
smoke should not hide the state of the others.
"""

from __future__ import annotations

from . import _smoke_l3_gate, _smoke_triage


MODULES = [
    ("_smoke_triage", _smoke_triage.main),
    ("_smoke_l3_gate", _smoke_l3_gate.main),
]


def main() -> int:
    failed: list[str] = []
    for name, entry in MODULES:
        print(f"\n=== {name} ===")
        try:
            rc = entry()
        except Exception as exc:  # AssertionError included — keep going
            print(f"[{name}] FAILED: {type(exc).__name__}: {exc}")
            failed.append(name)
            continue
        if rc:
            print(f"[{name}] FAILED: exit code {rc}")
            failed.append(name)

    print("\n=== summary ===")
    if failed:
        print(f"FAILED: {', '.join(failed)} "
              f"({len(failed)}/{len(MODULES)} module(s))")
        return 1
    print(f"OK — all {len(MODULES)} smoke module(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
