"""Length-bound tolerance gate (decision #48).

Final safety valve invoked AFTER an LLM phase has exhausted its strict
retry budget (Phase 0 L1+L2+L3 — decision #40 JSON-format repair tiers,
applies only inside ``orchestrator._summarize_chunk``; Phase 1
``exit_validation_max_retry``; Phase 2 baseline retry; Phase 4
``max_retries_per_chapter``; **Phase 3 only** ``repair`` framework 的
capped-tier 残留，即 T0–T2 修复器用尽后仍存的纯长度 miss — decision
#25 + #48 disambiguation: ``repair``'s checker/fixer matrix is the phase
3 lifecycle, not phase 0's three-tier JSON repair ladder; same字面
``L1/L2/L3`` but different semantics across #25 and #40). Relaxes ONLY
``minLength`` / ``maxLength`` by a
per-call tolerance fraction; all other constraints (``required`` /
``type`` / ``enum`` / ``pattern`` / ``minimum`` / ``maximum`` /
``minItems`` / ``maxItems``) stay strict. Acceptance is silent — no
metadata is written to the artifact.
"""

from __future__ import annotations

import copy as _copy
import math as _math

from ..types import ValidationIssue

try:
    import jsonschema
except ImportError as _jsonschema_exc:  # pragma: no cover
    raise ImportError(
        "jsonschema is a required dependency of persona-extraction. "
        "Install it with `pip install jsonschema` (or install the package "
        "with its dependencies). See docs/requirements.md §11.4."
    ) from _jsonschema_exc


def relaxed_schema_for_length(
    schema: dict,
    tolerance: float = 0.10,
) -> dict:
    """Deep-copy ``schema`` and recursively widen every ``minLength`` /
    ``maxLength`` by ``tolerance`` (default 10%):

    - ``minLength`` → ``floor(N * (1 - tolerance))`` (lower bound relaxed)
    - ``maxLength`` → ``ceil(N * (1 + tolerance))`` (upper bound relaxed)

    All other JSON Schema keywords are left untouched. The returned dict
    is independent of the input — mutating it does not affect ``schema``.
    """
    if not 0.0 <= tolerance < 1.0:
        raise ValueError(
            f"tolerance must be in [0.0, 1.0), got {tolerance!r}")

    relaxed = _copy.deepcopy(schema)

    def _walk(node):
        if isinstance(node, dict):
            if "minLength" in node and isinstance(node["minLength"], int):
                node["minLength"] = max(
                    0, _math.floor(node["minLength"] * (1.0 - tolerance)))
            if "maxLength" in node and isinstance(node["maxLength"], int):
                node["maxLength"] = _math.ceil(
                    node["maxLength"] * (1.0 + tolerance))
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)

    _walk(relaxed)
    return relaxed


def _is_length_bound_error(err: jsonschema.ValidationError) -> bool:
    """True iff a validation error is purely a ``minLength`` / ``maxLength``
    violation (the kinds the tolerance gate is allowed to relax).

    Uses ``ValidationError.validator`` which is set by jsonschema to the
    failing keyword name.
    """
    return err.validator in ("minLength", "maxLength")


def validate_with_length_tolerance(
    instance,
    schema: dict,
    tolerance: float = 0.10,
) -> tuple[bool, list[ValidationIssue]]:
    """Strict-first, tolerance-fallback validation.

    1. Validate ``instance`` against ``schema`` strictly.
    2. If strict pass → return ``(True, [])``.
    3. If strict fail and **all** errors are ``minLength`` / ``maxLength``
       violations → re-validate against ``relaxed_schema_for_length(schema,
       tolerance)``; relaxed pass → return ``(True, [])``.
    4. Otherwise (relaxed still fails, or strict errors include any other
       keyword) → return ``(False, [ValidationIssue(...)])`` carrying the
       original strict errors.

    The tolerance branch is silent: no artifact metadata is added. Callers
    that need to know whether tolerance was used can compare the boolean
    result against an additional strict-only check.
    """
    if not 0.0 <= tolerance < 1.0:
        raise ValueError(
            f"tolerance must be in [0.0, 1.0), got {tolerance!r}")

    strict_validator = jsonschema.Draft202012Validator(schema)
    strict_errors = list(strict_validator.iter_errors(instance))

    if not strict_errors:
        return True, []

    # Tolerance is permitted only when EVERY violation is a length bound.
    # A single ``required`` / ``enum`` / ``pattern`` / etc. violation
    # blocks the relaxation.
    if not all(_is_length_bound_error(e) for e in strict_errors):
        return False, [
            ValidationIssue(
                "error", "(length_tolerance_gate)",
                f"Schema violation at "
                f"{'.'.join(str(p) for p in e.absolute_path) or '(root)'}: "
                f"{e.message}")
            for e in strict_errors
        ]

    relaxed = relaxed_schema_for_length(schema, tolerance)
    relaxed_validator = jsonschema.Draft202012Validator(relaxed)
    relaxed_errors = list(relaxed_validator.iter_errors(instance))

    if not relaxed_errors:
        return True, []

    return False, [
        ValidationIssue(
            "error", "(length_tolerance_gate)",
            f"Schema violation at "
            f"{'.'.join(str(p) for p in e.absolute_path) or '(root)'}: "
            f"{e.message}")
        for e in strict_errors
    ]
