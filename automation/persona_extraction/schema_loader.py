"""Schema loader with cross-file ``$ref`` inlining.

Schemas under ``schemas/`` may use cross-file ``$ref`` to share common
fragments. The fragment lives in the directory of the domain that uses
it (e.g. ``schemas/character/targets_cap.schema.json`` carries the
single-source ``maxItems`` for target arrays referenced by
``target_baseline.targets`` and stage_snapshot's three target
structures, all of which live in ``schemas/character/``).

Both the orchestrator's repair_agent file-entry loader and validator's
``_validate_schema`` need ``$ref``-resolved schema dicts. ``referencing``
is available with jsonschema >= 4.18 but the older Draft7Validator path
in ``repair_agent/checkers/schema.py`` does not consume it. To keep both
paths working without forking the validator, we inline relative
``$ref`` fragments at load time, producing a self-contained schema dict
that any draft-version validator can consume directly.

Relative refs of the form ``./<file>.schema.json``,
``<file>.schema.json`` (sibling), or ``../<dir>/<file>.schema.json``
anchored under the ``schemas/`` directory are inlined. Absolute /
network refs are left untouched.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


def load_schema(schema_path: Path) -> dict:
    """Load a JSON Schema from disk with relative ``$ref`` fragments inlined."""
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    return _inline_refs(schema, Path(schema_path).parent)


@lru_cache(maxsize=64)
def _load_fragment(path: str) -> dict:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def _inline_refs(node, base_dir: Path):
    """Recursively replace ``{"$ref": "<relative>.schema.json"}`` nodes
    with the loaded content. Non-relative refs and non-dict nodes are
    returned as-is.
    """
    if isinstance(node, list):
        return [_inline_refs(item, base_dir) for item in node]
    if not isinstance(node, dict):
        return node

    ref = node.get("$ref")
    if isinstance(ref, str) and not ref.startswith(("#", "http://", "https://")):
        target = (base_dir / ref).resolve()
        if target.is_file():
            fragment = _load_fragment(str(target))
            inlined = _inline_refs(fragment, target.parent)
            siblings = {k: v for k, v in node.items() if k != "$ref"}
            if not siblings:
                return inlined
            merged = dict(inlined)
            for k, v in siblings.items():
                merged[k] = _inline_refs(v, base_dir)
            return merged

    return {k: _inline_refs(v, base_dir) for k, v in node.items()}
