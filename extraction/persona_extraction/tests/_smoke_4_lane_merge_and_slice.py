"""Smoke test for decision #55's 4-sub-lane char_snapshot topology +
prev snapshot slice helper. Run with ``python -m
extraction.persona_extraction.tests._smoke_4_lane_merge_and_slice``.

Covers:
  1. SUB_LANE_NAMES tuple is the 4 expected names.
  2. FIELD_ALLOCATION non-shared fields are mutually exclusive across
     lanes (no field allocated to two non-shared lanes).
  3. SHARED_KEY_SUBKEYS has the right contributing-lane shape
     (failure_modes across 3 / stage_delta across 2 / behavior_state
     across 2) and subkey unions cover the full schema set.
  4. 4 minimal-but-valid partials → merge_partials → returns a dict
     containing every allocated top-level field + program-injected
     metadata + passes the D4 set-equal pre-flight.
  5. slice_snapshot_for_lane round-trip: merged → 4 slices → each
     slice's keys match the lane's allocation (modulo shared-key
     subkey filtering); re-running merge_partials on the slices
     reproduces the merged dict (modulo program-injected fields).
  6. FIELD_ALLOCATION ∪ PROGRAM_INJECTED_FIELDS covers exactly the
     stage_snapshot schema's top-level properties — the lockstep
     conventions.md §Cross-File Alignment promises but nothing enforced.

Exits non-zero on first failed assertion. Plain stdlib only.
"""

from __future__ import annotations

import sys
from typing import Any

import json
from pathlib import Path

from ..phases.snapshot_merge import (
    FIELD_ALLOCATION,
    LANE_CHAR_DECISION,
    LANE_CHAR_EXPRESSION,
    LANE_CHAR_INTERNAL,
    LANE_CHAR_SOCIAL,
    PROGRAM_INJECTED_FIELDS,
    SHARED_KEY_SUBKEYS,
    SUB_LANE_NAMES,
    merge_partials,
    slice_snapshot_for_lane,
)


# Minimal fixtures — just enough shape to pass the merge gates without
# trying to satisfy the full stage_snapshot.schema.json (which has
# much richer required fields). We're testing merge logic + slice
# logic, not schema conformance.
_TARGETS = ("char_A", "char_B")
_BASELINE_KEYS = set(_TARGETS)


def _fixture_target_voice_map() -> list[dict[str, Any]]:
    # Schema: array of objects keyed by target_character_id.
    return [{"target_character_id": t, "tone": "neutral"} for t in _TARGETS]


def _fixture_target_behavior_map() -> list[dict[str, Any]]:
    # Schema: array of objects keyed by target_character_id.
    return [{"target_character_id": t, "default": "polite"} for t in _TARGETS]


def _fixture_relationships() -> list[dict[str, Any]]:
    return [{"target_character_id": t, "type": "friend"} for t in _TARGETS]


def _fixture_partials() -> dict[str, dict[str, Any]]:
    """Build 4 minimal-but-valid partials for the 4 sub-lanes."""
    return {
        LANE_CHAR_EXPRESSION: {
            "voice_state": {
                "tone_summary": "calm",
                "target_voice_map": _fixture_target_voice_map(),
            },
            "active_aliases": ["A"],
            "current_mood": "calm",
            "failure_modes": {
                "tone_traps": [{"id": "TT1", "description": "x"}],
            },
        },
        LANE_CHAR_DECISION: {
            "behavior_state": {
                "core_goals": ["g1"],
                "obsessions": [],
                "decision_making_style": "deliberate",
                "emotional_triggers": [],
                "emotional_reaction_map": {},
                "habitual_behaviors": [],
                "stress_response": "withdraw",
            },
            "boundary_state": {"limits": []},
            "emotional_baseline": {"baseline": "calm"},
            "current_personality": "stoic",
            "current_status": "active",
            "stage_delta": {
                "status_changes": [],
                "mood_shift": "",
                "personality_changes": [],
            },
        },
        LANE_CHAR_INTERNAL: {
            "knowledge_scope": {"knows": [], "does_not_know": []},
            "misunderstandings": [],
            "concealments": [],
            "snapshot_summary": "summary text",
            "failure_modes": {
                "knowledge_leaks": [],
                "common_failures": [],
            },
        },
        LANE_CHAR_SOCIAL: {
            "relationships": _fixture_relationships(),
            "relationship_state_summary": "summary",
            "stage_events": [{"id": "e1", "desc": "x"}],
            "character_arc": "arc text",
            "behavior_state": {
                "target_behavior_map": _fixture_target_behavior_map(),
            },
            "failure_modes": {
                "relationship_traps": [],
            },
            "stage_delta": {
                "trigger_events": [],
                "relationship_changes": [],
                "voice_shift": "",
            },
        },
    }


def _check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  [PASS] {label}")
    else:
        print(f"  [FAIL] {label}: {detail}")
        sys.exit(1)


