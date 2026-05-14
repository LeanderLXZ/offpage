"""Target-character importance lookup primitives.

Imported by both the Phase 2 baseline gate (when building the
importance map from ``candidate_characters.json``) and the repair
framework's L2 structural checker (to raise the minimum example count
for main / important characters). Pure functions — no I/O beyond what
the caller passes in.
"""

from __future__ import annotations


_IMPORTANCE_RANK = {"主角": 3, "重要配角": 2}


def importance_for_target(
    target: str, importance_map: dict[str, str],
) -> str:
    """Resolve a target identifier to its canonical importance.

    With the post-D4 character_id keying, ``target`` is normally a
    ``target_character_id`` and matches an entry in ``importance_map``
    directly. The substring match remains a defensive fallback for
    legacy / annotated labels (``<character_a>（<phase_alias>）`` or the
    occasional ``target_type`` sibling string) so the importance lookup
    still works while data is being migrated. Among matches, picks the
    most important importance; ties broken by longer ``character_id`` so
    that a specific id wins over one that happens to be a substring of
    another (e.g. ``张三丰`` over ``张三`` when both would match).
    """
    if not isinstance(target, str) or not target or not importance_map:
        return "其他"
    best: tuple[int, int, str] | None = None  # (rank, id_len, importance)
    for char_id, importance in importance_map.items():
        if not char_id or char_id not in target:
            continue
        rank = _IMPORTANCE_RANK.get(importance, 1)
        score = (rank, len(char_id))
        if best is None or score > (best[0], best[1]):
            best = (rank, len(char_id), importance or "其他")
    if best is None:
        return "其他"
    return best[2]


def importance_min_examples(importance: str) -> int:
    """Minimum example count required for a given importance.

    主角 → 5, 重要配角 → 3, others → 1.  Shared by the L2 structural
    checker and the Phase 3.5 consistency checker so both enforce the
    same threshold.
    """
    if "主角" in importance:
        return 5
    if "重要" in importance:
        return 3
    return 1
