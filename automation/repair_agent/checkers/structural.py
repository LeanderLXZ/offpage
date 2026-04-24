"""L2 — Structural checker.

Business-rule validation: field counts, string lengths, ID format
patterns, cross-file consistency.  Zero LLM tokens.

Rules are driven by configuration, not hardcoded.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from automation.persona_extraction.validator import (
    importance_for_target,
    importance_min_examples,
)

from . import BaseChecker
from ..protocol import FileEntry, Issue

_MEMORY_ID_RE = re.compile(r"^M-S(\d{3})-(\d{2})$")
_EVENT_ID_RE = re.compile(r"^E-S(\d{3})-(\d{2})$")
_SCENE_ID_RE = re.compile(r"^SC-S(\d{3})-(\d{2})$")


class StructuralChecker(BaseChecker):
    """Layer 2: business-rule checks."""

    layer = 2

    def __init__(
        self,
        importance_map: dict[str, str] | None = None,
        relationship_history_summary_max_chars: int = 100,
    ):
        self._importance_map = importance_map or {}
        self._rel_history_max_chars = relationship_history_summary_max_chars

    def check(self, files: list[FileEntry], **kwargs) -> list[Issue]:
        issues: list[Issue] = []
        for f in files:
            content = f.content if f.content is not None else f.load()
            if content is None:
                continue
            p = Path(f.path)

            # List content covers both .jsonl and .json-array files
            # (e.g., memory_timeline/{stage_id}.json). Both need ID-format
            # checks driven by the entry's own ID field.
            if isinstance(content, list):
                issues.extend(self._check_jsonl(f.path, content, p.name))
            elif isinstance(content, dict):
                issues.extend(self._check_dict(f.path, content, p))
        return issues

    # ------------------------------------------------------------------
    # Dict-based checks (stage_snapshot, identity, etc.)
    # ------------------------------------------------------------------

    def _check_dict(self, path: str, data: dict, p: Path) -> list[Issue]:
        issues: list[Issue] = []

        # --- stage_id alignment ---
        if "stage_id" in data and "expected_stage_id" in (data.get("_repair_hints") or {}):
            expected = data["_repair_hints"]["expected_stage_id"]
            if data["stage_id"] != expected:
                issues.append(Issue(
                    file=path, json_path="$.stage_id",
                    category="structural", severity="error",
                    rule="stage_id_alignment",
                    message=f"stage_id '{data['stage_id']}' != expected '{expected}'",
                    context={"expected": expected, "actual": data["stage_id"]},
                ))

        # --- Snapshot depth checks ---
        if "voice_state" in data:
            issues.extend(self._check_target_map(
                path, data, "voice_state", "target_voice_map",
                "dialogue_examples",
            ))
        if "behavior_state" in data:
            issues.extend(self._check_target_map(
                path, data, "behavior_state", "target_behavior_map",
                "action_examples",
            ))

        # --- relationships: driving_events + relationship_history_summary ---
        if "relationships" in data and isinstance(data["relationships"], list):
            for idx, rel in enumerate(data["relationships"]):
                if not isinstance(rel, dict):
                    continue
                target = (rel.get("target_label")
                          or rel.get("target_character_id")
                          or f"#{idx}")
                events = rel.get("driving_events")
                if not events or (isinstance(events, list) and len(events) == 0):
                    issues.append(Issue(
                        file=path,
                        json_path=f"$.relationships[{idx}].driving_events",
                        category="structural", severity="warning",
                        rule="driving_events_non_empty",
                        message=f"No driving_events for relationship with {target}",
                    ))
                summary = rel.get("relationship_history_summary")
                if not isinstance(summary, str) or not summary.strip():
                    issues.append(Issue(
                        file=path,
                        json_path=(f"$.relationships[{idx}]"
                                   f".relationship_history_summary"),
                        category="structural", severity="warning",
                        rule="relationship_history_summary_non_empty",
                        message=(f"Missing/empty relationship_history_summary "
                                 f"for relationship with {target}"),
                    ))
                elif len(summary) > self._rel_history_max_chars:
                    issues.append(Issue(
                        file=path,
                        json_path=(f"$.relationships[{idx}]"
                                   f".relationship_history_summary"),
                        category="structural", severity="error",
                        rule="relationship_history_summary_max_length",
                        message=(f"relationship_history_summary too long "
                                 f"for {target}: {len(summary)} chars "
                                 f"(max {self._rel_history_max_chars})"),
                        context={
                            "current_length": len(summary),
                            "max": self._rel_history_max_chars,
                            "target": target,
                        },
                    ))

        # --- character_arc required with stage_delta ---
        if "stage_delta" in data and "character_arc" not in data:
            issues.append(Issue(
                file=path, json_path="$.character_arc",
                category="structural", severity="warning",
                rule="character_arc_with_stage_delta",
                message="stage_delta present but character_arc missing",
            ))

        return issues

    # ------------------------------------------------------------------
    # JSONL checks (memory_digest, world_event_digest)
    # ------------------------------------------------------------------

    def _check_jsonl(self, path: str, entries: list,
                     filename: str) -> list[Issue]:
        issues: list[Issue] = []
        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue

            # memory_digest ID format
            mid = entry.get("memory_id")
            if mid is not None and not _MEMORY_ID_RE.match(str(mid)):
                issues.append(Issue(
                    file=path, json_path=f"$[{idx}].memory_id",
                    category="structural", severity="error",
                    rule="memory_id_format",
                    message=f"Invalid memory_id format: '{mid}' (expected M-S###-##)",
                    context={"value": str(mid)},
                ))

            # world_event_digest ID format
            eid = entry.get("event_id")
            if eid is not None and not _EVENT_ID_RE.match(str(eid)):
                issues.append(Issue(
                    file=path, json_path=f"$[{idx}].event_id",
                    category="structural", severity="error",
                    rule="event_id_format",
                    message=f"Invalid event_id format: '{eid}' (expected E-S###-##)",
                    context={"value": str(eid)},
                ))

        return issues

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_target_map(
        self, path: str, data: dict, state_key: str,
        map_key: str, examples_key: str,
    ) -> list[Issue]:
        """Validate target_voice_map / target_behavior_map (schema: array
        of objects keyed by ``target_type``).
        """
        issues: list[Issue] = []
        state = data.get(state_key, {})
        target_map = state.get(map_key, [])
        if not isinstance(target_map, list):
            return issues

        for idx, entry in enumerate(target_map):
            if not isinstance(entry, dict):
                continue
            target_name = entry.get("target_type") or f"#{idx}"
            examples = entry.get(examples_key, [])
            if not isinstance(examples, list):
                continue
            count = len(examples)
            importance = importance_for_target(
                target_name, self._importance_map)
            threshold = importance_min_examples(importance)
            if count < threshold:
                issues.append(Issue(
                    file=path,
                    json_path=(f"$.{state_key}.{map_key}[{idx}]"
                               f".{examples_key}"),
                    category="structural", severity="warning",
                    rule="min_examples",
                    message=(f"{examples_key} for '{target_name}' "
                             f"({importance}): {count} < {threshold}"),
                    context={
                        "current": count, "required": threshold,
                        "importance": importance, "target": target_name,
                        "coverage_shortage": True,
                    },
                ))
        return issues
