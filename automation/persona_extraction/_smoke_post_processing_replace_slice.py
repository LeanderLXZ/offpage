"""Smoke test for post-processing replace-slice contract (decision #50).

Two scenarios per digest type (memory_digest + world_event_digest):

  (A) Empty source (timeline 0 entries / stage_events empty) +
      existing digest carrying stale entries for this stage
      → after run, file exists, kept = entries from OTHER stages,
      stale entries for THIS stage are gone, warning issue emitted.
  (B) Non-empty source replaces matching-stage entries while
      preserving other-stage entries.

Run:  python -m automation.persona_extraction._smoke_post_processing_replace_slice
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from .post_processing import (
    generate_memory_digest,
    generate_world_event_digest,
)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _scenario_memory_a(root: Path) -> bool:
    """timeline empty + existing S001 stale + S002 keeper → replace-slice removes S001."""
    timeline_path = root / "memory_timeline" / "S001.json"
    timeline_path.parent.mkdir(parents=True, exist_ok=True)
    timeline_path.write_text("[]", encoding="utf-8")

    digest_path = root / "memory_digest.jsonl"
    digest_path.write_text(
        json.dumps({
            "memory_id": "M-S001-01", "summary": "stale S001",
            "importance": "minor", "time": "x", "location": "y",
        }, ensure_ascii=False) + "\n"
        + json.dumps({
            "memory_id": "M-S002-01", "summary": "keep S002",
            "importance": "minor", "time": "x", "location": "y",
        }, ensure_ascii=False) + "\n",
        encoding="utf-8")

    issues = generate_memory_digest(
        timeline_path=timeline_path,
        digest_path=digest_path,
        stage_id="S001",
        schema_dir=None,
    )
    rows = _read_jsonl(digest_path)
    has_warning = any("No digest entries generated" in i for i in issues)
    has_keeper = any(r.get("memory_id") == "M-S002-01" for r in rows)
    no_stale = not any(r.get("memory_id") == "M-S001-01" for r in rows)
    ok = has_warning and has_keeper and no_stale
    print(f"[memory-A] empty timeline + stale S001: rows={len(rows)} "
          f"warn={has_warning} keep_s002={has_keeper} stale_gone={no_stale} → "
          f"{'OK' if ok else 'FAIL'}")
    if not ok:
        for r in rows:
            print(f"  row: {r}")
        for i in issues:
            print(f"  issue: {i}")
    return ok


def _scenario_memory_b(root: Path) -> bool:
    """timeline 1 entry replaces stale S001 entry, S002 keeper preserved."""
    timeline_path = root / "memory_timeline" / "S001.json"
    timeline_path.parent.mkdir(parents=True, exist_ok=True)
    timeline_path.write_text(json.dumps([{
        "memory_id": "M-S001-01",
        "stage_id": "S001",
        "time": "新时间",
        "location": "新地点",
        "event_description": "x" * 160,
        "digest_summary": "新摘要 30+ 字" + "x" * 25,
        "subjective_experience": "y",
        "memory_importance": "minor",
    }], ensure_ascii=False), encoding="utf-8")

    digest_path = root / "memory_digest.jsonl"
    digest_path.write_text(
        json.dumps({
            "memory_id": "M-S001-01", "summary": "stale S001",
            "importance": "minor", "time": "x", "location": "y",
        }, ensure_ascii=False) + "\n"
        + json.dumps({
            "memory_id": "M-S002-01", "summary": "keep S002",
            "importance": "minor", "time": "x", "location": "y",
        }, ensure_ascii=False) + "\n",
        encoding="utf-8")

    issues = generate_memory_digest(
        timeline_path=timeline_path,
        digest_path=digest_path,
        stage_id="S001",
        schema_dir=None,
    )
    rows = _read_jsonl(digest_path)
    new_s001 = next(
        (r for r in rows if r.get("memory_id") == "M-S001-01"), None)
    keeper = next(
        (r for r in rows if r.get("memory_id") == "M-S002-01"), None)
    summary_replaced = (
        new_s001 is not None and new_s001.get("summary") != "stale S001")
    ok = (
        summary_replaced
        and keeper is not None
        and not any("No digest entries generated" in i for i in issues))
    print(f"[memory-B] non-empty timeline replaces S001, keeps S002: "
          f"rows={len(rows)} replaced={summary_replaced} "
          f"keep={keeper is not None} → {'OK' if ok else 'FAIL'}")
    if not ok:
        for r in rows:
            print(f"  row: {r}")
        for i in issues:
            print(f"  issue: {i}")
    return ok


def _scenario_world_a(root: Path) -> bool:
    """stage_events empty + existing E-S001 stale + E-S002 keeper → replace-slice."""
    snapshot_path = root / "world_stage_snapshot_S001.json"
    snapshot_path.write_text(json.dumps({
        "stage_id": "S001",
        "stage_events": [],
    }, ensure_ascii=False), encoding="utf-8")

    digest_path = root / "world_event_digest.jsonl"
    digest_path.write_text(
        json.dumps({
            "event_id": "E-S001-01", "summary": "stale S001 event",
            "importance": "minor", "time": "x", "location": "y",
        }, ensure_ascii=False) + "\n"
        + json.dumps({
            "event_id": "E-S002-01", "summary": "keep S002 event",
            "importance": "minor", "time": "x", "location": "y",
        }, ensure_ascii=False) + "\n",
        encoding="utf-8")

    issues = generate_world_event_digest(
        snapshot_path=snapshot_path,
        digest_path=digest_path,
        stage_id="S001",
        schema_dir=None,
    )
    rows = _read_jsonl(digest_path)
    has_warning = any("No stage_events" in i for i in issues)
    has_keeper = any(r.get("event_id") == "E-S002-01" for r in rows)
    no_stale = not any(r.get("event_id") == "E-S001-01" for r in rows)
    ok = has_warning and has_keeper and no_stale
    print(f"[world-A] empty stage_events + stale S001: rows={len(rows)} "
          f"warn={has_warning} keep_s002={has_keeper} stale_gone={no_stale} → "
          f"{'OK' if ok else 'FAIL'}")
    if not ok:
        for r in rows:
            print(f"  row: {r}")
        for i in issues:
            print(f"  issue: {i}")
    return ok


def _scenario_world_b(root: Path) -> bool:
    """stage_events 1 entry replaces stale E-S001, keeps E-S002."""
    snapshot_path = root / "world_stage_snapshot_S001.json"
    snapshot_path.write_text(json.dumps({
        "stage_id": "S001",
        "timeline_anchor": "新时间",
        "location_anchor": "新地点",
        "stage_events": ["新事件描述" + "x" * 50],
    }, ensure_ascii=False), encoding="utf-8")

    digest_path = root / "world_event_digest.jsonl"
    digest_path.write_text(
        json.dumps({
            "event_id": "E-S001-01", "summary": "stale S001 event",
            "importance": "minor", "time": "x", "location": "y",
        }, ensure_ascii=False) + "\n"
        + json.dumps({
            "event_id": "E-S002-01", "summary": "keep S002 event",
            "importance": "minor", "time": "x", "location": "y",
        }, ensure_ascii=False) + "\n",
        encoding="utf-8")

    issues = generate_world_event_digest(
        snapshot_path=snapshot_path,
        digest_path=digest_path,
        stage_id="S001",
        schema_dir=None,
    )
    rows = _read_jsonl(digest_path)
    new_s001 = next(
        (r for r in rows if r.get("event_id") == "E-S001-01"), None)
    keeper = next(
        (r for r in rows if r.get("event_id") == "E-S002-01"), None)
    replaced = (
        new_s001 is not None and new_s001.get("summary") != "stale S001 event")
    ok = (
        replaced
        and keeper is not None
        and not any("No stage_events" in i for i in issues))
    print(f"[world-B] non-empty stage_events replaces S001, keeps S002: "
          f"rows={len(rows)} replaced={replaced} keep={keeper is not None} "
          f"→ {'OK' if ok else 'FAIL'}")
    if not ok:
        for r in rows:
            print(f"  row: {r}")
        for i in issues:
            print(f"  issue: {i}")
    return ok


def main() -> int:
    results: list[bool] = []
    for fn, name in [
        (_scenario_memory_a, "memory_a"),
        (_scenario_memory_b, "memory_b"),
        (_scenario_world_a, "world_a"),
        (_scenario_world_b, "world_b"),
    ]:
        with tempfile.TemporaryDirectory(prefix=f"smoke_pp_slice_{name}_") as td:
            results.append(fn(Path(td)))

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\nSummary: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
