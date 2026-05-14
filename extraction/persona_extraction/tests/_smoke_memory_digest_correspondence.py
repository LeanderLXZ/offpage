"""Smoke test for Phase 3.5 memory_digest ↔ memory_timeline cross-checks.

Regression cover for the loader blind spot fixed alongside decision #50:
``_check_memory_id_correspondence`` and ``_check_memory_digest_summary_equality``
must now read ``memory_timeline/{stage_id}.json`` (top-level array) through
``_load_json_array``, not ``_load_json`` (object-only).

Four scenarios:
  (A) timeline 1 entry / digest empty
      → expect error category=memory_id, "missing from digest"
  (B) timeline empty / digest 1 entry
      → expect warning category=memory_id, "in digest but not in any timeline"
  (C) timeline 1 entry / digest 1 entry, same memory_id, summary != digest_summary
      → expect error category=memory_digest_summary
  (D) timeline 1 entry / digest 1 entry, same memory_id, summary == digest_summary
      → expect no issue from either check

Run:  python -m extraction.persona_extraction.tests._smoke_memory_digest_correspondence
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from extraction.validation.gates.phase3_5_consistency import (
    _check_memory_digest_summary_equality,
    _check_memory_id_correspondence,
)


WORK_ID = "smoke"
CHAR_ID = "char_a"
STAGE_ID = "S001"


def _build_skeleton(root: Path) -> Path:
    """Create works/{work_id}/characters/{char}/canon/{...} layout, return work_dir."""
    work_dir = root / "works" / WORK_ID
    canon = work_dir / "characters" / CHAR_ID / "canon"
    (canon / "memory_timeline").mkdir(parents=True, exist_ok=True)
    return work_dir


def _write_timeline(work_dir: Path, entries: list[dict]) -> None:
    p = (work_dir / "characters" / CHAR_ID / "canon"
         / "memory_timeline" / f"{STAGE_ID}.json")
    p.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")


def _write_digest(work_dir: Path, entries: list[dict]) -> None:
    p = (work_dir / "characters" / CHAR_ID / "canon"
         / "memory_digest.jsonl")
    p.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in entries),
        encoding="utf-8")


def _scenario_a(root: Path) -> bool:
    """timeline 1 / digest 0 → expect error 'missing from digest'."""
    work_dir = _build_skeleton(root)
    _write_timeline(work_dir, [{
        "memory_id": "M-S001-01",
        "digest_summary": "短摘要",
    }])
    issues = _check_memory_id_correspondence(work_dir, [CHAR_ID], [STAGE_ID])
    matched = [
        i for i in issues
        if i.severity == "error" and i.category == "memory_id"
        and "missing from digest" in i.message
        and "M-S001-01" in i.message]
    ok = len(matched) == 1
    print(f"[A] timeline1/digest0: error_count={len(matched)} (expect 1) → "
          f"{'OK' if ok else 'FAIL'}")
    if not ok:
        for i in issues:
            print(f"  observed: {i}")
    return ok


def _scenario_b(root: Path) -> bool:
    """timeline 0 / digest 1 → expect warning 'in digest but not in any timeline'."""
    work_dir = _build_skeleton(root)
    _write_timeline(work_dir, [])
    _write_digest(work_dir, [{
        "memory_id": "M-S001-01",
        "summary": "短摘要",
        "importance": "minor",
        "time": "某日",
        "location": "某地",
    }])
    issues = _check_memory_id_correspondence(work_dir, [CHAR_ID], [STAGE_ID])
    matched = [
        i for i in issues
        if i.severity == "warning" and i.category == "memory_id"
        and "in digest but not in any timeline" in i.message]
    ok = len(matched) == 1
    print(f"[B] timeline0/digest1: warning_count={len(matched)} (expect 1) → "
          f"{'OK' if ok else 'FAIL'}")
    if not ok:
        for i in issues:
            print(f"  observed: {i}")
    return ok


def _scenario_c(root: Path) -> bool:
    """timeline 1 / digest 1, summary != digest_summary → expect error."""
    work_dir = _build_skeleton(root)
    _write_timeline(work_dir, [{
        "memory_id": "M-S001-01",
        "digest_summary": "字面 A",
    }])
    _write_digest(work_dir, [{
        "memory_id": "M-S001-01",
        "summary": "字面 B (不同)",
        "importance": "minor",
        "time": "某日",
        "location": "某地",
    }])
    issues = _check_memory_digest_summary_equality(
        work_dir, [CHAR_ID], [STAGE_ID])
    matched = [
        i for i in issues
        if i.severity == "error" and i.category == "memory_digest_summary"
        and "M-S001-01" in i.location]
    ok = len(matched) == 1
    print(f"[C] summary!=digest_summary: error_count={len(matched)} "
          f"(expect 1) → {'OK' if ok else 'FAIL'}")
    if not ok:
        for i in issues:
            print(f"  observed: {i}")
    return ok


def _scenario_d(root: Path) -> bool:
    """timeline 1 / digest 1, summary == digest_summary → expect no issue."""
    work_dir = _build_skeleton(root)
    _write_timeline(work_dir, [{
        "memory_id": "M-S001-01",
        "digest_summary": "完全一致的短摘要",
    }])
    _write_digest(work_dir, [{
        "memory_id": "M-S001-01",
        "summary": "完全一致的短摘要",
        "importance": "minor",
        "time": "某日",
        "location": "某地",
    }])
    issues_corr = _check_memory_id_correspondence(
        work_dir, [CHAR_ID], [STAGE_ID])
    issues_eq = _check_memory_digest_summary_equality(
        work_dir, [CHAR_ID], [STAGE_ID])
    ok = not issues_corr and not issues_eq
    print(f"[D] summary==digest_summary: corr={len(issues_corr)} "
          f"eq={len(issues_eq)} (both expect 0) → {'OK' if ok else 'FAIL'}")
    if not ok:
        for i in issues_corr + issues_eq:
            print(f"  observed: {i}")
    return ok


def main() -> int:
    results: list[bool] = []
    for fn, name in [
        (_scenario_a, "A"),
        (_scenario_b, "B"),
        (_scenario_c, "C"),
        (_scenario_d, "D"),
    ]:
        with tempfile.TemporaryDirectory(prefix=f"smoke_mem_corr_{name}_") as td:
            results.append(fn(Path(td)))

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\nSummary: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
