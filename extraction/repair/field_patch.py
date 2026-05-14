"""Field-level JSON patching — surgical updates by json_path.

Only the targeted value is replaced; all other fields and key ordering
are preserved.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any


def apply_field_patch(original: dict | list, json_path: str,
                      new_value: Any) -> dict | list:
    """Replace the value at *json_path* in *original*, returning a new copy.

    Supports paths like ``$.foo.bar[0].baz`` and ``$.relationships[角色B]``.
    Raises KeyError / IndexError if the path does not exist.
    """
    obj = copy.deepcopy(original)
    tokens = _parse_path(json_path)
    if not tokens:
        return new_value  # root replacement

    parent = obj
    for tok in tokens[:-1]:
        parent = _navigate(parent, tok)
    _set_value(parent, tokens[-1], new_value)
    return obj


def extract_subtree(data: dict | list, json_path: str) -> Any:
    """Extract the value at *json_path* from *data*."""
    tokens = _parse_path(json_path)
    node = data
    for tok in tokens:
        node = _navigate(node, tok)
    return node


def write_patched_file(path: str, patched: dict | list) -> None:
    """Write *patched* content back to *path*, preserving JSON formatting."""
    p = Path(path)
    if p.suffix == ".jsonl" and isinstance(patched, list):
        lines = [json.dumps(entry, ensure_ascii=False) for entry in patched]
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        p.write_text(
            json.dumps(patched, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def _merge_jsonl_slice(
    full: list[dict],
    patched_slice: list[dict],
    key_field: str,
    current_stage_keys: frozenset[str] | None = None,
) -> list[dict]:
    """Merge a patched current-stage slice back into the full accumulated list.

    Two modes (decision #58 / M2):

    1. ``current_stage_keys`` provided (preferred): drop every entry in
       *full* whose ``key_field`` value is in that set, then append the
       patched slice in slice order. The slice is the authoritative
       current-stage content — so removals from the slice (e.g. repair
       deleting an invalid duplicate) actually stick, instead of being
       silently undone by the legacy replace-by-key path that always
       carried forward the corresponding full-list entry.

    2. ``current_stage_keys`` is None (legacy): fall back to replace-by-
       key + append-unseen — same behaviour as before. Used by callers
       that don't know the current-stage key set at construction time.

    Non-dict entries in *full* are passed through unchanged. Slice
    entries missing ``key_field`` are appended verbatim in both modes
    (no key to dedupe / drop by).
    """
    if current_stage_keys is not None:
        merged: list[dict] = []
        for entry in full:
            k = entry.get(key_field) if isinstance(entry, dict) else None
            if k and k in current_stage_keys:
                # Current-stage entry — slice is authoritative, drop it
                continue
            merged.append(entry)
        merged.extend(patched_slice)
        return merged

    slice_by_key = {
        e.get(key_field): e
        for e in patched_slice
        if isinstance(e, dict) and e.get(key_field)
    }
    seen: set = set()
    merged_legacy: list[dict] = []
    for entry in full:
        k = entry.get(key_field) if isinstance(entry, dict) else None
        if k and k in slice_by_key:
            merged_legacy.append(slice_by_key[k])
            seen.add(k)
        else:
            merged_legacy.append(entry)
    for k, entry in slice_by_key.items():
        if k not in seen:
            merged_legacy.append(entry)
    return merged_legacy


def write_file_entry(entry) -> None:
    """Write ``entry.content`` back to ``entry.path``, slice-aware.

    For a regular FileEntry this is equivalent to
    ``write_patched_file(entry.path, entry.content)``.

    For a JSONL slice (``entry.is_jsonl_slice``), the patched slice in
    ``entry.content`` is merged back into ``entry.jsonl_full_content``
    by ``entry.jsonl_key_field`` before writing, so prior-stage entries
    in the accumulated file are preserved. The in-memory full content
    is updated so subsequent patches within the same repair round see
    the new state.
    """
    if (
        getattr(entry, "is_jsonl_slice", False)
        and isinstance(entry.content, list)
        and entry.jsonl_full_content is not None
        and entry.jsonl_key_field
    ):
        merged = _merge_jsonl_slice(
            entry.jsonl_full_content, entry.content, entry.jsonl_key_field,
            current_stage_keys=getattr(entry, "current_stage_keys", None))
        write_patched_file(entry.path, merged)
        entry.jsonl_full_content = merged
        return
    write_patched_file(entry.path, entry.content)


# ---------------------------------------------------------------------------
# Path parsing helpers
# ---------------------------------------------------------------------------

# Matches: .key  [0]  [角色B]  ["key with dots"]
_TOKEN_RE = re.compile(
    r"""
    \.([^.\[\]]+)       # .key
    | \[(\d+)\]         # [0]
    | \[\"([^\"]+)\"\]  # ["key"]
    | \[([^\]]+)\]      # [角色B]
    """,
    re.VERBOSE,
)


def _parse_path(json_path: str) -> list[str | int]:
    """Parse ``$.foo.bar[0]`` into ``['foo', 'bar', 0]``."""
    path = json_path.lstrip("$")
    tokens: list[str | int] = []
    for m in _TOKEN_RE.finditer(path):
        dot_key, bracket_int, bracket_str, bracket_raw = m.groups()
        if dot_key is not None:
            tokens.append(dot_key)
        elif bracket_int is not None:
            tokens.append(int(bracket_int))
        elif bracket_str is not None:
            tokens.append(bracket_str)
        elif bracket_raw is not None:
            tokens.append(bracket_raw)
    return tokens


def _navigate(node: Any, token: str | int) -> Any:
    if isinstance(token, int):
        return node[token]
    if isinstance(node, dict):
        return node[token]
    raise KeyError(f"Cannot navigate {type(node)} with key {token!r}")


def _set_value(parent: Any, token: str | int, value: Any) -> None:
    if isinstance(token, int):
        parent[token] = value
    elif isinstance(parent, dict):
        parent[token] = value
    else:
        raise KeyError(f"Cannot set on {type(parent)} with key {token!r}")