def smoke_1_sub_lane_names() -> None:
    expected = (
        "char_expression", "char_decision", "char_internal", "char_social")
    _check(
        "1) SUB_LANE_NAMES == 4-tuple of new lane names",
        SUB_LANE_NAMES == expected,
        f"got {SUB_LANE_NAMES}")


def smoke_2_field_allocation_disjoint() -> None:
    # For each non-shared top-level field, it must appear in exactly
    # one lane's FIELD_ALLOCATION.
    non_shared_counts: dict[str, list[str]] = {}
    for lane, fields in FIELD_ALLOCATION.items():
        for f in fields:
            if f in SHARED_KEY_SUBKEYS:
                continue
            non_shared_counts.setdefault(f, []).append(lane)
    duplicates = {
        f: lanes for f, lanes in non_shared_counts.items() if len(lanes) > 1}
    _check(
        "2) FIELD_ALLOCATION non-shared fields are disjoint across lanes",
        not duplicates,
        f"duplicates: {duplicates}")


def smoke_3_shared_key_shape() -> None:
    fm = SHARED_KEY_SUBKEYS["failure_modes"]
    sd = SHARED_KEY_SUBKEYS["stage_delta"]
    bs = SHARED_KEY_SUBKEYS["behavior_state"]
    _check(
        "3a) failure_modes shared across 3 lanes (expression / internal / social)",
        set(fm.keys()) == {
            LANE_CHAR_EXPRESSION, LANE_CHAR_INTERNAL, LANE_CHAR_SOCIAL},
        f"got {sorted(fm.keys())}")
    fm_union = set().union(*(set(s) for s in fm.values()))
    _check(
        "3b) failure_modes union = {tone_traps, knowledge_leaks, common_failures, relationship_traps}",
        fm_union == {
            "tone_traps", "knowledge_leaks", "common_failures",
            "relationship_traps"},
        f"got {sorted(fm_union)}")
    _check(
        "3c) stage_delta shared across 2 lanes (decision / social)",
        set(sd.keys()) == {LANE_CHAR_DECISION, LANE_CHAR_SOCIAL},
        f"got {sorted(sd.keys())}")
    sd_union = set().union(*(set(s) for s in sd.values()))
    _check(
        "3d) stage_delta union covers all 6 subkeys",
        sd_union == {
            "status_changes", "mood_shift", "personality_changes",
            "trigger_events", "relationship_changes", "voice_shift"},
        f"got {sorted(sd_union)}")
    _check(
        "3e) behavior_state shared across 2 lanes (decision / social)",
        set(bs.keys()) == {LANE_CHAR_DECISION, LANE_CHAR_SOCIAL},
        f"got {sorted(bs.keys())}")
    _check(
        "3f) behavior_state.social ONLY has target_behavior_map",
        bs[LANE_CHAR_SOCIAL] == ("target_behavior_map",),
        f"got {bs[LANE_CHAR_SOCIAL]}")
    _check(
        "3g) behavior_state.decision has the 7 self-behavior subkeys",
        set(bs[LANE_CHAR_DECISION]) == {
            "core_goals", "obsessions", "decision_making_style",
            "emotional_triggers", "emotional_reaction_map",
            "habitual_behaviors", "stress_response"},
        f"got {sorted(bs[LANE_CHAR_DECISION])}")


def smoke_4_merge_happy_path() -> dict[str, Any]:
    partials = _fixture_partials()
    merged = merge_partials(
        partials,
        schema_version="2",
        work_id="test_work",
        character_id="char_main",
        stage_id="S001",
        stage_title="Test Stage",
        chapter_scope={"from": "C0001", "to": "C0010"},
        baseline_keys=_BASELINE_KEYS,
    )
    # Verify every allocated top-level field is present (excluding shared
    # keys treated separately and program-injected metadata).
    expected_top = set()
    for lane, fields in FIELD_ALLOCATION.items():
        for f in fields:
            expected_top.add(f)
    missing = expected_top - set(merged.keys())
    _check(
        "4a) merged dict contains every allocated top-level field",
        not missing, f"missing: {sorted(missing)}")
    _check(
        "4b) merged.behavior_state has all 8 subkeys",
        set(merged["behavior_state"].keys()) == {
            "core_goals", "obsessions", "decision_making_style",
            "emotional_triggers", "emotional_reaction_map",
            "habitual_behaviors", "stress_response",
            "target_behavior_map"},
        f"got {sorted(merged['behavior_state'].keys())}")
    _check(
        "4c) merged.failure_modes has all 4 subkeys",
        set(merged["failure_modes"].keys()) == {
            "tone_traps", "knowledge_leaks", "common_failures",
            "relationship_traps"},
        f"got {sorted(merged['failure_modes'].keys())}")
    _check(
        "4d) merged.stage_delta has all 6 subkeys",
        set(merged["stage_delta"].keys()) == {
            "status_changes", "mood_shift", "personality_changes",
            "trigger_events", "relationship_changes", "voice_shift"},
        f"got {sorted(merged['stage_delta'].keys())}")
    _check(
        "4e) program-injected metadata present in merged",
        all(k in merged for k in (
            "schema_version", "work_id", "character_id", "stage_id",
            "stage_title", "timeline_anchor", "chapter_scope")),
        "missing one or more injected fields")
    return merged


