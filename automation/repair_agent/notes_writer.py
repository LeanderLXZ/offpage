"""Persists accepted SourceNotes to canon/extraction_notes/{stage}.jsonl.

One file per (entity, stage). Characters live under
``characters/{char}/canon/extraction_notes/``, world-level artifacts
under ``world/extraction_notes/``. The path is derived from the
extracted file's path so one writer handles both.

Note IDs are assigned per (entity, stage): SN-S{stage:03d}-{seq:02d}.
``seq`` continues from whatever the existing file already contains so
re-running a stage's repair after partial acceptance keeps a stable,
monotonic numbering.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import tempfile
from pathlib import Path

from .protocol import SourceNote

logger = logging.getLogger(__name__)


class NotesWriter:
    """Derives note paths and appends SourceNotes atomically."""

    def __init__(self, work_path: str) -> None:
        self._work_path = Path(work_path).resolve()
        # (entity_root_str, stage_id) -> next seq
        self._seq_cache: dict[tuple[str, str], int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def notes_path_for(self, file_path: str, stage_id: str) -> Path:
        """Return the extraction_notes/{stage}.jsonl path for a file.

        Resolves the entity root (``.../canon`` for characters,
        ``.../world`` for world artifacts) and appends
        ``extraction_notes/{stage_id}.jsonl``.
        """
        entity_root = self._entity_root(file_path)
        return entity_root / "extraction_notes" / f"{stage_id}.jsonl"

    def next_seq(self, file_path: str, stage_id: str) -> int:
        """Return the next SN seq for this (entity, stage) pair."""
        entity_root = self._entity_root(file_path)
        key = (str(entity_root), stage_id)
        if key not in self._seq_cache:
            self._seq_cache[key] = self._load_max_seq(
                self.notes_path_for(file_path, stage_id)) + 1
        seq = self._seq_cache[key]
        return seq

    def allocate_note_id(self, file_path: str, stage_id: str) -> str:
        """Reserve and format the next note_id for (entity, stage)."""
        seq = self.next_seq(file_path, stage_id)
        stage_num = int(stage_id.lstrip("S"))
        note_id = f"SN-S{stage_num:03d}-{seq:02d}"
        self._seq_cache[(str(self._entity_root(file_path)), stage_id)] = seq + 1
        return note_id

    def append(self, notes: list[SourceNote]) -> list[Path]:
        """Append notes, atomic per target file. Returns written paths."""
        if not notes:
            return []

        # Group by target path — each file is appended in one rewrite.
        by_path: dict[Path, list[SourceNote]] = {}
        for note in notes:
            path = self.notes_path_for(note.file, note.stage_id)
            by_path.setdefault(path, []).append(note)

        written: list[Path] = []
        for path, path_notes in by_path.items():
            self._append_file(path, path_notes)
            written.append(path)
            logger.info("wrote %d note(s) to %s", len(path_notes), path)
        return written

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _entity_root(self, file_path: str) -> Path:
        """Find the entity root (``.../canon`` or ``.../world``).

        Accepts both absolute and work-relative paths.
        """
        p = Path(file_path)
        if not p.is_absolute():
            p = self._work_path / p
        parts = p.parts
        # Prefer deepest `canon` (character) or `world` (world-level).
        for anchor in ("canon", "world"):
            if anchor in parts:
                idx = len(parts) - 1 - parts[::-1].index(anchor)
                return Path(*parts[: idx + 1])
        raise ValueError(
            f"cannot derive entity root from {file_path!r} — "
            "expected a 'canon/' or 'world/' ancestor")

    def _load_max_seq(self, path: Path) -> int:
        if not path.exists():
            return 0
        max_seq = 0
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                nid = obj.get("note_id", "")
                # SN-S###-##
                if len(nid) >= 10 and nid.startswith("SN-S"):
                    try:
                        max_seq = max(max_seq, int(nid.split("-")[-1]))
                    except ValueError:
                        continue
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("notes_writer: could not read %s: %s", path, exc)
        return max_seq

    def _append_file(self, path: Path, notes: list[SourceNote]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = ""
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            if existing and not existing.endswith("\n"):
                existing += "\n"
        new_lines = "".join(
            json.dumps(_serialize_note(n), ensure_ascii=False) + "\n"
            for n in notes
        )
        # Atomic write: tmp file + rename (same dir, same filesystem).
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=".note-", suffix=".jsonl.tmp")
        try:
            with open(fd, "w", encoding="utf-8") as fh:
                fh.write(existing + new_lines)
            Path(tmp_name).replace(path)
        except Exception:
            Path(tmp_name).unlink(missing_ok=True)
            raise


def _serialize_note(note: SourceNote) -> dict:
    """SourceNote → jsonschema-compliant dict (line_range as list)."""
    d = dataclasses.asdict(note)
    # source_evidence.line_range is a tuple in-memory; schema wants array.
    ev = d.get("source_evidence")
    if isinstance(ev, dict) and "line_range" in ev:
        ev["line_range"] = list(ev["line_range"])
    return d
