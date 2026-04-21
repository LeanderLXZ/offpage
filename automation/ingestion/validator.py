"""Source-package validator — ingestion gate.

After ``prompts/ingestion/原始资料规范化.md`` produces the source work
package (``sources/works/{work_id}/``) this validator checks that the
three required metadata files exist, parse as JSON, and match their
schemas. It runs before Phase 0 so ingestion issues surface immediately
rather than during extraction.

Usage
-----

    python -m automation.ingestion.validator <work_id>

Exit code is 0 on pass, 1 on fail. A human-readable report is printed
to stdout.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import jsonschema
except ImportError as _jsonschema_exc:  # pragma: no cover
    raise ImportError(
        "jsonschema is a required dependency of persona-engine ingestion "
        "validation. Install it with `pip install jsonschema`."
    ) from _jsonschema_exc


REQUIRED_FILES: tuple[tuple[str, str], ...] = (
    ("manifest.json", "work/work_manifest.schema.json"),
    ("metadata/book_metadata.json", "work/book_metadata.schema.json"),
    ("metadata/chapter_index.json", "work/chapter_index.schema.json"),
)


@dataclass
class ValidationIssue:
    severity: str
    file: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.file}: {self.message}"


@dataclass
class ValidationReport:
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def summary(self) -> str:
        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        lines = [
            f"Source package validation: {'PASSED' if self.passed else 'FAILED'}",
            f"  Errors: {len(errors)}, Warnings: {len(warnings)}",
        ]
        for issue in self.issues:
            lines.append(f"  {issue}")
        return "\n".join(lines)


def _load_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_schema(schema_dir: Path, rel: str) -> dict:
    return json.loads((schema_dir / rel).read_text(encoding="utf-8"))


def _validate_against_schema(
    data: object, schema: dict, file_label: str
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    for err in sorted(validator.iter_errors(data), key=lambda e: e.path):
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        issues.append(
            ValidationIssue("error", file_label, f"{loc}: {err.message}")
        )
    return issues


def validate_source_package(
    project_root: Path, work_id: str, schema_dir: Path | None = None
) -> ValidationReport:
    """Validate the source package for ``work_id``.

    Checks:

    - each required file exists
    - each file parses as JSON
    - each file validates against its schema
    - chapter_count in book_metadata matches len(chapter_index)
    - chapter_index sequence numbers are strictly 1..N consecutive
    """
    schema_dir = schema_dir or (project_root / "schemas")
    source_dir = project_root / "sources" / "works" / work_id
    issues: list[ValidationIssue] = []

    if not source_dir.exists():
        issues.append(
            ValidationIssue(
                "error",
                str(source_dir),
                "source package directory does not exist",
            )
        )
        return ValidationReport(passed=False, issues=issues)

    loaded: dict[str, object] = {}

    for rel, schema_rel in REQUIRED_FILES:
        path = source_dir / rel
        label = str(path)
        if not path.exists():
            issues.append(ValidationIssue("error", label, "missing"))
            continue
        data = _load_json(path)
        if data is None:
            issues.append(ValidationIssue("error", label, "invalid JSON"))
            continue
        try:
            schema = _load_schema(schema_dir, schema_rel)
        except Exception as exc:
            issues.append(
                ValidationIssue(
                    "error", label, f"failed to load schema {schema_rel}: {exc}"
                )
            )
            continue
        issues.extend(_validate_against_schema(data, schema, label))
        loaded[rel] = data

    bm = loaded.get("metadata/book_metadata.json")
    ci = loaded.get("metadata/chapter_index.json")
    if isinstance(bm, dict) and isinstance(ci, list):
        declared = bm.get("chapter_count")
        actual = len(ci)
        if isinstance(declared, int) and declared != actual:
            issues.append(
                ValidationIssue(
                    "error",
                    str(source_dir / "metadata/book_metadata.json"),
                    f"chapter_count={declared} disagrees with "
                    f"chapter_index length={actual}",
                )
            )
    if isinstance(ci, list):
        for idx, entry in enumerate(ci, start=1):
            if not isinstance(entry, dict):
                continue
            seq = entry.get("sequence")
            if seq != idx:
                issues.append(
                    ValidationIssue(
                        "error",
                        str(source_dir / "metadata/chapter_index.json"),
                        f"sequence at index {idx - 1} is {seq}, "
                        f"expected {idx} (must be strictly consecutive)",
                    )
                )
                break

    passed = not any(i.severity == "error" for i in issues)
    return ValidationReport(passed=passed, issues=issues)


def _project_root_from_this_file() -> Path:
    # automation/ingestion/validator.py → parents[2] = repo root
    return Path(__file__).resolve().parents[2]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            "usage: python -m automation.ingestion.validator <work_id>",
            file=sys.stderr,
        )
        return 2
    work_id = argv[1]
    report = validate_source_package(_project_root_from_this_file(), work_id)
    print(report.summary())
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
