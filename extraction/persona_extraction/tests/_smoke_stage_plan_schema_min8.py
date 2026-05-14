"""Smoke test for stage_plan.schema.json chapter_count.minimum=8 hard gate.

Verifies the schema directly rejects monolithic LLM outputs whose
chapter_count violates the [8, 15] closed range, replacing the prior
design where minimum=1 + code-layer ``_check_stage_plan_limits`` was the
sole enforcer of the lower bound. Pairs with decision #27i
(schema-gate-as-retry-trigger): violations now feed into the existing
``prior_error`` retry path instead of needing a separate code-layer
abort.

Five scenarios:

  (A) chapter_count=8  → schema valid (lower bound)
  (B) chapter_count=15 → schema valid (upper bound)
  (C) chapter_count=5  → schema invalid (minimum=8 violated)
  (D) chapter_count=16 → schema invalid (maximum=15 violated)
  (E) chapter_count=1  → schema invalid (minimum=8 violated; documents
        the known trade-off that ``_build_light_novel_stage_plan``-
        derived stage_plan.json is schema-invalid by design — the
        derivation path bypasses schema validation entirely, see
        decisions.md #27m)

Run:  python -m extraction.persona_extraction.tests._smoke_stage_plan_schema_min8
"""

from __future__ import annotations

import sys
from typing import Any

import jsonschema

from ..orchestrator import _stage_plan_validator


def _make_stage_plan(chapter_count: int) -> dict[str, Any]:
    """Build a minimal valid stage_plan with one stage of given chapter_count."""
    end = chapter_count
    return {
        "work_id": "smoke",
        "total_chapters": end,
        "stages": [
            {
                "stage_id": "S001",
                "stage_title": "smoke stage",
                "chapters": f"C0001-C{end:04d}",
                "chapter_count": chapter_count,
                "boundary_reason": "smoke test boundary",
            }
        ],
    }


def _validate(chapter_count: int) -> tuple[bool, str]:
    """Return (is_valid, first_error_msg_or_empty)."""
    validator = _stage_plan_validator()
    errors = list(validator.iter_errors(_make_stage_plan(chapter_count)))
    if not errors:
        return True, ""
    return False, errors[0].message


def _scenario(label: str, chapter_count: int, expect_valid: bool,
              expect_msg_substr: str = "") -> bool:
    is_valid, msg = _validate(chapter_count)
    if expect_valid:
        ok = is_valid
    else:
        ok = (not is_valid) and (
            expect_msg_substr in msg if expect_msg_substr else True)
    state = "valid" if is_valid else f"invalid: {msg}"
    print(f"[{label}] chapter_count={chapter_count}: {state} → "
          f"{'OK' if ok else 'FAIL'}")
    return ok


def main() -> int:
    results: list[bool] = []
    # (A) lower bound — valid
    results.append(_scenario("A", 8, expect_valid=True))
    # (B) upper bound — valid
    results.append(_scenario("B", 15, expect_valid=True))
    # (C) below minimum — invalid (minimum=8)
    results.append(_scenario("C", 5, expect_valid=False,
                             expect_msg_substr="minimum"))
    # (D) above maximum — invalid (maximum=15)
    results.append(_scenario("D", 16, expect_valid=False,
                             expect_msg_substr="maximum"))
    # (E) light_novel-style chapter_count=1 — invalid (known trade-off
    #     documented in decisions.md #27m; derivation path bypasses schema)
    results.append(_scenario("E", 1, expect_valid=False,
                             expect_msg_substr="minimum"))

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\nSummary: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
