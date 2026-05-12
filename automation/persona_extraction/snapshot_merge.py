"""Sub-lane partial merge for ``char_snapshot`` (decision #55).

The single ``char_snapshot`` lane fans out into three parallel sub-lanes
(``char_expression`` / ``char_decision`` / ``char_cognition``) that share
one prompt template and write disjoint slices of the final
``stage_snapshot.json``. ``merge_partials`` welds the three slices into
one schema-valid object, runs the merge-time hard gates, and returns the
final dict ready to be written to disk.

The field allocation (``FIELD_ALLOCATION`` below) is the **single source
of truth** consumed by both the prompt builder (`{lane_field_whitelist}`
placeholder) and the merge function. Adjusting the allocation here
automatically updates the prompt's per-lane whitelist; never duplicate
the table in another file.

Merge-time hard gates (all enforced before returning the merged dict):

1. Each partial's top-level field set must equal the lane's allocation
   (no extra, no missing).
2. ``failure_modes`` 4 subkeys must be mutually exclusive across the two
   lanes that write them (``tone_traps`` only from ``char_expression`` /
   the other three only from ``char_cognition``) and all 4 must be
   present after merge.
3. ``stage_delta`` 6 subkeys must be mutually exclusive across the two
   lanes that write them (``char_decision`` / ``char_cognition``).
   Either all 6 subkeys are present after merge OR ``stage_delta`` is
   absent from both partials (the S001 case — no prev, no delta).
4. The three target-keyed structures (``voice_state.target_voice_map``
   / ``behavior_state.target_behavior_map`` / top-level ``relationships``)
   must all carry keys whose set equals ``baseline_keys`` (the caller
   provides the baseline target set; on disk the
   ``TargetsKeysEqBaselineChecker`` enforces the same rule against
   ``target_baseline.json``).
5. Decision #11f (D) drop semantics: merge **does not** check partial
   entry count ≥ prev. Resolved / revealed / overcome entries are
   legitimately dropped; the responsibility for recording the reason
   lives in ``stage_delta`` (and phase 3.5 ``consistency_checker``).

Failures raise ``MergeError``. The orchestrator treats any
``MergeError`` as a partial-level failure: the whole snapshot lane is
re-run (with PENDING / ERROR ``.partial/`` files wiped by
``progress.reconcile_with_disk``).

File-level fingerprint (``compute_fingerprint``) is a stable SHA-256 of
the canonical-JSON-serialised merged dict; the repair_agent lifecycle
layer reads it to skip already-accepted regenerations.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


# ---------------------------------------------------------------------------
# Field allocation (single source of truth — see decision #55)
# ---------------------------------------------------------------------------

LANE_CHAR_EXPRESSION = "char_expression"
LANE_CHAR_DECISION = "char_decision"
LANE_CHAR_COGNITION = "char_cognition"

SUB_LANE_NAMES: tuple[str, ...] = (
    LANE_CHAR_EXPRESSION,
    LANE_CHAR_DECISION,
    LANE_CHAR_COGNITION,
)

# Top-level fields each sub-lane is responsible for. Order matters: keys
# are iterated when building the per-lane whitelist for the prompt, so
# keep them grouped semantically.
FIELD_ALLOCATION: dict[str, tuple[str, ...]] = {
    LANE_CHAR_EXPRESSION: (
        "voice_state",
        "active_aliases",
        "current_mood",
        "failure_modes",  # only the tone_traps subkey, see SHARED_KEY_SUBKEYS
    ),
    LANE_CHAR_DECISION: (
        "behavior_state",
        "boundary_state",
        "emotional_baseline",
        "current_personality",
        "current_status",
        "stage_delta",  # only the 3 decision-side subkeys
    ),
    LANE_CHAR_COGNITION: (
        "knowledge_scope",
        "misunderstandings",
        "concealments",
        "relationships",
        "relationship_state_summary",
        "stage_events",
        "character_arc",
        "snapshot_summary",
        "stage_delta",  # the other 3 subkeys
        "failure_modes",  # the other 3 subkeys
    ),
}

# Subkey allocation for the two compound top-level keys that two lanes
# share. ``failure_modes`` and ``stage_delta`` are each split.
SHARED_KEY_SUBKEYS: dict[str, dict[str, tuple[str, ...]]] = {
    "failure_modes": {
        LANE_CHAR_EXPRESSION: ("tone_traps",),
        LANE_CHAR_COGNITION: (
            "common_failures",
            "relationship_traps",
            "knowledge_leaks",
        ),
    },
    "stage_delta": {
        LANE_CHAR_DECISION: (
            "status_changes",
            "mood_shift",
            "personality_changes",
        ),
        LANE_CHAR_COGNITION: (
            "trigger_events",
            "relationship_changes",
            "voice_shift",
        ),
    },
}

# Top-level fields that are non-required at the schema level — partials
# are allowed to omit them entirely (e.g. ``emotional_baseline`` /
# ``current_status`` / ``misunderstandings`` / ``concealments`` /
# ``relationship_state_summary`` / ``stage_delta`` / ``chapter_scope``).
# Sub-lane partials may drop these without tripping the "field set
# equals allocation" gate.
OPTIONAL_TOP_LEVEL_FIELDS: frozenset[str] = frozenset({
    "emotional_baseline",
    "current_status",
    "misunderstandings",
    "concealments",
    "relationship_state_summary",
    "stage_delta",
})

# Fields the orchestrator injects post-merge (mechanical metadata; not
# produced by any sub-lane). ``timeline_anchor`` is derived from
# ``stage_title`` (truncated to schema cap) — semantic but mechanically
# fillable, see decision #55.
PROGRAM_INJECTED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "work_id",
    "character_id",
    "stage_id",
    "stage_title",
    "timeline_anchor",
    "chapter_scope",
)


class MergeError(ValueError):
    """Raised when a sub-lane partial set fails any merge-time gate."""


# ---------------------------------------------------------------------------
# Per-lane partial validation
# ---------------------------------------------------------------------------

def lane_field_whitelist(lane: str) -> list[str]:
    """Return the human-readable whitelist of top-level fields a sub-lane
    must write. Used by the prompt builder to fill
    ``{lane_field_whitelist}``."""
    if lane not in FIELD_ALLOCATION:
        raise ValueError(f"unknown sub-lane: {lane!r}")
    return list(FIELD_ALLOCATION[lane])


def lane_shared_subkeys(lane: str) -> dict[str, tuple[str, ...]]:
    """Subkey allocation for compound top-level fields, scoped to one
    sub-lane. Empty dict if the sub-lane owns no compound key."""
    out: dict[str, tuple[str, ...]] = {}
    for top_key, by_lane in SHARED_KEY_SUBKEYS.items():
        if lane in by_lane:
            out[top_key] = by_lane[lane]
    return out


def _expected_top_keys(lane: str) -> set[str]:
    return set(FIELD_ALLOCATION[lane])


def _validate_partial_fields(lane: str, partial: dict[str, Any]) -> None:
    """Verify a single sub-lane partial's top-level field set equals the
    lane's allocation (modulo optional fields the lane is allowed to
    omit) and that compound keys carry only the lane's allowed subkeys.
    """
    expected = _expected_top_keys(lane)
    actual = set(partial.keys())

    extra = actual - expected
    if extra:
        raise MergeError(
            f"sub-lane {lane!r} partial wrote disallowed top-level fields "
            f"{sorted(extra)} (allocation: {sorted(expected)})")

    missing = expected - actual
    # Optional fields can legitimately be absent. For compound shared
    # keys (failure_modes / stage_delta) the empty-state contract is
    # checked at merge time, not here.
    must_have_missing = {
        k for k in missing
        if k not in OPTIONAL_TOP_LEVEL_FIELDS
        and k not in SHARED_KEY_SUBKEYS
    }
    if must_have_missing:
        raise MergeError(
            f"sub-lane {lane!r} partial missing required top-level fields "
            f"{sorted(must_have_missing)} (allocation: {sorted(expected)})")

    # Compound key subkey validation: if present, must carry only the
    # lane's allocated subkeys.
    for top_key, by_lane in SHARED_KEY_SUBKEYS.items():
        if top_key not in partial:
            continue
        if lane not in by_lane:
            raise MergeError(
                f"sub-lane {lane!r} wrote {top_key!r} but is not allocated "
                f"to it (allocated lanes: {sorted(by_lane.keys())})")
        section = partial[top_key]
        if not isinstance(section, dict):
            raise MergeError(
                f"sub-lane {lane!r} {top_key!r} must be an object, got "
                f"{type(section).__name__}")
        allowed = set(by_lane[lane])
        sub_actual = set(section.keys())
        sub_extra = sub_actual - allowed
        if sub_extra:
            raise MergeError(
                f"sub-lane {lane!r} wrote disallowed {top_key} subkeys "
                f"{sorted(sub_extra)} (allowed for this lane: "
                f"{sorted(allowed)})")


# ---------------------------------------------------------------------------
# Cross-lane mutual-exclusion / coverage gates
# ---------------------------------------------------------------------------

def _check_shared_key_coverage(
    top_key: str,
    partials: dict[str, dict[str, Any]],
    *,
    allow_absent_both: bool,
) -> dict[str, Any] | None:
    """Verify mutual exclusion + coverage for a compound shared key.

    Returns the merged sub-object if any lane wrote it, ``None`` if all
    contributing lanes omitted it (and ``allow_absent_both`` permits).
    """
    by_lane = SHARED_KEY_SUBKEYS[top_key]
    contributing = sorted(by_lane.keys())

    present = {lane: partials[lane].get(top_key) for lane in contributing}
    written = {lane: section for lane, section in present.items()
               if section is not None}

    if not written:
        if allow_absent_both:
            return None
        raise MergeError(
            f"{top_key!r} required after merge but all contributing "
            f"sub-lanes ({contributing}) omitted it")

    if len(written) != len(contributing):
        missing = [lane for lane in contributing if lane not in written]
        raise MergeError(
            f"{top_key!r} written by some but not all contributing sub-"
            f"lanes (wrote: {sorted(written.keys())}; missing: {missing}); "
            f"either every contributing lane writes it or none do")

    merged: dict[str, Any] = {}
    seen_subkeys: dict[str, str] = {}  # subkey → which lane wrote it
    for lane in contributing:
        section = written[lane]
        for subkey, value in section.items():
            if subkey in seen_subkeys:
                raise MergeError(
                    f"{top_key}.{subkey} written by both "
                    f"{seen_subkeys[subkey]!r} and {lane!r}; subkeys "
                    f"must be mutually exclusive across sub-lanes")
            seen_subkeys[subkey] = lane
            merged[subkey] = value

    all_required = set()
    for lane in contributing:
        all_required.update(by_lane[lane])
    missing_subkeys = all_required - merged.keys()
    if missing_subkeys:
        raise MergeError(
            f"{top_key!r} merge missing subkeys {sorted(missing_subkeys)} "
            f"(must cover {sorted(all_required)} across all contributing "
            f"sub-lanes)")
    return merged


def _collect_target_keys(entries: Any) -> set[str]:
    """Pull ``target_character_id`` from every dict entry of an array.

    Mirrors ``checkers/targets_keys_eq_baseline.py::_collect_keys`` so
    the merge pre-flight uses the same key-extraction semantics.
    """
    if not isinstance(entries, list):
        return set()
    keys: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        cid = entry.get("target_character_id")
        if isinstance(cid, str) and cid:
            keys.add(cid)
    return keys


def _validate_targets_set_equal(
    merged: dict[str, Any],
    baseline_keys: set[str],
) -> None:
    """Pre-flight the D4 set-equal constraint before writing the merged
    file. Reuses the same rule as
    ``automation/repair_agent/checkers/targets_keys_eq_baseline.py``
    (decision #13) — fail at merge time so the on-disk checker never
    sees a drifted file.
    """
    structures = (
        ("voice_state.target_voice_map",
         (merged.get("voice_state") or {}).get("target_voice_map")),
        ("behavior_state.target_behavior_map",
         (merged.get("behavior_state") or {}).get("target_behavior_map")),
        ("relationships", merged.get("relationships")),
    )
    snap_key_sets: dict[str, set[str]] = {}
    for path, entries in structures:
        if entries is None:
            raise MergeError(
                f"merge missing {path}; cannot satisfy D4 keys==baseline")
        snap_key_sets[path] = _collect_target_keys(entries)

    # All three structures must agree with each other.
    path_pairs = list(snap_key_sets.items())
    base_path, base_keys = path_pairs[0]
    for other_path, other_keys in path_pairs[1:]:
        if other_keys != base_keys:
            diff = sorted(base_keys ^ other_keys)
            raise MergeError(
                f"target keys disagree across structures: {base_path} vs "
                f"{other_path} (diff: {diff})")

    # And the shared set must equal baseline_keys.
    if base_keys != baseline_keys:
        missing = sorted(baseline_keys - base_keys)
        extra = sorted(base_keys - baseline_keys)
        raise MergeError(
            f"target keys do not match target_baseline.targets[].target_"
            f"character_id (missing: {missing}; extra: {extra})")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def merge_partials(
    partials: dict[str, dict[str, Any]],
    *,
    schema_version: str,
    work_id: str,
    character_id: str,
    stage_id: str,
    stage_title: str,
    chapter_scope: dict[str, str] | None,
    baseline_keys: set[str],
    timeline_anchor_max_length: int = 50,
) -> dict[str, Any]:
    """Merge three sub-lane partials into a single ``stage_snapshot`` dict.

    Args:
        partials: Mapping of sub-lane name → partial dict. Must contain
            all three sub-lanes in ``SUB_LANE_NAMES``.
        schema_version / work_id / character_id / stage_id / stage_title:
            Program-injected structural metadata; never produced by any
            sub-lane.
        chapter_scope: Optional ``{"from": "C####", "to": "C####"}``
            object; pass ``None`` to omit (matches schema where
            ``chapter_scope`` is non-required).
        baseline_keys: ``set(target_baseline.targets[].target_character_id)``
            of the owning character. Used for the D4 set-equal check.
        timeline_anchor_max_length: Schema cap for the injected
            ``timeline_anchor`` (default 50, mirrors
            ``stage_snapshot.schema.json``). Pass dynamically only if the
            schema cap changes.

    Returns the merged dict, ready to ``json.dump``.

    Raises ``MergeError`` on any gate failure. Callers should treat any
    raise as a partial-level failure (whole snapshot lane re-runs).
    """
    missing_lanes = set(SUB_LANE_NAMES) - set(partials.keys())
    if missing_lanes:
        raise MergeError(
            f"merge missing partials for sub-lanes {sorted(missing_lanes)} "
            f"(provided: {sorted(partials.keys())})")
    extra_lanes = set(partials.keys()) - set(SUB_LANE_NAMES)
    if extra_lanes:
        raise MergeError(
            f"merge received unknown sub-lanes {sorted(extra_lanes)}")

    for lane in SUB_LANE_NAMES:
        _validate_partial_fields(lane, partials[lane])

    merged: dict[str, Any] = {}

    # Non-shared top-level fields — each owned by exactly one lane.
    seen: dict[str, str] = {}
    for lane in SUB_LANE_NAMES:
        for key in FIELD_ALLOCATION[lane]:
            if key in SHARED_KEY_SUBKEYS:
                continue
            if key not in partials[lane]:
                continue
            if key in seen:
                raise MergeError(
                    f"top-level field {key!r} written by both "
                    f"{seen[key]!r} and {lane!r} (allocation table "
                    f"violation)")
            seen[key] = lane
            merged[key] = partials[lane][key]

    # Shared compound keys.
    failure_modes = _check_shared_key_coverage(
        "failure_modes", partials, allow_absent_both=False)
    if failure_modes is not None:
        merged["failure_modes"] = failure_modes

    stage_delta = _check_shared_key_coverage(
        "stage_delta", partials, allow_absent_both=True)
    if stage_delta is not None:
        merged["stage_delta"] = stage_delta

    # Program-injected metadata.
    merged["schema_version"] = schema_version
    merged["work_id"] = work_id
    merged["character_id"] = character_id
    merged["stage_id"] = stage_id
    merged["stage_title"] = stage_title
    anchor = stage_title or stage_id
    if len(anchor) > timeline_anchor_max_length:
        anchor = anchor[:timeline_anchor_max_length]
    merged["timeline_anchor"] = anchor
    if chapter_scope is not None:
        merged["chapter_scope"] = chapter_scope

    # Cross-structure D4 set-equal pre-flight.
    _validate_targets_set_equal(merged, baseline_keys)

    return merged


def compute_fingerprint(merged: dict[str, Any]) -> str:
    """SHA-256 of canonical JSON; stable across runs.

    Used as the file-level fingerprint for repair_agent lifecycle 2
    accept-list (sub-lane shared, not per-lane — decision #55).
    """
    blob = json.dumps(
        merged, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def derive_chapter_scope(chapters: str) -> dict[str, str] | None:
    """Parse a ``stage_plan.chapters`` range (``C####-C####``) into the
    schema's ``chapter_scope`` shape. Returns ``None`` if the input is
    empty / malformed (caller can then skip injection)."""
    if not chapters or "-" not in chapters:
        return None
    head, _, tail = chapters.partition("-")
    head = head.strip()
    tail = tail.strip()
    if not head or not tail:
        return None
    return {"from": head, "to": tail}