def smoke_5_slice_round_trip(merged: dict[str, Any]) -> None:
    # Slice the merged dict back into 4 per-lane slices.
    slices = {
        lane: slice_snapshot_for_lane(merged, lane)
        for lane in SUB_LANE_NAMES
    }

    # Each slice should NOT carry program-injected fields.
    program_fields = {
        "schema_version", "work_id", "character_id", "stage_id",
        "stage_title", "timeline_anchor", "chapter_scope"}
    for lane, sl in slices.items():
        leaked = set(sl.keys()) & program_fields
        _check(
            f"5a) slice[{lane}] carries no program-injected fields",
            not leaked, f"leaked: {sorted(leaked)}")

    # Each slice's non-shared keys should be a subset of the lane's
    # allocation (no leakage from other lanes' fields).
    for lane, sl in slices.items():
        allowed = set(FIELD_ALLOCATION[lane])
        extra = set(sl.keys()) - allowed
        _check(
            f"5b) slice[{lane}] keys ⊆ FIELD_ALLOCATION",
            not extra, f"extra: {sorted(extra)}")

    # Behavior_state slice content: decision slice has only the 7 self
    # behaviour subkeys; social slice has only target_behavior_map.
    dec_bs = slices[LANE_CHAR_DECISION].get("behavior_state", {})
    soc_bs = slices[LANE_CHAR_SOCIAL].get("behavior_state", {})
    _check(
        "5c) slice[decision].behavior_state has the 7 self-behaviour subkeys",
        set(dec_bs.keys()) == set(
            SHARED_KEY_SUBKEYS["behavior_state"][LANE_CHAR_DECISION]),
        f"got {sorted(dec_bs.keys())}")
    _check(
        "5d) slice[social].behavior_state has ONLY target_behavior_map",
        set(soc_bs.keys()) == {"target_behavior_map"},
        f"got {sorted(soc_bs.keys())}")

    # Round-trip: feed the 4 slices back to merge_partials. The shape
    # of the merged dict (minus program-injected fields) should equal
    # the originally merged dict's non-program-injected shape.
    re_merged = merge_partials(
        slices,
        schema_version="2",
        work_id="test_work",
        character_id="char_main",
        stage_id="S001",
        stage_title="Test Stage",
        chapter_scope={"from": "C0001", "to": "C0010"},
        baseline_keys=_BASELINE_KEYS,
    )
    orig_content = {k: v for k, v in merged.items() if k not in program_fields}
    re_content = {k: v for k, v in re_merged.items() if k not in program_fields}
    _check(
        "5e) slice → merge_partials round-trip preserves non-injected content",
        orig_content == re_content,
        f"diff keys: orig - re = {set(orig_content) - set(re_content)}, "
        f"re - orig = {set(re_content) - set(orig_content)}")


def smoke_6_allocation_covers_schema() -> None:
    # The merge gates only compare a partial against FIELD_ALLOCATION —
    # nothing ever compares FIELD_ALLOCATION against the schema itself.
    # conventions.md §Cross-File Alignment promises that a new top-level
    # stage_snapshot property must be attached to some sub-lane "or the merge
    # hard gate errors"; without this check that promise rests on memory, and
    # a new *optional* property would simply never be produced by any lane.
    schema_path = (Path(__file__).resolve().parents[3] / "schemas"
                   / "character" / "stage_snapshot.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema_top = set(schema.get("properties", {}).keys())

    allocated: set[str] = set()
    for fields in FIELD_ALLOCATION.values():
        allocated.update(fields)
    covered = allocated | set(PROGRAM_INJECTED_FIELDS)

    unallocated = schema_top - covered   # in schema, no lane produces it
    phantom = covered - schema_top       # allocated but not in the schema
    _check(
        "6) FIELD_ALLOCATION ∪ PROGRAM_INJECTED_FIELDS == schema top-level",
        not unallocated and not phantom,
        f"unallocated (no lane writes these): {sorted(unallocated)}; "
        f"phantom (not in schema): {sorted(phantom)}")


def main() -> None:
    print("Smoke: decision #55 4-sub-lane topology + slice round-trip")
    smoke_1_sub_lane_names()
    smoke_2_field_allocation_disjoint()
    smoke_3_shared_key_shape()
    merged = smoke_4_merge_happy_path()
    smoke_5_slice_round_trip(merged)
    smoke_6_allocation_covers_schema()
    print("\nAll smoke checks passed.")


if __name__ == "__main__":
    main()
