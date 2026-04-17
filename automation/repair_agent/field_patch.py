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
